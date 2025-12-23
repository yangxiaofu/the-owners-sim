"""
Team View - Dashboard showing user's team overview.

Split panel layout with:
- Left sidebar: Team identity, record, power ranking, coaching, stats, top performers
- Right main area: Tabbed content (Schedule, Games, News)

Game-centric focus for the user's controlled team.
"""

import json
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTabWidget, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.widgets.team_sidebar_widget import TeamSidebarWidget
from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
from game_cycle_ui.widgets.game_preview_widget import GamePreviewWidget
from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
from game_cycle_ui.widgets.roster_table_widget import RosterTableWidget
from game_cycle_ui.theme import (
    ESPN_THEME, TAB_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE, WARNING_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors
)


class TeamView(QWidget):
    """
    Team dashboard view displaying comprehensive team overview.

    Split panel layout:
    - Left (280px): TeamSidebarWidget with identity, record, stats
    - Right (expandable): Tabbed content (Schedule, Games, News)
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
        self.header_label.setFont(Typography.H4)
        self.header_label.setStyleSheet("color: white;")
        header_row.addWidget(self.header_label)

        header_row.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_row.addWidget(refresh_btn)

        main_layout.addLayout(header_row)

        # Tab widget
        self.content_tabs = QTabWidget()
        self.content_tabs.setStyleSheet(TAB_STYLE)

        # Tab 1: Schedule
        self._create_schedule_tab()

        # Tab 2: Players (Roster)
        self._create_players_tab()

        # Tab 3: Games (Recent Results)
        self._create_games_tab()

        # Tab 4: News
        self._create_news_tab()

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

    def _create_players_tab(self):
        """Create the Players tab with roster table."""
        players_container = QWidget()
        layout = QVBoxLayout(players_container)
        layout.setContentsMargins(0, 8, 0, 0)

        self.roster_widget = RosterTableWidget()
        # Connect double-click to open player detail dialog
        self.roster_widget.table.cellDoubleClicked.connect(self._on_roster_player_double_clicked)
        layout.addWidget(self.roster_widget)

        self.content_tabs.addTab(players_container, "Players")

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
        self.news_layout.setSpacing(0)  # No spacing - items have bottom borders
        self.news_layout.setContentsMargins(0, 0, 0, 0)
        self.news_layout.addStretch()

        scroll.setWidget(self.news_container)
        layout.addWidget(scroll)

        # Empty state
        self.news_empty_label = QLabel("No news yet")
        self.news_empty_label.setFont(Typography.SMALL)
        self.news_empty_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self.news_empty_label.setAlignment(Qt.AlignCenter)
        self.news_empty_label.hide()
        layout.addWidget(self.news_empty_label)

        self.content_tabs.addTab(news_container, "News")

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

        # Update roster widget with game season for age calculation
        if hasattr(self, 'roster_widget'):
            self.roster_widget.set_season(season)

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
        self._load_star_power()
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

    def _load_star_power(self):
        """Load team star power summary from popularity data."""
        if not self._db_path or not self._dynasty_id or not self._team_id:
            return

        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.popularity_api import PopularityAPI
            from database.player_roster_api import PlayerRosterAPI

            # Get current week (estimate from schedule)
            current_week = 1
            for game in self._schedule_data:
                if game.get('is_played'):
                    current_week = max(current_week, game.get('week', 1))

            # Get team roster
            roster_api = PlayerRosterAPI(self._db_path)
            try:
                roster = roster_api.get_team_roster(self._dynasty_id, self._team_id)
            except ValueError:
                # Roster not in database yet
                self.sidebar.set_star_power({
                    'transcendent_count': 0,
                    'star_count': 0,
                    'known_count': 0
                })
                return

            # Get popularity for each player
            db = GameCycleDatabase(self._db_path)
            popularity_api = PopularityAPI(db)

            tier_counts = {
                'transcendent': 0,
                'star': 0,
                'known': 0
            }
            top_player = None
            top_score = 0

            for player in roster:
                player_id = player.get('player_id')
                score = popularity_api.get_popularity_score(
                    self._dynasty_id, player_id, self._season, current_week
                )

                if score:
                    # Count by tier
                    if score.popularity_score >= 90:
                        tier_counts['transcendent'] += 1
                    elif score.popularity_score >= 75:
                        tier_counts['star'] += 1
                    elif score.popularity_score >= 50:
                        tier_counts['known'] += 1

                    # Track top player
                    if score.popularity_score > top_score:
                        top_score = score.popularity_score
                        first_name = player.get('first_name', '')
                        last_name = player.get('last_name', '')
                        top_player = f"{first_name} {last_name}".strip()

            # Update sidebar
            star_power_data = {
                'transcendent_count': tier_counts['transcendent'],
                'star_count': tier_counts['star'],
                'known_count': tier_counts['known'],
                'top_player_name': top_player,
                'top_player_score': int(top_score) if top_score > 0 else None
            }
            self.sidebar.set_star_power(star_power_data)

        except Exception as e:
            print(f"[TeamView] Error loading star power: {e}")
            # Set default state
            self.sidebar.set_star_power({
                'transcendent_count': 0,
                'star_count': 0,
                'known_count': 0
            })

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
                    'headline_type': h.headline_type,
                    'created_at': h.created_at
                }
                for h in headlines[:15]  # Show more items with compact design
            ]

            for headline_data in self._headlines:
                card = HeadlineCardWidget(headline_data=headline_data)
                card.clicked.connect(self._on_headline_clicked)
                self.news_layout.addWidget(card)

            self.news_layout.addStretch()

        except Exception as e:
            print(f"[TeamView] Error loading news: {e}")

    def _load_roster(self):
        """Load team roster with player attributes and season stats from database."""
        if not self._team_id:
            return

        try:
            # Load roster from database (where drafted/signed players exist)
            if self._db_path and self._dynasty_id:
                from database.player_roster_api import PlayerRosterAPI

                roster_api = PlayerRosterAPI(self._db_path)
                try:
                    db_roster = roster_api.get_team_roster(self._dynasty_id, self._team_id)

                    # Convert database rows to expected format
                    # Database returns positions/attributes as JSON strings
                    players = []
                    for row in db_roster:
                        player = dict(row) if not isinstance(row, dict) else row.copy()

                        # Parse JSON strings to Python objects
                        if isinstance(player.get('positions'), str):
                            try:
                                player['positions'] = json.loads(player['positions'])
                            except (json.JSONDecodeError, TypeError):
                                player['positions'] = []

                        if isinstance(player.get('attributes'), str):
                            try:
                                player['attributes'] = json.loads(player['attributes'])
                            except (json.JSONDecodeError, TypeError):
                                player['attributes'] = {}

                        players.append(player)

                    # Load season stats from database
                    season_stats = self._load_player_season_stats()

                    # Update roster widget
                    self.roster_widget.set_roster(players, season_stats)
                    return

                except ValueError as e:
                    # Roster not in database yet, fall back to JSON
                    print(f"[TeamView] Database roster not available: {e}")

            # Fallback: Load from JSON file (for initial setup or if DB not available)
            from pathlib import Path

            players_dir = Path(__file__).parent.parent.parent / "src" / "data" / "players"

            team_files = list(players_dir.glob(f"team_{self._team_id:02d}_*.json"))
            if not team_files:
                print(f"[TeamView] No player file found for team {self._team_id}")
                return

            with open(team_files[0]) as f:
                data = json.load(f)

            players_dict = data.get('players', {})
            players = list(players_dict.values())

            # Update roster widget (no stats from JSON)
            self.roster_widget.set_roster(players, {})

        except Exception as e:
            print(f"[TeamView] Error loading roster: {e}")

    def _load_player_season_stats(self) -> Dict[int, Dict]:
        """Load aggregated season stats for all players on the team."""
        try:
            from game_cycle.database.player_stats_api import PlayerSeasonStatsAPI

            api = PlayerSeasonStatsAPI(self._db_path)
            return api.get_team_player_stats(
                self._dynasty_id, self._team_id, self._season
            )

        except Exception as e:
            print(f"[TeamView] Error loading player stats: {e}")
            return {}

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

    def _on_roster_player_double_clicked(self, row: int, column: int):
        """Handle roster table double-click - open player detail dialog."""
        # Get player data from the name item's UserRole
        name_item = self.roster_widget.table.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        player_data = name_item.data(Qt.UserRole + 1)
        player_name = name_item.text()

        if not player_id or not player_data:
            return

        # Check if required context is available
        if not self._dynasty_id or not self._db_path:
            return

        # Add team_id to player_data for the dialog
        player_data['team_id'] = self._team_id

        # Get team name
        team_name = self._team_data.get('name', '') or self._team_names.get(self._team_id, '')

        from game_cycle_ui.dialogs.player_detail_dialog import PlayerDetailDialog
        dialog = PlayerDetailDialog(
            player_id=player_id,
            player_name=player_name,
            player_data=player_data,
            dynasty_id=self._dynasty_id,
            season=self._season,
            db_path=self._db_path,
            team_name=team_name,
            parent=self
        )
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
        self.roster_widget.clear()
        self.game_preview_widget.clear()
        self.header_label.setText("MY TEAM")
