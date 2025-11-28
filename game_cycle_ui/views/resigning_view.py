"""
Re-signing View - Shows expiring contracts for user's team.

Allows the user to see which players have expiring contracts and
decide whether to re-sign them or let them walk to free agency.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.dialogs import ContractDetailsDialog


class ResigningView(QWidget):
    """
    View for the re-signing stage.

    Shows a table of expiring contracts with action buttons.
    Users can mark players to re-sign or let walk to free agency.
    """

    # Signals emitted when user takes action
    player_resigned = Signal(int)  # player_id
    player_released = Signal(int)  # player_id
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._expiring_players: List[Dict] = []
        self._db_path: str = ""
        self._available_cap_space: int = 0  # Track cap space for affordability checks
        self._pending_resignings: set = set()  # Track player_ids marked for re-sign
        self._setup_ui()

    def set_db_path(self, db_path: str):
        """Set the database path for contract lookups."""
        self._db_path = db_path

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Main table of expiring players
        self._create_players_table(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and counts."""
        summary_group = QGroupBox("Re-signing Summary")
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

        # Expiring contracts count
        expiring_frame = QFrame()
        expiring_layout = QVBoxLayout(expiring_frame)
        expiring_layout.setContentsMargins(0, 0, 0, 0)

        expiring_title = QLabel("Expiring Contracts")
        expiring_title.setStyleSheet("color: #666; font-size: 11px;")
        expiring_layout.addWidget(expiring_title)

        self.expiring_count_label = QLabel("0")
        self.expiring_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        expiring_layout.addWidget(self.expiring_count_label)

        summary_layout.addWidget(expiring_frame)

        # Pending re-signs
        resign_frame = QFrame()
        resign_layout = QVBoxLayout(resign_frame)
        resign_layout.setContentsMargins(0, 0, 0, 0)

        resign_title = QLabel("Pending Re-signs")
        resign_title.setStyleSheet("color: #666; font-size: 11px;")
        resign_layout.addWidget(resign_title)

        self.resign_count_label = QLabel("0")
        self.resign_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.resign_count_label.setStyleSheet("color: #1976D2;")  # Blue
        resign_layout.addWidget(self.resign_count_label)

        summary_layout.addWidget(resign_frame)

        # Total spending
        spending_frame = QFrame()
        spending_layout = QVBoxLayout(spending_frame)
        spending_layout.setContentsMargins(0, 0, 0, 0)

        spending_title = QLabel("Total Spending")
        spending_title.setStyleSheet("color: #666; font-size: 11px;")
        spending_layout.addWidget(spending_title)

        self.spending_label = QLabel("$0")
        self.spending_label.setFont(QFont("Arial", 16, QFont.Bold))
        spending_layout.addWidget(self.spending_label)

        summary_layout.addWidget(spending_frame)

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

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of expiring players."""
        table_group = QGroupBox("Expiring Contracts")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(7)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Est. Cap Hit", "Status", "Action"
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
        header.resizeSection(6, 150)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Click 'Re-sign' to keep a player, or 'Let Go' to allow them to enter free agency. "
            "Re-signed players will receive a new contract. Players you let go will be available "
            "to all teams in the Free Agency stage."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_expiring_players(self, players: List[Dict]):
        """
        Populate the table with expiring contract players.

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - age: int
                - overall: int
                - salary: int
                - years_remaining: int
        """
        self._expiring_players = players
        self.expiring_count_label.setText(str(len(players)))
        self.players_table.setRowCount(len(players))

        for row, player in enumerate(players):
            self._populate_row(row, player)

    def set_cap_space(self, cap_space: int):
        """Update the cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space (red if negative)
        if cap_space < 0:
            self.cap_space_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)

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

        # Estimated Year 1 Cap Hit (actual cap impact for new contract)
        # Falls back to AAV if year 1 cap hit not available
        estimated_cap_hit = player.get("estimated_year1_cap_hit", player.get("estimated_aav", 0))
        cap_text = f"${estimated_cap_hit:,}" if estimated_cap_hit else "N/A"
        cap_item = QTableWidgetItem(cap_text)
        cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.players_table.setItem(row, 4, cap_item)

        # Status (default: Pending)
        status_item = QTableWidgetItem("Pending")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor("#666"))
        self.players_table.setItem(row, 5, status_item)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        # View contract button (if contract exists)
        contract_id = player.get("contract_id")
        player_name = player.get("name", "Unknown")
        if contract_id:
            view_btn = QPushButton("View")
            view_btn.setStyleSheet(
                "QPushButton { background-color: #1976D2; color: white; border-radius: 3px; padding: 4px 8px; }"
                "QPushButton:hover { background-color: #1565C0; }"
            )
            view_btn.clicked.connect(
                lambda checked, cid=contract_id, pname=player_name: self._on_view_contract(cid, pname)
            )
            action_layout.addWidget(view_btn)

        resign_btn = QPushButton("Re-sign")
        resign_btn.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; border-radius: 3px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #1B5E20; }"
        )
        resign_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_resign_clicked(pid, r))
        action_layout.addWidget(resign_btn)

        let_go_btn = QPushButton("Let Go")
        let_go_btn.setStyleSheet(
            "QPushButton { background-color: #C62828; color: white; border-radius: 3px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #B71C1C; }"
        )
        let_go_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_let_go_clicked(pid, r))
        action_layout.addWidget(let_go_btn)

        self.players_table.setCellWidget(row, 6, action_widget)

    def _on_view_contract(self, contract_id: int, player_name: str):
        """Handle view contract button click - opens contract details dialog."""
        if not self._db_path:
            return

        dialog = ContractDetailsDialog(
            player_name=player_name,
            contract_id=contract_id,
            db_path=self._db_path,
            parent=self
        )
        dialog.exec()

    def _on_resign_clicked(self, player_id: int, row: int):
        """Handle re-sign button click."""
        # Add to pending resignings set
        self._pending_resignings.add(player_id)

        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Re-signing")
            status_item.setForeground(QColor("#2E7D32"))  # Green

        # Update pending count
        self._update_resign_count()

        # Refresh affordability for remaining players
        self._refresh_affordability()

        # Emit signal (for future implementation)
        self.player_resigned.emit(player_id)

    def _on_let_go_clicked(self, player_id: int, row: int):
        """Handle let go button click."""
        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Free Agent")
            status_item.setForeground(QColor("#C62828"))  # Red

        # Update pending count
        self._update_resign_count()

        # Emit signal (for future implementation)
        self.player_released.emit(player_id)

    def _update_resign_count(self):
        """Update the count of pending re-signs."""
        count = 0
        for row in range(self.players_table.rowCount()):
            status_item = self.players_table.item(row, 5)
            if status_item and status_item.text() == "Re-signing":
                count += 1
        self.resign_count_label.setText(str(count))

    def show_no_expiring_message(self):
        """Show a message when there are no expiring contracts."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 7)

        message_item = QTableWidgetItem("No expiring contracts for your team")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.players_table.setItem(0, 0, message_item)
        self.expiring_count_label.setText("0")

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant, pending_spending, projected_available,
                      is_over_cap, over_cap_amount, carryover
        """
        available = cap_data.get("available_space", 0)
        spending = cap_data.get("total_spending", 0)
        pending = cap_data.get("pending_spending", 0)
        projected = cap_data.get("projected_available", available)
        is_over_cap = cap_data.get("is_over_cap", False)
        over_cap_amount = cap_data.get("over_cap_amount", 0)
        carryover = cap_data.get("carryover", 0)

        # Store cap space for affordability checks
        self._available_cap_space = available

        # Update spending label
        self.spending_label.setText(f"${spending:,}")

        # Update rollover label (carryover from previous season)
        self.rollover_label.setText(f"${carryover:,}")

        # Show pending impact if any re-signs are selected
        if pending > 0:
            # Format: "$50M → $35M" showing before/after
            self.cap_space_label.setText(f"${available:,} → ${projected:,}")

            # Color code based on projected available space
            if projected < 0:
                self.cap_space_label.setStyleSheet("color: #C62828;")  # Red - over cap
            elif projected < available * 0.1:
                self.cap_space_label.setStyleSheet("color: #F57C00;")  # Orange - tight
            else:
                self.cap_space_label.setStyleSheet("color: #1976D2;")  # Blue - ok with pending
        else:
            # No pending decisions - show base cap space
            self.set_cap_space(available)

        # Emit cap validation signal to enable/disable Process button
        self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

        # Refresh table affordability after cap data update
        self._refresh_affordability()

    def _calculate_projected_cap(self) -> int:
        """
        Calculate available cap space after pending re-signings.

        Returns:
            Projected available cap space in dollars
        """
        pending_total = sum(
            p.get("estimated_aav", p.get("salary", 0))
            for p in self._expiring_players
            if p.get("player_id") in self._pending_resignings
        )
        return self._available_cap_space - pending_total

    def _refresh_affordability(self):
        """Refresh the affordability indicators for all rows in the table."""
        projected_cap = self._calculate_projected_cap()

        for row in range(self.players_table.rowCount()):
            # Get player_id from name item
            name_item = self.players_table.item(row, 0)
            if not name_item:
                continue

            player_id = name_item.data(Qt.UserRole)

            # Find player data
            player = next(
                (p for p in self._expiring_players if p.get("player_id") == player_id),
                None
            )
            if not player:
                continue

            # Get estimated cap hit
            estimated_aav = player.get("estimated_aav", player.get("salary", 0))

            # Check if this player is already pending re-sign
            is_pending = player_id in self._pending_resignings

            # Calculate affordability (use projected cap, but add back this player's aav if pending)
            effective_cap = projected_cap
            if is_pending:
                effective_cap += estimated_aav  # Player's cap hit already counted in projected

            can_afford = estimated_aav <= effective_cap

            # Update cap hit text color (column 4)
            cap_item = self.players_table.item(row, 4)
            if cap_item:
                if not can_afford and not is_pending:
                    cap_item.setForeground(QColor("#C62828"))  # Red - unaffordable
                else:
                    cap_item.setForeground(QColor("#000000"))  # Default

            # Update status column (column 5) if still pending
            status_item = self.players_table.item(row, 5)
            if status_item and status_item.text() == "Pending":
                if not can_afford:
                    status_item.setText("Can't Afford")
                    status_item.setForeground(QColor("#C62828"))
                else:
                    status_item.setText("Pending")
                    status_item.setForeground(QColor("#666"))

            # Update Re-sign button state (in action widget, column 6)
            action_widget = self.players_table.cellWidget(row, 6)
            if action_widget:
                # Find the Re-sign button
                for child in action_widget.children():
                    if isinstance(child, QPushButton) and child.text() == "Re-sign":
                        child.setEnabled(can_afford or is_pending)
                        if not can_afford and not is_pending:
                            child.setToolTip(
                                f"Insufficient cap space. Need ${estimated_aav:,}, have ${effective_cap:,}"
                            )
                            child.setStyleSheet(
                                "QPushButton { background-color: #555; color: #888; border-radius: 3px; padding: 4px 8px; }"
                            )
                        else:
                            child.setToolTip("")
                            child.setStyleSheet(
                                "QPushButton { background-color: #2E7D32; color: white; border-radius: 3px; padding: 4px 8px; }"
                                "QPushButton:hover { background-color: #1B5E20; }"
                            )
