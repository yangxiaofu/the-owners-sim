"""
Playoff System Constants

Shared constants and data structures used throughout the playoff system.
Provides single source of truth for NFL structure and playoff configuration.
"""

from .nfl_structure import (
    NFL_DIVISIONS,
    NFL_CONFERENCES,
    TOTAL_NFL_TEAMS,
    TEAMS_PER_CONFERENCE,
    TEAMS_PER_DIVISION,
    get_team_conference,
    get_team_division,
    get_division_teams,
    get_conference_teams
)

from .playoff_constants import (
    PlayoffRound,
    PLAYOFF_TEAMS_PER_CONFERENCE,
    DIVISION_WINNERS_PER_CONFERENCE,
    WILD_CARD_TEAMS_PER_CONFERENCE,
    PLAYOFF_ROUNDS,
    WILD_CARD_MATCHUPS,
    TEAMS_WITH_BYES,
    GAMES_PER_ROUND,
    TEAMS_ADVANCING_PER_CONFERENCE,
    PLAYOFF_SCHEDULE_TIMING,
    HOME_FIELD_RULES,
    get_next_round,
    is_final_round
)

__all__ = [
    # NFL Structure
    'NFL_DIVISIONS',
    'NFL_CONFERENCES',
    'TOTAL_NFL_TEAMS',
    'TEAMS_PER_CONFERENCE',
    'TEAMS_PER_DIVISION',
    'get_team_conference',
    'get_team_division',
    'get_division_teams',
    'get_conference_teams',

    # Playoff Constants
    'PlayoffRound',
    'PLAYOFF_TEAMS_PER_CONFERENCE',
    'DIVISION_WINNERS_PER_CONFERENCE',
    'WILD_CARD_TEAMS_PER_CONFERENCE',
    'PLAYOFF_ROUNDS',
    'WILD_CARD_MATCHUPS',
    'TEAMS_WITH_BYES',
    'GAMES_PER_ROUND',
    'TEAMS_ADVANCING_PER_CONFERENCE',
    'PLAYOFF_SCHEDULE_TIMING',
    'HOME_FIELD_RULES',
    'get_next_round',
    'is_final_round'
]