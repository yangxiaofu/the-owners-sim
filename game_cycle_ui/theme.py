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