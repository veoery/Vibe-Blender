"""Command-line interface for Vibe-Blender."""

import logging
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import Config, setup_logging
from .orchestrator import Orchestrator
from .execution import BlenderExecutor
from .models import ClarificationRequest, ClarificationResponse

app = typer.Typer(
    name="vibe-blender",
    help="Text-to-3D generation with ReAct self-correction",
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Text description of the 3D model to generate"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for generated files"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
    max_retries: Optional[int] = typer.Option(
        None, "--max-retries", "-r", help="Maximum retry attempts (overrides config)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        help="Disable interactive clarification prompts"
    ),
):
    """Generate a 3D model from a text prompt.

    By default, the planner will ask clarifying questions if your prompt
    is unclear. Use --no-interactive to disable this behavior.

    Examples:
        vibe-blender generate "A table"  # Will ask what type of table
        vibe-blender generate "A cyberpunk coffee table"  # Clear, no questions
        vibe-blender generate "A table" --no-interactive  # Skip questions
    """
    # Load configuration
    try:
        cfg = Config.load(config)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("Run 'vibe-blender init' to create a configuration file.")
        raise typer.Exit(1)

    # Override max retries if specified
    if max_retries:
        cfg.pipeline.max_retries = max_retries

    # Determine output directory
    if output is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(cfg.pipeline.output_dir) / timestamp
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    # Set up logging (to console and file)
    if verbose:
        cfg.logging.level = "DEBUG"
    log_file = output / "pipeline.log"
    setup_logging(cfg, log_file=log_file)

    # Show configuration
    interactive = not no_interactive
    console.print(Panel(f"[bold]Vibe-Blender v{__version__}[/bold]"))
    console.print(f"Prompt: {prompt}")
    console.print(f"Backend: {cfg.llm.backend}")
    console.print(f"Max retries: {cfg.pipeline.max_retries}")
    console.print(f"Interactive: {'Yes' if interactive else 'No'}")
    console.print(f"Log file: {log_file}")
    console.print()

    # Run the pipeline
    try:
        orchestrator = Orchestrator(cfg, interactive=interactive)

        # Set clarification callback if interactive
        if interactive:
            orchestrator.on_clarification = _handle_clarification_prompt

        state = orchestrator.run(prompt, output)

        # Return appropriate exit code
        if state.status.value == "success":
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _handle_clarification_prompt(
    request: ClarificationRequest
) -> Optional[ClarificationResponse]:
    """Handle clarification requests with interactive CLI prompts.

    Args:
        request: The clarification request from the planner

    Returns:
        ClarificationResponse with user answers, or None if user declines
    """
    logger.info("=" * 60)
    logger.info("CLARIFICATION INTERACTION")
    logger.info("=" * 60)
    logger.info(f"Reason: {request.reason}")
    logger.info(f"Number of questions: {len(request.questions)}")

    console.print("\n[bold yellow]The planner needs clarification:[/bold yellow]")
    console.print(f"[dim]{request.reason}[/dim]\n")

    # Ask if user wants to provide clarifications
    should_clarify = typer.confirm(
        "Answer these questions? (No = proceed with AI assumptions)",
        default=True
    )

    if not should_clarify:
        logger.info("User DECLINED to provide clarifications - proceeding with AI assumptions")
        logger.info("=" * 60)
        console.print("[dim]Proceeding with AI assumptions...[/dim]")
        return None

    logger.info("User ACCEPTED to answer clarification questions")

    answers = {}

    for idx, question in enumerate(request.questions, 1):
        logger.info(f"\nQuestion {idx}/{len(request.questions)}:")
        logger.info(f"  Key: {question.key}")
        logger.info(f"  Question: {question.question}")
        logger.info(f"  Required: {question.required}")
        if question.suggestions:
            logger.info(f"  Suggestions: {question.suggestions}")

        console.print(f"\n[bold]Q: {question.question}[/bold]")

        # Show suggestions
        if question.suggestions:
            console.print("[dim]Suggestions:[/dim]")
            for suggestion in question.suggestions:
                console.print(f"  - {suggestion}")

        # Prompt for answer
        while True:
            answer = typer.prompt(
                f"  {'(Required) ' if question.required else '(Optional) '}Your answer",
                default="" if not question.required else None,
                show_default=False,
            )

            # Validate required
            if question.required and not answer.strip():
                console.print("[red]This question is required[/red]")
                logger.info(f"  Answer: [EMPTY - required field, retrying]")
                continue

            if answer.strip():
                answers[question.key] = answer.strip()
                logger.info(f"  Answer: {answer.strip()}")
            else:
                logger.info(f"  Answer: [SKIPPED - optional field]")
            break

    if not answers:
        logger.info("\nNo answers provided by user - proceeding with AI assumptions")
        logger.info("=" * 60)
        console.print("[dim]No answers provided - proceeding with AI assumptions...[/dim]")
        return None

    logger.info("\nClarification Summary:")
    logger.info(f"  Total answers received: {len(answers)}")
    for key, value in answers.items():
        logger.info(f"    {key}: {value}")
    logger.info("=" * 60)

    console.print(f"\n[green]Received {len(answers)} answer(s). Continuing...[/green]")
    return ClarificationResponse(answers=answers)


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing config file"
    ),
):
    """Initialize a new configuration file.

    Creates a config.yaml file in the current directory with
    default settings that you can customize.
    """
    config_path = Path("config.yaml")
    example_path = Path(__file__).parent.parent.parent / "config.example.yaml"

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    # Copy example config or create default
    if example_path.exists():
        shutil.copy(example_path, config_path)
    else:
        # Create a basic config
        config_content = """# Vibe-Blender Configuration

blender:
  executable: "/Applications/Blender.app/Contents/MacOS/Blender"
  timeout: 120

llm:
  backend: "openai"
  openai:
    model: "gpt-4o"
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3"
    vision_model: "llava"

pipeline:
  max_retries: 5
  output_dir: "./outputs"
  render_resolution: [512, 512]
  save_intermediate: true

logging:
  level: "INFO"
"""
        config_path.write_text(config_content)

    console.print(f"[green]Created config file: {config_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Edit config.yaml to set your Blender executable path")
    console.print("2. Set OPENAI_API_KEY environment variable (or configure Ollama)")
    console.print("3. Run: vibe-blender generate \"Your prompt here\"")


@app.command()
def doctor():
    """Validate your Vibe-Blender setup.

    Checks that all required dependencies and configurations
    are properly set up.
    """
    console.print(Panel("[bold]Vibe-Blender Doctor[/bold]"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    all_ok = True

    # Check config file
    config_path = Config.find_config()
    if config_path:
        table.add_row("Config file", "[green]OK[/green]", str(config_path))
        try:
            cfg = Config.from_yaml(config_path)
        except Exception as e:
            table.add_row("Config valid", "[red]FAIL[/red]", str(e)[:50])
            all_ok = False
            cfg = None
    else:
        table.add_row("Config file", "[red]MISSING[/red]", "Run 'vibe-blender init'")
        all_ok = False
        cfg = None

    # Check Blender
    if cfg:
        blender_path = Path(cfg.blender.executable)
        if blender_path.exists():
            executor = BlenderExecutor(cfg)
            if executor.validate_blender():
                table.add_row("Blender", "[green]OK[/green]", str(blender_path))
            else:
                table.add_row("Blender", "[red]FAIL[/red]", "Found but not working")
                all_ok = False
        else:
            table.add_row("Blender", "[red]MISSING[/red]", f"Not found: {blender_path}")
            all_ok = False

    # Check LLM configuration
    if cfg:
        if cfg.llm.backend == "openai":
            import os
            api_key = cfg.llm.openai.api_key or os.environ.get("OPENAI_API_KEY")
            if api_key:
                masked = api_key[:8] + "..." + api_key[-4:]
                table.add_row("OpenAI API Key", "[green]OK[/green]", masked)
            else:
                table.add_row("OpenAI API Key", "[red]MISSING[/red]", "Set OPENAI_API_KEY")
                all_ok = False
        else:
            # Check Ollama
            import httpx
            try:
                resp = httpx.get(f"{cfg.llm.ollama.base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    table.add_row("Ollama", "[green]OK[/green]", cfg.llm.ollama.base_url)
                else:
                    table.add_row("Ollama", "[red]FAIL[/red]", f"Status: {resp.status_code}")
                    all_ok = False
            except Exception as e:
                table.add_row("Ollama", "[red]FAIL[/red]", "Not reachable")
                all_ok = False

    # Check Python dependencies
    try:
        import PIL
        table.add_row("Pillow", "[green]OK[/green]", PIL.__version__)
    except ImportError:
        table.add_row("Pillow", "[red]MISSING[/red]", "pip install pillow")
        all_ok = False

    try:
        import imageio
        table.add_row("imageio", "[green]OK[/green]", imageio.__version__)
    except ImportError:
        table.add_row("imageio", "[red]MISSING[/red]", "pip install imageio")
        all_ok = False

    console.print(table)

    if all_ok:
        console.print("\n[bold green]All checks passed![/bold green]")
        raise typer.Exit(0)
    else:
        console.print("\n[bold red]Some checks failed. Please fix the issues above.[/bold red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print(f"Vibe-Blender v{__version__}")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
