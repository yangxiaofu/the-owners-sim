"""
Box Score Dialog - Shows full game statistics for a played game.

Displays player stats organized by team with offense/defense columns.
Toggle between teams using side-by-side buttons. Accessed by double-clicking
a game in StageView.
"""

from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QWidget, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QScrollArea, QFileDialog, QMessageBox, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QAction

from database.unified_api import UnifiedDatabaseAPI
from game_cycle_ui.theme import (
    Colors,
    TAB_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
    Typography,
    FontSizes,
    TextColors,
    apply_table_style,
)


class BoxScoreDialog(QDialog):
    """
    Dialog showing full box score for a game.

    Layout:
    - Header with final score
    - Team toggle buttons (side-by-side)
    - Two-column layout: Offense (left) | Defense (right)
    """

    def __init__(
        self,
        game_id: str,
        home_team: Dict[str, Any],
        away_team: Dict[str, Any],
        home_score: int,
        away_score: int,
        db_path: str,
        dynasty_id: str,
        game_result: Optional[Any] = None,
        parent=None
    ):
        """
        Initialize box score dialog.

        Args:
            game_id: Game ID to display stats for
            home_team: Dict with 'id', 'name', 'abbr' for home team
            away_team: Dict with 'id', 'name', 'abbr' for away team
            home_score: Home team's final score
            away_score: Away team's final score
            db_path: Path to the database
            dynasty_id: Dynasty ID for database queries
            game_result: Optional GameResult object with play-by-play data
            parent: Parent widget
        """
        super().__init__(parent)
        self._game_id = game_id
        self._home_team = home_team
        self._away_team = away_team
        self._home_score = home_score
        self._away_score = away_score
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._game_result = game_result

        # Stats storage
        self._home_stats: List[Dict[str, Any]] = []
        self._away_stats: List[Dict[str, Any]] = []

        # Box score data from database (has TOP, 3rd/4th down, quarter scores)
        self._home_box_score: Dict[str, Any] = {}
        self._away_box_score: Dict[str, Any] = {}

        # Current team being displayed
        self._current_team: str = 'home'

        # Single set of tables (refreshed on team switch)
        self._tables: Dict[str, QTableWidget] = {}

        # Team stats comparison table
        self._team_stats_table: QTableWidget = None

        # Aggregated team stats
        self._home_team_stats: Dict[str, Any] = {}
        self._away_team_stats: Dict[str, Any] = {}

        # Toggle buttons
        self._home_btn: QPushButton = None
        self._away_btn: QPushButton = None

        # Header label (shows which team's stats)
        self._team_header: QLabel = None

        away_abbr = away_team.get('abbr', 'AWAY')
        home_abbr = home_team.get('abbr', 'HOME')
        self.setWindowTitle(f"Box Score: {away_abbr} {away_score} @ {home_abbr} {home_score}")
        self.setMinimumSize(1000, 800)
        self.setModal(True)

        self._setup_ui()
        self._load_stats()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header with final score
        self._create_header(layout)

        # Create tab widget to hold different views
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(TAB_STYLE)

        # Tab 1: Team Stats (side-by-side comparison)
        team_stats_tab = self._create_team_stats_tab()
        tab_widget.addTab(team_stats_tab, "Team Stats")

        # Tab 2: Player Stats (offense/defense tables)
        player_stats_tab = self._create_player_stats_tab()
        tab_widget.addTab(player_stats_tab, "Player Stats")

        # Tab 3: Play-by-Play
        # Priority: 1. In-memory game result, 2. Database, 3. Placeholder
        if self._game_result and hasattr(self._game_result, 'drives') and self._game_result.drives:
            plays_tab = self._create_plays_tab()
            tab_widget.addTab(plays_tab, "Play-by-Play")
        else:
            # Try loading from database
            db_plays_data = self._load_plays_from_db()
            if db_plays_data and db_plays_data.get('plays'):
                plays_tab = self._create_plays_tab_from_db(db_plays_data)
                tab_widget.addTab(plays_tab, "Play-by-Play")
            else:
                # Show placeholder tab explaining play-by-play is not available
                placeholder_tab = self._create_plays_placeholder_tab()
                tab_widget.addTab(placeholder_tab, "Play-by-Play")

        layout.addWidget(tab_widget, stretch=1)

        # Button row
        btn_layout = QHBoxLayout()

        # Export button with dropdown menu
        export_btn = QPushButton("Export")
        export_btn.setStyleSheet(
            SECONDARY_BUTTON_STYLE +
            "QPushButton { padding: 8px 24px; }"
            "QPushButton::menu-indicator { width: 0; height: 0; }"
        )
        export_menu = QMenu(self)
        export_menu.addAction("Export as Markdown (.md)", self._export_markdown)
        export_menu.addAction("Export as JSON (.json)", self._export_json)
        export_btn.setMenu(export_menu)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            NEUTRAL_BUTTON_STYLE +
            "QPushButton { padding: 8px 24px; }"
        )
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _create_team_stats_tab(self) -> QWidget:
        """Create the Team Stats tab with side-by-side comparison."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(10)
        tab_layout.setContentsMargins(8, 8, 8, 8)

        # Team stats comparison table (all 14 stats)
        self._create_team_stats_section(tab_layout)

        # Add stretch to center content vertically
        tab_layout.addStretch()

        return tab

    def _create_player_stats_tab(self) -> QWidget:
        """Create the Player Stats tab with offense/defense tables."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(10)
        tab_layout.setContentsMargins(8, 8, 8, 8)

        # Team toggle buttons
        self._create_team_toggle(tab_layout)

        # Two-column content: Offense | Defense
        content = self._create_two_column_layout()
        tab_layout.addWidget(content, stretch=1)

        return tab

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header showing final score."""
        away_name = self._away_team.get('name', 'Away')
        home_name = self._home_team.get('name', 'Home')

        header_text = f"{away_name} {self._away_score}  @  {home_name} {self._home_score}"
        header = QLabel(header_text)
        header.setFont(Typography.H4)
        header.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(header)

    def _create_team_stats_section(self, parent_layout: QVBoxLayout):
        """Create ESPN-style side-by-side team stats comparison table."""
        # Section header
        section_header = QLabel("TEAM STATS")
        section_header.setFont(Typography.BODY_SMALL_BOLD)
        section_header.setStyleSheet(f"color: {Colors.MUTED}; margin-top: 8px;")
        parent_layout.addWidget(section_header)

        # Get team abbreviations for column headers
        away_abbr = self._away_team.get('abbr', 'AWAY')
        home_abbr = self._home_team.get('abbr', 'HOME')

        # Create table
        self._team_stats_table = QTableWidget()
        self._team_stats_table.setColumnCount(3)
        self._team_stats_table.setHorizontalHeaderLabels(["", away_abbr, home_abbr])
        self._team_stats_table.setSelectionMode(QTableWidget.NoSelection)
        self._team_stats_table.setMaximumHeight(380)  # Increased for 14 stat rows

        # Apply standard table styling
        apply_table_style(self._team_stats_table)

        # Column resize modes
        header = self._team_stats_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self._team_stats_table.setColumnWidth(1, 80)
        self._team_stats_table.setColumnWidth(2, 80)

        parent_layout.addWidget(self._team_stats_table)

    def _aggregate_team_stats(self, player_stats: List[Dict]) -> Dict[str, Any]:
        """Aggregate player stats into team totals."""
        passing_completions = sum(s.get('passing_completions') or 0 for s in player_stats)
        passing_attempts = sum(s.get('passing_attempts') or 0 for s in player_stats)
        rushing_attempts = sum(s.get('rushing_attempts') or 0 for s in player_stats)
        total_plays = passing_attempts + rushing_attempts
        passing_yards = sum(s.get('passing_yards') or 0 for s in player_stats)
        rushing_yards = sum(s.get('rushing_yards') or 0 for s in player_stats)
        total_yards = passing_yards + rushing_yards

        return {
            'passing_yards': passing_yards,
            'rushing_yards': rushing_yards,
            'total_yards': total_yards,
            'turnovers': sum(
                (s.get('passing_interceptions') or 0) + (s.get('rushing_fumbles') or 0)
                for s in player_stats
            ),
            'sacks': sum(s.get('sacks') or 0 for s in player_stats),
            'interceptions': sum(s.get('interceptions') or 0 for s in player_stats),
            'passing_tds': sum(s.get('passing_tds') or 0 for s in player_stats),
            'rushing_tds': sum(s.get('rushing_tds') or 0 for s in player_stats),
            # Derivable stats
            'passing_completions': passing_completions,
            'passing_attempts': passing_attempts,
            'total_plays': total_plays,
            'completion_pct': (passing_completions / passing_attempts * 100) if passing_attempts > 0 else 0,
            'yards_per_play': (total_yards / total_plays) if total_plays > 0 else 0,
        }

    def _populate_team_stats(self):
        """Populate the team stats comparison table."""
        if not self._team_stats_table:
            return

        # Aggregate stats for both teams from player stats
        away_stats = self._aggregate_team_stats(self._away_stats)
        home_stats = self._aggregate_team_stats(self._home_stats)

        # Get box score data (has TOP, 3rd/4th down, first downs, etc.)
        away_box = self._away_box_score or {}
        home_box = self._home_box_score or {}

        # Format Time of Possession (MM:SS)
        away_top = away_box.get('time_of_possession_str', 'N/A')
        home_top = home_box.get('time_of_possession_str', 'N/A')

        # Format 3rd Down (conv/att format like "5/10")
        away_3rd_conv = away_box.get('third_down_conv', 0) or 0
        away_3rd_att = away_box.get('third_down_att', 0) or 0
        home_3rd_conv = home_box.get('third_down_conv', 0) or 0
        home_3rd_att = home_box.get('third_down_att', 0) or 0
        away_3rd = f"{away_3rd_conv}/{away_3rd_att}" if away_3rd_att else "0/0"
        home_3rd = f"{home_3rd_conv}/{home_3rd_att}" if home_3rd_att else "0/0"
        away_3rd_pct = (away_3rd_conv / away_3rd_att * 100) if away_3rd_att else 0
        home_3rd_pct = (home_3rd_conv / home_3rd_att * 100) if home_3rd_att else 0

        # Format 4th Down (conv/att format)
        away_4th_conv = away_box.get('fourth_down_conv', 0) or 0
        away_4th_att = away_box.get('fourth_down_att', 0) or 0
        home_4th_conv = home_box.get('fourth_down_conv', 0) or 0
        home_4th_att = home_box.get('fourth_down_att', 0) or 0
        away_4th = f"{away_4th_conv}/{away_4th_att}" if away_4th_att else "0/0"
        home_4th = f"{home_4th_conv}/{home_4th_att}" if home_4th_att else "0/0"
        away_4th_pct = (away_4th_conv / away_4th_att * 100) if away_4th_att else 0
        home_4th_pct = (home_4th_conv / home_4th_att * 100) if home_4th_att else 0

        # First Downs
        away_first_downs = away_box.get('first_downs', 0) or 0
        home_first_downs = home_box.get('first_downs', 0) or 0

        # Penalties
        away_pen = away_box.get('penalties', 0) or 0
        away_pen_yds = away_box.get('penalty_yards', 0) or 0
        home_pen = home_box.get('penalties', 0) or 0
        home_pen_yds = home_box.get('penalty_yards', 0) or 0
        away_pen_str = f"{away_pen}-{away_pen_yds}"
        home_pen_str = f"{home_pen}-{home_pen_yds}"

        # Derivable stats
        away_comp_pct = away_stats['completion_pct']
        home_comp_pct = home_stats['completion_pct']
        away_ypp = away_stats['yards_per_play']
        home_ypp = home_stats['yards_per_play']

        # Turnover margin: my turnovers forced (opponent turnovers) minus my turnovers lost
        # For away team: home_turnovers - away_turnovers
        # For home team: away_turnovers - home_turnovers
        away_to_margin = home_stats['turnovers'] - away_stats['turnovers']
        home_to_margin = away_stats['turnovers'] - home_stats['turnovers']

        # Define rows: (label, away_value, home_value, higher_is_better, is_string)
        # is_string=True means don't compare numerically (e.g. TOP, 3rd down)
        rows = [
            ("First Downs", away_first_downs, home_first_downs, True, False),
            ("Total Yards", away_stats['total_yards'], home_stats['total_yards'], True, False),
            ("Passing Yards", away_stats['passing_yards'], home_stats['passing_yards'], True, False),
            ("Rushing Yards", away_stats['rushing_yards'], home_stats['rushing_yards'], True, False),
            ("Comp %", f"{away_comp_pct:.1f}%", f"{home_comp_pct:.1f}%", True, True, away_comp_pct, home_comp_pct),
            ("Yards/Play", f"{away_ypp:.1f}", f"{home_ypp:.1f}", True, True, away_ypp, home_ypp),
            ("Passing TDs", away_stats['passing_tds'], home_stats['passing_tds'], True, False),
            ("Rushing TDs", away_stats['rushing_tds'], home_stats['rushing_tds'], True, False),
            ("Turnovers", away_stats['turnovers'], home_stats['turnovers'], False, False),
            ("TO Margin", f"{away_to_margin:+d}", f"{home_to_margin:+d}", True, True, away_to_margin, home_to_margin),
            ("3rd Down Eff", away_3rd, home_3rd, True, True, away_3rd_pct, home_3rd_pct),
            ("4th Down Eff", away_4th, home_4th, True, True, away_4th_pct, home_4th_pct),
            ("Time of Possession", away_top, home_top, True, True),
            ("Penalties", away_pen_str, home_pen_str, False, True, away_pen, home_pen),
        ]

        self._team_stats_table.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            label = row_data[0]
            away_val = row_data[1]
            home_val = row_data[2]
            higher_better = row_data[3]
            is_string = row_data[4] if len(row_data) > 4 else False
            # For string comparisons, use numeric values if provided
            compare_away = row_data[5] if len(row_data) > 5 else None
            compare_home = row_data[6] if len(row_data) > 6 else None

            # Stat label
            label_item = QTableWidgetItem(label)
            label_item.setFont(Typography.SMALL)
            self._team_stats_table.setItem(row_idx, 0, label_item)

            # Away value
            away_item = QTableWidgetItem(str(away_val))
            away_item.setTextAlignment(Qt.AlignCenter)
            away_item.setFont(Typography.SMALL_BOLD)

            # Home value
            home_item = QTableWidgetItem(str(home_val))
            home_item.setTextAlignment(Qt.AlignCenter)
            home_item.setFont(Typography.SMALL_BOLD)

            # Highlight winner (green for better stat)
            if not is_string:
                if higher_better:
                    if away_val > home_val:
                        away_item.setForeground(Qt.green)
                    elif home_val > away_val:
                        home_item.setForeground(Qt.green)
                else:  # Lower is better (turnovers, penalties)
                    if away_val < home_val:
                        away_item.setForeground(Qt.green)
                    elif home_val < away_val:
                        home_item.setForeground(Qt.green)
            elif compare_away is not None and compare_home is not None:
                # Use numeric comparison values for string displays
                if higher_better:
                    if compare_away > compare_home:
                        away_item.setForeground(Qt.green)
                    elif compare_home > compare_away:
                        home_item.setForeground(Qt.green)
                else:
                    if compare_away < compare_home:
                        away_item.setForeground(Qt.green)
                    elif compare_home < compare_away:
                        home_item.setForeground(Qt.green)

            self._team_stats_table.setItem(row_idx, 1, away_item)
            self._team_stats_table.setItem(row_idx, 2, home_item)

        # Ensure rows are properly sized
        self._team_stats_table.resizeRowsToContents()

    def _create_team_toggle(self, parent_layout: QVBoxLayout):
        """Create side-by-side team toggle buttons."""
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(8)

        # Away team button (listed first for @ convention)
        away_name = self._away_team.get('name', 'Away')
        self._away_btn = QPushButton(f"{away_name}")
        self._away_btn.setFont(Typography.BODY_SMALL)
        self._away_btn.setCursor(Qt.PointingHandCursor)
        self._away_btn.clicked.connect(lambda: self._show_team('away'))

        # Home team button
        home_name = self._home_team.get('name', 'Home')
        self._home_btn = QPushButton(f"{home_name}")
        self._home_btn.setFont(Typography.BODY_SMALL)
        self._home_btn.setCursor(Qt.PointingHandCursor)
        self._home_btn.clicked.connect(lambda: self._show_team('home'))

        toggle_layout.addStretch()
        toggle_layout.addWidget(self._away_btn)
        toggle_layout.addWidget(self._home_btn)
        toggle_layout.addStretch()

        parent_layout.addLayout(toggle_layout)

        # Update initial button styles
        self._update_button_styles()

    def _create_two_column_layout(self) -> QWidget:
        """Create two-column layout: Offense (left) | Defense (right)."""
        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(0, 8, 0, 0)

        # LEFT COLUMN: Offense (Passing, Rushing, Receiving)
        offense_widget = QWidget()
        offense_layout = QVBoxLayout(offense_widget)
        offense_layout.setSpacing(8)
        offense_layout.setContentsMargins(0, 0, 0, 0)

        # Offense header
        offense_header = QLabel("OFFENSE")
        offense_header.setFont(Typography.H6)
        offense_header.setStyleSheet("color: #2196F3; padding: 4px 0;")
        offense_layout.addWidget(offense_header)

        # Passing table
        self._tables['passing'] = self._create_stat_table(
            offense_layout, "PASSING",
            ["Player", "CMP/ATT", "YDS", "TD", "INT", "RTG"],
            max_height=150
        )

        # Rushing table (added FUM column)
        self._tables['rushing'] = self._create_stat_table(
            offense_layout, "RUSHING",
            ["Player", "ATT", "YDS", "AVG", "TD", "LNG", "FUM"],
            max_height=150
        )

        # Receiving table (added LNG and DRP columns)
        self._tables['receiving'] = self._create_stat_table(
            offense_layout, "RECEIVING",
            ["Player", "REC", "TGT", "YDS", "AVG", "TD", "LNG", "DRP"],
            max_height=200
        )

        # RIGHT COLUMN: Defense
        defense_widget = QWidget()
        defense_layout = QVBoxLayout(defense_widget)
        defense_layout.setSpacing(8)
        defense_layout.setContentsMargins(0, 0, 0, 0)

        # Defense header
        defense_header = QLabel("DEFENSE")
        defense_header.setFont(Typography.H6)
        defense_header.setStyleSheet("color: #F44336; padding: 4px 0;")
        defense_layout.addWidget(defense_header)

        # Defense table (expanded with solo/assist and fumbles recovered)
        self._tables['defense'] = self._create_stat_table(
            defense_layout, "DEFENSE",
            ["Player", "SOLO", "AST", "TKL", "SACK", "INT", "PD", "FF", "FR"],
            max_height=280
        )

        # Special Teams header
        st_header = QLabel("SPECIAL TEAMS")
        st_header.setFont(Typography.H6)
        st_header.setStyleSheet("color: #FF9800; padding: 4px 0; margin-top: 8px;")
        defense_layout.addWidget(st_header)

        # Kicking table (FG, XP)
        self._tables['kicking'] = self._create_stat_table(
            defense_layout, "KICKING",
            ["Player", "FGM", "FGA", "FG%", "XPM", "XPA", "XP%"],
            max_height=80
        )

        # Punting table
        self._tables['punting'] = self._create_stat_table(
            defense_layout, "PUNTING",
            ["Player", "PUNTS", "YDS", "AVG", "LNG", "IN20"],
            max_height=80
        )

        # Add columns with equal stretch
        main_layout.addWidget(offense_widget, stretch=1)

        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #444;")
        main_layout.addWidget(separator)

        main_layout.addWidget(defense_widget, stretch=1)

        return container

    def _create_stat_table(
        self,
        parent_layout: QVBoxLayout,
        category: str,
        columns: List[str],
        max_height: int = 120
    ) -> QTableWidget:
        """Create a stat table with header."""
        # Category label
        label = QLabel(category)
        label.setFont(Typography.SMALL_BOLD)
        label.setStyleSheet(f"color: {Colors.MUTED}; margin-top: 4px;")
        parent_layout.addWidget(label)

        # Table
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setMaximumHeight(max_height)

        # Apply standard table styling
        apply_table_style(table)

        # Column resize modes
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        parent_layout.addWidget(table)
        return table

    def _load_stats(self):
        """Load game stats from database and store by team."""
        try:
            print(f"[BoxScoreDialog] Loading stats for game_id='{self._game_id}'")
            api = UnifiedDatabaseAPI(self._db_path, dynasty_id=self._dynasty_id)
            all_stats = api.stats_get_game_stats(self._game_id)
            print(f"[BoxScoreDialog] Query returned {len(all_stats) if all_stats else 0} player stats")

            if not all_stats:
                # DEBUG: Check if stats exist under different game_id pattern
                from game_cycle.database.connection import GameCycleDatabase
                with GameCycleDatabase(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT DISTINCT game_id FROM player_game_stats WHERE dynasty_id = ? ORDER BY game_id LIMIT 15",
                        (self._dynasty_id,)
                    )
                    available_ids = [r[0] for r in cursor.fetchall()]
                    print(f"[BoxScoreDialog] WARNING: No stats found! Available game_ids in DB: {available_ids}")
                return

            # Split by team
            home_id = self._home_team.get('id')
            away_id = self._away_team.get('id')

            self._home_stats = [s for s in all_stats if s.get('team_id') == home_id]
            self._away_stats = [s for s in all_stats if s.get('team_id') == away_id]

            # Load box scores (has TOP, 3rd/4th down, quarter scores, etc.)
            box_scores = api.box_scores_get(self._game_id)
            for bs in box_scores:
                if bs.get('team_id') == home_id:
                    self._home_box_score = bs
                elif bs.get('team_id') == away_id:
                    self._away_box_score = bs

            # Populate team stats comparison table
            self._populate_team_stats()

            # Show home team player stats by default
            self._show_team('home')

        except Exception as e:
            print(f"[BoxScoreDialog] Error loading stats: {e}")

    def _show_team(self, team: str):
        """Switch displayed team and refresh tables."""
        self._current_team = team
        self._update_button_styles()

        # Get stats for selected team
        stats = self._home_stats if team == 'home' else self._away_stats
        self._populate_team_tables(stats)

    def _update_button_styles(self):
        """Update toggle button styles based on current team."""
        if self._current_team == 'home':
            self._home_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
            self._away_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        else:
            self._away_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
            self._home_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)

    def _populate_team_tables(self, stats: List[Dict[str, Any]]):
        """Populate all stat tables for a team."""
        # Passing
        passers = self._get_passers(stats)
        self._populate_passing_table(self._tables['passing'], passers)

        # Rushing
        rushers = self._get_rushers(stats)
        self._populate_rushing_table(self._tables['rushing'], rushers)

        # Receiving
        receivers = self._get_receivers(stats)
        self._populate_receiving_table(self._tables['receiving'], receivers)

        # Defense
        defenders = self._get_defenders(stats)
        self._populate_defense_table(self._tables['defense'], defenders)

        # Special Teams - Kicking (FG, XP)
        kickers = self._get_kickers(stats)
        self._populate_kicking_table(self._tables['kicking'], kickers)

        # Special Teams - Punting
        punters = self._get_punters(stats)
        self._populate_punting_table(self._tables['punting'], punters)

    def _get_passers(self, stats: List[Dict]) -> List[Dict]:
        """Get players with passing attempts, sorted by yards."""
        return sorted(
            [s for s in stats if (s.get('passing_attempts') or 0) > 0],
            key=lambda x: x.get('passing_yards') or 0,
            reverse=True
        )

    def _get_rushers(self, stats: List[Dict]) -> List[Dict]:
        """Get players with rushing attempts, sorted by yards."""
        return sorted(
            [s for s in stats if (s.get('rushing_attempts') or 0) > 0],
            key=lambda x: x.get('rushing_yards') or 0,
            reverse=True
        )

    def _get_receivers(self, stats: List[Dict]) -> List[Dict]:
        """Get players with receptions or targets, sorted by yards."""
        return sorted(
            [s for s in stats if (s.get('receptions') or 0) > 0 or (s.get('targets') or 0) > 0],
            key=lambda x: x.get('receiving_yards') or 0,
            reverse=True
        )

    def _get_defenders(self, stats: List[Dict]) -> List[Dict]:
        """Get players with defensive stats, sorted by tackles."""
        return sorted(
            [s for s in stats if (s.get('tackles_total') or 0) > 0 or (s.get('sacks') or 0) > 0],
            key=lambda x: x.get('tackles_total') or 0,
            reverse=True
        )[:10]  # Limit defenders to make room for special teams

    def _get_kickers(self, stats: List[Dict]) -> List[Dict]:
        """Get players with kicking stats (FG or XP attempts)."""
        return [s for s in stats if
                (s.get('field_goals_attempted') or 0) > 0 or
                (s.get('extra_points_attempted') or 0) > 0]

    def _get_punters(self, stats: List[Dict]) -> List[Dict]:
        """Get players with punting stats."""
        return [s for s in stats if (s.get('punts') or 0) > 0]

    def _populate_passing_table(self, table: QTableWidget, players: List[Dict]):
        """Populate passing stats table."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            comp = p.get('passing_completions') or 0
            att = p.get('passing_attempts') or 0
            yds = p.get('passing_yards') or 0
            td = p.get('passing_tds') or 0
            ints = p.get('passing_interceptions') or 0
            rtg = p.get('passing_rating') or 0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(f"{comp}/{att}"))
            table.setItem(row, 2, self._centered_item(str(yds)))
            table.setItem(row, 3, self._centered_item(str(td)))
            table.setItem(row, 4, self._centered_item(str(ints)))
            table.setItem(row, 5, self._centered_item(f"{rtg:.1f}"))

    def _populate_rushing_table(self, table: QTableWidget, players: List[Dict]):
        """Populate rushing stats table."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            att = p.get('rushing_attempts') or 0
            yds = p.get('rushing_yards') or 0
            avg = yds / att if att > 0 else 0.0
            td = p.get('rushing_tds') or 0
            lng = p.get('rushing_long') or 0
            fum = p.get('rushing_fumbles') or 0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(str(att)))
            table.setItem(row, 2, self._centered_item(str(yds)))
            table.setItem(row, 3, self._centered_item(f"{avg:.1f}"))
            table.setItem(row, 4, self._centered_item(str(td)))
            table.setItem(row, 5, self._centered_item(str(lng)))
            table.setItem(row, 6, self._centered_item(str(fum)))

    def _populate_receiving_table(self, table: QTableWidget, players: List[Dict]):
        """Populate receiving stats table."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            rec = p.get('receptions') or 0
            tgt = p.get('targets') or 0
            yds = p.get('receiving_yards') or 0
            avg = yds / rec if rec > 0 else 0.0
            td = p.get('receiving_tds') or 0
            lng = p.get('receiving_long') or 0
            drp = p.get('receiving_drops') or 0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(str(rec)))
            table.setItem(row, 2, self._centered_item(str(tgt)))
            table.setItem(row, 3, self._centered_item(str(yds)))
            table.setItem(row, 4, self._centered_item(f"{avg:.1f}"))
            table.setItem(row, 5, self._centered_item(str(td)))
            table.setItem(row, 6, self._centered_item(str(lng)))
            table.setItem(row, 7, self._centered_item(str(drp)))

    def _populate_defense_table(self, table: QTableWidget, players: List[Dict]):
        """Populate defense stats table."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            solo = p.get('tackles_solo') or 0
            ast = p.get('tackles_assist') or 0
            tkl = p.get('tackles_total') or 0
            sacks = p.get('sacks') or 0
            ints = p.get('interceptions') or 0
            pd = p.get('passes_defended') or 0
            ff = p.get('forced_fumbles') or 0
            fr = p.get('fumbles_recovered') or 0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(str(solo)))
            table.setItem(row, 2, self._centered_item(str(ast)))
            table.setItem(row, 3, self._centered_item(str(tkl)))
            table.setItem(row, 4, self._centered_item(f"{sacks:.1f}" if sacks else "0"))
            table.setItem(row, 5, self._centered_item(str(ints)))
            table.setItem(row, 6, self._centered_item(str(pd)))
            table.setItem(row, 7, self._centered_item(str(ff)))
            table.setItem(row, 8, self._centered_item(str(fr)))

    def _populate_kicking_table(self, table: QTableWidget, players: List[Dict]):
        """Populate kicking stats table (FG and XP)."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            fgm = p.get('field_goals_made') or 0
            fga = p.get('field_goals_attempted') or 0
            fg_pct = (fgm / fga * 100) if fga > 0 else 0.0
            xpm = p.get('extra_points_made') or 0
            xpa = p.get('extra_points_attempted') or 0
            xp_pct = (xpm / xpa * 100) if xpa > 0 else 0.0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(str(fgm)))
            table.setItem(row, 2, self._centered_item(str(fga)))
            table.setItem(row, 3, self._centered_item(f"{fg_pct:.0f}%"))
            table.setItem(row, 4, self._centered_item(str(xpm)))
            table.setItem(row, 5, self._centered_item(str(xpa)))
            table.setItem(row, 6, self._centered_item(f"{xp_pct:.0f}%"))

    def _populate_punting_table(self, table: QTableWidget, players: List[Dict]):
        """Populate punting stats table."""
        table.setRowCount(len(players))
        for row, p in enumerate(players):
            name = p.get('player_name', 'Unknown')
            punts = p.get('punts') or 0
            yds = p.get('punt_yards') or 0
            avg = yds / punts if punts > 0 else 0.0
            lng = p.get('punt_long') or 0
            in20 = p.get('punts_inside_20') or 0

            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, self._centered_item(str(punts)))
            table.setItem(row, 2, self._centered_item(str(yds)))
            table.setItem(row, 3, self._centered_item(f"{avg:.1f}"))
            table.setItem(row, 4, self._centered_item(str(lng)))
            table.setItem(row, 5, self._centered_item(str(in20)))

    def _centered_item(self, text: str) -> QTableWidgetItem:
        """Create a centered table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _create_plays_placeholder_tab(self) -> QWidget:
        """Create a placeholder tab when play-by-play data is not available."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(16)
        tab_layout.setContentsMargins(24, 24, 24, 24)

        tab_layout.addStretch()

        # Icon/emoji placeholder
        icon_label = QLabel("📋")
        icon_label.setFont(Typography.ICON_LARGE)
        icon_label.setAlignment(Qt.AlignCenter)
        tab_layout.addWidget(icon_label)

        # Main message
        message = QLabel("Play-by-Play Not Available")
        message.setFont(Typography.H4)
        message.setStyleSheet(f"color: {TextColors.ON_DARK};")
        message.setAlignment(Qt.AlignCenter)
        tab_layout.addWidget(message)

        # Explanation
        explanation = QLabel(
            "Play-by-play data is only available immediately after simulating a game.\n"
            "Historical games show player stats but not detailed play breakdowns."
        )
        explanation.setFont(Typography.BODY_SMALL)
        explanation.setStyleSheet(f"color: {Colors.MUTED};")
        explanation.setAlignment(Qt.AlignCenter)
        explanation.setWordWrap(True)
        tab_layout.addWidget(explanation)

        tab_layout.addStretch()

        return tab

    def _load_plays_from_db(self) -> Optional[Dict[str, Any]]:
        """
        Load play-by-play data from the database.

        Returns:
            Dict with 'drives' and 'plays' keys, or None if not available.
        """
        try:
            from game_cycle.database.play_by_play_api import PlayByPlayAPI
            api = PlayByPlayAPI(self._db_path)

            if not api.has_play_by_play(self._dynasty_id, self._game_id):
                return None

            return {
                'drives': api.get_game_drives(self._dynasty_id, self._game_id),
                'plays': api.get_game_plays(self._dynasty_id, self._game_id)
            }
        except Exception as e:
            print(f"[BoxScoreDialog] Failed to load plays from DB: {e}")
            return None

    def _create_plays_tab_from_db(self, plays_data: Dict[str, Any]) -> QWidget:
        """
        Create the play-by-play tab from database data.

        Args:
            plays_data: Dict with 'drives' and 'plays' from database.

        Returns:
            QWidget containing the play-by-play tree.
        """
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(8)
        tab_layout.setContentsMargins(8, 8, 8, 8)

        # Header with info
        header_layout = QHBoxLayout()

        info_label = QLabel("Play-by-play breakdown (loaded from history)")
        info_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        header_layout.addWidget(info_label)

        header_layout.addStretch()
        tab_layout.addLayout(header_layout)

        # Create tree widget
        tree = QTreeWidget()
        tree.setHeaderLabels(["Play Description", "Result", "Yards"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setIndentation(20)
        tree.setWordWrap(True)

        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tree.setColumnWidth(0, 600)

        # Populate from database data
        self._populate_plays_tree_from_db(tree, plays_data)

        tab_layout.addWidget(tree)
        return tab

    def _populate_plays_tree_from_db(self, tree: QTreeWidget, plays_data: Dict[str, Any]):
        """
        Populate the tree widget with plays from database.

        Args:
            tree: QTreeWidget to populate.
            plays_data: Dict with 'drives' and 'plays' from database.
        """
        plays = plays_data.get('plays', [])
        drives = plays_data.get('drives', [])

        if not plays:
            no_data_item = QTreeWidgetItem(["No play-by-play data available", "", ""])
            tree.addTopLevelItem(no_data_item)
            return

        # Get team info
        home_id = self._home_team.get('id')
        home_abbr = self._home_team.get('abbr', 'HOME')
        away_abbr = self._away_team.get('abbr', 'AWAY')

        # Create drive lookup
        drive_map = {d['drive_number']: d for d in drives}

        # Group plays by quarter
        current_quarter = None
        quarter_item = None
        current_drive = None
        drive_item = None

        for play in plays:
            quarter = play.get('quarter', 1)
            drive_number = play.get('drive_number', 0)
            possession_team_id = play.get('possession_team_id')

            # Create quarter header if needed
            if quarter != current_quarter:
                current_quarter = quarter
                quarter_text = f"QUARTER {quarter}" if quarter <= 4 else f"OVERTIME {quarter - 4}"
                quarter_item = QTreeWidgetItem([quarter_text, "", ""])
                quarter_item.setFont(0, Typography.BODY_SMALL_BOLD)
                quarter_item.setForeground(0, Qt.darkBlue)
                tree.addTopLevelItem(quarter_item)
                quarter_item.setExpanded(True)
                current_drive = None  # Reset drive tracking for new quarter

            # Create drive header if needed
            if drive_number != current_drive:
                current_drive = drive_number
                team_abbr = home_abbr if possession_team_id == home_id else away_abbr

                # Get drive info from drive_map
                drive_info = drive_map.get(drive_number, {})
                drive_outcome = drive_info.get('drive_outcome', 'unknown')
                total_yards = drive_info.get('total_yards', 0)
                total_plays = drive_info.get('total_plays', 0)

                # Format drive outcome for display
                outcome_display = drive_outcome.upper().replace('_', ' ')
                drive_summary = f"{team_abbr} Drive #{drive_number} - {outcome_display} ({total_plays} plays, {total_yards} yds)"

                drive_item = QTreeWidgetItem([drive_summary, "", ""])
                drive_item.setFont(0, Typography.SMALL_BOLD)
                if quarter_item:
                    quarter_item.addChild(drive_item)
                else:
                    tree.addTopLevelItem(drive_item)
                drive_item.setExpanded(False)  # Collapsed by default

            # Add play to current drive
            if drive_item:
                play_desc = play.get('play_description', 'Unknown play')
                outcome = play.get('outcome', '')
                yards = play.get('yards_gained', 0)

                # Format down and distance
                down = play.get('down', 1)
                distance = play.get('distance', 10)
                yard_line = play.get('yard_line', 50)
                down_dist = f"{self._ordinal(down)}&{distance}"

                # Build full description
                full_desc = f"{down_dist} at {yard_line} - {play_desc}"

                play_item = QTreeWidgetItem([full_desc, outcome, str(yards)])
                drive_item.addChild(play_item)

                # Color scoring plays
                if play.get('is_scoring_play'):
                    play_item.setForeground(0, Qt.darkGreen)
                elif play.get('is_turnover'):
                    play_item.setForeground(0, Qt.darkRed)

    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal (1 -> '1st', 2 -> '2nd', etc.)"""
        if n == 1:
            return "1st"
        elif n == 2:
            return "2nd"
        elif n == 3:
            return "3rd"
        elif n == 4:
            return "4th"
        else:
            return f"{n}th"

    def _create_plays_tab(self) -> QWidget:
        """Create the play-by-play tab showing drives and plays."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(8)
        tab_layout.setContentsMargins(8, 8, 8, 8)

        # Header with info and export buttons
        header_layout = QHBoxLayout()

        # Info label
        info_label = QLabel("Play-by-play breakdown of all drives and plays")
        info_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        header_layout.addWidget(info_label)

        header_layout.addStretch()

        # Export buttons
        export_md_btn = QPushButton("Export as Markdown")
        export_md_btn.setStyleSheet(
            SECONDARY_BUTTON_STYLE +
            "QPushButton { padding: 6px 12px; }"
        )
        export_md_btn.clicked.connect(self._export_as_markdown)
        header_layout.addWidget(export_md_btn)

        export_json_btn = QPushButton("Export as JSON")
        export_json_btn.setStyleSheet(
            PRIMARY_BUTTON_STYLE +
            "QPushButton { padding: 6px 12px; }"
        )
        export_json_btn.clicked.connect(self._export_as_json)
        header_layout.addWidget(export_json_btn)

        tab_layout.addLayout(header_layout)

        # Create tree widget for hierarchical display (drives → plays)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Play Description", "Result", "Yards"])
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setIndentation(20)
        tree.setWordWrap(True)  # Enable word wrapping for long descriptions

        # Set column widths - make description column much wider
        header = tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Allow manual resizing
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Set minimum width for description column (wider to show full plays)
        tree.setColumnWidth(0, 600)  # Wide enough for full play descriptions

        # Populate tree with drives and plays
        self._populate_plays_tree(tree)

        tab_layout.addWidget(tree)

        return tab

    def _populate_plays_tree(self, tree: QTreeWidget):
        """Populate the tree widget with drives and plays from GameResult."""
        if not self._game_result or not hasattr(self._game_result, 'drives'):
            # No play data available
            no_data_item = QTreeWidgetItem(["No play-by-play data available", "", ""])
            tree.addTopLevelItem(no_data_item)
            return

        drives = self._game_result.drives
        if not drives:
            no_data_item = QTreeWidgetItem(["No drives recorded", "", ""])
            tree.addTopLevelItem(no_data_item)
            return

        # Get team names for display
        home_id = self._home_team.get('id')
        away_id = self._away_team.get('id')
        home_abbr = self._home_team.get('abbr', 'HOME')
        away_abbr = self._away_team.get('abbr', 'AWAY')

        # Track quarter for grouping
        current_quarter = None
        quarter_item = None

        # Track running score throughout the game
        home_score = 0
        away_score = 0

        # Track cumulative game time
        total_game_time = 0  # in seconds

        for drive_num, drive in enumerate(drives, 1):
            # ✅ FIX: Add quarter grouping to tree view
            drive_quarter = getattr(drive, 'quarter_started', 1)
            if drive_quarter != current_quarter:
                current_quarter = drive_quarter
                quarter_text = f"QUARTER {current_quarter}" if current_quarter <= 4 else f"OVERTIME {current_quarter - 4}"
                quarter_item = QTreeWidgetItem([quarter_text, "", ""])
                quarter_item.setFont(0, Typography.BODY_SMALL_BOLD)
                quarter_item.setForeground(0, Qt.darkBlue)
                tree.addTopLevelItem(quarter_item)
                quarter_item.setExpanded(True)

            # Get drive info
            possessing_team_id = getattr(drive, 'possessing_team_id', None)
            team_abbr = home_abbr if possessing_team_id == home_id else away_abbr

            drive_outcome = getattr(drive, 'drive_outcome', 'unknown')
            points_scored = getattr(drive, 'points_scored', 0)
            plays = getattr(drive, 'plays', [])

            # Calculate drive yards and time of possession
            drive_yards = sum(getattr(play, 'yards', 0) for play in plays)
            drive_time_seconds = sum(getattr(play, 'time_elapsed', 0) for play in plays)

            # Format time as MM:SS
            time_minutes = int(drive_time_seconds // 60)
            time_seconds = int(drive_time_seconds % 60)
            time_str = f"{time_minutes}:{time_seconds:02d}"

            # Create drive summary text (handle enum or string)
            if hasattr(drive_outcome, 'value'):
                outcome_text = drive_outcome.value.replace('_', ' ').title()
            elif isinstance(drive_outcome, str):
                outcome_text = drive_outcome.replace('_', ' ').title()
            else:
                outcome_text = str(drive_outcome).replace('_', ' ').title()

            if points_scored > 0:
                outcome_text = f"{outcome_text} ({points_scored} pts)"

            drive_summary = f"Drive {drive_num}: {team_abbr} - {len(plays)} plays, {drive_yards} yds, {time_str} → {outcome_text}"

            # Create drive item
            drive_item = QTreeWidgetItem([drive_summary, "", ""])
            drive_item.setFont(0, Typography.SMALL_BOLD)

            # Track situational context (use actual starting down state for quarter continuations)
            current_down = getattr(drive, 'starting_down', 1)
            yards_to_go = getattr(drive, 'starting_distance', 10)
            field_position = getattr(drive, 'starting_field_position', 50)

            # Add kickoff as first item if present (matches JSON export behavior)
            kickoff_result = getattr(drive, 'kickoff_result', None)
            if kickoff_result:
                is_touchback = getattr(kickoff_result, 'is_touchback', False)
                return_yards = getattr(kickoff_result, 'return_yards', 0)
                starting_pos = getattr(kickoff_result, 'starting_field_position', 25)

                if is_touchback:
                    kickoff_desc = f"Kickoff: Touchback, ball at OWN {starting_pos}"
                else:
                    kickoff_desc = f"Kickoff: Returned {return_yards} yards to OWN {starting_pos}"

                kickoff_item = QTreeWidgetItem([
                    kickoff_desc,
                    "Kickoff",
                    f"+{return_yards}" if return_yards > 0 else "TB"
                ])
                kickoff_item.setForeground(0, Qt.darkCyan)  # Distinct color for kickoffs
                drive_item.addChild(kickoff_item)

            # Add plays as children
            for play_num, play in enumerate(plays, 1):
                play_desc = self._format_play_description(
                    play, play_num, current_down, yards_to_go, field_position
                )
                play_outcome = getattr(play, 'outcome', 'unknown')
                play_yards = getattr(play, 'yards', 0)
                play_time = getattr(play, 'time_elapsed', 0)

                # Update cumulative game time and format it
                total_game_time += play_time
                time_minutes = int(total_game_time // 60)
                time_seconds = int(total_game_time % 60)
                time_display = f"{time_minutes}:{time_seconds:02d}"

                # Add time elapsed to play description
                play_desc = f"{play_desc} (Time: {time_display})"

                # Format outcome (handle enum or string)
                if hasattr(play_outcome, 'value'):
                    outcome_text = play_outcome.value.replace('_', ' ').title()
                elif isinstance(play_outcome, str):
                    outcome_text = play_outcome.replace('_', ' ').title()
                else:
                    outcome_text = str(play_outcome).replace('_', ' ').title()

                play_item = QTreeWidgetItem([
                    play_desc,
                    outcome_text,
                    f"{play_yards:+d}" if play_yards != 0 else "0"
                ])

                # Color code scoring plays and turnovers
                if getattr(play, 'is_scoring_play', False):
                    play_item.setForeground(0, Qt.green)
                    play_item.setFont(0, Typography.TINY_BOLD)
                elif getattr(play, 'is_turnover', False):
                    play_item.setForeground(0, Qt.red)
                    play_item.setFont(0, Typography.TINY_BOLD)

                drive_item.addChild(play_item)

                # Update situational context for next play
                # Use DriveManager's corrected state from snapshots (REQUIRED - no fallback)
                is_last_play = (play_num == len(plays))
                if hasattr(play, 'down_after_play') and play.down_after_play is not None:
                    current_down = play.down_after_play
                    yards_to_go = play.distance_after_play
                    field_position = play.field_position_after_play
                elif is_last_play:
                    # Last play of drive - down_after_play is None (expected, drive ended)
                    # Just update field_position for consistency
                    field_position = getattr(play, 'field_position_after_play', field_position)
                else:
                    # FAIL LOUDLY: Mid-drive play missing snapshot - this is a bug
                    raise ValueError(
                        f"Play #{play_num}/{len(plays)} in Drive {drive_num} missing down_after_play snapshot. "
                        f"DriveManager.process_play_result() must set down_after_play, distance_after_play, "
                        f"and field_position_after_play on every PlayResult. "
                        f"Play outcome: {getattr(play, 'outcome', 'unknown')}, yards: {play_yards}"
                    )

            # ✅ Display PAT (extra point) play if this was a touchdown drive
            pat_result = getattr(drive, 'pat_result', None)
            if pat_result:
                # Update cumulative game time with PAT attempt time (typically ~5 seconds)
                pat_time = 5.0  # Standard PAT attempt time
                total_game_time += pat_time
                time_minutes = int(total_game_time // 60)
                time_seconds = int(total_game_time % 60)
                time_display = f"{time_minutes}:{time_seconds:02d}"

                # Format PAT play description
                if pat_result.get('made', False):
                    pat_desc = f"Extra Point GOOD (Time: {time_display})"
                    pat_outcome = "Made"
                    pat_yards = 0  # PATs don't change field position
                    pat_color = Qt.green
                else:
                    pat_desc = f"Extra Point MISSED (Time: {time_display})"
                    pat_outcome = "Missed"
                    pat_yards = 0
                    pat_color = Qt.red

                # Create PAT play item
                pat_item = QTreeWidgetItem([
                    pat_desc,
                    pat_outcome,
                    f"{pat_yards:+d}" if pat_yards != 0 else "0"
                ])
                pat_item.setForeground(0, pat_color)
                pat_item.setFont(0, Typography.TINY_BOLD)
                drive_item.addChild(pat_item)

            # ✅ FIX: Add drive as child of quarter item instead of top-level
            if quarter_item:
                quarter_item.addChild(drive_item)
            else:
                tree.addTopLevelItem(drive_item)
            drive_item.setExpanded(True)  # Expand by default

            # Update score if this was a scoring drive
            if points_scored > 0:
                # Add touchdown/field goal points
                drive_points = points_scored

                # Add PAT points if applicable
                if pat_result and pat_result.get('made', False):
                    drive_points += 1  # Extra point adds 1 point

                # Update team score
                if possessing_team_id == home_id:
                    home_score += drive_points
                else:
                    away_score += drive_points

                # Add score line after scoring drive
                score_line = f"Score: {away_abbr} {away_score}, {home_abbr} {home_score}"
                score_item = QTreeWidgetItem([score_line, "", ""])
                score_item.setForeground(0, Qt.darkGreen)
                score_item.setFont(0, Typography.TINY_BOLD)
                # ✅ FIX: Add score as child of quarter item
                if quarter_item:
                    quarter_item.addChild(score_item)
                else:
                    tree.addTopLevelItem(score_item)

    def _format_play_description(
        self,
        play,
        play_num: int,
        down: int,
        distance: int,
        yard_line: int
    ) -> str:
        """Format a single play into a readable description with game situation."""
        outcome = getattr(play, 'outcome', 'unknown')
        yards = getattr(play, 'yards', 0)

        # Convert enum to string if needed
        if hasattr(outcome, 'value'):
            outcome_str = outcome.value
        else:
            outcome_str = str(outcome)

        # Format down & distance (e.g., "1st & 10" or "1st & Goal")
        down_str = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(down, f"{down}th")
        # Goal-to-go: when first down line would be at or past the goal line
        if yard_line + distance >= 100:
            dist_str = "Goal"
        else:
            dist_str = str(distance)

        # Format yard line (0-100 becomes team side)
        if yard_line <= 50:
            field_str = f"OWN {yard_line}"
        else:
            field_str = f"OPP {100 - yard_line}"

        situation = f"{down_str} & {dist_str} at {field_str}"

        # Filter out punt execution failed (system error, not interesting)
        if 'punt_execution_failed' in outcome_str.lower():
            # Show as a generic punt with note
            return f"{situation}: Punt (execution error)"

        # Get player names if available
        players = ""
        if hasattr(play, 'get_key_players'):
            players = play.get_key_players()
            if players:
                players = f" ({players})"

        # ✅ FIX 4: Check if this play crossed goal line for TD
        play_yards = getattr(play, 'yards', 0)
        crosses_goal_line = (yard_line + play_yards >= 100 and play_yards > 0)
        is_touchdown_play = crosses_goal_line or getattr(play, 'is_scoring_play', False)

        # Basic description
        # ✅ NEW: Handle detailed pass outcomes from PassPlaySimulator
        # These outcomes don't contain "pass" so need explicit handlers
        # ✅ FIX: Check 'incomplete' FIRST - 'complete' in 'incomplete' returns True!
        outcome_lower = outcome_str.lower()
        if outcome_lower == 'incomplete':
            play_desc = f"Pass incomplete{players}"
        elif outcome_lower == 'completion' or (outcome_lower != 'incomplete' and 'complete' in outcome_lower):
            play_desc = f"Pass complete{players}, {yards} yards"
            if is_touchdown_play and 'field_goal' not in outcome_lower:
                play_desc += " - TOUCHDOWN"
        elif outcome_str.lower() == 'interception':
            play_desc = f"INTERCEPTION{players}"
        elif 'pass' in outcome_str.lower():
            if 'completion' in outcome_str.lower():
                play_desc = f"Pass complete{players}, {yards} yards"
                if is_touchdown_play and 'field_goal' not in outcome_str.lower():
                    play_desc += " - TOUCHDOWN"  # ✅ Explicit TD notation
            elif 'incomplete' in outcome_str.lower():
                play_desc = f"Pass incomplete{players}"
            elif 'sack' in outcome_str.lower() or (yards < 0 and 'pass' in outcome_str.lower()):
                # Detect both explicit sacks and negative yardage passes
                play_desc = f"Sacked{players}, {yards} yards"
            else:
                # If 0 yards and no specific outcome, likely incomplete
                if yards == 0:
                    if players:
                        play_desc = f"Pass incomplete{players}"
                    else:
                        play_desc = "Pass incomplete (no target)"
                else:
                    play_desc = f"{outcome_str.replace('_', ' ').title()}{players}"
        elif 'rush' in outcome_str.lower() or outcome_str.lower() == 'run':
            # Cap run play yards at -5 minimum (realistic TFL range is -3 to -5)
            # Anything below -5 is likely a display bug or penalty misattribution
            display_yards = max(-5, yards) if yards < 0 else yards
            play_desc = f"Rush{players}, {display_yards} yards"
            if is_touchdown_play:
                play_desc += " - TOUCHDOWN"  # ✅ Explicit TD notation
        elif 'punt' in outcome_str.lower():
            # Get punt distance from PlayResult if available
            punt_distance = getattr(play, 'punt_distance', None)
            return_yards = getattr(play, 'return_yards', None)
            if punt_distance:
                if return_yards and return_yards > 0:
                    play_desc = f"Punt{players}, {punt_distance} yards (returned {return_yards})"
                else:
                    play_desc = f"Punt{players}, {punt_distance} yards"
            else:
                # Fallback: calculate estimated punt distance from field position change
                # A punt from OWN 20 ending at opposing team's 25 ≈ 55-yard punt
                play_desc = f"Punt{players}"
        elif 'field_goal' in outcome_str.lower():
            # Calculate field goal distance: (100 - yard_line) + 17 (end zone + line of scrimmage)
            fg_distance = (100 - yard_line) + 17 if yard_line < 100 else 17

            # Check for "made" to determine if it was good
            if 'made' in outcome_str.lower():
                play_desc = f"{fg_distance}-yard Field Goal GOOD{players}"
            else:
                play_desc = f"{fg_distance}-yard Field Goal MISSED{players}"

            # NEW: Field goals should show 0 yards unless it's a fake
            if not getattr(play, 'is_fake_field_goal', False):
                yards = 0  # Real FGs always show 0 yards
            # else: keep yards as-is for fake FGs

            # Show penalty separately if it occurred
            if hasattr(play, 'penalty_occurred') and play.penalty_occurred:
                penalty_yards = getattr(play, 'penalty_yards', 0)
                if penalty_yards != 0:
                    play_desc += f" (Penalty: {penalty_yards:+d} yards)"
        else:
            play_desc = f"{outcome_str.replace('_', ' ').title()}{players}"

        # Add scoring indicator
        if getattr(play, 'is_scoring_play', False):
            points = getattr(play, 'points', 0)
            if points > 0:
                play_desc += f" [+{points} pts]"

        # Special notation for safety (defensive scoring)
        if 'safety' in outcome_str.lower():
            play_desc += " [SAFETY: +2 pts for defense]"

        # Add turnover indicator
        if getattr(play, 'is_turnover', False):
            turnover_type = getattr(play, 'turnover_type', 'turnover')
            play_desc += f" [TURNOVER: {turnover_type}]"

        # Check for penalties on ALL play types (not just field goals)
        if hasattr(play, 'penalty_occurred') and play.penalty_occurred:
            penalty_yards = getattr(play, 'penalty_yards', 0)
            penalty_type = getattr(play, 'penalty_type', None)

            # Try to get detailed penalty info from player_stats_summary
            if hasattr(play, 'player_stats_summary') and play.player_stats_summary:
                penalty_instance = getattr(play.player_stats_summary, 'penalty_instance', None)
                if penalty_instance:
                    penalty_type = getattr(penalty_instance, 'penalty_type', 'Penalty')
                    penalty_type = penalty_type.replace('_', ' ').title()
                    player_num = getattr(penalty_instance, 'penalized_player_number', '')
                    team_side = getattr(penalty_instance, 'team_side', 'offense')
                    yards = abs(getattr(penalty_instance, 'yards_assessed', penalty_yards))
                    # ✅ FIX: Include accept/decline status
                    accepted = getattr(penalty_instance, 'penalty_accepted', None)
                    status_str = ""
                    if accepted is True:
                        status_str = ", ACCEPTED"
                    elif accepted is False:
                        status_str = ", DECLINED"

                    if player_num:
                        play_desc += f" [PENALTY: {penalty_type} #{player_num} ({team_side}), {yards} yds{status_str}]"
                    else:
                        play_desc += f" [PENALTY: {penalty_type}, {yards} yds{status_str}]"
            elif penalty_type:
                penalty_type = penalty_type.replace('_', ' ').title()
                play_desc += f" [PENALTY: {penalty_type}, {abs(penalty_yards)} yds]"
            elif penalty_yards != 0:
                play_desc += f" [PENALTY: {abs(penalty_yards)} yds]"

        # Combine situation + play description
        return f"{situation}: {play_desc}"

    def _format_play_description_for_table(
        self,
        play,
        play_num: int,
        down: int,
        distance: int,
        yard_line: int
    ) -> str:
        """
        Format a play description for markdown table format (no situation prefix).

        Returns just the play type and players for cleaner table display.
        """
        outcome = getattr(play, 'outcome', 'unknown')
        yards = getattr(play, 'yards', 0)

        # Convert enum to string if needed
        if hasattr(outcome, 'value'):
            outcome_str = outcome.value
        else:
            outcome_str = str(outcome)

        # Filter out punt execution failed
        if 'punt_execution_failed' in outcome_str.lower():
            return "Punt (error)"

        # Get player names if available
        players = ""
        if hasattr(play, 'get_key_players'):
            players = play.get_key_players()
            if players:
                players = f" ({players})"

        # Check if this play crossed goal line for TD
        play_yards = getattr(play, 'yards', 0)
        crosses_goal_line = (yard_line + play_yards >= 100 and play_yards > 0)
        is_touchdown_play = crosses_goal_line or getattr(play, 'is_scoring_play', False)

        # Format play description based on outcome type
        # ✅ FIX: Check 'incomplete' FIRST - 'complete' in 'incomplete' returns True!
        outcome_lower = outcome_str.lower()
        if outcome_lower == 'incomplete':
            play_desc = f"Incomplete{players}"
        elif 'deflected' in outcome_lower:
            # Handle deflected_incomplete - must check BEFORE 'complete' check
            play_desc = f"Incomplete{players}"
        elif outcome_lower == 'completion' or (outcome_lower != 'incomplete' and 'complete' in outcome_lower):
            play_desc = f"Pass{players}"
            if is_touchdown_play:
                play_desc += " **TD**"
        elif outcome_lower == 'interception':
            play_desc = f"INT{players}"
        elif 'pass' in outcome_lower:
            if 'completion' in outcome_str.lower():
                play_desc = f"Pass{players}"
                if is_touchdown_play:
                    play_desc += " **TD**"
            elif 'incomplete' in outcome_str.lower():
                play_desc = f"Incomplete{players}"
            elif 'sack' in outcome_str.lower() or yards < 0:
                play_desc = f"Sack{players}"
            else:
                if yards == 0:
                    play_desc = f"Incomplete{players}"
                else:
                    play_desc = f"Pass{players}"
        elif 'rush' in outcome_str.lower() or 'run' in outcome_str.lower():
            play_desc = f"Rush{players}"
            if is_touchdown_play:
                play_desc += " **TD**"
        elif 'scramble' in outcome_str.lower():
            # QB scramble - format as "QB Scrambles for X yards, tackled by Defender"
            qb_name = ""
            tackler_info = ""
            if players:
                inner = players.strip(" ()")
                if ", tackled by " in inner:
                    parts = inner.split(", tackled by ")
                    qb_name = parts[0]
                    tackler_info = f", tackled by {parts[1]}"
                else:
                    qb_name = inner

            if is_touchdown_play:
                play_desc = f"{qb_name} Scrambles for {yards} yards **TD**"
            else:
                play_desc = f"{qb_name} Scrambles for {yards} yards{tackler_info}"
        elif 'punt' in outcome_str.lower():
            punt_distance = getattr(play, 'punt_distance', None)
            return_yards = getattr(play, 'return_yards', None)
            if punt_distance:
                if return_yards and return_yards > 0:
                    play_desc = f"Punt {punt_distance}yds (ret {return_yards})"
                else:
                    play_desc = f"Punt {punt_distance}yds"
            else:
                play_desc = "Punt"
        elif 'field_goal' in outcome_str.lower():
            fg_distance = 100 - yard_line + 17
            if 'miss' in outcome_str.lower() or 'block' in outcome_str.lower():
                play_desc = f"FG MISS {fg_distance}yds"
            else:
                play_desc = f"FG GOOD {fg_distance}yds"
        elif 'spike' in outcome_str.lower():
            play_desc = "Spike (clock stop)"
        elif 'kneel' in outcome_str.lower():
            play_desc = "Kneel"
        else:
            # Fallback
            play_desc = outcome_str.replace('_', ' ').title() + players

        # Add penalty info if present - ✅ FIX: Include accept/decline status
        if hasattr(play, 'penalty_occurred') and play.penalty_occurred:
            # Try to get detailed penalty info from player_stats_summary
            penalty_instance = None
            if hasattr(play, 'player_stats_summary') and play.player_stats_summary:
                penalty_instance = getattr(play.player_stats_summary, 'penalty_instance', None)

            if penalty_instance:
                penalty_type = getattr(penalty_instance, 'penalty_type', 'Penalty')
                penalty_type = penalty_type.replace('_', ' ').title()
                penalty_yards = abs(getattr(penalty_instance, 'yards_assessed', 0))
                accepted = getattr(penalty_instance, 'penalty_accepted', None)

                if accepted is True:
                    play_desc += f" [PEN: {penalty_type} {penalty_yards}yds, ACCEPTED]"
                elif accepted is False:
                    play_desc += f" [PEN: {penalty_type} {penalty_yards}yds, DECLINED]"
                else:
                    play_desc += f" [PEN: {penalty_type} {penalty_yards}yds]"
            else:
                # Fallback to basic penalty info
                penalty_type = getattr(play, 'penalty_type', None)
                penalty_yards = getattr(play, 'penalty_yards', 0)
                if penalty_type:
                    penalty_type = penalty_type.replace('_', ' ').title()
                    play_desc += f" [PEN: {penalty_type}]"
                elif penalty_yards != 0:
                    play_desc += f" [PEN: {abs(penalty_yards)}yds]"

        return play_desc

    def _export_as_markdown(self):
        """Export play-by-play data as a Markdown file."""
        if not self._game_result or not hasattr(self._game_result, 'drives'):
            QMessageBox.warning(self, "No Data", "No play-by-play data available to export.")
            return

        # Get save location
        away_abbr = self._away_team.get('abbr', 'AWAY')
        home_abbr = self._home_team.get('abbr', 'HOME')
        default_filename = f"playbyplay_{away_abbr}_at_{home_abbr}.md"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Play-by-Play as Markdown",
            default_filename,
            "Markdown Files (*.md);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Build markdown content
            markdown_lines = []
            markdown_lines.append(f"# Game: {self._away_team.get('name')} {self._away_score} @ {self._home_team.get('name')} {self._home_score}\n")
            markdown_lines.append(f"**Game ID:** {self._game_id}\n")
            markdown_lines.append("---\n")

            home_id = self._home_team.get('id')
            away_id = self._away_team.get('id')
            home_abbr = self._home_team.get('abbr', 'HOME')
            away_abbr = self._away_team.get('abbr', 'AWAY')
            home_name = self._home_team.get('name')
            away_name = self._away_team.get('name')

            # Track previous drive for kickoff detection
            prev_possessing_team_id = None
            prev_drive_outcome = None
            prev_points_scored = 0

            # Initialize running score tracking
            home_score = 0
            away_score = 0

            # Track quarter based on cumulative time (15 min per quarter)
            cumulative_time = 0.0
            current_quarter = 1
            quarter_time_elapsed = 0.0  # Time elapsed in current quarter (resets at quarter change)
            halftime_shown = False

            # Add initial quarter header
            markdown_lines.append(f"\n---\n")
            markdown_lines.append(f"# QUARTER 1\n")
            markdown_lines.append(f"---\n")

            for drive_num, drive in enumerate(self._game_result.drives, 1):
                # Calculate drive time and determine quarter changes
                plays = getattr(drive, 'plays', [])
                drive_time_seconds = sum(getattr(play, 'time_elapsed', 0) for play in plays)

                # ✅ Use actual quarter from DriveResult (more accurate than calculated)
                drive_quarter = getattr(drive, 'quarter_started', 1)

                # Check for quarter change
                if drive_quarter > current_quarter:
                    # Show halftime if transitioning from Q2 to Q3
                    if current_quarter == 2 and drive_quarter >= 3 and not halftime_shown:
                        markdown_lines.append(f"\n---\n")
                        markdown_lines.append(f"## HALFTIME\n")
                        markdown_lines.append(f"**Score:** {away_abbr} {away_score} - {home_abbr} {home_score}\n")
                        markdown_lines.append(f"---\n")
                        halftime_shown = True

                    current_quarter = drive_quarter
                    quarter_time_elapsed = 0.0  # Reset quarter clock at quarter change
                    markdown_lines.append(f"\n---\n")
                    markdown_lines.append(f"# QUARTER {current_quarter}\n")
                    markdown_lines.append(f"---\n")

                # Update cumulative time
                cumulative_time += drive_time_seconds

                possessing_team_id = getattr(drive, 'possessing_team_id', None)
                team_abbr = home_abbr if possessing_team_id == home_id else away_abbr
                team_name = self._home_team.get('name') if possessing_team_id == home_id else self._away_team.get('name')

                drive_outcome = getattr(drive, 'drive_outcome', 'unknown')
                points_scored = getattr(drive, 'points_scored', 0)

                # ✅ FIX: Display kickoff from drive.kickoff_result if present
                # This handles ALL kickoffs: game-start, halftime, and post-score
                kickoff_result = getattr(drive, 'kickoff_result', None)
                if kickoff_result:
                    kicking_team_id = getattr(kickoff_result, 'kicking_team_id', None)
                    receiving_team_id = getattr(kickoff_result, 'receiving_team_id', None)
                    is_touchback = getattr(kickoff_result, 'is_touchback', False)
                    return_yards = getattr(kickoff_result, 'return_yards', 0)
                    starting_pos = getattr(kickoff_result, 'starting_field_position', 25)

                    # Get team names
                    kicking_team = home_name if kicking_team_id == home_id else away_name
                    receiving_team = home_name if receiving_team_id == home_id else away_name

                    markdown_lines.append(f"\n## Kickoff: {kicking_team} to {receiving_team}\n")
                    if is_touchback:
                        markdown_lines.append(f"**Return:** Touchback to 25-yard line\n")
                    elif return_yards > 0:
                        markdown_lines.append(f"**Return:** Returned {return_yards} yards to OWN {starting_pos}\n")
                    else:
                        markdown_lines.append(f"**Return:** Returned to OWN {starting_pos}\n")
                    markdown_lines.append(f"**Score:** {away_abbr} {away_score}, {home_abbr} {home_score}\n")

                # Calculate drive stats
                drive_yards = sum(getattr(play, 'yards', 0) for play in plays)
                drive_time_seconds = sum(getattr(play, 'time_elapsed', 0) for play in plays)
                time_minutes = int(drive_time_seconds // 60)
                time_seconds = int(drive_time_seconds % 60)
                time_str = f"{time_minutes}:{time_seconds:02d}"

                # Format outcome
                if hasattr(drive_outcome, 'value'):
                    outcome_text = drive_outcome.value.replace('_', ' ').title()
                else:
                    outcome_text = str(drive_outcome).replace('_', ' ').title()

                if points_scored > 0:
                    outcome_text = f"{outcome_text} ({points_scored} pts)"

                # Drive header (include quarter indicator)
                markdown_lines.append(f"\n## Drive {drive_num} (Q{drive_quarter}): {team_name} ({team_abbr})\n")
                markdown_lines.append(f"**Stats:** {len(plays)} plays, {drive_yards} yards, {time_str}\n")
                markdown_lines.append(f"**Result:** {outcome_text}\n")

                # Track situational context (use actual starting down state for quarter continuations)
                current_down = getattr(drive, 'starting_down', 1)
                yards_to_go = getattr(drive, 'starting_distance', 10)
                field_position = getattr(drive, 'starting_field_position', 50)

                # ✅ FIX: Use quarter_time_elapsed instead of modulo (properly resets at quarter changes)
                # Note: quarter_time_elapsed is reset at each quarter change above

                # ✅ NEW: Use markdown table format for plays
                # Table header
                markdown_lines.append("\n| Qtr | Time | Down | Field Pos | Play Description | Result |\n")
                markdown_lines.append("|-----|------|------|-----------|------------------|--------|\n")

                # Plays
                for play_num, play in enumerate(plays, 1):
                    play_yards = getattr(play, 'yards', 0)
                    play_time = getattr(play, 'time_elapsed', 0)

                    # ✅ FIX: Calculate remaining clock time using quarter_time_elapsed (properly resets at quarter changes)
                    quarter_seconds_remaining = max(0, 900 - quarter_time_elapsed)
                    clock_minutes = int(quarter_seconds_remaining // 60)
                    clock_seconds = int(quarter_seconds_remaining % 60)
                    time_display = f"{clock_minutes}:{clock_seconds:02d}"

                    # Check for two-minute warning (only in Q2 and Q4)
                    time_before_play = quarter_seconds_remaining
                    time_after_play = max(0, quarter_seconds_remaining - play_time)
                    if current_quarter in [2, 4]:
                        if time_before_play > 120 >= time_after_play:
                            markdown_lines.append(f"| Q{current_quarter} | ⏱️ | | | **TWO-MINUTE WARNING** | |\n")

                    # Update quarter time elapsed after this play
                    quarter_time_elapsed += play_time

                    # Format down & distance (shows "Goal" when in goal-to-go situation)
                    down_str = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(current_down, f"{current_down}th")
                    if field_position + yards_to_go >= 100:
                        down_dist = f"{down_str} & Goal"
                    else:
                        down_dist = f"{down_str} & {yards_to_go}"

                    # Format field position
                    if field_position <= 50:
                        field_str = f"OWN {field_position}"
                    else:
                        field_str = f"OPP {100 - field_position}"

                    # Format play description (simplified for table)
                    play_desc = self._format_play_description_for_table(play, play_num, current_down, yards_to_go, field_position)

                    # Format result
                    is_scoring = getattr(play, 'is_scoring_play', False)
                    is_turnover = getattr(play, 'is_turnover', False)
                    points = getattr(play, 'points', 0)
                    if is_scoring and points == 6:
                        # Touchdown: Calculate actual TD yards from field position (not penalty-adjusted)
                        # field_position is in OWN territory scale (0-100), TD is at 100
                        actual_td_yards = 100 - field_position
                        result_str = f"**+{actual_td_yards} TD**"
                    elif is_scoring and points == 3:
                        # Field goal: FGs don't gain yards, just show +0 (scoring is in play description)
                        result_str = f"+0"
                    elif is_turnover:
                        result_str = f"{play_yards:+d} TO"
                    else:
                        result_str = f"{play_yards:+d}"

                    # Add table row
                    markdown_lines.append(f"| Q{current_quarter} | {time_display} | {down_dist} | {field_str} | {play_desc} | {result_str} |\n")

                    # Update situational context
                    # Use DriveManager's corrected state from snapshots (REQUIRED - no fallback)
                    is_last_play = (play_num == len(plays))
                    if hasattr(play, 'down_after_play') and play.down_after_play is not None:
                        current_down = play.down_after_play
                        yards_to_go = play.distance_after_play
                        field_position = play.field_position_after_play
                    elif is_last_play:
                        # Last play of drive - down_after_play is None (expected, drive ended)
                        # Just update field_position for consistency
                        field_position = getattr(play, 'field_position_after_play', field_position)
                    else:
                        # FAIL LOUDLY: Mid-drive play missing snapshot - this is a bug
                        raise ValueError(
                            f"Play #{play_num}/{len(plays)} in Drive {drive_num} missing down_after_play snapshot. "
                            f"DriveManager.process_play_result() must set down_after_play, distance_after_play, "
                            f"and field_position_after_play on every PlayResult. "
                            f"Play outcome: {getattr(play, 'outcome', 'unknown')}, yards: {play_yards}"
                        )

                # Add PAT (extra point or 2-point conversion) if present
                pat_result = getattr(drive, 'pat_result', None)
                pat_points = 0
                if pat_result:
                    # Check both 'success' and 'made' keys for compatibility
                    pat_success = pat_result.get('success', pat_result.get('made', False))
                    pat_type = pat_result.get('type', 'extra_point')

                    if pat_type == 'two_point':
                        outcome = "GOOD" if pat_success else "FAILED"
                        points = 2 if pat_success else 0
                        pat_points = points
                        markdown_lines.append(f"- **PAT:** 2-Point Conversion {outcome} [+{points} pts] (+0 yds)\n")
                    else:
                        # Default to extra point
                        outcome = "GOOD" if pat_success else "MISSED"
                        points = 1 if pat_success else 0
                        pat_points = points
                        markdown_lines.append(f"- **PAT:** Extra Point {outcome} [+{points} pts] (+0 yds)\n")

                # ✅ FIX: Calculate score based on drive_outcome instead of play points
                # This handles cases where the scoring play might be missing from the plays list
                # Get string value of drive_outcome (handle both enum and string)
                if hasattr(drive_outcome, 'value'):
                    outcome_str = drive_outcome.value.lower()
                else:
                    outcome_str = str(drive_outcome).lower()

                # Calculate drive points from outcome type
                drive_points_from_outcome = 0
                if 'touchdown' in outcome_str:
                    drive_points_from_outcome = 6
                elif 'field_goal' in outcome_str and 'missed' not in outcome_str:
                    drive_points_from_outcome = 3
                elif 'safety' in outcome_str:
                    # Safety is special - defense gets 2 points, not offense
                    if possessing_team_id == home_id:
                        away_score += 2
                    else:
                        home_score += 2
                    # Don't add to drive_points_from_outcome, safety is handled above
                    drive_points_from_outcome = 0

                # Add drive points + PAT to possessing team (unless it was a safety)
                if 'safety' not in outcome_str:
                    drive_total_points = drive_points_from_outcome + pat_points
                    if possessing_team_id == home_id:
                        home_score += drive_total_points
                    else:
                        away_score += drive_total_points

                # Update tracking for next iteration
                prev_possessing_team_id = possessing_team_id
                prev_drive_outcome = drive_outcome
                prev_points_scored = points_scored

            # Add final score
            markdown_lines.append(f"\n---\n")
            markdown_lines.append(f"# FINAL SCORE\n")
            markdown_lines.append(f"**{away_name} {away_score} - {home_name} {home_score}**\n")
            markdown_lines.append(f"---\n")

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(markdown_lines)

            QMessageBox.information(self, "Export Successful", f"Play-by-play exported to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export play-by-play:\n{str(e)}")

    def _export_as_json(self):
        """Export play-by-play data as a JSON file."""
        if not self._game_result or not hasattr(self._game_result, 'drives'):
            QMessageBox.warning(self, "No Data", "No play-by-play data available to export.")
            return

        # Get save location
        away_abbr = self._away_team.get('abbr', 'AWAY')
        home_abbr = self._home_team.get('abbr', 'HOME')
        default_filename = f"playbyplay_{away_abbr}_at_{home_abbr}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Play-by-Play as JSON",
            default_filename,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Build JSON structure
            home_id = self._home_team.get('id')
            away_id = self._away_team.get('id')
            home_abbr = self._home_team.get('abbr', 'HOME')
            away_abbr = self._away_team.get('abbr', 'AWAY')

            game_data = {
                "game_id": self._game_id,
                "home_team": {
                    "id": home_id,
                    "name": self._home_team.get('name'),
                    "abbr": home_abbr,
                    "score": self._home_score
                },
                "away_team": {
                    "id": away_id,
                    "name": self._away_team.get('name'),
                    "abbr": away_abbr,
                    "score": self._away_score
                },
                "drives": []
            }

            for drive_num, drive in enumerate(self._game_result.drives, 1):
                possessing_team_id = getattr(drive, 'possessing_team_id', None)
                team_abbr = home_abbr if possessing_team_id == home_id else away_abbr

                drive_outcome = getattr(drive, 'drive_outcome', 'unknown')
                points_scored = getattr(drive, 'points_scored', 0)
                plays = getattr(drive, 'plays', [])

                # Calculate drive stats
                drive_yards = sum(getattr(play, 'yards', 0) for play in plays)
                drive_time_seconds = sum(getattr(play, 'time_elapsed', 0) for play in plays)

                # Format outcome
                if hasattr(drive_outcome, 'value'):
                    outcome_text = drive_outcome.value
                else:
                    outcome_text = str(drive_outcome)

                drive_data = {
                    "drive_number": drive_num,
                    "possessing_team": team_abbr,
                    "possessing_team_id": possessing_team_id,
                    "starting_field_position": getattr(drive, 'starting_field_position', 50),
                    "total_plays": len(plays),
                    "total_yards": drive_yards,
                    "time_of_possession_seconds": drive_time_seconds,
                    "outcome": outcome_text,
                    "points_scored": points_scored,
                    "plays": []
                }

                # Add kickoff as "play 0" if present (matches markdown export behavior)
                kickoff_result = getattr(drive, 'kickoff_result', None)
                if kickoff_result:
                    is_touchback = getattr(kickoff_result, 'is_touchback', False)
                    return_yards = getattr(kickoff_result, 'return_yards', 0)
                    starting_pos = getattr(kickoff_result, 'starting_field_position', 25)
                    kickoff_data = {
                        "play_number": 0,
                        "down": None,
                        "distance": None,
                        "yard_line": starting_pos,
                        "outcome": "touchback" if is_touchback else "kickoff_return",
                        "yards_gained": return_yards,
                        "time_elapsed": 0,
                        "is_scoring_play": False,
                        "is_turnover": False,
                        "is_first_down": False,
                        "points": 0,
                        "is_kickoff": True
                    }
                    drive_data["plays"].append(kickoff_data)

                # Track situational context (use actual starting down state for quarter continuations)
                current_down = getattr(drive, 'starting_down', 1)
                yards_to_go = getattr(drive, 'starting_distance', 10)
                field_position = getattr(drive, 'starting_field_position', 50)

                # Add plays
                for play_num, play in enumerate(plays, 1):
                    play_outcome = getattr(play, 'outcome', 'unknown')
                    play_yards = getattr(play, 'yards', 0)
                    time_elapsed = getattr(play, 'time_elapsed', 0)

                    # Format outcome
                    if hasattr(play_outcome, 'value'):
                        outcome_str = play_outcome.value
                    else:
                        outcome_str = str(play_outcome)

                    play_data = {
                        "play_number": play_num,
                        "down": current_down,
                        "distance": yards_to_go,
                        "yard_line": field_position,
                        "outcome": outcome_str,
                        "yards_gained": play_yards,
                        "time_elapsed": time_elapsed,
                        "is_scoring_play": getattr(play, 'is_scoring_play', False),
                        "is_turnover": getattr(play, 'is_turnover', False),
                        "is_first_down": getattr(play, 'achieved_first_down', False),
                        "points": getattr(play, 'points', 0)
                    }

                    # Add player info if available
                    if hasattr(play, 'get_key_players'):
                        players = play.get_key_players()
                        if players:
                            play_data["players"] = players

                    drive_data["plays"].append(play_data)

                    # Update situational context for next play
                    # Use DriveManager's corrected state from snapshots (REQUIRED - no fallback)
                    is_last_play = (play_num == len(plays))
                    if hasattr(play, 'down_after_play') and play.down_after_play is not None:
                        current_down = play.down_after_play
                        yards_to_go = play.distance_after_play
                        field_position = play.field_position_after_play
                    elif is_last_play:
                        # Last play of drive - down_after_play is None (expected, drive ended)
                        field_position = getattr(play, 'field_position_after_play', field_position)
                    else:
                        # FAIL LOUDLY: Mid-drive play missing snapshot - this is a bug
                        raise ValueError(
                            f"Play #{play_num}/{len(plays)} in Drive missing down_after_play snapshot. "
                            f"DriveManager.process_play_result() must set down_after_play, distance_after_play, "
                            f"and field_position_after_play on every PlayResult. "
                            f"Play outcome: {getattr(play, 'outcome', 'unknown')}, yards: {play_yards}"
                        )

                game_data["drives"].append(drive_data)

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2)

            QMessageBox.information(self, "Export Successful", f"Play-by-play exported to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export play-by-play:\n{str(e)}")

    def _export_markdown(self):
        """Export box score as Markdown file."""
        # Generate default filename
        default_name = f"boxscore_{self._game_id}.md"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Box Score as Markdown",
            default_name,
            "Markdown Files (*.md);;All Files (*)"
        )

        if not file_path:
            return

        try:
            away_name = self._away_team.get('name', 'Away')
            home_name = self._home_team.get('name', 'Home')
            away_abbr = self._away_team.get('abbr', 'AWAY')
            home_abbr = self._home_team.get('abbr', 'HOME')

            lines = []

            # Header
            lines.append(f"# Box Score: {away_name} @ {home_name}")
            lines.append(f"**Final Score: {away_abbr} {self._away_score} - {home_abbr} {self._home_score}**")
            lines.append("")
            lines.append(f"Game ID: `{self._game_id}`")
            lines.append("")

            # Team Stats Comparison
            lines.append("## Team Stats")
            lines.append("")
            lines.append(f"| Stat | {away_abbr} | {home_abbr} |")
            lines.append("|------|-----|-----|")

            away_agg = self._aggregate_team_stats(self._away_stats)
            home_agg = self._aggregate_team_stats(self._home_stats)
            away_box = self._away_box_score or {}
            home_box = self._home_box_score or {}

            # First Downs
            lines.append(f"| First Downs | {away_box.get('first_downs', 0) or 0} | {home_box.get('first_downs', 0) or 0} |")

            # Total Yards
            lines.append(f"| Total Yards | {away_agg.get('total_yards', 0)} | {home_agg.get('total_yards', 0)} |")

            # Passing Yards
            lines.append(f"| Passing Yards | {away_agg.get('passing_yards', 0)} | {home_agg.get('passing_yards', 0)} |")

            # Rushing Yards
            lines.append(f"| Rushing Yards | {away_agg.get('rushing_yards', 0)} | {home_agg.get('rushing_yards', 0)} |")

            # Turnovers
            lines.append(f"| Turnovers | {away_agg.get('turnovers', 0)} | {home_agg.get('turnovers', 0)} |")

            # Time of Possession
            away_top = away_box.get('time_of_possession_str', 'N/A')
            home_top = home_box.get('time_of_possession_str', 'N/A')
            lines.append(f"| Time of Possession | {away_top} | {home_top} |")

            # 3rd Down
            away_3rd = f"{away_box.get('third_down_conv', 0) or 0}/{away_box.get('third_down_att', 0) or 0}"
            home_3rd = f"{home_box.get('third_down_conv', 0) or 0}/{home_box.get('third_down_att', 0) or 0}"
            lines.append(f"| 3rd Down | {away_3rd} | {home_3rd} |")

            # 4th Down
            away_4th = f"{away_box.get('fourth_down_conv', 0) or 0}/{away_box.get('fourth_down_att', 0) or 0}"
            home_4th = f"{home_box.get('fourth_down_conv', 0) or 0}/{home_box.get('fourth_down_att', 0) or 0}"
            lines.append(f"| 4th Down | {away_4th} | {home_4th} |")

            # Penalties
            away_pen = f"{away_box.get('penalties', 0) or 0}-{away_box.get('penalty_yards', 0) or 0}"
            home_pen = f"{home_box.get('penalties', 0) or 0}-{home_box.get('penalty_yards', 0) or 0}"
            lines.append(f"| Penalties | {away_pen} | {home_pen} |")

            lines.append("")

            # Player Stats for each team
            for team_label, team_name, stats in [
                (away_abbr, away_name, self._away_stats),
                (home_abbr, home_name, self._home_stats)
            ]:
                lines.append(f"## {team_name} Player Stats")
                lines.append("")

                # Passing
                passers = self._get_passers(stats)
                if passers:
                    lines.append("### Passing")
                    lines.append("| Player | C/ATT | YDS | TD | INT | RTG |")
                    lines.append("|--------|-------|-----|----|----|-----|")
                    for p in passers:
                        comp = p.get('passing_completions') or 0
                        att = p.get('passing_attempts') or 0
                        yds = p.get('passing_yards') or 0
                        td = p.get('passing_tds') or 0
                        ints = p.get('passing_interceptions') or 0
                        rtg = p.get('passing_rating') or 0
                        lines.append(f"| {p.get('player_name', 'Unknown')} | {comp}/{att} | {yds} | {td} | {ints} | {rtg:.1f} |")
                    lines.append("")

                # Rushing
                rushers = self._get_rushers(stats)
                if rushers:
                    lines.append("### Rushing")
                    lines.append("| Player | ATT | YDS | AVG | TD | LNG |")
                    lines.append("|--------|-----|-----|-----|----|----|")
                    for p in rushers:
                        att = p.get('rushing_attempts') or 0
                        yds = p.get('rushing_yards') or 0
                        avg = yds / att if att > 0 else 0
                        td = p.get('rushing_tds') or 0
                        lng = p.get('rushing_long') or 0
                        lines.append(f"| {p.get('player_name', 'Unknown')} | {att} | {yds} | {avg:.1f} | {td} | {lng} |")
                    lines.append("")

                # Receiving
                receivers = self._get_receivers(stats)
                if receivers:
                    lines.append("### Receiving")
                    lines.append("| Player | REC | YDS | AVG | TD | TGT |")
                    lines.append("|--------|-----|-----|-----|----|----|")
                    for p in receivers:
                        rec = p.get('receptions') or 0
                        yds = p.get('receiving_yards') or 0
                        avg = yds / rec if rec > 0 else 0
                        td = p.get('receiving_tds') or 0
                        tgt = p.get('targets') or 0
                        lines.append(f"| {p.get('player_name', 'Unknown')} | {rec} | {yds} | {avg:.1f} | {td} | {tgt} |")
                    lines.append("")

                # Defense
                defenders = self._get_defenders(stats)
                if defenders:
                    lines.append("### Defense")
                    lines.append("| Player | TKL | SACK | INT | PD | FF |")
                    lines.append("|--------|-----|------|-----|----|----|")
                    for p in defenders:
                        tkl = p.get('tackles_total') or 0
                        sck = p.get('sacks') or 0
                        ints = p.get('interceptions') or 0
                        pd = p.get('passes_defended') or 0
                        ff = p.get('forced_fumbles') or 0
                        lines.append(f"| {p.get('player_name', 'Unknown')} | {tkl} | {sck:.1f} | {ints} | {pd} | {ff} |")
                    lines.append("")

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            QMessageBox.information(self, "Export Successful", f"Box score exported to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export box score:\n{str(e)}")

    def _export_json(self):
        """Export box score as JSON file."""
        # Generate default filename
        default_name = f"boxscore_{self._game_id}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Box Score as JSON",
            default_name,
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            away_agg = self._aggregate_team_stats(self._away_stats)
            home_agg = self._aggregate_team_stats(self._home_stats)

            # Build export data
            export_data = {
                "game_id": self._game_id,
                "away_team": {
                    "id": self._away_team.get('id'),
                    "name": self._away_team.get('name', 'Away'),
                    "abbr": self._away_team.get('abbr', 'AWAY'),
                    "score": self._away_score
                },
                "home_team": {
                    "id": self._home_team.get('id'),
                    "name": self._home_team.get('name', 'Home'),
                    "abbr": self._home_team.get('abbr', 'HOME'),
                    "score": self._home_score
                },
                "team_stats": {
                    "away": {
                        **away_agg,
                        "first_downs": (self._away_box_score or {}).get('first_downs', 0),
                        "time_of_possession": (self._away_box_score or {}).get('time_of_possession_str', 'N/A'),
                        "third_down_conv": (self._away_box_score or {}).get('third_down_conv', 0),
                        "third_down_att": (self._away_box_score or {}).get('third_down_att', 0),
                        "fourth_down_conv": (self._away_box_score or {}).get('fourth_down_conv', 0),
                        "fourth_down_att": (self._away_box_score or {}).get('fourth_down_att', 0),
                        "penalties": (self._away_box_score or {}).get('penalties', 0),
                        "penalty_yards": (self._away_box_score or {}).get('penalty_yards', 0),
                    },
                    "home": {
                        **home_agg,
                        "first_downs": (self._home_box_score or {}).get('first_downs', 0),
                        "time_of_possession": (self._home_box_score or {}).get('time_of_possession_str', 'N/A'),
                        "third_down_conv": (self._home_box_score or {}).get('third_down_conv', 0),
                        "third_down_att": (self._home_box_score or {}).get('third_down_att', 0),
                        "fourth_down_conv": (self._home_box_score or {}).get('fourth_down_conv', 0),
                        "fourth_down_att": (self._home_box_score or {}).get('fourth_down_att', 0),
                        "penalties": (self._home_box_score or {}).get('penalties', 0),
                        "penalty_yards": (self._home_box_score or {}).get('penalty_yards', 0),
                    }
                },
                "player_stats": {
                    "away": self._away_stats,
                    "home": self._home_stats
                }
            }

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)

            QMessageBox.information(self, "Export Successful", f"Box score exported to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export box score:\n{str(e)}")
