"""
Game of the Week Widget - Highlights the best/closest game with star players.

Displays:
- Final score with team colors
- 2-3 star players with key stats
- Clickable to open box score detail
- ESPN dark theme styling
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    ESPN_THEME,
    Colors,
    Typography,
    FontSizes,
    TextColors,
)
from team_management.teams.team_loader import get_team_by_id


class GameOfWeekWidget(QWidget):
    """
    Widget highlighting the best/closest game of the week.

    Shows:
    - Title header
    - Team matchup with final score (using team colors)
    - 2-3 star players with key stats
    - Click to view box score button

    Signals:
        game_clicked: Emitted when user clicks to view box score (emits game_id)
    """

    game_clicked = Signal(str)  # game_id

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the Game of the Week widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._game_id: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        # Main container
        self.setFixedHeight(400)  # Increased from 250 to give more space

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Card frame with ESPN styling
        self.card = QFrame()
        self.card.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {ESPN_THEME['card_bg']}; "
            f"border: none; "
            f"border-radius: 6px; "
            f"}}"
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.header_label = QLabel("GAME OF THE WEEK")
        self.header_label.setFont(Typography.H6)
        self.header_label.setStyleSheet(
            f"color: {ESPN_THEME['red']}; font-weight: bold;"
        )
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()
        card_layout.addLayout(header_layout)

        # Divider line removed per user request

        # Score section
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(0, 4, 0, 4)

        # Away team
        self.away_team_label = QLabel("AWAY")
        self.away_team_label.setFont(Typography.H4)
        self.away_team_label.setAlignment(Qt.AlignLeft)
        score_layout.addWidget(self.away_team_label)

        self.away_score_label = QLabel("0")
        self.away_score_label.setFont(Typography.H3)
        self.away_score_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.away_score_label)

        # VS separator
        vs_label = QLabel(",")
        vs_label.setFont(Typography.H5)
        vs_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        vs_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(vs_label)

        # Home team
        self.home_team_label = QLabel("HOME")
        self.home_team_label.setFont(Typography.H4)
        self.home_team_label.setAlignment(Qt.AlignLeft)
        score_layout.addWidget(self.home_team_label)

        self.home_score_label = QLabel("0")
        self.home_score_label.setFont(Typography.H3)
        self.home_score_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.home_score_label)

        score_layout.addStretch()
        card_layout.addLayout(score_layout)

        # Star players section
        self.star_players_layout = QVBoxLayout()
        self.star_players_layout.setSpacing(6)
        self.star_players_layout.setContentsMargins(0, 4, 0, 4)
        card_layout.addLayout(self.star_players_layout)

        # Empty state label
        self.empty_label = QLabel("No star players to display")
        self.empty_label.setFont(Typography.BODY_SMALL)
        self.empty_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        self.star_players_layout.addWidget(self.empty_label)

        card_layout.addStretch()

        # Click for box score button
        self.box_score_button = QPushButton("Click for box score")
        self.box_score_button.setFont(Typography.BODY_SMALL_BOLD)
        self.box_score_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.box_score_button.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {ESPN_THEME['red']}; "
            f"color: {TextColors.ON_DARK}; "
            f"border: none; "
            f"border-radius: 4px; "
            f"padding: 8px 16px; "
            f"}}"
            f"QPushButton:hover {{ "
            f"background-color: {ESPN_THEME['dark_red']}; "
            f"}}"
            f"QPushButton:pressed {{ "
            f"background-color: #770000; "
            f"}}"
        )
        self.box_score_button.clicked.connect(self._on_button_clicked)
        card_layout.addWidget(self.box_score_button)

        main_layout.addWidget(self.card)

    def set_game(self, game_data: Dict[str, Any]):
        """
        Display game data.

        Args:
            game_data: Dictionary containing:
                - game_id: str - Unique game identifier
                - home_team_id: int - Home team ID (1-32)
                - away_team_id: int - Away team ID (1-32)
                - home_score: int - Home team final score
                - away_score: int - Away team final score
                - star_players: List[Dict] - List of star players with:
                    - name: str - Player name
                    - team_abbr: str - Team abbreviation
                    - stats: List[str] - Key stat lines (e.g., "4 Total TDs")
        """
        self._game_id = game_data.get("game_id")

        # Get team data
        home_team_id = game_data.get("home_team_id")
        away_team_id = game_data.get("away_team_id")
        home_score = game_data.get("home_score", 0)
        away_score = game_data.get("away_score", 0)

        # Load team info
        home_team = get_team_by_id(home_team_id) if home_team_id else None
        away_team = get_team_by_id(away_team_id) if away_team_id else None

        # Set team names
        home_abbr = home_team.abbreviation if home_team else "HOME"
        away_abbr = away_team.abbreviation if away_team else "AWAY"

        self.home_team_label.setText(home_abbr)
        self.away_team_label.setText(away_abbr)

        # Set scores with team colors
        home_color = home_team.colors.get("primary", TextColors.ON_DARK) if home_team else TextColors.ON_DARK
        away_color = away_team.colors.get("primary", TextColors.ON_DARK) if away_team else TextColors.ON_DARK

        self.home_team_label.setStyleSheet(f"color: {home_color}; font-weight: bold;")
        self.away_team_label.setStyleSheet(f"color: {away_color}; font-weight: bold;")

        # Highlight winning score
        if home_score > away_score:
            self.home_score_label.setStyleSheet(f"color: {home_color}; font-weight: bold;")
            self.away_score_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        elif away_score > home_score:
            self.away_score_label.setStyleSheet(f"color: {away_color}; font-weight: bold;")
            self.home_score_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        else:
            # Tie
            self.home_score_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            self.away_score_label.setStyleSheet(f"color: {TextColors.ON_DARK};")

        self.home_score_label.setText(str(home_score))
        self.away_score_label.setText(str(away_score))

        # Clear existing star players
        self._clear_star_players()

        # Add star players
        star_players = game_data.get("star_players", [])
        if star_players:
            self.empty_label.hide()
            for player_data in star_players[:3]:  # Limit to 3 players
                self._add_star_player(player_data)
        else:
            self.empty_label.show()

    def _clear_star_players(self):
        """Remove all star player widgets."""
        # Remove all widgets except the empty label
        while self.star_players_layout.count() > 1:
            item = self.star_players_layout.takeAt(0)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

    def _add_star_player(self, player_data: Dict[str, Any]):
        """
        Add a star player to the display.

        Args:
            player_data: Dictionary containing:
                - name: str - Player name
                - team_abbr: str - Team abbreviation
                - stats: List[str] - Stat lines
        """
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(2)

        # Player name with star icon
        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)

        star_icon = QLabel("★")
        star_icon.setFont(Typography.BODY)
        star_icon.setStyleSheet(f"color: {ESPN_THEME['red']};")
        star_icon.setFixedWidth(20)
        name_layout.addWidget(star_icon)

        player_name = player_data.get("name", "Unknown Player")
        team_abbr = player_data.get("team_abbr", "")

        name_label = QLabel(f"{player_name} ({team_abbr})")
        name_label.setFont(Typography.BODY_BOLD)
        name_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        name_layout.addWidget(name_label)
        name_layout.addStretch()

        player_layout.addLayout(name_layout)

        # Stats
        stats = player_data.get("stats", [])
        for stat_line in stats:
            stat_label = QLabel(f"  - {stat_line}")
            stat_label.setFont(Typography.BODY_SMALL)
            stat_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
            player_layout.addWidget(stat_label)

        # Add to layout (before empty label if it exists)
        insert_index = max(0, self.star_players_layout.count() - 1)
        self.star_players_layout.insertWidget(insert_index, player_container)

    def clear(self):
        """Clear the widget display."""
        self._game_id = None
        self.home_team_label.setText("HOME")
        self.away_team_label.setText("AWAY")
        self.home_score_label.setText("0")
        self.away_score_label.setText("0")

        # Reset colors
        self.home_team_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        self.away_team_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        self.home_score_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.away_score_label.setStyleSheet(f"color: {TextColors.ON_DARK};")

        # Clear star players
        self._clear_star_players()
        self.empty_label.show()

    def _on_button_clicked(self):
        """Handle box score button click."""
        if self._game_id:
            self.game_clicked.emit(self._game_id)
