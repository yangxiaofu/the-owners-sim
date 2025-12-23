"""
Signing Proposal Widget - Display for free agent signing proposals.

Part of Tollgate 4: Approval UI.

Displays: Player info, contract terms, competing offers, cap impact.
"""

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors


class SigningProposalWidget(BaseProposalWidget):
    """Widget for displaying SIGNING proposal details."""

    def _setup_ui(self) -> None:
        """Build the signing proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Player Information
        player_group, player_layout = self._create_info_group("Player Information")

        self._create_stat_frame(
            player_layout,
            "Player",
            f"{self.details.get('player_name', 'Unknown')} ({self.details.get('position', '?')})",
        )
        self._create_stat_frame(
            player_layout,
            "Age",
            str(self.details.get("age", "?")),
        )
        rating = self.details.get("overall_rating", 0)
        self._create_stat_frame(
            player_layout,
            "Overall",
            str(rating),
            value_color=self._get_rating_color(rating),
        )
        competing = self.details.get("competing_offers", 0)
        self._create_stat_frame(
            player_layout,
            "Competing Offers",
            str(competing),
            value_color=Colors.WARNING if competing > 2 else None,
        )

        player_layout.addStretch()
        layout.addWidget(player_group)

        # Contract Terms
        contract = self.details.get("contract", {})
        contract_group, contract_layout = self._create_info_group("Proposed Contract")

        self._create_stat_frame(
            contract_layout,
            "Years",
            str(contract.get("years", 0)),
        )
        self._create_stat_frame(
            contract_layout,
            "Total Value",
            self._format_currency(contract.get("total", 0)),
        )
        self._create_stat_frame(
            contract_layout,
            "AAV",
            self._format_currency(contract.get("aav", 0)),
        )
        guaranteed = contract.get("guaranteed", 0)
        total = contract.get("total", 1)
        gtd_pct = (guaranteed / total * 100) if total > 0 else 0
        self._create_stat_frame(
            contract_layout,
            "Guaranteed",
            f"{self._format_currency(guaranteed)} ({gtd_pct:.0f}%)",
            value_color=Colors.SUCCESS,
        )

        contract_layout.addStretch()
        layout.addWidget(contract_group)

        # Cap Impact
        cap_group, cap_layout = self._create_info_group("Cap Impact")

        cap_before = self.details.get("cap_space_before", 0)
        cap_after = self.details.get("cap_space_after", 0)

        self._create_stat_frame(
            cap_layout,
            "Cap Space Before",
            self._format_currency(cap_before),
        )
        self._create_stat_frame(
            cap_layout,
            "Cap Space After",
            self._format_currency(cap_after),
            value_color=self._get_cap_color(cap_after),
        )
        year1_hit = contract.get("aav", 0)  # Simplified: AAV as year 1 hit
        self._create_stat_frame(
            cap_layout,
            "Year 1 Cap Hit",
            self._format_currency(year1_hit),
            value_color=Colors.WARNING if year1_hit > 15_000_000 else None,
        )

        cap_layout.addStretch()
        layout.addWidget(cap_group)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        name = self.details.get("player_name", "Unknown")
        pos = self.details.get("position", "?")
        rating = self.details.get("overall_rating", 0)
        contract = self.details.get("contract", {})
        aav = contract.get("aav", 0)

        return f"{pos} {name} ({rating} OVR) - {self._format_currency(aav)}/yr"

    def _get_cap_color(self, cap_space: int) -> str:
        """Get color based on remaining cap space."""
        if cap_space < 5_000_000:
            return Colors.ERROR
        elif cap_space < 15_000_000:
            return Colors.WARNING
        else:
            return Colors.SUCCESS