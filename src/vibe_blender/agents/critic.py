"""Critic agent for evaluating rendered 3D models."""

# from pathlib import Path
# PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "critic.txt"
# print(PROMPT_PATH)

import json
import logging
import re
from pathlib import Path
from typing import Optional

from ..llm.base import BaseLLM
from ..models.schemas import (
    CritiqueResult,
    CritiqueVerdict,
    SceneDescription,
    RenderOutput,
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "critic.txt"

class CriticAgent:
    """Agent that evaluates rendered 3D models against their prompts.

    The Critic uses vision capabilities to analyze render images
    and determine if the model matches the user's intent.
    """

    def __init__(self, llm: BaseLLM, pass_threshold: float = 7.0):
        """Initialize the Critic agent.

        Args:
            llm: LLM backend with vision capabilities
            pass_threshold: Minimum score to pass (default 7.0)
        """
        self.llm = llm
        self.pass_threshold = pass_threshold
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
        return """Evaluate this 3D model render against the user's prompt.
Output JSON: {"verdict": "pass/fail", "score": 0-10, "feedback": "...", "issues": [...], "suggestions": [...]}

User prompt: {user_prompt}
Scene description: {scene_description}"""

    def critique(
        self,
        render_output: RenderOutput,
        user_prompt: str,
        scene_description: SceneDescription,
        iteration: int,
    ) -> CritiqueResult:
        """Analyze rendered images and provide feedback.

        Args:
            render_output: Paths to rendered images
            user_prompt: Original user prompt
            scene_description: Scene description from Planner
            iteration: Current iteration number

        Returns:
            CritiqueResult with verdict and feedback

        Raises:
            FileNotFoundError: If render images don't exist
        """
        logger.info(f"Critiquing render (iteration {iteration})")

        # Check for Blender script errors first
        if render_output.blender_error:
            logger.error(f"Blender script had errors: {render_output.blender_error[:200]}")
            return CritiqueResult(
                verdict=CritiqueVerdict.FAIL,
                score=0.0,
                feedback=f"Blender script failed with error:\n{render_output.blender_error}",
                issues=["Script execution error"],
                suggestions=["Fix the Python error in the generated script"],
                iteration=iteration,
            )

        # Collect images to analyze
        images = []
        if render_output.grid_image and render_output.grid_image.exists():
            images.append(render_output.grid_image)

        if not images:
            logger.error("No render images found for critique")
            return CritiqueResult(
                verdict=CritiqueVerdict.FAIL,
                score=0.0,
                feedback="No render images were produced. The script may have failed. Check blender.log for details.",
                issues=["No render output"],
                suggestions=["Check script for errors", "Verify Blender execution"],
                iteration=iteration,
            )

        # Format the prompt
        # logger.info("Prompt for critic model:\n")
        prompt = self.prompt_template.format(
            user_prompt=user_prompt,
            scene_description=scene_description.model_dump_json(indent=2),
        )
        # logger.info(prompt[:800])

        # Analyze with vision
        response = self.llm.analyze_images(
            image_paths=images,
            prompt=prompt,
        )
        logger.debug(f"Output from critic model: \n{response}")

        return self._parse_response(response, iteration)

    def _parse_response(self, response: str, iteration: int) -> CritiqueResult:
        """Parse the LLM response into a CritiqueResult.

        Args:
            response: Raw LLM response
            iteration: Current iteration number

        Returns:
            Parsed CritiqueResult
        """
        logger.debug(f"Parsing critique response ({len(response)} chars)")

        try:
            # Try multiple methods to extract JSON
            json_str = None

            # Method 1: Look for ```json blocks
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1).strip()
                logger.debug("Found JSON in ```json block")

            # Method 2: Look for ``` blocks
            if not json_str:
                code_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
                if code_match:
                    json_str = code_match.group(1).strip()
                    logger.debug("Found JSON in ``` block")

            # Method 3: Find complete JSON object with balanced braces
            if not json_str:
                json_str = self._extract_json_object(response)
                if json_str:
                    logger.debug("Found JSON via brace matching")

            if not json_str:
                raise ValueError("No JSON found in response")

            # Clean up common issues
            json_str = json_str.strip()

            # Try to parse
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try fixing common issues
                logger.debug(f"Initial parse failed: {e}, attempting fixes")
                # Remove trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                data = json.loads(json_str)

            # Determine verdict (inside try block to catch conversion errors)
            verdict_str = str(data.get("verdict", "fail")).lower()

            # Safe score conversion
            raw_score = data.get("score", 5.0)
            try:
                score = float(raw_score)
                # Clamp to valid range
                score = max(0.0, min(10.0, score))
            except (TypeError, ValueError):
                logger.warning(f"Invalid score value: {raw_score}, defaulting to 5.0")
                score = 5.0

            # Use threshold to determine final verdict
            if verdict_str == "pass" and score >= self.pass_threshold:
                verdict = CritiqueVerdict.PASS
            elif score >= self.pass_threshold:
                verdict = CritiqueVerdict.PASS
            else:
                verdict = CritiqueVerdict.FAIL

            # Get feedback, issues, suggestions with safe defaults
            feedback = str(data.get("feedback", "No feedback provided"))
            issues = data.get("issues", [])
            if not isinstance(issues, list):
                issues = [str(issues)] if issues else []
            suggestions = data.get("suggestions", [])
            if not isinstance(suggestions, list):
                suggestions = [str(suggestions)] if suggestions else []

            return CritiqueResult(
                verdict=verdict,
                score=score,
                feedback=feedback,
                issues=issues,
                suggestions=suggestions,
                iteration=iteration,
            )

        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse critique response: {e}")
            logger.debug(f"Raw response: {response[:1000]}")
            # Return a default result that uses the raw response as feedback
            return CritiqueResult(
                verdict=CritiqueVerdict.FAIL,
                score=5.0,
                feedback=f"Model provided feedback but in wrong format. Raw response: {response[:800]}",
                issues=["Critique parsing failed"],
                suggestions=["Continue iterating based on the raw feedback above"],
                iteration=iteration,
            )

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract a complete JSON object from text using brace matching.

        Args:
            text: Text that may contain a JSON object

        Returns:
            Extracted JSON string or None
        """
        # Find the first opening brace
        start = text.find('{')
        if start == -1:
            return None

        # Count braces to find matching close
        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None
