"""
Trade Proposal Card - Executive memo style card for GM trade proposals.

Large, rich card displaying:
- Priority badge and title
- GM confidence bar
- Deal summary (assets sent/received)
- Value analysis
- GM justification
- Strategic fit bullet points
- Approve/Reject action buttons

Collapsible: Click header to expand/collapse full details.
"""

from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    PRIMARY_BUTTON_STYLE, DANGER_BUTTON_STYLE,
    Colors, TextColors, Typography, ESPN_CARD_BG
)
from game_cycle_ui.widgets.confidence_bar import ConfidenceBar
from game_cycle_ui.widgets.asset_list_widget import AssetListWidget


class TradeProposalCard(QFrame):
    """
    Executive memo style card for a single trade proposal.

    Large card with visual hierarchy:
    1. Header (priority + title + confidence)
    2. Deal Summary (sending/receiving assets)
    3. Value Analysis
    4. GM Justification
    5. Strategic Fit
    6. Action Buttons

    Emits signals when approved/rejected.
    """

    # Signals
    proposal_approved = Signal(str)  # proposal_id
    proposal_rejected = Signal(str)  # proposal_id
    card_expanded = Signal(str)      # proposal_id
    card_collapsed = Signal(str)     # proposal_id

    def __init__(self, proposal: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize trade proposal card.

        Args:
            proposal: Proposal dictionary with all required fields
            parent: Parent widget
        """
        super().__init__(parent)
        self._proposal = proposal
        self._proposal_id = proposal.get("proposal_id", "unknown")
        self._is_expanded = True  # Start expanded
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        # Card frame styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1px solid {Colors.INFO};
            }}
        """)
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header section (always visible)
        header = self._create_header()
        layout.addWidget(header)

        # Expandable content section
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Confidence bar
        confidence = self._proposal.get("confidence", 0.0)
        self._confidence_bar = ConfidenceBar(confidence=confidence)
        content_layout.addWidget(self._confidence_bar)

        # Divider
        content_layout.addWidget(self._create_divider())

        # Deal section header
        deal_header = QLabel("THE DEAL:")
        deal_header.setFont(Typography.H4)
        deal_header.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        content_layout.addWidget(deal_header)

        # Asset lists (sending/receiving)
        sending = self._proposal.get("sending", [])
        receiving = self._proposal.get("receiving", [])
        asset_list = AssetListWidget(sending=sending, receiving=receiving)
        content_layout.addWidget(asset_list)

        # Value analysis
        value_widget = self._create_value_analysis()
        content_layout.addWidget(value_widget)

        # GM Justification
        gm_reasoning = self._proposal.get("gm_reasoning", "")
        if gm_reasoning:
            justification_widget = self._create_justification_section(gm_reasoning)
            content_layout.addWidget(justification_widget)

        # Strategic Fit
        strategic_fit = self._proposal.get("strategic_fit", [])
        if strategic_fit:
            fit_widget = self._create_strategic_fit_section(strategic_fit)
            content_layout.addWidget(fit_widget)

        # Action buttons
        actions_widget = self._create_action_buttons()
        content_layout.addWidget(actions_widget)

        layout.addWidget(self._content_widget)

        # Initially expanded
        self._content_widget.setVisible(True)

    def _create_header(self) -> QWidget:
        """Create card header with priority badge and title."""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        # Priority badge
        priority = self._proposal.get("priority", "MEDIUM")
        badge = self._create_priority_badge(priority)
        header_layout.addWidget(badge)

        # Title and partner info
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title = self._proposal.get("title", "Trade Proposal")
        title_label = QLabel(title)
        title_label.setFont(Typography.H3)
        title_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-weight: 600;
        """)
        title_layout.addWidget(title_label)

        partner = self._proposal.get("trade_partner", "Unknown Team")
        partner_label = QLabel(f"Trade Proposal with {partner}")
        partner_label.setFont(Typography.BODY)
        partner_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
        """)
        title_layout.addWidget(partner_label)

        header_layout.addWidget(title_widget, stretch=1)

        # Expand/collapse toggle (future enhancement)
        # For now, always expanded

        return header

    def _create_priority_badge(self, priority: str) -> QLabel:
        """Create priority badge with emoji and color coding."""
        # Map priority to emoji and color
        priority_map = {
            "HIGH": ("🔥", Colors.ERROR, Colors.BG_SECONDARY),
            "MEDIUM": ("⚡", Colors.WARNING, Colors.BG_SECONDARY),
            "LOW": ("⭐", Colors.SUCCESS, Colors.BG_SECONDARY)
        }

        emoji, text_color, bg_color = priority_map.get(
            priority.upper(),
            ("⚡", Colors.WARNING, Colors.BG_SECONDARY)  # Default to MEDIUM
        )

        badge = QLabel(f"{emoji} {priority} PRIORITY")
        badge.setFont(Typography.CAPTION_BOLD)
        badge.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        """)
        badge.setAlignment(Qt.AlignCenter)
        badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        return badge

    def _create_divider(self) -> QFrame:
        """Create horizontal divider line."""
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"""
            QFrame {{
                color: {Colors.BORDER};
                margin: 4px 0px;
            }}
        """)
        return divider

    def _create_value_analysis(self) -> QWidget:
        """Create value analysis section."""
        value_widget = QWidget()
        value_layout = QHBoxLayout(value_widget)
        value_layout.setContentsMargins(0, 0, 0, 0)

        value_diff = self._proposal.get("value_differential", 0)

        # Determine color and label based on value
        if value_diff > 50:
            color = Colors.SUCCESS  # Green
            assessment = "Favorable"
        elif value_diff > 0:
            color = Colors.SUCCESS  # Green (slightly favorable still green)
            assessment = "Slightly Favorable"
        elif value_diff == 0:
            color = Colors.WARNING  # Orange
            assessment = "Even"
        elif value_diff > -50:
            color = Colors.ERROR  # Red (slightly unfavorable still red)
            assessment = "Slightly Unfavorable"
        else:
            color = Colors.ERROR  # Red
            assessment = "Unfavorable"

        # Format value differential with sign
        value_str = f"+{value_diff}" if value_diff > 0 else str(value_diff)

        value_label = QLabel(f"VALUE ANALYSIS: {value_str} pts ({assessment})")
        value_label.setFont(Typography.BODY_BOLD)
        value_label.setStyleSheet(f"""
            color: {color};
            font-weight: 600;
            background-color: {Colors.BG_SECONDARY};
            padding: 8px 12px;
            border-radius: 4px;
        """)

        value_layout.addWidget(value_label)
        value_layout.addStretch()

        return value_widget

    def _create_justification_section(self, reasoning: str) -> QWidget:
        """Create GM justification section."""
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(6)

        # Header
        header = QLabel("GM JUSTIFICATION:")
        header.setFont(Typography.H4)
        header.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        section_layout.addWidget(header)

        # Reasoning text
        reasoning_label = QLabel(f'"{reasoning}"')
        reasoning_label.setFont(Typography.BODY)
        reasoning_label.setWordWrap(True)
        reasoning_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-style: italic;
            background-color: {Colors.BG_SECONDARY};
            padding: 12px;
            border-radius: 4px;
            line-height: 1.5;
        """)
        section_layout.addWidget(reasoning_label)

        return section

    def _create_strategic_fit_section(self, fit_points: List[str]) -> QWidget:
        """Create strategic fit bullet points section."""
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(6)

        # Header
        header = QLabel("STRATEGIC FIT:")
        header.setFont(Typography.H4)
        header.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        section_layout.addWidget(header)

        # Bullet points
        for point in fit_points:
            bullet = QLabel(f"• {point}")
            bullet.setFont(Typography.BODY)
            bullet.setWordWrap(True)
            bullet.setStyleSheet(f"""
                color: {TextColors.ON_DARK};
                padding-left: 8px;
            """)
            section_layout.addWidget(bullet)

        return section

    def _create_action_buttons(self) -> QWidget:
        """Create approve/reject action buttons."""
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 8, 0, 0)
        actions_layout.setSpacing(12)

        # Approve button
        approve_btn = QPushButton("APPROVE TRADE")
        approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        approve_btn.setCursor(QCursor(Qt.PointingHandCursor))
        approve_btn.setMinimumHeight(40)
        approve_btn.clicked.connect(lambda: self._on_approve_clicked())
        actions_layout.addWidget(approve_btn)

        # Reject button
        reject_btn = QPushButton("REJECT")
        reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        reject_btn.setCursor(QCursor(Qt.PointingHandCursor))
        reject_btn.setMinimumHeight(40)
        reject_btn.clicked.connect(lambda: self._on_reject_clicked())
        actions_layout.addWidget(reject_btn)

        # Future: "Request Changes" button
        # request_btn = QPushButton("Request Changes")
        # actions_layout.addWidget(request_btn)

        actions_layout.addStretch()

        return actions

    def _on_approve_clicked(self):
        """Handle approve button click."""
        self.proposal_approved.emit(self._proposal_id)

    def _on_reject_clicked(self):
        """Handle reject button click."""
        self.proposal_rejected.emit(self._proposal_id)

    def get_proposal_id(self) -> str:
        """Get the proposal ID."""
        return self._proposal_id

    def get_proposal(self) -> Dict[str, Any]:
        """Get the full proposal dictionary."""
        return self._proposal
