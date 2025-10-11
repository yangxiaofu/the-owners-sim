"""
League View for The Owner's Sim

Displays league-wide statistics, standings, and team comparisons.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QPushButton,
    QHeaderView, QTabWidget
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

        layout.addWidget(self.tabs)

        # Load initial data
        if self.controller:
            self.load_standings()

    def _create_standings_tab(self) -> QWidget:
        """Create standings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Standings table
        self.standings_table = QTableView()
        self.standings_model = TeamListModel()
        self.standings_table.setModel(self.standings_model)

        # Configure table appearance
        self.standings_table.setSortingEnabled(True)
        self.standings_table.setAlternatingRowColors(True)
        self.standings_table.setSelectionBehavior(QTableView.SelectRows)
        self.standings_table.setSelectionMode(QTableView.SingleSelection)
        self.standings_table.verticalHeader().setVisible(False)

        # Set column widths
        header = self.standings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Team name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Division
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Conference
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Record

        layout.addWidget(self.standings_table)

        # Refresh button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_button = QPushButton("Refresh Standings")
        self.refresh_button.clicked.connect(self.load_standings)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        return widget

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
        """Load standings data from controller and display in table."""
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
                if isinstance(division_data, dict) and 'teams' in division_data:
                    # Division contains list of team standing dicts
                    for team_dict in division_data['teams']:
                        if 'standing' in team_dict:
                            standing = team_dict['standing']
                            records[standing.team_id] = {
                                'wins': standing.wins,
                                'losses': standing.losses,
                                'ties': standing.ties
                            }
                elif isinstance(division_data, list):
                    # Alternative: division_data is direct list of team dicts
                    for team_dict in division_data:
                        if 'standing' in team_dict:
                            standing = team_dict['standing']
                            records[standing.team_id] = {
                                'wins': standing.wins,
                                'losses': standing.losses,
                                'ties': standing.ties
                            }

        # Update model
        self.standings_model.set_teams(teams, records if records else None)

        # Force table to refresh and become visible
        self.standings_table.viewport().update()
        self.standings_table.show()

        # Update status
        team_count = len(teams)
        if records:
            self.refresh_button.setText(f"Refresh Standings ({team_count} teams)")
        else:
            self.refresh_button.setText(f"Refresh Standings ({team_count} teams - No season data)")
