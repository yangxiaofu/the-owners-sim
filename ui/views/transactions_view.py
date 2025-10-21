"""
Transactions View for The Owner's Sim

Displays league-wide transaction history for all player movements.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from widgets.transaction_history_widget import TransactionHistoryWidget


class TransactionsView(QWidget):
    """
    Transaction history view.

    Displays complete transaction history for the current dynasty,
    showing all player movements (drafts, signings, releases, trades, etc.).
    """

    def __init__(
        self,
        parent=None,
        db_path: str = "data/database/nfl_simulation.db",
        dynasty_id: str = "default",
        season: int = 2025
    ):
        super().__init__(parent)
        self.main_window = parent
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title with dynasty info
        title_layout = QHBoxLayout()

        title = QLabel("Transaction History")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_layout.addWidget(title)

        # Dynasty info label
        dynasty_label = QLabel(
            f"Dynasty: {dynasty_id} | Season: {season}"
        )
        dynasty_label.setStyleSheet("font-size: 14px; color: #888;")
        dynasty_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(dynasty_label)

        layout.addLayout(title_layout)

        # Transaction history widget (main content)
        self.transaction_widget = TransactionHistoryWidget(
            self,
            db_path=db_path,
            dynasty_id=dynasty_id,
            season=season
        )
        layout.addWidget(self.transaction_widget)

    def refresh(self):
        """
        Refresh transaction history.

        Called when user switches to this tab or when data changes.
        """
        if hasattr(self, 'transaction_widget'):
            self.transaction_widget.refresh()
