"""Planner agent for parsing user prompts into scene descriptions."""

import json
import logging
from pathlib import Path
from typing import Optional

from ..llm.base import BaseLLM
from ..models.schemas import (
    SceneDescription,
    ObjectDescription,
    MaterialDescription,
    ClarificationRequest,
    ClarificationQuestion,
    ClarificationResponse,
)

logger = logging.getLogger(__name__)

# Load prompt templates
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner.txt"
CLARIFICATION_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_clarification.txt"


class PlannerAgent:
    """Agent that parses user prompts into structured scene descriptions.

    The Planner analyzes the user's text prompt and extracts:
    - Objects to create
    - Materials and colors
    - Style preferences
    - Lighting requirements
    """

    def __init__(self, llm: BaseLLM):
        """Initialize the Planner agent.

        Args:
            llm: LLM backend for text generation
        """
        self.llm = llm
        self._load_prompt_template()
        self._load_clarification_prompt_template()

    def _load_prompt_template(self) -> None:
        """Load the system prompt template."""
        if PROMPT_PATH.exists():
            self.system_prompt = PROMPT_PATH.read_text()
        else:
            logger.warning(f"Prompt template not found at {PROMPT_PATH}, using default")
            self.system_prompt = self._default_prompt()

    def _default_prompt(self) -> str:
        """Return default system prompt if template not found."""
        return """You are a 3D scene planner. Analyze the user's prompt and create a scene description.
Output a JSON object with: summary, style, objects, materials, lighting, camera_notes, complexity."""

    def _load_clarification_prompt_template(self) -> None:
        """Load the clarification detection prompt template."""
        if CLARIFICATION_PROMPT_PATH.exists():
            self.clarification_prompt = CLARIFICATION_PROMPT_PATH.read_text()
        else:
            logger.warning(f"Clarification prompt template not found at {CLARIFICATION_PROMPT_PATH}, using default")
            self.clarification_prompt = self._default_clarification_prompt()

    def _default_clarification_prompt(self) -> str:
        """Return default clarification prompt if template not found."""
        return """You are a 3D scene planner. Analyze if the user's prompt needs clarification.
Output a JSON object with: needs_clarification (bool), reason (string or null), questions (array)."""

    def check_clarity(
        self,
        user_prompt: str,
        reference_images: Optional[list[Path]] = None,
    ) -> ClarificationRequest:
        """Check if the user prompt needs clarification, considering reference images.

        Args:
            user_prompt: The user's text description
            reference_images: Optional reference images to analyze alongside the prompt

        Returns:
            ClarificationRequest indicating if clarification is needed
        """
        logger.info(f"Checking clarity for prompt: {user_prompt[:100]}...")

        if reference_images:
            logger.info(f"Analyzing clarity with {len(reference_images)} reference images")
            # Use vision API to analyze both text and images together
            response = self.llm.analyze_images(
                image_paths=reference_images,
                prompt=f"User prompt: {user_prompt}",
                system=self.clarification_prompt,
            )
        else:
            # Text-only analysis
            response = self.llm.generate(
                prompt=f"User prompt: {user_prompt}",
                system=self.clarification_prompt,
                temperature=1.0,
            )

        return self._parse_clarification_response(response)

    def _parse_clarification_response(self, response: str) -> ClarificationRequest:
        """Parse the LLM response into a ClarificationRequest.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed ClarificationRequest
        """
        try:
            # Handle responses that might have markdown code blocks
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to find JSON object in response
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)

            # Convert questions to ClarificationQuestion objects
            questions = []
            for q_data in data.get("questions", []):
                questions.append(ClarificationQuestion(
                    key=q_data.get("key", ""),
                    question=q_data.get("question", ""),
                    suggestions=q_data.get("suggestions"),
                    required=q_data.get("required", True),
                ))

            return ClarificationRequest(
                needs_clarification=data.get("needs_clarification", False),
                reason=data.get("reason"),
                questions=questions,
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse clarification response: {e}")
            logger.debug(f"Raw response: {response}")
            # Gracefully fallback - assume no clarification needed
            return ClarificationRequest(
                needs_clarification=False,
                reason="Failed to parse clarification request",
                questions=[],
            )

    def plan(
        self,
        user_prompt: str,
        clarifications: Optional[ClarificationResponse] = None,
        reference_images: Optional[list[Path]] = None,
    ) -> SceneDescription:
        """Plan scene with optional clarifications and reference images.

        Args:
            user_prompt: User's text prompt
            clarifications: Optional clarification responses
            reference_images: Optional reference images (LLM will see them directly)

        Returns:
            SceneDescription

        Raises:
            ValueError: If the LLM response cannot be parsed
        """
        # Build enriched prompt
        prompt_parts = [f"User prompt: {user_prompt}"]

        # Add clarifications
        if clarifications and clarifications.answers:
            clarification_text = "\n".join(
                f"- {key}: {value}"
                for key, value in clarifications.answers.items()
            )
            prompt_parts.append(f"\nAdditional details:\n{clarification_text}")

        enriched_prompt = "\n".join(prompt_parts)

        # Use vision API if images provided, otherwise text-only
        if reference_images:
            logger.info(f"Planning with {len(reference_images)} reference images")
            response = self.llm.analyze_images(
                image_paths=reference_images,
                prompt=enriched_prompt,
                system=self.system_prompt,
            )
        else:
            logger.info("Planning without reference images")
            response = self.llm.generate(
                prompt=enriched_prompt,
                system=self.system_prompt,
                temperature=1.0,
            )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> SceneDescription:
        """Parse the LLM response into a SceneDescription.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed SceneDescription

        Raises:
            ValueError: If parsing fails
        """
        # Try to extract JSON from the response
        try:
            # Handle responses that might have markdown code blocks
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to find JSON object in response
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            raise ValueError(f"Failed to parse scene description from LLM response: {e}")

        # Convert to SceneDescription
        return self._dict_to_scene_description(data)

    def _dict_to_scene_description(self, data: dict) -> SceneDescription:
        """Convert a dictionary to a SceneDescription model.

        Args:
            data: Dictionary from parsed JSON

        Returns:
            SceneDescription instance
        """
        objects = []
        for obj_data in data.get("objects", []):
            objects.append(ObjectDescription(
                name=obj_data.get("name", "Object"),
                shape=obj_data.get("shape"),
                dimensions=obj_data.get("dimensions"),
                position=tuple(obj_data.get("position", [0, 0, 0])) if obj_data.get("position") else None,
                details=obj_data.get("details"),
            ))

        materials = []
        for mat_data in data.get("materials", []):
            materials.append(MaterialDescription(
                name=mat_data.get("name", "Material"),
                base_color=mat_data.get("base_color"),
                metallic=mat_data.get("metallic"),
                roughness=mat_data.get("roughness"),
                emission=mat_data.get("emission"),
            ))

        return SceneDescription(
            summary=data.get("summary", ""),
            style=data.get("style"),
            objects=objects,
            materials=materials,
            lighting=data.get("lighting"),
            camera_notes=data.get("camera_notes"),
            complexity=data.get("complexity", "medium"),
        )
