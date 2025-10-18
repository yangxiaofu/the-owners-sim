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

    # Calculated stats
    yards_per_carry: float
    yards_per_game: float

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

    # Calculated stats
    catch_rate: float
    yards_per_reception: float
    yards_per_target: float
    yards_per_game: float

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
    sacks: float
    interceptions: int

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
