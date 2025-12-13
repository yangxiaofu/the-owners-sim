"""
Stats View - Shows league leaders by category.

Displays league leaders for passing, rushing, receiving, defense, and kicking.
Data is loaded from player_game_stats via UnifiedDatabaseAPI.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFrame, QTabWidget, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import TABLE_HEADER_STYLE


class NumericTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts numerically instead of alphabetically."""

    def __init__(self, value: Any, display_text: str = None):
        """
        Args:
            value: The numeric value for sorting
            display_text: The text to display (if different from value)
        """
        super().__init__(display_text if display_text else str(value))
        self._sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            # Handle None/0 values
            self_val = self._sort_value if self._sort_value is not None else 0
            other_val = other._sort_value if other._sort_value is not None else 0
            return self_val < other_val
        return super().__lt__(other)


class StatsView(QWidget):
    """
    View for displaying league statistics.

    Shows league leaders across 6 categories:
    - Passing (yards, TDs, completions, rating)
    - Rushing (yards, TDs, attempts, average)
    - Receiving (yards, TDs, receptions, targets)
    - Defense (tackles, sacks, interceptions)
    - Kicking (FG%, XP%, points)
    - Blocking (pancakes, sacks allowed, pressures)
    """

    # Signals
    refresh_requested = Signal()  # Emitted when user requests refresh

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._season: int = 2025
        self._dynasty_id: str = ""
        self._db_path: str = ""
        self._unified_api = None
        self._team_filter: Optional[int] = None  # None = All Teams
        self._defense_sort_by: str = 'tackles'  # Default sort for defense table
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with season selector
        self._create_header(layout)

        # Summary panel
        self._create_summary_panel(layout)

        # Category tabs (Passing, Rushing, etc.)
        self._create_category_tabs(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title, team filter, and season selector."""
        header = QHBoxLayout()

        title = QLabel("LEAGUE STATS")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header.addWidget(title)

        header.addStretch()

        # Team filter
        team_label = QLabel("Team:")
        header.addWidget(team_label)

        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(150)
        self.team_combo.addItem("All Teams", None)
        self._populate_team_combo()
        self.team_combo.currentIndexChanged.connect(self._on_team_changed)
        header.addWidget(self.team_combo)

        header.addSpacing(20)

        # Season selector
        season_label = QLabel("Season:")
        header.addWidget(season_label)

        self.season_combo = QComboBox()
        self.season_combo.setMinimumWidth(100)
        self.season_combo.currentIndexChanged.connect(self._on_season_changed)
        header.addWidget(self.season_combo)

        header.addSpacing(20)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(self.refresh_btn)

        parent_layout.addLayout(header)

    def _populate_team_combo(self):
        """Populate team dropdown with all NFL teams."""
        try:
            from team_management.teams.team_loader import get_all_teams
            teams = get_all_teams()
            # Sort by city name
            sorted_teams = sorted(teams, key=lambda t: t.city)
            for team in sorted_teams:
                self.team_combo.addItem(f"{team.city} {team.nickname}", team.team_id)
        except Exception as e:
            print(f"[StatsView] Error loading teams: {e}")

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary statistics panel."""
        summary_group = QGroupBox("Season Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Games played
        self._create_stat_widget(
            summary_layout, "games_label", "Games Played", "0"
        )

        # Players with stats
        self._create_stat_widget(
            summary_layout, "players_label", "Players", "0"
        )

        # Current week
        self._create_stat_widget(
            summary_layout, "week_label", "Week", "0"
        )

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_stat_widget(
        self,
        parent_layout: QHBoxLayout,
        attr_name: str,
        title: str,
        initial_value: str,
        color: Optional[str] = None
    ):
        """Create a single stat widget."""
        frame = QFrame()
        vlayout = QVBoxLayout(frame)
        vlayout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 11px;")
        vlayout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        if color:
            value_label.setStyleSheet(f"color: {color};")
        vlayout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        parent_layout.addWidget(frame)

    def _create_category_tabs(self, parent_layout: QVBoxLayout):
        """Create tab widget with stat category tables."""
        self.category_tabs = QTabWidget()

        # Passing tab
        self.passing_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "CMP", "ATT", "CMP%", "YDS", "TD", "INT", "RTG"
        ])
        self.category_tabs.addTab(self.passing_table, "Passing")

        # Rushing tab - added SNAPS column
        self.rushing_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "ATT", "YDS", "AVG", "TD", "LNG", "FUM", "SNAPS"
        ])
        self.category_tabs.addTab(self.rushing_table, "Rushing")

        # Receiving tab - added SNAPS column
        self.receiving_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "REC", "TGT", "YDS", "AVG", "TD", "LNG", "DRP", "SNAPS"
        ])
        self.category_tabs.addTab(self.receiving_table, "Receiving")

        # Defense tab - uses server-side sorting
        self.defense_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "TKL", "SOLO", "AST", "SACK", "INT", "PD", "FF", "FR"
        ])
        # Disable client-side sorting for defense table - we use server-side sorting
        self.defense_table.setSortingEnabled(False)
        # Connect header click for server-side sorting
        self.defense_table.horizontalHeader().sectionClicked.connect(
            self._on_defense_header_clicked
        )
        self.category_tabs.addTab(self.defense_table, "Defense")

        # Kicking tab
        self.kicking_table = self._create_stats_table([
            "#", "Player", "Team", "FGM", "FGA", "FG%", "XPM", "XPA", "PTS"
        ])
        self.category_tabs.addTab(self.kicking_table, "Kicking")

        # Punting tab
        self.punting_table = self._create_stats_table([
            "#", "Player", "Team", "PUNTS", "YDS", "AVG"
        ])
        self.category_tabs.addTab(self.punting_table, "Punting")

        # Blocking tab (O-Line)
        self.blocking_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "PB", "PKS", "SKA", "HUR", "PRES", "RBG", "PBE"
        ])
        self.category_tabs.addTab(self.blocking_table, "Blocking")

        # Coverage tab (DBs/LBs)
        self.coverage_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "TGT", "CMP", "YDS", "CMP%", "PD", "INT", "SNAPS"
        ])
        self.category_tabs.addTab(self.coverage_table, "Coverage")

        # Pass Rush tab (DL/EDGE)
        self.pass_rush_table = self._create_stats_table([
            "#", "Player", "Pos", "Team", "PR ATT", "PR WIN", "WIN%", "SACK", "DBL", "SNAPS"
        ])
        self.category_tabs.addTab(self.pass_rush_table, "Pass Rush")

        # Team Stats tab (league-wide team rankings)
        team_stats_container = self._create_team_stats_tab()
        self.category_tabs.addTab(team_stats_container, "Team Stats")

        parent_layout.addWidget(self.category_tabs, stretch=1)

    def _create_team_stats_tab(self) -> QWidget:
        """Create the Team Stats tab with toggle buttons and rankings table."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        # Toggle button row
        toggle_row = QHBoxLayout()

        # Toggle button styling
        toggle_style = """
            QPushButton {
                background-color: #3a3a3a;
                color: #888;
                border: 1px solid #555;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #1976D2;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover:!checked {
                background-color: #4a4a4a;
            }
        """

        # Create toggle buttons
        self.team_stats_buttons = {}
        self._current_team_stats_view = "offense"

        for i, (view_type, label) in enumerate([
            ("offense", "Offense"),
            ("defense", "Defense"),
            ("special_teams", "Special Teams"),
            ("turnovers", "Turnovers")
        ]):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(toggle_style)

            # Round corners only on first/last buttons
            if i == 0:
                btn.setStyleSheet(toggle_style + """
                    QPushButton { border-top-left-radius: 4px; border-bottom-left-radius: 4px; }
                """)
            elif i == 3:
                btn.setStyleSheet(toggle_style + """
                    QPushButton { border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
                """)

            btn.clicked.connect(lambda checked, vt=view_type: self._on_team_stats_toggle(vt))
            self.team_stats_buttons[view_type] = btn
            toggle_row.addWidget(btn)

        # Set default selection
        self.team_stats_buttons["offense"].setChecked(True)

        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # Team stats table
        self.team_stats_table = self._create_stats_table([
            "#", "Team", "GP", "Total YDS", "Pass YDS", "Rush YDS", "PTS", "PTS/G"
        ])
        layout.addWidget(self.team_stats_table, stretch=1)

        return container

    def _on_team_stats_toggle(self, view_type: str):
        """Handle team stats toggle button click."""
        # Uncheck all other buttons
        for vt, btn in self.team_stats_buttons.items():
            btn.setChecked(vt == view_type)
        self._current_team_stats_view = view_type
        self._load_team_stats()

    def _create_stats_table(self, headers: List[str]) -> QTableWidget:
        """Create a configured stats table with sorting enabled."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # Configure appearance
        header = table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Rank
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Player name
        for i in range(2, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        # Enable sorting by clicking column headers
        table.setSortingEnabled(True)

        return table

    # === Context and Data Methods ===

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set dynasty context for data queries.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to database
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

        # Initialize UnifiedDatabaseAPI
        from database.unified_api import UnifiedDatabaseAPI
        self._unified_api = UnifiedDatabaseAPI(db_path, dynasty_id)

        # Populate season combo
        self._populate_season_combo()

    def _populate_season_combo(self):
        """Populate season dropdown with available seasons."""
        self.season_combo.blockSignals(True)
        self.season_combo.clear()

        # Add current and past seasons (last 5 years)
        for year in range(self._season, self._season - 5, -1):
            self.season_combo.addItem(str(year), year)

        self.season_combo.blockSignals(False)

    def refresh_stats(self):
        """Refresh all stats tables from database."""
        if not self._unified_api:
            return

        self._load_passing_leaders()
        self._load_rushing_leaders()
        self._load_receiving_leaders()
        self._load_defense_leaders()
        self._load_kicking_leaders()
        self._load_punting_leaders()
        self._load_blocking_leaders()
        self._load_coverage_leaders()
        self._load_pass_rush_leaders()
        self._load_team_stats()
        self._update_summary()

    def _on_season_changed(self, index: int):
        """Handle season selection change."""
        if index >= 0:
            self._season = self.season_combo.itemData(index)
            self.refresh_stats()

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_stats()
        self.refresh_requested.emit()

    def _on_team_changed(self, index: int):
        """Handle team filter selection change."""
        if index >= 0:
            self._team_filter = self.team_combo.itemData(index)
            self.refresh_stats()

    def _on_defense_header_clicked(self, column: int):
        """Handle defense table column header click for server-side sorting."""
        # Map column indices to sort_by values
        # Columns: #, Player, Pos, Team, TKL, SOLO, AST, SACK, INT, PD, FF, FR
        column_to_sort = {
            4: 'tackles',          # TKL column
            5: 'tackles_solo',     # SOLO column
            6: 'tackles_assist',   # AST column
            7: 'sacks',            # SACK column
            8: 'interceptions',    # INT column
            9: 'passes_defended',  # PD column
            10: 'forced_fumbles',  # FF column
            11: 'fumbles_recovered',  # FR column
        }
        sort_by = column_to_sort.get(column)
        if sort_by:
            self._defense_sort_by = sort_by
            self._load_defense_leaders()

    # === Data Loading Methods ===

    def _load_passing_leaders(self):
        """Load passing leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_passing(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_passing_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading passing leaders: {e}")
            self.passing_table.setRowCount(0)

    def _load_rushing_leaders(self):
        """Load rushing leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_rushing(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_rushing_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading rushing leaders: {e}")
            self.rushing_table.setRowCount(0)

    def _load_receiving_leaders(self):
        """Load receiving leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_receiving(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_receiving_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading receiving leaders: {e}")
            self.receiving_table.setRowCount(0)

    def _load_defense_leaders(self):
        """Load defensive leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_defense(
                season=self._season,
                limit=25,
                team_id=self._team_filter,
                sort_by=self._defense_sort_by
            )
            self._populate_defense_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading defense leaders: {e}")
            self.defense_table.setRowCount(0)

    def _load_kicking_leaders(self):
        """Load kicking leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_kicking(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_kicking_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading kicking leaders: {e}")
            self.kicking_table.setRowCount(0)

    def _load_punting_leaders(self):
        """Load punting leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_punting(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_punting_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading punting leaders: {e}")
            self.punting_table.setRowCount(0)

    def _load_blocking_leaders(self):
        """Load blocking (O-Line) leaders into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_blocking(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_blocking_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading blocking leaders: {e}")
            self.blocking_table.setRowCount(0)

    def _load_coverage_leaders(self):
        """Load coverage leaders (DBs/LBs) into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_coverage(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_coverage_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading coverage leaders: {e}")
            self.coverage_table.setRowCount(0)

    def _load_pass_rush_leaders(self):
        """Load pass rush leaders (DL/EDGE) into table using category-specific method."""
        try:
            leaders = self._unified_api.stats_get_category_leaders_pass_rush(
                season=self._season,
                limit=25,
                team_id=self._team_filter
            )
            self._populate_pass_rush_table(leaders)
        except Exception as e:
            print(f"[StatsView] Error loading pass rush leaders: {e}")
            self.pass_rush_table.setRowCount(0)

    def _load_team_stats(self):
        """Load team statistics based on selected view (offense/defense/special_teams/turnovers)."""
        try:
            view_type = self._current_team_stats_view

            # Get all teams' stats using the unified API
            all_stats = self._unified_api.team_stats_get_all_teams(self._season)

            if not all_stats:
                self.team_stats_table.setRowCount(1)
                msg_item = QTableWidgetItem("No team statistics available")
                msg_item.setForeground(QColor("#666"))
                self.team_stats_table.setItem(0, 1, msg_item)
                return

            # Update table headers based on view
            self._update_team_stats_headers(view_type)

            # Sort and populate based on view type
            self._populate_team_stats_table(all_stats, view_type)

        except Exception as e:
            print(f"[StatsView] Error loading team stats: {e}")
            self.team_stats_table.setRowCount(0)

    def _update_team_stats_headers(self, view_type: str):
        """Update team stats table headers based on view type."""
        if view_type == "offense":
            headers = ["#", "Team", "GP", "Total YDS", "Pass YDS", "Rush YDS", "PTS", "PTS/G"]
        elif view_type == "defense":
            headers = ["#", "Team", "GP", "YDS Allowed", "Pass YDS", "Rush YDS", "PTS Allowed", "PTS/G"]
        elif view_type == "special_teams":
            headers = ["#", "Team", "GP", "FG%", "XP%", "Punt Avg", "KR Avg", "PR Avg"]
        else:  # turnovers
            headers = ["#", "Team", "GP", "Turnovers", "TO Forced", "TO Margin", "INT", "Sacks"]

        self.team_stats_table.setColumnCount(len(headers))
        self.team_stats_table.setHorizontalHeaderLabels(headers)

    def _populate_team_stats_table(self, all_stats: List[Dict], view_type: str):
        """Populate team stats table based on view type."""
        from team_management.teams.team_loader import get_team_by_id

        # Sort based on view type
        if view_type == "offense":
            sorted_stats = sorted(all_stats, key=lambda x: x.get('total_yards', 0), reverse=True)
        elif view_type == "defense":
            sorted_stats = sorted(all_stats, key=lambda x: x.get('yards_allowed', 0))  # Lower is better
        elif view_type == "special_teams":
            # Sort by FG% (higher is better)
            sorted_stats = sorted(all_stats, key=lambda x: x.get('field_goal_percentage', 0), reverse=True)
        else:  # turnovers
            sorted_stats = sorted(all_stats, key=lambda x: x.get('turnover_margin', 0), reverse=True)

        self.team_stats_table.setRowCount(len(sorted_stats))

        for row, stats in enumerate(sorted_stats):
            team_id = stats.get('team_id')
            team = get_team_by_id(team_id) if team_id else None
            team_abbr = team.abbreviation if team else f"Team {team_id}"
            games_played = stats.get('games_played', 0)

            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.team_stats_table.setItem(row, 0, rank_item)

            # Team
            self.team_stats_table.setItem(row, 1, QTableWidgetItem(team_abbr))

            # Games Played
            gp_item = NumericTableWidgetItem(games_played, str(games_played))
            gp_item.setTextAlignment(Qt.AlignCenter)
            self.team_stats_table.setItem(row, 2, gp_item)

            if view_type == "offense":
                # Total Yards
                total_yds = stats.get('total_yards', 0)
                self.team_stats_table.setItem(row, 3, NumericTableWidgetItem(total_yds, f"{total_yds:,}"))

                # Pass Yards
                pass_yds = stats.get('passing_yards', 0)
                self.team_stats_table.setItem(row, 4, NumericTableWidgetItem(pass_yds, f"{pass_yds:,}"))

                # Rush Yards
                rush_yds = stats.get('rushing_yards', 0)
                self.team_stats_table.setItem(row, 5, NumericTableWidgetItem(rush_yds, f"{rush_yds:,}"))

                # Points
                pts = stats.get('points_scored', 0)
                self.team_stats_table.setItem(row, 6, NumericTableWidgetItem(pts, str(pts)))

                # Points Per Game
                ppg = stats.get('points_per_game', 0)
                self.team_stats_table.setItem(row, 7, NumericTableWidgetItem(ppg, f"{ppg:.1f}"))

            elif view_type == "defense":
                # Yards Allowed
                yds_allowed = stats.get('yards_allowed', 0)
                self.team_stats_table.setItem(row, 3, NumericTableWidgetItem(yds_allowed, f"{yds_allowed:,}"))

                # Pass Yards Allowed
                pass_yds_allowed = stats.get('passing_yards_allowed', 0)
                self.team_stats_table.setItem(row, 4, NumericTableWidgetItem(pass_yds_allowed, f"{pass_yds_allowed:,}"))

                # Rush Yards Allowed
                rush_yds_allowed = stats.get('rushing_yards_allowed', 0)
                self.team_stats_table.setItem(row, 5, NumericTableWidgetItem(rush_yds_allowed, f"{rush_yds_allowed:,}"))

                # Points Allowed
                pts_allowed = stats.get('points_allowed', 0)
                self.team_stats_table.setItem(row, 6, NumericTableWidgetItem(pts_allowed, str(pts_allowed)))

                # Points Allowed Per Game
                papg = stats.get('points_allowed_per_game', 0)
                self.team_stats_table.setItem(row, 7, NumericTableWidgetItem(papg, f"{papg:.1f}"))

            elif view_type == "special_teams":
                # Field Goal Percentage
                fg_pct = stats.get('field_goal_percentage', 0)
                self.team_stats_table.setItem(row, 3, NumericTableWidgetItem(fg_pct, f"{fg_pct:.1f}%"))

                # Extra Point Percentage
                xp_pct = stats.get('extra_point_percentage', 0)
                self.team_stats_table.setItem(row, 4, NumericTableWidgetItem(xp_pct, f"{xp_pct:.1f}%"))

                # Punt Average
                punt_avg = stats.get('punt_average', 0)
                self.team_stats_table.setItem(row, 5, NumericTableWidgetItem(punt_avg, f"{punt_avg:.1f}"))

                # Kick Return Average
                kr_avg = stats.get('kick_return_average', 0)
                self.team_stats_table.setItem(row, 6, NumericTableWidgetItem(kr_avg, f"{kr_avg:.1f}"))

                # Punt Return Average
                pr_avg = stats.get('punt_return_average', 0)
                self.team_stats_table.setItem(row, 7, NumericTableWidgetItem(pr_avg, f"{pr_avg:.1f}"))

            else:  # turnovers
                # Turnovers
                turnovers = stats.get('turnovers', 0)
                self.team_stats_table.setItem(row, 3, NumericTableWidgetItem(turnovers, str(turnovers)))

                # Turnovers Forced
                to_forced = stats.get('turnovers_forced', 0)
                self.team_stats_table.setItem(row, 4, NumericTableWidgetItem(to_forced, str(to_forced)))

                # Turnover Margin
                to_margin = stats.get('turnover_margin', 0)
                margin_str = f"+{to_margin}" if to_margin > 0 else str(to_margin)
                self.team_stats_table.setItem(row, 5, NumericTableWidgetItem(to_margin, margin_str))

                # Interceptions
                ints = stats.get('interceptions', 0)
                self.team_stats_table.setItem(row, 6, NumericTableWidgetItem(ints, str(ints)))

                # Sacks
                sacks = stats.get('sacks', 0)
                self.team_stats_table.setItem(row, 7, NumericTableWidgetItem(sacks, f"{sacks:.1f}"))

    def _update_summary(self):
        """Update summary panel with aggregate stats."""
        try:
            # Get game count
            games_count = self._unified_api.stats_get_game_count(self._season)
            self.games_label.setText(str(games_count))

            # Get player count
            player_count = self._unified_api.stats_get_player_count(self._season)
            self.players_label.setText(str(player_count))

            # Get current week (max week with data)
            current_week = self._unified_api.stats_get_current_week(self._season)
            self.week_label.setText(str(current_week))
        except Exception as e:
            print(f"[StatsView] Error updating summary: {e}")

    # === Table Population Methods ===

    def _populate_passing_table(self, leaders: List[Dict]):
        """Populate passing table with leader data."""
        from team_management.teams.team_loader import get_team_by_id

        self.passing_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.passing_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.passing_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "QB"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.passing_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.passing_table.setItem(row, 3, team_item)

            # Stats columns
            cmp = player.get("passing_completions", 0) or 0
            att = player.get("passing_attempts", 0) or 0
            yds = player.get("passing_yards", 0) or 0
            td = player.get("passing_tds", 0) or 0
            int_ = player.get("passing_interceptions", 0) or 0

            # Completion percentage calculation
            cmp_pct = (cmp / att * 100) if att > 0 else 0.0

            # Passer rating calculation
            rtg = self._calculate_passer_rating(cmp, att, yds, td, int_)

            self._set_stat_cell(self.passing_table, row, 4, cmp)
            self._set_stat_cell(self.passing_table, row, 5, att)
            self._set_stat_cell(self.passing_table, row, 6, f"{cmp_pct:.1f}%")
            self._set_stat_cell(self.passing_table, row, 7, yds)
            self._set_stat_cell(self.passing_table, row, 8, td, highlight=row == 0)
            self._set_stat_cell(self.passing_table, row, 9, int_)
            self._set_stat_cell(self.passing_table, row, 10, f"{rtg:.1f}")

    def _populate_rushing_table(self, leaders: List[Dict]):
        """Populate rushing table with leader data."""
        self.rushing_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.rushing_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.rushing_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "RB"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.rushing_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.rushing_table.setItem(row, 3, team_item)

            # Stats columns
            att = player.get("rushing_attempts", 0) or 0
            yds = player.get("rushing_yards", 0) or 0
            td = player.get("rushing_tds", 0) or 0
            lng = player.get("rushing_long", 0) or 0
            fum = player.get("rushing_fumbles", 0) or 0
            snaps = player.get("snap_counts_offense", 0) or 0

            # Calculate average
            avg = yds / att if att > 0 else 0.0

            self._set_stat_cell(self.rushing_table, row, 4, att)
            self._set_stat_cell(self.rushing_table, row, 5, yds, highlight=row == 0)
            self._set_stat_cell(self.rushing_table, row, 6, f"{avg:.1f}")
            self._set_stat_cell(self.rushing_table, row, 7, td)
            self._set_stat_cell(self.rushing_table, row, 8, lng)
            self._set_stat_cell(self.rushing_table, row, 9, fum)
            self._set_stat_cell(self.rushing_table, row, 10, snaps)

    def _populate_receiving_table(self, leaders: List[Dict]):
        """Populate receiving table with leader data."""
        self.receiving_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.receiving_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.receiving_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "WR"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.receiving_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.receiving_table.setItem(row, 3, team_item)

            # Stats columns
            rec = player.get("receptions", 0) or 0
            tgt = player.get("targets", 0) or 0
            yds = player.get("receiving_yards", 0) or 0
            td = player.get("receiving_tds", 0) or 0
            lng = player.get("receiving_long", 0) or 0
            drp = player.get("receiving_drops", 0) or 0
            snaps = player.get("snap_counts_offense", 0) or 0

            # Calculate average
            avg = yds / rec if rec > 0 else 0.0

            self._set_stat_cell(self.receiving_table, row, 4, rec)
            self._set_stat_cell(self.receiving_table, row, 5, tgt)
            self._set_stat_cell(self.receiving_table, row, 6, yds, highlight=row == 0)
            self._set_stat_cell(self.receiving_table, row, 7, f"{avg:.1f}")
            self._set_stat_cell(self.receiving_table, row, 8, td)
            self._set_stat_cell(self.receiving_table, row, 9, lng)
            self._set_stat_cell(self.receiving_table, row, 10, drp)
            self._set_stat_cell(self.receiving_table, row, 11, snaps)

    def _populate_defense_table(self, leaders: List[Dict]):
        """Populate defense table with leader data."""
        self.defense_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.defense_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.defense_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "LB"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.defense_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.defense_table.setItem(row, 3, team_item)

            # Stats columns - TKL, SOLO, AST, SACK, INT, PD, FF, FR
            tkl = player.get("tackles_total", 0) or 0
            solo = player.get("tackles_solo", 0) or 0
            ast = player.get("tackles_assist", 0) or 0
            sack = player.get("sacks", 0) or 0
            int_ = player.get("interceptions", 0) or 0
            pd = player.get("passes_defended", 0) or 0
            ff = player.get("forced_fumbles", 0) or 0
            fr = player.get("fumbles_recovered", 0) or 0

            # Columns: #, Player, Pos, Team, TKL, SOLO, AST, SACK, INT, PD, FF, FR
            self._set_stat_cell(self.defense_table, row, 4, tkl, highlight=row == 0)
            self._set_stat_cell(self.defense_table, row, 5, solo)
            self._set_stat_cell(self.defense_table, row, 6, ast)
            self._set_stat_cell(self.defense_table, row, 7, f"{sack:.1f}" if isinstance(sack, float) else sack)
            self._set_stat_cell(self.defense_table, row, 8, int_)
            self._set_stat_cell(self.defense_table, row, 9, pd)
            self._set_stat_cell(self.defense_table, row, 10, ff)
            self._set_stat_cell(self.defense_table, row, 11, fr)

    def _populate_kicking_table(self, leaders: List[Dict]):
        """Populate kicking table with leader data."""
        self.kicking_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.kicking_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.kicking_table.setItem(row, 1, QTableWidgetItem(name))

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.kicking_table.setItem(row, 2, team_item)

            # Stats columns
            fgm = player.get("field_goals_made", 0) or 0
            fga = player.get("field_goals_attempted", 0) or 0
            xpm = player.get("extra_points_made", 0) or 0
            xpa = player.get("extra_points_attempted", 0) or 0

            # Calculate percentages
            fg_pct = (fgm / fga * 100) if fga > 0 else 0.0

            # Calculate total points
            pts = (fgm * 3) + xpm

            self._set_stat_cell(self.kicking_table, row, 3, fgm, highlight=row == 0)
            self._set_stat_cell(self.kicking_table, row, 4, fga)
            self._set_stat_cell(self.kicking_table, row, 5, f"{fg_pct:.1f}%")
            self._set_stat_cell(self.kicking_table, row, 6, xpm)
            self._set_stat_cell(self.kicking_table, row, 7, xpa)
            self._set_stat_cell(self.kicking_table, row, 8, pts)

    def _populate_punting_table(self, leaders: List[Dict]):
        """Populate punting table with leader data."""
        self.punting_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.punting_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.punting_table.setItem(row, 1, QTableWidgetItem(name))

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.punting_table.setItem(row, 2, team_item)

            # Stats columns
            punts = player.get("punts", 0) or 0
            yds = player.get("punt_yards", 0) or 0

            # Calculate average
            avg = yds / punts if punts > 0 else 0.0

            self._set_stat_cell(self.punting_table, row, 3, punts, highlight=row == 0)
            self._set_stat_cell(self.punting_table, row, 4, yds)
            self._set_stat_cell(self.punting_table, row, 5, f"{avg:.1f}")

    def _populate_blocking_table(self, leaders: List[Dict]):
        """Populate blocking (O-Line) table with leader data."""
        self.blocking_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.blocking_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.blocking_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "OL"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.blocking_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.blocking_table.setItem(row, 3, team_item)

            # Stats columns
            # PB = Pass Blocks, PKS = Pancakes, SKA = Sacks Allowed, HUR = Hurries Allowed
            # PRES = Pressures Allowed, RBG = Run Block Grade, PBE = Pass Block Eff
            pb = player.get("pass_blocks", 0) or 0
            pks = player.get("pancakes", 0) or 0
            ska = player.get("sacks_allowed", 0) or 0
            hur = player.get("hurries_allowed", 0) or 0
            pres = player.get("pressures_allowed", 0) or 0
            rbg = player.get("run_blocking_grade", 0) or 0
            pbe = player.get("pass_blocking_efficiency", 0) or 0

            self._set_stat_cell(self.blocking_table, row, 4, pb, highlight=row == 0)
            self._set_stat_cell(self.blocking_table, row, 5, pks)
            self._set_stat_cell(self.blocking_table, row, 6, ska)
            self._set_stat_cell(self.blocking_table, row, 7, hur)
            self._set_stat_cell(self.blocking_table, row, 8, pres)
            self._set_stat_cell(self.blocking_table, row, 9, f"{rbg:.1f}" if isinstance(rbg, float) else rbg)
            self._set_stat_cell(self.blocking_table, row, 10, f"{pbe:.1f}%" if isinstance(pbe, float) else f"{pbe}%")

    def _populate_coverage_table(self, leaders: List[Dict]):
        """Populate coverage (DBs/LBs) table with leader data."""
        self.coverage_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.coverage_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.coverage_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "CB"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.coverage_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.coverage_table.setItem(row, 3, team_item)

            # Stats columns
            # TGT = Coverage Targets, CMP = Completions Allowed, YDS = Yards Allowed
            # CMP% = Completion % allowed, PD = Passes Defended, INT = Interceptions
            tgt = player.get("coverage_targets", 0) or 0
            cmp = player.get("coverage_completions", 0) or 0
            yds = player.get("coverage_yards_allowed", 0) or 0
            pd = player.get("passes_defended", 0) or 0
            int_ = player.get("interceptions", 0) or 0
            snaps = player.get("snap_counts_defense", 0) or 0

            # Calculate completion percentage allowed
            cmp_pct = (cmp / tgt * 100) if tgt > 0 else 0.0

            self._set_stat_cell(self.coverage_table, row, 4, tgt, highlight=row == 0)
            self._set_stat_cell(self.coverage_table, row, 5, cmp)
            self._set_stat_cell(self.coverage_table, row, 6, yds)
            self._set_stat_cell(self.coverage_table, row, 7, f"{cmp_pct:.1f}%")
            self._set_stat_cell(self.coverage_table, row, 8, pd)
            self._set_stat_cell(self.coverage_table, row, 9, int_)
            self._set_stat_cell(self.coverage_table, row, 10, snaps)

    def _populate_pass_rush_table(self, leaders: List[Dict]):
        """Populate pass rush (DL/EDGE) table with leader data."""
        self.pass_rush_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.pass_rush_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            self.pass_rush_table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos = self._get_position_abbr(player.get("position", "DE"))
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.pass_rush_table.setItem(row, 2, pos_item)

            # Team abbreviation
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.pass_rush_table.setItem(row, 3, team_item)

            # Stats columns
            # PR ATT = Pass Rush Attempts, PR WIN = Pass Rush Wins, WIN% = Win Rate
            # SACK = Sacks, DBL = Times Double Teamed
            pr_att = player.get("pass_rush_attempts", 0) or 0
            pr_win = player.get("pass_rush_wins", 0) or 0
            sack = player.get("sacks", 0) or 0
            dbl = player.get("times_double_teamed", 0) or 0
            snaps = player.get("snap_counts_defense", 0) or 0

            # Calculate win percentage
            win_pct = (pr_win / pr_att * 100) if pr_att > 0 else 0.0

            self._set_stat_cell(self.pass_rush_table, row, 4, pr_att, highlight=row == 0)
            self._set_stat_cell(self.pass_rush_table, row, 5, pr_win)
            self._set_stat_cell(self.pass_rush_table, row, 6, f"{win_pct:.1f}%")
            self._set_stat_cell(self.pass_rush_table, row, 7, f"{sack:.1f}" if isinstance(sack, float) else sack)
            self._set_stat_cell(self.pass_rush_table, row, 8, dbl)
            self._set_stat_cell(self.pass_rush_table, row, 9, snaps)

    # === Helper Methods ===

    def _set_stat_cell(
        self,
        table: QTableWidget,
        row: int,
        col: int,
        value: Any,
        highlight: bool = False
    ):
        """Set a stat cell with proper formatting and numeric sorting."""
        # Parse numeric value for sorting
        sort_value = value
        display_text = str(value)

        if isinstance(value, str):
            # Handle percentage strings like "85.5%"
            if value.endswith("%"):
                try:
                    sort_value = float(value[:-1])
                except ValueError:
                    sort_value = 0
            else:
                # Try to parse as float
                try:
                    sort_value = float(value)
                except ValueError:
                    sort_value = value  # Keep as string

        # Use NumericTableWidgetItem for numeric values
        if isinstance(sort_value, (int, float)):
            item = NumericTableWidgetItem(sort_value, display_text)
        else:
            item = QTableWidgetItem(display_text)

        item.setTextAlignment(Qt.AlignCenter)

        if highlight:
            item.setForeground(QColor("#2E7D32"))
            item.setFont(QFont("Arial", 10, QFont.Bold))

        table.setItem(row, col, item)

    def _get_team_abbr(self, team_id: int) -> str:
        """Get team abbreviation from team ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else "FA"
        except Exception:
            return "FA" if team_id == 0 else f"T{team_id}"

    def _get_position_abbr(self, position: str) -> str:
        """Get position abbreviation."""
        # Map common positions to abbreviations
        pos_map = {
            "quarterback": "QB",
            "running_back": "RB",
            "wide_receiver": "WR",
            "tight_end": "TE",
            "left_tackle": "LT",
            "left_guard": "LG",
            "center": "C",
            "right_guard": "RG",
            "right_tackle": "RT",
            "defensive_end": "DE",
            "defensive_tackle": "DT",
            "linebacker": "LB",
            "cornerback": "CB",
            "safety": "S",
            "kicker": "K",
            "punter": "P",
        }

        pos_lower = position.lower().replace(" ", "_")
        return pos_map.get(pos_lower, position[:3].upper())

    def _calculate_passer_rating(
        self,
        completions: int,
        attempts: int,
        yards: int,
        touchdowns: int,
        interceptions: int
    ) -> float:
        """
        Calculate NFL passer rating.

        Formula:
            a = ((completions / attempts) - 0.3) * 5
            b = ((yards / attempts) - 3) * 0.25
            c = (touchdowns / attempts) * 20
            d = 2.375 - ((interceptions / attempts) * 25)

            rating = ((a + b + c + d) / 6) * 100

        Returns:
            Passer rating (0.0 to 158.3)
        """
        if attempts == 0:
            return 0.0

        # Component A: Completion percentage
        a = ((completions / attempts) - 0.3) * 5
        a = max(0, min(2.375, a))  # Clamp to [0, 2.375]

        # Component B: Yards per attempt
        b = ((yards / attempts) - 3) * 0.25
        b = max(0, min(2.375, b))

        # Component C: Touchdown percentage
        c = (touchdowns / attempts) * 20
        c = max(0, min(2.375, c))

        # Component D: Interception percentage
        d = 2.375 - ((interceptions / attempts) * 25)
        d = max(0, min(2.375, d))

        # Final rating
        rating = ((a + b + c + d) / 6) * 100

        return rating

    def clear(self):
        """Clear all data from the view."""
        self.games_label.setText("0")
        self.players_label.setText("0")
        self.week_label.setText("0")

        self.passing_table.setRowCount(0)
        self.rushing_table.setRowCount(0)
        self.receiving_table.setRowCount(0)
        self.defense_table.setRowCount(0)
        self.kicking_table.setRowCount(0)
        self.punting_table.setRowCount(0)
        self.blocking_table.setRowCount(0)
        self.coverage_table.setRowCount(0)
        self.pass_rush_table.setRowCount(0)
