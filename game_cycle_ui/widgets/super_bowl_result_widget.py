"""
Super Bowl Result Widget - Displays Super Bowl champion and MVPs.

Extracted from SuperBowlResultsDialog for use in Season Recap tabbed view.
Redesigned with hero layout showing Champion, Super Bowl MVP, and League MVP.
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
    Widget displaying Super Bowl champion and MVPs (hero component).

    Shows:
    - Super Bowl number and season header
    - Champion team (hero) with result: "Bills defeat Rams 34-28"
    - Two MVP cards side-by-side: Super Bowl MVP and League MVP
    - View Box Score button

    Designed for ESPN dark theme.
    """

    view_box_score = Signal(str)  # game_id for navigation

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._super_bowl_result: Dict[str, Any] = {}
        self._super_bowl_mvp: Dict[str, Any] = {}
        self._league_mvp: Dict[str, Any] = {}  # NEW: League MVP data
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
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Header: "SEASON RECAP"
        self._header_label = QLabel()
        self._header_label.setFont(Typography.H1)
        self._header_label.setAlignment(Qt.AlignCenter)
        self._header_label.setStyleSheet(f"color: #FFD700;")  # Gold for championship
        layout.addWidget(self._header_label)

        # Subtitle: "Super Bowl LX"
        self._subtitle_label = QLabel()
        self._subtitle_label.setFont(Typography.H4)
        self._subtitle_label.setAlignment(Qt.AlignCenter)
        self._subtitle_label.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(self._subtitle_label)

        # Champion frame (HERO section)
        self._champion_frame = self._create_champion_section()
        layout.addWidget(self._champion_frame)

        # MVP cards row (Super Bowl MVP + League MVP side-by-side)
        self._mvp_cards_row = self._create_mvp_cards_row()
        layout.addLayout(self._mvp_cards_row)

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
        """Create the champion display frame (hero component)."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 2px solid #FFD700;
                border-radius: 12px;
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        # "SUPER BOWL CHAMPION" label
        champions_label = QLabel("SUPER BOWL CHAMPION")
        champions_label.setFont(Typography.H5)
        champions_label.setAlignment(Qt.AlignCenter)
        champions_label.setStyleSheet("color: #FFD700; letter-spacing: 3px;")
        layout.addWidget(champions_label)

        layout.addSpacing(8)

        # Team name (HERO - large)
        self._team_name_label = QLabel()
        self._team_name_label.setFont(Typography.H1)
        self._team_name_label.setAlignment(Qt.AlignCenter)
        self._team_name_label.setStyleSheet("color: white; font-size: 36px; font-weight: bold;")
        layout.addWidget(self._team_name_label)

        layout.addSpacing(8)

        # Result: "Bills defeat Rams 34-28"
        self._result_label = QLabel()
        self._result_label.setFont(Typography.H4)
        self._result_label.setAlignment(Qt.AlignCenter)
        self._result_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(self._result_label)

        return frame

    def _create_mvp_cards_row(self) -> QHBoxLayout:
        """Create row with Super Bowl MVP and League MVP cards side-by-side."""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)

        # Super Bowl MVP card
        self._sb_mvp_card = self._create_mvp_card("SUPER BOWL MVP")
        row_layout.addWidget(self._sb_mvp_card)

        # League MVP card
        self._league_mvp_card = self._create_mvp_card("LEAGUE MVP")
        row_layout.addWidget(self._league_mvp_card)

        return row_layout

    def _create_mvp_card(self, title: str) -> QFrame:
        """Create an MVP card widget."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Title label
        title_label = QLabel(title)
        title_label.setFont(Typography.H6)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FFD700; letter-spacing: 2px;")
        layout.addWidget(title_label)

        layout.addSpacing(8)

        # Player name and position
        name_label = QLabel()
        name_label.setFont(Typography.H4)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: white;")
        name_label.setObjectName("name_label")
        layout.addWidget(name_label)

        # Team
        team_label = QLabel()
        team_label.setFont(Typography.BODY)
        team_label.setAlignment(Qt.AlignCenter)
        team_label.setStyleSheet(f"color: {Colors.MUTED};")
        team_label.setObjectName("team_label")
        layout.addWidget(team_label)

        # Stats (optional)
        stats_label = QLabel()
        stats_label.setFont(Typography.SMALL)
        stats_label.setAlignment(Qt.AlignCenter)
        stats_label.setStyleSheet(f"color: #888888;")
        stats_label.setWordWrap(True)
        stats_label.setObjectName("stats_label")
        stats_label.hide()  # Only show if stats available
        layout.addWidget(stats_label)

        return card

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
        season: int,
        league_mvp: Optional[Dict[str, Any]] = None
    ):
        """
        Populate widget with Super Bowl and MVP data.

        Args:
            super_bowl_result: Dict with winner_team_id, home_team_id, away_team_id,
                              home_score, away_score, game_id
            super_bowl_mvp: Dict with player_name, position, team_id, stat_summary
            team_loader: TeamLoader for getting team names
            season: Season year
            league_mvp: Dict with player_name, position, team_id (optional)
        """
        self._super_bowl_result = super_bowl_result or {}
        self._super_bowl_mvp = super_bowl_mvp or {}
        self._league_mvp = league_mvp or {}
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
        self._sb_mvp_card.show()
        self._league_mvp_card.show()
        self._box_score_btn.show()
        self._empty_label.hide()

        # Header: "SEASON RECAP" with subtitle "Super Bowl LX"
        sb_number = self._get_super_bowl_number()
        self._header_label.setText("SEASON RECAP")
        self._subtitle_label.setText(f"Super Bowl {sb_number}")

        # Champion section
        self._populate_champion_section()

        # MVP cards (both)
        self._populate_mvp_cards()

        # Box score button
        self._box_score_btn.setEnabled(bool(self._game_id))

    def _populate_champion_section(self):
        """Populate the champion display with sentence format and team colors."""

        winner_team_id = self._super_bowl_result.get("winner_team_id")
        home_team_id = self._super_bowl_result.get("home_team_id")
        away_team_id = self._super_bowl_result.get("away_team_id")
        home_score = self._super_bowl_result.get("home_score", 0)
        away_score = self._super_bowl_result.get("away_score", 0)

        winner_name = "Unknown"
        loser_name = "Unknown"
        winner_score = 0
        loser_score = 0
        team_primary_color = "#FFD700"  # Default gold
        team_secondary_color = "#FFFFFF"

        if self._team_loader and winner_team_id:
            winner_team = self._team_loader.get_team_by_id(winner_team_id)
            winner_name = winner_team.full_name if winner_team else f"Team {winner_team_id}"

            # Get team colors
            if winner_team and hasattr(winner_team, 'colors') and winner_team.colors:
                team_primary_color = winner_team.colors.get('primary', '#FFD700')
                team_secondary_color = winner_team.colors.get('secondary', '#FFFFFF')

            loser_team_id = away_team_id if winner_team_id == home_team_id else home_team_id
            loser_team = self._team_loader.get_team_by_id(loser_team_id)
            loser_name = loser_team.full_name if loser_team else f"Team {loser_team_id}"

            if winner_team_id == home_team_id:
                winner_score = home_score
                loser_score = away_score
            else:
                winner_score = away_score
                loser_score = home_score

        # Update champion frame with team colors
        self._champion_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 3px solid {team_primary_color};
                border-radius: 12px;
                padding: 16px;
            }}
        """)

        # Update header color to match team
        self._header_label.setStyleSheet(f"color: {team_primary_color};")

        # Update "SUPER BOWL CHAMPION" label color
        for child in self._champion_frame.findChildren(QLabel):
            if child.text() == "SUPER BOWL CHAMPION":
                child.setStyleSheet(f"color: {team_primary_color}; letter-spacing: 3px;")
                break

        # Team name (hero, large) - use team color
        self._team_name_label.setText(winner_name.upper())
        self._team_name_label.setStyleSheet(f"color: {team_primary_color}; font-size: 36px; font-weight: bold;")

        # Result sentence: "defeat Rams 34-28"
        self._result_label.setText(f"defeat {loser_name} {winner_score}-{loser_score}")

    def _populate_mvp_cards(self):
        """Populate both MVP cards."""
        # Super Bowl MVP
        self._populate_mvp_card(
            self._sb_mvp_card,
            self._super_bowl_mvp,
            show_stats=True
        )

        # League MVP
        self._populate_mvp_card(
            self._league_mvp_card,
            self._league_mvp,
            show_stats=False
        )

    def _populate_mvp_card(self, card: QFrame, mvp_data: Dict[str, Any], show_stats: bool = False):
        """Populate a single MVP card."""
        name_label = card.findChild(QLabel, "name_label")
        team_label = card.findChild(QLabel, "team_label")
        stats_label = card.findChild(QLabel, "stats_label")

        if not mvp_data:
            name_label.setText("TBD")
            team_label.setText("")
            stats_label.hide()
            return

        player_name = mvp_data.get("player_name", "Unknown")
        position = mvp_data.get("position", "")
        team_id = mvp_data.get("team_id")

        # Name with position: "Patrick Mahomes"
        name_label.setText(player_name)

        # Team info: "QB - Chiefs"
        team_abbr = ""
        if self._team_loader and team_id:
            team = self._team_loader.get_team_by_id(team_id)
            team_abbr = team.abbreviation if team else f"Team {team_id}"

        team_label.setText(f"{position} - {team_abbr}" if position else team_abbr)

        # Stats (optional)
        stat_summary = mvp_data.get("stat_summary", "")
        if show_stats and stat_summary:
            stats_label.setText(stat_summary)
            stats_label.show()
        else:
            stats_label.hide()

    def _show_empty_state(self):
        """Show empty state when no Super Bowl data."""
        self._header_label.hide()
        self._subtitle_label.hide()
        self._champion_frame.hide()
        self._sb_mvp_card.hide()
        self._league_mvp_card.hide()
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
