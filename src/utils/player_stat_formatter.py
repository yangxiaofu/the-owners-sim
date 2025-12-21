"""
Centralized Player Stats Formatter

Provides consistent stat formatting across the entire application.
Eliminates 18+ duplicate formatting implementations with a single source of truth.

Usage:
    from src.utils.player_stat_formatter import format_player_stats, StatFormatStyle, CaseStyle

    # Compact lowercase (default)
    format_player_stats({"passing_yards": 287, "passing_tds": 2}, "QB")
    # Returns: "287 yds, 2 TD, 0 INT"

    # Uppercase for UI
    format_player_stats({"tackles_total": 12, "sacks": 2.5}, "LB", case=CaseStyle.UPPERCASE)
    # Returns: "12 TKL, 2.5 SK"
"""

from enum import Enum
from typing import Dict, Any, List, Optional


class StatFormatStyle(Enum):
    """Formatting style for stat display."""
    COMPACT = "compact"     # "287 yds, 2 TD"
    VERBOSE = "verbose"     # "287 passing yards, 2 touchdowns"
    NATURAL = "natural"     # "2 TDs, 287 yards" (natural word order)
    CAREER = "career"       # Multi-line format for career stats


class CaseStyle(Enum):
    """Case style for stat abbreviations."""
    LOWERCASE = "lowercase"  # "yds", "td", "tkl"
    UPPERCASE = "uppercase"  # "YDS", "TD", "TKL"
    TITLE = "title"         # "Yds", "Td", "Tkl"


# Position-to-Stats Mapping: Which stats to display for each position
POSITION_STAT_MAPPING = {
    # Offense - Skill Positions
    "QB": ["passing_yards", "passing_tds", "passing_interceptions", "rushing_yards"],
    "RB": ["rushing_yards", "rushing_tds", "receptions", "receiving_yards"],
    "FB": ["rushing_yards", "rushing_tds", "receptions", "receiving_yards"],
    "WR": ["receptions", "receiving_yards", "receiving_tds"],
    "TE": ["receptions", "receiving_yards", "receiving_tds"],

    # Defensive Line
    "DE": ["tackles_total", "sacks", "forced_fumbles"],
    "DT": ["tackles_total", "sacks", "forced_fumbles"],
    "NT": ["tackles_total", "sacks", "forced_fumbles"],

    # Linebackers
    "LB": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "MLB": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "ILB": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "OLB": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "MIKE": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "WILL": ["tackles_total", "sacks", "interceptions", "passes_defended"],
    "SAM": ["tackles_total", "sacks", "interceptions", "passes_defended"],

    # Secondary
    "CB": ["tackles_total", "interceptions", "passes_defended"],
    "NCB": ["tackles_total", "interceptions", "passes_defended"],
    "S": ["tackles_total", "interceptions", "passes_defended"],
    "FS": ["tackles_total", "interceptions", "passes_defended"],
    "SS": ["tackles_total", "interceptions", "passes_defended"],

    # Special Teams
    "K": ["field_goals_made", "field_goals_attempted", "extra_points_made"],
    "P": ["punts", "punt_average", "punts_inside_20"],
    "LS": ["snaps"],
    "KR": ["kick_returns", "kick_return_yards", "kick_return_tds"],
    "PR": ["punt_returns", "punt_return_yards", "punt_return_tds"],
}


# Stat Label Mappings: How to display each stat in different formats
STAT_LABELS = {
    # Passing
    "passing_yards": {
        "compact": {"lower": "yds", "upper": "YDS", "title": "Yds"},
        "verbose": {"singular": "passing yard", "plural": "passing yards"},
    },
    "passing_tds": {
        "compact": {"lower": "TD", "upper": "TD", "title": "TD"},
        "verbose": {"singular": "TD", "plural": "TDs"},
    },
    "passing_interceptions": {
        "compact": {"lower": "INT", "upper": "INT", "title": "INT"},
        "verbose": {"singular": "INT", "plural": "INTs"},
    },

    # Rushing
    "rushing_yards": {
        "compact": {"lower": "yds", "upper": "YDS", "title": "Yds"},
        "verbose": {"singular": "rushing yard", "plural": "rushing yards"},
    },
    "rushing_tds": {
        "compact": {"lower": "TD", "upper": "TD", "title": "TD"},
        "verbose": {"singular": "TD", "plural": "TDs"},
    },

    # Receiving
    "receptions": {
        "compact": {"lower": "rec", "upper": "REC", "title": "Rec"},
        "verbose": {"singular": "reception", "plural": "receptions"},
    },
    "receiving_yards": {
        "compact": {"lower": "yds", "upper": "YDS", "title": "Yds"},
        "verbose": {"singular": "receiving yard", "plural": "receiving yards"},
    },
    "receiving_tds": {
        "compact": {"lower": "TD", "upper": "TD", "title": "TD"},
        "verbose": {"singular": "TD", "plural": "TDs"},
    },

    # Defensive
    "tackles_total": {
        "compact": {"lower": "tkl", "upper": "TKL", "title": "Tkl"},
        "verbose": {"singular": "tackle", "plural": "tackles"},
    },
    "sacks": {
        "compact": {"lower": "sk", "upper": "SK", "title": "Sk"},
        "verbose": {"singular": "sack", "plural": "sacks"},
    },
    "interceptions": {
        "compact": {"lower": "INT", "upper": "INT", "title": "INT"},
        "verbose": {"singular": "INT", "plural": "INTs"},
    },
    "passes_defended": {
        "compact": {"lower": "PD", "upper": "PD", "title": "PD"},
        "verbose": {"singular": "pass defended", "plural": "passes defended"},
    },
    "forced_fumbles": {
        "compact": {"lower": "FF", "upper": "FF", "title": "FF"},
        "verbose": {"singular": "forced fumble", "plural": "forced fumbles"},
    },

    # Special Teams
    "field_goals_made": {
        "compact": {"lower": "FGM", "upper": "FGM", "title": "FGM"},
        "verbose": {"singular": "field goal made", "plural": "field goals made"},
    },
    "field_goals_attempted": {
        "compact": {"lower": "FGA", "upper": "FGA", "title": "FGA"},
        "verbose": {"singular": "field goal attempt", "plural": "field goal attempts"},
    },
    "extra_points_made": {
        "compact": {"lower": "XPM", "upper": "XPM", "title": "XPM"},
        "verbose": {"singular": "extra point", "plural": "extra points"},
    },
    "punts": {
        "compact": {"lower": "punts", "upper": "PUNTS", "title": "Punts"},
        "verbose": {"singular": "punt", "plural": "punts"},
    },
    "punt_average": {
        "compact": {"lower": "avg", "upper": "AVG", "title": "Avg"},
        "verbose": {"singular": "yard average", "plural": "yard average"},
    },
    "punts_inside_20": {
        "compact": {"lower": "in20", "upper": "IN20", "title": "In20"},
        "verbose": {"singular": "inside 20", "plural": "inside 20"},
    },
}


# Field Name Normalization: Handle alternate field names
DEFAULT_FIELD_MAPPING = {
    "pass_yards": "passing_yards",
    "pass_yds": "passing_yards",
    "pass_tds": "passing_tds",
    "pass_ints": "passing_interceptions",
    "rush_yards": "rushing_yards",
    "rush_yds": "rushing_yards",
    "rush_tds": "rushing_tds",
    "rec": "receptions",
    "rec_yards": "receiving_yards",
    "rec_yds": "receiving_yards",
    "rec_tds": "receiving_tds",
    "tackles": "tackles_total",
    "ints": "interceptions",
    "pd": "passes_defended",
    "ff": "forced_fumbles",
}


def normalize_stat_fields(
    stats: Dict[str, Any],
    field_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Normalize stat field names to standard format.

    Args:
        stats: Stats dictionary with possibly alternate field names
        field_mapping: Optional custom field mapping (uses DEFAULT_FIELD_MAPPING if None)

    Returns:
        Dictionary with normalized field names

    Example:
        >>> normalize_stat_fields({"pass_yards": 300})
        {"passing_yards": 300}
    """
    mapping = field_mapping or DEFAULT_FIELD_MAPPING
    normalized = {}

    for key, value in stats.items():
        # Use mapped name if available, otherwise keep original
        normalized_key = mapping.get(key, key)
        normalized[normalized_key] = value

    return normalized


def get_primary_stats_for_position(position: str) -> List[str]:
    """
    Get the primary stats to display for a position.

    Args:
        position: Position abbreviation (QB, RB, LB, etc.)

    Returns:
        List of stat field names in priority order

    Example:
        >>> get_primary_stats_for_position("QB")
        ["passing_yards", "passing_tds", "passing_interceptions", "rushing_yards"]
    """
    # Convert position to uppercase for consistency
    pos_upper = position.upper() if position else ""

    return POSITION_STAT_MAPPING.get(pos_upper, [])


def format_stat_value(
    value: Any,
    stat_name: str,
    *,
    style: StatFormatStyle,
    case: CaseStyle
) -> str:
    """
    Format a single stat value with appropriate label.

    Args:
        value: The stat value (int, float, etc.)
        stat_name: Name of the stat (e.g., "passing_yards")
        style: Formatting style
        case: Case style for abbreviations

    Returns:
        Formatted string: "287 yds" or "287 YDS" etc.
    """
    if value is None:
        return ""

    # Get label info for this stat
    label_info = STAT_LABELS.get(stat_name, {})

    if style == StatFormatStyle.COMPACT:
        # Use compact abbreviations
        case_key = case.value  # "lowercase", "uppercase", or "title"
        case_mapping = {"lowercase": "lower", "uppercase": "upper", "title": "title"}
        label_key = case_mapping[case_key]

        label = label_info.get("compact", {}).get(label_key, stat_name.upper())

        # Format sacks with 1 decimal place, others as integers
        if stat_name == "sacks" and isinstance(value, (int, float)):
            return f"{value:.1f} {label}"
        elif isinstance(value, float) and value.is_integer():
            return f"{int(value)} {label}"
        elif isinstance(value, (int, float)):
            return f"{value} {label}"
        else:
            return f"{value} {label}"

    elif style == StatFormatStyle.VERBOSE:
        # Use full words
        verbose_info = label_info.get("verbose", {})
        if value == 1:
            label = verbose_info.get("singular", stat_name)
        else:
            label = verbose_info.get("plural", stat_name)

        return f"{value} {label}"

    else:
        # Natural or career - similar to verbose for now
        return format_stat_value(value, stat_name, style=StatFormatStyle.VERBOSE, case=case)


def format_player_stats(
    stats: Dict[str, Any],
    position: str,
    *,
    style: StatFormatStyle = StatFormatStyle.COMPACT,
    case: CaseStyle = CaseStyle.LOWERCASE,
    max_stats: int = 3,
    include_zeros: bool = False,
    field_name_mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Format player stats for display based on position and style.

    Args:
        stats: Dictionary of player stats (passing_yards, tackles_total, etc.)
        position: Position abbreviation (QB, RB, WR, LB, CB, etc.)
        style: Formatting style (compact, verbose, natural, career)
        case: Case style for abbreviations (lowercase, uppercase, title)
        max_stats: Maximum number of stats to include
        include_zeros: Whether to include stats with zero values
        field_name_mapping: Optional custom field name mapping

    Returns:
        Formatted stats string

    Examples:
        >>> format_player_stats({"passing_yards": 287, "passing_tds": 2, "passing_interceptions": 0}, "QB")
        "287 yds, 2 TD, 0 INT"

        >>> format_player_stats({"tackles_total": 12, "sacks": 2.5}, "LB", case=CaseStyle.UPPERCASE)
        "12 TKL, 2.5 SK"

        >>> format_player_stats({"receptions": 8, "receiving_yards": 95, "receiving_tds": 1}, "WR")
        "8 rec, 95 yds, 1 TD"
    """
    # Normalize field names
    normalized_stats = normalize_stat_fields(stats, field_name_mapping)

    # Get primary stats for this position
    primary_stats = get_primary_stats_for_position(position)

    if not primary_stats:
        # Unknown position - return N/A or fantasy points if available
        fp = normalized_stats.get("fantasy_points", 0)
        if fp:
            return format_stat_value(fp, "fantasy_points", style=style, case=case)
        return "N/A"

    # Build formatted stat parts
    parts = []
    stats_added = 0

    for stat_name in primary_stats:
        if stats_added >= max_stats:
            break

        value = normalized_stats.get(stat_name)

        # Skip None values
        if value is None:
            continue

        # Handle zero values based on include_zeros flag
        # Special case: QB INTs and defensive stats - always show
        always_show_zero = stat_name in ["passing_interceptions", "interceptions"]

        if value == 0 and not include_zeros and not always_show_zero:
            # Skip zeros for most stats unless they're important context
            # Exception: For QB, always show INT count
            if position.upper() == "QB" and stat_name == "passing_interceptions":
                formatted = format_stat_value(value, stat_name, style=style, case=case)
                if formatted:
                    parts.append(formatted)
                    stats_added += 1
            continue

        # Special handling for conditional stats
        if stat_name == "rushing_yards" and position.upper() == "QB":
            # QB rushing yards - only show if >= 20
            if value < 20:
                continue

        if stat_name in ["receptions", "receiving_yards"] and position.upper() in ["RB", "FB"]:
            # RB/FB receiving - only show if they have receptions
            if normalized_stats.get("receptions", 0) == 0:
                continue

        # Format and add the stat
        formatted = format_stat_value(value, stat_name, style=style, case=case)
        if formatted:
            parts.append(formatted)
            stats_added += 1

    # Return formatted string or N/A if no stats
    return ", ".join(parts) if parts else "N/A"
