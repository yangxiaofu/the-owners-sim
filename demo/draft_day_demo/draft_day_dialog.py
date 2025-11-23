"""
Draft Day Dialog - Interactive NFL Draft Simulation UI

PySide6/Qt dialog for interactive draft day simulation with AI decision-making.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QListWidget, QSplitter,
    QHeaderView, QMessageBox, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Import from existing codebase
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from team_management.teams.team_loader import get_team_by_id
from draft_demo_controller import DraftDemoController


class NumericTableWidgetItem(QTableWidgetItem):
    """
    QTableWidgetItem subclass that sorts numerically using UserRole data.

    This class overrides the less-than operator to compare numeric values
    stored in Qt.UserRole instead of comparing display text strings.
    """

    def __lt__(self, other: QTableWidgetItem) -> bool:
        """
        Compare items numerically using UserRole data.

        Args:
            other: Another QTableWidgetItem to compare against

        Returns:
            True if this item's numeric value is less than other's
        """
        # Get numeric values from UserRole
        self_value = self.data(Qt.UserRole)
        other_value = other.data(Qt.UserRole)

        # Compare numerically if both have numeric data
        if self_value is not None and other_value is not None:
            try:
                return float(self_value) < float(other_value)
            except (ValueError, TypeError):
                # If conversion fails, fall back to string comparison
                pass

        # Fall back to default string comparison
        return super().__lt__(other)


class DraftDayDialog(QDialog):
    """
    Interactive Draft Day Simulation Dialog.

    Provides full UI for simulating NFL draft with:
    - Available prospects table (sortable)
    - Team needs display
    - User pick controls
    - AI simulation
    - Pick history tracking
    """

    def __init__(
        self,
        controller: DraftDemoController,
        parent=None
    ):
        """
        Initialize Draft Day Dialog.

        Args:
            controller: DraftDemoController instance for business logic
            parent: Parent widget
        """
        super().__init__(parent)

        # Store controller reference
        self.controller = controller
        self.user_team_id = controller.user_team_id

        # UI references
        self.current_pick_label: Optional[QLabel] = None
        self.user_team_label: Optional[QLabel] = None
        self.prospects_table: Optional[QTableWidget] = None
        self.team_needs_list: Optional[QListWidget] = None
        self.pick_history_table: Optional[QTableWidget] = None
        self.make_pick_btn: Optional[QPushButton] = None
        self.auto_sim_btn: Optional[QPushButton] = None

        # Configure dialog
        self.setWindowTitle(f"Draft Day Simulation - {controller.season} NFL Draft")
        self.resize(1000, 700)

        # Create UI
        self._create_ui()

        # Initial UI refresh
        self.refresh_all_ui()

    def _create_ui(self):
        """Build complete UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top section: Current pick info
        top_section = self._create_top_section()
        main_layout.addLayout(top_section)

        # Middle section: Prospects + Team Needs (2 columns with splitter)
        middle_section = self._create_middle_section()
        main_layout.addWidget(middle_section, stretch=3)

        # Bottom left: Action buttons
        button_section = self._create_button_section()
        main_layout.addLayout(button_section)

        # Bottom section: Pick history
        history_section = self._create_history_section()
        main_layout.addWidget(history_section, stretch=1)

    def _create_top_section(self) -> QHBoxLayout:
        """Create top info section with current pick and user team."""
        layout = QHBoxLayout()

        # Current pick label
        self.current_pick_label = QLabel()
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.current_pick_label.setFont(font)
        layout.addWidget(self.current_pick_label)

        layout.addStretch()

        # User team label
        self.user_team_label = QLabel()
        user_team = get_team_by_id(self.user_team_id)
        team_name = user_team.full_name if user_team else f"Team {self.user_team_id}"
        self.user_team_label.setText(f"Your Team: {team_name}")
        self.user_team_label.setStyleSheet("font-size: 12px; color: #0066cc;")
        layout.addWidget(self.user_team_label)

        return layout

    def _create_middle_section(self) -> QSplitter:
        """Create middle section with prospects table and team needs."""
        splitter = QSplitter(Qt.Horizontal)

        # Left: Available prospects table
        prospects_widget = self._create_prospects_table()
        splitter.addWidget(prospects_widget)

        # Right: Team needs list
        needs_widget = self._create_team_needs_list()
        splitter.addWidget(needs_widget)

        # Set initial sizes (70% prospects, 30% needs)
        splitter.setSizes([700, 300])

        return splitter

    def _create_prospects_table(self) -> QTableWidget:
        """Create available prospects table."""
        self.prospects_table = QTableWidget()
        self.prospects_table.setColumnCount(5)
        self.prospects_table.setHorizontalHeaderLabels([
            "Rank", "Name", "Pos", "College", "Overall"
        ])

        # Configure table
        self.prospects_table.setAlternatingRowColors(True)
        self.prospects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospects_table.setSelectionMode(QTableWidget.SingleSelection)
        self.prospects_table.setSortingEnabled(True)
        self.prospects_table.verticalHeader().setVisible(False)

        # Column sizing
        header = self.prospects_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name column
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # College column

        return self.prospects_table

    def _create_team_needs_list(self) -> QListWidget:
        """Create team needs list widget."""
        from PySide6.QtWidgets import QWidget, QVBoxLayout

        # Container widget with label
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        label = QLabel("Team Needs")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)

        # List widget
        self.team_needs_list = QListWidget()
        layout.addWidget(self.team_needs_list)

        return container

    def _create_button_section(self) -> QHBoxLayout:
        """Create action buttons section."""
        layout = QHBoxLayout()

        # Make Pick button (enabled only on user's turn)
        self.make_pick_btn = QPushButton("Make Pick")
        self.make_pick_btn.setMinimumHeight(40)
        self.make_pick_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.make_pick_btn.clicked.connect(self.on_make_pick_clicked)
        layout.addWidget(self.make_pick_btn)

        # Auto-Sim button (always enabled)
        self.auto_sim_btn = QPushButton("Auto-Sim to My Next Pick")
        self.auto_sim_btn.setMinimumHeight(40)
        self.auto_sim_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.auto_sim_btn.clicked.connect(self.on_auto_sim_clicked)
        layout.addWidget(self.auto_sim_btn)

        layout.addStretch()

        return layout

    def _create_history_section(self) -> QTableWidget:
        """Create pick history table."""
        self.pick_history_table = QTableWidget()
        self.pick_history_table.setColumnCount(5)
        self.pick_history_table.setHorizontalHeaderLabels([
            "Pick", "Round", "Team", "Player", "Pos"
        ])

        # Configure table
        self.pick_history_table.setAlternatingRowColors(True)
        self.pick_history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pick_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pick_history_table.setSortingEnabled(False)
        self.pick_history_table.verticalHeader().setVisible(False)

        # Column sizing
        header = self.pick_history_table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Team column
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Player column

        return self.pick_history_table

    def populate_prospects_table(self):
        """Load available prospects into table."""
        # Disable sorting while populating
        self.prospects_table.setSortingEnabled(False)
        self.prospects_table.setRowCount(0)

        # Get available prospects from controller
        prospects = self.controller.get_available_prospects(limit=300)

        for rank, prospect in enumerate(prospects, start=1):
            player_id = prospect['player_id']
            first_name = prospect['first_name']
            last_name = prospect['last_name']
            position = prospect['position']
            college = prospect.get('college', 'Unknown')
            overall = prospect['overall']

            row = self.prospects_table.rowCount()
            self.prospects_table.insertRow(row)

            # Rank
            rank_item = NumericTableWidgetItem(str(rank))
            rank_item.setData(Qt.UserRole, rank)
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 0, rank_item)

            # Name
            name = f"{first_name} {last_name}"
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, player_id)  # Store player_id
            self.prospects_table.setItem(row, 1, name_item)

            # Position
            pos_item = QTableWidgetItem(position)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 2, pos_item)

            # College
            college_item = QTableWidgetItem(college or "Unknown")
            self.prospects_table.setItem(row, 3, college_item)

            # Overall rating
            overall_item = NumericTableWidgetItem(str(overall))
            overall_item.setData(Qt.UserRole, overall)
            overall_item.setTextAlignment(Qt.AlignCenter)
            # Color code by rating
            if overall >= 85:
                overall_item.setForeground(Qt.darkGreen)
            elif overall >= 75:
                overall_item.setForeground(Qt.darkBlue)
            elif overall < 65:
                overall_item.setForeground(Qt.darkRed)
            self.prospects_table.setItem(row, 4, overall_item)

        # Re-enable sorting
        self.prospects_table.setSortingEnabled(True)
        self.prospects_table.sortItems(0, Qt.AscendingOrder)  # Sort by rank

    def populate_team_needs(self):
        """Load user team's needs."""
        self.team_needs_list.clear()

        # Get team needs from controller
        needs = self.controller.get_team_needs(self.user_team_id)

        for need in needs:
            position = need['position']
            urgency = need['urgency'].name if hasattr(need['urgency'], 'name') else str(need['urgency'])
            urgency_score = need.get('urgency_score', 0)

            # Format: "QB - CRITICAL"
            need_text = f"{position.upper()} - {urgency}"

            item = QListWidgetItem(need_text)

            # Color code by urgency score (5=CRITICAL, 1=LOW)
            if urgency_score >= 5:
                item.setForeground(Qt.darkRed)
            elif urgency_score >= 3:
                item.setForeground(Qt.darkYellow)
            else:
                item.setForeground(Qt.darkGray)

            self.team_needs_list.addItem(item)

    def populate_pick_history(self):
        """Load recent picks (last 15)."""
        self.pick_history_table.setRowCount(0)

        # Get recent picks from controller
        draft_order = self.controller.draft_order
        current_idx = self.controller.current_pick_index

        recent_picks = []
        for i in range(max(0, current_idx - 15), current_idx):
            if i < len(draft_order):
                pick = draft_order[i]
                if pick.is_executed and pick.player_id:
                    recent_picks.append(pick)

        # Populate table
        for pick in recent_picks:
            # Get prospect details from controller
            prospect = self.controller.draft_api.get_prospect_by_id(pick.player_id, self.controller.dynasty_id)
            if not prospect:
                continue

            player_name = f"{prospect['first_name']} {prospect['last_name']}"
            position = prospect['position']

            # Get team name
            team = get_team_by_id(pick.current_team_id)
            team_name = team.full_name if team else f"Team {pick.current_team_id}"

            row = self.pick_history_table.rowCount()
            self.pick_history_table.insertRow(row)

            # Pick number
            pick_item = NumericTableWidgetItem(str(pick.overall_pick))
            pick_item.setData(Qt.UserRole, pick.overall_pick)
            pick_item.setTextAlignment(Qt.AlignCenter)
            self.pick_history_table.setItem(row, 0, pick_item)

            # Round
            round_item = NumericTableWidgetItem(str(pick.round_number))
            round_item.setData(Qt.UserRole, pick.round_number)
            round_item.setTextAlignment(Qt.AlignCenter)
            self.pick_history_table.setItem(row, 1, round_item)

            # Team
            team_item = QTableWidgetItem(team_name)
            self.pick_history_table.setItem(row, 2, team_item)

            # Player
            player_item = QTableWidgetItem(player_name)
            self.pick_history_table.setItem(row, 3, player_item)

            # Position
            pos_item = QTableWidgetItem(position)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.pick_history_table.setItem(row, 4, pos_item)

    def advance_to_next_pick(self):
        """Move to next pick (user or CPU)."""
        if self.controller.current_pick_index >= len(self.controller.draft_order):
            self._show_draft_complete_message()
            return

        current_pick = self.controller.draft_order[self.controller.current_pick_index]

        if current_pick.current_team_id == self.user_team_id:
            # User's turn - enable make pick button
            self.make_pick_btn.setEnabled(True)
        else:
            # CPU turn - disable make pick, execute after delay
            self.make_pick_btn.setEnabled(False)
            QTimer.singleShot(1000, self.execute_cpu_pick)

    def on_make_pick_clicked(self):
        """User picks selected prospect."""
        # Get selected prospect
        selected_rows = self.prospects_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a prospect to draft.")
            return

        row = selected_rows[0].row()
        name_item = self.prospects_table.item(row, 1)
        player_id = name_item.data(Qt.UserRole)

        if not player_id:
            QMessageBox.warning(self, "Error", "Could not get player ID.")
            return

        # Execute pick through controller
        try:
            result = self.controller.execute_user_pick(player_id)
            # Controller already advanced current_pick_index
            self.refresh_all_ui()
            self.advance_to_next_pick()
        except ValueError as e:
            QMessageBox.warning(self, "Pick Error", str(e))

    def on_auto_sim_clicked(self):
        """Simulate until user's next pick."""
        # Disable button during simulation
        self.auto_sim_btn.setEnabled(False)
        self.make_pick_btn.setEnabled(False)

        # Simulate picks until we hit user's turn or end of draft
        self._auto_sim_next_pick()

    def _auto_sim_next_pick(self):
        """Recursively simulate picks until user's turn."""
        if self.controller.current_pick_index >= len(self.controller.draft_order):
            self._show_draft_complete_message()
            self.auto_sim_btn.setEnabled(False)
            return

        current_pick = self.controller.draft_order[self.controller.current_pick_index]

        if current_pick.current_team_id == self.user_team_id:
            # User's turn - stop auto-sim
            self.auto_sim_btn.setEnabled(True)
            self.make_pick_btn.setEnabled(True)
            self.refresh_all_ui()
            return

        # CPU pick - execute and continue
        self.execute_cpu_pick()

        # Schedule next pick after 500ms
        QTimer.singleShot(500, self._auto_sim_next_pick)

    def execute_cpu_pick(self):
        """AI makes a pick."""
        if self.controller.current_pick_index >= len(self.controller.draft_order):
            return

        # Execute AI pick through controller
        try:
            result = self.controller.execute_ai_pick()
            # Controller already advanced current_pick_index
            self.refresh_all_ui()

            # If next pick is CPU and not auto-simming, continue
            if self.controller.current_pick_index < len(self.controller.draft_order):
                next_pick = self.controller.draft_order[self.controller.current_pick_index]
                if next_pick.current_team_id != self.user_team_id and not self.auto_sim_btn.isEnabled():
                    # Continue CPU picks
                    QTimer.singleShot(1000, self.execute_cpu_pick)
        except Exception as e:
            print(f"Error executing AI pick: {e}")

    def refresh_all_ui(self):
        """Refresh all UI components."""
        if self.controller.is_draft_complete():
            self.current_pick_label.setText("DRAFT COMPLETE")
            self.make_pick_btn.setEnabled(False)
            self.auto_sim_btn.setEnabled(False)
            return

        if self.controller.current_pick_index >= len(self.controller.draft_order):
            return

        # Update current pick label
        current_pick = self.controller.draft_order[self.controller.current_pick_index]
        team = get_team_by_id(current_pick.current_team_id)
        team_name = team.full_name if team else f"Team {current_pick.current_team_id}"

        pick_text = (
            f"Round {current_pick.round_number}, Pick {current_pick.pick_in_round} "
            f"(Overall: {current_pick.overall_pick}) - {team_name}"
        )
        self.current_pick_label.setText(pick_text)

        # Refresh tables
        self.populate_prospects_table()
        self.populate_team_needs()
        self.populate_pick_history()

        # Update button states
        is_user_turn = current_pick.current_team_id == self.user_team_id
        self.make_pick_btn.setEnabled(is_user_turn)
        self.auto_sim_btn.setEnabled(not self.controller.is_draft_complete())

    def _show_draft_complete_message(self):
        """Show draft completion message with summary."""
        # Count picks by team
        all_prospects = self.controller.draft_api.get_all_prospects(
            dynasty_id=self.controller.dynasty_id,
            season=self.controller.season,
            available_only=False
        )

        team_picks = {}
        for prospect in all_prospects:
            if prospect.get('is_drafted'):
                team_id = prospect.get('drafted_by_team_id')
                if team_id:
                    team_picks[team_id] = team_picks.get(team_id, 0) + 1

        user_picks = team_picks.get(self.user_team_id, 0)

        message = (
            f"The {self.controller.season} NFL Draft is complete!\n\n"
            f"Total picks made: {sum(team_picks.values())}\n"
            f"Your picks: {user_picks}\n\n"
            f"All prospects have been drafted."
        )

        QMessageBox.information(self, "Draft Complete", message)
