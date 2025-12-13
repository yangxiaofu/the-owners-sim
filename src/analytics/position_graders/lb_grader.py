"""
Linebacker Grader

Grades LBs on coverage, tackling, blitzing, and run fits.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    LB_COMPONENT_WEIGHTS,
    LB_ADJUSTMENTS,
)


class LBGrader(BasePositionGrader):
    """Grades linebackers on coverage, tackling, blitzing, and run fits."""

    def get_component_weights(self) -> Dict[str, float]:
        return LB_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "coverage": self._grade_coverage(stats),
            "tackling": self._grade_tackling(stats),
            "blitzing": self._grade_blitzing(stats),
            "run_fits": self._grade_run_fits(stats),
        }

    def _grade_coverage(self, stats: Any) -> float:
        """Grade pass coverage ability using coverage attribution stats."""
        base = BASELINE_GRADE

        # Primary coverage metrics (from coverage attribution system)
        coverage_targets = self._get_stat(stats, "coverage_targets", 0)
        coverage_completions = self._get_stat(stats, "coverage_completions", 0)
        coverage_yards_allowed = self._get_stat(stats, "coverage_yards_allowed", 0)

        # Use coverage attribution if available (much more accurate)
        # LBs have higher expected catch rates than DBs (covering TEs/RBs)
        if coverage_targets > 0:
            catch_rate_allowed = coverage_completions / coverage_targets
            yards_per_target = coverage_yards_allowed / coverage_targets

            # Elite coverage for LB: catch rate <= 55%
            if catch_rate_allowed <= 0.55:
                base += 22
            # Good coverage: catch rate <= 65%
            elif catch_rate_allowed <= 0.65:
                base += 12
            # Average coverage: catch rate <= 75%
            elif catch_rate_allowed <= 0.75:
                base += 4
            # Below average coverage: catch rate <= 85%
            elif catch_rate_allowed <= 0.85:
                base -= 5
            # Poor coverage: catch rate > 85%
            else:
                base -= 12

            # Yards per target adjustment (LBs expected to give up more YAC)
            if yards_per_target <= 6.0:
                base += 6  # Limiting damage
            elif yards_per_target >= 10.0:
                base -= 8  # Giving up too many yards
        else:
            # FALLBACK: Only use traditional stats when no coverage attribution data
            passes_defended = self._get_stat(stats, "passes_defended", 0)
            interceptions = self._get_stat(stats, "interceptions", 0)

            if interceptions > 0:
                base += LB_ADJUSTMENTS.get("interception", 25)

            if passes_defended > 0:
                base += LB_ADJUSTMENTS.get("pass_defended", 15)

        return self._clamp(base)

    def _grade_tackling(self, stats: Any) -> float:
        """Grade tackling efficiency."""
        base = BASELINE_GRADE

        tackles = self._get_stat(stats, "tackles", 0)
        assisted_tackles = self._get_stat(stats, "assisted_tackles", 0)
        tackles_for_loss = self._get_stat(stats, "tackles_for_loss", 0)
        missed_tackles = self._get_stat(stats, "missed_tackles", 0)
        forced_fumbles = self._get_stat(stats, "forced_fumbles", 0)

        # Positive plays
        if tackles > 0:
            base += LB_ADJUSTMENTS.get("solo_tackle", 10)

        if assisted_tackles > 0:
            base += LB_ADJUSTMENTS.get("assisted_tackle", 5)

        if tackles_for_loss > 0:
            base += LB_ADJUSTMENTS.get("tackle_for_loss", 15)

        if forced_fumbles > 0:
            base += LB_ADJUSTMENTS.get("forced_fumble", 20)

        # Negative plays
        if missed_tackles > 0:
            base += LB_ADJUSTMENTS.get("missed_tackle", -15)

        return self._clamp(base)

    def _grade_blitzing(self, stats: Any) -> float:
        """Grade pass rush when blitzing."""
        base = BASELINE_GRADE

        sacks = self._get_stat(stats, "sacks", 0)
        qb_hits = self._get_stat(stats, "qb_hits", 0)
        qb_pressures = self._get_stat(stats, "qb_pressures", 0)

        if sacks > 0:
            base += LB_ADJUSTMENTS.get("sack", 22)

        if qb_hits > 0:
            base += 12

        if qb_pressures > 0:
            base += 8

        return self._clamp(base)

    def _grade_run_fits(self, stats: Any) -> float:
        """Grade gap discipline and run defense."""
        base = BASELINE_GRADE

        tackles = self._get_stat(stats, "tackles", 0)
        tackles_for_loss = self._get_stat(stats, "tackles_for_loss", 0)
        missed_tackles = self._get_stat(stats, "missed_tackles", 0)

        # Good run fits result in tackles near line
        if tackles_for_loss > 0:
            base += 15

        if tackles > 0:
            base += 8

        # Missing tackles indicates bad pursuit angles
        if missed_tackles > 0:
            base -= 12

        return self._clamp(base)
