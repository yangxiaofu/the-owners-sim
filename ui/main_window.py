"""
Main Window for The Owner's Sim

OOTP-inspired main application window with tab-based navigation.
"""
import sys
import os

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar,
    QLabel, QMessageBox
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

# Add src to path for controller imports
ui_path = os.path.dirname(__file__)
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

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

    def __init__(self, db_path="data/database/nfl_simulation.db", dynasty_id="default", season=2025):
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

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

    def _create_controllers(self):
        """Initialize all controllers for data access."""
        # Season controller for season management and calendar operations
        self.season_controller = SeasonController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )

        # League controller for league-wide statistics and standings
        self.league_controller = LeagueController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )

        # Calendar controller for event management
        self.calendar_controller = CalendarController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )

        # Simulation controller for season progression
        self.simulation_controller = SimulationController(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )

        # Playoff controller for playoff bracket and seeding
        self.playoff_controller = PlayoffController(
            simulation_controller=self.simulation_controller
        )

        # Connect simulation signals to UI updates
        self.simulation_controller.date_changed.connect(self._on_date_changed)
        self.simulation_controller.games_played.connect(self._on_games_played)

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
            dynasty_id=self.dynasty_id,
            season=self.season
        )
        self.player_view = PlayerView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )
        self.offseason_view = OffseasonView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )
        self.league_view = LeagueView(self, controller=self.league_controller)
        self.playoff_view = PlayoffView(self, controller=self.playoff_controller)
        self.game_view = GameView(self)
        self.transactions_view = TransactionsView(
            self,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
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
        self.playoff_tab_index = 7  # Playoffs tab position (was 6, now 7 due to Transactions tab)

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
            lambda: self.tabs.setCurrentIndex(0),
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
            lambda: self.tabs.setCurrentIndex(2),
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
            lambda: self.tabs.setCurrentIndex(3),
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
            lambda: self.tabs.setCurrentIndex(5),
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
            lambda: self.tabs.setCurrentIndex(2),
            "Go to my team"
        ))
        self.toolbar.addAction(self._create_action(
            "Standings",
            self._show_standings,
            "View standings"
        ))
        self.toolbar.addAction(self._create_action(
            "League",
            lambda: self.tabs.setCurrentIndex(5),
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
        """Simulate one day."""
        result = self.simulation_controller.advance_day()

        if result['success']:
            # Show results
            msg = result['message']
            if result['games_played'] > 0:
                msg += f"\n\n{result['games_played']} games simulated"
            QMessageBox.information(self, "Simulation Complete", msg)

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
        """Simulate one week."""
        result = self.simulation_controller.advance_week()

        if result.get('success', False):
            # Show results
            msg = result.get('message', 'Week simulated successfully')
            games_played = result.get('games_played', 0)
            if games_played > 0:
                msg += f"\n\n{games_played} games simulated this week"

            QMessageBox.information(self, "Week Simulation Complete", msg)

            # Refresh calendar view (re-sync date and reload events)
            if hasattr(self, 'calendar_view'):
                self.calendar_view.refresh_current_date()

            # Refresh playoff view if playoffs tab is visible (playoffs or offseason)
            if self.simulation_controller.get_current_phase() in ["playoffs", "offseason"]:
                if hasattr(self, 'playoff_view'):
                    self.playoff_view.refresh()
        else:
            QMessageBox.warning(
                self,
                "Week Simulation Failed",
                result.get('message', 'Unknown error')
            )

    def _sim_to_phase_end(self):
        """Simulate to end of current phase with progress dialog."""
        from PySide6.QtWidgets import QProgressDialog, QApplication

        # Create progress dialog
        progress = QProgressDialog(
            "Simulating...",
            "Cancel",
            0,
            100,  # Will update max dynamically
            self
        )
        progress.setWindowTitle("Season Simulation")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately

        weeks_completed = 0

        # Progress callback
        def update_progress(week_num, games_played):
            nonlocal weeks_completed
            weeks_completed = week_num
            progress.setValue(week_num)
            progress.setLabelText(
                f"Simulating week {week_num}...\n{games_played} games simulated"
            )
            QApplication.processEvents()

            # Check if user cancelled
            if progress.wasCanceled():
                # TODO: Implement cancellation logic if needed
                pass

        # Execute simulation
        summary = self.simulation_controller.advance_to_end_of_phase(
            progress_callback=update_progress
        )

        progress.close()

        # Show summary dialog
        if summary.get('success', False):
            # Detect if this is a milestone stop (offseason) vs phase completion
            if 'milestone_reached' in summary:
                # Offseason milestone stop - show milestone details
                title = "Milestone Reached"
                msg = (
                    f"Stopped at: {summary['milestone_reached']}\n\n"
                    f"Milestone Type: {summary.get('milestone_type', 'N/A')}\n"
                    f"Milestone Date: {summary.get('milestone_date', 'N/A')}\n"
                    f"Days Advanced: {summary.get('days_simulated', 0)}\n\n"
                    f"Still in: {summary['ending_phase'].replace('_', ' ').title()}"
                )
            else:
                # Phase completion - show phase summary
                title = "Simulation Complete"
                phase_name = summary['starting_phase'].replace('_', ' ').title()

                # Determine next phase for message (use next_phase if available, otherwise ending_phase)
                next_phase_display = summary.get('next_phase', summary['ending_phase'])

                msg = (
                    f"{phase_name} Complete!\n\n"
                    f"Weeks Simulated: {summary['weeks_simulated']}\n"
                    f"Games Played: {summary['total_games']}\n"
                    f"End Date: {summary['end_date']}\n\n"
                    f"Now entering: {next_phase_display.replace('_', ' ').title()}"
                )
            QMessageBox.information(self, title, msg)

            # Automatically advance one day to trigger phase transition
            # This ensures the phase indicator updates correctly (e.g., Preseason → Regular Season)
            if summary.get('next_phase') and not summary.get('phase_transition'):
                # Only advance if we haven't already transitioned (stopped at phase boundary)
                self.simulation_controller.advance_day()

            # Refresh views
            if hasattr(self, 'calendar_view'):
                self.calendar_view.refresh_current_date()
            if hasattr(self, 'playoff_view') and summary['ending_phase'] == 'playoffs':
                self.playoff_view.refresh()
        else:
            QMessageBox.warning(
                self,
                "Simulation Failed",
                summary.get('message', 'Unknown error')
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
        # Switch to League tab (index 5)
        self.tabs.setCurrentIndex(5)

    def _show_stats_leaders(self):
        """Show statistical leaders by switching to League tab → Stats Leaders sub-tab."""
        # Switch to League tab (index 5)
        self.tabs.setCurrentIndex(5)
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
        import sys
        from pathlib import Path

        # Add src to path for imports
        src_path = Path(__file__).parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

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

    def _on_skip_to_new_season(self):
        """Skip remaining offseason events and start new season."""
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Skip to New Season",
            "Are you sure you want to skip the remaining offseason?\n\n"
            "This will simulate all pending offseason events and advance to the new season.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
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
            # Get next milestone name from backend
            next_milestone = self.simulation_controller.get_next_milestone_name()

            # Update "Sim to Phase End" button text
            self.sim_phase_action.setText(f"Sim to {next_milestone}")
            self.sim_phase_action.setToolTip(f"Simulate to next offseason milestone: {next_milestone}")

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

    def _on_tab_changed(self, index: int):
        """Handle tab change - refresh data when switching to certain tabs."""
        # League tab (index 5) - refresh standings
        if index == 5 and hasattr(self, 'league_view'):
            self.league_view.load_standings()

        # Transactions tab (index 6) - refresh transaction history
        elif index == 6 and hasattr(self, 'transactions_view'):
            self.transactions_view.refresh()

        # Playoffs tab (index 7) - refresh bracket and seeding
        elif index == 7 and hasattr(self, 'playoff_view'):
            self.playoff_view.refresh()
