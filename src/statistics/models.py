"""
Statistical Data Models for The Owner's Sim

Type-safe dataclasses for all statistical queries.
Provides structured data for UI layer integration.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass(frozen=True)
class PassingStats:
    """Complete passing statistics for a player"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    games: int

    # Raw stats
    completions: int
    attempts: int
    yards: int
    touchdowns: int
    interceptions: int

    # Calculated stats
    completion_pct: float
    yards_per_attempt: float
    yards_per_game: float
    passer_rating: float

    # Rankings (optional)
    league_rank: Optional[int] = None
    conference_rank: Optional[int] = None
    division_rank: Optional[int] = None


@dataclass(frozen=True)
class RushingStats:
    """Complete rushing statistics for a player"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    games: int

    # Raw stats
    attempts: int
    yards: int
    touchdowns: int
    longest: int = 0  # Longest rush

    # Calculated stats
    yards_per_carry: float = 0.0
    yards_per_game: float = 0.0

    # Rankings (optional)
    league_rank: Optional[int] = None
    conference_rank: Optional[int] = None
    division_rank: Optional[int] = None


@dataclass(frozen=True)
class ReceivingStats:
    """Complete receiving statistics for a player"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    games: int

    # Raw stats
    receptions: int
    targets: int
    yards: int
    touchdowns: int
    longest: int = 0  # Longest reception

    # Calculated stats
    catch_rate: float = 0.0
    yards_per_reception: float = 0.0
    yards_per_target: float = 0.0
    yards_per_game: float = 0.0

    # Rankings (optional)
    league_rank: Optional[int] = None
    conference_rank: Optional[int] = None
    division_rank: Optional[int] = None


@dataclass(frozen=True)
class DefensiveStats:
    """Complete defensive statistics for a player"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    games: int

    # Raw stats
    tackles_total: int
    tackles_solo: int = 0  # Solo tackles
    tackles_assist: int = 0  # Assisted tackles
    sacks: float = 0.0
    interceptions: int = 0
    forced_fumbles: int = 0
    touchdowns: int = 0  # Defensive/return TDs

    # Rankings (optional)
    league_rank: Optional[int] = None
    conference_rank: Optional[int] = None
    division_rank: Optional[int] = None


@dataclass(frozen=True)
class SpecialTeamsStats:
    """Complete special teams statistics for a player"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    games: int

    # Raw stats
    field_goals_made: int
    field_goals_attempted: int
    extra_points_made: int
    extra_points_attempted: int

    # Calculated stats
    fg_percentage: float
    xp_percentage: float

    # Rankings (optional)
    league_rank: Optional[int] = None


@dataclass(frozen=True)
class TeamStats:
    """Aggregated team statistics"""
    team_id: int
    season: int
    dynasty_id: str

    # Offensive totals
    total_passing_yards: int
    total_rushing_yards: int
    total_points: int

    # Defensive totals
    total_points_allowed: int
    total_yards_allowed: int

    # Rankings (optional)
    offensive_rank: Optional[int] = None
    defensive_rank: Optional[int] = None


# =============================================================================
# Statistics Preservation Data Models
# =============================================================================


@dataclass
class PlayerSeasonStats:
    """
    Aggregated player statistics for a single season.

    Used by the statistics preservation system to store pre-aggregated
    season totals in the player_season_stats table. This enables fast
    career stat queries without joining across all games.
    """
    dynasty_id: str
    player_id: str
    season: int
    team_id: int
    position: str

    # Games played
    games_played: int = 0
    games_started: int = 0

    # Passing stats (aggregated from all games)
    passing_yards: int = 0
    passing_tds: int = 0
    passing_completions: int = 0
    passing_attempts: int = 0
    interceptions: int = 0

    # Rushing stats (aggregated)
    rushing_yards: int = 0
    rushing_tds: int = 0
    rushing_attempts: int = 0

    # Receiving stats (aggregated)
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    targets: int = 0

    # Defense stats (aggregated)
    tackles_total: int = 0
    tackles_solo: int = 0
    tackles_assist: int = 0
    sacks: float = 0.0
    interceptions_def: int = 0
    forced_fumbles: int = 0
    defensive_tds: int = 0

    # Special teams stats (aggregated)
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    extra_points_made: int = 0
    extra_points_attempted: int = 0

    # Calculated metrics (stored for query performance)
    passer_rating: Optional[float] = None
    yards_per_carry: Optional[float] = None
    catch_rate: Optional[float] = None
    yards_per_reception: Optional[float] = None

    # Awards and honors (JSON array stored as string)
    awards: List[str] = field(default_factory=list)

    # Metadata
    created_at: Optional[datetime] = None


@dataclass
class SeasonArchive:
    """
    Metadata for an archived season.

    Stores high-level information about a completed season including
    champions, awards, and season records. Used by the statistics
    preservation system for season_archives table.
    """
    dynasty_id: str
    season: int

    # Champions
    super_bowl_champion: int  # team_id
    afc_champion: int         # team_id
    nfc_champion: int         # team_id

    # Individual awards (player_ids)
    mvp_player_id: str
    offensive_poy: str
    defensive_poy: str
    offensive_rookie_of_year: Optional[str] = None
    defensive_rookie_of_year: Optional[str] = None
    comeback_player: Optional[str] = None

    # Coach awards
    coach_of_year: Optional[int] = None  # team_id

    # Season records (JSON stored as dict)
    season_records: Dict[str, Any] = field(default_factory=dict)

    # Team records
    best_record_team_id: Optional[int] = None
    best_record_wins: Optional[int] = None
    best_record_losses: Optional[int] = None

    # Metadata
    games_played: int = 272
    archived_at: Optional[datetime] = None


@dataclass
class RetentionPolicy:
    """
    Retention policy configuration for a dynasty.

    Defines how long to keep detailed game data vs aggregated summaries.
    Used by RetentionPolicyManager to determine archival behavior.
    """
    dynasty_id: str

    # Policy type: 'keep_all', 'keep_n_seasons', or 'summary_only'
    policy_type: str = 'keep_n_seasons'

    # Number of seasons to keep in hot storage (full detail)
    retention_seasons: int = 3

    # Whether to automatically archive on season end
    auto_archive: bool = True

    # Statistics
    last_archival_season: Optional[int] = None
    last_archival_timestamp: Optional[datetime] = None
    total_seasons_archived: int = 0

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ArchivalResult:
    """
    Result of an archival operation.

    Returned by StatisticsArchiver.archive_season() to indicate
    success/failure and provide detailed metrics.
    """
    success: bool
    season: int

    # Metrics
    player_stats_aggregated: int = 0
    game_stats_archived: int = 0
    games_archived: int = 0

    # Validation
    validation_passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Performance
    duration_seconds: float = 0.0

    # Timestamp
    archived_at: Optional[datetime] = None


@dataclass
class ValidationResult:
    """
    Result of a validation check.

    Used by ArchivalValidator to report validation status with
    detailed error messages and warnings.
    """
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
