"""
NFL Position Abbreviations and Display Names

Provides mapping from database/JSON position names (underscore format) to
standard NFL position abbreviations for UI display.

Also provides position aliases for formation-based snap tracking, allowing
generic positions (e.g., 'linebacker') to fill specific formation slots
(e.g., 'mike_linebacker', 'sam_linebacker').

Usage:
    from constants.position_abbreviations import get_position_abbreviation, POSITION_ALIASES

    position = "wide_receiver"
    abbrev = get_position_abbreviation(position)  # Returns "WR"
"""

from typing import Dict, List
from constants.position_normalizer import normalize_position

# Position abbreviation mapping (underscore format → NFL abbreviation)
POSITION_ABBREVIATIONS = {
    # Offense - Skill Positions
    "quarterback": "QB",
    "running_back": "RB",
    "fullback": "FB",
    "wide_receiver": "WR",
    "tight_end": "TE",

    # Offensive Line
    "left_tackle": "LT",
    "left_guard": "LG",
    "center": "C",
    "right_guard": "RG",
    "right_tackle": "RT",
    "tackle": "T",
    "guard": "G",
    "offensive_line": "OL",
    "offensive_guard": "OG",
    "offensive_tackle": "OT",

    # Defensive Line
    "defensive_end": "DE",
    "defensive_tackle": "DT",
    "nose_tackle": "NT",

    # Linebackers
    "linebacker": "LB",
    "middle_linebacker": "MLB",
    "inside_linebacker": "ILB",
    "outside_linebacker": "OLB",
    "weak_side_linebacker": "WIL",
    "strong_side_linebacker": "SAM",
    "mike_linebacker": "MIKE",
    "will_linebacker": "WILL",
    "sam_linebacker": "SAM",

    # Secondary
    "cornerback": "CB",
    "nickel_cornerback": "NCB",
    "safety": "S",
    "free_safety": "FS",
    "strong_safety": "SS",

    # Special Teams
    "kicker": "K",
    "punter": "P",
    "long_snapper": "LS",
    "kick_returner": "KR",
    "punt_returner": "PR",
}


def get_position_abbreviation(position: str) -> str:
    """
    Get standard NFL abbreviation for a position.

    Args:
        position: Position name in underscore format (e.g., "wide_receiver")

    Returns:
        Standard NFL abbreviation (e.g., "WR")
        If position not found, returns uppercase version of input

    Examples:
        >>> get_position_abbreviation("quarterback")
        'QB'
        >>> get_position_abbreviation("wide_receiver")
        'WR'
        >>> get_position_abbreviation("linebacker")
        'LB'
        >>> get_position_abbreviation("unknown_position")
        'UNKNOWN_POSITION'
    """
    return POSITION_ABBREVIATIONS.get(normalize_position(position), position.upper())


# =============================================================================
# POSITION ALIASES FOR FORMATION-BASED SNAP TRACKING
# =============================================================================
#
# These aliases allow generic positions (e.g., 'linebacker') to fill specific
# formation slots (e.g., 'mike_linebacker', 'sam_linebacker'). This is needed
# because player rosters often use generic positions while defensive formations
# require specific positions.
#
# Example: A player with position 'linebacker' can fill any of the LB slots
# in a 4-3 defense (mike_linebacker, sam_linebacker, will_linebacker).

POSITION_ALIASES: Dict[str, List[str]] = {
    # Generic LB can fill any LB slot (4-3 or 3-4 schemes)
    'linebacker': [
        'mike_linebacker', 'sam_linebacker', 'will_linebacker',
        'inside_linebacker', 'outside_linebacker'
    ],
    # Inside LB can fill MIKE or ILB slots
    'inside_linebacker': ['mike_linebacker', 'inside_linebacker'],
    # Middle LB is same as MIKE
    'middle_linebacker': ['mike_linebacker'],
    # Outside LB can fill SAM, WILL, or OLB slots
    'outside_linebacker': ['sam_linebacker', 'will_linebacker', 'outside_linebacker'],
    # Generic safety can fill FS or SS
    'safety': ['free_safety', 'strong_safety'],
    # Generic DL can fill DE or DT
    'defensive_lineman': ['defensive_end', 'defensive_tackle'],
    # Generic DB can fill CB or safety
    'defensive_back': ['cornerback', 'free_safety', 'strong_safety'],
}


def get_position_limit_with_aliases(
    position: str,
    personnel: Dict[str, int],
    position_counts: Dict[str, int]
) -> tuple:
    """
    Get the available slots for a position, checking aliases if direct match not found.

    Args:
        position: The player's position
        personnel: Formation personnel requirements (position -> count)
        position_counts: Current counts of positions filled

    Returns:
        Tuple of (limit, tracking_position) where:
        - limit: The number of slots available for this position type
        - tracking_position: The position key to use for counting (may be an alias)

    Examples:
        >>> personnel = {'mike_linebacker': 1, 'sam_linebacker': 1, 'will_linebacker': 1}
        >>> counts = {}
        >>> get_position_limit_with_aliases('linebacker', personnel, counts)
        (1, 'mike_linebacker')  # First available LB slot
    """
    # First try direct match
    if position in personnel:
        return (personnel.get(position, 0), position)

    # Try aliases - find first alias with available slots
    for alias in POSITION_ALIASES.get(position, []):
        if alias in personnel:
            alias_limit = personnel.get(alias, 0)
            alias_count = position_counts.get(alias, 0)
            if alias_count < alias_limit:
                return (alias_limit, alias)

    # No match found
    return (0, position)
