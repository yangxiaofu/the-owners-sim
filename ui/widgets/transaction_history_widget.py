"""
Transaction History Widget for The Owner's Sim

Displays 500 most recent player transactions sorted by date.
Integrated with TransactionAPI for real database data.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PySide6.QtCore import Qt
from datetime import datetime
from typing import List, Dict, Any, Optional


class TransactionHistoryWidget(QWidget):
    """
    Transaction history widget displaying recent player transactions.

    Shows the 500 most recent transactions across the league with:
    - Date (formatted as "Mar 15, 2025")
    - Transaction type (friendly names)
    - Player name and position
    - From team (full team name)
    - To team (full team name)
    - Transaction details (formatted JSON)

    Integrated with TransactionAPI for real database data.
    """

    def __init__(
        self,
        parent=None,
        db_path: str = "data/database/nfl_simulation.db",
        dynasty_id: str = "default",
        season: int = 2025
    ):
        super().__init__(parent)

        # Store parameters
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize TransactionAPI (follows StatsLeadersWidget pattern)
        import sys
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from persistence.transaction_api import TransactionAPI
        self.transaction_api = TransactionAPI(db_path)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Transaction table
        self.table = self._create_transaction_table()
        layout.addWidget(self.table)

        # Status label
        self.status_label = QLabel("Loading transactions...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Load initial data
        self.load_transactions()

    def _create_header(self) -> QHBoxLayout:
        """Create header with title and refresh button."""
        header = QHBoxLayout()

        # Title
        title = QLabel("Recent Transactions")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self.load_transactions)
        header.addWidget(refresh_btn)

        return header

    def _create_transaction_table(self) -> QTableWidget:
        """Create transaction table with 6 columns."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Date", "Type", "Player", "From Team", "To Team", "Details"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)

        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Player
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # From Team
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # To Team
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Details

        return table

    def load_transactions(self):
        """Load 500 most recent transactions from database."""
        try:
            # Get transactions from API (sorted by date DESC)
            transactions = self.transaction_api.get_recent_transactions(
                dynasty_id=self.dynasty_id,
                limit=500
            )

            # Populate table
            self._populate_table(transactions)

            # Update status
            if len(transactions) > 0:
                self.status_label.setText(
                    f"Showing {len(transactions)} most recent transactions"
                )
            else:
                self.status_label.setText("No transactions found")

        except Exception as e:
            print(f"Error loading transactions: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error loading transactions: {str(e)}")

    def _populate_table(self, transactions: List[Dict[str, Any]]):
        """
        Populate table with transaction data.

        Args:
            transactions: List of transaction dicts from TransactionAPI
        """
        # Disable sorting while populating
        self.table.setSortingEnabled(False)

        # Set row count
        self.table.setRowCount(len(transactions))

        # Populate rows
        for row, txn in enumerate(transactions):
            # Column 0: Date (formatted as "Mar 15, 2025")
            date_str = self._format_date(txn['transaction_date'])
            self.table.setItem(row, 0, self._create_item(date_str))

            # Column 1: Type (friendly name)
            type_str = self._format_transaction_type(txn['transaction_type'])
            self.table.setItem(row, 1, self._create_item(type_str))

            # Column 2: Player (name + position)
            player_str = self._format_player(
                txn['player_name'],
                txn.get('position')
            )
            self.table.setItem(row, 2, self._create_item(player_str))

            # Column 3: From Team (full team name)
            from_team_str = self._get_team_name(txn.get('from_team_id'))
            self.table.setItem(row, 3, self._create_item(from_team_str))

            # Column 4: To Team (full team name)
            to_team_str = self._get_team_name(txn.get('to_team_id'))
            self.table.setItem(row, 4, self._create_item(to_team_str))

            # Column 5: Details (formatted JSON)
            details_str = self._format_details(
                txn.get('details'),
                txn['transaction_type']
            )
            self.table.setItem(row, 5, self._create_item(details_str))

        # Re-enable sorting
        self.table.setSortingEnabled(True)

    def _create_item(self, text: str) -> QTableWidgetItem:
        """
        Create non-editable, center-aligned table item.

        Args:
            text: Item text

        Returns:
            QTableWidgetItem configured for display
        """
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _format_date(self, date_str: str) -> str:
        """
        Format date string as "Mar 15, 2025".

        Args:
            date_str: ISO format date string (e.g., "2025-03-15")

        Returns:
            Formatted date string
        """
        try:
            # Parse ISO date
            dt = datetime.fromisoformat(date_str)
            # Format as "Mar 15, 2025"
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            return date_str

    def _format_transaction_type(self, type_code: str) -> str:
        """
        Convert transaction type code to friendly name.

        Args:
            type_code: Transaction type code (e.g., "UFA_SIGNING")

        Returns:
            Friendly display name (e.g., "UFA Signing")
        """
        type_map = {
            'DRAFT': 'Draft Pick',
            'UDFA_SIGNING': 'UDFA Signing',
            'UFA_SIGNING': 'UFA Signing',
            'RFA_SIGNING': 'RFA Signing',
            'RELEASE': 'Released',
            'WAIVER_CLAIM': 'Waiver Claim',
            'TRADE': 'Traded',
            'ROSTER_CUT': 'Roster Cut',
            'PRACTICE_SQUAD_ADD': 'Practice Squad Added',
            'PRACTICE_SQUAD_REMOVE': 'Practice Squad Removed',
            'PRACTICE_SQUAD_ELEVATE': 'Practice Squad Elevated',
            'FRANCHISE_TAG': 'Franchise Tagged',
            'TRANSITION_TAG': 'Transition Tagged',
            'RESTRUCTURE': 'Contract Restructured'
        }
        return type_map.get(type_code, type_code)

    def _format_player(
        self,
        player_name: str,
        position: Optional[str]
    ) -> str:
        """
        Format player display string.

        Args:
            player_name: Player name
            position: Player position (optional)

        Returns:
            Formatted string (e.g., "Kirk Cousins (QB)")
        """
        if position:
            return f"{player_name} ({position})"
        return player_name

    def _get_team_name(self, team_id: Optional[int]) -> str:
        """
        Convert team ID to full team name.

        Args:
            team_id: Team ID (1-32) or None

        Returns:
            Full team name or "Free Agent" if None
        """
        if team_id is None:
            return "Free Agent"

        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.full_name if team else f"Team {team_id}"
        except Exception as e:
            print(f"Error getting team name for ID {team_id}: {e}")
            return f"Team {team_id}"

    def _format_details(
        self,
        details: Any,
        transaction_type: str
    ) -> str:
        """
        Format transaction details JSON for display.

        Args:
            details: Details dict or JSON string
            transaction_type: Transaction type code

        Returns:
            Formatted details string
        """
        # Handle None/empty details
        if not details:
            return "-"

        # Parse JSON if string
        if isinstance(details, str):
            try:
                import json
                details = json.loads(details)
            except (json.JSONDecodeError, ValueError):
                return details

        # Handle dict details not being a dict
        if not isinstance(details, dict):
            return str(details)

        # Format based on transaction type
        if transaction_type == 'DRAFT':
            # Example: "Round 1, Pick 1 (USC)"
            round_num = details.get('round', '?')
            pick_num = details.get('pick', '?')
            college = details.get('college', '')
            if college:
                return f"Round {round_num}, Pick {pick_num} ({college})"
            return f"Round {round_num}, Pick {pick_num}"

        elif transaction_type in ['UFA_SIGNING', 'RFA_SIGNING']:
            # Example: "4 years, $180M ($100M guaranteed)"
            years = details.get('contract_years', details.get('years', '?'))
            value = details.get('contract_value', details.get('value', 0))
            guaranteed = details.get('guaranteed', 0)

            # Format currency
            value_str = self._format_currency(value)
            if guaranteed > 0:
                guaranteed_str = self._format_currency(guaranteed)
                return f"{years} years, {value_str} ({guaranteed_str} guaranteed)"
            return f"{years} years, {value_str}"

        elif transaction_type == 'RELEASE':
            # Example: "$5M savings, $85M dead money"
            savings = details.get('cap_savings', 0)
            dead = details.get('dead_money', 0)
            savings_str = self._format_currency(savings)
            dead_str = self._format_currency(dead)
            return f"{savings_str} savings, {dead_str} dead money"

        elif transaction_type == 'WAIVER_CLAIM':
            # Example: "Waiver priority: 3"
            priority = details.get('waiver_priority', '?')
            return f"Waiver priority: {priority}"

        elif transaction_type in ['FRANCHISE_TAG', 'TRANSITION_TAG']:
            # Example: "Tag salary: $19.7M"
            salary = details.get('tag_salary', details.get('salary', 0))
            salary_str = self._format_currency(salary)
            return f"Tag salary: {salary_str}"

        # Default: Show all key-value pairs
        return ", ".join(f"{k}={v}" for k, v in details.items())

    def _format_currency(self, amount: int) -> str:
        """
        Format currency amount.

        Args:
            amount: Amount in dollars

        Returns:
            Formatted string (e.g., "$180M", "$5.5M", "$500K")
        """
        if amount >= 1_000_000:
            # Millions
            millions = amount / 1_000_000
            if millions >= 100:
                return f"${millions:.0f}M"
            return f"${millions:.1f}M"
        elif amount >= 1_000:
            # Thousands
            thousands = amount / 1_000
            return f"${thousands:.0f}K"
        else:
            return f"${amount:,}"

    def refresh(self):
        """
        Reload transactions from database.

        Called when games are played or user clicks refresh button.
        """
        self.load_transactions()
