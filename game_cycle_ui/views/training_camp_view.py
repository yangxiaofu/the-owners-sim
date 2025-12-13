"""
Training Camp View - Shows before/after player attribute changes.

Displays a table of all league players with their training camp
development results, including attribute changes and overall rating changes.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

from game_cycle_ui.theme import TABLE_HEADER_STYLE


class TrainingCampView(QWidget):
    """
    View for the training camp stage.

    Shows before/after comparison table for all players with:
    - Overall rating changes (+/- with color coding)
    - Individual attribute changes
    - Filter by team/position
    - Summary statistics panel
    """

    # Signals
    continue_clicked = Signal()  # User ready to proceed

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._results: List[Dict] = []
        self._filtered_results: List[Dict] = []
        self._summary: Dict[str, Any] = {}
        self._user_team_id: int = 1
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Filter panel
        self._create_filter_panel(layout)

        # Tab widget for different views
        self._create_tabs(layout)

        # Continue button at bottom
        self._create_continue_button(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary statistics panel."""
        summary_group = QGroupBox("Training Camp Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Total players
        self._create_stat_widget(
            summary_layout, "total_label", "Total Players", "0"
        )

        # Improved
        self._create_stat_widget(
            summary_layout, "improved_label", "Improved", "0",
            color="#2E7D32"  # Green
        )

        # Declined
        self._create_stat_widget(
            summary_layout, "declined_label", "Declined", "0",
            color="#C62828"  # Red
        )

        # Unchanged
        self._create_stat_widget(
            summary_layout, "unchanged_label", "Unchanged", "0",
            color="#666"
        )

        # Depth charts updated
        self._create_stat_widget(
            summary_layout, "depth_chart_label", "Depth Charts", "0/32",
            color="#1976D2"  # Blue
        )

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_stat_widget(
        self,
        parent_layout: QHBoxLayout,
        attr_name: str,
        title: str,
        initial_value: str,
        color: Optional[str] = None
    ):
        """Create a single stat widget."""
        frame = QFrame()
        vlayout = QVBoxLayout(frame)
        vlayout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 11px;")
        vlayout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        if color:
            value_label.setStyleSheet(f"color: {color};")
        vlayout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        parent_layout.addWidget(frame)

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls."""
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)

        # Team filter
        team_label = QLabel("Team:")
        filter_layout.addWidget(team_label)

        self.team_combo = QComboBox()
        self.team_combo.addItem("All Teams", -1)
        self.team_combo.addItem("Free Agents", 0)
        # Populate with actual team names
        from team_management.teams.team_loader import get_all_teams
        teams = get_all_teams()
        sorted_teams = sorted(teams, key=lambda t: f"{t.city} {t.nickname}")
        for team in sorted_teams:
            self.team_combo.addItem(f"{team.city} {team.nickname}", team.team_id)
        self.team_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.team_combo)

        filter_layout.addSpacing(20)

        # Position filter
        pos_label = QLabel("Position:")
        filter_layout.addWidget(pos_label)

        self.position_combo = QComboBox()
        self.position_combo.addItem("All Positions", "")
        positions = [
            "Quarterback", "Running Back", "Wide Receiver", "Tight End",
            "Left Tackle", "Left Guard", "Center", "Right Guard", "Right Tackle",
            "Defensive End", "Defensive Tackle", "Linebacker",
            "Cornerback", "Safety", "Kicker", "Punter"
        ]
        for pos in positions:
            self.position_combo.addItem(pos, pos.lower().replace(" ", "_"))
        self.position_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.position_combo)

        filter_layout.addSpacing(20)

        # Change type filter
        change_label = QLabel("Show:")
        filter_layout.addWidget(change_label)

        self.change_combo = QComboBox()
        self.change_combo.addItem("All Players", "all")
        self.change_combo.addItem("Improved Only", "improved")
        self.change_combo.addItem("Declined Only", "declined")
        self.change_combo.addItem("Changed Only", "changed")
        self.change_combo.addItem("Breakouts Only", "breakout")
        self.change_combo.addItem("Busts Only", "bust")
        self.change_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.change_combo)

        filter_layout.addStretch()
        parent_layout.addWidget(filter_frame)

    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create tab widget with different views."""
        self.tab_widget = QTabWidget()

        # Main results table
        self._create_results_table()
        self.tab_widget.addTab(self.results_table, "All Players")

        # Top gainers table
        self._create_top_gainers_table()
        self.tab_widget.addTab(self.top_gainers_table, "Top Gainers")

        # Biggest declines table
        self._create_declines_table()
        self.tab_widget.addTab(self.declines_table, "Biggest Declines")

        # Position breakdown table
        self._create_position_breakdown_table()
        self.tab_widget.addTab(self.position_breakdown_table, "By Position")

        parent_layout.addWidget(self.tab_widget, stretch=1)

    def _create_results_table(self):
        """Create main results table."""
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Player", "Position", "Team", "Age", "Category",
            "Old OVR", "New OVR", "Change", "Potential"
        ])
        self._configure_table(self.results_table)

    def _create_top_gainers_table(self):
        """Create top gainers table."""
        self.top_gainers_table = QTableWidget()
        self.top_gainers_table.setColumnCount(9)
        self.top_gainers_table.setHorizontalHeaderLabels([
            "Player", "Position", "Team", "Age", "Category",
            "Old OVR", "New OVR", "Change", "Potential"
        ])
        self._configure_table(self.top_gainers_table)

    def _create_declines_table(self):
        """Create biggest declines table."""
        self.declines_table = QTableWidget()
        self.declines_table.setColumnCount(9)
        self.declines_table.setHorizontalHeaderLabels([
            "Player", "Position", "Team", "Age", "Category",
            "Old OVR", "New OVR", "Change", "Potential"
        ])
        self._configure_table(self.declines_table)

    def _create_position_breakdown_table(self):
        """Create position breakdown table."""
        self.position_breakdown_table = QTableWidget()
        self.position_breakdown_table.setColumnCount(6)
        self.position_breakdown_table.setHorizontalHeaderLabels([
            "Position", "Players", "Improved", "Declined", "Avg Change", "Breakouts"
        ])

        header = self.position_breakdown_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Position
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.position_breakdown_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.position_breakdown_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.position_breakdown_table.setAlternatingRowColors(True)
        self.position_breakdown_table.verticalHeader().setVisible(False)

    def _configure_table(self, table: QTableWidget):
        """Configure table appearance."""
        header = table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name
        for i in range(1, 9):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        # Connect double-click handler
        table.cellDoubleClicked.connect(self._on_row_double_clicked)

    def _create_continue_button(self, parent_layout: QVBoxLayout):
        """Create continue button."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.continue_btn = QPushButton("Continue to Preseason")
        self.continue_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 10px 24px; font-size: 14px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        self.continue_btn.clicked.connect(self.continue_clicked.emit)
        btn_layout.addWidget(self.continue_btn)

        parent_layout.addLayout(btn_layout)

    def set_training_camp_data(self, data: Dict[str, Any]):
        """
        Populate the view with training camp results.

        Args:
            data: Dictionary containing:
                - results: List of PlayerDevelopmentResult (as dicts)
                - summary: Summary statistics dict
                - depth_chart_summary: Depth chart update info
        """
        # Convert dataclass results to dicts if needed
        self._results = []
        for r in data.get("results", []):
            if hasattr(r, "__dict__"):
                # It's a dataclass
                age_cat = r.age_category
                if hasattr(age_cat, 'value'):
                    age_cat = age_cat.value
                result_dict = {
                    "player_id": r.player_id,
                    "player_name": r.player_name,
                    "position": r.position,
                    "age": r.age,
                    "team_id": r.team_id,
                    "age_category": age_cat,
                    "old_overall": r.old_overall,
                    "new_overall": r.new_overall,
                    "overall_change": r.overall_change,
                    "potential": getattr(r, "potential", 0),
                }
                self._results.append(result_dict)
            else:
                self._results.append(r)

        self._summary = data.get("summary", {})
        depth_summary = data.get("depth_chart_summary", {})

        # Update summary labels
        self.total_label.setText(str(self._summary.get("total_players", 0)))
        self.improved_label.setText(
            f"{self._summary.get('improved_count', 0)} ({self._summary.get('improved_pct', 0)}%)"
        )
        self.declined_label.setText(
            f"{self._summary.get('declined_count', 0)} ({self._summary.get('declined_pct', 0)}%)"
        )
        self.unchanged_label.setText(str(self._summary.get("unchanged_count", 0)))
        self.depth_chart_label.setText(
            f"{depth_summary.get('teams_updated', 0)}/{depth_summary.get('total_teams', 32)}"
        )

        # Populate top gainers/declines from summary
        top_gainers = self._summary.get("top_gainers", [])
        biggest_declines = self._summary.get("biggest_declines", [])

        self._populate_table(self.top_gainers_table, top_gainers)
        self._populate_table(self.declines_table, biggest_declines)

        # Populate position breakdown
        self._populate_position_breakdown()

        # Apply filters to main table
        self._apply_filters()

    def _apply_filters(self):
        """Apply filters to main results table."""
        team_filter = self.team_combo.currentData()
        position_filter = self.position_combo.currentData()
        change_filter = self.change_combo.currentData()

        self._filtered_results = []

        for result in self._results:
            # Team filter
            if team_filter != -1 and result.get("team_id") != team_filter:
                continue

            # Position filter
            if position_filter:
                pos = result.get("position", "").lower().replace(" ", "_")
                if pos != position_filter:
                    continue

            # Change type filter
            change = result.get("overall_change", 0)
            if change_filter == "improved" and change <= 0:
                continue
            elif change_filter == "declined" and change >= 0:
                continue
            elif change_filter == "changed" and change == 0:
                continue
            elif change_filter == "breakout" and not self._is_breakout(result):
                continue
            elif change_filter == "bust" and not self._is_bust(result):
                continue

            self._filtered_results.append(result)

        # Sort by change (descending)
        self._filtered_results.sort(
            key=lambda r: r.get("overall_change", 0),
            reverse=True
        )

        self._populate_table(self.results_table, self._filtered_results)

    def _is_breakout(self, result) -> bool:
        """
        Determine if a player had a breakout season.

        Breakout criteria:
        - 5+ overall gain for any age
        - 3+ overall gain for veterans
        """
        change = result.get("overall_change", 0) if isinstance(result, dict) else getattr(result, "overall_change", 0)
        age_category = result.get("age_category", "prime") if isinstance(result, dict) else getattr(result, "age_category", "prime")
        if hasattr(age_category, 'value'):
            age_category = age_category.value
        return change >= 5 or (age_category == "veteran" and change >= 3)

    def _is_bust(self, result) -> bool:
        """
        Determine if a player busted (unexpectedly declined).

        Bust criteria:
        - Young player with 2+ point decline
        """
        change = result.get("overall_change", 0) if isinstance(result, dict) else getattr(result, "overall_change", 0)
        age_category = result.get("age_category", "prime") if isinstance(result, dict) else getattr(result, "age_category", "prime")
        if hasattr(age_category, 'value'):
            age_category = age_category.value
        return age_category == "young" and change < -2

    def _populate_table(self, table: QTableWidget, results: List):
        """Populate a table with results."""
        # Handle both dataclass and dict formats
        processed_results = []
        for r in results:
            if hasattr(r, "__dict__"):
                age_cat = r.age_category
                if hasattr(age_cat, 'value'):
                    age_cat = age_cat.value
                processed_results.append({
                    "player_name": r.player_name,
                    "position": r.position,
                    "team_id": r.team_id,
                    "age": r.age,
                    "age_category": age_cat,
                    "old_overall": r.old_overall,
                    "new_overall": r.new_overall,
                    "overall_change": r.overall_change,
                    "potential": getattr(r, "potential", 0),
                    "player_id": getattr(r, "player_id", 0),
                })
            else:
                processed_results.append(r)

        table.setRowCount(len(processed_results))

        for row, result in enumerate(processed_results):
            self._populate_row(table, row, result)

    def _populate_row(self, table: QTableWidget, row: int, result: Dict):
        """Populate a single row."""
        change = result.get("overall_change", 0)
        is_breakout = self._is_breakout(result)
        is_bust = self._is_bust(result)

        # Determine row highlight color and text color
        if is_breakout:
            row_color = QColor("#E1F5FE")  # Light blue background
            text_color = QColor("#0D47A1")  # Dark blue text
        elif is_bust:
            row_color = QColor("#FFEBEE")  # Light red background
            text_color = QColor("#B71C1C")  # Dark red text
        elif change > 0:
            row_color = QColor("#E8F5E9")  # Light green background
            text_color = QColor("#1B5E20")  # Dark green text
        elif change < 0:
            row_color = QColor("#FFEBEE")  # Light red background
            text_color = QColor("#B71C1C")  # Dark red text
        else:
            row_color = None
            text_color = None

        # Player name with prefix for breakout/bust
        player_name = result.get("player_name", "Unknown")
        if is_breakout:
            player_name = "★ " + player_name
        elif is_bust:
            player_name = "⚠ " + player_name

        name_item = QTableWidgetItem(player_name)
        name_item.setData(Qt.UserRole, result.get("player_id"))
        if row_color:
            name_item.setBackground(QBrush(row_color))
            name_item.setForeground(text_color)
        table.setItem(row, 0, name_item)

        # Position
        from constants.position_abbreviations import get_position_abbreviation
        pos_abbrev = get_position_abbreviation(result.get("position", ""))
        pos_item = QTableWidgetItem(pos_abbrev)
        pos_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            pos_item.setBackground(QBrush(row_color))
            pos_item.setForeground(text_color)
        table.setItem(row, 1, pos_item)

        # Team
        team_id = result.get("team_id", 0)
        team_text = self._get_team_name(team_id)
        team_item = QTableWidgetItem(team_text)
        team_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            team_item.setBackground(QBrush(row_color))
            team_item.setForeground(text_color)
        table.setItem(row, 2, team_item)

        # Age
        age_item = QTableWidgetItem(str(result.get("age", 0)))
        age_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            age_item.setBackground(QBrush(row_color))
            age_item.setForeground(text_color)
        table.setItem(row, 3, age_item)

        # Age category
        category = result.get("age_category", "prime")
        if hasattr(category, 'value'):
            category = category.value
        cat_item = QTableWidgetItem(str(category).title())
        cat_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            cat_item.setBackground(QBrush(row_color))
            cat_item.setForeground(text_color)
        table.setItem(row, 4, cat_item)

        # Old overall
        old_ovr_item = QTableWidgetItem(str(result.get("old_overall", 0)))
        old_ovr_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            old_ovr_item.setBackground(QBrush(row_color))
            old_ovr_item.setForeground(text_color)
        table.setItem(row, 5, old_ovr_item)

        # New overall
        new_ovr_item = QTableWidgetItem(str(result.get("new_overall", 0)))
        new_ovr_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            new_ovr_item.setBackground(QBrush(row_color))
            new_ovr_item.setForeground(text_color)
        table.setItem(row, 6, new_ovr_item)

        # Change with color coding
        if change > 0:
            change_text = f"+{change}"
            change_color = QColor("#2E7D32")
        elif change < 0:
            change_text = str(change)
            change_color = QColor("#C62828")
        else:
            change_text = "0"
            change_color = QColor("#666")

        change_item = QTableWidgetItem(change_text)
        change_item.setTextAlignment(Qt.AlignCenter)
        change_item.setForeground(change_color)
        change_item.setFont(QFont("Arial", 10, QFont.Bold))
        if row_color:
            change_item.setBackground(QBrush(row_color))
        table.setItem(row, 7, change_item)

        # Potential with color coding
        potential = result.get("potential", 0)
        new_overall = result.get("new_overall", 0)
        upside = potential - new_overall

        potential_item = QTableWidgetItem(str(potential))
        potential_item.setTextAlignment(Qt.AlignCenter)

        # Color code based on upside
        if upside <= 2:
            # Near ceiling - Green
            potential_item.setForeground(QColor("#2E7D32"))
        elif upside >= 10:
            # High upside - Blue
            potential_item.setForeground(QColor("#1976D2"))

        if row_color:
            potential_item.setBackground(QBrush(row_color))
            if is_breakout or is_bust:
                potential_item.setForeground(text_color)

        table.setItem(row, 8, potential_item)

    def _populate_position_breakdown(self):
        """Populate the position breakdown table."""
        # Position groupings
        position_groups = {
            "QB": ["quarterback"],
            "RB": ["running_back"],
            "FB": ["fullback"],
            "WR": ["wide_receiver"],
            "TE": ["tight_end"],
            "OL": ["left_tackle", "left_guard", "center", "right_guard", "right_tackle"],
            "DL": ["defensive_end", "defensive_tackle"],
            "LB": ["linebacker"],
            "DB": ["cornerback", "safety"],
            "K": ["kicker"],
            "P": ["punter"]
        }

        breakdown_data = {}

        for group_name, positions in position_groups.items():
            players = []
            improved = 0
            declined = 0
            total_change = 0
            breakouts = 0

            for result in self._results:
                pos = result.get("position", "").lower().replace(" ", "_")
                if pos in positions:
                    players.append(result)
                    change = result.get("overall_change", 0)
                    total_change += change
                    if change > 0:
                        improved += 1
                    elif change < 0:
                        declined += 1
                    if self._is_breakout(result):
                        breakouts += 1

            if players:
                avg_change = total_change / len(players)
                breakdown_data[group_name] = {
                    "count": len(players),
                    "improved": improved,
                    "declined": declined,
                    "avg_change": avg_change,
                    "breakouts": breakouts
                }

        # Populate table
        self.position_breakdown_table.setRowCount(len(breakdown_data))
        row = 0

        for position, data in sorted(breakdown_data.items()):
            # Position
            pos_item = QTableWidgetItem(position)
            pos_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.position_breakdown_table.setItem(row, 0, pos_item)

            # Players
            count_item = QTableWidgetItem(str(data["count"]))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.position_breakdown_table.setItem(row, 1, count_item)

            # Improved
            improved_item = QTableWidgetItem(str(data["improved"]))
            improved_item.setTextAlignment(Qt.AlignCenter)
            improved_item.setForeground(QColor("#2E7D32"))
            self.position_breakdown_table.setItem(row, 2, improved_item)

            # Declined
            declined_item = QTableWidgetItem(str(data["declined"]))
            declined_item.setTextAlignment(Qt.AlignCenter)
            declined_item.setForeground(QColor("#C62828"))
            self.position_breakdown_table.setItem(row, 3, declined_item)

            # Avg Change
            avg_change = data["avg_change"]
            if avg_change > 0:
                avg_text = f"+{avg_change:.2f}"
                avg_color = QColor("#2E7D32")
            elif avg_change < 0:
                avg_text = f"{avg_change:.2f}"
                avg_color = QColor("#C62828")
            else:
                avg_text = "0.00"
                avg_color = QColor("#666")

            avg_item = QTableWidgetItem(avg_text)
            avg_item.setTextAlignment(Qt.AlignCenter)
            avg_item.setForeground(avg_color)
            avg_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.position_breakdown_table.setItem(row, 4, avg_item)

            # Breakouts
            breakout_item = QTableWidgetItem(str(data["breakouts"]))
            breakout_item.setTextAlignment(Qt.AlignCenter)
            if data["breakouts"] > 0:
                breakout_item.setForeground(QColor("#1976D2"))
                breakout_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.position_breakdown_table.setItem(row, 5, breakout_item)

            row += 1

    def _get_team_name(self, team_id: int) -> str:
        """Get team display name from team_id."""
        if team_id == 0:
            return "FA"
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else f"T{team_id}"
        except Exception:
            return f"T{team_id}"

    def clear(self):
        """Clear all data from the view."""
        self._results = []
        self._filtered_results = []
        self._summary = {}

        self.total_label.setText("0")
        self.improved_label.setText("0")
        self.declined_label.setText("0")
        self.unchanged_label.setText("0")
        self.depth_chart_label.setText("0/32")

        self.results_table.setRowCount(0)
        self.top_gainers_table.setRowCount(0)
        self.declines_table.setRowCount(0)
        self.position_breakdown_table.setRowCount(0)

    def set_dynasty_info(self, dynasty_id: str, db_path: str):
        """Store dynasty info for player detail dialog access."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def _on_row_double_clicked(self, row: int, column: int):
        """Handle double-click to open player progression dialog."""
        # Get the sending table
        table = self.sender()

        # Get player_id from name cell's UserRole data
        name_item = table.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        if not player_id:
            return

        # Get player name
        player_name = name_item.text().lstrip("★⚠ ")  # Remove breakout/bust prefix

        # Build player_data dict from row
        player_data = {
            "player_id": player_id,
            "overall": int(table.item(row, 6).text()) if table.item(row, 6) else 70,  # New OVR column
            "potential": int(table.item(row, 8).text()) if table.item(row, 8) else 99,  # Potential column
        }

        # Check if dynasty info is available
        if not hasattr(self, '_dynasty_id') or not hasattr(self, '_db_path'):
            return

        if not self._dynasty_id or not self._db_path:
            return

        # Import and open dialog
        from game_cycle_ui.dialogs.player_progression_dialog import PlayerProgressionDialog
        dialog = PlayerProgressionDialog(
            player_id=player_id,
            player_name=player_name,
            player_data=player_data,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path,
            parent=self
        )
        dialog.exec()

    def set_user_team_id(self, team_id: int):
        """
        Set the user's team ID and default the team filter to their team.

        Args:
            team_id: The user's team ID (1-32)
        """
        self._user_team_id = team_id
        # Find and select the user's team in the combo box
        for i in range(self.team_combo.count()):
            if self.team_combo.itemData(i) == team_id:
                self.team_combo.setCurrentIndex(i)
                break