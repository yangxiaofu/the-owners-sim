"""
Wave Results Dialog - Shows FA wave completion results.

Displays successful signings and lost bids after wave resolution.
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class WaveResultsDialog(QDialog):
    """
    Dialog showing Free Agency wave resolution results.

    Displays:
    - Players successfully signed by user
    - Bids user lost (players signed elsewhere)
    - Summary statistics
    """

    def __init__(self, result_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.result_data = result_data
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Wave Results")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        self._create_header(layout)

        # Successful Signings Section
        self._create_signings_section(layout)

        # Lost Bids Section
        self._create_lost_bids_section(layout)

        # Summary Footer
        self._create_summary(layout)

        # Close Button
        self._create_buttons(layout)

    def _create_header(self, parent_layout):
        """Wave completion header."""
        header = QLabel("Wave Complete!")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(header)

        wave_name = self.result_data.get("wave_name", "Unknown Wave")
        subtitle = QLabel(f"{wave_name} - All offers have been resolved")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 13px;")
        parent_layout.addWidget(subtitle)

    def _create_signings_section(self, parent_layout):
        """Show players user successfully signed."""
        user_signings = self.result_data.get("user_signings", [])

        section_label = QLabel(f"✅ Your Signings ({len(user_signings)})")
        section_label.setFont(QFont("Arial", 14, QFont.Bold))
        section_label.setStyleSheet("color: #2E7D32;")  # Green
        parent_layout.addWidget(section_label)

        if user_signings:
            table = self._create_player_table(user_signings)
            parent_layout.addWidget(table)
        else:
            no_signings = QLabel("No players signed this wave.")
            no_signings.setStyleSheet("color: #999; font-style: italic; padding: 10px;")
            parent_layout.addWidget(no_signings)

    def _create_lost_bids_section(self, parent_layout):
        """Show bids user lost (players signed elsewhere)."""
        lost_bids = self.result_data.get("user_lost_bids", [])

        if not lost_bids:
            return  # Don't show section if no lost bids

        section_label = QLabel(f"❌ Lost Bids ({len(lost_bids)})")
        section_label.setFont(QFont("Arial", 14, QFont.Bold))
        section_label.setStyleSheet("color: #C62828;")  # Red
        parent_layout.addWidget(section_label)

        table = self._create_player_table(lost_bids, show_team=True)
        parent_layout.addWidget(table)

    def _create_player_table(self, players: List[Dict], show_team: bool = False):
        """Create table showing player details."""
        columns = ["Player", "Contract"]
        if show_team:
            columns.append("Signed With")

        table = QTableWidget(len(players), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)

        for row, player in enumerate(players):
            # Player name
            name_item = QTableWidgetItem(player.get("player_name", "Unknown"))
            table.setItem(row, 0, name_item)

            # Contract
            aav = player.get("aav", 0)
            years = player.get("years", 0)
            contract_text = f"{years}yr / ${aav:,}"
            contract_item = QTableWidgetItem(contract_text)
            contract_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 1, contract_item)

            # Signed With (for lost bids)
            if show_team:
                team_item = QTableWidgetItem(player.get("team_name", "Unknown"))
                team_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, team_item)

        # Auto-resize columns
        table.resizeColumnsToContents()
        table.setMaximumHeight(200)

        return table

    def _create_summary(self, parent_layout):
        """Summary statistics."""
        user_signings = self.result_data.get("user_signings", [])
        lost_bids = self.result_data.get("user_lost_bids", [])
        pending = self.result_data.get("pending_offers", 0)

        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.StyledPanel)
        summary_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")

        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 8, 10, 8)

        # Summary text
        summary_text = (
            f"<b>Summary:</b> "
            f"{len(user_signings)} signed • "
            f"{len(lost_bids)} lost • "
            f"{pending} pending offers"
        )
        summary_label = QLabel(summary_text)
        summary_layout.addWidget(summary_label)

        parent_layout.addWidget(summary_frame)

    def _create_buttons(self, parent_layout):
        """Close button."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Continue")
        close_btn.setMinimumWidth(120)
        close_btn.setMinimumHeight(36)
        close_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 8px 16px; font-size: 13px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        button_layout.addStretch()
        parent_layout.addLayout(button_layout)