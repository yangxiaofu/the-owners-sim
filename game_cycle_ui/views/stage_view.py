"""
Stage View for The Owner's Sim (Game Cycle)

Displays current stage and provides controls for stage-based progression.
"""

from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QFrame, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTabWidget,
    QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import TABLE_HEADER_STYLE
from game_cycle import Stage, StageType, SeasonPhase


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

        # Overview tab: Division standings tables (compact, side-by-side)
        self.overview_afc_tables: Dict[str, QTableWidget] = {}
        self.overview_nfc_tables: Dict[str, QTableWidget] = {}

        # Detailed tab: Division standings tables (full columns, AFC/NFC sub-tabs)
        self.detailed_afc_tables: Dict[str, QTableWidget] = {}
        self.detailed_nfc_tables: Dict[str, QTableWidget] = {}

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

        # Week navigation header
        nav_layout = QHBoxLayout()

        self.prev_week_btn = QPushButton("< Prev Week")
        self.prev_week_btn.clicked.connect(self._on_prev_week)
        self.prev_week_btn.setEnabled(False)  # Week 1 starts disabled
        nav_layout.addWidget(self.prev_week_btn)

        self.week_display_label = QLabel("Week 1")
        self.week_display_label.setAlignment(Qt.AlignCenter)
        self.week_display_label.setFont(QFont("Arial", 12, QFont.Bold))
        nav_layout.addWidget(self.week_display_label, stretch=1)

        self.next_week_btn = QPushButton("Next Week >")
        self.next_week_btn.clicked.connect(self._on_next_week)
        nav_layout.addWidget(self.next_week_btn)

        layout.addLayout(nav_layout)

        # Games table
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(5)
        self.games_table.setHorizontalHeaderLabels(["Away", "Record", "@", "Home", "Record"])
        self.games_table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        self.games_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.games_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.games_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.games_table.setAlternatingRowColors(True)
        self.games_table.cellDoubleClicked.connect(self._on_game_double_clicked)
        layout.addWidget(self.games_table)

        return group

    def _create_standings_panel(self) -> QWidget:
        """Create standings panel with two tabs: Overview and Detailed."""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main tab widget
        self.standings_tabs = QTabWidget()

        # Tab 1: Overview - Compact side-by-side AFC/NFC
        overview_widget = self._create_overview_tab()
        self.standings_tabs.addTab(overview_widget, "Overview")

        # Tab 2: Detailed - AFC/NFC sub-tabs with full columns
        detailed_widget = self._create_detailed_tab()
        self.standings_tabs.addTab(detailed_widget, "Detailed")

        main_layout.addWidget(self.standings_tabs)
        return container

    def _create_overview_tab(self) -> QWidget:
        """Create Overview tab with compact side-by-side AFC/NFC standings."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(4, 4, 4, 4)

        # AFC column (left)
        afc_widget = self._create_overview_conference("AFC", self.overview_afc_tables)
        layout.addWidget(afc_widget)

        # NFC column (right)
        nfc_widget = self._create_overview_conference("NFC", self.overview_nfc_tables)
        layout.addWidget(nfc_widget)

        return widget

    def _create_overview_conference(self, conference: str, table_dict: Dict[str, QTableWidget]) -> QWidget:
        """Create compact conference column for Overview tab (5 columns: Team, W, L, PCT, PD)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        layout.setContentsMargins(2, 2, 2, 2)

        # Conference header
        header = QLabel(conference)
        header.setFont(QFont("Arial", 11, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        divisions = ["East", "North", "South", "West"]

        for division in divisions:
            # Division header
            div_label = QLabel(f"{conference} {division}")
            div_label.setFont(QFont("Arial", 8, QFont.Bold))
            div_label.setStyleSheet("color: #888; padding-top: 1px;")
            layout.addWidget(div_label)

            # Compact table (7 columns)
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(["Team", "W", "L", "PCT", "PF", "PA", "PD"])
            table.setRowCount(4)
            # Height to show all 4 teams without scrollbar
            table.setFixedHeight(120)
            table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 7):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setFixedHeight(26)
            table.verticalHeader().setDefaultSectionSize(16)

            table_dict[division] = table
            layout.addWidget(table)

        layout.addStretch()
        return widget

    def _create_detailed_tab(self) -> QWidget:
        """Create Detailed tab with AFC/NFC sub-tabs and full columns."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # Inner tab widget for AFC/NFC
        self.detailed_conf_tabs = QTabWidget()

        # AFC sub-tab
        afc_widget = self._create_detailed_conference("AFC", self.detailed_afc_tables)
        self.detailed_conf_tabs.addTab(afc_widget, "AFC")

        # NFC sub-tab
        nfc_widget = self._create_detailed_conference("NFC", self.detailed_nfc_tables)
        self.detailed_conf_tabs.addTab(nfc_widget, "NFC")

        layout.addWidget(self.detailed_conf_tabs)
        return widget

    def _create_detailed_conference(self, conference: str, table_dict: Dict[str, QTableWidget]) -> QWidget:
        """Create detailed conference view with full columns (11 columns)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        divisions = ["East", "North", "South", "West"]

        for division in divisions:
            # Division header
            div_label = QLabel(f"{conference} {division}")
            div_label.setFont(QFont("Arial", 10, QFont.Bold))
            div_label.setStyleSheet("color: #444; padding: 4px 0;")
            layout.addWidget(div_label)

            # Full table (11 columns)
            table = QTableWidget()
            table.setColumnCount(13)
            table.setHorizontalHeaderLabels([
                "Team", "W", "L", "T", "PCT", "PF", "PA", "PD", "Div", "Conf", "Home", "Away", "SOS"
            ])
            table.setRowCount(4)
            table.setMaximumHeight(130)
            table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 13):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setFixedHeight(28)
            table.verticalHeader().setDefaultSectionSize(20)

            table_dict[division] = table
            layout.addWidget(table)

        layout.addStretch()
        return widget

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

            # Store game data for BoxScoreDialog access
            game_data = {
                'game_id': matchup.get('game_id'),
                'home_team': {
                    'id': home_team.get('team_id'),
                    'name': home_team.get('name', 'Home'),
                    'abbr': home_name
                },
                'away_team': {
                    'id': away_team.get('team_id'),
                    'name': away_team.get('name', 'Away'),
                    'abbr': away_name
                },
                'home_score': home_score,
                'away_score': away_score,
                'is_played': is_played
            }
            away_item.setData(Qt.UserRole, game_data)

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
        """Update standings tables by division for both Overview and Detailed tabs."""
        # Group teams by conference and division
        afc = {"East": [], "North": [], "South": [], "West": []}
        nfc = {"East": [], "North": [], "South": [], "West": []}

        for team in standings:
            conf = team.get("conference", "AFC")
            div = team.get("division", "East")

            if conf == "AFC" and div in afc:
                afc[div].append(team)
            elif conf == "NFC" and div in nfc:
                nfc[div].append(team)

        # Sort each division by win percentage (descending)
        for div_teams in afc.values():
            div_teams.sort(key=lambda t: float(t.get("win_pct", "0").lstrip(".")), reverse=True)
        for div_teams in nfc.values():
            div_teams.sort(key=lambda t: float(t.get("win_pct", "0").lstrip(".")), reverse=True)

        # Populate Overview tab tables (compact, 5 columns)
        for division, teams in afc.items():
            if division in self.overview_afc_tables:
                self._populate_overview_table(self.overview_afc_tables[division], teams)
        for division, teams in nfc.items():
            if division in self.overview_nfc_tables:
                self._populate_overview_table(self.overview_nfc_tables[division], teams)

        # Populate Detailed tab tables (full, 11 columns)
        for division, teams in afc.items():
            if division in self.detailed_afc_tables:
                self._populate_detailed_table(self.detailed_afc_tables[division], teams)
        for division, teams in nfc.items():
            if division in self.detailed_nfc_tables:
                self._populate_detailed_table(self.detailed_nfc_tables[division], teams)

    def _populate_overview_table(self, table: QTableWidget, teams: List[Dict]):
        """Populate compact Overview table (7 columns: Team, W, L, PCT, PF, PA, PD)."""
        for row in range(4):
            if row < len(teams):
                team = teams[row]

                # Team abbreviation
                team_item = QTableWidgetItem(team.get("abbreviation", "???"))
                table.setItem(row, 0, team_item)

                # Wins
                wins_item = QTableWidgetItem(str(team.get("wins", 0)))
                wins_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, wins_item)

                # Losses
                losses_item = QTableWidgetItem(str(team.get("losses", 0)))
                losses_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, losses_item)

                # Win PCT
                pct_item = QTableWidgetItem(team.get("win_pct", ".000"))
                pct_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 3, pct_item)

                # Points For
                pf_item = QTableWidgetItem(str(team.get("points_for", 0)))
                pf_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 4, pf_item)

                # Points Against
                pa_item = QTableWidgetItem(str(team.get("points_against", 0)))
                pa_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 5, pa_item)

                # Point Differential
                pd = team.get("point_diff", 0)
                pd_text = f"+{pd}" if pd > 0 else str(pd)
                pd_item = QTableWidgetItem(pd_text)
                pd_item.setTextAlignment(Qt.AlignCenter)
                if pd > 0:
                    pd_item.setForeground(QColor("green"))
                elif pd < 0:
                    pd_item.setForeground(QColor("red"))
                table.setItem(row, 6, pd_item)
            else:
                for col in range(7):
                    table.setItem(row, col, QTableWidgetItem(""))

    def _populate_detailed_table(self, table: QTableWidget, teams: List[Dict]):
        """Populate full Detailed table (13 columns: Team, W, L, T, PCT, PF, PA, PD, Div, Conf, Home, Away, SOS)."""
        for row in range(4):
            if row < len(teams):
                team = teams[row]

                # Team abbreviation
                team_item = QTableWidgetItem(team.get("abbreviation", "???"))
                table.setItem(row, 0, team_item)

                # Wins
                wins_item = QTableWidgetItem(str(team.get("wins", 0)))
                wins_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, wins_item)

                # Losses
                losses_item = QTableWidgetItem(str(team.get("losses", 0)))
                losses_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, losses_item)

                # Ties
                ties_item = QTableWidgetItem(str(team.get("ties", 0)))
                ties_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 3, ties_item)

                # Win PCT
                pct_item = QTableWidgetItem(team.get("win_pct", ".000"))
                pct_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 4, pct_item)

                # Points For
                pf_item = QTableWidgetItem(str(team.get("points_for", 0)))
                pf_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 5, pf_item)

                # Points Against
                pa_item = QTableWidgetItem(str(team.get("points_against", 0)))
                pa_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 6, pa_item)

                # Point Differential
                pd = team.get("point_diff", 0)
                pd_text = f"+{pd}" if pd > 0 else str(pd)
                pd_item = QTableWidgetItem(pd_text)
                pd_item.setTextAlignment(Qt.AlignCenter)
                if pd > 0:
                    pd_item.setForeground(QColor("green"))
                elif pd < 0:
                    pd_item.setForeground(QColor("red"))
                table.setItem(row, 7, pd_item)

                # Division Record
                div_item = QTableWidgetItem(team.get("div_record", "0-0"))
                div_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 8, div_item)

                # Conference Record
                conf_item = QTableWidgetItem(team.get("conf_record", "0-0"))
                conf_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 9, conf_item)

                # Home Record
                home_item = QTableWidgetItem(team.get("home_record", "0-0"))
                home_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 10, home_item)

                # Away Record
                away_item = QTableWidgetItem(team.get("away_record", "0-0"))
                away_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 11, away_item)

                # Strength of Schedule
                sos_item = QTableWidgetItem(team.get("sos", ".000"))
                sos_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 12, sos_item)
            else:
                for col in range(13):
                    table.setItem(row, col, QTableWidgetItem(""))

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
            self._current_stage.phase == SeasonPhase.OFFSEASON and
            self._current_stage.stage_type != StageType.OFFSEASON_PRESEASON):
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
        print(f"[StageView] store_game_results called with {len(games_played)} games")
        for game in games_played:
            game_id = game.get('game_id')
            game_result = game.get('game_result')
            print(f"[StageView] Game {game_id}: has game_result={game_result is not None}")
            if game_id and game_result:
                self._game_results_cache[game_id] = game_result
                print(f"[StageView] ✓ Cached GameResult for {game_id}")
                print(f"[StageView] GameResult has drives: {hasattr(game_result, 'drives')}")
            else:
                print(f"[StageView] ✗ NOT caching {game_id} - missing game_id or game_result")

    def _on_game_double_clicked(self, row: int, column: int):
        """Open box score dialog when game row is double-clicked."""
        print(f"[StageView] Double-clicked row={row}, column={column}")

        # Get the first column item (has game data in UserRole)
        item = self.games_table.item(row, 0)
        if not item:
            print("[StageView] No item found at row 0")
            return

        game_data = item.data(Qt.UserRole)
        print(f"[StageView] game_data={game_data}")
        if not game_data:
            print("[StageView] No game_data stored in UserRole")
            return  # No game data stored

        # Check if game was played (has scores and game_id)
        is_played = game_data.get('is_played')
        game_id = game_data.get('game_id')
        print(f"[StageView] is_played={is_played}, game_id={game_id}")
        if not is_played or not game_id:
            print("[StageView] Game not played yet or no game_id")
            return  # Game not played yet

        # Check we have context
        print(f"[StageView] db_path={self._db_path}, dynasty_id={self._dynasty_id}")
        if not self._db_path or not self._dynasty_id:
            print("[StageView] Cannot open box score: missing db_path or dynasty_id context")
            return

        from game_cycle_ui.dialogs import BoxScoreDialog

        # Debug: Show cache contents
        print(f"[StageView] Cache has {len(self._game_results_cache)} game results")
        print(f"[StageView] Cache keys: {list(self._game_results_cache.keys())}")
        print(f"[StageView] Looking for game_id: {game_id}")

        # Try to get GameResult from cache (for play-by-play)
        game_result = self._game_results_cache.get(game_id)
        if game_result:
            print(f"[StageView] Found cached GameResult for {game_id} - play-by-play available")
            print(f"[StageView] GameResult type: {type(game_result)}")
            print(f"[StageView] Has drives: {hasattr(game_result, 'drives')}")
        else:
            print(f"[StageView] No cached GameResult for {game_id} - no play-by-play available")

        print("[StageView] Creating BoxScoreDialog...")
        try:
            dialog = BoxScoreDialog(
                game_id=game_data['game_id'],
                home_team=game_data['home_team'],
                away_team=game_data['away_team'],
                home_score=game_data.get('home_score', 0),
                away_score=game_data.get('away_score', 0),
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                game_result=game_result,  # Pass GameResult for play-by-play
                parent=self
            )
            print("[StageView] Calling dialog.exec()...")
            dialog.exec()
            print("[StageView] Dialog closed")
        except Exception as e:
            print(f"[StageView] ERROR creating/showing dialog: {e}")
            import traceback
            traceback.print_exc()

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
