"""
Wide Receiver / Tight End Grader

Grades WRs and TEs on route running, separation, contested catches, blocking, and YAC.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    WR_COMPONENT_WEIGHTS,
    TE_COMPONENT_WEIGHTS,
    WR_ADJUSTMENTS,
)


class WRGrader(BasePositionGrader):
    """Grades wide receivers and tight ends."""

    def __init__(self, is_te: bool = False):
        self.is_te = is_te

    def get_component_weights(self) -> Dict[str, float]:
        return TE_COMPONENT_WEIGHTS if self.is_te else WR_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "route_running": self._grade_route_running(stats),
            "separation": self._grade_separation(stats),
            "contested_catches": self._grade_contested_catches(stats),
            "blocking": self._grade_blocking(stats),
            "yac": self._grade_yac(stats),
        }

    def _grade_route_running(self, stats: Any) -> float:
        """Grade route running - precision, timing, breaks."""
        base = BASELINE_GRADE

        targets = self._get_stat(stats, "targets", 0)
        receptions = self._get_stat(stats, "receptions", 0)
        receiving_yards = self._get_stat(stats, "receiving_yards", 0)
        air_yards = self._get_stat(stats, "air_yards", 0)

        if targets == 0:
            # Not targeted - could still grade route
            return BASELINE_GRADE

        # Catch rate indicates route quality
        if receptions > 0:
            base += 12

            # Deep routes are harder
            if air_yards and air_yards > 15:
                base += 8

        return self._clamp(base)

    def _grade_separation(self, stats: Any) -> float:
        """Grade separation - getting open, creating space."""
        base = BASELINE_GRADE

        targets = self._get_stat(stats, "targets", 0)
        receptions = self._get_stat(stats, "receptions", 0)

        if targets == 0:
            return BASELINE_GRADE

        # Getting targeted indicates separation
        base += 5

        # Catches indicate good separation
        if receptions > 0:
            base += 10

        return self._clamp(base)

    def _grade_contested_catches(self, stats: Any) -> float:
        """Grade contested catches - high-point catches, jump balls."""
        base = BASELINE_GRADE

        receptions = self._get_stat(stats, "receptions", 0)
        targets = self._get_stat(stats, "targets", 0)
        drops = self._get_stat(stats, "drops", 0)
        receiving_tds = self._get_stat(stats, "receiving_tds", 0)
        air_yards = self._get_stat(stats, "air_yards", 0)

        if targets == 0:
            return BASELINE_GRADE

        if receptions > 0:
            # Use air_yards to determine catch depth (deep catches valued ~2x short)
            if air_yards and air_yards >= 20:
                base += WR_ADJUSTMENTS.get("catch_deep", 22)
            elif air_yards and air_yards >= 10:
                base += WR_ADJUSTMENTS.get("catch_intermediate", 15)
            else:
                base += WR_ADJUSTMENTS.get("catch_short", 10)

        if drops > 0:
            base += WR_ADJUSTMENTS.get("drop", -15)

        if receiving_tds > 0:
            base += WR_ADJUSTMENTS.get("touchdown_catch", 10)

        return self._clamp(base)

    def _grade_blocking(self, stats: Any) -> float:
        """Grade blocking - run blocking, stalk blocking."""
        base = BASELINE_GRADE

        blocks = self._get_stat(stats, "blocks_made", 0)
        pancakes = self._get_stat(stats, "pancakes", 0)
        downfield_blocks = self._get_stat(stats, "downfield_blocks", 0)

        if blocks > 0:
            base += 8

        if pancakes > 0:
            base += WR_ADJUSTMENTS.get("pancake_block", 12)

        if downfield_blocks > 0:
            base += 10

        return self._clamp(base)

    def _grade_yac(self, stats: Any) -> float:
        """Grade yards after catch ability."""
        base = BASELINE_GRADE

        receptions = self._get_stat(stats, "receptions", 0)
        yac = self._get_stat(stats, "yac", 0) or self._get_stat(stats, "yards_after_catch", 0)
        receiving_yards = self._get_stat(stats, "receiving_yards", 0)

        if receptions == 0:
            return BASELINE_GRADE

        # YAC bonus
        if yac and yac >= 5:
            base += WR_ADJUSTMENTS.get("yac_bonus", 5) * (yac // 5)

        # Big YAC plays
        if yac and yac >= 15:
            base += 10

        return self._clamp(base)
