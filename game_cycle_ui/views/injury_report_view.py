"""
Injury Report View - Displays team injuries and IR management.

Shows active injuries and IR players with action buttons for the user's team.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import (
    UITheme, TABLE_HEADER_STYLE, Colors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, WARNING_BUTTON_STYLE,
    Typography, FontSizes, TextColors, apply_table_style
)


class InjuryReportView(QWidget):
    """
    View for team injury report and IR management.

    Shows active injuries (not on IR) and players on IR.
    User can place eligible players on IR or activate them from IR.
    """

    # Signals emitted for IR actions
    place_on_ir_requested = Signal(int, int)  # player_id, injury_id
    activate_from_ir_requested = Signal(int)  # player_id
    team_changed = Signal(int)  # team_id
    refresh_requested = Signal()

    # NFL IR Rules
    IR_MINIMUM_GAMES = 4
    IR_RETURN_SLOTS_MAX = 8

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: int = 2025
        self._user_team_id: Optional[int] = None
        self._current_team_id: int = 1
        self._current_week: int = 1
        self._is_user_team: bool = False
        self._active_injuries: List[Dict] = []
        self._ir_players: List[Dict] = []
        self._ir_slots_remaining: int = 8
        self._roster_count: int = 0  # For roster full check on IR activation
        self._setup_ui()

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """Set dynasty context for data operations."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

    def set_user_team_id(self, team_id: int):
        """Set user's team ID for enabling action buttons."""
        self._user_team_id = team_id

    def set_injury_data(self, data: Dict[str, Any]):
        """
        Populate the view with injury data.

        Args:
            data: Dict containing:
                - team_id: int
                - team_name: str
                - active_injuries: List[Dict] with injury + position
                - ir_players: List[Dict] with injury + position
                - ir_slots_remaining: int (0-8)
                - current_week: int
                - is_user_team: bool
        """
        self._current_team_id = data.get("team_id", 1)
        self._current_week = data.get("current_week", 1)
        self._is_user_team = data.get("is_user_team", False)
        self._active_injuries = data.get("active_injuries", [])
        self._ir_players = data.get("ir_players", [])
        self._ir_slots_remaining = data.get("ir_slots_remaining", 8)
        self._roster_count = data.get("roster_count", 0)

        # Update summary labels
        self._update_summary(data)

        # Update tables
        self._populate_active_injuries_table()
        self._populate_ir_table()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Collapsible IR rules panel
        self._create_ir_rules_panel(layout)

        # Active injuries table
        self._create_active_injuries_table(layout)

        # IR table
        self._create_ir_table(layout)

        # Instructions (kept as brief footer)
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing team stats and IR status."""
        summary_group = QGroupBox("Injury Report Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Team selector
        team_frame = QFrame()
        team_layout = QVBoxLayout(team_frame)
        team_layout.setContentsMargins(0, 0, 0, 0)

        team_title = QLabel("Team")
        team_title.setFont(Typography.CAPTION)
        team_title.setStyleSheet(f"color: {Colors.MUTED};")
        team_layout.addWidget(team_title)

        self.team_combo = QComboBox()
        self.team_combo.currentIndexChanged.connect(self._on_team_changed)
        team_layout.addWidget(self.team_combo)

        summary_layout.addWidget(team_frame)

        # IR slots remaining
        slots_frame = QFrame()
        slots_layout = QVBoxLayout(slots_frame)
        slots_layout.setContentsMargins(0, 0, 0, 0)

        slots_title = QLabel("IR Return Slots")
        slots_title.setFont(Typography.CAPTION)
        slots_title.setStyleSheet(f"color: {Colors.MUTED};")
        slots_layout.addWidget(slots_title)

        self.ir_slots_label = QLabel("8/8")
        self.ir_slots_label.setFont(Typography.H4)
        self.ir_slots_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        slots_layout.addWidget(self.ir_slots_label)

        summary_layout.addWidget(slots_frame)

        # Active injuries count
        active_frame = QFrame()
        active_layout = QVBoxLayout(active_frame)
        active_layout.setContentsMargins(0, 0, 0, 0)

        active_title = QLabel("Active Injuries")
        active_title.setFont(Typography.CAPTION)
        active_title.setStyleSheet(f"color: {Colors.MUTED};")
        active_layout.addWidget(active_title)

        self.active_count_label = QLabel("0")
        self.active_count_label.setFont(Typography.H4)
        self.active_count_label.setStyleSheet(f"color: {Colors.WARNING};")
        active_layout.addWidget(self.active_count_label)

        summary_layout.addWidget(active_frame)

        # On IR count
        ir_frame = QFrame()
        ir_layout = QVBoxLayout(ir_frame)
        ir_layout.setContentsMargins(0, 0, 0, 0)

        ir_title = QLabel("On IR")
        ir_title.setFont(Typography.CAPTION)
        ir_title.setStyleSheet(f"color: {Colors.MUTED};")
        ir_layout.addWidget(ir_title)

        self.ir_count_label = QLabel("0")
        self.ir_count_label.setFont(Typography.H4)
        self.ir_count_label.setStyleSheet(f"color: {Colors.ERROR};")
        ir_layout.addWidget(self.ir_count_label)

        summary_layout.addWidget(ir_frame)

        # Current week
        week_frame = QFrame()
        week_layout = QVBoxLayout(week_frame)
        week_layout.setContentsMargins(0, 0, 0, 0)

        week_title = QLabel("Current Week")
        week_title.setFont(Typography.CAPTION)
        week_title.setStyleSheet(f"color: {Colors.MUTED};")
        week_layout.addWidget(week_title)

        self.week_label = QLabel("1")
        self.week_label.setFont(Typography.H4)
        week_layout.addWidget(self.week_label)

        summary_layout.addWidget(week_frame)

        summary_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        summary_layout.addWidget(refresh_btn)

        parent_layout.addWidget(summary_group)

    def _create_ir_rules_panel(self, parent_layout: QVBoxLayout):
        """Create collapsible IR rules information panel."""
        # Container for collapsible section
        self.ir_rules_container = QFrame()
        container_layout = QVBoxLayout(self.ir_rules_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Header button (click to expand/collapse)
        self.ir_rules_toggle = QToolButton()
        self.ir_rules_toggle.setStyleSheet(f"""
            QToolButton {{
                background-color: {Colors.INFO};
                color: white;
                border: none;
                padding: 8px 12px;
                font-weight: bold;
                text-align: left;
                border-radius: 4px 4px 0 0;
            }}
            QToolButton:hover {{
                background-color: #1565C0;
            }}
        """)
        self.ir_rules_toggle.setText("\u25BC IR Rules & Information")
        self.ir_rules_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.ir_rules_toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ir_rules_toggle.setCheckable(True)
        self.ir_rules_toggle.setChecked(False)  # Start collapsed
        self.ir_rules_toggle.clicked.connect(self._toggle_ir_rules_panel)
        container_layout.addWidget(self.ir_rules_toggle)

        # Content panel (collapsible)
        self.ir_rules_content = QFrame()
        self.ir_rules_content.setStyleSheet(f"""
            QFrame {{
                background-color: #E3F2FD;
                border: 1px solid {Colors.INFO};
                border-top: none;
                border-radius: 0 0 4px 4px;
                padding: 12px;
            }}
        """)
        content_layout = QVBoxLayout(self.ir_rules_content)
        content_layout.setSpacing(8)

        # Rule items
        rules = [
            ("Roster Spot", "IR frees up a roster spot. The 53-man limit only counts active players."),
            ("Salary Cap", "Players on IR still count against the salary cap (NFL-accurate)."),
            ("IR Eligibility", "Only injuries of 4+ weeks are eligible for IR placement."),
            ("Minimum Stay", "Players must remain on IR for at least 4 games before activation."),
            ("Return Slots", "Each team has 8 IR-return slots per season."),
            ("Activation", "To activate from IR, team must have an open roster spot (may need to cut someone)."),
        ]

        for title, description in rules:
            rule_label = QLabel(f"<b>{title}:</b> {description}")
            rule_label.setFont(Typography.BODY)
            rule_label.setWordWrap(True)
            rule_label.setStyleSheet("color: #333; background: transparent; border: none;")
            content_layout.addWidget(rule_label)

        self.ir_rules_content.setVisible(False)  # Start collapsed
        container_layout.addWidget(self.ir_rules_content)

        parent_layout.addWidget(self.ir_rules_container)

    def _toggle_ir_rules_panel(self):
        """Toggle visibility of IR rules content."""
        is_expanded = self.ir_rules_toggle.isChecked()
        self.ir_rules_content.setVisible(is_expanded)

        if is_expanded:
            self.ir_rules_toggle.setText("\u25B2 IR Rules & Information")
        else:
            self.ir_rules_toggle.setText("\u25BC IR Rules & Information")

    def _create_active_injuries_table(self, parent_layout: QVBoxLayout):
        """Create the table for active injuries (not on IR)."""
        table_group = QGroupBox("Active Injuries (Not on IR)")
        table_layout = QVBoxLayout(table_group)

        self.active_table = QTableWidget()
        self.active_table.setColumnCount(8)
        self.active_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Injury", "Severity", "Weeks", "Return", "Status", "Action"
        ])

        # Apply standard table styling
        apply_table_style(self.active_table)

        # Configure columns
        header = self.active_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Injury
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Severity
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Weeks
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Return
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Action
        header.resizeSection(7, 100)

        table_layout.addWidget(self.active_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_ir_table(self, parent_layout: QVBoxLayout):
        """Create the table for players on IR."""
        table_group = QGroupBox("Injured Reserve")
        table_layout = QVBoxLayout(table_group)

        self.ir_table = QTableWidget()
        self.ir_table.setColumnCount(7)
        self.ir_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Injury", "Placed", "Eligible", "Status", "Action"
        ])

        # Apply standard table styling
        apply_table_style(self.ir_table)

        # Configure columns
        header = self.ir_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Injury
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Placed
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Eligible
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Action
        header.resizeSection(6, 100)

        table_layout.addWidget(self.ir_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "[+] = Place on IR (injury must be 4+ weeks)    "
            "[Activate] = Activate from IR (uses 1 return slot)    "
            "IR Return Slots: 8 per season"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def _update_summary(self, data: Dict[str, Any]):
        """Update the summary panel labels."""
        # IR slots - color coded
        slots = data.get("ir_slots_remaining", 8)
        slots_used = self.IR_RETURN_SLOTS_MAX - slots
        self.ir_slots_label.setText(f"{slots}/{self.IR_RETURN_SLOTS_MAX}")

        if slots == 0:
            self.ir_slots_label.setStyleSheet(f"color: {Colors.ERROR};")
        elif slots <= 2:
            self.ir_slots_label.setStyleSheet(f"color: {Colors.WARNING};")
        else:
            self.ir_slots_label.setStyleSheet(f"color: {Colors.SUCCESS};")

        # Counts
        active_count = len(data.get("active_injuries", []))
        ir_count = len(data.get("ir_players", []))

        self.active_count_label.setText(str(active_count))
        self.ir_count_label.setText(str(ir_count))

        # Week
        self.week_label.setText(str(data.get("current_week", 1)))

    def _populate_active_injuries_table(self):
        """Fill the active injuries table."""
        # Clear any previous spans (from "No injuries" message)
        self._clear_table_spans(self.active_table)

        self.active_table.setRowCount(len(self._active_injuries))

        if not self._active_injuries:
            self._show_no_injuries_message(self.active_table, "No active injuries")
            return

        for row, injury_data in enumerate(self._active_injuries):
            self._populate_active_injury_row(row, injury_data)

    def _populate_active_injury_row(self, row: int, injury_data: Dict):
        """Populate a single row in the active injuries table."""
        injury = injury_data.get("injury")
        position = injury_data.get("position", "")

        if not injury:
            return

        # Player name
        name_item = QTableWidgetItem(injury.player_name)
        name_item.setData(Qt.UserRole, injury.player_id)
        name_item.setData(Qt.UserRole + 1, injury.injury_id)
        self.active_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(position)
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.active_table.setItem(row, 1, pos_item)

        # Injury type
        injury_item = QTableWidgetItem(injury.display_name)
        self.active_table.setItem(row, 2, injury_item)

        # Severity with color coding
        severity_item = QTableWidgetItem(injury.severity.value)
        severity_item.setTextAlignment(Qt.AlignCenter)
        severity_color = self._get_severity_color(injury.severity.value)
        severity_item.setForeground(QColor(severity_color))
        self.active_table.setItem(row, 3, severity_item)

        # Weeks out
        weeks_item = QTableWidgetItem(str(injury.weeks_out))
        weeks_item.setTextAlignment(Qt.AlignCenter)
        self.active_table.setItem(row, 4, weeks_item)

        # Return week
        return_week = injury.estimated_return_week
        return_item = QTableWidgetItem(f"Week {return_week}")
        return_item.setTextAlignment(Qt.AlignCenter)
        self.active_table.setItem(row, 5, return_item)

        # IR eligibility status
        ir_eligible = injury.weeks_out >= self.IR_MINIMUM_GAMES
        if ir_eligible:
            status_text = "IR Eligible"
            status_color = Colors.SUCCESS
        else:
            status_text = f"< {self.IR_MINIMUM_GAMES} weeks"
            status_color = Colors.MUTED
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(status_color))
        self.active_table.setItem(row, 6, status_item)

        # Action button - only for user team
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if self._is_user_team:
            place_btn = QPushButton("+IR")
            place_btn.setEnabled(ir_eligible)

            if ir_eligible:
                place_btn.setStyleSheet(WARNING_BUTTON_STYLE)
                place_btn.setToolTip("Place on IR")
            else:
                place_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {Colors.DISABLED}; color: {Colors.MUTED}; "
                    f"border-radius: 3px; padding: 4px 12px; }}"
                )
                place_btn.setToolTip(f"Injury must be {self.IR_MINIMUM_GAMES}+ weeks")

            place_btn.clicked.connect(
                lambda checked, pid=injury.player_id, iid=injury.injury_id:
                self._on_place_on_ir_clicked(pid, iid)
            )
            action_layout.addWidget(place_btn)
        else:
            # Non-user team - show dash
            dash_label = QLabel("-")
            dash_label.setAlignment(Qt.AlignCenter)
            action_layout.addWidget(dash_label)

        self.active_table.setCellWidget(row, 7, action_widget)

    def _populate_ir_table(self):
        """Fill the IR table."""
        # Clear any previous spans (from "No players on IR" message)
        self._clear_table_spans(self.ir_table)

        self.ir_table.setRowCount(len(self._ir_players))

        if not self._ir_players:
            self._show_no_injuries_message(self.ir_table, "No players on IR")
            return

        for row, injury_data in enumerate(self._ir_players):
            self._populate_ir_row(row, injury_data)

    def _populate_ir_row(self, row: int, injury_data: Dict):
        """Populate a single row in the IR table."""
        injury = injury_data.get("injury")
        position = injury_data.get("position", "")

        if not injury:
            return

        # Player name
        name_item = QTableWidgetItem(injury.player_name)
        name_item.setData(Qt.UserRole, injury.player_id)
        self.ir_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(position)
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.ir_table.setItem(row, 1, pos_item)

        # Injury type
        injury_item = QTableWidgetItem(injury.display_name)
        self.ir_table.setItem(row, 2, injury_item)

        # Placed week
        placed_item = QTableWidgetItem(f"Week {injury.week_occurred}")
        placed_item.setTextAlignment(Qt.AlignCenter)
        self.ir_table.setItem(row, 3, placed_item)

        # Eligible week (placed week + 4)
        eligible_week = injury.week_occurred + self.IR_MINIMUM_GAMES
        eligible_item = QTableWidgetItem(f"Week {eligible_week}")
        eligible_item.setTextAlignment(Qt.AlignCenter)
        self.ir_table.setItem(row, 4, eligible_item)

        # Status - eligible to return?
        weeks_on_ir = self._current_week - injury.week_occurred
        can_activate = weeks_on_ir >= self.IR_MINIMUM_GAMES
        has_slots = self._ir_slots_remaining > 0
        has_roster_space = self._roster_count < 53  # 53-man roster limit

        if can_activate and has_slots and has_roster_space:
            status_text = "Eligible"
            status_color = Colors.SUCCESS
        elif can_activate and has_slots and not has_roster_space:
            status_text = "Roster Full"
            status_color = Colors.WARNING
        elif can_activate and not has_slots:
            status_text = "No Slots"
            status_color = Colors.ERROR
        else:
            status_text = f"Week {eligible_week}"
            status_color = Colors.MUTED

        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(status_color))
        self.ir_table.setItem(row, 5, status_item)

        # Action button - only for user team
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if self._is_user_team:
            activate_btn = QPushButton("Activate")
            can_use = can_activate and has_slots and has_roster_space
            activate_btn.setEnabled(can_use)

            if can_use:
                activate_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
                activate_btn.setToolTip("Activate from IR (uses 1 slot)")
            elif not can_activate:
                activate_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {Colors.DISABLED}; color: {Colors.MUTED}; "
                    f"border-radius: 3px; padding: 4px 12px; }}"
                )
                activate_btn.setToolTip(f"Not eligible until Week {eligible_week}")
            elif not has_roster_space:
                activate_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {Colors.DISABLED}; color: {Colors.MUTED}; "
                    f"border-radius: 3px; padding: 4px 12px; }}"
                )
                activate_btn.setToolTip(f"Roster full ({self._roster_count}/53). Cut a player first.")
            else:
                activate_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {Colors.DISABLED}; color: {Colors.MUTED}; "
                    f"border-radius: 3px; padding: 4px 12px; }}"
                )
                activate_btn.setToolTip("No IR return slots remaining")

            activate_btn.clicked.connect(
                lambda checked, pid=injury.player_id: self._on_activate_clicked(pid)
            )
            action_layout.addWidget(activate_btn)
        else:
            # Non-user team - show dash
            dash_label = QLabel("-")
            dash_label.setAlignment(Qt.AlignCenter)
            action_layout.addWidget(dash_label)

        self.ir_table.setCellWidget(row, 6, action_widget)

    def _clear_table_spans(self, table: QTableWidget):
        """Clear any spans in the table."""
        table.clearSpans()

    def _show_no_injuries_message(self, table: QTableWidget, message: str):
        """Show a message when table is empty."""
        table.setRowCount(1)
        table.setSpan(0, 0, 1, table.columnCount())

        message_item = QTableWidgetItem(message)
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor(Colors.MUTED))
        italic_font = Typography.BODY
        italic_font.setItalic(True)
        message_item.setFont(italic_font)

        table.setItem(0, 0, message_item)

    def _get_severity_color(self, severity: str) -> str:
        """Get color for injury severity."""
        severity_colors = {
            "minor": Colors.INFO,
            "moderate": Colors.WARNING,
            "severe": Colors.ERROR,
            "season_ending": Colors.ERROR,
        }
        return severity_colors.get(severity.lower(), Colors.MUTED)

    def _on_team_changed(self, index: int):
        """Handle team selection change."""
        if index >= 0:
            team_id = self.team_combo.itemData(index)
            if team_id:
                self._current_team_id = team_id
                self.team_changed.emit(team_id)

    def _on_place_on_ir_clicked(self, player_id: int, injury_id: int):
        """Handle Place on IR button click."""
        self.place_on_ir_requested.emit(player_id, injury_id)

    def _on_activate_clicked(self, player_id: int):
        """Handle Activate from IR button click."""
        self.activate_from_ir_requested.emit(player_id)

    def show_action_result(self, success: bool, message: str):
        """Display result of IR action to user."""
        # This will be connected to controller signal
        # For now just emit refresh to update view
        if success:
            self.refresh_requested.emit()

    def populate_team_selector(self, teams: List[Dict]):
        """
        Populate team combo box.

        Args:
            teams: List of dicts with team_id and name
        """
        self.team_combo.blockSignals(True)
        self.team_combo.clear()

        for team in teams:
            self.team_combo.addItem(team["name"], team["team_id"])

        self.team_combo.blockSignals(False)

    def set_selected_team(self, team_id: int):
        """Set the currently selected team in combo box."""
        for i in range(self.team_combo.count()):
            if self.team_combo.itemData(i) == team_id:
                self.team_combo.setCurrentIndex(i)
                break