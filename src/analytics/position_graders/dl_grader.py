"""
Defensive Line Grader

Grades DL on pass rush, run defense, and versatility.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import (
    BASELINE_GRADE,
    DL_COMPONENT_WEIGHTS,
    DL_ADJUSTMENTS,
)


class DLGrader(BasePositionGrader):
    """Grades defensive linemen on pass rush and run defense."""

    def get_component_weights(self) -> Dict[str, float]:
        return DL_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        return {
            "pass_rush": self._grade_pass_rush(stats),
            "run_defense": self._grade_run_defense(stats),
            "versatility": self._grade_versatility(stats),
        }

    def _grade_pass_rush(self, stats: Any) -> float:
        """Grade pass rushing ability using pass rush win rate and pressure stats."""
        base = BASELINE_GRADE

        # Primary metrics: pass rush win rate (if available)
        pass_rush_wins = self._get_stat(stats, "pass_rush_wins", 0)
        pass_rush_attempts = self._get_stat(stats, "pass_rush_attempts", 0)
        times_double_teamed = self._get_stat(stats, "times_double_teamed", 0)
        blocking_encounters = self._get_stat(stats, "blocking_encounters", 0)

        # Use pass rush win rate if we have enough data (PRIMARY method)
        if pass_rush_attempts >= 3:
            win_rate = pass_rush_wins / pass_rush_attempts

            # Adjusted thresholds based on real PFF data (Myles Garrett ~23% elite)
            # Elite pass rush win rate: 20%+
            if win_rate >= 0.20:
                base += 25
            # Good pass rush win rate: 16%+
            elif win_rate >= 0.16:
                base += 18
            # Average pass rush win rate: 12%+
            elif win_rate >= 0.12:
                base += 10
            # Below average: 8%+
            elif win_rate >= 0.08:
                base += 3
            # Poor pass rush: <8%
            else:
                base -= 8

            # Double team bonus (elite DL draw doubles)
            if blocking_encounters >= 3:
                double_team_rate = times_double_teamed / blocking_encounters
                if double_team_rate >= 0.40:
                    base += 12  # Commands significant doubles
                elif double_team_rate >= 0.30:
                    base += 8   # Regularly doubled
        else:
            # FALLBACK: Use traditional outcome stats when insufficient win rate data
            sacks = self._get_stat(stats, "sacks", 0)
            qb_hits = self._get_stat(stats, "qb_hits", 0)
            qb_pressures = self._get_stat(stats, "qb_pressures", 0)
            qb_hurries = self._get_stat(stats, "qb_hurries", 0)

            if sacks > 0:
                base += DL_ADJUSTMENTS.get("sack", 25)
            if qb_hits > 0:
                base += DL_ADJUSTMENTS.get("qb_hit", 15)
            if qb_pressures > 0:
                base += DL_ADJUSTMENTS.get("qb_pressure", 10)
            if qb_hurries > 0:
                base += 6

        return self._clamp(base)

    def _grade_run_defense(self, stats: Any) -> float:
        """Grade run stopping ability."""
        base = BASELINE_GRADE

        tackles = self._get_stat(stats, "tackles", 0)
        assisted_tackles = self._get_stat(stats, "assisted_tackles", 0)
        tackles_for_loss = self._get_stat(stats, "tackles_for_loss", 0)
        missed_tackles = self._get_stat(stats, "missed_tackles", 0)

        # Positive plays
        if tackles_for_loss > 0:
            base += DL_ADJUSTMENTS.get("tackle_for_loss", 18)

        if tackles > 0:
            base += 10  # Making the tackle

        if assisted_tackles > 0:
            base += 5  # Contribution to tackle

        # Negative plays
        if missed_tackles > 0:
            base += DL_ADJUSTMENTS.get("missed_tackle", -15)

        return self._clamp(base)

    def _grade_versatility(self, stats: Any) -> float:
        """Grade ability to contribute in both pass rush and run defense."""
        base = BASELINE_GRADE

        # Check for contributions in both areas
        pass_rush_contribution = (
            self._get_stat(stats, "sacks", 0) > 0 or
            self._get_stat(stats, "qb_hits", 0) > 0 or
            self._get_stat(stats, "qb_pressures", 0) > 0
        )

        run_defense_contribution = (
            self._get_stat(stats, "tackles", 0) > 0 or
            self._get_stat(stats, "tackles_for_loss", 0) > 0
        )

        # Bonus for contributing in both areas
        if pass_rush_contribution and run_defense_contribution:
            base += 15
        elif pass_rush_contribution or run_defense_contribution:
            base += 8

        return self._clamp(base)
