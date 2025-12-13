"""
Defensive Back Grader

Grades DBs on coverage, ball skills, tackling, and zone awareness.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    DB_COMPONENT_WEIGHTS,
    DB_ADJUSTMENTS,
)


class DBGrader(BasePositionGrader):
    """Grades defensive backs on coverage, ball skills, tackling, and awareness."""

    def get_component_weights(self) -> Dict[str, float]:
        return DB_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "coverage": self._grade_coverage(stats),
            "ball_skills": self._grade_ball_skills(stats),
            "tackling": self._grade_tackling(stats),
            "zone_awareness": self._grade_zone_awareness(stats),
        }

    def _grade_coverage(self, stats: Any) -> float:
        """Grade man and zone coverage ability using coverage attribution stats."""
        base = BASELINE_GRADE

        # Primary coverage metrics (from coverage attribution system)
        coverage_targets = self._get_stat(stats, "coverage_targets", 0)
        coverage_completions = self._get_stat(stats, "coverage_completions", 0)
        coverage_yards_allowed = self._get_stat(stats, "coverage_yards_allowed", 0)

        # Use coverage attribution if available (much more accurate)
        if coverage_targets > 0:
            catch_rate_allowed = coverage_completions / coverage_targets
            yards_per_target = coverage_yards_allowed / coverage_targets

            # Elite coverage: catch rate <= 40%
            if catch_rate_allowed <= 0.40:
                base += 25
            # Good coverage: catch rate <= 55%
            elif catch_rate_allowed <= 0.55:
                base += 15
            # Average coverage: catch rate <= 65%
            elif catch_rate_allowed <= 0.65:
                base += 5
            # Below average coverage: catch rate <= 75%
            elif catch_rate_allowed <= 0.75:
                base -= 5
            # Poor coverage: catch rate > 75%
            else:
                base -= 15

            # Yards per target adjustment
            if yards_per_target <= 5.0:
                base += 8  # Limiting damage
            elif yards_per_target >= 12.0:
                base -= 10  # Giving up big plays
        else:
            # FALLBACK: Only use traditional stats when no coverage attribution data
            passes_defended = self._get_stat(stats, "passes_defended", 0)
            interceptions = self._get_stat(stats, "interceptions", 0)

            if interceptions > 0:
                base += 20  # INT shows great coverage

            if passes_defended > 0:
                base += 12  # PD shows good positioning

        return self._clamp(base)

    def _grade_ball_skills(self, stats: Any) -> float:
        """Grade interceptions and pass breakups."""
        base = BASELINE_GRADE

        interceptions = self._get_stat(stats, "interceptions", 0)
        passes_defended = self._get_stat(stats, "passes_defended", 0)
        forced_fumbles = self._get_stat(stats, "forced_fumbles", 0)

        if interceptions > 0:
            base += DB_ADJUSTMENTS.get("interception", 28)

        if passes_defended > 0:
            base += DB_ADJUSTMENTS.get("pass_defended", 18)

        if forced_fumbles > 0:
            base += DB_ADJUSTMENTS.get("forced_fumble", 20)

        return self._clamp(base)

    def _grade_tackling(self, stats: Any) -> float:
        """Grade tackling in space."""
        base = BASELINE_GRADE

        tackles = self._get_stat(stats, "tackles", 0)
        assisted_tackles = self._get_stat(stats, "assisted_tackles", 0)
        missed_tackles = self._get_stat(stats, "missed_tackles", 0)

        if tackles > 0:
            base += DB_ADJUSTMENTS.get("solo_tackle", 8)

        if assisted_tackles > 0:
            base += 4

        # DBs who miss tackles in space often lead to big plays
        if missed_tackles > 0:
            base += DB_ADJUSTMENTS.get("missed_tackle", -18)

        return self._clamp(base)

    def _grade_zone_awareness(self, stats: Any) -> float:
        """Grade reading routes and zone discipline."""
        base = BASELINE_GRADE

        # Zone awareness is harder to quantify directly
        # Use pass defense and INT as proxies
        passes_defended = self._get_stat(stats, "passes_defended", 0)
        interceptions = self._get_stat(stats, "interceptions", 0)

        # Good reads lead to plays on the ball
        if interceptions > 0:
            base += 15

        if passes_defended > 0:
            base += 10

        return self._clamp(base)
