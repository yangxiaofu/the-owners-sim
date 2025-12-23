"""
GM Proposal Notification Dialog - Real-time GM free agency proposal approval.

Part of Milestone 10: GM-Driven Free Agency with Owner Oversight.
Phase 1 MVP: Approve/Reject buttons (Counter-offer in Phase 3).
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from game_cycle.models import GMProposal
from game_cycle_ui.theme import (
    Colors,
    Typography,
    FontSizes,
    PRIMARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
)
from game_cycle_ui.widgets import (
    ValuationBreakdownWidget,
    GMStyleBadge,
    PressureLevelIndicator,
    CollapsibleSection,
)
from game_cycle_ui.widgets.stat_frame import create_stat_display


class GMProposalNotificationDialog(QDialog):
    """
    Dialog for reviewing and approving/rejecting GM free agency proposals.

    Shows one proposal at a time with navigation if multiple proposals exist.
    Owner can approve, reject, or modify each proposal.

    Signals:
        proposal_approved: GMProposal that was approved
        proposal_rejected: GMProposal that was rejected
        proposal_modify_clicked: User wants to modify terms (GMProposal)
    """

    proposal_approved = Signal(object)  # GMProposal
    proposal_rejected = Signal(object)  # GMProposal
    proposal_modify_clicked = Signal(object)  # GMProposal to modify

    def __init__(
        self,
        proposals: List[GMProposal],
        gm_name: str = "Your GM",
        parent=None
    ):
        """
        Initialize proposal notification dialog.

        Args:
            proposals: List of GMProposal objects to review (1-3)
            gm_name: Name of the GM making proposals
            parent: Parent widget
        """
        super().__init__(parent)
        self._proposals = proposals
        self._gm_name = gm_name
        self._current_index = 0
        self._decisions: List[Optional[bool]] = [None] * len(proposals)  # True=approve, False=reject

        self.setWindowTitle(f"GM Proposal - {gm_name}")
        self.setMinimumSize(700, 650)
        self.setModal(True)

        self._setup_ui()
        self._show_proposal(0)

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel(f"GM PROPOSAL - {self._gm_name}")
        header.setFont(Typography.H5)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Info text
        info = QLabel(
            "Your GM has identified a free agent target and is requesting your approval "
            "for this signing. Review the proposal and decide whether to approve or reject."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.CAPTION}; padding: 8px;")
        layout.addWidget(info)

        # Player info panel
        self._create_player_panel(layout)

        # Contract terms panel
        self._create_contract_panel(layout)

        # GM reasoning panels
        self._create_pitch_panel(layout)
        self._create_rationale_panel(layout)

        # Valuation breakdown section (collapsible)
        self._create_valuation_section(layout)

        # Cap impact panel
        self._create_cap_impact_panel(layout)

        layout.addStretch()

        # Navigation (if multiple proposals)
        if len(self._proposals) > 1:
            self._create_navigation(layout)

        # Action buttons
        self._create_action_buttons(layout)

    def _create_player_panel(self, parent_layout: QVBoxLayout):
        """Create panel showing player information."""
        player_group = QGroupBox("Player Information")
        player_layout = QHBoxLayout(player_group)
        player_layout.setSpacing(20)

        # Name & Position
        self._player_name_label = self._create_stat_frame(
            player_layout, "Player", "Unknown"
        )

        # Age
        self._player_age_label = self._create_stat_frame(
            player_layout, "Age", "0"
        )

        # Overall Rating
        self._player_rating_label = self._create_stat_frame(
            player_layout, "Overall", "0"
        )

        # Tier
        self._player_tier_label = self._create_stat_frame(
            player_layout, "Tier", "Unknown"
        )

        # Need addressed
        self._need_label = self._create_stat_frame(
            player_layout, "Need Addressed", ""
        )

        player_layout.addStretch()
        parent_layout.addWidget(player_group)

    def _create_contract_panel(self, parent_layout: QVBoxLayout):
        """Create panel showing proposed contract terms."""
        contract_group = QGroupBox("Proposed Contract Terms")
        contract_layout = QHBoxLayout(contract_group)
        contract_layout.setSpacing(20)

        # AAV
        self._aav_label = self._create_stat_frame(
            contract_layout, "AAV", "$0"
        )

        # Years
        self._years_label = self._create_stat_frame(
            contract_layout, "Years", "0"
        )

        # Total Value
        self._total_value_label = self._create_stat_frame(
            contract_layout, "Total Value", "$0"
        )

        # Guaranteed
        self._guaranteed_label = self._create_stat_frame(
            contract_layout, "Guaranteed", "$0 (0%)"
        )

        # Signing Bonus
        self._signing_bonus_label = self._create_stat_frame(
            contract_layout, "Signing Bonus", "$0"
        )

        contract_layout.addStretch()
        parent_layout.addWidget(contract_group)

    def _create_pitch_panel(self, parent_layout: QVBoxLayout):
        """Create panel showing GM's pitch."""
        pitch_group = QGroupBox("GM's Pitch")
        pitch_layout = QVBoxLayout(pitch_group)

        self._pitch_label = QLabel("Loading...")
        self._pitch_label.setWordWrap(True)
        self._pitch_label.setStyleSheet(f"padding: 10px; font-size: {FontSizes.BODY};")
        pitch_layout.addWidget(self._pitch_label)

        parent_layout.addWidget(pitch_group)

    def _create_rationale_panel(self, parent_layout: QVBoxLayout):
        """Create panel showing archetype rationale."""
        rationale_group = QGroupBox("Why This Fits My Philosophy")
        rationale_layout = QVBoxLayout(rationale_group)

        self._rationale_label = QLabel("Loading...")
        self._rationale_label.setWordWrap(True)
        self._rationale_label.setStyleSheet(
            f"padding: 10px; font-size: {FontSizes.CAPTION}; color: {Colors.TEXT_SECONDARY}; font-style: italic;"
        )
        rationale_layout.addWidget(self._rationale_label)

        parent_layout.addWidget(rationale_group)

    def _create_valuation_section(self, parent_layout: QVBoxLayout):
        """Create collapsible section showing contract valuation breakdown."""
        # Container for the valuation section
        self._valuation_container = QFrame()
        valuation_layout = QVBoxLayout(self._valuation_container)
        valuation_layout.setContentsMargins(0, 0, 0, 0)

        # Collapsible section
        self._valuation_section = CollapsibleSection(
            "How Was This Contract Valued?", expanded=False
        )

        # Valuation breakdown widget inside the collapsible
        self._valuation_widget = ValuationBreakdownWidget()
        self._valuation_section.content_layout().addWidget(self._valuation_widget)

        valuation_layout.addWidget(self._valuation_section)

        # Initially hidden - only shown when proposal has valuation_result
        self._valuation_container.setVisible(False)

        parent_layout.addWidget(self._valuation_container)

    def _create_cap_impact_panel(self, parent_layout: QVBoxLayout):
        """Create panel showing cap impact."""
        cap_group = QGroupBox("Cap Impact")
        cap_layout = QHBoxLayout(cap_group)
        cap_layout.setSpacing(30)

        # Year 1 cap hit
        self._cap_hit_label = create_stat_display(
            cap_layout, "Year 1 Cap Hit", "$0", title_font_size=FontSizes.SMALL, value_font=Typography.BODY_BOLD
        )

        # Remaining cap after
        self._remaining_cap_label = create_stat_display(
            cap_layout, "Remaining Cap Space", "$0", title_font_size=FontSizes.SMALL, value_font=Typography.BODY_BOLD
        )

        cap_layout.addStretch()
        parent_layout.addWidget(cap_group)

    def _create_navigation(self, parent_layout: QVBoxLayout):
        """Create navigation buttons for multiple proposals."""
        nav_frame = QFrame()
        nav_frame.setStyleSheet(
            "QFrame { background-color: #f5f5f5; border-radius: 5px; padding: 10px; }"
        )
        nav_layout = QHBoxLayout(nav_frame)

        self._prev_btn = QPushButton("← Previous Proposal")
        self._prev_btn.clicked.connect(self._on_previous)
        self._prev_btn.setEnabled(False)  # Disabled on first proposal

        self._proposal_counter_label = QLabel("Proposal 1 of 1")
        self._proposal_counter_label.setAlignment(Qt.AlignCenter)
        self._proposal_counter_label.setFont(Typography.CAPTION_BOLD)

        self._next_btn = QPushButton("Next Proposal →")
        self._next_btn.clicked.connect(self._on_next)

        nav_layout.addWidget(self._prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self._proposal_counter_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self._next_btn)

        parent_layout.addWidget(nav_frame)

    def _create_action_buttons(self, parent_layout: QVBoxLayout):
        """Create approve/modify/reject action buttons."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # Reject button
        self._reject_btn = QPushButton("✗ Reject")
        self._reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self._reject_btn.clicked.connect(self._on_reject)

        # Modify button (adjust terms before approval)
        self._modify_btn = QPushButton("✎ Modify Terms")
        self._modify_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 10px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2196F3; }"
        )
        self._modify_btn.setToolTip("Modify contract terms before approval")
        self._modify_btn.clicked.connect(self._on_modify)

        # Approve button
        self._approve_btn = QPushButton("✓ Approve")
        self._approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._approve_btn.clicked.connect(self._on_approve)
        self._approve_btn.setDefault(True)

        btn_layout.addWidget(self._reject_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self._modify_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self._approve_btn)

        parent_layout.addLayout(btn_layout)

    def _show_proposal(self, index: int):
        """Display proposal at given index."""
        if index < 0 or index >= len(self._proposals):
            return

        self._current_index = index
        proposal = self._proposals[index]

        # Update player info
        self._player_name_label.setText(f"{proposal.player_name} ({proposal.position})")
        self._player_age_label.setText(str(proposal.age))
        self._player_rating_label.setText(str(proposal.overall_rating))
        self._player_tier_label.setText(proposal.tier)
        self._need_label.setText(proposal.need_addressed)

        # Update contract terms
        self._aav_label.setText(f"${proposal.aav:,}")
        self._years_label.setText(f"{proposal.years} year{'s' if proposal.years > 1 else ''}")

        total_value = proposal.get_total_value()
        self._total_value_label.setText(f"${total_value:,}")

        guaranteed_pct = int(proposal.get_guaranteed_percent() * 100)
        self._guaranteed_label.setText(f"${proposal.guaranteed:,} ({guaranteed_pct}%)")

        self._signing_bonus_label.setText(f"${proposal.signing_bonus:,}")

        # Update GM reasoning
        self._pitch_label.setText(proposal.pitch)
        self._rationale_label.setText(proposal.archetype_rationale)

        # Update cap impact
        self._cap_hit_label.setText(f"${proposal.cap_impact:,}")
        self._remaining_cap_label.setText(f"${proposal.remaining_cap_after:,}")

        # Update valuation breakdown (if available)
        if proposal.valuation_result is not None:
            self._valuation_widget.set_valuation_result(proposal.valuation_result)
            self._valuation_container.setVisible(True)
        else:
            self._valuation_container.setVisible(False)

        # Style cap impact based on available space
        if proposal.remaining_cap_after < 5_000_000:
            self._remaining_cap_label.setStyleSheet(f"color: {Colors.ERROR}; font-weight: bold;")  # Red - low cap
        elif proposal.remaining_cap_after < 15_000_000:
            self._remaining_cap_label.setStyleSheet(f"color: {Colors.WARNING}; font-weight: bold;")  # Orange - moderate
        else:
            self._remaining_cap_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")  # Green - healthy

        # Update navigation
        if len(self._proposals) > 1:
            self._proposal_counter_label.setText(
                f"Proposal {index + 1} of {len(self._proposals)}"
            )
            self._prev_btn.setEnabled(index > 0)
            self._next_btn.setEnabled(index < len(self._proposals) - 1)

        # Update button states based on decision
        decision = self._decisions[index]
        if decision is True:  # Previously approved
            self._approve_btn.setText("✓ Approved")
            self._approve_btn.setEnabled(False)
            self._modify_btn.setEnabled(False)
            self._reject_btn.setEnabled(True)
            self._reject_btn.setText("✗ Reject (Undo)")
        elif decision is False:  # Previously rejected
            self._reject_btn.setText("✗ Rejected")
            self._reject_btn.setEnabled(False)
            self._modify_btn.setEnabled(False)
            self._approve_btn.setEnabled(True)
            self._approve_btn.setText("✓ Approve (Undo)")
        else:  # Not yet decided
            self._approve_btn.setText("✓ Approve")
            self._approve_btn.setEnabled(True)
            self._modify_btn.setEnabled(True)
            self._reject_btn.setText("✗ Reject")
            self._reject_btn.setEnabled(True)

    def _on_previous(self):
        """Show previous proposal."""
        if self._current_index > 0:
            self._show_proposal(self._current_index - 1)

    def _on_next(self):
        """Show next proposal."""
        if self._current_index < len(self._proposals) - 1:
            self._show_proposal(self._current_index + 1)

    def _on_approve(self):
        """Handle approve button click."""
        current_proposal = self._proposals[self._current_index]
        previous_decision = self._decisions[self._current_index]

        # If undoing a rejection, just reset
        if previous_decision is False:
            self._decisions[self._current_index] = None
            self._show_proposal(self._current_index)
            return

        # Confirm approval for high-value or long-term deals
        if current_proposal.is_high_value_signing() or current_proposal.is_long_term_commitment():
            summary = current_proposal.get_contract_summary()
            confirm = QMessageBox.question(
                self,
                "Confirm High-Value Signing",
                f"This is a significant commitment:\n\n{summary}\n\n"
                f"Are you sure you want to approve this proposal?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        # Mark as approved
        self._decisions[self._current_index] = True
        self.proposal_approved.emit(current_proposal)

        # Update UI
        self._show_proposal(self._current_index)

        # Auto-advance to next proposal if available
        if self._current_index < len(self._proposals) - 1:
            self._show_proposal(self._current_index + 1)
        else:
            # All proposals reviewed - close dialog
            self.accept()

    def _on_modify(self):
        """Handle modify button click - emit signal to open modification dialog."""
        current_proposal = self._proposals[self._current_index]
        self.proposal_modify_clicked.emit(current_proposal)

    def _on_reject(self):
        """Handle reject button click."""
        current_proposal = self._proposals[self._current_index]
        previous_decision = self._decisions[self._current_index]

        # If undoing an approval, just reset
        if previous_decision is True:
            self._decisions[self._current_index] = None
            self._show_proposal(self._current_index)
            return

        # Mark as rejected
        self._decisions[self._current_index] = False
        self.proposal_rejected.emit(current_proposal)

        # Update UI
        self._show_proposal(self._current_index)

        # Auto-advance to next proposal if available
        if self._current_index < len(self._proposals) - 1:
            self._show_proposal(self._current_index + 1)
        else:
            # All proposals reviewed - close dialog
            self.accept()

    def get_decisions(self) -> List[Optional[bool]]:
        """
        Get list of decisions for all proposals.

        Returns:
            List where True=approved, False=rejected, None=no decision
        """
        return self._decisions.copy()

    def get_approved_proposals(self) -> List[GMProposal]:
        """Get list of approved proposals."""
        return [
            self._proposals[i]
            for i, decision in enumerate(self._decisions)
            if decision is True
        ]

    def get_rejected_proposals(self) -> List[GMProposal]:
        """Get list of rejected proposals."""
        return [
            self._proposals[i]
            for i, decision in enumerate(self._decisions)
            if decision is False
        ]
