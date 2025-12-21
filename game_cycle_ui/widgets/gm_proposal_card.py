"""
GM Proposal Card - Enhanced card-based display for GM signing recommendations.

Part of Concept 1 UI redesign - replaces table with rich cards showing:
- Player info (name, position, OVR, contract)
- Inline GM reasoning
- Confidence bar
- Large approve/reject buttons
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from game_cycle_ui.theme import (
    Typography, FontSizes, Colors,
    PRIMARY_BUTTON_STYLE, DANGER_BUTTON_STYLE
)
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class ProposalCardState(Enum):
    """Visual states for GM proposal cards."""
    PENDING = "pending"              # Awaiting user decision
    APPROVED = "approved"            # User approved, not executed
    PENDING_EXECUTION = "pending_execution"  # Queued for execution
    SIGNED = "signed"                # Player accepted after execution
    REJECTED = "rejected"            # Player rejected after execution


class GMProposalCard(QFrame):
    """
    Single GM proposal displayed as rich card.

    Shows: Player name, position, OVR, contract, reasoning bullets,
    confidence bar, approve/reject/modify buttons.

    Supports approved state with retract capability - approvals are
    tracked locally until committed via Process Wave.

    Signals:
        proposal_approved: User approved this proposal (proposal_id)
        proposal_rejected: User rejected this proposal (proposal_id)
        proposal_retracted: User retracted a previous approval (proposal_id)
        proposal_modify_clicked: User wants to modify terms (proposal_id, proposal_data)
        search_trade_partner_clicked: User clicked search for trade partner (proposal_id, cap_shortage)
    """

    proposal_approved = Signal(str)  # proposal_id
    proposal_rejected = Signal(str)  # proposal_id
    proposal_retracted = Signal(str)  # proposal_id - new signal for undo
    proposal_modify_clicked = Signal(str, object)  # proposal_id, proposal_data dict
    search_trade_partner_clicked = Signal(str, int)  # proposal_id, cap_shortage

    def __init__(self, proposal_data: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.proposal_id = proposal_data.get("proposal_id", "")
        self._proposal_data = proposal_data  # Store for modify dialog
        # Check if proposal is pre-approved (new default behavior)
        from game_cycle.models.proposal_enums import ProposalStatus
        proposal_status = ProposalStatus.normalize(proposal_data.get("status", "PENDING"))
        self._is_approved = (proposal_status == ProposalStatus.APPROVED)

        # Track current visual state
        self._state = ProposalCardState.PENDING

        # Store cap data for affordability check
        details = proposal_data.get("details", {})
        self.cap_space_after = details.get("cap_space_after", 0)
        self.cap_shortage = abs(self.cap_space_after) if self.cap_space_after < 0 else 0

        # References to UI elements we need to modify
        self._approve_btn = None
        self._modify_btn = None
        self._reject_btn = None
        self._retract_btn = None
        self._btn_row = None
        self._approved_badge = None
        self._result_badge = None  # For signed/rejected state after Process Wave
        self._result_details = None  # Contract summary or rejection reason

        self._setup_ui(proposal_data)

        # If proposal is pre-approved, set the approved state in the UI
        if self._is_approved:
            self.set_approved_state(True)

    def _setup_ui(self, data: Dict[str, Any]):
        """Build the card layout."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left section: Player info + reasoning
        left_section = self._create_info_section(data)
        layout.addWidget(left_section, stretch=3)

        # Right section: Confidence + actions
        right_section = self._create_action_section(data)
        layout.addWidget(right_section, stretch=1)

        # Card styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            GMProposalCard {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            GMProposalCard:hover {
                border-color: #1e88e5;
            }
        """)

        # Set minimum height for consistent card sizing
        self.setMinimumHeight(120)

    def _create_info_section(self, data: Dict[str, Any]) -> QWidget:
        """Player name, contract, age, interest, reasoning bullets."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Extract details
        details = data.get("details", {})
        contract = details.get("contract", {})

        player_name = details.get("player_name", "Unknown")
        position = details.get("position", "")
        overall = extract_overall_rating(details, default=0)
        age = details.get("age", 0)
        aav = contract.get("aav", 0)
        years = contract.get("years", 0)

        # Get interest score if available
        interest = data.get("interest_score", 0)  # May not be in proposal data

        # Header: Name + Position + OVR + Contract
        header_html = (
            f"<b style='font-size: 14px'>{player_name}</b> "
            f"<span style='color: #888'>{get_position_abbreviation(position)}</span> "
            f"<span style='color: #4caf50'>{overall} OVR</span> "
            f"<span style='color: #2196f3'>${aav/1e6:.1f}M/{years}yr</span>"
        )
        header = QLabel(header_html)
        header.setFont(Typography.BODY)
        layout.addWidget(header)

        # Subheader: Age, Interest, Cap Impact
        total_cap = data.get("total_cap", 255_400_000)  # Default cap if not provided
        cap_impact_pct = (aav / total_cap * 100) if total_cap > 0 else 0

        subheader_parts = [f"Age: {age}"]
        if interest > 0:
            subheader_parts.append(f"Interest: {interest}%")
        subheader_parts.append(f"Cap Impact: {cap_impact_pct:.0f}%")

        subheader = QLabel(" • ".join(subheader_parts))
        subheader.setFont(Typography.SMALL)
        subheader.setStyleSheet("color: #bbb;")
        layout.addWidget(subheader)

        # GM Reasoning (inline)
        reasoning = data.get("gm_reasoning", "")
        if reasoning:
            reasoning_label = QLabel(f"<i>\"{reasoning}\"</i>")
            reasoning_label.setWordWrap(True)
            reasoning_label.setFont(Typography.SMALL)
            reasoning_label.setStyleSheet("color: #ccc; padding-top: 4px;")
            layout.addWidget(reasoning_label)

        layout.addStretch()

        return widget

    def _create_action_section(self, data: Dict[str, Any]) -> QWidget:
        """Confidence bar + Approve/Reject buttons."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Confidence progress bar
        confidence = data.get("confidence", 0.5)
        confidence_pct = int(confidence * 100)

        conf_label = QLabel(f"GM Confidence: {confidence_pct}%")
        conf_label.setFont(Typography.SMALL)
        conf_label.setStyleSheet("color: #bbb;")
        layout.addWidget(conf_label)

        confidence_bar = QProgressBar()
        confidence_bar.setValue(confidence_pct)
        confidence_bar.setTextVisible(False)
        confidence_bar.setMaximumHeight(8)
        confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4caf50, stop:1 #2196f3);
                border-radius: 3px;
            }
        """)
        layout.addWidget(confidence_bar)

        layout.addSpacing(8)

        # Conditional: Trade Search button (if unaffordable)
        if self.cap_space_after < 0:
            trade_search_btn = QPushButton("Search for Trade Partner")
            trade_search_btn.setFont(Typography.SMALL)
            trade_search_btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; "
                "border-radius: 4px; padding: 8px 16px; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )
            trade_search_btn.setToolTip(f"Find trades to clear ${self.cap_shortage:,} in cap space")
            trade_search_btn.clicked.connect(self._on_trade_search_clicked)
            layout.addWidget(trade_search_btn)
            layout.addSpacing(8)

        # Approved badge (hidden initially)
        self._approved_badge = QLabel("✓ APPROVED")
        self._approved_badge.setFont(QFont(Typography.FAMILY, 11, QFont.Weight.Bold))
        self._approved_badge.setStyleSheet("color: #4caf50; padding: 4px 0;")
        self._approved_badge.hide()
        layout.addWidget(self._approved_badge)

        # Result badge (hidden initially - shown after Process Wave)
        self._result_badge = QLabel("")
        self._result_badge.setFont(QFont(Typography.FAMILY, 11, QFont.Weight.Bold))
        self._result_badge.hide()
        layout.addWidget(self._result_badge)

        # Result details (contract summary or rejection reason)
        self._result_details = QLabel("")
        self._result_details.setFont(Typography.SMALL)
        self._result_details.setWordWrap(True)
        self._result_details.hide()
        layout.addWidget(self._result_details)

        # Button row container
        self._btn_row = QWidget()
        btn_layout = QHBoxLayout(self._btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        # Approve button
        self._approve_btn = QPushButton("Approve")
        self._approve_btn.setFont(Typography.SMALL)
        self._approve_btn.setStyleSheet(
            "QPushButton { background-color: #4caf50; color: white; "
            "border-radius: 4px; padding: 8px 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: #66bb6a; }"
        )
        self._approve_btn.setToolTip(
            "Queue this signing for execution.\n"
            "Click 'Process Wave' to execute all approved signings."
        )
        self._approve_btn.clicked.connect(self._on_approve_clicked)
        btn_layout.addWidget(self._approve_btn)

        # Modify button (adjust terms before approval)
        self._modify_btn = QPushButton("Modify")
        self._modify_btn.setFont(Typography.SMALL)
        self._modify_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 8px 12px; }"
            "QPushButton:hover { background-color: #2196F3; }"
        )
        self._modify_btn.setToolTip("Modify contract terms before approval")
        self._modify_btn.clicked.connect(self._on_modify_clicked)
        btn_layout.addWidget(self._modify_btn)

        # Reject button
        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setFont(Typography.SMALL)
        self._reject_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; "
            "border-radius: 4px; padding: 8px 12px; }"
            "QPushButton:hover { background-color: #e57373; }"
        )
        self._reject_btn.clicked.connect(self._on_reject_clicked)
        btn_layout.addWidget(self._reject_btn)

        # Retract button (hidden initially)
        self._retract_btn = QPushButton("Retract")
        self._retract_btn.setFont(Typography.SMALL)
        self._retract_btn.setStyleSheet(
            "QPushButton { background-color: #666; color: white; "
            "border-radius: 4px; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #888; }"
        )
        self._retract_btn.clicked.connect(self._on_retract_clicked)
        self._retract_btn.hide()
        btn_layout.addWidget(self._retract_btn)

        layout.addWidget(self._btn_row)

        layout.addStretch()

        return widget

    def _on_trade_search_clicked(self):
        """Handle trade search button click - emit signal to request cap-clearing trades."""
        self.search_trade_partner_clicked.emit(self.proposal_id, self.cap_shortage)

    def _on_approve_clicked(self):
        """Handle approve button click - switch to approved state."""
        self.set_approved_state(True)
        self.proposal_approved.emit(self.proposal_id)

    def _on_reject_clicked(self):
        """Handle reject button click - emit rejection signal."""
        self.proposal_rejected.emit(self.proposal_id)

    def _on_modify_clicked(self):
        """Handle modify button click - emit signal with proposal data."""
        self.proposal_modify_clicked.emit(self.proposal_id, self._proposal_data)

    def _on_retract_clicked(self):
        """Handle retract button click - switch back to pending state."""
        self.set_approved_state(False)
        self.proposal_retracted.emit(self.proposal_id)

    def set_state(self, state: ProposalCardState, details: Optional[Dict[str, Any]] = None):
        """
        Set card visual state with unified state management.

        Args:
            state: Target state
            details: Optional dict with state-specific data (contract for SIGNED, reason for REJECTED)
        """
        self._state = state
        details = details or {}

        if state == ProposalCardState.PENDING:
            # Pending state (normal)
            self.setStyleSheet("""
                GMProposalCard {
                    background-color: #2a2a2a;
                    border: 1px solid #444;
                    border-radius: 6px;
                    margin-bottom: 8px;
                }
                GMProposalCard:hover {
                    border-color: #1e88e5;
                }
            """)
            self._approved_badge.hide()
            self._result_badge.hide()
            self._result_details.hide()
            self._approve_btn.show()
            self._modify_btn.show()
            self._reject_btn.show()
            self._retract_btn.hide()

        elif state == ProposalCardState.APPROVED:
            # Approved state
            self.setStyleSheet("""
                GMProposalCard {
                    background-color: #2a2a2a;
                    border: 2px solid #4caf50;
                    border-radius: 6px;
                    margin-bottom: 8px;
                }
            """)
            self._approved_badge.show()
            self._result_badge.hide()
            self._result_details.hide()
            self._approve_btn.hide()
            self._modify_btn.hide()
            self._reject_btn.hide()
            self._retract_btn.show()

        elif state == ProposalCardState.PENDING_EXECUTION:
            # Pending execution state
            self._approve_btn.hide()
            self._modify_btn.hide()
            self._reject_btn.hide()
            self._retract_btn.hide()
            self._approved_badge.hide()

            self._result_badge.setText("⏳ PENDING EXECUTION")
            self._result_badge.setStyleSheet("color: #FFA500; padding: 4px 0; font-weight: bold;")
            self._result_badge.show()

            self._result_details.setText("Click 'Process Wave' to execute this signing")
            self._result_details.setStyleSheet("color: #FFB84D;")
            self._result_details.show()

            self.setStyleSheet("""
                GMProposalCard {
                    background-color: #3a2a1b;
                    border: 2px solid #FFA500;
                    border-radius: 6px;
                    margin-bottom: 8px;
                }
            """)

        elif state == ProposalCardState.SIGNED:
            # Signed state
            self._approved_badge.hide()
            self._approve_btn.hide()
            self._modify_btn.hide()
            self._reject_btn.hide()
            self._retract_btn.hide()
            self._btn_row.hide()

            self._result_badge.setText("✓ SIGNED")
            self._result_badge.setStyleSheet("color: #4caf50; padding: 4px 0;")
            self._result_badge.show()

            # Show contract summary if provided
            aav = details.get("aav", 0)
            years = details.get("years", 0)
            if aav and years:
                self._result_details.setText(f"{years}yr, ${aav:,}/yr")
                self._result_details.setStyleSheet("color: #81c784;")
                self._result_details.show()

            self.setStyleSheet("""
                GMProposalCard {
                    background-color: #1b3a1b;
                    border: 2px solid #4caf50;
                    border-radius: 6px;
                    margin-bottom: 8px;
                }
            """)

        elif state == ProposalCardState.REJECTED:
            # Rejected state
            self._approved_badge.hide()
            self._approve_btn.hide()
            self._modify_btn.hide()
            self._reject_btn.hide()
            self._retract_btn.hide()
            self._btn_row.hide()

            self._result_badge.setText("✗ REJECTED")
            self._result_badge.setStyleSheet("color: #f44336; padding: 4px 0;")
            self._result_badge.show()

            # Show rejection details
            reason = details.get("reason", "Player rejected offer")
            concerns = details.get("concerns", [])
            if concerns:
                details_text = f"{reason}\n• " + "\n• ".join(concerns[:2])  # Show top 2 concerns
            else:
                details_text = reason
            self._result_details.setText(details_text)
            self._result_details.setStyleSheet("color: #ef9a9a;")
            self._result_details.show()

            self.setStyleSheet("""
                GMProposalCard {
                    background-color: #3a1b1b;
                    border: 2px solid #f44336;
                    border-radius: 6px;
                    margin-bottom: 8px;
                }
            """)

    def set_approved_state(self, approved: bool):
        """
        Backwards compatible wrapper for set_state().

        Toggle between approved and pending state.

        When approved:
        - Show green tint on card border
        - Show "✓ APPROVED" badge
        - Hide Approve/Reject buttons, show Retract button

        When not approved (pending):
        - Normal card styling
        - Hide badge
        - Show Approve/Reject buttons, hide Retract button
        """
        self._is_approved = approved
        state = ProposalCardState.APPROVED if approved else ProposalCardState.PENDING
        self.set_state(state)

    def is_approved(self) -> bool:
        """Return whether this card is in approved state."""
        return self._is_approved

    def set_signed_state(self, contract_details: Dict[str, Any]):
        """
        Backwards compatible wrapper for set_state().

        Show signed state after successful Process Wave.

        Args:
            contract_details: Dict with aav, years from the signed contract
        """
        self.set_state(ProposalCardState.SIGNED, details=contract_details)

    def set_rejected_state(self, reason: str, concerns: Optional[List[str]] = None):
        """
        Backwards compatible wrapper for set_state().

        Show rejected state after failed signing attempt.

        Args:
            reason: Main rejection reason (e.g., "Player rejected offer")
            concerns: Optional list of specific concerns
        """
        details = {"reason": reason, "concerns": concerns or []}
        self.set_state(ProposalCardState.REJECTED, details=details)

    def set_pending_execution_state(self):
        """
        Backwards compatible wrapper for set_state().

        Set card to pending execution state (approved but not yet processed).

        Shows that the proposal has been queued for execution when "Process Wave" is clicked.
        """
        self.set_state(ProposalCardState.PENDING_EXECUTION)


class GMProposalsPanel(QWidget):
    """
    Container for GM proposal cards + batch controls.

    Shows up to 3 proposal cards stacked vertically.
    Bottom bar: Approve All, Review Later, Auto-approval indicator.

    Approvals are tracked locally (not committed) until Process Wave.
    Users can retract approvals before committing.

    Signals:
        proposal_approved: User approved a proposal (proposal_id)
        proposal_rejected: User rejected a proposal (proposal_id)
        proposal_retracted: User retracted a previous approval (proposal_id)
        proposal_modify_clicked: User wants to modify terms (proposal_id, proposal_data)
        all_approved: User clicked Approve All
        review_later: User clicked Review Later
        search_trade_partner: User clicked search for trade partner (proposal_id, cap_shortage)
    """

    proposal_approved = Signal(str)
    proposal_rejected = Signal(str)
    proposal_retracted = Signal(str)  # New: for undo capability
    proposal_modify_clicked = Signal(str, object)  # proposal_id, proposal_data dict
    all_approved = Signal()
    review_later = Signal()
    search_trade_partner = Signal(str, int)  # proposal_id, cap_shortage

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._proposals_data = []
        self._pending_approvals: set[str] = set()  # Track approved proposal_ids
        self._cards: dict[str, GMProposalCard] = {}  # Map proposal_id -> card widget
        self._setup_ui()

    def _setup_ui(self):
        """Build the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Title with count
        self.title = QLabel("GM SIGNING RECOMMENDATIONS")
        self.title.setFont(Typography.H5)
        self.title.setStyleSheet("color: #1e88e5; font-weight: bold; padding: 8px 0;")
        layout.addWidget(self.title)

        # Cards container
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)

        layout.addWidget(self.cards_container)

        # Bottom controls
        controls = self._create_controls_bar()
        layout.addWidget(controls)

        # Initially hidden (no proposals)
        self.hide()

    def _create_controls_bar(self) -> QWidget:
        """Approve All, Review Later, Auto-approval indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        self.approve_all_btn = QPushButton("Approve All 0 Proposals")
        self.approve_all_btn.setFont(Typography.BODY)
        self.approve_all_btn.setStyleSheet(
            "QPushButton { background-color: #4caf50; color: white; "
            "border-radius: 4px; padding: 10px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #66bb6a; }"
            "QPushButton:disabled { background-color: #666; color: #999; }"
        )
        self.approve_all_btn.clicked.connect(self._on_approve_all)
        layout.addWidget(self.approve_all_btn)

        self.review_later_btn = QPushButton("Review Later")
        self.review_later_btn.setFont(Typography.BODY)
        self.review_later_btn.setStyleSheet(
            "QPushButton { background-color: #666; color: white; "
            "border-radius: 4px; padding: 10px 20px; }"
            "QPushButton:hover { background-color: #888; }"
        )
        self.review_later_btn.clicked.connect(self.review_later.emit)
        layout.addWidget(self.review_later_btn)

        layout.addStretch()

        self.auto_indicator = QLabel("")
        self.auto_indicator.setFont(Typography.SMALL)
        self.auto_indicator.setStyleSheet("color: #4caf50; font-style: italic;")
        layout.addWidget(self.auto_indicator)

        return widget

    def set_proposals(self, proposals: list, auto_approve: bool = False):
        """
        Populate cards from proposal data.

        Args:
            proposals: List of proposal dicts with:
                - proposal_id: str
                - details: dict with player_name, position, overall_rating,
                           contract (years, aav, guaranteed)
                - gm_reasoning: str
                - confidence: float (0-1)
            auto_approve: If True, show auto-approval indicator
        """
        self._proposals_data = proposals
        self._pending_approvals.clear()
        self._cards.clear()

        # Clear existing cards
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not proposals:
            self.hide()
            return

        # Show panel
        self.show()

        # Add new cards (max 3)
        for proposal in proposals[:3]:
            proposal_id = proposal.get("proposal_id", "")
            card = GMProposalCard(proposal)
            card.proposal_approved.connect(self._on_proposal_approved)
            card.proposal_rejected.connect(self._on_proposal_rejected)
            card.proposal_retracted.connect(self._on_proposal_retracted)
            card.proposal_modify_clicked.connect(self.proposal_modify_clicked.emit)
            card.search_trade_partner_clicked.connect(self.search_trade_partner.emit)
            self.cards_layout.addWidget(card)
            self._cards[proposal_id] = card  # Store reference

        # Register any pre-approved proposals
        self._register_pre_approved_proposals()

        # Update controls
        count = len(proposals)
        self._update_approve_all_button()

        # Update title with pre-approved count
        self._update_title()

        # Auto-approval indicator
        if auto_approve:
            self.auto_indicator.setText("Auto-Approve: ON ✓")
        else:
            self.auto_indicator.setText("")

    def _register_pre_approved_proposals(self):
        """Detect and register pre-approved proposals in pending set."""
        for proposal_id, card in self._cards.items():
            if card.is_approved():
                self._pending_approvals.add(proposal_id)
                print(f"[DEBUG GMProposalsPanel] Pre-approved proposal added to pending: {proposal_id}")

    def _on_proposal_approved(self, proposal_id: str):
        """
        Handle approval - track in pending set but don't commit yet.

        Card remains visible with approved state until Process Wave commits.
        """
        self._pending_approvals.add(proposal_id)
        self._update_approve_all_button()
        # Forward signal (view can track for UI updates)
        self.proposal_approved.emit(proposal_id)

    def _on_proposal_rejected(self, proposal_id: str):
        """
        Handle rejection - remove card and forward signal.

        Rejections are immediate (no undo) since they require GM to propose
        something new.
        """
        self.proposal_rejected.emit(proposal_id)

        # Remove from local list and cards dict
        self._proposals_data = [
            p for p in self._proposals_data
            if p.get("proposal_id") != proposal_id
        ]
        self._cards.pop(proposal_id, None)
        self._pending_approvals.discard(proposal_id)

        # Remove card widget
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, GMProposalCard) and card.proposal_id == proposal_id:
                    self.cards_layout.removeWidget(card)
                    card.deleteLater()
                    break

        # Update button and hide if empty
        self._update_approve_all_button()
        self._update_title()
        if not self._proposals_data:
            self.hide()

    def _on_proposal_retracted(self, proposal_id: str):
        """
        Handle retraction - remove from pending set.

        Card stays visible but returns to normal pending state.
        """
        self._pending_approvals.discard(proposal_id)
        self._update_approve_all_button()
        # Forward signal (view can track for UI updates)
        self.proposal_retracted.emit(proposal_id)

    def _on_approve_all(self):
        """Approve all visible cards."""
        for proposal_id, card in self._cards.items():
            if not card.is_approved():
                card.set_approved_state(True)
                self._pending_approvals.add(proposal_id)
                self.proposal_approved.emit(proposal_id)
        self._update_approve_all_button()

    def _update_approve_all_button(self):
        """Update the Approve All button text based on pending state."""
        pending_count = len(self._pending_approvals)
        total_count = len(self._cards)
        unapproved_count = total_count - pending_count

        if unapproved_count > 0:
            self.approve_all_btn.setText(f"Approve All {unapproved_count} Proposal{'s' if unapproved_count != 1 else ''}")
            self.approve_all_btn.setEnabled(True)
        else:
            self.approve_all_btn.setText("All Approved ✓")
            self.approve_all_btn.setEnabled(False)

    def _update_title(self):
        """Update the title with current count."""
        count = len(self._proposals_data)
        pending_count = len(self._pending_approvals)
        if pending_count > 0:
            self.title.setText(f"GM SIGNING RECOMMENDATIONS ({count}) - {pending_count} approved")
        else:
            self.title.setText(f"GM SIGNING RECOMMENDATIONS ({count})")

    def get_proposal_count(self) -> int:
        """Return number of proposals."""
        return len(self._proposals_data)

    def get_pending_approvals(self) -> set[str]:
        """Return the set of proposal_ids that have been approved but not committed."""
        return self._pending_approvals.copy()

    def clear_pending_approvals(self):
        """Clear pending approvals after they've been committed."""
        self._pending_approvals.clear()
        # Remove approved cards from display
        for proposal_id in list(self._cards.keys()):
            card = self._cards.get(proposal_id)
            if card and card.is_approved():
                self._proposals_data = [
                    p for p in self._proposals_data
                    if p.get("proposal_id") != proposal_id
                ]
                self._cards.pop(proposal_id, None)
                self.cards_layout.removeWidget(card)
                card.deleteLater()

        self._update_approve_all_button()
        self._update_title()
        if not self._proposals_data:
            self.hide()
