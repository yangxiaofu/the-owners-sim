"""
Extension Proposal Widget - Display for contract extension proposals.

Part of Tollgate 4: Approval UI.

Displays: Current contract, proposed contract, market comparison.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors


class ExtensionProposalWidget(BaseProposalWidget):
    """Widget for displaying EXTENSION proposal details."""

    def _setup_ui(self) -> None:
        """Build the extension proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Player Information
        player_group, player_layout = self._create_info_group("Player Information")

        self._create_stat_frame(
            player_layout,
            "Player",
            f"{self.details.get('player_name', 'Unknown')} ({self.details.get('position', '?')})",
        )

        player_layout.addStretch()
        layout.addWidget(player_group)

        # Current Contract
        current = self.details.get("current_contract", {})
        current_group, current_layout = self._create_info_group("Current Contract")

        self._create_stat_frame(
            current_layout,
            "Years Remaining",
            str(current.get("years", 0)),
        )
        self._create_stat_frame(
            current_layout,
            "Total Remaining",
            self._format_currency(current.get("total", 0)),
        )
        self._create_stat_frame(
            current_layout,
            "Current AAV",
            self._format_currency(current.get("aav", 0)),
        )

        current_layout.addStretch()
        layout.addWidget(current_group)

        # Proposed Contract
        proposed = self.details.get("proposed_contract", {})
        proposed_group, proposed_layout = self._create_info_group("Proposed Extension")

        self._create_stat_frame(
            proposed_layout,
            "New Years",
            str(proposed.get("years", 0)),
        )
        self._create_stat_frame(
            proposed_layout,
            "New Total",
            self._format_currency(proposed.get("total", 0)),
        )
        self._create_stat_frame(
            proposed_layout,
            "New AAV",
            self._format_currency(proposed.get("aav", 0)),
            value_color=Colors.INFO,
        )
        guaranteed = proposed.get("guaranteed", 0)
        total = proposed.get("total", 1)
        gtd_pct = (guaranteed / total * 100) if total > 0 else 0
        self._create_stat_frame(
            proposed_layout,
            "Guaranteed",
            f"{self._format_currency(guaranteed)} ({gtd_pct:.0f}%)",
            value_color=Colors.SUCCESS,
        )

        proposed_layout.addStretch()
        layout.addWidget(proposed_group)

        # AAV Change Comparison
        current_aav = current.get("aav", 0)
        proposed_aav = proposed.get("aav", 0)
        if current_aav > 0:
            change_pct = ((proposed_aav - current_aav) / current_aav) * 100
            change_text = f"+{change_pct:.1f}%" if change_pct > 0 else f"{change_pct:.1f}%"
            change_color = Colors.WARNING if change_pct > 20 else Colors.SUCCESS

            change_label = QLabel(f"AAV Change: {change_text} from current")
            change_label.setStyleSheet(f"color: {change_color}; font-weight: bold;")
            layout.addWidget(change_label)

        # Market Comparison
        market = self.details.get("market_comparison", "")
        if market:
            market_group, market_layout = self._create_text_group("Market Comparison")
            market_label = self._create_body_label(market)
            market_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
            market_layout.addWidget(market_label)
            layout.addWidget(market_group)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        name = self.details.get("player_name", "Unknown")
        pos = self.details.get("position", "?")
        proposed = self.details.get("proposed_contract", {})
        years = proposed.get("years", 0)
        aav = proposed.get("aav", 0)

        return f"{pos} {name} - {years}yr / {self._format_currency(aav)}/yr extension"