"""
Cut Proposal Widget - Display for roster cut proposals.

Part of Tollgate 4: Approval UI.

Displays: Player info, cap savings, dead money, replacement options.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors
from constants.position_abbreviations import get_position_abbreviation


class CutProposalWidget(BaseProposalWidget):
    """Widget for displaying CUT proposal details."""

    def _setup_ui(self) -> None:
        """Build the cut proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Player Information
        player_group, player_layout = self._create_info_group("Player to Release")

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

        # Financial Impact
        finance_group, finance_layout = self._create_info_group("Financial Impact")

        cap_savings = self.details.get("cap_savings", 0)
        self._create_stat_frame(
            finance_layout,
            "Cap Savings",
            self._format_currency(cap_savings),
            value_color=Colors.SUCCESS if cap_savings > 0 else Colors.MUTED,
        )

        dead_money = self.details.get("dead_money", 0)
        self._create_stat_frame(
            finance_layout,
            "Dead Money",
            self._format_currency(dead_money),
            value_color=Colors.ERROR if dead_money > 0 else Colors.MUTED,
        )

        net_savings = cap_savings - dead_money
        self._create_stat_frame(
            finance_layout,
            "Net Savings",
            self._format_currency(net_savings),
            value_color=Colors.SUCCESS if net_savings > 0 else Colors.ERROR,
        )

        finance_layout.addStretch()
        layout.addWidget(finance_group)

        # Replacement Options
        replacement = self.details.get("replacement_options", "")
        if replacement:
            replace_group, replace_layout = self._create_text_group("Replacement Plan")
            replace_label = self._create_body_label(replacement)
            replace_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
            replace_layout.addWidget(replace_label)
            layout.addWidget(replace_group)

        # Warning for low-rated cuts
        if rating < 60:
            warning_label = QLabel(
                "Note: This player has a low rating. Cutting them "
                "should not significantly impact roster depth."
            )
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(f"color: {Colors.MUTED};")
            layout.addWidget(warning_label)
        elif rating >= 75:
            warning_label = QLabel(
                "Warning: This is a solid contributor. Consider the "
                "impact on team depth before approving."
            )
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(f"color: {Colors.WARNING};")
            layout.addWidget(warning_label)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        name = self.details.get("player_name", "Unknown")
        pos = get_position_abbreviation(self.details.get("position", "?"))
        rating = self.details.get("overall_rating", 0)
        cap_savings = self.details.get("cap_savings", 0)

        # Extract short reason from gm_reasoning (e.g., "PERFORMANCE CONCERN" from first line)
        reasoning = self._proposal.gm_reasoning or ""
        reason = ""
        if reasoning:
            first_line = reasoning.split("\n")[0]
            # Extract tier name (e.g., "PERFORMANCE CONCERN" from "PERFORMANCE CONCERN: ...")
            if ":" in first_line:
                reason = first_line.split(":")[0].strip()

        if reason:
            return f"{pos} {name} ({rating} OVR) - {reason} - Save {self._format_currency(cap_savings)}"
        return f"{pos} {name} ({rating} OVR) - Save {self._format_currency(cap_savings)}"