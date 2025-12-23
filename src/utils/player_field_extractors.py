"""
Player Field Extraction Utilities

Centralized utilities for extracting fields from player dictionaries.
Handles inconsistencies between database rows and transformed dicts.

Usage:
    from utils.player_field_extractors import extract_primary_position

    position = extract_primary_position(player.get("positions"))
"""

import json
from typing import Any, Optional


def extract_primary_position(
    positions: Any,
    default: str = "",
    uppercase: bool = False
) -> str:
    """
    Extract primary position from database positions field.

    Handles multiple formats:
    - JSON string: '["quarterback"]' -> "quarterback"
    - Python list: ["quarterback"] -> "quarterback"
    - Already extracted string: "quarterback" -> "quarterback"
    - None/empty: "" or default

    Args:
        positions: Can be JSON string, list, string, or None
        default: Default value if extraction fails (default: "")
        uppercase: Whether to uppercase the result (default: False)

    Returns:
        Primary position abbreviation (e.g., "quarterback", "QB")

    Examples:
        >>> extract_primary_position(["quarterback"])
        'quarterback'
        >>> extract_primary_position('["QB"]', uppercase=True)
        'QB'
        >>> extract_primary_position(None, default="WR")
        'WR'
        >>> extract_primary_position("quarterback")
        'quarterback'
    """
    # Handle None/empty
    if not positions:
        return default

    # If already a string (not JSON), return it
    if isinstance(positions, str):
        # Try to parse as JSON first
        if positions.startswith('[') or positions.startswith('{'):
            try:
                positions = json.loads(positions)
            except (json.JSONDecodeError, TypeError, ValueError):
                # Not valid JSON, treat as plain string
                result = positions if positions else default
                return result.upper() if uppercase and result else result
        else:
            # Plain string, not JSON
            result = positions if positions else default
            return result.upper() if uppercase and result else result

    # If list, get first position
    if isinstance(positions, list) and len(positions) > 0:
        result = positions[0] if positions[0] else default
        return result.upper() if uppercase and result else result

    return default


def extract_overall_rating(
    player: dict,
    default: int = 70
) -> int:
    """
    Extract overall rating from player dict.

    Handles multiple formats:
    - Top-level "overall": {"overall": 85} -> 85
    - Top-level "overall_rating": {"overall_rating": 85} -> 85
    - Nested in attributes: {"attributes": {"overall": 85}} -> 85
    - Nested in JSON string: {"attributes": '{"overall": 85}'} -> 85

    Args:
        player: Player dictionary
        default: Default value if extraction fails (default: 70)

    Returns:
        Overall rating (integer)

    Examples:
        >>> extract_overall_rating({"overall": 85})
        85
        >>> extract_overall_rating({"overall_rating": 90})
        90
        >>> extract_overall_rating({"attributes": {"overall": 88}})
        88
        >>> extract_overall_rating({}, default=75)
        75
    """
    # Check top-level fields first (most common in transformed dicts)
    if "overall" in player:
        overall = player["overall"]
        return int(overall) if overall is not None else default

    if "overall_rating" in player:
        overall = player["overall_rating"]
        return int(overall) if overall is not None else default

    # Check in attributes (database row format)
    attributes = player.get("attributes")
    if not attributes:
        return default

    # If attributes is a JSON string, parse it
    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except (json.JSONDecodeError, TypeError, ValueError):
            return default

    # Extract overall from attributes dict
    if isinstance(attributes, dict):
        overall = attributes.get("overall")
        return int(overall) if overall is not None else default

    return default
