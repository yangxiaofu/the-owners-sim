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
from PySide6.QtGui import QFont


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


# =============================================================================
# TYPOGRAPHY & FONT CLASSES (Must be defined before style constants use them)
# =============================================================================

class Typography:
    """
    Standardized fonts for consistent UI appearance.

    Usage:
        from game_cycle_ui.theme import Typography
        label.setFont(Typography.H1)
    """
    FAMILY = "Arial"

    # HEADINGS (Bold)
    DISPLAY = QFont("Arial", 28, QFont.Bold)     # Team abbrevs, large records
    H1 = QFont("Arial", 24, QFont.Bold)          # Page titles, stage labels
    H2 = QFont("Arial", 20, QFont.Bold)          # Major section headers
    H3 = QFont("Arial", 18, QFont.Bold)          # Sub-section headers
    H4 = QFont("Arial", 16, QFont.Bold)          # Card headers, stat values
    H5 = QFont("Arial", 14, QFont.Bold)          # Minor headers
    H6 = QFont("Arial", 12, QFont.Bold)          # Small headers

    # BODY TEXT
    BODY_LARGE = QFont("Arial", 14)              # Prominent body
    BODY = QFont("Arial", 12)                    # Standard body
    BODY_SMALL = QFont("Arial", 11)              # Compact body
    BODY_LARGE_BOLD = QFont("Arial", 14, QFont.Bold)
    BODY_BOLD = QFont("Arial", 12, QFont.Bold)
    BODY_SMALL_BOLD = QFont("Arial", 11, QFont.Bold)

    # DETAIL TEXT
    CAPTION = QFont("Arial", 11)                 # Stat labels
    CAPTION_BOLD = QFont("Arial", 11, QFont.Bold)
    SMALL = QFont("Arial", 10)                   # Tertiary text
    SMALL_BOLD = QFont("Arial", 10, QFont.Bold)
    TINY = QFont("Arial", 9)                     # Meta info
    TINY_BOLD = QFont("Arial", 9, QFont.Bold)

    # SPECIAL PURPOSE
    TABLE = QFont("Arial", 11)                   # Table cells
    TABLE_HEADER = QFont("Arial", 10, QFont.Bold)
    TABLE_LARGE = QFont("Arial", 18)             # Large table displays
    ICON_LARGE = QFont("Arial", 48)              # Emoji displays

    @staticmethod
    def apply(widget, font: QFont) -> None:
        """
        Apply a typography style to a widget.

        Usage:
            Typography.apply(label, Typography.H1)

        Args:
            widget: Any QWidget with setFont() method
            font: A QFont from Typography constants
        """
        widget.setFont(font)


class FontSizes:
    """Font sizes as strings for CSS stylesheets."""
    DISPLAY = "28px"
    H1 = "24px"
    H2 = "20px"
    H3 = "18px"
    H4 = "16px"
    H5 = "14px"
    H6 = "12px"
    BODY = "12px"
    BODY_SMALL = "11px"
    CAPTION = "11px"
    SMALL = "10px"
    TINY = "9px"


class TextColors:
    """
    Text colors organized by background context.

    Usage:
        label.setStyleSheet(f"color: {TextColors.ON_DARK};")
    """
    # FOR DARK BACKGROUNDS (ESPN theme: #1a1a1a, #2a2a2a, #333333)
    ON_DARK = "#FFFFFF"           # Primary text on dark bg
    ON_DARK_SECONDARY = "#CCCCCC" # Secondary text on dark bg
    ON_DARK_MUTED = "#888888"     # Tertiary/muted text on dark bg
    ON_DARK_DISABLED = "#666666"  # Disabled text on dark bg

    # FOR LIGHT BACKGROUNDS (#FFFFFF, #F5F5F5)
    ON_LIGHT = "#212121"          # Primary text on light bg
    ON_LIGHT_SECONDARY = "#666666" # Secondary text on light bg
    ON_LIGHT_MUTED = "#999999"    # Tertiary/muted text on light bg
    ON_LIGHT_DISABLED = "#CCCCCC" # Disabled text on light bg

    # SEMANTIC (work on both themes)
    SUCCESS = "#2E7D32"           # Green - victories, positive
    ERROR = "#C62828"             # Red - losses, negative
    WARNING = "#F57C00"           # Orange - caution
    INFO = "#1976D2"              # Blue - informational
    NEUTRAL = "#757575"           # Gray - neutral


# =============================================================================
# STYLE CONSTANTS (Using classes defined above)
# =============================================================================

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

# Table body styling (ESPN dark theme)
TABLE_STYLE = """
    QTableWidget {
        background-color: #1a1a1a;
        gridline-color: #333333;
        color: white;
        border: none;
    }
    QTableWidget::item {
        padding: 4px;
        border-bottom: 1px solid #333333;
    }
    QTableWidget::item:selected {
        background-color: #2a4a6a;
    }
    QTableWidget::item:alternate {
        background-color: #222222;
    }
"""

# Table dimensions
TABLE_ROW_HEIGHT = 32  # Standard row height in pixels (matches standings)


def apply_table_style(table, row_height: int = TABLE_ROW_HEIGHT):
    """
    Apply standard ESPN dark table styling to a QTableWidget.

    Usage:
        from game_cycle_ui.theme import apply_table_style
        table = QTableWidget()
        apply_table_style(table)

    Args:
        table: QTableWidget instance to style
        row_height: Row height in pixels (default: 32)
    """
    from PySide6.QtWidgets import QTableWidget
    table.setStyleSheet(TABLE_STYLE)
    table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
    table.setFont(Typography.TABLE)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)


# =============================================================================
# TAB WIDGET STYLING (ESPN Dark Theme)
# =============================================================================
# Standardized tab styling for all QTabWidget instances.
# Based on team_view.py reference implementation.

TAB_STYLE = """
    QTabWidget::pane { border: none; background: transparent; }
    QTabBar::tab {
        background: #333333;
        color: #888888;
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected { background: #444444; color: #FFFFFF; }
    QTabBar::tab:hover { background: #3a3a3a; }
"""

# Main navigation tabs (larger padding for top-level navigation in main_window)
MAIN_NAV_TAB_STYLE = """
    QTabWidget::pane { border: none; background: transparent; }
    QTabBar::tab {
        background: #333333;
        color: #888888;
        padding: 10px 20px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
        font-weight: bold;
    }
    QTabBar::tab:selected { background: #444444; color: #FFFFFF; }
    QTabBar::tab:hover { background: #3a3a3a; }
"""

# =============================================================================
# BUTTON STYLING
# =============================================================================
# Standardized button styles for consistent appearance across all views.
# Use these constants instead of inline stylesheets.


def _generate_button_style(
    bg: str, hover: str, pressed: str, *, bold: bool = True, compact: bool = False
) -> str:
    """
    Generate button stylesheet with consistent structure.

    Args:
        bg: Background color (hex)
        hover: Hover background color (hex)
        pressed: Pressed background color (hex)
        bold: Whether to use bold font weight (default True)
        compact: Use compact sizing for table cells (default False)
    """
    if compact:
        padding = "4px 12px"
        radius = "3px"
        extra = "font-size: 12px; min-width: 60px;"
    else:
        padding = "8px 16px"
        radius = "4px"
        extra = ""

    weight = "font-weight: bold;" if bold else ""

    return f"""
    QPushButton {{
        background-color: {bg};
        color: white;
        border: none;
        border-radius: {radius};
        padding: {padding};
        {weight}
        {extra}
    }}
    QPushButton:hover {{ background-color: {hover}; }}
    QPushButton:pressed {{ background-color: {pressed}; }}
    QPushButton:disabled {{ background-color: #CCCCCC; color: #666666; }}
"""


# Standard button styles
PRIMARY_BUTTON_STYLE = _generate_button_style("#2E7D32", "#1B5E20", "#145214")
SECONDARY_BUTTON_STYLE = _generate_button_style("#1976D2", "#1565C0", "#0D47A1")
DANGER_BUTTON_STYLE = _generate_button_style("#C62828", "#B71C1C", "#8E0000")
WARNING_BUTTON_STYLE = _generate_button_style("#F57C00", "#E65100", "#BF360C")
NEUTRAL_BUTTON_STYLE = _generate_button_style("#666666", "#555555", "#444444", bold=False)

# Compact button styles for table cells (reduced padding for 32px row height)
TABLE_BUTTON_STYLE = _generate_button_style("#1976D2", "#1565C0", "#0D47A1", compact=True)
TABLE_BUTTON_NEUTRAL_STYLE = _generate_button_style(
    "#666666", "#555555", "#444444", bold=False, compact=True
)

# Dark-themed GroupBox styling for consistent section headers
GROUPBOX_DARK_STYLE = f"""
    QGroupBox {{
        font-weight: bold;
        font-size: {FontSizes.H5};
        color: {TextColors.ON_DARK};
        background-color: #263238;
        border: 1px solid #37474f;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: {TextColors.ON_DARK};
    }}
"""

# Rivalry intensity colors (dark backgrounds for ESPN theme - use white text)
RIVALRY_INTENSITY_COLORS = {
    "legendary": "#4a2020",   # Dark red (90-100 intensity)
    "intense": "#4a3520",     # Dark orange (75-89)
    "competitive": "#3a3a20", # Dark olive (50-74)
    "developing": "#203a20",  # Dark green (25-49)
    "mild": "#2a2a2a",        # Dark gray (1-24)
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


# =============================================================================
# SPACING SYSTEM
# =============================================================================

class Spacing:
    """Standardized spacing for consistent layouts."""
    MAJOR = 16   # Between major sections
    MINOR = 8    # Between related items
    MICRO = 4    # Between tightly coupled items


# =============================================================================
# GRADE/RATING COLORS
# =============================================================================

GRADE_THRESHOLDS = {
    "elite": 85,      # 85+ = Green
    "solid": 75,      # 75-84 = Blue
    "average": 65,    # 65-74 = Gray
    "below": 50,      # 50-64 = Orange
    "poor": 0,        # <50 = Red
}

GRADE_COLORS = {
    "elite": "#2E7D32",      # Green
    "solid": "#1976D2",      # Blue
    "average": "#666666",    # Gray
    "below": "#F57C00",      # Orange
    "poor": "#C62828",       # Red
}

# Grade tier colors (simplified 5-tier system for performance display)
GRADE_TIER_COLORS = {
    "elite": "#2E7D32",       # 90+
    "excellent": "#4CAF50",   # 80-89
    "good": "#1976D2",        # 70-79
    "average": "#FF9800",     # 60-69
    "below_average": "#f44336",  # <60
}


def get_grade_color(value: int) -> str:
    """Return color hex string for a grade/rating value (0-100)."""
    if value >= GRADE_THRESHOLDS["elite"]:
        return GRADE_COLORS["elite"]
    elif value >= GRADE_THRESHOLDS["solid"]:
        return GRADE_COLORS["solid"]
    elif value >= GRADE_THRESHOLDS["average"]:
        return GRADE_COLORS["average"]
    elif value >= GRADE_THRESHOLDS["below"]:
        return GRADE_COLORS["below"]
    return GRADE_COLORS["poor"]


# =============================================================================
# PROSPECT/PLAYER RATING COLORIZER
# =============================================================================

class RatingColorizer:
    """
    Color coding for player/prospect ratings (0-100).

    Uses draft-specific thresholds optimized for prospect evaluation.
    Different from general grade thresholds to reflect draft context.
    """

    # Draft prospect thresholds (more optimistic than general grading)
    ELITE_THRESHOLD = 80      # Elite prospect - franchise potential
    SOLID_THRESHOLD = 70      # Solid prospect - starter quality
    PROJECT_THRESHOLD = 60    # Project - developmental upside
    # Below 60 = Backup/depth

    @staticmethod
    def get_color_for_rating(rating: int) -> str:
        """
        Get color hex string for a player/prospect rating.

        Args:
            rating: Player overall rating (0-100)

        Returns:
            Hex color string

        Examples:
            >>> RatingColorizer.get_color_for_rating(85)
            '#2E7D32'  # Green (elite)
            >>> RatingColorizer.get_color_for_rating(72)
            '#1976D2'  # Blue (solid)
            >>> RatingColorizer.get_color_for_rating(65)
            '#F57C00'  # Orange (project)
            >>> RatingColorizer.get_color_for_rating(55)
            '#666666'  # Gray (backup)
        """
        if rating >= RatingColorizer.ELITE_THRESHOLD:
            return Colors.SUCCESS  # Green - Elite prospect
        elif rating >= RatingColorizer.SOLID_THRESHOLD:
            return Colors.INFO     # Blue - Solid prospect
        elif rating >= RatingColorizer.PROJECT_THRESHOLD:
            return Colors.WARNING  # Orange - Project
        else:
            return Colors.MUTED    # Gray - Backup/depth


# =============================================================================
# DIRECT COLOR ACCESSORS
# =============================================================================

class Colors:
    """Direct access to common colors without category lookup."""
    SUCCESS = "#2E7D32"
    SUCCESS_DARK = "#1B3D1B"
    ERROR = "#C62828"
    WARNING = "#F57C00"
    WARNING_DARK = "#3D2B1B"
    INFO = "#1976D2"
    INFO_DARK = "#1B2D3D"
    MUTED = "#666666"
    DISABLED = "#CCCCCC"

    # Cap space
    CAP_HEALTHY = "#2E7D32"
    CAP_PROJECTED = "#1976D2"
    CAP_TIGHT = "#F57C00"
    CAP_OVER = "#C62828"

    # Text
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#666666"
    TEXT_MUTED = "#999999"
    TEXT_INVERSE = "#FFFFFF"

    # Backgrounds (ESPN dark theme)
    BG_PRIMARY = "#1a1a1a"
    BG_SECONDARY = "#2a2a2a"
    BG_HOVER = "#333333"
    BORDER = "#444444"

    # Staff performance widget colors
    STAFF_HEADER = "#1e88e5"
    STAFF_CONTRACT_INFO = "#bbbbbb"
    STAFF_PERFORMANCE_METRIC = "#999999"
    STAFF_KEEP_BUTTON = "#4caf50"
    STAFF_KEEP_BUTTON_HOVER = "#66bb6a"
    STAFF_FIRE_BUTTON = "#f44336"
    STAFF_FIRE_BUTTON_HOVER = "#e57373"
    STAFF_TAB_BACKGROUND = "#37474F"
    STAFF_TAB_SELECTED = "#1e88e5"
    STAFF_CARD_BACKGROUND = "#263238"

    # Transaction type colors
    TRANSACTION_TRADE = "#2196f3"
    TRANSACTION_FA_SIGNING = "#4caf50"
    TRANSACTION_DRAFT_PICK = "#ff9800"
    TRANSACTION_CUT = "#f44336"