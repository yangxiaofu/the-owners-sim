"""
Team View - Dashboard showing user's team overview.

Split panel layout with:
- Left sidebar: Team identity, record, power ranking, coaching, stats, top performers
- Right main area: Tabbed content (Schedule, Games, News, Roster)

Game-centric focus for the user's controlled team.
"""

import json
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from game_cycle_ui.widgets.team_sidebar_widget import TeamSidebarWidget
from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
from game_cycle_ui.widgets.game_preview_widget import GamePreviewWidget
from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
from game_cycle_ui.theme import TABLE_HEADER_STYLE, ESPN_THEME


class TeamView(QWidget):
    """
    Team dashboard view displaying comprehensive team overview.

    Split panel layout:
    - Left (280px): TeamSidebarWidget with identity, record, stats
    - Right (expandable): Tabbed content (Schedule, Games, News, Roster)
    """

    # Signals
    refresh_requested = Signal()
    game_selected = Signal(str)  # game_id for opening box score dialog

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: int = 2025
        self._team_id: Optional[int] = None
        self._team_data: Dict[str, Any] = {}

        # Cached data
        self._schedule_data: List[Dict] = []
        self._bye_week: Optional[int] = None
        self._team_names: Dict[int, str] = {}
        self._rivalry_cache: Dict[tuple, Any] = {}
        self._headlines: List[Dict] = []  # For headline click lookup

        self._setup_ui()

    def _setup_ui(self):
        """Build the split panel layout."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left sidebar (fixed width)
        self.sidebar = TeamSidebarWidget()
        layout.addWidget(self.sidebar)

        # Right main content area
        self._create_main_content(layout)

    def _create_main_content(self, parent_layout: QHBoxLayout):
        """Create the tabbed main content area."""
        main_frame = QFrame()
        main_frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['dark_bg']}; "
            "border-radius: 8px; }}"
        )

        main_layout = QVBoxLayout(main_frame)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Header with refresh button
        header_row = QHBoxLayout()

        self.header_label = QLabel("MY TEAM")
        self.header_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.header_label.setStyleSheet("color: white;")
        header_row.addWidget(self.header_label)

        header_row.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_row.addWidget(refresh_btn)

        main_layout.addLayout(header_row)

        # Tab widget
        self.content_tabs = QTabWidget()
        self.content_tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: transparent; }"
            "QTabBar::tab { background: #333; color: #888; padding: 8px 16px; "
            "border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }"
            "QTabBar::tab:selected { background: #444; color: white; }"
            "QTabBar::tab:hover { background: #3a3a3a; }"
        )

        # Tab 1: Schedule
        self._create_schedule_tab()

        # Tab 2: Games (Recent Results)
        self._create_games_tab()

        # Tab 3: News
        self._create_news_tab()

        # Tab 4: Roster (Top Players)
        self._create_roster_tab()

        main_layout.addWidget(self.content_tabs)
        parent_layout.addWidget(main_frame, 1)  # Stretch factor

    def _create_schedule_tab(self):
        """Create the Schedule tab with TeamScheduleWidget."""
        schedule_container = QWidget()
        layout = QVBoxLayout(schedule_container)
        layout.setContentsMargins(0, 8, 0, 0)

        self.schedule_widget = TeamScheduleWidget()
        self.schedule_widget.game_clicked.connect(self._on_schedule_game_clicked)
        layout.addWidget(self.schedule_widget)

        self.content_tabs.addTab(schedule_container, "Schedule")

    def _create_games_tab(self):
        """Create the Upcoming Games tab with game preview."""
        games_container = QWidget()
        layout = QVBoxLayout(games_container)
        layout.setContentsMargins(0, 8, 0, 0)

        self.game_preview_widget = GamePreviewWidget()
        layout.addWidget(self.game_preview_widget)

        self.content_tabs.addTab(games_container, "Upcoming")

    def _create_news_tab(self):
        """Create the News tab with team headlines."""
        news_container = QWidget()
        layout = QVBoxLayout(news_container)
        layout.setContentsMargins(0, 8, 0, 0)

        # Scroll area for headlines
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 8px; background: #1a1a1a; }"
            "QScrollBar::handle:vertical { background: #444; border-radius: 4px; }"
        )

        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setSpacing(8)
        self.news_layout.setContentsMargins(0, 0, 4, 0)
        self.news_layout.addStretch()

        scroll.setWidget(self.news_container)
        layout.addWidget(scroll)

        # Empty state
        self.news_empty_label = QLabel("No news yet")
        self.news_empty_label.setFont(QFont("Arial", 10))
        self.news_empty_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self.news_empty_label.setAlignment(Qt.AlignCenter)
        self.news_empty_label.hide()
        layout.addWidget(self.news_empty_label)

        self.content_tabs.addTab(news_container, "News")

    def _create_roster_tab(self):
        """Create the Roster tab with top players by position."""
        roster_container = QWidget()
        layout = QVBoxLayout(roster_container)
        layout.setContentsMargins(0, 8, 0, 0)

        # Top players table
        self.roster_table = QTableWidget()
        self.roster_table.setColumnCount(5)
        self.roster_table.setHorizontalHeaderLabels([
            "Pos", "Player", "Grade", "Key Stat", "Trend"
        ])

        # Configure header
        header = self.roster_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Pos
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Player
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Grade
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Key Stat
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Trend

        self.roster_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.roster_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.roster_table.setAlternatingRowColors(True)
        self.roster_table.verticalHeader().setVisible(False)

        layout.addWidget(self.roster_table)
        self.content_tabs.addTab(roster_container, "Roster")

    # =========================================================================
    # Public API
    # =========================================================================

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set dynasty context for database operations.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle database
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

    def set_user_team_id(self, team_id: int):
        """
        Set the user's team and load data.

        Args:
            team_id: User's team ID (1-32)
        """
        self._team_id = team_id
        self._load_team_data()
        self.refresh_data()

    def refresh_data(self):
        """Reload all dashboard data."""
        if not self._team_id or not self._dynasty_id:
            return

        self._load_standing()
        self._load_power_ranking()
        self._load_coaching_style()
        self._load_team_stats()
        self._load_top_performers()
        self._load_schedule()
        self._load_game_preview()
        self._load_news()
        self._load_roster()

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_team_data(self):
        """Load basic team data from JSON."""
        if not self._team_id:
            return

        try:
            from pathlib import Path
            teams_path = Path(__file__).parent.parent.parent / "src" / "data" / "teams.json"
            with open(teams_path) as f:
                teams_data = json.load(f)

            team_data = teams_data.get('teams', {}).get(str(self._team_id), {})
            self._team_data = team_data

            # Also build team names lookup
            for tid, tdata in teams_data.get('teams', {}).items():
                full_name = f"{tdata.get('city', '')} {tdata.get('nickname', '')}"
                self._team_names[int(tid)] = full_name.strip()

            # Update sidebar
            self.sidebar.set_team_data(self._team_id, team_data)

            # Update header
            city = team_data.get('city', '')
            nickname = team_data.get('nickname', '')
            self.header_label.setText(f"{city} {nickname}".upper())

        except Exception as e:
            print(f"[TeamView] Error loading team data: {e}")

    def _load_coaching_style(self):
        """Load coaching style from config."""
        if not self._team_id:
            return

        try:
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "src" / "config" / "team_coaching_styles.json"
            with open(config_path) as f:
                styles_data = json.load(f)

            team_style = styles_data.get(str(self._team_id), {})
            hc = team_style.get('head_coach', '').replace('_', ' ').title()
            oc = team_style.get('offensive_coordinator', '').replace('_', ' ').title()
            dc = team_style.get('defensive_coordinator', '').replace('_', ' ').title()

            self.sidebar.set_coaching_style(hc, oc, dc)

        except Exception as e:
            print(f"[TeamView] Error loading coaching style: {e}")

    def _load_standing(self):
        """Load team standing from database."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.standings_api import StandingsAPI

            db = GameCycleDatabase(self._db_path)
            api = StandingsAPI(db)
            standing = api.get_team_standing(
                self._dynasty_id, self._season, self._team_id
            )
            self.sidebar.set_standing(standing)

        except Exception as e:
            print(f"[TeamView] Error loading standing: {e}")

    def _load_power_ranking(self):
        """Load latest power ranking from database."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.media_coverage_api import MediaCoverageAPI

            db = GameCycleDatabase(self._db_path)
            api = MediaCoverageAPI(db)
            ranking = api.get_latest_team_ranking(
                self._dynasty_id, self._season, self._team_id
            )
            self.sidebar.set_power_ranking(ranking)

        except Exception as e:
            print(f"[TeamView] Error loading power ranking: {e}")

    def _load_team_stats(self):
        """Load team season stats from database."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.team_stats_api import TeamSeasonStatsAPI

            api = TeamSeasonStatsAPI(self._db_path)
            stats = api.get_team_season_stats(
                self._dynasty_id, self._team_id, self._season
            )
            self.sidebar.set_team_stats(stats)

        except Exception as e:
            print(f"[TeamView] Error loading team stats: {e}")

    def _load_top_performers(self):
        """Load top performers by position group with league rankings."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.analytics_api import AnalyticsAPI

            api = AnalyticsAPI(self._db_path)

            # Get all grades league-wide to calculate rankings
            all_grades = api.get_league_grades_from_game_grades(
                self._dynasty_id, self._season
            )

            # Get this team's grades
            team_grades = api.get_team_grades_from_game_grades(
                self._dynasty_id, self._team_id, self._season
            )

            # Position groups for display
            position_groups = {
                'QB': ['quarterback', 'qb'],
                'RB': ['running_back', 'halfback', 'rb', 'hb', 'fb'],
                'WR': ['wide_receiver', 'wr'],
                'DEF': ['linebacker', 'cornerback', 'safety', 'defensive_end',
                        'defensive_tackle', 'lb', 'cb', 'fs', 'ss', 'de', 'dt',
                        'edge', 'mlb', 'lolb', 'rolb', 'le', 're']
            }

            # Build league-wide rankings by position group
            league_rankings = {}
            for group_name, positions in position_groups.items():
                # Get all players in this position group league-wide
                group_players = []
                for grade in all_grades:
                    pos = grade.get('position', '').lower()
                    if pos in positions:
                        group_players.append(grade)

                # Sort by grade descending
                group_players.sort(key=lambda x: x.get('overall_grade', 0), reverse=True)

                # Assign ranks
                for rank, player in enumerate(group_players, 1):
                    player_id = player.get('player_id')
                    if player_id not in league_rankings:
                        league_rankings[player_id] = {}
                    league_rankings[player_id][group_name] = rank

            # Find best player on this team for each position group
            performers = []
            for group_name, positions in position_groups.items():
                best_grade = None
                best_player = None
                for grade in team_grades:
                    pos = grade.get('position', '').lower()
                    if pos in positions:
                        current_grade = grade.get('overall_grade', 0)
                        if best_grade is None or current_grade > best_grade:
                            best_grade = current_grade
                            best_player = grade

                if best_player:
                    player_id = best_player.get('player_id')
                    rank = league_rankings.get(player_id, {}).get(group_name, 99)
                    performers.append({
                        'position': group_name,
                        'name': best_player.get('player_name', f"Player {player_id}"),
                        'rank': rank,
                        'player_id': player_id
                    })

            self.sidebar.set_top_performers(performers)

        except Exception as e:
            print(f"[TeamView] Error loading top performers: {e}")

    def _load_schedule(self):
        """Load team schedule from games and events tables."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.bye_week_api import ByeWeekAPI

            db = GameCycleDatabase(self._db_path)
            bye_api = ByeWeekAPI(db)

            schedule = []
            completed_game_ids = set()

            # Step 1: Load completed games from games table
            for week in range(1, 19):
                rows = db.query_all(
                    """SELECT game_id, week, home_team_id, away_team_id,
                              home_score, away_score
                       FROM games
                       WHERE dynasty_id = ? AND season = ? AND week = ?
                         AND season_type = 'regular_season'
                         AND (home_team_id = ? OR away_team_id = ?)
                       ORDER BY game_id""",
                    (self._dynasty_id, self._season, week, self._team_id, self._team_id)
                )
                for row in rows:
                    completed_game_ids.add(row['game_id'])
                    schedule.append({
                        'game_id': row['game_id'],  # Store actual game_id from DB
                        'week': row['week'],
                        'home_team_id': row['home_team_id'],
                        'away_team_id': row['away_team_id'],
                        'home_score': row['home_score'],
                        'away_score': row['away_score'],
                        'is_played': True
                    })

            # Step 2: Load scheduled (unplayed) games from events table
            scheduled_rows = db.query_all(
                """SELECT event_id, game_id, data
                   FROM events
                   WHERE dynasty_id = ?
                     AND json_extract(data, '$.parameters.season') = ?
                     AND json_extract(data, '$.parameters.season_type') = 'regular_season'
                   ORDER BY json_extract(data, '$.parameters.week'), game_id""",
                (self._dynasty_id, self._season)
            )

            for row in scheduled_rows:
                game_id = row['game_id']
                if game_id in completed_game_ids:
                    continue

                try:
                    data = json.loads(row['data'])
                except (json.JSONDecodeError, TypeError):
                    continue

                params = data.get('parameters', {})
                week = params.get('week')
                home_team_id = params.get('home_team_id')
                away_team_id = params.get('away_team_id')

                if not week or week < 1 or week > 18:
                    continue

                # Only include games for this team
                if home_team_id != self._team_id and away_team_id != self._team_id:
                    continue

                schedule.append({
                    'week': week,
                    'home_team_id': home_team_id,
                    'away_team_id': away_team_id,
                    'home_score': None,
                    'away_score': None,
                    'is_played': False
                })

            # Sort by week
            schedule.sort(key=lambda x: x['week'])

            # Get bye week
            bye_week = bye_api.get_team_bye_week(
                self._dynasty_id, self._season, self._team_id
            )

            # Load rivalries
            try:
                from game_cycle.database.rivalry_api import RivalryAPI
                rivalry_api = RivalryAPI(db)
                rivalries = rivalry_api.get_all_rivalries(self._dynasty_id)
                for r in rivalries:
                    key = (min(r.team_a_id, r.team_b_id), max(r.team_a_id, r.team_b_id))
                    self._rivalry_cache[key] = r
            except Exception:
                pass

            self._schedule_data = schedule
            self._bye_week = bye_week

            # Update widget
            team_name = self._team_data.get('nickname', 'Team')
            self.schedule_widget.set_team_schedule(
                team_id=self._team_id,
                team_name=team_name,
                schedule=schedule,
                bye_week=bye_week,
                team_names=self._team_names,
                rivalry_cache=self._rivalry_cache
            )

        except Exception as e:
            print(f"[TeamView] Error loading schedule: {e}")

    def _load_game_preview(self):
        """Load game preview for next unplayed game."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            # Find next unplayed game from schedule data
            next_game = next(
                (g for g in self._schedule_data if not g.get('is_played')),
                None
            )

            if not next_game:
                self.game_preview_widget.clear()
                return

            week = next_game.get('week', 0)
            home_team_id = next_game.get('home_team_id')
            away_team_id = next_game.get('away_team_id')
            is_home = (home_team_id == self._team_id)
            opponent_id = away_team_id if is_home else home_team_id

            user_team_name = self._team_names.get(self._team_id, 'My Team')
            opponent_name = self._team_names.get(opponent_id, f'Team {opponent_id}')

            # Get team comparison data
            team_comparison = self._get_team_comparison(self._team_id, opponent_id)

            # Get player matchups
            player_matchups = self._get_player_matchups(self._team_id, opponent_id)

            # Update widget
            self.game_preview_widget.set_preview_data(
                week=week,
                user_team_name=user_team_name,
                opponent_name=opponent_name,
                is_home=is_home,
                team_comparison=team_comparison,
                player_matchups=player_matchups
            )

        except Exception as e:
            print(f"[TeamView] Error loading game preview: {e}")
            self.game_preview_widget.clear()

    def _get_team_comparison(self, user_team_id: int, opponent_id: int) -> Dict[str, Dict]:
        """Get team comparison stats for preview."""
        comparison = {'user': {}, 'opponent': {}}

        try:
            from game_cycle.database.team_stats_api import TeamSeasonStatsAPI

            api = TeamSeasonStatsAPI(self._db_path)

            # Get rankings for each stat category
            # Offensive stats: higher is better (ascending=False)
            pass_off_ranks = api.calculate_rankings(
                self._dynasty_id, self._season, 'passing_yards', ascending=False
            )
            rush_off_ranks = api.calculate_rankings(
                self._dynasty_id, self._season, 'rushing_yards', ascending=False
            )
            # Defensive stats: lower allowed is better (ascending=True)
            pass_def_ranks = api.calculate_rankings(
                self._dynasty_id, self._season, 'passing_yards_allowed', ascending=True
            )
            rush_def_ranks = api.calculate_rankings(
                self._dynasty_id, self._season, 'rushing_yards_allowed', ascending=True
            )

            # Build lookup dicts from rankings
            def ranks_to_dict(rankings):
                return {r.team_id: r.rank for r in rankings}

            pass_off_dict = ranks_to_dict(pass_off_ranks)
            rush_off_dict = ranks_to_dict(rush_off_ranks)
            pass_def_dict = ranks_to_dict(pass_def_ranks)
            rush_def_dict = ranks_to_dict(rush_def_ranks)

            # Apply rankings to both teams
            for team_id, target_dict in [(user_team_id, 'user'), (opponent_id, 'opponent')]:
                comparison[target_dict]['pass_off_rank'] = pass_off_dict.get(team_id, 0)
                comparison[target_dict]['rush_off_rank'] = rush_off_dict.get(team_id, 0)
                comparison[target_dict]['pass_def_rank'] = pass_def_dict.get(team_id, 0)
                comparison[target_dict]['rush_def_rank'] = rush_def_dict.get(team_id, 0)

            # Get stats for both teams for PPG
            user_stats = api.get_team_season_stats(
                self._dynasty_id, user_team_id, self._season
            )
            opp_stats = api.get_team_season_stats(
                self._dynasty_id, opponent_id, self._season
            )

            # Get PPG from stats
            if user_stats:
                comparison['user']['ppg'] = user_stats.points_per_game or 0
                comparison['user']['opp_ppg'] = user_stats.points_allowed_per_game or 0
            if opp_stats:
                comparison['opponent']['ppg'] = opp_stats.points_per_game or 0
                comparison['opponent']['opp_ppg'] = opp_stats.points_allowed_per_game or 0

            # Get records from standings
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.standings_api import StandingsAPI

            db = GameCycleDatabase(self._db_path)
            try:
                standings_api = StandingsAPI(db)

                user_standing = standings_api.get_team_standing(
                    self._dynasty_id, self._season, user_team_id
                )
                opp_standing = standings_api.get_team_standing(
                    self._dynasty_id, self._season, opponent_id
                )

                if user_standing:
                    comparison['user']['record'] = f"{user_standing.wins}-{user_standing.losses}"
                if opp_standing:
                    comparison['opponent']['record'] = f"{opp_standing.wins}-{opp_standing.losses}"
            finally:
                db.close()

            # Get power rankings
            from game_cycle.database.media_coverage_api import MediaCoverageAPI

            db = GameCycleDatabase(self._db_path)
            try:
                media_api = MediaCoverageAPI(db)

                user_ranking = media_api.get_latest_team_ranking(
                    self._dynasty_id, self._season, user_team_id
                )
                opp_ranking = media_api.get_latest_team_ranking(
                    self._dynasty_id, self._season, opponent_id
                )

                if user_ranking:
                    comparison['user']['power_rank'] = user_ranking.rank
                if opp_ranking:
                    comparison['opponent']['power_rank'] = opp_ranking.rank
            finally:
                db.close()

        except Exception as e:
            print(f"[TeamView] Error getting team comparison: {e}")

        return comparison

    def _get_player_matchups(self, user_team_id: int, opponent_id: int) -> List[Dict]:
        """Get key player matchups for preview (starters with most snaps)."""
        matchups = []

        try:
            from game_cycle.database.analytics_api import AnalyticsAPI

            api = AnalyticsAPI(self._db_path)

            # Get all grades league-wide
            all_grades = api.get_league_grades_from_game_grades(
                self._dynasty_id, self._season
            )

            # Position groups and mappings
            position_groups = {
                'QB': ['quarterback', 'qb'],
                'RB': ['running_back', 'halfback', 'rb', 'hb', 'fb'],
                'WR': ['wide_receiver', 'wr'],
                'TE': ['tight_end', 'te'],
                'DL': ['defensive_end', 'defensive_tackle', 'de', 'dt', 'le', 're', 'edge', 'nose_tackle', 'nt'],
                'LB': ['linebacker', 'lb', 'mlb', 'lolb', 'rolb', 'ilb', 'olb', 'middle_linebacker', 'outside_linebacker'],
                'DB': ['cornerback', 'safety', 'cb', 'fs', 'ss', 'free_safety', 'strong_safety', 'nickel', 'dime']
            }

            # Minimum snaps per game to qualify for rankings
            min_snaps_per_game = {
                'QB': 25,
                'RB': 8,
                'WR': 15,
                'TE': 12,
                'DL': 15,
                'LB': 15,
                'DB': 15
            }

            # Build rankings by position group (sorted by grade for ranking)
            for group_name, positions in position_groups.items():
                min_spg = min_snaps_per_game.get(group_name, 15)

                # Get all players in this position group
                group_players = []
                for grade in all_grades:
                    pos = grade.get('position', '').lower()
                    if pos in positions:
                        group_players.append(grade)

                # Filter to qualified players (meet minimum snaps per game)
                qualified_players = []
                for player in group_players:
                    games = player.get('games_graded', 1) or 1
                    snaps = player.get('total_snaps', 0) or 0
                    snaps_per_game = snaps / games
                    if snaps_per_game >= min_spg:
                        qualified_players.append(player)

                # Sort qualified players by grade descending to assign rankings
                qualified_players.sort(key=lambda x: x.get('overall_grade', 0), reverse=True)

                # Assign ranks only to qualified players
                player_ranks = {}
                for rank, player in enumerate(qualified_players, 1):
                    player_id = player.get('player_id')
                    player_ranks[player_id] = rank

                # Find starter (most snaps) for each team from ALL players
                user_players = [p for p in group_players if p.get('team_id') == user_team_id]
                opp_players = [p for p in group_players if p.get('team_id') == opponent_id]

                # Sort by snaps to find starter
                user_players.sort(key=lambda x: x.get('total_snaps', 0), reverse=True)
                opp_players.sort(key=lambda x: x.get('total_snaps', 0), reverse=True)

                user_starter = user_players[0] if user_players else None
                opp_starter = opp_players[0] if opp_players else None

                # Format player strings
                user_str = "--"
                opp_str = "--"

                if user_starter:
                    name = user_starter.get('player_name', 'Unknown')
                    # Shorten name: "John Smith" -> "J. Smith"
                    parts = name.split()
                    if len(parts) >= 2:
                        short_name = f"{parts[0][0]}. {parts[-1]}"
                    else:
                        short_name = name
                    rank = player_ranks.get(user_starter.get('player_id'))
                    if rank:
                        user_str = f"{short_name} (#{rank})"
                    else:
                        user_str = f"{short_name} (NQ)"  # Not qualified

                if opp_starter:
                    name = opp_starter.get('player_name', 'Unknown')
                    parts = name.split()
                    if len(parts) >= 2:
                        short_name = f"{parts[0][0]}. {parts[-1]}"
                    else:
                        short_name = name
                    rank = player_ranks.get(opp_starter.get('player_id'))
                    if rank:
                        opp_str = f"{short_name} (#{rank})"
                    else:
                        opp_str = f"{short_name} (NQ)"  # Not qualified

                matchups.append({
                    'position': group_name,
                    'user_player': user_str,
                    'opp_player': opp_str
                })

        except Exception as e:
            print(f"[TeamView] Error getting player matchups: {e}")

        return matchups

    def _load_news(self):
        """Load team news headlines."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.media_coverage_api import MediaCoverageAPI

            db = GameCycleDatabase(self._db_path)
            api = MediaCoverageAPI(db)

            # Get current week (estimate from schedule)
            current_week = 1
            for game in self._schedule_data:
                if game.get('is_played'):
                    current_week = max(current_week, game.get('week', 1))

            # Get headlines for team
            headlines = api.get_headlines_for_team(
                self._dynasty_id, self._season, current_week, self._team_id
            )

            # Clear existing headlines
            while self.news_layout.count() > 0:
                item = self.news_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if not headlines:
                self.news_empty_label.show()
                self.news_layout.addStretch()
                return

            self.news_empty_label.hide()

            # Store headlines for click lookup
            self._headlines = [
                {
                    'id': h.id,
                    'headline': h.headline,
                    'subheadline': h.subheadline,
                    'body_text': h.body_text,
                    'sentiment': h.sentiment,
                    'headline_type': h.headline_type
                }
                for h in headlines[:10]
            ]

            for headline_data in self._headlines:
                card = HeadlineCardWidget(headline_data=headline_data)
                card.clicked.connect(self._on_headline_clicked)
                self.news_layout.addWidget(card)

            self.news_layout.addStretch()

        except Exception as e:
            print(f"[TeamView] Error loading news: {e}")

    def _load_roster(self):
        """Load roster/top players table."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.analytics_api import AnalyticsAPI

            api = AnalyticsAPI(self._db_path)
            # Use get_team_grades_from_game_grades which includes player_name
            grades = api.get_team_grades_from_game_grades(
                self._dynasty_id, self._team_id, self._season
            )

            # Sort by grade and take top 15
            sorted_grades = sorted(
                grades, key=lambda g: g.get('overall_grade', 0), reverse=True
            )[:15]

            self.roster_table.setRowCount(len(sorted_grades))

            for row, grade in enumerate(sorted_grades):
                # Position
                pos = grade.get('position', '?')
                pos_item = QTableWidgetItem(pos[:3].upper() if pos else "?")
                pos_item.setTextAlignment(Qt.AlignCenter)
                self.roster_table.setItem(row, 0, pos_item)

                # Player name
                name = grade.get('player_name') or f"Player {grade.get('player_id')}"
                name_item = QTableWidgetItem(name)
                self.roster_table.setItem(row, 1, name_item)

                # Grade with color
                overall = grade.get('overall_grade', 0)
                grade_item = QTableWidgetItem(f"{overall:.1f}")
                grade_item.setTextAlignment(Qt.AlignCenter)
                if overall >= 85:
                    grade_item.setForeground(Qt.green)
                elif overall >= 70:
                    grade_item.setForeground(Qt.yellow)
                elif overall >= 60:
                    grade_item.setForeground(Qt.white)
                else:
                    grade_item.setForeground(Qt.red)
                self.roster_table.setItem(row, 2, grade_item)

                # Key stat - show snaps played
                snaps = grade.get('total_snaps', 0)
                stat_item = QTableWidgetItem(f"{snaps} snaps")
                stat_item.setTextAlignment(Qt.AlignCenter)
                self.roster_table.setItem(row, 3, stat_item)

                # Trend - show games graded
                games = grade.get('games_graded', 0)
                trend_item = QTableWidgetItem(f"{games}G")
                trend_item.setTextAlignment(Qt.AlignCenter)
                self.roster_table.setItem(row, 4, trend_item)

        except Exception as e:
            print(f"[TeamView] Error loading roster: {e}")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_data()
        self.refresh_requested.emit()

    def _on_schedule_game_clicked(self, week: int, home_team_id: int, away_team_id: int):
        """Handle schedule game click - show box score dialog."""
        # Find game from schedule data
        for game in self._schedule_data:
            if (game.get('week') == week and
                game.get('home_team_id') == home_team_id and
                game.get('away_team_id') == away_team_id and
                game.get('is_played')):

                # Get stored game_id from database
                game_id = game.get('game_id')
                if not game_id:
                    return  # No game_id stored

                # Import dialog
                from game_cycle_ui.dialogs.box_score_dialog import BoxScoreDialog

                # Build team info dicts
                home_team = {
                    'id': home_team_id,
                    'name': self._team_names.get(home_team_id, f'Team {home_team_id}'),
                    'abbr': self._team_names.get(home_team_id, 'TM')[:3].upper()
                }
                away_team = {
                    'id': away_team_id,
                    'name': self._team_names.get(away_team_id, f'Team {away_team_id}'),
                    'abbr': self._team_names.get(away_team_id, 'TM')[:3].upper()
                }

                # Show dialog
                dialog = BoxScoreDialog(
                    game_id=game_id,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=game.get('home_score', 0),
                    away_score=game.get('away_score', 0),
                    db_path=self._db_path,
                    dynasty_id=self._dynasty_id,
                    game_result=None,  # No cached play-by-play
                    parent=self
                )
                dialog.exec()
                break

    def _on_headline_clicked(self, headline_id: int):
        """Handle headline card click - show article detail dialog."""
        headline_data = next(
            (h for h in self._headlines if h.get("id") == headline_id),
            None
        )
        if headline_data:
            from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog
            dialog = ArticleDetailDialog(headline_data, parent=self)
            dialog.exec()

    def clear(self):
        """Clear all data."""
        self._team_id = None
        self._team_data = {}
        self._schedule_data = []
        self._bye_week = None
        self._headlines = []

        self.sidebar.clear()
        self.schedule_widget.clear()
        self.game_preview_widget.clear()
        self.roster_table.setRowCount(0)
        self.header_label.setText("MY TEAM")
