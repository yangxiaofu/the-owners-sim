"""
Offseason View for The Owner's Sim

Displays offseason dashboard with deadlines, free agency, draft, and roster management.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableView, QPushButton, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from models.roster_table_model import RosterTableModel
from controllers.player_controller import PlayerController


class OffseasonView(QWidget):
    """
    Offseason management view.

    Phase 1: Placeholder
    Phase 4: Full implementation with offseason dashboard and dialogs
    """

    def __init__(self, parent=None, db_path=None, dynasty_id=None, season=2025):
        super().__init__(parent)
        self.main_window = parent
        self.db_path = db_path or "data/database/nfl_simulation.db"
        self.dynasty_id = dynasty_id or "default"
        self.season = season

        # Initialize controller
        self.controller = PlayerController(self.db_path, self.dynasty_id, self.season)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Offseason Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Tab widget for sub-sections
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._create_free_agents_tab(), "Free Agents")
        self.tabs.addTab(self._create_draft_tab(), "Draft")

        layout.addWidget(self.tabs)

    def _create_dashboard_tab(self) -> QWidget:
        """Create dashboard tab with offseason overview."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        description = QLabel(
            "Offseason Dashboard (Placeholder)\n\n"
            "Coming in Phase 4:\n"
            "• Current date and offseason phase display\n"
            "• Deadline countdown timers\n"
            "• Salary cap status panel\n"
            "• Action buttons (Franchise Tag, Cuts)\n"
            "• Transaction feed\n"
            "• Calendar advancement controls"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(description)
        layout.addStretch()

        return widget

    def _create_free_agents_tab(self) -> QWidget:
        """Create free agents tab with player list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter bar
        filter_layout = QHBoxLayout()

        # Position filter
        position_label = QLabel("Position:")
        self.fa_position_filter = QComboBox()
        self.fa_position_filter.addItems([
            "All Positions", "QB", "RB", "WR", "TE", "OL",
            "DL", "LB", "DB", "K", "P"
        ])
        self.fa_position_filter.currentTextChanged.connect(self._filter_free_agents)

        # Search box
        search_label = QLabel("Search:")
        self.fa_search_box = QLineEdit()
        self.fa_search_box.setPlaceholderText("Player name...")
        self.fa_search_box.textChanged.connect(self._filter_free_agents)

        filter_layout.addWidget(position_label)
        filter_layout.addWidget(self.fa_position_filter)
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.fa_search_box)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Free agents table
        self.fa_table = QTableView()
        self.fa_model = RosterTableModel(self)
        self.fa_table.setModel(self.fa_model)
        self.fa_table.setAlternatingRowColors(True)
        self.fa_table.setSelectionBehavior(QTableView.SelectRows)
        self.fa_table.setSortingEnabled(True)

        layout.addWidget(self.fa_table)

        # Action buttons (placeholders)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.sign_player_btn = QPushButton("Sign Player")
        self.sign_player_btn.setToolTip("Contract signing coming in Phase 4")
        self.sign_player_btn.setEnabled(False)  # Placeholder
        button_layout.addWidget(self.sign_player_btn)

        layout.addLayout(button_layout)

        # Load free agents
        self._load_free_agents()

        return widget

    def _create_draft_tab(self) -> QWidget:
        """Create draft tab (placeholder)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        description = QLabel(
            "Draft Board (Placeholder)\n\n"
            "Coming in Phase 4:\n"
            "• Draft board with all prospects\n"
            "• Team needs analysis\n"
            "• Pick selection interface\n"
            "• Draft tracker"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(description)
        layout.addStretch()

        return widget

    def _load_free_agents(self):
        """Load free agents from database."""
        try:
            free_agents = self.controller.get_free_agents()
            self.fa_model.set_roster(free_agents)
            self.fa_table.viewport().update()
        except Exception as e:
            print(f"Error loading free agents: {e}")

    def _filter_free_agents(self):
        """Filter free agents table (placeholder)."""
        # TODO: Implement filtering logic
        pass
