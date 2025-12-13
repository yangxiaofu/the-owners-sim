"""
Advanced Metrics

Calculators for advanced football analytics:
- EPA (Expected Points Added)
- Success Rate
- Air yards and YAC metrics
- Pressure metrics
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import AdvancedMetrics
from .grading_constants import (
    EPA_BY_YARD_LINE,
    EPA_DOWN_MULTIPLIER,
    SUCCESS_RATE_THRESHOLDS,
)


class EPACalculator:
    """Calculate Expected Points Added for plays.

    EPA = EP(end state) - EP(start state)

    Where EP (Expected Points) is based on field position and down.
    """

    def __init__(self):
        self._ep_cache: Dict[tuple, float] = {}

    def calculate_play_epa(
        self,
        start_yard_line: int,
        end_yard_line: int,
        start_down: int,
        end_down: int,
        is_turnover: bool = False,
        is_score: bool = False,
        points_scored: int = 0,
    ) -> float:
        """Calculate EPA for a single play.

        Args:
            start_yard_line: Yard line before play (1-99, own 1 to opp 1)
            end_yard_line: Yard line after play
            start_down: Down before play (1-4)
            end_down: Down after play (1-4)
            is_turnover: Whether play resulted in turnover
            is_score: Whether play resulted in score
            points_scored: Points scored on the play (if scoring play)

        Returns:
            EPA value (positive = good for offense, negative = bad)
        """
        start_ep = self._expected_points(start_yard_line, start_down)

        if is_score:
            return points_scored - start_ep

        if is_turnover:
            # Opponent gets ball at their own yard line
            opponent_start_yard = 100 - end_yard_line
            opponent_ep = self._expected_points(opponent_start_yard, 1)
            return -start_ep - opponent_ep

        end_ep = self._expected_points(end_yard_line, end_down)
        return end_ep - start_ep

    def _expected_points(self, yard_line: int, down: int) -> float:
        """Get expected points for a field position and down.

        Uses linear interpolation between lookup table values.
        """
        cache_key = (yard_line, down)
        if cache_key in self._ep_cache:
            return self._ep_cache[cache_key]

        # Clamp yard line
        yard_line = max(1, min(99, yard_line))
        down = max(1, min(4, down))

        # Get base EP from field position
        base_ep = self._interpolate_ep(yard_line)

        # Apply down modifier
        down_modifier = EPA_DOWN_MULTIPLIER.get(down, 1.0)
        ep = base_ep * down_modifier

        self._ep_cache[cache_key] = ep
        return ep

    def _interpolate_ep(self, yard_line: int) -> float:
        """Interpolate EP from the lookup table."""
        # Find surrounding values in the lookup table
        sorted_yards = sorted(EPA_BY_YARD_LINE.keys())

        # Find lower and upper bounds
        lower = 1
        upper = 99

        for yl in sorted_yards:
            if yl <= yard_line:
                lower = yl
            if yl >= yard_line:
                upper = yl
                break

        if lower == upper:
            return EPA_BY_YARD_LINE.get(lower, 0.0)

        # Linear interpolation
        lower_ep = EPA_BY_YARD_LINE.get(lower, 0.0)
        upper_ep = EPA_BY_YARD_LINE.get(upper, lower_ep)

        fraction = (yard_line - lower) / (upper - lower) if upper != lower else 0
        return lower_ep + (upper_ep - lower_ep) * fraction


class SuccessRateCalculator:
    """Calculate success rates for plays.

    A play is "successful" if it meets yard gain thresholds:
    - 1st down: Gain 40% of yards to go
    - 2nd down: Gain 50% of yards to go
    - 3rd/4th down: Convert (100% of yards to go)
    """

    def is_successful_play(
        self,
        down: int,
        distance: int,
        yards_gained: int,
    ) -> bool:
        """Determine if a play was successful.

        Args:
            down: Current down (1-4)
            distance: Yards to go for first down
            yards_gained: Yards gained on the play

        Returns:
            True if play met success threshold
        """
        if down < 1 or down > 4:
            return False

        threshold = SUCCESS_RATE_THRESHOLDS.get(down, 1.0)
        yards_needed = distance * threshold

        return yards_gained >= yards_needed

    def calculate_success_rate(
        self,
        plays: List[Dict[str, Any]],
    ) -> Optional[float]:
        """Calculate success rate for a list of plays.

        Args:
            plays: List of dicts with 'down', 'distance', 'yards_gained'

        Returns:
            Success rate (0.0-1.0) or None if no plays
        """
        if not plays:
            return None

        successful = 0
        for play in plays:
            down = play.get("down", 1)
            distance = play.get("distance", 10)
            yards_gained = play.get("yards_gained", 0)

            if self.is_successful_play(down, distance, yards_gained):
                successful += 1

        return successful / len(plays)


@dataclass
class PlayMetrics:
    """Metrics for a single play."""

    epa: float = 0.0
    is_successful: bool = False
    air_yards: int = 0
    yac: int = 0
    was_pressure: bool = False


class AdvancedMetricsCalculator:
    """Calculate all advanced metrics for a game or team."""

    def __init__(self):
        self.epa_calculator = EPACalculator()
        self.success_calculator = SuccessRateCalculator()

    def calculate_game_metrics(
        self,
        game_id: str,
        team_id: int,
        plays: List[Dict[str, Any]],
    ) -> AdvancedMetrics:
        """Calculate all advanced metrics for a team in a game.

        Args:
            game_id: Unique game identifier
            team_id: Team ID (1-32)
            plays: List of play data dictionaries

        Returns:
            AdvancedMetrics object with all calculated metrics
        """
        if not plays:
            return AdvancedMetrics(game_id=game_id, team_id=team_id)

        # Separate passing and rushing plays
        pass_plays = [p for p in plays if p.get("play_type") == "pass"]
        rush_plays = [p for p in plays if p.get("play_type") == "run"]

        # Calculate EPA
        total_epa = sum(self._play_epa(p) for p in plays)
        passing_epa = sum(self._play_epa(p) for p in pass_plays)
        rushing_epa = sum(self._play_epa(p) for p in rush_plays)
        epa_per_play = total_epa / len(plays) if plays else None

        # Calculate success rates
        success_rate = self.success_calculator.calculate_success_rate(plays)
        passing_success = self.success_calculator.calculate_success_rate(pass_plays)
        rushing_success = self.success_calculator.calculate_success_rate(rush_plays)

        # Calculate passing metrics
        air_yards_total = sum(p.get("air_yards", 0) for p in pass_plays)
        yac_total = sum(p.get("yac", 0) for p in pass_plays)

        # Calculate completion % over expected (simplified)
        completion_over_expected = self._completion_over_expected(pass_plays)

        # Calculate avg time to throw
        times = [p.get("time_to_throw") for p in pass_plays if p.get("time_to_throw")]
        avg_time_to_throw = sum(times) / len(times) if times else None

        # Calculate pressure rate
        pressured = sum(1 for p in pass_plays if p.get("was_pressured", False))
        pressure_rate = pressured / len(pass_plays) if pass_plays else None

        # Calculate defensive metrics (from defensive plays)
        defense_plays = [p for p in plays if p.get("is_defense", False)]
        pass_rush_wins = sum(1 for p in defense_plays if p.get("pass_rush_win", False))
        pass_rush_attempts = sum(1 for p in defense_plays if p.get("pass_rush_attempt", False))
        pass_rush_win_rate = (
            pass_rush_wins / pass_rush_attempts if pass_rush_attempts > 0 else None
        )

        coverage_successes = sum(1 for p in defense_plays if p.get("coverage_success", False))
        coverage_attempts = sum(1 for p in defense_plays if p.get("coverage_attempt", False))
        coverage_success_rate = (
            coverage_successes / coverage_attempts if coverage_attempts > 0 else None
        )

        missed_tackles = sum(p.get("missed_tackles", 0) for p in defense_plays)
        tackle_attempts = sum(p.get("tackle_attempts", 0) for p in defense_plays)
        missed_tackle_rate = (
            missed_tackles / tackle_attempts if tackle_attempts > 0 else None
        )

        forced_incompletions = sum(p.get("forced_incompletions", 0) for p in defense_plays)
        qb_hits = sum(p.get("qb_hits", 0) for p in defense_plays)

        return AdvancedMetrics(
            game_id=game_id,
            team_id=team_id,
            epa_total=round(total_epa, 2),
            epa_passing=round(passing_epa, 2),
            epa_rushing=round(rushing_epa, 2),
            epa_per_play=round(epa_per_play, 3) if epa_per_play else None,
            success_rate=round(success_rate, 3) if success_rate else None,
            passing_success_rate=round(passing_success, 3) if passing_success else None,
            rushing_success_rate=round(rushing_success, 3) if rushing_success else None,
            air_yards_total=air_yards_total,
            yac_total=yac_total,
            completion_pct_over_expected=completion_over_expected,
            avg_time_to_throw=round(avg_time_to_throw, 2) if avg_time_to_throw else None,
            pressure_rate=round(pressure_rate, 3) if pressure_rate else None,
            pass_rush_win_rate=round(pass_rush_win_rate, 3) if pass_rush_win_rate else None,
            coverage_success_rate=round(coverage_success_rate, 3) if coverage_success_rate else None,
            missed_tackle_rate=round(missed_tackle_rate, 3) if missed_tackle_rate else None,
            forced_incompletions=forced_incompletions,
            qb_hits=qb_hits,
        )

    def _play_epa(self, play: Dict[str, Any]) -> float:
        """Calculate EPA for a single play."""
        return self.epa_calculator.calculate_play_epa(
            start_yard_line=play.get("start_yard_line", 25),
            end_yard_line=play.get("end_yard_line", 25),
            start_down=play.get("down", 1),
            end_down=play.get("end_down", 1),
            is_turnover=play.get("is_turnover", False),
            is_score=play.get("is_score", False),
            points_scored=play.get("points_scored", 0),
        )

    def _completion_over_expected(self, pass_plays: List[Dict]) -> Optional[float]:
        """Calculate completion percentage over expected.

        Simplified version - would need actual expected completion data.
        """
        if not pass_plays:
            return None

        attempts = len(pass_plays)
        completions = sum(1 for p in pass_plays if p.get("completed", False))

        # Simplified expected completion (would need ML model in real implementation)
        # Use league average of ~65% as baseline
        expected_comp_rate = 0.65
        actual_comp_rate = completions / attempts

        return round(actual_comp_rate - expected_comp_rate, 3)
