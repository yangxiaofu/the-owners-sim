"""
Trade Proposal Widget - Display for trade proposals.

Part of Tollgate 4: Approval UI.

Displays: Trade partner, sending/receiving assets, value analysis.
"""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors, Typography, apply_table_style


class TradeProposalWidget(BaseProposalWidget):
    """Widget for displaying TRADE proposal details."""

    def _setup_ui(self) -> None:
        """Build the trade proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Trade Partner
        partner = self.details.get("trade_partner", "Unknown Team")
        partner_label = QLabel(f"Trade with: {partner}")
        partner_label.setFont(Typography.H4)
        layout.addWidget(partner_label)

        # Assets Exchange (side by side)
        exchange_layout = QHBoxLayout()

        # Sending (left side)
        sending_frame = self._create_assets_table(
            "You Send",
            self.details.get("sending", []),
            Colors.ERROR,
        )
        exchange_layout.addWidget(sending_frame)

        # Arrow separator
        arrow_label = QLabel("  ⟷  ")
        arrow_label.setFont(Typography.H2)
        arrow_label.setAlignment(Qt.AlignCenter)
        exchange_layout.addWidget(arrow_label)

        # Receiving (right side)
        receiving_frame = self._create_assets_table(
            "You Receive",
            self.details.get("receiving", []),
            Colors.SUCCESS,
        )
        exchange_layout.addWidget(receiving_frame)

        layout.addLayout(exchange_layout)

        # Value Analysis
        analysis_group, analysis_layout = self._create_info_group("Trade Analysis")

        value_diff = self.details.get("value_differential", 0)
        if value_diff > 0:
            value_text = f"+{value_diff} (favorable)"
            value_color = Colors.SUCCESS
        elif value_diff < 0:
            value_text = f"{value_diff} (unfavorable)"
            value_color = Colors.ERROR
        else:
            value_text = "0 (even)"
            value_color = Colors.MUTED

        self._create_stat_frame(
            analysis_layout,
            "Value Differential",
            value_text,
            value_color=value_color,
        )

        cap_impact = self.details.get("cap_impact", 0)
        if cap_impact > 0:
            cap_text = f"+{self._format_currency(cap_impact)}"
            cap_color = Colors.ERROR  # Spending more cap
        elif cap_impact < 0:
            cap_text = self._format_currency(cap_impact)
            cap_color = Colors.SUCCESS  # Saving cap
        else:
            cap_text = "$0"
            cap_color = Colors.MUTED

        self._create_stat_frame(
            analysis_layout,
            "Cap Impact",
            cap_text,
            value_color=cap_color,
        )

        analysis_layout.addStretch()
        layout.addWidget(analysis_group)

        layout.addStretch()

    def _create_assets_table(
        self, title: str, assets: list, accent_color: str
    ) -> QFrame:
        """Create a table showing trade assets."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ border: 2px solid {accent_color}; border-radius: 4px; }}"
        )
        frame_layout = QVBoxLayout(frame)

        # Title
        title_label = QLabel(title)
        title_label.setFont(Typography.H5)
        title_label.setStyleSheet(f"color: {accent_color}; border: none;")
        title_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title_label)

        if not assets:
            empty_label = QLabel("(Nothing)")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: {Colors.MUTED}; border: none;")
            frame_layout.addWidget(empty_label)
        else:
            # Assets table
            table = QTableWidget(len(assets), 3)
            table.setHorizontalHeaderLabels(["Type", "Name", "Value"])
            apply_table_style(table, row_height=28)

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

            for row, asset in enumerate(assets):
                asset_type = asset.get("type", "?").title()
                name = asset.get("name", "Unknown")
                value = asset.get("value", 0)

                type_item = QTableWidgetItem(asset_type)
                type_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, type_item)

                name_item = QTableWidgetItem(name)
                table.setItem(row, 1, name_item)

                value_item = QTableWidgetItem(str(value))
                value_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, value_item)

            table.setMaximumHeight(120)
            frame_layout.addWidget(table)

        return frame

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        partner = self.details.get("trade_partner", "Unknown")
        sending = self.details.get("sending", [])
        receiving = self.details.get("receiving", [])

        send_count = len(sending)
        recv_count = len(receiving)

        return f"Trade with {partner}: Send {send_count} asset(s), receive {recv_count}"