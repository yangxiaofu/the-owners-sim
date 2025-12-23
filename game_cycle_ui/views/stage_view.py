"""
Stage View for The Owner's Sim (Game Cycle)

Displays current stage and provides controls for stage-based progression.
"""

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QFrame, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTabWidget,
    QApplication, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import TABLE_HEADER_STYLE, TAB_STYLE, Typography, FontSizes, TextColors, apply_table_style, PRIMARY_BUTTON_STYLE
from game_cycle import Stage, StageType, SeasonPhase
from game_cycle_ui.widgets.expandable_game_row import ExpandableGameRow


class StageView(QWidget):
    """
    Stage-based progression view.

    Shows:
    - Current stage (e.g., "Week 5" or "Wild Card")
    - Stage preview (upcoming games with team records)
    - Game results after simulation
    - Current standings
    - Advance button to progress to next stage
    - Season progress indicator

    Signals:
        stage_advance_requested: Emitted when user clicks Simulate
        skip_to_playoffs_requested: Emitted when user clicks Skip to Playoffs
        skip_to_offseason_requested: Emitted when user clicks Skip to Offseason
    """

    stage_advance_requested = Signal()
    stage_executed = Signal(dict)
    skip_to_playoffs_requested = Signal()
    skip_to_offseason_requested = Signal()
    week_navigation_requested = Signal(int)  # Emits week number for navigation
    navigate_to_offseason_requested = Signal()  # Emitted when user wants to navigate to Offseason tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._logger = logging.getLogger(__name__)

        self._current_stage: Optional[Stage] = None
        self._preview_data: Dict[str, Any] = {}
        self._last_results: List[Dict[str, Any]] = []

        # Context for BoxScoreDialog (set via set_context)
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None

        # Cache for GameResult objects (for play-by-play access)
        # Maps game_id -> GameResult
        self._game_results_cache: Dict[str, Any] = {}

        # Week navigation state
        self._display_week: int = 1   # Week currently being displayed
        self._current_week: int = 1   # Actual current stage week
        self._max_week: int = 22      # Maximum week (18 regular + 4 playoff weeks)

        # Expandable game rows (replaces games_table)
        self._game_rows: List[ExpandableGameRow] = []
        self._games_container: Optional[QWidget] = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header with current stage
        self._create_header(layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Games section (now takes full width)
        middle_panel = self._create_middle_panel()
        splitter.addWidget(middle_panel)

        layout.addWidget(splitter, 1)  # Stretch factor = 1 (expand to fill space)

        # Progress bar at bottom
        self._create_progress_bar(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header showing current stage."""
        header_frame = QFrame()
        header_frame.setContentsMargins(8, 4, 8, 4)  # Compact margins
        header_layout = QHBoxLayout(header_frame)
        header_layout.setSpacing(12)  # Compact spacing

        # Season year
        self.season_label = QLabel("2025 Season")
        Typography.apply(self.season_label, Typography.H5)
        header_layout.addWidget(self.season_label)

        header_layout.addStretch()

        # Current stage (compact, centered)
        self.stage_label = QLabel("Week 1")
        Typography.apply(self.stage_label, Typography.H3)  # Reduced from H1
        self.stage_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.stage_label)

        header_layout.addStretch()

        # Phase indicator
        self.phase_label = QLabel("Regular Season")
        Typography.apply(self.phase_label, Typography.H5)
        self.phase_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        header_layout.addWidget(self.phase_label)

        header_layout.addStretch()

        # Simulation button (follows playoff view pattern)
        self.simulate_btn = QPushButton("Game Day ▶")
        self.simulate_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.simulate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.simulate_btn.setMinimumWidth(150)
        self.simulate_btn.clicked.connect(self._on_simulate_clicked)
        header_layout.addWidget(self.simulate_btn)

        parent_layout.addWidget(header_frame)

    def _create_middle_panel(self) -> QGroupBox:
        """Create middle panel with expandable game rows."""
        group = QGroupBox("Games")
        layout = QVBoxLayout(group)

        # Week navigation header
        nav_layout = QHBoxLayout()

        self.prev_week_btn = QPushButton("< Prev Week")
        self.prev_week_btn.clicked.connect(self._on_prev_week)
        self.prev_week_btn.setEnabled(False)  # Week 1 starts disabled
        nav_layout.addWidget(self.prev_week_btn)

        self.week_display_label = QLabel("Week 1")
        self.week_display_label.setAlignment(Qt.AlignCenter)
        Typography.apply(self.week_display_label, Typography.BODY)
        self.week_display_label.setFont(QFont(self.week_display_label.font().family(), self.week_display_label.font().pointSize(), QFont.Bold))
        nav_layout.addWidget(self.week_display_label, stretch=1)

        self.next_week_btn = QPushButton("Next Week >")
        self.next_week_btn.clicked.connect(self._on_next_week)
        nav_layout.addWidget(self.next_week_btn)

        layout.addLayout(nav_layout)

        # Scrollable container for expandable game rows
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Container widget to hold game rows
        self._games_container = QWidget()
        self._games_layout = QVBoxLayout(self._games_container)
        self._games_layout.setSpacing(10)
        self._games_layout.setContentsMargins(0, 0, 0, 0)
        self._games_layout.addStretch()  # Push rows to top

        scroll_area.setWidget(self._games_container)
        layout.addWidget(scroll_area, 1)  # Stretch factor = 1 (expand to fill GroupBox)

        return group

    def _create_progress_bar(self, parent_layout: QVBoxLayout):
        """Create season progress bar."""
        progress_frame = QFrame()
        progress_layout = QHBoxLayout(progress_frame)

        progress_label = QLabel("Season Progress:")
        progress_layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% complete")
        progress_layout.addWidget(self.progress_bar, stretch=1)

        parent_layout.addWidget(progress_frame)

    # Public methods for controller to call

    def set_current_stage(self, stage: Stage):
        """Update the display with current stage info."""
        self._current_stage = stage

        self.stage_label.setText(stage.display_name)
        self.season_label.setText(f"{stage.season_year} Season")
        self.phase_label.setText(stage.phase.name.replace("_", " ").title())

        # Update progress bar
        progress = self._calculate_progress(stage)
        self.progress_bar.setValue(progress)

        # Update simulate button
        if hasattr(self, 'simulate_btn'):
            self.simulate_btn.setEnabled(True)

            # Update button text based on stage
            from game_cycle_ui.widgets.stage_action_mapping import get_simulate_button_text
            button_text = get_simulate_button_text(stage)
            self.simulate_btn.setText(button_text)

        # Note: Advance button and skip buttons removed from left panel
        # Will be added to menu bar in future update

    def set_preview(self, preview_data: Dict[str, Any]):
        """Update the games panel with expandable game rows or offseason info."""
        self._preview_data = preview_data

        # Check if we're in offseason mode (no matchups, has stage_name)
        # BUT preseason game stages should be treated as game stages (they have matchups)
        is_preseason_game = (
            self._current_stage and
            self._current_stage.stage_type in (
                StageType.OFFSEASON_PRESEASON_W1,
                StageType.OFFSEASON_PRESEASON_W2,
                StageType.OFFSEASON_PRESEASON_W3
            )
        )

        if self._current_stage and self._current_stage.phase == SeasonPhase.OFFSEASON and not is_preseason_game:
            self._show_offseason_preview(preview_data)
            return

        matchups = preview_data.get("matchups", [])

        # Filter out invalid matchups (require both abbreviation AND team_id for each team)
        valid_matchups = []
        for m in matchups:
            away = m.get("away_team", {})
            home = m.get("home_team", {})
            # Require both teams have abbreviation AND team_id to prevent malformed rows
            if (away.get("abbreviation") and away.get("team_id") and
                home.get("abbreviation") and home.get("team_id")):
                valid_matchups.append(m)
            else:
                self._logger.warning(f"Skipping malformed matchup: game_id={m.get('game_id')}, "
                                    f"away={away.get('abbreviation')}/{away.get('team_id')}, "
                                    f"home={home.get('abbreviation')}/{home.get('team_id')}")

        # Clear existing game rows
        for row in self._game_rows:
            row.deleteLater()
        self._game_rows.clear()

        # Create expandable game row for each matchup
        for matchup in valid_matchups:
            # Create game row widget
            game_row = ExpandableGameRow(matchup, parent=self._games_container)

            # Connect info clicked signal to show box score dialog
            game_row.info_clicked.connect(self._on_game_info_clicked)

            # Add to layout (insert before stretch)
            self._games_layout.insertWidget(len(self._game_rows), game_row)
            self._game_rows.append(game_row)

    def update_preview_data(self, preview_data: Dict[str, Any]):
        """
        Update preview data without rebuilding the game rows.

        This is used after simulation to update internal data (for box score dialog)
        while preserving the existing UI state with results and top performers.

        Args:
            preview_data: Preview data dict with matchups, stage info, etc.
        """
        self._preview_data = preview_data

    def _on_game_info_clicked(self, game_id: str):
        """Handle info button clicked on a game row - show box score dialog."""
        # Find the matchup data for this game
        matchups = self._preview_data.get("matchups", [])
        for matchup in matchups:
            if matchup.get('game_id') == game_id:
                # Build game data dict for BoxScoreDialog
                away_team = matchup.get("away_team", {})
                home_team = matchup.get("home_team", {})

                game_data = {
                    'game_id': game_id,
                    'home_team': {
                        'id': home_team.get('team_id') or home_team.get('id'),
                        'name': home_team.get('name', 'Home'),
                        'abbr': home_team.get('abbreviation', '???')
                    },
                    'away_team': {
                        'id': away_team.get('team_id') or away_team.get('id'),
                        'name': away_team.get('name', 'Away'),
                        'abbr': away_team.get('abbreviation', '???')
                    },
                    'home_score': matchup.get('home_score'),
                    'away_score': matchup.get('away_score'),
                    'is_played': matchup.get('is_played', False)
                }

                # Call the existing box score dialog handler
                self._show_box_score_dialog(game_data)
                break

    def _show_box_score_dialog(self, game_data: Dict[str, Any]):
        """Show box score dialog for a game."""
        if not game_data.get('is_played'):
            return  # Don't show dialog for unplayed games

        try:
            from game_cycle_ui.dialogs.box_score_dialog import BoxScoreDialog

            dialog = BoxScoreDialog(
                game_id=game_data['game_id'],
                home_team=game_data['home_team'],
                away_team=game_data['away_team'],
                home_score=game_data['home_score'],
                away_score=game_data['away_score'],
                dynasty_id=self._dynasty_id,
                db_path=self._db_path,
                parent=self
            )
            dialog.exec()
        except Exception as e:
            self._logger.error(f"Error showing box score dialog: {e}", exc_info=True)

    def update_with_results(self, results: List[Dict[str, Any]]):
        """
        Update expandable game rows with post-simulation results.

        Called by StageController after week simulation completes.
        Updates rows with scores and top performers, then auto-expands them.

        Args:
            results: List of result dicts with structure:
                {
                    'game_id': str,
                    'home_score': int,
                    'away_score': int,
                    'top_performers': {
                        'home': [player_dict, ...],
                        'away': [player_dict, ...]
                    },
                    'game_stats': {...}  # Optional
                }
        """
        # Key by team IDs (game_id formats differ between events/games tables)
        results_map = {}
        for r in results:
            key = (r.get('home_team_id'), r.get('away_team_id'))
            results_map[key] = r

        # Update each game row with its result
        for game_row in self._game_rows:
            home_id = game_row.game_data.get('home_team', {}).get('team_id')
            away_id = game_row.game_data.get('away_team', {}).get('team_id')
            result_data = results_map.get((home_id, away_id))
            if result_data:
                # Update the row (will auto-expand if collapsed)
                game_row.update_with_result(result_data)

    def set_standings(self, standings: List[Dict[str, Any]]):
        """
        No-op: Standings are no longer displayed in this view.

        Standings tables were removed to make room for expanded game view.
        Standings are available in the League view (separate tab).
        """
        pass

    def set_status(self, message: str, is_error: bool = False):
        """Update the status message."""
        # Note: Status label removed from left panel
        # Using logger for debugging until status bar is implemented
        if is_error:
            self._logger.error(f"StageView: {message}")
        else:
            self._logger.info(f"StageView: {message}")

    def set_advance_enabled(self, enabled: bool, tooltip: str = ""):
        """Enable/disable the advance button with optional tooltip."""
        # Note: Advance button removed from left panel
        # Will be added to menu bar in future update
        self._logger.debug(f"Advance button {'enabled' if enabled else 'disabled'}{f' - {tooltip}' if tooltip else ''}")

    def show_execution_result(self, result: Dict[str, Any]):
        """Display results after stage execution."""
        # Restore normal cursor after simulation completes
        QApplication.restoreOverrideCursor()

        completed_stage = result.get("stage_name", "Unknown")

        games = result.get("games_played", [])
        events = result.get("events_processed", [])

        if games:
            self.set_status(f"✓ {completed_stage}: {len(games)} games played")
        elif events:
            self.set_status(f"✓ {completed_stage}: {len(events)} events processed")
        else:
            self.set_status(f"✓ {completed_stage} completed")

        self.stage_executed.emit(result)

    # Private methods

    def _calculate_progress(self, stage: Stage) -> int:
        """
        Calculate season progress percentage.

        There are 31 total stages:
        - 3 preseason weeks
        - 18 regular season weeks
        - 4 playoff rounds
        - 6 offseason phases
        """
        all_stages = list(StageType)
        try:
            current_index = all_stages.index(stage.stage_type)
            total = len(all_stages)
            return int(((current_index + 1) / total) * 100)
        except (ValueError, ZeroDivisionError):
            return 0

    def _on_advance_clicked(self):
        """Handle advance button click."""
        # Check if we're in offseason phase (but exclude Preseason)
        if (self._current_stage and
            self._current_stage.phase == SeasonPhase.OFFSEASON):

            # OFFSEASON_OWNER requires using the Owner tab's Continue button
            if self._current_stage.stage_type == StageType.OFFSEASON_OWNER:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Owner Review Required",
                    "Please complete your owner decisions in the Owner tab, "
                    "then click 'Continue to Franchise Tag'.\n\n"
                    "Switch to the Owner tab to proceed."
                )
                return

            # Navigate to Offseason tab instead of executing
            self.navigate_to_offseason_requested.emit()
            return

        # Regular season/playoffs/preseason: execute as normal
        self.set_advance_enabled(False)
        self.set_status("Simulating games... please wait")

        # Show busy cursor so user knows processing is happening
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()  # Force UI update before blocking execution

        self.stage_advance_requested.emit()

    def _on_simulate_clicked(self):
        """Handle simulate button click."""
        # Disable button during simulation
        self.simulate_btn.setEnabled(False)
        self.simulate_btn.setText("Simulating...")

        # Emit signal that controller is listening for
        self.stage_advance_requested.emit()

    def _on_skip_to_playoffs(self):
        """Skip ahead to playoffs."""
        self.set_advance_enabled(False)
        self.set_status("Simulating to playoffs...")
        self.skip_to_playoffs_requested.emit()

    def _on_skip_to_offseason(self):
        """Skip ahead to offseason."""
        self.set_advance_enabled(False)
        self.set_status("Simulating to offseason...")
        self.skip_to_offseason_requested.emit()

    def _show_offseason_preview(self, preview_data: Dict[str, Any]):
        """Show offseason stage preview instead of game matchups."""
        # Extract offseason info
        stage_name = preview_data.get("stage_name", "Offseason")
        description = preview_data.get("description", "")

        # Clear existing game rows
        for row in self._game_rows:
            row.deleteLater()
        self._game_rows.clear()

        # Create informational message widget
        message_widget = QLabel()
        message_widget.setText(f"{stage_name}\n\n{description}\n\nSee the Offseason tab for more details.")
        message_widget.setAlignment(Qt.AlignCenter)
        message_widget.setWordWrap(True)
        message_widget.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; padding: 40px;")
        Typography.apply(message_widget, Typography.BODY)

        # Add to games container (insert at index 0, before stretch)
        self._games_layout.insertWidget(0, message_widget)

    def set_context(self, dynasty_id: str, db_path: str):
        """Store dynasty context for BoxScoreDialog access."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def store_game_results(self, games_played: List[Dict[str, Any]]):
        """
        Store GameResult objects from executed games for play-by-play access.

        Args:
            games_played: List of game dicts, each with optional 'game_result' field
        """
        self._logger.debug(f"store_game_results called with {len(games_played)} games")
        for game in games_played:
            game_id = game.get('game_id')
            game_result = game.get('game_result')
            self._logger.debug(f"Game {game_id}: has game_result={game_result is not None}")
            if game_id and game_result:
                self._game_results_cache[game_id] = game_result
                self._logger.debug(f"✓ Cached GameResult for {game_id}")
                self._logger.debug(f"GameResult has drives: {hasattr(game_result, 'drives')}")
            else:
                self._logger.debug(f"✗ NOT caching {game_id} - missing game_id or game_result")

    # Week navigation handlers

    def _on_prev_week(self):
        """Navigate to previous week."""
        if self._display_week > 1:
            self._display_week -= 1
            self._refresh_week_display()

    def _on_next_week(self):
        """Navigate to next week."""
        if self._display_week < self._max_week:
            self._display_week += 1
            self._refresh_week_display()

    def _refresh_week_display(self):
        """Refresh games table for the displayed week."""
        self.week_display_label.setText(self._get_week_label(self._display_week))

        # Update button states
        self.prev_week_btn.setEnabled(self._display_week > 1)
        self.next_week_btn.setEnabled(self._display_week < self._max_week)

        # Emit signal to request preview data for displayed week
        self.week_navigation_requested.emit(self._display_week)

    def _get_week_label(self, week: int) -> str:
        """
        Get display label for a week number.

        Regular season weeks 1-18 show "Week N".
        Playoff weeks 19-22 show the round name.

        Args:
            week: Week number (1-22)

        Returns:
            Display label for the week
        """
        PLAYOFF_LABELS = {
            19: "Wild Card",
            20: "Divisional",
            21: "Conference Championship",
            22: "Super Bowl"
        }
        if week in PLAYOFF_LABELS:
            return PLAYOFF_LABELS[week]
        return f"Week {week}"

    def set_week_navigation_state(self, current_week: int, display_week: int = None):
        """
        Update week navigation state (called by controller).

        Args:
            current_week: The actual current stage week (1-22, includes playoff weeks)
            display_week: The week to display (defaults to current_week)
        """
        self._current_week = current_week
        self._display_week = display_week if display_week is not None else current_week

        # Update UI with proper label (handles playoff week names)
        self.week_display_label.setText(self._get_week_label(self._display_week))
        self.prev_week_btn.setEnabled(self._display_week > 1)
        self.next_week_btn.setEnabled(self._display_week < self._max_week)

    def set_week_navigation_visible(self, visible: bool):
        """Show/hide week navigation controls (hide during playoffs/offseason)."""
        self.prev_week_btn.setVisible(visible)
        self.week_display_label.setVisible(visible)
        self.next_week_btn.setVisible(visible)
