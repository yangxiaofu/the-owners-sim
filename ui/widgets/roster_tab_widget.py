"""
Roster Tab Widget for The Owner's Sim UI

Sub-tab widget for Team View showing team roster with filtering, sorting, and player actions.
"""

from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QComboBox, QLineEdit, QMenu
)
from PySide6.QtCore import Qt, QPoint, QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QAction

from ui.models.roster_table_model import RosterTableModel


class RosterFilterProxyModel(QSortFilterProxyModel):
    """
    Custom filter proxy model for roster table.

    Supports filtering by:
    - Position groups (Offense, Defense, Special Teams)
    - Specific position categories (QB, RB/FB, WR, etc.)
    - Individual positions (QB, RB, WR, etc.)
    """

    def __init__(self, parent=None):
        """Initialize roster filter proxy model."""
        super().__init__(parent)
        self._position_filter = "All Positions"
        self._group_filter = "All"
        self._search_text = ""

    def set_position_filter(self, filter_text: str):
        """
        Set position filter.

        Args:
            filter_text: Filter dropdown text (e.g., "All Positions", "Offense", "  Quarterbacks (QB)")
        """
        self._position_filter = filter_text
        self.invalidateFilter()

    def set_group_filter(self, filter_text: str):
        """
        Set group filter.

        Args:
            filter_text: Filter dropdown text (e.g., "All", "Offense", "Defense", "Special Teams")
        """
        self._group_filter = filter_text
        self.invalidateFilter()

    def set_search_filter(self, search_text: str):
        """
        Set search filter for player names.

        Args:
            search_text: Search query string (case-insensitive partial match)
        """
        self._search_text = search_text.strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Determine if row should be shown based on current filters.

        Args:
            source_row: Row index in source model
            source_parent: Parent model index

        Returns:
            True if row passes all active filters, False otherwise
        """
        # Get source model (RosterTableModel)
        model = self.sourceModel()
        if not model:
            return True

        # Get player data from source model
        position = model.get_player_position(source_row)
        player_name = model.get_player_name(source_row)

        if not position:
            return True

        # Apply search filter first (text search box)
        if self._search_text:
            # Case-insensitive substring match
            if self._search_text.lower() not in player_name.lower():
                return False

        # Apply group filter (All/Offense/Defense/Special Teams dropdown)
        if self._group_filter != "All":
            if self._group_filter == "Offense":
                if not model.is_offense_position(position):
                    return False
            elif self._group_filter == "Defense":
                if not model.is_defense_position(position):
                    return False
            elif self._group_filter == "Special Teams":
                if not model.is_special_teams_position(position):
                    return False

        # Apply position filter (detailed position dropdown)
        if self._position_filter == "All Positions":
            return True

        elif self._position_filter == "Offense":
            return model.is_offense_position(position)

        elif self._position_filter == "  Quarterbacks (QB)":
            return position.upper() == "QB"

        elif self._position_filter == "  Running Backs (RB, FB)":
            return position.upper() in {"RB", "FB"}

        elif self._position_filter == "  Wide Receivers (WR)":
            return position.upper() == "WR"

        elif self._position_filter == "  Tight Ends (TE)":
            return position.upper() == "TE"

        elif self._position_filter == "  Offensive Line (OL)":
            return position.upper() in {"OT", "OG", "C", "OL"}

        elif self._position_filter == "Defense":
            return model.is_defense_position(position)

        elif self._position_filter == "  Defensive Line (DL)":
            return position.upper() in {"DE", "DT", "DL"}

        elif self._position_filter == "  Linebackers (LB)":
            return position.upper() == "LB"

        elif self._position_filter == "  Secondary (DB)":
            return position.upper() in {"CB", "S", "DB", "FS", "SS"}

        elif self._position_filter == "Special Teams":
            return model.is_special_teams_position(position)

        elif self._position_filter == "  Kickers/Punters (K, P)":
            return position.upper() in {"K", "P"}

        elif self._position_filter == "  Returners (KR, PR)":
            return position.upper() in {"KR", "PR"}

        # Default: show all rows
        return True


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
        self.position_filter.currentIndexChanged.connect(self._on_position_filter_changed)
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
        self.group_filter.currentIndexChanged.connect(self._on_group_filter_changed)
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
        self.sort_filter.currentIndexChanged.connect(self._on_sort_changed)
        filter_layout.addWidget(self.sort_filter)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search players...")
        self.search_box.setMinimumWidth(200)
        self.search_box.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_box)

        filter_layout.addStretch()

        return filter_layout

    def _create_roster_table(self) -> QTableView:
        """Create roster table with model."""
        table = QTableView()

        # Set up model and proxy for filtering
        self.roster_model = RosterTableModel(self)
        self.roster_proxy = RosterFilterProxyModel(self)
        self.roster_proxy.setSourceModel(self.roster_model)
        table.setModel(self.roster_proxy)

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

        # Set column widths (optimized for readability - no truncation)
        table.setColumnWidth(RosterTableModel.COL_SEL, 35)        # Checkbox column
        table.setColumnWidth(RosterTableModel.COL_NUMBER, 50)     # Jersey number
        table.setColumnWidth(RosterTableModel.COL_NAME, 200)      # Player name (Last, First)
        table.setColumnWidth(RosterTableModel.COL_POSITION, 60)   # Position abbreviation
        table.setColumnWidth(RosterTableModel.COL_AGE, 50)        # Age
        table.setColumnWidth(RosterTableModel.COL_OVERALL, 55)    # Overall rating
        table.setColumnWidth(RosterTableModel.COL_CONTRACT, 140)  # Contract (Xyrs/$XXM)
        table.setColumnWidth(RosterTableModel.COL_SALARY, 110)    # Salary ($XX.XM)
        table.setColumnWidth(RosterTableModel.COL_STATUS, 70)     # Status (active/IR/etc)

        # Enable sorting
        table.setSortingEnabled(True)

        return table

    def _on_sort_changed(self, index: int):
        """
        Handle sort dropdown selection change.

        Args:
            index: Selected dropdown index (0-9)
        """
        # Map dropdown index to (column, order) pairs
        sort_options = {
            0: (RosterTableModel.COL_OVERALL, Qt.DescendingOrder),   # Overall (High to Low)
            1: (RosterTableModel.COL_OVERALL, Qt.AscendingOrder),    # Overall (Low to High)
            2: (RosterTableModel.COL_NAME, Qt.AscendingOrder),       # Name (A-Z)
            3: (RosterTableModel.COL_NAME, Qt.DescendingOrder),      # Name (Z-A)
            4: (RosterTableModel.COL_POSITION, Qt.AscendingOrder),   # Position
            5: (RosterTableModel.COL_AGE, Qt.AscendingOrder),        # Age (Youngest First)
            6: (RosterTableModel.COL_AGE, Qt.DescendingOrder),       # Age (Oldest First)
            7: (RosterTableModel.COL_SALARY, Qt.DescendingOrder),    # Salary (High to Low)
            8: (RosterTableModel.COL_SALARY, Qt.AscendingOrder),     # Salary (Low to High)
            9: (RosterTableModel.COL_CONTRACT, Qt.DescendingOrder),  # Contract Years Remaining
        }

        if index in sort_options:
            column, order = sort_options[index]
            # Sort through proxy model
            self.roster_proxy.sort(column, order)

    def _on_position_filter_changed(self, index: int):
        """
        Handle position filter dropdown selection change.

        Args:
            index: Selected dropdown index
        """
        filter_text = self.position_filter.currentText()
        self.roster_proxy.set_position_filter(filter_text)

    def _on_group_filter_changed(self, index: int):
        """
        Handle group filter dropdown selection change.

        Args:
            index: Selected dropdown index
        """
        filter_text = self.group_filter.currentText()
        self.roster_proxy.set_group_filter(filter_text)

    def _on_search_changed(self, text: str):
        """
        Handle search box text change.

        Args:
            text: Current search box text
        """
        self.roster_proxy.set_search_filter(text)

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

        # Apply initial sort based on current dropdown selection
        self._on_sort_changed(self.sort_filter.currentIndex())

        # Refresh table display
        self.roster_table.viewport().update()

    def clear_roster(self):
        """Clear all roster data."""
        self.roster_model.clear()
