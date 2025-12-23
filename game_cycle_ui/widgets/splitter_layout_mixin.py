"""
SplitterLayoutMixin - Reusable mixin for views with horizontal splitter layout.

Provides consistent implementation for the common offseason view pattern:
- Header/Summary section (full width)
- Horizontal splitter (60/40 default ratio)
  - Left panel: Main content (table, etc.)
  - Right panel: Sidebar (scrollable)
- Footer section (optional, full width)

Used by: FranchiseTagView, ResigningView, DraftView, TradingView, AwardsView, StageView
"""

from typing import Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QScrollArea, QFrame
)
from PySide6.QtCore import Qt


class SplitterLayoutMixin:
    """
    Mixin for views with horizontal splitter layout.

    Provides standard methods for creating:
    - Horizontal splitter with configurable ratio
    - Scrollable sidebar panel with consistent styling

    Example usage:
        class MyView(QWidget, SplitterLayoutMixin):
            def _setup_ui(self):
                layout = QVBoxLayout(self)

                # Create left panel content
                left = self._create_left_panel()

                # Create right panel content layout
                right_layout = QVBoxLayout()
                self._add_sidebar_content(right_layout)
                right_layout.addStretch()

                # Create scrollable sidebar
                right = self._create_scrollable_sidebar(right_layout)

                # Create splitter and add to layout
                splitter = self._create_content_splitter(left, right)
                layout.addWidget(splitter, stretch=1)
    """

    def _create_content_splitter(
        self,
        left_widget: QWidget,
        right_widget: QWidget,
        ratio: Tuple[int, int] = (600, 400)
    ) -> QSplitter:
        """
        Create horizontal splitter with standard configuration.

        Args:
            left_widget: Widget for left panel (typically main table)
            right_widget: Widget for right panel (typically sidebar)
            ratio: Initial size ratio as (left, right) tuple. Default (600, 400) = 60/40

        Returns:
            Configured QSplitter widget
        """
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes(list(ratio))
        return splitter

    def _create_scrollable_sidebar(
        self,
        content_layout: QVBoxLayout,
        left_margin: int = 4
    ) -> QScrollArea:
        """
        Create scrollable right panel with standard styling.

        Args:
            content_layout: QVBoxLayout with sidebar content
            left_margin: Left margin inside scroll area (default 4px for splitter gap)

        Returns:
            Configured QScrollArea widget
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 8px; background: #1a1a1a; }"
            "QScrollBar::handle:vertical { background: #444; border-radius: 4px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        # Content widget
        content = QWidget()
        content_layout.setContentsMargins(left_margin, 0, 0, 0)
        content.setLayout(content_layout)
        scroll.setWidget(content)

        return scroll

    def _create_left_panel_container(
        self,
        right_margin: int = 4
    ) -> Tuple[QWidget, QVBoxLayout]:
        """
        Create container widget for left panel content.

        Args:
            right_margin: Right margin for gap before splitter (default 4px)

        Returns:
            Tuple of (container widget, layout for content)
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, right_margin, 0)
        layout.setSpacing(8)
        return panel, layout
