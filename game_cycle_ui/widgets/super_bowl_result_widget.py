"""
Super Bowl Result Widget - Displays Super Bowl champion and MVP.

Extracted from SuperBowlResultsDialog for use in Season Recap tabbed view.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QWidget
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    Typography, FontSizes, Colors, TextColors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
)


class SuperBowlResultWidget(QFrame):
    """
    Widget displaying Super Bowl champion and MVP.

    Shows:
    - Super Bowl number and season
    - Champion team with final score
    - Super Bowl MVP with stat summary
    - View Box Score button

    Designed for ESPN dark theme.
    """

    view_box_score = Signal(str)  # game_id for navigation

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._super_bowl_result: Dict[str, Any] = {}
        self._super_bowl_mvp: Dict[str, Any] = {}
        self._team_loader = None
        self._season = 0
        self._game_id: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 20, 40, 20)

        # Header placeholder
        self._header_label = QLabel()
        self._header_label.setFont(Typography.H1)
        self._header_label.setAlignment(Qt.AlignCenter)
        self._header_label.setStyleSheet(f"color: {Colors.INFO};")
        layout.addWidget(self._header_label)

        # Subtitle placeholder
        self._subtitle_label = QLabel()
        self._subtitle_label.setFont(Typography.BODY)
        self._subtitle_label.setAlignment(Qt.AlignCenter)
        self._subtitle_label.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(self._subtitle_label)

        layout.addSpacing(10)

        # Champion frame
        self._champion_frame = self._create_champion_section()
        layout.addWidget(self._champion_frame)

        layout.addSpacing(10)

        # MVP section
        self._mvp_group = self._create_mvp_section()
        layout.addWidget(self._mvp_group)

        layout.addSpacing(20)

        # View Box Score button
        self._box_score_btn = self._create_box_score_button()
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self._box_score_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        # Empty state placeholder
        self._empty_label = QLabel("No Super Bowl data available")
        self._empty_label.setFont(Typography.H4)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {Colors.MUTED};")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

    def _create_champion_section(self) -> QFrame:
        """Create the champion display frame."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1a237e;
                border: 2px solid {Colors.INFO};
                border-radius: 12px;
                padding: 24px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        # "CHAMPIONS" label
        champions_label = QLabel("CHAMPIONS")
        champions_label.setFont(Typography.H5)
        champions_label.setAlignment(Qt.AlignCenter)
        champions_label.setStyleSheet(f"color: #90CAF9; letter-spacing: 4px;")
        layout.addWidget(champions_label)

        # Team name
        self._team_name_label = QLabel()
        self._team_name_label.setFont(Typography.H2)
        self._team_name_label.setAlignment(Qt.AlignCenter)
        self._team_name_label.setStyleSheet("color: white;")
        layout.addWidget(self._team_name_label)

        # Score
        self._score_label = QLabel()
        self._score_label.setFont(Typography.H3)
        self._score_label.setAlignment(Qt.AlignCenter)
        self._score_label.setStyleSheet("color: #FFD700;")  # Gold
        layout.addWidget(self._score_label)

        # Opponent
        self._opponent_label = QLabel()
        self._opponent_label.setFont(Typography.BODY)
        self._opponent_label.setAlignment(Qt.AlignCenter)
        self._opponent_label.setStyleSheet("color: #B0BEC5;")
        layout.addWidget(self._opponent_label)

        return frame

    def _create_mvp_section(self) -> QGroupBox:
        """Create the Super Bowl MVP section."""
        group = QGroupBox("SUPER BOWL MVP")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {FontSizes.H5};
                color: white;
                border: 1px solid #546E7A;
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px;
                padding-top: 24px;
                background-color: #263238;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #90CAF9;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # MVP name and position
        self._mvp_name_label = QLabel()
        self._mvp_name_label.setFont(Typography.H4)
        self._mvp_name_label.setAlignment(Qt.AlignCenter)
        self._mvp_name_label.setStyleSheet("color: white;")
        layout.addWidget(self._mvp_name_label)

        # Stats summary
        self._mvp_stats_label = QLabel()
        self._mvp_stats_label.setFont(Typography.BODY)
        self._mvp_stats_label.setAlignment(Qt.AlignCenter)
        self._mvp_stats_label.setStyleSheet(f"color: {Colors.MUTED};")
        self._mvp_stats_label.setWordWrap(True)
        layout.addWidget(self._mvp_stats_label)

        return group

    def _create_box_score_button(self) -> QPushButton:
        """Create the View Box Score button."""
        btn = QPushButton("View Box Score")
        btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn.setMinimumWidth(160)
        btn.clicked.connect(self._on_box_score_clicked)
        return btn

    def set_data(
        self,
        super_bowl_result: Dict[str, Any],
        super_bowl_mvp: Dict[str, Any],
        team_loader: Any,
        season: int
    ):
        """
        Populate widget with Super Bowl data.

        Args:
            super_bowl_result: Dict with winner_team_id, home_team_id, away_team_id,
                              home_score, away_score, game_id
            super_bowl_mvp: Dict with player_name, position, team_id, stat_summary
            team_loader: TeamLoader for getting team names
            season: Season year
        """
        self._super_bowl_result = super_bowl_result or {}
        self._super_bowl_mvp = super_bowl_mvp or {}
        self._team_loader = team_loader
        self._season = season
        self._game_id = super_bowl_result.get("game_id") if super_bowl_result else None

        self._populate_data()

    def _populate_data(self):
        """Populate all labels with current data."""
        if not self._super_bowl_result:
            self._show_empty_state()
            return

        # Show all sections
        self._header_label.show()
        self._subtitle_label.show()
        self._champion_frame.show()
        self._mvp_group.show()
        self._box_score_btn.show()
        self._empty_label.hide()

        # Header
        sb_number = self._get_super_bowl_number()
        self._header_label.setText(f"Super Bowl {sb_number}")
        self._subtitle_label.setText(f"{self._season} Season Champions")

        # Champion section
        self._populate_champion_section()

        # MVP section
        self._populate_mvp_section()

        # Box score button
        self._box_score_btn.setEnabled(bool(self._game_id))

    def _populate_champion_section(self):
        """Populate the champion display."""
        winner_team_id = self._super_bowl_result.get("winner_team_id")
        home_team_id = self._super_bowl_result.get("home_team_id")
        away_team_id = self._super_bowl_result.get("away_team_id")
        home_score = self._super_bowl_result.get("home_score", 0)
        away_score = self._super_bowl_result.get("away_score", 0)

        winner_name = "Unknown"
        loser_name = "Unknown"
        winner_score = 0
        loser_score = 0

        if self._team_loader and winner_team_id:
            winner_team = self._team_loader.get_team_by_id(winner_team_id)
            winner_name = winner_team.full_name if winner_team else f"Team {winner_team_id}"

            loser_team_id = away_team_id if winner_team_id == home_team_id else home_team_id
            loser_team = self._team_loader.get_team_by_id(loser_team_id)
            loser_name = loser_team.full_name if loser_team else f"Team {loser_team_id}"

            if winner_team_id == home_team_id:
                winner_score = home_score
                loser_score = away_score
            else:
                winner_score = away_score
                loser_score = home_score

        self._team_name_label.setText(winner_name.upper())
        self._score_label.setText(f"{winner_score} - {loser_score}")
        self._opponent_label.setText(f"vs {loser_name}")

    def _populate_mvp_section(self):
        """Populate the MVP display."""
        if not self._super_bowl_mvp:
            self._mvp_group.hide()
            return

        self._mvp_group.show()

        player_name = self._super_bowl_mvp.get("player_name", "Unknown")
        position = self._super_bowl_mvp.get("position", "")
        team_id = self._super_bowl_mvp.get("team_id")

        team_abbr = ""
        if self._team_loader and team_id:
            team = self._team_loader.get_team_by_id(team_id)
            team_abbr = f" - {team.abbreviation}" if team else ""

        self._mvp_name_label.setText(f"{position} {player_name}{team_abbr}")

        stat_summary = self._super_bowl_mvp.get("stat_summary", "")
        if stat_summary:
            self._mvp_stats_label.setText(stat_summary)
            self._mvp_stats_label.show()
        else:
            self._mvp_stats_label.hide()

    def _show_empty_state(self):
        """Show empty state when no Super Bowl data."""
        self._header_label.hide()
        self._subtitle_label.hide()
        self._champion_frame.hide()
        self._mvp_group.hide()
        self._box_score_btn.hide()
        self._empty_label.show()

    def _get_super_bowl_number(self) -> str:
        """Get Super Bowl number in Roman numerals."""
        # Super Bowl I was 1966 season
        number = self._season - 1966 + 1
        return self._to_roman_numerals(number)

    def _to_roman_numerals(self, n: int) -> str:
        """Convert number to Roman numerals."""
        if n <= 0:
            return str(n)

        result = ""
        values = [
            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
        ]

        for value, numeral in values:
            while n >= value:
                result += numeral
                n -= value

        return result

    def _on_box_score_clicked(self):
        """Handle View Box Score button click."""
        if self._game_id:
            self.view_box_score.emit(self._game_id)
