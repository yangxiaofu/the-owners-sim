"""
Draft View - Interactive NFL Draft UI for game cycle offseason.

Allows the user to select prospects for their team while AI teams
auto-pick. Supports simulate-to-pick and auto-complete modes.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import TABLE_HEADER_STYLE
from game_cycle_ui.dialogs import DraftDirectionDialog
from game_cycle.models import DraftDirection, DraftStrategy


class DraftView(QWidget):
    """
    Interactive draft view for the OFFSEASON_DRAFT stage.

    Features:
    - Summary panel (round, pick, on the clock)
    - Prospects table with position filter
    - Draft history table
    - Progress bar (0-224)
    - Action buttons: Draft Selected, Simulate to My Pick, Auto-Draft All

    Signals:
        prospect_drafted: Emitted when user selects a prospect (prospect_id)
        simulate_to_pick_requested: Emitted when user wants to sim to their pick
        auto_draft_all_requested: Emitted when user wants to auto-complete draft
    """

    # Signals
    prospect_drafted = Signal(int)  # prospect_id
    simulate_to_pick_requested = Signal()
    auto_draft_all_requested = Signal()
    round_filter_changed = Signal(object)  # None or int (round number)
    draft_direction_changed = Signal(object)  # DraftDirection

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._prospects: List[Dict] = []
        self._draft_history: List[Dict] = []
        self._current_pick: Optional[Dict] = None
        self._user_team_id: int = 1
        self._selected_prospect_id: Optional[int] = None
        self._is_user_turn: bool = False
        self._current_direction: Optional[DraftDirection] = None  # Draft strategy

        # Team context for draft direction dialog (Phase 2)
        self._season: int = 0
        self._dynasty_id: str = ""
        self._db_path: str = ""

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Progress bar
        self._create_progress_bar(layout)

        # Main content: prospects and history side by side
        splitter = QSplitter(Qt.Horizontal)

        # Left: Prospects table with filter
        prospects_widget = self._create_prospects_panel()
        splitter.addWidget(prospects_widget)

        # Right: Draft history
        history_widget = self._create_history_panel()
        splitter.addWidget(history_widget)

        # Set initial sizes (60/40 split)
        splitter.setSizes([600, 400])

        layout.addWidget(splitter, stretch=1)

        # Action buttons at bottom
        self._create_action_buttons(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing draft progress."""
        summary_group = QGroupBox("Draft Status")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(40)

        # Round info
        round_frame = QFrame()
        round_layout = QVBoxLayout(round_frame)
        round_layout.setContentsMargins(0, 0, 0, 0)

        round_title = QLabel("Round")
        round_title.setStyleSheet("color: #666; font-size: 11px;")
        round_layout.addWidget(round_title)

        self.round_label = QLabel("1")
        self.round_label.setFont(QFont("Arial", 20, QFont.Bold))
        round_layout.addWidget(self.round_label)

        summary_layout.addWidget(round_frame)

        # Pick info
        pick_frame = QFrame()
        pick_layout = QVBoxLayout(pick_frame)
        pick_layout.setContentsMargins(0, 0, 0, 0)

        pick_title = QLabel("Overall Pick")
        pick_title.setStyleSheet("color: #666; font-size: 11px;")
        pick_layout.addWidget(pick_title)

        self.pick_label = QLabel("1")
        self.pick_label.setFont(QFont("Arial", 20, QFont.Bold))
        pick_layout.addWidget(self.pick_label)

        summary_layout.addWidget(pick_frame)

        # On the clock
        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        clock_layout.setContentsMargins(0, 0, 0, 0)

        clock_title = QLabel("On The Clock")
        clock_title.setStyleSheet("color: #666; font-size: 11px;")
        clock_layout.addWidget(clock_title)

        self.on_clock_label = QLabel("--")
        self.on_clock_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.on_clock_label.setStyleSheet("color: #1976D2;")
        clock_layout.addWidget(self.on_clock_label)

        summary_layout.addWidget(clock_frame)

        # Picks made
        made_frame = QFrame()
        made_layout = QVBoxLayout(made_frame)
        made_layout.setContentsMargins(0, 0, 0, 0)

        made_title = QLabel("Picks Made")
        made_title.setStyleSheet("color: #666; font-size: 11px;")
        made_layout.addWidget(made_title)

        self.picks_made_label = QLabel("0 / 224")
        self.picks_made_label.setFont(QFont("Arial", 14, QFont.Bold))
        made_layout.addWidget(self.picks_made_label)

        summary_layout.addWidget(made_frame)

        # User status indicator
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)

        status_title = QLabel("Your Status")
        status_title.setStyleSheet("color: #666; font-size: 11px;")
        status_layout.addWidget(status_title)

        self.user_status_label = QLabel("Waiting...")
        self.user_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        status_layout.addWidget(self.user_status_label)

        summary_layout.addWidget(status_frame)

        summary_layout.addStretch()

        # Strategy info and button
        strategy_frame = QFrame()
        strategy_layout = QVBoxLayout(strategy_frame)
        strategy_layout.setContentsMargins(0, 0, 0, 0)

        self._strategy_badge = QLabel("Strategy: Balanced")
        self._strategy_badge.setFont(QFont("Arial", 10))
        self._strategy_badge.setStyleSheet(
            "color: #1976D2; background-color: #E3F2FD; "
            "padding: 4px 8px; border-radius: 3px;"
        )
        strategy_layout.addWidget(self._strategy_badge)

        self._set_strategy_btn = QPushButton("⚙️ Set Strategy")
        self._set_strategy_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border-radius: 4px; "
            "padding: 6px 12px; font-size: 11px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        self._set_strategy_btn.clicked.connect(self._show_draft_direction_dialog)
        strategy_layout.addWidget(self._set_strategy_btn)

        summary_layout.addWidget(strategy_frame)

        parent_layout.addWidget(summary_group)

    def _create_progress_bar(self, parent_layout: QVBoxLayout):
        """Create the draft progress bar."""
        progress_layout = QHBoxLayout()

        progress_label = QLabel("Draft Progress:")
        progress_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(224)  # 7 rounds * 32 teams
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m picks")
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #ccc; border-radius: 4px; text-align: center; }"
            "QProgressBar::chunk { background-color: #1976D2; }"
        )
        progress_layout.addWidget(self.progress_bar, stretch=1)

        parent_layout.addLayout(progress_layout)

    def _create_prospects_panel(self) -> QWidget:
        """Create the prospects panel with table and filter."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with filter
        header_layout = QHBoxLayout()

        header_label = QLabel("Available Prospects")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        filter_label = QLabel("Position:")
        header_layout.addWidget(filter_label)

        self.position_filter = QComboBox()
        self.position_filter.addItem("All Positions", "")
        positions = ["QB", "RB", "WR", "TE", "OT", "OG", "C", "EDGE", "DT", "LB", "CB", "S", "K", "P"]
        for pos in positions:
            self.position_filter.addItem(pos, pos)
        self.position_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.position_filter.setMinimumWidth(120)
        header_layout.addWidget(self.position_filter)

        layout.addLayout(header_layout)

        # Prospects table
        self.prospects_table = QTableWidget()
        self.prospects_table.setColumnCount(7)
        self.prospects_table.setHorizontalHeaderLabels([
            "Rank", "Name", "Position", "College", "OVR", "Age", "Select"
        ])

        # Configure table appearance
        header = self.prospects_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Rank
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # College
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # OVR
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 80)  # Select button column

        self.prospects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prospects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospects_table.setAlternatingRowColors(True)
        self.prospects_table.verticalHeader().setVisible(False)

        layout.addWidget(self.prospects_table)

        return widget

    def _create_history_panel(self) -> QWidget:
        """Create the draft history panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with round filter
        header_layout = QHBoxLayout()

        header_label = QLabel("Draft History")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Round filter dropdown
        round_label = QLabel("Round:")
        header_layout.addWidget(round_label)

        self.history_round_filter = QComboBox()
        self.history_round_filter.addItem("All Rounds", None)
        for r in range(1, 8):
            self.history_round_filter.addItem(f"Round {r}", r)
        self.history_round_filter.currentIndexChanged.connect(self._on_history_round_filter_changed)
        self.history_round_filter.setMinimumWidth(100)
        header_layout.addWidget(self.history_round_filter)

        layout.addLayout(header_layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Pick", "Team", "Player", "Pos", "OVR"
        ])

        header = self.history_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)

        layout.addWidget(self.history_table)

        return widget

    def _create_action_buttons(self, parent_layout: QVBoxLayout):
        """Create the action buttons at the bottom."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)

        # Simulate to my pick button
        self.sim_to_pick_btn = QPushButton("Simulate to My Pick")
        self.sim_to_pick_btn.setMinimumHeight(40)
        self.sim_to_pick_btn.setMinimumWidth(180)
        self.sim_to_pick_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; border-radius: 4px; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.sim_to_pick_btn.clicked.connect(self._on_sim_to_pick)
        button_layout.addWidget(self.sim_to_pick_btn)

        # Draft selected button (only enabled when it's user's turn and a prospect is selected)
        self.draft_btn = QPushButton("Draft Selected")
        self.draft_btn.setMinimumHeight(40)
        self.draft_btn.setMinimumWidth(150)
        self.draft_btn.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; border-radius: 4px; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1B5E20; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.draft_btn.setEnabled(False)
        self.draft_btn.clicked.connect(self._on_draft_selected)
        button_layout.addWidget(self.draft_btn)

        button_layout.addStretch()

        # Auto-draft all button
        self.auto_draft_btn = QPushButton("Auto-Draft All Remaining")
        self.auto_draft_btn.setMinimumHeight(40)
        self.auto_draft_btn.setMinimumWidth(200)
        self.auto_draft_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border-radius: 4px; "
            "padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.auto_draft_btn.clicked.connect(self._on_auto_draft)
        button_layout.addWidget(self.auto_draft_btn)

        parent_layout.addLayout(button_layout)

    # ========================================================================
    # Public Methods
    # ========================================================================

    def set_user_team_id(self, team_id: int):
        """Set the user's team ID for determining when it's their pick."""
        self._user_team_id = team_id

    def set_team_context(self, season: int, dynasty_id: str, db_path: str):
        """
        Set team context for draft direction dialog (Phase 2).

        Args:
            season: Current season
            dynasty_id: Dynasty ID
            db_path: Database path
        """
        self._season = season
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def set_prospects(self, prospects: List[Dict]):
        """
        Set the available prospects.

        Args:
            prospects: List of prospect dictionaries with:
                - prospect_id: int
                - name: str
                - position: str
                - college: str (optional)
                - overall: int
                - age: int
                - rank: int (draft rank)
        """
        self._prospects = prospects
        self._refresh_prospects_table()

    def set_current_pick(self, pick_info: Optional[Dict]):
        """
        Set the current pick information.

        Args:
            pick_info: Dictionary with:
                - round: int
                - pick_in_round: int
                - overall_pick: int
                - team_id: int
                - team_name: str (optional)
        """
        self._current_pick = pick_info

        if pick_info is None:
            # Draft complete
            self.round_label.setText("-")
            self.pick_label.setText("-")
            self.on_clock_label.setText("Draft Complete")
            self.on_clock_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
            self._is_user_turn = False
            self._update_button_states()
            return

        # Update display
        round_num = pick_info.get("round", 1)
        overall = pick_info.get("overall_pick", 1)
        team_id = pick_info.get("team_id", 0)
        team_name = pick_info.get("team_name", f"Team {team_id}")

        self.round_label.setText(str(round_num))
        self.pick_label.setText(str(overall))
        self.on_clock_label.setText(team_name)

        # Check if it's user's turn
        self._is_user_turn = (team_id == self._user_team_id)

        if self._is_user_turn:
            self.on_clock_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
            self.user_status_label.setText("YOUR PICK!")
            self.user_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        else:
            self.on_clock_label.setStyleSheet("color: #1976D2;")
            self.user_status_label.setText("Waiting...")
            self.user_status_label.setStyleSheet("color: #666;")

        self._update_button_states()

    def set_draft_progress(self, picks_made: int, total_picks: int = 224):
        """Update the draft progress bar and counter."""
        self.progress_bar.setMaximum(total_picks)
        self.progress_bar.setValue(picks_made)
        self.picks_made_label.setText(f"{picks_made} / {total_picks}")

    def set_draft_history(self, history: List[Dict]):
        """
        Set the draft history.

        Args:
            history: List of pick dictionaries with:
                - overall_pick: int
                - team_name: str
                - player_name: str
                - position: str
                - overall: int
        """
        self._draft_history = history
        self._refresh_history_table()

    def set_draft_complete(self):
        """Mark the draft as complete."""
        self.set_current_pick(None)
        self.draft_btn.setEnabled(False)
        self.sim_to_pick_btn.setEnabled(False)
        self.auto_draft_btn.setEnabled(False)

        self.user_status_label.setText("Draft Complete!")
        self.user_status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _refresh_prospects_table(self):
        """Refresh the prospects table with current filter."""
        filter_pos = self.position_filter.currentData()

        # Filter prospects
        if filter_pos:
            filtered = [p for p in self._prospects if p.get("position") == filter_pos]
        else:
            filtered = self._prospects

        self.prospects_table.setRowCount(len(filtered))

        for row, prospect in enumerate(filtered):
            self._populate_prospect_row(row, prospect)

    def _populate_prospect_row(self, row: int, prospect: Dict):
        """Populate a single row in the prospects table."""
        prospect_id = prospect.get("prospect_id", 0)

        # Rank
        rank = prospect.get("rank", row + 1)
        rank_item = QTableWidgetItem(str(rank))
        rank_item.setTextAlignment(Qt.AlignCenter)
        rank_item.setData(Qt.UserRole, prospect_id)
        self.prospects_table.setItem(row, 0, rank_item)

        # Name
        name = prospect.get("name", "Unknown")
        name_item = QTableWidgetItem(name)
        self.prospects_table.setItem(row, 1, name_item)

        # Position
        pos = prospect.get("position", "")
        pos_item = QTableWidgetItem(pos)
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.prospects_table.setItem(row, 2, pos_item)

        # College
        college = prospect.get("college", "")
        college_item = QTableWidgetItem(college)
        self.prospects_table.setItem(row, 3, college_item)

        # Overall
        overall = prospect.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 80:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite prospect
        elif overall >= 70:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid prospect
        elif overall >= 60:
            ovr_item.setForeground(QColor("#FF9800"))  # Orange - Project
        self.prospects_table.setItem(row, 4, ovr_item)

        # Age
        age = prospect.get("age", 21)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        self.prospects_table.setItem(row, 5, age_item)

        # Select button
        select_btn = QPushButton("Select")
        select_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border-radius: 3px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        select_btn.clicked.connect(lambda checked, pid=prospect_id: self._on_prospect_selected(pid))
        # Only enable if it's user's turn
        select_btn.setEnabled(self._is_user_turn)
        self.prospects_table.setCellWidget(row, 6, select_btn)

    def _refresh_history_table(self):
        """Refresh the draft history table."""
        # Show most recent picks first
        history = list(reversed(self._draft_history))
        self.history_table.setRowCount(len(history))

        for row, pick in enumerate(history):
            self._populate_history_row(row, pick)

    def _populate_history_row(self, row: int, pick: Dict):
        """Populate a single row in the history table."""
        # Pick number
        overall = pick.get("overall_pick", 0)
        pick_item = QTableWidgetItem(str(overall))
        pick_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 0, pick_item)

        # Team
        team_name = pick.get("team_name", "")
        team_item = QTableWidgetItem(team_name)
        self.history_table.setItem(row, 1, team_item)

        # Player
        player_name = pick.get("player_name", "")
        player_item = QTableWidgetItem(player_name)
        self.history_table.setItem(row, 2, player_item)

        # Position
        pos = pick.get("position", "")
        pos_item = QTableWidgetItem(pos)
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 3, pos_item)

        # Overall
        overall_rating = pick.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall_rating))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        self.history_table.setItem(row, 4, ovr_item)

    def _on_filter_changed(self):
        """Handle position filter change."""
        self._refresh_prospects_table()

    def _on_history_round_filter_changed(self):
        """Handle history round filter change."""
        round_val = self.history_round_filter.currentData()
        self.round_filter_changed.emit(round_val)

    def _on_prospect_selected(self, prospect_id: int):
        """Handle prospect selection."""
        self._selected_prospect_id = prospect_id
        self._update_button_states()

        # Highlight selected row
        for row in range(self.prospects_table.rowCount()):
            rank_item = self.prospects_table.item(row, 0)
            if rank_item and rank_item.data(Qt.UserRole) == prospect_id:
                self.prospects_table.selectRow(row)
                break

        # If it's user's turn, draft immediately
        if self._is_user_turn and prospect_id:
            self._on_draft_selected()

    def _on_draft_selected(self):
        """Handle draft selected button click."""
        if self._selected_prospect_id and self._is_user_turn:
            self.draft_btn.setEnabled(False)
            self.prospect_drafted.emit(self._selected_prospect_id)
            self._selected_prospect_id = None

    def _on_sim_to_pick(self):
        """Handle simulate to my pick button click."""
        self.sim_to_pick_btn.setEnabled(False)
        self.sim_to_pick_btn.setText("Simulating...")
        self.simulate_to_pick_requested.emit()

    def _on_auto_draft(self):
        """Handle auto-draft all button click."""
        self.auto_draft_btn.setEnabled(False)
        self.auto_draft_btn.setText("Auto-Drafting...")
        self.auto_draft_all_requested.emit()

    def _update_button_states(self):
        """Update button enabled states based on current state."""
        # Draft button: only when user's turn and prospect selected
        can_draft = self._is_user_turn and self._selected_prospect_id is not None
        self.draft_btn.setEnabled(can_draft)

        # Sim to pick: always enabled if not user's turn and draft not complete
        can_sim = not self._is_user_turn and self._current_pick is not None
        self.sim_to_pick_btn.setEnabled(can_sim)
        self.sim_to_pick_btn.setText("Simulate to My Pick")

        # Auto draft: always enabled if draft not complete
        can_auto = self._current_pick is not None
        self.auto_draft_btn.setEnabled(can_auto)
        self.auto_draft_btn.setText("Auto-Draft All Remaining")

        # Update select buttons in table
        for row in range(self.prospects_table.rowCount()):
            btn = self.prospects_table.cellWidget(row, 6)
            if btn:
                btn.setEnabled(self._is_user_turn)

    def show_no_prospects_message(self):
        """Show a message when there are no available prospects."""
        self.prospects_table.setRowCount(1)
        self.prospects_table.setSpan(0, 0, 1, 7)

        message_item = QTableWidgetItem("No prospects available - Draft class not generated")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.prospects_table.setItem(0, 0, message_item)

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant
        """
        # Draft view uses rookie contracts (slot-based)
        # Cap impact is minimal and fixed by pick position
        pass

    def _show_draft_direction_dialog(self):
        """Show the draft direction configuration dialog."""
        dialog = DraftDirectionDialog(
            current_direction=self._current_direction,
            team_id=self._user_team_id,
            season=self._season,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path,
            parent=self
        )

        dialog.direction_saved.connect(self._on_direction_saved)
        dialog.exec()

    def _on_direction_saved(self, direction: DraftDirection):
        """
        Handle saved draft direction.

        Args:
            direction: New draft direction from dialog
        """
        self._current_direction = direction
        self.draft_direction_changed.emit(direction)

        # Update badge
        strategy_names = {
            DraftStrategy.BEST_PLAYER_AVAILABLE: "BPA",
            DraftStrategy.BALANCED: "Balanced",
            DraftStrategy.NEEDS_BASED: "Needs-Based",
            DraftStrategy.POSITION_FOCUS: "Position Focus",
        }
        strategy_text = strategy_names.get(direction.strategy, "Balanced")
        self._strategy_badge.setText(f"Strategy: {strategy_text}")

    def get_draft_direction(self) -> Optional[DraftDirection]:
        """
        Get the current draft direction.

        Returns:
            Current DraftDirection or None
        """
        return self._current_direction