"""
Game Cycle Main Window for The Owner's Sim

Stage-based main window using the new game cycle system.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Uses production database APIs
- Shares database with main.py
"""

from typing import Optional
from collections import deque

from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar,
    QLabel, QMessageBox, QComboBox, QStackedWidget,
    QVBoxLayout, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction

from game_cycle_ui.views.stage_view import StageView
from game_cycle_ui.views.playoff_bracket_view import PlayoffBracketView
from game_cycle_ui.views.offseason_view import OffseasonView
from game_cycle_ui.views.stats_view import StatsView
from game_cycle_ui.views.injury_report_view import InjuryReportView
from game_cycle_ui.views.analytics_view import AnalyticsView
from game_cycle_ui.views.ir_activation_view import IRActivationView
from game_cycle_ui.views.awards_view import AwardsView
from game_cycle_ui.views.season_recap_view import SeasonRecapView
from game_cycle_ui.views.schedule_view import ScheduleView
from game_cycle_ui.views.media_coverage_view import MediaCoverageView
from game_cycle_ui.views.owner_view import OwnerView
from game_cycle_ui.views.team_view import TeamView
from game_cycle_ui.views.league_view import LeagueView
from game_cycle_ui.views.finances_view import FinancesView
from game_cycle_ui.views.inbox_view import InboxView
from game_cycle_ui.dialogs.rivalry_info_dialog import RivalryInfoDialog
from game_cycle_ui.dialogs.super_bowl_results_dialog import SuperBowlResultsDialog
from game_cycle_ui.controllers.stage_controller import StageUIController
from game_cycle import Stage, StageType, SeasonPhase
from ui.widgets.transaction_history_widget import TransactionHistoryWidget
from game_cycle_ui.theme import Typography, FontSizes, TextColors
from game_cycle_ui.widgets.category_nav_bar import CategoryNavBar
from game_cycle_ui.widgets.action_bar_widget import ActionBarWidget
from game_cycle_ui.widgets.news_rail_widget import NewsRailWidget
from game_cycle_ui.widgets.social_feed_widget import SocialFeedWidget
from game_cycle.database.connection import GameCycleDatabase


class GameCycleMainWindow(QMainWindow):
    """
    Main window for stage-based game cycle.

    Uses StageView for progression instead of CalendarView.
    Dynasty context is required and flows through all controllers.
    """

    # Views that need set_context() called when season changes
    SEASON_AWARE_VIEWS = [
        'stats_view',
        'analytics_view',
        'season_recap_view',
        'media_view',
        'finances_view',
        'team_view',
        'league_view',
        'schedule_view',
        'injury_view',
    ]

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int = 2025
    ):
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self._season = season

        # Create database connection for widgets
        self._db = GameCycleDatabase(db_path)

        # Navigation history (for back button)
        self._view_history = deque(maxlen=10)  # Last 10 views
        self._current_view_key = None

        # Window setup - include dynasty in title
        self.setWindowTitle(f"The Owner's Sim - {dynasty_id} ({season} Season)")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1000, 600)

        # Initialize controllers
        self._create_controllers()

        # Create UI
        self._create_central_widget()
        self._create_toolbar()
        self._create_statusbar()

        # Initialize state
        self._initialize()

    @property
    def season(self) -> int:
        """Current season year."""
        stage = self.stage_controller.current_stage
        if stage:
            return stage.season_year
        return self._season

    def _create_controllers(self):
        """Create controllers for the window."""
        # Get user team ID from dynasty info
        # Note: Use `or 1` because .get() returns None when key exists but is NULL
        from database.dynasty_database_api import DynastyDatabaseAPI
        dynasty_db_api = DynastyDatabaseAPI(self.db_path)
        dynasty_info = dynasty_db_api.get_dynasty_by_id(self.dynasty_id)
        user_team_id = (dynasty_info.get('team_id') or 1) if dynasty_info else 1

        self.stage_controller = StageUIController(
            database_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self._season,
            user_team_id=user_team_id,
            parent=self
        )

    def _create_central_widget(self):
        """Create the category navigation bar and content stack."""
        # Create central widget container
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Create category navigation bar
        self.nav_bar = CategoryNavBar()
        self.nav_bar.view_selected.connect(self._on_view_selected)
        central_layout.addWidget(self.nav_bar)

        # Create action bar (NEW: back button, breadcrumbs, next action)
        self._action_bar = ActionBarWidget()
        self._action_bar.back_clicked.connect(self._navigate_back)
        self._action_bar.next_action_clicked.connect(self._show_view)
        central_layout.addWidget(self._action_bar)

        # Create horizontal layout for news rail + content stack
        content_row = QWidget()
        content_layout = QHBoxLayout(content_row)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # News rail (left side)
        self._news_rail = NewsRailWidget()
        self._news_rail.headline_clicked.connect(self._on_headline_clicked)
        self._news_rail.show_all_clicked.connect(lambda: self._show_view("news"))
        content_layout.addWidget(self._news_rail)

        # Create content stack for all views
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack, 1)  # 1 = expanding

        # Social feed (right side) - Milestone 14
        self._social_feed = self._create_social_feed()
        if self._social_feed:
            content_layout.addWidget(self._social_feed)

        central_layout.addWidget(content_row, 1)  # 1 = expanding

        # =====================================================================
        # Create all views
        # =====================================================================

        # Stage View (main view) - "season"
        self.stage_view = StageView(parent=self)
        self.stage_controller.set_view(self.stage_view)
        self.stage_view.set_context(self.dynasty_id, self.db_path)

        # Connect navigation signal for offseason
        self.stage_view.navigate_to_offseason_requested.connect(self._navigate_to_offseason_tab)

        # Team View (Team Dashboard) - "roster"
        self.team_view = TeamView(parent=self)
        self.team_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.team_view.set_user_team_id(self.stage_controller._user_team_id)

        # Connect team view signals
        self.team_view.refresh_requested.connect(self._on_team_refresh)
        self.team_view.game_selected.connect(self._on_team_game_selected)

        # League View - "standings"
        self.league_view = LeagueView(parent=self)
        self.league_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.league_view.refresh_requested.connect(self._on_league_refresh)

        # Schedule View (Milestone 11: Rivalries) - "schedule"
        self.schedule_view = ScheduleView(parent=self)
        self.schedule_view.set_context(self.dynasty_id, self.db_path, self._season)

        # Connect schedule view signals
        self.schedule_view.game_selected.connect(self._on_schedule_game_selected)
        self.schedule_view.refresh_requested.connect(self._on_schedule_refresh)

        # Stats View (Tollgate 4) - "stats"
        self.stats_view = StatsView(parent=self)
        self.stats_view.set_context(self.dynasty_id, self.db_path, self._season)

        # Connect refresh signal
        self.stats_view.refresh_requested.connect(self._on_stats_refresh)

        # Analytics View (PFF-style grades) - "grades"
        self.analytics_view = AnalyticsView(parent=self)
        self.analytics_view.set_context(self.dynasty_id, self.db_path, self._season)

        # Connect analytics refresh signal
        self.analytics_view.refresh_requested.connect(self._on_analytics_refresh)
        self.analytics_view.set_user_team_id(self.stage_controller._user_team_id)

        # Season Recap View (Super Bowl, Awards, Retirements) - "season_recap"
        self.season_recap_view = SeasonRecapView(parent=self)
        self.season_recap_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.season_recap_view.set_user_team_id(self.stage_controller._user_team_id)

        # Connect season recap continue signal (for offseason flow)
        self.season_recap_view.continue_to_next_stage.connect(self._on_awards_continue)

        # Owner View (for post-awards offseason decisions) - "owner"
        self.owner_view = OwnerView(parent=self)

        # Connect owner view signals (for offseason flow)
        self.owner_view.continue_clicked.connect(self._on_owner_continue)
        self.owner_view.gm_fired.connect(self._on_gm_fired)
        self.owner_view.hc_fired.connect(self._on_hc_fired)
        self.owner_view.gm_hired.connect(self._on_gm_hired)
        self.owner_view.hc_hired.connect(self._on_hc_hired)
        self.owner_view.directives_saved.connect(self._on_directives_saved)

        # Finances View (Contract Matrix) - "finances"
        self.finances_view = FinancesView(parent=self)
        self.finances_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.finances_view.set_user_team_id(self.stage_controller._user_team_id)

        # Connect finances view refresh signal
        self.finances_view.refresh_requested.connect(self._on_finances_refresh)

        # Injury Report View - "injuries"
        self.injury_view = InjuryReportView(parent=self)
        self.injury_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.injury_view.set_user_team_id(self.stage_controller._user_team_id)

        # Connect injury view signals
        self._setup_injury_view_connections()

        # IR Activation View (modal/floating view for weekly roster management)
        self.ir_activation_view = IRActivationView(parent=self)
        self.stage_controller.set_ir_activation_view(self.ir_activation_view)

        # Playoff Bracket View - "playoffs"
        self.playoff_view = PlayoffBracketView(parent=self)
        self.playoff_view.set_context(self.dynasty_id, self.db_path)

        # Connect playoff simulate button to stage controller
        self.playoff_view.simulate_round_requested.connect(
            self.stage_controller.execute_current_stage
        )

        # Offseason View - "offseason_overview"
        self.offseason_view = OffseasonView(parent=self)
        self.offseason_view.set_db_path(self.db_path)  # For contract detail lookups

        # Connect offseason view to stage controller for re-signing decisions
        self.stage_controller.set_offseason_view(self.offseason_view)

        # Media Coverage View (Milestone 12) - "news"
        self.media_view = MediaCoverageView(parent=self)
        self.media_view.set_context(self.dynasty_id, self.db_path, self._season)

        # Connect media view signals
        self.media_view.refresh_requested.connect(self._on_media_refresh)

        # Transactions View - "transactions"
        self.transactions_view = TransactionHistoryWidget(
            parent=self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
        )

        # Inbox View - "inbox"
        self.inbox_view = InboxView(parent=self)

        # =====================================================================
        # Build view registry and add to content stack
        # =====================================================================
        self._view_registry = {
            "season": self.stage_view,
            "schedule": self.schedule_view,
            "playoffs": self.playoff_view,
            "roster": self.team_view,
            "injuries": self.injury_view,
            "standings": self.league_view,
            "stats": self.stats_view,
            "grades": self.analytics_view,
            "owner": self.owner_view,
            "finances": self.finances_view,
            "news": self.media_view,
            "transactions": self.transactions_view,
            "inbox": self.inbox_view,
            "offseason_overview": self.offseason_view,
            "season_recap": self.season_recap_view,
        }

        # Add all views to the content stack
        for view_key, view in self._view_registry.items():
            self.content_stack.addWidget(view)

        # Set initial view
        self._show_view("season")

        self.setCentralWidget(central_widget)

    def _on_view_selected(self, view_key: str):
        """Handle navigation bar view selection."""
        self._show_view(view_key)

    def _show_view(self, view_key: str):
        """Switch to the specified view."""
        view = self._view_registry.get(view_key)
        if not view:
            return

        # Track navigation history (avoid adding same view consecutively)
        if self._current_view_key and self._current_view_key != view_key:
            self._view_history.append(self._current_view_key)

        self._current_view_key = view_key

        # Switch to the view
        self.content_stack.setCurrentWidget(view)
        self.nav_bar.set_current_view(view_key)

        # Update action bar with current context
        current_stage = self.stage_controller.current_stage
        self._action_bar.update_from_stage(current_stage, view_key)

        # Update back button state
        self._update_back_button()

    def _navigate_back(self):
        """Navigate to the previous view in history."""
        if not self._view_history:
            return

        previous_view = self._view_history.pop()

        # Update current view without adding to history (avoid loop)
        self._current_view_key = previous_view

        # Switch to the view
        view = self._view_registry.get(previous_view)
        if view:
            self.content_stack.setCurrentWidget(view)
            self.nav_bar.set_current_view(previous_view)

            # Update action bar and back button
            current_stage = self.stage_controller.current_stage
            self._action_bar.update_from_stage(current_stage, previous_view)
            self._update_back_button()

    def _update_back_button(self):
        """Update back button enabled state and tooltip."""
        has_history = len(self._view_history) > 0

        if has_history:
            previous_view_key = self._view_history[-1]
            previous_view_name = self._action_bar.get_view_display_name(previous_view_key)
            self._action_bar.enable_back_button(True, previous_view_name)
        else:
            self._action_bar.enable_back_button(False)

    def _update_nav_badges(self, stage: Stage):
        """Update category badges based on current stage."""
        from game_cycle_ui.widgets.stage_action_mapping import get_badge_for_stage

        # Clear all badges first
        for category in ["Game Day", "My Team", "League", "Front Office", "Media", "Offseason"]:
            self.nav_bar.set_category_badge(category, None)

        # Get badge type for this stage
        badge_type = get_badge_for_stage(stage.stage_type)

        # Set badge on appropriate category
        if badge_type:
            from game_cycle_ui.widgets.stage_action_mapping import get_action_for_stage
            action_config = get_action_for_stage(stage.stage_type)
            category = action_config.get("category", "Game Day")
            self.nav_bar.set_category_badge(category, badge_type)

    def _on_headline_clicked(self, headline_id: int):
        """Handle headline click - navigate to media view and highlight headline."""
        # Navigate to news view
        self._show_view("news")

        # TODO: Signal the media view to scroll to/highlight the specific headline
        # This would require adding a method to MediaCoverageView

    def _refresh_news_rail(self):
        """Refresh the news rail with latest headlines."""
        try:
            current_stage = self.stage_controller.current_stage
            self._news_rail.refresh(
                self.db_path,
                self.dynasty_id,
                self.season,
                current_stage  # Pass current stage
            )
        except Exception as e:
            # Silently fail to not disrupt UI
            print(f"Warning: Failed to refresh news rail: {e}")

    def _create_social_feed(self) -> Optional[SocialFeedWidget]:
        """Create the social media feed widget (Milestone 14)."""
        try:
            from team_management.teams.team_loader import get_all_teams

            # Load teams data for filter dropdown
            teams = get_all_teams()
            teams_data = [
                {'id': team.team_id, 'abbreviation': team.abbreviation}
                for team in teams
            ]

            # Create social feed widget
            social_feed = SocialFeedWidget(
                db=self._db,
                dynasty_id=self.dynasty_id,
                teams_data=teams_data,
                parent=self
            )

            # Set current context (season/week)
            current_stage = self.stage_controller.current_stage
            if current_stage:
                social_feed.set_context(current_stage.season_year, current_stage.week_number)

            # Connect signals
            social_feed.post_clicked.connect(self._on_social_post_clicked)

            return social_feed

        except Exception as e:
            # If social feed creation fails, don't break the app
            print(f"Warning: Failed to create social feed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _on_social_post_clicked(self, post_id: int):
        """Handle social post click event."""
        # TODO: Implement post detail view or highlight related content
        print(f"Social post clicked: {post_id}")

    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # New Season action
        new_season_action = QAction("New Season", self)
        new_season_action.triggered.connect(self._on_new_season)
        toolbar.addAction(new_season_action)

        toolbar.addSeparator()

        # Quick jump actions
        jump_playoffs_action = QAction("Jump to Playoffs", self)
        jump_playoffs_action.triggered.connect(
            lambda: self.stage_controller.jump_to_stage(StageType.WILD_CARD)
        )
        toolbar.addAction(jump_playoffs_action)

        jump_offseason_action = QAction("Jump to Offseason", self)
        jump_offseason_action.triggered.connect(
            lambda: self.stage_controller.jump_to_stage(StageType.OFFSEASON_OWNER)
        )
        toolbar.addAction(jump_offseason_action)

        toolbar.addSeparator()

        # Simulation Mode Toggle
        sim_mode_label = QLabel("Sim Mode: ")
        toolbar.addWidget(sim_mode_label)

        self.sim_mode_combo = QComboBox()
        self.sim_mode_combo.addItems(["Instant (Fast)", "Full Sim (Realistic)"])
        self.sim_mode_combo.setCurrentIndex(1)  # Default to Full Sim
        self.sim_mode_combo.setToolTip(
            "Instant: Fast mock stats generation (~1s/week)\n"
            "Full Sim: Real play-by-play simulation (~3-5s/game)"
        )
        self.sim_mode_combo.currentIndexChanged.connect(self._on_sim_mode_changed)
        toolbar.addWidget(self.sim_mode_combo)

        toolbar.addSeparator()

        # Export Commentary Context action
        export_action = QAction("Export for AI Commentary", self)
        export_action.setToolTip(
            "Export current league context as JSON for AI commentary tools"
        )
        export_action.triggered.connect(self._on_export_commentary)
        toolbar.addAction(export_action)


    def _create_statusbar(self):
        """Create the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Stage indicator
        self.stage_status = QLabel("Week 1")
        self.stage_status.setFont(Typography.SMALL_BOLD)
        self.statusbar.addWidget(self.stage_status)

        # Spacer
        self.statusbar.addWidget(QLabel(" | "))

        # Season indicator
        self.season_status = QLabel("2025 Season")
        self.statusbar.addWidget(self.season_status)

        # Spacer
        self.statusbar.addWidget(QLabel(" | "))

        # Phase indicator
        self.phase_status = QLabel("Regular Season")
        self.statusbar.addPermanentWidget(self.phase_status)

        # Trade deadline indicator (hidden by default)
        self._deadline_label = QLabel("")
        self._deadline_label.setStyleSheet(f"color: {TextColors.ERROR}; font-weight: bold;")
        self._deadline_label.hide()
        self.statusbar.addPermanentWidget(self._deadline_label)

        # Connect to stage changes
        self.stage_controller.stage_changed.connect(self._update_statusbar)
        self.stage_controller.stage_changed.connect(self._update_playoff_bracket)
        self.stage_controller.stage_changed.connect(self._update_offseason_view)
        self.stage_controller.stage_changed.connect(self._update_nav_visibility)
        self.stage_controller.stage_changed.connect(self._update_deadline_indicator)
        self.stage_controller.stage_changed.connect(self._update_schedule_view)
        self.stage_controller.stage_changed.connect(self._on_stage_changed_update_views)
        self.stage_controller.stage_changed.connect(self._update_nav_badges)  # NEW: Update category badges
        self.stage_controller.stage_changed.connect(lambda: self._refresh_news_rail())  # NEW: Refresh news
        self.stage_controller.season_started.connect(self._on_season_started)

        # Connect awards calculated signal (for OFFSEASON_HONORS flow)
        self.stage_controller.awards_calculated.connect(self._on_awards_calculated)

        # Connect owner stage ready signal (for OFFSEASON_OWNER flow)
        self.stage_controller.owner_stage_ready.connect(self._on_owner_stage_ready)

        # Connect Super Bowl completed signal (for results dialog)
        self.stage_controller.super_bowl_completed.connect(self._on_super_bowl_completed)

        # Connect execution complete to cache playoff game results for play-by-play
        self.stage_controller.execution_complete.connect(self._on_execution_complete)

        # Connect FA signing result signal for feedback (Tollgate 7)
        self.stage_controller.fa_signing_result.connect(self._on_fa_signing_result)

        # Connect week navigation signal to update media view (historical navigation)
        self.stage_controller.week_navigated.connect(self._on_week_navigated)

    def _initialize(self):
        """Initialize the window state."""
        self.stage_controller.refresh()

        # Initialize action bar and news rail with current stage
        current_stage = self.stage_controller.current_stage
        if current_stage:
            self._action_bar.update_from_stage(current_stage, "season")
            self._update_nav_badges(current_stage)
            self._refresh_news_rail()

    def _update_statusbar(self, stage: Stage):
        """Update status bar when stage changes."""
        self.stage_status.setText(stage.display_name)
        self.season_status.setText(f"{stage.season_year} Season")
        self.phase_status.setText(stage.phase.name.replace("_", " ").title())

        # Refresh transactions to show any new signings/cuts/trades
        if hasattr(self, 'transactions_view'):
            self.transactions_view.refresh()

        # Refresh stats view to show updated stats after simulating weeks
        if hasattr(self, 'stats_view'):
            self.stats_view.refresh_stats()

        # Refresh analytics view to show updated grades after simulating weeks
        if hasattr(self, 'analytics_view'):
            self.analytics_view.refresh_data()

        # Refresh season recap view to show any newly calculated awards (offseason)
        if hasattr(self, 'season_recap_view'):
            self.season_recap_view.refresh_data()

        # Refresh media view to show updated headlines/rankings after simulating weeks
        if hasattr(self, 'media_view'):
            self.media_view.refresh_data()

        # Refresh team view to show updated record/stats/schedule after simulating weeks
        if hasattr(self, 'team_view'):
            self.team_view.refresh_data()

        # Refresh league view to show updated standings/playoff picture after simulating weeks
        if hasattr(self, 'league_view'):
            self.league_view.refresh_data()

    def _update_playoff_bracket(self, stage: Stage):
        """Update playoff bracket view when stage changes."""
        # Always update playoff view - show empty if no playoff games yet
        bracket_data = self.stage_controller.get_playoff_bracket()
        self.playoff_view.set_bracket_data(bracket_data)

        # Show notification when entering playoffs (unless already on playoffs view)
        if stage.phase == SeasonPhase.PLAYOFFS and self._current_view_key != "playoffs":
            self._show_playoff_notification(stage)

    def _show_playoff_notification(self, stage: Stage):
        """Show notification for playoff round transitions."""
        # Map stage type to friendly round name
        round_names = {
            StageType.WILD_CARD: ("Wild Card Round", "The NFL Playoffs are underway!"),
            StageType.DIVISIONAL: ("Divisional Round", "Divisional matchups are set!"),
            StageType.CONFERENCE_CHAMPIONSHIP: ("Conference Championships", "Conference Championship matchups are set!"),
            StageType.SUPER_BOWL: ("Super Bowl", "The Super Bowl matchup is set!"),
        }

        round_info = round_names.get(stage.stage_type)
        if not round_info:
            return

        round_name, message = round_info

        msg = QMessageBox(self)
        msg.setWindowTitle(f"{round_name} Ready")
        msg.setText(f"{stage.season_year} {round_name}")
        msg.setInformativeText(f"{message}\n\nWould you like to view the playoff bracket?")
        msg.setIcon(QMessageBox.Information)

        go_button = msg.addButton("Go to Playoffs", QMessageBox.AcceptRole)
        msg.addButton("Stay Here", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() == go_button:
            self._show_view("playoffs")

    def _update_offseason_view(self, stage: Stage):
        """Update offseason view when stage changes."""
        if stage.phase == SeasonPhase.OFFSEASON:
            # Special handling for OFFSEASON_HONORS - show season recap
            if stage.stage_type == StageType.OFFSEASON_HONORS:
                # CRITICAL: Use stage.season_year (season that just finished, e.g., 2025)
                # NOT self._season (effective season for offseason = next year, e.g., 2026)
                # Awards and Super Bowl data were calculated/played in the season that just finished
                self.season_recap_view.set_context(
                    self.dynasty_id,
                    self.db_path,
                    stage.season_year  # Actual season, not effective season
                )
                self._show_view("season_recap")
                self.season_recap_view.set_offseason_mode(True)

                # Auto-execute honors stage with loading indicator
                self.season_recap_view.show_loading("Calculating Season Awards...")
                self.stage_controller.execute_current_stage()

                return

            # Special handling for OFFSEASON_OWNER - show owner view
            if stage.stage_type == StageType.OFFSEASON_OWNER:
                self._on_owner_stage_ready()
                return

            # Preseason game stages - show in stage_view (game day view) not offseason_view
            # These are game stages that need the simulate button
            print(f"[DEBUG _update_offseason_view] Checking stage: {stage.stage_type.name}")
            if stage.stage_type in (
                StageType.OFFSEASON_PRESEASON_W1,
                StageType.OFFSEASON_PRESEASON_W2,
                StageType.OFFSEASON_PRESEASON_W3
            ):
                # Don't switch views - let stage_view handle these game stages
                print(f"[DEBUG _update_offseason_view] Preseason game stage detected, returning early")
                return

            # All other offseason stages - show offseason view
            print(f"[DEBUG _update_offseason_view] Not a preseason stage, showing offseason view")
            preview = self.stage_controller.get_offseason_preview()
            self.offseason_view.set_stage(stage, preview)

            self._show_view("offseason_overview")

    def _on_season_started(self):
        """Handle transition from offseason to new season."""
        # Switch to Season view
        self._show_view("season")

        # Update window title with new season year
        stage = self.stage_controller.current_stage
        if stage:
            print(f"[DEBUG MainWindow] _on_season_started: stage.season_year={stage.season_year}, "
                  f"stage_type={stage.stage_type.name}")
            self.setWindowTitle(f"The Owner's Sim - {self.dynasty_id} ({stage.season_year} Season)")

            # Update all season-aware views with new season context
            for view_name in self.SEASON_AWARE_VIEWS:
                view = getattr(self, view_name, None)
                if view is not None:
                    print(f"[DEBUG MainWindow] Updating {view_name} with season={stage.season_year}")
                    view.set_context(self.dynasty_id, self.db_path, stage.season_year)

    def _on_stage_changed_update_views(self, stage: Stage):
        """
        Update season-aware views when stage changes.
        Uses stage.season_year (SSOT) directly.

        Views are categorized into:
        - GAME DATA VIEWS: Show actual game events (use game_season = stage.season_year)
        - PLANNING VIEWS: Show roster/financial planning (use planning_season = +1 during offseason)
        """
        # SSOT: stage.season_year is the season for ALL game data
        game_season = stage.season_year

        # Planning season: +1 during offseason for age/roster planning views
        planning_season = game_season + 1 if stage.phase == SeasonPhase.OFFSEASON else game_season

        # Update status bar to show planning season (what user perceives as "current")
        if hasattr(self, 'season_status'):
            self.season_status.setText(f"{planning_season} Season")

        # Team view needs planning season (show ages for upcoming year during offseason)
        if hasattr(self, 'team_view'):
            self.team_view.set_context(self.dynasty_id, self.db_path, planning_season)

        # Social feed always uses game season (SSOT)
        if hasattr(self, '_social_feed') and self._social_feed is not None:
            week = stage.week_number
            if week is None and stage.phase == SeasonPhase.REGULAR_SEASON:
                print(f"[MAIN_WINDOW] WARNING: week_number is None during REGULAR_SEASON stage={stage.stage_type.name}")
            self._social_feed.set_context(game_season, week)

        # Window title shows planning season (what user thinks of as "current")
        self.setWindowTitle(f"The Owner's Sim - {self.dynasty_id} ({planning_season} Season)")

        # Views that query GAME DATA: Use game_season (SSOT)
        GAME_DATA_VIEWS = {'schedule_view', 'stats_view', 'analytics_view',
                           'season_recap_view', 'media_view'}

        # Views that show PLANNING DATA: Use planning_season
        PLANNING_VIEWS = {'finances_view', 'league_view', 'injury_view'}

        # Update all season-aware views using category-based season logic
        for view_name in self.SEASON_AWARE_VIEWS:
            if view_name == 'team_view':
                continue  # Already updated above

            view = getattr(self, view_name, None)
            if view is not None:
                # Choose season based on view category
                if view_name in GAME_DATA_VIEWS:
                    season = game_season       # SSOT: actual season with game data
                elif view_name in PLANNING_VIEWS:
                    season = planning_season   # Planning season for roster decisions
                else:
                    season = planning_season   # Default: planning season

                view.set_context(self.dynasty_id, self.db_path, season)

        # Track planning season for other uses
        if planning_season != self._season:
            self._season = planning_season

    def _navigate_to_offseason_tab(self):
        """Navigate to Offseason view when user clicks Process button from Season tab."""
        self._show_view("offseason_overview")

    def _update_nav_visibility(self, stage: Stage):
        """Update navigation visibility based on current game phase."""
        # Hide Offseason category during regular season
        self.nav_bar.set_category_visible(
            "Offseason",
            stage.phase == SeasonPhase.OFFSEASON
        )

        # Hide Playoffs menu item during regular season
        self.nav_bar.set_item_visible(
            "Game Day", "Playoffs",
            stage.phase in (SeasonPhase.PLAYOFFS, SeasonPhase.OFFSEASON)
        )

        # OFFSEASON_OWNER special handling: disable Process button (use Owner tab Continue instead)
        if stage.stage_type == StageType.OFFSEASON_OWNER:
            self.stage_view.set_advance_enabled(
                False,
                "Use the 'Continue' button in the Owner tab to proceed"
            )
        else:
            # Re-enable for other stages (if not in middle of simulation)
            self.stage_view.set_advance_enabled(True)

    def _on_new_season(self):
        """Handle new season action."""
        reply = QMessageBox.question(
            self,
            "New Season",
            f"Start a new {self.season + 1} season?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.stage_controller.start_new_season(self.season + 1)

    def _on_stats_refresh(self):
        """Handle stats view refresh request."""
        if hasattr(self, 'stats_view'):
            self.stats_view.refresh_stats()

    def _on_analytics_refresh(self):
        """Handle analytics view refresh request."""
        if hasattr(self, 'analytics_view'):
            self.analytics_view.refresh_data()

    def _on_season_recap_refresh(self):
        """Handle season recap view refresh request."""
        if hasattr(self, 'season_recap_view'):
            self.season_recap_view.refresh_data()

    def _on_media_refresh(self):
        """Handle media view refresh request."""
        if hasattr(self, 'media_view'):
            self.media_view.refresh_data()

    def _on_team_refresh(self):
        """Handle team view refresh request."""
        if hasattr(self, 'team_view'):
            self.team_view.refresh_data()

    def _on_league_refresh(self):
        """Handle league view refresh request."""
        if hasattr(self, 'league_view'):
            self.league_view.refresh_data()

    def _on_finances_refresh(self):
        """Handle finances view refresh request."""
        if hasattr(self, 'finances_view'):
            self.finances_view.refresh_data()

    def _on_team_game_selected(self, game_id: str):
        """Handle game selection from team view - open box score dialog."""
        try:
            from game_cycle_ui.dialogs.box_score_dialog import BoxScoreDialog
            dialog = BoxScoreDialog(
                game_id=game_id,
                dynasty_id=self.dynasty_id,
                db_path=self.db_path,
                parent=self
            )
            dialog.exec()
        except Exception as e:
            print(f"[MainWindow] Error opening box score: {e}")

    def _on_execution_complete(self, result: dict):
        """
        Handle stage execution completion - cache game results for play-by-play.

        For playoff stages, forwards games_played to playoff_bracket_view so
        the play-by-play tab is available when opening box scores.

        Also refreshes the social feed and news rail to show newly generated content.
        """
        games_played = result.get("games_played", [])

        # Refresh social feed after game simulation (shows newly generated posts)
        if hasattr(self, '_social_feed') and self._social_feed is not None and games_played:
            self._social_feed.refresh_feed()

        # Refresh news rail after game simulation (shows newly generated headlines)
        if games_played:
            self._refresh_news_rail()

        if not games_played:
            return

        # Check if current stage is a playoff stage
        stage = self.stage_controller.current_stage
        if stage and stage.phase == SeasonPhase.PLAYOFFS:
            # Forward game results to playoff_bracket_view for caching
            if hasattr(self, 'playoff_view'):
                self.playoff_view.store_game_results(games_played)

    def _on_fa_signing_result(self, proposal_id: str, success: bool, result: dict):
        """
        Handle FA signing result - show feedback on the proposal card.

        Forwards the result to FreeAgencyView via OffseasonView to update
        the card with signed/rejected state.
        """
        if hasattr(self, 'offseason_view') and hasattr(self.offseason_view, 'free_agency_view'):
            fa_view = self.offseason_view.free_agency_view
            if success:
                # Show signed state with contract details
                contract_details = result.get("contract_details", {})
                fa_view.show_signing_result(proposal_id, True, contract_details)
            else:
                # Show rejected state with reason and concerns
                reason = result.get("rejection_reason", result.get("error_message", "Signing failed"))
                concerns = result.get("concerns", [])
                fa_view.show_signing_result(proposal_id, False, {
                    "reason": reason,
                    "concerns": concerns
                })

    def _on_week_navigated(self, week_number: int):
        """
        Handle week navigation signal from StageUIController.

        Updates media view to show data for the specific historical week
        when user clicks prev/next week buttons.

        Args:
            week_number: Week number to navigate to (1-22)
        """
        if hasattr(self, 'media_view'):
            self.media_view.navigate_to_week(week_number)

    def _on_awards_calculated(self):
        """
        Handle awards calculated signal from OFFSEASON_HONORS stage.

        After awards are calculated in background, refresh the season recap view
        to populate with newly calculated data (awards, retirements, HOF).
        View is already showing and in offseason mode from _update_offseason_view().
        """
        if hasattr(self, 'season_recap_view'):
            # Hide loading indicator
            self.season_recap_view.hide_loading()
            # Refresh season recap data (awards, retirements now available)
            self.season_recap_view.refresh_data()
            # NOTE: View is already showing season_recap from _update_offseason_view
            # and offseason mode is already enabled - just refresh data
            print("[MainWindow] Awards calculated - Season Recap refreshed")

    def _on_awards_continue(self):
        """
        Handle Continue button click from awards view during offseason flow.

        Advances from OFFSEASON_HONORS to the next stage (Owner Review).
        """
        # Advance to next offseason stage (Owner Review)
        self.stage_controller.advance_stage()

    def _on_owner_stage_ready(self):
        """
        Handle owner stage ready signal from OFFSEASON_OWNER stage.

        After awards are viewed, this:
        1. Disables the Process button (Owner tab's Continue button is used instead)
        2. Loads current staff and directives from OwnerService
        3. Populates the owner view with data
        4. Switches to the Owner tab so user can make decisions
        """
        # Disable Process button - Owner stage uses Continue button in Owner tab
        self.stage_view.set_advance_enabled(
            False,
            "Use the 'Continue' button in the Owner tab to proceed"
        )

        if hasattr(self, 'owner_view'):
            # Refresh owner view
            self.owner_view.refresh()

            user_team_id = self.stage_controller._user_team_id

            # Load salary cap data first (always runs, even if other data fails)
            # During offseason, cap calculations are for NEXT league year
            # (contracts signed during offseason count against next year's cap)
            try:
                from game_cycle.services.cap_helper import CapHelper

                cap_helper = CapHelper(
                    self.db_path,
                    self.dynasty_id,
                    self._season + 1  # Next season (offseason cap decisions affect next year)
                )
                cap_summary = cap_helper.get_cap_summary(user_team_id)

                # Format for owner view's set_cap_data method
                cap_data = {
                    "total_cap": cap_summary.get("salary_cap_limit", 255_400_000),
                    "cap_used": cap_summary.get("total_spending", 0),
                    "cap_room": cap_summary.get("available_space", 255_400_000)
                }
                self.owner_view.set_cap_data(cap_data)
            except Exception as cap_error:
                import logging
                logging.getLogger(__name__).warning(
                    f"Error loading cap data for owner view: {cap_error}"
                )
                # Still show default cap values on error
                default_cap = 255_400_000
                self.owner_view.set_cap_data({
                    "total_cap": default_cap,
                    "cap_used": 0,
                    "cap_room": default_cap
                })

            # Load data from OwnerService
            try:
                from game_cycle.services.owner_service import OwnerService

                service = OwnerService(
                    self.db_path,
                    self.dynasty_id,
                    self._season
                )

                # Get current staff
                current_staff = service.ensure_staff_exists(user_team_id)
                self.owner_view.set_current_staff(current_staff)

                # Get season summary (record vs. target)
                season_summary = service.get_season_summary(user_team_id)

                # Try to get actual wins/losses from standings
                try:
                    from game_cycle.database.standings_api import StandingsAPI
                    from game_cycle.database.connection import GameCycleDatabase
                    with GameCycleDatabase(self.db_path) as conn:
                        standings_api = StandingsAPI(conn, self.dynasty_id)
                        standings = standings_api.get_standings(self._season)
                        for team_data in standings:
                            if team_data.get("team_id") == user_team_id:
                                season_summary["wins"] = team_data.get("wins", 0)
                                season_summary["losses"] = team_data.get("losses", 0)
                                break
                except Exception as e:
                    # Standings may not exist yet (expected early in season) or database error (unexpected)
                    logging.getLogger(__name__).debug(f"Standings not available: {e}")

                # Ensure defaults when no season data exists (e.g., skipping to offseason for testing)
                if season_summary.get("wins") is None:
                    season_summary["wins"] = 0
                if season_summary.get("losses") is None:
                    season_summary["losses"] = 0
                if season_summary.get("target_wins") is None:
                    season_summary["target_wins"] = 9  # Reasonable mid-tier expectation

                # Include cap data in season summary (reuse already-fetched cap_data)
                season_summary["cap_used"] = cap_data.get("cap_used", 0)
                season_summary["cap_total"] = cap_data.get("total_cap", 255_400_000)

                self.owner_view.set_season_summary(season_summary)

                # Get previous directives
                prev_directives = service.get_directives(user_team_id)
                self.owner_view.set_directives(prev_directives)

            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error loading owner data: {e}")

            # Switch to Owner view
            self._show_view("owner")

    def _on_owner_continue(self):
        """
        Handle Continue button click from owner view during offseason flow.

        Advances from OFFSEASON_OWNER to the next stage (Franchise Tag).
        """
        # Advance to next offseason stage (Franchise Tag)
        self.stage_controller.advance_stage()

    def _on_gm_fired(self):
        """Handle GM fired signal - generate replacement candidates."""
        try:
            from game_cycle.services.owner_service import OwnerService

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                self._season
            )

            user_team_id = self.stage_controller._user_team_id
            candidates = service.fire_gm(user_team_id)
            self.owner_view.set_gm_candidates(candidates)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error firing GM: {e}")

    def _on_hc_fired(self):
        """Handle HC fired signal - generate replacement candidates."""
        try:
            from game_cycle.services.owner_service import OwnerService

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                self._season
            )

            user_team_id = self.stage_controller._user_team_id
            candidates = service.fire_hc(user_team_id)
            self.owner_view.set_hc_candidates(candidates)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error firing HC: {e}")

    def _on_gm_hired(self, candidate_id: str):
        """Handle GM hired signal - save the hire."""
        try:
            from game_cycle.services.owner_service import OwnerService

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                self._season
            )

            user_team_id = self.stage_controller._user_team_id
            hired = service.hire_gm(user_team_id, candidate_id)

            # Update view with new staff
            current_staff = service.get_current_staff(user_team_id)
            self.owner_view.set_current_staff(current_staff)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error hiring GM: {e}")

    def _on_hc_hired(self, candidate_id: str):
        """Handle HC hired signal - save the hire."""
        try:
            from game_cycle.services.owner_service import OwnerService

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                self._season
            )

            user_team_id = self.stage_controller._user_team_id
            hired = service.hire_hc(user_team_id, candidate_id)

            # Update view with new staff
            current_staff = service.get_current_staff(user_team_id)
            self.owner_view.set_current_staff(current_staff)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error hiring HC: {e}")

    def _on_directives_saved(self, directives: dict):
        """Handle directives saved signal - persist to database."""
        try:
            from game_cycle.services.owner_service import OwnerService
            from PySide6.QtWidgets import QMessageBox

            # CRITICAL: Use actual season from stage, not effective season
            # During offseason, self._season = effective_season (season_year + 1)
            # But OwnerService.save_directives() already adds +1, so we need the actual season
            current_stage = self.stage_controller.current_stage
            actual_season = current_stage.season_year if current_stage else self._season

            # Debug logging for directive save
            print(f"[DEBUG] Saving directives: actual_season={actual_season}, "
                  f"target_season={actual_season + 1}, "
                  f"priority_positions={directives.get('priority_positions', [])}")

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                actual_season
            )

            user_team_id = self.stage_controller._user_team_id
            success = service.save_directives(user_team_id, directives)

            if success:
                QMessageBox.information(
                    self,
                    "Directives Saved",
                    "Strategic directives have been saved for the upcoming season."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    "Failed to save directives. Please try again."
                )

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error saving directives: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error saving directives: {str(e)}"
            )

    def _on_super_bowl_completed(self, super_bowl_result: dict, season_awards: dict):
        """
        Handle Super Bowl completion signal.

        Shows the SuperBowlResultsDialog with winner, MVP, and season awards.
        After user clicks Continue, advances to Franchise Tag stage.

        Args:
            super_bowl_result: Dict with winner_team_id, scores, mvp data
            season_awards: Dict mapping award_id to award result
        """
        # Get team loader for team names
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()

        # Create and show dialog
        dialog = SuperBowlResultsDialog(
            super_bowl_result=super_bowl_result,
            season_awards=season_awards,
            team_loader=team_loader,
            season=self._season,
            parent=self
        )

        # Connect continue signal to advance stage
        dialog.continue_clicked.connect(self._on_super_bowl_continue)

        # Show dialog
        dialog.exec()

    def _on_super_bowl_continue(self):
        """
        Handle Continue button click from Super Bowl results dialog.

        Advances from SUPER_BOWL to Franchise Tag (skipping OFFSEASON_HONORS).
        """
        # Advance to next stage (Franchise Tag)
        self.stage_controller.advance_stage()

    def _on_sim_mode_changed(self, index: int):
        """Handle simulation mode change."""
        mode = "full" if index == 1 else "instant"
        self.stage_controller.set_simulation_mode(mode)

        # Show info message when switching to full sim
        if mode == "full":
            QMessageBox.information(
                self,
                "Full Simulation Mode",
                "Full simulation mode provides realistic play-by-play stats "
                "but takes longer (~3-5 seconds per game).\n\n"
                "A 16-game week will take approximately 45-80 seconds."
            )

    def _on_export_commentary(self):
        """Handle Export for AI Commentary action."""
        try:
            # Validate stage
            stage = self.stage_controller.current_stage
            if not stage:
                QMessageBox.warning(
                    self,
                    "No Active Season",
                    "Please start a season before exporting."
                )
                return

            # Check if offseason
            if stage.phase == SeasonPhase.OFFSEASON:
                QMessageBox.warning(
                    self,
                    "Offseason Export",
                    "Commentary export is only available during regular season and playoffs."
                )
                return

            # Get context
            dynasty_id = self.dynasty_id
            season = stage.season_year
            week = stage.week_number or 0
            stage_type = stage.stage_type.name
            user_team_id = self.stage_controller._user_team_id

            # Show progress
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.statusbar.showMessage("Exporting commentary context...")

            # Perform export
            from src.game_cycle.services.commentary_export_service import CommentaryExportService

            service = CommentaryExportService(self.db_path)
            result = service.export_commentary_context(
                dynasty_id=dynasty_id,
                season=season,
                week=week,
                stage_type=stage_type,
                user_team_id=user_team_id
            )

            QApplication.restoreOverrideCursor()

            if result.success:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Commentary context exported successfully!\n\n"
                    f"File: {result.file_path}\n"
                    f"Size: {result.file_size_bytes / 1024:.1f} KB"
                )
                self.statusbar.showMessage(f"Export complete: {result.file_path}", 5000)
            else:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export commentary context:\n{result.error_message}"
                )
                self.statusbar.showMessage("Export failed", 5000)

        except Exception as e:
            from PySide6.QtWidgets import QApplication
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Export Error",
                f"An unexpected error occurred:\n{str(e)}"
            )
            self.statusbar.showMessage("Export error", 5000)

    def _update_deadline_indicator(self, stage: Stage):
        """Show trade deadline countdown during Weeks 7-9."""
        if stage.phase == SeasonPhase.REGULAR_SEASON:
            week = stage.week_number
            if 7 <= week <= 9:
                weeks_left = 10 - week
                self._deadline_label.setText(
                    f" | Trade Deadline: {weeks_left} week(s)"
                )
                self._deadline_label.show()
                return

        self._deadline_label.hide()

    # ========================================================================
    # Injury View Support
    # ========================================================================

    def _setup_injury_view_connections(self):
        """Connect injury view signals to handlers."""
        # Connect view signals to controller
        self.injury_view.place_on_ir_requested.connect(
            self.stage_controller.place_player_on_ir
        )
        self.injury_view.activate_from_ir_requested.connect(
            self.stage_controller.activate_player_from_ir
        )
        self.injury_view.team_changed.connect(self._on_injury_team_changed)
        self.injury_view.refresh_requested.connect(self._refresh_injury_view)

        # Connect controller result back to view
        self.stage_controller.ir_action_complete.connect(
            self.injury_view.show_action_result
        )

        # Connect stage changes to refresh injury view
        self.stage_controller.stage_changed.connect(self._update_injury_view)

        # Populate team selector and load initial data
        self._populate_injury_team_selector()

    def _populate_injury_team_selector(self):
        """Populate the team selector in injury view."""
        from team_management.teams.team_loader import get_all_teams

        teams = get_all_teams()
        team_list = [
            {"team_id": team.team_id, "name": f"{team.city} {team.nickname}"}
            for team in teams
        ]
        # Sort by team name
        team_list.sort(key=lambda t: t["name"])

        self.injury_view.populate_team_selector(team_list)

        # Set user team as default
        user_team_id = self.stage_controller._user_team_id
        self.injury_view.set_selected_team(user_team_id)

        # Load initial data
        self._refresh_injury_view()

    def _on_injury_team_changed(self, team_id: int):
        """Handle team selection change in injury view."""
        data = self.stage_controller.get_injury_data_for_team(team_id)
        self.injury_view.set_injury_data(data)

    def _refresh_injury_view(self):
        """Refresh injury view with current team's data."""
        if not hasattr(self, 'injury_view'):
            return

        # Get currently selected team (or user team as fallback)
        current_team = self.injury_view._current_team_id
        if not current_team:
            current_team = self.stage_controller._user_team_id

        data = self.stage_controller.get_injury_data_for_team(current_team)
        self.injury_view.set_injury_data(data)

    def _update_injury_view(self, stage: Stage):
        """Update injury view when stage changes."""
        if hasattr(self, 'injury_view'):
            self._refresh_injury_view()

    # ========================================================================
    # Schedule View Support
    # ========================================================================

    def _on_schedule_game_selected(self, game_id: int, home_team_id: int, away_team_id: int):
        """Handle game selection in schedule view - show rivalry dialog if applicable."""
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.database.rivalry_api import RivalryAPI
        from game_cycle.database.head_to_head_api import HeadToHeadAPI
        from team_management.teams.team_loader import get_team_by_id

        try:
            # Use default path like other parts of the codebase
            db = GameCycleDatabase()
            try:
                rivalry_api = RivalryAPI(db)
                h2h_api = HeadToHeadAPI(db)

                # Check if there's a rivalry between these teams
                rivalry = rivalry_api.get_rivalry_between_teams(
                    self.dynasty_id, home_team_id, away_team_id
                )

                if rivalry:
                    # Get H2H record
                    h2h_record = h2h_api.get_record(
                        self.dynasty_id, home_team_id, away_team_id
                    )

                    # Build team names dict
                    team_names = {}
                    home_team = get_team_by_id(home_team_id)
                    away_team = get_team_by_id(away_team_id)
                    if home_team:
                        team_names[home_team_id] = home_team.name
                    if away_team:
                        team_names[away_team_id] = away_team.name

                    # Show rivalry dialog
                    dialog = RivalryInfoDialog(rivalry, h2h_record, team_names, self)
                    dialog.exec()
            finally:
                db.close()
        except Exception as e:
            print(f"[ScheduleView] Error showing rivalry info: {e}")

    def _on_schedule_refresh(self):
        """Handle schedule view refresh request."""
        if hasattr(self, 'schedule_view'):
            self.schedule_view.reload_data()

    def _update_schedule_view(self, stage: Stage):
        """Update schedule view when stage changes."""
        if not hasattr(self, 'schedule_view'):
            return

        # Reload data to reflect any game results
        self.schedule_view.reload_data()

        # Update current week if in regular season
        if stage.phase == SeasonPhase.REGULAR_SEASON and stage.week_number:
            self.schedule_view.set_current_week(stage.week_number)

        # Update media view with current stage (for all phases)
        if hasattr(self, 'media_view'):
            stage_name = stage.stage_type.name if hasattr(stage.stage_type, 'name') else str(stage.stage_type)
            week = stage.week_number if stage.week_number else 1
            self.media_view.set_current_stage(stage_name, week)
