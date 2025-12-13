"""
MediaCoverageView - ESPN-style "Today's Coverage" view for current stage content.

Part of Milestone 12: Media Coverage.

Single-page design showing what's happening NOW in the dynasty:
- Scoreboard Ticker (games if applicable)
- Breaking News Banner
- Current Stage Badge
- Headlines for current stage
- Power Rankings (regular season) or Stage-specific content
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush, QFont

from game_cycle_ui.theme import (
    UITheme,
    SENTIMENT_COLORS,
    TIER_COLORS,
    MOVEMENT_COLORS,
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_BORDER,
)
from constants.team_abbreviations import get_team_abbreviation
from game_cycle_ui.widgets.scoreboard_ticker_widget import ScoreboardTickerWidget
from game_cycle_ui.widgets.breaking_news_widget import BreakingNewsBanner
from game_cycle_ui.widgets.espn_headline_widget import ESPNHeadlinesGridWidget
from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget


logger = logging.getLogger(__name__)


# Stage display names and colors
STAGE_DISPLAY = {
    # Regular Season
    "REGULAR_WEEK_1": ("REGULAR SEASON", "WEEK 1", "#1976D2"),
    "REGULAR_WEEK_2": ("REGULAR SEASON", "WEEK 2", "#1976D2"),
    "REGULAR_WEEK_3": ("REGULAR SEASON", "WEEK 3", "#1976D2"),
    "REGULAR_WEEK_4": ("REGULAR SEASON", "WEEK 4", "#1976D2"),
    "REGULAR_WEEK_5": ("REGULAR SEASON", "WEEK 5", "#1976D2"),
    "REGULAR_WEEK_6": ("REGULAR SEASON", "WEEK 6", "#1976D2"),
    "REGULAR_WEEK_7": ("REGULAR SEASON", "WEEK 7", "#1976D2"),
    "REGULAR_WEEK_8": ("REGULAR SEASON", "WEEK 8", "#1976D2"),
    "REGULAR_WEEK_9": ("REGULAR SEASON", "WEEK 9", "#1976D2"),
    "REGULAR_WEEK_10": ("REGULAR SEASON", "WEEK 10", "#1976D2"),
    "REGULAR_WEEK_11": ("REGULAR SEASON", "WEEK 11", "#1976D2"),
    "REGULAR_WEEK_12": ("REGULAR SEASON", "WEEK 12", "#1976D2"),
    "REGULAR_WEEK_13": ("REGULAR SEASON", "WEEK 13", "#1976D2"),
    "REGULAR_WEEK_14": ("REGULAR SEASON", "WEEK 14", "#1976D2"),
    "REGULAR_WEEK_15": ("REGULAR SEASON", "WEEK 15", "#1976D2"),
    "REGULAR_WEEK_16": ("REGULAR SEASON", "WEEK 16", "#1976D2"),
    "REGULAR_WEEK_17": ("REGULAR SEASON", "WEEK 17", "#1976D2"),
    "REGULAR_WEEK_18": ("REGULAR SEASON", "WEEK 18", "#1976D2"),
    # Playoffs
    "WILD_CARD": ("PLAYOFFS", "WILD CARD", ESPN_RED),
    "DIVISIONAL": ("PLAYOFFS", "DIVISIONAL", ESPN_RED),
    "CONFERENCE_CHAMPIONSHIP": ("PLAYOFFS", "CONFERENCE CHAMPIONSHIP", ESPN_RED),
    "SUPER_BOWL": ("PLAYOFFS", "SUPER BOWL", "#FFD700"),
    # Offseason
    "OFFSEASON_HONORS": ("OFFSEASON", "AWARDS CEREMONY", "#7B1FA2"),
    "OFFSEASON_FRANCHISE_TAG": ("OFFSEASON", "FRANCHISE TAG", "#F57C00"),
    "OFFSEASON_RESIGNING": ("OFFSEASON", "RE-SIGNING PERIOD", "#F57C00"),
    "OFFSEASON_FREE_AGENCY": ("OFFSEASON", "FREE AGENCY", "#2E7D32"),
    "OFFSEASON_TRADING": ("OFFSEASON", "TRADE PERIOD", "#F57C00"),
    "OFFSEASON_DRAFT": ("OFFSEASON", "NFL DRAFT", "#1976D2"),
    "OFFSEASON_ROSTER_CUTS": ("OFFSEASON", "ROSTER CUTS", "#C62828"),
    "OFFSEASON_WAIVER_WIRE": ("OFFSEASON", "WAIVER WIRE", "#F57C00"),
    "OFFSEASON_TRAINING_CAMP": ("OFFSEASON", "TRAINING CAMP", "#2E7D32"),
    "OFFSEASON_PRESEASON": ("PRESEASON", "EXHIBITION GAMES", "#666666"),
    # Preseason
    "PRESEASON_WEEK_1": ("PRESEASON", "WEEK 1", "#666666"),
    "PRESEASON_WEEK_2": ("PRESEASON", "WEEK 2", "#666666"),
    "PRESEASON_WEEK_3": ("PRESEASON", "WEEK 3", "#666666"),
}


class MediaCoverageView(QWidget):
    """
    ESPN-style "Today's Coverage" view showing current stage content.

    Features:
    - Scoreboard ticker at top (shows games if applicable)
    - Breaking news banner for high-priority items
    - Current stage badge (Regular Season Week 12, Playoffs, Offseason, etc.)
    - Headlines for current stage
    - Power Rankings section (during regular season/playoffs)
    - Single scrollable page - no tabs or week selection

    Signals:
        refresh_requested: Emitted when refresh button is clicked
    """

    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the media coverage view."""
        super().__init__(parent)

        # Context (set by main window)
        self._dynasty_id: str = ""
        self._db_path: str = ""
        self._season: int = 2025
        self._current_stage: str = "REGULAR_WEEK_1"
        self._current_week: int = 1

        # Data storage
        self._headlines: List[Dict[str, Any]] = []
        self._rankings: List[Dict[str, Any]] = []
        self._games: List[Dict[str, Any]] = []

        # Team name lookup
        self._team_names: Dict[int, str] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Build the ESPN-style single-page view UI."""
        # Dark background for ESPN look
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {ESPN_DARK_BG};
                color: {ESPN_TEXT_PRIMARY};
            }}
            QScrollArea {{
                background-color: {ESPN_DARK_BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {ESPN_CARD_BG};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444444;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {ESPN_RED};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # =====================================================================
        # SCOREBOARD TICKER (Top bar with game scores)
        # =====================================================================
        self._scoreboard = ScoreboardTickerWidget()
        self._scoreboard.game_clicked.connect(self._on_game_clicked)
        layout.addWidget(self._scoreboard)

        # =====================================================================
        # BREAKING NEWS BANNER
        # =====================================================================
        self._breaking_news = BreakingNewsBanner()
        self._breaking_news.clicked.connect(self._on_headline_clicked)
        layout.addWidget(self._breaking_news)

        # =====================================================================
        # HEADER ROW (Title + Stage Badge + Refresh)
        # =====================================================================
        header_container = QWidget()
        header_container.setStyleSheet(f"""
            background-color: {ESPN_DARK_BG};
            border-bottom: 1px solid {ESPN_BORDER};
        """)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(16)

        # ESPN-style logo area
        logo_label = QLabel("NFL COVERAGE")
        logo_label.setStyleSheet(f"""
            color: {ESPN_RED};
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        # Stage badge - shows current phase (no week number)
        self._stage_badge = QLabel("REGULAR SEASON")
        self._stage_badge.setStyleSheet(f"""
            background-color: #1976D2;
            color: {ESPN_TEXT_PRIMARY};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 6px 12px;
            border-radius: 4px;
        """)
        header_layout.addWidget(self._stage_badge)

        # Refresh button
        self._refresh_btn = QPushButton("REFRESH")
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_RED};
                color: {ESPN_TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: #990000;
            }}
            QPushButton:pressed {{
                background-color: #660000;
            }}
        """)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self._refresh_btn)

        layout.addWidget(header_container)

        # =====================================================================
        # MAIN CONTENT SCROLL AREA
        # =====================================================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        self._content_layout = QVBoxLayout(content_widget)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(24)

        # HEADLINES SECTION
        headlines_header = self._create_section_header("TODAY'S HEADLINES")
        self._content_layout.addWidget(headlines_header)

        self._headlines_grid = ESPNHeadlinesGridWidget()
        self._headlines_grid.headline_clicked.connect(self._on_headline_clicked)
        self._content_layout.addWidget(self._headlines_grid)

        # POWER RANKINGS SECTION (collapsible, shown during regular season)
        self._rankings_section = QWidget()
        rankings_layout = QVBoxLayout(self._rankings_section)
        rankings_layout.setContentsMargins(0, 0, 0, 0)
        rankings_layout.setSpacing(8)

        rankings_header = self._create_section_header("POWER RANKINGS")
        rankings_layout.addWidget(rankings_header)

        self._rankings_widget = PowerRankingsWidget()
        self._rankings_widget.team_selected.connect(self._on_team_selected)
        rankings_layout.addWidget(self._rankings_widget)

        self._content_layout.addWidget(self._rankings_section)

        # Empty state label (shown when no content)
        self._empty_label = QLabel("Coverage begins when games are simulated.")
        self._empty_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: 14px;
            padding: 40px;
        """)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)
        self._content_layout.addWidget(self._empty_label)

        self._content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        # =====================================================================
        # STATUS BAR
        # =====================================================================
        status_container = QWidget()
        status_container.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-top: 1px solid {ESPN_BORDER};
        """)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(16, 8, 16, 8)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: 11px;
        """)
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()

        layout.addWidget(status_container)

    def _create_section_header(self, title: str) -> QWidget:
        """Create an ESPN-styled section header."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border-left: 4px solid {ESPN_RED};
                padding: 8px 12px;
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(title)
        label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(label)
        layout.addStretch()

        return header

    # =========================================================================
    # CONTEXT MANAGEMENT
    # =========================================================================

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set the dynasty context for data loading.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to database
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._load_team_names()
        self.refresh_data()

    def set_current_stage(self, stage: str, week: int = 1):
        """
        Set the current stage for display.

        Args:
            stage: Stage name (e.g., "REGULAR_WEEK_12", "WILD_CARD", "OFFSEASON_DRAFT")
            week: Week number (for regular season stages)
        """
        self._current_stage = stage
        self._current_week = week
        self._update_stage_badge()
        self.refresh_data()

    def set_current_week(self, week: int):
        """
        Set the current week (for backwards compatibility).

        Args:
            week: Week number (1-18)
        """
        self._current_week = week
        self._current_stage = f"REGULAR_WEEK_{week}"
        self._update_stage_badge()
        self.refresh_data()

    def _update_stage_badge(self):
        """Update the stage badge display based on current stage."""
        stage_info = STAGE_DISPLAY.get(self._current_stage)
        if stage_info:
            phase, _, color = stage_info  # Ignore period (week name) - not shown in UI
            self._stage_badge.setText(phase)
            self._stage_badge.setStyleSheet(f"""
                background-color: {color};
                color: {ESPN_TEXT_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 6px 12px;
                border-radius: 4px;
            """)
        else:
            # Fallback for unknown stages
            self._stage_badge.setText("NFL")

        # Show/hide sections based on stage type
        is_regular_or_playoffs = (
            self._current_stage.startswith("REGULAR_") or
            self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL")
        )
        self._rankings_section.setVisible(is_regular_or_playoffs)

    # =========================================================================
    # DATA LOADING
    # =========================================================================

    def refresh_data(self):
        """Load all media coverage data for current stage."""
        if not self._dynasty_id or not self._db_path:
            logger.debug(f"refresh_data() SKIPPED - no context (dynasty={self._dynasty_id}, db_path={self._db_path})")
            return

        logger.debug(f"refresh_data() START - dynasty={self._dynasty_id}, season={self._season}, stage={self._current_stage}")
        self._status_label.setText("Loading...")

        try:
            self._load_games()
            self._load_headlines()
            self._load_rankings()

            logger.debug(f"Data loaded: {len(self._headlines)} headlines, {len(self._rankings)} rankings, {len(self._games)} games")

            self._update_empty_state()

            logger.debug(f"Visibility: headlines_grid={self._headlines_grid.isVisible()}, empty_label={self._empty_label.isVisible()}")

            self._status_label.setText(f"Coverage loaded")
        except Exception as e:
            logger.error(f"Failed to load media coverage: {e}", exc_info=True)
            self._status_label.setText(f"Error: {e}")

    def _load_team_names(self):
        """Load team name lookup from database or JSON fallback."""
        try:
            from src.game_cycle.database.connection import GameCycleDatabase

            db = GameCycleDatabase(self._db_path)
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT team_id, name FROM teams
            """)

            self._team_names = {row[0]: row[1] for row in cursor.fetchall()}
            logger.debug(f"Loaded {len(self._team_names)} team names from database")

            # Fallback to JSON if database table is empty
            if not self._team_names:
                self._load_team_names_from_json()
        except Exception as e:
            logger.warning(f"Failed to load team names from database: {e}")
            self._load_team_names_from_json()

    def _load_team_names_from_json(self):
        """Load team names from JSON file as fallback."""
        try:
            import json
            import os

            json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "src", "data", "teams.json"
            )

            with open(json_path, 'r') as f:
                data = json.load(f)

            teams_data = data.get('teams', {})
            self._team_names = {
                int(team_id): team_info.get('full_name', f"Team {team_id}")
                for team_id, team_info in teams_data.items()
            }
            logger.debug(f"Loaded {len(self._team_names)} team names from JSON")
        except Exception as e:
            logger.warning(f"Failed to load team names from JSON: {e}")
            self._team_names = {}

    def _load_games(self):
        """Load game scores for the scoreboard ticker."""
        try:
            from src.game_cycle.database.connection import GameCycleDatabase
            from src.game_cycle.database.schedule_api import ScheduleAPI

            db = GameCycleDatabase(self._db_path)
            api = ScheduleAPI(db)

            # Determine week based on stage
            week = self._get_display_week()

            # DEBUG: Log query parameters
            logger.info(
                f"[MediaCoverage] Loading games: week={week}, stage={self._current_stage}"
            )

            # Get games for this week/round
            if self._current_stage.startswith("REGULAR_"):
                games = api.get_games_for_week(week)
            elif self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"):
                # Playoff games - map stage to round_name format
                round_map = {
                    "WILD_CARD": "wild_card",
                    "DIVISIONAL": "divisional",
                    "CONFERENCE_CHAMPIONSHIP": "conference",
                    "SUPER_BOWL": "super_bowl",
                }
                round_name = round_map.get(self._current_stage, self._current_stage.lower())
                games = api.get_playoff_games(round_name)
            else:
                # Offseason - no games to show
                games = []

            # DEBUG: Log results
            logger.info(f"[MediaCoverage] Loaded {len(games)} games")

            self._games = []
            for game in games:
                # ScheduledGame is a dataclass with properties, not a dict
                home_name = self._team_names.get(game.home_team_id, "")
                away_name = self._team_names.get(game.away_team_id, "")
                home_abbr = get_team_abbreviation(home_name) if home_name else f"T{game.home_team_id}"
                away_abbr = get_team_abbreviation(away_name) if away_name else f"T{game.away_team_id}"

                self._games.append({
                    "game_id": game.id,
                    "home_abbr": home_abbr,
                    "away_abbr": away_abbr,
                    "home_score": game.home_score or 0,
                    "away_score": game.away_score or 0,
                    "is_final": game.is_played,
                    "status": "FINAL" if game.is_played else "SCHEDULED",
                })

            self._scoreboard.set_games(self._games)
            # Hide ticker if no games
            self._scoreboard.setVisible(len(self._games) > 0)

        except Exception as e:
            logger.error(f"Failed to load games for ticker: {e}", exc_info=True)
            self._games = []
            self._scoreboard.set_games([])
            self._scoreboard.setVisible(False)

    def _get_current_week_from_stage(self) -> int:
        """Extract week number from current stage name.

        Centralizes the stage name parsing logic to avoid duplication.

        Returns:
            Week number (1-18) for regular season stages, 0 otherwise.
        """
        if self._current_stage.startswith("REGULAR_WEEK_"):
            try:
                return int(self._current_stage.split("_")[-1])
            except ValueError:
                return self._current_week
        return 0

    def _is_regular_season(self) -> bool:
        """Check if current stage is a regular season week."""
        return self._current_stage.startswith("REGULAR_WEEK_")

    def _is_playoffs(self) -> bool:
        """Check if current stage is a playoff round."""
        return self._current_stage in (
            "WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"
        )

    def _get_display_week(self) -> int:
        """Get week number for media content (last completed week).

        After simulating Week N, the stage advances to REGULAR_WEEK_{N+1}.
        Headlines are stored for Week N (the completed week), so we need to
        query for the previous week to show content for completed games.

        For offseason/playoffs, query the database for the most recent week
        with headlines to show the latest content.

        Returns:
            The week number of the most recently completed games (0 if none).
        """
        if self._is_regular_season():
            current_week = self._get_current_week_from_stage()
            # Headlines are for completed games (previous week)
            # At Week 1, no games have been played yet - return 0
            return max(0, current_week - 1)

        # For offseason/playoffs, get the most recent week with headlines
        # This ensures we show the latest content (e.g., Week 18 + awards)
        try:
            from src.game_cycle.database.connection import GameCycleDatabase

            gc_db = GameCycleDatabase(self._db_path)
            try:
                row = gc_db.query_one(
                    """SELECT MAX(week) FROM media_headlines
                       WHERE dynasty_id = ? AND season = ?""",
                    (self._dynasty_id, self._season)
                )
                if row and row[0] is not None:
                    return row[0]
            finally:
                gc_db.close()
        except Exception as e:
            logger.warning(f"Could not get latest headline week: {e}")

        return self._current_week

    def _load_headlines(self):
        """Load headlines for the current stage."""
        db = None
        try:
            from src.game_cycle.database.connection import GameCycleDatabase
            from src.game_cycle.database.media_coverage_api import MediaCoverageAPI

            db = GameCycleDatabase(self._db_path)
            api = MediaCoverageAPI(db)

            # Regular season: use timing-aware method
            # Shows RECAPs from previous week + PREVIEWs for current week
            if self._is_regular_season():
                current_week = self._get_current_week_from_stage()

                if current_week == 0:
                    logger.debug("_load_headlines: Week 0 - no games simulated")
                    self._headlines = []
                    self._populate_headlines()
                    return

                logger.debug(f"_load_headlines: Regular season, current_week={current_week}")
                headlines = api.get_headlines_for_display(
                    self._dynasty_id, self._season, current_week, limit=20
                )
            else:
                # Playoffs/offseason: use existing behavior (all headlines for max week)
                week = self._get_display_week()
                if week == 0:
                    self._headlines = []
                    self._populate_headlines()
                    return

                logger.debug(f"_load_headlines: Non-regular season, week={week}")
                headlines = api.get_top_headlines(
                    self._dynasty_id, self._season, week, limit=20
                )

            logger.debug(f"_load_headlines: API returned {len(headlines)} headlines")

            self._headlines = [self._headline_to_dict(h) for h in headlines]
            self._populate_headlines()

        except Exception as e:
            logger.error(f"Failed to load headlines: {e}", exc_info=True)
            self._headlines = []
            self._populate_headlines()
        finally:
            if db is not None:
                db.close()

    def _headline_to_dict(self, headline) -> Dict[str, Any]:
        """Convert Headline dataclass to dictionary."""
        return {
            "id": headline.id,
            "headline": headline.headline,
            "subheadline": headline.subheadline,
            "body_text": headline.body_text,
            "sentiment": headline.sentiment,
            "priority": headline.priority,
            "headline_type": headline.headline_type,
            "team_ids": headline.team_ids,
            "player_ids": headline.player_ids,
        }

    def _load_rankings(self):
        """Load power rankings for regular season/playoffs."""
        # Only load rankings for regular season and playoffs
        if not (self._current_stage.startswith("REGULAR_") or
                self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL")):
            logger.info(f"[MediaCoverage] Skipping rankings for stage: {self._current_stage}")
            self._rankings = []
            self._populate_rankings()
            return

        week = self._get_display_week()

        # Week 0 means no games have been simulated yet
        if week == 0:
            logger.debug("[MediaCoverage] Week 0 - no rankings available yet")
            self._rankings = []
            self._populate_rankings()
            return

        try:
            from src.game_cycle.database.connection import GameCycleDatabase
            from src.game_cycle.database.media_coverage_api import MediaCoverageAPI

            db = GameCycleDatabase(self._db_path)
            api = MediaCoverageAPI(db)

            # DEBUG: Log query parameters
            logger.info(
                f"[MediaCoverage] Loading rankings: dynasty={self._dynasty_id}, "
                f"season={self._season}, week={week}, stage={self._current_stage}"
            )

            rankings = api.get_power_rankings(
                self._dynasty_id, self._season, week
            )

            # DEBUG: Log results
            logger.info(f"[MediaCoverage] Loaded {len(rankings)} rankings")

            self._rankings = [self._ranking_to_dict(r) for r in rankings]
            self._populate_rankings()

        except Exception as e:
            logger.error(f"Failed to load rankings: {e}", exc_info=True)
            self._rankings = []
            self._populate_rankings()

    def _ranking_to_dict(self, ranking) -> Dict[str, Any]:
        """Convert PowerRanking dataclass to dictionary."""
        team_name = getattr(ranking, 'team_name', None) or self._team_names.get(
            ranking.team_id, f"Team {ranking.team_id}"
        )
        return {
            "team_id": ranking.team_id,
            "team_name": team_name,
            "rank": ranking.rank,
            "previous_rank": ranking.previous_rank,
            "tier": ranking.tier,
            "blurb": ranking.blurb,
            "movement": ranking.movement,
        }

    def _update_empty_state(self):
        """Show/hide empty state based on content, with stage-appropriate message."""
        has_content = len(self._headlines) > 0 or len(self._rankings) > 0

        logger.debug(f"_update_empty_state: headlines={len(self._headlines)}, rankings={len(self._rankings)}, has_content={has_content}")

        self._empty_label.setVisible(not has_content)

        # Show the headlines grid if we have headlines
        # Note: Do NOT walk up parent chain and force visibility - this conflicts
        # with QTabWidget's tab visibility management and causes tab overlap bugs
        should_show_headlines = len(self._headlines) > 0
        self._headlines_grid.setVisible(should_show_headlines)

        logger.debug(f"_update_empty_state: headlines_grid.isVisible()={self._headlines_grid.isVisible()}")

        # Set stage-appropriate empty message
        if not has_content:
            if self._current_stage.startswith("REGULAR_"):
                self._empty_label.setText("Coverage begins when games are simulated.")
            elif self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"):
                self._empty_label.setText("Playoff coverage available after games are played.")
            elif self._current_stage.startswith("OFFSEASON_"):
                self._empty_label.setText("Check back during the regular season for game coverage.")
            else:
                self._empty_label.setText("No coverage available yet.")

    # =========================================================================
    # UI POPULATION
    # =========================================================================

    def _populate_headlines(self):
        """Populate the headlines section."""
        logger.debug(f"_populate_headlines: Passing {len(self._headlines)} headlines to grid")
        try:
            self._headlines_grid.set_headlines(self._headlines)
        except Exception as e:
            logger.error(f"_populate_headlines: EXCEPTION in set_headlines: {e}", exc_info=True)
        self._breaking_news.set_breaking_news(self._headlines)

    def _populate_rankings(self):
        """Populate the power rankings section."""
        if not self._rankings:
            self._rankings_widget.clear()
            return

        self._rankings_widget.set_rankings(self._rankings)

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_requested.emit()
        self.refresh_data()

    def _on_headline_clicked(self, headline_id: int):
        """Handle headline card click."""
        headline_data = next(
            (h for h in self._headlines if h.get("id") == headline_id),
            None
        )
        if headline_data:
            self._show_article_detail(headline_data)

    def _on_game_clicked(self, game_id: str):
        """Handle game card click in ticker."""
        logger.debug(f"Game clicked: {game_id}")
        # Could open box score dialog

    def _on_team_selected(self, team_id: int):
        """Handle team selection in rankings."""
        logger.debug(f"Team selected: {team_id}")
        # Could filter headlines to show team-specific content

    def _show_article_detail(self, headline_data: Dict[str, Any]):
        """Show article detail dialog."""
        try:
            from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog

            dialog = ArticleDetailDialog(headline_data, parent=self)
            dialog.exec()
        except ImportError:
            from PySide6.QtWidgets import QMessageBox

            body = headline_data.get("body_text", "No article content available.")
            QMessageBox.information(
                self,
                headline_data.get("headline", "Article"),
                body or "No article content available."
            )
