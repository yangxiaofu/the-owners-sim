"""
HeadlineCardWidget - Compact card for displaying media headlines.

Part of Milestone 12: Media Coverage, Tollgate 7.

Displays headline content with:
- Sentiment indicator (colored badge)
- Headline text (bold if featured)
- Subheadline (truncated)
- Click handler for detail view
"""

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import SENTIMENT_COLORS, SENTIMENT_BADGES, ESPN_THEME


class HeadlineCardWidget(QWidget):
    """
    Compact card widget for displaying a single headline.

    Can be displayed in two modes:
    - Featured: Larger, more prominent styling for top stories
    - Regular: Compact styling for secondary headlines

    Signals:
        clicked: Emitted when card is clicked, passes headline_id
    """

    clicked = Signal(int)  # headline_id

    def __init__(
        self,
        headline_data: Dict[str, Any],
        is_featured: bool = False,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the headline card.

        Args:
            headline_data: Dictionary containing headline info:
                - id: int
                - headline: str
                - subheadline: Optional[str]
                - body_text: Optional[str]
                - sentiment: str (POSITIVE, NEGATIVE, NEUTRAL, HYPE, CRITICAL)
                - priority: int
                - headline_type: str
                - team_ids: List[int]
                - player_ids: List[int]
            is_featured: If True, display in featured/prominent style
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = headline_data
        self._is_featured = is_featured
        self._setup_ui()

    def _setup_ui(self):
        """Build the card UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Container frame for styling
        self._frame = QFrame()
        self._frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._frame.setObjectName("headline_card")

        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(10)

        # Top row: sentiment badge + headline type
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Sentiment badge
        sentiment = self._data.get("sentiment", "NEUTRAL")
        badge_text = SENTIMENT_BADGES.get(sentiment, "•")
        badge_color = SENTIMENT_COLORS.get(sentiment, "#666666")

        self._badge = QLabel(badge_text)
        self._badge.setStyleSheet(
            f"color: {badge_color}; font-weight: bold; font-size: 28px;"
        )
        self._badge.setFixedWidth(36)
        top_row.addWidget(self._badge)

        # Headline type label
        headline_type = self._data.get("headline_type", "")
        if headline_type:
            type_label = QLabel(headline_type.replace("_", " ").title())
            type_label.setStyleSheet(
                f"color: {badge_color}; font-size: 20px; font-weight: bold;"
            )
            top_row.addWidget(type_label)

        top_row.addStretch()
        frame_layout.addLayout(top_row)

        # Headline text
        headline_text = self._data.get("headline", "Untitled")
        self._headline_label = QLabel(headline_text)
        self._headline_label.setWordWrap(True)

        if self._is_featured:
            self._headline_label.setStyleSheet(
                f"font-size: 32px; font-weight: bold; color: {ESPN_THEME['text_primary']};"
            )
        else:
            self._headline_label.setStyleSheet(
                f"font-size: 26px; font-weight: bold; color: {ESPN_THEME['text_primary']};"
            )

        frame_layout.addWidget(self._headline_label)

        # Subheadline (if present)
        subheadline = self._data.get("subheadline", "")
        if subheadline:
            self._sub_label = QLabel(subheadline)
            self._sub_label.setWordWrap(True)
            self._sub_label.setStyleSheet(
                f"color: {ESPN_THEME['text_secondary']}; font-size: 22px;"
            )
            # Truncate long subheadlines
            if len(subheadline) > 120:
                self._sub_label.setText(subheadline[:117] + "...")
            frame_layout.addWidget(self._sub_label)

        # Body preview for featured cards
        if self._is_featured:
            body_text = self._data.get("body_text", "")
            if body_text:
                # Show first ~150 chars
                preview = body_text[:150].rsplit(" ", 1)[0] + "..." if len(body_text) > 150 else body_text
                self._body_preview = QLabel(preview)
                self._body_preview.setWordWrap(True)
                self._body_preview.setStyleSheet(
                    f"color: {ESPN_THEME['text_secondary']}; font-size: 24px; margin-top: 8px;"
                )
                frame_layout.addWidget(self._body_preview)

        # Apply card styling
        self._apply_card_style()

        layout.addWidget(self._frame)

        # Make clickable
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _apply_card_style(self):
        """Apply border and background styling to the card."""
        sentiment = self._data.get("sentiment", "NEUTRAL")
        border_color = SENTIMENT_COLORS.get(sentiment, "#666666")

        if self._is_featured:
            # Featured: more prominent border and dark background
            self._frame.setStyleSheet(f"""
                QFrame#headline_card {{
                    background-color: {ESPN_THEME['card_bg']};
                    border: 2px solid {border_color};
                    border-radius: 6px;
                }}
                QFrame#headline_card:hover {{
                    background-color: {ESPN_THEME['card_hover']};
                    border-color: {border_color};
                }}
            """)
        else:
            # Regular: subtle border with dark background
            self._frame.setStyleSheet(f"""
                QFrame#headline_card {{
                    background-color: {ESPN_THEME['card_bg']};
                    border: 1px solid {ESPN_THEME['border']};
                    border-left: 3px solid {border_color};
                    border-radius: 4px;
                }}
                QFrame#headline_card:hover {{
                    background-color: {ESPN_THEME['card_hover']};
                }}
            """)

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
        Update the card with new headline data.

        Args:
            headline_data: New headline dictionary
        """
        self._data = headline_data
        # Clear and rebuild UI
        # For simplicity, just update the labels
        self._headline_label.setText(headline_data.get("headline", "Untitled"))

        sentiment = headline_data.get("sentiment", "NEUTRAL")
        badge_text = SENTIMENT_BADGES.get(sentiment, "•")
        badge_color = SENTIMENT_COLORS.get(sentiment, "#666666")
        self._badge.setText(badge_text)
        self._badge.setStyleSheet(
            f"color: {badge_color}; font-weight: bold; font-size: 28px;"
        )

        self._apply_card_style()
