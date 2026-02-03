"""Pydantic data models for the Vibe-Blender pipeline."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    """A single clarification question."""

    key: str = Field(..., description="Unique key for this question (e.g., 'table_type', 'style')")
    question: str = Field(..., description="The question to ask the user")
    suggestions: Optional[list[str]] = Field(None, description="Suggested answers")
    required: bool = Field(True, description="Whether this question must be answered")


class ClarificationRequest(BaseModel):
    """Request for clarification from Planner."""

    needs_clarification: bool = Field(..., description="Whether clarification is needed")
    reason: Optional[str] = Field(None, description="Why clarification is needed")
    questions: list[ClarificationQuestion] = Field(default_factory=list, description="Questions to ask")
    timestamp: datetime = Field(default_factory=datetime.now)


class ClarificationResponse(BaseModel):
    """User's answers to clarification questions."""

    answers: dict[str, str] = Field(..., description="Map of question key to user's answer")
    timestamp: datetime = Field(default_factory=datetime.now)


class UserPrompt(BaseModel):
    """Original user input for 3D generation."""

    text: str = Field(..., description="The user's text prompt describing the 3D object")
    clarifications: Optional[ClarificationResponse] = Field(None, description="User's clarification responses")
    reference_images: Optional[list[Path]] = Field(
        None,
        description="Optional reference image paths for style/aesthetic guidance",
        max_length=5
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    def get_enriched_prompt(self) -> str:
        """Merge original text with clarifications.

        Returns:
            Prompt text with clarifications appended if available
        """
        if not self.clarifications or not self.clarifications.answers:
            return self.text

        clarification_text = "\n".join(
            f"- {key}: {value}"
            for key, value in self.clarifications.answers.items()
        )
        return f"{self.text}\n\nAdditional details:\n{clarification_text}"

    def has_references(self) -> bool:
        """Check if reference images are provided.

        Returns:
            True if reference images exist and list is not empty
        """
        return bool(self.reference_images and len(self.reference_images) > 0)

    def validate_references(self) -> list[str]:
        """Validate reference images and return list of errors.

        Returns:
            List of error messages (empty if all valid)
        """
        if not self.reference_images:
            return []

        errors = []
        valid_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

        for ref_path in self.reference_images:
            if not ref_path.exists():
                errors.append(f"Reference image not found: {ref_path}")
            elif ref_path.suffix.lower() not in valid_formats:
                errors.append(f"Unsupported format {ref_path.suffix}: {ref_path.name}")

        return errors


class ObjectDescription(BaseModel):
    """Description of a single object in the scene."""

    name: str = Field(..., description="Name/type of the object")
    shape: Optional[str] = Field(None, description="Basic shape (cube, sphere, cylinder, etc.)")
    dimensions: Optional[dict[str, float]] = Field(None, description="Approximate dimensions")
    position: Optional[tuple[float, float, float]] = Field(None, description="Position in scene")
    details: Optional[str] = Field(None, description="Additional details about the object")


class MaterialDescription(BaseModel):
    """Description of a material/texture."""

    name: str = Field(..., description="Name of the material")
    base_color: Optional[str] = Field(None, description="Base color (hex or name)")
    metallic: Optional[float] = Field(None, ge=0, le=1, description="Metallic factor")
    roughness: Optional[float] = Field(None, ge=0, le=1, description="Roughness factor")
    emission: Optional[str] = Field(None, description="Emission color if any")


class SceneDescription(BaseModel):
    """Structured scene description from the Planner agent."""

    summary: str = Field(..., description="Brief summary of the scene")
    style: Optional[str] = Field(None, description="Visual style (realistic, low-poly, cartoon)")
    objects: list[ObjectDescription] = Field(default_factory=list)
    materials: list[MaterialDescription] = Field(default_factory=list)
    lighting: Optional[str] = Field(None, description="Lighting setup description")
    camera_notes: Optional[str] = Field(None, description="Special camera considerations")
    complexity: str = Field("medium", description="Estimated complexity: simple, medium, complex")


class GeneratedScript(BaseModel):
    """Blender Python script generated by the Generator agent."""

    code: str = Field(..., description="The Python script code")
    iteration: int = Field(..., ge=1, description="Which iteration this script is from")
    based_on_feedback: Optional[str] = Field(None, description="Feedback this iteration addresses")
    edit_based: bool = Field(False, description="True if produced by applying edits, False if fully regenerated")
    edits_applied: Optional[int] = Field(None, description="Number of edits applied (None if not edit-based)")
    timestamp: datetime = Field(default_factory=datetime.now)


class RenderOutput(BaseModel):
    """Paths to rendered output files."""

    script_path: Path = Field(..., description="Path to the executed script")
    blend_file: Optional[Path] = Field(None, description="Path to saved .blend file")
    grid_image: Optional[Path] = Field(None, description="Path to 4-view grid image")
    turntable_gif: Optional[Path] = Field(None, description="Path to turntable animation GIF")
    render_dir: Path = Field(..., description="Directory containing all renders")
    blender_error: Optional[str] = Field(None, description="Blender stderr if script had errors")


class CritiqueVerdict(str, Enum):
    """Verdict from the Critic agent."""

    PASS = "pass"
    FAIL = "fail"


class CritiqueResult(BaseModel):
    """Result from the Critic agent's analysis."""

    verdict: CritiqueVerdict = Field(..., description="Pass or fail verdict")
    score: Optional[float] = Field(None, ge=0, le=10, description="Quality score 0-10")
    feedback: str = Field(..., description="Detailed feedback for improvement")
    issues: list[str] = Field(default_factory=list, description="Specific issues identified")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for next iteration")
    iteration: int = Field(..., ge=1, description="Which iteration was critiqued")


class PipelineStatus(str, Enum):
    """Status of the pipeline execution."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_RETRIES = "max_retries"


class IterationRecord(BaseModel):
    """Record of a single iteration in the pipeline."""

    iteration: int
    script: Optional[GeneratedScript] = None
    render_output: Optional[RenderOutput] = None
    critique: Optional[CritiqueResult] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PipelineState(BaseModel):
    """Current state of the pipeline execution."""

    user_prompt: UserPrompt
    scene_description: Optional[SceneDescription] = None
    current_iteration: int = Field(default=0)
    max_retries: int = Field(default=5)
    status: PipelineStatus = Field(default=PipelineStatus.RUNNING)
    iterations: list[IterationRecord] = Field(default_factory=list)
    final_output: Optional[RenderOutput] = None
    output_dir: Path
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_iteration(self, record: IterationRecord) -> None:
        """Add an iteration record to the history."""
        self.iterations.append(record)
        self.current_iteration = record.iteration

    def get_latest_critique(self) -> Optional[CritiqueResult]:
        """Get the most recent critique result."""
        for record in reversed(self.iterations):
            if record.critique:
                return record.critique
        return None

    def get_feedback_history(self) -> list[str]:
        """Get all feedback from previous iterations."""
        return [
            record.critique.feedback
            for record in self.iterations
            if record.critique and record.critique.verdict == CritiqueVerdict.FAIL
        ]
