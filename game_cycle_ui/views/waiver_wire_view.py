"""
Waiver Wire View - Shows players on waivers for claiming.

Allows the user to view cut players and submit waiver claims.
Claims are processed by priority (worst record = highest priority).
"""

from typing import Dict, List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush


class WaiverWireView(QWidget):
    """
    View for the waiver wire stage.

    Shows a table of players available on waivers with claim buttons.
    Users can submit claims which are processed by waiver priority.
    """

    # Signals
    claim_submitted = Signal(int)  # player_id
    claim_cancelled = Signal(int)  # player_id
    process_waivers_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._waiver_players: List[Dict] = []
        self._filtered_players: List[Dict] = []
        self._user_claims: Set[int] = set()
        self._user_priority: int = 16  # Default to middle priority
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Filter panel
        self._create_filter_panel(layout)

        # Main table of waiver players
        self._create_players_table(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing waiver info."""
        summary_group = QGroupBox("Waiver Wire Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Available players
        available_frame = QFrame()
        available_layout = QVBoxLayout(available_frame)
        available_layout.setContentsMargins(0, 0, 0, 0)

        available_title = QLabel("Players on Waivers")
        available_title.setStyleSheet("color: #666; font-size: 11px;")
        available_layout.addWidget(available_title)

        self.available_count_label = QLabel("0")
        self.available_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        available_layout.addWidget(self.available_count_label)

        summary_layout.addWidget(available_frame)

        # Your waiver priority
        priority_frame = QFrame()
        priority_layout = QVBoxLayout(priority_frame)
        priority_layout.setContentsMargins(0, 0, 0, 0)

        priority_title = QLabel("Your Waiver Priority")
        priority_title.setStyleSheet("color: #666; font-size: 11px;")
        priority_layout.addWidget(priority_title)

        self.priority_label = QLabel("#16")
        self.priority_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.priority_label.setStyleSheet("color: #1976D2;")  # Blue
        priority_layout.addWidget(self.priority_label)

        summary_layout.addWidget(priority_frame)

        # Your pending claims
        claims_frame = QFrame()
        claims_layout = QVBoxLayout(claims_frame)
        claims_layout.setContentsMargins(0, 0, 0, 0)

        claims_title = QLabel("Your Claims")
        claims_title.setStyleSheet("color: #666; font-size: 11px;")
        claims_layout.addWidget(claims_title)

        self.claims_count_label = QLabel("0")
        self.claims_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.claims_count_label.setStyleSheet("color: #FF6F00;")  # Orange
        claims_layout.addWidget(self.claims_count_label)

        summary_layout.addWidget(claims_frame)

        # Priority explanation
        priority_info_frame = QFrame()
        priority_info_layout = QVBoxLayout(priority_info_frame)
        priority_info_layout.setContentsMargins(0, 0, 0, 0)

        priority_info_title = QLabel("Priority Info")
        priority_info_title.setStyleSheet("color: #666; font-size: 11px;")
        priority_info_layout.addWidget(priority_info_title)

        self.priority_info_label = QLabel("Lower # = Higher Priority")
        self.priority_info_label.setFont(QFont("Arial", 10))
        self.priority_info_label.setStyleSheet("color: #666;")
        priority_info_layout.addWidget(self.priority_info_label)

        summary_layout.addWidget(priority_info_frame)

        summary_layout.addStretch()

        parent_layout.addWidget(summary_group)

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls for position and overall."""
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)

        # Position filter
        pos_label = QLabel("Position:")
        filter_layout.addWidget(pos_label)

        self.position_combo = QComboBox()
        self.position_combo.addItem("All Positions", "")
        positions = [
            "Quarterback", "Running Back", "Wide Receiver", "Tight End",
            "Left Tackle", "Left Guard", "Center", "Right Guard", "Right Tackle",
            "Defensive End", "Defensive Tackle", "Linebacker",
            "Cornerback", "Safety", "Kicker", "Punter"
        ]
        for pos in positions:
            self.position_combo.addItem(pos, pos.lower().replace(" ", "_"))
        self.position_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.position_combo)

        filter_layout.addSpacing(20)

        # Min overall filter
        ovr_label = QLabel("Min Overall:")
        filter_layout.addWidget(ovr_label)

        self.min_overall_spin = QSpinBox()
        self.min_overall_spin.setRange(0, 99)
        self.min_overall_spin.setValue(50)
        self.min_overall_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.min_overall_spin)

        filter_layout.addStretch()

        parent_layout.addWidget(filter_frame)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of waiver players."""
        table_group = QGroupBox("Available on Waivers")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(8)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Former Team", "Dead $", "Status", "Action"
        ])

        # Configure table appearance
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.resizeSection(7, 120)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Click 'Claim' to submit a waiver claim for a player. "
            "Claims are processed by waiver priority (worst record = highest priority). "
            "If multiple teams claim the same player, the team with the highest priority gets them. "
            "Unclaimed players become free agents."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_waiver_data(self, data: Dict):
        """
        Populate the view with waiver wire data.

        Args:
            data: Dictionary containing:
                - waiver_players: List of player dicts on waivers
                - user_priority: int (1-32, 1 = highest priority)
                - user_claims: List of player_ids already claimed by user
        """
        self._waiver_players = data.get("waiver_players", [])
        self._user_priority = data.get("user_priority", 16)
        self._user_claims = set(data.get("user_claims", []))

        # Update summary labels
        self.available_count_label.setText(str(len(self._waiver_players)))
        self.priority_label.setText(f"#{self._user_priority}")
        self.claims_count_label.setText(str(len(self._user_claims)))

        # Color priority based on position
        if self._user_priority <= 5:
            self.priority_label.setStyleSheet("color: #2E7D32;")  # Green - high priority
            self.priority_info_label.setText("You have high priority!")
        elif self._user_priority <= 16:
            self.priority_label.setStyleSheet("color: #1976D2;")  # Blue - mid priority
            self.priority_info_label.setText("You have mid priority")
        else:
            self.priority_label.setStyleSheet("color: #C62828;")  # Red - low priority
            self.priority_info_label.setText("You have low priority")

        self._apply_filters()

    def _apply_filters(self):
        """Apply position and overall filters to waiver list."""
        position_filter = self.position_combo.currentData()
        min_overall = self.min_overall_spin.value()

        self._filtered_players = []
        for player in self._waiver_players:
            # Position filter
            if position_filter:
                player_pos = player.get("position", "").lower().replace(" ", "_")
                if player_pos != position_filter:
                    continue

            # Overall filter
            if player.get("overall", 0) < min_overall:
                continue

            self._filtered_players.append(player)

        # Sort by overall (highest first)
        self._filtered_players.sort(key=lambda p: p.get("overall", 0), reverse=True)

        # Update table
        self.players_table.setRowCount(len(self._filtered_players))
        for row, player in enumerate(self._filtered_players):
            self._populate_row(row, player)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)
        has_claim = player_id in self._user_claims

        # Highlight claimed players
        highlight_color = QColor("#E3F2FD") if has_claim else None  # Light blue

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        if highlight_color:
            name_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(player.get("position", ""))
        pos_item.setTextAlignment(Qt.AlignCenter)
        if highlight_color:
            pos_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 1, pos_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))
        if highlight_color:
            age_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 2, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))
        if highlight_color:
            ovr_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 3, ovr_item)

        # Former team
        former_team = player.get("former_team", "Unknown")
        team_item = QTableWidgetItem(former_team)
        team_item.setTextAlignment(Qt.AlignCenter)
        if highlight_color:
            team_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 4, team_item)

        # Dead money (from former team's cut)
        dead_money = player.get("dead_money", 0)
        dead_text = f"${dead_money:,}" if dead_money else "$0"
        dead_item = QTableWidgetItem(dead_text)
        dead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dead_item.setForeground(QColor("#666"))
        if highlight_color:
            dead_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 5, dead_item)

        # Status
        if has_claim:
            status_text = "Claimed"
            status_color = QColor("#1976D2")  # Blue
        else:
            status_text = "Available"
            status_color = QColor("#666")

        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(status_color)
        if highlight_color:
            status_item.setBackground(QBrush(highlight_color))
        self.players_table.setItem(row, 6, status_item)

        # Action button
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if has_claim:
            # Cancel button for existing claims
            btn = QPushButton("Cancel")
            btn.setStyleSheet(
                "QPushButton { background-color: #757575; color: white; border-radius: 3px; padding: 4px 8px; }"
                "QPushButton:hover { background-color: #616161; }"
            )
            btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_cancel_clicked(pid, r))
        else:
            # Claim button
            btn = QPushButton("Claim")
            btn.setStyleSheet(
                "QPushButton { background-color: #1976D2; color: white; border-radius: 3px; padding: 4px 8px; }"
                "QPushButton:hover { background-color: #1565C0; }"
            )
            btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_claim_clicked(pid, r))

        action_layout.addWidget(btn)
        self.players_table.setCellWidget(row, 7, action_widget)

    def _on_claim_clicked(self, player_id: int, row: int):
        """Handle claim button click."""
        # Update status cell
        status_item = self.players_table.item(row, 6)
        if status_item:
            status_item.setText("Claimed")
            status_item.setForeground(QColor("#1976D2"))

        # Update button to Cancel
        action_widget = self.players_table.cellWidget(row, 7)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Cancel")
                    child.setStyleSheet(
                        "QPushButton { background-color: #757575; color: white; border-radius: 3px; padding: 4px 8px; }"
                        "QPushButton:hover { background-color: #616161; }"
                    )
                    # Reconnect to cancel handler
                    child.clicked.disconnect()
                    child.clicked.connect(lambda checked, pid=player_id, r=row: self._on_cancel_clicked(pid, r))

        # Highlight row
        for col in range(7):
            item = self.players_table.item(row, col)
            if item:
                item.setBackground(QBrush(QColor("#E3F2FD")))

        # Track claim
        self._user_claims.add(player_id)
        self._update_claims_count()

        # Emit signal
        self.claim_submitted.emit(player_id)

    def _on_cancel_clicked(self, player_id: int, row: int):
        """Handle cancel button click."""
        # Update status cell
        status_item = self.players_table.item(row, 6)
        if status_item:
            status_item.setText("Available")
            status_item.setForeground(QColor("#666"))

        # Update button to Claim
        action_widget = self.players_table.cellWidget(row, 7)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Claim")
                    child.setStyleSheet(
                        "QPushButton { background-color: #1976D2; color: white; border-radius: 3px; padding: 4px 8px; }"
                        "QPushButton:hover { background-color: #1565C0; }"
                    )
                    # Reconnect to claim handler
                    child.clicked.disconnect()
                    child.clicked.connect(lambda checked, pid=player_id, r=row: self._on_claim_clicked(pid, r))

        # Remove highlight
        for col in range(7):
            item = self.players_table.item(row, col)
            if item:
                item.setBackground(QBrush(QColor("white")))

        # Remove claim
        self._user_claims.discard(player_id)
        self._update_claims_count()

        # Emit signal
        self.claim_cancelled.emit(player_id)

    def _update_claims_count(self):
        """Update the claims count label."""
        self.claims_count_label.setText(str(len(self._user_claims)))

    def get_claimed_player_ids(self) -> List[int]:
        """Get list of player IDs claimed by user."""
        return list(self._user_claims)

    def show_no_waivers_message(self):
        """Show message when there are no players on waivers."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 8)

        message_item = QTableWidgetItem("No players currently on waivers")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))

        self.players_table.setItem(0, 0, message_item)
        self.available_count_label.setText("0")

    def clear_claims(self):
        """Reset claims (call after processing)."""
        self._user_claims.clear()
        self._update_claims_count()
        self._apply_filters()

    def set_user_priority(self, priority: int):
        """Update the user's waiver priority."""
        self._user_priority = priority
        self.priority_label.setText(f"#{priority}")

        if priority <= 5:
            self.priority_label.setStyleSheet("color: #2E7D32;")
            self.priority_info_label.setText("You have high priority!")
        elif priority <= 16:
            self.priority_label.setStyleSheet("color: #1976D2;")
            self.priority_info_label.setText("You have mid priority")
        else:
            self.priority_label.setStyleSheet("color: #C62828;")
            self.priority_info_label.setText("You have low priority")

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant
        """
        # Waiver wire view currently doesn't show cap space
        # Claims are for minimum salary players, so cap impact is minimal
        pass