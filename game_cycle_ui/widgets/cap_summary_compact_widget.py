"""
Compact Salary Cap Summary Widget for Owner Review.

Shows cap metrics in a horizontal layout:
- Total Cap
- Cap Used
- Cap Room (with color coding)
"""

from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
)
from game_cycle_ui.theme import Typography, ESPN_THEME, TextColors


class CapSummaryCompactWidget(QFrame):
    """
    Compact salary cap summary for Owner Review right column.

    Shows: Total Cap, Cap Used, Cap Room
    Height: ~90px
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header
        header = QLabel("SALARY CAP")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        layout.addWidget(header)

        # Horizontal layout for 3 metrics
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)

        # Total Cap
        self.total_cap_label = QLabel("$0.0M")
        total_cap_container = self._create_metric("Total Cap", self.total_cap_label)
        metrics_layout.addWidget(total_cap_container)

        # Cap Used
        self.cap_used_label = QLabel("$0.0M")
        cap_used_container = self._create_metric("Used", self.cap_used_label)
        metrics_layout.addWidget(cap_used_container)

        # Cap Room
        self.cap_room_label = QLabel("$0.0M")
        cap_room_container = self._create_metric("Room", self.cap_room_label)
        metrics_layout.addWidget(cap_room_container)

        layout.addLayout(metrics_layout)

        # Styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            CapSummaryCompactWidget {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
            }}
        """)

    def _create_metric(self, label_text: str, value_label: QLabel) -> QWidget:
        """
        Create metric container with label + value.

        Args:
            label_text: The metric label (e.g., "Total Cap")
            value_label: The QLabel widget for the metric value

        Returns:
            Container widget with label and value
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(label_text)
        label.setFont(Typography.TINY)
        label.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        layout.addWidget(label)

        value_label.setFont(Typography.BODY)
        value_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        layout.addWidget(value_label)

        return container

    def set_data(self, cap_data: Dict[str, Any]):
        """
        Update cap metrics.

        Args:
            cap_data: {
                'total_cap': int,
                'cap_used': int,
                'cap_room': int
            }
        """
        total = cap_data.get('total_cap', 255_400_000)
        used = cap_data.get('cap_used', 0)
        room = cap_data.get('cap_room', 0)

        self.total_cap_label.setText(f"${total/1e6:.1f}M")
        self.cap_used_label.setText(f"${used/1e6:.1f}M")

        # Color code room (green if positive, red if negative)
        room_color = TextColors.SUCCESS if room > 0 else TextColors.ERROR
        self.cap_room_label.setText(f"${room/1e6:.1f}M")
        self.cap_room_label.setStyleSheet(f"color: {room_color};")
