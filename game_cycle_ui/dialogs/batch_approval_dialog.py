"""
Batch Approval Dialog - Dialog for bulk proposal approval.

Part of Tollgate 4: Approval UI.

Used for stages with many similar proposals (e.g., roster cuts)
where individual review would be tedious.

Features:
- Checkbox list with one-line summaries
- Select All / Deselect All
- Running totals (e.g., total cap savings)
- Approve Selected / Cancel
"""

from typing import List, Tuple, Callable, Optional, Union
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Signal, Qt

from game_cycle.models.persistent_gm_proposal import PersistentGMProposal
from game_cycle_ui.theme import (
    Typography,
    Colors,
    PRIMARY_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)
from .proposal_widgets import create_proposal_widget


@dataclass
class ProposalSection:
    """Represents a section of proposals in batch dialog."""

    title: str
    proposals: List[PersistentGMProposal]
    icon: str = ""
    description: str = ""


@dataclass
class BatchDecision:
    """Represents a batch decision on a proposal."""

    proposal_id: str
    approved: bool


class BatchApprovalDialog(QDialog):
    """
    Dialog for bulk approval of multiple proposals.

    Shows checkbox list with summaries and running totals.

    Signals:
        batch_resolved: Emitted with list of (proposal_id, approved) tuples
    """

    batch_resolved = Signal(list)  # List[BatchDecision]

    def __init__(
        self,
        proposals: Optional[List[PersistentGMProposal]] = None,
        sections: Optional[List[ProposalSection]] = None,
        title: str = "Batch Approval",
        description: str = "",
        total_calculator: Optional[Callable[[List[PersistentGMProposal]], str]] = None,
        parent=None,
    ):
        """
        Initialize the batch approval dialog.

        Args:
            proposals: List of proposals to review (legacy, single section)
            sections: List of ProposalSection objects (multi-section support)
            title: Dialog title
            description: Description text shown at top
            total_calculator: Optional function to calculate running total display
            parent: Parent widget

        Note: Provide either proposals OR sections, not both.
        """
        super().__init__(parent)

        # Handle both single-list and multi-section initialization
        if sections is not None:
            # Multi-section mode
            self._sections = sections
            self._proposals = []
            for section in sections:
                self._proposals.extend(section.proposals)
        elif proposals is not None:
            # Single-section mode (backward compatible)
            self._sections = [ProposalSection(title="", proposals=proposals)]
            self._proposals = proposals
        else:
            raise ValueError("Must provide either 'proposals' or 'sections' parameter")

        self._title = title
        self._description = description
        self._total_calculator = total_calculator
        self._checkboxes: List[QCheckBox] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle(self._title)
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title_label = QLabel(self._title.upper())
        title_label.setFont(Typography.H3)
        layout.addWidget(title_label)

        # Description
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setWordWrap(True)
            desc_label.setFont(Typography.BODY)
            desc_label.setStyleSheet(f"color: {Colors.MUTED};")
            layout.addWidget(desc_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #444;")
        layout.addWidget(sep)

        # Checkbox List (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #444; border-radius: 4px; }"
        )

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setSpacing(8)

        # Render sections with headers
        proposal_index = 0
        for section_idx, section in enumerate(self._sections):
            # Section header (skip if no title - backward compatibility)
            if section.title:
                section_header = QLabel(f"{section.icon} {section.title}".strip())
                section_header.setFont(Typography.H4)
                section_header.setStyleSheet(f"color: {Colors.INFO}; padding: 8px 0 4px 0;")
                list_layout.addWidget(section_header)

            # Section description
            if section.description:
                desc_label = QLabel(section.description)
                desc_label.setFont(Typography.CAPTION)
                desc_label.setStyleSheet(f"color: {Colors.MUTED}; padding-left: 16px; padding-bottom: 8px;")
                desc_label.setWordWrap(True)
                list_layout.addWidget(desc_label)

            # Checkboxes for this section
            for proposal in section.proposals:
                checkbox = self._create_proposal_checkbox(proposal, proposal_index)
                self._checkboxes.append(checkbox)
                list_layout.addWidget(checkbox)
                proposal_index += 1

            # Separator between sections (skip after last section)
            if section_idx < len(self._sections) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("background-color: #333; margin: 8px 0;")
                list_layout.addWidget(sep)

        list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, 1)

        # Select All / Deselect All
        select_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        select_all_btn.clicked.connect(self._select_all)
        select_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(deselect_all_btn)

        select_layout.addStretch()
        layout.addLayout(select_layout)

        # Totals
        totals_frame = QFrame()
        totals_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 4px; padding: 8px; }"
        )
        totals_layout = QHBoxLayout(totals_frame)

        self._count_label = QLabel("0 selected")
        self._count_label.setFont(Typography.BODY_BOLD)
        totals_layout.addWidget(self._count_label)

        totals_layout.addStretch()

        self._total_label = QLabel("")
        self._total_label.setFont(Typography.BODY_BOLD)
        self._total_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        totals_layout.addWidget(self._total_label)

        layout.addWidget(totals_frame)

        # Action Buttons
        action_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)

        action_layout.addStretch()

        self._approve_btn = QPushButton("Approve Selected (0)")
        self._approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._approve_btn.clicked.connect(self._on_approve)
        action_layout.addWidget(self._approve_btn)

        layout.addLayout(action_layout)

        # Update initial totals (must be after all widgets are created)
        self._update_totals()

    def _create_proposal_checkbox(
        self, proposal: PersistentGMProposal, index: int
    ) -> QCheckBox:
        """Create a checkbox for a proposal with summary text."""
        # Get summary from widget
        widget = create_proposal_widget(proposal)
        summary = widget.get_summary()
        widget.deleteLater()

        checkbox = QCheckBox(summary)
        checkbox.setChecked(True)  # Default to selected
        checkbox.setProperty("proposal_index", index)
        checkbox.stateChanged.connect(self._update_totals)

        # Style based on proposal details
        checkbox.setFont(Typography.BODY)

        return checkbox

    def _select_all(self) -> None:
        """Select all checkboxes."""
        for checkbox in self._checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselect all checkboxes."""
        for checkbox in self._checkboxes:
            checkbox.setChecked(False)

    def _update_totals(self) -> None:
        """Update the totals display."""
        selected_count = sum(1 for cb in self._checkboxes if cb.isChecked())

        self._count_label.setText(f"{selected_count} of {len(self._checkboxes)} selected")
        self._approve_btn.setText(f"Approve Selected ({selected_count})")
        self._approve_btn.setEnabled(selected_count > 0)

        # Calculate custom total if calculator provided
        if self._total_calculator:
            selected_proposals = self._get_selected_proposals()
            total_text = self._total_calculator(selected_proposals)
            self._total_label.setText(total_text)

    def _get_selected_proposals(self) -> List[PersistentGMProposal]:
        """Get list of selected proposals."""
        selected = []
        for i, checkbox in enumerate(self._checkboxes):
            if checkbox.isChecked():
                selected.append(self._proposals[i])
        return selected

    def _on_approve(self) -> None:
        """Handle approve button click."""
        decisions = []
        for i, checkbox in enumerate(self._checkboxes):
            decisions.append(
                BatchDecision(
                    proposal_id=self._proposals[i].proposal_id,
                    approved=checkbox.isChecked(),
                )
            )

        self.batch_resolved.emit(decisions)
        self.accept()

    # =========================================================================
    # Public Methods
    # =========================================================================

    def get_selected_proposal_ids(self) -> List[str]:
        """Get IDs of selected proposals."""
        return [
            self._proposals[i].proposal_id
            for i, cb in enumerate(self._checkboxes)
            if cb.isChecked()
        ]

    def get_approved_proposals(self) -> List[PersistentGMProposal]:
        """Get list of selected proposals."""
        return self._get_selected_proposals()


# =============================================================================
# Helper Functions for Common Use Cases
# =============================================================================

def create_roster_cuts_batch_dialog(
    proposals: List[PersistentGMProposal],
    parent=None,
) -> BatchApprovalDialog:
    """
    Factory for roster cuts batch dialog.

    Includes cap savings calculator.
    """

    def calculate_cap_savings(selected: List[PersistentGMProposal]) -> str:
        total_savings = sum(
            p.details.get("cap_savings", 0) for p in selected
        )
        dead_money = sum(
            p.details.get("dead_money", 0) for p in selected
        )
        net = total_savings - dead_money

        if net >= 1_000_000:
            return f"Net Cap Savings: ${net / 1_000_000:,.1f}M"
        elif net >= 1_000:
            return f"Net Cap Savings: ${net / 1_000:,.0f}K"
        else:
            return f"Net Cap Savings: ${net:,}"

    return BatchApprovalDialog(
        proposals=proposals,
        title="Roster Cuts",
        description=f"GM proposes cutting {len(proposals)} players to reach the 53-man roster.",
        total_calculator=calculate_cap_savings,
        parent=parent,
    )


def create_waiver_claims_batch_dialog(
    proposals: List[PersistentGMProposal],
    parent=None,
) -> BatchApprovalDialog:
    """Factory for waiver claims batch dialog."""
    return BatchApprovalDialog(
        proposals=proposals,
        title="Waiver Wire Claims",
        description=f"GM recommends {len(proposals)} waiver claim(s).",
        parent=parent,
    )