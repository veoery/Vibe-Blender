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
    ReferenceAnalysis,
)

logger = logging.getLogger(__name__)

# Load prompt templates
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner.txt"
CLARIFICATION_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_clarification.txt"
REFERENCE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_reference.txt"


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
        self._load_reference_prompt_template()

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

    def _load_reference_prompt_template(self) -> None:
        """Load the reference image analysis prompt template."""
        if REFERENCE_PROMPT_PATH.exists():
            self.reference_prompt = REFERENCE_PROMPT_PATH.read_text()
        else:
            logger.warning(f"Reference prompt template not found at {REFERENCE_PROMPT_PATH}, using default")
            self.reference_prompt = self._default_reference_prompt()

    def _default_reference_prompt(self) -> str:
        """Return default reference analysis prompt if template not found."""
        return """Analyze the reference images and extract:
- Visual style (realistic, low-poly, cartoon, abstract, etc.)
- Materials and textures visible
- Dominant colors (hex codes or color names)
- Key shapes and forms
- Notable details or features
Output JSON with: style_notes, materials, colors, shapes, details"""

    def check_clarity(self, user_prompt: str) -> ClarificationRequest:
        """Check if the user prompt needs clarification.

        Args:
            user_prompt: The user's text description

        Returns:
            ClarificationRequest indicating if clarification is needed
        """
        logger.info(f"Checking clarity for prompt: {user_prompt[:100]}...")

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

    def analyze_references(
        self,
        reference_images: list[Path],
        user_prompt: str,
    ) -> ReferenceAnalysis:
        """Analyze reference images to extract style guidance.

        Args:
            reference_images: Paths to reference images
            user_prompt: User's text prompt for context

        Returns:
            ReferenceAnalysis with extracted style information
        """
        logger.info(f"Analyzing {len(reference_images)} reference images...")

        prompt = f"""User wants to create: "{user_prompt}"

Analyze the provided reference images and extract key visual information:
1. Overall visual style
2. Materials and textures
3. Color palette (hex codes or names)
4. Shapes and geometric forms
5. Notable details

Output JSON matching this schema:
{{
  "style_notes": "description of overall style",
  "materials": ["material1", "material2", ...],
  "colors": ["#RRGGBB or color name", ...],
  "shapes": ["shape1", "shape2", ...],
  "details": "additional notable details"
}}"""

        response = self.llm.analyze_images(
            image_paths=reference_images,
            prompt=prompt,
            system=self.reference_prompt,
        )

        return self._parse_reference_response(response)

    def _parse_reference_response(self, response: str) -> ReferenceAnalysis:
        """Parse LLM response into ReferenceAnalysis.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed ReferenceAnalysis
        """
        try:
            # Extract JSON (same pattern as _parse_clarification_response)
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)
            return ReferenceAnalysis(**data)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse reference analysis: {e}")
            logger.debug(f"Raw response: {response}")
            # Graceful fallback
            return ReferenceAnalysis(
                style_notes="Unable to parse reference analysis",
                materials=[],
                colors=[],
                shapes=[],
                details=response[:200],  # Include snippet
            )

    def plan(self, user_prompt: str) -> SceneDescription:
        """Parse a user prompt into a structured scene description.

        Args:
            user_prompt: The user's text description of the desired 3D model

        Returns:
            SceneDescription with parsed details

        Raises:
            ValueError: If the LLM response cannot be parsed
        """
        logger.info(f"Planning scene for prompt: {user_prompt[:100]}...")

        response = self.llm.generate(
            prompt=f"User prompt: {user_prompt}",
            system=self.system_prompt,
            temperature=1.0,  # Lower temperature for more consistent parsing
        )

        return self._parse_response(response)

    def plan_with_references(
        self,
        user_prompt: str,
        clarifications: Optional[ClarificationResponse] = None,
        reference_analysis: Optional[ReferenceAnalysis] = None,
    ) -> SceneDescription:
        """Plan scene with optional clarifications and reference analysis.

        This is the main entry point for planning. It integrates clarifications
        and reference analysis into the prompt before planning.

        Args:
            user_prompt: User's text prompt
            clarifications: Optional clarification responses
            reference_analysis: Optional reference image analysis

        Returns:
            SceneDescription with all context integrated

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
            prompt_parts.append(f"\nAdditional details from user:\n{clarification_text}")
            logger.info(f"Planning with clarifications: {list(clarifications.answers.keys())}")

        # Add reference analysis
        if reference_analysis:
            ref_text = f"""
Reference Image Analysis:
- Style: {reference_analysis.style_notes}
- Materials: {', '.join(reference_analysis.materials) if reference_analysis.materials else 'None specified'}
- Colors: {', '.join(reference_analysis.colors) if reference_analysis.colors else 'None specified'}
- Shapes: {', '.join(reference_analysis.shapes) if reference_analysis.shapes else 'None specified'}
- Details: {reference_analysis.details}

IMPORTANT: Use the reference analysis to guide material choices, color palette, and overall style.
"""
            prompt_parts.append(ref_text)
            logger.info("Planning with reference analysis")

        enriched_prompt = "\n".join(prompt_parts)

        logger.info(f"Planning scene for prompt: {user_prompt[:100]}...")

        response = self.llm.generate(
            prompt=enriched_prompt,
            system=self.system_prompt,
            temperature=1.0,
        )

        scene_desc = self._parse_response(response)
        scene_desc.reference_analysis = reference_analysis
        return scene_desc

    def plan_with_clarifications(
        self,
        user_prompt: str,
        clarifications: Optional[ClarificationResponse] = None,
    ) -> SceneDescription:
        """Parse a user prompt into a structured scene description with optional clarifications.

        This method is maintained for backward compatibility. It calls plan_with_references()
        with reference_analysis=None.

        Args:
            user_prompt: The user's text description of the desired 3D model
            clarifications: Optional clarification responses from the user

        Returns:
            SceneDescription with parsed details

        Raises:
            ValueError: If the LLM response cannot be parsed
        """
        return self.plan_with_references(user_prompt, clarifications, reference_analysis=None)

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
