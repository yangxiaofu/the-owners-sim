"""
Standings Table Widget - Displays NFL standings with division tables.

Shows standings for a selected conference (AFC/NFC) with 4 division tables
(North, South, East, West). Includes playoff seed highlighting, win percentage,
point differential, streak, and split records.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFrame, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from game_cycle_ui.theme import (
    ESPN_THEME, TABLE_HEADER_STYLE, SECONDARY_BUTTON_STYLE, Colors,
    Typography, FontSizes, TextColors
)


# Division order for display
DIVISIONS = ["North", "South", "East", "West"]

# Playoff seed colors (1-7)
PLAYOFF_SEED_COLORS = {
    1: "#FFD700",  # Gold - 1st seed (bye)
    2: "#C0C0C0",  # Silver - 2nd seed (bye)
    3: "#CD7F32",  # Bronze - Division winner
    4: "#8B7355",  # Dark bronze - Division winner
    5: "#4A90D9",  # Blue - Wild card
    6: "#4A90D9",  # Blue - Wild card
    7: "#4A90D9",  # Blue - Wild card
}

PLAYOFF_SEED_TEXT_COLORS = {
    1: "#000000",  # Black on gold
    2: "#000000",  # Black on silver
    3: "#FFFFFF",  # White on bronze
    4: "#FFFFFF",  # White on dark bronze
    5: "#FFFFFF",  # White on blue
    6: "#FFFFFF",  # White on blue
    7: "#FFFFFF",  # White on blue
}


class DivisionTableWidget(QTableWidget):
    """
    Single division standings table.

    Displays one division's standings with columns:
    Team, W, L, T, PCT, PF, PA, DIFF, STRK, HOME, AWAY, DIV
    """

    def __init__(self, division_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.division_name = division_name

        # Configure table
        self.setColumnCount(12)
        self.setHorizontalHeaderLabels([
            "Team", "W", "L", "T", "PCT", "PF", "PA", "DIFF", "STRK", "HOME", "AWAY", "DIV"
        ])

        # Table appearance
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(False)  # Manual row coloring
        self.verticalHeader().setVisible(False)
        self.setFont(Typography.TABLE)  # 11px Arial
        self.verticalHeader().setDefaultSectionSize(32)
        self.setMaximumHeight(32 * 5 + 35)  # 4 teams + header + padding

        # Column sizing
        header = self.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Team name stretches
        for col in range(1, 12):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Dark theme styling
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ESPN_THEME['card_bg']};
                gridline-color: {ESPN_THEME['border']};
                color: white;
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {ESPN_THEME['border']};
            }}
            QTableWidget::item:selected {{
                background-color: #2a4a6a;
            }}
        """)

    def populate(self, teams: List[Dict]):
        """
        Populate the division table with team data.

        Args:
            teams: List of team dicts with standings data, pre-sorted by division rank
        """
        self.setRowCount(len(teams))

        for row, team in enumerate(teams):
            self._populate_row(row, team)

    def _populate_row(self, row: int, team: Dict):
        """Populate a single team row."""
        # Team abbreviation
        team_abbrev = team.get('team_abbrev', team.get('team_name', 'UNK'))
        team_item = QTableWidgetItem(team_abbrev)
        team_item.setFont(Typography.BODY_SMALL_BOLD)  # 11px Arial Bold

        # Check if division leader (first in division)
        is_division_leader = row == 0

        # Check playoff seed for highlighting
        playoff_seed = team.get('playoff_seed')

        # Apply playoff seed highlighting
        if playoff_seed and 1 <= playoff_seed <= 7:
            bg_color = QColor(PLAYOFF_SEED_COLORS[playoff_seed])
            text_color = QColor(PLAYOFF_SEED_TEXT_COLORS[playoff_seed])

            # Set background and text color for team name
            team_item.setBackground(bg_color)
            team_item.setForeground(text_color)

            # Add seed indicator to team name
            team_item.setText(f"{team_abbrev} ({playoff_seed})")
        elif is_division_leader:
            # Division leader gets accent color text
            team_item.setForeground(QColor(ESPN_THEME['red']))
        else:
            team_item.setForeground(QColor("white"))

        self.setItem(row, 0, team_item)

        # Win-Loss-Tie record
        wins = team.get('wins', 0)
        losses = team.get('losses', 0)
        ties = team.get('ties', 0)

        self._set_centered_item(row, 1, str(wins))
        self._set_centered_item(row, 2, str(losses))
        self._set_centered_item(row, 3, str(ties))

        # Win percentage
        total_games = wins + losses + ties
        if total_games > 0:
            pct = (wins + ties * 0.5) / total_games
            pct_str = f"{pct:.3f}"
        else:
            pct_str = ".000"
        self._set_centered_item(row, 4, pct_str)

        # Points for/against
        points_for = team.get('points_for', 0)
        points_against = team.get('points_against', 0)
        self._set_centered_item(row, 5, str(points_for))
        self._set_centered_item(row, 6, str(points_against))

        # Point differential
        diff = points_for - points_against
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        diff_item = QTableWidgetItem(diff_str)
        diff_item.setTextAlignment(Qt.AlignCenter)

        # Color code differential
        if diff > 0:
            diff_item.setForeground(QColor(Colors.SUCCESS))
        elif diff < 0:
            diff_item.setForeground(QColor(Colors.ERROR))
        else:
            diff_item.setForeground(QColor(ESPN_THEME['text_secondary']))

        self.setItem(row, 7, diff_item)

        # Streak (W3, L2, etc.)
        streak = team.get('streak', '--')
        streak_item = QTableWidgetItem(streak)
        streak_item.setTextAlignment(Qt.AlignCenter)

        # Color code streak
        if isinstance(streak, str) and streak.startswith('W'):
            streak_item.setForeground(QColor(Colors.SUCCESS))
        elif isinstance(streak, str) and streak.startswith('L'):
            streak_item.setForeground(QColor(Colors.ERROR))
        else:
            streak_item.setForeground(QColor(ESPN_THEME['text_secondary']))

        self.setItem(row, 8, streak_item)

        # Home record
        home_record = team.get('home_record', '--')
        self._set_centered_item(row, 9, home_record, ESPN_THEME['text_secondary'])

        # Away record
        away_record = team.get('away_record', '--')
        self._set_centered_item(row, 10, away_record, ESPN_THEME['text_secondary'])

        # Division record
        division_record = team.get('division_record', '--')
        self._set_centered_item(row, 11, division_record, ESPN_THEME['text_secondary'])

        # Alternate row background (subtle)
        if row % 2 == 1:
            for col in range(12):
                item = self.item(row, col)
                if item and not item.background().color().isValid():
                    # Only set if no playoff seed background
                    if not (playoff_seed and 1 <= playoff_seed <= 7 and col == 0):
                        item.setBackground(QColor("#222222"))

    def _set_centered_item(self, row: int, col: int, text: str, color: str = "white"):
        """Helper to create centered table item with color."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor(color))
        self.setItem(row, col, item)

    def clear_table(self):
        """Clear all data from table."""
        self.setRowCount(0)


class StandingsTableWidget(QWidget):
    """
    NFL Standings Widget with conference toggle and division tables.

    Features:
    - Conference toggle buttons (AFC/NFC)
    - 4 division tables per conference (North, South, East, West)
    - Division leader highlighting
    - Playoff seed color-coding (1-7)
    - Win percentage, point differential, streaks
    - Home/Away/Division split records

    Usage:
        widget = StandingsTableWidget()
        widget.set_conference("AFC")
        widget.set_standings(standings_list, "AFC")
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._standings: List[Dict] = []
        self._current_conference: str = "AFC"
        self._division_tables: Dict[str, DivisionTableWidget] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Conference toggle buttons
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(8)

        self.afc_button = QPushButton("AFC")
        self.afc_button.setCheckable(True)
        self.afc_button.setChecked(True)
        self.afc_button.clicked.connect(lambda: self.set_conference("AFC"))
        self.afc_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        toggle_row.addWidget(self.afc_button)

        self.nfc_button = QPushButton("NFC")
        self.nfc_button.setCheckable(True)
        self.nfc_button.setChecked(False)
        self.nfc_button.clicked.connect(lambda: self.set_conference("NFC"))
        self.nfc_button.setStyleSheet(self._get_inactive_button_style())
        toggle_row.addWidget(self.nfc_button)

        toggle_row.addStretch()

        # Legend
        legend_label = QLabel("1-2: Bye | 3-4: Division Winner | 5-7: Wild Card")
        legend_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']}; font-size: {FontSizes.CAPTION};")
        toggle_row.addWidget(legend_label)

        layout.addLayout(toggle_row)

        # Division tables in 2x2 grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)

        for idx, division in enumerate(DIVISIONS):
            row = idx // 2
            col = idx % 2

            # Division container
            division_frame = QFrame()
            division_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {ESPN_THEME['card_bg']};
                    border: 1px solid {ESPN_THEME['border']};
                    border-radius: 4px;
                }}
            """)
            division_layout = QVBoxLayout(division_frame)
            division_layout.setContentsMargins(8, 8, 8, 8)
            division_layout.setSpacing(4)

            # Division header
            header_label = QLabel(f"{self._current_conference} {division}")
            header_label.setFont(Typography.H6)  # 12px Arial Bold
            header_label.setStyleSheet(f"color: {ESPN_THEME['red']}; padding: 4px;")
            division_layout.addWidget(header_label)

            # Division table
            table = DivisionTableWidget(division)
            self._division_tables[division] = table
            division_layout.addWidget(table)

            grid_layout.addWidget(division_frame, row, col)

        layout.addLayout(grid_layout)
        layout.addStretch()

    def set_conference(self, conference: str):
        """
        Set the displayed conference.

        Args:
            conference: "AFC" or "NFC"
        """
        if conference not in ("AFC", "NFC"):
            return

        self._current_conference = conference

        # Update button states
        self.afc_button.setChecked(conference == "AFC")
        self.nfc_button.setChecked(conference == "NFC")

        # Update button styles
        if conference == "AFC":
            self.afc_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
            self.nfc_button.setStyleSheet(self._get_inactive_button_style())
        else:
            self.nfc_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
            self.afc_button.setStyleSheet(self._get_inactive_button_style())

        # Update division headers
        for division, table in self._division_tables.items():
            # Find the division frame parent and update header
            parent_frame = table.parent()
            if parent_frame:
                layout = parent_frame.layout()
                if layout and layout.count() > 0:
                    header_widget = layout.itemAt(0).widget()
                    if isinstance(header_widget, QLabel):
                        header_widget.setText(f"{conference} {division}")

        # Refresh standings display
        self._populate_divisions()

    def set_standings(self, standings: List[Dict], conference: str = None):
        """
        Set the standings data and optionally change conference.

        Args:
            standings: List of team standings dicts with keys:
                - team_id, team_abbrev, team_name, division, conference
                - wins, losses, ties, points_for, points_against
                - playoff_seed (optional, 1-7)
                - streak (e.g., "W3", "L2")
                - home_record (e.g., "5-3")
                - away_record (e.g., "3-5")
                - division_record (e.g., "4-2")
            conference: Optional conference to switch to ("AFC" or "NFC")
        """
        self._standings = standings or []

        if conference:
            self.set_conference(conference)
        else:
            self._populate_divisions()

    def _populate_divisions(self):
        """Populate all division tables with current standings data."""
        # Filter standings by current conference
        conference_standings = [
            team for team in self._standings
            if team.get('conference') == self._current_conference
        ]

        # Group by division
        for division in DIVISIONS:
            division_teams = [
                team for team in conference_standings
                if team.get('division') == division
            ]

            # Sort by division rank (wins, then point differential)
            division_teams.sort(key=lambda t: (
                -t.get('wins', 0),  # More wins first
                -(t.get('points_for', 0) - t.get('points_against', 0))  # Better diff first
            ))

            # Populate division table
            table = self._division_tables.get(division)
            if table:
                table.populate(division_teams)

    def _get_inactive_button_style(self) -> str:
        """Get stylesheet for inactive conference toggle button."""
        return """
            QPushButton {
                background-color: #333333;
                color: #888888;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: white;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """

    def clear(self):
        """Clear all standings data."""
        self._standings = []
        for table in self._division_tables.values():
            table.clear_table()
