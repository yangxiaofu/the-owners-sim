"""
Schedule View - Displays 18-week NFL schedule with rivalry and primetime indicators.

Part of Milestone 11: Schedule & Rivalries, Tollgate 7.
Shows week-by-week schedule with rivalry game highlighting, primetime badges,
bye week indicators, and head-to-head history.
"""

import json
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import (
    UITheme, TABLE_HEADER_STYLE, get_intensity_label,
    PRIMETIME_BADGES, TIME_SLOT_BADGES,
    SCHEDULE_ROW_COLORS, get_rivalry_symbol
)


class ScheduleView(QWidget):
    """
    Full season schedule view with rivalry and primetime indicators.

    Features:
    - Week-by-week navigation (1-18)
    - All games for selected week displayed in table
    - Rivalry games highlighted by intensity
    - Primetime badges (TNF/SNF/MNF)
    - Bye week row for teams on bye
    - Double-click game to open RivalryInfoDialog
    - Team filter dropdown to show single team's schedule
    """

    # Signals
    game_selected = Signal(int, int, int)  # game_id, home_team_id, away_team_id
    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: int = 2025
        self._current_week: int = 1
        self._selected_team_id: Optional[int] = None  # None = all teams
        self._schedule_data: Dict[int, List] = {}     # week -> List[ScheduledGame]
        self._rivalry_cache: Dict[tuple, Any] = {}    # (team_a, team_b) -> Rivalry
        self._bye_weeks: Dict[int, int] = {}          # team_id -> bye_week
        self._standings_cache: Dict[int, tuple] = {}  # team_id -> (wins, losses, ties)
        self._team_names: Dict[int, str] = {}         # team_id -> team_name
        self._primetime_assignments: Dict[str, Any] = {}  # game_id -> PrimetimeAssignment
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header: Week navigation + Team filter
        self._create_header(layout)

        # Games table
        self._create_games_table(layout)

        # Bye week indicator
        self._create_bye_indicator(layout)

        # Legend
        self._create_legend(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header with week navigation and team filter."""
        header_group = QGroupBox("Schedule")
        header_layout = QHBoxLayout(header_group)
        header_layout.setSpacing(16)

        # Week navigation
        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        self.prev_btn = QPushButton("< Prev")
        self.prev_btn.setStyleSheet(UITheme.button_style("secondary"))
        self.prev_btn.clicked.connect(self._prev_week)
        nav_layout.addWidget(self.prev_btn)

        self.week_label = QLabel("Week 1")
        self.week_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.week_label.setAlignment(Qt.AlignCenter)
        self.week_label.setMinimumWidth(100)
        nav_layout.addWidget(self.week_label)

        self.next_btn = QPushButton("Next >")
        self.next_btn.setStyleSheet(UITheme.button_style("secondary"))
        self.next_btn.clicked.connect(self._next_week)
        nav_layout.addWidget(self.next_btn)

        header_layout.addWidget(nav_frame)
        header_layout.addStretch()

        # Team filter
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        filter_label = QLabel("Team:")
        filter_label.setStyleSheet("color: #666;")
        filter_layout.addWidget(filter_label)

        self.team_filter = QComboBox()
        self.team_filter.setMinimumWidth(200)
        self.team_filter.currentIndexChanged.connect(self._on_team_filter_changed)
        filter_layout.addWidget(self.team_filter)

        header_layout.addWidget(filter_frame)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(UITheme.button_style("secondary"))
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(refresh_btn)

        parent_layout.addWidget(header_group)

    def _create_games_table(self, parent_layout: QVBoxLayout):
        """Create the main games table."""
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(8)
        self.games_table.setHorizontalHeaderLabels([
            "Time", "Away", "Record", "@", "Home", "Record", "Result", "Rivalry"
        ])

        # Configure header
        header = self.games_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Away
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Away Record
        header.setSectionResizeMode(3, QHeaderView.Fixed)             # @
        header.resizeSection(3, 30)
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Home
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Home Record
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Result
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Rivalry

        # Configure table
        self.games_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.games_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.games_table.setAlternatingRowColors(True)
        self.games_table.verticalHeader().setVisible(False)
        self.games_table.cellDoubleClicked.connect(self._on_game_double_clicked)

        parent_layout.addWidget(self.games_table, stretch=1)

    def _create_bye_indicator(self, parent_layout: QVBoxLayout):
        """Create the bye week indicator at the bottom."""
        bye_frame = QFrame()
        bye_frame.setStyleSheet("""
            QFrame {
                background-color: #E0E0E0;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        bye_layout = QHBoxLayout(bye_frame)
        bye_layout.setContentsMargins(12, 8, 12, 8)

        bye_icon = QLabel("BYE")
        bye_icon.setFont(QFont("Arial", 10, QFont.Bold))
        bye_icon.setStyleSheet("color: #666;")
        bye_layout.addWidget(bye_icon)

        self.bye_label = QLabel("Teams on bye: None")
        self.bye_label.setStyleSheet("color: #333;")
        bye_layout.addWidget(self.bye_label)

        bye_layout.addStretch()
        parent_layout.addWidget(bye_frame)

    def _create_legend(self, parent_layout: QVBoxLayout):
        """Create the legend for rivalry symbols, primetime badges, and flex indicator."""
        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        legend_layout.setSpacing(16)

        # Rivalry symbols legend
        rivalry_label = QLabel("Rivalry: ### Legendary  ## Intense  # Competitive  - Developing")
        rivalry_label.setStyleSheet("color: #999;")
        legend_layout.addWidget(rivalry_label)

        legend_layout.addStretch()

        # Flex indicator legend
        flex_label = QLabel("★ = Flexed")
        flex_label.setStyleSheet("color: #999;")
        flex_label.setToolTip("Game was moved into/out of primetime slot via flex scheduling")
        legend_layout.addWidget(flex_label)

        # Primetime legend
        legend_layout.addWidget(QLabel("Primetime:"))
        for slot_key, badge_info in PRIMETIME_BADGES.items():
            badge_widget = QLabel(badge_info["text"])
            badge_widget.setStyleSheet(
                f"background-color: {badge_info['bg']}; color: {badge_info['fg']}; "
                f"padding: 2px 6px; border-radius: 3px; font-weight: bold;"
            )
            legend_layout.addWidget(badge_widget)

        parent_layout.addWidget(legend_frame)

    # -------------------- Context & Data Loading --------------------

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """Set dynasty context and load data."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._load_all_data()
        self._populate_team_filter()
        self._refresh_display()

    def _load_all_data(self):
        """Load schedule from games table AND events table, rivalries, bye weeks, and standings.

        This method loads both completed games (from games table) and scheduled/unplayed
        games (from events table) to show the full season schedule.
        """
        if not self._db_path or not self._dynasty_id:
            return

        from types import SimpleNamespace
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.database.rivalry_api import RivalryAPI
        from game_cycle.database.bye_week_api import ByeWeekAPI
        from game_cycle.database.standings_api import StandingsAPI
        from game_cycle.services.primetime_scheduler import PrimetimeScheduler
        from team_management.teams.team_loader import get_team_by_id

        db = GameCycleDatabase(self._db_path)

        try:
            rivalry_api = RivalryAPI(db)
            bye_api = ByeWeekAPI(db)
            standings_api = StandingsAPI(db)

            # Clear data structures
            self._schedule_data.clear()
            self._primetime_assignments.clear()

            # Track completed game_ids to avoid duplicates
            completed_game_ids = set()

            # Step 1: Load completed games from games table
            for week in range(1, 19):
                rows = db.query_all(
                    """SELECT game_id as id, week, home_team_id, away_team_id,
                              home_score, away_score
                       FROM games
                       WHERE dynasty_id = ? AND season = ? AND week = ?
                         AND season_type = 'regular_season'
                       ORDER BY game_id""",
                    (self._dynasty_id, self._season, week)
                )
                # Convert rows to game-like objects
                games = []
                for row in rows:
                    completed_game_ids.add(row['id'])
                    game = SimpleNamespace(
                        id=row['id'],
                        week=row['week'],
                        home_team_id=row['home_team_id'],
                        away_team_id=row['away_team_id'],
                        home_score=row['home_score'],
                        away_score=row['away_score'],
                        is_played=True
                    )
                    games.append(game)
                self._schedule_data[week] = games

            # Step 2: Load scheduled (unplayed) games from events table
            # These are games where results is null (not yet simulated)
            scheduled_rows = db.query_all(
                """SELECT event_id, game_id, data
                   FROM events
                   WHERE dynasty_id = ?
                     AND json_extract(data, '$.parameters.season') = ?
                     AND json_extract(data, '$.parameters.season_type') = 'regular_season'
                   ORDER BY json_extract(data, '$.parameters.week'), game_id""",
                (self._dynasty_id, self._season)
            )

            for row in scheduled_rows:
                game_id = row['game_id']

                # Skip if already loaded as completed game
                if game_id in completed_game_ids:
                    continue

                # Parse event data
                try:
                    data = json.loads(row['data'])
                except (json.JSONDecodeError, TypeError):
                    continue

                params = data.get('parameters', {})
                week = params.get('week')

                if not week or week < 1 or week > 18:
                    continue

                # Initialize week list if needed
                if week not in self._schedule_data:
                    self._schedule_data[week] = []

                # Create game object for scheduled (unplayed) game
                game = SimpleNamespace(
                    id=game_id,
                    week=week,
                    home_team_id=params.get('home_team_id'),
                    away_team_id=params.get('away_team_id'),
                    home_score=None,
                    away_score=None,
                    is_played=False
                )
                self._schedule_data[week].append(game)

            # Load all rivalries into cache
            self._rivalry_cache.clear()
            rivalries = rivalry_api.get_all_rivalries(self._dynasty_id)
            for r in rivalries:
                key = (min(r.team_a_id, r.team_b_id), max(r.team_a_id, r.team_b_id))
                self._rivalry_cache[key] = r

            # Load bye weeks
            self._bye_weeks = bye_api.get_all_bye_weeks(self._dynasty_id, self._season)

            # Load standings for records
            self._standings_cache.clear()
            standings = standings_api.get_standings(self._dynasty_id, self._season)
            for s in standings:
                self._standings_cache[s.team_id] = (s.wins, s.losses, s.ties)

            # Load team names
            self._team_names.clear()
            for team_id in range(1, 33):
                team = get_team_by_id(team_id)
                if team:
                    self._team_names[team_id] = team.full_name

            # Load primetime slot assignments via PrimetimeScheduler service
            # Store full assignment objects to access flexed_from field
            primetime_scheduler = PrimetimeScheduler(db, self._dynasty_id)
            for week in range(1, 19):
                assignments = primetime_scheduler.get_week_schedule(self._season, week)
                for assignment in assignments:
                    # Store full assignment (includes slot, flexed_from, appeal_score)
                    self._primetime_assignments[assignment.game_id] = assignment

        finally:
            db.close()

    def _populate_team_filter(self):
        """Populate the team filter dropdown."""
        self.team_filter.blockSignals(True)
        self.team_filter.clear()

        # Add "All Teams" option
        self.team_filter.addItem("All Teams", None)

        # Add each team sorted by name
        teams = sorted(self._team_names.items(), key=lambda x: x[1])
        for team_id, team_name in teams:
            self.team_filter.addItem(team_name, team_id)

        self.team_filter.blockSignals(False)

    # -------------------- Display Methods --------------------

    def _refresh_display(self):
        """Refresh table for current week and team filter."""
        games = self._schedule_data.get(self._current_week, [])

        # Filter by team if selected
        if self._selected_team_id:
            games = [g for g in games
                     if g.home_team_id == self._selected_team_id
                     or g.away_team_id == self._selected_team_id]

        self._populate_table(games)
        self._update_bye_label()
        self._update_navigation()
        self.week_label.setText(f"Week {self._current_week}")

    def _populate_table(self, games: List):
        """Fill table with game rows."""
        self.games_table.setRowCount(len(games))

        if not games:
            self._show_no_games_message()
            return

        for row, game in enumerate(games):
            self._populate_game_row(row, game)

    def _populate_game_row(self, row: int, game):
        """Populate a single row in the games table."""
        # Get rivalry if exists
        rivalry = self._get_rivalry(game.home_team_id, game.away_team_id)

        # Consistent color scheme from theme (no played/unplayed distinction)
        text_primary = QColor(SCHEDULE_ROW_COLORS["text_primary"])
        text_secondary = QColor(SCHEDULE_ROW_COLORS["text_secondary"])
        score_away_win = QColor(SCHEDULE_ROW_COLORS["score_away_win"])
        score_home_win = QColor(SCHEDULE_ROW_COLORS["score_home_win"])

        # Time slot (primetime or default) with flex indicator
        assignment = self._primetime_assignments.get(game.id)
        slot_key = assignment.slot.value if assignment else "SUN"
        badge = TIME_SLOT_BADGES.get(slot_key, TIME_SLOT_BADGES.get("SUN", {}))
        display_text = badge.get("text", slot_key)

        # Add flex indicator if game was flexed
        tooltip_text = None
        if assignment and assignment.flexed_from:
            display_text += " ★"
            tooltip_text = f"Flexed from {assignment.flexed_from.value}"

        time_item = QTableWidgetItem(display_text)
        time_item.setTextAlignment(Qt.AlignCenter)
        time_item.setData(Qt.UserRole, game.id)  # Store game_id
        time_item.setBackground(QColor(badge.get("bg", "#455A64")))
        time_item.setForeground(QColor(badge.get("fg", "#FFFFFF")))
        time_item.setFont(QFont("Arial", 9, QFont.Bold))
        if tooltip_text:
            time_item.setToolTip(tooltip_text)
        self.games_table.setItem(row, 0, time_item)

        # Away team
        away_name = self._team_names.get(game.away_team_id, f"Team {game.away_team_id}")
        away_item = QTableWidgetItem(away_name)
        away_item.setData(Qt.UserRole, game.away_team_id)
        away_item.setForeground(text_primary)
        self.games_table.setItem(row, 1, away_item)

        # Away record
        away_record = self._get_record_string(game.away_team_id)
        away_record_item = QTableWidgetItem(away_record)
        away_record_item.setTextAlignment(Qt.AlignCenter)
        away_record_item.setForeground(text_secondary)
        self.games_table.setItem(row, 2, away_record_item)

        # @ symbol
        at_item = QTableWidgetItem("@")
        at_item.setTextAlignment(Qt.AlignCenter)
        at_item.setForeground(text_secondary)
        self.games_table.setItem(row, 3, at_item)

        # Home team
        home_name = self._team_names.get(game.home_team_id, f"Team {game.home_team_id}")
        home_item = QTableWidgetItem(home_name)
        home_item.setData(Qt.UserRole, game.home_team_id)
        home_item.setForeground(text_primary)
        self.games_table.setItem(row, 4, home_item)

        # Home record
        home_record = self._get_record_string(game.home_team_id)
        home_record_item = QTableWidgetItem(home_record)
        home_record_item.setTextAlignment(Qt.AlignCenter)
        home_record_item.setForeground(text_secondary)
        self.games_table.setItem(row, 5, home_record_item)

        # Result
        if game.is_played:
            result_text = f"{game.away_score} - {game.home_score}"
            result_item = QTableWidgetItem(result_text)
            result_item.setTextAlignment(Qt.AlignCenter)
            # Color the winner's score
            if game.away_score > game.home_score:
                result_item.setForeground(score_away_win)
            elif game.home_score > game.away_score:
                result_item.setForeground(score_home_win)
            else:
                result_item.setForeground(text_primary)  # Tie
        else:
            result_item = QTableWidgetItem("Scheduled")
            result_item.setTextAlignment(Qt.AlignCenter)
            result_item.setForeground(text_secondary)
        self.games_table.setItem(row, 6, result_item)

        # Rivalry indicator (using symbols: ###, ##, #, -, or blank)
        if rivalry:
            symbol = get_rivalry_symbol(rivalry.intensity)
            rivalry_item = QTableWidgetItem(symbol)
            rivalry_item.setTextAlignment(Qt.AlignCenter)
            rivalry_item.setFont(QFont("Arial", 11, QFont.Bold))
            rivalry_item.setForeground(text_primary)
            rivalry_item.setToolTip(
                f"{rivalry.rivalry_name}\n"
                f"Type: {rivalry.rivalry_type.value.title()}\n"
                f"Intensity: {rivalry.intensity} ({get_intensity_label(rivalry.intensity)})"
            )
        else:
            rivalry_item = QTableWidgetItem("")
            rivalry_item.setTextAlignment(Qt.AlignCenter)
        self.games_table.setItem(row, 7, rivalry_item)

    def _show_no_games_message(self):
        """Show message when no games for the week."""
        self.games_table.setRowCount(1)
        self.games_table.setSpan(0, 0, 1, 8)

        message_item = QTableWidgetItem("No games scheduled for this week")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.games_table.setItem(0, 0, message_item)

    def _get_rivalry(self, team_a: int, team_b: int):
        """Get rivalry from cache."""
        key = (min(team_a, team_b), max(team_a, team_b))
        return self._rivalry_cache.get(key)

    def _get_slot_text(self, game) -> str:
        """Get time slot text for a game (legacy method, kept for compatibility)."""
        # Check if primetime assignment exists
        assignment = self._primetime_assignments.get(game.id)
        if assignment:
            return assignment.slot.value

        # Default to Sunday for games without a primetime assignment
        return "SUN"

    def _get_record_string(self, team_id: int) -> str:
        """Get formatted record string for a team."""
        record = self._standings_cache.get(team_id)
        if not record:
            return "0-0"
        wins, losses, ties = record
        if ties > 0:
            return f"{wins}-{losses}-{ties}"
        return f"{wins}-{losses}"

    def _update_bye_label(self):
        """Update the bye week label with teams on bye."""
        if not self._bye_weeks:
            self.bye_label.setText("Teams on bye: None")
            return

        # Find teams with bye this week
        teams_on_bye = [
            team_id for team_id, bye_week in self._bye_weeks.items()
            if bye_week == self._current_week
        ]

        if not teams_on_bye:
            self.bye_label.setText("Teams on bye: None")
        else:
            team_names = [self._team_names.get(tid, f"Team {tid}") for tid in sorted(teams_on_bye)]
            self.bye_label.setText(f"Teams on bye: {', '.join(team_names)}")

    def _update_navigation(self):
        """Update navigation button states."""
        self.prev_btn.setEnabled(self._current_week > 1)
        self.next_btn.setEnabled(self._current_week < 18)

    # -------------------- Event Handlers --------------------

    def _prev_week(self):
        """Navigate to previous week."""
        if self._current_week > 1:
            self._current_week -= 1
            self._refresh_display()

    def _next_week(self):
        """Navigate to next week."""
        if self._current_week < 18:
            self._current_week += 1
            self._refresh_display()

    def _on_team_filter_changed(self, index: int):
        """Handle team filter selection change."""
        if index >= 0:
            self._selected_team_id = self.team_filter.itemData(index)
            self._refresh_display()

    def _on_game_double_clicked(self, row: int, col: int):
        """Handle double-click on game row to show rivalry info."""
        time_item = self.games_table.item(row, 0)
        if not time_item:
            return

        game_id = time_item.data(Qt.UserRole)
        away_item = self.games_table.item(row, 1)
        home_item = self.games_table.item(row, 4)

        if away_item and home_item:
            away_team_id = away_item.data(Qt.UserRole)
            home_team_id = home_item.data(Qt.UserRole)
            self.game_selected.emit(game_id, home_team_id, away_team_id)

    # -------------------- Public Methods --------------------

    def set_current_week(self, week: int):
        """Set the current week to display."""
        if 1 <= week <= 18:
            self._current_week = week
            self._refresh_display()

    def set_selected_team(self, team_id: Optional[int]):
        """Set the team filter selection."""
        if team_id is None:
            self.team_filter.setCurrentIndex(0)
        else:
            for i in range(self.team_filter.count()):
                if self.team_filter.itemData(i) == team_id:
                    self.team_filter.setCurrentIndex(i)
                    break

    def get_current_week(self) -> int:
        """Get the currently displayed week."""
        return self._current_week

    def get_selected_team_id(self) -> Optional[int]:
        """Get the currently selected team filter."""
        return self._selected_team_id

    def reload_data(self):
        """Reload all data from database."""
        self._load_all_data()
        self._refresh_display()
