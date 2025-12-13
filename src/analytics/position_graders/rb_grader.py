"""
Running Back Grader

Grades RBs on vision, elusiveness, power, pass blocking, and receiving.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    RB_COMPONENT_WEIGHTS,
    RB_ADJUSTMENTS,
)


class RBGrader(BasePositionGrader):
    """Grades running backs on vision, elusiveness, power, blocking, receiving."""

    def get_component_weights(self) -> Dict[str, float]:
        return RB_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "vision": self._grade_vision(context, stats),
            "elusiveness": self._grade_elusiveness(stats),
            "power": self._grade_power(stats),
            "pass_blocking": self._grade_pass_blocking(stats),
            "receiving": self._grade_receiving(stats),
        }

    def _grade_vision(self, context: PlayContext, stats: Any) -> float:
        """Grade vision - finding holes and reading blocks."""
        base = BASELINE_GRADE

        rushing_yards = self._get_stat(stats, "rushing_yards", 0)
        rushing_attempts = self._get_stat(stats, "rushing_attempts", 0)
        rushing_tds = self._get_stat(stats, "rushing_tds", 0)

        if rushing_attempts == 0:
            return BASELINE_GRADE  # Not a rushing play for this RB

        # Grade based on yardage
        if rushing_yards >= 10:
            base += RB_ADJUSTMENTS.get("explosive_play", 25)
        elif rushing_yards >= 4:
            base += RB_ADJUSTMENTS.get("chunk_play", 18)
        elif rushing_yards > 0:
            base += RB_ADJUSTMENTS.get("positive_yards", 10)
        elif rushing_yards < 0:
            base += RB_ADJUSTMENTS.get("negative_yards", -12)

        # TD bonus
        if rushing_tds > 0:
            base += RB_ADJUSTMENTS.get("touchdown_rush", 10)

        return self._clamp(base)

    def _grade_elusiveness(self, stats: Any) -> float:
        """Grade elusiveness - breaking tackles and making defenders miss."""
        base = BASELINE_GRADE

        rushing_yards = self._get_stat(stats, "rushing_yards", 0)
        rushing_attempts = self._get_stat(stats, "rushing_attempts", 0)
        yards_after_contact = self._get_stat(stats, "yards_after_contact", 0)
        broken_tackles = self._get_stat(stats, "broken_tackles", 0)

        if rushing_attempts == 0:
            return BASELINE_GRADE

        # Yards after contact shows elusiveness
        if yards_after_contact and yards_after_contact > 2:
            base += RB_ADJUSTMENTS.get("yards_after_contact_bonus", 5) * (yards_after_contact // 2)

        # Broken tackles show elusiveness (capped at 3 per play for grade sanity)
        if broken_tackles > 0:
            base += RB_ADJUSTMENTS.get("broken_tackle", 8) * min(broken_tackles, 3)

        # Long runs indicate elusiveness
        if rushing_yards >= 15:
            base += 12

        return self._clamp(base)

    def _grade_power(self, stats: Any) -> float:
        """Grade power - yards after contact, short yardage success."""
        base = BASELINE_GRADE

        rushing_yards = self._get_stat(stats, "rushing_yards", 0)
        rushing_attempts = self._get_stat(stats, "rushing_attempts", 0)
        yards_after_contact = self._get_stat(stats, "yards_after_contact", 0)
        rushing_tds = self._get_stat(stats, "rushing_tds", 0)

        if rushing_attempts == 0:
            return BASELINE_GRADE

        # Power is shown by YAC and goal-line success
        if yards_after_contact and yards_after_contact > 3:
            base += 15

        # Short yardage TD shows power
        if rushing_tds > 0:
            base += 12

        return self._clamp(base)

    def _grade_pass_blocking(self, stats: Any) -> float:
        """Grade pass blocking ability."""
        base = BASELINE_GRADE

        pass_blocks = self._get_stat(stats, "pass_blocks", 0)
        sacks_allowed = self._get_stat(stats, "sacks_allowed", 0)
        pressures_allowed = self._get_stat(stats, "pressures_allowed", 0)

        if pass_blocks == 0:
            return BASELINE_GRADE  # No blocking assignment

        # Good blocking
        if pass_blocks > 0 and sacks_allowed == 0 and pressures_allowed == 0:
            base += 12

        # Bad blocking
        if sacks_allowed > 0:
            base -= 20
        if pressures_allowed > 0:
            base -= 8

        return self._clamp(base)

    def _grade_receiving(self, stats: Any) -> float:
        """Grade receiving ability."""
        base = BASELINE_GRADE

        targets = self._get_stat(stats, "targets", 0)
        receptions = self._get_stat(stats, "receptions", 0)
        receiving_yards = self._get_stat(stats, "receiving_yards", 0)
        receiving_tds = self._get_stat(stats, "receiving_tds", 0)
        drops = self._get_stat(stats, "drops", 0)

        if targets == 0:
            return BASELINE_GRADE  # Not targeted

        if receptions > 0:
            if receiving_yards >= 20:
                base += 20  # Big play in passing game
            elif receiving_yards >= 10:
                base += 15
            else:
                base += 10

        if drops > 0:
            base -= 15

        if receiving_tds > 0:
            base += 12

        return self._clamp(base)
