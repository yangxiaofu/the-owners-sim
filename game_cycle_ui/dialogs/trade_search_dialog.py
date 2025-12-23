"""
Trade Search Dialog - Shows cap-clearing trade options.

Displays GM-suggested trades that would free up cap space to afford a signing.
Each trade card shows the trade partner, assets exchanged, cap impact, and GM reasoning.
"""

from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    Colors, PRIMARY_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors
)
from constants.position_abbreviations import get_position_abbreviation


class TradeSearchDialog(QDialog):
    """Dialog showing cap-clearing trade options."""

    trade_selected = Signal(str)  # proposal_id

    def __init__(
        self,
        parent: QWidget,
        player_info: Dict[str, Any],
        cap_shortage: int,
        trade_options: List[Dict[str, Any]]
    ):
        """
        Initialize the trade search dialog.

        Args:
            parent: Parent widget (FreeAgencyView)
            player_info: Dict with name, position, aav of player trying to sign
            cap_shortage: Amount over cap (positive number)
            trade_options: List of trade proposal dicts from TradeProposalGenerator
        """
        super().__init__(parent)
        self.setWindowTitle("Find Trade Partner to Clear Cap Space")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._player_info = player_info
        self._cap_shortage = cap_shortage
        self._trade_options = trade_options

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header section
        header = self._create_header()
        layout.addWidget(header)

        # Trade cards (scrollable)
        if self._trade_options:
            scroll_area = self._create_trade_cards_section()
            layout.addLayout(scroll_area)
        else:
            # No trades available message
            no_trades_msg = self._create_no_trades_message()
            layout.addWidget(no_trades_msg)

        # Bottom buttons
        bottom_bar = self._create_bottom_bar()
        layout.addLayout(bottom_bar)

    def _create_header(self) -> QWidget:
        """Create header showing context (player trying to sign, cap shortage)."""
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #2a2a2a; border-radius: 6px; padding: 12px; }")
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(6)

        # Title
        title = QLabel("Find Trade Partner to Clear Cap Space")
        title.setFont(Typography.H4)
        title.setStyleSheet(f"color: {Colors.INFO}; font-weight: bold;")
        header_layout.addWidget(title)

        # Player context
        player_name = self._player_info.get("name", "Unknown")
        position = self._player_info.get("position", "")
        aav = self._player_info.get("aav", 0)

        context_text = (
            f"Trying to sign: <b>{player_name}</b> "
            f"({get_position_abbreviation(position)}) for <b>${aav/1e6:.1f}M/yr</b>"
        )
        context_label = QLabel(context_text)
        context_label.setFont(Typography.BODY)
        context_label.setStyleSheet(f"color: {TextColors.ON_DARK_PRIMARY};")
        header_layout.addWidget(context_label)

        # Cap shortage
        shortage_text = f"Cap shortage: <b style='color: {Colors.ERROR};'>${self._cap_shortage/1e6:.1f}M</b>"
        shortage_label = QLabel(shortage_text)
        shortage_label.setFont(Typography.BODY)
        shortage_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        header_layout.addWidget(shortage_label)

        return header

    def _create_trade_cards_section(self) -> QVBoxLayout:
        """Create scrollable section with trade cards."""
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Section title
        trades_title = QLabel(f"GM-Suggested Trades ({len(self._trade_options)})")
        trades_title.setFont(Typography.H5)
        trades_title.setStyleSheet(f"color: {TextColors.ON_DARK_PRIMARY}; font-weight: bold; padding: 8px 0;")
        layout.addWidget(trades_title)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Container for cards
        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        # Add trade cards
        for proposal in self._trade_options:
            card = self._create_trade_card(proposal)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        scroll.setWidget(cards_container)
        layout.addWidget(scroll)

        return layout

    def _create_trade_card(self, proposal: Dict[str, Any]) -> QFrame:
        """Create a single trade option card."""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        card.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 12px;
            }
            QFrame:hover {
                border-color: #1e88e5;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Get proposal details
        details = proposal.get("details", {})
        partner_name = details.get("trade_partner", "Unknown Team")
        cap_impact = details.get("cap_impact", 0)
        confidence = proposal.get("confidence", 0.5)
        reasoning = proposal.get("gm_reasoning", "")

        # Header: Trade partner + Cap impact
        header_layout = QHBoxLayout()

        partner_label = QLabel(f"Trade with <b>{partner_name}</b>")
        partner_label.setFont(Typography.BODY)
        partner_label.setStyleSheet(f"color: {TextColors.ON_DARK_PRIMARY};")
        header_layout.addWidget(partner_label)

        header_layout.addStretch()

        # Cap impact with color coding
        cap_adequacy = (cap_impact / self._cap_shortage) if self._cap_shortage > 0 else 1.0
        if cap_adequacy >= 1.0:
            cap_color = Colors.SUCCESS
            adequacy_text = "✓ Clears needed cap"
        elif cap_adequacy >= 0.5:
            cap_color = Colors.WARNING
            adequacy_text = f"({int(cap_adequacy*100)}% of needed)"
        else:
            cap_color = "#f57c00"  # Orange
            adequacy_text = f"({int(cap_adequacy*100)}% of needed)"

        cap_label = QLabel(f"+${cap_impact/1e6:.1f}M cap space")
        cap_label.setFont(Typography.H5)
        cap_label.setStyleSheet(f"color: {cap_color}; font-weight: bold;")
        header_layout.addWidget(cap_label)

        layout.addLayout(header_layout)

        # Adequacy subtext (if partial)
        if cap_adequacy < 1.0:
            adequacy_label = QLabel(adequacy_text)
            adequacy_label.setFont(Typography.SMALL)
            adequacy_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; font-style: italic;")
            layout.addWidget(adequacy_label)

        # Assets section
        assets_row = QHBoxLayout()
        assets_row.setSpacing(16)

        # Sending column
        sending_widget = self._create_assets_column("Sending:", details.get("sending", []))
        assets_row.addWidget(sending_widget, stretch=1)

        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setFont(Typography.H4)
        arrow_label.setStyleSheet(f"color: {Colors.INFO};")
        arrow_label.setAlignment(Qt.AlignCenter)
        assets_row.addWidget(arrow_label)

        # Receiving column
        receiving_widget = self._create_assets_column("Receiving:", details.get("receiving", []))
        assets_row.addWidget(receiving_widget, stretch=1)

        layout.addLayout(assets_row)

        # GM reasoning
        if reasoning:
            reasoning_label = QLabel(f"<i>GM: \"{reasoning}\"</i>")
            reasoning_label.setWordWrap(True)
            reasoning_label.setFont(Typography.SMALL)
            reasoning_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY}; padding-top: 4px;")
            layout.addWidget(reasoning_label)

        # Confidence bar
        conf_layout = QHBoxLayout()

        conf_label = QLabel(f"GM Confidence: {int(confidence*100)}%")
        conf_label.setFont(Typography.SMALL)
        conf_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        conf_layout.addWidget(conf_label)

        confidence_bar = QProgressBar()
        confidence_bar.setValue(int(confidence * 100))
        confidence_bar.setTextVisible(False)
        confidence_bar.setMaximumHeight(6)
        confidence_bar.setFixedWidth(100)
        confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4caf50, stop:1 #2196f3);
                border-radius: 2px;
            }
        """)
        conf_layout.addWidget(confidence_bar)

        conf_layout.addStretch()

        # Approve button
        approve_btn = QPushButton("Approve Trade")
        approve_btn.setFont(Typography.SMALL)
        approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        approve_btn.clicked.connect(lambda: self._on_trade_approved(proposal.get("proposal_id", "")))
        conf_layout.addWidget(approve_btn)

        layout.addLayout(conf_layout)

        return card

    def _create_assets_column(self, title: str, assets: List[Dict]) -> QWidget:
        """Create column showing assets (players/picks)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title
        title_label = QLabel(title)
        title_label.setFont(Typography.SMALL)
        title_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; font-weight: bold;")
        layout.addWidget(title_label)

        # Assets
        if not assets:
            none_label = QLabel("(Nothing)")
            none_label.setFont(Typography.SMALL)
            none_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; font-style: italic;")
            layout.addWidget(none_label)
        else:
            for asset in assets:
                asset_type = asset.get("type", "unknown")
                if asset_type == "player":
                    asset_text = f"• {asset.get('name', 'Unknown')} ({get_position_abbreviation(asset.get('position', ''))})"
                    if "overall" in asset and asset["overall"] > 0:
                        asset_text += f" - {asset['overall']} OVR"
                elif asset_type == "pick":
                    asset_text = f"• {asset.get('name', 'Pick')}"
                else:
                    asset_text = f"• {asset.get('name', 'Unknown')}"

                asset_label = QLabel(asset_text)
                asset_label.setFont(Typography.SMALL)
                asset_label.setStyleSheet(f"color: {TextColors.ON_DARK_PRIMARY};")
                layout.addWidget(asset_label)

        layout.addStretch()
        return widget

    def _create_no_trades_message(self) -> QWidget:
        """Create message when no trades are available."""
        widget = QFrame()
        widget.setStyleSheet("QFrame { background-color: #2a2a2a; border-radius: 6px; padding: 20px; }")
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Icon + Message
        title = QLabel("No Cap-Clearing Trades Available")
        title.setFont(Typography.H4)
        title.setStyleSheet(f"color: {Colors.WARNING}; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Explanation
        explanation = QLabel(
            "The GM couldn't find any trades that other teams would accept "
            "to clear cap space. Consider these alternatives:"
        )
        explanation.setWordWrap(True)
        explanation.setFont(Typography.BODY)
        explanation.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        explanation.setAlignment(Qt.AlignCenter)
        layout.addWidget(explanation)

        # Suggestions
        suggestions = QLabel(
            "• Cut high-cap players to free up space<br/>"
            "• Pursue cheaper free agent alternatives<br/>"
            "• Wait until next offseason for more flexibility"
        )
        suggestions.setFont(Typography.BODY)
        suggestions.setStyleSheet(f"color: {TextColors.ON_DARK_PRIMARY};")
        layout.addWidget(suggestions)

        layout.addStretch()
        return widget

    def _create_bottom_bar(self) -> QHBoxLayout:
        """Create bottom button bar."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(Typography.BODY)
        close_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        return layout

    def _on_trade_approved(self, proposal_id: str):
        """Handle user approving a trade."""
        self.trade_selected.emit(proposal_id)
        self.accept()  # Close dialog
