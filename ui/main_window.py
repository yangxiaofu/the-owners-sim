"""
Main Window for The Owner's Sim

OOTP-inspired main application window with tab-based navigation.
"""
import sys
import os
from typing import Dict, Any

from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar,
    QLabel, QMessageBox, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction

from ui.views.season_view import SeasonView
from ui.views.calendar_view import CalendarView
from ui.views.team_view import TeamView
from ui.views.player_view import PlayerView
from ui.views.offseason_view import OffseasonView
from ui.views.league_view import LeagueView
from ui.views.game_view import GameView
from ui.views.playoff_view import PlayoffView
from ui.views.transactions_view import TransactionsView

# Path setup - consolidated at module level
ui_path = os.path.dirname(__file__)
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

project_root = os.path.dirname(ui_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from controllers.season_controller import SeasonController
from controllers.calendar_controller import CalendarController
from controllers.simulation_controller import SimulationController
from controllers.league_controller import LeagueController
from controllers.playoff_controller import PlayoffController


class MainWindow(QMainWindow):
    """
    Main application window with OOTP-style tab navigation.

    Features:
    - Tab-based primary navigation (Season, Team, Player, Offseason, League, Game)
    - Menu bar with Game, Season, Team, League, Tools, Help menus
    - Toolbar with quick actions
    - Status bar displaying current date and phase
    """

    # Tab indices for consistent navigation
    TAB_SEASON = 0
    TAB_CALENDAR = 1
    TAB_TEAM = 2
    TAB_PLAYER = 3
    TAB_OFFSEASON = 4
    TAB_LEAGUE = 5
    TAB_TRANSACTIONS = 6
    TAB_PLAYOFFS = 7
    TAB_GAME = 8

    def __init__(self, db_path="data/database/nfl_simulation.db", dynasty_id="default", season=2025):
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self._initialization_season = season  # Only used for new dynasty creation

        # Load user team ID from dynasty (None if league-wide view)
        self.user_team_id = self._load_user_team_id()

        # Window setup
        self.setWindowTitle(f"The Owner's Sim - {dynasty_id}")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 700)

        # Initialize controllers
        self._create_controllers()

        # Create UI components
        self._create_central_widget()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

    @property
    def season(self) -> int:
        """
        Current season year (proxied from simulation controller).

        This property delegates to SimulationController.season which itself
        delegates to SimulationDataModel.season (SINGLE SOURCE OF TRUTH).

        Returns:
            int: Current season year from database
        """
        return self.simulation_controller.season

    def _load_user_team_id(self) -> int | None:
        """
        Load user's team ID from dynasty database.

        Returns:
            Team ID (1-32) if user controls a team, None if league-wide view
        """
        try:
            from database.dynasty_database_api import DynastyDatabaseAPI

            dynasty_api = DynastyDatabaseAPI(self.db_path)
            dynasty_info = dynasty_api.get_dynasty(self.dynasty_id)

            if dynasty_info:
                team_id = dynasty_info.get('team_id')
                if team_id:
                    print(f"[INFO MainWindow] User team loaded: Team ID {team_id}")
                else:
                    print(f"[INFO MainWindow] League-wide dynasty (no user team)")
                return team_id
            else:
                print(f"[WARNING MainWindow] Dynasty '{self.dynasty_id}' not found in database")
                return None

        except Exception as e:
            print(f"[ERROR MainWindow] Failed to load user team ID: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_controllers(self):
        """Initialize all controllers for data access."""
        # Season controller for season management and calendar operations
        self.season_controller = SeasonController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            main_window=self  # Proxy pattern - uses main_window.season property
        )

        # League controller for league-wide statistics and standings
        self.league_controller = LeagueController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            main_window=self  # Proxy pattern - uses main_window.season property
        )

        # Calendar controller for event management
        self.calendar_controller = CalendarController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            main_window=self  # Proxy pattern - uses main_window.season property
        )

        # Simulation controller for season progression
        self.simulation_controller = SimulationController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self._initialization_season  # Only for new dynasty creation
        )

        # Playoff controller for playoff bracket and seeding
        self.playoff_controller = PlayoffController(
            simulation_controller=self.simulation_controller
        )

        # Connect simulation signals to UI updates
        self.simulation_controller.date_changed.connect(self._on_date_changed)
        self.simulation_controller.games_played.connect(self._on_games_played)
        self.simulation_controller.checkpoint_saved.connect(self._on_checkpoint_saved)

    def _create_central_widget(self):
        """Create central tab widget with primary views."""
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)  # Fixed tab order like OOTP
        self.tabs.setDocumentMode(True)  # Cleaner look

        # Create views with controllers
        self.season_view = SeasonView(self, controller=self.season_controller)
        self.calendar_view = CalendarView(self, controller=self.calendar_controller)
        self.team_view = TeamView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
            # Note: season property now proxied from parent (MainWindow)
        )
        self.player_view = PlayerView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
            # Note: season property now proxied from parent (MainWindow)
        )
        self.offseason_view = OffseasonView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
            # Note: season property now proxied from parent (MainWindow)
        )
        self.league_view = LeagueView(self, controller=self.league_controller)
        self.playoff_view = PlayoffView(self, controller=self.playoff_controller)
        self.game_view = GameView(self)
        self.transactions_view = TransactionsView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id
            # Note: season property now proxied from parent (MainWindow)
        )

        # Add tabs
        self.tabs.addTab(self.season_view, "Season")
        self.tabs.addTab(self.calendar_view, "Calendar")
        self.tabs.addTab(self.team_view, "Team")
        self.tabs.addTab(self.player_view, "Player")
        self.tabs.addTab(self.offseason_view, "Offseason")
        self.tabs.addTab(self.league_view, "League")
        self.tabs.addTab(self.transactions_view, "Transactions")
        self.tabs.addTab(self.playoff_view, "Playoffs")
        self.tabs.addTab(self.game_view, "Game")

        # Store playoff tab index for visibility toggling
        self.playoff_tab_index = self.TAB_PLAYOFFS

        # Set Playoffs tab visibility based on initial phase
        current_phase = self.simulation_controller.get_current_phase()
        if current_phase in ["playoffs", "offseason"]:
            self.tabs.setTabVisible(self.playoff_tab_index, True)
            # Refresh playoff view if in playoffs phase
            if current_phase == "playoffs" and hasattr(self, 'playoff_view'):
                self.playoff_view.refresh()
        else:
            self.tabs.setTabVisible(self.playoff_tab_index, False)

        # Connect tab change signal for auto-refresh
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

    def _create_menus(self):
        """Create menu bar with OOTP-style menus."""
        menubar = self.menuBar()

        # Game Menu
        game_menu = menubar.addMenu("&Game")
        game_menu.addAction(self._create_action(
            "&New Dynasty",
            self._new_dynasty,
            "Start a new dynasty with your favorite team"
        ))
        game_menu.addAction(self._create_action(
            "&Load Dynasty",
            self._load_dynasty,
            "Load an existing dynasty"
        ))
        game_menu.addSeparator()
        game_menu.addAction(self._create_action(
            "&Settings",
            self._show_settings,
            "Configure application settings"
        ))
        game_menu.addSeparator()
        game_menu.addAction(self._create_action(
            "E&xit",
            self.close,
            "Exit the application",
            "Ctrl+Q"
        ))

        # Season Menu
        season_menu = menubar.addMenu("&Season")
        season_menu.addAction(self._create_action(
            "Simulate &Day",
            self._sim_day,
            "Simulate one day",
            "Ctrl+D"
        ))
        season_menu.addAction(self._create_action(
            "Simulate &Week",
            self._sim_week,
            "Simulate one week",
            "Ctrl+W"
        ))
        season_menu.addSeparator()
        season_menu.addAction(self._create_action(
            "View &Schedule",
            lambda: self.tabs.setCurrentIndex(self.TAB_SEASON),
            "View season schedule"
        ))
        season_menu.addAction(self._create_action(
            "View S&tandings",
            self._show_standings,
            "View division and conference standings"
        ))

        # Team Menu
        team_menu = menubar.addMenu("&Team")
        team_menu.addAction(self._create_action(
            "View &Roster",
            lambda: self.tabs.setCurrentIndex(self.TAB_TEAM),
            "View team roster"
        ))
        team_menu.addAction(self._create_action(
            "&Depth Chart",
            self._show_depth_chart,
            "Manage depth chart"
        ))
        team_menu.addAction(self._create_action(
            "&Finances",
            self._show_finances,
            "View salary cap and finances"
        ))

        # Player Menu
        player_menu = menubar.addMenu("&Player")
        player_menu.addAction(self._create_action(
            "View &Player",
            lambda: self.tabs.setCurrentIndex(self.TAB_PLAYER),
            "View player details"
        ))
        player_menu.addAction(self._create_action(
            "&Stats Leaders",
            self._show_stats_leaders,
            "View league statistical leaders"
        ))

        # League Menu
        league_menu = menubar.addMenu("&League")
        league_menu.addAction(self._create_action(
            "League &Standings",
            self._show_standings,
            "View all division standings"
        ))
        league_menu.addAction(self._create_action(
            "League &Stats",
            lambda: self.tabs.setCurrentIndex(self.TAB_LEAGUE),
            "View league-wide statistics"
        ))
        league_menu.addAction(self._create_action(
            "&Playoff Picture",
            self._show_playoff_picture,
            "View current playoff standings"
        ))

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction(self._create_action(
            "Draft Day &Demo",
            self._launch_draft_demo,
            "Launch interactive draft day simulation"
        ))
        tools_menu.addSeparator()
        tools_menu.addAction(self._create_action(
            "&Preferences",
            self._show_settings,
            "Application preferences"
        ))

        # Debug Menu
        debug_menu = menubar.addMenu("&Debug")
        debug_menu.addAction(self._create_action(
            "Show &Random Team Transactions",
            self._show_random_team_transactions,
            "Show transaction activity log for a random team (debugging)"
        ))
        debug_menu.addAction(self._create_action(
            "Show Transaction AI Activity &Log",
            self._show_transaction_ai_debug_log,
            "Show complete transaction AI debug log with probability calculations (Ctrl+Shift+T)",
            "Ctrl+Shift+T"
        ))

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self._create_action(
            "&User Guide",
            self._show_help,
            "View user documentation"
        ))
        help_menu.addAction(self._create_action(
            "&About",
            self._show_about,
            "About The Owner's Sim"
        ))

    def _create_toolbar(self):
        """Create toolbar with quick actions."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Simulation controls
        self.toolbar.addAction(self._create_action(
            "Sim Day",
            self._sim_day,
            "Simulate one day"
        ))
        self.toolbar.addAction(self._create_action(
            "Sim Week",
            self._sim_week,
            "Simulate one week"
        ))

        # Phase-end simulation button (dynamic text based on current phase)
        self.sim_phase_action = self._create_action(
            "Sim to Playoffs",
            self._sim_to_phase_end,
            "Simulate to end of regular season"
        )
        self.toolbar.addAction(self.sim_phase_action)

        # Skip to New Season button (only visible during offseason)
        self.skip_to_new_season_action = QAction("Skip to New Season", self)
        self.skip_to_new_season_action.setToolTip("Skip remaining offseason events and start new season")
        self.skip_to_new_season_action.triggered.connect(self._on_skip_to_new_season)
        self.skip_to_new_season_action.setVisible(False)  # Hidden by default
        self.toolbar.addAction(self.skip_to_new_season_action)

        self.toolbar.addSeparator()

        # Quick navigation
        self.toolbar.addAction(self._create_action(
            "My Team",
            lambda: self.tabs.setCurrentIndex(self.TAB_TEAM),
            "Go to my team"
        ))
        self.toolbar.addAction(self._create_action(
            "Standings",
            self._show_standings,
            "View standings"
        ))
        self.toolbar.addAction(self._create_action(
            "League",
            lambda: self.tabs.setCurrentIndex(self.TAB_LEAGUE),
            "View league stats"
        ))

    def _create_statusbar(self):
        """Create status bar with current date and phase."""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        # Get current simulation state
        current_date = self.simulation_controller.get_current_date()
        current_phase = self.simulation_controller.get_current_phase()
        current_week = self.simulation_controller.get_current_week()

        # Format phase display
        phase_display = current_phase.replace('_', ' ').title()
        if current_week:
            phase_display += f" - Week {current_week}"

        # Current date label
        self.date_label = QLabel(f"Date: {current_date}")
        self.date_label.setStyleSheet("padding: 0 10px;")

        # Current phase label
        self.phase_label = QLabel(f"Phase: {phase_display}")
        self.phase_label.setStyleSheet("padding: 0 10px;")

        # Add to status bar
        statusbar.addWidget(self.date_label)
        statusbar.addPermanentWidget(self.phase_label)

        # Initialize phase-dependent button text
        self._update_phase_button(current_phase)

    def _create_action(self, text, slot, tooltip=None, shortcut=None):
        """
        Helper method to create QAction.

        Args:
            text: Action text
            slot: Callback function
            tooltip: Tooltip text (optional)
            shortcut: Keyboard shortcut (optional)

        Returns:
            QAction instance
        """
        action = QAction(text, self)
        action.triggered.connect(slot)

        if tooltip:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)

        if shortcut:
            action.setShortcut(shortcut)

        return action

    # Action handlers (placeholders for Phase 1)
    def _new_dynasty(self):
        """Create a new dynasty."""
        QMessageBox.information(
            self,
            "New Dynasty",
            "New Dynasty feature coming soon!\n\nThis will allow you to start a new franchise."
        )

    def _load_dynasty(self):
        """Load an existing dynasty."""
        QMessageBox.information(
            self,
            "Load Dynasty",
            "Load Dynasty feature coming soon!\n\nThis will allow you to continue an existing franchise."
        )

    def _show_settings(self):
        """Show settings dialog."""
        QMessageBox.information(
            self,
            "Settings",
            "Settings dialog coming soon!\n\nYou'll be able to configure themes, preferences, and game options."
        )

    def _sim_day(self):
        """Simulate one day (with draft day and milestone event interception)."""
        # CHECK FOR DRAFT DAY BEFORE SIMULATION
        draft_event = self.simulation_controller.check_for_draft_day_event()

        if draft_event and self.user_team_id:
            # Draft day detected - launch interactive dialog
            success = self._handle_draft_day_interactive(draft_event)

            if not success:
                # User cancelled or dialog failed
                QMessageBox.information(
                    self,
                    "Draft Cancelled",
                    "Draft day simulation was cancelled. Calendar will not advance."
                )
                return

            # Draft completed successfully - calendar already advanced by draft dialog
            # DO NOT call advance_day() again to prevent double execution

            # Refresh calendar view to show new date
            self.calendar_view.refresh_current_date()

            # Show success message
            current_date_str = self.simulation_controller.get_current_date()
            formatted_date = self._format_date(current_date_str)
            QMessageBox.information(
                self,
                "Draft Complete",
                f"Draft day completed successfully!\n\nAdvanced to: {formatted_date}"
            )

            return  # Exit here to prevent second execution via advance_day()

        # CHECK FOR OTHER INTERACTIVE MILESTONE EVENTS (franchise tags, free agency, roster cuts, cap compliance)
        milestone_event = self.simulation_controller.check_for_interactive_event()

        if milestone_event and self.user_team_id:
            event_type = milestone_event.get('event_type')
            params = milestone_event.get('data', {}).get('parameters', {})

            # Route to appropriate handler based on event type
            if event_type == 'DEADLINE':
                deadline_type = params.get('deadline_type')

                if deadline_type == 'FRANCHISE_TAG':
                    success = self._handle_franchise_tag_interactive(milestone_event)
                    event_name = "Franchise Tag Deadline"
                    if success:
                        self._mark_event_executed(milestone_event, "Franchise tag deadline processed")

                elif deadline_type == 'FINAL_ROSTER_CUTS':
                    success = self._handle_roster_cuts_interactive(milestone_event)
                    event_name = "Final Roster Cuts Deadline"
                    if success:
                        self._mark_event_executed(milestone_event, "Final roster cuts completed")

                elif deadline_type == 'SALARY_CAP_COMPLIANCE':
                    success = self._handle_cap_compliance_interactive(milestone_event)
                    event_name = "Salary Cap Compliance Deadline"
                    if success:
                        self._mark_event_executed(milestone_event, "Salary cap compliance verified")
                else:
                    success = True  # Unknown deadline type, allow simulation to proceed
                    event_name = "Offseason Deadline"

            elif event_type == 'WINDOW':
                window_name = params.get('window_name')

                if window_name == 'FREE_AGENCY':
                    success = self._handle_free_agency_interactive(milestone_event)
                    event_name = "Free Agency Period"
                    if success:
                        self._mark_event_executed(milestone_event, "Free agency period started")
                else:
                    success = True  # Unknown window type, allow simulation to proceed
                    event_name = "Offseason Window"
            else:
                success = True  # Unknown event type, allow simulation to proceed
                event_name = "Offseason Event"

            if not success:
                # User cancelled or dialog failed
                QMessageBox.information(
                    self,
                    f"{event_name} Cancelled",
                    f"{event_name} was cancelled. Calendar will not advance."
                )
                return

            # Event completed successfully - continue with normal simulation

        # Normal simulation flow
        result = self.simulation_controller.advance_day()

        if result['success']:
            # Get current date after simulation
            current_date_str = self.simulation_controller.get_current_date()
            formatted_date = self._format_date(current_date_str)

            # Build message with date
            msg = f"Simulated: {formatted_date}\n\n{result['message']}"
            if result['games_played'] > 0:
                msg += f"\n\nGames played: {result['games_played']}"

            QMessageBox.information(self, "Day Simulation Complete", msg)

            # Refresh calendar view (re-sync date and reload events)
            if hasattr(self, 'calendar_view'):
                self.calendar_view.refresh_current_date()

            # Refresh playoff view if playoffs tab is visible (playoffs or offseason)
            if self.simulation_controller.get_current_phase() in ["playoffs", "offseason"]:
                if hasattr(self, 'playoff_view'):
                    self.playoff_view.refresh()
        else:
            QMessageBox.warning(self, "Simulation Failed", result['message'])

    def _sim_week(self):
        """
        Simulate one week with milestone detection in UI layer.

        Uses an iterative approach that checks for milestones after each one
        is handled, ensuring no milestones are skipped.

        This refactor moves milestone detection from backend to UI layer,
        achieving proper MVC separation (backend simulates, UI routes).
        """
        start_date_str = self.simulation_controller.get_current_date()
        milestones_handled = []
        days_simulated = 0
        max_days = 7

        print(f"\n[SIM_WEEK] ===== Starting _sim_week() =====")
        print(f"[SIM_WEEK] Start date: {start_date_str}")
        print(f"[SIM_WEEK] Max days: {max_days}")

        while days_simulated < max_days:
            # Check for milestone on current day or ahead (within remaining days)
            remaining_days = max_days - days_simulated
            current_date = self.simulation_controller.get_current_date()

            print(f"\n[SIM_WEEK] --- Loop iteration ---")
            print(f"[SIM_WEEK] Current date: {current_date}")
            print(f"[SIM_WEEK] Days simulated: {days_simulated}")
            print(f"[SIM_WEEK] Remaining days: {remaining_days}")
            print(f"[SIM_WEEK] Checking milestones with days_ahead={remaining_days + 1}")

            milestone = self.simulation_controller.check_upcoming_milestones(days_ahead=remaining_days + 1)

            if milestone:
                days_until = milestone['days_until']
                print(f"[SIM_WEEK] Milestone found: {milestone['display_name']} (days_until={days_until})")

                # Only handle if milestone is within our remaining simulation window
                if days_until <= remaining_days:
                    if days_until > 0:
                        # Simulate days BEFORE milestone
                        print(f"[SIM_WEEK] Advancing {days_until} days BEFORE milestone")
                        result = self.simulation_controller.advance_days(days_until)
                        if not result['success']:
                            QMessageBox.warning(self, "Simulation Failed", result['message'])
                            return
                        days_simulated += days_until
                        print(f"[SIM_WEEK] Now at date: {self.simulation_controller.get_current_date()}")

                    # Handle the milestone
                    print(f"[SIM_WEEK] Handling milestone: {milestone['display_name']}")
                    if self.user_team_id:
                        success = self._handle_interactive_event_router(milestone['event'])
                        print(f"[SIM_WEEK] Handler returned: {success}")
                        if not success:
                            # User cancelled
                            end_date_str = self.simulation_controller.get_current_date()
                            QMessageBox.information(
                                self,
                                "Milestone Paused",
                                f"Simulation paused at {milestone['display_name']}.\n\n"
                                f"Calendar: {self._format_date(end_date_str)}\n\n"
                                "You can resume simulation when ready."
                            )
                            return

                    milestones_handled.append(milestone['display_name'])

                    # STOP at milestone - don't continue simulating
                    # User must click "Sim Week" again to continue past this milestone
                    end_date_str = self.simulation_controller.get_current_date()
                    date_range = self._format_date_range(start_date_str, end_date_str)

                    if days_simulated > 0:
                        msg = f"Simulated {days_simulated} day(s).\n\n{date_range}\n\nStopped at: {milestone['display_name']}"
                    else:
                        msg = f"Stopped at: {milestone['display_name']}\n\nDate: {self._format_date(end_date_str)}"

                    print(f"\n[SIM_WEEK] ===== STOPPING at milestone =====")
                    print(f"[SIM_WEEK] Milestone: {milestone['display_name']}")
                    print(f"[SIM_WEEK] Current date: {end_date_str}")
                    print(f"[SIM_WEEK] Days simulated before stop: {days_simulated}")
                    print(f"[SIM_WEEK] =====================================\n")

                    QMessageBox.information(self, "Milestone Reached", msg)
                    self._refresh_views_after_simulation()
                    return  # STOP HERE - don't continue past milestone
                else:
                    # Milestone is beyond our remaining window - simulate remaining days
                    print(f"[SIM_WEEK] Milestone beyond window (days_until={days_until} > remaining={remaining_days})")
                    if remaining_days > 0:
                        print(f"[SIM_WEEK] Simulating remaining {remaining_days} days")
                        result = self.simulation_controller.advance_days(remaining_days)
                        if not result['success']:
                            QMessageBox.warning(self, "Simulation Failed", result['message'])
                            return
                        days_simulated += remaining_days
            else:
                # No more milestones - simulate remaining days
                print(f"[SIM_WEEK] No milestone found, simulating remaining {remaining_days} days")
                if remaining_days > 0:
                    result = self.simulation_controller.advance_days(remaining_days)
                    if not result['success']:
                        QMessageBox.warning(self, "Simulation Failed", result['message'])
                        return
                    days_simulated += remaining_days

        # Show completion message
        end_date_str = self.simulation_controller.get_current_date()
        date_range = self._format_date_range(start_date_str, end_date_str)
        msg = f"Week simulated successfully.\n\n{date_range}"

        if milestones_handled:
            msg += f"\n\nMilestones handled: {', '.join(milestones_handled)}"

        print(f"\n[SIM_WEEK] ===== Completed _sim_week() =====")
        print(f"[SIM_WEEK] End date: {end_date_str}")
        print(f"[SIM_WEEK] Milestones handled: {milestones_handled}")
        print(f"[SIM_WEEK] =====================================\n")

        QMessageBox.information(self, "Week Complete", msg)

        # Refresh views
        self._refresh_views_after_simulation()

    def _create_phase_progress_dialog(self) -> QProgressDialog:
        """Create a modal progress dialog for phase simulation."""
        progress = QProgressDialog(
            "Simulating to end of phase...",
            "Cancel",
            0, 100,
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        return progress

    def _sim_to_phase_end(self):
        """Simulate to end of current phase, pausing at interactive events."""
        starting_phase = self.simulation_controller.get_current_phase()
        start_date_str = self.simulation_controller.get_current_date()

        # Create progress dialog
        progress = self._create_phase_progress_dialog()

        days_simulated = 0
        total_games_played = 0
        MAX_DAYS = 365

        try:
            while days_simulated < MAX_DAYS:
                # Check if user cancelled progress dialog
                if progress.wasCanceled():
                    raise InterruptedError("User cancelled simulation")

                # Check for interactive event BEFORE advancing day
                interactive_event = self.simulation_controller.check_for_interactive_event()

                if interactive_event and self.user_team_id:
                    # Close progress dialog
                    progress.close()

                    # Launch interactive dialog
                    success = self._handle_interactive_event_router(interactive_event)

                    if not success:
                        # User cancelled - show partial completion
                        end_date_str = self.simulation_controller.get_current_date()
                        date_range = self._format_date_range(start_date_str, end_date_str)

                        QMessageBox.information(
                            self,
                            "Phase Simulation Paused",
                            f"Simulation paused at user's request.\n\n"
                            f"{date_range}\n\n"
                            f"Days simulated: {days_simulated}\n"
                            f"Games played: {total_games_played}\n\n"
                            f"Calendar updated to {self._format_date(end_date_str)}.\n"
                            "You can resume simulation when ready."
                        )
                        return

                    # Recreate progress dialog for remainder
                    progress = self._create_phase_progress_dialog()
                    progress.setValue(min(99, days_simulated // 7))

                # Advance day
                result = self.simulation_controller.advance_day()

                if result['success']:
                    days_simulated += 1
                    total_games_played += result.get('games_played', 0)

                    # Update progress
                    progress.setValue(min(99, days_simulated // 7))
                    QApplication.processEvents()

                    # Check for phase transition
                    current_phase = self.simulation_controller.get_current_phase()
                    if current_phase != starting_phase:
                        break
                else:
                    progress.close()
                    QMessageBox.warning(self, "Simulation Failed", result['message'])
                    return

            progress.close()

            # Show completion message
            end_date_str = self.simulation_controller.get_current_date()
            date_range = self._format_date_range(start_date_str, end_date_str)
            current_phase = self.simulation_controller.get_current_phase()

            msg = (
                f"Phase simulation complete.\n\n"
                f"{date_range}\n\n"
                f"Days simulated: {days_simulated}\n"
                f"Games played: {total_games_played}\n\n"
                f"Current phase: {current_phase.replace('_', ' ').title()}"
            )
            QMessageBox.information(self, "Phase Complete", msg)

            # Refresh views
            QApplication.processEvents()
            if hasattr(self, 'calendar_view'):
                self.calendar_view.refresh_current_date()
            if hasattr(self, 'playoff_view'):
                self.playoff_view.refresh()

        except InterruptedError:
            progress.close()

            end_date_str = self.simulation_controller.get_current_date()
            date_range = self._format_date_range(start_date_str, end_date_str)

            QMessageBox.information(
                self,
                "Simulation Cancelled",
                f"Simulation cancelled by user.\n\n"
                f"{date_range}\n\n"
                f"Days simulated: {days_simulated}\n"
                f"Games played: {total_games_played}\n\n"
                f"Calendar updated to {self._format_date(end_date_str)}."
            )

    def _show_depth_chart(self):
        """Show depth chart."""
        QMessageBox.information(
            self,
            "Depth Chart",
            "Depth Chart coming in Phase 5!\n\nYou'll be able to manage your team's depth chart with drag-and-drop."
        )

    def _show_finances(self):
        """Show team finances."""
        QMessageBox.information(
            self,
            "Finances",
            "Finances view coming in Phase 2!\n\nView salary cap, contracts, and financial details."
        )

    def _show_standings(self):
        """Show league standings by switching to League tab."""
        self.tabs.setCurrentIndex(self.TAB_LEAGUE)

    def _show_stats_leaders(self):
        """Show statistical leaders by switching to League tab → Stats Leaders sub-tab."""
        self.tabs.setCurrentIndex(self.TAB_LEAGUE)
        # Switch to Stats Leaders sub-tab (index 2: Standings=0, Free Agents=1, Stats Leaders=2)
        if hasattr(self, 'league_view') and hasattr(self.league_view, 'tabs'):
            self.league_view.tabs.setCurrentIndex(2)

    def _show_playoff_picture(self):
        """Show playoff picture by switching to Playoffs tab."""
        if self.simulation_controller.get_current_phase() == "playoffs":
            # Switch to Playoffs tab (index 6)
            self.tabs.setCurrentIndex(self.playoff_tab_index)
        else:
            QMessageBox.information(
                self,
                "Playoff Picture",
                "Playoffs have not started yet.\n\nComplete the regular season to view playoff bracket."
            )

    def _show_help(self):
        """Show user guide."""
        QMessageBox.information(
            self,
            "User Guide",
            "User Guide coming soon!\n\nDetailed documentation will be available in Phase 6."
        )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About The Owner's Sim",
            "<h2>The Owner's Sim</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A comprehensive NFL management simulation game with deep statistical analysis.</p>"
            "<p>Inspired by Out of the Park Baseball.</p>"
            "<br>"
            "<p><b>Built with:</b> Python, PySide6/Qt</p>"
            "<p>© 2024 OwnersSimDev</p>"
        )

    def _show_random_team_transactions(self):
        """Show transaction log for a random team (debugging feature)."""
        import random

        try:
            from constants.team_ids import TeamIDs
            from team_management.teams.team_loader import get_team_by_id
            from persistence.transaction_api import TransactionAPI
            from ui.dialogs.transaction_log_dialog import TransactionLogDialog

            # Get random team
            all_team_ids = TeamIDs.get_all_team_ids()
            random_team_id = random.choice(all_team_ids)
            team = get_team_by_id(random_team_id)

            # Get transactions
            api = TransactionAPI(self.db_path)
            transactions = api.get_team_transactions(
                team_id=random_team_id,
                dynasty_id=self.dynasty_id
            )

            # Show dialog
            dialog = TransactionLogDialog(
                team_id=random_team_id,
                team_name=team.full_name,
                transactions=transactions,
                dynasty_id=self.dynasty_id,
                parent=self
            )
            dialog.exec()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Transaction Log Error",
                f"Failed to load transaction log:\n\n{str(e)}\n\n{error_details}"
            )

    def _show_transaction_ai_debug_log(self):
        """Show transaction AI activity log with debug information."""
        try:
            from ui.dialogs.transaction_ai_debug_dialog import TransactionAIDebugDialog

            # Get debug data from simulation controller
            debug_data = self.simulation_controller.get_transaction_debug_data()

            if not debug_data:
                QMessageBox.information(
                    self,
                    "No Debug Data",
                    "No transaction AI activity recorded yet.\n\n"
                    "Run a simulation (Sim Day/Sim Week) to collect debug data."
                )
                return

            # Show dialog
            dialog = TransactionAIDebugDialog(debug_data, parent=self)
            dialog.exec()

            # Clear debug data after viewing to prevent memory buildup
            self.simulation_controller.clear_transaction_debug_data()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Transaction AI Debug Log Error",
                f"Failed to load transaction AI debug log:\n\n{str(e)}\n\n{error_details}"
            )

    def _launch_draft_demo(self):
        """Launch Draft Day Demo in a modal dialog."""
        import random
        from pathlib import Path

        try:
            from demo.draft_day_demo.draft_day_dialog import DraftDayDialog
            from demo.draft_day_demo.draft_demo_controller import DraftDemoController
            from demo.draft_day_demo.setup_demo_database import setup_draft_demo_database

            # Setup demo database path
            demo_db = Path("demo/draft_day_demo/draft_demo.db")

            # Create database if doesn't exist
            if not demo_db.exists():
                QMessageBox.information(
                    self,
                    "Setting Up Demo",
                    "First time setup: Creating draft demo database...\n\n"
                    "This will generate 224 prospects and may take 10-15 seconds."
                )

                success = setup_draft_demo_database(str(demo_db))

                if not success:
                    QMessageBox.critical(
                        self,
                        "Setup Failed",
                        "Failed to create draft demo database.\n\n"
                        "Check console for error details."
                    )
                    return

            # Random team assignment
            user_team_id = random.randint(1, 32)

            # Create controller
            controller = DraftDemoController(
                db_path=str(demo_db),
                dynasty_id="draft_day_demo",
                season=2026,
                user_team_id=user_team_id
            )

            # Launch dialog
            dialog = DraftDayDialog(
                controller=controller,
                parent=self
            )

            dialog.exec()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Draft Demo Error",
                f"Failed to launch Draft Day Demo:\n\n{str(e)}\n\n{error_details}"
            )

    def _handle_draft_day_interactive(self, draft_event: Dict[str, Any]) -> bool:
        """
        Launch interactive draft day dialog.

        Args:
            draft_event: Draft day event data from database

        Returns:
            True if draft completed successfully, False if cancelled
        """
        try:
            # Import here to avoid circular dependency
            from ui.controllers.draft_dialog_controller import DraftDialogController
            from ui.dialogs.draft_day_dialog import DraftDayDialog
            from PySide6.QtWidgets import QDialog

            # Get season from event or current state
            draft_season = draft_event.get('season', self.season)

            print(f"[INFO MainWindow] Launching draft day dialog for season {draft_season}, team {self.user_team_id}")

            # Create controller (uses MAIN database, not demo database)
            controller = DraftDialogController(
                database_path=self.db_path,
                dynasty_id=self.dynasty_id,
                season_year=draft_season,
                user_team_id=self.user_team_id
            )

            # Launch dialog (modal - blocks until draft completes)
            dialog = DraftDayDialog(controller=controller, parent=self)
            result = dialog.exec()

            # Check if user completed the draft
            if result == QDialog.DialogCode.Accepted:
                print(f"[INFO MainWindow] Draft completed successfully")

                # Mark draft event as executed to prevent re-triggering
                self._mark_event_executed(draft_event, "Draft completed successfully")

                return True
            else:
                print(f"[INFO MainWindow] Draft cancelled by user")
                return False

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "Draft Day Error",
                f"Failed to launch draft day dialog:\n\n{str(e)}\n\n{error_details}"
            )
            return False

    def _handle_franchise_tag_interactive(self, event: Dict[str, Any]) -> bool:
        """
        Handle franchise tag deadline event (STUB).

        TODO: Implement interactive franchise tag dialog showing:
        - List of pending free agents eligible for franchise/transition tags
        - Team's available cap space
        - Tag cost estimates
        - UI to apply franchise/transition tags

        Args:
            event: Franchise tag deadline event data

        Returns:
            True to allow simulation to proceed, False to cancel
        """
        print(f"[STUB] Franchise tag deadline detected: {event.get('event_date')}")
        print("[STUB] Interactive franchise tag dialog not yet implemented")
        print("[STUB] Allowing simulation to proceed...")

        # Mark event as executed to prevent re-triggering
        self._mark_event_executed(event, "Franchise tag deadline handled (stub)")

        return True  # Allow simulation to proceed for now

    def _handle_roster_cuts_interactive(self, event: Dict[str, Any]) -> bool:
        """
        Handle final roster cuts deadline event (STUB).

        TODO: Implement interactive roster cuts dialog showing:
        - Current roster size (90+ players)
        - Target roster size (53 players)
        - Depth chart with cut recommendations
        - UI to make roster cut decisions

        Args:
            event: Roster cuts deadline event data

        Returns:
            True to allow simulation to proceed, False to cancel
        """
        print(f"[STUB] Final roster cuts deadline detected: {event.get('event_date')}")
        print("[STUB] Interactive roster cuts dialog not yet implemented")
        print("[STUB] Allowing simulation to proceed...")

        # Mark event as executed to prevent re-triggering
        self._mark_event_executed(event, "Roster cuts deadline handled (stub)")

        return True  # Allow simulation to proceed for now

    def _handle_free_agency_interactive(self, event: Dict[str, Any]) -> bool:
        """
        Handle free agency period start event (STUB).

        TODO: Implement interactive free agency dialog showing:
        - Available free agents with ratings/stats
        - Team needs analysis
        - Cap space available
        - UI to make free agent offers and signings

        Args:
            event: Free agency window start event data

        Returns:
            True to allow simulation to proceed, False to cancel
        """
        print(f"[STUB] Free agency period start detected: {event.get('event_date')}")
        print("[STUB] Interactive free agency dialog not yet implemented")
        print("[STUB] Allowing simulation to proceed...")

        # Mark event as executed to prevent re-triggering
        self._mark_event_executed(event, "Free agency start handled (stub)")

        return True  # Allow simulation to proceed for now

    def _handle_cap_compliance_interactive(self, event: Dict[str, Any]) -> bool:
        """
        Handle salary cap compliance deadline event (STUB).

        TODO: Implement interactive cap compliance dialog showing:
        - Current cap situation (over/under)
        - Required cuts/restructures to achieve compliance
        - Contract restructure options
        - UI to make cap-saving decisions

        Args:
            event: Cap compliance deadline event data

        Returns:
            True to allow simulation to proceed, False to cancel
        """
        print(f"[STUB] Salary cap compliance deadline detected: {event.get('event_date')}")
        print("[STUB] Interactive cap compliance dialog not yet implemented")
        print("[STUB] Allowing simulation to proceed...")

        # Mark event as executed to prevent re-triggering
        self._mark_event_executed(event, "Cap compliance deadline handled (stub)")

        return True  # Allow simulation to proceed for now

    def _handle_generic_deadline_interactive(self, event: Dict[str, Any], deadline_type: str) -> bool:
        """
        Handle deadline types without specific handlers.

        Shows an informational dialog and allows simulation to proceed.
        This ensures unknown deadline types don't silently pass through.

        Args:
            event: Event dictionary from database
            deadline_type: The type of deadline (e.g., 'RFA_TENDER')

        Returns:
            True (always allows simulation to proceed after showing info)
        """
        display_name = deadline_type.replace('_', ' ').title() if deadline_type else 'Unknown'

        QMessageBox.information(
            self,
            f"Deadline: {display_name}",
            f"The {display_name} deadline has been reached.\n\n"
            f"This is an informational milestone. Click OK to continue simulation."
        )

        # Mark event as executed to prevent re-triggering
        self._mark_event_executed(event, f"Generic deadline handled: {display_name}")

        return True

    def _mark_event_executed(self, event: Dict[str, Any], message: str) -> None:
        """
        Mark milestone event as executed by setting results field.

        This prevents the event from re-triggering when user clicks "Sim Day"
        again on the same date (e.g., after going back in calendar).

        Args:
            event: Event dictionary from database
            message: Human-readable completion message
        """
        from datetime import datetime

        try:
            # Add execution results to event data
            if 'data' not in event:
                event['data'] = {}

            event['data']['results'] = {
                'success': True,
                'executed_at': datetime.now().isoformat(),
                'message': message
            }

            print(f"[DEBUG _mark_event_executed] Event ID: {event.get('event_id')}")
            print(f"[DEBUG _mark_event_executed] Event type: {event.get('event_type')}")
            print(f"[DEBUG _mark_event_executed] Setting results: {event['data']['results']}")

            # Update in database via calendar controller's data model
            calendar_data_model = self.calendar_controller._get_data_model()
            calendar_data_model.event_api.update_event_by_dict(event)

            print(f"[INFO MainWindow] Marked event as executed: {message}")

            # Verify the update worked by re-querying
            event_id = event.get('event_id')
            if event_id:
                updated_event = calendar_data_model.event_api.get_event_by_id(event_id)
                if updated_event:
                    updated_results = updated_event.get('data', {}).get('results')
                    print(f"[DEBUG _mark_event_executed] Verification - results in DB: {updated_results}")
                else:
                    print(f"[DEBUG _mark_event_executed] Verification - could not re-query event")

        except Exception as e:
            print(f"[ERROR MainWindow] Failed to mark event as executed: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - this is non-critical, simulation can proceed

    def _handle_interactive_event_router(self, event: Dict[str, Any]) -> bool:
        """
        Route interactive event to appropriate handler dialog.

        This centralizes event routing logic used by Sim Day, Sim Week, and
        Sim to Phase End operations. Prevents code duplication.

        Args:
            event: Event dict from check_for_interactive_event()

        Returns:
            True if event handled successfully, False if user cancelled
        """
        event_type = event.get('event_type')
        params = event.get('data', {}).get('parameters', {})

        # Draft day event
        if event_type == 'DRAFT_DAY':
            return self._handle_draft_day_interactive(event)

        # Deadline events (franchise tag, roster cuts, cap compliance)
        elif event_type == 'DEADLINE':
            deadline_type = params.get('deadline_type')

            if deadline_type == 'FRANCHISE_TAG':
                return self._handle_franchise_tag_interactive(event)
            elif deadline_type == 'FINAL_ROSTER_CUTS':
                return self._handle_roster_cuts_interactive(event)
            elif deadline_type == 'SALARY_CAP_COMPLIANCE':
                return self._handle_cap_compliance_interactive(event)
            else:
                # Unknown deadline type - show info dialog and mark as handled
                return self._handle_generic_deadline_interactive(event, deadline_type)

        # Window events (free agency start)
        elif event_type == 'WINDOW':
            window_name = params.get('window_name')

            if window_name == 'FREE_AGENCY':
                return self._handle_free_agency_interactive(event)

        # Unknown event type - allow simulation to proceed
        return True

    def _on_skip_to_new_season(self):
        """Skip remaining offseason events and start new season."""
        # Build enhanced warning message
        warning_text = (
            "⚠️ WARNING: You are about to skip all remaining offseason events.\n\n"
            "The following interactive milestones will be AUTO-SIMULATED:\n\n"
            "• Franchise Tag Deadline\n"
            "• Free Agency Period\n"
            "• NFL Draft\n"
            "• Final Roster Cuts\n"
            "• Salary Cap Compliance\n\n"
            "You will NOT be able to:\n"
            "• Apply franchise tags to your players\n"
            "• Sign free agents\n"
            "• Make draft picks\n"
            "• Finalize roster cuts\n\n"
            "AI will make ALL decisions for your team during these events.\n\n"
            "Are you ABSOLUTELY SURE you want to skip the entire offseason?"
        )

        reply = QMessageBox.warning(
            self,
            "Skip to New Season - Confirmation Required",
            warning_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default to No for safety
        )

        if reply == QMessageBox.Yes:
            # Call simulation controller to skip to new season
            result = self.simulation_controller.simulate_to_new_season()

            if result.get('success', False):
                # Show success message
                msg = result.get('message', 'Successfully advanced to new season')
                QMessageBox.information(self, "Skip to New Season Complete", msg)

                # Refresh calendar view
                if hasattr(self, 'calendar_view'):
                    self.calendar_view.refresh_current_date()
            else:
                # Show error message
                error_msg = result.get('message', 'Unknown error occurred')
                QMessageBox.warning(self, "Skip to New Season Failed", error_msg)

    def _update_phase_button(self, phase: str):
        """
        Update phase-dependent UI elements based on current phase.

        Args:
            phase: Current phase ("preseason", "regular_season", "playoffs", "offseason")
        """
        # Update phase-end button text dynamically based on current phase
        if phase == "preseason":
            self.sim_phase_action.setText("Sim to Regular Season")
            self.sim_phase_action.setToolTip("Simulate rest of preseason")
        elif phase == "regular_season":
            self.sim_phase_action.setText("Sim to Playoffs")
            self.sim_phase_action.setToolTip("Simulate rest of regular season")
        elif phase == "playoffs":
            self.sim_phase_action.setText("Sim to Offseason")
            self.sim_phase_action.setToolTip("Simulate rest of playoffs")
        else:  # offseason
            # Get next milestone action from backend (returns detailed state info)
            action = self.simulation_controller.get_next_milestone_action()

            # Update button text from action
            self.sim_phase_action.setText(action["text"])

            # Update tooltip with detailed information
            self.sim_phase_action.setToolTip(action["tooltip"])

            # Enable/disable button based on action type
            self.sim_phase_action.setEnabled(action["enabled"])

            # Show "Skip to New Season" button
            self.skip_to_new_season_action.setVisible(True)

        # Hide "Skip to New Season" button during preseason, regular season, and playoffs
        if phase != "offseason":
            self.skip_to_new_season_action.setVisible(False)

    # Signal handlers for simulation updates
    def _on_date_changed(self, date_str: str):
        """Handle simulation date change."""
        from PySide6.QtWidgets import QApplication

        # Query fresh phase state (single source of truth)
        phase = self.simulation_controller.get_current_phase()

        print(f"[DEBUG MainWindow] _on_date_changed called: date={date_str}, phase={phase}")

        # Update date label
        self.date_label.setText(f"Date: {date_str}")

        # Format phase consistently with initial creation
        phase_display = phase.replace('_', ' ').title()
        current_week = self.simulation_controller.get_current_week()
        if current_week:
            phase_display += f" - Week {current_week}"
        self.phase_label.setText(f"Phase: {phase_display}")

        # Force immediate repaint of status bar widgets
        self.date_label.repaint()
        self.phase_label.repaint()
        self.statusBar().repaint()

        # Process pending Qt events to ensure UI updates are visible
        QApplication.processEvents()

        print(f"[DEBUG MainWindow] Status bar updated and repainted")

        # Update phase-dependent UI (button text, tab visibility)
        self._update_phase_button(phase)

        # Show/hide Playoffs tab based on phase
        # Show during playoffs and offseason, hide during preseason and regular season
        if phase in ["playoffs", "offseason"]:
            self.tabs.setTabVisible(self.playoff_tab_index, True)
            # Refresh view when entering playoffs or offseason phase
            if phase in ["playoffs", "offseason"] and hasattr(self, 'playoff_view'):
                self.playoff_view.refresh()
        else:  # preseason or regular_season
            self.tabs.setTabVisible(self.playoff_tab_index, False)

    def _refresh_status_bar(self):
        """
        Force refresh of status bar displays (date and phase).

        This is a helper method that can be called to manually update the status bar
        when automatic signal processing may be delayed or missed.
        """
        from PySide6.QtWidgets import QApplication

        # Get current state from controller
        current_date = self.simulation_controller.get_current_date()
        current_phase = self.simulation_controller.get_current_phase()

        # Update date label
        self.date_label.setText(f"Date: {current_date}")

        # Format phase with week info if available
        phase_display = current_phase.replace('_', ' ').title()
        current_week = self.simulation_controller.get_current_week()
        if current_week:
            phase_display += f" - Week {current_week}"
        self.phase_label.setText(f"Phase: {phase_display}")

        # Force immediate repaint
        self.date_label.repaint()
        self.phase_label.repaint()
        self.statusBar().repaint()

        # Process pending events
        QApplication.processEvents()

    def _on_games_played(self, game_results: list):
        """
        Handle games played signal.

        Refreshes team statistics widget to show newly simulated game data.
        This ensures statistics appear immediately without requiring app restart.

        Args:
            game_results: List of game results from simulation
        """
        # Refresh team statistics with fresh database connection
        if hasattr(self, 'team_view') and hasattr(self.team_view, 'statistics_tab'):
            self.team_view.statistics_tab.refresh()
            print(f"[DEBUG MainWindow] Team statistics refreshed after {len(game_results)} games")

        # Refresh transactions view to show newly simulated transactions
        if hasattr(self, 'transactions_view') and hasattr(self.transactions_view, 'transaction_widget'):
            self.transactions_view.transaction_widget.refresh()
            print(f"[DEBUG MainWindow] Transactions refreshed after {len(game_results)} games")

    def _on_checkpoint_saved(self, day_num: int, date_str: str):
        """
        Handle checkpoint saved signal during week simulation.

        Displays progress feedback in status bar as each day completes.
        Implements incremental persistence feedback for Issue #1.

        Args:
            day_num: Day number (1-7) that was just saved
            date_str: Date string for the saved checkpoint
        """
        # Update status bar with checkpoint progress
        formatted_date = self._format_date(date_str)
        self.statusBar().showMessage(
            f"Checkpoint saved: Day {day_num}/7 ({formatted_date})",
            2000  # 2 second timeout
        )
        print(f"[DEBUG MainWindow] Checkpoint {day_num}/7 saved: {date_str}")

    def _format_date(self, date_str: str) -> str:
        """Format date string for display (e.g., '2025-09-05' -> 'Sep 5, 2025')."""
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            return date_str

    def _format_date_range(self, start_date: str, end_date: str) -> str:
        """Format date range for display (e.g., 'Sep 5, 2025 - Sep 12, 2025')."""
        formatted_start = self._format_date(start_date)
        formatted_end = self._format_date(end_date)

        if formatted_start == formatted_end:
            return formatted_start
        return f"{formatted_start} - {formatted_end}"

    def _on_tab_changed(self, index: int):
        """Handle tab change - refresh data when switching to certain tabs."""
        if index == self.TAB_LEAGUE and hasattr(self, 'league_view'):
            self.league_view.load_standings()
        elif index == self.TAB_TRANSACTIONS and hasattr(self, 'transactions_view'):
            self.transactions_view.refresh()
        elif index == self.TAB_PLAYOFFS and hasattr(self, 'playoff_view'):
            self.playoff_view.refresh()

    def _refresh_views_after_simulation(self):
        """
        Refresh UI views after simulation completes.

        Consolidates view refresh logic used by Sim Day, Sim Week, and
        Sim to Phase End operations. Prevents code duplication.
        """
        # Refresh calendar view (re-sync date and reload events)
        if hasattr(self, 'calendar_view'):
            self.calendar_view.refresh_current_date()

        # Refresh playoff view if in playoffs or offseason
        if self.simulation_controller.get_current_phase() in ["playoffs", "offseason"]:
            if hasattr(self, 'playoff_view'):
                self.playoff_view.refresh()
