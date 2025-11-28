"""
Free Agency View - Shows available free agents for signing.

Allows the user to see available free agents and sign them to their team.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import UITheme


class FreeAgencyView(QWidget):
    """
    View for the free agency stage.

    Shows a table of available free agents with sign buttons.
    Users can filter by position and minimum overall rating.
    """

    # Signals emitted when user clicks Sign/Unsign button
    player_signed = Signal(int)  # player_id
    player_unsigned = Signal(int)  # player_id - for removing pending signings
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)

    # Default NFL salary cap (2024 value)
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._free_agents: List[Dict] = []
        self._filtered_agents: List[Dict] = []
        self._signed_players: set = set()  # Track pending signings
        self._cap_limit: int = self.DEFAULT_CAP_LIMIT  # Current season cap limit
        self._available_cap_space: int = 0  # Track for affordability check
        self._setup_ui()

    @property
    def cap_limit(self) -> int:
        """Get the current salary cap limit."""
        return self._cap_limit

    @cap_limit.setter
    def cap_limit(self, value: int) -> None:
        """Set the salary cap limit (updates each season)."""
        self._cap_limit = value

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Filter panel
        self._create_filter_panel(layout)

        # Main table of free agents
        self._create_players_table(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and counts."""
        summary_group = QGroupBox("Free Agency Summary")
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

        # Free agents count
        fa_frame = QFrame()
        fa_layout = QVBoxLayout(fa_frame)
        fa_layout.setContentsMargins(0, 0, 0, 0)

        fa_title = QLabel("Available Free Agents")
        fa_title.setStyleSheet("color: #666; font-size: 11px;")
        fa_layout.addWidget(fa_title)

        self.fa_count_label = QLabel("0")
        self.fa_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        fa_layout.addWidget(self.fa_count_label)

        summary_layout.addWidget(fa_frame)

        # Projected cap (after pending signings)
        projected_frame = QFrame()
        projected_layout = QVBoxLayout(projected_frame)
        projected_layout.setContentsMargins(0, 0, 0, 0)

        projected_title = QLabel("Projected Cap")
        projected_title.setStyleSheet("color: #666; font-size: 11px;")
        projected_layout.addWidget(projected_title)

        self.projected_cap_label = QLabel("$0")
        self.projected_cap_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.projected_cap_label.setStyleSheet("color: #1976D2;")  # Blue
        projected_layout.addWidget(self.projected_cap_label)

        summary_layout.addWidget(projected_frame)

        # Pending signings
        pending_frame = QFrame()
        pending_layout = QVBoxLayout(pending_frame)
        pending_layout.setContentsMargins(0, 0, 0, 0)

        pending_title = QLabel("Pending Signings")
        pending_title.setStyleSheet("color: #666; font-size: 11px;")
        pending_layout.addWidget(pending_title)

        self.pending_count_label = QLabel("0")
        self.pending_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.pending_count_label.setStyleSheet("color: #1976D2;")  # Blue
        pending_layout.addWidget(self.pending_count_label)

        summary_layout.addWidget(pending_frame)

        # Cap rollover (carryover from previous season)
        rollover_frame = QFrame()
        rollover_layout = QVBoxLayout(rollover_frame)
        rollover_layout.setContentsMargins(0, 0, 0, 0)

        rollover_title = QLabel("Cap Rollover")
        rollover_title.setStyleSheet("color: #666; font-size: 11px;")
        rollover_layout.addWidget(rollover_title)

        self.rollover_label = QLabel("$0")
        self.rollover_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.rollover_label.setStyleSheet("color: #7B1FA2;")  # Purple
        rollover_layout.addWidget(self.rollover_label)

        summary_layout.addWidget(rollover_frame)

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
        self.min_overall_spin.setValue(60)
        self.min_overall_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.min_overall_spin)

        filter_layout.addStretch()

        parent_layout.addWidget(filter_frame)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of free agents."""
        table_group = QGroupBox("Available Free Agents")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(7)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Est. AAV", "Status", "Action"
        ])

        # Configure table appearance
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 100)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Click 'Sign' to add a free agent to your team. "
            "Signed players will receive a market-value contract. "
            "Click 'Process Free Agency' when done to finalize signings and let AI teams make their picks."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_free_agents(self, players: List[Dict]):
        """
        Populate the table with free agents.

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - age: int
                - overall: int
                - estimated_aav: int
        """
        self._free_agents = players
        self._signed_players.clear()
        self.fa_count_label.setText(str(len(players)))
        self.pending_count_label.setText("0")
        self._apply_filters()

    def set_cap_space(self, cap_space: int):
        """Update the cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space (red if negative)
        if cap_space < 0:
            self.cap_space_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant, projected_available (optional), carryover
        """
        available = cap_data.get("available_space", 0)
        self._available_cap_space = available  # Store for affordability checks
        self.set_cap_space(available)

        # Update cap limit from data if provided
        if "salary_cap_limit" in cap_data:
            self.cap_limit = cap_data["salary_cap_limit"]

        # Set projected cap (defaults to available if no pending signings)
        projected = cap_data.get("projected_available", available)
        self.set_projected_cap(projected)

        # Update rollover label (carryover from previous season)
        carryover = cap_data.get("carryover", 0)
        self.rollover_label.setText(f"${carryover:,}")

        # Refresh table to update affordability indicators
        if self._free_agents:
            self._apply_filters()

    def set_projected_cap(self, projected: int):
        """
        Update the projected cap space display.

        Color coding from theme:
        - projected (blue): Healthy cap space
        - tight (orange): Less than 10% of cap remaining
        - over_cap (red): Negative cap space

        Args:
            projected: Projected cap space after pending signings
        """
        self.projected_cap_label.setText(f"${projected:,}")

        # Get threshold from theme
        tight_threshold = UITheme.get_threshold("cap_space", "tight_percentage")

        # Color coding based on cap health
        if projected < 0:
            color = UITheme.get_color("cap_space", "over_cap")
        elif projected < self._cap_limit * tight_threshold:
            color = UITheme.get_color("cap_space", "tight")
        else:
            color = UITheme.get_color("cap_space", "projected")

        self.projected_cap_label.setStyleSheet(f"color: {color};")

        # Emit cap validation signal to enable/disable Process button
        is_over_cap = projected < 0
        over_cap_amount = abs(projected) if is_over_cap else 0
        self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

    def _apply_filters(self):
        """Apply position and overall filters to the free agent list."""
        position_filter = self.position_combo.currentData()
        min_overall = self.min_overall_spin.value()

        self._filtered_agents = []
        for player in self._free_agents:
            # Skip already signed players
            if player["player_id"] in self._signed_players:
                continue

            # Position filter
            if position_filter:
                player_pos = player.get("position", "").lower().replace(" ", "_")
                if player_pos != position_filter:
                    continue

            # Overall filter
            if player.get("overall", 0) < min_overall:
                continue

            self._filtered_agents.append(player)

        # Update table
        self.players_table.setRowCount(len(self._filtered_agents))
        for row, player in enumerate(self._filtered_agents):
            self._populate_row(row, player)

        # Update filtered count display
        self.fa_count_label.setText(str(len(self._filtered_agents)))

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)
        aav = player.get("estimated_aav", 0)

        # Calculate affordability using projected cap (after pending signings)
        projected_cap = self._calculate_projected_cap()
        can_afford = aav <= projected_cap

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        self.players_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(player.get("position", ""))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))  # Red
        self.players_table.setItem(row, 2, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
        self.players_table.setItem(row, 3, ovr_item)

        # Estimated AAV - color red if unaffordable
        aav_text = f"${aav:,}" if aav else "N/A"
        aav_item = QTableWidgetItem(aav_text)
        aav_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if not can_afford:
            aav_item.setForeground(QColor("#C62828"))  # Red - unaffordable
        self.players_table.setItem(row, 4, aav_item)

        # Status - show "Can't Afford" if unaffordable
        if can_afford:
            status_item = QTableWidgetItem("Available")
            status_item.setForeground(QColor("#666"))
        else:
            status_item = QTableWidgetItem("Can't Afford")
            status_item.setForeground(QColor("#C62828"))  # Red
        status_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 5, status_item)

        # Action button - disable if unaffordable
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        sign_btn = QPushButton("Sign")
        sign_btn.setEnabled(can_afford)  # Disable if can't afford
        if can_afford:
            sign_btn.setStyleSheet(
                "QPushButton { background-color: #2E7D32; color: white; border-radius: 3px; padding: 4px 12px; }"
                "QPushButton:hover { background-color: #1B5E20; }"
            )
        else:
            sign_btn.setStyleSheet(
                "QPushButton { background-color: #ccc; color: #666; border-radius: 3px; padding: 4px 12px; }"
            )
            sign_btn.setToolTip(f"Insufficient cap space. Need ${aav:,}, have ${projected_cap:,}")
        sign_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_sign_clicked(pid, r))
        action_layout.addWidget(sign_btn)

        self.players_table.setCellWidget(row, 6, action_widget)

    def _on_sign_clicked(self, player_id: int, row: int):
        """Handle sign/unsign button click (toggle behavior)."""
        if player_id in self._signed_players:
            # UNSIGN - remove from pending
            self._signed_players.discard(player_id)
            self._update_row_unsigned(row)
            self._update_pending_count()
            self.player_unsigned.emit(player_id)
        else:
            # SIGN - add to pending
            self._signed_players.add(player_id)
            self._update_row_signed(row)
            self._update_pending_count()
            self.player_signed.emit(player_id)

        # Refresh affordability for all visible players
        self._refresh_affordability()

    def _update_row_signed(self, row: int):
        """Update row appearance when player is marked for signing."""
        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Signing")
            color = UITheme.get_color("status", "success")
            status_item.setForeground(QColor(color))

        # Change button to "Unsign" with warning color
        action_widget = self.players_table.cellWidget(row, 6)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Unsign")
                    child.setStyleSheet(UITheme.button_style("warning"))

    def _update_row_unsigned(self, row: int):
        """Update row appearance when player is unmarked (unsigned)."""
        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Available")
            color = UITheme.get_color("status", "neutral")
            status_item.setForeground(QColor(color))

        # Change button back to "Sign" with primary color
        action_widget = self.players_table.cellWidget(row, 6)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Sign")
                    child.setStyleSheet(UITheme.button_style("primary"))

    def _update_pending_count(self):
        """Update the count of pending signings."""
        self.pending_count_label.setText(str(len(self._signed_players)))

    def _calculate_projected_cap(self) -> int:
        """
        Calculate cap space remaining after pending signings.

        Returns:
            Projected cap space (base available - pending AAV totals)
        """
        pending_total = sum(
            p.get("estimated_aav", 0)
            for p in self._free_agents
            if p["player_id"] in self._signed_players
        )
        return self._available_cap_space - pending_total

    def _refresh_affordability(self):
        """
        Refresh affordability indicators for all visible rows after signing/unsigning.

        Updates:
        - Projected cap display in summary panel
        - AAV color (red if unaffordable)
        - Status text ("Available" vs "Can't Afford")
        - Sign button enabled state and tooltip
        """
        projected_cap = self._calculate_projected_cap()

        # Update projected cap display
        self.set_projected_cap(projected_cap)

        # Update affordability for each visible row
        for row in range(self.players_table.rowCount()):
            name_item = self.players_table.item(row, 0)
            if not name_item:
                continue

            player_id = name_item.data(Qt.UserRole)

            # Skip already-signed players (they show "Signing" status)
            if player_id in self._signed_players:
                continue

            # Find this player's data
            player = next(
                (p for p in self._filtered_agents if p["player_id"] == player_id),
                None
            )
            if not player:
                continue

            aav = player.get("estimated_aav", 0)
            can_afford = aav <= projected_cap

            # Update AAV color
            aav_item = self.players_table.item(row, 4)
            if aav_item:
                if can_afford:
                    aav_item.setForeground(QColor("#333"))  # Default
                else:
                    aav_item.setForeground(QColor("#C62828"))  # Red

            # Update status
            status_item = self.players_table.item(row, 5)
            if status_item:
                if can_afford:
                    status_item.setText("Available")
                    status_item.setForeground(QColor("#666"))
                else:
                    status_item.setText("Can't Afford")
                    status_item.setForeground(QColor("#C62828"))

            # Update button state
            action_widget = self.players_table.cellWidget(row, 6)
            if action_widget:
                for child in action_widget.children():
                    if isinstance(child, QPushButton) and child.text() == "Sign":
                        child.setEnabled(can_afford)
                        if can_afford:
                            child.setStyleSheet(
                                "QPushButton { background-color: #2E7D32; color: white; "
                                "border-radius: 3px; padding: 4px 12px; }"
                                "QPushButton:hover { background-color: #1B5E20; }"
                            )
                            child.setToolTip("")
                        else:
                            child.setStyleSheet(
                                "QPushButton { background-color: #ccc; color: #666; "
                                "border-radius: 3px; padding: 4px 12px; }"
                            )
                            child.setToolTip(
                                f"Insufficient cap space. Need ${aav:,}, have ${projected_cap:,}"
                            )

    def show_no_free_agents_message(self):
        """Show a message when there are no free agents available."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 7)

        message_item = QTableWidgetItem("No free agents available")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.players_table.setItem(0, 0, message_item)
        self.fa_count_label.setText("0")

    def clear_signed_players(self):
        """Reset signed players (call after processing)."""
        self._signed_players.clear()
        self.pending_count_label.setText("0")
        self._apply_filters()

    def get_signed_player_ids(self) -> List[int]:
        """Get list of player IDs that were signed."""
        return list(self._signed_players)