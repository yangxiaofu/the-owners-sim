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
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class PlayoffBracketView(QWidget):
    """
    Compact table-based playoff bracket display.

    Shows all 4 playoff rounds in horizontal layout:
    - Wild Card (6 games)
    - Divisional (4 games)
    - Conference Championships (2 games)
    - Super Bowl (1 game)
    """

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
        self._setup_ui()

    def _setup_ui(self):
        """Build the layout with 4 tables (one per round)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Header
        header = QLabel("NFL PLAYOFFS")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

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
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setShowGrid(True)
        table.setAlternatingRowColors(True)

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
            home_score = game.get("home_score")
            away_score = game.get("away_score")
            winner_id = game.get("winner_id")

            # Away team column: "#7 MIA"
            away_abbrev = away_team.get("abbrev", "???")
            away_seed = away_team.get("seed", "")
            away_text = f"#{away_seed} {away_abbrev}" if away_seed else away_abbrev
            away_item = QTableWidgetItem(away_text)
            away_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Highlight winner
            if is_played and winner_id == away_team.get("id"):
                away_item.setForeground(self.WINNER_COLOR)
                font = away_item.font()
                font.setBold(True)
                away_item.setFont(font)

            table.setItem(row, 0, away_item)

            # Home team column: "#2 BUF"
            home_abbrev = home_team.get("abbrev", "???")
            home_seed = home_team.get("seed", "")
            home_text = f"#{home_seed} {home_abbrev}" if home_seed else home_abbrev
            home_item = QTableWidgetItem(home_text)
            home_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Highlight winner
            if is_played and winner_id == home_team.get("id"):
                home_item.setForeground(self.WINNER_COLOR)
                font = home_item.font()
                font.setBold(True)
                home_item.setFont(font)

            table.setItem(row, 1, home_item)

            # Score column: "24-31"
            if is_played and home_score is not None and away_score is not None:
                score_text = f"{away_score}-{home_score}"
                score_item = QTableWidgetItem(score_text)
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 2, score_item)
            else:
                vs_item = QTableWidgetItem("@")
                vs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                vs_item.setForeground(QColor("#999"))
                table.setItem(row, 2, vs_item)

            # Status column
            status_item = QTableWidgetItem("FINAL" if is_played else "")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_played:
                status_item.setForeground(QColor("#666"))
                font = status_item.font()
                font.setPointSize(8)
                status_item.setFont(font)
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
