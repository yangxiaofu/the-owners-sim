"""
HOF Inductee Dialog - Celebration announcement for Hall of Fame inductees.

Shows newly inducted players with:
- Player name, position, career highlights
- HOF score, first-ballot status, vote percentage
- Career statistics summary
- Multiple inductees displayed together
"""

from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QGroupBox, QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from game_cycle_ui.theme import Typography, Colors, ESPN_THEME


class HOFInducteeDialog(QDialog):
    """
    Dialog celebrating Hall of Fame inductees.

    Layout:
    - Header: "Hall of Fame Class of YYYY"
    - Inductee cards: One per player with career highlights
    - Close button
    """

    def __init__(
        self,
        inductees: List[Dict[str, Any]],
        season: int,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize HOF inductee dialog.

        Args:
            inductees: List of inductee dicts from voting results
            season: Induction season year
            parent: Parent widget
        """
        super().__init__(parent)
        self._inductees = inductees
        self._season = season

        self.setWindowTitle(f"Hall of Fame Class of {season}")
        self.setMinimumSize(700, 600)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Dark background
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ESPN_THEME['bg']};
            }}
        """)

        # Header
        self._create_header(layout)

        # Scroll area for inductees (in case of many inductees)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(f"background-color: {ESPN_THEME['bg']};")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)

        # Create card for each inductee
        for inductee in self._inductees:
            card = self._create_inductee_card(inductee)
            scroll_layout.addWidget(card)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Close button
        self._create_close_button(layout)

    def _create_header(self, layout: QVBoxLayout):
        """Create the header section."""
        header = QLabel(f"🏆 Hall of Fame Class of {self._season} 🏆")
        header.setFont(Typography.H1)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"color: {Colors.INFO}; padding: 12px;")
        layout.addWidget(header)

        count_label = QLabel(
            f"{len(self._inductees)} Player{'s' if len(self._inductees) > 1 else ''} Enshrined"
        )
        count_label.setFont(Typography.BODY)
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet(f"color: {Colors.MUTED}; padding-bottom: 8px;")
        layout.addWidget(count_label)

    def _create_inductee_card(self, inductee: Dict[str, Any]) -> QFrame:
        """Create a card for a single inductee."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border: 2px solid {ESPN_THEME['red']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Player name and position
        name_layout = QHBoxLayout()

        player_name = inductee.get('player_name', 'Unknown')
        name_label = QLabel(player_name)
        name_label.setFont(Typography.H2)
        name_label.setStyleSheet(f"color: {ESPN_THEME['red']};")
        name_layout.addWidget(name_label)

        # First-ballot badge
        if inductee.get('is_first_ballot'):
            first_ballot_badge = QLabel("FIRST BALLOT")
            first_ballot_badge.setFont(Typography.BODY_SMALL_BOLD)
            first_ballot_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: #FFD700;
                    color: #000000;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
            """)
            name_layout.addWidget(first_ballot_badge)

        name_layout.addStretch()
        card_layout.addLayout(name_layout)

        # Position and basic info
        position = inductee.get('primary_position', 'N/A')
        retired_season = inductee.get('retirement_season', 'N/A')
        career_seasons = inductee.get('career_seasons', 0)

        info_label = QLabel(f"{position} • Retired {retired_season} • {career_seasons} Seasons")
        info_label.setFont(Typography.BODY)
        info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        card_layout.addWidget(info_label)

        # Score and voting info
        score_layout = QHBoxLayout()

        hof_score = inductee.get('hof_score', 0)
        score_label = QLabel(f"HOF Score: {hof_score}")
        score_label.setFont(Typography.BODY_BOLD)
        score_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        score_layout.addWidget(score_label)

        vote_pct = inductee.get('vote_percentage', 0.0)
        vote_label = QLabel(f"Vote: {vote_pct:.1f}%")
        vote_label.setFont(Typography.BODY_BOLD)
        vote_label.setStyleSheet(f"color: {Colors.INFO};")
        score_layout.addWidget(vote_label)

        years_on_ballot = inductee.get('years_on_ballot', 1)
        ballot_label = QLabel(f"Ballot Years: {years_on_ballot}")
        ballot_label.setFont(Typography.BODY)
        ballot_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        score_layout.addWidget(ballot_label)

        score_layout.addStretch()
        card_layout.addLayout(score_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {ESPN_THEME['border']};")
        card_layout.addWidget(separator)

        # Career highlights (if score_breakdown available)
        score_breakdown = inductee.get('score_breakdown')
        if score_breakdown and isinstance(score_breakdown, dict):
            highlights_layout = self._create_highlights_section(score_breakdown)
            card_layout.addLayout(highlights_layout)
        else:
            # Fallback: generic career highlights message
            highlights_label = QLabel("A legendary career worthy of the Hall of Fame.")
            highlights_label.setFont(Typography.BODY)
            highlights_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-style: italic;")
            card_layout.addWidget(highlights_label)

        return card

    def _create_highlights_section(self, breakdown: Dict[str, Any]) -> QGridLayout:
        """Create career highlights grid from score breakdown."""
        grid = QGridLayout()
        grid.setSpacing(8)

        highlights = []

        # MVP Awards
        mvp_count = breakdown.get('mvp_count', 0)
        if mvp_count > 0:
            highlights.append(("MVP Awards", str(mvp_count)))

        # Super Bowl Wins
        sb_count = breakdown.get('super_bowl_count', 0)
        if sb_count > 0:
            highlights.append(("Super Bowl Wins", str(sb_count)))

        # All-Pro First Team
        ap1_count = breakdown.get('all_pro_first_count', 0)
        if ap1_count > 0:
            highlights.append(("All-Pro 1st", str(ap1_count)))

        # All-Pro Second Team
        ap2_count = breakdown.get('all_pro_second_count', 0)
        if ap2_count > 0:
            highlights.append(("All-Pro 2nd", str(ap2_count)))

        # Pro Bowls
        pb_count = breakdown.get('pro_bowl_count', 0)
        if pb_count > 0:
            highlights.append(("Pro Bowls", str(pb_count)))

        # Stats tier
        stats_tier = breakdown.get('stats_tier', '')
        if stats_tier:
            highlights.append(("Stats", stats_tier.title()))

        # Add to grid (2 columns)
        for i, (label, value) in enumerate(highlights):
            row = i // 2
            col = i % 2

            label_widget = QLabel(f"{label}:")
            label_widget.setFont(Typography.BODY_SMALL)
            label_widget.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            grid.addWidget(label_widget, row, col * 2)

            value_widget = QLabel(value)
            value_widget.setFont(Typography.BODY_SMALL_BOLD)
            value_widget.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
            grid.addWidget(value_widget, row, col * 2 + 1)

        return grid

    def _create_close_button(self, layout: QVBoxLayout):
        """Create the close button."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(120)
        close_btn.setFont(Typography.BODY_BOLD)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_THEME['red']};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #C41E3A;
            }}
        """)
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)