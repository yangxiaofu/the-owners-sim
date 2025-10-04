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
from ui.views.team_view import TeamView
from ui.views.player_view import PlayerView
from ui.views.offseason_view import OffseasonView
from ui.views.league_view import LeagueView
from ui.views.game_view import GameView


class MainWindow(QMainWindow):
    """
    Main application window with OOTP-style tab navigation.

    Features:
    - Tab-based primary navigation (Season, Team, Player, Offseason, League, Game)
    - Menu bar with Game, Season, Team, League, Tools, Help menus
    - Toolbar with quick actions
    - Status bar displaying current date and phase
    """

    def __init__(self, db_path="data/database/nfl_simulation.db", dynasty_id="default"):
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id

        # Window setup
        self.setWindowTitle("The Owner's Sim")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 700)

        # Create UI components
        self._create_central_widget()
        self._create_menus()
        self._create_toolbar()
        self._create_statusbar()

    def _create_central_widget(self):
        """Create central tab widget with primary views."""
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)  # Fixed tab order like OOTP
        self.tabs.setDocumentMode(True)  # Cleaner look

        # Create views
        self.season_view = SeasonView(self)
        self.team_view = TeamView(self)
        self.player_view = PlayerView(self)
        self.offseason_view = OffseasonView(self)
        self.league_view = LeagueView(self)
        self.game_view = GameView(self)

        # Add tabs
        self.tabs.addTab(self.season_view, "Season")
        self.tabs.addTab(self.team_view, "Team")
        self.tabs.addTab(self.player_view, "Player")
        self.tabs.addTab(self.offseason_view, "Offseason")
        self.tabs.addTab(self.league_view, "League")
        self.tabs.addTab(self.game_view, "Game")

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
            lambda: self.tabs.setCurrentIndex(1),
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
            lambda: self.tabs.setCurrentIndex(2),
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
            lambda: self.tabs.setCurrentIndex(4),
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
            lambda: self.tabs.setCurrentIndex(1),
            "Go to my team"
        ))
        toolbar.addAction(self._create_action(
            "Standings",
            self._show_standings,
            "View standings"
        ))
        toolbar.addAction(self._create_action(
            "League",
            lambda: self.tabs.setCurrentIndex(4),
            "View league stats"
        ))

    def _create_statusbar(self):
        """Create status bar with current date and phase."""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        # Current date label
        self.date_label = QLabel("Date: Sep 5, 2024")
        self.date_label.setStyleSheet("padding: 0 10px;")

        # Current phase label
        self.phase_label = QLabel("Phase: Regular Season - Week 1")
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
        QMessageBox.information(
            self,
            "Simulate Day",
            "Day simulation coming in Phase 2!\n\nThis will advance the calendar by one day and simulate all games."
        )

    def _sim_week(self):
        """Simulate one week."""
        QMessageBox.information(
            self,
            "Simulate Week",
            "Week simulation coming in Phase 2!\n\nThis will advance the calendar by one week and simulate all games."
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
        """Show league standings."""
        QMessageBox.information(
            self,
            "Standings",
            "Standings coming in Phase 2!\n\nView division and conference standings with playoff picture."
        )

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
