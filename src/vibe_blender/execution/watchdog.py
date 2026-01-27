"""Watchdog for pipeline iteration control."""

import logging
from datetime import datetime
from typing import Optional

from ..models.schemas import (
    PipelineState,
    PipelineStatus,
    IterationRecord,
    CritiqueVerdict,
)

logger = logging.getLogger(__name__)


class Watchdog:
    """Monitors and controls pipeline iterations.

    Enforces maximum retry limits and tracks iteration history
    to prevent infinite loops.
    """

    def __init__(self, max_retries: int = 5):
        """Initialize the watchdog.

        Args:
            max_retries: Maximum allowed iterations
        """
        self.max_retries = max_retries

    def can_continue(self, state: PipelineState) -> bool:
        """Check if the pipeline can continue iterating.

        Args:
            state: Current pipeline state

        Returns:
            True if more iterations are allowed
        """
        if state.status != PipelineStatus.RUNNING:
            logger.info(f"Pipeline not running (status: {state.status})")
            return False

        if state.current_iteration >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) reached")
            return False

        return True

    def check_completion(self, state: PipelineState) -> bool:
        """Check if the pipeline has successfully completed.

        Args:
            state: Current pipeline state

        Returns:
            True if the latest iteration passed
        """
        if not state.iterations:
            return False

        latest = state.iterations[-1]
        if latest.critique and latest.critique.verdict == CritiqueVerdict.PASS:
            return True

        return False

    def get_iteration_summary(self, state: PipelineState) -> str:
        """Get a summary of all iterations for context.

        Args:
            state: Current pipeline state

        Returns:
            Human-readable summary
        """
        if not state.iterations:
            return "No iterations completed yet."

        lines = [f"Iteration History ({len(state.iterations)} total):"]

        for record in state.iterations:
            status = "?"
            if record.error:
                status = "ERROR"
            elif record.critique:
                status = record.critique.verdict.value.upper()
                if record.critique.score:
                    status += f" ({record.critique.score:.1f}/10)"

            lines.append(f"  [{record.iteration}] {status}")

            if record.critique and record.critique.verdict == CritiqueVerdict.FAIL:
                # Add brief feedback
                feedback = record.critique.feedback[:100]
                if len(record.critique.feedback) > 100:
                    feedback += "..."
                lines.append(f"      → {feedback}")

        return "\n".join(lines)

    def should_stop_early(self, state: PipelineState) -> tuple[bool, Optional[str]]:
        """Check if the pipeline should stop early due to repeated failures.

        Args:
            state: Current pipeline state

        Returns:
            Tuple of (should_stop, reason)
        """
        if len(state.iterations) < 3:
            return False, None

        # Check for repeated identical errors
        recent_errors = [
            r.error for r in state.iterations[-3:]
            if r.error
        ]
        if len(recent_errors) == 3 and len(set(recent_errors)) == 1:
            return True, f"Same error repeated 3 times: {recent_errors[0][:100]}"

        # Check for declining scores
        recent_scores = [
            r.critique.score for r in state.iterations[-3:]
            if r.critique and r.critique.score is not None
        ]
        if len(recent_scores) == 3:
            if recent_scores[-1] < recent_scores[-2] < recent_scores[-3]:
                if recent_scores[-1] < 3:
                    return True, "Scores declining and below threshold"

        return False, None

    def update_state_for_max_retries(self, state: PipelineState) -> None:
        """Update state when max retries is reached.

        Args:
            state: Pipeline state to update
        """
        state.status = PipelineStatus.MAX_RETRIES
        state.completed_at = datetime.now()

        # Find best iteration based on score
        best_score = -1
        best_record = None

        for record in state.iterations:
            if record.critique and record.critique.score:
                if record.critique.score > best_score:
                    best_score = record.critique.score
                    best_record = record

        if best_record and best_record.render_output:
            state.final_output = best_record.render_output
            logger.info(f"Using best iteration {best_record.iteration} (score: {best_score})")

    def update_state_for_success(self, state: PipelineState) -> None:
        """Update state for successful completion.

        Args:
            state: Pipeline state to update
        """
        state.status = PipelineStatus.SUCCESS
        state.completed_at = datetime.now()

        # Use the latest successful iteration's output
        if state.iterations:
            latest = state.iterations[-1]
            if latest.render_output:
                state.final_output = latest.render_output

    def update_state_for_failure(self, state: PipelineState, reason: str) -> None:
        """Update state for pipeline failure.

        Args:
            state: Pipeline state to update
            reason: Failure reason
        """
        state.status = PipelineStatus.FAILED
        state.completed_at = datetime.now()
        logger.error(f"Pipeline failed: {reason}")
