"""
Cap Summary Widget - Reusable widget showing team salary cap status.

Displays cap limit, total spending, available space (color-coded), and dead money.
Used across all offseason stage views.
"""

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class CapSummaryWidget(QWidget):
    """
    Reusable widget showing team salary cap status.

    Displays:
    - Salary Cap Limit (e.g., $255.4M)
    - Total Spending (e.g., $230.1M)
    - Available Space (color-coded green/yellow/red)
    - Dead Money (e.g., $5.2M)

    Color coding for available space:
    - Green: > 10% of cap available
    - Yellow/Amber: 5-10% available
    - Red: < 5% available or over cap
    """

    # Signal emitted when cap data changes (for external listeners)
    cap_changed = Signal(dict)

    # Default NFL salary cap for 2025 season
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        show_group_box: bool = True,
        title: str = "Salary Cap"
    ):
        """
        Initialize the cap summary widget.

        Args:
            parent: Parent widget
            show_group_box: If True, wrap in QGroupBox; if False, flat layout
            title: Title for the group box (if show_group_box=True)
        """
        super().__init__(parent)
        self._show_group_box = show_group_box
        self._title = title
        self._cap_data: Dict = {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        if self._show_group_box:
            group_box = QGroupBox(self._title)
            content_layout = QHBoxLayout(group_box)
            content_layout.setSpacing(30)
            main_layout.addWidget(group_box)
        else:
            content_layout = QHBoxLayout()
            content_layout.setSpacing(30)
            main_layout.addLayout(content_layout)

        # Cap Limit
        self._cap_limit_frame = self._create_stat_frame(
            "Cap Limit",
            "$255.4M"
        )
        content_layout.addWidget(self._cap_limit_frame)

        # Total Spending
        self._spending_frame = self._create_stat_frame(
            "Total Spending",
            "$0"
        )
        content_layout.addWidget(self._spending_frame)

        # Available Space (gets color coded)
        self._available_frame = self._create_stat_frame(
            "Available Space",
            "$0",
            value_color="#2E7D32"  # Default green
        )
        content_layout.addWidget(self._available_frame)

        # Dead Money
        self._dead_money_frame = self._create_stat_frame(
            "Dead Money",
            "$0",
            value_color="#C62828"  # Red for dead money
        )
        content_layout.addWidget(self._dead_money_frame)

        content_layout.addStretch()

    def _create_stat_frame(
        self,
        title: str,
        initial_value: str,
        value_color: str = "#000"
    ) -> QFrame:
        """
        Create a frame with title label and value label.

        Args:
            title: The label text above the value
            initial_value: Initial value to display
            value_color: Color for the value text

        Returns:
            QFrame containing the title and value labels
        """
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(title_label)

        # Value label
        value_label = QLabel(initial_value)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        value_label.setStyleSheet(f"color: {value_color};")
        layout.addWidget(value_label)

        # Store reference to value label for updates
        frame.value_label = value_label

        return frame

    def set_cap_data(self, cap_data: Dict):
        """
        Update display with cap data.

        Args:
            cap_data: Dictionary with keys:
                - salary_cap_limit: int (e.g., 255400000)
                - total_spending: int (e.g., 230100000)
                - available_space: int (e.g., 25300000)
                - dead_money: int (e.g., 5200000)
                - is_compliant: bool (optional)
        """
        self._cap_data = cap_data

        limit = cap_data.get("salary_cap_limit", self.DEFAULT_CAP_LIMIT)
        spending = cap_data.get("total_spending", 0)
        available = cap_data.get("available_space", 0)
        dead_money = cap_data.get("dead_money", 0)

        # Update labels with formatted values
        self._cap_limit_frame.value_label.setText(self._format_currency(limit))
        self._spending_frame.value_label.setText(self._format_currency(spending))
        self._available_frame.value_label.setText(self._format_currency(available))
        self._dead_money_frame.value_label.setText(self._format_currency(dead_money))

        # Color code available space based on cap health
        color = self._get_health_color(available, limit)
        self._available_frame.value_label.setStyleSheet(f"color: {color};")

        # Emit signal for external listeners
        self.cap_changed.emit(cap_data)

    def _format_currency(self, amount: int) -> str:
        """
        Format amount as currency string.

        Args:
            amount: Dollar amount

        Returns:
            Formatted string (e.g., "$25.3M" or "$1.2M")
        """
        if abs(amount) >= 1_000_000:
            # Show in millions with 1 decimal
            millions = amount / 1_000_000
            return f"${millions:,.1f}M"
        elif abs(amount) >= 1_000:
            # Show in thousands
            thousands = amount / 1_000
            return f"${thousands:,.0f}K"
        else:
            return f"${amount:,}"

    def _get_health_color(self, available: int, limit: int) -> str:
        """
        Get color based on cap health.

        Args:
            available: Available cap space
            limit: Salary cap limit

        Returns:
            Hex color code
        """
        if available < 0:
            # Over cap - red
            return "#C62828"

        if limit <= 0:
            return "#2E7D32"  # Default green if no limit

        pct = available / limit

        if pct > 0.10:
            # > 10% available - healthy (green)
            return "#2E7D32"
        elif pct > 0.05:
            # 5-10% available - caution (amber)
            return "#FF8F00"
        else:
            # < 5% available - tight (red)
            return "#C62828"

    def get_cap_data(self) -> Dict:
        """Get the current cap data."""
        return self._cap_data.copy()

    def get_available_space(self) -> int:
        """Get the current available cap space."""
        return self._cap_data.get("available_space", 0)

    def is_compliant(self) -> bool:
        """Check if team is cap compliant."""
        return self._cap_data.get("is_compliant", True)

    def clear(self):
        """Reset the widget to default values."""
        self.set_cap_data({
            "salary_cap_limit": self.DEFAULT_CAP_LIMIT,
            "total_spending": 0,
            "available_space": self.DEFAULT_CAP_LIMIT,
            "dead_money": 0,
            "is_compliant": True
        })