"""
Table utilities for consistent table cell creation across UI views.

Eliminates the repeated 5-10 line pattern for creating table cells,
reducing code duplication and improving maintainability.
"""

from typing import Any, Optional
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class NumericTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem that sorts numerically instead of alphabetically.

    Standard QTableWidgetItem sorts as strings, so "9" > "80".
    This class enables proper numeric sorting in QTableWidget columns.

    Examples:
        >>> # Instead of QTableWidgetItem(str(age))
        >>> item = NumericTableWidgetItem(age)
        >>>
        >>> # With custom display text
        >>> item = NumericTableWidgetItem(rating, display_text="85 OVR")
    """

    def __init__(self, value: Any, display_text: str = None):
        """
        Args:
            value: The numeric value for sorting
            display_text: The text to display (if different from value)
        """
        super().__init__(display_text if display_text else str(value))
        self._sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            # Handle None/0 values
            self_val = self._sort_value if self._sort_value is not None else 0
            other_val = other._sort_value if other._sort_value is not None else 0
            return self_val < other_val
        return super().__lt__(other)


class TableCellHelper:
    """
    Helper class for creating and setting table cells with common formatting.

    Replaces the repeated pattern of:
        item = QTableWidgetItem(str(value))
        item.setTextAlignment(Qt.AlignCenter)
        item.setData(Qt.UserRole, data)
        item.setForeground(QColor(color))
        table.setItem(row, col, item)

    With a single method call:
        TableCellHelper.set_cell(table, row, col, value, align=Qt.AlignCenter, data=data, color=color)
    """

    @staticmethod
    def set_cell(
        table: QTableWidget,
        row: int,
        col: int,
        value: Any,
        align: Optional[Qt.AlignmentFlag] = None,
        color: Optional[str] = None,
        data: Optional[Any] = None,
        data_role: int = Qt.UserRole
    ) -> QTableWidgetItem:
        """
        Create and set a table cell with common formatting options.

        This eliminates the 5-10 line pattern repeated throughout UI code.

        Args:
            table: QTableWidget to set the cell in
            row: Row index
            col: Column index
            value: Cell value (will be converted to string)
            align: Optional alignment flag (e.g., Qt.AlignCenter)
            color: Optional foreground color hex string (e.g., "#2E7D32")
            data: Optional data to store in the cell (via Qt.UserRole by default)
            data_role: Qt data role to use (default: Qt.UserRole)

        Returns:
            The created QTableWidgetItem (for further customization if needed)

        Examples:
            >>> # Simple cell
            >>> TableCellHelper.set_cell(table, 0, 0, "Hello")

            >>> # Centered cell with data
            >>> TableCellHelper.set_cell(table, 0, 1, 42, align=Qt.AlignCenter, data=player_id)

            >>> # Colored cell
            >>> TableCellHelper.set_cell(table, 0, 2, 85, color="#2E7D32")

            >>> # All options
            >>> TableCellHelper.set_cell(
            ...     table, 0, 3, "Elite",
            ...     align=Qt.AlignCenter,
            ...     color="#2E7D32",
            ...     data={"rating": 85, "position": "QB"}
            ... )
        """
        item = QTableWidgetItem(str(value))

        if align:
            item.setTextAlignment(align)

        if color:
            item.setForeground(QColor(color))

        if data is not None:
            item.setData(data_role, data)

        table.setItem(row, col, item)
        return item
