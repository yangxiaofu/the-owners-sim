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
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont

from game_cycle_ui.views.stage_view import StageView
from game_cycle_ui.views.playoff_bracket_view import PlayoffBracketView
from game_cycle_ui.controllers.stage_controller import StageUIController
from src.game_cycle import Stage, StageType, SeasonPhase


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
        self.stage_controller = StageUIController(
            database_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self._season,
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
        self.tabs.addTab(self.stage_view, "Season")

        # Placeholder tabs for future views
        placeholder_label = QLabel("Team view - coming soon")
        placeholder_label.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(placeholder_label, "Team")

        placeholder_label2 = QLabel("Players view - coming soon")
        placeholder_label2.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(placeholder_label2, "Players")

        placeholder_label3 = QLabel("League view - coming soon")
        placeholder_label3.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(placeholder_label3, "League")

        # Playoff Bracket View
        self.playoff_view = PlayoffBracketView(parent=self)
        self.tabs.addTab(self.playoff_view, "Playoffs")

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
            lambda: self.stage_controller.jump_to_stage(StageType.OFFSEASON_RESIGNING)
        )
        toolbar.addAction(jump_offseason_action)

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

        # Connect to stage changes
        self.stage_controller.stage_changed.connect(self._update_statusbar)
        self.stage_controller.stage_changed.connect(self._update_playoff_bracket)

    def _initialize(self):
        """Initialize the window state."""
        self.stage_controller.refresh()

    def _update_statusbar(self, stage: Stage):
        """Update status bar when stage changes."""
        self.stage_status.setText(stage.display_name)
        self.season_status.setText(f"{stage.season_year} Season")
        self.phase_status.setText(stage.phase.name.replace("_", " ").title())

    def _update_playoff_bracket(self, stage: Stage):
        """Update playoff bracket view when stage changes."""
        # Always update playoff view - show empty if no playoff games yet
        bracket_data = self.stage_controller.get_playoff_bracket()
        self.playoff_view.set_bracket_data(bracket_data)

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
