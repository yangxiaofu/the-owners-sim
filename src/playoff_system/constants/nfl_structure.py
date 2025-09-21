"""
NFL Structure Constants

Single source of truth for NFL organizational structure including divisions,
conferences, and team mappings. Used throughout the playoff system to ensure
consistency and eliminate duplication.
"""

from typing import Dict, List, Optional

# Core NFL constants
TOTAL_NFL_TEAMS = 32
TEAMS_PER_CONFERENCE = 16
TEAMS_PER_DIVISION = 4
TOTAL_DIVISIONS = 8

# NFL Division Structure - Single Source of Truth
# Team IDs 1-16 are AFC, 17-32 are NFC
NFL_DIVISIONS = {
    'AFC_EAST': [1, 2, 3, 4],        # Buffalo, Miami, New England, New York Jets
    'AFC_NORTH': [5, 6, 7, 8],       # Baltimore, Cincinnati, Cleveland, Pittsburgh
    'AFC_SOUTH': [9, 10, 11, 12],    # Houston, Indianapolis, Jacksonville, Tennessee
    'AFC_WEST': [13, 14, 15, 16],    # Denver, Kansas City, Las Vegas, Los Angeles Chargers
    'NFC_EAST': [17, 18, 19, 20],    # Dallas, New York Giants, Philadelphia, Washington
    'NFC_NORTH': [21, 22, 23, 24],   # Chicago, Detroit, Green Bay, Minnesota
    'NFC_SOUTH': [25, 26, 27, 28],   # Atlanta, Carolina, New Orleans, Tampa Bay
    'NFC_WEST': [29, 30, 31, 32]     # Arizona, Los Angeles Rams, San Francisco, Seattle
}

# NFL Conference Structure
NFL_CONFERENCES = {
    'AFC': list(range(1, 17)),      # Teams 1-16
    'NFC': list(range(17, 33))      # Teams 17-32
}

# Reverse mappings for quick lookups
_TEAM_TO_DIVISION = {}
_TEAM_TO_CONFERENCE = {}

# Build reverse mappings
for division_name, team_ids in NFL_DIVISIONS.items():
    conference = 'AFC' if division_name.startswith('AFC') else 'NFC'
    for team_id in team_ids:
        _TEAM_TO_DIVISION[team_id] = division_name
        _TEAM_TO_CONFERENCE[team_id] = conference


def get_team_conference(team_id: int) -> Optional[str]:
    """
    Get the conference (AFC/NFC) for a team ID.

    Args:
        team_id: NFL team ID (1-32)

    Returns:
        Conference name ('AFC' or 'NFC'), or None if invalid team_id
    """
    if not (1 <= team_id <= TOTAL_NFL_TEAMS):
        return None
    return _TEAM_TO_CONFERENCE.get(team_id)


def get_team_division(team_id: int) -> Optional[str]:
    """
    Get the division for a team ID.

    Args:
        team_id: NFL team ID (1-32)

    Returns:
        Division name (e.g., 'AFC_EAST'), or None if invalid team_id
    """
    if not (1 <= team_id <= TOTAL_NFL_TEAMS):
        return None
    return _TEAM_TO_DIVISION.get(team_id)


def get_division_teams(division_name: str) -> List[int]:
    """
    Get all team IDs in a division.

    Args:
        division_name: Division name (e.g., 'AFC_EAST')

    Returns:
        List of team IDs in the division, empty list if invalid division
    """
    return NFL_DIVISIONS.get(division_name, [])


def get_conference_teams(conference_name: str) -> List[int]:
    """
    Get all team IDs in a conference.

    Args:
        conference_name: Conference name ('AFC' or 'NFC')

    Returns:
        List of team IDs in the conference, empty list if invalid conference
    """
    return NFL_CONFERENCES.get(conference_name, [])


def get_division_rivals(team_id: int) -> List[int]:
    """
    Get division rivals for a team (other teams in same division).

    Args:
        team_id: NFL team ID (1-32)

    Returns:
        List of rival team IDs (excludes the input team)
    """
    division = get_team_division(team_id)
    if not division:
        return []

    division_teams = get_division_teams(division)
    return [rival_id for rival_id in division_teams if rival_id != team_id]


def get_conference_rivals(team_id: int) -> List[int]:
    """
    Get conference rivals for a team (other teams in same conference).

    Args:
        team_id: NFL team ID (1-32)

    Returns:
        List of conference rival team IDs (excludes the input team)
    """
    conference = get_team_conference(team_id)
    if not conference:
        return []

    conference_teams = get_conference_teams(conference)
    return [rival_id for rival_id in conference_teams if rival_id != team_id]


def validate_team_id(team_id: int) -> bool:
    """
    Validate that a team ID is within valid NFL range.

    Args:
        team_id: Team ID to validate

    Returns:
        True if valid (1-32), False otherwise
    """
    return 1 <= team_id <= TOTAL_NFL_TEAMS


def get_all_team_ids() -> List[int]:
    """
    Get all valid NFL team IDs.

    Returns:
        List of all team IDs (1-32)
    """
    return list(range(1, TOTAL_NFL_TEAMS + 1))


# Division name variants for compatibility with different naming conventions
DIVISION_NAME_VARIANTS = {
    # Primary format (with underscores)
    'AFC_EAST': 'AFC_EAST',
    'AFC_NORTH': 'AFC_NORTH',
    'AFC_SOUTH': 'AFC_SOUTH',
    'AFC_WEST': 'AFC_WEST',
    'NFC_EAST': 'NFC_EAST',
    'NFC_NORTH': 'NFC_NORTH',
    'NFC_SOUTH': 'NFC_SOUTH',
    'NFC_WEST': 'NFC_WEST',

    # Alternative format (with spaces)
    'AFC East': 'AFC_EAST',
    'AFC North': 'AFC_NORTH',
    'AFC South': 'AFC_SOUTH',
    'AFC West': 'AFC_WEST',
    'NFC East': 'NFC_EAST',
    'NFC North': 'NFC_NORTH',
    'NFC South': 'NFC_SOUTH',
    'NFC West': 'NFC_WEST'
}


def normalize_division_name(division_name: str) -> Optional[str]:
    """
    Normalize division name to standard format.

    Args:
        division_name: Division name in any supported format

    Returns:
        Normalized division name, or None if not recognized
    """
    return DIVISION_NAME_VARIANTS.get(division_name)