"""
League View for The Owner's Sim

Displays league-wide statistics, standings, and team comparisons.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QPushButton,
    QHeaderView, QTabWidget, QGridLayout, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from models.team_list_model import TeamListModel
from models.roster_table_model import RosterTableModel
from controllers.league_controller import LeagueController
from controllers.player_controller import PlayerController
from widgets.stats_leaders_widget import StatsLeadersWidget


class LeagueView(QWidget):
    """
    League-wide statistics and standings view.

    Displays NFL standings, team comparisons, and league-wide stats.
    """

    def __init__(self, parent=None, controller: LeagueController = None):
        super().__init__(parent)
        self.main_window = parent
        self.controller = controller

        # Initialize player controller for free agents
        if controller:
            dynasty_info = controller.get_dynasty_info()
            self.player_controller = PlayerController(
                controller.db_path,  # Direct access - LeagueController has db_path attribute
                dynasty_info['dynasty_id'],
                season=int(dynasty_info['season'])  # Pass season for accurate age calculation
            )
        else:
            self.player_controller = None

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title with dynasty info
        title_layout = QHBoxLayout()

        title = QLabel("NFL League Information")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_layout.addWidget(title)

        if self.controller:
            dynasty_info = self.controller.get_dynasty_info()
            dynasty_label = QLabel(
                f"Dynasty: {dynasty_info['dynasty_id']} | Season: {dynasty_info['season']}"
            )
            dynasty_label.setStyleSheet("font-size: 14px; color: #888;")
            dynasty_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            title_layout.addWidget(dynasty_label)

        layout.addLayout(title_layout)

        # Tab widget for sub-sections
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_standings_tab(), "Standings")
        self.tabs.addTab(self._create_free_agents_tab(), "Free Agents")
        self.tabs.addTab(self._create_stats_leaders_tab(), "Stats Leaders")

        layout.addWidget(self.tabs)

        # Load initial data
        if self.controller:
            self.load_standings()

    def _create_standings_tab(self) -> QWidget:
        """Create standings tab with 8 division tables in a scrollable area."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create scroll area to hold the grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        # Create container widget for the grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Store division tables and models for later updates
        self.division_tables = {}
        self.division_models = {}

        # Define divisions in display order
        afc_divisions = ["AFC East", "AFC North", "AFC South", "AFC West"]
        nfc_divisions = ["NFC East", "NFC North", "NFC South", "NFC West"]

        # Create AFC division tables (left column)
        for row, division in enumerate(afc_divisions):
            group_box = self._create_division_table(division)
            grid_layout.addWidget(group_box, row, 0)

        # Create NFC division tables (right column)
        for row, division in enumerate(nfc_divisions):
            group_box = self._create_division_table(division)
            grid_layout.addWidget(group_box, row, 1)

        # Add grid container to scroll area
        scroll_area.setWidget(grid_container)
        layout.addWidget(scroll_area)

        # Refresh button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_button = QPushButton("Refresh Standings (32 teams)")
        self.refresh_button.clicked.connect(self.load_standings)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        return widget

    def _create_division_table(self, division: str) -> QGroupBox:
        """Create a table for a single division.

        Args:
            division: Division name (e.g., "AFC East")

        Returns:
            QGroupBox containing the division table
        """
        group_box = QGroupBox(division)
        group_box.setStyleSheet("QGroupBox { font-weight: bold; }")

        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(5, 10, 5, 5)

        # Create table for this division
        table = QTableView()
        model = TeamListModel()
        table.setModel(model)

        # Configure table appearance
        table.setSortingEnabled(False)  # Manual sorting by win%
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(False)

        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Team name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # W
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # L
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # T
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Win%
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # PF
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # PA

        # Disable scrollbars - main scroll area handles scrolling
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(table)

        # Store references for later updates
        self.division_tables[division] = table
        self.division_models[division] = model

        return group_box

    def _create_free_agents_tab(self) -> QWidget:
        """Create free agents tab (read-only, informational)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Info label
        info_label = QLabel("League-Wide Free Agent Pool (Read-Only)")
        info_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(info_label)

        # Free agents table
        self.fa_table = QTableView()
        self.fa_model = RosterTableModel(self)
        self.fa_table.setModel(self.fa_model)
        self.fa_table.setAlternatingRowColors(True)
        self.fa_table.setSelectionBehavior(QTableView.SelectRows)
        self.fa_table.setSortingEnabled(True)

        layout.addWidget(self.fa_table)

        # Status label
        self.fa_status_label = QLabel("")
        self.fa_status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.fa_status_label)

        # Load free agents
        self._load_free_agents()

        return widget

    def _load_free_agents(self):
        """Load free agents from database."""
        if not self.player_controller:
            return

        try:
            free_agents = self.player_controller.get_free_agents()
            self.fa_model.set_roster(free_agents)
            self.fa_table.viewport().update()
            self.fa_status_label.setText(
                f"{len(free_agents)} free agents available league-wide"
            )
        except Exception as e:
            print(f"Error loading free agents: {e}")
            self.fa_status_label.setText("Error loading free agents")

    def load_standings(self):
        """Load standings data from controller and display in division tables."""
        if not self.controller:
            return

        # Get all teams
        teams = self.controller.get_all_teams()

        # Get all standings in one database call
        standings_data = self.controller.get_standings()

        # Extract records dict from standings structure
        records = {}
        if standings_data:
            # standings_data is organized by division
            for division_name, division_data in standings_data.items():
                if isinstance(division_data, list):
                    # division_data is list of team dicts
                    for team_dict in division_data:
                        if 'standing' in team_dict:
                            standing = team_dict['standing']
                            records[standing.team_id] = {
                                'wins': standing.wins,
                                'losses': standing.losses,
                                'ties': standing.ties,
                                'points_for': standing.points_for,
                                'points_against': standing.points_against
                            }

        # Create team lookup by ID
        teams_by_id = {team.team_id: team for team in teams}

        # Update each division table
        for division_name, model in self.division_models.items():
            # Filter teams for this division
            division_teams = [team for team in teams if f"{team.conference} {team.division}" == division_name]

            # Sort by win percentage (descending)
            if records:
                def get_win_pct(team):
                    """Calculate win percentage for sorting."""
                    if team.team_id not in records:
                        return 0.0
                    record = records[team.team_id]
                    wins = record.get('wins', 0)
                    losses = record.get('losses', 0)
                    ties = record.get('ties', 0)
                    total = wins + losses + ties
                    if total == 0:
                        return 0.0
                    return (wins + 0.5 * ties) / total

                division_teams.sort(key=get_win_pct, reverse=True)

            # Update model for this division
            model.set_teams(division_teams, records if records else None)

            # Force table to refresh
            table = self.division_tables[division_name]
            table.viewport().update()

            # Calculate and set proper height to show all rows without scrolling
            # Get row count (should be 4 for NFL divisions)
            row_count = model.rowCount()
            if row_count > 0:
                # Calculate total height: header + all rows + frame
                header_height = table.horizontalHeader().height()
                row_height = table.rowHeight(0)  # Get height of first row
                total_row_height = row_height * row_count
                frame_height = table.frameWidth() * 2

                # Set minimum height to show all content
                calculated_height = header_height + total_row_height + frame_height + 5  # +5 for padding
                table.setMinimumHeight(calculated_height)
                table.setMaximumHeight(calculated_height)

        # Update status
        team_count = len(teams)
        if records:
            self.refresh_button.setText(f"Refresh Standings ({team_count} teams)")
        else:
            self.refresh_button.setText(f"Refresh Standings ({team_count} teams - No season data)")

    def _create_stats_leaders_tab(self) -> QWidget:
        """Create stats leaders tab with league-wide leaderboards."""
        if self.controller:
            dynasty_info = self.controller.get_dynasty_info()
            widget = StatsLeadersWidget(
                self,
                db_path=self.controller.db_path,
                dynasty_id=dynasty_info['dynasty_id'],
                season=int(dynasty_info['season'])
            )
        else:
            # Fallback if no controller (shouldn't happen in production)
            widget = StatsLeadersWidget(self)
        return widget
