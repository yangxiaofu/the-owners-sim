"""
Player Detail Dialog - Dashboard-style display of player stats and game logs.

Displays:
- Player header with name, position, team
- Season stats card with key statistics
- Player info card with OVR, age, experience, rank
- Game log table showing per-game performance
- Season highs and recent form cards
"""

from typing import Dict, Optional, List, Any
import sqlite3

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from game_cycle.database.player_stats_api import PlayerSeasonStatsAPI
from game_cycle_ui.theme import (
    Colors,
    Typography,
    FontSizes,
    TextColors,
    NEUTRAL_BUTTON_STYLE,
    get_grade_color,
    apply_table_style
)


# Position abbreviation mapping (normalized)
POSITION_ABBREV = {
    'quarterback': 'QB', 'qb': 'QB',
    'running_back': 'RB', 'halfback': 'RB', 'rb': 'RB', 'hb': 'RB',
    'fullback': 'FB', 'fb': 'FB',
    'wide_receiver': 'WR', 'wr': 'WR',
    'tight_end': 'TE', 'te': 'TE',
    'left_tackle': 'LT', 'lt': 'LT',
    'left_guard': 'LG', 'lg': 'LG',
    'center': 'C', 'c': 'C',
    'right_guard': 'RG', 'rg': 'RG',
    'right_tackle': 'RT', 'rt': 'RT',
    'guard': 'G', 'g': 'G',
    'tackle': 'T', 't': 'T',
    'offensive_line': 'OL', 'ol': 'OL',
    'offensive_guard': 'OG', 'og': 'OG',
    'offensive_tackle': 'OT', 'ot': 'OT',
    'left_end': 'LE', 'le': 'LE',
    'defensive_tackle': 'DT', 'dt': 'DT',
    'nose_tackle': 'NT', 'nt': 'NT',
    'right_end': 'RE', 're': 'RE',
    'defensive_end': 'DE', 'de': 'DE',
    'edge': 'EDGE',
    'left_outside_linebacker': 'LOLB', 'lolb': 'LOLB',
    'middle_linebacker': 'MLB', 'mlb': 'MLB', 'mike': 'MLB',
    'linebacker': 'LB', 'lb': 'LB',
    'right_outside_linebacker': 'ROLB', 'rolb': 'ROLB',
    'inside_linebacker': 'ILB', 'ilb': 'ILB',
    'cornerback': 'CB', 'cb': 'CB',
    'free_safety': 'FS', 'fs': 'FS',
    'strong_safety': 'SS', 'ss': 'SS',
    'safety': 'S', 's': 'S',
    'kicker': 'K', 'k': 'K',
    'punter': 'P', 'p': 'P',
    'long_snapper': 'LS', 'ls': 'LS',
}

# Position group mapping for stats display
POSITION_GROUPS = {
    'QB': 'passing',
    'RB': 'rushing', 'HB': 'rushing', 'FB': 'rushing',
    'WR': 'receiving', 'TE': 'receiving',
    'LT': 'blocking', 'LG': 'blocking', 'C': 'blocking', 'RG': 'blocking', 'RT': 'blocking',
    'LE': 'defense', 'DT': 'defense', 'NT': 'defense', 'RE': 'defense', 'DE': 'defense', 'EDGE': 'defense',
    'LOLB': 'defense', 'MLB': 'defense', 'LB': 'defense', 'ROLB': 'defense', 'ILB': 'defense',
    'CB': 'defense', 'FS': 'defense', 'SS': 'defense', 'S': 'defense',
    'K': 'kicking', 'P': 'punting',
}


class PlayerDetailDialog(QDialog):
    """
    Dashboard-style dialog showing player stats and game logs.

    Displays:
    - Season stats summary (position-specific)
    - Player info (OVR, age, experience)
    - Game log table (per-game stats)
    - Season highs and recent form
    """

    def __init__(
        self,
        player_id: int,
        player_name: str,
        player_data: Dict,
        dynasty_id: str,
        season: int,
        db_path: str,
        team_name: str = "",
        parent=None
    ):
        """
        Initialize player detail dialog.

        Args:
            player_id: Player's ID
            player_name: Player's display name
            player_data: Dict with position, overall, age, experience, etc.
            dynasty_id: Current dynasty ID
            season: Current season year
            db_path: Path to the game_cycle database
            team_name: Player's team name for display
            parent: Parent widget
        """
        super().__init__(parent)
        self._player_id = player_id
        self._player_name = player_name
        self._player_data = player_data
        self._dynasty_id = dynasty_id
        self._season = season
        self._db_path = db_path
        self._team_name = team_name

        # Enrich player_data with years_pro if not present
        self._enrich_player_data()

        # Data containers
        self._season_stats: Dict[str, Any] = {}
        self._game_log: List[Dict] = []
        self._game_grades: Dict[str, float] = {}  # game_id -> grade

        self.setWindowTitle(f"Player Details - {player_name}")
        self.setMinimumSize(750, 650)
        self.setModal(True)

        self._setup_ui()
        self._load_data()

    def _enrich_player_data(self):
        """Load additional player data from database if not provided."""
        # Skip if years_pro is already present
        if 'years_pro' in self._player_data:
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT years_pro, birthdate, positions, attributes
                FROM players
                WHERE dynasty_id = ? AND player_id = ?
                """,
                (self._dynasty_id, self._player_id)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                # Copy years_pro
                if row['years_pro'] is not None:
                    self._player_data['years_pro'] = row['years_pro']

                # Calculate age from birthdate if not present
                if 'age' not in self._player_data and row['birthdate']:
                    birth_year = int(row['birthdate'].split('-')[0])
                    self._player_data['age'] = self._season - birth_year

                # Parse positions if not present
                if 'positions' not in self._player_data and row['positions']:
                    import json
                    self._player_data['positions'] = json.loads(row['positions'])

                # Parse overall from attributes if not present
                if 'overall' not in self._player_data and row['attributes']:
                    import json
                    attrs = json.loads(row['attributes'])
                    self._player_data['overall'] = attrs.get('overall', 0)

        except Exception as e:
            print(f"[PlayerDetailDialog] Error enriching player data: {e}")

    def _get_position_abbrev(self) -> str:
        """Get standardized position abbreviation."""
        # Try 'positions' list first
        positions = self._player_data.get('positions', [])
        if positions:
            pos_raw = positions[0].lower() if isinstance(positions[0], str) else str(positions[0]).lower()
            abbrev = POSITION_ABBREV.get(pos_raw, None)
            if abbrev:
                return abbrev
            # If not in mapping, try uppercase first 2-3 chars
            if pos_raw.upper()[:3] in POSITION_GROUPS:
                return pos_raw.upper()[:3]
            if pos_raw.upper()[:2] in POSITION_GROUPS:
                return pos_raw.upper()[:2]

        # Try 'position' (singular) field
        position = self._player_data.get('position', '')
        if position:
            pos_raw = position.lower() if isinstance(position, str) else str(position).lower()
            abbrev = POSITION_ABBREV.get(pos_raw, None)
            if abbrev:
                return abbrev
            # If not in mapping, try uppercase first 2-3 chars
            if pos_raw.upper()[:3] in POSITION_GROUPS:
                return pos_raw.upper()[:3]
            if pos_raw.upper()[:2] in POSITION_GROUPS:
                return pos_raw.upper()[:2]

        return "??"

    def _get_position_group(self) -> str:
        """Get position group for stats display."""
        pos_abbrev = self._get_position_abbrev()
        group = POSITION_GROUPS.get(pos_abbrev, None)
        if group:
            return group

        # Fallback: infer from game stats if available
        return self._infer_position_group_from_stats()

    def _infer_position_group_from_stats(self) -> str:
        """Infer position group from game stats when position is unknown."""
        if not self._game_log:
            # Try season stats as fallback
            if self._season_stats:
                if self._season_stats.get('passing_attempts', 0) > 0:
                    return 'passing'
                if self._season_stats.get('rushing_attempts', 0) > 0:
                    return 'rushing'
                if self._season_stats.get('targets', 0) > 0 or self._season_stats.get('receptions', 0) > 0:
                    return 'receiving'
                if self._season_stats.get('tackles_total', 0) > 0:
                    return 'defense'
                if self._season_stats.get('field_goals_attempted', 0) > 0:
                    return 'kicking'
                if self._season_stats.get('punts', 0) > 0:
                    return 'punting'
            return 'other'

        # Check first game's stats
        game = self._game_log[0]

        if game.get('passing_attempts', 0) > 0:
            return 'passing'
        if game.get('rushing_attempts', 0) > 0:
            return 'rushing'
        if game.get('targets', 0) > 0 or game.get('receptions', 0) > 0:
            return 'receiving'
        if game.get('tackles_total', 0) > 0:
            return 'defense'
        if game.get('field_goals_attempted', 0) > 0:
            return 'kicking'
        if game.get('punts', 0) > 0:
            return 'punting'

        return 'other'

    def _setup_ui(self):
        """Build the dialog layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header
        self._create_header(main_layout)

        # Stats cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._create_season_card(cards_row)
        self._create_info_card(cards_row)
        main_layout.addLayout(cards_row)

        # Game log table
        self._create_game_log_table(main_layout)

        # Footer cards row
        footer_row = QHBoxLayout()
        footer_row.setSpacing(12)
        self._create_season_highs_card(footer_row)
        self._create_recent_form_card(footer_row)
        main_layout.addLayout(footer_row)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create player header section."""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setStyleSheet("background-color: #3a3a3a; border-radius: 4px; padding: 8px;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # Player name (white text on dark background)
        name_label = QLabel(self._player_name)
        name_label.setFont(Typography.H3)
        name_label.setStyleSheet("color: white;")
        header_layout.addWidget(name_label)

        # Position | Team | Season
        pos_abbrev = self._get_position_abbrev()
        years_pro = self._player_data.get('years_pro', 0)
        exp_suffix = "yr" if years_pro == 1 else "yrs"

        subtitle = f"{pos_abbrev} | {self._team_name} | {self._season} Season"
        if years_pro:
            subtitle += f" | {years_pro} {exp_suffix} exp"

        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(Typography.BODY)
        subtitle_label.setStyleSheet("color: #aaaaaa;")  # Lighter muted for dark background
        header_layout.addWidget(subtitle_label)

        parent_layout.addWidget(header_frame)

    def _create_season_card(self, parent_layout: QHBoxLayout):
        """Create season stats card."""
        self._season_card = QGroupBox(f"{self._season} Season Stats")
        card_layout = QVBoxLayout(self._season_card)
        card_layout.setSpacing(8)

        # Top row: Games + Grade
        top_row = QHBoxLayout()
        self._games_label = self._create_stat_block("Games", "0")
        self._grade_label = self._create_stat_block("Grade", "--")
        top_row.addWidget(self._games_label[2])
        top_row.addWidget(self._grade_label[2])
        top_row.addStretch()
        card_layout.addLayout(top_row)

        # Position-specific stats (4 stats in a row)
        self._stat_labels: List[tuple] = []
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        # Placeholder labels - will be updated based on position
        for _ in range(4):
            label_tuple = self._create_stat_block("--", "--")
            self._stat_labels.append(label_tuple)
            stats_row.addWidget(label_tuple[2])

        stats_row.addStretch()
        card_layout.addLayout(stats_row)

        parent_layout.addWidget(self._season_card, stretch=1)

    def _create_info_card(self, parent_layout: QHBoxLayout):
        """Create player info card."""
        info_card = QGroupBox("Player Info")
        card_layout = QVBoxLayout(info_card)
        card_layout.setSpacing(6)

        # Overall Rating
        ovr = self._player_data.get('overall', 0) or self._player_data.get('attributes', {}).get('overall', 0)
        self._ovr_row = self._create_info_row("Overall Rating", str(ovr), get_grade_color(ovr))
        card_layout.addWidget(self._ovr_row)

        # Age
        age = self._player_data.get('age', '--')
        self._age_row = self._create_info_row("Age", str(age))
        card_layout.addWidget(self._age_row)

        # Experience (years pro)
        years_pro = self._player_data.get('years_pro', 0)
        exp_text = f"{years_pro} yrs" if years_pro else "Rookie"
        self._exp_row = self._create_info_row("Experience", exp_text)
        card_layout.addWidget(self._exp_row)

        # Position Rank (placeholder - would need league-wide data)
        self._rank_row = self._create_info_row("Position Rank", "--")
        card_layout.addWidget(self._rank_row)

        # HOF Status (for retired players only)
        self._add_hof_status_if_retired(card_layout)

        card_layout.addStretch()
        parent_layout.addWidget(info_card, stretch=1)

    def _create_stat_block(self, title: str, value: str) -> tuple:
        """Create a stat block with title and value. Returns (title_label, value_label, frame)."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        value_label = QLabel(value)
        value_label.setFont(Typography.H5)
        layout.addWidget(value_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        layout.addWidget(title_label)

        return (title_label, value_label, frame)

    def _create_info_row(self, label: str, value: str, value_color: str = None) -> QWidget:
        """Create an info row with label and value."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        label_widget = QLabel(label + ":")
        label_widget.setFont(Typography.BODY)
        label_widget.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(label_widget)

        layout.addStretch()

        value_widget = QLabel(value)
        value_widget.setFont(Typography.BODY_BOLD)
        if value_color:
            value_widget.setStyleSheet(f"color: {value_color};")
        value_widget.setObjectName("value")
        layout.addWidget(value_widget)

        return row

    def _create_game_log_table(self, parent_layout: QVBoxLayout):
        """Create the game log table."""
        log_group = QGroupBox(f"{self._season} Game Log")
        log_layout = QVBoxLayout(log_group)

        self._game_log_table = QTableWidget()
        self._game_log_table.setColumnCount(6)
        self._game_log_table.setHorizontalHeaderLabels([
            "WK", "OPPONENT", "RESULT", "STATS", "GRD", ""
        ])

        # Apply standardized table styling
        apply_table_style(self._game_log_table, row_height=26)

        # Configure column resize modes
        header = self._game_log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 1)  # Hidden spacer column

        # Additional customization
        self._game_log_table.setMaximumHeight(220)

        log_layout.addWidget(self._game_log_table)
        parent_layout.addWidget(log_group, stretch=1)

    def _create_season_highs_card(self, parent_layout: QHBoxLayout):
        """Create season highs card."""
        highs_card = QGroupBox("Season Highs")
        card_layout = QVBoxLayout(highs_card)
        card_layout.setSpacing(4)

        # Placeholder rows
        self._high_1_label = QLabel("--")
        self._high_1_label.setFont(Typography.BODY)
        card_layout.addWidget(self._high_1_label)

        self._high_2_label = QLabel("--")
        self._high_2_label.setFont(Typography.BODY)
        card_layout.addWidget(self._high_2_label)

        self._high_3_label = QLabel("--")
        self._high_3_label.setFont(Typography.BODY)
        card_layout.addWidget(self._high_3_label)

        card_layout.addStretch()
        parent_layout.addWidget(highs_card, stretch=1)

    def _create_recent_form_card(self, parent_layout: QHBoxLayout):
        """Create recent form card."""
        form_card = QGroupBox("Recent Form")
        card_layout = QVBoxLayout(form_card)
        card_layout.setSpacing(4)

        # Last N games grades
        self._recent_grades_label = QLabel("Last 3: --")
        self._recent_grades_label.setFont(Typography.BODY)
        card_layout.addWidget(self._recent_grades_label)

        # Average grade
        self._avg_grade_label = QLabel("Avg Grade: --")
        self._avg_grade_label.setFont(Typography.BODY)
        card_layout.addWidget(self._avg_grade_label)

        # Trend indicator
        self._trend_label = QLabel("Trend: --")
        self._trend_label.setFont(Typography.BODY)
        card_layout.addWidget(self._trend_label)

        card_layout.addStretch()
        parent_layout.addWidget(form_card, stretch=1)

    def _load_data(self):
        """Load player data from the database."""
        try:
            # Load season stats
            stats_api = PlayerSeasonStatsAPI(self._db_path)
            self._season_stats = stats_api.get_player_season_stats(
                self._dynasty_id, self._player_id, self._season
            )

            # Load game log
            self._load_game_log()

            # Load game grades
            self._load_game_grades()

            # Populate UI
            self._populate_season_card()
            self._populate_game_log_table()
            self._populate_season_highs()
            self._populate_recent_form()

        except Exception as e:
            self._show_error(str(e))

    def _load_game_log(self):
        """Load game-by-game stats from database."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT
                    pgs.*,
                    g.week,
                    g.home_team_id,
                    g.away_team_id,
                    g.home_score,
                    g.away_score
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ?
                  AND CAST(pgs.player_id AS INTEGER) = ?
                  AND g.season = ?
                  AND pgs.season_type = 'regular_season'
                ORDER BY g.week DESC
                """,
                (self._dynasty_id, self._player_id, self._season)
            )
            self._game_log = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _load_game_grades(self):
        """Load per-game grades from database."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT game_id, overall_grade
                FROM player_game_grades
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
                """,
                (self._dynasty_id, self._player_id, self._season)
            )
            for row in cursor.fetchall():
                self._game_grades[row['game_id']] = row['overall_grade']
        except sqlite3.OperationalError:
            # Table may not exist yet
            pass
        finally:
            conn.close()

    def _populate_season_card(self):
        """Populate the season stats card based on position."""
        if not self._season_stats:
            return

        # Games played
        games = self._season_stats.get('games_played', 0)
        self._games_label[1].setText(str(games))

        # Average grade
        grades = list(self._game_grades.values())
        if grades:
            avg_grade = sum(grades) / len(grades)
            self._grade_label[1].setText(f"{avg_grade:.1f}")
            self._grade_label[1].setStyleSheet(f"color: {get_grade_color(int(avg_grade))};")
        else:
            self._grade_label[1].setText("--")

        # Position-specific stats
        pos_group = self._get_position_group()
        stats_config = self._get_stats_config(pos_group)

        for i, (label, key, formatter) in enumerate(stats_config[:4]):
            if i < len(self._stat_labels):
                value = self._season_stats.get(key, 0)
                self._stat_labels[i][0].setText(label)
                self._stat_labels[i][1].setText(formatter(value))

    def _get_stats_config(self, pos_group: str) -> List[tuple]:
        """Get stats configuration for position group. Returns [(label, key, formatter), ...]"""
        def fmt_int(v): return f"{v:,}" if v else "0"
        def fmt_pct(v): return f"{v:.1f}%" if v else "0.0%"
        def fmt_float(v): return f"{v:.1f}" if v else "0.0"

        if pos_group == 'passing':
            return [
                ("YDS", "passing_yards", fmt_int),
                ("TD", "passing_tds", fmt_int),
                ("INT", "passing_interceptions", fmt_int),
                ("CMP%", "comp_pct", lambda v: fmt_pct(self._calc_comp_pct())),
            ]
        elif pos_group == 'rushing':
            return [
                ("YDS", "rushing_yards", fmt_int),
                ("TD", "rushing_tds", fmt_int),
                ("ATT", "rushing_attempts", fmt_int),
                ("YPC", "ypc", lambda v: fmt_float(self._calc_ypc())),
            ]
        elif pos_group == 'receiving':
            return [
                ("REC", "receptions", fmt_int),
                ("YDS", "receiving_yards", fmt_int),
                ("TD", "receiving_tds", fmt_int),
                ("TGT", "targets", fmt_int),
            ]
        elif pos_group == 'defense':
            return [
                ("TKL", "tackles_total", fmt_int),
                ("SACK", "sacks", fmt_float),
                ("INT", "interceptions", fmt_int),
                ("FF", "forced_fumbles", fmt_int),
            ]
        elif pos_group == 'kicking':
            return [
                ("FGM", "field_goals_made", fmt_int),
                ("FGA", "field_goals_attempted", fmt_int),
                ("XPM", "extra_points_made", fmt_int),
                ("XPA", "extra_points_attempted", fmt_int),
            ]
        elif pos_group == 'punting':
            return [
                ("PUNTS", "punts", fmt_int),
                ("YDS", "punt_yards", fmt_int),
                ("AVG", "punt_avg", lambda v: fmt_float(self._calc_punt_avg())),
                ("GP", "games_played", fmt_int),
            ]
        else:
            return [
                ("GP", "games_played", fmt_int),
                ("--", None, lambda v: "--"),
                ("--", None, lambda v: "--"),
                ("--", None, lambda v: "--"),
            ]

    def _calc_comp_pct(self) -> float:
        """Calculate completion percentage."""
        att = self._season_stats.get('passing_attempts', 0)
        comp = self._season_stats.get('passing_completions', 0)
        return (comp / att * 100) if att > 0 else 0.0

    def _calc_ypc(self) -> float:
        """Calculate yards per carry."""
        att = self._season_stats.get('rushing_attempts', 0)
        yds = self._season_stats.get('rushing_yards', 0)
        return (yds / att) if att > 0 else 0.0

    def _calc_punt_avg(self) -> float:
        """Calculate punt average."""
        punts = self._season_stats.get('punts', 0)
        yds = self._season_stats.get('punt_yards', 0)
        return (yds / punts) if punts > 0 else 0.0

    def _populate_game_log_table(self):
        """Populate the game log table."""
        if not self._game_log:
            self._game_log_table.setRowCount(1)
            self._game_log_table.setSpan(0, 0, 1, 5)
            no_data = QTableWidgetItem("No games played this season")
            no_data.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setForeground(QColor(Colors.MUTED))
            self._game_log_table.setItem(0, 0, no_data)
            return

        player_team_id = self._player_data.get('team_id')

        self._game_log_table.setRowCount(len(self._game_log))
        for row, game in enumerate(self._game_log):
            self._populate_game_log_row(row, game, player_team_id)

    def _populate_game_log_row(self, row: int, game: Dict, player_team_id: int):
        """Populate a single game log row."""
        # Week
        week = game.get('week', 0)
        week_item = QTableWidgetItem(str(week))
        week_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._game_log_table.setItem(row, 0, week_item)

        # Opponent (vs/@ prefix)
        home_team = game.get('home_team_id')
        away_team = game.get('away_team_id')
        home_score = game.get('home_score', 0)
        away_score = game.get('away_score', 0)

        # Determine opponent
        if player_team_id == home_team:
            opp_team_id = away_team
            prefix = "vs "
            player_score = home_score
            opp_score = away_score
        else:
            opp_team_id = home_team
            prefix = "@ "
            player_score = away_score
            opp_score = home_score

        # Get team abbreviation for opponent
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(opp_team_id)
            opp_name = team.abbreviation if team else f"Team {opp_team_id}"
        except Exception:
            opp_name = f"Team {opp_team_id}"
        opp_item = QTableWidgetItem(f"{prefix}{opp_name}")
        self._game_log_table.setItem(row, 1, opp_item)

        # Result (W/L score)
        if player_score > opp_score:
            result = f"W {player_score}-{opp_score}"
            result_color = Colors.SUCCESS
        elif player_score < opp_score:
            result = f"L {player_score}-{opp_score}"
            result_color = Colors.ERROR
        else:
            result = f"T {player_score}-{opp_score}"
            result_color = Colors.MUTED

        result_item = QTableWidgetItem(result)
        result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        result_item.setForeground(QColor(result_color))
        self._game_log_table.setItem(row, 2, result_item)

        # Stats (position-specific)
        stats_str = self._format_game_stats(game)
        stats_item = QTableWidgetItem(stats_str)
        stats_item.setForeground(QColor(Colors.MUTED))
        self._game_log_table.setItem(row, 3, stats_item)

        # Grade
        game_id = game.get('game_id')
        grade = self._game_grades.get(game_id)
        if grade is not None:
            grade_item = QTableWidgetItem(f"{grade:.1f}")
            grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            grade_item.setForeground(QColor(get_grade_color(int(grade))))
        else:
            grade_item = QTableWidgetItem("--")
            grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            grade_item.setForeground(QColor(Colors.MUTED))
        self._game_log_table.setItem(row, 4, grade_item)

    def _format_game_stats(self, game: Dict) -> str:
        """Format game stats based on position."""
        pos_group = self._get_position_group()

        if pos_group == 'passing':
            comp = game.get('passing_completions', 0)
            att = game.get('passing_attempts', 0)
            yds = game.get('passing_yards', 0)
            td = game.get('passing_tds', 0)
            ints = game.get('passing_interceptions', 0)
            return f"{comp}/{att}, {yds} YDS, {td} TD, {ints} INT"

        elif pos_group == 'rushing':
            att = game.get('rushing_attempts', 0)
            yds = game.get('rushing_yards', 0)
            td = game.get('rushing_tds', 0)
            return f"{att} ATT, {yds} YDS, {td} TD"

        elif pos_group == 'receiving':
            rec = game.get('receptions', 0)
            tgt = game.get('targets', 0)
            yds = game.get('receiving_yards', 0)
            td = game.get('receiving_tds', 0)
            return f"{rec}/{tgt} REC, {yds} YDS, {td} TD"

        elif pos_group == 'defense':
            tkl = game.get('tackles_total', 0)
            sacks = game.get('sacks', 0)
            ints = game.get('interceptions', 0)
            ff = game.get('forced_fumbles', 0)
            parts = [f"{tkl} TKL"]
            if sacks:
                parts.append(f"{sacks:.1f} SK" if isinstance(sacks, float) else f"{sacks} SK")
            if ints:
                parts.append(f"{ints} INT")
            if ff:
                parts.append(f"{ff} FF")
            return ", ".join(parts)

        elif pos_group == 'kicking':
            fgm = game.get('field_goals_made', 0)
            fga = game.get('field_goals_attempted', 0)
            xpm = game.get('extra_points_made', 0)
            xpa = game.get('extra_points_attempted', 0)
            return f"{fgm}/{fga} FG, {xpm}/{xpa} XP"

        elif pos_group == 'punting':
            punts = game.get('punts', 0)
            yds = game.get('punt_yards', 0)
            avg = yds / punts if punts > 0 else 0
            return f"{punts} P, {avg:.1f} AVG"

        return "--"

    def _populate_season_highs(self):
        """Populate season highs card."""
        if not self._game_log:
            return

        pos_group = self._get_position_group()
        highs = []

        if pos_group == 'passing':
            max_yds = max(self._game_log, key=lambda g: g.get('passing_yards', 0), default=None)
            max_tds = max(self._game_log, key=lambda g: g.get('passing_tds', 0), default=None)
            if max_yds:
                highs.append(f"Most Yards: {max_yds.get('passing_yards', 0)} (Wk {max_yds.get('week', '?')})")
            if max_tds:
                highs.append(f"Most TDs: {max_tds.get('passing_tds', 0)} (Wk {max_tds.get('week', '?')})")

        elif pos_group == 'rushing':
            max_yds = max(self._game_log, key=lambda g: g.get('rushing_yards', 0), default=None)
            max_tds = max(self._game_log, key=lambda g: g.get('rushing_tds', 0), default=None)
            if max_yds:
                highs.append(f"Most Yards: {max_yds.get('rushing_yards', 0)} (Wk {max_yds.get('week', '?')})")
            if max_tds:
                highs.append(f"Most TDs: {max_tds.get('rushing_tds', 0)} (Wk {max_tds.get('week', '?')})")

        elif pos_group == 'receiving':
            max_rec = max(self._game_log, key=lambda g: g.get('receptions', 0), default=None)
            max_yds = max(self._game_log, key=lambda g: g.get('receiving_yards', 0), default=None)
            if max_rec:
                highs.append(f"Most Rec: {max_rec.get('receptions', 0)} (Wk {max_rec.get('week', '?')})")
            if max_yds:
                highs.append(f"Most Yards: {max_yds.get('receiving_yards', 0)} (Wk {max_yds.get('week', '?')})")

        elif pos_group == 'defense':
            max_tkl = max(self._game_log, key=lambda g: g.get('tackles_total', 0), default=None)
            max_sack = max(self._game_log, key=lambda g: g.get('sacks', 0), default=None)
            if max_tkl:
                highs.append(f"Most Tackles: {max_tkl.get('tackles_total', 0)} (Wk {max_tkl.get('week', '?')})")
            if max_sack and max_sack.get('sacks', 0) > 0:
                highs.append(f"Most Sacks: {max_sack.get('sacks', 0)} (Wk {max_sack.get('week', '?')})")

        # Best grade
        if self._game_grades:
            best_game_id = max(self._game_grades, key=lambda k: self._game_grades[k])
            best_grade = self._game_grades[best_game_id]
            # Find week for this game
            for g in self._game_log:
                if g.get('game_id') == best_game_id:
                    highs.append(f"Best Grade: {best_grade:.1f} (Wk {g.get('week', '?')})")
                    break

        # Update labels
        labels = [self._high_1_label, self._high_2_label, self._high_3_label]
        for i, label in enumerate(labels):
            if i < len(highs):
                label.setText(highs[i])
            else:
                label.setText("--")

    def _populate_recent_form(self):
        """Populate recent form card."""
        if not self._game_log or not self._game_grades:
            return

        # Get last 3 games' grades
        recent_grades = []
        for game in self._game_log[:3]:
            game_id = game.get('game_id')
            if game_id in self._game_grades:
                recent_grades.append(self._game_grades[game_id])

        if recent_grades:
            grades_str = ", ".join(f"{g:.1f}" for g in recent_grades)
            self._recent_grades_label.setText(f"Last {len(recent_grades)}: {grades_str}")

            avg = sum(recent_grades) / len(recent_grades)
            self._avg_grade_label.setText(f"Avg Grade: {avg:.1f}")
            self._avg_grade_label.setStyleSheet(f"color: {get_grade_color(int(avg))};")

            # Trend
            if len(recent_grades) >= 2:
                if recent_grades[0] > recent_grades[-1]:
                    self._trend_label.setText("Trend: Improving")
                    self._trend_label.setStyleSheet(f"color: {Colors.SUCCESS};")
                elif recent_grades[0] < recent_grades[-1]:
                    self._trend_label.setText("Trend: Declining")
                    self._trend_label.setStyleSheet(f"color: {Colors.ERROR};")
                else:
                    self._trend_label.setText("Trend: Stable")
                    self._trend_label.setStyleSheet(f"color: {Colors.MUTED};")

    def _show_error(self, message: str):
        """Display error message in the game log table."""
        self._game_log_table.setRowCount(1)
        self._game_log_table.setSpan(0, 0, 1, 5)

        error_item = QTableWidgetItem(f"Error loading data: {message}")
        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        error_item.setForeground(QColor(Colors.ERROR))
        self._game_log_table.setItem(0, 0, error_item)

    def _add_hof_status_if_retired(self, card_layout: QVBoxLayout):
        """Add HOF status information if player is retired."""
        try:
            # Check if player is retired
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT hof_score, hof_inducted, induction_season
                FROM retired_players
                WHERE dynasty_id = ? AND player_id = ?
                """,
                (self._dynasty_id, self._player_id)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                # Player is not retired
                return

            # Add separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet(f"background-color: {Colors.MUTED};")
            card_layout.addWidget(separator)

            # HOF header
            hof_header = QLabel("Hall of Fame")
            hof_header.setFont(Typography.BODY_BOLD)
            hof_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; margin-top: 4px;")
            card_layout.addWidget(hof_header)

            # HOF Score
            hof_score = row['hof_score'] or 0
            tier = self._score_to_tier(hof_score)
            tier_color = self._get_tier_color(tier)

            score_row = self._create_info_row("HOF Score", f"{hof_score} ({tier})", tier_color)
            card_layout.addWidget(score_row)

            # Induction Status
            if row['hof_inducted']:
                induction_year = row['induction_season']
                status_text = f"Inducted {induction_year}"
                status_color = Colors.SUCCESS
            else:
                # Check eligibility based on retirement
                status_text = self._get_hof_status_text(hof_score)
                status_color = tier_color

            status_row = self._create_info_row("Status", status_text, status_color)
            card_layout.addWidget(status_row)

        except sqlite3.OperationalError:
            # Table may not exist
            pass
        except Exception as e:
            print(f"[PlayerDetailDialog] Error loading HOF status: {e}")

    def _score_to_tier(self, score: int) -> str:
        """Convert HOF score to tier string."""
        if score >= 85:
            return "First-Ballot"
        elif score >= 70:
            return "Strong"
        elif score >= 55:
            return "Borderline"
        elif score >= 40:
            return "Long Shot"
        else:
            return "Not HOF"

    def _get_tier_color(self, tier: str) -> str:
        """Get color for HOF tier."""
        tier_colors = {
            "First-Ballot": "#FFD700",  # Gold
            "Strong": "#4CAF50",         # Green
            "Borderline": "#FFC107",     # Amber
            "Long Shot": "#FF9800",      # Orange
            "Not HOF": "#9E9E9E",        # Gray
        }
        return tier_colors.get(tier, Colors.MUTED)

    def _get_hof_status_text(self, score: int) -> str:
        """Get status text based on HOF score for non-inducted players."""
        if score >= 85:
            return "HOF Lock"
        elif score >= 70:
            return "Strong Candidate"
        elif score >= 55:
            return "Borderline"
        elif score >= 40:
            return "Long Shot"
        else:
            return "Not Eligible"
