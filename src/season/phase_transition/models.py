"""
Phase Transition Models

Data classes representing phase transitions and related errors.
"""

from dataclasses import dataclass
from typing import Dict, Any

# Use src. prefix to avoid collision with Python builtin calendar
try:
    from calendar.season_phase_tracker import SeasonPhase
except ModuleNotFoundError:
    # Fallback for test environment
    from src.calendar.season_phase_tracker import SeasonPhase


@dataclass
class PhaseTransition:
    """
    Represents a phase transition event.

    Attributes:
        from_phase: Phase transitioning from
        to_phase: Phase transitioning to
        trigger: What triggered the transition
        metadata: Additional transition metadata
    """

    from_phase: SeasonPhase
    to_phase: SeasonPhase
    trigger: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of transition
        """
        return {
            'from_phase': self.from_phase.value,
            'to_phase': self.to_phase.value,
            'trigger': self.trigger,
            'metadata': self.metadata
        }

    def __str__(self) -> str:
        """String representation."""
        return f"{self.from_phase.value} → {self.to_phase.value} (trigger: {self.trigger})"


class TransitionFailedError(Exception):
    """
    Exception raised when a phase transition fails.

    This exception indicates that a transition could not be completed
    and any partial changes should be rolled back.
    """

    def __init__(self, message: str, original_exception: Exception = None):
        """
        Initialize exception.

        Args:
            message: Error message
            original_exception: The exception that caused the failure
        """
        super().__init__(message)
        self.original_exception = original_exception
