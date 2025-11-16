"""
Draft Board Widget for The Owner's Sim

Displays NFL draft order and picks across all rounds.
Shows previous year's draft order and completed picks.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTabWidget, QComboBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class DraftBoardWidget(QWidget):
    """
    NFL Draft board widget.

    Displays complete draft order (224 picks across 7 rounds) with:
    - Pick number
    - Team name
    - Team record
    - Strength of schedule
    - Player selected (if pick made)
    - Draft reason (playoff elimination round)

    Features:
    - Round 1 view (detailed, first 32 picks)
    - All Rounds view (complete 7-round draft)
    - Team View (all picks for selected team)
    - Color-coded by playoff elimination round
    """

    # Color coding by elimination round (from draft_order_demo)
    REASON_COLORS = {
        'non_playoff': QColor(255, 0, 0),        # Red
        'wild_card_loss': QColor(255, 255, 0),   # Yellow
        'divisional_loss': QColor(0, 255, 255),  # Cyan
        'conference_loss': QColor(0, 0, 255),    # Blue
        'super_bowl_loss': QColor(0, 255, 0),    # Green
        'super_bowl_win': QColor(255, 0, 255),   # Purple
    }

    def __init__(
        self,
        parent=None,
        controller=None
    ):
        """
        Initialize draft board widget.

        Args:
            parent: Parent widget
            controller: OffseasonController instance for data access
        """
        super().__init__(parent)

        # Store controller
        self.controller = controller

        # Table references
        self.round1_table = None
        self.all_rounds_table = None
        self.team_view_table = None

        # Info label references
        self.round1_info_label = None
        self.all_rounds_info_label = None
        self.team_view_info_label = None

        # Team selection combo box
        self.team_combo = None

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_round1_view(), "Round 1")
        self.tabs.addTab(self._create_all_rounds_view(), "All Rounds")
        self.tabs.addTab(self._create_team_view(), "Team View")

        layout.addWidget(self.tabs)

        # Load initial data
        self.load_data()

    def _create_header(self) -> QHBoxLayout:
        """Create header with title and summary info."""
        header = QHBoxLayout()

        # Title
        title = QLabel("NFL Draft Board")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Summary info (will be populated from controller)
        self.summary_label = QLabel("Draft Status: Loading...")
        self.summary_label.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.summary_label)

        return header

    def _create_round1_view(self) -> QWidget:
        """Create Round 1 view (picks 1-32)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Table
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Pick", "Round", "Team", "Record", "SOS", "Player", "Pos", "Reason"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(False)  # Keep draft order
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Team
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # Player
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Info label
        info = QLabel("Round 1 - Picks 1-32")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.round1_table = table
        self.round1_info_label = info

        return widget

    def _create_all_rounds_view(self) -> QWidget:
        """Create all rounds view (picks 1-224)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Round filter
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Round:")
        self.round_filter = QComboBox()
        self.round_filter.addItems(["All", "1", "2", "3", "4", "5", "6", "7"])
        self.round_filter.setMinimumWidth(80)
        self.round_filter.currentIndexChanged.connect(self.on_round_filter_changed)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.round_filter)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Table
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Pick", "Round", "Team", "Record", "SOS", "Player", "Pos", "Reason"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(False)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Info label
        info = QLabel("All rounds - 224 picks")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.all_rounds_table = table
        self.all_rounds_info_label = info

        return widget

    def _create_team_view(self) -> QWidget:
        """Create team-specific view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Team selection
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Team:")
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(200)
        self.team_combo.currentIndexChanged.connect(self.on_team_filter_changed)

        # Populate team combo (will be filled in load_data)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.team_combo)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Table
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Pick", "Round", "Pick in Round", "Record", "SOS", "Player", "Pos"
        ])

        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSortingEnabled(False)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # Player
        table.verticalHeader().setVisible(False)

        layout.addWidget(table)

        # Info label
        info = QLabel("Select a team to view their picks")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Store references
        self.team_view_table = table
        self.team_view_info_label = info

        return widget

    def load_data(self):
        """Load all draft data from controller."""
        if not self.controller:
            self._show_no_data_state()
            return

        # Update summary
        self._update_summary()

        # Populate team combo if not already populated
        if self.team_combo.count() == 0:
            self._populate_team_combo()

        # Load data for each tab
        self._load_round1_data()
        self._load_all_rounds_data()
        self._load_team_view_data()

    def _update_summary(self):
        """Update header summary label."""
        if not self.controller:
            self.summary_label.setText("Draft Status: No data")
            return

        summary = self.controller.get_draft_summary()
        self.summary_label.setText(
            f"Draft Status: {summary['picks_made']}/{summary['total_picks']} picks made | "
            f"Current: Round {summary['current_round']}, Pick #{summary['current_pick']}"
        )

    def _populate_team_combo(self):
        """Populate team selection combo box."""
        if not self.controller:
            return

        # Get all teams
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        # Sort by team ID
        all_teams.sort(key=lambda t: t.team_id)

        # Add teams to combo
        self.team_combo.clear()
        for team in all_teams:
            self.team_combo.addItem(f"{team.full_name}", team.team_id)

    def _load_round1_data(self):
        """Load Round 1 data (picks 1-32)."""
        if not self.controller:
            return

        # Get Round 1 picks (new dict format)
        result = self.controller.get_draft_order(round_number=1)

        # Debug logging
        print(f"[DEBUG DraftBoardWidget] Round 1 result: {len(result.get('picks', []))} picks, "
              f"{len(result.get('errors', []))} errors, {len(result.get('warnings', []))} warnings")
        if result.get('errors'):
            print(f"[DEBUG DraftBoardWidget] Errors: {result['errors']}")
        if result.get('warnings'):
            print(f"[DEBUG DraftBoardWidget] Warnings: {result['warnings']}")

        picks = result['picks']

        # Populate table
        self._populate_table(self.round1_table, picks)

        # Update info label
        self.round1_info_label.setText(f"Round 1 - {len(picks)} picks")

    def _load_all_rounds_data(self):
        """Load all rounds data (picks 1-224)."""
        if not self.controller:
            return

        # Get round filter
        round_filter_text = self.round_filter.currentText()
        if round_filter_text == "All":
            result = self.controller.get_draft_order()
            picks = result['picks']
        else:
            round_num = int(round_filter_text)
            result = self.controller.get_draft_order(round_number=round_num)
            picks = result['picks']

        # Populate table
        self._populate_table(self.all_rounds_table, picks)

        # Update info label
        if round_filter_text == "All":
            self.all_rounds_info_label.setText(f"All rounds - {len(picks)} picks")
        else:
            self.all_rounds_info_label.setText(f"Round {round_filter_text} - {len(picks)} picks")

    def _load_team_view_data(self):
        """Load team-specific draft picks."""
        if not self.controller or self.team_combo.count() == 0:
            return

        # Get selected team
        team_id = self.team_combo.currentData()
        if team_id is None:
            return

        # Get team picks
        picks = self.controller.get_team_draft_picks(team_id)

        # Populate table
        self._populate_table(self.team_view_table, picks, team_view=True)

        # Update info label
        team_name = self.team_combo.currentText()
        self.team_view_info_label.setText(f"{team_name} - {len(picks)} picks")

    def _populate_table(self, table: QTableWidget, picks: list, team_view: bool = False):
        """
        Populate table with draft pick data.

        Args:
            table: QTableWidget to populate
            picks: List of pick dicts
            team_view: If True, use team view columns (fewer columns)
        """
        # Clear table
        table.setRowCount(0)

        if not picks:
            # Show empty state
            table.setRowCount(1)
            no_data_item = QTableWidgetItem("No draft data available for this dynasty/season")
            no_data_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, no_data_item)
            table.setSpan(0, 0, 1, table.columnCount())
            return

        # Populate rows
        for row, pick in enumerate(picks):
            table.insertRow(row)

            if team_view:
                # Team view columns: Pick, Round, Pick in Round, Record, SOS, Player, Pos
                self._set_table_item(table, row, 0, f"#{pick['overall_pick']}")
                self._set_table_item(table, row, 1, str(pick['round_number']))
                self._set_table_item(table, row, 2, str(pick['pick_in_round']))
                self._set_table_item(table, row, 3, pick.get('team_record', '---'))
                self._set_table_item(table, row, 4, f"{pick.get('sos', 0.0):.3f}")

                # Player info
                player = pick.get('player')
                if player:
                    self._set_table_item(table, row, 5, player.get('name', '---'))
                    self._set_table_item(table, row, 6, player.get('position', '---'))
                else:
                    self._set_table_item(table, row, 5, '---')
                    self._set_table_item(table, row, 6, '---')
            else:
                # Full view columns: Pick, Round, Team, Record, SOS, Player, Pos, Reason
                self._set_table_item(table, row, 0, f"#{pick['overall_pick']}")
                self._set_table_item(table, row, 1, str(pick['round_number']))
                self._set_table_item(table, row, 2, pick.get('team_name', f"Team {pick['team_id']}"))
                self._set_table_item(table, row, 3, pick.get('team_record', '---'))
                self._set_table_item(table, row, 4, f"{pick.get('sos', 0.0):.3f}")

                # Player info
                player = pick.get('player')
                if player:
                    self._set_table_item(table, row, 5, player.get('name', '---'))
                    self._set_table_item(table, row, 6, player.get('position', '---'))
                else:
                    self._set_table_item(table, row, 5, '---')
                    self._set_table_item(table, row, 6, '---')

                # Reason (color-coded)
                reason = pick.get('reason', 'unknown')
                reason_item = QTableWidgetItem(reason.replace('_', ' ').title())
                reason_item.setTextAlignment(Qt.AlignCenter)

                # Apply color
                if reason in self.REASON_COLORS:
                    reason_item.setBackground(self.REASON_COLORS[reason])

                table.setItem(row, 7, reason_item)

    def _set_table_item(self, table: QTableWidget, row: int, col: int, text: str):
        """Helper to set table item with consistent formatting."""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter if col in [0, 1, 2, 4, 6, 7] else Qt.AlignLeft)
        table.setItem(row, col, item)

    def _show_no_data_state(self):
        """Show 'no data' state in all tables."""
        self.summary_label.setText("Draft Status: No data model provided")

        for table in [self.round1_table, self.all_rounds_table, self.team_view_table]:
            if table:
                table.setRowCount(1)
                no_data_item = QTableWidgetItem("No draft data available")
                no_data_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(0, 0, no_data_item)
                table.setSpan(0, 0, 1, table.columnCount())

    def on_round_filter_changed(self, index):
        """Handle round filter change."""
        self._load_all_rounds_data()

    def on_team_filter_changed(self, index):
        """Handle team filter change."""
        self._load_team_view_data()

    def showEvent(self, event):
        """
        Override showEvent to refresh data when widget becomes visible.

        This ensures draft data is always current when user clicks the Draft tab.
        """
        super().showEvent(event)
        self.load_data()
