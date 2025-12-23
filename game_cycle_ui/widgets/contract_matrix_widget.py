"""
Contract Matrix Widget - Displays player contracts across multiple years.

Features:
- Dynamic year columns (current year + N future years)
- Sortable by any column (player name, position, cap hit per year)
- Color coding: expiring contracts, guaranteed money, cap hit severity
- NumericTableWidgetItem for proper numeric sorting
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont

from game_cycle_ui.theme import (
    apply_table_style, Colors, Typography, ESPN_THEME
)
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem


class ContractMatrixWidget(QTableWidget):
    """
    Matrix table showing player contracts by year.

    Columns:
    - Player Name
    - Position
    - Total Value
    - Year 1 (current_year)
    - Year 2 (current_year + 1)
    - ... up to Year 7 (current_year + 6)

    Signals:
    - player_clicked(player_id: int)
    - contract_clicked(contract_id: int, player_name: str)
    """

    player_clicked = Signal(int)  # player_id
    contract_clicked = Signal(int, str)  # contract_id, player_name

    # Fixed columns before year columns
    FIXED_COLUMNS = ["Player", "Pos", "Total Value"]
    FIXED_COLUMN_COUNT = 3

    # Cap hit thresholds for color coding (in dollars)
    CAP_THRESHOLD_MEDIUM = 5_000_000   # $5M
    CAP_THRESHOLD_HIGH = 10_000_000    # $10M
    CAP_THRESHOLD_VERY_HIGH = 20_000_000  # $20M

    # Dark theme colors
    COLOR_DEFAULT_TEXT = "#FFFFFF"
    COLOR_MEDIUM_TEXT = Colors.WARNING       # Orange
    COLOR_HIGH_TEXT = Colors.ERROR           # Red
    COLOR_VERY_HIGH_BG = "#3D1B1B"           # Dark red background
    COLOR_VERY_HIGH_TEXT = "#FF6B6B"         # Bright red text
    COLOR_EXPIRING_BG = Colors.WARNING_DARK  # Dark orange background
    COLOR_EXPIRING_TEXT = Colors.WARNING     # Orange text
    COLOR_GUARANTEED_TEXT = Colors.INFO      # Blue text
    COLOR_MUTED_TEXT = "#666666"             # Gray for empty cells

    def __init__(
        self,
        current_year: int = 2025,
        num_years: int = 7,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._current_year = current_year
        self._num_years = num_years
        self._contract_data: List[Dict] = []

        self._setup_table()

    def _setup_table(self):
        """Initialize table with fixed + year columns."""
        # Build column headers
        year_headers = [
            str(self._current_year + i) for i in range(self._num_years)
        ]
        all_headers = self.FIXED_COLUMNS + year_headers

        self.setColumnCount(len(all_headers))
        self.setHorizontalHeaderLabels(all_headers)

        # Apply standard ESPN dark table styling
        apply_table_style(self)

        # Enable sorting
        self.setSortingEnabled(True)

        # Configure column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Total

        # Year columns - fixed width
        for i in range(self._num_years):
            col_idx = self.FIXED_COLUMN_COUNT + i
            header.setSectionResizeMode(col_idx, QHeaderView.Fixed)
            header.resizeSection(col_idx, 120)  # Enough for "$15.5M / $5.5M"

        # Connect double-click
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def set_current_year(self, year: int):
        """Update the current year and refresh column headers."""
        self._current_year = year
        year_headers = [
            str(self._current_year + i) for i in range(self._num_years)
        ]
        for i, header_text in enumerate(year_headers):
            self.setHorizontalHeaderItem(
                self.FIXED_COLUMN_COUNT + i,
                QTableWidgetItem(header_text)
            )
        self._refresh_table()

    def set_contract_data(self, data: List[Dict]):
        """
        Set the contract data and populate the table.

        Args:
            data: List of player contract entries:
                - player_id: int
                - player_name: str
                - position: str
                - contract_id: int
                - end_year: int
                - total_value: int
                - total_guaranteed: int
                - year_cap_hits: Dict[int, Dict] with keys:
                    - cap_hit: int
                    - guaranteed: bool
                    - is_final_year: bool
        """
        self._contract_data = data
        self._refresh_table()

    def _refresh_table(self):
        """Populate the table with current data."""
        # Disable sorting during population to avoid performance issues
        self.setSortingEnabled(False)
        self.setRowCount(len(self._contract_data))

        for row, entry in enumerate(self._contract_data):
            self._populate_row(row, entry)

        # Re-enable sorting
        self.setSortingEnabled(True)

    def _populate_row(self, row: int, entry: Dict):
        """Populate a single row."""
        player_id = entry.get('player_id', 0)
        contract_id = entry.get('contract_id', 0)
        end_year = entry.get('end_year', 0)

        # Column 0: Player name (store IDs for clicks)
        name_item = QTableWidgetItem(entry.get('player_name', 'Unknown'))
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, contract_id)
        self.setItem(row, 0, name_item)

        # Column 1: Position
        pos_item = QTableWidgetItem(entry.get('position', ''))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 1, pos_item)

        # Column 2: Total Value
        total_value = entry.get('total_value', 0)
        total_item = NumericTableWidgetItem(
            total_value,
            display_text=self._format_cap(total_value)
        )
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setItem(row, 2, total_item)

        # Year columns (3+)
        year_cap_hits = entry.get('year_cap_hits', {})

        for i in range(self._num_years):
            year = self._current_year + i
            col_idx = self.FIXED_COLUMN_COUNT + i

            cap_info = year_cap_hits.get(year, {})
            cap_hit = cap_info.get('cap_hit', 0)
            bonus = cap_info.get('signing_bonus_proration', 0)

            # Create item with dual-number display (cap hit / bonus)
            if cap_hit > 0:
                if bonus > 0:
                    display_text = f"{self._format_cap(cap_hit)} / {self._format_cap(bonus)}"
                else:
                    display_text = self._format_cap(cap_hit)
                item = NumericTableWidgetItem(cap_hit, display_text=display_text)
            else:
                item = NumericTableWidgetItem(0, display_text="-")
                item.setForeground(QColor(self.COLOR_MUTED_TEXT))

            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Apply visual indicators and rich tooltip
            if cap_hit > 0:
                self._apply_cap_hit_styling(item, cap_info)

            self.setItem(row, col_idx, item)

    def _apply_cap_hit_styling(
        self,
        item: QTableWidgetItem,
        cap_info: Dict
    ):
        """Apply color coding based on cap hit and contract status."""
        cap_hit = cap_info.get('cap_hit', 0)
        is_guaranteed = cap_info.get('guaranteed', False)
        is_final_year = cap_info.get('is_final_year', False)

        # Default: white text
        text_color = self.COLOR_DEFAULT_TEXT
        bg_color = None
        font = item.font()

        # Priority 1: Expiring contract (final year) - dark orange bg
        if is_final_year:
            bg_color = self.COLOR_EXPIRING_BG
            text_color = self.COLOR_EXPIRING_TEXT
        # Priority 2: Very high cap hit - dark red bg
        elif cap_hit >= self.CAP_THRESHOLD_VERY_HIGH:
            bg_color = self.COLOR_VERY_HIGH_BG
            text_color = self.COLOR_VERY_HIGH_TEXT
        # Priority 3: High cap hit - red text
        elif cap_hit >= self.CAP_THRESHOLD_HIGH:
            text_color = self.COLOR_HIGH_TEXT
        # Priority 4: Medium cap hit - orange text
        elif cap_hit >= self.CAP_THRESHOLD_MEDIUM:
            text_color = self.COLOR_MEDIUM_TEXT

        # Guaranteed money indicator: underline + blue (if not overridden by expiring)
        if is_guaranteed and not is_final_year:
            text_color = self.COLOR_GUARANTEED_TEXT
            font.setUnderline(True)
            item.setFont(font)

        # Apply colors
        item.setForeground(QColor(text_color))
        if bg_color:
            item.setBackground(QBrush(QColor(bg_color)))

        # Apply rich breakdown tooltip
        item.setToolTip(self._build_breakdown_tooltip(cap_info))

    def _format_cap(self, amount: int) -> str:
        """Format cap hit as $XXM or $XXK."""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        elif amount > 0:
            return f"${amount:,}"
        return "-"

    def _build_breakdown_tooltip(self, cap_info: Dict) -> str:
        """Build rich tooltip showing cap hit breakdown."""
        lines = []

        base = cap_info.get('base_salary', 0)
        signing = cap_info.get('signing_bonus_proration', 0)
        roster = cap_info.get('roster_bonus', 0)
        workout = cap_info.get('workout_bonus', 0)
        total = cap_info.get('cap_hit', 0)

        # Only show non-zero components
        if base > 0:
            lines.append(f"Base Salary: {self._format_cap(base)}")
        if signing > 0:
            lines.append(f"Signing Bonus: {self._format_cap(signing)}")
        if roster > 0:
            lines.append(f"Roster Bonus: {self._format_cap(roster)}")
        if workout > 0:
            lines.append(f"Workout Bonus: {self._format_cap(workout)}")

        # Add separator and total if we have breakdown components
        if lines:
            lines.append("─" * 22)
            lines.append(f"Total Cap Hit: {self._format_cap(total)}")

        # Add status indicators
        if cap_info.get('is_final_year'):
            lines.append("")
            lines.append("⚠ Final Year - Expiring")
        if cap_info.get('guaranteed'):
            if not cap_info.get('is_final_year'):
                lines.append("")
            lines.append("💰 Guaranteed")

        return "\n".join(lines) if lines else f"Cap Hit: {self._format_cap(total)}"

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click to emit signals."""
        name_item = self.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        contract_id = name_item.data(Qt.UserRole + 1)
        player_name = name_item.text()

        if player_id:
            self.player_clicked.emit(player_id)
        if contract_id:
            self.contract_clicked.emit(contract_id, player_name)

    def get_total_cap_for_year(self, year: int) -> int:
        """Calculate total cap committed for a specific year."""
        total = 0
        for entry in self._contract_data:
            year_cap_hits = entry.get('year_cap_hits', {})
            cap_info = year_cap_hits.get(year, {})
            total += cap_info.get('cap_hit', 0)
        return total

    def get_player_count(self) -> int:
        """Return number of players in the matrix."""
        return len(self._contract_data)