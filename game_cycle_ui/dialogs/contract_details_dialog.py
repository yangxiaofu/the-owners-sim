"""
Contract Details Dialog - Shows full contract breakdown for a player.

Displays year-by-year cap hits, signing bonus proration, guaranteed money,
and dead money projections. Used to satisfy Tollgate 2 success criteria:
"Can view contract details for any player showing cap hit breakdown"
"""

from typing import Dict, Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from salary_cap.contract_manager import ContractManager
from game_cycle_ui.widgets import (
    ValuationBreakdownWidget,
    CollapsibleSection,
)
from game_cycle_ui.widgets.stat_frame import create_stat_display

if TYPE_CHECKING:
    from contract_valuation.models import ValuationResult
from game_cycle_ui.theme import (
    Colors,
    Typography,
    FontSizes,
    TextColors,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
    apply_table_style
)


class ContractDetailsDialog(QDialog):
    """
    Dialog showing full contract breakdown for a player.

    Displays:
    - Contract summary (total value, signing bonus, guaranteed)
    - Year-by-year table with: Base Salary, Bonus Proration, Cap Hit, Guaranteed, Dead $ if Cut
    """

    def __init__(
        self,
        player_name: str,
        contract_id: int,
        db_path: str,
        parent=None,
        valuation_result: Optional["ValuationResult"] = None
    ):
        """
        Initialize contract details dialog.

        Args:
            player_name: Player's display name
            contract_id: Contract ID to display
            db_path: Path to the database
            parent: Parent widget
            valuation_result: Optional valuation breakdown to display
        """
        super().__init__(parent)
        self._player_name = player_name
        self._contract_id = contract_id
        self._db_path = db_path
        self._contract_data: Optional[Dict] = None
        self._valuation_result = valuation_result

        self.setWindowTitle(f"Contract Details - {player_name}")
        self.setMinimumSize(700, 400)
        self.setModal(True)

        self._setup_ui()
        self._load_contract_data()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header with player name
        header = QLabel(f"Contract: {self._player_name}")
        header.setFont(Typography.H5)
        layout.addWidget(header)

        # Summary panel
        self._create_summary_panel(layout)

        # Year-by-year table
        self._create_year_table(layout)

        # Valuation section (if available)
        if self._valuation_result is not None:
            valuation_section = self._create_valuation_section()
            layout.addWidget(valuation_section)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary showing contract totals."""
        summary_group = QGroupBox("Contract Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Total value
        self._total_value_label = create_stat_display(
            summary_layout, "Total Value", "$0"
        )

        # Contract years
        self._years_label = create_stat_display(
            summary_layout, "Years", "0"
        )

        # Signing bonus
        self._signing_bonus_label = create_stat_display(
            summary_layout, "Signing Bonus", "$0"
        )

        # Total guaranteed
        self._guaranteed_label = create_stat_display(
            summary_layout, "Total Guaranteed", "$0"
        )

        # Contract type
        self._type_label = create_stat_display(
            summary_layout, "Type", "N/A"
        )

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_year_table(self, parent_layout: QVBoxLayout):
        """Create the year-by-year breakdown table."""
        table_group = QGroupBox("Year-by-Year Breakdown")
        table_layout = QVBoxLayout(table_group)

        self._year_table = QTableWidget()
        self._year_table.setColumnCount(6)
        self._year_table.setHorizontalHeaderLabels([
            "Year", "Base Salary", "Bonus Proration", "Cap Hit", "Guaranteed", "Dead $ if Cut"
        ])

        # Apply centralized table styling
        apply_table_style(self._year_table)

        # Configure column resize modes
        header = self._year_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        # Additional table configuration
        self._year_table.setSelectionBehavior(QTableWidget.SelectRows)

        table_layout.addWidget(self._year_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_valuation_section(self) -> QFrame:
        """Create collapsible section showing contract valuation breakdown."""
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        section = CollapsibleSection("How Was This Contract Valued?", expanded=False)
        widget = ValuationBreakdownWidget()
        widget.set_valuation_result(self._valuation_result)
        section.content_layout().addWidget(widget)
        layout.addWidget(section)

        return container

    def _load_contract_data(self):
        """Load contract details from the database."""
        try:
            manager = ContractManager(self._db_path)
            self._contract_data = manager.get_contract_details(self._contract_id)
            self._populate_data()
        except Exception as e:
            self._show_error(str(e))

    def _populate_data(self):
        """Populate the UI with contract data."""
        if not self._contract_data:
            return

        contract = self._contract_data.get("contract", {})
        year_details = self._contract_data.get("year_details", [])
        dead_money_projections = self._contract_data.get("dead_money_projections", {})

        # Update summary
        total_value = contract.get("total_value", 0)
        self._total_value_label.setText(f"${total_value:,}")

        years = contract.get("contract_years", 0)
        start_year = contract.get("start_year", 0)
        end_year = contract.get("end_year", 0)
        self._years_label.setText(f"{years} ({start_year}-{end_year})")

        signing_bonus = contract.get("signing_bonus", 0)
        self._signing_bonus_label.setText(f"${signing_bonus:,}")

        total_guaranteed = contract.get("total_guaranteed", 0)
        self._guaranteed_label.setText(f"${total_guaranteed:,}")
        if total_guaranteed > 0:
            self._guaranteed_label.setStyleSheet(f"color: {Colors.INFO};")

        contract_type = contract.get("contract_type", "N/A")
        self._type_label.setText(contract_type)

        # Populate year table
        self._year_table.setRowCount(len(year_details))
        for row, detail in enumerate(year_details):
            season_year = detail.get("season_year", 0)

            # Year
            year_item = QTableWidgetItem(str(season_year))
            year_item.setTextAlignment(Qt.AlignCenter)
            self._year_table.setItem(row, 0, year_item)

            # Base salary
            base_salary = detail.get("base_salary", 0)
            base_item = QTableWidgetItem(f"${base_salary:,}")
            base_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._year_table.setItem(row, 1, base_item)

            # Bonus proration
            proration = detail.get("signing_bonus_proration", 0)
            proration_item = QTableWidgetItem(f"${proration:,}")
            proration_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            proration_item.setForeground(QColor(Colors.INFO))
            self._year_table.setItem(row, 2, proration_item)

            # Cap hit
            cap_hit = detail.get("total_cap_hit", 0)
            cap_item = QTableWidgetItem(f"${cap_hit:,}")
            cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cap_item.setFont(Typography.BODY_BOLD)
            self._year_table.setItem(row, 3, cap_item)

            # Guaranteed
            is_guaranteed = detail.get("base_salary_guaranteed", False)
            guarantee_type = detail.get("guarantee_type", "NONE")
            if is_guaranteed:
                guaranteed_text = f"${base_salary:,}" if guarantee_type == "FULL" else "Partial"
                guaranteed_color = QColor(Colors.SUCCESS)
            else:
                guaranteed_text = "$0"
                guaranteed_color = QColor(Colors.MUTED)

            guaranteed_item = QTableWidgetItem(guaranteed_text)
            guaranteed_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            guaranteed_item.setForeground(guaranteed_color)
            self._year_table.setItem(row, 4, guaranteed_item)

            # Dead money if cut
            dead_projection = dead_money_projections.get(season_year, {})
            dead_money = dead_projection.get("standard", 0)
            dead_item = QTableWidgetItem(f"${dead_money:,}")
            dead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if dead_money > 0:
                dead_item.setForeground(QColor(Colors.ERROR))
            self._year_table.setItem(row, 5, dead_item)

        # Add totals row
        self._add_totals_row(year_details)

    def _add_totals_row(self, year_details: list):
        """Add a totals row at the bottom of the table."""
        row = self._year_table.rowCount()
        self._year_table.insertRow(row)

        # "TOTAL" label
        total_label = QTableWidgetItem("TOTAL")
        total_label.setFont(Typography.BODY_BOLD)
        total_label.setTextAlignment(Qt.AlignCenter)
        self._year_table.setItem(row, 0, total_label)

        # Calculate totals
        total_base = sum(d.get("base_salary", 0) for d in year_details)
        total_proration = sum(d.get("signing_bonus_proration", 0) for d in year_details)
        total_cap = sum(d.get("total_cap_hit", 0) for d in year_details)
        total_guaranteed = sum(
            d.get("base_salary", 0) for d in year_details if d.get("base_salary_guaranteed")
        )

        # Base salary total
        base_total = QTableWidgetItem(f"${total_base:,}")
        base_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        base_total.setFont(Typography.BODY_BOLD)
        self._year_table.setItem(row, 1, base_total)

        # Proration total
        proration_total = QTableWidgetItem(f"${total_proration:,}")
        proration_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        proration_total.setFont(Typography.BODY_BOLD)
        proration_total.setForeground(QColor(Colors.INFO))
        self._year_table.setItem(row, 2, proration_total)

        # Cap hit total
        cap_total = QTableWidgetItem(f"${total_cap:,}")
        cap_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cap_total.setFont(Typography.BODY_BOLD)
        self._year_table.setItem(row, 3, cap_total)

        # Guaranteed total
        guaranteed_total = QTableWidgetItem(f"${total_guaranteed:,}")
        guaranteed_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        guaranteed_total.setFont(Typography.BODY_BOLD)
        guaranteed_total.setForeground(QColor(Colors.SUCCESS))
        self._year_table.setItem(row, 4, guaranteed_total)

        # Dead money N/A for totals
        na_item = QTableWidgetItem("-")
        na_item.setTextAlignment(Qt.AlignCenter)
        self._year_table.setItem(row, 5, na_item)

    def _show_error(self, message: str):
        """Display error message in the dialog."""
        self._year_table.setRowCount(1)
        self._year_table.setSpan(0, 0, 1, 6)

        error_item = QTableWidgetItem(f"Error loading contract: {message}")
        error_item.setTextAlignment(Qt.AlignCenter)
        error_item.setForeground(QColor(Colors.ERROR))
        self._year_table.setItem(0, 0, error_item)
