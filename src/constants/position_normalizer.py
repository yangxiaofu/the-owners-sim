"""
Position string normalization utilities.

Provides consistent position string normalization across the codebase.
All position lookups should use normalize_position() before dictionary/set lookups.
"""


def normalize_position(position: str) -> str:
    """
    Normalize position string to lowercase underscore format.

    Converts: "Left Tackle", "left-tackle", "LEFT_TACKLE" → "left_tackle"

    Args:
        position: Raw position string in any format

    Returns:
        Normalized position string (lowercase, underscores only)
    """
    if not position:
        return ""
    return position.lower().replace(' ', '_').replace('-', '_')