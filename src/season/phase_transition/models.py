"""
Phase Transition Models

Data classes representing phase transitions and related errors.
"""

from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum

# Use src. prefix to avoid collision with Python builtin calendar
try:
    from src.calendar.season_phase_tracker import SeasonPhase
except ModuleNotFoundError:
    # Fallback for test environment
    from src.calendar.season_phase_tracker import SeasonPhase


class TransitionHandlerKey(Enum):
    """
    Type-safe keys for phase transition handlers.

    Eliminates magic strings and provides autocomplete support for handler registration.
    Each enum value represents a valid phase transition in the NFL season cycle.

    Format: {FROM_PHASE}_TO_{TO_PHASE}

    Example:
        # Type-safe handler registration
        handlers = {
            TransitionHandlerKey.OFFSEASON_TO_PRESEASON: offseason_handler.execute,
            TransitionHandlerKey.REGULAR_SEASON_TO_PLAYOFFS: playoff_handler.execute,
        }
    """
    PRESEASON_TO_REGULAR_SEASON = "preseason_to_regular_season"
    REGULAR_SEASON_TO_PLAYOFFS = "regular_season_to_playoffs"
    PLAYOFFS_TO_OFFSEASON = "playoffs_to_offseason"
    OFFSEASON_TO_PRESEASON = "offseason_to_preseason"

    @classmethod
    def from_phases(cls, from_phase: SeasonPhase, to_phase: SeasonPhase) -> 'TransitionHandlerKey':
        """
        Get handler key from SeasonPhase enum values.

        Dynamically constructs the handler key string from phase enums and maps
        it to the corresponding TransitionHandlerKey enum value.

        Args:
            from_phase: Phase transitioning from (SeasonPhase enum)
            to_phase: Phase transitioning to (SeasonPhase enum)

        Returns:
            TransitionHandlerKey enum for the given phase transition

        Raises:
            ValueError: If transition is not supported (no matching enum value)

        Example:
            >>> key = TransitionHandlerKey.from_phases(
            ...     SeasonPhase.OFFSEASON,
            ...     SeasonPhase.PRESEASON
            ... )
            >>> print(key)
            TransitionHandlerKey.OFFSEASON_TO_PRESEASON
        """
        # Build expected key string from phase enum values
        key_str = f"{from_phase.value}_to_{to_phase.value}"

        # Search for matching enum value
        for handler_key in cls:
            if handler_key.value == key_str:
                return handler_key

        # No matching transition found
        raise ValueError(
            f"Unsupported phase transition: {from_phase.value} → {to_phase.value}. "
            f"Valid transitions: {[k.value for k in cls]}"
        )


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
