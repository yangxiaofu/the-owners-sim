"""
Finances Tab Widget for The Owner's Sim UI

Displays salary cap information and player contracts for the Team View.
"""

from typing import Dict, Any
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

        # Store references to cap summary labels for dynamic updates
        self._cap_labels: Dict[str, QLabel] = {}

        self._init_ui()

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

        # Set column widths (5 columns total)
        self._contract_table.setColumnWidth(0, 200)  # Player
        self._contract_table.setColumnWidth(1, 60)   # Pos
        self._contract_table.setColumnWidth(2, 120)  # Cap Hit
        self._contract_table.setColumnWidth(3, 100)  # Years Left
        self._contract_table.setColumnWidth(4, 120)  # Dead Money

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
        cap_limit_widget, self._cap_labels['cap_limit'] = self._create_cap_label_with_ref("Team Salary Cap:", "Loading...", mono_font)
        left_layout.addWidget(cap_limit_widget)

        cap_used_widget, self._cap_labels['cap_used'] = self._create_cap_label_with_ref("Current Spending:", "Loading...", mono_font)
        left_layout.addWidget(cap_used_widget)

        # Cap space with green/red color based on value
        cap_space_widget, self._cap_labels['cap_space'] = self._create_cap_label_with_ref("Cap Space:", "Loading...", mono_font)
        left_layout.addWidget(cap_space_widget)

        top_51_widget, self._cap_labels['top_51'] = self._create_cap_label_with_ref("Top-51 Rule (Offseason):", "Loading...", mono_font)
        left_layout.addWidget(top_51_widget)

        current_cap_layout.addLayout(left_layout, stretch=1)

        # Right column
        right_layout = QVBoxLayout()
        roster_widget, self._cap_labels['roster'] = self._create_cap_label_with_ref("Roster Count:", "Loading...", mono_font)
        right_layout.addWidget(roster_widget)

        dead_money_widget, self._cap_labels['dead_money'] = self._create_cap_label_with_ref("Dead Money:", "Loading...", mono_font)
        right_layout.addWidget(dead_money_widget)

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
        next_year_cap_widget, self._cap_labels['next_year_cap'] = self._create_cap_label_with_ref("Projected 2026 Cap:", "Loading...", mono_font)
        proj_left_layout.addWidget(next_year_cap_widget)

        next_year_commitments_widget, self._cap_labels['next_year_commitments'] = self._create_cap_label_with_ref("2026 Commitments:", "Loading...", mono_font)
        proj_left_layout.addWidget(next_year_commitments_widget)
        projection_layout.addLayout(proj_left_layout, stretch=1)

        proj_right_layout = QVBoxLayout()
        next_year_space_widget, self._cap_labels['next_year_space'] = self._create_cap_label_with_ref("2026 Projected Space:", "Loading...", mono_font)
        proj_right_layout.addWidget(next_year_space_widget)
        proj_right_layout.addWidget(QLabel())  # Spacer
        projection_layout.addLayout(proj_right_layout, stretch=1)

        layout.addLayout(projection_layout)

        return group

    def _create_cap_label_with_ref(self, label_text: str, value_text: str, font: QFont) -> tuple[QWidget, QLabel]:
        """
        Create a label-value pair for cap information with reference to value label.

        Args:
            label_text: Label text (e.g., "Team Salary Cap:")
            value_text: Value text (e.g., "$224,800,000")
            font: Font to use for the value

        Returns:
            Tuple of (widget, value_label) for dynamic updates
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setMinimumWidth(200)
        layout.addWidget(label)

        value = QLabel(value_text)
        value.setObjectName("value_label")
        value.setFont(font)
        value.setAlignment(Qt.AlignLeft)
        layout.addWidget(value)

        layout.addStretch()

        return widget, value

    def load_finances_data(self, controller, team_id: int):
        """
        Load real finances data from database.

        Args:
            controller: TeamController instance for data access
            team_id: Team ID to load finances for
        """
        try:
            # Load cap summary
            cap_summary = controller.get_cap_summary(team_id)
            if cap_summary:
                self._update_cap_summary(cap_summary)

            # Load contracts
            contracts = controller.get_team_contracts(team_id)
            self._contract_model.set_contracts(contracts)

            # Sort table by cap hit descending
            self._contract_table.sortByColumn(ContractTableModel.COL_CAP_HIT, Qt.DescendingOrder)

        except Exception as e:
            print(f"[ERROR FinancesTabWidget] Failed to load finances data for team {team_id}: {e}")
            import traceback
            traceback.print_exc()

    def _update_cap_summary(self, cap_summary: Dict[str, Any]):
        """
        Update cap summary panel with real data.

        Args:
            cap_summary: Cap summary dict from controller
        """
        # Format currency helper
        def format_currency(amount: int) -> str:
            """Format amount in dollars to $XXX,XXX,XXX format."""
            millions = amount / 1_000_000.0
            return f"${millions:,.1f}M"

        # Update cap limit
        cap_limit = cap_summary.get('cap_limit', 0)
        self._cap_labels['cap_limit'].setText(f"${cap_limit:,}")

        # Update cap used
        cap_used = cap_summary.get('cap_used', 0)
        self._cap_labels['cap_used'].setText(f"${cap_used:,}")

        # Update cap space (with color coding)
        cap_space = cap_summary.get('cap_space', 0)
        if cap_space >= 0:
            self._cap_labels['cap_space'].setText(f"${cap_space:,} ✅ COMPLIANT")
            self._cap_labels['cap_space'].setStyleSheet("color: #388E3C; font-weight: bold;")
        else:
            self._cap_labels['cap_space'].setText(f"${cap_space:,} ❌ OVER CAP")
            self._cap_labels['cap_space'].setStyleSheet("color: #D32F2F; font-weight: bold;")

        # Update roster count
        roster_count = cap_summary.get('roster_count', 0)
        max_roster = 53
        self._cap_labels['roster'].setText(f"{roster_count} / {max_roster}")

        # Update dead money
        dead_money = cap_summary.get('dead_money', 0)
        self._cap_labels['dead_money'].setText(format_currency(dead_money))

        # Update top-51 status
        top_51_active = cap_summary.get('top_51_active', False)
        self._cap_labels['top_51'].setText("ACTIVE" if top_51_active else "INACTIVE")

        # Update next year projections
        next_year_cap = cap_summary.get('next_year_cap', 0)
        self._cap_labels['next_year_cap'].setText(f"${next_year_cap:,}")

        next_year_commitments = cap_summary.get('next_year_commitments', 0)
        self._cap_labels['next_year_commitments'].setText(format_currency(next_year_commitments))

        next_year_space = cap_summary.get('next_year_space', 0)
        self._cap_labels['next_year_space'].setText(format_currency(next_year_space))

    def clear_data(self):
        """Clear all displayed data."""
        self._contract_model.clear()

        # Reset all cap labels to "Loading..."
        for label in self._cap_labels.values():
            label.setText("Loading...")
            label.setStyleSheet("")  # Remove any custom styling
