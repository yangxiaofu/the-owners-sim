"""
Draft Trade Offers Panel - Display AI trade offers when user is on the clock.

Shows incoming trade offers for the user's current draft pick with:
- Card layout per offer showing assets offered
- GM recommendation badge with confidence
- Accept/Reject buttons
- Scrollable if multiple offers

Part of Draft Stage UI.
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    Typography,
    FontSizes,
    Colors,
    TextColors,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)


class TradeOfferCard(QFrame):
    """
    Single trade offer card with offer details and action buttons.

    Shows:
    - Offering team name
    - Assets being offered (picks and/or players)
    - GM recommendation with confidence
    - Accept/Reject buttons

    Signals:
        accepted: Emitted when Accept button clicked (proposal_id)
        rejected: Emitted when Reject button clicked (proposal_id)
    """

    accepted = Signal(str)  # proposal_id
    rejected = Signal(str)  # proposal_id

    def __init__(self, offer: Dict, parent: Optional[QWidget] = None):
        """
        Initialize trade offer card.

        Args:
            offer: Trade offer dict with:
                - proposal_id: str
                - offering_team: str (team name)
                - offering_team_id: int
                - offering_assets: List[Dict] with type, name, value
                - requesting_pick: str (e.g., "Round 1, Pick 15")
                - gm_recommendation: str ("accept" or "reject")
                - gm_reasoning: str
                - gm_confidence: float (0.0-1.0)
            parent: Parent widget
        """
        super().__init__(parent)
        self.proposal_id = offer.get("proposal_id", "")
        self._setup_ui(offer)

    def _setup_ui(self, offer: Dict):
        """Build the card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header: Team name
        offering_team = offer.get("offering_team", "Unknown Team")
        team_header = QLabel(f"{offering_team.upper()} offer:")
        team_header.setFont(Typography.H5)
        team_header.setStyleSheet(f"color: {Colors.INFO}; font-weight: bold;")
        layout.addWidget(team_header)

        # Assets list
        assets = offer.get("offering_assets", [])
        if assets:
            assets_container = QWidget()
            assets_layout = QVBoxLayout(assets_container)
            assets_layout.setContentsMargins(12, 0, 0, 0)
            assets_layout.setSpacing(4)

            for asset in assets:
                asset_type = asset.get("type", "")
                asset_name = asset.get("name", "")
                asset_value = asset.get("value", "")

                # Format asset display
                if asset_type == "pick":
                    display_text = f"• {asset_name}"
                elif asset_type == "player":
                    display_text = f"• {asset_name} ({asset_value})"
                else:
                    display_text = f"• {asset_name}"

                asset_label = QLabel(display_text)
                asset_label.setFont(Typography.BODY)
                asset_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
                assets_layout.addWidget(asset_label)

            layout.addWidget(assets_container)

        layout.addSpacing(8)

        # GM Recommendation section
        gm_rec = offer.get("gm_recommendation", "reject").lower()
        gm_reasoning = offer.get("gm_reasoning", "")
        gm_confidence = offer.get("gm_confidence", 0.5)
        confidence_pct = int(gm_confidence * 100)

        # Recommendation badge
        rec_text = gm_rec.upper()
        rec_color = Colors.SUCCESS if gm_rec == "accept" else Colors.ERROR

        rec_label = QLabel(f"GM RECOMMENDATION: {rec_text} ({confidence_pct}% confidence)")
        rec_label.setFont(QFont(Typography.FAMILY, 11, QFont.Weight.Bold))
        rec_label.setStyleSheet(f"color: {rec_color};")
        layout.addWidget(rec_label)

        # GM reasoning
        if gm_reasoning:
            reasoning_label = QLabel(f'"{gm_reasoning}"')
            reasoning_label.setWordWrap(True)
            reasoning_label.setFont(Typography.SMALL)
            reasoning_label.setStyleSheet(
                f"color: {TextColors.ON_DARK_SECONDARY}; font-style: italic;"
            )
            layout.addWidget(reasoning_label)

        layout.addSpacing(8)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        accept_btn = QPushButton("Accept")
        accept_btn.setFont(Typography.BODY)
        accept_btn.setStyleSheet(
            "QPushButton { background-color: #4caf50; color: white; "
            "border-radius: 4px; padding: 8px 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #66bb6a; }"
        )
        accept_btn.clicked.connect(lambda: self.accepted.emit(self.proposal_id))
        btn_layout.addWidget(accept_btn)

        reject_btn = QPushButton("Reject")
        reject_btn.setFont(Typography.BODY)
        reject_btn.setStyleSheet(
            "QPushButton { background-color: #666; color: white; "
            "border-radius: 4px; padding: 8px 20px; }"
            "QPushButton:hover { background-color: #888; }"
        )
        reject_btn.clicked.connect(lambda: self.rejected.emit(self.proposal_id))
        btn_layout.addWidget(reject_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Card styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            TradeOfferCard {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            TradeOfferCard:hover {
                border-color: #1e88e5;
            }
        """)

        self.setMinimumHeight(140)


class DraftTradeOffersPanel(QWidget):
    """
    Panel displaying all incoming trade offers for user's current pick.

    Shows scrollable list of offer cards with Accept/Reject actions.
    Updates header with current pick information.

    Signals:
        offer_accepted: User accepted an offer (proposal_id)
        offer_rejected: User rejected an offer (proposal_id)
    """

    offer_accepted = Signal(str)  # proposal_id
    offer_rejected = Signal(str)  # proposal_id

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the draft trade offers panel."""
        super().__init__(parent)
        self._offers: List[Dict] = []
        self._cards: List[TradeOfferCard] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header section
        header_container = QWidget()
        header_container.setStyleSheet(
            "QWidget { background-color: #1e3a5f; border-radius: 4px; padding: 8px; }"
        )
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(4)

        # Title
        self.title_label = QLabel("INCOMING TRADE OFFERS FOR YOUR PICK")
        self.title_label.setFont(Typography.H4)
        self.title_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        # Pick info
        self.pick_info_label = QLabel("Round 1, Pick 1 (Overall #1)")
        self.pick_info_label.setFont(Typography.BODY)
        self.pick_info_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        header_layout.addWidget(self.pick_info_label)

        layout.addWidget(header_container)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #444;")
        layout.addWidget(sep)

        # Scrollable offers area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.offers_container = QWidget()
        self.offers_layout = QVBoxLayout(self.offers_container)
        self.offers_layout.setContentsMargins(0, 0, 0, 0)
        self.offers_layout.setSpacing(8)

        scroll_area.setWidget(self.offers_container)
        layout.addWidget(scroll_area, 1)

        # Footer section
        footer_container = QWidget()
        footer_container.setStyleSheet(
            "QWidget { background-color: #1a1a1a; border-radius: 4px; padding: 8px; }"
        )
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(12, 8, 12, 8)

        self.footer_label = QLabel("No offers")
        self.footer_label.setFont(Typography.BODY)
        self.footer_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        footer_layout.addWidget(self.footer_label)

        footer_layout.addStretch()

        layout.addWidget(footer_container)

        # Initially hidden until offers are set
        self.hide()

    def set_current_pick_info(self, round_num: int, pick_in_round: int, overall: int):
        """
        Update header with current pick information.

        Args:
            round_num: Draft round number (1-7)
            pick_in_round: Pick number within round
            overall: Overall pick number
        """
        pick_text = f"Round {round_num}, Pick {pick_in_round} (Overall #{overall})"
        self.pick_info_label.setText(pick_text)

    def set_trade_offers(self, offers: List[Dict]):
        """
        Update panel with new trade offers.

        Args:
            offers: List of trade offer dicts with:
                - proposal_id: str
                - offering_team: str (team name)
                - offering_team_id: int
                - offering_assets: List[Dict] with type, name, value
                - requesting_pick: str
                - gm_recommendation: str ("accept" or "reject")
                - gm_reasoning: str
                - gm_confidence: float (0.0-1.0)
        """
        self._offers = offers

        # Clear existing cards
        self.clear()

        if not offers:
            self.footer_label.setText("No offers")
            self.hide()
            return

        # Show panel
        self.show()

        # Create cards for each offer
        for offer in offers:
            card = TradeOfferCard(offer)
            card.accepted.connect(self._on_offer_accepted)
            card.rejected.connect(self._on_offer_rejected)
            self.offers_layout.addWidget(card)
            self._cards.append(card)

        # Add stretch at end
        self.offers_layout.addStretch()

        # Update footer
        offer_count = len(offers)
        if offer_count == 1:
            footer_text = "1 trade offer • Make your pick or wait for new offers"
        else:
            footer_text = f"{offer_count} trade offers • Make your pick or wait for new offers"
        self.footer_label.setText(footer_text)

    def clear(self):
        """Clear all offer cards."""
        # Remove all cards
        while self.offers_layout.count() > 0:
            item = self.offers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._cards.clear()
        self._offers.clear()
        self.footer_label.setText("No offers")

    def _on_offer_accepted(self, proposal_id: str):
        """Handle offer acceptance."""
        # Remove the accepted offer card
        self._remove_offer_by_id(proposal_id)
        # Forward signal
        self.offer_accepted.emit(proposal_id)

    def _on_offer_rejected(self, proposal_id: str):
        """Handle offer rejection."""
        # Remove the rejected offer card
        self._remove_offer_by_id(proposal_id)
        # Forward signal
        self.offer_rejected.emit(proposal_id)

    def _remove_offer_by_id(self, proposal_id: str):
        """Remove an offer card by proposal_id."""
        # Find and remove from offers list
        self._offers = [o for o in self._offers if o.get("proposal_id") != proposal_id]

        # Find and remove card widget
        for i, card in enumerate(self._cards):
            if card.proposal_id == proposal_id:
                self.offers_layout.removeWidget(card)
                card.deleteLater()
                self._cards.pop(i)
                break

        # Update footer
        offer_count = len(self._offers)
        if offer_count == 0:
            self.footer_label.setText("No more offers • Make your pick or wait for new offers")
        elif offer_count == 1:
            self.footer_label.setText("1 trade offer • Make your pick or wait for new offers")
        else:
            self.footer_label.setText(
                f"{offer_count} trade offers • Make your pick or wait for new offers"
            )

        # Hide panel if no offers remain
        if not self._offers:
            self.hide()

    def get_offer_count(self) -> int:
        """Return number of active offers."""
        return len(self._offers)
