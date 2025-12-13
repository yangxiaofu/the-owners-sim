"""
Base Position Grader

Abstract base class that provides common functionality for all position graders.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from analytics.models import PlayContext
from analytics.grading_constants import BASELINE_GRADE, clamp_grade


class BasePositionGrader(ABC):
    """Base class for position-specific graders.

    Each position grader implements:
    - grade_play(): Returns component grades for a play
    - get_component_weights(): Returns weights for each component
    """

    @abstractmethod
    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        """Calculate position-specific component grades.

        Args:
            context: Play context (down, distance, yard_line, etc.)
            stats: Player stats for this play (PlayerStats object)

        Returns:
            Dictionary mapping component names to grades (0-100)
        """
        pass

    @abstractmethod
    def get_component_weights(self) -> Dict[str, float]:
        """Get weights for each component.

        Returns:
            Dictionary mapping component names to weights (should sum to ~1.0)
        """
        pass

    def _get_stat(self, stats: Any, attr: str, default: Any = 0) -> Any:
        """Safely get an attribute from stats object."""
        return getattr(stats, attr, default) if stats else default

    def _clamp(self, value: float) -> float:
        """Clamp grade to valid range (0-100)."""
        return clamp_grade(value)

    def _bonus(self, base: float, amount: float, max_bonus: float = 35.0) -> float:
        """Apply a capped bonus to base grade."""
        return base + min(amount, max_bonus)

    def _penalty(self, base: float, amount: float, max_penalty: float = 35.0) -> float:
        """Apply a capped penalty to base grade."""
        return base - min(amount, max_penalty)
