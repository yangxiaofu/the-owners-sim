"""
Draft Pick Proposal Widget - Display for draft selection proposals.

Part of Tollgate 4: Approval UI.

Displays: Pick info, prospect details, alternatives list, draft grade.
"""

from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt

from .base_widget import BaseProposalWidget
from game_cycle_ui.theme import Colors, Typography, apply_table_style


class DraftPickProposalWidget(BaseProposalWidget):
    """Widget for displaying DRAFT_PICK proposal details."""

    def _setup_ui(self) -> None:
        """Build the draft pick proposal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Pick Information
        pick_group, pick_layout = self._create_info_group("Draft Selection")

        self._create_stat_frame(
            pick_layout,
            "Round",
            str(self.details.get("round", "?")),
        )
        self._create_stat_frame(
            pick_layout,
            "Pick",
            str(self.details.get("pick", "?")),
        )
        self._create_stat_frame(
            pick_layout,
            "Overall",
            f"#{self.details.get('overall', '?')}",
            value_color=Colors.INFO,
        )

        pick_layout.addStretch()
        layout.addWidget(pick_group)

        # Prospect Information
        prospect_group, prospect_layout = self._create_info_group("Recommended Selection")

        self._create_stat_frame(
            prospect_layout,
            "Player",
            f"{self.details.get('player_name', 'Unknown')} ({self.details.get('position', '?')})",
        )
        self._create_stat_frame(
            prospect_layout,
            "College",
            self.details.get("college", "Unknown"),
        )
        rating = self.details.get("projected_rating", 0)
        self._create_stat_frame(
            prospect_layout,
            "Proj. Rating",
            str(rating),
            value_color=self._get_rating_color(rating),
        )
        grade = self.details.get("draft_grade", "?")
        self._create_stat_frame(
            prospect_layout,
            "Draft Grade",
            grade,
            value_color=self._get_grade_color(grade),
        )

        prospect_layout.addStretch()
        layout.addWidget(prospect_group)

        # Alternatives
        alternatives = self.details.get("alternatives", [])
        if alternatives:
            alt_group, alt_layout = self._create_text_group("Also Available")

            alt_table = QTableWidget(len(alternatives), 3)
            alt_table.setHorizontalHeaderLabels(["Name", "Position", "Rating"])
            apply_table_style(alt_table, row_height=28)

            header = alt_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

            for row, alt in enumerate(alternatives):
                name_item = QTableWidgetItem(alt.get("name", "Unknown"))
                alt_table.setItem(row, 0, name_item)

                pos_item = QTableWidgetItem(alt.get("position", "?"))
                pos_item.setTextAlignment(Qt.AlignCenter)
                alt_table.setItem(row, 1, pos_item)

                rating = alt.get("rating", 0)
                rating_item = QTableWidgetItem(str(rating))
                rating_item.setTextAlignment(Qt.AlignCenter)
                alt_table.setItem(row, 2, rating_item)

            alt_table.setMaximumHeight(100)
            alt_layout.addWidget(alt_table)

            hint_label = QLabel("You can request an alternative player during review.")
            hint_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
            alt_layout.addWidget(hint_label)

            layout.addWidget(alt_group)

        layout.addStretch()

    def get_summary(self) -> str:
        """Return one-line summary for batch view."""
        round_num = self.details.get("round", "?")
        pick = self.details.get("pick", "?")
        name = self.details.get("player_name", "Unknown")
        pos = self.details.get("position", "?")
        rating = self.details.get("projected_rating", 0)

        return f"Rd {round_num} Pick {pick}: {pos} {name} ({rating} proj.)"

    def _get_grade_color(self, grade: str) -> str:
        """Get color for draft grade."""
        if grade.startswith("A"):
            return Colors.SUCCESS
        elif grade.startswith("B"):
            return Colors.INFO
        elif grade.startswith("C"):
            return Colors.WARNING
        else:
            return Colors.ERROR