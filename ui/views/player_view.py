"""
Player View for The Owner's Sim

Displays individual player details, statistics, and career history.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QTableView
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# Add src to path for team imports
src_path = os.path.join(ui_path, '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from models.roster_table_model import RosterTableModel
from controllers.player_controller import PlayerController
from team_management.teams.team_loader import TeamDataLoader


class PlayerView(QWidget):
    """
    Player details view.

    Phase 1: Placeholder
    Phase 3: Full implementation with player stats and career history
    """

    def __init__(self, parent=None, db_path=None, dynasty_id=None):
        super().__init__(parent)
        self.main_window = parent
        self.db_path = db_path or "data/database/nfl_simulation.db"
        self.dynasty_id = dynasty_id or "default"

        # Initialize controller
        self.controller = PlayerController(self.db_path, self.dynasty_id, main_window=parent)

        # Initialize team loader
        self.team_loader = TeamDataLoader()

        # Setup UI
        self._setup_ui()

    @property
    def season(self) -> int:
        """Current season year (proxied from parent/main window)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        return 2025  # Fallback for testing/standalone usage

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Player Browser")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Filter bar
        filter_layout = QHBoxLayout()

        # Team selector
        team_label = QLabel("Team:")
        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(200)
        # Populate FIRST (without signal connected to avoid premature triggering)
        self._populate_team_selector()
        # Connect signal AFTER populating
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)

        # Position filter
        position_label = QLabel("Position:")
        self.position_filter = QComboBox()
        self.position_filter.addItems([
            "All Positions", "QB", "RB", "WR", "TE", "OL",
            "DL", "LB", "DB", "K", "P"
        ])
        self.position_filter.currentTextChanged.connect(self._filter_players)

        # Search box
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Player name...")
        self.search_box.textChanged.connect(self._filter_players)

        filter_layout.addWidget(team_label)
        filter_layout.addWidget(self.team_selector)
        filter_layout.addWidget(position_label)
        filter_layout.addWidget(self.position_filter)
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.search_box)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Player table
        self.player_table = QTableView()
        self.player_model = RosterTableModel(self)
        self.player_table.setModel(self.player_model)
        self.player_table.setAlternatingRowColors(True)
        self.player_table.setSelectionBehavior(QTableView.SelectRows)
        self.player_table.setSortingEnabled(True)
        self.player_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.player_table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.player_table)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # Trigger initial load after all UI components are created
        # (Signal may not fire when first item added to empty combo)
        self._on_team_changed(0)

    def _populate_team_selector(self):
        """Populate team selector with all NFL teams + free agents."""
        # Add FREE AGENTS as first option
        self.team_selector.addItem("FREE AGENTS", 0)

        # Add all 32 NFL teams (sorted by team name)
        teams = []
        for team_id in range(1, 33):
            team = self.team_loader.get_team_by_id(team_id)
            if team:
                teams.append((team.full_name, team_id))

        teams.sort()  # Sort alphabetically

        for team_name, team_id in teams:
            self.team_selector.addItem(team_name, team_id)

    def _on_team_changed(self, index):
        """Handle team selection change."""
        team_id = self.team_selector.currentData()

        if team_id == 0:
            # Free agents
            self._load_free_agents()
        elif team_id is not None:
            # Team roster
            self._load_team_roster(team_id)

    def _load_free_agents(self):
        """Load free agents from database."""
        try:
            free_agents = self.controller.get_free_agents()
            self.player_model.set_roster(free_agents)
            self.player_table.viewport().update()
            self.status_label.setText(f"Showing {len(free_agents)} free agents")
        except Exception as e:
            print(f"Error loading free agents: {e}")
            self.status_label.setText("Error loading free agents")

    def _load_team_roster(self, team_id: int):
        """Load team roster from database."""
        try:
            roster = self.controller.get_team_roster(team_id)
            self.player_model.set_roster(roster)
            self.player_table.viewport().update()

            team = self.team_loader.get_team_by_id(team_id)
            team_name = team.full_name if team else f"Team {team_id}"
            self.status_label.setText(f"Showing {len(roster)} players for {team_name}")
        except Exception as e:
            print(f"Error loading team roster: {e}")
            self.status_label.setText("Error loading team roster")

    def _filter_players(self):
        """Filter players table (placeholder)."""
        # TODO: Implement filtering logic
        pass

    def _show_context_menu(self, position):
        """Show context menu on right-click (placeholder)."""
        # TODO: Implement context menu with "View Player Details" option
        pass
