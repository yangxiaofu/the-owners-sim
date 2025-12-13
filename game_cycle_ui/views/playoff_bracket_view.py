"""
Playoff Bracket View - Compact table-based playoff bracket display.

Dynasty-First Architecture:
- Displays playoff matchups for all rounds
- Updates automatically when stage changes
- Shows teams, seeds, scores, and winners
"""

from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.dialogs.box_score_dialog import BoxScoreDialog
from game_cycle_ui.theme import TABLE_HEADER_STYLE


class PlayoffBracketView(QWidget):
    """
    Compact table-based playoff bracket display.

    Shows all 4 playoff rounds in horizontal layout:
    - Wild Card (6 games)
    - Divisional (4 games)
    - Conference Championships (2 games)
    - Super Bowl (1 game)
    """

    # Signals
    simulate_round_requested = Signal()

    # Week numbers for playoff rounds
    WEEK_WILD_CARD = 19
    WEEK_DIVISIONAL = 20
    WEEK_CONFERENCE = 21
    WEEK_SUPER_BOWL = 22

    # Colors
    WINNER_COLOR = QColor("#2E7D32")  # Green
    AFC_COLOR = QColor("#1976D2")  # Blue
    NFC_COLOR = QColor("#C62828")  # Red

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Context for BoxScoreDialog
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        # Cache for GameResult objects (play-by-play data)
        self._game_results_cache: Dict[str, Any] = {}
        self._setup_ui()

    def set_context(self, dynasty_id: str, db_path: str):
        """Store dynasty context for opening box scores."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def store_game_results(self, games_played: List[Dict[str, Any]]):
        """
        Cache GameResult objects from simulated playoff games for play-by-play access.

        Args:
            games_played: List of game result dicts, each containing:
                - game_id: Unique game identifier
                - game_result: GameSimulationResult object with drives/plays data
        """
        print(f"[PlayoffBracketView] store_game_results called with {len(games_played)} games")
        for game in games_played:
            game_id = game.get("game_id")
            game_result = game.get("game_result")
            if game_id and game_result:
                self._game_results_cache[game_id] = game_result
                print(f"[PlayoffBracketView] Cached game_result for {game_id}")

    def _setup_ui(self):
        """Build the layout with 4 tables (one per round)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Header row with title and simulate button
        header_layout = QHBoxLayout()

        header = QLabel("NFL PLAYOFFS")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.simulate_btn = QPushButton("Simulate Round")
        self.simulate_btn.setStyleSheet(
            "QPushButton { background-color: #388E3C; color: white; "
            "border-radius: 4px; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2E7D32; }"
        )
        self.simulate_btn.clicked.connect(self.simulate_round_requested.emit)
        header_layout.addWidget(self.simulate_btn)

        layout.addLayout(header_layout)

        # Scroll area for round tables
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        rounds_layout = QHBoxLayout(scroll_content)
        rounds_layout.setSpacing(15)

        # Create table for each round
        self.wild_card_group = self._create_round_table("Wild Card", 6)
        self.divisional_group = self._create_round_table("Divisional", 4)
        self.conference_group = self._create_round_table("Conference", 2)
        self.super_bowl_group = self._create_round_table("Super Bowl", 1)

        rounds_layout.addWidget(self.wild_card_group)
        rounds_layout.addWidget(self.divisional_group)
        rounds_layout.addWidget(self.conference_group)
        rounds_layout.addWidget(self.super_bowl_group)
        rounds_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Status label
        self.status_label = QLabel("Select a dynasty and simulate through playoffs")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

    def _create_round_table(self, title: str, num_games: int) -> QGroupBox:
        """Create a grouped table for one round."""
        group = QGroupBox(title)
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        group.setMinimumWidth(280)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 10, 5, 5)

        table = QTableWidget(num_games, 4)
        table.setHorizontalHeaderLabels(["Away", "Home", "Score", "Status"])
        table.setObjectName("round_table")

        # Configure table
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setShowGrid(True)
        table.setAlternatingRowColors(True)

        # Connect double-click to open box score
        table.cellDoubleClicked.connect(
            lambda row, col, t=table: self._on_game_double_clicked(t, row)
        )

        # Configure columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Away
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Home
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Score
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Status
        table.setColumnWidth(2, 60)
        table.setColumnWidth(3, 50)

        # Row height
        table.verticalHeader().setDefaultSectionSize(35)
        table.verticalHeader().setVisible(False)

        # Calculate height based on games
        table_height = num_games * 35 + 30  # rows + header
        table.setMaximumHeight(table_height)

        layout.addWidget(table)

        return group

    def _get_table(self, group: QGroupBox) -> QTableWidget:
        """Get the table widget from a group box."""
        return group.findChild(QTableWidget, "round_table")

    def set_bracket_data(self, bracket_data: Dict[str, Any]):
        """
        Update all tables with current playoff state.

        Args:
            bracket_data: Dict with keys:
                - wild_card: List of game dicts
                - divisional: List of game dicts
                - conference: List of game dicts
                - super_bowl: List of game dicts
                - season: Season year
        """
        season = bracket_data.get("season", 2025)

        wild_card = bracket_data.get("wild_card", [])
        divisional = bracket_data.get("divisional", [])
        conference = bracket_data.get("conference", [])
        super_bowl = bracket_data.get("super_bowl", [])

        self._populate_table(self.wild_card_group, wild_card)
        self._populate_table(self.divisional_group, divisional)
        self._populate_table(self.conference_group, conference)
        self._populate_table(self.super_bowl_group, super_bowl)

        # Update status
        total_games = len(wild_card) + len(divisional) + len(conference) + len(super_bowl)
        played_games = sum(
            1 for games in [wild_card, divisional, conference, super_bowl]
            for g in games if g.get("is_played")
        )

        if total_games == 0:
            self.status_label.setText(f"No playoff games scheduled yet for {season}")
        elif played_games == total_games:
            self.status_label.setText(f"{season} Playoffs Complete!")
        else:
            self.status_label.setText(f"{season} Playoffs: {played_games}/{total_games} games played")

    # Color for placeholder/TBD entries
    PLACEHOLDER_COLOR = QColor("#999")

    def _populate_table(self, group: QGroupBox, games: List[Dict[str, Any]]):
        """Fill table rows with game data."""
        table = self._get_table(group)
        if table is None:
            return

        # Clear existing content
        table.clearContents()

        for row, game in enumerate(games):
            if row >= table.rowCount():
                break

            away_team = game.get("away_team", {})
            home_team = game.get("home_team", {})
            is_played = game.get("is_played", False)
            is_placeholder = game.get("is_placeholder", False)
            home_score = game.get("home_score")
            away_score = game.get("away_score")
            winner_id = game.get("winner_id")

            # Away team column: "#7 MIA" or "TBD" for placeholders
            away_abbrev = away_team.get("abbrev", "???")
            away_seed = away_team.get("seed", "")

            # For placeholders, don't show "?" seeds, just show team text
            if is_placeholder:
                away_text = away_abbrev
            elif away_seed and away_seed != "?":
                away_text = f"#{away_seed} {away_abbrev}"
            else:
                away_text = away_abbrev

            away_item = QTableWidgetItem(away_text)
            away_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Style placeholder entries in gray italic
            if is_placeholder:
                away_item.setForeground(self.PLACEHOLDER_COLOR)
                font = away_item.font()
                font.setItalic(True)
                away_item.setFont(font)
            # Highlight winner
            elif is_played and winner_id == away_team.get("id"):
                away_item.setForeground(self.WINNER_COLOR)
                font = away_item.font()
                font.setBold(True)
                away_item.setFont(font)

            # Store game data for double-click handler
            away_item.setData(Qt.ItemDataRole.UserRole, {
                'game_id': game.get('game_id'),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'is_played': is_played
            })

            table.setItem(row, 0, away_item)

            # Home team column: "#2 BUF" or "TBD" for placeholders
            home_abbrev = home_team.get("abbrev", "???")
            home_seed = home_team.get("seed", "")

            if is_placeholder:
                home_text = home_abbrev
            elif home_seed and home_seed != "?":
                home_text = f"#{home_seed} {home_abbrev}"
            else:
                home_text = home_abbrev

            home_item = QTableWidgetItem(home_text)
            home_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Style placeholder entries in gray italic
            if is_placeholder:
                home_item.setForeground(self.PLACEHOLDER_COLOR)
                font = home_item.font()
                font.setItalic(True)
                home_item.setFont(font)
            # Highlight winner
            elif is_played and winner_id == home_team.get("id"):
                home_item.setForeground(self.WINNER_COLOR)
                font = home_item.font()
                font.setBold(True)
                home_item.setFont(font)

            table.setItem(row, 1, home_item)

            # Score column: "24-31" or "@" for pending or "-" for placeholders
            if is_played and home_score is not None and away_score is not None:
                score_text = f"{away_score}-{home_score}"
                score_item = QTableWidgetItem(score_text)
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 2, score_item)
            elif is_placeholder:
                # Show "-" for placeholder matchups
                vs_item = QTableWidgetItem("-")
                vs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                vs_item.setForeground(self.PLACEHOLDER_COLOR)
                table.setItem(row, 2, vs_item)
            else:
                vs_item = QTableWidgetItem("@")
                vs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                vs_item.setForeground(QColor("#999"))
                table.setItem(row, 2, vs_item)

            # Status column
            if is_placeholder:
                status_item = QTableWidgetItem("TBD")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(self.PLACEHOLDER_COLOR)
                font = status_item.font()
                font.setPointSize(8)
                font.setItalic(True)
                status_item.setFont(font)
            elif is_played:
                status_item = QTableWidgetItem("FINAL")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(QColor("#666"))
                font = status_item.font()
                font.setPointSize(8)
                status_item.setFont(font)
            else:
                status_item = QTableWidgetItem("")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            table.setItem(row, 3, status_item)

        # Fill empty rows with placeholders
        for row in range(len(games), table.rowCount()):
            for col in range(4):
                item = QTableWidgetItem("-" if col < 2 else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#CCC"))
                table.setItem(row, col, item)

    def clear(self):
        """Clear all tables."""
        for group in [self.wild_card_group, self.divisional_group,
                      self.conference_group, self.super_bowl_group]:
            table = self._get_table(group)
            if table:
                table.clearContents()
        self.status_label.setText("No playoff data")

    def _on_game_double_clicked(self, table: QTableWidget, row: int):
        """Handle double-click on a game row to open box score."""
        if not self._dynasty_id or not self._db_path:
            print("[PlayoffBracketView] No context set - cannot open box score")
            return

        item = table.item(row, 0)  # Get away team item (column 0)
        if not item:
            return

        game_data = item.data(Qt.ItemDataRole.UserRole)
        if not game_data:
            return

        if not game_data.get('is_played'):
            return  # Game not played yet

        game_id = game_data.get('game_id')
        if not game_id:
            return

        # Extract team info for dialog
        home_team = game_data.get('home_team', {})
        away_team = game_data.get('away_team', {})
        home_score = game_data.get('home_score', 0)
        away_score = game_data.get('away_score', 0)

        # Try to get GameResult from cache (for play-by-play)
        game_result = self._game_results_cache.get(game_id)
        if game_result:
            print(f"[PlayoffBracketView] Found cached GameResult for {game_id} - play-by-play available")
        else:
            print(f"[PlayoffBracketView] No cached GameResult for {game_id} - no play-by-play available")

        # Open box score dialog
        dialog = BoxScoreDialog(
            game_id=game_id,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            game_result=game_result,  # Pass GameResult for play-by-play
            parent=self
        )
        dialog.exec()
