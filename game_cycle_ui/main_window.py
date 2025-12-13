"""
Game Cycle Main Window for The Owner's Sim

Stage-based main window using the new game cycle system.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Uses production database APIs
- Shares database with main.py
"""

from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar,
    QLabel, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont

from game_cycle_ui.views.stage_view import StageView
from game_cycle_ui.views.playoff_bracket_view import PlayoffBracketView
from game_cycle_ui.views.offseason_view import OffseasonView
from game_cycle_ui.views.stats_view import StatsView
from game_cycle_ui.views.injury_report_view import InjuryReportView
from game_cycle_ui.views.analytics_view import AnalyticsView
from game_cycle_ui.views.ir_activation_view import IRActivationView
from game_cycle_ui.views.awards_view import AwardsView
from game_cycle_ui.views.schedule_view import ScheduleView
from game_cycle_ui.views.media_coverage_view import MediaCoverageView
from game_cycle_ui.views.owner_view import OwnerView
from game_cycle_ui.views.team_view import TeamView
from game_cycle_ui.dialogs.rivalry_info_dialog import RivalryInfoDialog
from game_cycle_ui.dialogs.super_bowl_results_dialog import SuperBowlResultsDialog
from game_cycle_ui.controllers.stage_controller import StageUIController
from game_cycle import Stage, StageType, SeasonPhase
from ui.widgets.transaction_history_widget import TransactionHistoryWidget


class GameCycleMainWindow(QMainWindow):
    """
    Main window for stage-based game cycle.

    Uses StageView for progression instead of CalendarView.
    Dynasty context is required and flows through all controllers.
    """

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
        """Create the tabbed central widget."""
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # Stage View (main view)
        self.stage_view = StageView(parent=self)
        self.stage_controller.set_view(self.stage_view)
        self.stage_view.set_context(self.dynasty_id, self.db_path)
        self.tabs.addTab(self.stage_view, "Season")

        # Connect navigation signal for offseason
        self.stage_view.navigate_to_offseason_requested.connect(self._navigate_to_offseason_tab)

        # Team View (Team Dashboard)
        self.team_view = TeamView(parent=self)
        self.team_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.team_view.set_user_team_id(self.stage_controller._user_team_id)
        self.tabs.addTab(self.team_view, "Team")

        # Connect team view signals
        self.team_view.refresh_requested.connect(self._on_team_refresh)
        self.team_view.game_selected.connect(self._on_team_game_selected)

        placeholder_label2 = QLabel("Players view - coming soon")
        placeholder_label2.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(placeholder_label2, "Players")

        placeholder_label3 = QLabel("League view - coming soon")
        placeholder_label3.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(placeholder_label3, "League")

        # Schedule View (Milestone 11: Rivalries)
        self.schedule_view = ScheduleView(parent=self)
        self.schedule_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.tabs.addTab(self.schedule_view, "Schedule")

        # Connect schedule view signals
        self.schedule_view.game_selected.connect(self._on_schedule_game_selected)
        self.schedule_view.refresh_requested.connect(self._on_schedule_refresh)

        # Stats View (Tollgate 4)
        self.stats_view = StatsView(parent=self)
        self.stats_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.tabs.addTab(self.stats_view, "Stats")

        # Connect refresh signal
        self.stats_view.refresh_requested.connect(self._on_stats_refresh)

        # Analytics View (PFF-style grades)
        self.analytics_view = AnalyticsView(parent=self)
        self.analytics_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.tabs.addTab(self.analytics_view, "Grades")

        # Connect analytics refresh signal
        self.analytics_view.refresh_requested.connect(self._on_analytics_refresh)
        self.analytics_view.set_user_team_id(self.stage_controller._user_team_id)

        # Awards View (MVP, All-Pro, Pro Bowl, Stat Leaders)
        self.awards_view = AwardsView(parent=self)
        self.awards_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.tabs.addTab(self.awards_view, "Awards")

        # Connect awards refresh signal
        self.awards_view.refresh_requested.connect(self._on_awards_refresh)

        # Connect awards continue signal (for offseason flow)
        self.awards_view.continue_to_next_stage.connect(self._on_awards_continue)

        # Owner View (for post-awards offseason decisions)
        self.owner_view = OwnerView(parent=self)
        self.tabs.addTab(self.owner_view, "Owner")

        # Connect owner view signals (for offseason flow)
        self.owner_view.continue_clicked.connect(self._on_owner_continue)
        self.owner_view.gm_fired.connect(self._on_gm_fired)
        self.owner_view.hc_fired.connect(self._on_hc_fired)
        self.owner_view.gm_hired.connect(self._on_gm_hired)
        self.owner_view.hc_hired.connect(self._on_hc_hired)
        self.owner_view.directives_saved.connect(self._on_directives_saved)

        # Injury Report View
        self.injury_view = InjuryReportView(parent=self)
        self.injury_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.injury_view.set_user_team_id(self.stage_controller._user_team_id)
        self.tabs.addTab(self.injury_view, "Injuries")

        # Connect injury view signals
        self._setup_injury_view_connections()

        # IR Activation View (modal/floating view for weekly roster management)
        self.ir_activation_view = IRActivationView(parent=self)
        self.stage_controller.set_ir_activation_view(self.ir_activation_view)

        # Playoff Bracket View
        self.playoff_view = PlayoffBracketView(parent=self)
        self.playoff_view.set_context(self.dynasty_id, self.db_path)
        self.tabs.addTab(self.playoff_view, "Playoffs")

        # Connect playoff simulate button to stage controller
        self.playoff_view.simulate_round_requested.connect(
            self.stage_controller.execute_current_stage
        )

        # Offseason View
        self.offseason_view = OffseasonView(parent=self)
        self.offseason_view.set_db_path(self.db_path)  # For contract detail lookups

        # Connect offseason view to stage controller for re-signing decisions
        self.stage_controller.set_offseason_view(self.offseason_view)

        self.tabs.addTab(self.offseason_view, "Offseason")

        # Media Coverage View (Milestone 12)
        self.media_view = MediaCoverageView(parent=self)
        self.media_view.set_context(self.dynasty_id, self.db_path, self._season)
        self.tabs.addTab(self.media_view, "Media")

        # Connect media view signals
        self.media_view.refresh_requested.connect(self._on_media_refresh)

        # Transactions View - reuse existing widget from calendar UI
        self.transactions_view = TransactionHistoryWidget(
            parent=self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
        )
        self.tabs.addTab(self.transactions_view, "Transactions")

        self.setCentralWidget(self.tabs)

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


    def _create_statusbar(self):
        """Create the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Stage indicator
        self.stage_status = QLabel("Week 1")
        self.stage_status.setFont(QFont("Arial", 10, QFont.Bold))
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
        self._deadline_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        self._deadline_label.hide()
        self.statusbar.addPermanentWidget(self._deadline_label)

        # Connect to stage changes
        self.stage_controller.stage_changed.connect(self._update_statusbar)
        self.stage_controller.stage_changed.connect(self._update_playoff_bracket)
        self.stage_controller.stage_changed.connect(self._update_offseason_view)
        self.stage_controller.stage_changed.connect(self._update_tab_states)
        self.stage_controller.stage_changed.connect(self._update_deadline_indicator)
        self.stage_controller.stage_changed.connect(self._update_schedule_view)
        self.stage_controller.season_started.connect(self._on_season_started)

        # Connect awards calculated signal (for OFFSEASON_HONORS flow)
        self.stage_controller.awards_calculated.connect(self._on_awards_calculated)

        # Connect owner stage ready signal (for OFFSEASON_OWNER flow)
        self.stage_controller.owner_stage_ready.connect(self._on_owner_stage_ready)

        # Connect Super Bowl completed signal (for results dialog)
        self.stage_controller.super_bowl_completed.connect(self._on_super_bowl_completed)

        # Connect execution complete to cache playoff game results for play-by-play
        self.stage_controller.execution_complete.connect(self._on_execution_complete)

    def _initialize(self):
        """Initialize the window state."""
        self.stage_controller.refresh()

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

        # Refresh awards view to show any newly calculated awards (offseason)
        if hasattr(self, 'awards_view'):
            self.awards_view.refresh_data()

        # Refresh media view to show updated headlines/rankings after simulating weeks
        if hasattr(self, 'media_view'):
            self.media_view.refresh_data()

        # Refresh team view to show updated record/stats/schedule after simulating weeks
        if hasattr(self, 'team_view'):
            self.team_view.refresh_data()

    def _update_playoff_bracket(self, stage: Stage):
        """Update playoff bracket view when stage changes."""
        # Always update playoff view - show empty if no playoff games yet
        bracket_data = self.stage_controller.get_playoff_bracket()
        self.playoff_view.set_bracket_data(bracket_data)

    def _update_offseason_view(self, stage: Stage):
        """Update offseason view when stage changes."""
        if stage.phase == SeasonPhase.OFFSEASON:
            # Special handling for OFFSEASON_OWNER - show owner view
            if stage.stage_type == StageType.OFFSEASON_OWNER:
                self._on_owner_stage_ready()
                return

            # All other offseason stages - show offseason view
            preview = self.stage_controller.get_offseason_preview()
            self.offseason_view.set_stage(stage, preview)

            offseason_tab_index = self.tabs.indexOf(self.offseason_view)
            if offseason_tab_index >= 0:
                self.tabs.setCurrentIndex(offseason_tab_index)

    def _on_season_started(self):
        """Handle transition from offseason to new season."""
        # Switch to Season tab (index 0)
        season_tab_index = self.tabs.indexOf(self.stage_view)
        if season_tab_index >= 0:
            self.tabs.setCurrentIndex(season_tab_index)

        # Update window title with new season year
        stage = self.stage_controller.current_stage
        if stage:
            self.setWindowTitle(f"The Owner's Sim - {self.dynasty_id} ({stage.season_year} Season)")

            # Update stats view with new season context so dropdown includes new year
            if hasattr(self, 'stats_view'):
                self.stats_view.set_context(self.dynasty_id, self.db_path, stage.season_year)

            # Update analytics view with new season context
            if hasattr(self, 'analytics_view'):
                self.analytics_view.set_context(self.dynasty_id, self.db_path, stage.season_year)

            # Update awards view with new season context
            if hasattr(self, 'awards_view'):
                self.awards_view.set_context(self.dynasty_id, self.db_path, stage.season_year)

            # Update media view with new season context
            if hasattr(self, 'media_view'):
                self.media_view.set_context(self.dynasty_id, self.db_path, stage.season_year)

    def _navigate_to_offseason_tab(self):
        """Navigate to Offseason tab when user clicks Process button from Season tab."""
        offseason_tab_index = self.tabs.indexOf(self.offseason_view)
        if offseason_tab_index >= 0:
            self.tabs.setCurrentIndex(offseason_tab_index)

    def _update_tab_states(self, stage: Stage):
        """Enable/disable tabs based on current game phase."""
        playoffs_index = self.tabs.indexOf(self.playoff_view)
        offseason_index = self.tabs.indexOf(self.offseason_view)

        # Playoffs tab: enabled during PLAYOFFS and OFFSEASON (to view bracket/results)
        if playoffs_index >= 0:
            self.tabs.setTabEnabled(playoffs_index, stage.phase in (SeasonPhase.PLAYOFFS, SeasonPhase.OFFSEASON))

        # Offseason tab: only enabled during OFFSEASON phase
        if offseason_index >= 0:
            self.tabs.setTabEnabled(offseason_index, stage.phase == SeasonPhase.OFFSEASON)

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

    def _on_awards_refresh(self):
        """Handle awards view refresh request."""
        if hasattr(self, 'awards_view'):
            self.awards_view.refresh_data()

    def _on_media_refresh(self):
        """Handle media view refresh request."""
        if hasattr(self, 'media_view'):
            self.media_view.refresh_data()

    def _on_team_refresh(self):
        """Handle team view refresh request."""
        if hasattr(self, 'team_view'):
            self.team_view.refresh_data()

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
        """
        games_played = result.get("games_played", [])
        if not games_played:
            return

        # Check if current stage is a playoff stage
        stage = self.stage_controller.current_stage
        if stage and stage.phase == SeasonPhase.PLAYOFFS:
            # Forward game results to playoff_bracket_view for caching
            if hasattr(self, 'playoff_view'):
                self.playoff_view.store_game_results(games_played)

    def _on_awards_calculated(self):
        """
        Handle awards calculated signal from OFFSEASON_HONORS stage.

        After awards are calculated, this:
        1. Refreshes the awards view with newly calculated data
        2. Switches to the Awards tab so user can see results
        3. Enables offseason mode on awards view to show Continue button
        """
        if hasattr(self, 'awards_view'):
            # Refresh awards data
            self.awards_view.refresh_data()

            # Switch to Awards tab
            awards_tab_index = self.tabs.indexOf(self.awards_view)
            if awards_tab_index >= 0:
                self.tabs.setCurrentIndex(awards_tab_index)

            # Enable offseason mode to show Continue button
            self.awards_view.set_offseason_mode(True)

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
        1. Loads current staff and directives from OwnerService
        2. Populates the owner view with data
        3. Switches to the Owner tab so user can make decisions
        """
        if hasattr(self, 'owner_view'):
            # Refresh owner view
            self.owner_view.refresh()

            # Load data from OwnerService
            try:
                from game_cycle.services.owner_service import OwnerService

                service = OwnerService(
                    self.db_path,
                    self.dynasty_id,
                    self._season
                )

                user_team_id = self.stage_controller._user_team_id

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
                except Exception:
                    pass  # Standings may not exist yet

                self.owner_view.set_season_summary(season_summary)

                # Get previous directives
                prev_directives = service.get_directives(user_team_id)
                self.owner_view.set_directives(prev_directives)

            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error loading owner data: {e}")

            # Switch to Owner tab
            owner_tab_index = self.tabs.indexOf(self.owner_view)
            if owner_tab_index >= 0:
                self.tabs.setCurrentIndex(owner_tab_index)

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

            service = OwnerService(
                self.db_path,
                self.dynasty_id,
                self._season
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
