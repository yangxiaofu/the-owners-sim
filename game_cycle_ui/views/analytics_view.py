"""
Analytics View - Displays PFF-style player grades and advanced metrics.

Shows player grades (0-100 scale, 60 = neutral) with:
- Grade leaderboards by position
- Team grade breakdowns
- Advanced metrics (EPA, success rate)
- Player grade history
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFrame, QTabWidget, QPushButton, QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from constants.position_abbreviations import get_position_abbreviation
from game_cycle_ui.theme import TABLE_HEADER_STYLE


class NumericTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts numerically instead of alphabetically."""

    def __init__(self, value: Any, display_text: str = None):
        super().__init__(display_text if display_text else str(value))
        self._sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            self_val = self._sort_value if self._sort_value is not None else 0
            other_val = other._sort_value if other._sort_value is not None else 0
            return self_val < other_val
        return super().__lt__(other)


class GradeProgressBar(QProgressBar):
    """Custom progress bar for displaying grades with color coding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setTextVisible(True)
        self.setFixedHeight(20)
        self.setFixedWidth(100)

    def set_grade(self, grade: float):
        """Set grade value with appropriate color."""
        self.setValue(int(grade))
        self.setFormat(f"{grade:.1f}")

        # Color based on grade tier
        if grade >= 90:
            color = "#1565C0"  # Elite - Blue
        elif grade >= 80:
            color = "#2E7D32"  # Great - Green
        elif grade >= 70:
            color = "#558B2F"  # Good - Light Green
        elif grade >= 60:
            color = "#F9A825"  # Average - Yellow
        elif grade >= 50:
            color = "#EF6C00"  # Below Average - Orange
        else:
            color = "#C62828"  # Poor - Red

        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class AnalyticsView(QWidget):
    """
    View for displaying PFF-style player grades and advanced analytics.

    Shows:
    - Grade Leaderboard: Top players by overall grade, filterable by position
    - Team Grades: All players on a team sorted by grade
    - Advanced Metrics: EPA, success rate, and other team-level metrics
    """

    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._season: int = 2025
        self._dynasty_id: str = ""
        self._db_path: str = ""
        self._stats_api = None
        self._position_filter: Optional[str] = None
        self._team_filter: Optional[int] = None
        self._user_team_id: Optional[int] = None
        self._selected_player_id: Optional[int] = None
        self._selected_player_name: str = ""
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        self._create_header(layout)
        self._create_summary_panel(layout)
        self._create_tabs(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title, filters, and refresh button."""
        header = QHBoxLayout()

        title = QLabel("PLAYER GRADES")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header.addWidget(title)

        header.addStretch()

        # Position filter
        pos_label = QLabel("Position:")
        header.addWidget(pos_label)

        self.position_combo = QComboBox()
        self.position_combo.setMinimumWidth(120)
        self._populate_position_combo()
        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        header.addWidget(self.position_combo)

        header.addSpacing(15)

        # Team filter
        team_label = QLabel("Team:")
        header.addWidget(team_label)

        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(150)
        self.team_combo.addItem("All Teams", None)
        self._populate_team_combo()
        self.team_combo.currentIndexChanged.connect(self._on_team_changed)
        header.addWidget(self.team_combo)

        header.addSpacing(15)

        # Season selector
        season_label = QLabel("Season:")
        header.addWidget(season_label)

        self.season_combo = QComboBox()
        self.season_combo.setMinimumWidth(100)
        self.season_combo.currentIndexChanged.connect(self._on_season_changed)
        header.addWidget(self.season_combo)

        header.addSpacing(15)

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

    def _populate_position_combo(self):
        """Populate position dropdown."""
        self.position_combo.addItem("All Positions", None)

        positions = [
            ("Offense", None),
            ("  QB", "QB"),
            ("  RB", "RB"),
            ("  WR", "WR"),
            ("  TE", "TE"),
            ("  OL", "OL"),
            ("Defense", None),
            ("  DL", "DL"),
            ("  LB", "LB"),
            ("  DB", "DB"),
        ]

        for display, value in positions:
            if value is None and display != "All Positions":
                # Section header
                self.position_combo.addItem(display, "__header__")
            else:
                self.position_combo.addItem(display, value)

    def _populate_team_combo(self):
        """Populate team dropdown with all NFL teams."""
        try:
            from team_management.teams.team_loader import get_all_teams
            teams = get_all_teams()
            sorted_teams = sorted(teams, key=lambda t: t.city)
            for team in sorted_teams:
                self.team_combo.addItem(f"{team.city} {team.nickname}", team.team_id)
        except Exception as e:
            print(f"[AnalyticsView] Error loading teams: {e}")

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary panel with grade distribution."""
        summary_group = QGroupBox("Grade Distribution")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Grade tier counts
        self._create_grade_tier_widget(summary_layout, "elite_label", "Elite (90+)", "0", "#1565C0")
        self._create_grade_tier_widget(summary_layout, "great_label", "Great (80-89)", "0", "#2E7D32")
        self._create_grade_tier_widget(summary_layout, "good_label", "Good (70-79)", "0", "#558B2F")
        self._create_grade_tier_widget(summary_layout, "avg_label", "Average (60-69)", "0", "#F9A825")
        self._create_grade_tier_widget(summary_layout, "below_label", "Below Avg (<60)", "0", "#C62828")

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_grade_tier_widget(
        self,
        parent_layout: QHBoxLayout,
        attr_name: str,
        title: str,
        initial_value: str,
        color: str
    ):
        """Create a single grade tier widget."""
        frame = QFrame()
        vlayout = QVBoxLayout(frame)
        vlayout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        vlayout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(QFont("Arial", 18, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        vlayout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        parent_layout.addWidget(frame)

    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create tab widget with grade tables."""
        self.tabs = QTabWidget()

        # Grade Leaders tab
        self.leaders_table = self._create_grade_table([
            "#", "Player", "Pos", "Team", "Grade", "Snaps", "Pos Rank"
        ])
        self.tabs.addTab(self.leaders_table, "Grade Leaders")

        # Team Grades tab
        self.team_table = self._create_grade_table([
            "#", "Player", "Pos", "Grade", "Off", "Def", "Snaps", "Trend"
        ])
        self.tabs.addTab(self.team_table, "Team Grades")

        # Advanced Metrics tab
        self.metrics_table = self._create_metrics_table([
            "Team", "EPA/Play", "Pass EPA", "Rush EPA", "Success %", "Pass %", "Rush %"
        ])
        self.tabs.addTab(self.metrics_table, "Advanced Metrics")

        # Player History tab
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 0, 0, 0)

        # Player name header for history tab
        self.history_header = QLabel("Click a player in Grade Leaders or Team Grades to view history")
        self.history_header.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        history_layout.addWidget(self.history_header)

        self.history_table = self._create_grade_table([
            "Week", "Opponent", "Grade", "Off", "Def", "Snaps", "Key Stats"
        ])
        history_layout.addWidget(self.history_table)
        self.tabs.addTab(history_widget, "Player History")

        # Connect click handlers for player selection
        self.leaders_table.cellClicked.connect(self._on_leaders_table_clicked)
        self.team_table.cellClicked.connect(self._on_team_table_clicked)

        parent_layout.addWidget(self.tabs, stretch=1)

    def _create_grade_table(self, headers: List[str]) -> QTableWidget:
        """Create a configured grade table with sorting enabled."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        header = table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)

        return table

    def _create_metrics_table(self, headers: List[str]) -> QTableWidget:
        """Create metrics table with team-level stats."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        header = table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)

        return table

    # === Context and Data Methods ===

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """Set dynasty context for data queries."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

        # Initialize StatsAPI
        from statistics.stats_api import StatsAPI
        self._stats_api = StatsAPI(db_path, dynasty_id)

        self._populate_season_combo()

    def set_user_team_id(self, team_id: int):
        """Set the user's team ID and default Team Grades tab to show this team."""
        self._user_team_id = team_id
        # Auto-select user's team in team combo and switch to Team Grades tab
        self._select_user_team_in_combo()

    def _select_user_team_in_combo(self):
        """Select the user's team in the team combo box."""
        if not self._user_team_id:
            return
        # Find and select the user's team in the combo box
        for i in range(self.team_combo.count()):
            if self.team_combo.itemData(i) == self._user_team_id:
                self.team_combo.setCurrentIndex(i)
                break

    def _populate_season_combo(self):
        """Populate season dropdown."""
        self.season_combo.blockSignals(True)
        self.season_combo.clear()

        for year in range(self._season, self._season - 5, -1):
            self.season_combo.addItem(str(year), year)

        self.season_combo.blockSignals(False)

    def refresh_data(self):
        """Refresh all grade data from database."""
        if not self._stats_api:
            return

        self._load_grade_leaders()
        self._load_team_grades()
        self._load_advanced_metrics()
        self._update_summary()

    def _on_season_changed(self, index: int):
        """Handle season selection change."""
        if index >= 0:
            self._season = self.season_combo.itemData(index)
            self.refresh_data()

    def _on_position_changed(self, index: int):
        """Handle position filter change."""
        if index >= 0:
            value = self.position_combo.itemData(index)
            if value == "__header__":
                return
            self._position_filter = value
            self.refresh_data()

    def _on_team_changed(self, index: int):
        """Handle team filter change."""
        if index >= 0:
            self._team_filter = self.team_combo.itemData(index)
            if self._team_filter:
                self.tabs.setCurrentWidget(self.team_table)
            self.refresh_data()

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_data()
        self.refresh_requested.emit()

    # === Data Loading Methods ===

    def _load_grade_leaders(self):
        """Load grade leaders into table."""
        try:
            leaders = self._stats_api.get_grade_leaders(
                season=self._season,
                position=self._position_filter,
                limit=50
            )
            # Debug logging to help diagnose position filter issues
            print(f"[AnalyticsView] Grade leaders: position={self._position_filter}, count={len(leaders)}")
            self._populate_leaders_table(leaders)
        except Exception as e:
            print(f"[AnalyticsView] Error loading grade leaders: {e}")
            self.leaders_table.setRowCount(0)

    def _load_team_grades(self):
        """Load team grades into table."""
        if not self._team_filter:
            self.team_table.setRowCount(1)
            msg_item = QTableWidgetItem("Select a team to view grades")
            msg_item.setForeground(QColor("#666"))
            self.team_table.setItem(0, 1, msg_item)
            return

        try:
            grades = self._stats_api.get_team_grades(
                team_id=self._team_filter,
                season=self._season
            )
            self._populate_team_table(grades)
        except Exception as e:
            print(f"[AnalyticsView] Error loading team grades: {e}")
            self.team_table.setRowCount(0)

    def _load_advanced_metrics(self):
        """Load advanced metrics into table."""
        try:
            metrics = self._stats_api.get_advanced_metrics(
                season=self._season,
                team_id=self._team_filter
            )
            self._populate_metrics_table(metrics)
        except Exception as e:
            print(f"[AnalyticsView] Error loading advanced metrics: {e}")
            self.metrics_table.setRowCount(0)

    def _update_summary(self):
        """Update grade distribution summary."""
        try:
            leaders = self._stats_api.get_grade_leaders(
                season=self._season,
                limit=500
            )

            elite = sum(1 for p in leaders if p.get("overall_grade", 0) >= 90)
            great = sum(1 for p in leaders if 80 <= p.get("overall_grade", 0) < 90)
            good = sum(1 for p in leaders if 70 <= p.get("overall_grade", 0) < 80)
            avg = sum(1 for p in leaders if 60 <= p.get("overall_grade", 0) < 70)
            below = sum(1 for p in leaders if p.get("overall_grade", 0) < 60)

            self.elite_label.setText(str(elite))
            self.great_label.setText(str(great))
            self.good_label.setText(str(good))
            self.avg_label.setText(str(avg))
            self.below_label.setText(str(below))
        except Exception as e:
            print(f"[AnalyticsView] Error updating summary: {e}")

    # === Table Population Methods ===

    def _populate_leaders_table(self, leaders: List[Dict]):
        """Populate grade leaders table."""
        self.leaders_table.setRowCount(len(leaders))

        for row, player in enumerate(leaders):
            # Rank - store player_id in the first cell's data
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            rank_item.setData(Qt.UserRole, player.get("player_id"))
            self.leaders_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, player.get("player_id"))
            self.leaders_table.setItem(row, 1, name_item)

            # Position (convert to abbreviation)
            pos = player.get("position", "")
            pos_abbr = get_position_abbreviation(pos) if pos else ""
            pos_item = QTableWidgetItem(pos_abbr)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.leaders_table.setItem(row, 2, pos_item)

            # Team
            team_id = player.get("team_id", 0)
            team_abbr = self._get_team_abbr(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.leaders_table.setItem(row, 3, team_item)

            # Grade with color
            grade = player.get("overall_grade", 0.0)
            self._set_grade_cell(self.leaders_table, row, 4, grade)

            # Snaps
            snaps = player.get("total_snaps", 0)
            self._set_stat_cell(self.leaders_table, row, 5, snaps)

            # Position rank
            pos_rank = player.get("position_rank", "-")
            rank_text = f"#{pos_rank}" if isinstance(pos_rank, int) else str(pos_rank)
            self._set_stat_cell(self.leaders_table, row, 6, rank_text)

    def _populate_team_table(self, grades: List[Dict]):
        """Populate team grades table."""
        self.team_table.clearSpans()
        self.team_table.setRowCount(len(grades))

        for row, player in enumerate(grades):
            # Rank - store player_id in the first cell's data
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            rank_item.setData(Qt.UserRole, player.get("player_id"))
            self.team_table.setItem(row, 0, rank_item)

            # Player name
            name = player.get("player_name", "Unknown")
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, player.get("player_id"))
            self.team_table.setItem(row, 1, name_item)

            # Position (convert to abbreviation)
            pos = player.get("position", "")
            pos_abbr = get_position_abbreviation(pos) if pos else ""
            pos_item = QTableWidgetItem(pos_abbr)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.team_table.setItem(row, 2, pos_item)

            # Overall grade
            overall = player.get("overall_grade", 0.0)
            self._set_grade_cell(self.team_table, row, 3, overall)

            # Offense grade
            off_grade = player.get("offense_grade", 0.0)
            if off_grade > 0:
                self._set_grade_cell(self.team_table, row, 4, off_grade)
            else:
                self._set_stat_cell(self.team_table, row, 4, "-")

            # Defense grade
            def_grade = player.get("defense_grade", 0.0)
            if def_grade > 0:
                self._set_grade_cell(self.team_table, row, 5, def_grade)
            else:
                self._set_stat_cell(self.team_table, row, 5, "-")

            # Snaps
            snaps = player.get("total_snaps", 0)
            self._set_stat_cell(self.team_table, row, 6, snaps)

            # Trend (comparing recent to overall)
            trend = self._calculate_trend(player)
            trend_item = QTableWidgetItem(trend)
            trend_item.setTextAlignment(Qt.AlignCenter)
            if "+" in trend:
                trend_item.setForeground(QColor("#2E7D32"))
            elif "-" in trend and trend != "-":
                trend_item.setForeground(QColor("#C62828"))
            self.team_table.setItem(row, 7, trend_item)

    def _populate_metrics_table(self, metrics: List[Dict]):
        """Populate advanced metrics table."""
        self.metrics_table.setRowCount(len(metrics))

        for row, team_metrics in enumerate(metrics):
            # Team name
            team_id = team_metrics.get("team_id", 0)
            team_name = self._get_team_name(team_id)
            self.metrics_table.setItem(row, 0, QTableWidgetItem(team_name))

            # EPA per play
            epa_play = team_metrics.get("epa_per_play")
            self._set_epa_cell(self.metrics_table, row, 1, epa_play)

            # Pass EPA
            pass_epa = team_metrics.get("epa_passing")
            self._set_epa_cell(self.metrics_table, row, 2, pass_epa)

            # Rush EPA
            rush_epa = team_metrics.get("epa_rushing")
            self._set_epa_cell(self.metrics_table, row, 3, rush_epa)

            # Success Rate
            success = team_metrics.get("success_rate")
            if success is not None:
                self._set_stat_cell(self.metrics_table, row, 4, f"{success * 100:.1f}%")
            else:
                self._set_stat_cell(self.metrics_table, row, 4, "-")

            # Pass Success Rate
            pass_success = team_metrics.get("passing_success_rate")
            if pass_success is not None:
                self._set_stat_cell(self.metrics_table, row, 5, f"{pass_success * 100:.1f}%")
            else:
                self._set_stat_cell(self.metrics_table, row, 5, "-")

            # Rush Success Rate
            rush_success = team_metrics.get("rushing_success_rate")
            if rush_success is not None:
                self._set_stat_cell(self.metrics_table, row, 6, f"{rush_success * 100:.1f}%")
            else:
                self._set_stat_cell(self.metrics_table, row, 6, "-")

    # === Helper Methods ===

    def _set_grade_cell(self, table: QTableWidget, row: int, col: int, grade: float):
        """Set a grade cell with color coding."""
        item = NumericTableWidgetItem(grade, f"{grade:.1f}")
        item.setTextAlignment(Qt.AlignCenter)

        # Color based on grade tier
        if grade >= 90:
            item.setForeground(QColor("#1565C0"))
            item.setFont(QFont("Arial", 10, QFont.Bold))
        elif grade >= 80:
            item.setForeground(QColor("#2E7D32"))
            item.setFont(QFont("Arial", 10, QFont.Bold))
        elif grade >= 70:
            item.setForeground(QColor("#558B2F"))
        elif grade >= 60:
            item.setForeground(QColor("#F9A825"))
        else:
            item.setForeground(QColor("#C62828"))

        table.setItem(row, col, item)

    def _set_epa_cell(self, table: QTableWidget, row: int, col: int, epa: Optional[float]):
        """Set an EPA cell with color coding (positive = green, negative = red)."""
        if epa is None:
            self._set_stat_cell(table, row, col, "-")
            return

        item = NumericTableWidgetItem(epa, f"{epa:+.2f}")
        item.setTextAlignment(Qt.AlignCenter)

        if epa > 0:
            item.setForeground(QColor("#2E7D32"))
        elif epa < 0:
            item.setForeground(QColor("#C62828"))

        table.setItem(row, col, item)

    def _set_stat_cell(self, table: QTableWidget, row: int, col: int, value: Any):
        """Set a stat cell with proper formatting."""
        sort_value = value
        display_text = str(value)

        if isinstance(value, str):
            if value.endswith("%"):
                try:
                    sort_value = float(value[:-1])
                except ValueError:
                    sort_value = 0
            else:
                try:
                    sort_value = float(value)
                except ValueError:
                    sort_value = value

        if isinstance(sort_value, (int, float)):
            item = NumericTableWidgetItem(sort_value, display_text)
        else:
            item = QTableWidgetItem(display_text)

        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _calculate_trend(self, player: Dict) -> str:
        """Calculate trend indicator for player grade."""
        recent = player.get("recent_grade")
        overall = player.get("overall_grade", 0)

        if recent is None or overall == 0:
            return "-"

        diff = recent - overall
        if diff > 2:
            return f"+{diff:.1f}"
        elif diff < -2:
            return f"{diff:.1f}"
        return "="

    def _get_team_abbr(self, team_id: int) -> str:
        """Get team abbreviation from team ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else "FA"
        except Exception:
            return "FA" if team_id == 0 else f"T{team_id}"

    def _get_team_name(self, team_id: int) -> str:
        """Get full team name from team ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return f"{team.city} {team.nickname}" if team else "Unknown"
        except Exception:
            return f"Team {team_id}"

    def clear(self):
        """Clear all data from the view."""
        self.elite_label.setText("0")
        self.great_label.setText("0")
        self.good_label.setText("0")
        self.avg_label.setText("0")
        self.below_label.setText("0")

        self.leaders_table.setRowCount(0)
        self.team_table.setRowCount(0)
        self.metrics_table.setRowCount(0)
        self.history_table.setRowCount(0)

    # === Player History Click Handlers ===

    def _on_leaders_table_clicked(self, row: int, col: int):
        """Handle click on leaders table - show player history."""
        item = self.leaders_table.item(row, 0)  # Get rank cell which has player_id
        if item:
            player_id = item.data(Qt.UserRole)
            name_item = self.leaders_table.item(row, 1)
            player_name = name_item.text() if name_item else "Unknown"
            self._show_player_history(player_id, player_name)

    def _on_team_table_clicked(self, row: int, col: int):
        """Handle click on team table - show player history."""
        item = self.team_table.item(row, 0)  # Get rank cell which has player_id
        if item:
            player_id = item.data(Qt.UserRole)
            name_item = self.team_table.item(row, 1)
            player_name = name_item.text() if name_item else "Unknown"
            self._show_player_history(player_id, player_name)

    def _show_player_history(self, player_id: int, player_name: str):
        """Load and display player history, then switch to history tab."""
        if not player_id:
            return

        self._selected_player_id = player_id
        self._selected_player_name = player_name

        # Update header
        self.history_header.setText(f"Game-by-Game Grades: {player_name}")
        self.history_header.setStyleSheet(
            "color: #1976D2; font-weight: bold; font-size: 13px; padding: 8px;"
        )

        # Load history data
        self._load_player_history(player_id)

        # Switch to history tab
        self.tabs.setCurrentIndex(3)  # Player History is the 4th tab (index 3)

    def _load_player_history(self, player_id: int):
        """Load player's game-by-game grades from database."""
        if not self._stats_api:
            return

        try:
            history = self._stats_api.get_player_game_history(
                player_id=player_id,
                season=self._season
            )
            self._populate_history_table(history)
        except Exception as e:
            print(f"[AnalyticsView] Error loading player history: {e}")
            self.history_table.setRowCount(1)
            msg_item = QTableWidgetItem(f"Error loading history: {e}")
            msg_item.setForeground(QColor("#C62828"))
            self.history_table.setItem(0, 0, msg_item)

    def _populate_history_table(self, history: List[Dict]):
        """Populate player history table with game-by-game data."""
        if not history:
            self.history_table.setRowCount(1)
            msg_item = QTableWidgetItem("No game data found for this player")
            msg_item.setForeground(QColor("#666"))
            self.history_table.setItem(0, 0, msg_item)
            return

        self.history_table.setRowCount(len(history))

        for row, game in enumerate(history):
            # Week
            week = game.get("week", 0)
            week_item = QTableWidgetItem(f"Week {week}")
            week_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 0, week_item)

            # Opponent
            opponent_id = game.get("opponent_team_id", 0)
            opponent = self._get_team_abbr(opponent_id)
            opp_item = QTableWidgetItem(opponent)
            opp_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 1, opp_item)

            # Overall grade
            grade = game.get("overall_grade", 0.0)
            self._set_grade_cell(self.history_table, row, 2, grade)

            # Offense grade
            off_grade = game.get("offense_grade", 0.0)
            if off_grade > 0:
                self._set_grade_cell(self.history_table, row, 3, off_grade)
            else:
                self._set_stat_cell(self.history_table, row, 3, "-")

            # Defense grade
            def_grade = game.get("defense_grade", 0.0)
            if def_grade > 0:
                self._set_grade_cell(self.history_table, row, 4, def_grade)
            else:
                self._set_stat_cell(self.history_table, row, 4, "-")

            # Snaps
            snaps = game.get("snaps", 0)
            self._set_stat_cell(self.history_table, row, 5, snaps)

            # Key stats summary
            key_stats = game.get("key_stats", "-")
            self.history_table.setItem(row, 6, QTableWidgetItem(str(key_stats)))
