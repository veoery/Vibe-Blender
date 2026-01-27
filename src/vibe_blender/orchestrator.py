"""Main orchestrator for the Vibe-Blender pipeline.

Implements the ReAct (Reasoning + Acting) loop that coordinates
all agents and execution components.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from .llm import create_llm, BaseLLM
from .agents import PlannerAgent, GeneratorAgent, CriticAgent
from .execution import BlenderExecutor, Watchdog
from .models import (
    UserPrompt,
    PipelineState,
    PipelineStatus,
    IterationRecord,
    CritiqueVerdict,
    ClarificationRequest,
    ClarificationResponse,
)

logger = logging.getLogger(__name__)
console = Console()


class Orchestrator:
    """Main pipeline orchestrator implementing the ReAct loop.

    The orchestrator coordinates:
    1. Planner: Parse prompt → Scene description
    2. Generator: Create Blender script
    3. Executor: Run Blender
    4. Critic: Evaluate output
    5. Loop back to Generator with feedback if needed
    """

    def __init__(
        self,
        config: Config,
        llm: Optional[BaseLLM] = None,
        on_iteration: Optional[Callable[[IterationRecord], None]] = None,
        interactive: bool = True,
    ):
        """Initialize the orchestrator.

        Args:
            config: Application configuration
            llm: Optional LLM backend (created from config if not provided)
            on_iteration: Optional callback for iteration events
            interactive: Whether to enable interactive clarification prompts (default: True)
        """
        self.config = config
        self.interactive = interactive

        # Create LLM if not provided
        if llm is None:
            llm_config = config.llm
            if llm_config.backend == "openai":
                llm = create_llm(
                    "openai",
                    model=llm_config.openai.model,
                    api_key=llm_config.openai.api_key,
                )
            else:
                llm = create_llm(
                    "ollama",
                    base_url=llm_config.ollama.base_url,
                    model=llm_config.ollama.model,
                    vision_model=llm_config.ollama.vision_model,
                )

        self.llm = llm

        # Initialize agents
        self.planner = PlannerAgent(llm)
        self.generator = GeneratorAgent(llm)
        self.critic = CriticAgent(llm)

        # Initialize execution components
        self.executor = BlenderExecutor(config)
        self.watchdog = Watchdog(config.pipeline.max_retries)

        # Callbacks
        self.on_iteration = on_iteration
        self.on_clarification: Optional[
            Callable[[ClarificationRequest], Optional[ClarificationResponse]]
        ] = None

    def run(
        self,
        prompt: str,
        output_dir: Optional[Path] = None,
        reference_images: Optional[list[Path]] = None,
    ) -> PipelineState:
        """Run the full pipeline for a given prompt.

        Args:
            prompt: User's text prompt describing the 3D model
            output_dir: Optional output directory (defaults from config)
            reference_images: Optional reference image paths for style guidance

        Returns:
            Final PipelineState with results
        """
        # Set up output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.config.pipeline.output_dir) / timestamp
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting pipeline for: {prompt[:100]}...")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Interactive mode: {self.interactive}")
        logger.info(f"Reference images: {len(reference_images) if reference_images else 0}")

        try:
            # Phase 0: Clarification (if interactive)
            if self.interactive:
                console.print("[bold blue]Phase 0: Analyzing prompt...[/bold blue]")
                logger.info("Phase 0: Clarification check...")
                user_prompt = self._clarification_phase(prompt)
            else:
                logger.info("Non-interactive mode - skipping clarification phase")
                user_prompt = UserPrompt(text=prompt)

            # Add reference images to UserPrompt
            if reference_images:
                user_prompt.reference_images = reference_images

                # Validate references
                errors = user_prompt.validate_references()
                if errors:
                    for error in errors:
                        logger.error(error)
                    raise ValueError(f"Reference image validation failed: {errors[0]}")

            # Initialize state
            state = PipelineState(
                user_prompt=user_prompt,
                max_retries=self.config.pipeline.max_retries,
                output_dir=output_dir,
            )

            # Phase 0.5: Analyze references (if provided)
            reference_analysis = None
            if user_prompt.has_references():
                console.print(f"[bold blue]Analyzing {len(user_prompt.reference_images)} reference image(s)...[/bold blue]")
                logger.info("Phase 0.5: Reference image analysis...")
                reference_analysis = self.planner.analyze_references(
                    user_prompt.reference_images,
                    user_prompt.text,
                )
                logger.info(f"Reference style: {reference_analysis.style_notes[:100]}...")

            # Phase 1: Planning
            console.print("[bold blue]Phase 1: Planning scene...[/bold blue]")
            logger.info("Phase 1: Planning scene...")
            state.scene_description = self.planner.plan_with_references(
                user_prompt.text,
                user_prompt.clarifications,
                reference_analysis,
            )
            logger.info(f"Scene planned: {state.scene_description.summary}")

            # Phase 2: ReAct Loop
            console.print("[bold blue]Phase 2: Generation loop...[/bold blue]")
            logger.info("Phase 2: Generation loop...")
            self._run_react_loop(state)

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            self.watchdog.update_state_for_failure(state, str(e))

        # Log final status
        self._log_completion(state)

        return state

    def _clarification_phase(self, prompt: str) -> UserPrompt:
        """Handle clarification detection and collection.

        Args:
            prompt: The user's original prompt text

        Returns:
            UserPrompt with optional clarifications
        """
        # Check if clarification needed
        logger.info("Checking if clarification is needed...")
        request = self.planner.check_clarity(prompt)

        if not request.needs_clarification:
            logger.info("No clarification needed - prompt is clear")
            return UserPrompt(text=prompt)

        logger.info(f"Clarification needed: {request.reason}")
        logger.info(f"Questions: {len(request.questions)}")

        # Get user responses via callback
        if self.on_clarification:
            console.print("[yellow]Clarification needed...[/yellow]")
            response = self.on_clarification(request)
            if response:
                logger.info(f"Received {len(response.answers)} clarification answers")
                return UserPrompt(text=prompt, clarifications=response)
            else:
                logger.info("User declined to provide clarifications - proceeding with assumptions")

        # No callback or no response - proceed without clarifications
        return UserPrompt(text=prompt)

    def _run_react_loop(self, state: PipelineState) -> None:
        """Run the ReAct loop until success or max retries.

        Args:
            state: Pipeline state to update
        """
        feedback = None

        while self.watchdog.can_continue(state):
            iteration = state.current_iteration + 1
            console.print(f"\n[cyan]Iteration {iteration}/{state.max_retries}[/cyan]")
            logger.info(f"=== Iteration {iteration}/{state.max_retries} ===")

            record = IterationRecord(iteration=iteration, script=None)

            try:
                # Generate script
                console.print("  Generating Blender script...")
                logger.info("Generating Blender script...")
                if feedback:
                    script = self.generator.refine(
                        original_script=state.iterations[-1].script,
                        scene_description=state.scene_description,
                        feedback=feedback,
                        iteration=iteration,
                    )
                else:
                    script = self.generator.generate(
                        scene_description=state.scene_description,
                        iteration=iteration,
                    )
                record.script = script
                logger.info("Script generated successfully")

                # Execute script
                console.print("  Executing in Blender...")
                logger.info("Executing in Blender...")
                render_output = self.executor.execute(script, state.output_dir)
                record.render_output = render_output
                logger.info(f"Blender execution complete. Grid: {render_output.grid_image is not None}, Error: {render_output.blender_error is not None}")

                # Critique output
                console.print("  Analyzing output...")
                logger.info("Analyzing output with vision model...")
                critique = self.critic.critique(
                    render_output=render_output,
                    user_prompt=state.user_prompt.text,
                    scene_description=state.scene_description,
                    iteration=iteration,
                    reference_images=state.user_prompt.reference_images if state.user_prompt.has_references() else None,
                )
                record.critique = critique

                # Log critique result
                verdict_color = "green" if critique.verdict == CritiqueVerdict.PASS else "red"
                console.print(
                    f"  Verdict: [{verdict_color}]{critique.verdict.value.upper()}[/{verdict_color}] "
                    f"(Score: {critique.score:.1f}/10)"
                )
                logger.info(f"Verdict: {critique.verdict.value.upper()} (Score: {critique.score:.1f}/10)")

                if critique.verdict == CritiqueVerdict.FAIL:
                    console.print(f"  Feedback: {critique.feedback[:100]}...")
                    logger.info(f"Feedback: {critique.feedback[:200]}...")

                    # Merge feedback, issues, and suggestions into comprehensive feedback
                    feedback_parts = [critique.feedback]

                    if critique.issues:
                        issues_text = "\n".join(f"  - {issue}" for issue in critique.issues)
                        feedback_parts.append(f"\nKey Issues:\n{issues_text}")

                    if critique.suggestions:
                        suggestions_text = "\n".join(f"  - {suggestion}" for suggestion in critique.suggestions)
                        feedback_parts.append(f"\nSuggestions:\n{suggestions_text}")

                    feedback = "\n".join(feedback_parts)

            except Exception as e:
                logger.error(f"Iteration {iteration} failed: {e}")
                record.error = str(e)
                feedback = f"Error in previous iteration: {e}"

            # Record iteration
            state.add_iteration(record)

            # Callback
            if self.on_iteration:
                self.on_iteration(record)

            # Check for completion
            if self.watchdog.check_completion(state):
                console.print("[bold green]Success![/bold green]")
                logger.info("SUCCESS - Model passed critique!")
                self.watchdog.update_state_for_success(state)
                return

            # Check for early stop conditions
            should_stop, reason = self.watchdog.should_stop_early(state)
            if should_stop:
                console.print(f"[yellow]Stopping early: {reason}[/yellow]")
                logger.warning(f"Stopping early: {reason}")
                self.watchdog.update_state_for_failure(state, reason)
                return

        # Max retries reached
        console.print("[yellow]Max retries reached[/yellow]")
        logger.warning("Max retries reached")
        self.watchdog.update_state_for_max_retries(state)

    def _log_completion(self, state: PipelineState) -> None:
        """Log pipeline completion status.

        Args:
            state: Final pipeline state
        """
        duration = (state.completed_at or datetime.now()) - state.started_at

        console.print("\n" + "=" * 50)
        console.print(f"[bold]Pipeline Complete[/bold]")
        console.print(f"Status: {state.status.value}")
        console.print(f"Iterations: {state.current_iteration}")
        console.print(f"Duration: {duration.total_seconds():.1f}s")

        logger.info("=" * 50)
        logger.info("Pipeline Complete")
        logger.info(f"Status: {state.status.value}")
        logger.info(f"Iterations: {state.current_iteration}")
        logger.info(f"Duration: {duration.total_seconds():.1f}s")

        if state.final_output:
            console.print(f"\nOutput directory: {state.output_dir}")
            logger.info(f"Output directory: {state.output_dir}")
            if state.final_output.blend_file:
                console.print(f"Blend file: {state.final_output.blend_file}")
                logger.info(f"Blend file: {state.final_output.blend_file}")
            if state.final_output.grid_image:
                console.print(f"Grid image: {state.final_output.grid_image}")
                logger.info(f"Grid image: {state.final_output.grid_image}")
            if state.final_output.turntable_gif:
                console.print(f"Turntable GIF: {state.final_output.turntable_gif}")
                logger.info(f"Turntable GIF: {state.final_output.turntable_gif}")

        console.print("=" * 50)
        logger.info("=" * 50)


def run_pipeline(
    prompt: str,
    config_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> PipelineState:
    """Convenience function to run the pipeline.

    Args:
        prompt: User's text prompt
        config_path: Optional path to config file
        output_dir: Optional output directory

    Returns:
        Final PipelineState
    """
    config = Config.load(config_path)
    orchestrator = Orchestrator(config)
    return orchestrator.run(prompt, output_dir)
