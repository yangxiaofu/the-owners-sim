"""
PersonalityBadge - Small pill/chip widget for social personality types.

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 6.

Displays a small colored badge indicating personality type:
- FAN (blue pill)
- MEDIA (orange pill)
- BEAT_REPORTER (teal pill)
- HOT_TAKE (red pill)
- STATS_ANALYST (purple pill)
"""

from typing import Optional

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


# Personality type colors (ESPN-style)
PERSONALITY_COLORS = {
    "FAN": {"bg": "#1565C0", "fg": "#FFFFFF"},              # Blue
    "MEDIA": {"bg": "#E65100", "fg": "#FFFFFF"},            # Orange
    "BEAT_REPORTER": {"bg": "#00838F", "fg": "#FFFFFF"},    # Teal
    "HOT_TAKE": {"bg": "#C62828", "fg": "#FFFFFF"},         # Red
    "STATS_ANALYST": {"bg": "#7B1FA2", "fg": "#FFFFFF"},    # Purple
    "DEFAULT": {"bg": "#424242", "fg": "#FFFFFF"},          # Gray
}


class PersonalityBadge(QLabel):
    """
    Small colored pill/chip displaying personality type.

    Compact badge that shows whether post is from FAN, MEDIA, etc.
    Uses ESPN color scheme for visual consistency.

    Example:
        badge = PersonalityBadge("FAN")
        # Displays blue pill with "FAN" text
    """

    def __init__(
        self,
        personality_type: str,
        parent: Optional[QLabel] = None
    ):
        """
        Initialize the personality badge.

        Args:
            personality_type: Type of personality ("FAN", "MEDIA", "BEAT_REPORTER", etc.)
            parent: Parent widget
        """
        super().__init__(parent)

        # Normalize type and get display text
        self._personality_type = personality_type.upper()
        display_text = self._get_display_text(self._personality_type)

        # Set badge text
        self.setText(display_text)

        # Apply styling
        self._setup_style()

    def _get_display_text(self, personality_type: str) -> str:
        """
        Get display text for personality type.

        Args:
            personality_type: Raw personality type

        Returns:
            Formatted display text
        """
        # Map personality types to display text
        display_map = {
            "FAN": "FAN",
            "MEDIA": "MEDIA",
            "BEAT_REPORTER": "BEAT",
            "HOT_TAKE": "HOT TAKE",
            "STATS_ANALYST": "STATS",
        }

        return display_map.get(personality_type, personality_type[:8])

    def _setup_style(self):
        """Apply ESPN-style pill styling."""
        # Get colors for this personality type
        colors = PERSONALITY_COLORS.get(
            self._personality_type,
            PERSONALITY_COLORS["DEFAULT"]
        )

        # Apply pill styling
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['bg']};
                color: {colors['fg']};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.3px;
                min-width: 35px;
                max-width: 60px;
            }}
        """)

        # Center text
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set fixed height for consistency
        self.setFixedHeight(18)
