"""
Roster Tab Widget for The Owner's Sim UI

Sub-tab widget for Team View showing team roster with filtering, sorting, and player actions.
"""

from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QComboBox, QLineEdit, QMenu
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction

from ui.models.roster_table_model import RosterTableModel


class RosterTabWidget(QWidget):
    """
    Roster tab widget for Team View.

    Displays team roster with:
    - Position and group filtering
    - Sort options
    - Player search
    - Right-click context menu
    - Color-coded status indicators
    """

    def __init__(self, parent=None):
        """Initialize roster tab widget."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Filter bar
        filter_bar = self._create_filter_bar()
        layout.addLayout(filter_bar)

        # Roster table
        self.roster_table = self._create_roster_table()
        layout.addWidget(self.roster_table)

    def _create_filter_bar(self) -> QHBoxLayout:
        """Create filter bar with position, group, sort dropdowns and search."""
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Position filter dropdown
        self.position_filter = QComboBox()
        self.position_filter.setMinimumWidth(150)
        self.position_filter.addItems([
            "All Positions",
            "Offense",
            "  Quarterbacks (QB)",
            "  Running Backs (RB, FB)",
            "  Wide Receivers (WR)",
            "  Tight Ends (TE)",
            "  Offensive Line (OL)",
            "Defense",
            "  Defensive Line (DL)",
            "  Linebackers (LB)",
            "  Secondary (DB)",
            "Special Teams",
            "  Kickers/Punters (K, P)",
            "  Returners (KR, PR)"
        ])
        filter_layout.addWidget(self.position_filter)

        # Group filter dropdown
        self.group_filter = QComboBox()
        self.group_filter.setMinimumWidth(120)
        self.group_filter.addItems([
            "All",
            "Offense",
            "Defense",
            "Special Teams"
        ])
        filter_layout.addWidget(self.group_filter)

        # Sort dropdown
        self.sort_filter = QComboBox()
        self.sort_filter.setMinimumWidth(180)
        self.sort_filter.addItems([
            "Overall (High to Low)",
            "Overall (Low to High)",
            "Name (A-Z)",
            "Name (Z-A)",
            "Position",
            "Age (Youngest First)",
            "Age (Oldest First)",
            "Salary (High to Low)",
            "Salary (Low to High)",
            "Contract Years Remaining"
        ])
        filter_layout.addWidget(self.sort_filter)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search players...")
        self.search_box.setMinimumWidth(200)
        filter_layout.addWidget(self.search_box)

        filter_layout.addStretch()

        return filter_layout

    def _create_roster_table(self) -> QTableView:
        """Create roster table with model."""
        table = QTableView()

        # Set model
        self.roster_model = RosterTableModel(self)
        table.setModel(self.roster_model)

        # Table properties
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)

        # Connect context menu
        table.customContextMenuRequested.connect(self._show_context_menu)

        # Column widths
        header = table.horizontalHeader()
        header.setStretchLastSection(False)

        # Set column widths (approximate based on spec)
        table.setColumnWidth(RosterTableModel.COL_NUMBER, 40)
        table.setColumnWidth(RosterTableModel.COL_NAME, 180)
        table.setColumnWidth(RosterTableModel.COL_POSITION, 50)
        table.setColumnWidth(RosterTableModel.COL_AGE, 50)
        table.setColumnWidth(RosterTableModel.COL_OVERALL, 50)
        table.setColumnWidth(RosterTableModel.COL_CONTRACT, 120)
        table.setColumnWidth(RosterTableModel.COL_SALARY, 100)
        table.setColumnWidth(RosterTableModel.COL_STATUS, 50)

        # Enable sorting
        table.setSortingEnabled(True)

        return table

    def _show_context_menu(self, position: QPoint):
        """
        Show context menu on right-click.

        Args:
            position: Position where right-click occurred
        """
        # Get selected row
        index = self.roster_table.indexAt(position)
        if not index.isValid():
            return

        # Create context menu
        menu = QMenu(self)

        # View actions
        view_details_action = QAction("View Player Details", self)
        view_stats_action = QAction("View Season Stats", self)
        menu.addAction(view_details_action)
        menu.addAction(view_stats_action)
        menu.addSeparator()

        # Depth chart actions
        set_starter_action = QAction("Set as Starter", self)
        menu.addAction(set_starter_action)
        menu.addSeparator()

        # Contract actions
        view_contract_action = QAction("View Contract Details", self)
        menu.addAction(view_contract_action)
        menu.addSeparator()

        # Roster actions
        release_action = QAction("Release Player", self)
        menu.addAction(release_action)

        # Show menu at cursor position
        menu.exec(self.roster_table.viewport().mapToGlobal(position))

    def set_roster_data(self, roster: List[Dict]):
        """
        Load roster data from API and display in table.

        Args:
            roster: List of player dicts from TeamDataModel

        Format expected:
        {
            'player_id': int,
            'number': int,
            'name': str,
            'position': str,
            'age': int,
            'overall': int,
            'contract': str,  # "2yr/$45M"
            'salary': str,  # "$22.5M"
            'status': str  # 'ACT', 'IR', etc.
        }
        """
        # Update the model with new data
        self.roster_model.set_roster(roster)

        # Refresh table display
        self.roster_table.viewport().update()

    def clear_roster(self):
        """Clear all roster data."""
        self.roster_model.clear()
