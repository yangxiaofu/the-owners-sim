"""
NFL Position Abbreviations and Display Names

Provides mapping from database/JSON position names (underscore format) to
standard NFL position abbreviations for UI display.

Usage:
    from constants.position_abbreviations import get_position_abbreviation

    position = "wide_receiver"
    abbrev = get_position_abbreviation(position)  # Returns "WR"
"""

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
    return POSITION_ABBREVIATIONS.get(position.lower(), position.upper())
