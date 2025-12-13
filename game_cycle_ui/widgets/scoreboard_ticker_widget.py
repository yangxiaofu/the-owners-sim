"""
ScoreboardTickerWidget - ESPN-style horizontal scrolling scoreboard.

Displays game scores in a horizontal ticker bar at the top of the Media view.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_CARD_HOVER,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
    ESPN_BORDER,
)


class GameScoreCard(QFrame):
    """Individual game score card in the ticker."""

    clicked = Signal(str)  # game_id

    def __init__(
        self,
        game_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._game_data = game_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the score card UI."""
        self.setFixedWidth(140)
        self.setFixedHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Determine if game is final or in progress
        is_final = self._game_data.get("is_final", True)

        # Card styling
        self.setStyleSheet(f"""
            GameScoreCard {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {ESPN_BORDER};
                border-radius: 4px;
            }}
            GameScoreCard:hover {{
                border: 1px solid {ESPN_RED};
                background-color: {ESPN_CARD_HOVER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Away team row
        away_row = QHBoxLayout()
        away_row.setSpacing(4)

        away_abbr = self._game_data.get("away_abbr", "AWY")
        away_score = self._game_data.get("away_score", 0)
        away_won = away_score > self._game_data.get("home_score", 0)

        away_label = QLabel(away_abbr)
        away_label.setStyleSheet(
            f"color: {ESPN_TEXT_PRIMARY if away_won else ESPN_TEXT_SECONDARY}; font-size: 11px; font-weight: {'bold' if away_won else 'normal'};"
        )
        away_row.addWidget(away_label)
        away_row.addStretch()

        away_score_label = QLabel(str(away_score))
        away_score_label.setStyleSheet(
            f"color: {ESPN_TEXT_PRIMARY if away_won else ESPN_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;"
        )
        away_row.addWidget(away_score_label)

        layout.addLayout(away_row)

        # Home team row
        home_row = QHBoxLayout()
        home_row.setSpacing(4)

        home_abbr = self._game_data.get("home_abbr", "HME")
        home_score = self._game_data.get("home_score", 0)
        home_won = home_score > away_score

        home_label = QLabel(home_abbr)
        home_label.setStyleSheet(
            f"color: {ESPN_TEXT_PRIMARY if home_won else ESPN_TEXT_SECONDARY}; font-size: 11px; font-weight: {'bold' if home_won else 'normal'};"
        )
        home_row.addWidget(home_label)
        home_row.addStretch()

        home_score_label = QLabel(str(home_score))
        home_score_label.setStyleSheet(
            f"color: {ESPN_TEXT_PRIMARY if home_won else ESPN_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;"
        )
        home_row.addWidget(home_score_label)

        layout.addLayout(home_row)

        # Status row (Final, Q4, etc.)
        status = "FINAL" if is_final else self._game_data.get("status", "")
        status_label = QLabel(status)
        status_label.setStyleSheet(
            f"color: {ESPN_RED}; font-size: 9px; font-weight: bold;" if not is_final
            else f"color: {ESPN_TEXT_MUTED}; font-size: 9px;"
        )
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

    def mousePressEvent(self, event):
        """Handle click to emit game_id."""
        game_id = self._game_data.get("game_id", "")
        if game_id:
            self.clicked.emit(game_id)
        super().mousePressEvent(event)


class ScoreboardTickerWidget(QWidget):
    """
    ESPN-style horizontal scoreboard ticker.

    Features:
    - Horizontal scrolling list of game scores
    - Left/right navigation arrows
    - Click on game to view details
    """

    game_clicked = Signal(str)  # game_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._games: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the ticker UI."""
        self.setFixedHeight(90)
        self.setStyleSheet(f"""
            ScoreboardTickerWidget {{
                background-color: {ESPN_DARK_BG};
                border-bottom: 2px solid {ESPN_RED};
            }}
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left arrow button
        self._left_btn = QPushButton("<")
        self._left_btn.setFixedSize(30, 70)
        self._left_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_CARD_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ESPN_RED};
            }}
            QPushButton:disabled {{
                color: #444444;
            }}
        """)
        self._left_btn.clicked.connect(self._scroll_left)
        main_layout.addWidget(self._left_btn)

        # Scroll area for game cards
        self._scroll_area = QScrollArea()
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        # Container for game cards
        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background-color: transparent;")
        self._cards_layout = QHBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        self._scroll_area.setWidget(self._cards_container)
        main_layout.addWidget(self._scroll_area)

        # Right arrow button
        self._right_btn = QPushButton(">")
        self._right_btn.setFixedSize(30, 70)
        self._right_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_CARD_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ESPN_RED};
            }}
            QPushButton:disabled {{
                color: #444444;
            }}
        """)
        self._right_btn.clicked.connect(self._scroll_right)
        main_layout.addWidget(self._right_btn)

    def set_games(self, games: List[Dict[str, Any]]):
        """
        Set the games to display in the ticker.

        Args:
            games: List of game dicts with keys:
                - game_id: str
                - home_abbr: str
                - away_abbr: str
                - home_score: int
                - away_score: int
                - is_final: bool
                - status: str (optional)
        """
        self._games = games

        # Clear existing cards
        while self._cards_layout.count() > 1:  # Keep stretch
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add game cards
        for game in games:
            card = GameScoreCard(game)
            card.clicked.connect(self.game_clicked.emit)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        # Update button states
        self._update_button_states()

    def _scroll_left(self):
        """Scroll ticker left."""
        scroll_bar = self._scroll_area.horizontalScrollBar()
        scroll_bar.setValue(scroll_bar.value() - 300)
        self._update_button_states()

    def _scroll_right(self):
        """Scroll ticker right."""
        scroll_bar = self._scroll_area.horizontalScrollBar()
        scroll_bar.setValue(scroll_bar.value() + 300)
        self._update_button_states()

    def _update_button_states(self):
        """Update enabled state of navigation buttons."""
        scroll_bar = self._scroll_area.horizontalScrollBar()
        self._left_btn.setEnabled(scroll_bar.value() > scroll_bar.minimum())
        self._right_btn.setEnabled(scroll_bar.value() < scroll_bar.maximum())
