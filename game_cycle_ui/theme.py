"""
UI Theme Loader - Centralized theme management for game_cycle_ui.

Loads colors and thresholds from src/config/ui_theme.json for consistent
styling across all UI components.

Usage:
    from game_cycle_ui.theme import UITheme

    # Get a color
    color = UITheme.get_color("cap_space", "healthy")  # Returns "#2E7D32"

    # Get a threshold
    threshold = UITheme.get_threshold("cap_space", "tight_percentage")  # Returns 0.10

    # Get button stylesheet
    style = UITheme.button_style("primary")
"""

import json
from pathlib import Path
from typing import Any, Optional
import logging


class UITheme:
    """
    Singleton theme manager that loads colors from ui_theme.json.

    Provides centralized access to:
    - Colors (status, cap_space, player_ratings, buttons, text, background)
    - Thresholds (cap_space, player_age, player_rating)
    - Pre-built stylesheets for common components
    """

    _instance: Optional["UITheme"] = None
    _theme_data: dict = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Load theme data if not already loaded."""
        if cls._loaded:
            return

        # Find the theme file relative to project root
        # game_cycle_ui/theme.py -> src/config/ui_theme.json
        theme_path = Path(__file__).parent.parent / "src" / "config" / "ui_theme.json"

        if not theme_path.exists():
            logging.warning(f"Theme file not found: {theme_path}. Using defaults.")
            cls._theme_data = cls._get_defaults()
            cls._loaded = True
            return

        try:
            with open(theme_path, "r") as f:
                cls._theme_data = json.load(f)
            cls._loaded = True
            logging.debug(f"Loaded UI theme: {cls._theme_data.get('name', 'unknown')}")
        except Exception as e:
            logging.error(f"Failed to load theme: {e}. Using defaults.")
            cls._theme_data = cls._get_defaults()
            cls._loaded = True

    @classmethod
    def _get_defaults(cls) -> dict:
        """Return default theme if JSON fails to load."""
        return {
            "colors": {
                "status": {
                    "success": "#2E7D32",
                    "warning": "#F57C00",
                    "error": "#C62828",
                    "info": "#1976D2",
                    "neutral": "#666666",
                    "disabled": "#CCCCCC"
                },
                "cap_space": {
                    "healthy": "#2E7D32",
                    "projected": "#1976D2",
                    "tight": "#F57C00",
                    "over_cap": "#C62828"
                },
                "buttons": {
                    "primary": "#2E7D32",
                    "primary_hover": "#1B5E20",
                    "danger": "#C62828",
                    "danger_hover": "#B71C1C",
                    "warning": "#F57C00",
                    "warning_hover": "#E65100"
                }
            },
            "thresholds": {
                "cap_space": {"tight_percentage": 0.10},
                "player_age": {"veteran": 30, "old": 33},
                "player_rating": {"elite": 85, "solid": 75, "average": 65}
            }
        }

    @classmethod
    def get_color(cls, category: str, name: str) -> str:
        """
        Get a color from the theme.

        Args:
            category: Color category (status, cap_space, player_ratings, buttons, text, background)
            name: Color name within the category

        Returns:
            Hex color string (e.g., "#2E7D32")
        """
        cls._ensure_loaded()
        colors = cls._theme_data.get("colors", {})
        return colors.get(category, {}).get(name, "#666666")

    @classmethod
    def get_threshold(cls, category: str, name: str) -> Any:
        """
        Get a threshold value from the theme.

        Args:
            category: Threshold category (cap_space, player_age, player_rating)
            name: Threshold name within the category

        Returns:
            Threshold value (int or float)
        """
        cls._ensure_loaded()
        thresholds = cls._theme_data.get("thresholds", {})
        return thresholds.get(category, {}).get(name, 0)

    @classmethod
    def button_style(cls, style_type: str = "primary") -> str:
        """
        Get a QPushButton stylesheet.

        Args:
            style_type: Button type (primary, danger, warning, secondary)

        Returns:
            CSS stylesheet string for QPushButton
        """
        cls._ensure_loaded()
        colors = cls._theme_data.get("colors", {}).get("buttons", {})

        bg = colors.get(style_type, "#2E7D32")
        hover = colors.get(f"{style_type}_hover", "#1B5E20")
        text = cls.get_color("text", "inverse")
        disabled = cls.get_color("status", "disabled")

        return (
            f"QPushButton {{ background-color: {bg}; color: {text}; "
            f"border-radius: 3px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
            f"QPushButton:disabled {{ background-color: {disabled}; }}"
        )

    @classmethod
    def label_style(cls, color_category: str, color_name: str) -> str:
        """
        Get a QLabel color stylesheet.

        Args:
            color_category: Color category
            color_name: Color name

        Returns:
            CSS stylesheet string for QLabel color
        """
        color = cls.get_color(color_category, color_name)
        return f"color: {color};"

    @classmethod
    def reload(cls) -> None:
        """Force reload the theme from disk."""
        cls._loaded = False
        cls._ensure_loaded()


# Table header style constant for consistent white text on dark background
TABLE_HEADER_STYLE = """
    QHeaderView::section {
        background-color: #1e3a5f;
        color: #ffffff;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #2c5282;
        font-weight: bold;
    }
"""

# Rivalry intensity colors (light backgrounds for table rows)
RIVALRY_INTENSITY_COLORS = {
    "legendary": "#FFCDD2",   # Light red (90-100 intensity)
    "intense": "#FFE0B2",     # Light orange (75-89)
    "competitive": "#FFF9C4", # Light yellow (50-74)
    "developing": "#C8E6C9",  # Light green (25-49)
    "mild": "#FFFFFF",        # White (1-24)
}

# Rivalry type badge colors
RIVALRY_TYPE_COLORS = {
    "division": "#1976D2",    # Blue
    "historic": "#C62828",    # Red
    "geographic": "#2E7D32",  # Green
    "recent": "#F57C00",      # Orange
}

# Primetime slot badges
PRIMETIME_BADGES = {
    "TNF": {"text": "TNF", "bg": "#4CAF50", "fg": "#FFFFFF"},  # Green
    "SNF": {"text": "SNF", "bg": "#2196F3", "fg": "#FFFFFF"},  # Blue
    "MNF": {"text": "MNF", "bg": "#F44336", "fg": "#FFFFFF"},  # Red
}

# All time slot badges (used for consistent styling in schedule view)
# Using darker background colors for better text contrast
TIME_SLOT_BADGES = {
    "TNF": {"text": "TNF", "bg": "#2E7D32", "fg": "#FFFFFF"},           # Dark green
    "SNF": {"text": "SNF", "bg": "#1565C0", "fg": "#FFFFFF"},           # Dark blue
    "MNF": {"text": "MNF", "bg": "#C62828", "fg": "#FFFFFF"},           # Dark red
    "KICKOFF": {"text": "Kickoff", "bg": "#6A1B9A", "fg": "#FFFFFF"},   # Dark purple
    "SUN_EARLY": {"text": "Sun Early", "bg": "#455A64", "fg": "#FFFFFF"},  # Dark blue-gray
    "SUN_LATE": {"text": "Sun Late", "bg": "#E65100", "fg": "#FFFFFF"},    # Dark orange
    "SUN": {"text": "Sunday", "bg": "#455A64", "fg": "#FFFFFF"},        # Dark blue-gray (fallback)
}

# Schedule view row colors (for consistency)
SCHEDULE_ROW_COLORS = {
    "background": "#FFFFFF",           # White for all rows
    "alt_background": "#F8F8F8",       # Slight alternation
    "text_primary": "#FFFFFF",         # White text for dark theme
    "text_secondary": "#E0E0E0",       # Light gray for records/@
    "score_away_win": "#81C784",       # Light green for away wins
    "score_home_win": "#64B5F6",       # Light blue for home wins
}

# Rivalry intensity symbols (replace colored backgrounds)
RIVALRY_SYMBOLS = {
    "legendary": "###",    # 90-100
    "intense": "##",       # 75-89
    "competitive": "#",    # 50-74
    "developing": "-",     # 25-49
    "mild": "",            # 1-24 (blank)
}

# =============================================================================
# MEDIA COVERAGE THEME CONSTANTS
# =============================================================================

# Sentiment colors for headlines (Milestone 12: Media Coverage)
SENTIMENT_COLORS = {
    "POSITIVE": "#2E7D32",   # Green - victories, achievements
    "NEGATIVE": "#C62828",   # Red - losses, injuries
    "NEUTRAL": "#666666",    # Gray - routine events
    "HYPE": "#F57C00",       # Orange - playoff implications, excitement
    "CRITICAL": "#7B1FA2",   # Purple - hot seat, controversies
}

# Sentiment badges/icons for headlines
SENTIMENT_BADGES = {
    "POSITIVE": "✓",
    "NEGATIVE": "!",
    "NEUTRAL": "•",
    "HYPE": "★",
    "CRITICAL": "⚠",
}

# Power rankings tier colors (background colors for tier grouping)
TIER_COLORS = {
    "ELITE": "#FFD700",      # Gold (Ranks 1-4)
    "CONTENDER": "#C0C0C0",  # Silver (Ranks 5-10)
    "PLAYOFF": "#CD7F32",    # Bronze (Ranks 11-16)
    "BUBBLE": "#4A90D9",     # Blue (Ranks 17-22)
    "REBUILDING": "#888888", # Gray (Ranks 23-32)
}

# Tier text colors (for contrast on tier backgrounds)
TIER_TEXT_COLORS = {
    "ELITE": "#000000",      # Black on gold
    "CONTENDER": "#000000",  # Black on silver
    "PLAYOFF": "#FFFFFF",    # White on bronze
    "BUBBLE": "#FFFFFF",     # White on blue
    "REBUILDING": "#FFFFFF", # White on gray
}

# Movement indicators for power rankings
MOVEMENT_COLORS = {
    "up": "#2E7D32",         # Green for rising
    "down": "#C62828",       # Red for falling
    "same": "#666666",       # Gray for unchanged
    "new": "#1976D2",        # Blue for new entry
}

# =============================================================================
# ESPN THEME CONSTANTS
# =============================================================================
# Centralized ESPN color palette used across all media coverage widgets.
# Previously duplicated in: media_coverage_view.py, breaking_news_widget.py,
# espn_headline_widget.py, power_rankings_widget.py, scoreboard_ticker_widget.py

ESPN_THEME = {
    "red": "#cc0000",
    "dark_red": "#990000",
    "dark_bg": "#0d0d0d",
    "card_bg": "#1a1a1a",
    "card_hover": "#252525",
    "text_primary": "#FFFFFF",
    "text_secondary": "#888888",
    "text_muted": "#666666",
    "border": "#333333",
}

# Convenience aliases for direct import
ESPN_RED = ESPN_THEME["red"]
ESPN_DARK_RED = ESPN_THEME["dark_red"]
ESPN_DARK_BG = ESPN_THEME["dark_bg"]
ESPN_CARD_BG = ESPN_THEME["card_bg"]
ESPN_CARD_HOVER = ESPN_THEME["card_hover"]
ESPN_TEXT_PRIMARY = ESPN_THEME["text_primary"]
ESPN_TEXT_SECONDARY = ESPN_THEME["text_secondary"]
ESPN_TEXT_MUTED = ESPN_THEME["text_muted"]
ESPN_BORDER = ESPN_THEME["border"]

# =============================================================================
# HEADLINE CATEGORIES
# =============================================================================
# Display names for headline types used in media coverage UI.

HEADLINE_CATEGORIES = {
    "GAME_RECAP": "Game Recap",
    "BLOWOUT": "Blowout Win",
    "UPSET": "Upset Alert",
    "COMEBACK": "Comeback",
    "INJURY": "Injury Report",
    "TRADE": "Trade",
    "SIGNING": "Free Agency",
    "AWARD": "Awards",
    "MILESTONE": "Milestone",
    "RUMOR": "Rumor Mill",
    "STREAK": "Streak Watch",
    "POWER_RANKING": "Power Rankings",
    "PREVIEW": "Game Preview",
    "DRAFT": "Draft",
}


def get_headline_category_display(headline_type: str) -> str:
    """
    Get display name for headline type.

    Args:
        headline_type: Raw headline type string (e.g., "GAME_RECAP")

    Returns:
        Human-readable display name (e.g., "Game Recap")
    """
    return HEADLINE_CATEGORIES.get(
        headline_type,
        headline_type.replace("_", " ").title()
    )


def get_rivalry_symbol(intensity: int) -> str:
    """
    Get text symbol for rivalry intensity.

    Args:
        intensity: Rivalry intensity value (1-100)

    Returns:
        Symbol string (###, ##, #, -, or blank)
    """
    if intensity >= 90:
        return RIVALRY_SYMBOLS["legendary"]
    elif intensity >= 75:
        return RIVALRY_SYMBOLS["intense"]
    elif intensity >= 50:
        return RIVALRY_SYMBOLS["competitive"]
    elif intensity >= 25:
        return RIVALRY_SYMBOLS["developing"]
    return RIVALRY_SYMBOLS["mild"]


def get_rivalry_intensity_color(intensity: int) -> str:
    """
    Get background color for rivalry intensity.

    Args:
        intensity: Rivalry intensity value (1-100)

    Returns:
        Hex color string for row background
    """
    if intensity >= 90:
        return RIVALRY_INTENSITY_COLORS["legendary"]
    elif intensity >= 75:
        return RIVALRY_INTENSITY_COLORS["intense"]
    elif intensity >= 50:
        return RIVALRY_INTENSITY_COLORS["competitive"]
    elif intensity >= 25:
        return RIVALRY_INTENSITY_COLORS["developing"]
    else:
        return RIVALRY_INTENSITY_COLORS["mild"]


def get_intensity_label(intensity: int) -> str:
    """
    Get text label for rivalry intensity level.

    Args:
        intensity: Rivalry intensity value (1-100)

    Returns:
        Human-readable intensity label
    """
    if intensity >= 90:
        return "Legendary"
    elif intensity >= 75:
        return "Intense"
    elif intensity >= 50:
        return "Competitive"
    elif intensity >= 25:
        return "Developing"
    else:
        return "Mild"