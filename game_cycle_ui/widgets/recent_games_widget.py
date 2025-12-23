"""
Upcoming Games Widget - Displays upcoming game previews.

Part of the Team Dashboard. Shows compact game preview cards with
opponent info and click-to-expand functionality.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QCursor

from game_cycle_ui.theme import ESPN_THEME, Colors, Typography, FontSizes, TextColors


class GameResultCard(QFrame):
    """
    Compact card displaying a single game result.

    Shows:
    - Opponent name and score
    - Win/Loss indicator with color
    - Key stats (yards, turnovers)
    - Click to view full box score
    """

    clicked = Signal(str)  # Emits game_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._game_id: Optional[str] = None
        self._is_win: bool = False
        self._setup_ui()

    def _setup_ui(self):
        """Build the card layout."""
        self.setFixedHeight(90)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._set_default_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        # Top row: Result badge + Opponent + Score
        top_row = QHBoxLayout()

        self.result_badge = QLabel("W")
        self.result_badge.setFont(Typography.H6)
        self.result_badge.setFixedWidth(24)
        self.result_badge.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.result_badge)

        self.opponent_label = QLabel("vs Opponent")
        self.opponent_label.setFont(Typography.BODY_SMALL_BOLD)
        self.opponent_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        top_row.addWidget(self.opponent_label, 1)

        self.score_label = QLabel("0-0")
        self.score_label.setFont(Typography.H5)
        self.score_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.score_label.setAlignment(Qt.AlignRight)
        top_row.addWidget(self.score_label)

        layout.addLayout(top_row)

        # Week label
        self.week_label = QLabel("Week --")
        self.week_label.setFont(Typography.TINY)
        self.week_label.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        layout.addWidget(self.week_label)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.yards_label = QLabel("Yds: --")
        self.yards_label.setFont(Typography.TINY)
        self.yards_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        stats_row.addWidget(self.yards_label)

        self.turnovers_label = QLabel("TO: --")
        self.turnovers_label.setFont(Typography.TINY)
        self.turnovers_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        stats_row.addWidget(self.turnovers_label)

        stats_row.addStretch()
        layout.addLayout(stats_row)

    def _set_default_style(self):
        """Set default card styling."""
        self.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 6px; border: 1px solid #333; }}"
            f"QFrame:hover {{ border: 1px solid {ESPN_THEME['red']}; }}"
        )

    def set_game_data(
        self,
        game_id: str,
        week: int,
        opponent_name: str,
        team_score: int,
        opponent_score: int,
        is_home: bool,
        total_yards: int = 0,
        turnovers: int = 0
    ):
        """
        Populate card with game data.

        Args:
            game_id: Unique game identifier
            week: Week number (1-18 or playoff round)
            opponent_name: Opponent team name
            team_score: User team's score
            opponent_score: Opponent's score
            is_home: True if user team was home
            total_yards: Team's total yards
            turnovers: Team's turnovers
        """
        self._game_id = game_id

        # Determine win/loss
        if team_score > opponent_score:
            self._is_win = True
            self.result_badge.setText("W")
            self.result_badge.setStyleSheet(
                f"color: {TextColors.ON_DARK}; background-color: {Colors.SUCCESS}; border-radius: 4px;"
            )
        elif team_score < opponent_score:
            self._is_win = False
            self.result_badge.setText("L")
            self.result_badge.setStyleSheet(
                f"color: {TextColors.ON_DARK}; background-color: {Colors.ERROR}; border-radius: 4px;"
            )
        else:
            self._is_win = False
            self.result_badge.setText("T")
            self.result_badge.setStyleSheet(
                f"color: {TextColors.ON_DARK}; background-color: {Colors.MUTED}; border-radius: 4px;"
            )

        # Opponent
        prefix = "vs" if is_home else "@"
        self.opponent_label.setText(f"{prefix} {opponent_name}")

        # Score
        self.score_label.setText(f"{team_score}-{opponent_score}")

        # Week
        if week <= 18:
            self.week_label.setText(f"Week {week}")
        else:
            # Playoff rounds
            round_names = {19: "Wild Card", 20: "Divisional", 21: "Conference", 22: "Super Bowl"}
            self.week_label.setText(round_names.get(week, f"Week {week}"))

        # Stats
        self.yards_label.setText(f"Yds: {total_yards}")
        self.turnovers_label.setText(f"TO: {turnovers}")

    def mousePressEvent(self, event):
        """Handle click to emit game_id."""
        if self._game_id:
            self.clicked.emit(self._game_id)
        super().mousePressEvent(event)


class RecentGamesWidget(QWidget):
    """
    Widget displaying a list of recent game results.

    Shows the most recent games as compact cards with
    win/loss indicators and key stats.
    """

    game_clicked = Signal(str)  # Emits game_id when a card is clicked

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._games: List[Dict] = []
        self._cards: List[GameResultCard] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("UPCOMING GAMES")
        header.setFont(Typography.H6)
        header.setStyleSheet(f"color: {TextColors.ON_DARK};")
        layout.addWidget(header)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 8px; background: #1a1a1a; }"
            "QScrollBar::handle:vertical { background: #444; border-radius: 4px; }"
        )

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        # Empty state label
        self.empty_label = QLabel("No upcoming games")
        self.empty_label.setFont(Typography.SMALL)
        self.empty_label.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def set_games(self, games: List[Dict]):
        """
        Populate with game data.

        Args:
            games: List of game dicts with keys:
                - game_id: str
                - week: int
                - opponent_name: str
                - team_score: int
                - opponent_score: int
                - is_home: bool
                - total_yards: int (optional)
                - turnovers: int (optional)
        """
        self._games = games

        # Clear existing cards
        for card in self._cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Remove stretch
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not games:
            self.empty_label.show()
            self.cards_layout.addStretch()
            return

        self.empty_label.hide()

        # Add cards for each game
        for game_data in games:
            card = GameResultCard()
            card.set_game_data(
                game_id=game_data.get('game_id', ''),
                week=game_data.get('week', 0),
                opponent_name=game_data.get('opponent_name', 'Unknown'),
                team_score=game_data.get('team_score', 0),
                opponent_score=game_data.get('opponent_score', 0),
                is_home=game_data.get('is_home', True),
                total_yards=game_data.get('total_yards', 0),
                turnovers=game_data.get('turnovers', 0)
            )
            card.clicked.connect(self._on_card_clicked)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.cards_layout.addStretch()

    def _on_card_clicked(self, game_id: str):
        """Propagate card click to parent."""
        self.game_clicked.emit(game_id)

    def clear(self):
        """Clear all games."""
        self.set_games([])
