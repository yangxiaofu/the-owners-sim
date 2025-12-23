"""
IR Activation View - Weekly IR activation roster management.

Shows players eligible to return from IR and allows batch activation decisions
with corresponding roster cuts to make room.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from game_cycle_ui.theme import apply_table_style, Colors, Typography, FontSizes, TextColors


class IRActivationView(QWidget):
    """
    View for weekly IR activation decisions.

    Shows two tables:
    1. Eligible IR players (with activate checkboxes and cut selection dropdowns)
    2. Cut candidates (reference table showing player values)

    User selects which players to activate and which to cut, then processes all decisions atomically.
    """

    # Signals
    activations_complete = Signal(dict)  # Emits result summary after processing
    skip_all = Signal()  # User chose to skip all activations this week

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._eligible_players: List[Dict] = []
        self._cut_candidates: List[Dict] = []
        self._current_week: int = 0
        self._ir_slots_remaining: int = 0
        self._roster_count: int = 0
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel(f"Injured Reserve Activations")
        title.setFont(Typography.H3)
        layout.addWidget(title)

        # Summary panel
        self._create_summary_panel(layout)

        # Eligible players table
        self._create_eligible_players_table(layout)

        # Cut candidates table (reference)
        self._create_cut_candidates_table(layout)

        # Action buttons
        self._create_action_buttons(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary panel showing IR status and roster info."""
        summary_group = QGroupBox("Weekly IR Status")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # IR Slots Remaining
        slots_frame = QFrame()
        slots_layout = QVBoxLayout(slots_frame)
        slots_layout.setContentsMargins(0, 0, 0, 0)

        slots_title = QLabel("IR Return Slots")
        slots_title.setFont(Typography.CAPTION)
        slots_title.setStyleSheet(f"color: {Colors.MUTED};")
        slots_layout.addWidget(slots_title)

        self._ir_slots_label = QLabel("0 / 8")
        self._ir_slots_label.setFont(Typography.H4)
        slots_layout.addWidget(self._ir_slots_label)

        summary_layout.addWidget(slots_frame)

        # Roster Count
        roster_frame = QFrame()
        roster_layout = QVBoxLayout(roster_frame)
        roster_layout.setContentsMargins(0, 0, 0, 0)

        roster_title = QLabel("Active Roster")
        roster_title.setFont(Typography.CAPTION)
        roster_title.setStyleSheet(f"color: {Colors.MUTED};")
        roster_layout.addWidget(roster_title)

        self._roster_count_label = QLabel("53 / 53")
        self._roster_count_label.setFont(Typography.H4)
        roster_layout.addWidget(self._roster_count_label)

        summary_layout.addWidget(roster_frame)

        # Eligible Returns
        eligible_frame = QFrame()
        eligible_layout = QVBoxLayout(eligible_frame)
        eligible_layout.setContentsMargins(0, 0, 0, 0)

        eligible_title = QLabel("Eligible Returns")
        eligible_title.setFont(Typography.CAPTION)
        eligible_title.setStyleSheet(f"color: {Colors.MUTED};")
        eligible_layout.addWidget(eligible_title)

        self._eligible_count_label = QLabel("0")
        self._eligible_count_label.setFont(Typography.H4)
        self._eligible_count_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        eligible_layout.addWidget(self._eligible_count_label)

        summary_layout.addWidget(eligible_frame)

        # Decisions Made
        decisions_frame = QFrame()
        decisions_layout = QVBoxLayout(decisions_frame)
        decisions_layout.setContentsMargins(0, 0, 0, 0)

        decisions_title = QLabel("Decisions Made")
        decisions_title.setFont(Typography.CAPTION)
        decisions_title.setStyleSheet(f"color: {Colors.MUTED};")
        decisions_layout.addWidget(decisions_title)

        self._decisions_label = QLabel("0 / 0")
        self._decisions_label.setFont(Typography.H4)
        self._decisions_label.setStyleSheet(f"color: {Colors.INFO};")
        decisions_layout.addWidget(self._decisions_label)

        summary_layout.addWidget(decisions_frame)

        parent_layout.addWidget(summary_group)

    def _create_eligible_players_table(self, parent_layout: QVBoxLayout):
        """Create table showing players eligible to return from IR."""
        group = QGroupBox("Players Eligible to Return from IR")
        layout = QVBoxLayout(group)

        self._eligible_table = QTableWidget()
        self._eligible_table.setColumnCount(8)
        self._eligible_table.setHorizontalHeaderLabels([
            "Activate", "Player", "Pos", "OVR", "Weeks on IR",
            "Injury", "Est. Return", "Cut Player"
        ])

        # Set column widths
        header = self._eligible_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Activate checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Player name
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Position
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # OVR
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Weeks on IR
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Injury
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Est. Return
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Cut dropdown

        self._eligible_table.setColumnWidth(0, 70)   # Activate
        self._eligible_table.setColumnWidth(2, 50)   # Pos
        self._eligible_table.setColumnWidth(3, 50)   # OVR
        self._eligible_table.setColumnWidth(4, 100)  # Weeks on IR
        self._eligible_table.setColumnWidth(6, 80)   # Est. Return

        # Apply standard table styling
        apply_table_style(self._eligible_table)
        self._eligible_table.setSelectionMode(QTableWidget.NoSelection)

        layout.addWidget(self._eligible_table)
        parent_layout.addWidget(group)

    def _create_cut_candidates_table(self, parent_layout: QVBoxLayout):
        """Create reference table showing potential cut candidates sorted by value."""
        group = QGroupBox("Cut Candidates (Sorted by Value - Lowest First)")
        layout = QVBoxLayout(group)

        instructions = QLabel(
            "These are potential players to cut, sorted by value (lowest = best cut candidates). "
            "Select from the dropdown in the table above."
        )
        instructions.setFont(Typography.CAPTION)
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {Colors.MUTED}; padding: 5px;")
        layout.addWidget(instructions)

        self._candidates_table = QTableWidget()
        self._candidates_table.setColumnCount(7)
        self._candidates_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Value Score",
            "Cap Hit", "Protected"
        ])

        # Set column widths
        header = self._candidates_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # Position
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # Age
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # OVR
        header.setSectionResizeMode(4, QHeaderView.Fixed)    # Value Score
        header.setSectionResizeMode(5, QHeaderView.Fixed)    # Cap Hit
        header.setSectionResizeMode(6, QHeaderView.Fixed)    # Protected

        self._candidates_table.setColumnWidth(1, 50)   # Pos
        self._candidates_table.setColumnWidth(2, 50)   # Age
        self._candidates_table.setColumnWidth(3, 50)   # OVR
        self._candidates_table.setColumnWidth(4, 100)  # Value Score
        self._candidates_table.setColumnWidth(5, 100)  # Cap Hit
        self._candidates_table.setColumnWidth(6, 80)   # Protected

        # Apply standard table styling
        apply_table_style(self._candidates_table)
        self._candidates_table.setSelectionMode(QTableWidget.NoSelection)
        self._candidates_table.setMaximumHeight(250)  # Limit height (reference table)

        layout.addWidget(self._candidates_table)
        parent_layout.addWidget(group)

    def _create_action_buttons(self, parent_layout: QVBoxLayout):
        """Create action buttons at bottom."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._skip_button = QPushButton("Skip All Activations")
        self._skip_button.setMinimumWidth(180)
        self._skip_button.clicked.connect(self._on_skip_all)
        button_layout.addWidget(self._skip_button)

        self._process_button = QPushButton("Process Activations")
        self._process_button.setMinimumWidth(180)
        self._process_button.setEnabled(False)  # Disabled until decisions made
        self._process_button.clicked.connect(self._on_process_activations)
        button_layout.addWidget(self._process_button)

        parent_layout.addLayout(button_layout)

    def load_data(
        self,
        eligible_players: List[Dict],
        cut_candidates: List[Dict],
        current_week: int,
        ir_slots_remaining: int,
        roster_count: int
    ):
        """
        Load IR activation data into the view.

        Args:
            eligible_players: List of players eligible to return from IR
            cut_candidates: List of potential cut candidates (sorted by value)
            current_week: Current week number
            ir_slots_remaining: IR return slots available (0-8)
            roster_count: Current active roster count
        """
        self._eligible_players = eligible_players
        self._cut_candidates = cut_candidates
        self._current_week = current_week
        self._ir_slots_remaining = ir_slots_remaining
        self._roster_count = roster_count

        # Update summary labels
        self._ir_slots_label.setText(f"{ir_slots_remaining} / 8")
        if ir_slots_remaining > 0:
            self._ir_slots_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self._ir_slots_label.setStyleSheet(f"color: {Colors.ERROR};")

        self._roster_count_label.setText(f"{roster_count} / 53")
        if roster_count >= 53:
            self._roster_count_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self._roster_count_label.setStyleSheet(f"color: {Colors.SUCCESS};")

        self._eligible_count_label.setText(str(len(eligible_players)))
        self._decisions_label.setText(f"0 / {len(eligible_players)}")

        # Populate tables
        self._populate_eligible_players_table()
        self._populate_cut_candidates_table()

    def _populate_eligible_players_table(self):
        """Populate the eligible players table with checkboxes and dropdowns."""
        self._eligible_table.setRowCount(len(self._eligible_players))

        for row, player in enumerate(self._eligible_players):
            # Activate checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(self._on_selection_changed)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self._eligible_table.setCellWidget(row, 0, checkbox_widget)

            # Player name
            self._eligible_table.setItem(row, 1, QTableWidgetItem(player["player_name"]))

            # Position
            self._eligible_table.setItem(row, 2, QTableWidgetItem(player["position"]))

            # Overall
            ovr_item = QTableWidgetItem(str(player["overall"]))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            self._eligible_table.setItem(row, 3, ovr_item)

            # Weeks on IR
            weeks_item = QTableWidgetItem(str(player["weeks_on_ir"]))
            weeks_item.setTextAlignment(Qt.AlignCenter)
            self._eligible_table.setItem(row, 4, weeks_item)

            # Injury type
            self._eligible_table.setItem(row, 5, QTableWidgetItem(player["injury_type"]))

            # Estimated return week
            est_return = QTableWidgetItem(f"Week {player['estimated_return_week']}")
            est_return.setTextAlignment(Qt.AlignCenter)
            self._eligible_table.setItem(row, 6, est_return)

            # Cut player dropdown
            cut_dropdown = QComboBox()
            cut_dropdown.addItem("-- Select player to cut --", None)

            for candidate in self._cut_candidates:
                if candidate.get("protected", False):
                    label = f"{candidate['player_name']} ({candidate['position']}, {candidate['overall']} OVR) [PROTECTED]"
                    cut_dropdown.addItem(label, candidate["player_id"])
                    # Disable protected items
                    cut_dropdown.model().item(cut_dropdown.count() - 1).setEnabled(False)
                else:
                    label = f"{candidate['player_name']} ({candidate['position']}, {candidate['overall']} OVR, Value: {candidate['value_score']:.1f})"
                    cut_dropdown.addItem(label, candidate["player_id"])

            cut_dropdown.currentIndexChanged.connect(self._on_selection_changed)
            self._eligible_table.setCellWidget(row, 7, cut_dropdown)

    def _populate_cut_candidates_table(self):
        """Populate the cut candidates reference table."""
        self._candidates_table.setRowCount(len(self._cut_candidates))

        for row, candidate in enumerate(self._cut_candidates):
            # Player name
            self._candidates_table.setItem(row, 0, QTableWidgetItem(candidate["player_name"]))

            # Position
            self._candidates_table.setItem(row, 1, QTableWidgetItem(candidate["position"]))

            # Age
            age_item = QTableWidgetItem(str(candidate["age"]))
            age_item.setTextAlignment(Qt.AlignCenter)
            self._candidates_table.setItem(row, 2, age_item)

            # Overall
            ovr_item = QTableWidgetItem(str(candidate["overall"]))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            self._candidates_table.setItem(row, 3, ovr_item)

            # Value Score
            value_item = QTableWidgetItem(f"{candidate['value_score']:.1f}")
            value_item.setTextAlignment(Qt.AlignCenter)
            self._candidates_table.setItem(row, 4, value_item)

            # Cap Hit (format as currency)
            cap_hit = candidate["cap_hit"]
            cap_item = QTableWidgetItem(f"${cap_hit:,.0f}")
            cap_item.setTextAlignment(Qt.AlignCenter)
            self._candidates_table.setItem(row, 5, cap_item)

            # Protected status
            protected_item = QTableWidgetItem("Yes" if candidate.get("protected", False) else "No")
            protected_item.setTextAlignment(Qt.AlignCenter)
            if candidate.get("protected", False):
                protected_item.setForeground(QBrush(QColor(Colors.ERROR)))
            self._candidates_table.setItem(row, 6, protected_item)

    def _on_selection_changed(self):
        """Handle selection changes - validate and enable/disable Process button."""
        decisions_made = 0
        all_valid = True

        for row in range(self._eligible_table.rowCount()):
            checkbox_widget = self._eligible_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            cut_dropdown = self._eligible_table.cellWidget(row, 7)

            if checkbox.isChecked():
                decisions_made += 1
                # Validate that a cut player is selected
                if cut_dropdown.currentData() is None:
                    all_valid = False

        # Update decisions label
        total = len(self._eligible_players)
        self._decisions_label.setText(f"{decisions_made} / {total}")

        # Enable Process button only if at least one decision made and all are valid
        self._process_button.setEnabled(decisions_made > 0 and all_valid)

    def _on_skip_all(self):
        """User clicked Skip All Activations button."""
        self.skip_all.emit()

    def _on_process_activations(self):
        """User clicked Process Activations button - gather decisions and emit."""
        activations = []

        for row in range(self._eligible_table.rowCount()):
            checkbox_widget = self._eligible_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            cut_dropdown = self._eligible_table.cellWidget(row, 7)

            if checkbox.isChecked():
                player_to_activate = self._eligible_players[row]["player_id"]
                player_to_cut = cut_dropdown.currentData()

                if player_to_cut is not None:
                    activations.append({
                        "player_to_activate": player_to_activate,
                        "player_to_cut": player_to_cut
                    })

        # Emit the batch activation request
        self.activations_complete.emit({
            "activations": activations,
            "current_week": self._current_week
        })
