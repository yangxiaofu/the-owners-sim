"""
HeadlineCardWidget - ESPN-style compact news feed item.

Part of Milestone 12: Media Coverage, Tollgate 7.

Displays headline in a compact single-row format with:
- Category chip (colored pill)
- Headline text
- Timestamp
- Hover effect for interactivity
"""

from typing import Any, Dict, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    ESPN_THEME,
    Colors,
    FontSizes,
    TextColors,
    Typography,
)


# Category colors for chips (ESPN-style)
CATEGORY_COLORS = {
    "PREVIEW": {"bg": "#E65100", "fg": "#FFFFFF"},      # Orange
    "GAME_RECAP": {"bg": "#1565C0", "fg": "#FFFFFF"},   # Blue
    "BREAKING": {"bg": "#C62828", "fg": "#FFFFFF"},     # Red
    "INJURY": {"bg": "#7B1FA2", "fg": "#FFFFFF"},       # Purple
    "TRADE": {"bg": "#2E7D32", "fg": "#FFFFFF"},        # Green
    "SIGNING": {"bg": "#00838F", "fg": "#FFFFFF"},      # Teal
    "DRAFT": {"bg": "#F9A825", "fg": "#1a1a1a"},        # Yellow
    "DEFAULT": {"bg": "#424242", "fg": "#FFFFFF"},      # Gray
}

# Sentiment icons (minimal)
SENTIMENT_ICONS = {
    "POSITIVE": "●",
    "NEGATIVE": "●",
    "NEUTRAL": "●",
    "HYPE": "★",
    "CRITICAL": "●",
}

SENTIMENT_ICON_COLORS = {
    "POSITIVE": "#4CAF50",   # Green
    "NEGATIVE": "#F44336",   # Red
    "NEUTRAL": "#9E9E9E",    # Gray
    "HYPE": "#FF9800",       # Orange
    "CRITICAL": "#F44336",   # Red
}


class HeadlineCardWidget(QWidget):
    """
    Compact ESPN-style news feed item.

    Single row layout: [SENTIMENT] [CATEGORY] Headline text              [TIME]

    Signals:
        clicked: Emitted when item is clicked, passes headline_id
    """

    clicked = Signal(int)  # headline_id

    def __init__(
        self,
        headline_data: Dict[str, Any],
        is_featured: bool = False,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the headline feed item.

        Args:
            headline_data: Dictionary containing headline info
            is_featured: If True, slightly more prominent styling
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = headline_data
        self._is_featured = is_featured
        self._setup_ui()

    def _setup_ui(self):
        """Build the compact feed item UI."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Dynamic height based on content (no fixed height)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Apply hover styling
        self._apply_style(hovered=False)

        # Sentiment indicator (small dot)
        sentiment = self._data.get("sentiment", "NEUTRAL")
        icon = SENTIMENT_ICONS.get(sentiment, "●")
        icon_color = SENTIMENT_ICON_COLORS.get(sentiment, "#9E9E9E")

        self._sentiment_dot = QLabel(icon)
        self._sentiment_dot.setFixedWidth(16)
        self._sentiment_dot.setAlignment(Qt.AlignCenter)
        self._sentiment_dot.setStyleSheet(
            f"color: {icon_color}; font-size: {FontSizes.CAPTION};"
        )
        layout.addWidget(self._sentiment_dot)

        # Category chip
        headline_type = self._data.get("headline_type", "DEFAULT").upper()
        category_style = CATEGORY_COLORS.get(headline_type, CATEGORY_COLORS["DEFAULT"])

        display_type = headline_type.replace("_", " ").title()
        if len(display_type) > 12:
            display_type = display_type[:10] + "..."

        self._category_chip = QLabel(display_type)
        self._category_chip.setFont(Typography.CAPTION)
        self._category_chip.setAlignment(Qt.AlignCenter)
        self._category_chip.setStyleSheet(
            f"background-color: {category_style['bg']}; "
            f"color: {category_style['fg']}; "
            f"border-radius: 3px; "
            f"padding: 2px 6px; "
            f"font-weight: bold;"
        )
        self._category_chip.setFixedWidth(80)
        layout.addWidget(self._category_chip)

        # Headline text container (vertical layout for headline + subheadline)
        from PySide6.QtWidgets import QVBoxLayout
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        # Main headline
        headline_text = self._data.get("headline", "Untitled")
        self._headline_label = QLabel(headline_text)
        self._headline_label.setFont(Typography.BODY if not self._is_featured else Typography.BODY_BOLD)
        self._headline_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self._headline_label.setWordWrap(True)  # Allow wrapping instead of truncating
        self._headline_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_layout.addWidget(self._headline_label)

        # Subheadline (if exists)
        subheadline_text = self._data.get("subheadline", "")
        if subheadline_text:
            self._subheadline_label = QLabel(subheadline_text)
            self._subheadline_label.setFont(Typography.CAPTION)
            self._subheadline_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
            self._subheadline_label.setWordWrap(True)
            self._subheadline_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            text_layout.addWidget(self._subheadline_label)
        else:
            self._subheadline_label = None

        layout.addWidget(text_container, 1)  # Stretch factor 1

        # Timestamp (right-aligned)
        created_at = self._data.get("created_at")
        time_text = self._format_timestamp(created_at)

        self._time_label = QLabel(time_text)
        self._time_label.setFont(Typography.CAPTION)
        self._time_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self._time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label.setFixedWidth(50)
        layout.addWidget(self._time_label)

        # Make clickable
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _format_timestamp(self, created_at) -> str:
        """Format timestamp as relative time."""
        if not created_at:
            return ""

        try:
            if isinstance(created_at, str):
                # Parse ISO format
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif isinstance(created_at, datetime):
                dt = created_at
            else:
                return ""

            now = datetime.now()
            if dt.tzinfo:
                now = datetime.now(dt.tzinfo)

            diff = now - dt

            if diff.days > 7:
                return dt.strftime("%m/%d")
            elif diff.days > 0:
                return f"{diff.days}d"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600}h"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60}m"
            else:
                return "now"
        except Exception:
            return ""

    def _apply_style(self, hovered: bool = False):
        """Apply background style based on hover state."""
        if hovered:
            self.setStyleSheet(
                f"HeadlineCardWidget {{ "
                f"background-color: {ESPN_THEME['card_hover']}; "
                f"border-bottom: 1px solid {ESPN_THEME['border']}; "
                f"}}"
            )
        else:
            self.setStyleSheet(
                f"HeadlineCardWidget {{ "
                f"background-color: transparent; "
                f"border-bottom: 1px solid {ESPN_THEME['border']}; "
                f"}}"
            )

    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave for hover effect."""
        self._apply_style(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            headline_id = self._data.get("id", 0)
            self.clicked.emit(headline_id)
        super().mousePressEvent(event)

    @property
    def headline_id(self) -> int:
        """Get the headline ID."""
        return self._data.get("id", 0)

    @property
    def headline_data(self) -> Dict[str, Any]:
        """Get the full headline data."""
        return self._data

    def set_data(self, headline_data: Dict[str, Any]):
        """
        Update the item with new headline data.

        Args:
            headline_data: New headline dictionary
        """
        self._data = headline_data

        # Update headline (no truncation)
        headline_text = headline_data.get("headline", "Untitled")
        self._headline_label.setText(headline_text)

        # Update subheadline
        subheadline_text = headline_data.get("subheadline", "")
        if self._subheadline_label:
            if subheadline_text:
                self._subheadline_label.setText(subheadline_text)
                self._subheadline_label.setVisible(True)
            else:
                self._subheadline_label.setVisible(False)

        # Update sentiment
        sentiment = headline_data.get("sentiment", "NEUTRAL")
        icon = SENTIMENT_ICONS.get(sentiment, "●")
        icon_color = SENTIMENT_ICON_COLORS.get(sentiment, "#9E9E9E")
        self._sentiment_dot.setText(icon)
        self._sentiment_dot.setStyleSheet(
            f"color: {icon_color}; font-size: {FontSizes.CAPTION};"
        )

        # Update category
        headline_type = headline_data.get("headline_type", "DEFAULT").upper()
        category_style = CATEGORY_COLORS.get(headline_type, CATEGORY_COLORS["DEFAULT"])
        display_type = headline_type.replace("_", " ").title()
        if len(display_type) > 12:
            display_type = display_type[:10] + "..."
        self._category_chip.setText(display_type)
        self._category_chip.setStyleSheet(
            f"background-color: {category_style['bg']}; "
            f"color: {category_style['fg']}; "
            f"border-radius: 3px; "
            f"padding: 2px 6px; "
            f"font-weight: bold;"
        )

        # Update timestamp
        created_at = headline_data.get("created_at")
        self._time_label.setText(self._format_timestamp(created_at))
