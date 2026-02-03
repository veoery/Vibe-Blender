"""Generator agent for creating Blender Python scripts."""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from ..llm.base import BaseLLM
from ..models.schemas import SceneDescription, GeneratedScript
from .editor import apply_edits

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "generator.txt"
REFINE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "generator_refine.txt"


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
        self._load_refine_prompt_template()

    def _load_prompt_template(self) -> None:
        """Load the system prompt template."""
        if PROMPT_PATH.exists():
            self.prompt_template = PROMPT_PATH.read_text()
        else:
            logger.warning(f"Prompt template not found at {PROMPT_PATH}, using default")
            self.prompt_template = self._default_prompt()

    def _load_refine_prompt_template(self) -> None:
        """Load the refinement (edit-based) prompt template."""
        if REFINE_PROMPT_PATH.exists():
            self.refine_prompt_template = REFINE_PROMPT_PATH.read_text()
        else:
            logger.warning(f"Refine prompt template not found at {REFINE_PROMPT_PATH}")
            self.refine_prompt_template = None

    def _default_prompt(self) -> str:
        """Return default prompt if template not found."""
        return """You are a Blender Python script generator.
Create a complete, executable script that generates the described 3D model.
Use the bpy module. Save the file using OUTPUT_BLEND_PATH variable.

Scene: {scene_description}
Feedback: {feedback}"""

    def _call_llm(
        self,
        prompt: str,
        reference_images: Optional[list[Path]] = None,
        max_tokens: int = 4000,
    ) -> str:
        """Route a prompt to the LLM, using vision if images are provided."""
        if reference_images:
            logger.info(f"LLM call with {len(reference_images)} reference images")
            return self.llm.analyze_images(
                image_paths=reference_images,
                prompt=prompt,
                max_tokens=max_tokens,
            )

        logger.info("LLM call (text-only)")
        return self.llm.generate(
            prompt=prompt,
            temperature=1.0,
            max_tokens=max_tokens,
        )

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

        scene_json = scene_description.model_dump_json(indent=2)
        prompt = self.prompt_template.format(
            scene_description=scene_json,
            feedback=feedback or "None - this is the first iteration",
        )

        response = self._call_llm(prompt, reference_images, max_tokens=4000)
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

    def _parse_edits(self, response: str) -> list[dict] | None:
        """Extract a JSON array of edits from the LLM response.

        Uses the same fence-detection + bracket-depth-matching approach as
        critic.py's _parse_response / _extract_json_object.

        Returns:
            List of {"old_code": str, "new_code": str} dicts, or None on any
            parse failure.
        """
        json_str = None

        # Method 1: ```json … ```
        m = re.search(r"```json\s*([\s\S]*?)\s*```", response)
        if m:
            json_str = m.group(1).strip()

        # Method 2: ``` … ```
        if not json_str:
            m = re.search(r"```\s*([\s\S]*?)\s*```", response)
            if m:
                json_str = m.group(1).strip()

        # Method 3: find outermost [ … ] with depth matching
        if not json_str:
            json_str = self._extract_json_array(response)

        if not json_str:
            logger.debug("_parse_edits: no JSON array found in response")
            return None

        # Clean trailing commas before the closing bracket
        json_str = re.sub(r",\s*]", "]", json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"_parse_edits: JSON decode error: {e}")
            return None

        if not isinstance(data, list):
            logger.debug("_parse_edits: parsed value is not a list")
            return None

        # Validate each edit entry
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                logger.debug(f"_parse_edits: edit {i + 1} is not a dict")
                return None
            if "old_code" not in item or not isinstance(item["old_code"], str) or not item["old_code"]:
                logger.debug(f"_parse_edits: edit {i + 1} has invalid old_code")
                return None
            if "new_code" not in item or not isinstance(item["new_code"], str):
                logger.debug(f"_parse_edits: edit {i + 1} has invalid new_code")
                return None

        return data

    @staticmethod
    def _extract_json_array(text: str) -> str | None:
        """Extract a complete JSON array from text using bracket-depth matching."""
        start = text.find("[")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == "\\" and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return None

    def refine(
        self,
        original_script: GeneratedScript,
        scene_description: SceneDescription,
        feedback: str,
        iteration: int,
        reference_images: Optional[list[Path]] = None,
    ) -> GeneratedScript:
        """Refine a script based on Critic feedback.

        Attempts edit-based refinement first: asks the LLM for surgical
        {old_code, new_code} edits and applies them to the existing script.
        Falls back to full regeneration if the edit prompt template is missing,
        the LLM response cannot be parsed, or any edit fails to apply.

        Args:
            original_script: The script to refine
            scene_description: Original scene description
            feedback: Feedback from the Critic
            iteration: New iteration number
            reference_images: Optional reference images for style guidance

        Returns:
            Refined GeneratedScript
        """
        # --- Attempt edit-based refinement ---
        if self.refine_prompt_template:
            try:
                prompt = self.refine_prompt_template.format(
                    current_code=original_script.code,
                    feedback=feedback,
                )
                response = self._call_llm(prompt, reference_images, max_tokens=1500)

                edits = self._parse_edits(response)
                if edits is None:
                    raise ValueError("Failed to parse edits from LLM response")

                result = apply_edits(original_script.code, edits)
                if not result.success:
                    raise ValueError(result.error or "Edit application failed")

                logger.info(
                    f"Edit-based refinement succeeded ({result.applied_count} edits applied)"
                )
                return GeneratedScript(
                    code=result.code,
                    iteration=iteration,
                    based_on_feedback=feedback,
                    edit_based=True,
                    edits_applied=result.applied_count,
                )

            except Exception as e:
                logger.warning(
                    f"Edit-based refinement failed ({e}), falling back to full regeneration"
                )

        # --- Fallback: full regeneration (original behavior) ---
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
