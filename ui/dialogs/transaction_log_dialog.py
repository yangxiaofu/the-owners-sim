"""
Transaction Log Dialog

Displays transaction activity logs for a specific team.
Used for debugging and verifying transaction system functionality.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class TransactionLogDialog(QDialog):
    """Dialog to display transaction activity logs for a team."""

    def __init__(self, team_id: int, team_name: str, transactions: list,
                 dynasty_id: str = None, parent=None):
        """
        Initialize the transaction log dialog.

        Args:
            team_id: Team ID (1-32)
            team_name: Full team name (e.g., "Detroit Lions")
            transactions: List of transaction dictionaries from TransactionAPI
            dynasty_id: Dynasty ID for context (optional)
            parent: Parent widget
        """
        super().__init__(parent)

        self.team_id = team_id
        self.team_name = team_name
        self.transactions = transactions
        self.dynasty_id = dynasty_id

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle(f"Transaction Log - {self.team_name}")
        self.setMinimumSize(900, 600)
        self.setModal(True)

        layout = QVBoxLayout()

        # Header section
        header_layout = QVBoxLayout()

        # Title
        title = QLabel(f"{self.team_name} - Transaction Activity Log")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        # Summary info
        summary = QLabel(self._get_summary_text())
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_font = QFont()
        summary_font.setPointSize(10)
        summary.setFont(summary_font)
        header_layout.addWidget(summary)

        layout.addLayout(header_layout)

        # Transaction log display
        log_group = QGroupBox("Transaction History")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setHtml(self._format_transactions())
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _get_summary_text(self) -> str:
        """Generate summary text for the header."""
        count = len(self.transactions)
        dynasty_info = f" (Dynasty: {self.dynasty_id})" if self.dynasty_id else ""

        if count == 0:
            return f"No transactions found{dynasty_info}"
        elif count == 1:
            return f"1 transaction found{dynasty_info}"
        else:
            return f"{count} transactions found{dynasty_info}"

    def _format_transactions(self) -> str:
        """Format transactions as HTML for display."""
        html = []

        # CSS styling
        html.append("""
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
                font-size: 12px;
            }
            th {
                background-color: #2c3e50;
                color: white;
                padding: 10px;
                text-align: left;
                font-weight: bold;
            }
            td {
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .type-draft { color: #27ae60; font-weight: bold; }
            .type-signing { color: #2980b9; font-weight: bold; }
            .type-release { color: #e74c3c; font-weight: bold; }
            .type-tag { color: #8e44ad; font-weight: bold; }
            .type-cut { color: #c0392b; font-weight: bold; }
            .type-trade { color: #f39c12; font-weight: bold; }
            .type-other { color: #7f8c8d; font-weight: bold; }
        </style>
        """)

        if not self.transactions:
            html.append("<p style='text-align: center; color: #7f8c8d; padding: 20px;'>")
            html.append("No transaction activity found for this team.")
            html.append("</p>")
            return "".join(html)

        # Table header
        html.append("<table>")
        html.append("<thead>")
        html.append("<tr>")
        html.append("<th>Date</th>")
        html.append("<th>Season</th>")
        html.append("<th>Type</th>")
        html.append("<th>Player</th>")
        html.append("<th>Position</th>")
        html.append("<th>Movement</th>")
        html.append("<th>Details</th>")
        html.append("</tr>")
        html.append("</thead>")
        html.append("<tbody>")

        # Sort transactions by date (most recent first)
        sorted_txns = sorted(
            self.transactions,
            key=lambda x: x.get('transaction_date', ''),
            reverse=True
        )

        # Limit to most recent 100 transactions
        for txn in sorted_txns[:100]:
            html.append("<tr>")

            # Date
            date = txn.get('transaction_date', 'N/A')
            html.append(f"<td>{date}</td>")

            # Season
            season = txn.get('season', 'N/A')
            html.append(f"<td>{season}</td>")

            # Type (with color coding)
            txn_type = txn.get('transaction_type', 'UNKNOWN')
            css_class = self._get_type_css_class(txn_type)
            formatted_type = self._format_transaction_type(txn_type)
            html.append(f"<td><span class='{css_class}'>{formatted_type}</span></td>")

            # Player
            player_name = txn.get('player_name', 'Unknown Player')
            html.append(f"<td>{player_name}</td>")

            # Position
            position = txn.get('position', '-')
            html.append(f"<td>{position}</td>")

            # Movement (From → To)
            movement = self._format_movement(txn)
            html.append(f"<td>{movement}</td>")

            # Details
            details = self._format_details(txn)
            html.append(f"<td>{details}</td>")

            html.append("</tr>")

        html.append("</tbody>")
        html.append("</table>")

        # Add note if there are more transactions
        if len(sorted_txns) > 100:
            html.append(f"<p style='text-align: center; color: #7f8c8d; padding: 10px;'>")
            html.append(f"Showing most recent 100 of {len(sorted_txns)} transactions")
            html.append("</p>")

        return "".join(html)

    def _get_type_css_class(self, txn_type: str) -> str:
        """Get CSS class for transaction type color coding."""
        if txn_type == 'DRAFT':
            return 'type-draft'
        elif txn_type in ('UFA_SIGNING', 'RFA_SIGNING', 'UDFA_SIGNING'):
            return 'type-signing'
        elif txn_type in ('RELEASE', 'WAIVER_CLAIM'):
            return 'type-release'
        elif txn_type in ('FRANCHISE_TAG', 'TRANSITION_TAG'):
            return 'type-tag'
        elif txn_type in ('ROSTER_CUT', 'PRACTICE_SQUAD_REMOVE'):
            return 'type-cut'
        elif txn_type == 'TRADE':
            return 'type-trade'
        else:
            return 'type-other'

    def _format_transaction_type(self, txn_type: str) -> str:
        """Format transaction type for display."""
        # Convert SNAKE_CASE to Title Case
        return txn_type.replace('_', ' ').title()

    def _format_movement(self, txn: dict) -> str:
        """Format team movement (From → To)."""
        from_team = txn.get('from_team_id')
        to_team = txn.get('to_team_id')

        if from_team and to_team:
            # Trade or transfer
            from_name = self._get_team_abbreviation(from_team)
            to_name = self._get_team_abbreviation(to_team)
            return f"{from_name} → {to_name}"
        elif to_team:
            # Signing or draft
            to_name = self._get_team_abbreviation(to_team)
            return f"→ {to_name}"
        elif from_team:
            # Release or cut
            from_name = self._get_team_abbreviation(from_team)
            return f"{from_name} →"
        else:
            return "-"

    def _get_team_abbreviation(self, team_id: int) -> str:
        """Get team abbreviation for display."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if hasattr(team, 'abbreviation') else team.name
        except:
            return f"Team{team_id}"

    def _format_details(self, txn: dict) -> str:
        """Format transaction details for display."""
        import json

        details = txn.get('details')
        if not details:
            return "-"

        # Parse JSON if it's a string
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                return str(details)

        if not isinstance(details, dict):
            return str(details)

        # Format based on transaction type
        txn_type = txn.get('transaction_type', '')

        if txn_type == 'DRAFT':
            round_num = details.get('round', '?')
            pick = details.get('pick', '?')
            return f"Round {round_num}, Pick {pick}"

        elif txn_type in ('UFA_SIGNING', 'RFA_SIGNING'):
            years = details.get('contract_years', '?')
            value = details.get('contract_value', 0)
            if value:
                value_m = value / 1_000_000
                return f"{years}yr, ${value_m:.1f}M"
            return f"{years} years"

        elif txn_type == 'RELEASE':
            cap_savings = details.get('cap_savings', 0)
            dead_money = details.get('dead_money', 0)
            if cap_savings or dead_money:
                savings_m = cap_savings / 1_000_000
                dead_m = dead_money / 1_000_000
                return f"Save: ${savings_m:.1f}M, Dead: ${dead_m:.1f}M"
            return "-"

        elif txn_type == 'TRADE':
            comp = details.get('compensation', '')
            return comp if comp else "Trade"

        elif txn_type in ('FRANCHISE_TAG', 'TRANSITION_TAG'):
            salary = details.get('tag_salary', 0)
            if salary:
                salary_m = salary / 1_000_000
                return f"${salary_m:.1f}M"
            return txn_type.replace('_', ' ').title()

        # Default: show first few key-value pairs
        items = []
        for key, value in list(details.items())[:3]:
            items.append(f"{key}: {value}")
        return ", ".join(items) if items else "-"
