"""
Statistical Data Models for The Owner's Sim

Type-safe dataclasses for all statistical queries.
Provides structured data for UI layer integration.
"""
from dataclasses import dataclass
from typing import Optional


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
