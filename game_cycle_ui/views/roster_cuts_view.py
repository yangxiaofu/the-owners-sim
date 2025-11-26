"""
Roster Cuts View - Shows roster for cutting down to 53-man limit.

Allows the user to cut players from their roster, with AI suggestions
highlighting low-value players while respecting position minimums.
"""

from typing import Dict, List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush


class RosterCutsView(QWidget):
    """
    View for the roster cuts stage.

    Shows a table of all roster players with cut buttons.
    AI suggestions are highlighted for easy identification.
    Users can filter by position and minimum overall rating.
    """

    # Signals
    player_cut = Signal(int)  # player_id
    get_suggestions_requested = Signal()
    process_cuts_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._roster_players: List[Dict] = []
        self._filtered_players: List[Dict] = []
        self._cut_players: Set[int] = set()
        self._suggested_cuts: Set[int] = set()
        self._protected_players: Set[int] = set()
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

        # Main table of roster players
        self._create_players_table(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing roster and cut info."""
        summary_group = QGroupBox("Roster Cuts Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Current roster size
        roster_frame = QFrame()
        roster_layout = QVBoxLayout(roster_frame)
        roster_layout.setContentsMargins(0, 0, 0, 0)

        roster_title = QLabel("Current Roster")
        roster_title.setStyleSheet("color: #666; font-size: 11px;")
        roster_layout.addWidget(roster_title)

        self.roster_size_label = QLabel("0 / 53")
        self.roster_size_label.setFont(QFont("Arial", 16, QFont.Bold))
        roster_layout.addWidget(self.roster_size_label)

        summary_layout.addWidget(roster_frame)

        # Cuts needed
        cuts_frame = QFrame()
        cuts_layout = QVBoxLayout(cuts_frame)
        cuts_layout.setContentsMargins(0, 0, 0, 0)

        cuts_title = QLabel("Cuts Needed")
        cuts_title.setStyleSheet("color: #666; font-size: 11px;")
        cuts_layout.addWidget(cuts_title)

        self.cuts_needed_label = QLabel("0")
        self.cuts_needed_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.cuts_needed_label.setStyleSheet("color: #C62828;")  # Red
        cuts_layout.addWidget(self.cuts_needed_label)

        summary_layout.addWidget(cuts_frame)

        # Players marked for cut
        marked_frame = QFrame()
        marked_layout = QVBoxLayout(marked_frame)
        marked_layout.setContentsMargins(0, 0, 0, 0)

        marked_title = QLabel("Marked for Cut")
        marked_title.setStyleSheet("color: #666; font-size: 11px;")
        marked_layout.addWidget(marked_title)

        self.marked_cut_label = QLabel("0")
        self.marked_cut_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.marked_cut_label.setStyleSheet("color: #FF6F00;")  # Orange
        marked_layout.addWidget(self.marked_cut_label)

        summary_layout.addWidget(marked_frame)

        # Total dead money
        dead_frame = QFrame()
        dead_layout = QVBoxLayout(dead_frame)
        dead_layout.setContentsMargins(0, 0, 0, 0)

        dead_title = QLabel("Total Dead Money")
        dead_title.setStyleSheet("color: #666; font-size: 11px;")
        dead_layout.addWidget(dead_title)

        self.dead_money_label = QLabel("$0")
        self.dead_money_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.dead_money_label.setStyleSheet("color: #C62828;")  # Red
        dead_layout.addWidget(self.dead_money_label)

        summary_layout.addWidget(dead_frame)

        # Cap savings
        savings_frame = QFrame()
        savings_layout = QVBoxLayout(savings_frame)
        savings_layout.setContentsMargins(0, 0, 0, 0)

        savings_title = QLabel("Cap Savings")
        savings_title.setStyleSheet("color: #666; font-size: 11px;")
        savings_layout.addWidget(savings_title)

        self.cap_savings_label = QLabel("$0")
        self.cap_savings_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.cap_savings_label.setStyleSheet("color: #2E7D32;")  # Green
        savings_layout.addWidget(self.cap_savings_label)

        summary_layout.addWidget(savings_frame)

        summary_layout.addStretch()

        parent_layout.addWidget(summary_group)

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls and AI suggestion button."""
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

        # Show suggestions only checkbox
        self.show_suggestions_check = QCheckBox("Show Suggested Cuts Only")
        self.show_suggestions_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.show_suggestions_check)

        filter_layout.addSpacing(20)

        # Get Suggestions button
        self.suggestions_btn = QPushButton("Get AI Suggestions")
        self.suggestions_btn.setStyleSheet(
            "QPushButton { background-color: #FF6F00; color: white; border-radius: 3px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #E65100; }"
        )
        self.suggestions_btn.clicked.connect(self._on_get_suggestions)
        filter_layout.addWidget(self.suggestions_btn)

        filter_layout.addStretch()

        parent_layout.addWidget(filter_frame)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of roster players."""
        table_group = QGroupBox("Current Roster")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(10)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Salary", "Value",
            "Dead $", "Savings", "Status", "Action"
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
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.Fixed)
        header.resizeSection(9, 100)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Click 'Cut' to mark a player for release. "
            "Highlighted rows are AI-suggested cuts based on player value vs cap impact. "
            "Protected players (last at their position) cannot be cut. "
            "Click 'Process Cuts' when done to release marked players to the waiver wire."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_roster_data(self, data: Dict):
        """
        Populate the view with roster cut data.

        Args:
            data: Dictionary containing:
                - roster: List of player dicts with value_score, dead_money, cap_savings
                - current_size: int
                - target_size: int (53)
                - cuts_needed: int
                - ai_suggestions: List of player_ids suggested for cuts
                - protected_players: List of player_ids that cannot be cut
        """
        self._roster_players = data.get("roster", [])
        self._suggested_cuts = set(data.get("ai_suggestions", []))
        self._protected_players = set(data.get("protected_players", []))
        self._cut_players.clear()

        current_size = data.get("current_size", len(self._roster_players))
        target_size = data.get("target_size", 53)
        cuts_needed = data.get("cuts_needed", max(0, current_size - target_size))

        # Update summary labels
        self.roster_size_label.setText(f"{current_size} / {target_size}")
        if current_size > target_size:
            self.roster_size_label.setStyleSheet("color: #C62828;")  # Red - over limit
        else:
            self.roster_size_label.setStyleSheet("color: #2E7D32;")  # Green - at/under limit

        self.cuts_needed_label.setText(str(cuts_needed))
        if cuts_needed > 0:
            self.cuts_needed_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cuts_needed_label.setStyleSheet("color: #2E7D32;")  # Green

        self.marked_cut_label.setText("0")
        self.dead_money_label.setText("$0")
        self.cap_savings_label.setText("$0")

        self._apply_filters()

    def _apply_filters(self):
        """Apply position filter and suggestions filter to roster."""
        position_filter = self.position_combo.currentData()
        show_suggestions_only = self.show_suggestions_check.isChecked()

        self._filtered_players = []
        for player in self._roster_players:
            player_id = player.get("player_id", 0)

            # Skip already cut players
            if player_id in self._cut_players:
                continue

            # Position filter
            if position_filter:
                player_pos = player.get("position", "").lower().replace(" ", "_")
                if player_pos != position_filter:
                    continue

            # Suggestions filter
            if show_suggestions_only and player_id not in self._suggested_cuts:
                continue

            self._filtered_players.append(player)

        # Sort by value score (lowest first for easier cutting)
        self._filtered_players.sort(key=lambda p: p.get("value_score", 0))

        # Update table
        self.players_table.setRowCount(len(self._filtered_players))
        for row, player in enumerate(self._filtered_players):
            self._populate_row(row, player)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)
        is_suggested = player_id in self._suggested_cuts
        is_protected = player_id in self._protected_players

        # Highlight color for suggested cuts
        highlight_color = QColor("#FFF3E0") if is_suggested else None  # Light orange
        protected_color = QColor("#E8F5E9") if is_protected else None  # Light green

        row_color = protected_color if is_protected else highlight_color

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        if row_color:
            name_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(player.get("position", ""))
        pos_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            pos_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 1, pos_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))
        if row_color:
            age_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 2, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))
        if row_color:
            ovr_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 3, ovr_item)

        # Salary
        salary = player.get("salary", 0)
        salary_text = f"${salary:,}" if salary else "N/A"
        salary_item = QTableWidgetItem(salary_text)
        salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if row_color:
            salary_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 4, salary_item)

        # Value score
        value = player.get("value_score", 0)
        value_item = QTableWidgetItem(f"{value:.1f}")
        value_item.setTextAlignment(Qt.AlignCenter)
        if value < 50:
            value_item.setForeground(QColor("#C62828"))  # Red - low value
        if row_color:
            value_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 5, value_item)

        # Dead money
        dead_money = player.get("dead_money", 0)
        dead_text = f"${dead_money:,}" if dead_money else "$0"
        dead_item = QTableWidgetItem(dead_text)
        dead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if dead_money > 0:
            dead_item.setForeground(QColor("#C62828"))
        if row_color:
            dead_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 6, dead_item)

        # Cap savings
        cap_savings = player.get("cap_savings", 0)
        savings_text = f"${cap_savings:,}" if cap_savings else "$0"
        savings_item = QTableWidgetItem(savings_text)
        savings_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if cap_savings > 0:
            savings_item.setForeground(QColor("#2E7D32"))
        if row_color:
            savings_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 7, savings_item)

        # Status
        if is_protected:
            status_text = "Protected"
            status_color = QColor("#2E7D32")
        elif is_suggested:
            status_text = "Suggested"
            status_color = QColor("#FF6F00")
        else:
            status_text = "Roster"
            status_color = QColor("#666")

        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(status_color)
        if row_color:
            status_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 8, status_item)

        # Action button
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if is_protected:
            # Show disabled button for protected players
            btn = QPushButton("Protected")
            btn.setEnabled(False)
            btn.setStyleSheet(
                "QPushButton { background-color: #ccc; color: #666; border-radius: 3px; padding: 4px 8px; }"
            )
        else:
            btn = QPushButton("Cut")
            btn.setStyleSheet(
                "QPushButton { background-color: #C62828; color: white; border-radius: 3px; padding: 4px 8px; }"
                "QPushButton:hover { background-color: #B71C1C; }"
            )
            btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_cut_clicked(pid, r))

        action_layout.addWidget(btn)
        self.players_table.setCellWidget(row, 9, action_widget)

    def _on_cut_clicked(self, player_id: int, row: int):
        """Handle cut button click."""
        # Find player data for cap calculations
        player = next((p for p in self._roster_players if p.get("player_id") == player_id), None)
        if not player:
            return

        # Update status cell
        status_item = self.players_table.item(row, 8)
        if status_item:
            status_item.setText("Cutting")
            status_item.setForeground(QColor("#C62828"))

        # Disable the button
        action_widget = self.players_table.cellWidget(row, 9)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setEnabled(False)
                    child.setText("Cut")

        # Track cut player
        self._cut_players.add(player_id)

        # Update counts and totals
        self._update_totals()

        # Emit signal
        self.player_cut.emit(player_id)

    def _update_totals(self):
        """Update the summary totals based on marked cuts."""
        total_dead = 0
        total_savings = 0

        for player in self._roster_players:
            if player.get("player_id") in self._cut_players:
                total_dead += player.get("dead_money", 0)
                total_savings += player.get("cap_savings", 0)

        self.marked_cut_label.setText(str(len(self._cut_players)))
        self.dead_money_label.setText(f"${total_dead:,}")
        self.cap_savings_label.setText(f"${total_savings:,}")

        # Update roster size to reflect pending cuts
        current = len(self._roster_players) - len(self._cut_players)
        target = 53
        self.roster_size_label.setText(f"{current} / {target}")
        if current > target:
            self.roster_size_label.setStyleSheet("color: #C62828;")
        else:
            self.roster_size_label.setStyleSheet("color: #2E7D32;")

        # Update cuts needed
        cuts_needed = max(0, current - target)
        self.cuts_needed_label.setText(str(cuts_needed))
        if cuts_needed > 0:
            self.cuts_needed_label.setStyleSheet("color: #C62828;")
        else:
            self.cuts_needed_label.setStyleSheet("color: #2E7D32;")

    def _on_get_suggestions(self):
        """Handle get suggestions button click."""
        self.get_suggestions_requested.emit()

    def set_ai_suggestions(self, suggestions: List[int], protected: List[int]):
        """Update AI suggestions after request."""
        self._suggested_cuts = set(suggestions)
        self._protected_players = set(protected)
        self._apply_filters()

    def get_cut_player_ids(self) -> List[int]:
        """Get list of player IDs marked for cutting."""
        return list(self._cut_players)

    def show_no_cuts_needed_message(self):
        """Show message when roster is already at or under limit."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 10)

        message_item = QTableWidgetItem("Your roster is already at or below the 53-man limit. No cuts needed!")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#2E7D32"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))

        self.players_table.setItem(0, 0, message_item)

    def clear_cuts(self):
        """Reset cut players (call after processing)."""
        self._cut_players.clear()
        self._update_totals()
        self._apply_filters()