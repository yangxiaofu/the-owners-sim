"""
Restructure Dialog - GM-proposed contract restructures for cap space (Owner approval pattern).

Part of Owner-GM Flow: GM analyzes contracts and recommends restructures to create cap space
during re-signing phase. Owner can approve or reject each proposal via toggle switches.

UX Pattern: Toggle switches (like ResigningView extension recommendations)
- Toggle ON (green) = approved (GM recommendation, default)
- Toggle OFF (gray) = rejected (owner override)
- Row dims when rejected
- No confirmation dialogs (instant visual feedback)
- Signals emit on dialog close (batch processing)
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QWidget, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import (
    apply_table_style,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    Colors,
    FontSizes,
    TextColors
)

from game_cycle_ui.utils.table_utils import NumericTableWidgetItem
from constants.position_abbreviations import get_position_abbreviation


class RestructureDialog(QDialog):
    """
    Dialog for reviewing and approving GM-recommended contract restructures.

    Workflow:
    1. Display GM recommendations with cap hit changes and reasoning
    2. All recommendations are pre-approved (toggle ON by default)
    3. Owner toggles OFF to reject individual restructures
    4. Show running total of selected savings
    5. Provide "Select All" to toggle all ON

    Usage:
        proposals = [
            {
                "contract_id": 901,
                "player_name": "Brandon Graham",
                "position": "EDGE",
                "overall": 78,
                "current_cap_hit": 13_500_000,
                "new_cap_hit": 8_500_000,
                "cap_savings": 5_000_000,
                "dead_money_added": 10_000_000,
                "gm_reasoning": "Restructure to create cap flexibility.",
                "proposal_id": "restructure_901"
            }
        ]
        dialog = RestructureDialog(proposals, parent=self)
        dialog.proposal_approved.connect(self._on_restructure_approved)
        dialog.proposal_rejected.connect(self._on_restructure_rejected)
        dialog.exec()
    """

    # Signal emitted when a restructure is approved (emitted on dialog accept)
    proposal_approved = Signal(dict)  # Full proposal dict

    # Signal emitted when a restructure is rejected (emitted on dialog accept)
    proposal_rejected = Signal(dict)  # Full proposal dict

    # Column indices
    COL_PLAYER = 0
    COL_POS = 1
    COL_OVR = 2
    COL_CURRENT_HIT = 3
    COL_NEW_HIT = 4
    COL_SAVINGS = 5
    COL_DEAD_MONEY = 6
    COL_TOGGLE = 7  # Toggle replaces Status + Action columns

    def __init__(
        self,
        proposals: List[Dict],
        parent=None
    ):
        """
        Initialize the restructure dialog.

        Args:
            proposals: List of restructure proposal dicts with keys:
                - contract_id: Unique contract identifier
                - player_name: Player name
                - position: Player position
                - overall: Player OVR rating
                - current_cap_hit: Current cap hit amount
                - new_cap_hit: Cap hit after restructure
                - cap_savings: Immediate cap savings
                - dead_money_added: Dead money added
                - gm_reasoning: GM's reasoning for the recommendation
                - proposal_id: Unique proposal ID (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self._proposals = proposals or []

        # Toggle state tracking: contract_id -> is_approved (True = ON/approved)
        self._toggle_states: Dict[int, bool] = {}
        self._toggle_widgets: Dict[int, QCheckBox] = {}  # For bulk operations

        # Initialize all proposals as approved (toggle ON by default)
        for proposal in self._proposals:
            self._toggle_states[proposal["contract_id"]] = True

        self.setWindowTitle("GM Restructure Recommendations")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._populate_table()
        self._update_summary()

    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header section
        self._create_header(layout)

        # Recommendations table
        self._create_table(layout)

        # Summary section
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: {FontSizes.BODY}; "
            f"font-weight: bold; padding: 8px;"
        )
        layout.addWidget(self.summary_label)

        # Buttons
        self._create_buttons(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header with title and instructions."""
        header = QLabel("GM Restructure Recommendations")
        header.setStyleSheet(
            f"font-size: {FontSizes.H3}; font-weight: bold; color: {Colors.TEXT_PRIMARY};"
        )
        parent_layout.addWidget(header)

        # Dynamic subtitle showing GM summary
        if self._proposals:
            total_savings = sum(p.get("cap_savings", 0) for p in self._proposals)
            self.subtitle_label = QLabel(
                f"Your GM recommends {len(self._proposals)} contract restructure"
                f"{'s' if len(self._proposals) != 1 else ''} "
                f"to save ${total_savings / 1_000_000:.1f}M in cap space."
            )
        else:
            self.subtitle_label = QLabel(
                "Your GM has no restructure recommendations at this time."
            )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.BODY}; padding: 4px 0;"
        )
        parent_layout.addWidget(self.subtitle_label)

        # Info/warning
        info = QLabel(
            "Toggle OFF to reject a restructure. "
            "Restructuring converts salary into signing bonus, spreading the cap hit over future years. "
            "This creates immediate cap space but increases future dead money risk."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION}; padding: 8px; "
            f"background: {Colors.BG_SECONDARY}; border-radius: 4px;"
        )
        parent_layout.addWidget(info)

    def _create_table(self, parent_layout: QVBoxLayout):
        """Create the recommendations table."""
        # Action bar with Select All button
        action_bar = QHBoxLayout()
        action_bar.addWidget(QLabel("Recommendations:"))
        action_bar.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.select_all_btn.clicked.connect(self._on_select_all)
        action_bar.addWidget(self.select_all_btn)

        parent_layout.addLayout(action_bar)

        # Table - 8 columns (removed Status column, Action -> Toggle)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Player", "Pos", "OVR", "Current Hit", "New Hit",
            "Savings", "Dead Money", "Approve"
        ])

        apply_table_style(self.table)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setDefaultSectionSize(48)

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_PLAYER, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_POS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_OVR, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_CURRENT_HIT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_NEW_HIT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_SAVINGS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_DEAD_MONEY, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TOGGLE, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(self.COL_POS, 50)
        self.table.setColumnWidth(self.COL_OVR, 50)
        self.table.setColumnWidth(self.COL_CURRENT_HIT, 100)
        self.table.setColumnWidth(self.COL_NEW_HIT, 100)
        self.table.setColumnWidth(self.COL_SAVINGS, 90)
        self.table.setColumnWidth(self.COL_DEAD_MONEY, 100)
        self.table.setColumnWidth(self.COL_TOGGLE, 80)

        parent_layout.addWidget(self.table, stretch=1)

    def _create_buttons(self, parent_layout: QVBoxLayout):
        """Create bottom button row."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # Cancel button - closes without emitting signals
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        # Confirm button - emits signals for all decisions
        confirm_btn = QPushButton("Confirm Selections")
        confirm_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        parent_layout.addLayout(btn_layout)

    def _get_toggle_stylesheet(self) -> str:
        """Get the stylesheet for toggle checkboxes (iOS-style switches)."""
        return f"""
            QCheckBox {{
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 44px;
                height: 24px;
                border-radius: 12px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SUCCESS};
                border: 2px solid {Colors.SUCCESS};
                image: none;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {Colors.MUTED};
                border: 2px solid {Colors.MUTED};
                image: none;
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {Colors.SUCCESS};
            }}
            QCheckBox::indicator:unchecked:hover {{
                background-color: #6b7280;
            }}
        """

    def _populate_table(self):
        """Populate the recommendations table."""
        if not self._proposals:
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 8)
            msg_item = QTableWidgetItem("No restructure recommendations at this time")
            msg_item.setTextAlignment(Qt.AlignCenter)
            msg_item.setForeground(QColor(Colors.MUTED))
            self.table.setItem(0, 0, msg_item)
            self.select_all_btn.setEnabled(False)
            return

        self.table.setRowCount(len(self._proposals))

        for row, proposal in enumerate(self._proposals):
            self._populate_row(row, proposal)

    def _populate_row(self, row: int, proposal: Dict):
        """Populate a single table row."""
        contract_id = proposal.get("contract_id")
        is_approved = self._toggle_states.get(contract_id, True)

        # Player name (with tooltip for reasoning)
        player_name = proposal.get("player_name", "Unknown")
        name_item = QTableWidgetItem(player_name)
        name_item.setData(Qt.UserRole, proposal)  # Store proposal in UserRole
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name_item.setToolTip(f"GM Reasoning: {proposal.get('gm_reasoning', 'N/A')}")
        self.table.setItem(row, self.COL_PLAYER, name_item)

        # Position
        pos_item = QTableWidgetItem(
            get_position_abbreviation(proposal.get("position", ""))
        )
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, self.COL_POS, pos_item)

        # Overall (color coded)
        ovr = proposal.get("overall", 0)
        ovr_item = NumericTableWidgetItem(ovr)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        ovr_item.setFlags(ovr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if ovr >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif ovr >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.table.setItem(row, self.COL_OVR, ovr_item)

        # Current cap hit
        current_hit = proposal.get("current_cap_hit", 0)
        current_item = QTableWidgetItem(f"${current_hit / 1_000_000:.1f}M")
        current_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        current_item.setFlags(current_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, self.COL_CURRENT_HIT, current_item)

        # New cap hit (after restructure)
        new_hit = proposal.get("new_cap_hit", 0)
        new_item = QTableWidgetItem(f"${new_hit / 1_000_000:.1f}M")
        new_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        new_item.setFlags(new_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        new_item.setForeground(QColor(Colors.SUCCESS))  # Lower is better
        self.table.setItem(row, self.COL_NEW_HIT, new_item)

        # Savings (green, prominent)
        savings = proposal.get("cap_savings", 0)
        savings_text = f"+${savings / 1_000_000:.1f}M"
        savings_item = QTableWidgetItem(savings_text)
        savings_item.setTextAlignment(Qt.AlignCenter)
        savings_item.setForeground(QColor(Colors.SUCCESS))
        savings_item.setFlags(savings_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        font = savings_item.font()
        font.setBold(True)
        savings_item.setFont(font)
        self.table.setItem(row, self.COL_SAVINGS, savings_item)

        # Dead money added (orange/warning)
        dead_money = proposal.get("dead_money_added", 0)
        dead_text = f"+${dead_money / 1_000_000:.1f}M"
        dead_item = QTableWidgetItem(dead_text)
        dead_item.setTextAlignment(Qt.AlignCenter)
        dead_item.setForeground(QColor(Colors.WARNING))
        dead_item.setFlags(dead_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, self.COL_DEAD_MONEY, dead_item)

        # Toggle widget (ON by default = approved)
        self._create_toggle_widget(row, contract_id)

        # Apply initial row styling
        self._apply_row_styling(row, is_approved)

    def _create_toggle_widget(self, row: int, contract_id: int):
        """Create a toggle checkbox for approving/rejecting a proposal."""
        toggle_widget = QWidget()
        toggle_layout = QHBoxLayout(toggle_widget)
        toggle_layout.setContentsMargins(4, 2, 4, 2)
        toggle_layout.setAlignment(Qt.AlignCenter)

        toggle = QCheckBox()
        toggle.setChecked(True)  # Default: approved (GM recommendation)
        toggle.setProperty("contract_id", contract_id)
        toggle.setProperty("row", row)
        toggle.setStyleSheet(self._get_toggle_stylesheet())
        toggle.stateChanged.connect(
            lambda state, cid=contract_id, r=row: self._on_toggle_changed(cid, r, state)
        )

        toggle_layout.addWidget(toggle)
        self.table.setCellWidget(row, self.COL_TOGGLE, toggle_widget)

        # Store reference for bulk operations
        self._toggle_widgets[contract_id] = toggle

    def _on_toggle_changed(self, contract_id: int, row: int, state: int):
        """Handle toggle state change."""
        is_approved = (state == Qt.CheckState.Checked.value)
        self._toggle_states[contract_id] = is_approved
        self._apply_row_styling(row, is_approved)
        self._update_summary()

    def _apply_row_styling(self, row: int, is_approved: bool):
        """Apply styling to row based on approval state (dim rejected rows)."""
        for col in range(self.COL_TOGGLE):  # All columns except toggle
            item = self.table.item(row, col)
            if item:
                if is_approved:
                    # Restore appropriate color based on column
                    if col == self.COL_OVR:
                        ovr = item.data(Qt.DisplayRole)
                        if ovr and int(ovr) >= 85:
                            item.setForeground(QColor(Colors.SUCCESS))
                        elif ovr and int(ovr) >= 75:
                            item.setForeground(QColor(Colors.INFO))
                        else:
                            item.setForeground(QColor(TextColors.ON_DARK))
                    elif col == self.COL_NEW_HIT:
                        item.setForeground(QColor(Colors.SUCCESS))
                    elif col == self.COL_SAVINGS:
                        item.setForeground(QColor(Colors.SUCCESS))
                    elif col == self.COL_DEAD_MONEY:
                        item.setForeground(QColor(Colors.WARNING))
                    else:
                        item.setForeground(QColor(TextColors.ON_DARK))
                else:
                    # Dim the row
                    item.setForeground(QColor(Colors.MUTED))

    def _on_select_all(self):
        """Toggle all proposals to ON (approved)."""
        for contract_id, toggle in self._toggle_widgets.items():
            toggle.setChecked(True)
            # State change handler will update _toggle_states and styling

    def _update_summary(self):
        """Update the summary label showing selected restructures and savings."""
        if not self._proposals:
            self.summary_label.setText("")
            return

        approved_count = sum(1 for v in self._toggle_states.values() if v)
        approved_savings = sum(
            p.get("cap_savings", 0)
            for p in self._proposals
            if self._toggle_states.get(p["contract_id"], False)
        )

        if approved_count == 0:
            self.summary_label.setText("No restructures selected")
            self.summary_label.setStyleSheet(
                f"color: {Colors.MUTED}; font-size: {FontSizes.BODY}; "
                f"font-weight: normal; padding: 8px;"
            )
        else:
            plural = "s" if approved_count != 1 else ""
            self.summary_label.setText(
                f"{approved_count} restructure{plural} selected "
                f"(+${approved_savings / 1_000_000:.1f}M savings)"
            )
            self.summary_label.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-size: {FontSizes.BODY}; "
                f"font-weight: bold; padding: 8px;"
            )

        # Update Select All button state
        all_selected = all(self._toggle_states.values()) if self._toggle_states else True
        self.select_all_btn.setEnabled(not all_selected)

    def accept(self):
        """
        Handle dialog acceptance - emit signals for all decisions.

        Approved proposals emit proposal_approved signal.
        Rejected proposals emit proposal_rejected signal.
        """
        for proposal in self._proposals:
            contract_id = proposal.get("contract_id")
            is_approved = self._toggle_states.get(contract_id, True)

            if is_approved:
                self.proposal_approved.emit(proposal)
            else:
                self.proposal_rejected.emit(proposal)

        super().accept()

    def get_approved_proposals(self) -> List[Dict]:
        """Get list of approved proposals (toggle ON)."""
        return [
            p for p in self._proposals
            if self._toggle_states.get(p["contract_id"], True)
        ]

    def get_rejected_proposals(self) -> List[Dict]:
        """Get list of rejected proposals (toggle OFF)."""
        return [
            p for p in self._proposals
            if not self._toggle_states.get(p["contract_id"], True)
        ]
