"""
Team Schedule Widget - Displays a single team's 17-game schedule.

Part of Milestone 11: Schedule & Rivalries, Tollgate 7.
Shows compact view of team's schedule with bye week, game results,
and rivalry indicators. Can be embedded in team info panels.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import (
    get_rivalry_intensity_color, RIVALRY_TYPE_COLORS
)


class TeamScheduleWidget(QWidget):
    """
    Display a single team's 17-game schedule.

    Used in team info panels or as embedded widget.
    Shows all 17 games + bye week in compact format with:
    - Week number
    - Opponent name
    - Home/Away indicator
    - Game result (if played)
    - Rivalry badge (if applicable)
    """

    # Signals
    game_clicked = Signal(int, int, int)  # week, home_team_id, away_team_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._team_id: Optional[int] = None
        self._team_name: str = "Team"
        self._schedule: List[Dict] = []
        self._bye_week: Optional[int] = None
        self._team_names: Dict[int, str] = {}
        self._rivalry_cache: Dict[tuple, Any] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Team header
        self.team_header = QLabel("Team Schedule")
        self.team_header.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(self.team_header)

        # Schedule table
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(5)
        self.schedule_table.setHorizontalHeaderLabels([
            "Week", "Opponent", "H/A", "Result", "Rivalry"
        ])

        # Configure header
        header = self.schedule_table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #1e3a5f;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #2c5282;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        header.setMinimumHeight(40)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Week
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Opponent
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # H/A
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Result
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Rivalry

        # Configure table
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.schedule_table.setAlternatingRowColors(True)
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.cellDoubleClicked.connect(self._on_row_clicked)

        # Set larger default font for table
        self.schedule_table.setFont(QFont("Arial", 18))
        self.schedule_table.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self.schedule_table)

    def set_team_schedule(
        self,
        team_id: int,
        team_name: str,
        schedule: List[Dict],
        bye_week: Optional[int],
        team_names: Dict[int, str],
        rivalry_cache: Optional[Dict[tuple, Any]] = None
    ):
        """
        Populate with team's 17-game schedule + bye.

        Args:
            team_id: Team ID (1-32)
            team_name: Team name for header
            schedule: List of game dicts with keys:
                - week: int
                - home_team_id: int
                - away_team_id: int
                - home_score: Optional[int]
                - away_score: Optional[int]
                - is_played: bool
            bye_week: Week number of bye (5-14), or None
            team_names: Dict mapping team_id -> team_name
            rivalry_cache: Optional dict mapping (team_a, team_b) -> Rivalry
        """
        self._team_id = team_id
        self._team_name = team_name
        self._schedule = schedule
        self._bye_week = bye_week
        self._team_names = team_names
        self._rivalry_cache = rivalry_cache or {}

        self.team_header.setText(f"{team_name} Schedule")
        self._populate_table()

    def _populate_table(self):
        """Fill table with team's 17-game schedule + bye."""
        # 18 rows: 17 games + 1 bye
        self.schedule_table.setRowCount(18)

        # Build schedule by week
        schedule_by_week: Dict[int, Dict] = {}
        for game in self._schedule:
            week = game.get('week')
            if week:
                schedule_by_week[week] = game

        for row, week in enumerate(range(1, 19)):
            if week == self._bye_week:
                # Bye week row
                self._create_bye_row(row, week)
            elif week in schedule_by_week:
                # Game row
                self._create_game_row(row, week, schedule_by_week[week])
            else:
                # No game scheduled (shouldn't happen in full schedule)
                self._create_empty_row(row, week)

    def _create_bye_row(self, row: int, week: int):
        """Create a bye week row."""
        bye_color = QColor("#E0E0E0")

        # Week
        week_item = QTableWidgetItem(f"Week {week}")
        week_item.setTextAlignment(Qt.AlignCenter)
        week_item.setBackground(bye_color)
        self.schedule_table.setItem(row, 0, week_item)

        # Bye text spanning columns
        bye_item = QTableWidgetItem("BYE WEEK")
        bye_item.setTextAlignment(Qt.AlignCenter)
        bye_item.setFont(QFont("Arial", 18, QFont.Bold))
        bye_item.setForeground(QColor("#666"))
        bye_item.setBackground(bye_color)
        self.schedule_table.setItem(row, 1, bye_item)

        # Fill remaining columns with dashes
        for col in range(2, 5):
            item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(bye_color)
            item.setForeground(QColor("#999"))
            self.schedule_table.setItem(row, col, item)

    def _create_game_row(self, row: int, week: int, game: Dict):
        """Create a game row."""
        home_team_id = game.get('home_team_id')
        away_team_id = game.get('away_team_id')
        is_home = (home_team_id == self._team_id)
        opponent_id = away_team_id if is_home else home_team_id

        # Week
        week_item = QTableWidgetItem(f"Week {week}")
        week_item.setTextAlignment(Qt.AlignCenter)
        week_item.setData(Qt.UserRole, {
            'week': week,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id
        })
        self.schedule_table.setItem(row, 0, week_item)

        # Opponent
        opponent_name = self._team_names.get(opponent_id, f"Team {opponent_id}")
        opp_item = QTableWidgetItem(opponent_name)
        self.schedule_table.setItem(row, 1, opp_item)

        # Home/Away
        ha_item = QTableWidgetItem("vs" if is_home else "@")
        ha_item.setTextAlignment(Qt.AlignCenter)
        ha_item.setForeground(QColor("#1976D2" if is_home else "#F57C00"))
        ha_item.setFont(QFont("Arial", 18, QFont.Bold))
        self.schedule_table.setItem(row, 2, ha_item)

        # Result
        if game.get('is_played'):
            home_score = game.get('home_score', 0)
            away_score = game.get('away_score', 0)

            # Format from team's perspective
            team_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score

            if team_score > opp_score:
                result_text = f"W {team_score}-{opp_score}"
                result_color = "#2E7D32"  # Green
            elif team_score < opp_score:
                result_text = f"L {team_score}-{opp_score}"
                result_color = "#C62828"  # Red
            else:
                result_text = f"T {team_score}-{opp_score}"
                result_color = "#666"

            result_item = QTableWidgetItem(result_text)
            result_item.setTextAlignment(Qt.AlignCenter)
            result_item.setForeground(QColor(result_color))
            result_item.setFont(QFont("Arial", 18, QFont.Bold))
        else:
            result_item = QTableWidgetItem("-")
            result_item.setTextAlignment(Qt.AlignCenter)
            result_item.setForeground(QColor("#999"))

        self.schedule_table.setItem(row, 3, result_item)

        # Rivalry badge
        rivalry = self._get_rivalry(home_team_id, away_team_id)
        if rivalry:
            rivalry_text = rivalry.rivalry_type.value.upper()[:4]
            rivalry_item = QTableWidgetItem(rivalry_text)
            rivalry_item.setTextAlignment(Qt.AlignCenter)

            type_color = RIVALRY_TYPE_COLORS.get(rivalry.rivalry_type.value, "#666")
            rivalry_item.setForeground(QColor(type_color))
            rivalry_item.setFont(QFont("Arial", 18, QFont.Bold))
            rivalry_item.setToolTip(f"{rivalry.rivalry_name} (Intensity: {rivalry.intensity})")

            # Apply row highlighting for rivalry - set background and dark text
            intensity_color = get_rivalry_intensity_color(rivalry.intensity)

            # Also apply to rivalry item before adding
            rivalry_item.setBackground(QColor(intensity_color))
            rivalry_item.setForeground(QColor("#1a1a1a"))
            self.schedule_table.setItem(row, 4, rivalry_item)

            # Apply to all columns including the rivalry column (0-4)
            for col in range(5):
                item = self.schedule_table.item(row, col)
                if item:
                    item.setBackground(QColor(intensity_color))
                    # Use dark text on light backgrounds for readability
                    item.setForeground(QColor("#1a1a1a"))
        else:
            empty_item = QTableWidgetItem("-")
            empty_item.setTextAlignment(Qt.AlignCenter)
            empty_item.setForeground(QColor("#CCC"))
            self.schedule_table.setItem(row, 4, empty_item)

    def _create_empty_row(self, row: int, week: int):
        """Create an empty row for a week with no scheduled game."""
        # Week
        week_item = QTableWidgetItem(f"Week {week}")
        week_item.setTextAlignment(Qt.AlignCenter)
        self.schedule_table.setItem(row, 0, week_item)

        # No game
        no_game_item = QTableWidgetItem("No game")
        no_game_item.setForeground(QColor("#999"))
        self.schedule_table.setItem(row, 1, no_game_item)

        # Fill remaining columns
        for col in range(2, 5):
            item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor("#CCC"))
            self.schedule_table.setItem(row, col, item)

    def _get_rivalry(self, team_a: int, team_b: int):
        """Get rivalry from cache."""
        key = (min(team_a, team_b), max(team_a, team_b))
        return self._rivalry_cache.get(key)

    def _on_row_clicked(self, row: int, col: int):
        """Handle row click to emit game_clicked signal."""
        week_item = self.schedule_table.item(row, 0)
        if not week_item:
            return

        game_data = week_item.data(Qt.UserRole)
        if game_data:
            self.game_clicked.emit(
                game_data['week'],
                game_data['home_team_id'],
                game_data['away_team_id']
            )

    def get_team_id(self) -> Optional[int]:
        """Get the currently displayed team ID."""
        return self._team_id

    def clear(self):
        """Clear the schedule display."""
        self._team_id = None
        self._schedule = []
        self._bye_week = None
        self.team_header.setText("Team Schedule")
        self.schedule_table.setRowCount(0)
