"""
Franchise Tag Proposal Widget - Display for franchise tag proposals.

Part of Tollgate 4: Approval UI.

Displays: Player info, tag type, tag amount, cap impact.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors


class FranchiseTagProposalWidget(BaseProposalWidget):
    """Widget for displaying FRANCHISE_TAG proposal details."""

    def _setup_ui(self) -> None:
        """Build the franchise tag proposal UI."""
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

        # Tag Details
        tag_group, tag_layout = self._create_info_group("Franchise Tag Details")

        tag_type = self.details.get("tag_type", "exclusive")
        tag_display = "Exclusive Tag" if tag_type == "exclusive" else "Non-Exclusive Tag"
        self._create_stat_frame(
            tag_layout,
            "Tag Type",
            tag_display,
            value_color=Colors.INFO if tag_type == "exclusive" else Colors.WARNING,
        )
        self._create_stat_frame(
            tag_layout,
            "Tag Amount",
            self._format_currency(self.details.get("tag_amount", 0)),
        )
        self._create_stat_frame(
            tag_layout,
            "Cap Impact",
            self._format_currency(self.details.get("cap_impact", 0)),
            value_color=Colors.WARNING,
        )

        tag_layout.addStretch()
        layout.addWidget(tag_group)

        # Tag Type Explanation
        if tag_type == "exclusive":
            explanation = (
                "Exclusive Tag: Player cannot negotiate with other teams. "
                "Tag amount is average of top 5 salaries at position."
            )
        else:
            explanation = (
                "Non-Exclusive Tag: Player can negotiate with other teams. "
                "If signed, you receive two first-round picks as compensation."
            )

        explain_label = QLabel(explanation)
        explain_label.setWordWrap(True)
        explain_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        layout.addWidget(explain_label)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        name = self.details.get("player_name", "Unknown")
        pos = self.details.get("position", "?")
        tag_type = self.details.get("tag_type", "exclusive")
        amount = self.details.get("tag_amount", 0)
        tag_label = "Exclusive" if tag_type == "exclusive" else "Non-Exclusive"

        return f"{pos} {name} - {tag_label} Tag ({self._format_currency(amount)})"