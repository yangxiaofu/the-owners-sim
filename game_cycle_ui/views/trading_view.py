"""
Trading View - Executive Memo Style for GM Trade Proposals.

Redesigned to make GM trade proposals the hero component.
Features large, rich cards with narrative-driven justification.

Layout:
- Filter bar (status, priority, sort)
- Scrollable card container (TradeProposalCard widgets)
- Empty state when no proposals match filters
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QCursor

from game_cycle_ui.widgets.trade_proposal_card import TradeProposalCard
from game_cycle_ui.theme import Colors, TextColors, Typography, ESPN_CARD_BG, ESPN_BORDER


class TradingView(QWidget):
    """
    View for GM trade proposals in executive memo style.

    Displays trade proposals as large, rich cards with:
    - Priority indicators
    - GM confidence levels
    - Deal summaries
    - Strategic justification
    - Approve/reject actions

    Removes roster views to focus on GM recommendations.
    """

    # Signals (maintain compatibility with existing integration)
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)
    proposal_approved = Signal(str)   # proposal_id
    proposal_rejected = Signal(str)   # proposal_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Data
        self._proposals: List[Dict[str, Any]] = []
        self._card_widgets: List[TradeProposalCard] = []
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: Optional[int] = None
        self._team_id: Optional[int] = None

        # Filter state
        self._status_filter = "ALL"  # ALL, PENDING, APPROVED, REJECTED
        self._priority_filter = "ALL"  # ALL, HIGH, MEDIUM, LOW
        self._sort_by = "priority"  # priority, confidence, value

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        # Filter bar
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Scroll area for cards
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Card container
        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(16)
        self._card_layout.setAlignment(Qt.AlignTop)

        self._scroll_area.setWidget(self._card_container)
        layout.addWidget(self._scroll_area)

        # Empty state widget (hidden by default)
        self._empty_state = self._create_empty_state()
        self._empty_state.hide()
        layout.addWidget(self._empty_state)

    def _create_filter_bar(self) -> QWidget:
        """Create filter and sort controls."""
        filter_bar = QFrame()
        filter_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(8, 8, 8, 8)
        filter_layout.setSpacing(12)

        # Status filter label
        status_label = QLabel("Status:")
        status_label.setFont(Typography.BODY)
        status_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY}; font-weight: 500;")
        filter_layout.addWidget(status_label)

        # Status filter buttons
        self._status_buttons = {}
        for status in ["All", "Pending", "Approved", "Rejected"]:
            btn = QPushButton(status)
            btn.setCheckable(True)
            btn.setChecked(status == "All")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self._get_filter_button_style(status == "All"))
            btn.clicked.connect(lambda checked, s=status.upper(): self._on_status_filter_changed(s))
            self._status_buttons[status.upper()] = btn
            filter_layout.addWidget(btn)

        filter_layout.addSpacing(16)

        # Priority filter label
        priority_label = QLabel("Priority:")
        priority_label.setFont(Typography.BODY)
        priority_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY}; font-weight: 500;")
        filter_layout.addWidget(priority_label)

        # Priority filter dropdown
        self._priority_combo = QComboBox()
        self._priority_combo.addItems(["All", "High", "Medium", "Low"])
        self._priority_combo.setStyleSheet(self._get_combo_style())
        self._priority_combo.currentTextChanged.connect(
            lambda text: self._on_priority_filter_changed(text.upper())
        )
        filter_layout.addWidget(self._priority_combo)

        filter_layout.addStretch()

        # Sort dropdown
        sort_label = QLabel("Sort by:")
        sort_label.setFont(Typography.BODY)
        sort_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY}; font-weight: 500;")
        filter_layout.addWidget(sort_label)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["Priority", "Confidence", "Value"])
        self._sort_combo.setStyleSheet(self._get_combo_style())
        self._sort_combo.currentTextChanged.connect(
            lambda text: self._on_sort_changed(text.lower())
        )
        filter_layout.addWidget(self._sort_combo)

        return filter_bar

    def _get_filter_button_style(self, is_active: bool) -> str:
        """Get stylesheet for filter buttons."""
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {Colors.INFO};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {Colors.INFO};
                    opacity: 0.9;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TextColors.ON_DARK_SECONDARY};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                    padding: 6px 16px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BG_SECONDARY};
                    border: 1px solid {Colors.INFO};
                }}
                QPushButton:checked {{
                    background-color: {Colors.INFO};
                    color: white;
                    border: none;
                }}
            """

    def _get_combo_style(self) -> str:
        """Get stylesheet for combo boxes."""
        return f"""
            QComboBox {{
                background-color: {ESPN_CARD_BG};
                color: {TextColors.ON_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border: 1px solid {Colors.INFO};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {TextColors.ON_DARK_SECONDARY};
                margin-right: 8px;
            }}
        """

    def _create_empty_state(self) -> QWidget:
        """Create empty state widget shown when no proposals match filters."""
        empty = QFrame()
        empty.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border: 2px dashed {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(40, 40, 40, 40)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignCenter)

        # Icon placeholder
        icon = QLabel("📋")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon)

        # Message
        message = QLabel("No trade proposals match your filters")
        message.setFont(Typography.H4)
        message.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
            font-weight: 500;
        """)
        message.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(message)

        # Hint
        hint = QLabel("Try adjusting your filter settings or check back later")
        hint.setFont(Typography.BODY)
        hint.setStyleSheet(f"""
            color: {TextColors.ON_DARK_SECONDARY};
        """)
        hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(hint)

        return empty

    @Slot(str)
    def _on_status_filter_changed(self, status: str):
        """Handle status filter button click."""
        self._status_filter = status

        # Update button states
        for s, btn in self._status_buttons.items():
            is_active = (s == status)
            btn.setChecked(is_active)
            btn.setStyleSheet(self._get_filter_button_style(is_active))

        self._apply_filters()

    @Slot(str)
    def _on_priority_filter_changed(self, priority: str):
        """Handle priority filter change."""
        self._priority_filter = priority
        self._apply_filters()

    @Slot(str)
    def _on_sort_changed(self, sort_by: str):
        """Handle sort change."""
        self._sort_by = sort_by
        self._apply_filters()  # Re-apply to trigger re-sort

    def _apply_filters(self):
        """Apply current filters and sorting to proposals."""
        # Filter proposals
        filtered = self._proposals.copy()

        # Status filter
        if self._status_filter != "ALL":
            filtered = [
                p for p in filtered
                if p.get("status", "PENDING").upper() == self._status_filter
            ]

        # Priority filter
        if self._priority_filter != "ALL":
            filtered = [
                p for p in filtered
                if p.get("priority", "MEDIUM").upper() == self._priority_filter
            ]

        # Sort proposals
        if self._sort_by == "priority":
            priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            filtered.sort(
                key=lambda p: priority_order.get(p.get("priority", "MEDIUM").upper(), 1)
            )
        elif self._sort_by == "confidence":
            filtered.sort(key=lambda p: p.get("confidence", 0.0), reverse=True)
        elif self._sort_by == "value":
            filtered.sort(key=lambda p: p.get("value_differential", 0), reverse=True)

        # Rebuild cards
        self._rebuild_cards(filtered)

    def _rebuild_cards(self, proposals: List[Dict[str, Any]]):
        """Rebuild card widgets from filtered/sorted proposals."""
        # Clear existing cards
        for card in self._card_widgets:
            card.deleteLater()
        self._card_widgets.clear()

        # Show empty state if no proposals
        if not proposals:
            self._scroll_area.hide()
            self._empty_state.show()
            return

        # Hide empty state, show cards
        self._empty_state.hide()
        self._scroll_area.show()

        # Create new cards
        for proposal in proposals:
            card = TradeProposalCard(proposal)

            # Connect signals
            card.proposal_approved.connect(self._on_card_approved)
            card.proposal_rejected.connect(self._on_card_rejected)

            self._card_layout.addWidget(card)
            self._card_widgets.append(card)

        # Add stretch at end
        self._card_layout.addStretch()

    @Slot(str)
    def _on_card_approved(self, proposal_id: str):
        """Handle card approval."""
        print(f"[TradingView] Approved proposal: {proposal_id}")

        # Emit signal for external handlers
        self.proposal_approved.emit(proposal_id)

        # Remove card from view
        self._remove_card_by_id(proposal_id)

    @Slot(str)
    def _on_card_rejected(self, proposal_id: str):
        """Handle card rejection."""
        print(f"[TradingView] Rejected proposal: {proposal_id}")

        # Emit signal for external handlers
        self.proposal_rejected.emit(proposal_id)

        # Remove card from view
        self._remove_card_by_id(proposal_id)

    def _remove_card_by_id(self, proposal_id: str):
        """Remove a card from the view by proposal ID."""
        # Find and remove card widget
        for card in self._card_widgets:
            if card.get_proposal_id() == proposal_id:
                card.deleteLater()
                self._card_widgets.remove(card)
                break

        # Update proposals list
        self._proposals = [
            p for p in self._proposals
            if p.get("proposal_id") != proposal_id
        ]

        # If no cards left, show empty state
        if not self._card_widgets:
            self._scroll_area.hide()
            self._empty_state.show()

    # Public API

    def set_context(
        self,
        dynasty_id: str,
        db_path: str,
        season: int,
        team_id: Optional[int] = None
    ):
        """
        Set context for the view.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game database
            season: Current season year
            team_id: Team ID (optional)
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._team_id = team_id

    def set_gm_proposals(self, proposals: List[Dict[str, Any]]):
        """
        Set GM trade proposals for display.

        Args:
            proposals: List of proposal dictionaries with structure:
                {
                    "proposal_id": str,
                    "priority": str ("HIGH"/"MEDIUM"/"LOW"),
                    "title": str,
                    "trade_partner": str,
                    "confidence": float (0.0-1.0),
                    "sending": List[Dict],
                    "receiving": List[Dict],
                    "value_differential": int,
                    "cap_impact": int,
                    "gm_reasoning": str,
                    "strategic_fit": List[str],
                    "status": str ("PENDING"/"APPROVED"/"REJECTED")
                }
        """
        self._proposals = proposals
        self._apply_filters()

    def remove_proposal(self, proposal_id: str):
        """
        Remove a proposal from the view (used by demo script).

        Args:
            proposal_id: ID of proposal to remove
        """
        self._remove_card_by_id(proposal_id)

    # Legacy compatibility methods (may be called by existing integration)

    def set_trading_data(self, preview_data: Dict[str, Any]):
        """
        Legacy method for backward compatibility.

        Extracts GM proposals from preview data if present.
        """
        if "gm_proposals" in preview_data:
            self.set_gm_proposals(preview_data["gm_proposals"])

    def set_cap_data(self, cap_data: Dict[str, Any]):
        """
        Legacy method for backward compatibility.

        Cap data no longer displayed in redesigned view.
        """
        pass  # No-op in redesigned view
