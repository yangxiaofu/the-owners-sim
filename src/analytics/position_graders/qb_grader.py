"""
Quarterback Grader

Grades QBs on accuracy, decision-making, pocket presence, deep ball, and mobility.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    QB_COMPONENT_WEIGHTS,
    QB_ADJUSTMENTS,
)


class QBGrader(BasePositionGrader):
    """Grades quarterbacks on accuracy, decision-making, pocket presence."""

    def get_component_weights(self) -> Dict[str, float]:
        return QB_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "accuracy": self._grade_accuracy(stats),
            "decision": self._grade_decision(context, stats),
            "pocket_presence": self._grade_pocket_presence(stats),
            "deep_ball": self._grade_deep_ball(stats),
            "mobility": self._grade_mobility(stats),
        }

    def _grade_accuracy(self, stats: Any) -> float:
        """Grade based on completion and throw quality."""
        attempts = self._get_stat(stats, "passing_attempts", 0)
        if attempts == 0:
            return BASELINE_GRADE  # Neutral for non-passing play

        base = BASELINE_GRADE
        completions = self._get_stat(stats, "passing_completions", 0)
        interceptions = self._get_stat(stats, "interceptions_thrown", 0)
        drops = self._get_stat(stats, "drops", 0)
        air_yards = self._get_stat(stats, "air_yards", 0)

        if completions > 0:
            # Completion bonus based on depth
            if air_yards and air_yards > 20:
                base += QB_ADJUSTMENTS.get("completion_deep", 25)
            elif air_yards and air_yards > 10:
                base += QB_ADJUSTMENTS.get("completion_intermediate", 18)
            else:
                base += QB_ADJUSTMENTS.get("completion_short", 12)

            # Big-Time Throw: deep completion under pressure (P2 enhancement)
            pressures = self._get_stat(stats, "pressures_faced", 0)
            if air_yards and air_yards >= 20 and pressures > 0:
                base += 10  # BTT bonus for exceptional throw
        else:
            # Incompletion handling (INTs penalized in decision grade, not here)
            if drops > 0:
                base += QB_ADJUSTMENTS.get("dropped_pass", 5)  # Not QB's fault
            elif interceptions == 0:
                # Only penalize non-INT incompletions (INTs handled in decision grade)
                base += QB_ADJUSTMENTS.get("incompletion", -10)

        return self._clamp(base)

    def _grade_decision(self, context: PlayContext, stats: Any) -> float:
        """Grade decision-making."""
        base = BASELINE_GRADE

        completions = self._get_stat(stats, "passing_completions", 0)
        interceptions = self._get_stat(stats, "interceptions_thrown", 0)
        sacks = self._get_stat(stats, "sacks_taken", 0)
        tds = self._get_stat(stats, "passing_tds", 0)

        # Good decision indicators
        if context.down >= 3 and completions > 0:
            base += 10  # Conversion on critical down

        if tds > 0:
            base += 8  # Touchdown pass shows good read

        # Bad decision indicators
        if interceptions > 0:
            base -= 25  # Interception is a major mistake
        if sacks > 0:
            base -= 10  # Held ball too long

        return self._clamp(base)

    def _grade_pocket_presence(self, stats: Any) -> float:
        """Grade pocket awareness and movement."""
        base = BASELINE_GRADE

        pressures = self._get_stat(stats, "pressures_faced", 0)
        sacks = self._get_stat(stats, "sacks_taken", 0)
        qb_hits = self._get_stat(stats, "qb_hits_taken", 0)
        completions = self._get_stat(stats, "passing_completions", 0)

        if pressures > 0:
            if sacks == 0:
                base += QB_ADJUSTMENTS.get("sack_avoided_under_pressure", 15)
            else:
                base -= 10

        if qb_hits > 0 and completions > 0:
            base += QB_ADJUSTMENTS.get("pressure_completion", 10)

        return self._clamp(base)

    def _grade_deep_ball(self, stats: Any) -> float:
        """Grade deep passing ability."""
        air_yards = self._get_stat(stats, "air_yards", 0)

        if not air_yards or air_yards < 20:
            return BASELINE_GRADE  # No deep attempt

        base = BASELINE_GRADE
        completions = self._get_stat(stats, "passing_completions", 0)

        if completions > 0:
            base += 20  # Deep completion is valuable
        else:
            base -= 5  # Deep incompletion is less penalized

        return self._clamp(base)

    def _grade_mobility(self, stats: Any) -> float:
        """Grade scrambling and mobility."""
        base = BASELINE_GRADE

        rushing_yards = self._get_stat(stats, "rushing_yards", 0)
        rushing_tds = self._get_stat(stats, "rushing_tds", 0)

        if rushing_yards > 0:
            base += min(15, rushing_yards // 2)

        if rushing_tds > 0:
            base += 20

        return self._clamp(base)
