"""
Database Record Models

Value objects representing database records for different table types.
Immutable objects that match database schema structure.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, date


@dataclass(frozen=True)
class PlayerGameStatsRecord:
    """
    Database record for player game statistics.

    Matches the structure of the player_game_stats table
    with comprehensive statistics including new O-line fields.
    """

    # Required fields
    dynasty_id: str
    game_id: str
    player_id: str
    player_name: str
    team_id: int
    position: str

    # Passing stats
    passing_yards: int = 0
    passing_tds: int = 0
    passing_attempts: int = 0
    passing_completions: int = 0
    passing_interceptions: int = 0
    passing_sacks: int = 0
    passing_sack_yards: int = 0
    passing_rating: float = 0.0

    # Rushing stats
    rushing_yards: int = 0
    rushing_tds: int = 0
    rushing_attempts: int = 0
    rushing_long: int = 0
    rushing_fumbles: int = 0

    # Receiving stats
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    targets: int = 0
    receiving_long: int = 0
    receiving_drops: int = 0

    # Defensive stats
    tackles_total: int = 0
    tackles_solo: int = 0
    tackles_assist: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    forced_fumbles: int = 0
    fumbles_recovered: int = 0
    passes_defended: int = 0

    # Special teams stats
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    extra_points_made: int = 0
    extra_points_attempted: int = 0
    punts: int = 0
    punt_yards: int = 0

    # Comprehensive Offensive Line stats (NEW)
    pancakes: int = 0
    sacks_allowed: int = 0
    hurries_allowed: int = 0
    pressures_allowed: int = 0
    run_blocking_grade: float = 0.0
    pass_blocking_efficiency: float = 0.0
    missed_assignments: int = 0
    holding_penalties: int = 0
    false_start_penalties: int = 0
    downfield_blocks: int = 0
    double_team_blocks: int = 0
    chip_blocks: int = 0

    # Performance metrics
    fantasy_points: float = 0.0
    snap_counts_offense: int = 0
    snap_counts_defense: int = 0
    snap_counts_special_teams: int = 0

    def to_database_dict(self) -> Dict[str, Any]:
        """
        Convert record to dictionary format for database insertion.

        Returns:
            Dictionary with field names as keys
        """
        return {
            'dynasty_id': self.dynasty_id,
            'game_id': self.game_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,

            # Passing
            'passing_yards': self.passing_yards,
            'passing_tds': self.passing_tds,
            'passing_attempts': self.passing_attempts,
            'passing_completions': self.passing_completions,
            'passing_interceptions': self.passing_interceptions,
            'passing_sacks': self.passing_sacks,
            'passing_sack_yards': self.passing_sack_yards,
            'passing_rating': self.passing_rating,

            # Rushing
            'rushing_yards': self.rushing_yards,
            'rushing_tds': self.rushing_tds,
            'rushing_attempts': self.rushing_attempts,
            'rushing_long': self.rushing_long,
            'rushing_fumbles': self.rushing_fumbles,

            # Receiving
            'receiving_yards': self.receiving_yards,
            'receiving_tds': self.receiving_tds,
            'receptions': self.receptions,
            'targets': self.targets,
            'receiving_long': self.receiving_long,
            'receiving_drops': self.receiving_drops,

            # Defensive
            'tackles_total': self.tackles_total,
            'tackles_solo': self.tackles_solo,
            'tackles_assist': self.tackles_assist,
            'sacks': self.sacks,
            'interceptions': self.interceptions,
            'forced_fumbles': self.forced_fumbles,
            'fumbles_recovered': self.fumbles_recovered,
            'passes_defended': self.passes_defended,

            # Special teams
            'field_goals_made': self.field_goals_made,
            'field_goals_attempted': self.field_goals_attempted,
            'extra_points_made': self.extra_points_made,
            'extra_points_attempted': self.extra_points_attempted,
            'punts': self.punts,
            'punt_yards': self.punt_yards,

            # Comprehensive O-line stats
            'pancakes': self.pancakes,
            'sacks_allowed': self.sacks_allowed,
            'hurries_allowed': self.hurries_allowed,
            'pressures_allowed': self.pressures_allowed,
            'run_blocking_grade': self.run_blocking_grade,
            'pass_blocking_efficiency': self.pass_blocking_efficiency,
            'missed_assignments': self.missed_assignments,
            'holding_penalties': self.holding_penalties,
            'false_start_penalties': self.false_start_penalties,
            'downfield_blocks': self.downfield_blocks,
            'double_team_blocks': self.double_team_blocks,
            'chip_blocks': self.chip_blocks,

            # Performance
            'fantasy_points': self.fantasy_points,
            'snap_counts_offense': self.snap_counts_offense,
            'snap_counts_defense': self.snap_counts_defense,
            'snap_counts_special_teams': self.snap_counts_special_teams
        }

    def is_offensive_lineman(self) -> bool:
        """Check if this player is an offensive lineman."""
        o_line_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']
        return self.position.lower() in o_line_positions

    def has_offensive_line_stats(self) -> bool:
        """Check if this record has any offensive line statistics."""
        return (self.pancakes > 0 or self.sacks_allowed > 0 or
                self.hurries_allowed > 0 or self.pressures_allowed > 0 or
                self.run_blocking_grade > 0 or self.pass_blocking_efficiency > 0)


@dataclass(frozen=True)
class TeamGameStatsRecord:
    """
    Database record for team game statistics.

    Aggregated team-level statistics for a single game.
    """

    dynasty_id: str
    game_id: str
    team_id: int

    # Offensive totals
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    first_downs: int = 0
    third_down_conversions: int = 0
    third_down_attempts: int = 0
    red_zone_conversions: int = 0
    red_zone_attempts: int = 0

    # Turnovers
    turnovers: int = 0
    interceptions_thrown: int = 0
    fumbles_lost: int = 0

    # Defensive totals
    sacks: float = 0.0
    tackles_for_loss: int = 0
    interceptions: int = 0
    forced_fumbles: int = 0
    passes_defended: int = 0

    # Special teams
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    punts: int = 0
    punt_average: float = 0.0

    # Game flow
    time_of_possession_seconds: int = 0
    penalties: int = 0
    penalty_yards: int = 0

    def to_database_dict(self) -> Dict[str, Any]:
        """
        Convert record to dictionary format for database insertion.

        Returns:
            Dictionary with field names as keys
        """
        return {
            'dynasty_id': self.dynasty_id,
            'game_id': self.game_id,
            'team_id': self.team_id,
            'total_yards': self.total_yards,
            'passing_yards': self.passing_yards,
            'rushing_yards': self.rushing_yards,
            'first_downs': self.first_downs,
            'third_down_conversions': self.third_down_conversions,
            'third_down_attempts': self.third_down_attempts,
            'red_zone_conversions': self.red_zone_conversions,
            'red_zone_attempts': self.red_zone_attempts,
            'turnovers': self.turnovers,
            'interceptions_thrown': self.interceptions_thrown,
            'fumbles_lost': self.fumbles_lost,
            'sacks': self.sacks,
            'tackles_for_loss': self.tackles_for_loss,
            'interceptions': self.interceptions,
            'forced_fumbles': self.forced_fumbles,
            'passes_defended': self.passes_defended,
            'field_goals_made': self.field_goals_made,
            'field_goals_attempted': self.field_goals_attempted,
            'punts': self.punts,
            'punt_average': self.punt_average,
            'time_of_possession_seconds': self.time_of_possession_seconds,
            'penalties': self.penalties,
            'penalty_yards': self.penalty_yards
        }


@dataclass(frozen=True)
class GameContextRecord:
    """
    Database record for game context information.

    Metadata about the game itself for persistence operations.
    """

    dynasty_id: str
    game_id: str
    away_team_id: int
    home_team_id: int
    game_date: date
    week: int
    season_type: str
    away_score: int
    home_score: int
    winning_team_id: Optional[int] = None
    total_plays: int = 0
    game_duration_minutes: int = 0
    created_at: datetime = None

    def __post_init__(self):
        """Set created_at if not provided."""
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now())

    def to_database_dict(self) -> Dict[str, Any]:
        """
        Convert record to dictionary format for database insertion.

        Returns:
            Dictionary with field names as keys
        """
        return {
            'dynasty_id': self.dynasty_id,
            'game_id': self.game_id,
            'away_team_id': self.away_team_id,
            'home_team_id': self.home_team_id,
            'game_date': self.game_date.isoformat(),
            'week': self.week,
            'season_type': self.season_type,
            'away_score': self.away_score,
            'home_score': self.home_score,
            'winning_team_id': self.winning_team_id,
            'total_plays': self.total_plays,
            'game_duration_minutes': self.game_duration_minutes,
            'created_at': self.created_at.isoformat()
        }