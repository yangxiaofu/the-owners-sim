"""
Grading Algorithm

Core grading logic with context-aware modifiers for the PFF-style
player grading system.

Implements:
- GradingAlgorithm protocol (for pluggable implementations)
- StandardGradingAlgorithm (default implementation)
- Grade aggregation functions (play → game → season)
"""

from typing import Protocol, Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict

from .models import PlayGrade, GameGrade, SeasonGrade, PlayContext
from .grading_constants import (
    BASELINE_GRADE,
    POSITIVE_PLAY_THRESHOLD,
    MIN_GRADE,
    MAX_GRADE,
    CONTEXT_MODIFIERS,
    get_position_group,
    get_component_weights,
    clamp_grade,
    MIN_SNAPS_FOR_GAME_GRADE,
    MIN_SNAPS_FOR_SEASON_RANKING,
    MIN_GAMES_FOR_SEASON_RANKING,
)

if TYPE_CHECKING:
    from play_engine.simulation.stats import PlayerStats
    from play_engine.core.play_result import PlayResult


class PositionGraderProtocol(Protocol):
    """Protocol for position-specific graders."""

    def grade_play(
        self, context: PlayContext, stats: Any
    ) -> Dict[str, float]:
        """Calculate position-specific component grades.

        Returns a dictionary of component name to grade value (0-100).
        """
        ...

    def get_component_weights(self) -> Dict[str, float]:
        """Get weights for each component."""
        ...


class GradingAlgorithm(Protocol):
    """Protocol for pluggable grading algorithms."""

    def grade_play(
        self,
        context: PlayContext,
        player_stats: Any,
        play_result: Any,
    ) -> PlayGrade:
        """Calculate grade for a single play."""
        ...

    def aggregate_to_game(
        self,
        play_grades: List[PlayGrade],
        game_id: str,
        season: int,
        week: int,
    ) -> GameGrade:
        """Aggregate play grades to game grade."""
        ...

    def aggregate_to_season(
        self,
        game_grades: List[GameGrade],
    ) -> SeasonGrade:
        """Aggregate game grades to season grade."""
        ...


class StandardGradingAlgorithm:
    """Default implementation with context-aware grading.

    This algorithm:
    1. Uses position-specific graders for component grades
    2. Applies context modifiers (clutch, red zone, etc.)
    3. Calculates weighted overall grade
    4. Handles aggregation from play → game → season
    """

    def __init__(self, position_graders: Optional[Dict[str, PositionGraderProtocol]] = None):
        """Initialize with optional position graders.

        If position_graders is None, uses default grading logic.
        """
        self.position_graders = position_graders or {}

    def grade_play(
        self,
        context: PlayContext,
        player_stats: Any,
        play_result: Any,
    ) -> PlayGrade:
        """Calculate grade for a single play.

        Grade formula:
        1. Establish baseline (60 = neutral)
        2. Get position-specific component grades
        3. Apply context modifiers (clutch, pressure, etc.)
        4. Calculate weighted overall grade
        5. Clamp to 0-100
        """
        position = getattr(player_stats, "position", "UNKNOWN")
        player_id = getattr(player_stats, "player_id", 0) or getattr(player_stats, "player_number", 0)
        team_id = getattr(player_stats, "team_id", 0)

        # Get position group and grader
        position_group = get_position_group(position)

        # Calculate component grades
        if position_group in self.position_graders:
            grader = self.position_graders[position_group]
            components = grader.grade_play(context, player_stats)
            weights = grader.get_component_weights()
        else:
            # Default grading when no specific grader available
            components = self._default_grade_components(context, player_stats, play_result)
            weights = {"default": 1.0}

        # Calculate weighted overall grade
        if components and weights:
            total_weight = sum(weights.get(k, 1.0) for k in components)
            if total_weight > 0:
                overall = sum(
                    components[k] * weights.get(k, 1.0) for k in components
                ) / total_weight
            else:
                overall = BASELINE_GRADE
        else:
            overall = BASELINE_GRADE

        # Apply context modifiers
        context_modifier = self._calculate_context_modifier(context)
        overall = overall * context_modifier

        # Ensure grade is within bounds
        overall = clamp_grade(overall)

        # Determine if positive play
        was_positive = overall >= POSITIVE_PLAY_THRESHOLD

        # Calculate EPA contribution (placeholder - will be filled by EPACalculator)
        epa = self._estimate_epa_contribution(context, play_result)

        return PlayGrade(
            player_id=player_id,
            game_id=context.game_id,
            play_number=context.play_number,
            position=position,
            team_id=team_id,
            play_grade=round(overall, 1),
            grade_components=components,
            context=context,
            was_positive_play=was_positive,
            epa_contribution=epa,
        )

    def _default_grade_components(
        self,
        context: PlayContext,
        player_stats: Any,
        play_result: Any,
    ) -> Dict[str, float]:
        """Generate default component grades when no specific grader is available.

        Uses basic heuristics based on available stats.
        """
        base = BASELINE_GRADE

        # Check for positive/negative outcomes
        yards = getattr(play_result, "yards", 0) if play_result else 0

        if context.is_offense:
            # Offensive player grading
            if yards > 0:
                base += min(15, yards * 1.5)  # Bonus for positive yards
            elif yards < 0:
                base -= min(15, abs(yards) * 2)  # Penalty for negative yards

            # Check for big plays
            if yards >= 20:
                base += 10  # Explosive play bonus

            # Check for turnovers
            if hasattr(play_result, "is_turnover") and play_result.is_turnover:
                base -= 20  # Turnover penalty

            # Touchdown bonus
            if hasattr(play_result, "points") and play_result.points > 0:
                base += 15
        else:
            # Defensive player grading
            tackles = getattr(player_stats, "tackles", 0) or 0
            sacks = getattr(player_stats, "sacks", 0) or 0
            interceptions = getattr(player_stats, "interceptions", 0) or 0
            passes_defended = getattr(player_stats, "passes_defended", 0) or 0

            if tackles > 0:
                base += 8
            if sacks > 0:
                base += 20
            if interceptions > 0:
                base += 25
            if passes_defended > 0:
                base += 12

            # Negative plays allowed
            if yards > 10:
                base -= 10  # Big play allowed

        return {"default": clamp_grade(base)}

    def _calculate_context_modifier(self, context: PlayContext) -> float:
        """Calculate context modifier based on game situation.

        Context modifiers:
        - 4th quarter, close game: 1.1x
        - Red zone: 1.05x
        - 3rd/4th down: 1.05x
        - Garbage time: 0.9x
        - Goal line: 1.08x
        - Two-minute warning: 1.07x
        """
        modifier = 1.0

        # Clutch situations (4th quarter, close game within 8 points)
        if context.quarter == 4 and abs(context.score_differential) <= 8:
            modifier *= CONTEXT_MODIFIERS.get("clutch", 1.1)

        # Red zone (inside opponent's 20-yard line, i.e., yard_line >= 80)
        if context.yard_line >= 80:
            modifier *= CONTEXT_MODIFIERS.get("red_zone", 1.05)

        # Goal line (inside 5-yard line, i.e., yard_line >= 95)
        if context.yard_line >= 95:
            modifier *= CONTEXT_MODIFIERS.get("goal_line", 1.08)

        # Critical downs (3rd and 4th down)
        if context.down >= 3:
            modifier *= CONTEXT_MODIFIERS.get("critical_down", 1.05)

        # Two-minute warning (less than 2 minutes in 2nd or 4th quarter)
        if context.quarter in (2, 4) and context.game_clock <= 120:
            modifier *= CONTEXT_MODIFIERS.get("two_minute", 1.07)

        # Garbage time penalty (4th quarter, score differential > 21)
        if context.quarter == 4 and abs(context.score_differential) > 21:
            modifier *= CONTEXT_MODIFIERS.get("garbage_time", 0.9)

        # Cap total modifier to prevent grade inflation (PFF adjustments are subtle)
        modifier = min(modifier, 1.15)

        return modifier

    def _estimate_epa_contribution(
        self, context: PlayContext, play_result: Any
    ) -> float:
        """Estimate EPA contribution (simplified).

        Full EPA calculation should use EPACalculator from advanced_metrics.
        This provides a rough estimate based on yards gained.
        """
        if play_result is None:
            return 0.0

        yards = getattr(play_result, "yards", 0) or 0
        is_turnover = getattr(play_result, "is_turnover", False)
        points = getattr(play_result, "points", 0) or 0

        if points > 0:
            return float(points)
        if is_turnover:
            return -2.5
        return yards * 0.05  # Rough estimate

    def aggregate_to_game(
        self,
        play_grades: List[PlayGrade],
        game_id: str,
        season: int,
        week: int,
    ) -> GameGrade:
        """Aggregate play grades to a game grade.

        Uses simple average weighted by snap participation.
        """
        if not play_grades:
            raise ValueError("Cannot aggregate empty play grades list")

        # All grades should be for the same player
        player_id = play_grades[0].player_id
        position = play_grades[0].position
        team_id = play_grades[0].team_id

        # Calculate overall grade (simple average)
        overall_grade = sum(g.play_grade for g in play_grades) / len(play_grades)

        # Count positive/negative plays
        positive_plays = sum(1 for g in play_grades if g.was_positive_play)
        negative_plays = sum(1 for g in play_grades if g.play_grade < BASELINE_GRADE)

        # Sum EPA
        epa_total = sum(g.epa_contribution for g in play_grades)

        # Calculate success rate
        success_rate = positive_plays / len(play_grades) if play_grades else None

        # Count offensive vs defensive snaps using the is_offense flag stored
        # directly on each grade (avoids context sharing bug where all grades
        # from same play shared one context object by reference)
        offensive_snaps = sum(1 for g in play_grades if g.is_offense)
        defensive_snaps = len(play_grades) - offensive_snaps

        # Aggregate component grades by position
        position_grades = self._aggregate_position_grades(play_grades, position)

        return GameGrade(
            player_id=player_id,
            game_id=game_id,
            season=season,
            week=week,
            position=position,
            team_id=team_id,
            overall_grade=round(overall_grade, 1),
            offensive_snaps=offensive_snaps,
            defensive_snaps=defensive_snaps,
            epa_total=round(epa_total, 2),
            success_rate=round(success_rate, 3) if success_rate is not None else None,
            play_count=len(play_grades),
            positive_plays=positive_plays,
            negative_plays=negative_plays,
            **position_grades,
        )

    def _aggregate_position_grades(
        self, play_grades: List[PlayGrade], position: str
    ) -> Dict[str, Optional[float]]:
        """Aggregate position-specific sub-grades from play grades using actual component grades."""
        position_group = get_position_group(position)

        # Initialize all sub-grades as None
        sub_grades = {
            "passing_grade": None,
            "rushing_grade": None,
            "receiving_grade": None,
            "pass_blocking_grade": None,
            "run_blocking_grade": None,
            "pass_rush_grade": None,
            "run_defense_grade": None,
            "coverage_grade": None,
            "tackling_grade": None,
        }

        # Map component names (from graders) to sub-grade keys
        component_to_subgrade = {
            # OL components
            "pass_blocking": "pass_blocking_grade",
            "run_blocking": "run_blocking_grade",
            # QB components
            "accuracy": "passing_grade",
            "decision": "passing_grade",
            "pocket_presence": "passing_grade",
            # RB components
            "vision": "rushing_grade",
            "elusiveness": "rushing_grade",
            "power": "rushing_grade",
            "receiving": "receiving_grade",
            # WR/TE components
            "route_running": "receiving_grade",
            "catch": "receiving_grade",
            "yac": "receiving_grade",
            # DL components
            "pass_rush": "pass_rush_grade",
            "run_stop": "run_defense_grade",
            # LB/DB components
            "coverage": "coverage_grade",
            "tackling": "tackling_grade",
            "blitz": "pass_rush_grade",
            "run_defense": "run_defense_grade",
        }

        # Map position groups to relevant sub-grade keys (for fallback)
        position_to_grades = {
            "QB": ["passing_grade"],
            "RB": ["rushing_grade", "receiving_grade", "pass_blocking_grade"],
            "WR": ["receiving_grade", "run_blocking_grade"],
            "OL": ["pass_blocking_grade", "run_blocking_grade"],
            "DL": ["pass_rush_grade", "run_defense_grade"],
            "LB": ["coverage_grade", "tackling_grade", "pass_rush_grade", "run_defense_grade"],
            "DB": ["coverage_grade", "tackling_grade"],
        }

        relevant_keys = position_to_grades.get(position_group, [])

        if not play_grades:
            return sub_grades

        # Aggregate component grades from each play's grade_components
        component_sums = {}
        component_counts = {}

        for play_grade in play_grades:
            if play_grade.grade_components:
                for component_name, grade in play_grade.grade_components.items():
                    subgrade_key = component_to_subgrade.get(component_name)
                    if subgrade_key and subgrade_key in relevant_keys:
                        component_sums[subgrade_key] = component_sums.get(subgrade_key, 0) + grade
                        component_counts[subgrade_key] = component_counts.get(subgrade_key, 0) + 1

        # Calculate averages for each sub-grade that has data
        for key in relevant_keys:
            if key in component_sums and component_counts[key] > 0:
                sub_grades[key] = round(component_sums[key] / component_counts[key], 1)

        # Fallback: If no component grades found for a relevant key, use overall average
        # This handles cases where graders don't populate grade_components
        avg_grade = sum(g.play_grade for g in play_grades) / len(play_grades)
        for key in relevant_keys:
            if sub_grades[key] is None:
                sub_grades[key] = round(avg_grade, 1)

        return sub_grades

    def aggregate_to_season(
        self,
        game_grades: List[GameGrade],
    ) -> SeasonGrade:
        """Aggregate game grades to a season grade.

        Uses snap-weighted average across all games.
        """
        if not game_grades:
            raise ValueError("Cannot aggregate empty game grades list")

        player_id = game_grades[0].player_id
        position = game_grades[0].position
        team_id = game_grades[0].team_id
        season = game_grades[0].season

        # Calculate snap-weighted average
        total_snaps = sum(g.total_snaps for g in game_grades)
        if total_snaps > 0:
            overall_grade = sum(
                g.overall_grade * g.total_snaps for g in game_grades
            ) / total_snaps
        else:
            overall_grade = sum(g.overall_grade for g in game_grades) / len(game_grades)

        # Sum totals
        total_plays = sum(g.play_count for g in game_grades)
        total_positive = sum(g.positive_plays for g in game_grades)
        epa_total = sum(g.epa_total for g in game_grades)

        # Calculate rates
        positive_play_rate = total_positive / total_plays if total_plays > 0 else None
        epa_per_play = epa_total / total_plays if total_plays > 0 else None

        # Aggregate sub-grades (snap-weighted)
        sub_grades = self._aggregate_season_sub_grades(game_grades, total_snaps)

        return SeasonGrade(
            player_id=player_id,
            season=season,
            position=position,
            team_id=team_id,
            overall_grade=round(overall_grade, 1),
            total_snaps=total_snaps,
            games_graded=len(game_grades),
            total_plays_graded=total_plays,
            positive_play_rate=round(positive_play_rate, 3) if positive_play_rate else None,
            epa_total=round(epa_total, 2),
            epa_per_play=round(epa_per_play, 3) if epa_per_play else None,
            **sub_grades,
        )

    def _aggregate_season_sub_grades(
        self, game_grades: List[GameGrade], total_snaps: int
    ) -> Dict[str, Optional[float]]:
        """Aggregate sub-grades across games with snap weighting."""
        sub_grade_keys = [
            "passing_grade",
            "rushing_grade",
            "receiving_grade",
            "pass_blocking_grade",
            "run_blocking_grade",
            "pass_rush_grade",
            "run_defense_grade",
            "coverage_grade",
            "tackling_grade",
        ]

        result = {}
        for key in sub_grade_keys:
            grades_with_values = [
                (getattr(g, key), g.total_snaps)
                for g in game_grades
                if getattr(g, key) is not None
            ]

            if grades_with_values:
                total_weight = sum(snaps for _, snaps in grades_with_values)
                if total_weight > 0:
                    weighted_sum = sum(grade * snaps for grade, snaps in grades_with_values)
                    result[key] = round(weighted_sum / total_weight, 1)
                else:
                    result[key] = round(
                        sum(grade for grade, _ in grades_with_values) / len(grades_with_values),
                        1,
                    )
            else:
                result[key] = None

        return result


def calculate_rankings(
    season_grades: List[SeasonGrade],
    min_snaps: int = MIN_SNAPS_FOR_SEASON_RANKING,
    min_games: int = MIN_GAMES_FOR_SEASON_RANKING,
) -> List[SeasonGrade]:
    """Calculate position and overall rankings for season grades.

    Modifies grades in place and returns the list.
    """
    # Filter qualified players
    qualified = [
        g for g in season_grades
        if g.total_snaps >= min_snaps and g.games_graded >= min_games
    ]

    # Sort by overall grade for overall rankings
    qualified_sorted = sorted(qualified, key=lambda g: g.overall_grade, reverse=True)
    for rank, grade in enumerate(qualified_sorted, 1):
        grade.overall_rank = rank

    # Group by position for position rankings
    by_position: Dict[str, List[SeasonGrade]] = defaultdict(list)
    for grade in qualified:
        by_position[grade.position].append(grade)

    # Assign position ranks
    for position, grades in by_position.items():
        sorted_grades = sorted(grades, key=lambda g: g.overall_grade, reverse=True)
        for rank, grade in enumerate(sorted_grades, 1):
            grade.position_rank = rank

    return season_grades
