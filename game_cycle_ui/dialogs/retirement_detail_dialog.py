"""
Retirement Detail Dialog - Career retrospective for retiring players.

Displays comprehensive career summary including:
- Player header with name, position, retirement details
- Career statistics (position-specific)
- Career timeline (teams played for)
- Awards and accomplishments
- Hall of Fame projection
- One-Day Contract offer button (for former team players)

Part of Milestone 17: Player Retirements, Tollgate 6.
"""

from typing import Dict, Any, Optional, List
import json
import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    Colors, Typography, FontSizes, TextColors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE
)

logger = logging.getLogger(__name__)


class RetirementDetailDialog(QDialog):
    """
    Career retrospective dialog for retired players.

    Shows complete career summary with statistics, timeline,
    awards, and Hall of Fame projection.

    Signals:
        one_day_contract_requested: Emitted when user clicks One-Day Contract button
    """

    one_day_contract_requested = Signal(int, int)  # player_id, team_id

    def __init__(
        self,
        retirement_data: Dict[str, Any],
        career_summary: Dict[str, Any],
        user_team_id: int = 0,
        parent=None
    ):
        """
        Initialize retirement detail dialog.

        Args:
            retirement_data: Dict with player_id, player_name, position, age_at_retirement,
                            years_played, final_team_id, retirement_reason, etc.
            career_summary: Dict with career stats, awards, teams_played_for,
                           hall_of_fame_score, etc.
            user_team_id: User's team ID (for One-Day Contract eligibility)
            parent: Parent widget
        """
        super().__init__(parent)

        self._retirement = retirement_data
        self._career = career_summary
        self._user_team_id = user_team_id
        self._player_id = retirement_data.get('player_id', 0)
        self._player_name = retirement_data.get('player_name', 'Unknown')

        self.setWindowTitle(f"Career Retrospective - {self._player_name}")
        self.setMinimumSize(700, 700)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog layout."""
        # Dark theme background
        DIALOG_BACKGROUND = "#1a1a1a"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DIALOG_BACKGROUND};
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: {FontSizes.H5};
                color: {TextColors.ON_DARK};
                background-color: #263238;
                border: 1px solid #37474f;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {TextColors.ON_DARK};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Header section
        self._create_header_section(content_layout)

        # Career statistics section
        self._create_stats_section(content_layout)

        # Career timeline section
        self._create_timeline_section(content_layout)

        # Awards and accomplishments section
        self._create_awards_section(content_layout)

        # Hall of Fame projection section
        self._create_hof_section(content_layout)

        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)

        # Bottom buttons
        self._create_buttons(main_layout)

    def _create_header_section(self, parent_layout: QVBoxLayout):
        """Create the player header with name and retirement info."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: #1a237e;
                border: 2px solid {Colors.INFO};
                border-radius: 10px;
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(header)
        layout.setSpacing(8)

        # Position and name
        position = self._retirement.get('position', '')
        name_label = QLabel(f"{position} {self._player_name}")
        name_label.setFont(Typography.H2)
        name_label.setStyleSheet("color: white;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # Age, seasons, HOF score
        age = self._retirement.get('age_at_retirement', 0)
        years = self._retirement.get('years_played', 0)
        hof_score = self._career.get('hall_of_fame_score', 0)

        subtitle = QLabel(f"Age {age} | {years} Seasons | HOF Score: {hof_score}")
        subtitle.setFont(Typography.BODY)
        subtitle.setStyleSheet("color: #90CAF9;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Retirement reason
        reason = self._format_retirement_reason(self._retirement.get('retirement_reason', ''))
        reason_label = QLabel(f"Retirement Reason: {reason}")
        reason_label.setFont(Typography.BODY_SMALL)
        reason_label.setStyleSheet(f"color: {Colors.MUTED};")
        reason_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(reason_label)

        # Headline if available
        headline = self._retirement.get('headline', '')
        if headline:
            headline_label = QLabel(f'"{headline}"')
            headline_label.setFont(Typography.BODY)
            headline_label.setStyleSheet("color: #FFD700; font-style: italic;")
            headline_label.setAlignment(Qt.AlignCenter)
            headline_label.setWordWrap(True)
            layout.addWidget(headline_label)

        parent_layout.addWidget(header)

    def _create_stats_section(self, parent_layout: QVBoxLayout):
        """Create position-specific career statistics section."""
        group = QGroupBox("CAREER STATISTICS")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        position = self._retirement.get('position', '').upper()

        # Games played/started
        games = self._career.get('games_played', 0)
        starts = self._career.get('games_started', 0)
        games_label = QLabel(f"Games: {games} ({starts} starts)")
        games_label.setFont(Typography.BODY)
        games_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        layout.addWidget(games_label)

        # Position-specific stats
        stats_text = self._build_position_stats(position)
        if stats_text:
            stats_label = QLabel(stats_text)
            stats_label.setFont(Typography.BODY)
            stats_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            stats_label.setWordWrap(True)
            layout.addWidget(stats_label)

        parent_layout.addWidget(group)

    def _build_position_stats(self, position: str) -> str:
        """Build position-specific stats string."""
        parts = []

        if position == 'QB':
            pass_yds = self._career.get('pass_yards', 0)
            pass_tds = self._career.get('pass_tds', 0)
            pass_ints = self._career.get('pass_ints', 0)
            parts.append(f"Passing: {pass_yds:,} yards | {pass_tds} TD | {pass_ints} INT")

            # Add rushing if significant
            rush_yds = self._career.get('rush_yards', 0)
            if rush_yds > 500:
                rush_tds = self._career.get('rush_tds', 0)
                parts.append(f"Rushing: {rush_yds:,} yards | {rush_tds} TD")

        elif position in ('RB', 'FB', 'HB'):
            rush_yds = self._career.get('rush_yards', 0)
            rush_tds = self._career.get('rush_tds', 0)
            parts.append(f"Rushing: {rush_yds:,} yards | {rush_tds} TD")

            rec = self._career.get('receptions', 0)
            rec_yds = self._career.get('rec_yards', 0)
            if rec > 50:
                parts.append(f"Receiving: {rec} catches | {rec_yds:,} yards")

        elif position in ('WR', 'TE'):
            rec = self._career.get('receptions', 0)
            rec_yds = self._career.get('rec_yards', 0)
            rec_tds = self._career.get('rec_tds', 0)
            parts.append(f"Receiving: {rec} catches | {rec_yds:,} yards | {rec_tds} TD")

        elif position in ('EDGE', 'DT', 'DE', 'LE', 'RE', 'NT'):
            tackles = self._career.get('tackles', 0)
            sacks = self._career.get('sacks', 0)
            ff = self._career.get('forced_fumbles', 0)
            parts.append(f"Defense: {tackles} tackles | {sacks:.1f} sacks | {ff} forced fumbles")

        elif position in ('LB', 'MLB', 'LOLB', 'ROLB', 'ILB'):
            tackles = self._career.get('tackles', 0)
            sacks = self._career.get('sacks', 0)
            ints = self._career.get('interceptions', 0)
            parts.append(f"Defense: {tackles} tackles | {sacks:.1f} sacks | {ints} INT")

        elif position in ('CB', 'FS', 'SS', 'S'):
            tackles = self._career.get('tackles', 0)
            ints = self._career.get('interceptions', 0)
            parts.append(f"Defense: {tackles} tackles | {ints} interceptions")

        elif position == 'K':
            fg_made = self._career.get('fg_made', 0)
            fg_att = self._career.get('fg_attempted', 0)
            pct = (fg_made / fg_att * 100) if fg_att > 0 else 0
            parts.append(f"Field Goals: {fg_made}/{fg_att} ({pct:.1f}%)")

        elif position == 'P':
            # Punter stats if available
            parts.append("Career punter statistics")

        else:
            # O-line or other positions
            parts.append(f"Career {position} statistics")

        return "\n".join(parts)

    def _create_timeline_section(self, parent_layout: QVBoxLayout):
        """Create career timeline showing teams played for."""
        group = QGroupBox("CAREER TIMELINE")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        teams = self._career.get('teams_played_for', [])
        primary_team_id = self._career.get('primary_team_id')

        if not teams:
            # Fallback to final team
            final_team_id = self._retirement.get('final_team_id', 0)
            if final_team_id > 0:
                teams = [final_team_id]

        if teams:
            for team_id in teams:
                team_name = self._get_team_name(team_id)
                is_primary = team_id == primary_team_id

                team_text = team_name
                if is_primary:
                    team_text += " ★"  # Primary team indicator

                team_label = QLabel(f"• {team_text}")
                team_label.setFont(Typography.BODY)
                color = "#FFD700" if is_primary else TextColors.ON_DARK
                team_label.setStyleSheet(f"color: {color};")
                layout.addWidget(team_label)
        else:
            no_data = QLabel("Team history unavailable")
            no_data.setStyleSheet(f"color: {Colors.MUTED};")
            layout.addWidget(no_data)

        parent_layout.addWidget(group)

    def _create_awards_section(self, parent_layout: QVBoxLayout):
        """Create awards and accomplishments section."""
        group = QGroupBox("ACCOMPLISHMENTS")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        awards_found = False

        # Super Bowl wins
        sb_wins = self._career.get('super_bowl_wins', 0)
        if sb_wins > 0:
            awards_found = True
            text = f"🏆 {sb_wins}x Super Bowl Champion"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet("color: #FFD700;")  # Gold
            layout.addWidget(label)

        # Super Bowl MVPs
        sb_mvps = self._career.get('super_bowl_mvps', 0)
        if sb_mvps > 0:
            awards_found = True
            text = f"🏆 {sb_mvps}x Super Bowl MVP"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet("color: #FFD700;")
            layout.addWidget(label)

        # MVP awards
        mvps = self._career.get('mvp_awards', 0)
        if mvps > 0:
            awards_found = True
            text = f"🏅 {mvps}x NFL MVP"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet("color: #C0C0C0;")  # Silver
            layout.addWidget(label)

        # Pro Bowls
        pro_bowls = self._career.get('pro_bowls', 0)
        if pro_bowls > 0:
            awards_found = True
            text = f"⭐ {pro_bowls}x Pro Bowl"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            layout.addWidget(label)

        # All-Pro First Team
        first_team = self._career.get('all_pro_first_team', 0)
        if first_team > 0:
            awards_found = True
            text = f"🥇 {first_team}x First-Team All-Pro"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            layout.addWidget(label)

        # All-Pro Second Team
        second_team = self._career.get('all_pro_second_team', 0)
        if second_team > 0:
            awards_found = True
            text = f"🥈 {second_team}x Second-Team All-Pro"
            label = QLabel(text)
            label.setFont(Typography.BODY)
            label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            layout.addWidget(label)

        if not awards_found:
            no_awards = QLabel("No major awards")
            no_awards.setStyleSheet(f"color: {Colors.MUTED};")
            layout.addWidget(no_awards)

        parent_layout.addWidget(group)

    def _create_hof_section(self, parent_layout: QVBoxLayout):
        """Create Hall of Fame projection section."""
        group = QGroupBox("HALL OF FAME PROJECTION")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        hof_score = self._career.get('hall_of_fame_score', 0)

        # Score label with status
        status = self._get_hof_status(hof_score)
        score_label = QLabel(f"Score: {hof_score}/100 - {status}")
        score_label.setFont(Typography.H5)
        score_label.setStyleSheet(f"color: {self._get_hof_color(hof_score)};")
        layout.addWidget(score_label)

        # Progress bar
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(hof_score)
        progress.setTextVisible(False)
        progress.setFixedHeight(20)
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #37474F;
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {self._get_hof_color(hof_score)};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(progress)

        # Eligibility
        retirement_season = self._retirement.get('retirement_season', 0)
        if retirement_season > 0:
            eligible_season = retirement_season + 5
            eligible_label = QLabel(f"Eligible: {eligible_season} Season")
            eligible_label.setFont(Typography.BODY_SMALL)
            eligible_label.setStyleSheet(f"color: {Colors.MUTED};")
            layout.addWidget(eligible_label)

        parent_layout.addWidget(group)

    def _create_buttons(self, parent_layout: QVBoxLayout):
        """Create bottom button row."""
        button_layout = QHBoxLayout()

        # One-Day Contract button (only if eligible)
        if self._is_eligible_for_one_day_contract():
            self._one_day_btn = QPushButton("Offer One-Day Contract")
            self._one_day_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
            self._one_day_btn.setMinimumWidth(180)
            self._one_day_btn.clicked.connect(self._on_one_day_contract)
            button_layout.addWidget(self._one_day_btn)

        button_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        parent_layout.addLayout(button_layout)

    def _is_eligible_for_one_day_contract(self) -> bool:
        """Check if player is eligible for one-day contract from user's team."""
        if self._user_team_id == 0:
            return False

        # Check if player already has one-day contract
        if self._retirement.get('one_day_contract_team_id'):
            return False

        # Check if player played for user's team
        teams = self._career.get('teams_played_for', [])
        primary_team = self._career.get('primary_team_id')
        final_team = self._retirement.get('final_team_id', 0)

        return (
            self._user_team_id in teams or
            self._user_team_id == primary_team or
            self._user_team_id == final_team
        )

    def _on_one_day_contract(self):
        """Handle One-Day Contract button click."""
        self.one_day_contract_requested.emit(self._player_id, self._user_team_id)
        # Update button state
        self._one_day_btn.setText("Contract Offered")
        self._one_day_btn.setEnabled(False)

    def _format_retirement_reason(self, reason: str) -> str:
        """Format retirement reason for display."""
        reason_map = {
            'age_decline': 'Age / Performance Decline',
            'injury': 'Career-Ending Injury',
            'championship': 'Retired as Champion',
            'contract': 'Contract Dispute',
            'personal': 'Personal Reasons',
            'released': 'Released / No Offers',
        }
        return reason_map.get(reason, reason.replace('_', ' ').title())

    def _get_team_name(self, team_id: int) -> str:
        """Get team name from team ID."""
        if team_id == 0:
            return "Free Agent"

        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.full_name if team else f"Team {team_id}"
        except Exception:
            return f"Team {team_id}"

    def _get_hof_status(self, score: int) -> str:
        """Get HOF status text based on score."""
        if score >= 85:
            return "FIRST BALLOT LOCK"
        elif score >= 70:
            return "STRONG CANDIDATE"
        elif score >= 50:
            return "BORDERLINE"
        elif score >= 30:
            return "LONG SHOT"
        else:
            return "UNLIKELY"

    def _get_hof_color(self, score: int) -> str:
        """Get HOF color based on score."""
        if score >= 85:
            return "#FFD700"  # Gold
        elif score >= 70:
            return "#4CAF50"  # Green
        elif score >= 50:
            return "#2196F3"  # Blue
        elif score >= 30:
            return "#FF9800"  # Orange
        else:
            return "#78909C"  # Gray

    # Public getters for testing
    def get_player_id(self) -> int:
        """Get the player ID."""
        return self._player_id

    def get_player_name(self) -> str:
        """Get the player name."""
        return self._player_name

    def get_hof_score(self) -> int:
        """Get the Hall of Fame score."""
        return self._career.get('hall_of_fame_score', 0)
