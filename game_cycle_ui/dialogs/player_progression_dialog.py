"""
Player Progression Dialog - Shows development history and career arc chart.

Displays:
- Development info panel (Dev Curve, Peak Window, Current OVR, Potential, Upside)
- Career arc chart showing overall rating changes over time
- Season-by-season history table with before/after/change
"""

from typing import Dict, Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from game_cycle.database.progression_history_api import ProgressionHistoryAPI
from player_generation.archetypes.archetype_registry import ArchetypeRegistry
from game_cycle_ui.widgets.stat_frame import create_stat_display
from game_cycle_ui.theme import (
    Colors,
    Typography,
    FontSizes,
    TextColors,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
    apply_table_style
)


class PlayerProgressionDialog(QDialog):
    """
    Dialog showing player development history and career progression.

    Displays:
    - Development summary (curve type, peak window, current/potential/upside)
    - Line chart showing overall rating changes across seasons
    - History table with season-by-season changes
    """

    def __init__(
        self,
        player_id: int,
        player_name: str,
        player_data: Dict,
        dynasty_id: str,
        db_path: str,
        parent=None
    ):
        """
        Initialize player progression dialog.

        Args:
            player_id: Player's ID
            player_name: Player's display name
            player_data: Dict with potential, dev_type, overall, archetype_id, etc.
            dynasty_id: Current dynasty ID
            db_path: Path to the database
            parent: Parent widget
        """
        super().__init__(parent)
        self._player_id = player_id
        self._player_name = player_name
        self._player_data = player_data
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._history: List[Dict] = []
        self._archetype = None

        self.setWindowTitle(f"Player Development - {player_name}")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header with player name
        header = QLabel(f"Development: {self._player_name}")
        header.setFont(Typography.H5)
        layout.addWidget(header)

        # Development info panel
        self._create_dev_info_panel(layout)

        # Career arc chart
        self._create_career_arc_chart(layout)

        # History table
        self._create_history_table(layout)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_dev_info_panel(self, parent_layout: QVBoxLayout):
        """Create development info panel with 5 stat frames."""
        dev_group = QGroupBox("Development Profile")
        dev_layout = QHBoxLayout(dev_group)
        dev_layout.setSpacing(30)

        # Dev Curve
        self._dev_curve_label = create_stat_display(
            dev_layout, "Dev Curve", "Unknown"
        )

        # Peak Window
        self._peak_window_label = create_stat_display(
            dev_layout, "Peak Window", "N/A"
        )

        # Current OVR
        self._current_ovr_label = create_stat_display(
            dev_layout, "Current OVR", "0"
        )

        # Potential
        self._potential_label = create_stat_display(
            dev_layout, "Potential", "0"
        )

        # Upside
        self._upside_label = create_stat_display(
            dev_layout, "Upside", "0"
        )

        dev_layout.addStretch()
        parent_layout.addWidget(dev_group)

    def _create_career_arc_chart(self, parent_layout: QVBoxLayout):
        """Create the career arc line chart."""
        chart_group = QGroupBox("Career Arc")
        chart_layout = QVBoxLayout(chart_group)

        # Create chart view (will populate in _load_data)
        self._chart = QChart()
        self._chart.setTitle("")
        self._chart.legend().hide()

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(self._chart_view.renderHints())
        self._chart_view.setMinimumHeight(200)

        chart_layout.addWidget(self._chart_view)
        parent_layout.addWidget(chart_group, stretch=1)

    def _create_history_table(self, parent_layout: QVBoxLayout):
        """Create the season-by-season history table."""
        table_group = QGroupBox("Season History")
        table_layout = QVBoxLayout(table_group)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(5)
        self._history_table.setHorizontalHeaderLabels([
            "Season", "Age", "Before", "After", "Change"
        ])

        # Apply centralized table styling
        apply_table_style(self._history_table)

        # Configure column resize modes
        header = self._history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        table_layout.addWidget(self._history_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _load_data(self):
        """Load player development data from the database."""
        try:
            # Load archetype info
            archetype_id = self._player_data.get("archetype_id")
            if archetype_id:
                registry = ArchetypeRegistry()
                self._archetype = registry.get_archetype(archetype_id)

            # Load progression history
            history_api = ProgressionHistoryAPI(self._db_path)
            self._history = history_api.get_player_history(
                self._dynasty_id, self._player_id, limit=10
            )

            # Populate UI
            self._populate_dev_info()
            self._populate_chart()
            self._populate_history_table()

        except Exception as e:
            self._show_error(str(e))

    def _populate_dev_info(self):
        """Populate the development info panel."""
        # Dev Curve
        dev_curve = "Normal"
        dev_color = Colors.MUTED

        if self._archetype:
            curve_type = self._archetype.development_curve.lower()
            if curve_type == "early":
                dev_curve = "Early"
                dev_color = Colors.WARNING
            elif curve_type == "late":
                dev_curve = "Late"
                dev_color = Colors.INFO

        self._dev_curve_label.setText(dev_curve)
        self._dev_curve_label.setStyleSheet(f"color: {dev_color};")

        # Peak Window
        peak_window = "25-29"  # Default
        if self._archetype:
            peak_start, peak_end = self._archetype.peak_age_range
            peak_window = f"{peak_start}-{peak_end}"

        self._peak_window_label.setText(peak_window)

        # Current OVR
        current_ovr = self._player_data.get("overall", 0)
        self._current_ovr_label.setText(str(current_ovr))

        # Potential
        potential = self._player_data.get("potential", 0)
        self._potential_label.setText(str(potential))

        # Upside (difference between potential and current)
        upside = potential - current_ovr
        upside_color = Colors.MUTED
        if upside >= 10:
            upside_color = Colors.SUCCESS
        elif upside >= 5:
            upside_color = Colors.INFO

        self._upside_label.setText(f"+{upside}" if upside > 0 else str(upside))
        self._upside_label.setStyleSheet(f"color: {upside_color};")

    def _populate_chart(self):
        """Populate the career arc chart with history data."""
        if not self._history:
            # No history - show placeholder message
            self._chart.setTitle("No progression history available")
            return

        # Create line series (oldest to newest for chart)
        series = QLineSeries()
        series.setName("Overall Rating")

        # Reverse history (API returns newest first, we want oldest first for chart)
        for record in reversed(self._history):
            season = record["season"]
            overall_after = record["overall_after"]
            series.append(season, overall_after)

        # Add current season point if not in history
        if self._history:
            latest_season = self._history[0]["season"]
            current_ovr = self._player_data.get("overall", 0)
            # Only add if we have a newer season
            if latest_season < latest_season + 1:  # This would be current season logic
                pass  # For now, we'll just show historical data

        # Configure chart
        self._chart.removeAllSeries()
        self._chart.addSeries(series)

        # X-axis: Season (integer years)
        axis_x = QValueAxis()
        axis_x.setTitleText("Season")
        axis_x.setLabelFormat("%d")
        axis_x.setTickCount(min(len(self._history) + 1, 10))

        # Y-axis: Overall (range 50-100)
        axis_y = QValueAxis()
        axis_y.setTitleText("Overall Rating")
        axis_y.setRange(50, 100)
        axis_y.setTickCount(6)

        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        # Style the series
        pen = series.pen()
        pen.setWidth(3)
        pen.setColor(QColor(Colors.INFO))
        series.setPen(pen)

    def _populate_history_table(self):
        """Populate the history table with season data."""
        if not self._history:
            self._history_table.setRowCount(1)
            self._history_table.setSpan(0, 0, 1, 5)

            no_data_item = QTableWidgetItem("No progression history available")
            no_data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_item.setForeground(QColor(Colors.MUTED))
            self._history_table.setItem(0, 0, no_data_item)
            return

        # Populate table (newest first - already in that order from API)
        self._history_table.setRowCount(len(self._history))
        for row, record in enumerate(self._history):
            # Season
            season_item = QTableWidgetItem(str(record["season"]))
            season_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._history_table.setItem(row, 0, season_item)

            # Age
            age_item = QTableWidgetItem(str(record["age"]))
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._history_table.setItem(row, 1, age_item)

            # Before
            before_item = QTableWidgetItem(str(record["overall_before"]))
            before_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._history_table.setItem(row, 2, before_item)

            # After
            after_item = QTableWidgetItem(str(record["overall_after"]))
            after_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._history_table.setItem(row, 3, after_item)

            # Change
            change = record["overall_change"]
            change_text = f"+{change}" if change > 0 else str(change)
            change_item = QTableWidgetItem(change_text)
            change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            change_item.setFont(Typography.BODY_BOLD)

            # Color code the change
            if change > 0:
                change_item.setForeground(QColor(Colors.SUCCESS))
            elif change < 0:
                change_item.setForeground(QColor(Colors.ERROR))
            else:
                change_item.setForeground(QColor(Colors.MUTED))

            self._history_table.setItem(row, 4, change_item)

    def _show_error(self, message: str):
        """Display error message in the dialog."""
        self._history_table.setRowCount(1)
        self._history_table.setSpan(0, 0, 1, 5)

        error_item = QTableWidgetItem(f"Error loading progression data: {message}")
        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        error_item.setForeground(QColor(Colors.ERROR))
        self._history_table.setItem(0, 0, error_item)

        # Also show error in chart
        self._chart.setTitle(f"Error: {message}")
