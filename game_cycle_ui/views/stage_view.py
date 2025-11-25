"""
Stage View for The Owner's Sim (Game Cycle)

Displays current stage and provides controls for stage-based progression.
"""

from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QFrame, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from src.game_cycle import Stage, StageType, SeasonPhase


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        self._current_stage: Optional[Stage] = None
        self._preview_data: Dict[str, Any] = {}
        self._last_results: List[Dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header with current stage
        self._create_header(layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Stage info and controls
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Middle: Preview/Results of games
        middle_panel = self._create_middle_panel()
        splitter.addWidget(middle_panel)

        # Right: Standings
        right_panel = self._create_standings_panel()
        splitter.addWidget(right_panel)

        # Set stretch factors
        splitter.setStretchFactor(0, 1)  # Left: controls
        splitter.setStretchFactor(1, 2)  # Middle: games
        splitter.setStretchFactor(2, 2)  # Right: standings

        layout.addWidget(splitter)

        # Progress bar at bottom
        self._create_progress_bar(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header showing current stage."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)

        # Season year
        self.season_label = QLabel("2025 Season")
        self.season_label.setFont(QFont("Arial", 14))
        header_layout.addWidget(self.season_label)

        header_layout.addStretch()

        # Current stage (large, centered)
        self.stage_label = QLabel("Week 1")
        self.stage_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.stage_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.stage_label)

        header_layout.addStretch()

        # Phase indicator
        self.phase_label = QLabel("Regular Season")
        self.phase_label.setFont(QFont("Arial", 14))
        self.phase_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.phase_label)

        parent_layout.addWidget(header_frame)

    def _create_left_panel(self) -> QGroupBox:
        """Create left panel with stage controls."""
        group = QGroupBox("Stage Controls")
        layout = QVBoxLayout(group)

        # Advance button
        self.advance_button = QPushButton("Simulate Stage")
        self.advance_button.setMinimumHeight(50)
        self.advance_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.advance_button.clicked.connect(self._on_advance_clicked)
        layout.addWidget(self.advance_button)

        # Status message
        self.status_label = QLabel("Ready to simulate")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; padding: 8px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Quick actions
        actions_label = QLabel("Quick Actions")
        actions_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(actions_label)

        self.skip_to_playoffs_btn = QPushButton("Skip to Playoffs")
        self.skip_to_playoffs_btn.clicked.connect(self._on_skip_to_playoffs)
        layout.addWidget(self.skip_to_playoffs_btn)

        self.skip_to_offseason_btn = QPushButton("Skip to Offseason")
        self.skip_to_offseason_btn.clicked.connect(self._on_skip_to_offseason)
        layout.addWidget(self.skip_to_offseason_btn)

        return group

    def _create_middle_panel(self) -> QGroupBox:
        """Create middle panel with games preview/results."""
        group = QGroupBox("Games")
        layout = QVBoxLayout(group)

        # Games table
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(5)
        self.games_table.setHorizontalHeaderLabels(["Away", "Record", "@", "Home", "Record"])
        self.games_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.games_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.games_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.games_table.setAlternatingRowColors(True)
        layout.addWidget(self.games_table)

        return group

    def _create_standings_panel(self) -> QGroupBox:
        """Create right panel with standings."""
        group = QGroupBox("Standings (Top 16)")
        layout = QVBoxLayout(group)

        # Standings table
        self.standings_table = QTableWidget()
        self.standings_table.setColumnCount(6)
        self.standings_table.setHorizontalHeaderLabels(["#", "Team", "W", "L", "PCT", "PD"])
        self.standings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.standings_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.standings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.standings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.standings_table.setAlternatingRowColors(True)
        layout.addWidget(self.standings_table)

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

        # Update button text based on stage type
        if stage.phase == SeasonPhase.OFFSEASON:
            self.advance_button.setText(f"Process {stage.display_name}")
        else:
            self.advance_button.setText(f"Simulate {stage.display_name}")

        # Enable/disable skip buttons based on current phase
        self.skip_to_playoffs_btn.setEnabled(stage.phase == SeasonPhase.REGULAR_SEASON)
        self.skip_to_offseason_btn.setEnabled(stage.phase in (SeasonPhase.REGULAR_SEASON, SeasonPhase.PLAYOFFS))

    def set_preview(self, preview_data: Dict[str, Any]):
        """Update the games panel with matchups or offseason info."""
        self._preview_data = preview_data

        # Check if we're in offseason mode (no matchups, has stage_name)
        if self._current_stage and self._current_stage.phase == SeasonPhase.OFFSEASON:
            self._show_offseason_preview(preview_data)
            return

        matchups = preview_data.get("matchups", [])
        self.games_table.setRowCount(len(matchups))

        for row, matchup in enumerate(matchups):
            away_team = matchup.get("away_team", {})
            home_team = matchup.get("home_team", {})

            # Away team
            away_name = away_team.get("abbreviation", "???")
            away_record = away_team.get("record", "0-0")

            # Home team
            home_name = home_team.get("abbreviation", "???")
            home_record = home_team.get("record", "0-0")

            # Scores if played
            is_played = matchup.get("is_played", False)
            home_score = matchup.get("home_score")
            away_score = matchup.get("away_score")

            # Create items
            away_item = QTableWidgetItem(away_name)
            away_record_item = QTableWidgetItem(away_record)
            at_item = QTableWidgetItem("@")
            at_item.setTextAlignment(Qt.AlignCenter)
            home_item = QTableWidgetItem(home_name)
            home_record_item = QTableWidgetItem(home_record)

            # Style based on played status
            if is_played and home_score is not None and away_score is not None:
                # Show scores
                away_item.setText(f"{away_name} ({away_score})")
                home_item.setText(f"{home_name} ({home_score})")

                # Highlight winner
                if home_score > away_score:
                    home_item.setForeground(QColor("green"))
                    home_item.setFont(QFont("Arial", -1, QFont.Bold))
                elif away_score > home_score:
                    away_item.setForeground(QColor("green"))
                    away_item.setFont(QFont("Arial", -1, QFont.Bold))

            self.games_table.setItem(row, 0, away_item)
            self.games_table.setItem(row, 1, away_record_item)
            self.games_table.setItem(row, 2, at_item)
            self.games_table.setItem(row, 3, home_item)
            self.games_table.setItem(row, 4, home_record_item)

    def set_standings(self, standings: List[Dict[str, Any]]):
        """Update the standings table."""
        # Show top 16 teams
        top_standings = standings[:16]
        self.standings_table.setRowCount(len(top_standings))

        for row, team in enumerate(top_standings):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)

            team_item = QTableWidgetItem(team.get("abbreviation", "???"))
            wins_item = QTableWidgetItem(str(team.get("wins", 0)))
            wins_item.setTextAlignment(Qt.AlignCenter)
            losses_item = QTableWidgetItem(str(team.get("losses", 0)))
            losses_item.setTextAlignment(Qt.AlignCenter)
            pct_item = QTableWidgetItem(team.get("win_pct", ".000"))
            pct_item.setTextAlignment(Qt.AlignCenter)

            pd = team.get("point_diff", 0)
            pd_text = f"+{pd}" if pd > 0 else str(pd)
            pd_item = QTableWidgetItem(pd_text)
            pd_item.setTextAlignment(Qt.AlignCenter)
            if pd > 0:
                pd_item.setForeground(QColor("green"))
            elif pd < 0:
                pd_item.setForeground(QColor("red"))

            self.standings_table.setItem(row, 0, rank_item)
            self.standings_table.setItem(row, 1, team_item)
            self.standings_table.setItem(row, 2, wins_item)
            self.standings_table.setItem(row, 3, losses_item)
            self.standings_table.setItem(row, 4, pct_item)
            self.standings_table.setItem(row, 5, pd_item)

    def set_status(self, message: str, is_error: bool = False):
        """Update the status message."""
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet("color: red; padding: 8px;")
        else:
            self.status_label.setStyleSheet("color: #666; padding: 8px;")

    def set_advance_enabled(self, enabled: bool):
        """Enable/disable the advance button."""
        self.advance_button.setEnabled(enabled)

    def show_execution_result(self, result: Dict[str, Any]):
        """Display results after stage execution."""
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
        self.set_advance_enabled(False)
        self.set_status("Simulating...")
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
        # Clear games table and show a single row with offseason message
        stage_name = preview_data.get("stage_name", "Offseason")
        description = preview_data.get("description", "")

        self.games_table.setRowCount(1)
        self.games_table.setSpan(0, 0, 1, 5)  # Span all 5 columns

        message = f"{stage_name}\n\n{description}\n\nSee the Offseason tab for more details."

        message_item = QTableWidgetItem(message)
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))

        self.games_table.setItem(0, 0, message_item)
        self.games_table.setRowHeight(0, 100)  # Taller row for multi-line message
