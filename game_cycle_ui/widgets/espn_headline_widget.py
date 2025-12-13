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
    get_headline_category_display,
)


class ESPNFeaturedStoryWidget(QWidget):
    """
    Large featured story card for top headline.

    ESPN-style prominent display with:
    - Large image placeholder area
    - Bold headline
    - Story excerpt
    - Category badge
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
        """Build the featured story UI."""
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

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Image placeholder (simulated with colored bar)
        image_placeholder = QFrame()
        image_placeholder.setFixedHeight(120)
        image_placeholder.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a
            );
            border-bottom: 3px solid {ESPN_RED};
        """)

        # Center icon in placeholder
        placeholder_layout = QVBoxLayout(image_placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("🏈")
        icon_label.setStyleSheet("font-size: 36px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(icon_label)

        container_layout.addWidget(image_placeholder)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(8)

        # Category badge
        headline_type = self._data.get("headline_type", "GAME_RECAP")
        category = get_headline_category_display(headline_type)

        category_label = QLabel(category.upper())
        category_label.setStyleSheet(f"""
            color: {ESPN_RED};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        content_layout.addWidget(category_label)

        # Headline
        headline_text = self._data.get("headline", "Top Story")
        headline_label = QLabel(headline_text)
        headline_label.setWordWrap(True)
        headline_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: 18px;
            font-weight: bold;
            line-height: 1.3;
        """)
        content_layout.addWidget(headline_label)

        # Excerpt
        body_text = self._data.get("body_text", "")
        if body_text:
            excerpt = body_text[:150].rsplit(" ", 1)[0] + "..." if len(body_text) > 150 else body_text
            excerpt_label = QLabel(excerpt)
            excerpt_label.setWordWrap(True)
            excerpt_label.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                font-size: 13px;
            """)
            content_layout.addWidget(excerpt_label)

        container_layout.addWidget(content)
        layout.addWidget(self._container)

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
        self.setFixedHeight(90)
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
        icon_label.setStyleSheet("font-size: 20px; background: transparent;")
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
            font-size: 9px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        content_layout.addWidget(category_label)

        # Headline (truncated)
        headline_text = self._data.get("headline", "Story")
        if len(headline_text) > 60:
            headline_text = headline_text[:57] + "..."

        headline_label = QLabel(headline_text)
        headline_label.setWordWrap(True)
        headline_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: 12px;
            font-weight: bold;
        """)
        content_layout.addWidget(headline_label)
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

    def set_headlines(self, headlines: List[Dict[str, Any]]):
        """
        Set headlines to display.

        Args:
            headlines: List of headline dictionaries sorted by priority
        """
        self._headlines = headlines
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
                color: {ESPN_TEXT_MUTED};
                font-style: italic;
                padding: 40px;
            """)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(empty_label)
            return

        # Featured story (first headline)
        logger.debug(f"_rebuild_ui: Creating featured story: {self._headlines[0].get('headline', 'N/A')[:50]}...")
        self._featured_widget = ESPNFeaturedStoryWidget(self._headlines[0])
        self._featured_widget.clicked.connect(self.headline_clicked.emit)
        self._layout.addWidget(self._featured_widget)
        logger.debug(f"_rebuild_ui: Featured widget added, size={self._featured_widget.sizeHint()}")

        # Thumbnail grid (remaining headlines)
        if len(self._headlines) > 1:
            self._grid_container = QWidget()
            self._grid_layout = QGridLayout(self._grid_container)
            self._grid_layout.setContentsMargins(0, 0, 0, 0)
            self._grid_layout.setSpacing(12)

            # Add up to 6 thumbnails in a 2x3 grid
            for i, headline_data in enumerate(self._headlines[1:7]):
                row = i // 2
                col = i % 2

                thumbnail = ESPNThumbnailWidget(headline_data)
                thumbnail.clicked.connect(self.headline_clicked.emit)
                self._grid_layout.addWidget(thumbnail, row, col)

            self._layout.addWidget(self._grid_container)

        self._layout.addStretch()

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
