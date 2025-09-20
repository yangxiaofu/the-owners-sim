"""
Constants package for NFL simulation

Contains various constants used throughout the simulation system.
"""

from .team_ids import TeamIDs, PopularTeams
from .player_stats_fields import (
    PlayerStatField, StatCategory,
    OFFENSIVE_STATS, DEFENSIVE_STATS, SPECIAL_TEAMS_STATS, ALL_STAT_FIELDS,
    validate_player_stats_dict, migrate_legacy_field_name
)

__all__ = [
    'TeamIDs',
    'PopularTeams',
    'PlayerStatField',
    'StatCategory',
    'OFFENSIVE_STATS',
    'DEFENSIVE_STATS',
    'SPECIAL_TEAMS_STATS',
    'ALL_STAT_FIELDS',
    'validate_player_stats_dict',
    'migrate_legacy_field_name'
]