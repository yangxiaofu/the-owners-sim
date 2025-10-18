"""
Stats Leaders Widget for The Owner's Sim

Displays league-wide statistical leaderboards across all categories.
Integrated with StatsAPI for real database data.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTabWidget, QComboBox, QHeaderView
)
from PySide6.QtCore import Qt


class StatsLeadersWidget(QWidget):
    """
    League-wide statistical leaderboards widget.

    Displays top players across all categories:
    - Passing (QB stats)
    - Rushing (RB stats)
    - Receiving (WR/TE stats)
    - Defense (tackle, sack, INT leaders)
    - Special Teams (kicking, punting stats)

    Integrated with StatsAPI for real database data.
    """

    def __init__(self, parent=None, db_path: str = "data/database/nfl_simulation.db", dynasty_id: str = "default", season: int = 2025):
        super().__init__(parent)

        # Store parameters
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize StatsAPI
        from statistics.stats_api import StatsAPI
        self.stats_api = StatsAPI(db_path, dynasty_id)

        # Table references (will be set when tables are created)
        self.passing_table = None
        self.rushing_table = None
        self.receiving_table = None
        self.defense_table = None
        self.special_teams_table = None

        # Info label references
        self.passing_info_label = None
        self.rushing_info_label = None
        self.receiving_info_label = None
        self.defense_info_label = None
        self.special_teams_info_label = None

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header with filters
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Category tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_passing_leaders(), "Passing")
        self.tabs.addTab(self._create_rushing_leaders(), "Rushing")
        self.tabs.addTab(self._create_receiving_leaders(), "Receiving")
        self.tabs.addTab(self._create_defense_leaders(), "Defense")
        self.tabs.addTab(self._create_special_teams_leaders(), "Special Teams")

        layout.addWidget(self.tabs)

        # Load initial data
        self.load_data()

    def showEvent(self, event):
        """
        Override showEvent to refresh stats when widget becomes visible.

        This ensures stats are always current when user clicks the Stats Leaders tab.
        """
        super().showEvent(event)

        # Refresh stats whenever the widget is shown
        # (happens when user clicks Stats Leaders tab or switches from another tab)
        self.load_data()

    def _create_header(self) -> QHBoxLayout:
        """Create header with filter controls."""
        header = QHBoxLayout()

        # Title
        title = QLabel("NFL Statistical Leaders")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Conference filter
        conf_label = QLabel("Conference:")
        self.conf_filter = QComboBox()
        self.conf_filter.addItems(["All", "AFC", "NFC"])
        self.conf_filter.setMinimumWidth(100)
        self.conf_filter.currentIndexChanged.connect(self.on_filter_changed)

        # Division filter
        div_label = QLabel("Division:")
        self.div_filter = QComboBox()
        self.div_filter.addItems(["All", "East", "North", "South", "West"])
        self.div_filter.setMinimumWidth(100)
        self.div_filter.currentIndexChanged.connect(self.on_filter_changed)

        header.addWidget(conf_label)
        header.addWidget(self.conf_filter)
        header.addWidget(div_label)
        header.addWidget(self.div_filter)

        return header

    def _create_passing_leaders(self) -> QWidget:
        """Create passing leaders table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "Rank", "Player", "Team", "Games", "Comp", "Att", "Yards", "TDs", "INTs", "Rating"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Player name
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Team
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Info label
        info = QLabel("Loading passing leaders...")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.passing_table = table
        self.passing_info_label = info

        return widget

    def _create_rushing_leaders(self) -> QWidget:
        """Create rushing leaders table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "Rank", "Player", "Team", "Games", "Attempts", "Yards", "Avg", "TDs", "Long"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        info = QLabel("Loading rushing leaders...")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.rushing_table = table
        self.rushing_info_label = info

        return widget

    def _create_receiving_leaders(self) -> QWidget:
        """Create receiving leaders table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "Rank", "Player", "Team", "Games", "Rec", "Yards", "Avg", "TDs", "Long"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        info = QLabel("Loading receiving leaders...")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.receiving_table = table
        self.receiving_info_label = info

        return widget

    def _create_defense_leaders(self) -> QWidget:
        """Create defensive leaders table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "Rank", "Player", "Team", "Games", "Tackles", "Assists", "Sacks", "INTs", "FF", "TDs"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        info = QLabel("Loading defensive leaders...")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.defense_table = table
        self.defense_info_label = info

        return widget

    def _create_special_teams_leaders(self) -> QWidget:
        """Create special teams leaders table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "Rank", "Player", "Team", "Pos", "FGM", "FGA", "FG%", "Long", "XPM", "XPA"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        info = QLabel("Loading special teams leaders...")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.special_teams_table = table
        self.special_teams_info_label = info

        return widget

    def on_filter_changed(self):
        """Reload data when filters change"""
        self.load_data()

    def load_data(self):
        """Load all leaderboards"""
        self.load_passing_leaders()
        self.load_rushing_leaders()
        self.load_receiving_leaders()
        self.load_defense_leaders()
        self.load_special_teams_leaders()

    def load_passing_leaders(self):
        """Load passing leaders from API"""
        try:
            # DEBUG: Print query parameters
            print(f"[DEBUG StatsLeadersWidget] Querying passing leaders:")
            print(f"  dynasty_id = '{self.dynasty_id}'")
            print(f"  season = {self.season}")

            # Get current filter values
            conference = self.conf_filter.currentText()
            division = self.div_filter.currentText()

            # Build filters
            filters = {}
            if conference != "All":
                filters['conference'] = conference
            if division != "All":
                filters['division'] = division

            # Call API
            leaders = self.stats_api.get_passing_leaders(
                season=self.season,
                limit=25,
                filters=filters if filters else None
            )

            # DEBUG: Print results
            print(f"  Results: {len(leaders)} passing leaders found")

            # Populate table
            self.passing_table.setRowCount(len(leaders))
            for row, leader in enumerate(leaders):
                # Column 0: Rank
                self.passing_table.setItem(row, 0, QTableWidgetItem(str(leader.league_rank or row + 1)))
                # Column 1: Player name
                self.passing_table.setItem(row, 1, QTableWidgetItem(leader.player_name))
                # Column 2: Team (get team name from team_id)
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(leader.team_id)
                team_name = team.full_name if team else f"Team {leader.team_id}"
                self.passing_table.setItem(row, 2, QTableWidgetItem(team_name))
                # Column 3: Games
                self.passing_table.setItem(row, 3, QTableWidgetItem(str(leader.games)))
                # Column 4: Completions
                self.passing_table.setItem(row, 4, QTableWidgetItem(str(leader.completions)))
                # Column 5: Attempts
                self.passing_table.setItem(row, 5, QTableWidgetItem(str(leader.attempts)))
                # Column 6: Yards
                self.passing_table.setItem(row, 6, QTableWidgetItem(str(leader.yards)))
                # Column 7: TDs
                self.passing_table.setItem(row, 7, QTableWidgetItem(str(leader.touchdowns)))
                # Column 8: INTs
                self.passing_table.setItem(row, 8, QTableWidgetItem(str(leader.interceptions)))
                # Column 9: Rating
                self.passing_table.setItem(row, 9, QTableWidgetItem(f"{leader.passer_rating:.1f}"))

                # Make all cells non-editable and center-aligned
                for col in range(10):
                    item = self.passing_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(leaders) > 0:
                self.passing_info_label.setText(f"Showing top {len(leaders)} passing leaders")
            else:
                self.passing_info_label.setText("No passing leaders found")

        except Exception as e:
            print(f"Error loading passing leaders: {e}")
            import traceback
            traceback.print_exc()
            self.passing_info_label.setText(f"Error loading passing leaders: {str(e)}")

    def load_rushing_leaders(self):
        """Load rushing leaders from API"""
        try:
            # Get current filter values
            conference = self.conf_filter.currentText()
            division = self.div_filter.currentText()

            # Build filters
            filters = {}
            if conference != "All":
                filters['conference'] = conference
            if division != "All":
                filters['division'] = division

            # Call API
            leaders = self.stats_api.get_rushing_leaders(
                season=self.season,
                limit=25,
                filters=filters if filters else None
            )

            # Populate table
            self.rushing_table.setRowCount(len(leaders))
            for row, leader in enumerate(leaders):
                # Column 0: Rank
                self.rushing_table.setItem(row, 0, QTableWidgetItem(str(leader.league_rank or row + 1)))
                # Column 1: Player name
                self.rushing_table.setItem(row, 1, QTableWidgetItem(leader.player_name))
                # Column 2: Team
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(leader.team_id)
                team_name = team.full_name if team else f"Team {leader.team_id}"
                self.rushing_table.setItem(row, 2, QTableWidgetItem(team_name))
                # Column 3: Games
                self.rushing_table.setItem(row, 3, QTableWidgetItem(str(leader.games)))
                # Column 4: Attempts
                self.rushing_table.setItem(row, 4, QTableWidgetItem(str(leader.attempts)))
                # Column 5: Yards
                self.rushing_table.setItem(row, 5, QTableWidgetItem(str(leader.yards)))
                # Column 6: Avg
                avg = leader.yards / leader.attempts if leader.attempts > 0 else 0.0
                self.rushing_table.setItem(row, 6, QTableWidgetItem(f"{avg:.1f}"))
                # Column 7: TDs
                self.rushing_table.setItem(row, 7, QTableWidgetItem(str(leader.touchdowns)))
                # Column 8: Long
                self.rushing_table.setItem(row, 8, QTableWidgetItem(str(leader.longest)))

                # Make all cells non-editable and center-aligned
                for col in range(9):
                    item = self.rushing_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(leaders) > 0:
                self.rushing_info_label.setText(f"Showing top {len(leaders)} rushing leaders")
            else:
                self.rushing_info_label.setText("No rushing leaders found")

        except Exception as e:
            print(f"Error loading rushing leaders: {e}")
            import traceback
            traceback.print_exc()
            self.rushing_info_label.setText(f"Error loading rushing leaders: {str(e)}")

    def load_receiving_leaders(self):
        """Load receiving leaders from API"""
        try:
            # Get current filter values
            conference = self.conf_filter.currentText()
            division = self.div_filter.currentText()

            # Build filters
            filters = {}
            if conference != "All":
                filters['conference'] = conference
            if division != "All":
                filters['division'] = division

            # Call API
            leaders = self.stats_api.get_receiving_leaders(
                season=self.season,
                limit=25,
                filters=filters if filters else None
            )

            # Populate table
            self.receiving_table.setRowCount(len(leaders))
            for row, leader in enumerate(leaders):
                # Column 0: Rank
                self.receiving_table.setItem(row, 0, QTableWidgetItem(str(leader.league_rank or row + 1)))
                # Column 1: Player name
                self.receiving_table.setItem(row, 1, QTableWidgetItem(leader.player_name))
                # Column 2: Team
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(leader.team_id)
                team_name = team.full_name if team else f"Team {leader.team_id}"
                self.receiving_table.setItem(row, 2, QTableWidgetItem(team_name))
                # Column 3: Games
                self.receiving_table.setItem(row, 3, QTableWidgetItem(str(leader.games)))
                # Column 4: Receptions
                self.receiving_table.setItem(row, 4, QTableWidgetItem(str(leader.receptions)))
                # Column 5: Yards
                self.receiving_table.setItem(row, 5, QTableWidgetItem(str(leader.yards)))
                # Column 6: Avg
                avg = leader.yards / leader.receptions if leader.receptions > 0 else 0.0
                self.receiving_table.setItem(row, 6, QTableWidgetItem(f"{avg:.1f}"))
                # Column 7: TDs
                self.receiving_table.setItem(row, 7, QTableWidgetItem(str(leader.touchdowns)))
                # Column 8: Long
                self.receiving_table.setItem(row, 8, QTableWidgetItem(str(leader.longest)))

                # Make all cells non-editable and center-aligned
                for col in range(9):
                    item = self.receiving_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(leaders) > 0:
                self.receiving_info_label.setText(f"Showing top {len(leaders)} receiving leaders")
            else:
                self.receiving_info_label.setText("No receiving leaders found")

        except Exception as e:
            print(f"Error loading receiving leaders: {e}")
            import traceback
            traceback.print_exc()
            self.receiving_info_label.setText(f"Error loading receiving leaders: {str(e)}")

    def load_defense_leaders(self):
        """Load defensive leaders from API"""
        try:
            # Get current filter values
            conference = self.conf_filter.currentText()
            division = self.div_filter.currentText()

            # Build filters
            filters = {}
            if conference != "All":
                filters['conference'] = conference
            if division != "All":
                filters['division'] = division

            # Call API - get tackles total leaders
            leaders = self.stats_api.get_defensive_leaders(
                season=self.season,
                stat_category='tackles_total',
                limit=25,
                filters=filters if filters else None
            )

            # Populate table
            self.defense_table.setRowCount(len(leaders))
            for row, leader in enumerate(leaders):
                # Column 0: Rank
                self.defense_table.setItem(row, 0, QTableWidgetItem(str(leader.league_rank or row + 1)))
                # Column 1: Player name
                self.defense_table.setItem(row, 1, QTableWidgetItem(leader.player_name))
                # Column 2: Team
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(leader.team_id)
                team_name = team.full_name if team else f"Team {leader.team_id}"
                self.defense_table.setItem(row, 2, QTableWidgetItem(team_name))
                # Column 3: Games
                self.defense_table.setItem(row, 3, QTableWidgetItem(str(leader.games)))
                # Column 4: Tackles
                self.defense_table.setItem(row, 4, QTableWidgetItem(str(leader.tackles_solo)))
                # Column 5: Assists
                self.defense_table.setItem(row, 5, QTableWidgetItem(str(leader.tackles_assist)))
                # Column 6: Sacks
                self.defense_table.setItem(row, 6, QTableWidgetItem(f"{leader.sacks:.1f}"))
                # Column 7: INTs
                self.defense_table.setItem(row, 7, QTableWidgetItem(str(leader.interceptions)))
                # Column 8: FF
                self.defense_table.setItem(row, 8, QTableWidgetItem(str(leader.forced_fumbles)))
                # Column 9: TDs
                self.defense_table.setItem(row, 9, QTableWidgetItem(str(leader.touchdowns)))

                # Make all cells non-editable and center-aligned
                for col in range(10):
                    item = self.defense_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(leaders) > 0:
                self.defense_info_label.setText(f"Showing top {len(leaders)} defensive leaders")
            else:
                self.defense_info_label.setText("No defensive leaders found")

        except Exception as e:
            print(f"Error loading defensive leaders: {e}")
            import traceback
            traceback.print_exc()
            self.defense_info_label.setText(f"Error loading defensive leaders: {str(e)}")

    def load_special_teams_leaders(self):
        """Load special teams leaders from API"""
        try:
            # Get current filter values
            conference = self.conf_filter.currentText()
            division = self.div_filter.currentText()

            # Build filters
            filters = {}
            if conference != "All":
                filters['conference'] = conference
            if division != "All":
                filters['division'] = division

            # Call API
            leaders = self.stats_api.get_special_teams_leaders(
                season=self.season,
                limit=25,
                filters=filters if filters else None
            )

            # Populate table
            self.special_teams_table.setRowCount(len(leaders))
            for row, leader in enumerate(leaders):
                # Column 0: Rank
                self.special_teams_table.setItem(row, 0, QTableWidgetItem(str(leader.league_rank or row + 1)))
                # Column 1: Player name
                self.special_teams_table.setItem(row, 1, QTableWidgetItem(leader.player_name))
                # Column 2: Team
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(leader.team_id)
                team_name = team.full_name if team else f"Team {leader.team_id}"
                self.special_teams_table.setItem(row, 2, QTableWidgetItem(team_name))
                # Column 3: Position
                self.special_teams_table.setItem(row, 3, QTableWidgetItem(leader.position))
                # Column 4: FGM
                self.special_teams_table.setItem(row, 4, QTableWidgetItem(str(leader.field_goals_made)))
                # Column 5: FGA
                self.special_teams_table.setItem(row, 5, QTableWidgetItem(str(leader.field_goals_attempted)))
                # Column 6: FG%
                self.special_teams_table.setItem(row, 6, QTableWidgetItem(f"{leader.fg_percentage:.1f}"))
                # Column 7: Long (use field_goals_made as placeholder since longest isn't tracked yet)
                self.special_teams_table.setItem(row, 7, QTableWidgetItem("-"))
                # Column 8: XPM
                self.special_teams_table.setItem(row, 8, QTableWidgetItem(str(leader.extra_points_made)))
                # Column 9: XPA
                self.special_teams_table.setItem(row, 9, QTableWidgetItem(str(leader.extra_points_attempted)))

                # Make all cells non-editable and center-aligned
                for col in range(10):
                    item = self.special_teams_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(leaders) > 0:
                self.special_teams_info_label.setText(f"Showing top {len(leaders)} kickers")
            else:
                self.special_teams_info_label.setText("No special teams leaders found")

        except Exception as e:
            print(f"Error loading special teams leaders: {e}")
            import traceback
            traceback.print_exc()
            self.special_teams_info_label.setText(f"Error loading special teams leaders: {str(e)}")
