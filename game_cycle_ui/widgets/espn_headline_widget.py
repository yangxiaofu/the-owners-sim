"""
ESPNHeadlineWidget - ESPN-style headline card with featured story support.

Part of Milestone 12: Media Coverage, Tollgate 7.7.

Displays headlines in ESPN's signature style:
- Featured story with large image placeholder and prominent headline
- Thumbnail grid for secondary stories
- Red accent colors and dark theme
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor, QFont

from game_cycle_ui.theme import (
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_CARD_HOVER,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
    ESPN_BORDER,
    FontSizes,
    TextColors,
    get_headline_category_display,
)
from game_cycle_ui.widgets.player_spotlight_widget import PlayerSpotlightWidget


class ESPNFeaturedStoryWidget(QWidget):
    """
    Large featured story card for top headline.

    ESPN-style prominent display with:
    - Split layout: Player spotlight (left) + Story content (right)
    - Player headshot and key stats
    - Bold headline with star player subheader
    - Story excerpt
    - Category badge
    """

    clicked = Signal(int)  # headline_id

    def __init__(
        self,
        headline_data: Dict[str, Any],
        player_data: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize featured story widget.

        Args:
            headline_data: Headline data dict
            player_data: Optional player data dict with keys:
                - name, position, number, stats
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = headline_data
        self._player_data = player_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the featured story UI with split layout."""
        self.setMinimumHeight(200)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main container
        self._container = QFrame()
        self._container.setObjectName("featured_story")
        self._container.setStyleSheet(f"""
            QFrame#featured_story {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {ESPN_BORDER};
                border-radius: 4px;
            }}
            QFrame#featured_story:hover {{
                border: 1px solid {ESPN_RED};
                background-color: {ESPN_CARD_HOVER};
            }}
        """)

        # Split layout: Left (player spotlight) + Right (story content)
        container_layout = QHBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Left panel: Player spotlight (if player data available)
        if self._player_data:
            player_spotlight = PlayerSpotlightWidget(self._player_data)
            container_layout.addWidget(player_spotlight)
        else:
            # Fallback: Empty placeholder (maintain old behavior)
            placeholder = QFrame()
            placeholder.setFixedWidth(200)
            placeholder.setStyleSheet(f"""
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a
                );
                border-right: 3px solid {ESPN_RED};
                border-radius: 4px 0 0 4px;
            """)
            placeholder_layout = QVBoxLayout(placeholder)
            placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label = QLabel("🏈")
            icon_label.setStyleSheet(f"font-size: {FontSizes.DISPLAY}; background: transparent;")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(icon_label)
            container_layout.addWidget(placeholder)

        # Right panel: Story content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(8)

        # Category badge
        headline_type = self._data.get("headline_type", "GAME_RECAP")
        category = get_headline_category_display(headline_type)

        category_label = QLabel(category.upper())
        category_label.setStyleSheet(f"""
            color: {ESPN_RED};
            font-size: {FontSizes.SMALL};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        content_layout.addWidget(category_label)

        # Headline
        headline_text = self._data.get("headline", "Top Story")
        headline_label = QLabel(headline_text)
        headline_label.setWordWrap(True)
        headline_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-size: {FontSizes.H3};
            font-weight: bold;
            line-height: 1.3;
        """)
        content_layout.addWidget(headline_label)

        # Star player subheader (if player data available)
        if self._player_data:
            player_name = self._player_data.get("name", "")
            player_pos = self._player_data.get("position", "").upper()
            stats = self._player_data.get("stats", {})

            # Format stat line based on position
            stat_line = self._format_stat_subheader(player_pos, stats)

            subheader_label = QLabel(f"▸ {player_pos} {player_name}")
            subheader_label.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                font-size: {FontSizes.BODY};
                font-weight: bold;
            """)
            content_layout.addWidget(subheader_label)

            if stat_line:
                stat_label = QLabel(f"   {stat_line}")
                stat_label.setStyleSheet(f"""
                    color: {ESPN_TEXT_MUTED};
                    font-size: {FontSizes.SMALL};
                """)
                content_layout.addWidget(stat_label)

        # Excerpt
        body_text = self._data.get("body_text", "")
        if body_text:
            max_chars = 90 if self._player_data else 150
            excerpt = body_text[:max_chars].rsplit(" ", 1)[0] + "..." if len(body_text) > max_chars else body_text
            excerpt_label = QLabel(excerpt)
            excerpt_label.setWordWrap(True)
            excerpt_label.setStyleSheet(f"""
                color: {TextColors.ON_DARK_MUTED};
                font-size: {FontSizes.BODY};
            """)
            content_layout.addWidget(excerpt_label)

        content_layout.addStretch()
        container_layout.addWidget(content, 1)  # Give content area stretch factor
        layout.addWidget(self._container)

    def _format_stat_subheader(self, position: str, stats: Dict[str, Any]) -> str:
        """
        Format compact stat line for subheader.

        Args:
            position: Position abbreviation
            stats: Stats dictionary

        Returns:
            Formatted stat line string
        """
        if not stats:
            return ""

        # QB: 3 TDs, 285 yards, 0 INT
        if position == "QB":
            tds = stats.get("passing_tds", 0)
            yards = stats.get("passing_yards", 0)
            ints = stats.get("passing_interceptions", 0)
            return f"{tds} TDs, {yards} yards, {ints} INT"

        # RB: 120 rush yards, 2 TDs
        elif position == "RB":
            yards = stats.get("rushing_yards", 0)
            tds = stats.get("rushing_tds", 0)
            return f"{yards} rush yards, {tds} TDs"

        # WR/TE: 8 rec, 120 yards, 2 TDs
        elif position in ["WR", "TE"]:
            rec = stats.get("receptions", 0)
            yards = stats.get("receiving_yards", 0)
            tds = stats.get("receiving_tds", 0)
            return f"{rec} rec, {yards} yards, {tds} TDs"

        # DEF: 12 tackles, 2 sacks
        elif position in ["DE", "DT", "LB", "MLB", "OLB", "ILB", "CB", "S", "FS", "SS", "DB"]:
            tackles = stats.get("tackles_total", 0)
            sacks = stats.get("sacks", 0)
            if sacks > 0:
                return f"{tackles} tackles, {sacks} sacks"
            else:
                return f"{tackles} tackles"

        return ""

    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            headline_id = self._data.get("id", 0)
            self.clicked.emit(headline_id)
        super().mousePressEvent(event)


class ESPNThumbnailWidget(QWidget):
    """
    Small thumbnail story card for secondary headlines.

    Compact ESPN-style display with:
    - Small image placeholder
    - Truncated headline
    - Category indicator
    """

    clicked = Signal(int)  # headline_id

    def __init__(
        self,
        headline_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._data = headline_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the thumbnail UI."""
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container
        self._container = QFrame()
        self._container.setObjectName("thumbnail_story")
        self._container.setStyleSheet(f"""
            QFrame#thumbnail_story {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {ESPN_BORDER};
                border-radius: 4px;
            }}
            QFrame#thumbnail_story:hover {{
                border: 1px solid {ESPN_RED};
                background-color: {ESPN_CARD_HOVER};
            }}
        """)

        container_layout = QHBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Image placeholder
        image_placeholder = QFrame()
        image_placeholder.setFixedWidth(90)
        image_placeholder.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a1a1a, stop:0.5 #252525, stop:1 #1a1a1a
            );
            border-right: 2px solid {ESPN_RED};
            border-radius: 4px 0 0 4px;
        """)

        # Center icon
        placeholder_layout = QVBoxLayout(image_placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel("🏈")
        icon_label.setStyleSheet(f"font-size: {FontSizes.H2}; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(icon_label)

        container_layout.addWidget(image_placeholder)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(4)

        # Category
        headline_type = self._data.get("headline_type", "GAME_RECAP")
        category = get_headline_category_display(headline_type)

        category_label = QLabel(category.upper())
        category_label.setStyleSheet(f"""
            color: {ESPN_RED};
            font-size: {FontSizes.TINY};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        content_layout.addWidget(category_label)

        # Headline (no truncation)
        headline_text = self._data.get("headline", "Story")

        self._headline_label = QLabel(headline_text)
        self._headline_label.setWordWrap(True)
        self._headline_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-size: {FontSizes.BODY};
            font-weight: bold;
        """)
        self._headline_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout.addWidget(self._headline_label)

        # Subheadline (if exists)
        subheadline_text = self._data.get("subheadline", "")
        if subheadline_text:
            self._subheadline_label = QLabel(subheadline_text)
            self._subheadline_label.setWordWrap(True)
            self._subheadline_label.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                font-size: {FontSizes.TINY};
            """)
            self._subheadline_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            content_layout.addWidget(self._subheadline_label)
        else:
            self._subheadline_label = None

        content_layout.addStretch()

        container_layout.addWidget(content, 1)
        layout.addWidget(self._container)

    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            headline_id = self._data.get("id", 0)
            self.clicked.emit(headline_id)
        super().mousePressEvent(event)


class ESPNHeadlinesGridWidget(QWidget):
    """
    ESPN-style headlines layout with featured story and thumbnail grid.

    Layout:
    ┌────────────────────────────────────────────┐
    │           FEATURED STORY (large)            │
    ├──────────────────┬─────────────────────────┤
    │  Thumbnail 1     │  Thumbnail 2            │
    ├──────────────────┼─────────────────────────┤
    │  Thumbnail 3     │  Thumbnail 4            │
    └──────────────────┴─────────────────────────┘
    """

    headline_clicked = Signal(int)  # headline_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._headlines: List[Dict[str, Any]] = []
        self._player_data: Optional[Dict[str, Any]] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the grid layout."""
        self.setStyleSheet(f"background-color: {ESPN_DARK_BG};")

        # Set size policy to expand and take available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(100)  # Ensure non-zero initial height

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)

        # Featured story placeholder
        self._featured_widget: Optional[ESPNFeaturedStoryWidget] = None

        # Grid for thumbnails
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(12)

    def set_headlines(
        self,
        headlines: List[Dict[str, Any]],
        player_data: Optional[Dict[str, Any]] = None
    ):
        """
        Set headlines to display with optional player data for featured story.

        Args:
            headlines: List of headline dictionaries sorted by priority
            player_data: Optional player data dict (name, position, number, stats)
        """
        self._headlines = headlines
        self._player_data = player_data
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Rebuild the UI with current headlines."""
        logger.debug(f"_rebuild_ui: {len(self._headlines)} headlines")

        # Clear existing widgets
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._headlines:
            # Empty state
            logger.debug("_rebuild_ui: No headlines, showing empty state")
            empty_label = QLabel("No headlines available for this week.")
            empty_label.setStyleSheet(f"""
                color: {TextColors.ON_DARK_DISABLED};
                font-style: italic;
                padding: 40px;
            """)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(empty_label)
            return

        # Featured story (first headline) with optional player data
        logger.debug(f"_rebuild_ui: Creating featured story: {self._headlines[0].get('headline', 'N/A')[:50]}...")
        if self._player_data:
            logger.debug(f"_rebuild_ui: Including player data for {self._player_data.get('name', 'Unknown')}")
        self._featured_widget = ESPNFeaturedStoryWidget(
            headline_data=self._headlines[0],
            player_data=self._player_data
        )
        self._featured_widget.clicked.connect(self.headline_clicked.emit)
        self._layout.addWidget(self._featured_widget)
        logger.debug(f"_rebuild_ui: Featured widget added, size={self._featured_widget.sizeHint()}")

        # Scrollable list of remaining headlines (up to 49 more = 50 total)
        if len(self._headlines) > 1:
            # Create scroll area for headline list
            self._scroll_area = QScrollArea()
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll_area.setMinimumHeight(400)  # Ensure visible scroll area

            # Style the scrollbar to match theme
            self._scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background-color: {ESPN_DARK_BG};
                    width: 10px;
                    border-radius: 5px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {ESPN_BORDER};
                    border-radius: 5px;
                    min-height: 30px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {ESPN_RED};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)

            # Content widget with vertical layout
            self._scroll_content = QWidget()
            self._scroll_content.setStyleSheet("background-color: transparent;")
            self._scroll_layout = QVBoxLayout(self._scroll_content)
            self._scroll_layout.setContentsMargins(0, 0, 0, 0)
            self._scroll_layout.setSpacing(8)

            # Add headline cards (up to 49 more = 50 total)
            for headline_data in self._headlines[1:50]:
                thumbnail = ESPNThumbnailWidget(headline_data)
                thumbnail.clicked.connect(self.headline_clicked.emit)
                self._scroll_layout.addWidget(thumbnail)

            self._scroll_layout.addStretch()
            self._scroll_area.setWidget(self._scroll_content)
            self._layout.addWidget(self._scroll_area, 1)  # stretch factor 1 to fill space

        # Force Qt to recalculate the widget size after adding content
        self.updateGeometry()
        self.adjustSize()

        # Force visibility and repaint
        self.setVisible(True)
        self.show()
        self.update()
        logger.debug(f"_rebuild_ui COMPLETE: isVisible={self.isVisible()}, height={self.height()}, sizeHint={self.sizeHint()}")

    def clear(self):
        """Clear all headlines."""
        self._headlines = []
        self._rebuild_ui()
