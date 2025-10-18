"""
Team Statistics Widget for The Owner's Sim

Displays comprehensive player statistics for a selected team.
Uses StatsAPI for real database integration.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTabWidget, QHeaderView
)
from PySide6.QtCore import Qt


class TeamStatisticsWidget(QWidget):
    """
    Team-specific player statistics widget.

    Displays all players on selected team with their statistics:
    - Offense (QB, RB, WR, TE stats)
    - Defense (tackles, sacks, INTs)
    - Special Teams (kicking, punting, returns)

    Integrated with StatsAPI for real database access.
    """

    def __init__(self, parent=None, team_id: int = None, db_path: str = "data/database/nfl_simulation.db", dynasty_id: str = "default", season: int = 2025):
        super().__init__(parent)
        self.team_id = team_id or 22  # Default to Detroit Lions
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize StatsAPI
        from statistics.stats_api import StatsAPI
        self.stats_api = StatsAPI(db_path, dynasty_id)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Category tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_offense_stats(), "Offense")
        self.tabs.addTab(self._create_defense_stats(), "Defense")
        self.tabs.addTab(self._create_special_teams_stats(), "Special Teams")

        layout.addWidget(self.tabs)

        # Load initial data
        self.load_team_data()

    def _create_header(self) -> QHBoxLayout:
        """Create header with team name and stats info."""
        header = QHBoxLayout()

        # Title (will be updated when team data loads)
        self.title = QLabel("Team Player Statistics")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(self.title)

        header.addStretch()

        # Season info
        season_label = QLabel(f"{self.season} Season")
        season_label.setStyleSheet("font-size: 14px; color: #888;")
        header.addWidget(season_label)

        return header

    def _create_offense_stats(self) -> QWidget:
        """Create offensive statistics table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(12)
        table.setHorizontalHeaderLabels([
            "Player", "Pos", "G", "Pass Cmp", "Pass Att", "Pass Yds", "Pass TDs",
            "Rush Att", "Rush Yds", "Rec", "Rec Yds", "Total TDs"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Player name
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Store reference for later updates
        self.offense_table = table

        # Info label
        self.offense_info_label = QLabel("Loading offensive statistics...")
        self.offense_info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.offense_info_label)

        return widget

    def _create_defense_stats(self) -> QWidget:
        """Create defensive statistics table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            "Player", "Pos", "G", "Tackles", "Assists", "Sacks", "TFL", "INTs", "PD", "FF", "FR"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Store reference for later updates
        self.defense_table = table

        # Info label
        self.defense_info_label = QLabel("Loading defensive statistics...")
        self.defense_info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.defense_info_label)

        return widget

    def _create_special_teams_stats(self) -> QWidget:
        """Create special teams statistics table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            "Player", "Pos", "G", "FGM", "FGA", "FG%", "Long", "XPM", "XPA", "Punts", "Avg"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Store reference for later updates
        self.special_teams_table = table

        # Info label
        self.special_teams_info_label = QLabel("Loading special teams statistics...")
        self.special_teams_info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.special_teams_info_label)

        return widget

    def load_team_data(self):
        """Load statistics for current team from API"""
        try:
            # Get team name
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(self.team_id)
            team_name = team.full_name if team else f"Team {self.team_id}"

            # Update header
            self.title.setText(f"{team_name} - Player Statistics")

            # Load each category
            self.load_offense_stats()
            self.load_defense_stats()
            self.load_special_teams_stats()

        except Exception as e:
            print(f"Error loading team data: {e}")
            import traceback
            traceback.print_exc()

    def load_offense_stats(self):
        """Load offensive statistics for current team"""
        try:
            # Get offensive stats for team
            # Workaround: Get all leaders and filter by team
            all_passing = self.stats_api.get_passing_leaders(self.season, limit=500)
            all_rushing = self.stats_api.get_rushing_leaders(self.season, limit=500)
            all_receiving = self.stats_api.get_receiving_leaders(self.season, limit=500)

            # Filter by team_id
            team_passing = [p for p in all_passing if p.team_id == self.team_id]
            team_rushing = [p for p in all_rushing if p.team_id == self.team_id]
            team_receiving = [p for p in all_receiving if p.team_id == self.team_id]

            # Combine into single list (deduplicate by player_id)
            players = {}

            # Add passers
            for p in team_passing:
                players[p.player_id] = {
                    'player_name': p.player_name,
                    'position': p.position,
                    'games': p.games,
                    'pass_cmp': p.completions,
                    'pass_att': p.attempts,
                    'pass_yds': p.yards,
                    'pass_tds': p.touchdowns,
                    'rush_att': 0,
                    'rush_yds': 0,
                    'rec': 0,
                    'rec_yds': 0,
                    'total_tds': p.touchdowns,
                }

            # Add rushers (merge if player exists)
            for r in team_rushing:
                if r.player_id in players:
                    players[r.player_id]['rush_att'] = r.attempts
                    players[r.player_id]['rush_yds'] = r.yards
                    players[r.player_id]['total_tds'] += r.touchdowns
                else:
                    players[r.player_id] = {
                        'player_name': r.player_name,
                        'position': r.position,
                        'games': r.games,
                        'pass_cmp': 0,
                        'pass_att': 0,
                        'pass_yds': 0,
                        'pass_tds': 0,
                        'rush_att': r.attempts,
                        'rush_yds': r.yards,
                        'rec': 0,
                        'rec_yds': 0,
                        'total_tds': r.touchdowns,
                    }

            # Add receivers (merge if player exists)
            for rec in team_receiving:
                if rec.player_id in players:
                    players[rec.player_id]['rec'] = rec.receptions
                    players[rec.player_id]['rec_yds'] = rec.yards
                    players[rec.player_id]['total_tds'] += rec.touchdowns
                else:
                    players[rec.player_id] = {
                        'player_name': rec.player_name,
                        'position': rec.position,
                        'games': rec.games,
                        'pass_cmp': 0,
                        'pass_att': 0,
                        'pass_yds': 0,
                        'pass_tds': 0,
                        'rush_att': 0,
                        'rush_yds': 0,
                        'rec': rec.receptions,
                        'rec_yds': rec.yards,
                        'total_tds': rec.touchdowns,
                    }

            # Populate table
            player_list = list(players.values())
            self.offense_table.setRowCount(len(player_list))

            for row, player in enumerate(player_list):
                self.offense_table.setItem(row, 0, QTableWidgetItem(player['player_name']))
                self.offense_table.setItem(row, 1, QTableWidgetItem(player['position']))
                self.offense_table.setItem(row, 2, QTableWidgetItem(str(player['games'])))
                self.offense_table.setItem(row, 3, QTableWidgetItem(str(player['pass_cmp'])))
                self.offense_table.setItem(row, 4, QTableWidgetItem(str(player['pass_att'])))
                self.offense_table.setItem(row, 5, QTableWidgetItem(str(player['pass_yds'])))
                self.offense_table.setItem(row, 6, QTableWidgetItem(str(player['pass_tds'])))
                self.offense_table.setItem(row, 7, QTableWidgetItem(str(player['rush_att'])))
                self.offense_table.setItem(row, 8, QTableWidgetItem(str(player['rush_yds'])))
                self.offense_table.setItem(row, 9, QTableWidgetItem(str(player['rec'])))
                self.offense_table.setItem(row, 10, QTableWidgetItem(str(player['rec_yds'])))
                self.offense_table.setItem(row, 11, QTableWidgetItem(str(player['total_tds'])))

                # Make non-editable and center-aligned
                for col in range(12):
                    item = self.offense_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(player_list) > 0:
                self.offense_info_label.setText(f"Showing {len(player_list)} offensive players")
            else:
                self.offense_info_label.setText("No offensive statistics found for this team")

        except Exception as e:
            print(f"Error loading offensive stats: {e}")
            import traceback
            traceback.print_exc()
            self.offense_info_label.setText(f"Error loading offensive stats: {str(e)}")

    def load_defense_stats(self):
        """Load defensive statistics for current team"""
        try:
            # Get defensive leaders and filter by team
            tackles_leaders = self.stats_api.get_defensive_leaders(self.season, 'tackles_total', limit=500)
            sacks_leaders = self.stats_api.get_defensive_leaders(self.season, 'sacks', limit=500)
            int_leaders = self.stats_api.get_defensive_leaders(self.season, 'interceptions', limit=500)

            # Filter by team and merge
            team_defense = {}

            for p in tackles_leaders:
                if p.team_id == self.team_id:
                    team_defense[p.player_id] = {
                        'player_name': p.player_name,
                        'position': p.position,
                        'games': p.games,
                        'tackles': p.tackles_total,
                        'assists': 0,  # Not in current stat model
                        'sacks': 0.0,
                        'tfl': 0,  # Not in current stat model
                        'ints': 0,
                        'pd': 0,  # Not in current stat model
                        'ff': 0,  # Not in current stat model
                        'fr': 0,  # Not in current stat model
                    }

            for p in sacks_leaders:
                if p.team_id == self.team_id:
                    if p.player_id in team_defense:
                        team_defense[p.player_id]['sacks'] = p.sacks
                    else:
                        team_defense[p.player_id] = {
                            'player_name': p.player_name,
                            'position': p.position,
                            'games': p.games,
                            'tackles': 0,
                            'assists': 0,
                            'sacks': p.sacks,
                            'tfl': 0,
                            'ints': 0,
                            'pd': 0,
                            'ff': 0,
                            'fr': 0,
                        }

            for p in int_leaders:
                if p.team_id == self.team_id:
                    if p.player_id in team_defense:
                        team_defense[p.player_id]['ints'] = p.interceptions
                    else:
                        team_defense[p.player_id] = {
                            'player_name': p.player_name,
                            'position': p.position,
                            'games': p.games,
                            'tackles': 0,
                            'assists': 0,
                            'sacks': 0.0,
                            'tfl': 0,
                            'ints': p.interceptions,
                            'pd': 0,
                            'ff': 0,
                            'fr': 0,
                        }

            # Populate defense table
            player_list = list(team_defense.values())
            self.defense_table.setRowCount(len(player_list))

            for row, player in enumerate(player_list):
                self.defense_table.setItem(row, 0, QTableWidgetItem(player['player_name']))
                self.defense_table.setItem(row, 1, QTableWidgetItem(player['position']))
                self.defense_table.setItem(row, 2, QTableWidgetItem(str(player['games'])))
                self.defense_table.setItem(row, 3, QTableWidgetItem(str(player['tackles'])))
                self.defense_table.setItem(row, 4, QTableWidgetItem(str(player['assists'])))
                self.defense_table.setItem(row, 5, QTableWidgetItem(str(player['sacks'])))
                self.defense_table.setItem(row, 6, QTableWidgetItem(str(player['tfl'])))
                self.defense_table.setItem(row, 7, QTableWidgetItem(str(player['ints'])))
                self.defense_table.setItem(row, 8, QTableWidgetItem(str(player['pd'])))
                self.defense_table.setItem(row, 9, QTableWidgetItem(str(player['ff'])))
                self.defense_table.setItem(row, 10, QTableWidgetItem(str(player['fr'])))

                # Make non-editable and center-aligned
                for col in range(11):
                    item = self.defense_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(player_list) > 0:
                self.defense_info_label.setText(f"Showing {len(player_list)} defensive players")
            else:
                self.defense_info_label.setText("No defensive statistics found for this team")

        except Exception as e:
            print(f"Error loading defensive stats: {e}")
            import traceback
            traceback.print_exc()
            self.defense_info_label.setText(f"Error loading defensive stats: {str(e)}")

    def load_special_teams_stats(self):
        """Load special teams statistics for current team"""
        try:
            # Get kickers and filter by team
            kickers = self.stats_api.get_special_teams_leaders(self.season, limit=500)
            team_kickers = [k for k in kickers if k.team_id == self.team_id]

            # Populate special teams table
            self.special_teams_table.setRowCount(len(team_kickers))

            for row, kicker in enumerate(team_kickers):
                # Calculate FG%
                fg_pct = (kicker.field_goals_made / kicker.field_goals_attempted * 100) if kicker.field_goals_attempted > 0 else 0.0

                self.special_teams_table.setItem(row, 0, QTableWidgetItem(kicker.player_name))
                self.special_teams_table.setItem(row, 1, QTableWidgetItem(kicker.position))
                self.special_teams_table.setItem(row, 2, QTableWidgetItem(str(kicker.games)))
                self.special_teams_table.setItem(row, 3, QTableWidgetItem(str(kicker.field_goals_made)))
                self.special_teams_table.setItem(row, 4, QTableWidgetItem(str(kicker.field_goals_attempted)))
                self.special_teams_table.setItem(row, 5, QTableWidgetItem(f"{fg_pct:.1f}"))
                self.special_teams_table.setItem(row, 6, QTableWidgetItem(str(kicker.longest_field_goal)))
                self.special_teams_table.setItem(row, 7, QTableWidgetItem(str(kicker.extra_points_made)))
                self.special_teams_table.setItem(row, 8, QTableWidgetItem(str(kicker.extra_points_attempted)))
                self.special_teams_table.setItem(row, 9, QTableWidgetItem("0"))  # Punts - not in model
                self.special_teams_table.setItem(row, 10, QTableWidgetItem("0.0"))  # Avg - not in model

                # Make non-editable and center-aligned
                for col in range(11):
                    item = self.special_teams_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            # Update info label
            if len(team_kickers) > 0:
                self.special_teams_info_label.setText(f"Showing {len(team_kickers)} special teams players")
            else:
                self.special_teams_info_label.setText("No special teams statistics found for this team")

        except Exception as e:
            print(f"Error loading special teams stats: {e}")
            import traceback
            traceback.print_exc()
            self.special_teams_info_label.setText(f"Error loading special teams stats: {str(e)}")

    def set_team(self, team_id: int, team_name: str):
        """
        Update widget to display statistics for a different team.

        Args:
            team_id: Team ID (1-32)
            team_name: Full team name (e.g., "Detroit Lions")
        """
        self.team_id = team_id
        self.load_team_data()

    def refresh(self):
        """
        Refresh statistics with fresh database connection.

        This recreates the StatsAPI instance to get a new database connection,
        ensuring that any newly simulated games are reflected in the statistics.

        Called after games are simulated to update the display without requiring
        an app restart.
        """
        # Recreate StatsAPI with fresh database connection
        from statistics.stats_api import StatsAPI
        self.stats_api = StatsAPI(self.db_path, self.dynasty_id)

        # Reload all data
        self.load_team_data()
