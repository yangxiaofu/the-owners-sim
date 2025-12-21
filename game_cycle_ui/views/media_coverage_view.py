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
    QTabWidget,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush, QFont

from game_cycle_ui.theme import (
    UITheme,
    Colors,
    FontSizes,
    TextColors,
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
from constants.position_abbreviations import get_position_abbreviation
from constants.team_abbreviations import get_team_abbreviation
from game_cycle_ui.widgets.scoreboard_ticker_widget import ScoreboardTickerWidget
from game_cycle_ui.widgets.breaking_news_widget import BreakingNewsBanner
from game_cycle_ui.widgets.espn_headline_widget import ESPNHeadlinesGridWidget
from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
from game_cycle_ui.widgets.compact_story_card import CompactStoryCardWidget
from game_cycle_ui.widgets.top_performers_widget import TopPerformersWidget
from game_cycle_ui.widgets.game_of_week_widget import GameOfWeekWidget
# from game_cycle_ui.widgets.standings_snapshot_widget import StandingsSnapshotWidget  # Removed
from game_cycle_ui.widgets.transaction_feed_widget import TransactionFeedWidget


logger = logging.getLogger(__name__)


# Team market sizes for Game of Week selection (from game_slot.py)
TEAM_MARKET_SIZE = {
    17: 20,  # Cowboys
    18: 18,  # Giants
    4: 17,   # Jets
    19: 16,  # Eagles
    21: 15,  # Bears
    31: 14,  # 49ers
    20: 13,  # Commanders
    32: 12,  # Seahawks
    1: 11,   # Bills
    23: 10,  # Packers
    30: 9,   # Rams
    2: 8,    # Dolphins
    3: 7,    # Patriots
    24: 7,   # Vikings
    5: 6,    # Ravens
    28: 6,   # Buccaneers
    25: 5,   # Falcons
    14: 5,   # Chiefs
    26: 4,   # Panthers
    27: 4,   # Saints
    6: 3,    # Bengals
    7: 3,    # Browns
    16: 3,   # Chargers
    13: 2,   # Broncos
    29: 2,   # Cardinals
    9: 1,    # Texans
    10: 1,   # Colts
    12: 1,   # Titans
    8: 1,    # Steelers
    22: 0,   # Lions
    15: 0,   # Raiders
    11: 0,   # Jaguars
}


# Stage display names and colors
STAGE_DISPLAY = {
    # Regular Season
    "REGULAR_WEEK_1": ("REGULAR SEASON", "WEEK 1", Colors.INFO),
    "REGULAR_WEEK_2": ("REGULAR SEASON", "WEEK 2", Colors.INFO),
    "REGULAR_WEEK_3": ("REGULAR SEASON", "WEEK 3", Colors.INFO),
    "REGULAR_WEEK_4": ("REGULAR SEASON", "WEEK 4", Colors.INFO),
    "REGULAR_WEEK_5": ("REGULAR SEASON", "WEEK 5", Colors.INFO),
    "REGULAR_WEEK_6": ("REGULAR SEASON", "WEEK 6", Colors.INFO),
    "REGULAR_WEEK_7": ("REGULAR SEASON", "WEEK 7", Colors.INFO),
    "REGULAR_WEEK_8": ("REGULAR SEASON", "WEEK 8", Colors.INFO),
    "REGULAR_WEEK_9": ("REGULAR SEASON", "WEEK 9", Colors.INFO),
    "REGULAR_WEEK_10": ("REGULAR SEASON", "WEEK 10", Colors.INFO),
    "REGULAR_WEEK_11": ("REGULAR SEASON", "WEEK 11", Colors.INFO),
    "REGULAR_WEEK_12": ("REGULAR SEASON", "WEEK 12", Colors.INFO),
    "REGULAR_WEEK_13": ("REGULAR SEASON", "WEEK 13", Colors.INFO),
    "REGULAR_WEEK_14": ("REGULAR SEASON", "WEEK 14", Colors.INFO),
    "REGULAR_WEEK_15": ("REGULAR SEASON", "WEEK 15", Colors.INFO),
    "REGULAR_WEEK_16": ("REGULAR SEASON", "WEEK 16", Colors.INFO),
    "REGULAR_WEEK_17": ("REGULAR SEASON", "WEEK 17", Colors.INFO),
    "REGULAR_WEEK_18": ("REGULAR SEASON", "WEEK 18", Colors.INFO),
    # Playoffs
    "WILD_CARD": ("PLAYOFFS", "WILD CARD", ESPN_RED),
    "DIVISIONAL": ("PLAYOFFS", "DIVISIONAL", ESPN_RED),
    "CONFERENCE_CHAMPIONSHIP": ("PLAYOFFS", "CONFERENCE CHAMPIONSHIP", ESPN_RED),
    "SUPER_BOWL": ("PLAYOFFS", "SUPER BOWL", "#FFD700"),
    # Offseason
    "OFFSEASON_HONORS": ("OFFSEASON", "AWARDS CEREMONY", "#7B1FA2"),
    "OFFSEASON_FRANCHISE_TAG": ("OFFSEASON", "FRANCHISE TAG", Colors.WARNING),
    "OFFSEASON_RESIGNING": ("OFFSEASON", "RE-SIGNING PERIOD", Colors.WARNING),
    "OFFSEASON_FREE_AGENCY": ("OFFSEASON", "FREE AGENCY", Colors.SUCCESS),
    "OFFSEASON_TRADING": ("OFFSEASON", "TRADE PERIOD", Colors.WARNING),
    "OFFSEASON_DRAFT": ("OFFSEASON", "NFL DRAFT", Colors.INFO),
    "OFFSEASON_TRAINING_CAMP": ("OFFSEASON", "TRAINING CAMP", Colors.SUCCESS),
    "OFFSEASON_PRESEASON_W1": ("PRESEASON", "WEEK 1 CUTS", Colors.WARNING),
    "OFFSEASON_PRESEASON_W2": ("PRESEASON", "WEEK 2 CUTS", Colors.WARNING),
    "OFFSEASON_PRESEASON_W3": ("PRESEASON", "FINAL CUTS", Colors.ERROR),
    "OFFSEASON_WAIVER_WIRE": ("OFFSEASON", "WAIVER WIRE", Colors.WARNING),
    # Preseason
    "PRESEASON_WEEK_1": ("PRESEASON", "WEEK 1", Colors.MUTED),
    "PRESEASON_WEEK_2": ("PRESEASON", "WEEK 2", Colors.MUTED),
    "PRESEASON_WEEK_3": ("PRESEASON", "WEEK 3", Colors.MUTED),
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
        self._is_historical_view: bool = False  # Track if viewing historical week vs current stage

        # Data storage
        self._headlines: List[Dict[str, Any]] = []
        self._rankings: List[Dict[str, Any]] = []
        self._games: List[Dict[str, Any]] = []

        # Team name lookup
        self._team_names: Dict[int, str] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Build the ESPN-style tabbed view UI."""
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
            QTabWidget::pane {{
                background-color: {ESPN_DARK_BG};
                border: 1px solid {ESPN_BORDER};
                border-top: none;
            }}
            QTabBar::tab {{
                background-color: {ESPN_CARD_BG};
                color: {ESPN_TEXT_SECONDARY};
                border: 1px solid {ESPN_BORDER};
                border-bottom: none;
                padding: 10px 20px;
                font-size: {FontSizes.BODY};
                font-weight: bold;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {ESPN_DARK_BG};
                color: {ESPN_RED};
                border-bottom: 2px solid {ESPN_RED};
            }}
            QTabBar::tab:hover {{
                background-color: #2a2a2a;
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
            font-size: {FontSizes.H2};
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        # Stage badge - shows current phase (no week number)
        self._stage_badge = QLabel("REGULAR SEASON")
        self._stage_badge.setStyleSheet(f"""
            background-color: {Colors.INFO};
            color: {ESPN_TEXT_PRIMARY};
            font-size: {FontSizes.CAPTION};
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
                font-size: {FontSizes.CAPTION};
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
        # TAB WIDGET (Main content area with 4 tabs)
        # =====================================================================
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._create_headlines_tab(), "Headlines")
        self._tab_widget.addTab(self._create_rankings_tab(), "Power Rankings")
        self._tab_widget.addTab(self._create_leaders_tab(), "League Leaders")
        self._tab_widget.addTab(self._create_transactions_tab(), "Transactions")
        layout.addWidget(self._tab_widget, 1)

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
            font-size: {FontSizes.CAPTION};
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
            font-size: {FontSizes.H5};
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(label)
        layout.addStretch()

        return header

    # =========================================================================
    # TAB CREATION METHODS
    # =========================================================================

    def _create_headlines_tab(self) -> QWidget:
        """Create the Headlines tab with two-column layout (60/40 split)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Two-column layout (60% left, 40% right)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)

        # =================================================================
        # LEFT COLUMN (60%) - Headlines
        # =================================================================
        left_column = QWidget()
        left_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Headlines section header
        headlines_header = self._create_section_header("TODAY'S HEADLINES")
        left_layout.addWidget(headlines_header)

        # Container for headline cards (keep existing ESPNHeadlinesGridWidget for now)
        # TODO: Replace with CompactStoryCardWidget instances when headline data is available
        self._headlines_grid = ESPNHeadlinesGridWidget()
        self._headlines_grid.headline_clicked.connect(self._on_headline_clicked)
        left_layout.addWidget(self._headlines_grid)

        # Empty state label (shown when no content)
        self._empty_label = QLabel("Coverage begins when games are simulated.")
        self._empty_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.H5};
            padding: 40px;
        """)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setVisible(False)
        left_layout.addWidget(self._empty_label)

        left_layout.addStretch()

        # =================================================================
        # RIGHT COLUMN (40%) - Stats & Context Widgets
        # =================================================================
        right_column = QWidget()
        right_column.setFixedWidth(400)  # Fixed width for right sidebar
        right_column.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Top Performers Widget (450px height, with weekly/season toggle)
        self._top_performers_widget = TopPerformersWidget()
        # self._top_performers_widget.mode_changed.connect(self._on_performers_mode_changed)
        right_layout.addWidget(self._top_performers_widget)

        # Game of the Week Widget (250px height)
        self._game_of_week_widget = GameOfWeekWidget()
        self._game_of_week_widget.game_clicked.connect(self._on_game_of_week_clicked)
        right_layout.addWidget(self._game_of_week_widget)

        # Standings removed per user request - use more space for Game of Week
        # self._standings_snapshot_widget = StandingsSnapshotWidget()
        # right_layout.addWidget(self._standings_snapshot_widget)

        right_layout.addStretch()

        # Add columns to main row
        columns_layout.addWidget(left_column, 60)  # 60% stretch factor
        columns_layout.addWidget(right_column, 0)   # 0 stretch (fixed width)

        main_layout.addLayout(columns_layout)

        scroll.setWidget(content_widget)
        return scroll

    def _create_rankings_tab(self) -> QWidget:
        """Create the Power Rankings tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        rankings_layout = QVBoxLayout(content_widget)
        rankings_layout.setContentsMargins(16, 16, 16, 16)
        rankings_layout.setSpacing(8)

        # Rankings section header
        rankings_header = self._create_section_header("POWER RANKINGS")
        rankings_layout.addWidget(rankings_header)

        # Power rankings widget
        self._rankings_widget = PowerRankingsWidget()
        self._rankings_widget.team_selected.connect(self._on_team_selected)
        rankings_layout.addWidget(self._rankings_widget)

        rankings_layout.addStretch()
        scroll.setWidget(content_widget)
        return scroll

    def _create_leaders_tab(self) -> QWidget:
        """Create the League Leaders tab (placeholder)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        leaders_layout = QVBoxLayout(content_widget)
        leaders_layout.setContentsMargins(16, 16, 16, 16)
        leaders_layout.setSpacing(24)

        # Placeholder label
        placeholder = QLabel("League Leaders - Coming Soon")
        placeholder.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.H4};
            padding: 40px;
        """)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        leaders_layout.addWidget(placeholder)

        leaders_layout.addStretch()
        scroll.setWidget(content_widget)
        return scroll

    def _create_transactions_tab(self) -> QWidget:
        """Create the Transactions tab with transaction feed."""
        # Create transaction feed widget
        self._transaction_feed_widget = TransactionFeedWidget()
        # self._transaction_feed_widget.transaction_clicked.connect(self._on_transaction_clicked)

        # Return the widget directly (it has its own scroll area)
        return self._transaction_feed_widget

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
        Set the current stage for display (not historical navigation).

        This method is called when the actual game stage advances (e.g., after
        simulating a week). It resets historical navigation mode to show the
        "last completed week" behavior.

        Args:
            stage: Stage name (e.g., "REGULAR_WEEK_12", "WILD_CARD", "OFFSEASON_DRAFT")
            week: Week number (for regular season stages)
        """
        self._is_historical_view = False  # Reset to current stage mode
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

    def navigate_to_week(self, week: int):
        """
        Navigate to a specific historical week for viewing.

        This is distinct from set_current_stage() - it enables historical
        navigation mode where the user can view past weeks' data without
        the "last completed week" offset.

        Args:
            week: Week number to navigate to (1-18 for regular season)
        """
        self._is_historical_view = True
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
                font-size: {FontSizes.CAPTION};
                font-weight: bold;
                letter-spacing: 1px;
                padding: 6px 12px;
                border-radius: 4px;
            """)
        else:
            # Fallback for unknown stages
            self._stage_badge.setText("NFL")

        # Show/hide Power Rankings tab based on stage type
        is_regular_or_playoffs = (
            self._current_stage.startswith("REGULAR_") or
            self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL")
        )
        # Enable/disable the Power Rankings tab (index 1)
        self._tab_widget.setTabEnabled(1, is_regular_or_playoffs)

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
            self._load_top_performers()
            self._load_game_of_week()

            logger.debug(f"Data loaded: {len(self._headlines)} headlines, {len(self._rankings)} rankings, {len(self._games)} games")

            self._update_empty_state()

            logger.debug(f"Visibility: headlines_grid={self._headlines_grid.isVisible()}, empty_label={self._empty_label.isVisible()}")

            self._status_label.setText(f"Coverage loaded")
        except Exception as e:
            logger.error(f"Failed to load media coverage: {e}", exc_info=True)
            self._status_label.setText(f"Error: {e}")

    def _load_team_names(self):
        """
        Load team name lookup using centralized team_utils.

        Uses in-memory caching to reduce I/O overhead.
        """
        try:
            from src.utils.team_utils import get_all_team_names

            # Use team_utils with caching enabled
            self._team_names = get_all_team_names(
                dynasty_id=self._dynasty_id,
                db_path=self._db_path,
                use_cache=True
            )
            logger.debug(f"Loaded {len(self._team_names)} team names from team_utils")

        except Exception as e:
            logger.warning(f"Failed to load team names: {e}")
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

    def _is_offseason(self) -> bool:
        """Check if current stage is an offseason stage."""
        if not self._current_stage:
            return False
        return self._current_stage.startswith("OFFSEASON_")

    def _get_display_week(self) -> int:
        """Get week number for media content.

        Handles two modes:
        1. Current stage mode: Show last completed week (week - 1)
           - After simulating Week N, stage advances to REGULAR_WEEK_{N+1}
           - Headlines stored for Week N, so query week - 1
        2. Historical navigation mode: Show exact week navigated to
           - User clicked prev/next week buttons to view historical data

        For offseason/playoffs, query the database for the most recent week
        with headlines to show the latest content.

        Returns:
            The week number to query (0 if none).
        """
        if self._is_regular_season():
            current_week = self._get_current_week_from_stage()

            if self._is_historical_view:
                # Historical navigation: show exact week user navigated to
                return current_week
            else:
                # Current stage mode: show last completed week
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
                # Playoffs/offseason: use rolling headlines across all weeks
                # This ensures headlines from previous stages persist and accumulate
                # During offseason, headlines are stored with previous season (the season that just ended)
                query_season = self._season - 1 if self._is_offseason() else self._season
                logger.debug(f"_load_headlines: Playoffs/offseason, using rolling headlines for season={query_season}")
                headlines = api.get_rolling_headlines(
                    self._dynasty_id, query_season, limit=50
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
            "game_id": getattr(headline, 'game_id', None),
            "metadata": getattr(headline, 'metadata', {}),
        }

    def _fetch_player_data_for_headline(self, headline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch player data (name, position, stats) for headline's star player.

        Uses PlayerStatsAPI for consistent database access.

        Args:
            headline: Headline dictionary

        Returns:
            Dict with keys: name, position, stats (or None if not available)
        """
        player_ids = headline.get("player_ids", [])
        game_id = headline.get("game_id")

        if not player_ids or not game_id:
            logger.debug(f"_fetch_player_data: No player_ids or game_id for headline {headline.get('id')}")
            return None

        # Use first player in list (should be star player)
        player_id = player_ids[0]

        try:
            from src.game_cycle.database.player_stats_api import PlayerSeasonStatsAPI

            # Determine season type based on current stage
            is_playoff = self._current_stage in (
                "WILD_CARD", "DIVISIONAL",
                "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"
            )
            season_type_filter = 'playoffs' if is_playoff else 'regular_season'

            # Use PlayerStatsAPI to fetch game stats
            api = PlayerSeasonStatsAPI(self._db_path)
            player_data = api.get_player_game_stats(
                dynasty_id=self._dynasty_id,
                game_id=game_id,
                player_id=player_id,
                season_type=season_type_filter
            )

            if not player_data:
                logger.debug(f"_fetch_player_data: No stats found for player {player_id} in game {game_id}")
                return None

            # API returns dict with 'name', 'position', 'stats'
            return player_data

        except Exception as e:
            logger.error(f"Failed to fetch player data: {e}", exc_info=True)
            return None

    def _load_rankings(self):
        """Load power rankings for regular season/playoffs."""
        # Only load rankings for regular season and playoffs
        if not (self._current_stage.startswith("REGULAR_") or
                self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL")):
            logger.info(f"[MediaCoverage] Skipping rankings for stage: {self._current_stage}")
            self._rankings = []
            self._populate_rankings()
            return

        # For playoffs, always use Week 18 (last regular season)
        # Power rankings freeze at end of regular season
        if self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"):
            week = 18  # Always use last regular season week
            logger.info(f"[MediaCoverage] Loading frozen Week 18 power rankings for playoff stage: {self._current_stage}")
        else:
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

    def _load_top_performers(self):
        """Load weekly and season top performers from database."""
        if not self._db_path or not self._dynasty_id:
            return

        try:
            from src.game_cycle.database.player_stats_api import PlayerSeasonStatsAPI

            api = PlayerSeasonStatsAPI(self._db_path)

            # Determine current week for weekly leaders
            week = self._get_display_week()

            # Determine if we're in playoffs
            is_playoff = self._current_stage in (
                "WILD_CARD", "DIVISIONAL",
                "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"
            )

            # Query weekly top performers
            # For playoffs: only show playoff week stats
            # For regular season: only show regular season stats
            season_type_filter = 'playoffs' if is_playoff else 'regular_season'

            weekly_performers = api.get_weekly_top_performers(
                dynasty_id=self._dynasty_id,
                season=self._season,
                week=week,
                limit=5,
                season_type=season_type_filter
            )

            # Query season top performers
            # Always include playoff stats for cumulative season view
            season_performers = api.get_season_top_performers(
                dynasty_id=self._dynasty_id,
                season=self._season,
                limit=5,
                include_playoffs=True
            )

            # Format for widget
            weekly_formatted = [
                self._format_player_for_widget(p) for p in weekly_performers
            ]
            season_formatted = [
                self._format_player_for_widget(p) for p in season_performers
            ]

            # Set context
            self._top_performers_widget.set_context(
                self._dynasty_id,
                self._db_path,
                self._season,
                week
            )

            # Populate widget
            self._top_performers_widget.set_weekly_leaders(weekly_formatted)
            self._top_performers_widget.set_season_leaders(season_formatted)

            logger.debug(f"Loaded {len(weekly_formatted)} weekly and {len(season_formatted)} season top performers")

        except Exception as e:
            logger.error(f"Failed to load top performers: {e}", exc_info=True)

    def _format_player_for_widget(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw player stats from API to TopPerformersWidget format.

        Args:
            player_data: Dict from PlayerSeasonStatsAPI with all stats

        Returns:
            {
                'position': str,
                'name': str,
                'team': str,  # Team abbreviation
                'stats': str,  # Position-specific highlight
                'rating': str,  # "Rating: X.X" or "FP: X.X"
            }
        """
        position_raw = player_data.get('position', 'UNK')
        position = get_position_abbreviation(position_raw) if position_raw != 'UNK' else 'UNK'
        name = player_data.get('player_name', 'Unknown')
        team_id = player_data.get('team_id')

        # Get team abbreviation
        team_abbr = self._get_team_abbreviation(team_id) if team_id else 'FA'

        # Build position-specific stats line
        stats_line = self._build_stats_line(player_data, position)

        # Build rating line
        if position == 'QB':
            passer_rating = player_data.get('passing_rating', 0)
            rating_line = f"Rating: {passer_rating:.1f}"
        else:
            fantasy_points = player_data.get('fantasy_points', 0)
            rating_line = f"FP: {fantasy_points:.1f}"

        return {
            'position': position,
            'name': name,
            'team': team_abbr,
            'stats': stats_line,
            'rating': rating_line,
        }

    def _build_stats_line(self, player_data: Dict[str, Any], position: str) -> str:
        """Build position-specific stats highlight string."""
        if position == 'QB':
            yds = player_data.get('passing_yards', 0)
            tds = player_data.get('passing_tds', 0)
            ints = player_data.get('passing_interceptions', 0)
            return f"{yds} YDS, {tds} TD, {ints} INT"

        elif position == 'RB':
            rush_yds = player_data.get('rushing_yards', 0)
            rush_tds = player_data.get('rushing_tds', 0)
            rec_yds = player_data.get('receiving_yards', 0)
            if rec_yds > 0:
                return f"{rush_yds} RUSH YDS, {rec_yds} REC YDS, {rush_tds} TD"
            return f"{rush_yds} YDS, {rush_tds} TD"

        elif position in ('WR', 'TE'):
            rec = player_data.get('receptions', 0)
            yds = player_data.get('receiving_yards', 0)
            tds = player_data.get('receiving_tds', 0)
            return f"{rec} REC, {yds} YDS, {tds} TD"

        elif position in ('CB', 'S', 'FS', 'SS', 'LB', 'MLB', 'OLB', 'LOLB', 'ROLB', 'DE', 'DT', 'LE', 'RE'):
            tackles = player_data.get('tackles_total', 0)
            sacks = player_data.get('sacks', 0)
            ints = player_data.get('interceptions', 0)
            if ints > 0:
                return f"{tackles} TKL, {ints} INT, {sacks:.1f} SK"
            return f"{tackles} TKL, {sacks:.1f} SK"

        else:
            # Generic fallback
            fp = player_data.get('fantasy_points', 0)
            return f"{fp:.1f} Fantasy Points"

    def _get_team_abbreviation(self, team_id: int) -> str:
        """Get 2-3 letter team abbreviation from team_id."""
        # Map team_id to abbreviations
        TEAM_ABBRS = {
            1: 'BUF', 2: 'MIA', 3: 'NE', 4: 'NYJ',
            5: 'BAL', 6: 'CIN', 7: 'CLE', 8: 'PIT',
            9: 'HOU', 10: 'IND', 11: 'JAX', 12: 'TEN',
            13: 'DEN', 14: 'KC', 15: 'LV', 16: 'LAC',
            17: 'DAL', 18: 'NYG', 19: 'PHI', 20: 'WAS',
            21: 'CHI', 22: 'DET', 23: 'GB', 24: 'MIN',
            25: 'ATL', 26: 'CAR', 27: 'NO', 28: 'TB',
            29: 'ARI', 30: 'LAR', 31: 'SF', 32: 'SEA',
        }
        return TEAM_ABBRS.get(team_id, 'UNK')

    # =========================================================================
    # GAME OF THE WEEK SELECTION
    # =========================================================================

    def _select_game_of_week(self, games):
        """
        Select the most appealing game using a combined weighted formula.

        Formula:
            appeal_score = (1.0 * rivalry) + (0.7 * market) +
                           (0.5 * competitiveness) + (0.3 * playoff_implications)

        Args:
            games: List of ScheduledGame objects (played games only)

        Returns:
            ScheduledGame with highest appeal score, or None if no games
        """
        if not games:
            return None

        # Filter to only played games with scores
        played_games = [g for g in games if g.is_played and g.home_score is not None]
        if not played_games:
            return None

        best_game = None
        best_score = -1

        for game in played_games:
            # Calculate each factor
            rivalry_score = self._calculate_rivalry_score(
                game.home_team_id, game.away_team_id
            )
            market_score = self._calculate_market_score(
                game.home_team_id, game.away_team_id
            )
            competitive_score = self._calculate_competitive_score(
                game.home_score, game.away_score
            )
            playoff_score = self._calculate_playoff_implications(
                game.week, game.home_team_id, game.away_team_id
            )

            # Weighted combination
            appeal_score = (
                (1.0 * rivalry_score) +
                (0.7 * market_score) +
                (0.5 * competitive_score) +
                (0.3 * playoff_score)
            )

            logger.debug(
                f"Game {game.id}: rivalry={rivalry_score:.2f}, "
                f"market={market_score:.2f}, competitive={competitive_score:.2f}, "
                f"playoff={playoff_score:.2f}, total={appeal_score:.2f}"
            )

            if appeal_score > best_score:
                best_score = appeal_score
                best_game = game

        logger.info(f"Selected Game of Week: {best_game.id} (appeal={best_score:.2f})")
        return best_game

    def _calculate_rivalry_score(self, team1_id: int, team2_id: int) -> float:
        """
        Calculate rivalry bonus (0.0 to 1.0).

        Returns:
            1.0 if division rivals
            0.8 if Super Bowl rematch
            0.6 if historic rivalry
            0.4 if custom rivalry
            0.0 if no rivalry
        """
        try:
            from src.game_cycle.database.rivalry_api import RivalryAPI
            from src.game_cycle.database.connection import GameCycleDatabase

            db = GameCycleDatabase(self._db_path)
            try:
                rivalry_api = RivalryAPI(db)
                rivalry = rivalry_api.get_rivalry_between_teams(self._dynasty_id, team1_id, team2_id)

                if rivalry:
                    # Map rivalry type to score
                    type_scores = {
                        "DIVISION": 1.0,
                        "SUPER_BOWL_REMATCH": 0.8,
                        "HISTORIC": 0.6,
                        "CUSTOM": 0.4
                    }
                    return type_scores.get(rivalry.rivalry_type, 0.5)

                return 0.0  # No rivalry
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to get rivalry score: {e}")
            return 0.0

    def _calculate_market_score(self, team1_id: int, team2_id: int) -> float:
        """
        Calculate combined market appeal (0.0 to 1.0).

        Uses TEAM_MARKET_SIZE constant (scale 0-20 per team).
        Normalizes to 0-1 range by dividing by max possible (20 + 20 = 40).

        Returns:
            Normalized market score (0.0 = smallest markets, 1.0 = largest markets)
        """
        market1 = TEAM_MARKET_SIZE.get(team1_id, 5)  # Default to mid-range
        market2 = TEAM_MARKET_SIZE.get(team2_id, 5)
        combined = market1 + market2

        # Normalize to 0-1 (max possible is 40)
        return combined / 40.0

    def _calculate_competitive_score(self, score1: int, score2: int) -> float:
        """
        Calculate competitiveness based on score differential (0.0 to 1.0).

        Formula: 1.0 - (abs(diff) / 35.0)
        - One-score game (1-7 pts): 0.80-1.00 (very competitive)
        - Two-score game (8-14 pts): 0.60-0.79 (competitive)
        - Three-score game (15-21 pts): 0.40-0.59 (moderate)
        - Blowout (22+ pts): 0.0-0.39 (not competitive)

        Returns:
            Competitiveness score (1.0 = closest, 0.0 = 35+ point blowout)
        """
        diff = abs(score1 - score2)

        # Normalize: 0 point diff = 1.0, 35+ point diff = 0.0
        score = max(0.0, 1.0 - (diff / 35.0))
        return score

    def _calculate_playoff_implications(
        self, week: Optional[int], team1_id: int, team2_id: int
    ) -> float:
        """
        Calculate playoff implications score (0.0 to 1.0).

        Higher scores for:
        - Late season games (weeks 15-18)
        - Teams with winning records (potential playoff teams)
        - Teams close in standings (divisional implications)

        Returns:
            0.0 for early season or teams out of contention
            0.5 for mid-season or bubble teams
            1.0 for late season games between playoff contenders
        """
        if not week or week < 10:
            return 0.0  # Early season - no implications yet

        try:
            from src.game_cycle.database.standings_api import StandingsAPI
            from src.game_cycle.database.connection import GameCycleDatabase

            db = GameCycleDatabase(self._db_path)
            try:
                standings_api = StandingsAPI(db)

                # Get team standings
                team1_standing = standings_api.get_team_standing(
                    self._dynasty_id, self._season, team1_id
                )
                team2_standing = standings_api.get_team_standing(
                    self._dynasty_id, self._season, team2_id
                )

                if not team1_standing or not team2_standing:
                    return 0.0

                # Calculate win percentage
                team1_wins = team1_standing.wins
                team1_losses = team1_standing.losses
                team1_pct = team1_wins / max(1, team1_wins + team1_losses)

                team2_wins = team2_standing.wins
                team2_losses = team2_standing.losses
                team2_pct = team2_wins / max(1, team2_wins + team2_losses)

                # Base score on week (late season = higher)
                week_factor = (week - 9) / 9.0  # Weeks 10-18 → 0.11 to 1.0

                # Both teams above .500? Playoff contenders
                if team1_pct >= 0.5 and team2_pct >= 0.5:
                    return min(1.0, week_factor * 1.2)  # Boost for contenders

                # One team above .500? Moderate implications
                elif team1_pct >= 0.5 or team2_pct >= 0.5:
                    return week_factor * 0.7

                # Both teams below .500? Low implications
                else:
                    return week_factor * 0.3

            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to calculate playoff implications: {e}")
            return 0.0

    def _get_game_star_players(self, game_id: int, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Get top performers from a game for Game of Week display.

        Args:
            game_id: Game identifier
            limit: Max number of star players (default 3)

        Returns:
            List of formatted player dicts:
            [
                {
                    "name": "Jalen Hurts",
                    "team_abbr": "PHI",
                    "stats": ["4 Total TDs", "289 Pass YDS"]
                },
                ...
            ]
        """
        try:
            from src.game_cycle.database.player_stats_api import PlayerSeasonStatsAPI

            api = PlayerSeasonStatsAPI(self._db_path)

            # Determine season type based on current stage
            is_playoff = self._current_stage in (
                "WILD_CARD", "DIVISIONAL",
                "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"
            )
            season_type_filter = 'playoffs' if is_playoff else 'regular_season'

            # Get top performers sorted by fantasy points
            performers = api.get_game_top_performers(
                dynasty_id=self._dynasty_id,
                game_id=str(game_id),
                limit=limit,
                season_type=season_type_filter
            )

            star_players = []
            for player in performers:
                # Format stats based on position
                stats_list = self._format_star_player_stats(
                    player['stats'], player['position']
                )

                star_players.append({
                    "name": player['name'],
                    "team_abbr": self._get_team_abbreviation(player['team_id']),
                    "stats": stats_list
                })

            return star_players

        except Exception as e:
            logger.error(f"Failed to get star players for game {game_id}: {e}")
            return []

    def _format_star_player_stats(
        self, stats: Dict[str, Any], position: str
    ) -> List[str]:
        """
        Format player stats into 1-4 highlight strings for Game of Week.

        Args:
            stats: Player stats dictionary
            position: Player position (full name or abbreviation)

        Returns:
            List of 1-4 stat strings (e.g., ["4 Total TDs", "289 Pass YDS", "68.2% Comp", "1 INT"])
        """
        from constants.position_abbreviations import get_position_abbreviation

        # Normalize position to abbreviation (handles both full names and abbreviations)
        position_abbr = get_position_abbreviation(position)

        highlights = []

        if position_abbr == 'QB':
            # Passing yards (ALWAYS SHOW)
            pass_yds = stats.get('passing_yards', 0)
            highlights.append(f"{pass_yds} Pass YDS")

            # Passing TDs + Rushing TDs (ALWAYS SHOW)
            total_tds = stats.get('passing_tds', 0) + stats.get('rushing_tds', 0)
            highlights.append(f"{total_tds} Total TD{'s' if total_tds != 1 else ''}")

            # Completion percentage (conditional - only if attempted passes)
            completions = stats.get('passing_completions', 0)
            attempts = stats.get('passing_attempts', 0)
            if attempts > 0:
                comp_pct = (completions / attempts) * 100
                highlights.append(f"{comp_pct:.1f}% Comp")

            # Interceptions (ALWAYS SHOW)
            ints = stats.get('passing_interceptions', 0)
            highlights.append(f"{ints} INT")

        elif position_abbr == 'RB':
            # Rushing yards (ALWAYS SHOW)
            rush_yds = stats.get('rushing_yards', 0)
            highlights.append(f"{rush_yds} Rush YDS")

            # Rushing TDs + Receiving TDs (ALWAYS SHOW)
            total_tds = stats.get('rushing_tds', 0) + stats.get('receiving_tds', 0)
            highlights.append(f"{total_tds} Total TD{'s' if total_tds != 1 else ''}")

            # Yards per carry (conditional - only if had carries)
            rush_att = stats.get('rushing_attempts', 0)
            if rush_att > 0:
                ypc = rush_yds / rush_att
                highlights.append(f"{ypc:.1f} YPC")

            # Receptions (conditional - only if significant)
            recs = stats.get('receptions', 0)
            if recs >= 3:
                highlights.append(f"{recs} Rec")

        elif position_abbr in ('WR', 'TE'):
            # Receptions (ALWAYS SHOW)
            recs = stats.get('receptions', 0)
            highlights.append(f"{recs} Rec")

            # Receiving yards (ALWAYS SHOW)
            rec_yds = stats.get('receiving_yards', 0)
            highlights.append(f"{rec_yds} Rec YDS")

            # Receiving TDs (ALWAYS SHOW)
            rec_tds = stats.get('receiving_tds', 0)
            highlights.append(f"{rec_tds} Rec TD{'s' if rec_tds != 1 else ''}")

            # Yards per reception (conditional - only if caught passes)
            if recs > 0:
                ypr = rec_yds / recs
                highlights.append(f"{ypr:.1f} YPR")

        else:
            # Defensive or special teams
            tackles = stats.get('tackles_total', 0)
            sacks = stats.get('sacks', 0)
            ints = stats.get('interceptions', 0)
            pd = stats.get('passes_defended', 0)

            # Tackles (ALWAYS SHOW)
            highlights.append(f"{tackles} Tackles")

            # Sacks (conditional - only if had sacks)
            if sacks > 0:
                highlights.append(f"{sacks:.1f} Sack{'s' if sacks != 1.0 else ''}")

            # Interceptions (conditional - only if had INTs)
            if ints > 0:
                highlights.append(f"{ints} INT{'s' if ints != 1 else ''}")

            # Passes defended (conditional - only if had PD)
            if pd > 0:
                highlights.append(f"{pd} PD")

        # Return top 4 most impressive stats
        return highlights[:4]

    def _load_game_of_week(self):
        """Load and populate the Game of the Week widget."""
        logger.debug(f"_load_game_of_week() called - stage={self._current_stage}, dynasty={self._dynasty_id}, db_path={self._db_path}")

        if not self._db_path or not self._dynasty_id:
            logger.warning("_load_game_of_week() skipped - missing db_path or dynasty_id")
            return

        try:
            import sqlite3
            from dataclasses import dataclass

            # Get games for current week/round
            week = self._get_display_week()
            logger.debug(f"_load_game_of_week() - week={week}")

            # Query games table directly (actual played games)
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if self._current_stage.startswith("REGULAR_"):
                cursor.execute("""
                    SELECT
                        game_id as id,
                        week,
                        NULL as round_name,
                        home_team_id,
                        away_team_id,
                        home_score,
                        away_score,
                        1 as is_played,
                        0 as is_divisional,
                        0 as is_conference
                    FROM games
                    WHERE dynasty_id = ? AND week = ?
                    ORDER BY game_id
                """, (self._dynasty_id, week))
            elif self._current_stage in ("WILD_CARD", "DIVISIONAL", "CONFERENCE_CHAMPIONSHIP", "SUPER_BOWL"):
                round_map = {
                    "WILD_CARD": "wild_card",
                    "DIVISIONAL": "divisional",
                    "CONFERENCE_CHAMPIONSHIP": "conference_championship",
                    "SUPER_BOWL": "super_bowl",
                }
                round_name = round_map.get(self._current_stage)
                cursor.execute("""
                    SELECT
                        game_id as id,
                        NULL as week,
                        ? as round_name,
                        home_team_id,
                        away_team_id,
                        home_score,
                        away_score,
                        1 as is_played,
                        0 as is_divisional,
                        0 as is_conference
                    FROM games
                    WHERE dynasty_id = ? AND game_type = ?
                    ORDER BY game_id
                """, (round_name, self._dynasty_id, round_name))
            else:
                # Offseason - no games
                logger.debug(f"_load_game_of_week() - offseason stage, skipping")
                conn.close()
                return

            rows = cursor.fetchall()
            conn.close()

            logger.debug(f"_load_game_of_week() - loaded {len(rows)} games from database")

            # Convert rows to simple game objects
            @dataclass
            class GameData:
                id: int
                week: Optional[int]
                round_name: Optional[str]
                home_team_id: int
                away_team_id: int
                home_score: int
                away_score: int
                is_played: bool
                is_divisional: bool
                is_conference: bool

            games = [GameData(**dict(row)) for row in rows]

            # Select best game
            best_game = self._select_game_of_week(games)
            if not best_game:
                logger.warning("No game selected for Game of the Week - no games found")
                return

            # Get star players
            star_players = self._get_game_star_players(best_game.id, limit=4)  # Increased from 3 to 4

            # Format data for widget
            game_data = {
                "game_id": str(best_game.id),
                "home_team_id": best_game.home_team_id,
                "away_team_id": best_game.away_team_id,
                "home_score": best_game.home_score or 0,
                "away_score": best_game.away_score or 0,
                "star_players": star_players
            }

            # Populate widget
            self._game_of_week_widget.set_game(game_data)

            logger.debug(
                f"Loaded Game of Week: {best_game.home_team_id} vs "
                f"{best_game.away_team_id} ({best_game.home_score}-{best_game.away_score})"
            )

        except Exception as e:
            logger.error(f"Failed to load Game of the Week: {e}", exc_info=True)

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
                self._empty_label.setText("Offseason transaction headlines will appear here.")
            else:
                self._empty_label.setText("No coverage available yet.")

    # =========================================================================
    # UI POPULATION
    # =========================================================================

    def _populate_headlines(self):
        """Populate the headlines section with player data for featured story."""
        logger.debug(f"_populate_headlines: Passing {len(self._headlines)} headlines to grid")

        # Fetch player data for featured headline (first one)
        player_data = None
        if self._headlines:
            featured_headline = self._headlines[0]
            player_data = self._fetch_player_data_for_headline(featured_headline)
            if player_data:
                logger.debug(f"_populate_headlines: Fetched player data for {player_data.get('player_name')}")
            else:
                logger.debug("_populate_headlines: No player data available for featured headline")

        try:
            self._headlines_grid.set_headlines(self._headlines, player_data=player_data)
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
        """Handle game card click in ticker - opens box score dialog."""
        logger.debug(f"Game clicked: {game_id}")
        self._open_box_score_dialog(game_id)

    def _on_game_of_week_clicked(self, game_id: str):
        """Handle Game of the Week click - shows box score."""
        logger.debug(f"Game of Week clicked: {game_id}")
        self._open_box_score_dialog(game_id)

    def _open_box_score_dialog(self, game_id: str):
        """
        Open box score dialog for the given game.

        Args:
            game_id: The unique game identifier
        """
        try:
            import sqlite3
            from game_cycle_ui.dialogs.box_score_dialog import BoxScoreDialog
            from team_management.teams.team_loader import get_team_by_id

            # Query game data from database
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT home_team_id, away_team_id, home_score, away_score
                FROM games
                WHERE game_id = ? AND dynasty_id = ?
            """, (game_id, self._dynasty_id))

            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning(f"Game {game_id} not found in database")
                return

            # Get team data
            home_team_obj = get_team_by_id(row['home_team_id'])
            away_team_obj = get_team_by_id(row['away_team_id'])

            home_team = {
                'id': row['home_team_id'],
                'name': home_team_obj.full_name if home_team_obj else f"Team {row['home_team_id']}",
                'abbr': home_team_obj.abbreviation if home_team_obj else "UNK"
            }

            away_team = {
                'id': row['away_team_id'],
                'name': away_team_obj.full_name if away_team_obj else f"Team {row['away_team_id']}",
                'abbr': away_team_obj.abbreviation if away_team_obj else "UNK"
            }

            # Open box score dialog
            dialog = BoxScoreDialog(
                game_id=game_id,
                home_team=home_team,
                away_team=away_team,
                home_score=row['home_score'],
                away_score=row['away_score'],
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                game_result=None,
                parent=self
            )
            dialog.exec()

        except Exception as e:
            logger.error(f"Failed to open box score for game {game_id}: {e}", exc_info=True)

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
