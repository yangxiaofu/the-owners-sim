"""
Offensive Line Grader

Grades OL on pass blocking, run blocking, and penalty avoidance.
Leverages existing run_blocking_grade and pass_blocking_efficiency from PlayerStats.

Position-specific weights:
- Tackles (LT/RT): Focus on pass protection (blind side protection)
- Guards (LG/RG): Focus on run blocking (pulling, combo blocks)
- Center (C): Balanced (includes snapping responsibilities)
"""

from typing import Dict, Any, Optional

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    OL_COMPONENT_WEIGHTS,
    OL_ADJUSTMENTS,
)

# Position-specific component weights for OL grading
OL_POSITION_WEIGHTS: Dict[str, Dict[str, float]] = {
    # Tackles: 55% pass blocking, 35% run blocking, 10% penalties
    'LT': {'pass_blocking': 0.55, 'run_blocking': 0.35, 'penalties': 0.10},
    'RT': {'pass_blocking': 0.55, 'run_blocking': 0.35, 'penalties': 0.10},
    'left_tackle': {'pass_blocking': 0.55, 'run_blocking': 0.35, 'penalties': 0.10},
    'right_tackle': {'pass_blocking': 0.55, 'run_blocking': 0.35, 'penalties': 0.10},

    # Guards: 35% pass blocking, 55% run blocking, 10% penalties
    'LG': {'pass_blocking': 0.35, 'run_blocking': 0.55, 'penalties': 0.10},
    'RG': {'pass_blocking': 0.35, 'run_blocking': 0.55, 'penalties': 0.10},
    'left_guard': {'pass_blocking': 0.35, 'run_blocking': 0.55, 'penalties': 0.10},
    'right_guard': {'pass_blocking': 0.35, 'run_blocking': 0.55, 'penalties': 0.10},

    # Center: 45% pass blocking, 45% run blocking, 10% penalties (balanced)
    'C': {'pass_blocking': 0.45, 'run_blocking': 0.45, 'penalties': 0.10},
    'center': {'pass_blocking': 0.45, 'run_blocking': 0.45, 'penalties': 0.10},
}


class OLGrader(BasePositionGrader):
    """Grades offensive linemen on blocking and penalties with position-specific weights."""

    def __init__(self, position: Optional[str] = None):
        """
        Initialize OL grader with optional position for position-specific weighting.

        Args:
            position: Player's position (LT, LG, C, RG, RT or full names)
        """
        self.position = position

    def get_component_weights(self) -> Dict[str, float]:
        """Get position-specific component weights for OL grading."""
        if self.position and self.position in OL_POSITION_WEIGHTS:
            return OL_POSITION_WEIGHTS[self.position]
        return OL_COMPONENT_WEIGHTS  # Default weights if position not specified

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "pass_blocking": self._grade_pass_blocking(stats),
            "run_blocking": self._grade_run_blocking(stats),
            "penalties": self._grade_penalties(stats),
        }

    def _grade_pass_blocking(self, stats: Any) -> float:
        """Grade pass blocking using existing efficiency metric if available."""
        # Use existing pass_blocking_efficiency (0-100) if available
        existing_grade = self._get_stat(stats, "pass_blocking_efficiency", 0)
        if existing_grade > 0:
            return existing_grade

        # Fallback calculation
        base = BASELINE_GRADE

        sacks_allowed = self._get_stat(stats, "sacks_allowed", 0)
        pressures_allowed = self._get_stat(stats, "pressures_allowed", 0)
        hurries_allowed = self._get_stat(stats, "hurries_allowed", 0)
        pass_blocks = self._get_stat(stats, "pass_blocks", 0)

        if pass_blocks == 0:
            return BASELINE_GRADE  # Not a pass play or not blocking

        # Clean pocket is good
        if sacks_allowed == 0 and pressures_allowed == 0 and hurries_allowed == 0:
            base += OL_ADJUSTMENTS.get("clean_pocket", 8)

        # Negative outcomes
        if sacks_allowed > 0:
            base += OL_ADJUSTMENTS.get("sack_allowed", -25)
        if pressures_allowed > 0:
            base += OL_ADJUSTMENTS.get("pressure_allowed", -10)
        if hurries_allowed > 0:
            base += OL_ADJUSTMENTS.get("hurry_allowed", -5)

        return self._clamp(base)

    def _grade_run_blocking(self, stats: Any) -> float:
        """Grade run blocking using existing grade if available."""
        # Use existing run_blocking_grade (0-100) if available
        existing_grade = self._get_stat(stats, "run_blocking_grade", 0)
        if existing_grade > 0:
            return existing_grade

        # Fallback calculation
        base = BASELINE_GRADE

        pancakes = self._get_stat(stats, "pancakes", 0)
        downfield_blocks = self._get_stat(stats, "downfield_blocks", 0)
        double_team_blocks = self._get_stat(stats, "double_team_blocks", 0)
        blocks_made = self._get_stat(stats, "blocks_made", 0)
        blocks_missed = self._get_stat(stats, "blocks_missed", 0)

        # Positive plays
        if pancakes > 0:
            base += OL_ADJUSTMENTS.get("pancake", 15)
        if downfield_blocks > 0:
            base += OL_ADJUSTMENTS.get("downfield_block", 10)
        if double_team_blocks > 0:
            base += OL_ADJUSTMENTS.get("double_team_success", 8)

        # Good blocking sustaining
        if blocks_made > 0:
            base += 5

        # Missed blocks
        if blocks_missed > 0:
            base -= 10

        return self._clamp(base)

    def _grade_penalties(self, stats: Any) -> float:
        """Grade penalty avoidance (negative impact for penalties)."""
        base = 70.0  # Slightly above neutral (no penalty is good)

        holding_penalties = self._get_stat(stats, "holding_penalties", 0)
        false_start_penalties = self._get_stat(stats, "false_start_penalties", 0)
        missed_assignments = self._get_stat(stats, "missed_assignments", 0)

        if holding_penalties > 0:
            base += OL_ADJUSTMENTS.get("holding_penalty", -20)

        if false_start_penalties > 0:
            base += OL_ADJUSTMENTS.get("false_start", -15)

        if missed_assignments > 0:
            base -= 10

        return self._clamp(base)
