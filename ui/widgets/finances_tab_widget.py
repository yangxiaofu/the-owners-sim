"""
Finances Tab Widget for The Owner's Sim UI

Displays salary cap information and player contracts for the Team View.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.models.contract_table_model import ContractTableModel


class FinancesTabWidget(QWidget):
    """
    Finances sub-tab widget for Team View.

    Displays:
    - Salary cap summary with current year and projected next year
    - Player contracts table sorted by cap hit
    - Action buttons for cap management tools
    """

    def __init__(self, parent=None):
        """Initialize finances tab widget."""
        super().__init__(parent)

        # Create contract table model
        self._contract_model = ContractTableModel(self)

        self._init_ui()
        self._load_mock_data()

    def _init_ui(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Cap Summary Panel
        cap_summary_group = self._create_cap_summary_panel()
        cap_summary_group.setMaximumHeight(250)
        layout.addWidget(cap_summary_group)

        # Contract List Table
        contract_table_label = QLabel("Player Contracts (Sorted by Cap Hit)")
        contract_table_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(contract_table_label)

        self._contract_table = QTableView()
        self._contract_table.setModel(self._contract_model)
        self._contract_table.setSortingEnabled(True)
        self._contract_table.setAlternatingRowColors(True)
        self._contract_table.setSelectionBehavior(QTableView.SelectRows)
        self._contract_table.setSelectionMode(QTableView.SingleSelection)
        self._contract_table.horizontalHeader().setStretchLastSection(True)

        # Set column widths
        self._contract_table.setColumnWidth(0, 180)  # Player
        self._contract_table.setColumnWidth(1, 60)   # Pos
        self._contract_table.setColumnWidth(2, 120)  # Cap Hit
        self._contract_table.setColumnWidth(3, 120)  # Base Salary
        self._contract_table.setColumnWidth(4, 120)  # Bonus
        self._contract_table.setColumnWidth(5, 60)   # Years

        layout.addWidget(self._contract_table, stretch=1)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        export_button = QPushButton("Export to CSV")
        export_button.setEnabled(False)  # Disabled for now
        button_layout.addWidget(export_button)

        projection_button = QPushButton("Cap Projection Tool")
        projection_button.setEnabled(False)  # Disabled for now
        button_layout.addWidget(projection_button)

        layout.addLayout(button_layout)

    def _create_cap_summary_panel(self) -> QGroupBox:
        """Create the salary cap summary panel."""
        group = QGroupBox("💰 SALARY CAP SUMMARY - 2025")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11pt; }")

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Create monospace font for numbers
        mono_font = QFont("Courier New", 10)

        # Current Year Cap Information
        current_cap_layout = QHBoxLayout()

        # Left column
        left_layout = QVBoxLayout()
        left_layout.addWidget(self._create_cap_label("Team Salary Cap:", "$224,800,000", mono_font))
        left_layout.addWidget(self._create_cap_label("Current Spending:", "$212,252,668", mono_font))

        # Cap space with green color
        cap_space_label = self._create_cap_label("Cap Space:", "$12,547,332 ✅ COMPLIANT", mono_font)
        cap_space_value = cap_space_label.findChild(QLabel, "value_label")
        if cap_space_value:
            cap_space_value.setStyleSheet("color: #388E3C; font-weight: bold;")
        left_layout.addWidget(cap_space_label)

        left_layout.addWidget(self._create_cap_label("Top-51 Rule (Offseason):", "ACTIVE", mono_font))

        current_cap_layout.addLayout(left_layout, stretch=1)

        # Right column
        right_layout = QVBoxLayout()
        right_layout.addWidget(self._create_cap_label("Roster Count:", "53 / 53", mono_font))
        right_layout.addWidget(self._create_cap_label("Dead Money:", "$0", mono_font))
        right_layout.addWidget(QLabel())  # Spacer
        right_layout.addWidget(QLabel())  # Spacer

        current_cap_layout.addLayout(right_layout, stretch=1)

        layout.addLayout(current_cap_layout)

        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #555; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator)

        # Next Year Projections
        projection_layout = QHBoxLayout()

        proj_left_layout = QVBoxLayout()
        proj_left_layout.addWidget(self._create_cap_label("Projected 2026 Cap:", "$238,200,000", mono_font))
        proj_left_layout.addWidget(self._create_cap_label("2026 Commitments:", "$143,678,000", mono_font))
        projection_layout.addLayout(proj_left_layout, stretch=1)

        proj_right_layout = QVBoxLayout()
        proj_right_layout.addWidget(self._create_cap_label("2026 Projected Space:", "$94,522,000", mono_font))
        proj_right_layout.addWidget(QLabel())  # Spacer
        projection_layout.addLayout(proj_right_layout, stretch=1)

        layout.addLayout(projection_layout)

        return group

    def _create_cap_label(self, label_text: str, value_text: str, font: QFont) -> QWidget:
        """
        Create a label-value pair for cap information.

        Args:
            label_text: Label text (e.g., "Team Salary Cap:")
            value_text: Value text (e.g., "$224,800,000")
            font: Font to use for the value

        Returns:
            QWidget containing the label-value pair
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setMinimumWidth(200)
        layout.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("value_label")  # For finding it later
        value.setFont(font)
        value.setAlignment(Qt.AlignLeft)
        layout.addWidget(value)

        layout.addStretch()

        return widget

    def _load_mock_data(self):
        """Load mock contract data for demonstration."""
        # Mock contract data - top 15 contracts
        mock_contracts = [
            {
                'player_name': 'Patrick Mahomes',
                'position': 'QB',
                'cap_hit': 45000000,
                'base_salary': 37500000,
                'bonus': 7500000,
                'years_remaining': 8,
                'total_value': 450000000
            },
            {
                'player_name': 'Justin Jefferson',
                'position': 'WR',
                'cap_hit': 35000000,
                'base_salary': 28000000,
                'bonus': 7000000,
                'years_remaining': 4,
                'total_value': 140000000
            },
            {
                'player_name': 'Christian McCaffrey',
                'position': 'RB',
                'cap_hit': 17000000,
                'base_salary': 12000000,
                'bonus': 5000000,
                'years_remaining': 3,
                'total_value': 64000000
            },
            {
                'player_name': 'Trent Williams',
                'position': 'LT',
                'cap_hit': 15500000,
                'base_salary': 10500000,
                'bonus': 5000000,
                'years_remaining': 2,
                'total_value': 46000000
            },
            {
                'player_name': 'Fred Warner',
                'position': 'LB',
                'cap_hit': 14000000,
                'base_salary': 9500000,
                'bonus': 4500000,
                'years_remaining': 3,
                'total_value': 55000000
            },
            {
                'player_name': 'Nick Bosa',
                'position': 'DE',
                'cap_hit': 13800000,
                'base_salary': 9000000,
                'bonus': 4800000,
                'years_remaining': 4,
                'total_value': 170000000
            },
            {
                'player_name': 'Deebo Samuel',
                'position': 'WR',
                'cap_hit': 12500000,
                'base_salary': 8500000,
                'bonus': 4000000,
                'years_remaining': 2,
                'total_value': 71400000
            },
            {
                'player_name': 'George Kittle',
                'position': 'TE',
                'cap_hit': 11000000,
                'base_salary': 7500000,
                'bonus': 3500000,
                'years_remaining': 2,
                'total_value': 75000000
            },
            {
                'player_name': 'Javon Hargrave',
                'position': 'DT',
                'cap_hit': 10200000,
                'base_salary': 7200000,
                'bonus': 3000000,
                'years_remaining': 3,
                'total_value': 84000000
            },
            {
                'player_name': 'Charvarius Ward',
                'position': 'CB',
                'cap_hit': 9500000,
                'base_salary': 6500000,
                'bonus': 3000000,
                'years_remaining': 2,
                'total_value': 40500000
            },
            {
                'player_name': 'Brandon Aiyuk',
                'position': 'WR',
                'cap_hit': 8800000,
                'base_salary': 6000000,
                'bonus': 2800000,
                'years_remaining': 1,
                'total_value': 14124000
            },
            {
                'player_name': 'Talanoa Hufanga',
                'position': 'S',
                'cap_hit': 7500000,
                'base_salary': 5000000,
                'bonus': 2500000,
                'years_remaining': 2,
                'total_value': 40000000
            },
            {
                'player_name': 'Jake Moody',
                'position': 'K',
                'cap_hit': 1200000,
                'base_salary': 900000,
                'bonus': 300000,
                'years_remaining': 3,
                'total_value': 4500000
            },
            {
                'player_name': 'Mitch Wishnowsky',
                'position': 'P',
                'cap_hit': 1100000,
                'base_salary': 850000,
                'bonus': 250000,
                'years_remaining': 2,
                'total_value': 3000000
            },
            {
                'player_name': 'Brock Purdy',
                'position': 'QB',
                'cap_hit': 980000,
                'base_salary': 980000,
                'bonus': 0,
                'years_remaining': 1,
                'total_value': 980000
            },
        ]

        # Sort by cap hit descending
        mock_contracts.sort(key=lambda c: c['cap_hit'], reverse=True)

        self._contract_model.set_contracts(mock_contracts)

        # Sort table by cap hit descending by default
        self._contract_table.sortByColumn(ContractTableModel.COL_CAP_HIT, Qt.DescendingOrder)

    def refresh_data(self, team_id: int, dynasty_id: str):
        """
        Refresh finances data for the given team and dynasty.

        Args:
            team_id: Team ID to display finances for
            dynasty_id: Dynasty ID for database context
        """
        # TODO: Load real data from database
        # For now, just use mock data
        self._load_mock_data()

    def clear_data(self):
        """Clear all displayed data."""
        self._contract_model.clear()
