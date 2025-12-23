"""
CompactStoryCardWidget - Compact headline card with inline player stats.

Part of Milestone 12: Media Coverage.

Displays a compact headline card (~120px height) with:
- Category badge (colored by type)
- Bold headline text (1-2 lines)
- Optional player name with star icon
- Optional inline player stats (gray text)
- Body preview text (truncated)
- Clickable with hover effect
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

from game_cycle_ui.theme import (
    ESPN_THEME,
    ESPN_RED,
    ESPN_CARD_BG,
    ESPN_CARD_HOVER,
    ESPN_BORDER,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
    TextColors,
    Typography,
    FontSizes,
    get_headline_category_display,
)


# Category colors for badges (ESPN-style)
CATEGORY_BADGE_COLORS = {
    "GAME_RECAP": {"bg": "#1565C0", "fg": "#FFFFFF"},      # Blue
    "BLOWOUT": {"bg": "#E65100", "fg": "#FFFFFF"},         # Dark orange
    "UPSET": {"bg": "#C62828", "fg": "#FFFFFF"},           # Red
    "COMEBACK": {"bg": "#2E7D32", "fg": "#FFFFFF"},        # Green
    "INJURY": {"bg": "#7B1FA2", "fg": "#FFFFFF"},          # Purple
    "TRADE": {"bg": "#00838F", "fg": "#FFFFFF"},           # Teal
    "SIGNING": {"bg": "#00695C", "fg": "#FFFFFF"},         # Dark teal
    "AWARD": {"bg": "#F9A825", "fg": "#1a1a1a"},           # Gold
    "MILESTONE": {"bg": "#FFB300", "fg": "#1a1a1a"},       # Amber
    "DRAFT": {"bg": "#6A1B9A", "fg": "#FFFFFF"},           # Dark purple
    "PREVIEW": {"bg": "#E65100", "fg": "#FFFFFF"},         # Orange
    "POWER_RANKING": {"bg": "#1976D2", "fg": "#FFFFFF"},   # Blue
    "STREAK": {"bg": "#D32F2F", "fg": "#FFFFFF"},          # Red
    "DEFAULT": {"bg": "#424242", "fg": "#FFFFFF"},         # Gray
}


class CompactStoryCardWidget(QWidget):
    """
    Compact headline card with inline player stats (~120px height).

    Layout:
        [CATEGORY] Headline Text (bold, 1-2 lines)
        ★ Player Name (accent color) - optional
        Inline stats (gray text) - optional
        Body preview text (1-2 lines, truncated) - optional

    Signals:
        clicked: Emitted when card is clicked, passes headline_id
    """

    clicked = Signal(int)  # headline_id

    def __init__(
        self,
        headline: str,
        category: str,
        player_name: Optional[str] = None,
        player_stats: Optional[Dict[str, Any]] = None,
        body_preview: str = "",
        headline_id: int = 0,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the compact story card.

        Args:
            headline: Headline text
            category: Category/type (e.g., "GAME_RECAP", "INJURY")
            player_name: Optional player name to display with star
            player_stats: Optional stats dict (e.g., {"passing_yards": 320, "passing_tds": 4})
            body_preview: Optional preview text
            headline_id: Headline ID for click signal
            parent: Parent widget
        """
        super().__init__(parent)
        self._headline = headline
        self._category = category.upper()
        self._player_name = player_name
        self._player_stats = player_stats or {}
        self._body_preview = body_preview
        self._headline_id = headline_id
        self._setup_ui()

    def _setup_ui(self):
        """Build the compact card UI."""
        # Set fixed height for compact look
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container frame
        self._container = QFrame()
        self._container.setObjectName("compact_story_card")
        self._apply_style(hovered=False)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(6)

        # Top row: Category badge + Headline
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Category badge
        category_colors = CATEGORY_BADGE_COLORS.get(
            self._category,
            CATEGORY_BADGE_COLORS["DEFAULT"]
        )
        category_display = get_headline_category_display(self._category)

        self._category_badge = QLabel(category_display.upper())
        self._category_badge.setFont(Typography.TINY_BOLD)
        self._category_badge.setStyleSheet(f"""
            background-color: {category_colors['bg']};
            color: {category_colors['fg']};
            border-radius: 3px;
            padding: 3px 8px;
            font-weight: bold;
            letter-spacing: 0.5px;
        """)
        self._category_badge.setFixedHeight(20)
        self._category_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self._category_badge)

        # Headline text
        self._headline_label = QLabel(self._headline)
        self._headline_label.setFont(Typography.BODY_BOLD)
        self._headline_label.setWordWrap(True)
        self._headline_label.setMaximumHeight(48)  # ~2 lines max
        self._headline_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            line-height: 1.4;
        """)
        self._headline_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row.addWidget(self._headline_label, 1)

        container_layout.addLayout(top_row)

        # Player name row (if provided)
        if self._player_name:
            player_row = QHBoxLayout()
            player_row.setSpacing(4)

            star_label = QLabel("★")
            star_label.setStyleSheet(f"""
                color: {ESPN_RED};
                font-size: {FontSizes.BODY};
            """)
            player_row.addWidget(star_label)

            player_label = QLabel(self._player_name)
            player_label.setFont(Typography.BODY_SMALL_BOLD)
            player_label.setStyleSheet(f"""
                color: {ESPN_RED};
                font-weight: bold;
            """)
            player_row.addWidget(player_label)
            player_row.addStretch()

            container_layout.addLayout(player_row)

        # Player stats row (if provided)
        if self._player_stats:
            stats_text = self._format_stats()
            if stats_text:
                stats_label = QLabel(stats_text)
                stats_label.setFont(Typography.BODY_SMALL)
                stats_label.setStyleSheet(f"""
                    color: {ESPN_TEXT_MUTED};
                    padding-left: 18px;
                """)
                container_layout.addWidget(stats_label)

        # Body preview (if provided)
        if self._body_preview:
            # Truncate to ~100 characters
            preview_text = self._body_preview
            if len(preview_text) > 100:
                preview_text = preview_text[:97] + "..."

            preview_label = QLabel(preview_text)
            preview_label.setFont(Typography.BODY_SMALL)
            preview_label.setWordWrap(True)
            preview_label.setMaximumHeight(32)  # ~2 lines max
            preview_label.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                line-height: 1.3;
            """)
            container_layout.addWidget(preview_label)

        container_layout.addStretch()
        layout.addWidget(self._container)

    def _format_stats(self) -> str:
        """
        Format player stats into a compact inline string.

        Returns:
            Formatted stat string (e.g., "25/35, 320 YDS, 4 TD")
        """
        if not self._player_stats:
            return ""

        parts = []

        # Passing stats
        if "passing_completions" in self._player_stats:
            comp = self._player_stats.get("passing_completions", 0)
            att = self._player_stats.get("passing_attempts", 0)
            yards = self._player_stats.get("passing_yards", 0)
            tds = self._player_stats.get("passing_tds", 0)
            parts.append(f"{comp}/{att}, {yards} YDS, {tds} TD")

        # Rushing stats
        elif "rushing_yards" in self._player_stats:
            yards = self._player_stats.get("rushing_yards", 0)
            tds = self._player_stats.get("rushing_tds", 0)
            att = self._player_stats.get("rushing_attempts", 0)
            parts.append(f"{att} CAR, {yards} YDS, {tds} TD")

        # Receiving stats
        elif "receptions" in self._player_stats:
            rec = self._player_stats.get("receptions", 0)
            yards = self._player_stats.get("receiving_yards", 0)
            tds = self._player_stats.get("receiving_tds", 0)
            parts.append(f"{rec} REC, {yards} YDS, {tds} TD")

        # Defensive stats
        elif "tackles_total" in self._player_stats:
            tackles = self._player_stats.get("tackles_total", 0)
            sacks = self._player_stats.get("sacks", 0)
            ints = self._player_stats.get("interceptions", 0)
            if sacks > 0:
                parts.append(f"{tackles} TKL, {sacks} SK")
            elif ints > 0:
                parts.append(f"{tackles} TKL, {ints} INT")
            else:
                parts.append(f"{tackles} TKL")

        return ", ".join(parts)

    def _apply_style(self, hovered: bool = False):
        """
        Apply background style based on hover state.

        Args:
            hovered: True if mouse is hovering over card
        """
        if hovered:
            self._container.setStyleSheet(f"""
                QFrame#compact_story_card {{
                    background-color: {ESPN_CARD_HOVER};
                    border: 1px solid {ESPN_BORDER};
                    border-left: 3px solid {ESPN_RED};
                    border-radius: 4px;
                }}
            """)
        else:
            self._container.setStyleSheet(f"""
                QFrame#compact_story_card {{
                    background-color: {ESPN_CARD_BG};
                    border: 1px solid {ESPN_BORDER};
                    border-left: 3px solid {ESPN_BORDER};
                    border-radius: 4px;
                }}
            """)

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
            self.clicked.emit(self._headline_id)
        super().mousePressEvent(event)

    @property
    def headline_id(self) -> int:
        """Get the headline ID."""
        return self._headline_id

    def update_data(
        self,
        headline: str,
        category: str,
        player_name: Optional[str] = None,
        player_stats: Optional[Dict[str, Any]] = None,
        body_preview: str = "",
        headline_id: int = 0
    ):
        """
        Update the card with new data.

        Args:
            headline: New headline text
            category: New category
            player_name: New player name (or None)
            player_stats: New player stats (or None)
            body_preview: New body preview
            headline_id: New headline ID
        """
        self._headline = headline
        self._category = category.upper()
        self._player_name = player_name
        self._player_stats = player_stats or {}
        self._body_preview = body_preview
        self._headline_id = headline_id

        # Rebuild UI
        # Clear container
        for i in reversed(range(self._container.layout().count())):
            item = self._container.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Remove nested layouts
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

        # Rebuild from scratch
        self._setup_ui()
