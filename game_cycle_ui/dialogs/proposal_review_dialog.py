"""
Proposal Review Dialog - Main dialog for owner to review GM proposals.

Part of Tollgate 4: Approval UI.

Features:
- Navigation (Previous/Next) for multiple proposals
- Dynamic widget selection based on proposal_type
- Confidence meter (QProgressBar styled)
- GM reasoning panel
- Action buttons: Approve, Reject, Skip
- Decision tracking with rejection notes
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGroupBox,
    QProgressBar,
    QInputDialog,
    QMessageBox,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Signal, Qt

from game_cycle.models.persistent_gm_proposal import PersistentGMProposal
from game_cycle.models.proposal_enums import ProposalStatus
from game_cycle_ui.theme import (
    Typography,
    FontSizes,
    Colors,
    TextColors,
    PRIMARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)
from .proposal_widgets import create_proposal_widget


@dataclass
class ProposalDecision:
    """Represents a decision on a proposal."""

    proposal_id: str
    approved: Optional[bool]  # True=approved, False=rejected, None=skipped
    notes: Optional[str] = None


class ProposalReviewDialog(QDialog):
    """
    Dialog for reviewing and deciding on GM proposals.

    Supports navigation through multiple proposals with type-specific
    content rendering.

    Signals:
        proposals_resolved: Emitted with list of decisions when dialog closes
    """

    proposals_resolved = Signal(list)  # List[ProposalDecision]

    def __init__(
        self,
        proposals: List[PersistentGMProposal],
        stage_name: str = "Proposal Review",
        parent=None,
    ):
        """
        Initialize the proposal review dialog.

        Args:
            proposals: List of proposals to review
            stage_name: Display name for the current stage
            parent: Parent widget
        """
        super().__init__(parent)

        self._proposals = proposals
        self._stage_name = stage_name
        self._current_index = 0
        self._decisions: List[ProposalDecision] = [
            ProposalDecision(proposal_id=p.proposal_id, approved=None)
            for p in proposals
        ]
        self._content_widget: Optional[QWidget] = None

        self._setup_ui()
        self._load_proposal(0)

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle(f"GM Proposals - {self._stage_name}")
        self.setMinimumSize(750, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header with stage name and counter
        header_layout = QHBoxLayout()

        title_label = QLabel(f"GM PROPOSAL - {self._stage_name.upper()}")
        title_label.setFont(Typography.H3)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self._counter_label = QLabel("1 of 1")
        self._counter_label.setFont(Typography.H5)
        self._counter_label.setStyleSheet(f"color: {Colors.MUTED};")
        header_layout.addWidget(self._counter_label)

        layout.addLayout(header_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #444;")
        layout.addWidget(sep)

        # Proposal Type Header
        self._type_label = QLabel("PROPOSAL TYPE")
        self._type_label.setFont(Typography.H4)
        self._type_label.setStyleSheet(f"color: {Colors.INFO};")
        layout.addWidget(self._type_label)

        # Content Area (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._content_container)
        layout.addWidget(scroll, 1)

        # GM Reasoning
        reasoning_group = QGroupBox("GM Reasoning")
        reasoning_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #444; "
            "border-radius: 4px; margin-top: 8px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 5px; }"
        )
        reasoning_layout = QVBoxLayout(reasoning_group)

        self._reasoning_label = QLabel("")
        self._reasoning_label.setWordWrap(True)
        self._reasoning_label.setFont(Typography.BODY)
        self._reasoning_label.setStyleSheet(
            f"color: {TextColors.ON_DARK}; font-style: italic;"
        )
        reasoning_layout.addWidget(self._reasoning_label)

        layout.addWidget(reasoning_group)

        # Confidence Meter
        confidence_layout = QHBoxLayout()

        confidence_title = QLabel("GM Confidence:")
        confidence_title.setFont(Typography.BODY_BOLD)
        confidence_layout.addWidget(confidence_title)

        self._confidence_bar = QProgressBar()
        self._confidence_bar.setRange(0, 100)
        self._confidence_bar.setFixedHeight(18)
        self._confidence_bar.setTextVisible(True)
        self._confidence_bar.setFormat("%v%")
        confidence_layout.addWidget(self._confidence_bar, 1)

        layout.addLayout(confidence_layout)

        # Action Buttons
        action_frame = QFrame()
        action_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 4px; padding: 8px; }"
        )
        action_layout = QHBoxLayout(action_frame)
        action_layout.setSpacing(12)

        self._approve_btn = QPushButton("Approve")
        self._approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._approve_btn.clicked.connect(self._on_approve)
        action_layout.addWidget(self._approve_btn)

        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self._reject_btn.clicked.connect(self._on_reject)
        action_layout.addWidget(self._reject_btn)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        self._skip_btn.clicked.connect(self._on_skip)
        action_layout.addWidget(self._skip_btn)

        action_layout.addStretch()

        # Decision status indicator
        self._status_label = QLabel("")
        self._status_label.setFont(Typography.BODY_BOLD)
        action_layout.addWidget(self._status_label)

        layout.addWidget(action_frame)

        # Navigation
        nav_frame = QFrame()
        nav_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 4px; padding: 8px; }"
        )
        nav_layout = QHBoxLayout(nav_frame)

        self._prev_btn = QPushButton("Previous")
        self._prev_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._prev_btn.clicked.connect(self._on_previous)
        nav_layout.addWidget(self._prev_btn)

        nav_layout.addStretch()

        self._next_btn = QPushButton("Next")
        self._next_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._next_btn.clicked.connect(self._on_next)
        nav_layout.addWidget(self._next_btn)

        self._done_btn = QPushButton("Done")
        self._done_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._done_btn.clicked.connect(self._on_done)
        nav_layout.addWidget(self._done_btn)

        layout.addWidget(nav_frame)

    def _load_proposal(self, index: int) -> None:
        """Load and display the proposal at the given index."""
        if not 0 <= index < len(self._proposals):
            return

        self._current_index = index
        proposal = self._proposals[index]

        # Update counter
        self._counter_label.setText(f"{index + 1} of {len(self._proposals)}")

        # Update type header
        self._type_label.setText(proposal.get_type_display().upper())

        # Clear and recreate content widget
        if self._content_widget:
            self._content_widget.deleteLater()

        self._content_widget = create_proposal_widget(proposal)
        self._content_layout.addWidget(self._content_widget)

        # Update reasoning
        self._reasoning_label.setText(f'"{proposal.gm_reasoning}"')

        # Update confidence bar
        confidence_pct = int(proposal.confidence * 100)
        self._confidence_bar.setValue(confidence_pct)
        self._update_confidence_color(confidence_pct)

        # Update navigation buttons
        self._prev_btn.setEnabled(index > 0)
        self._next_btn.setEnabled(index < len(self._proposals) - 1)

        # Update action buttons based on existing decision
        self._update_decision_display()

    def _update_confidence_color(self, confidence: int) -> None:
        """Set confidence bar color based on level."""
        if confidence >= 70:
            color = Colors.SUCCESS
        elif confidence >= 40:
            color = Colors.INFO
        else:
            color = Colors.MUTED

        self._confidence_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; }}"
            f"QProgressBar {{ border: 1px solid #444; border-radius: 3px; }}"
        )

    def _update_decision_display(self) -> None:
        """Update action buttons and status based on current decision."""
        decision = self._decisions[self._current_index]

        if decision.approved is True:
            self._status_label.setText("APPROVED")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            self._approve_btn.setText("Approved")
            self._approve_btn.setEnabled(False)
            self._reject_btn.setText("Reject (Undo)")
            self._reject_btn.setEnabled(True)
            self._skip_btn.setEnabled(False)
        elif decision.approved is False:
            self._status_label.setText("REJECTED")
            self._status_label.setStyleSheet(f"color: {Colors.ERROR};")
            self._approve_btn.setText("Approve (Undo)")
            self._approve_btn.setEnabled(True)
            self._reject_btn.setText("Rejected")
            self._reject_btn.setEnabled(False)
            self._skip_btn.setEnabled(False)
        else:
            self._status_label.setText("PENDING")
            self._status_label.setStyleSheet(f"color: {Colors.WARNING};")
            self._approve_btn.setText("Approve")
            self._approve_btn.setEnabled(True)
            self._reject_btn.setText("Reject")
            self._reject_btn.setEnabled(True)
            self._skip_btn.setEnabled(True)

    def _on_approve(self) -> None:
        """Handle approve button click."""
        decision = self._decisions[self._current_index]

        if decision.approved is True:
            # Already approved, do nothing
            return

        # Check if undoing a rejection
        if decision.approved is False:
            decision.approved = None
            decision.notes = None
        else:
            decision.approved = True
            decision.notes = None

        self._update_decision_display()

        if decision.approved is True:
            self._advance_to_next()

    def _on_reject(self) -> None:
        """Handle reject button click."""
        decision = self._decisions[self._current_index]

        if decision.approved is False:
            # Already rejected, do nothing
            return

        # Check if undoing an approval
        if decision.approved is True:
            decision.approved = None
            decision.notes = None
            self._update_decision_display()
            return

        # Get rejection notes
        notes, ok = QInputDialog.getMultiLineText(
            self,
            "Rejection Notes",
            "Why are you rejecting this proposal? (optional)\n\n"
            "This helps the GM generate better alternatives.",
            "",
        )

        if ok:  # User didn't cancel
            decision.approved = False
            decision.notes = notes if notes.strip() else None
            self._update_decision_display()
            self._advance_to_next()

    def _on_skip(self) -> None:
        """Handle skip button click."""
        self._advance_to_next()

    def _advance_to_next(self) -> None:
        """Move to the next proposal, or finish if at the end."""
        if self._current_index < len(self._proposals) - 1:
            self._load_proposal(self._current_index + 1)
        else:
            # At the end, check if all reviewed
            pending = sum(1 for d in self._decisions if d.approved is None)
            if pending > 0:
                QMessageBox.information(
                    self,
                    "Review Complete",
                    f"You've reached the end. {pending} proposal(s) still pending.\n"
                    "Use Previous to review again, or click Done to finish.",
                )

    def _on_previous(self) -> None:
        """Handle previous button click."""
        if self._current_index > 0:
            self._load_proposal(self._current_index - 1)

    def _on_next(self) -> None:
        """Handle next button click."""
        if self._current_index < len(self._proposals) - 1:
            self._load_proposal(self._current_index + 1)

    def _on_done(self) -> None:
        """Handle done button click."""
        # Check for pending decisions
        pending = sum(1 for d in self._decisions if d.approved is None)

        if pending > 0:
            result = QMessageBox.question(
                self,
                "Pending Proposals",
                f"You have {pending} proposal(s) still pending.\n\n"
                "Pending proposals will remain for later review.\n"
                "Do you want to finish?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result != QMessageBox.Yes:
                return

        self.proposals_resolved.emit(self._decisions)
        self.accept()

    # =========================================================================
    # Public Methods
    # =========================================================================

    def get_decisions(self) -> List[ProposalDecision]:
        """Get all decisions made."""
        return self._decisions

    def get_approved_proposals(self) -> List[PersistentGMProposal]:
        """Get list of approved proposals."""
        return [
            self._proposals[i]
            for i, d in enumerate(self._decisions)
            if d.approved is True
        ]

    def get_rejected_proposals(self) -> List[PersistentGMProposal]:
        """Get list of rejected proposals."""
        return [
            self._proposals[i]
            for i, d in enumerate(self._decisions)
            if d.approved is False
        ]

    def get_pending_proposals(self) -> List[PersistentGMProposal]:
        """Get list of skipped/pending proposals."""
        return [
            self._proposals[i]
            for i, d in enumerate(self._decisions)
            if d.approved is None
        ]