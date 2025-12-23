"""
NewsRailWidget - Collapsible news sidebar for breaking headlines.

Displays breaking news across all views with auto-expand functionality.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QCursor

from game_cycle import Stage
from game_cycle_ui.theme import (
    ESPN_RED,
    ESPN_DARK_RED,
    ESPN_CARD_BG,
    ESPN_BORDER,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    FontSizes,
)


class HeadlineCard(QWidget):
    """Small headline card for news rail."""

    clicked = Signal(int)  # headline_id

    def __init__(self, headline_data: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._headline_data = headline_data
        self._setup_ui()

    def _setup_ui(self):
        """Setup the headline card UI."""
        self.setStyleSheet(f"""
            QWidget {{
                background: {ESPN_CARD_BG};
                border-bottom: 1px solid {ESPN_BORDER};
                padding: 8px;
            }}
            QWidget:hover {{
                background: #252525;
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Headline text (truncated)
        headline_text = self._headline_data.get("headline", "")
        if len(headline_text) > 60:
            headline_text = headline_text[:57] + "..."

        headline_label = QLabel(headline_text)
        headline_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: {FontSizes.SMALL};
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        headline_label.setWordWrap(True)
        layout.addWidget(headline_label)

        # Timestamp (relative)
        timestamp_label = QLabel(self._get_relative_time())
        timestamp_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.TINY};
            background: transparent;
            border: none;
        """)
        layout.addWidget(timestamp_label)

    def _get_relative_time(self) -> str:
        """Get relative time string (e.g., '2 min ago')."""
        # Placeholder - would need actual timestamp from headline_data
        return "Just now"

    def mousePressEvent(self, event):
        """Handle click event."""
        if event.button() == Qt.MouseButton.LeftButton:
            headline_id = self._headline_data.get("id", 0)
            self.clicked.emit(headline_id)
        super().mousePressEvent(event)


class NewsRailWidget(QWidget):
    """
    Collapsible news sidebar showing breaking headlines.

    Signals:
        headline_clicked(int): Emitted when a headline is clicked (headline_id)
        show_all_clicked: Emitted when "Show All" link is clicked
    """

    headline_clicked = Signal(int)
    show_all_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._is_expanded = False
        self._headlines: List[Dict[str, Any]] = []
        self._auto_collapse_timer: Optional[QTimer] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the news rail UI."""
        self.setStyleSheet(f"""
            QWidget {{
                background: {ESPN_CARD_BG};
                border-right: 1px solid {ESPN_BORDER};
            }}
        """)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toggle button (always visible)
        self._toggle_btn = QPushButton("🔴 LATEST (0)")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ESPN_RED};
                color: white;
                border: none;
                border-radius: 0;
                padding: 12px;
                font-weight: bold;
                font-size: {FontSizes.SMALL};
                text-align: left;
            }}
            QPushButton:hover {{
                background: {ESPN_DARK_RED};
            }}
        """)
        self._toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._toggle_btn.clicked.connect(self._toggle_expansion)
        layout.addWidget(self._toggle_btn)

        # Scrollable headlines container (initially hidden)
        self._headlines_scroll = QScrollArea()
        self._headlines_scroll.setWidgetResizable(True)
        self._headlines_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._headlines_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {ESPN_CARD_BG};
                border: none;
            }}
        """)
        self._headlines_scroll.setVisible(False)

        # Container for headline cards
        self._headlines_container = QWidget()
        self._headlines_layout = QVBoxLayout(self._headlines_container)
        self._headlines_layout.setContentsMargins(0, 0, 0, 0)
        self._headlines_layout.setSpacing(0)
        self._headlines_layout.addStretch()

        self._headlines_scroll.setWidget(self._headlines_container)
        layout.addWidget(self._headlines_scroll, 1)

        # "Show All" link at bottom
        self._show_all = QLabel('<a href="#" style="color: #888888; text-decoration: none;">Show All →</a>')
        self._show_all.setStyleSheet(f"""
            QLabel {{
                background: {ESPN_CARD_BG};
                padding: 8px 12px;
                border-top: 1px solid {ESPN_BORDER};
                font-size: {FontSizes.SMALL};
            }}
            QLabel:hover {{
                background: #252525;
            }}
        """)
        self._show_all.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._show_all.linkActivated.connect(lambda: self.show_all_clicked.emit())
        self._show_all.setVisible(False)
        layout.addWidget(self._show_all)

    def set_breaking_news(self, headlines: List[Dict[str, Any]]):
        """
        Update with latest breaking news.

        Args:
            headlines: List of headline dictionaries with priority >= 50
        """
        # Filter for top headlines (priority >= 50 or high-priority types)
        breaking = [
            h for h in headlines
            if h.get("priority", 0) >= 50
            or h.get("headline_type") in ("UPSET", "TRADE", "INJURY", "FRANCHISE_TAG", "SIGNING")
        ]
        self._headlines = breaking[:10]  # Max 10 headlines (balanced mix)

        count = len(self._headlines)
        self._toggle_btn.setText(f"🔴 LATEST ({count})")

        # Clear existing headline cards
        while self._headlines_layout.count() > 1:  # Keep the stretch
            item = self._headlines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new headline cards
        for headline_data in self._headlines:
            card = HeadlineCard(headline_data)
            card.clicked.connect(self.headline_clicked.emit)
            self._headlines_layout.insertWidget(self._headlines_layout.count() - 1, card)

        # Auto-expand if new breaking news arrived
        if count > 0 and not self._is_expanded:
            self._auto_expand()

    def _auto_expand(self):
        """Auto-expand for 10 seconds when new breaking news arrives."""
        self._is_expanded = True
        self._headlines_scroll.setVisible(True)
        self._show_all.setVisible(True)
        self._toggle_btn.setText(self._toggle_btn.text().replace("▼", "▲"))

        # Auto-collapse after 10 seconds
        if self._auto_collapse_timer:
            self._auto_collapse_timer.stop()

        self._auto_collapse_timer = QTimer(self)
        self._auto_collapse_timer.setSingleShot(True)
        self._auto_collapse_timer.timeout.connect(self._collapse)
        self._auto_collapse_timer.start(10000)  # 10 seconds

    def _collapse(self):
        """Collapse the news rail."""
        self._is_expanded = False
        self._headlines_scroll.setVisible(False)
        self._show_all.setVisible(False)
        self._toggle_btn.setText(self._toggle_btn.text().replace("▲", "▼"))

    def _toggle_expansion(self):
        """Toggle sidebar expansion."""
        if self._auto_collapse_timer:
            self._auto_collapse_timer.stop()

        if self._is_expanded:
            self._collapse()
        else:
            self._is_expanded = True
            self._headlines_scroll.setVisible(True)
            self._show_all.setVisible(True)
            self._toggle_btn.setText(self._toggle_btn.text().replace("▼", "▲"))

    def refresh(self, db_path: str, dynasty_id: str, season: int, current_stage: Optional[Stage]):
        """
        Refresh headlines from database.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty ID
            season: Current season
            current_stage: Current game stage
        """
        db = None
        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.media_coverage_api import MediaCoverageAPI
            from game_cycle.stage_definitions import SeasonPhase

            db = GameCycleDatabase(db_path)
            media_api = MediaCoverageAPI(db)

            # Determine if regular season or playoffs/offseason
            if current_stage and current_stage.phase == SeasonPhase.REGULAR_SEASON:
                # Extract week number from stage type (REGULAR_WEEK_1 -> week 1)
                week = int(current_stage.stage_type.name.replace("REGULAR_WEEK_", ""))
                # API expects completed_week: shows recaps for that week + previews for week+1
                # Stage week is the week to simulate, so completed week = week - 1
                completed_week = max(1, week - 1)
                headlines = media_api.get_headlines_for_display(dynasty_id, season, completed_week, limit=50)
            else:
                # Playoffs/offseason: use rolling headlines
                headlines = media_api.get_rolling_headlines(dynasty_id, season, limit=50)

            # Convert Headline dataclasses to dicts for set_breaking_news()
            headlines_dicts = [
                {
                    "id": h.id,
                    "headline": h.headline,
                    "headline_type": h.headline_type,
                    "priority": h.priority,
                    "subheadline": h.subheadline,
                    "body_text": h.body_text,
                }
                for h in headlines
            ]

            # Debug logging to diagnose empty headlines
            phase_name = current_stage.phase.name if current_stage else "UNKNOWN"
            week = current_stage.week_number if current_stage and hasattr(current_stage, 'week_number') else "N/A"
            print(f"[NEWS_RAIL] Loaded {len(headlines)} headlines for dynasty={dynasty_id}, season={season}, week={week}, phase={phase_name}")

            self.set_breaking_news(headlines_dicts)

        except Exception as e:
            # Log error with traceback for debugging
            print(f"[NEWS_RAIL] ERROR: Failed to refresh news rail: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if db is not None:
                db.close()
