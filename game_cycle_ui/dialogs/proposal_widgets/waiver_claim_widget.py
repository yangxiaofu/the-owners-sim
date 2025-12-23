"""
Waiver Claim Proposal Widget - Display for waiver wire claim proposals.

Part of Tollgate 4: Approval UI.

Displays: Player info, waiver priority, contract remaining, claim probability.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors


class WaiverClaimProposalWidget(BaseProposalWidget):
    """Widget for displaying WAIVER_CLAIM proposal details."""

    def _setup_ui(self) -> None:
        """Build the waiver claim proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Player Information
        player_group, player_layout = self._create_info_group("Player on Waivers")

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

        player_layout.addStretch()
        layout.addWidget(player_group)

        # Waiver Details
        waiver_group, waiver_layout = self._create_info_group("Waiver Details")

        priority = self.details.get("waiver_priority", 0)
        self._create_stat_frame(
            waiver_layout,
            "Your Priority",
            f"#{priority}",
            value_color=Colors.SUCCESS if priority <= 10 else Colors.WARNING,
        )

        # Contract Remaining
        contract = self.details.get("contract_remaining", {})
        years = contract.get("years", 0)
        total = contract.get("total", 0)

        self._create_stat_frame(
            waiver_layout,
            "Contract Years",
            str(years),
        )
        self._create_stat_frame(
            waiver_layout,
            "Contract Total",
            self._format_currency(total),
        )

        waiver_layout.addStretch()
        layout.addWidget(waiver_group)

        # Claim Probability Explanation
        if priority <= 5:
            prob_text = "High probability of successful claim (top 5 priority)"
            prob_color = Colors.SUCCESS
        elif priority <= 15:
            prob_text = "Moderate probability - several teams ahead in priority"
            prob_color = Colors.WARNING
        else:
            prob_text = "Low probability - many teams have priority over you"
            prob_color = Colors.ERROR

        prob_label = QLabel(prob_text)
        prob_label.setWordWrap(True)
        prob_label.setStyleSheet(f"color: {prob_color}; font-style: italic;")
        layout.addWidget(prob_label)

        # Note about waiver order
        note_label = QLabel(
            "Note: Waiver priority is based on inverse standings order. "
            "Teams with worse records have higher priority."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(note_label)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        name = self.details.get("player_name", "Unknown")
        pos = self.details.get("position", "?")
        rating = self.details.get("overall_rating", 0)
        priority = self.details.get("waiver_priority", 0)

        return f"{pos} {name} ({rating} OVR) - Priority #{priority}"