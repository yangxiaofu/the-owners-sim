"""
Contract Table Model for The Owner's Sim UI

Qt table model for displaying player contract information in the Finances tab.
"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QBrush, QColor
from typing import List, Optional, Any, Dict


class ContractTableModel(QAbstractTableModel):
    """
    Qt table model for displaying player contracts.

    Displays contract information in a sortable table format with
    proper currency formatting and highlighting for top contracts.
    """

    # Column indices
    COL_PLAYER = 0
    COL_POSITION = 1
    COL_CAP_HIT = 2
    COL_YEARS_LEFT = 3
    COL_DEAD_MONEY = 4

    def __init__(self, parent=None):
        """Initialize contract table model."""
        super().__init__(parent)
        self._contracts: List[Dict[str, Any]] = []

        # Column headers
        self._headers = ["Player", "Pos", "2025 Hit", "Years Left", "Dead $ (Cut)"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows (contracts)."""
        if parent.isValid():
            return 0
        return len(self._contracts)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._contracts):
            return None

        contract = self._contracts[row]

        # Background color for top 3 contracts
        if role == Qt.BackgroundRole:
            if row < 3:
                # Light gold/yellow shade for top contracts
                return QBrush(QColor(255, 250, 205))  # LemonChiffon
            return None

        # Text alignment
        if role == Qt.TextAlignmentRole:
            if col in (self.COL_PLAYER, self.COL_POSITION):
                return Qt.AlignLeft | Qt.AlignVCenter
            else:
                return Qt.AlignRight | Qt.AlignVCenter

        # Display data
        if role != Qt.DisplayRole:
            return None

        if col == self.COL_PLAYER:
            return contract["player"]

        elif col == self.COL_POSITION:
            return contract["pos"]

        elif col == self.COL_CAP_HIT:
            return self._format_currency(contract["cap_hit"])

        elif col == self.COL_YEARS_LEFT:
            years = contract["years_left"]
            return f"{years} yr{'s' if years != 1 else ''}"

        elif col == self.COL_DEAD_MONEY:
            return self._format_currency(contract["dead_money"])

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]

        elif orientation == Qt.Vertical:
            return str(section + 1)

        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        """Sort contracts by column."""
        self.beginResetModel()

        reverse = (order == Qt.DescendingOrder)

        if column == self.COL_PLAYER:
            self._contracts.sort(key=lambda c: c["player"], reverse=reverse)

        elif column == self.COL_POSITION:
            self._contracts.sort(key=lambda c: c["pos"], reverse=reverse)

        elif column == self.COL_CAP_HIT:
            self._contracts.sort(key=lambda c: c["cap_hit"], reverse=reverse)

        elif column == self.COL_YEARS_LEFT:
            self._contracts.sort(key=lambda c: c["years_left"], reverse=reverse)

        elif column == self.COL_DEAD_MONEY:
            self._contracts.sort(key=lambda c: c["dead_money"], reverse=reverse)

        self.endResetModel()

    def set_contracts(self, contracts: List[Dict[str, Any]]):
        """
        Set contract data for display.

        Args:
            contracts: List of contract dictionaries with keys:
                - player: Player name (str)
                - pos: Position (str)
                - cap_hit: 2025 cap hit in dollars (int)
                - years_left: Years remaining on contract (int)
                - dead_money: Dead money if cut (int)
        """
        self.beginResetModel()
        # Sort by cap hit (highest to lowest) by default
        self._contracts = sorted(contracts, key=lambda c: c["cap_hit"], reverse=True)
        self.endResetModel()

    def get_contract_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        """
        Get contract at given row index.

        Args:
            row: Row index

        Returns:
            Contract dictionary or None if invalid row
        """
        if 0 <= row < len(self._contracts):
            return self._contracts[row]
        return None

    def clear(self):
        """Clear all data from model."""
        self.beginResetModel()
        self._contracts = []
        self.endResetModel()

    @staticmethod
    def _format_currency(amount: int) -> str:
        """
        Format currency amount as "$XX.XM" or "$X.XM".

        Args:
            amount: Amount in dollars

        Returns:
            Formatted currency string
        """
        millions = amount / 1_000_000

        if millions >= 10:
            # Format as "$XX.XM" for amounts >= $10M
            return f"${millions:.1f}M"
        else:
            # Format as "$X.XM" for amounts < $10M
            return f"${millions:.1f}M"
