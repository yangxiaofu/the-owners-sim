"""
Transaction History Widget for The Owner's Sim

Displays 500 most recent player transactions sorted by date.
Integrated with TransactionAPI for real database data.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QComboBox
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

    # Filter name to transaction type mapping
    FILTER_MAP = {
        "All Transactions": None,
        "Draft Picks": "DRAFT",
        "Free Agent Signings": "UFA_SIGNING",
        "Franchise Tags": "FRANCHISE_TAG",
        "Releases": "RELEASE",
        "Roster Cuts": "ROSTER_CUT",
        "Waiver Claims": "WAIVER_CLAIM",
    }

    def __init__(
        self,
        parent=None,
        db_path: str = "data/database/nfl_simulation.db",
        dynasty_id: str = "default"
    ):
        super().__init__(parent)

        # Store parameters
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        # Note: season property now proxied from parent

        # Flag to block signals during initialization
        self._initializing = True

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

        # Done initializing
        self._initializing = False

        # Load initial data
        self.load_transactions()

    @property
    def season(self) -> int:
        """Current season year (proxied from parent)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        return 2025  # Fallback for testing/standalone usage

    def _create_header(self) -> QHBoxLayout:
        """Create header with title, filter dropdowns, and refresh button."""
        header = QHBoxLayout()

        # Title
        title = QLabel("Recent Transactions")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Season filter dropdown
        season_label = QLabel("Season:")
        season_label.setStyleSheet("font-size: 12px;")
        header.addWidget(season_label)

        self.season_combo = QComboBox()
        self.season_combo.addItem("All Seasons", None)
        # Add seasons dynamically (next year for offseason transactions, back to first year)
        current_season = self.season
        # Include next season since offseason transactions are logged for the upcoming season
        for year in range(current_season + 1, 2024, -1):  # Next season back to first season
            self.season_combo.addItem(str(year), year)
        self.season_combo.setMinimumWidth(100)
        self.season_combo.currentIndexChanged.connect(self._on_filter_changed)
        header.addWidget(self.season_combo)

        # Default to next season (where offseason transactions are logged)
        default_season = current_season + 1
        index = self.season_combo.findData(default_season)
        if index >= 0:
            self.season_combo.setCurrentIndex(index)

        # Team filter dropdown
        team_label = QLabel("Team:")
        team_label.setStyleSheet("font-size: 12px;")
        header.addWidget(team_label)

        self.team_combo = QComboBox()
        self.team_combo.addItem("All Teams", None)
        self._populate_team_dropdown()
        self.team_combo.setMinimumWidth(150)
        self.team_combo.currentIndexChanged.connect(self._on_filter_changed)
        header.addWidget(self.team_combo)

        # Type filter dropdown
        filter_label = QLabel("Type:")
        filter_label.setStyleSheet("font-size: 12px;")
        header.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(list(self.FILTER_MAP.keys()))
        self.filter_combo.setMinimumWidth(150)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header.addWidget(self.filter_combo)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self.load_transactions)
        header.addWidget(refresh_btn)

        return header

    def _populate_team_dropdown(self):
        """Populate team dropdown with all 32 teams."""
        try:
            from team_management.teams.team_loader import TeamDataLoader
            team_loader = TeamDataLoader()
            all_teams = team_loader.get_all_teams()
            for team in sorted(all_teams, key=lambda t: t.full_name):
                self.team_combo.addItem(team.full_name, team.team_id)
        except Exception as e:
            print(f"Error loading teams for filter: {e}")
            # Fallback: add generic team entries
            for i in range(1, 33):
                self.team_combo.addItem(f"Team {i}", i)

    def _on_filter_changed(self, *args):
        """Handle filter dropdown change."""
        # Skip during initialization (table/status_label don't exist yet)
        if self._initializing:
            return
        self.load_transactions()

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
        """Load transactions from database with combined filters."""
        try:
            # Get current filter values
            filter_text = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else "All Transactions"
            filter_type = self.FILTER_MAP.get(filter_text, None)
            season = self.season_combo.currentData() if hasattr(self, 'season_combo') else None
            team_id = self.team_combo.currentData() if hasattr(self, 'team_combo') else None

            # Build query based on filters
            if team_id:
                # Team filter - use get_team_transactions (includes season support)
                transactions = self.transaction_api.get_team_transactions(
                    team_id=team_id,
                    dynasty_id=self.dynasty_id,
                    season=season
                )
                # Apply type filter in memory if needed
                if filter_type:
                    transactions = [t for t in transactions if t['transaction_type'] == filter_type]
            elif filter_type:
                # Type filter with optional season
                transactions = self.transaction_api.get_transactions_by_type(
                    dynasty_id=self.dynasty_id,
                    transaction_type=filter_type,
                    season=season,
                    limit=500
                )
            elif season:
                # Season only - get all and filter in memory
                transactions = self.transaction_api.get_recent_transactions(
                    dynasty_id=self.dynasty_id,
                    limit=500
                )
                transactions = [t for t in transactions if t.get('season') == season]
            else:
                # No filters
                transactions = self.transaction_api.get_recent_transactions(
                    dynasty_id=self.dynasty_id,
                    limit=500
                )

            # Populate table
            self._populate_table(transactions)

            # Update status with active filters
            self._update_status_label(len(transactions), season, team_id, filter_type)

        except Exception as e:
            print(f"Error loading transactions: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error loading transactions: {str(e)}")

    def _update_status_label(self, count: int, season: Optional[int], team_id: Optional[int], filter_type: Optional[str]):
        """Update status label to show active filters."""
        # Build filter description
        filter_parts = []
        if season:
            filter_parts.append(str(season))
        if team_id:
            team_name = self._get_team_name(team_id)
            filter_parts.append(team_name)
        if filter_type:
            # Get friendly name from FILTER_MAP
            friendly_name = next((k for k, v in self.FILTER_MAP.items() if v == filter_type), filter_type)
            filter_parts.append(friendly_name)

        filter_label = f" ({', '.join(filter_parts)})" if filter_parts else ""

        if count > 0:
            self.status_label.setText(f"Showing {count} transactions{filter_label}")
        else:
            self.status_label.setText(f"No transactions found{filter_label}")

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

            # Column 3: From Team (full team name, context-aware for drafts)
            from_team_str = self._get_from_team_name(
                txn.get('from_team_id'), txn['transaction_type']
            )
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

    def _get_from_team_name(
        self,
        team_id: Optional[int],
        transaction_type: str
    ) -> str:
        """
        Convert team ID to display name, context-aware for "from" column.

        For null team_id, returns context-appropriate source:
        - DRAFT: "Draft" (not "Free Agent")
        - UDFA_SIGNING: "Undrafted"
        - WAIVER_CLAIM: "Waivers"
        - Others: "Free Agent"

        Args:
            team_id: Team ID (1-32) or None
            transaction_type: Transaction type code

        Returns:
            Full team name or context-aware source label
        """
        if team_id is None:
            # Context-aware display for null from_team_id
            if transaction_type == 'DRAFT':
                return "Draft"
            elif transaction_type == 'UDFA_SIGNING':
                return "Undrafted"
            elif transaction_type == 'WAIVER_CLAIM':
                return "Waivers"
            else:
                return "Free Agent"

        # For non-null team_id, use standard lookup
        return self._get_team_name(team_id)

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

        elif transaction_type == 'ROSTER_CUT':
            # Example: "$5M dead money, $3M savings" or "$2M dead (+ $3M next yr), $8M savings (June 1)"
            dead = details.get('dead_money', 0)
            dead_next_yr = details.get('dead_money_next_year', 0)
            savings = details.get('cap_savings', 0)
            use_june_1 = details.get('use_june_1', False)

            dead_str = self._format_currency(dead)
            savings_str = self._format_currency(savings)

            if use_june_1 and dead_next_yr > 0:
                # June 1 cut with split dead money
                next_yr_str = self._format_currency(dead_next_yr)
                return f"{dead_str} dead (+ {next_yr_str} next yr), {savings_str} savings (June 1)"
            else:
                # Regular cut
                return f"{dead_str} dead money, {savings_str} savings"

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
