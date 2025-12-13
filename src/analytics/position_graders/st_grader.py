"""
Special Teams Grader

Grades Kickers and Punters on field goal accuracy and punt placement.
Uses FGOE (Field Goal Over Expectation) for kickers based on distance/difficulty.
"""

from typing import Dict, Any

from .base_grader import BasePositionGrader
from analytics.models import PlayContext
from analytics.grading_constants import BASELINE_GRADE


# Expected FG make rates by distance (based on NFL averages)
EXPECTED_FG_RATE: Dict[int, float] = {
    20: 0.98,   # PAT distance
    30: 0.93,
    40: 0.85,
    50: 0.72,
    55: 0.60,
    60: 0.45,
}

ST_COMPONENT_WEIGHTS: Dict[str, float] = {
    "accuracy": 0.50,
    "distance": 0.30,
    "clutch": 0.20,
}


class STGrader(BasePositionGrader):
    """Grades kickers and punters."""

    def __init__(self, is_punter: bool = False):
        self.is_punter = is_punter

    def get_component_weights(self) -> Dict[str, float]:
        return ST_COMPONENT_WEIGHTS

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        if self.is_punter:
            return self._grade_punter(stats)
        return self._grade_kicker(context, stats)

    def _grade_kicker(self, context: PlayContext, stats: Any) -> Dict[str, float]:
        """Grade field goal attempt."""
        base = BASELINE_GRADE

        fg_made = self._get_stat(stats, "fg_made", 0)
        fg_attempted = self._get_stat(stats, "fg_attempted", 0)
        fg_distance = self._get_stat(stats, "fg_distance", 0)
        xp_made = self._get_stat(stats, "xp_made", 0)
        xp_attempted = self._get_stat(stats, "xp_attempted", 0)

        accuracy_grade = base
        distance_grade = base
        clutch_grade = base

        if fg_attempted > 0:
            # FGOE: Field Goal Over Expectation
            expected_rate = self._get_expected_fg_rate(fg_distance)

            if fg_made > 0:
                # Made FG: bonus based on difficulty
                difficulty_bonus = (1.0 - expected_rate) * 40  # 0-40 pts based on difficulty
                accuracy_grade = base + 15 + difficulty_bonus

                # Long distance bonus
                if fg_distance >= 50:
                    distance_grade = base + 25
                elif fg_distance >= 40:
                    distance_grade = base + 15
                else:
                    distance_grade = base + 5
            else:
                # Missed FG: penalty based on expected make rate
                expected_penalty = expected_rate * 30  # Higher expected = worse miss
                accuracy_grade = base - 10 - expected_penalty
                distance_grade = base - 5

        elif xp_attempted > 0:
            # Extra points
            if xp_made > 0:
                accuracy_grade = base + 5  # Expected result
            else:
                accuracy_grade = base - 20  # PAT miss is bad

        # Clutch situations (close game in 4th quarter)
        if context.quarter == 4 and abs(context.score_differential) <= 3:
            if fg_made > 0:
                clutch_grade = base + 20
            elif fg_attempted > 0:
                clutch_grade = base - 15

        return {
            "accuracy": self._clamp(accuracy_grade),
            "distance": self._clamp(distance_grade),
            "clutch": self._clamp(clutch_grade),
        }

    def _grade_punter(self, stats: Any) -> Dict[str, float]:
        """Grade punt attempt."""
        base = BASELINE_GRADE

        punt_yards = self._get_stat(stats, "punt_yards", 0)
        punt_attempts = self._get_stat(stats, "punt_attempts", 0)
        punts_inside_20 = self._get_stat(stats, "punts_inside_20", 0)
        touchbacks = self._get_stat(stats, "touchbacks", 0)
        hang_time = self._get_stat(stats, "hang_time", 0)

        accuracy_grade = base
        distance_grade = base

        if punt_attempts > 0:
            avg_punt = punt_yards / punt_attempts if punt_attempts > 0 else 0

            # Distance grading
            if avg_punt >= 50:
                distance_grade = base + 25
            elif avg_punt >= 45:
                distance_grade = base + 15
            elif avg_punt >= 40:
                distance_grade = base + 5
            elif avg_punt < 35:
                distance_grade = base - 15

            # Accuracy (inside 20 vs touchbacks)
            if punts_inside_20 > 0:
                accuracy_grade = base + 20
            elif touchbacks > 0:
                accuracy_grade = base - 10  # Touchback is suboptimal

            # Hang time bonus
            if hang_time and hang_time >= 4.5:
                accuracy_grade += 10

        return {
            "accuracy": self._clamp(accuracy_grade),
            "distance": self._clamp(distance_grade),
            "clutch": self._clamp(base),  # Punts rarely clutch
        }

    def _get_expected_fg_rate(self, distance: int) -> float:
        """Get expected FG make rate for a given distance."""
        for dist, rate in sorted(EXPECTED_FG_RATE.items()):
            if distance <= dist:
                return rate
        return 0.30  # Very long attempts