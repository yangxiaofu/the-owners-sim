"""
Game Preview Widget - Displays detailed preview of upcoming game.

Part of Team Dashboard. Shows team comparison and key player matchups
for the next unplayed game.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import ESPN_THEME


def _get_rank_color(rank: int) -> str:
    """Get color based on ranking position."""
    if rank <= 5:
        return "#4CAF50"  # Green - elite
    elif rank <= 15:
        return "#FFC107"  # Amber - good
    elif rank <= 25:
        return "#FF9800"  # Orange - average
    else:
        return "#F44336"  # Red - poor


def _get_rank_color_inverse(rank: int) -> str:
    """Get color for defensive rankings (lower is better)."""
    return _get_rank_color(rank)


class GamePreviewWidget(QWidget):
    """
    Widget displaying a detailed game preview.

    Shows:
    - Game header (Week, teams, home/away)
    - Team comparison table (offensive/defensive rankings, PPG)
    - Key player matchups (QB, RB, WR, DEF)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header section
        self._create_header_section(layout)

        # Team comparison section
        self._create_comparison_section(layout)

        # Key matchups section
        self._create_matchups_section(layout)

        # Empty state label (hidden by default)
        self.empty_label = QLabel("No upcoming games")
        self.empty_label.setFont(QFont("Arial", 22))
        self.empty_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

        layout.addStretch()

    def _create_header_section(self, parent_layout: QVBoxLayout):
        """Create the game header section."""
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 8px; }}"
        )

        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setSpacing(2)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # Top row: Week label + Home/Away badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.week_label = QLabel("WEEK -- PREVIEW")
        self.week_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.week_label.setStyleSheet(f"color: {ESPN_THEME['red']};")
        top_row.addWidget(self.week_label)

        top_row.addStretch()

        self.location_label = QLabel("HOME")
        self.location_label.setFont(QFont("Arial", 18))
        self.location_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
        top_row.addWidget(self.location_label)

        header_layout.addLayout(top_row)

        # Teams matchup
        self.matchup_label = QLabel("Team A vs Team B")
        self.matchup_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.matchup_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.matchup_label)

        parent_layout.addWidget(self.header_frame)

    def _create_comparison_section(self, parent_layout: QVBoxLayout):
        """Create the team comparison table."""
        self.comparison_frame = QFrame()
        self.comparison_frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 8px; }}"
        )

        comp_layout = QVBoxLayout(self.comparison_frame)
        comp_layout.setSpacing(0)
        comp_layout.setContentsMargins(12, 8, 12, 8)

        # Section header
        comp_header = QLabel("TEAM COMPARISON")
        comp_header.setFont(QFont("Arial", 20, QFont.Bold))
        comp_header.setStyleSheet("color: white;")
        comp_layout.addWidget(comp_header)

        # Grid for comparison
        self.comp_grid = QGridLayout()
        self.comp_grid.setSpacing(8)
        self.comp_grid.setContentsMargins(0, 12, 0, 0)

        # Column headers
        header_font = QFont("Arial", 18, QFont.Bold)

        spacer = QLabel("")
        self.comp_grid.addWidget(spacer, 0, 0)

        self.user_team_header = QLabel("User")
        self.user_team_header.setFont(header_font)
        self.user_team_header.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
        self.user_team_header.setAlignment(Qt.AlignCenter)
        self.comp_grid.addWidget(self.user_team_header, 0, 1)

        self.opp_team_header = QLabel("Opponent")
        self.opp_team_header.setFont(header_font)
        self.opp_team_header.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
        self.opp_team_header.setAlignment(Qt.AlignCenter)
        self.comp_grid.addWidget(self.opp_team_header, 0, 2)

        # Stat rows
        self.stat_labels = {}
        self.user_stat_values = {}
        self.opp_stat_values = {}

        stats = [
            ("record", "Record"),
            ("power_rank", "Power Ranking"),
            ("pass_off", "Pass Offense"),
            ("rush_off", "Rush Offense"),
            ("pass_def", "Pass Defense"),
            ("rush_def", "Rush Defense"),
            ("ppg", "Points/Game"),
            ("opp_ppg", "Opp Points/Game"),
        ]

        row_font = QFont("Arial", 18)
        value_font = QFont("Arial", 18, QFont.Bold)

        for row_idx, (key, label) in enumerate(stats, start=1):
            # Label
            stat_label = QLabel(label)
            stat_label.setFont(row_font)
            stat_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
            self.comp_grid.addWidget(stat_label, row_idx, 0)
            self.stat_labels[key] = stat_label

            # User value
            user_val = QLabel("--")
            user_val.setFont(value_font)
            user_val.setAlignment(Qt.AlignCenter)
            user_val.setStyleSheet("color: white;")
            self.comp_grid.addWidget(user_val, row_idx, 1)
            self.user_stat_values[key] = user_val

            # Opponent value
            opp_val = QLabel("--")
            opp_val.setFont(value_font)
            opp_val.setAlignment(Qt.AlignCenter)
            opp_val.setStyleSheet("color: white;")
            self.comp_grid.addWidget(opp_val, row_idx, 2)
            self.opp_stat_values[key] = opp_val

        comp_layout.addLayout(self.comp_grid)
        parent_layout.addWidget(self.comparison_frame)

    def _create_matchups_section(self, parent_layout: QVBoxLayout):
        """Create the key player matchups section."""
        self.matchups_frame = QFrame()
        self.matchups_frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 8px; }}"
        )

        matchups_layout = QVBoxLayout(self.matchups_frame)
        matchups_layout.setSpacing(8)
        matchups_layout.setContentsMargins(12, 12, 12, 12)

        # Section header
        matchups_header = QLabel("KEY MATCHUPS")
        matchups_header.setFont(QFont("Arial", 20, QFont.Bold))
        matchups_header.setStyleSheet("color: white;")
        matchups_layout.addWidget(matchups_header)

        # Matchup rows - store direct references to labels
        self.matchup_labels = {}  # {pos: {'user': QLabel, 'opp': QLabel}}
        positions = ["QB", "RB", "WR", "TE", "DL", "LB", "DB"]

        for pos in positions:
            row, user_label, opp_label = self._create_matchup_row(pos)
            matchups_layout.addWidget(row)
            self.matchup_labels[pos] = {'user': user_label, 'opp': opp_label}

        parent_layout.addWidget(self.matchups_frame)

    def _create_matchup_row(self, position: str):
        """Create a single matchup row. Returns (frame, user_label, opp_label)."""
        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 4px; }"
        )

        row_layout = QHBoxLayout(row_frame)
        row_layout.setSpacing(12)
        row_layout.setContentsMargins(12, 6, 12, 6)

        # Position badge
        pos_label = QLabel(position)
        pos_label.setFont(QFont("Arial", 16, QFont.Bold))
        pos_label.setStyleSheet(
            f"color: white; background-color: {ESPN_THEME['red']}; "
            "border-radius: 4px; padding: 2px 8px;"
        )
        pos_label.setFixedWidth(50)
        pos_label.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(pos_label)

        # User player info
        user_player = QLabel("--")
        user_player.setFont(QFont("Arial", 18))
        user_player.setStyleSheet("color: white;")
        row_layout.addWidget(user_player, 1)

        # VS separator
        vs_label = QLabel("vs")
        vs_label.setFont(QFont("Arial", 16))
        vs_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        vs_label.setAlignment(Qt.AlignCenter)
        vs_label.setFixedWidth(30)
        row_layout.addWidget(vs_label)

        # Opponent player info
        opp_player = QLabel("--")
        opp_player.setFont(QFont("Arial", 18))
        opp_player.setStyleSheet("color: white;")
        opp_player.setAlignment(Qt.AlignRight)
        row_layout.addWidget(opp_player, 1)

        return row_frame, user_player, opp_player

    def set_preview_data(
        self,
        week: int,
        user_team_name: str,
        opponent_name: str,
        is_home: bool,
        team_comparison: Dict[str, Dict],
        player_matchups: List[Dict]
    ):
        """
        Populate with game preview data.

        Args:
            week: Week number
            user_team_name: User's team name
            opponent_name: Opponent team name
            is_home: True if user is home team
            team_comparison: Dict with 'user' and 'opponent' stats:
                - pass_off_rank, rush_off_rank, pass_def_rank, rush_def_rank
                - ppg, opp_ppg
            player_matchups: List of dicts with:
                - position: str (QB, RB, WR, DEF)
                - user_player: str (name + rank)
                - opp_player: str (name + rank)
        """
        # Show content, hide empty state
        self.header_frame.show()
        self.comparison_frame.show()
        self.matchups_frame.show()
        self.empty_label.hide()

        # Header
        self.week_label.setText(f"WEEK {week} PREVIEW")

        if is_home:
            self.matchup_label.setText(f"{user_team_name} vs {opponent_name}")
            self.location_label.setText("HOME GAME")
        else:
            self.matchup_label.setText(f"{user_team_name} @ {opponent_name}")
            self.location_label.setText("AWAY GAME")

        # Team headers
        self.user_team_header.setText(user_team_name[:12])
        self.opp_team_header.setText(opponent_name[:12])

        # Team comparison stats
        user_stats = team_comparison.get('user', {})
        opp_stats = team_comparison.get('opponent', {})

        # Record (display as W-L)
        user_record = user_stats.get('record', '--')
        opp_record = opp_stats.get('record', '--')
        self.user_stat_values['record'].setText(user_record)
        self.user_stat_values['record'].setStyleSheet("color: white;")
        self.opp_stat_values['record'].setText(opp_record)
        self.opp_stat_values['record'].setStyleSheet("color: white;")

        # Power ranking (display as #X)
        user_power = user_stats.get('power_rank', 0)
        opp_power = opp_stats.get('power_rank', 0)
        if user_power > 0:
            self.user_stat_values['power_rank'].setText(f"#{user_power}")
            self.user_stat_values['power_rank'].setStyleSheet(
                f"color: {_get_rank_color(user_power)};"
            )
        else:
            self.user_stat_values['power_rank'].setText("--")
            self.user_stat_values['power_rank'].setStyleSheet("color: white;")

        if opp_power > 0:
            self.opp_stat_values['power_rank'].setText(f"#{opp_power}")
            self.opp_stat_values['power_rank'].setStyleSheet(
                f"color: {_get_rank_color(opp_power)};"
            )
        else:
            self.opp_stat_values['power_rank'].setText("--")
            self.opp_stat_values['power_rank'].setStyleSheet("color: white;")

        # Rankings (display as #X)
        rank_fields = [
            ('pass_off', 'pass_off_rank'),
            ('rush_off', 'rush_off_rank'),
            ('pass_def', 'pass_def_rank'),
            ('rush_def', 'rush_def_rank'),
        ]

        for display_key, stat_key in rank_fields:
            user_rank = user_stats.get(stat_key, 0)
            opp_rank = opp_stats.get(stat_key, 0)

            if user_rank > 0:
                self.user_stat_values[display_key].setText(f"#{user_rank}")
                self.user_stat_values[display_key].setStyleSheet(
                    f"color: {_get_rank_color(user_rank)};"
                )
            else:
                self.user_stat_values[display_key].setText("--")
                self.user_stat_values[display_key].setStyleSheet("color: white;")

            if opp_rank > 0:
                self.opp_stat_values[display_key].setText(f"#{opp_rank}")
                self.opp_stat_values[display_key].setStyleSheet(
                    f"color: {_get_rank_color(opp_rank)};"
                )
            else:
                self.opp_stat_values[display_key].setText("--")
                self.opp_stat_values[display_key].setStyleSheet("color: white;")

        # PPG stats (display as value)
        ppg_fields = [('ppg', 'ppg'), ('opp_ppg', 'opp_ppg')]

        for display_key, stat_key in ppg_fields:
            user_val = user_stats.get(stat_key, 0)
            opp_val = opp_stats.get(stat_key, 0)

            if user_val > 0:
                self.user_stat_values[display_key].setText(f"{user_val:.1f}")
            else:
                self.user_stat_values[display_key].setText("--")

            if opp_val > 0:
                self.opp_stat_values[display_key].setText(f"{opp_val:.1f}")
            else:
                self.opp_stat_values[display_key].setText("--")

        # Player matchups
        matchups_by_pos = {m['position']: m for m in player_matchups}

        for pos in ["QB", "RB", "WR", "TE", "DL", "LB", "DB"]:
            labels = self.matchup_labels.get(pos)
            if not labels:
                continue

            matchup = matchups_by_pos.get(pos, {})
            labels['user'].setText(matchup.get('user_player', '--'))
            labels['opp'].setText(matchup.get('opp_player', '--'))

    def clear(self):
        """Clear and show empty state."""
        self.header_frame.hide()
        self.comparison_frame.hide()
        self.matchups_frame.hide()
        self.empty_label.show()
