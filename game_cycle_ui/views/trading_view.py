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
    QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import UITheme, TABLE_HEADER_STYLE
from constants.position_abbreviations import get_position_abbreviation


class TradingView(QWidget):
    """
    View for the trading stage (read-only).

    Shows:
    - Summary panel with cap space and trade count
    - User's tradeable assets (players and picks)
    - Trade history (AI GM activity)
    """

    # Signals
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)

    # Default NFL salary cap (2024 value)
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._user_players: List[Dict] = []
        self._user_picks: List[Dict] = []
        self._trade_history: List[Dict] = []
        self._available_teams: List[Dict] = []
        self._cap_limit: int = self.DEFAULT_CAP_LIMIT
        self._available_cap_space: int = 0
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Create splitter for assets and history
        splitter = QSplitter(Qt.Horizontal)

        # Left: User's tradeable assets
        assets_widget = self._create_assets_panel()
        splitter.addWidget(assets_widget)

        # Right: Trade history
        history_widget = self._create_history_panel()
        splitter.addWidget(history_widget)

        # Set initial sizes (60/40 split)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, stretch=1)

        # Instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and trade counts."""
        summary_group = QGroupBox("Trading Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Cap space
        cap_frame = QFrame()
        cap_layout = QVBoxLayout(cap_frame)
        cap_layout.setContentsMargins(0, 0, 0, 0)

        cap_title = QLabel("Available Cap Space")
        cap_title.setStyleSheet("color: #666; font-size: 11px;")
        cap_layout.addWidget(cap_title)

        self.cap_space_label = QLabel("$0")
        self.cap_space_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green
        cap_layout.addWidget(self.cap_space_label)

        summary_layout.addWidget(cap_frame)

        # Tradeable players count
        players_frame = QFrame()
        players_layout = QVBoxLayout(players_frame)
        players_layout.setContentsMargins(0, 0, 0, 0)

        players_title = QLabel("Tradeable Players")
        players_title.setStyleSheet("color: #666; font-size: 11px;")
        players_layout.addWidget(players_title)

        self.players_count_label = QLabel("0")
        self.players_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        players_layout.addWidget(self.players_count_label)

        summary_layout.addWidget(players_frame)

        # Draft picks count
        picks_frame = QFrame()
        picks_layout = QVBoxLayout(picks_frame)
        picks_layout.setContentsMargins(0, 0, 0, 0)

        picks_title = QLabel("Tradeable Picks")
        picks_title.setStyleSheet("color: #666; font-size: 11px;")
        picks_layout.addWidget(picks_title)

        self.picks_count_label = QLabel("0")
        self.picks_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        picks_layout.addWidget(self.picks_count_label)

        summary_layout.addWidget(picks_frame)

        # Trades this season
        trades_frame = QFrame()
        trades_layout = QVBoxLayout(trades_frame)
        trades_layout.setContentsMargins(0, 0, 0, 0)

        trades_title = QLabel("Trades This Season")
        trades_title.setStyleSheet("color: #666; font-size: 11px;")
        trades_layout.addWidget(trades_title)

        self.trades_count_label = QLabel("0")
        self.trades_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.trades_count_label.setStyleSheet("color: #1976D2;")  # Blue
        trades_layout.addWidget(self.trades_count_label)

        summary_layout.addWidget(trades_frame)

        # Available trade partners
        partners_frame = QFrame()
        partners_layout = QVBoxLayout(partners_frame)
        partners_layout.setContentsMargins(0, 0, 0, 0)

        partners_title = QLabel("Trade Partners")
        partners_title.setStyleSheet("color: #666; font-size: 11px;")
        partners_layout.addWidget(partners_title)

        self.partners_count_label = QLabel("31")
        self.partners_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        partners_layout.addWidget(self.partners_count_label)

        summary_layout.addWidget(partners_frame)

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

        header = self.players_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

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

        header = self.picks_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.picks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.picks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.picks_table.setAlternatingRowColors(True)
        self.picks_table.verticalHeader().setVisible(False)

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

        header = self.history_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)

        history_layout.addWidget(self.history_table)

        return history_group

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Your GM is actively evaluating trade opportunities with other teams. "
            "Click 'Process Trading' to advance and see completed trades."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
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
            self.cap_space_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green

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
            overall = player.get("overall_rating", player.get("overall", 0))
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
            self._show_no_players_message()

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
            self._show_no_picks_message()

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
            self._show_no_history_message()

    def _show_no_players_message(self):
        """Show message when there are no tradeable players."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 5)

        message_item = QTableWidgetItem("No tradeable players available")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 11, QFont.Normal, True))

        self.players_table.setItem(0, 0, message_item)

    def _show_no_picks_message(self):
        """Show message when there are no tradeable picks."""
        self.picks_table.setRowCount(1)
        self.picks_table.setSpan(0, 0, 1, 4)

        message_item = QTableWidgetItem("No draft picks available for trade")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 11, QFont.Normal, True))

        self.picks_table.setItem(0, 0, message_item)

    def _show_no_history_message(self):
        """Show message when there are no trades this season."""
        self.history_table.setRowCount(1)
        self.history_table.setSpan(0, 0, 1, 4)

        message_item = QTableWidgetItem("No trades have been made this season yet")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 11, QFont.Normal, True))

        self.history_table.setItem(0, 0, message_item)

    def show_no_trading_message(self):
        """Show message when trading is not available."""
        self._show_no_players_message()
        self._show_no_picks_message()
        self._show_no_history_message()

    def get_user_players(self) -> List[Dict]:
        """Get the list of user's tradeable players."""
        return self._user_players

    def get_user_picks(self) -> List[Dict]:
        """Get the list of user's tradeable picks."""
        return self._user_picks

    def get_available_teams(self) -> List[Dict]:
        """Get the list of available trade partners."""
        return self._available_teams
