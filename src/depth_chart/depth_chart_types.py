"""
Depth Chart Type Definitions and Constants

Defines position requirements, constraints, and type definitions for depth chart system.
"""

from typing import Dict, TypedDict


class PositionRequirement(TypedDict):
    """Position depth chart requirements."""
    minimum: int       # Minimum number of players required
    recommended: int   # Recommended number of players


# Position depth chart requirements (minimum and recommended depth)
POSITION_REQUIREMENTS: Dict[str, PositionRequirement] = {
    # Offense
    'QB': {'minimum': 1, 'recommended': 3},
    'RB': {'minimum': 2, 'recommended': 4},
    'FB': {'minimum': 1, 'recommended': 2},
    'WR': {'minimum': 3, 'recommended': 6},
    'TE': {'minimum': 1, 'recommended': 3},

    # Offensive Line
    'LT': {'minimum': 1, 'recommended': 2},
    'LG': {'minimum': 1, 'recommended': 2},
    'C': {'minimum': 1, 'recommended': 2},
    'RG': {'minimum': 1, 'recommended': 2},
    'RT': {'minimum': 1, 'recommended': 2},
    'OL': {'minimum': 0, 'recommended': 3},  # Generic O-Line (backup)

    # Defensive Line
    'DE': {'minimum': 2, 'recommended': 4},
    'DT': {'minimum': 2, 'recommended': 4},
    'NT': {'minimum': 1, 'recommended': 2},
    'DL': {'minimum': 0, 'recommended': 2},  # Generic D-Line (backup)

    # Linebackers
    'MIKE': {'minimum': 1, 'recommended': 2},
    'SAM': {'minimum': 1, 'recommended': 2},
    'WILL': {'minimum': 1, 'recommended': 2},
    'ILB': {'minimum': 1, 'recommended': 2},
    'OLB': {'minimum': 2, 'recommended': 3},
    'LB': {'minimum': 0, 'recommended': 2},  # Generic LB (backup)

    # Secondary
    'CB': {'minimum': 2, 'recommended': 5},
    'NCB': {'minimum': 1, 'recommended': 2},  # Nickel/Slot CB
    'FS': {'minimum': 1, 'recommended': 2},
    'SS': {'minimum': 1, 'recommended': 2},
    'S': {'minimum': 0, 'recommended': 1},   # Generic Safety (backup)
    'DB': {'minimum': 0, 'recommended': 1},  # Generic DB (backup)

    # Special Teams
    'K': {'minimum': 1, 'recommended': 1},
    'P': {'minimum': 1, 'recommended': 1},
    'LS': {'minimum': 1, 'recommended': 1},
    'H': {'minimum': 1, 'recommended': 1},   # Holder (usually backup QB/P)
    'KR': {'minimum': 1, 'recommended': 2},
    'PR': {'minimum': 1, 'recommended': 2},
}

# Unassigned depth chart order (default for players not on depth chart)
UNASSIGNED_DEPTH_ORDER = 99

# Position groups for categorization
OFFENSE_POSITIONS = {'QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'OL'}
DEFENSE_POSITIONS = {'DE', 'DT', 'NT', 'DL', 'MIKE', 'SAM', 'WILL', 'ILB', 'OLB', 'LB', 'CB', 'NCB', 'FS', 'SS', 'S', 'DB'}
SPECIAL_TEAMS_POSITIONS = {'K', 'P', 'LS', 'H', 'KR', 'PR'}
