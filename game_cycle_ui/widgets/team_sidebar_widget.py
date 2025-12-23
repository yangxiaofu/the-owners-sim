"""
Team Sidebar Widget - Left panel for Team Dashboard.

Displays team identity, record, power ranking, coaching style,
stats snapshot, and top performers.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    TIER_COLORS, MOVEMENT_COLORS, ESPN_THEME, Colors,
    Typography, FontSizes, TextColors
)


class TeamSidebarWidget(QWidget):
    """
    Sidebar widget displaying team overview information.

    Sections:
    1. Team Identity Banner - Team colors, abbreviation
    2. Record Section - W-L-T, division standing, home/away splits
    3. Power Ranking - Current rank, movement arrow, tier
    4. Coaching Style - HC/OC/DC philosophy names
    5. Star Power - Popularity tier counts and top draw player
    6. Stats Snapshot - PPG, Opp PPG, Turnover Diff
    7. Top Performers - Best player per position group
    """

    # Signals
    player_clicked = Signal(int)  # Emitted when a player name is clicked

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._team_id: Optional[int] = None
        self._team_data: Dict[str, Any] = {}
        self._standing: Optional[Any] = None  # TeamStanding dataclass
        self._power_ranking: Optional[Any] = None  # PowerRanking dataclass
        self._team_stats: Optional[Any] = None  # TeamSeasonStats dataclass
        self._top_performers: List[Dict] = []
        self._coaching_style: Dict[str, str] = {}

        self.setFixedWidth(280)
        self._setup_ui()

    def _setup_ui(self):
        """Build the sidebar layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Team Identity Banner
        self._create_identity_banner(layout)

        # 2. Record Section
        self._create_record_section(layout)

        # 3. Power Ranking
        self._create_power_ranking_section(layout)

        # 4. Coaching Style
        self._create_coaching_section(layout)

        # 5. Star Power
        self._create_star_power_section(layout)

        # 6. Stats Snapshot
        self._create_stats_section(layout)

        # 7. Top Performers
        self._create_top_performers_section(layout)

        # Push everything up
        layout.addStretch()

    def _create_identity_banner(self, parent_layout: QVBoxLayout):
        """Create team identity banner with colors and abbreviation."""
        self.identity_frame = QFrame()
        self.identity_frame.setFixedHeight(80)
        self.identity_frame.setStyleSheet(
            f"background-color: {ESPN_THEME['dark_bg']}; "
            "border-radius: 8px;"
        )

        banner_layout = QVBoxLayout(self.identity_frame)
        banner_layout.setAlignment(Qt.AlignCenter)

        # Team abbreviation (large)
        self.team_abbrev_label = QLabel("---")
        self.team_abbrev_label.setFont(Typography.DISPLAY)
        self.team_abbrev_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.team_abbrev_label.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.team_abbrev_label)

        # Team full name (smaller)
        self.team_name_label = QLabel("Select a team")
        self.team_name_label.setFont(Typography.CAPTION)
        self.team_name_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        self.team_name_label.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(self.team_name_label)

        parent_layout.addWidget(self.identity_frame)

    def _create_record_section(self, parent_layout: QVBoxLayout):
        """Create record section with W-L-T and splits."""
        self.record_frame = QFrame()
        self.record_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        record_layout = QVBoxLayout(self.record_frame)
        record_layout.setSpacing(4)
        record_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("RECORD")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        record_layout.addWidget(header)

        # Main record (W-L-T)
        self.record_label = QLabel("0-0-0")
        self.record_label.setFont(Typography.H2)
        self.record_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        record_layout.addWidget(self.record_label)

        # Division standing
        self.division_label = QLabel("")
        self.division_label.setFont(Typography.SMALL)
        self.division_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        record_layout.addWidget(self.division_label)

        # Splits row
        splits_layout = QHBoxLayout()
        splits_layout.setSpacing(16)

        self.home_label = QLabel("Home: 0-0")
        self.home_label.setFont(Typography.TINY)
        self.home_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        splits_layout.addWidget(self.home_label)

        self.away_label = QLabel("Away: 0-0")
        self.away_label.setFont(Typography.TINY)
        self.away_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        splits_layout.addWidget(self.away_label)

        splits_layout.addStretch()
        record_layout.addLayout(splits_layout)

        parent_layout.addWidget(self.record_frame)

    def _create_power_ranking_section(self, parent_layout: QVBoxLayout):
        """Create power ranking section."""
        self.ranking_frame = QFrame()
        self.ranking_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        ranking_layout = QVBoxLayout(self.ranking_frame)
        ranking_layout.setSpacing(4)
        ranking_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("POWER RANKING")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        ranking_layout.addWidget(header)

        # Rank row
        rank_row = QHBoxLayout()

        self.rank_label = QLabel("#--")
        self.rank_label.setFont(Typography.H1)
        self.rank_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        rank_row.addWidget(self.rank_label)

        self.movement_label = QLabel("")
        self.movement_label.setFont(Typography.H5)
        rank_row.addWidget(self.movement_label)

        rank_row.addStretch()
        ranking_layout.addLayout(rank_row)

        # Tier label
        self.tier_label = QLabel("")
        self.tier_label.setFont(Typography.SMALL_BOLD)
        self.tier_label.setStyleSheet(
            "padding: 2px 8px; border-radius: 4px;"
        )
        ranking_layout.addWidget(self.tier_label)

        parent_layout.addWidget(self.ranking_frame)

    def _create_coaching_section(self, parent_layout: QVBoxLayout):
        """Create coaching style section."""
        self.coaching_frame = QFrame()
        self.coaching_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        coaching_layout = QVBoxLayout(self.coaching_frame)
        coaching_layout.setSpacing(4)
        coaching_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("COACHING STYLE")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        coaching_layout.addWidget(header)

        # Coach entries
        self.hc_label = QLabel("HC: --")
        self.hc_label.setFont(Typography.SMALL)
        self.hc_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        coaching_layout.addWidget(self.hc_label)

        self.oc_label = QLabel("OC: --")
        self.oc_label.setFont(Typography.SMALL)
        self.oc_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        coaching_layout.addWidget(self.oc_label)

        self.dc_label = QLabel("DC: --")
        self.dc_label.setFont(Typography.SMALL)
        self.dc_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        coaching_layout.addWidget(self.dc_label)

        parent_layout.addWidget(self.coaching_frame)

    def _create_star_power_section(self, parent_layout: QVBoxLayout):
        """Create star power summary section."""
        self.star_power_frame = QFrame()
        self.star_power_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        star_layout = QVBoxLayout(self.star_power_frame)
        star_layout.setSpacing(4)
        star_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("STAR POWER")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        star_layout.addWidget(header)

        # Tier counts line
        self.tier_counts_label = QLabel("Calculating...")
        self.tier_counts_label.setFont(Typography.SMALL)
        self.tier_counts_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.tier_counts_label.setWordWrap(True)
        star_layout.addWidget(self.tier_counts_label)

        # Top draw line
        self.top_draw_label = QLabel("")
        self.top_draw_label.setFont(Typography.SMALL)
        self.top_draw_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        star_layout.addWidget(self.top_draw_label)

        parent_layout.addWidget(self.star_power_frame)

    def _create_stats_section(self, parent_layout: QVBoxLayout):
        """Create stats snapshot section."""
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        stats_layout = QVBoxLayout(self.stats_frame)
        stats_layout.setSpacing(4)
        stats_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("SEASON STATS")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        stats_layout.addWidget(header)

        # Stats grid
        grid = QGridLayout()
        grid.setSpacing(8)

        # PPG
        ppg_title = QLabel("PPG")
        ppg_title.setFont(Typography.TINY)
        ppg_title.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        grid.addWidget(ppg_title, 0, 0)

        self.ppg_value = QLabel("0.0")
        self.ppg_value.setFont(Typography.H5)
        self.ppg_value.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(self.ppg_value, 1, 0)

        # Opp PPG
        opp_title = QLabel("Opp PPG")
        opp_title.setFont(Typography.TINY)
        opp_title.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        grid.addWidget(opp_title, 0, 1)

        self.opp_ppg_value = QLabel("0.0")
        self.opp_ppg_value.setFont(Typography.H5)
        self.opp_ppg_value.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(self.opp_ppg_value, 1, 1)

        # Turnover Diff
        to_title = QLabel("TO Diff")
        to_title.setFont(Typography.TINY)
        to_title.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        grid.addWidget(to_title, 0, 2)

        self.to_diff_value = QLabel("0")
        self.to_diff_value.setFont(Typography.H5)
        self.to_diff_value.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(self.to_diff_value, 1, 2)

        stats_layout.addLayout(grid)
        parent_layout.addWidget(self.stats_frame)

    def _create_top_performers_section(self, parent_layout: QVBoxLayout):
        """Create top performers section."""
        self.performers_frame = QFrame()
        self.performers_frame.setStyleSheet(
            "QFrame { background-color: #1a1a1a; border-radius: 6px; }"
        )

        performers_layout = QVBoxLayout(self.performers_frame)
        performers_layout.setSpacing(6)
        performers_layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("TOP PERFORMERS")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        performers_layout.addWidget(header)

        # Performer rows (will be populated dynamically)
        self.performer_labels: List[QLabel] = []
        for _ in range(4):  # QB, RB, WR, DEF
            row = QHBoxLayout()

            pos_label = QLabel("--")
            pos_label.setFont(Typography.TINY_BOLD)
            pos_label.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
            pos_label.setFixedWidth(30)
            row.addWidget(pos_label)

            name_label = QLabel("--")
            name_label.setFont(Typography.SMALL)
            name_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            row.addWidget(name_label, 1)

            rank_label = QLabel("--")
            rank_label.setFont(Typography.SMALL_BOLD)
            rank_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            rank_label.setAlignment(Qt.AlignRight)
            row.addWidget(rank_label)

            self.performer_labels.append({
                'pos': pos_label,
                'name': name_label,
                'rank': rank_label
            })

            performers_layout.addLayout(row)

        parent_layout.addWidget(self.performers_frame)

    # =========================================================================
    # Public Methods
    # =========================================================================

    def set_team_data(self, team_id: int, team_data: Dict[str, Any]):
        """
        Set team identity data.

        Args:
            team_id: Team ID (1-32)
            team_data: Dict with keys: abbreviation, city, nickname, colors
        """
        self._team_id = team_id
        self._team_data = team_data

        # Update identity banner
        abbrev = team_data.get('abbreviation', '---')
        self.team_abbrev_label.setText(abbrev)

        city = team_data.get('city', '')
        nickname = team_data.get('nickname', '')
        self.team_name_label.setText(f"{city} {nickname}")

        # Set team colors on banner
        primary_color = team_data.get('colors', {}).get('primary', '#333')
        self.identity_frame.setStyleSheet(
            f"background-color: {primary_color}; border-radius: 8px;"
        )

    def set_standing(self, standing: Any):
        """
        Set team standing data.

        Args:
            standing: TeamStanding dataclass with wins, losses, ties, etc.
        """
        self._standing = standing
        if not standing:
            return

        # Main record
        wins = standing.wins
        losses = standing.losses
        ties = standing.ties
        self.record_label.setText(f"{wins}-{losses}-{ties}")

        # Division standing (compute from context if needed)
        division = self._team_data.get('division', '')
        conference = self._team_data.get('conference', '')
        if standing.playoff_seed:
            self.division_label.setText(
                f"#{standing.playoff_seed} seed • {conference} {division}"
            )
        else:
            self.division_label.setText(f"{conference} {division}")

        # Home/Away splits
        self.home_label.setText(f"Home: {standing.home_wins}-{standing.home_losses}")
        self.away_label.setText(f"Away: {standing.away_wins}-{standing.away_losses}")

    def set_power_ranking(self, ranking: Any):
        """
        Set power ranking data.

        Args:
            ranking: PowerRanking dataclass with rank, tier, movement, etc.
        """
        self._power_ranking = ranking
        if not ranking:
            self.rank_label.setText("#--")
            self.movement_label.setText("")
            self.tier_label.setText("")
            return

        # Rank
        self.rank_label.setText(f"#{ranking.rank}")

        # Movement
        movement = ranking.movement
        if movement.startswith("▲"):
            color = MOVEMENT_COLORS.get('up', Colors.SUCCESS)
            self.movement_label.setStyleSheet(f"color: {color};")
        elif movement.startswith("▼"):
            color = MOVEMENT_COLORS.get('down', Colors.ERROR)
            self.movement_label.setStyleSheet(f"color: {color};")
        else:
            color = MOVEMENT_COLORS.get('same', Colors.MUTED)
            self.movement_label.setStyleSheet(f"color: {color};")
        self.movement_label.setText(movement)

        # Tier
        tier = ranking.tier or 'UNKNOWN'
        tier_color = TIER_COLORS.get(tier, '#444')
        self.tier_label.setText(tier)
        self.tier_label.setStyleSheet(
            f"background-color: {tier_color}; color: {TextColors.ON_DARK}; "
            "padding: 2px 8px; border-radius: 4px;"
        )

    def set_coaching_style(
        self, hc_style: str = "", oc_style: str = "", dc_style: str = ""
    ):
        """
        Set coaching philosophy names.

        Args:
            hc_style: Head coach style (e.g., "Aggressive", "Conservative")
            oc_style: Offensive coordinator style (e.g., "Air Raid", "West Coast")
            dc_style: Defensive coordinator style (e.g., "Zone Coverage", "Man Press")
        """
        self._coaching_style = {
            'hc': hc_style,
            'oc': oc_style,
            'dc': dc_style
        }

        self.hc_label.setText(f"HC: {hc_style or '--'}")
        self.oc_label.setText(f"OC: {oc_style or '--'}")
        self.dc_label.setText(f"DC: {dc_style or '--'}")

    def set_team_stats(self, stats: Any):
        """
        Set team season stats.

        Args:
            stats: TeamSeasonStats dataclass with points, turnovers, etc.
        """
        self._team_stats = stats
        if not stats:
            return

        # PPG
        ppg = stats.points_per_game
        self.ppg_value.setText(f"{ppg:.1f}")

        # Opp PPG
        opp_ppg = stats.points_allowed_per_game
        self.opp_ppg_value.setText(f"{opp_ppg:.1f}")

        # Turnover differential
        to_diff = stats.turnover_margin
        if to_diff > 0:
            self.to_diff_value.setText(f"+{to_diff}")
            self.to_diff_value.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif to_diff < 0:
            self.to_diff_value.setText(f"{to_diff}")
            self.to_diff_value.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.to_diff_value.setText("0")
            self.to_diff_value.setStyleSheet(f"color: {TextColors.ON_DARK};")

    def set_star_power(self, star_power_data: Dict):
        """
        Set star power summary data.

        Args:
            star_power_data: Dict with keys:
                - transcendent_count: int
                - star_count: int
                - known_count: int
                - top_player_name: str (optional)
                - top_player_score: int (optional)
        """
        transcendent = star_power_data.get('transcendent_count', 0)
        stars = star_power_data.get('star_count', 0)
        known = star_power_data.get('known_count', 0)
        top_name = star_power_data.get('top_player_name')
        top_score = star_power_data.get('top_player_score')

        # Build tier counts line with color coding
        parts = []
        if transcendent > 0:
            parts.append(f'<span style="color: #FFD700; font-weight: bold;">{transcendent} Transcendent</span>')
        if stars > 0:
            parts.append(f'<span style="color: #87CEEB; font-weight: bold;">{stars} Stars</span>')
        if known > 0:
            parts.append(f'{known} Known')

        if parts:
            tier_text = ', '.join(parts)
        else:
            tier_text = '<span style="color: #999;">No Star Players</span>'

        self.tier_counts_label.setText(tier_text)

        # Top draw line
        if top_name and top_score is not None:
            self.top_draw_label.setText(f'<b>Top Draw:</b> {top_name} ({top_score})')
        else:
            self.top_draw_label.setText('')

    def set_top_performers(self, performers: List[Dict]):
        """
        Set top performers by position group.

        Args:
            performers: List of dicts with keys:
                - position: str (e.g., "QB", "RB", "WR", "DEF")
                - name: str
                - rank: int (league rank at position)
                - player_id: int (optional)
        """
        self._top_performers = performers

        # Clear existing
        for i, labels in enumerate(self.performer_labels):
            labels['pos'].setText("--")
            labels['name'].setText("--")
            labels['rank'].setText("--")
            labels['rank'].setStyleSheet(f"color: {Colors.MUTED};")

        # Populate with data
        for i, performer in enumerate(performers[:4]):
            if i >= len(self.performer_labels):
                break

            labels = self.performer_labels[i]
            labels['pos'].setText(performer.get('position', '--'))
            labels['name'].setText(performer.get('name', '--'))

            rank = performer.get('rank', 0)
            labels['rank'].setText(f"#{rank}")

            # Color code rank (lower is better)
            if rank <= 5:
                color = Colors.SUCCESS  # Green (elite)
            elif rank <= 15:
                color = Colors.WARNING  # Amber (good)
            elif rank <= 25:
                color = Colors.WARNING  # Orange (average)
            else:
                color = Colors.ERROR  # Red (below average)
            labels['rank'].setStyleSheet(f"color: {color};")

    def clear(self):
        """Reset all display data."""
        self._team_id = None
        self._team_data = {}
        self._standing = None
        self._power_ranking = None
        self._team_stats = None
        self._top_performers = []
        self._coaching_style = {}

        # Reset UI
        self.team_abbrev_label.setText("---")
        self.team_name_label.setText("Select a team")
        self.identity_frame.setStyleSheet(
            f"background-color: {ESPN_THEME['dark_bg']}; "
            "border-radius: 8px;"
        )
        self.record_label.setText("0-0-0")
        self.division_label.setText("")
        self.home_label.setText("Home: 0-0")
        self.away_label.setText("Away: 0-0")
        self.rank_label.setText("#--")
        self.movement_label.setText("")
        self.tier_label.setText("")
        self.hc_label.setText("HC: --")
        self.oc_label.setText("OC: --")
        self.dc_label.setText("DC: --")
        self.ppg_value.setText("0.0")
        self.opp_ppg_value.setText("0.0")
        self.to_diff_value.setText("0")
        self.to_diff_value.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.tier_counts_label.setText("Calculating...")
        self.top_draw_label.setText("")

        for labels in self.performer_labels:
            labels['pos'].setText("--")
            labels['name'].setText("--")
            labels['rank'].setText("--")
            labels['rank'].setStyleSheet(f"color: {Colors.MUTED};")
