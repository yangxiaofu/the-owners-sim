"""
Main Window for The Owner's Sim

OOTP-inspired main application window with tab-based navigation.
"""
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

import sys
import os

# Add src to path for controller imports
ui_path = os.path.dirname(__file__)
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from controllers.season_controller import SeasonController
from controllers.calendar_controller import CalendarController
from controllers.simulation_controller import SimulationController
from controllers.league_controller import LeagueController


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
        self.player_view = PlayerView(self)
        self.offseason_view = OffseasonView(self)
        self.league_view = LeagueView(self, controller=self.league_controller)
        self.game_view = GameView(self)

        # Add tabs
        self.tabs.addTab(self.season_view, "Season")
        self.tabs.addTab(self.calendar_view, "Calendar")
        self.tabs.addTab(self.team_view, "Team")
        self.tabs.addTab(self.player_view, "Player")
        self.tabs.addTab(self.offseason_view, "Offseason")
        self.tabs.addTab(self.league_view, "League")
        self.tabs.addTab(self.game_view, "Game")

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
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Simulation controls
        toolbar.addAction(self._create_action(
            "Sim Day",
            self._sim_day,
            "Simulate one day"
        ))
        toolbar.addAction(self._create_action(
            "Sim Week",
            self._sim_week,
            "Simulate one week"
        ))
        toolbar.addSeparator()

        # Quick navigation
        toolbar.addAction(self._create_action(
            "My Team",
            lambda: self.tabs.setCurrentIndex(2),
            "Go to my team"
        ))
        toolbar.addAction(self._create_action(
            "Standings",
            self._show_standings,
            "View standings"
        ))
        toolbar.addAction(self._create_action(
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

            # Refresh calendar view
            if hasattr(self, 'calendar_view'):
                self.calendar_view.load_events()
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

            # Refresh calendar view
            if hasattr(self, 'calendar_view'):
                self.calendar_view.load_events()
        else:
            QMessageBox.warning(
                self,
                "Week Simulation Failed",
                result.get('message', 'Unknown error')
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
        """Show statistical leaders."""
        QMessageBox.information(
            self,
            "Stats Leaders",
            "Stats Leaders coming in Phase 3!\n\nView league leaders in all statistical categories."
        )

    def _show_playoff_picture(self):
        """Show playoff picture."""
        QMessageBox.information(
            self,
            "Playoff Picture",
            "Playoff Picture coming in Phase 2!\n\nView current playoff seeding and scenarios."
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

    # Signal handlers for simulation updates
    def _on_date_changed(self, date_str: str, phase: str):
        """Handle simulation date change."""
        # Update status bar
        self.date_label.setText(f"Date: {date_str}")
        self.phase_label.setText(f"Phase: {phase}")

    def _on_games_played(self, game_results: list):
        """Handle games played signal."""
        # Could show game results notification here if desired
        pass

    def _on_tab_changed(self, index: int):
        """Handle tab change - refresh data when switching to certain tabs."""
        # League tab (index 5) - refresh standings
        if index == 5 and hasattr(self, 'league_view'):
            self.league_view.load_standings()
