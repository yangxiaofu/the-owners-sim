"""
Draft Prospects Widget for The Owner's Sim

Displays all available draft prospects with filtering by position.
Shows prospect ratings, physical attributes, and college information.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTabWidget, QHeaderView, QPushButton
)
from PySide6.QtCore import Qt
from typing import Optional, List, Dict, Any


class NumericTableWidgetItem(QTableWidgetItem):
    """
    QTableWidgetItem subclass that sorts numerically using UserRole data.

    This class overrides the less-than operator to compare numeric values
    stored in Qt.UserRole instead of comparing display text strings.

    Example:
        With standard QTableWidgetItem:
            "1", "10", "2", "20" → sorts as 1, 10, 2, 20 (lexicographic)

        With NumericTableWidgetItem:
            "1", "10", "2", "20" → sorts as 1, 2, 10, 20 (numeric)

    Usage:
        rank_item = NumericTableWidgetItem(str(rank))
        rank_item.setData(Qt.UserRole, rank)  # Store numeric value
    """

    def __lt__(self, other: QTableWidgetItem) -> bool:
        """
        Compare items numerically using UserRole data.

        Args:
            other: Another QTableWidgetItem to compare against

        Returns:
            True if this item's numeric value is less than other's
        """
        # Get numeric values from UserRole
        self_value = self.data(Qt.UserRole)
        other_value = other.data(Qt.UserRole)

        # Compare numerically if both have numeric data
        if self_value is not None and other_value is not None:
            try:
                return float(self_value) < float(other_value)
            except (ValueError, TypeError):
                # If conversion fails, fall back to string comparison
                pass

        # Fall back to default string comparison
        return super().__lt__(other)


class DraftProspectsWidget(QWidget):
    """
    Draft prospects browser widget.

    Displays all prospects in the current draft class with:
    - Position tabs (All, QB, RB, WR, TE, OL, DL, LB, DB, K/P)
    - Sortable columns (Rank, Name, Position, College, Ratings)
    - Click to view detailed prospect profile
    - Auto-refresh when visible

    Integrated with DraftClassAPI via LeagueController.
    """

    # Position mappings for tabs
    POSITIONS = {
        'All': None,
        'QB': 'QB',
        'RB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'OL': ['OT', 'OG', 'C'],  # Offensive line positions
        'DL': ['DE', 'DT', 'EDGE'],  # Defensive line positions
        'LB': 'LB',
        'DB': ['CB', 'S'],  # Defensive backs
        'K/P': ['K', 'P']  # Kickers and punters
    }

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        # Store controller reference
        self.controller = controller

        # Table references for each position tab
        self.tables = {}

        # Info label references
        self.info_labels = {}

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Position tabs
        self.tabs = QTabWidget()
        for position_name in self.POSITIONS.keys():
            tab_widget = self._create_position_tab(position_name)
            self.tabs.addTab(tab_widget, position_name)

        layout.addWidget(self.tabs)

        # Load initial data
        if self.controller:
            self.load_data()

    @property
    def season(self) -> int:
        """Current season year (proxied from parent)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        elif self.controller and hasattr(self.controller, 'season'):
            return self.controller.season
        return 2025  # Fallback

    @property
    def draft_season(self) -> int:
        """Draft class season (current season + 1)."""
        return self.season + 1

    def showEvent(self, event):
        """
        Override showEvent to refresh prospects when widget becomes visible.

        This ensures prospect data is always current when user views this tab.
        """
        super().showEvent(event)

        # Refresh data whenever the widget is shown
        if self.controller:
            self.load_data()

    def _create_header(self) -> QHBoxLayout:
        """Create header with title and draft year info."""
        header = QHBoxLayout()

        # Title
        title = QLabel("NFL Draft Prospects")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        # Draft year label
        self.draft_year_label = QLabel()
        self._update_draft_year_label()
        self.draft_year_label.setStyleSheet("font-size: 14px; color: #666;")
        header.addWidget(self.draft_year_label)

        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        header.addWidget(refresh_btn)

        return header

    def _update_draft_year_label(self):
        """Update the draft year label based on current season."""
        draft_year = self.draft_season
        self.draft_year_label.setText(f"({draft_year} NFL Draft)")

    def _create_position_tab(self, position_name: str) -> QWidget:
        """
        Create a tab for a specific position filter.

        Args:
            position_name: Position tab name (All, QB, RB, etc.)

        Returns:
            QWidget containing table and info label
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "Rank", "Name", "Pos", "College", "Overall", "Potential",
            "Age", "Height", "Weight", "Status"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # College
        table.verticalHeader().setVisible(False)

        # Double-click to view prospect details
        table.doubleClicked.connect(lambda: self._on_prospect_double_clicked(table))

        layout.addWidget(table)

        # Info label
        info_label = QLabel("Loading prospects...")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        # Store references
        self.tables[position_name] = table
        self.info_labels[position_name] = info_label

        return widget

    def load_data(self):
        """Load all draft prospects from controller and populate tables."""
        if not self.controller:
            return

        # Update draft year label
        self._update_draft_year_label()

        # Load data for each position tab
        for position_name, position_filter in self.POSITIONS.items():
            self._load_position_data(position_name, position_filter)

    def _load_position_data(self, position_name: str, position_filter: Optional[Any]):
        """
        Load prospects for a specific position tab.

        Args:
            position_name: Tab name (All, QB, etc.)
            position_filter: Position filter value (None for All, str or list for specific)
        """
        table = self.tables.get(position_name)
        info_label = self.info_labels.get(position_name)

        if not table or not info_label:
            return

        try:
            # Get prospects from controller
            if isinstance(position_filter, list):
                # Multiple positions (OL, DL, DB, K/P)
                all_prospects = []
                for pos in position_filter:
                    prospects = self.controller.get_draft_prospects(position_filter=pos, limit=300)
                    all_prospects.extend(prospects)
            else:
                # Single position or All
                all_prospects = self.controller.get_draft_prospects(position_filter=position_filter, limit=300)

            # Populate table
            self._populate_table(table, all_prospects)

            # Update info label
            count = len(all_prospects)
            if count == 0:
                info_label.setText("No prospects found")
            elif count == 1:
                info_label.setText("1 prospect found")
            else:
                info_label.setText(f"{count} prospects found")

        except Exception as e:
            # Handle errors gracefully
            table.setRowCount(0)
            info_label.setText(f"Error loading prospects: {str(e)}")

    def _populate_table(self, table: QTableWidget, prospects: List[Dict[str, Any]]):
        """
        Populate a table with prospect data.

        Args:
            table: QTableWidget to populate
            prospects: List of prospect dictionaries
        """
        # Disable sorting while populating
        table.setSortingEnabled(False)

        # Clear existing rows
        table.setRowCount(0)

        # Add rows
        for rank, prospect in enumerate(prospects, start=1):
            row = table.rowCount()
            table.insertRow(row)

            # Rank
            rank_item = NumericTableWidgetItem(str(rank))
            rank_item.setData(Qt.UserRole, rank)  # Store numeric value for sorting
            rank_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, rank_item)

            # Name
            name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}"
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, prospect.get('player_id'))  # Store player_id
            table.setItem(row, 1, name_item)

            # Position
            pos_item = QTableWidgetItem(prospect.get('position', ''))
            pos_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, pos_item)

            # College
            college_item = QTableWidgetItem(prospect.get('college', 'Unknown'))
            table.setItem(row, 3, college_item)

            # Overall rating
            overall = prospect.get('overall', 0)
            overall_item = NumericTableWidgetItem(str(overall))
            overall_item.setData(Qt.UserRole, overall)  # Store numeric value for sorting
            overall_item.setTextAlignment(Qt.AlignCenter)
            # Color code by rating
            if overall >= 85:
                overall_item.setForeground(Qt.darkGreen)
            elif overall >= 75:
                overall_item.setForeground(Qt.darkBlue)
            elif overall < 65:
                overall_item.setForeground(Qt.darkRed)
            table.setItem(row, 4, overall_item)

            # Potential rating
            potential = prospect.get('potential', 0)
            potential_item = NumericTableWidgetItem(str(potential))
            potential_item.setData(Qt.UserRole, potential)  # Store numeric value for sorting
            potential_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 5, potential_item)

            # Age
            age = prospect.get('age', 0)
            age_item = NumericTableWidgetItem(str(age) if age else "")
            age_item.setData(Qt.UserRole, age if age else 0)  # Store numeric value for sorting
            age_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 6, age_item)

            # Height (convert inches to feet-inches)
            height_inches = prospect.get('height_inches')
            if height_inches:
                feet = height_inches // 12
                inches = height_inches % 12
                height_str = f"{feet}'{inches}\""
            else:
                height_str = ""
            height_item = QTableWidgetItem(height_str)
            height_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 7, height_item)

            # Weight
            weight = prospect.get('weight_lbs', 0)
            weight_item = NumericTableWidgetItem(str(weight) if weight else "")
            weight_item.setData(Qt.UserRole, weight if weight else 0)  # Store numeric value for sorting
            weight_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 8, weight_item)

            # Status
            is_drafted = prospect.get('is_drafted', False)
            if is_drafted:
                drafted_team_id = prospect.get('drafted_by_team_id')
                status_text = f"Drafted by Team {drafted_team_id}" if drafted_team_id else "Drafted"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.darkGray)
            else:
                status_item = QTableWidgetItem("Available")
                status_item.setForeground(Qt.darkGreen)
            table.setItem(row, 9, status_item)

        # Re-enable sorting
        table.setSortingEnabled(True)

        # Sort by rank (column 0) by default
        table.sortItems(0, Qt.AscendingOrder)

    def _on_prospect_double_clicked(self, table: QTableWidget):
        """
        Handle double-click on a prospect row to show detailed view.

        Args:
            table: QTableWidget that was double-clicked
        """
        # Get selected row
        selected_rows = table.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()

        # Get player_id from Name column (stored in UserRole)
        name_item = table.item(row, 1)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        if not player_id:
            return

        # Show prospect detail dialog
        self._show_prospect_detail(player_id)

    def _show_prospect_detail(self, player_id: int):
        """
        Show detailed prospect information dialog.

        Args:
            player_id: Prospect's player ID
        """
        from ui.dialogs.prospect_detail_dialog import ProspectDetailDialog

        if not self.controller:
            return

        # Get detailed prospect data
        try:
            prospect = self.controller.get_prospect_detail(player_id)
            if not prospect:
                return

            # Show dialog
            dialog = ProspectDetailDialog(prospect=prospect, parent=self)
            dialog.exec()

        except Exception as e:
            print(f"Error showing prospect detail: {e}")
