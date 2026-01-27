"""Generator agent for creating Blender Python scripts."""

import logging
import re
from pathlib import Path
from typing import Optional

from ..llm.base import BaseLLM
from ..models.schemas import SceneDescription, GeneratedScript

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "generator.txt"


class GeneratorAgent:
    """Agent that generates Blender Python scripts from scene descriptions.

    The Generator takes a structured scene description and produces
    executable Python code using the Blender (bpy) API.
    """

    def __init__(self, llm: BaseLLM):
        """Initialize the Generator agent.

        Args:
            llm: LLM backend for code generation
        """
        self.llm = llm
        self._load_prompt_template()

    def _load_prompt_template(self) -> None:
        """Load the system prompt template."""
        if PROMPT_PATH.exists():
            self.prompt_template = PROMPT_PATH.read_text()
        else:
            logger.warning(f"Prompt template not found at {PROMPT_PATH}, using default")
            self.prompt_template = self._default_prompt()

    def _default_prompt(self) -> str:
        """Return default prompt if template not found."""
        return """You are a Blender Python script generator.
Create a complete, executable script that generates the described 3D model.
Use the bpy module. Save the file using OUTPUT_BLEND_PATH variable.

Scene: {scene_description}
Feedback: {feedback}"""

    def generate(
        self,
        scene_description: SceneDescription,
        iteration: int = 1,
        feedback: Optional[str] = None,
        reference_images: Optional[list[Path]] = None,
    ) -> GeneratedScript:
        """Generate a Blender Python script for the scene.

        Args:
            scene_description: Structured scene description from Planner
            iteration: Current iteration number
            feedback: Optional feedback from previous iteration
            reference_images: Optional reference images for style guidance

        Returns:
            GeneratedScript with the Python code
        """
        logger.info(f"Generating script (iteration {iteration})")

        # Format the prompt with scene description and feedback
        scene_json = scene_description.model_dump_json(indent=2)

        prompt = self.prompt_template.format(
            scene_description=scene_json,
            feedback=feedback or "None - this is the first iteration",
        )

        # Use vision API if images provided
        if reference_images:
            logger.info(f"Generating with {len(reference_images)} reference images")
            response = self.llm.analyze_images(
                image_paths=reference_images,
                prompt=prompt,
                max_tokens=4000,
            )
        else:
            logger.info("Generating without reference images")
            response = self.llm.generate(
                prompt=prompt,
                temperature=1.0,  # Moderate temperature for code generation
                max_tokens=4000,
            )

        # Extract the Python code from the response
        code = self._extract_code(response)

        return GeneratedScript(
            code=code,
            iteration=iteration,
            based_on_feedback=feedback,
        )

    def _extract_code(self, response: str) -> str:
        """Extract Python code from the LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Extracted Python code
        """
        # Try to extract from markdown code blocks
        patterns = [
            r"```python\n(.*?)```",
            r"```\n(.*?)```",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code blocks, check if the whole response looks like Python
        if response.strip().startswith("import") or response.strip().startswith("#"):
            return response.strip()

        # Last resort: return as-is
        logger.warning("Could not extract code block, using raw response")
        return response.strip()

    def refine(
        self,
        original_script: GeneratedScript,
        scene_description: SceneDescription,
        feedback: str,
        iteration: int,
        reference_images: Optional[list[Path]] = None,
    ) -> GeneratedScript:
        """Refine a script based on feedback.

        This is a convenience method that calls generate with feedback.

        Args:
            original_script: The script to refine
            scene_description: Original scene description
            feedback: Feedback from the Critic
            iteration: New iteration number
            reference_images: Optional reference images for style guidance

        Returns:
            Refined GeneratedScript
        """
        # Build comprehensive feedback including the original script
        full_feedback = f"""Previous script (iteration {original_script.iteration}):
```python
{original_script.code}
```

Critic feedback:
{feedback}

Please fix the issues mentioned above while keeping what works well."""

        return self.generate(
            scene_description=scene_description,
            iteration=iteration,
            feedback=full_feedback,
            reference_images=reference_images,
        )
