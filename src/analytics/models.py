"""
Analytics Data Models

Dataclasses for player grades and advanced metrics, providing type-safe
structures for the PFF-style grading system.

Grade Scale:
- 90-100: Elite (top 5% of plays)
- 80-89: Above Average (positive contribution)
- 60-79: Neutral (expected performance)
- 40-59: Below Average (negative contribution)
- 0-39: Poor (significant negative impact)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class PlayContext:
    """Context information for grading a single play."""

    game_id: str
    play_number: int
    quarter: int  # 1-5 (5 = OT)
    down: int  # 1-4
    distance: int  # Yards to go
    yard_line: int  # 1-99 (own 1 to opponent 1)
    game_clock: int  # Seconds remaining in quarter
    score_differential: int  # Positive = player's team leading
    play_type: str  # 'pass', 'run', 'field_goal', 'punt', 'kickoff'
    is_offense: bool  # True for offensive players


@dataclass
class PlayGrade:
    """Per-play grade for a single player."""

    player_id: int
    game_id: str
    play_number: int
    position: str
    team_id: int

    # Core grade (0-100, 60 = neutral)
    play_grade: float

    # Position-specific sub-component grades
    # Keys vary by position (e.g., 'accuracy', 'decision' for QB)
    grade_components: Dict[str, float] = field(default_factory=dict)

    # Play context (stored for reference)
    context: Optional[PlayContext] = None

    # Play outcome
    was_positive_play: bool = False  # True if grade >= 70
    epa_contribution: float = 0.0  # Expected Points Added

    # Track if player was on offense (stored directly to avoid context sharing bug)
    is_offense: bool = False

    def __post_init__(self):
        """Ensure grade is within bounds."""
        self.play_grade = max(0.0, min(100.0, self.play_grade))
        self.was_positive_play = self.play_grade >= 70.0


@dataclass
class GameGrade:
    """Game-aggregated grade for a player."""

    player_id: int
    game_id: str
    season: int
    week: int
    position: str
    team_id: int

    # Overall game grade (weighted average of play grades)
    overall_grade: float

    # Position-specific sub-grades (None if not applicable)
    passing_grade: Optional[float] = None
    rushing_grade: Optional[float] = None
    receiving_grade: Optional[float] = None
    pass_blocking_grade: Optional[float] = None
    run_blocking_grade: Optional[float] = None
    pass_rush_grade: Optional[float] = None
    run_defense_grade: Optional[float] = None
    coverage_grade: Optional[float] = None
    tackling_grade: Optional[float] = None

    # Snap counts
    offensive_snaps: int = 0
    defensive_snaps: int = 0
    special_teams_snaps: int = 0

    # Advanced metrics for this game
    epa_total: float = 0.0
    success_rate: Optional[float] = None  # 0.0-1.0

    # Play tracking
    play_count: int = 0
    positive_plays: int = 0
    negative_plays: int = 0

    @property
    def total_snaps(self) -> int:
        """Total snaps played in the game."""
        return self.offensive_snaps + self.defensive_snaps + self.special_teams_snaps

    @property
    def positive_play_rate(self) -> Optional[float]:
        """Percentage of plays that were positive (grade >= 70)."""
        if self.play_count == 0:
            return None
        return self.positive_plays / self.play_count

    def __post_init__(self):
        """Ensure grade is within bounds."""
        self.overall_grade = max(0.0, min(100.0, self.overall_grade))


@dataclass
class SeasonGrade:
    """Season-aggregated grade with rankings."""

    player_id: int
    season: int
    position: str
    team_id: int

    # Overall season grade (snap-weighted average of game grades)
    overall_grade: float

    # Position-specific season grades
    passing_grade: Optional[float] = None
    rushing_grade: Optional[float] = None
    receiving_grade: Optional[float] = None
    pass_blocking_grade: Optional[float] = None
    run_blocking_grade: Optional[float] = None
    pass_rush_grade: Optional[float] = None
    run_defense_grade: Optional[float] = None
    coverage_grade: Optional[float] = None
    tackling_grade: Optional[float] = None

    # Season totals
    total_snaps: int = 0
    games_graded: int = 0
    total_plays_graded: int = 0
    positive_play_rate: Optional[float] = None  # 0.0-1.0

    # EPA metrics
    epa_total: float = 0.0
    epa_per_play: Optional[float] = None

    # Rankings (calculated after all games)
    position_rank: Optional[int] = None  # Rank among same position
    overall_rank: Optional[int] = None  # Rank among all players

    def __post_init__(self):
        """Ensure grade is within bounds."""
        self.overall_grade = max(0.0, min(100.0, self.overall_grade))


@dataclass
class AdvancedMetrics:
    """Advanced metrics for a game/team."""

    game_id: str
    team_id: int
    dynasty_id: str = ""

    # EPA (Expected Points Added)
    epa_total: float = 0.0
    epa_passing: float = 0.0
    epa_rushing: float = 0.0
    epa_per_play: Optional[float] = None

    # Success Rates (0.0-1.0)
    success_rate: Optional[float] = None
    passing_success_rate: Optional[float] = None
    rushing_success_rate: Optional[float] = None

    # Passing advanced metrics
    air_yards_total: int = 0
    yac_total: int = 0  # Yards After Catch
    completion_pct_over_expected: Optional[float] = None
    avg_time_to_throw: Optional[float] = None  # Seconds
    pressure_rate: Optional[float] = None  # 0.0-1.0

    # Defensive advanced metrics
    pass_rush_win_rate: Optional[float] = None  # 0.0-1.0
    coverage_success_rate: Optional[float] = None  # 0.0-1.0
    missed_tackle_rate: Optional[float] = None  # 0.0-1.0
    forced_incompletions: int = 0
    qb_hits: int = 0


@dataclass
class GradeBreakdown:
    """Detailed breakdown of grade components for UI display."""

    player_id: int
    position: str
    overall_grade: float

    # Component grades with names
    components: Dict[str, float] = field(default_factory=dict)

    # Component weights (how much each matters)
    weights: Dict[str, float] = field(default_factory=dict)

    # Grade tier classification
    @property
    def tier(self) -> str:
        """Get the grade tier classification."""
        if self.overall_grade >= 90:
            return "Elite"
        elif self.overall_grade >= 80:
            return "Above Average"
        elif self.overall_grade >= 60:
            return "Average"
        elif self.overall_grade >= 40:
            return "Below Average"
        else:
            return "Poor"

    @property
    def tier_color(self) -> str:
        """Get color code for the grade tier (for UI)."""
        if self.overall_grade >= 90:
            return "#00FF00"  # Green - Elite
        elif self.overall_grade >= 80:
            return "#90EE90"  # Light green - Above Average
        elif self.overall_grade >= 60:
            return "#FFFF00"  # Yellow - Average
        elif self.overall_grade >= 40:
            return "#FFA500"  # Orange - Below Average
        else:
            return "#FF0000"  # Red - Poor


@dataclass
class PlayerGradeHistory:
    """Historical grade data for a player across multiple games/seasons."""

    player_id: int
    player_name: str
    position: str
    team_id: int

    # Recent game grades (most recent first)
    game_grades: List[GameGrade] = field(default_factory=list)

    # Season grades by year
    season_grades: Dict[int, SeasonGrade] = field(default_factory=dict)

    @property
    def current_season_grade(self) -> Optional[SeasonGrade]:
        """Get the most recent season grade."""
        if not self.season_grades:
            return None
        latest_season = max(self.season_grades.keys())
        return self.season_grades[latest_season]

    @property
    def career_average_grade(self) -> Optional[float]:
        """Calculate career average grade across all seasons."""
        if not self.season_grades:
            return None

        total_snaps = sum(sg.total_snaps for sg in self.season_grades.values())
        if total_snaps == 0:
            return None

        weighted_sum = sum(
            sg.overall_grade * sg.total_snaps for sg in self.season_grades.values()
        )
        return weighted_sum / total_snaps

    def get_grade_trend(self, num_games: int = 5) -> str:
        """Determine if player's grade is trending up, down, or stable."""
        if len(self.game_grades) < num_games:
            return "insufficient_data"

        recent = self.game_grades[:num_games]
        older = self.game_grades[num_games : num_games * 2] if len(self.game_grades) >= num_games * 2 else []

        if not older:
            return "insufficient_data"

        recent_avg = sum(g.overall_grade for g in recent) / len(recent)
        older_avg = sum(g.overall_grade for g in older) / len(older)

        diff = recent_avg - older_avg
        if diff > 3:
            return "trending_up"
        elif diff < -3:
            return "trending_down"
        else:
            return "stable"
