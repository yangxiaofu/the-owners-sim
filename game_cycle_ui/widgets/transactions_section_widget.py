"""
Transactions Section Widget - Filterable list of season transactions.

Shows all transactions (trades, FA signings, draft picks, cuts) with:
- Filter tabs to show specific transaction types
- Card-based display with impact analysis
- Scrollable area for long transaction lists
"""

from typing import Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from game_cycle_ui.theme import Typography, ESPN_THEME, TextColors, Colors
from game_cycle_ui.widgets.base_widgets import ReadOnlyDataWidget


class TransactionsSectionWidget(ReadOnlyDataWidget):
    """
    Filterable list of season transactions.

    Shows: All transactions with filter tabs (Trades, FA, Draft, Cuts).
    Card-based display with impact analysis.
    """

    def __init__(self, parent=None):
        # Initialize data before base class calls _setup_ui()
        self._all_transactions = []
        super().__init__(parent)

    def _setup_ui(self):
        """Build the widget layout (called by base class)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Section header (using base class helper)
        self.header = self._create_section_header("TRANSACTIONS")
        layout.addWidget(self.header)

        # Filter tabs
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.all_btn = QPushButton("All")
        self.trades_btn = QPushButton("Trades")
        self.fa_btn = QPushButton("FA")
        self.draft_btn = QPushButton("Draft")
        self.cuts_btn = QPushButton("Cuts")

        # Style as tabs
        for btn in [self.all_btn, self.trades_btn, self.fa_btn, self.draft_btn, self.cuts_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.STAFF_TAB_BACKGROUND};
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 3px;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    background-color: {Colors.STAFF_TAB_SELECTED};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {Colors.STAFF_CARD_BACKGROUND};
                }}
            """)
            btn.clicked.connect(self._on_filter_changed)

        self.all_btn.setChecked(True)

        filter_row.addWidget(self.all_btn)
        filter_row.addWidget(self.trades_btn)
        filter_row.addWidget(self.fa_btn)
        filter_row.addWidget(self.draft_btn)
        filter_row.addWidget(self.cuts_btn)
        filter_row.addStretch()

        layout.addLayout(filter_row)

        # Transactions list (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(280)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.transactions_container = QWidget()
        self.transactions_layout = QVBoxLayout(self.transactions_container)
        self.transactions_layout.setContentsMargins(0, 0, 0, 0)
        self.transactions_layout.setSpacing(8)
        self.transactions_layout.addStretch()  # Push cards to top

        scroll.setWidget(self.transactions_container)
        layout.addWidget(scroll)

        # Note: Section styling is handled by ReadOnlyDataWidget base class

    def _on_filter_changed(self):
        """Update display when filter button clicked."""
        # Uncheck all buttons except sender
        for btn in [self.all_btn, self.trades_btn, self.fa_btn, self.draft_btn, self.cuts_btn]:
            if btn != self.sender():
                btn.setChecked(False)

        # Ensure sender is checked
        self.sender().setChecked(True)

        # Apply filter
        self._apply_filter()

    def _apply_filter(self):
        """Filter transactions based on selected button."""
        # Determine filter type
        if self.trades_btn.isChecked():
            filter_type = "trade"
        elif self.fa_btn.isChecked():
            filter_type = "fa_signing"
        elif self.draft_btn.isChecked():
            filter_type = "draft_pick"
        elif self.cuts_btn.isChecked():
            filter_type = "cut"
        else:
            filter_type = "all"

        # Clear existing cards (except stretch)
        while self.transactions_layout.count() > 1:
            child = self.transactions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add filtered cards
        for txn in self._all_transactions:
            if filter_type == "all" or txn.get('type') == filter_type:
                card = self._create_transaction_card(txn)
                self.transactions_layout.insertWidget(
                    self.transactions_layout.count() - 1,  # Before stretch
                    card
                )

    def _create_transaction_card(self, txn_data: Dict[str, Any]) -> QFrame:
        """
        Create card for single transaction.

        Args:
            txn_data: {
                'type': 'trade' | 'fa_signing' | 'draft_pick' | 'cut',
                'timing': 'Week 3' | 'March 15' | 'Round 1, Pick 18' | 'August 28',
                'acquired': str (or None),
                'sent': str (or None),
                'impact': str
            }
        """
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header: Type + Timing
        txn_type = txn_data.get('type', 'unknown').upper().replace('_', ' ')
        type_colors = {
            'trade': Colors.TRANSACTION_TRADE,
            'fa_signing': Colors.TRANSACTION_FA_SIGNING,
            'draft_pick': Colors.TRANSACTION_DRAFT_PICK,
            'cut': Colors.TRANSACTION_CUT
        }
        color = type_colors.get(txn_data.get('type'), '#bbb')

        timing = txn_data.get('timing', 'Unknown')
        header = QLabel(f"{txn_type} • {timing}")
        header.setFont(Typography.BODY)
        header.setStyleSheet(f"color: {color}; font-weight: bold;")
        layout.addWidget(header)

        # Acquired line (if applicable)
        acquired = txn_data.get('acquired')
        if acquired:
            acquired_label = QLabel(f"Acquired: {acquired}")
            acquired_label.setFont(Typography.SMALL)
            acquired_label.setStyleSheet("color: #ccc;")
            acquired_label.setWordWrap(True)
            layout.addWidget(acquired_label)

        # Sent line (if applicable)
        sent = txn_data.get('sent')
        if sent:
            sent_label = QLabel(f"Sent: {sent}")
            sent_label.setFont(Typography.SMALL)
            sent_label.setStyleSheet("color: #999;")
            sent_label.setWordWrap(True)
            layout.addWidget(sent_label)

        # Impact line
        impact = txn_data.get('impact', '')
        if impact:
            impact_label = QLabel(f"Impact: {impact}")
            impact_label.setFont(Typography.SMALL)
            impact_label.setStyleSheet("color: #888; font-style: italic;")
            impact_label.setWordWrap(True)
            layout.addWidget(impact_label)

        # Card background
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 4px;
            }}
        """)

        return card

    def set_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Populate with transaction data.

        Args:
            transactions: List of transaction dicts (see _create_transaction_card for format)
        """
        self._all_transactions = transactions

        # Update header count
        count = len(transactions)
        self.header.setText(f"TRANSACTIONS ({count} Total)")

        # Apply current filter
        self._apply_filter()
