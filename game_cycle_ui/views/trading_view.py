"""
Trading View - Shows trade history and team assets during offseason.

Read-only view showing AI GM trade activity and tradeable assets.
Future feature: Owner can direct GM to pursue specific trades.
"""

import json
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSplitter, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import (
    UITheme, TABLE_HEADER_STYLE, Typography, FontSizes, TextColors,
    apply_table_style, PRIMARY_BUTTON_STYLE, DANGER_BUTTON_STYLE
)
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class TradingView(QWidget):
    """
    View for the trading stage.

    Shows:
    - Summary panel with cap space and trade count
    - GM Trade Recommendations (Tollgate 8)
    - User's tradeable assets (players and picks)
    - Trade history (AI GM activity)
    """

    # Signals
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)
    proposal_approved = Signal(str)   # proposal_id - emitted when owner approves trade
    proposal_rejected = Signal(str)   # proposal_id - emitted when owner rejects trade

    # Default NFL salary cap (2024 value)
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._user_players: List[Dict] = []
        self._user_picks: List[Dict] = []
        self._trade_history: List[Dict] = []
        self._available_teams: List[Dict] = []
        self._gm_proposals: List[Dict] = []  # GM trade recommendations
        self._cap_limit: int = self.DEFAULT_CAP_LIMIT
        self._available_cap_space: int = 0
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout.

        Layout structure:
        ┌─────────────────────────────────────────┐
        │ Summary Panel (top)                     │
        ├──────────────────┬──────────────────────┤
        │ Left Column (60%)│ Right Column (40%)   │
        │ • Your Tradeable │ • GM Trade Recs      │
        │   Players Table  │                      │
        │                  │ • Recent Trades      │
        │ • Your Draft     │   (League-Wide)      │
        │   Picks Table    │                      │
        └──────────────────┴──────────────────────┘
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Main content splitter: Left (assets) / Right (GM recs + history)
        splitter = QSplitter(Qt.Horizontal)

        # Left: User's tradeable assets (players + picks)
        assets_widget = self._create_assets_panel()
        splitter.addWidget(assets_widget)

        # Right: GM recommendations + Trade history (stacked)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # GM Trade Recommendations (Tollgate 8)
        self._create_gm_proposals_section(right_layout)

        # Trade history
        history_widget = self._create_history_panel()
        right_layout.addWidget(history_widget, stretch=1)

        splitter.addWidget(right_panel)

        # Set initial sizes (60/40 split)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, stretch=1)

        # Instructions
        self._create_instructions(layout)

    def _create_summary_metric(self, title: str, attr_name: str,
                               initial_value: str = "0", color: str = None) -> QFrame:
        """Create a summary metric frame with title and value label.

        Args:
            title: Display title for the metric
            attr_name: Attribute name to store the value label on self
            initial_value: Initial display value
            color: Optional text color for the value

        Returns:
            QFrame containing the metric display
        """
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TextColors.ON_LIGHT_SECONDARY}; font-size: {FontSizes.CAPTION};"
        )
        layout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(Typography.H4)
        if color:
            value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        return frame

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and trade counts."""
        summary_group = QGroupBox("Trading Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Create all summary metrics using helper
        summary_layout.addWidget(
            self._create_summary_metric("Available Cap Space", "cap_space_label",
                                       "$0", TextColors.SUCCESS)
        )
        summary_layout.addWidget(
            self._create_summary_metric("Tradeable Players", "players_count_label")
        )
        summary_layout.addWidget(
            self._create_summary_metric("Tradeable Picks", "picks_count_label")
        )
        summary_layout.addWidget(
            self._create_summary_metric("Trades This Season", "trades_count_label",
                                       "0", TextColors.INFO)
        )
        summary_layout.addWidget(
            self._create_summary_metric("Trade Partners", "partners_count_label", "31")
        )

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_assets_panel(self) -> QWidget:
        """Create panel showing user's tradeable assets."""
        assets_widget = QWidget()
        assets_layout = QVBoxLayout(assets_widget)
        assets_layout.setContentsMargins(0, 0, 0, 0)

        # Players table
        players_group = QGroupBox("Your Tradeable Players")
        players_layout = QVBoxLayout(players_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(5)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Trade Value"
        ])

        # Apply standard table styling
        apply_table_style(self.players_table)

        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        players_layout.addWidget(self.players_table)
        assets_layout.addWidget(players_group, stretch=2)

        # Draft picks table
        picks_group = QGroupBox("Your Draft Picks")
        picks_layout = QVBoxLayout(picks_group)

        self.picks_table = QTableWidget()
        self.picks_table.setColumnCount(4)
        self.picks_table.setHorizontalHeaderLabels([
            "Year", "Round", "Original Team", "Trade Value"
        ])

        # Apply standard table styling
        apply_table_style(self.picks_table)

        header = self.picks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        picks_layout.addWidget(self.picks_table)
        assets_layout.addWidget(picks_group, stretch=1)

        return assets_widget

    def _create_history_panel(self) -> QWidget:
        """Create panel showing trade history."""
        history_group = QGroupBox("Recent Trades (League-Wide)")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Team 1", "Team 2", "Summary"
        ])

        # Apply standard table styling
        apply_table_style(self.history_table)

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        history_layout.addWidget(self.history_table)

        return history_group

    def _create_gm_proposals_section(self, parent_layout: QVBoxLayout):
        """Create GM Trade Recommendations section (Tollgate 8)."""
        self._gm_proposals_group = QGroupBox("GM TRADE RECOMMENDATIONS")
        self._gm_proposals_group.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #1976D2; }"
        )
        proposals_layout = QVBoxLayout(self._gm_proposals_group)
        proposals_layout.setContentsMargins(10, 10, 10, 10)
        proposals_layout.setSpacing(8)

        # Proposals table
        self._proposals_table = QTableWidget()
        self._proposals_table.setColumnCount(6)
        self._proposals_table.setHorizontalHeaderLabels([
            "Trade Partner", "We Send", "We Receive", "Value", "Confidence", "Action"
        ])

        # Apply standard table styling
        apply_table_style(self._proposals_table)

        # Configure column widths
        header = self._proposals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Partner
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # We Send
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # We Receive
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Value
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Confidence
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Action
        header.resizeSection(5, 150)

        # Set taller rows for buttons
        self._proposals_table.verticalHeader().setDefaultSectionSize(50)

        proposals_layout.addWidget(self._proposals_table)

        # GM reasoning display area
        self._gm_reasoning_label = QLabel()
        self._gm_reasoning_label.setWordWrap(True)
        self._gm_reasoning_label.setStyleSheet(
            f"background-color: #f5f5f5; padding: 10px; border-radius: 4px; "
            f"color: #333; font-size: {FontSizes.BODY}; font-style: italic;"
        )
        self._gm_reasoning_label.setMinimumHeight(60)
        self._gm_reasoning_label.hide()
        proposals_layout.addWidget(self._gm_reasoning_label)

        # Initially hidden
        self._gm_proposals_group.hide()

        parent_layout.addWidget(self._gm_proposals_group)

    def set_gm_proposals(self, proposals: List[Dict]) -> None:
        """
        Set GM trade proposals for display.

        Args:
            proposals: List of proposal dicts with:
                - proposal_id: str
                - details: dict with trade_partner, sending, receiving,
                           value_differential, cap_impact
                - gm_reasoning: str
                - confidence: float (0-1)
                - auto_approved: bool (optional)
        """
        self._gm_proposals = proposals

        if not proposals:
            self._gm_proposals_group.hide()
            return

        # Show the section
        self._gm_proposals_group.show()

        # Populate table
        self._proposals_table.setRowCount(len(proposals))

        for row, proposal in enumerate(proposals):
            self._populate_trade_proposal_row(row, proposal)

        # Show reasoning for first proposal by default
        if proposals:
            self._show_trade_reasoning(proposals[0])

    def _populate_trade_proposal_row(self, row: int, proposal: Dict):
        """Populate a single row in the proposals table."""
        details = proposal.get("details", {})
        proposal_id = proposal.get("proposal_id", "")
        auto_approved = proposal.get("auto_approved", False)

        # Trade partner
        partner = details.get("trade_partner", "Unknown")
        partner_item = QTableWidgetItem(partner)
        partner_item.setData(Qt.UserRole, proposal_id)
        self._proposals_table.setItem(row, 0, partner_item)

        # We Send - format as compact list
        sending = details.get("sending", [])
        send_text = self._format_assets(sending)
        send_item = QTableWidgetItem(send_text)
        send_item.setToolTip(send_text)  # Full text on hover
        self._proposals_table.setItem(row, 1, send_item)

        # We Receive
        receiving = details.get("receiving", [])
        recv_text = self._format_assets(receiving)
        recv_item = QTableWidgetItem(recv_text)
        recv_item.setToolTip(recv_text)
        self._proposals_table.setItem(row, 2, recv_item)

        # Value differential
        value_diff = details.get("value_differential", 0)
        if value_diff > 0:
            value_text = f"+{value_diff:,}"
            value_color = QColor("#2E7D32")  # Green - favorable
        elif value_diff < 0:
            value_text = f"{value_diff:,}"
            value_color = QColor("#C62828")  # Red - unfavorable
        else:
            value_text = "Even"
            value_color = QColor("#666")
        value_item = QTableWidgetItem(value_text)
        value_item.setTextAlignment(Qt.AlignCenter)
        value_item.setForeground(value_color)
        self._proposals_table.setItem(row, 3, value_item)

        # Confidence
        confidence = proposal.get("confidence", 0.5)
        conf_pct = int(confidence * 100)
        conf_item = QTableWidgetItem(f"{conf_pct}%")
        conf_item.setTextAlignment(Qt.AlignCenter)
        if conf_pct >= 80:
            conf_item.setForeground(QColor("#2E7D32"))
        elif conf_pct >= 60:
            conf_item.setForeground(QColor("#1976D2"))
        else:
            conf_item.setForeground(QColor("#F57C00"))
        self._proposals_table.setItem(row, 4, conf_item)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if auto_approved:
            # Already auto-approved in Trust GM mode
            approved_label = QLabel("Auto-Approved")
            approved_label.setStyleSheet(
                f"color: {TextColors.SUCCESS}; font-weight: bold;"
            )
            approved_label.setAlignment(Qt.AlignCenter)
            action_layout.addWidget(approved_label)
        else:
            approve_btn = QPushButton("Approve")
            approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
            approve_btn.setToolTip("Approve this trade recommendation")
            approve_btn.clicked.connect(
                lambda checked, pid=proposal_id: self._on_proposal_approved(pid)
            )
            action_layout.addWidget(approve_btn)

            reject_btn = QPushButton("Reject")
            reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
            reject_btn.setToolTip("Reject this trade recommendation")
            reject_btn.clicked.connect(
                lambda checked, pid=proposal_id: self._on_proposal_rejected(pid)
            )
            action_layout.addWidget(reject_btn)

        self._proposals_table.setCellWidget(row, 5, action_widget)

        # Connect row click to show reasoning
        self._proposals_table.cellClicked.connect(self._on_trade_row_clicked)

    def _format_assets(self, assets: List[Dict]) -> str:
        """Format list of trade assets as readable string."""
        parts = []
        for asset in assets:
            asset_type = asset.get("type", "")
            name = asset.get("name", "Unknown")
            if asset_type == "player":
                pos = asset.get("position", "")
                ovr = extract_overall_rating(asset, default=0)
                parts.append(f"{name} ({pos} {ovr})")
            elif asset_type == "pick":
                parts.append(name)
            else:
                parts.append(name)
        return ", ".join(parts) if parts else "Nothing"

    def _on_trade_row_clicked(self, row: int, column: int):
        """Handle click on proposal row to show reasoning."""
        if row < len(self._gm_proposals):
            self._show_trade_reasoning(self._gm_proposals[row])

    def _show_trade_reasoning(self, proposal: Dict):
        """Show GM reasoning for a trade proposal."""
        reasoning = proposal.get("gm_reasoning", "")
        if reasoning:
            self._gm_reasoning_label.setText(f"GM says: \"{reasoning}\"")
            self._gm_reasoning_label.show()
        else:
            self._gm_reasoning_label.hide()

    def _on_proposal_approved(self, proposal_id: str):
        """Handle approve button click."""
        self.proposal_approved.emit(proposal_id)

        # Remove from local list and refresh display
        self._gm_proposals = [
            p for p in self._gm_proposals
            if p.get("proposal_id") != proposal_id
        ]
        self.set_gm_proposals(self._gm_proposals)

    def _on_proposal_rejected(self, proposal_id: str):
        """Handle reject button click."""
        self.proposal_rejected.emit(proposal_id)

        # Remove from local list and refresh display
        self._gm_proposals = [
            p for p in self._gm_proposals
            if p.get("proposal_id") != proposal_id
        ]
        self.set_gm_proposals(self._gm_proposals)

    def clear_gm_proposals(self):
        """Clear all GM proposals."""
        self._gm_proposals = []
        self._proposals_table.setRowCount(0)
        self._gm_reasoning_label.hide()
        self._gm_proposals_group.hide()

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Your GM is actively evaluating trade opportunities with other teams. "
            "Click 'Process Trading' to advance and see completed trades."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY}; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_trading_data(self, preview_data: Dict[str, Any]):
        """
        Populate all trading data from preview.

        Args:
            preview_data: Dict from OffseasonHandler._get_trading_preview()
        """
        # Store data
        self._user_players = preview_data.get("user_players", [])
        self._user_picks = preview_data.get("user_picks", [])
        self._trade_history = preview_data.get("trade_history", [])
        self._available_teams = preview_data.get("available_teams", [])

        # Update summary
        self.players_count_label.setText(str(len(self._user_players)))
        self.picks_count_label.setText(str(len(self._user_picks)))
        self.trades_count_label.setText(str(preview_data.get("trade_count_this_season", 0)))
        self.partners_count_label.setText(str(len(self._available_teams)))

        # Populate tables
        self._populate_players_table()
        self._populate_picks_table()
        self._populate_history_table()

        # Set GM trade proposals if present (Tollgate 8)
        gm_proposals = preview_data.get("gm_proposals", [])
        self.set_gm_proposals(gm_proposals)

    def set_cap_data(self, cap_data: Dict[str, Any]):
        """
        Update the view with cap data.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, etc.
        """
        available = cap_data.get("available_space", 0)
        self._available_cap_space = available

        formatted = f"${available:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space
        if available < 0:
            self.cap_space_label.setStyleSheet(f"color: {TextColors.ERROR};")  # Red
        else:
            self.cap_space_label.setStyleSheet(f"color: {TextColors.SUCCESS};")  # Green

        if "salary_cap_limit" in cap_data:
            self._cap_limit = cap_data["salary_cap_limit"]

        # Emit cap validation
        is_over_cap = available < 0
        over_cap_amount = abs(available) if is_over_cap else 0
        self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

    def _populate_players_table(self):
        """Populate the players table with tradeable players."""
        self.players_table.setRowCount(len(self._user_players))

        for row, player in enumerate(self._user_players):
            # Player name
            name = player.get("name", f"Player {player.get('player_id', 0)}")
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, player.get("player_id"))
            self.players_table.setItem(row, 0, name_item)

            # Position - parse JSON list and get first position
            position_data = player.get("position", "")
            if isinstance(position_data, str) and position_data.startswith("["):
                # Parse JSON list
                try:
                    positions = json.loads(position_data)
                    position = positions[0] if positions else ""
                except (json.JSONDecodeError, IndexError, TypeError):
                    position = position_data
            elif isinstance(position_data, list):
                position = position_data[0] if position_data else ""
            else:
                position = position_data

            pos_item = QTableWidgetItem(get_position_abbreviation(position))
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.players_table.setItem(row, 1, pos_item)

            # Age
            age = player.get("age", 0)
            age_item = QTableWidgetItem(str(age))
            age_item.setTextAlignment(Qt.AlignCenter)
            if age >= 30:
                age_item.setForeground(QColor("#C62828"))  # Red for older players
            self.players_table.setItem(row, 2, age_item)

            # Overall
            overall = extract_overall_rating(player, default=0)
            ovr_item = QTableWidgetItem(str(overall))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            if overall >= 85:
                ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
            elif overall >= 75:
                ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
            self.players_table.setItem(row, 3, ovr_item)

            # Trade value
            trade_value = player.get("trade_value", 0)
            value_item = QTableWidgetItem(f"{trade_value:,}" if trade_value else "N/A")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.players_table.setItem(row, 4, value_item)

        if not self._user_players:
            self._show_empty_state(self.players_table, 5, "No tradeable players available")

    def _populate_picks_table(self):
        """Populate the picks table with tradeable draft picks."""
        self.picks_table.setRowCount(len(self._user_picks))

        for row, pick in enumerate(self._user_picks):
            # Year
            year_item = QTableWidgetItem(str(pick.get("season", "")))
            year_item.setTextAlignment(Qt.AlignCenter)
            year_item.setData(Qt.UserRole, pick.get("id"))
            self.picks_table.setItem(row, 0, year_item)

            # Round
            round_item = QTableWidgetItem(f"Round {pick.get('round', 0)}")
            round_item.setTextAlignment(Qt.AlignCenter)
            self.picks_table.setItem(row, 1, round_item)

            # Original team
            orig_team = pick.get("original_team_name", f"Team {pick.get('original_team_id', 0)}")
            team_item = QTableWidgetItem(orig_team)
            self.picks_table.setItem(row, 2, team_item)

            # Trade value
            trade_value = pick.get("trade_value", 0)
            value_item = QTableWidgetItem(f"{trade_value:,}" if trade_value else "N/A")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.picks_table.setItem(row, 3, value_item)

        if not self._user_picks:
            self._show_empty_state(self.picks_table, 4, "No draft picks available for trade")

    def _populate_history_table(self):
        """Populate the trade history table."""
        self.history_table.setRowCount(len(self._trade_history))

        for row, trade in enumerate(self._trade_history):
            # Date
            date_item = QTableWidgetItem(trade.get("trade_date", ""))
            date_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 0, date_item)

            # Team 1
            team1_name = trade.get("team1_name", f"Team {trade.get('team1_id', 0)}")
            team1_item = QTableWidgetItem(team1_name)
            self.history_table.setItem(row, 1, team1_item)

            # Team 2
            team2_name = trade.get("team2_name", f"Team {trade.get('team2_id', 0)}")
            team2_item = QTableWidgetItem(team2_name)
            self.history_table.setItem(row, 2, team2_item)

            # Summary (players/picks traded)
            summary = trade.get("summary", "Trade details unavailable")
            summary_item = QTableWidgetItem(summary)
            self.history_table.setItem(row, 3, summary_item)

        if not self._trade_history:
            self._show_empty_state(self.history_table, 4, "No trades have been made this season yet")

    def _show_empty_state(self, table: QTableWidget, col_count: int, message: str):
        """Show empty state message in a table.

        Args:
            table: The QTableWidget to show message in
            col_count: Number of columns to span
            message: Message to display
        """
        table.setRowCount(1)
        table.setSpan(0, 0, 1, col_count)

        message_item = QTableWidgetItem(message)
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor(TextColors.ON_LIGHT_SECONDARY))
        message_item.setFont(Typography.CAPTION)

        table.setItem(0, 0, message_item)

    def show_no_trading_message(self):
        """Show message when trading is not available."""
        self._show_empty_state(self.players_table, 5, "No tradeable players available")
        self._show_empty_state(self.picks_table, 4, "No draft picks available for trade")
        self._show_empty_state(self.history_table, 4, "No trades have been made this season yet")

    def get_user_players(self) -> List[Dict]:
        """Get the list of user's tradeable players."""
        return self._user_players

    def get_user_picks(self) -> List[Dict]:
        """Get the list of user's tradeable picks."""
        return self._user_picks

    def get_available_teams(self) -> List[Dict]:
        """Get the list of available trade partners."""
        return self._available_teams
