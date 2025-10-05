"""
Calendar View for The Owner's Sim

Displays NFL calendar with events (games, deadlines, windows, milestones).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTableView
)
from PySide6.QtCore import Qt
from datetime import datetime
from typing import Optional, Set

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from models.calendar_model import CalendarModel
from controllers.calendar_controller import CalendarController


class CalendarView(QWidget):
    """
    Calendar view for displaying NFL events.

    Shows schedule with games, deadlines, windows, and milestones.
    Provides month navigation and event filtering capabilities.
    """

    def __init__(self, parent=None, controller: Optional[CalendarController] = None):
        """
        Initialize calendar view.

        Args:
            parent: Parent widget
            controller: Calendar controller for data access
        """
        super().__init__(parent)
        self.main_window = parent
        self.controller = controller

        # Current month state
        self.current_date = datetime.now()

        # Track active filters
        self.active_filters: Set[str] = {"GAME", "DEADLINE", "WINDOW", "MILESTONE"}

        # Build UI
        self._setup_ui()

        # Load initial data
        if self.controller:
            self.load_events()

    def _setup_ui(self):
        """Build the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        layout.addLayout(self._create_header())

        # Navigation bar
        layout.addLayout(self._create_navigation_bar())

        # Filter checkboxes
        layout.addLayout(self._create_filter_bar())

        # Event table
        layout.addWidget(self._create_event_table())

        # Event details panel
        layout.addWidget(self._create_details_panel())

        self.setLayout(layout)

    def _create_header(self) -> QHBoxLayout:
        """
        Create header with title and dynasty info.

        Returns:
            QHBoxLayout with header elements
        """
        header = QHBoxLayout()

        # Title (left-aligned)
        title = QLabel("NFL Calendar")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)

        # Spacer
        header.addStretch()

        # Dynasty info (right-aligned)
        if self.controller:
            dynasty_info = self.controller.get_dynasty_info()
            info_text = f"Dynasty: {dynasty_info['dynasty_id']} | Season: {dynasty_info['season']}"
        else:
            info_text = "No dynasty loaded"

        self.dynasty_label = QLabel(info_text)
        self.dynasty_label.setStyleSheet("color: #666; font-size: 12px;")
        header.addWidget(self.dynasty_label)

        return header

    def _create_navigation_bar(self) -> QHBoxLayout:
        """
        Create navigation bar with month controls.

        Returns:
            QHBoxLayout with navigation buttons
        """
        nav_bar = QHBoxLayout()

        # Previous month button
        self.prev_button = QPushButton("<<")
        self.prev_button.setFixedWidth(50)
        self.prev_button.clicked.connect(self.handle_prev_month)
        nav_bar.addWidget(self.prev_button)

        # Current month/year label
        month_text = self.current_date.strftime("%B %Y")
        self.month_label = QLabel(month_text)
        self.month_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.month_label.setAlignment(Qt.AlignCenter)
        nav_bar.addWidget(self.month_label, stretch=1)

        # Next month button
        self.next_button = QPushButton(">>")
        self.next_button.setFixedWidth(50)
        self.next_button.clicked.connect(self.handle_next_month)
        nav_bar.addWidget(self.next_button)

        # Jump to today button
        self.today_button = QPushButton("Jump to Today")
        self.today_button.clicked.connect(self.handle_jump_today)
        nav_bar.addWidget(self.today_button)

        return nav_bar

    def _create_filter_bar(self) -> QHBoxLayout:
        """
        Create filter checkboxes for event types.

        Returns:
            QHBoxLayout with filter checkboxes
        """
        filter_bar = QHBoxLayout()

        # Filter label
        filter_label = QLabel("Show:")
        filter_label.setStyleSheet("font-weight: bold;")
        filter_bar.addWidget(filter_label)

        # Games filter
        self.games_checkbox = QCheckBox("Games")
        self.games_checkbox.setChecked(True)
        self.games_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.games_checkbox)

        # Deadlines filter
        self.deadlines_checkbox = QCheckBox("Deadlines")
        self.deadlines_checkbox.setChecked(True)
        self.deadlines_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.deadlines_checkbox)

        # Windows filter
        self.windows_checkbox = QCheckBox("Windows")
        self.windows_checkbox.setChecked(True)
        self.windows_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.windows_checkbox)

        # Milestones filter
        self.milestones_checkbox = QCheckBox("Milestones")
        self.milestones_checkbox.setChecked(True)
        self.milestones_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.milestones_checkbox)

        # Spacer
        filter_bar.addStretch()

        return filter_bar

    def _create_event_table(self) -> QTableView:
        """
        Create event table with model.

        Returns:
            QTableView configured for calendar events
        """
        # Create model
        self.calendar_model = CalendarModel()

        # Create table view
        self.event_table = QTableView()
        self.event_table.setModel(self.calendar_model)

        # Configure table
        self.event_table.setSortingEnabled(True)
        self.event_table.setAlternatingRowColors(True)
        self.event_table.setSelectionBehavior(QTableView.SelectRows)
        self.event_table.setSelectionMode(QTableView.SingleSelection)

        # Connect selection signal
        selection_model = self.event_table.selectionModel()
        if selection_model:
            selection_model.selectionChanged.connect(self._on_selection_changed)

        # Adjust column widths
        header = self.event_table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)

        return self.event_table

    def _create_details_panel(self) -> QLabel:
        """
        Create event details panel.

        Returns:
            QLabel for displaying event details
        """
        self.details_label = QLabel("Select an event to view details")
        self.details_label.setStyleSheet(
            "background-color: #f5f5f5; "
            "padding: 15px; "
            "border: 1px solid #ddd; "
            "border-radius: 4px; "
            "color: #666;"
        )
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.details_label.setWordWrap(True)
        self.details_label.setMinimumHeight(100)
        self.details_label.setMaximumHeight(150)

        return self.details_label

    def load_events(self):
        """Load events for current month from controller."""
        if not self.controller:
            return

        # Update month label
        month_text = self.current_date.strftime("%B %Y")
        self.month_label.setText(month_text)

        # Get month range
        year = self.current_date.year
        month = self.current_date.month

        # Calculate next month for end date
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        # Get events from controller
        events = self.controller.get_events_for_month(
            year=year,
            month=month,
            event_types=list(self.active_filters) if self.active_filters else None
        )

        # Update model
        self.calendar_model.set_events(events)

        # Clear details panel
        self.details_label.setText("Select an event to view details")

    def handle_prev_month(self):
        """Navigate to previous month."""
        # Calculate previous month
        year = self.current_date.year
        month = self.current_date.month

        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year

        self.current_date = datetime(prev_year, prev_month, 1)
        self.load_events()

    def handle_next_month(self):
        """Navigate to next month."""
        # Calculate next month
        year = self.current_date.year
        month = self.current_date.month

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        self.current_date = datetime(next_year, next_month, 1)
        self.load_events()

    def handle_jump_today(self):
        """Jump to today's month."""
        self.current_date = datetime.now()
        self.load_events()

    def handle_filter_change(self):
        """Reload events with new filters."""
        # Update active filters based on checkbox states
        self.active_filters.clear()

        if self.games_checkbox.isChecked():
            self.active_filters.add("GAME")

        if self.deadlines_checkbox.isChecked():
            self.active_filters.add("DEADLINE")

        if self.windows_checkbox.isChecked():
            self.active_filters.add("WINDOW")

        if self.milestones_checkbox.isChecked():
            self.active_filters.add("MILESTONE")

        # Reload events with new filters
        self.load_events()

    def _on_selection_changed(self):
        """Handle table selection change."""
        selection_model = self.event_table.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return

        # Get selected row
        indexes = selection_model.selectedRows()
        if not indexes:
            return

        index = indexes[0]
        self.handle_event_selected(index)

    def handle_event_selected(self, index):
        """
        Show event details for selected event.

        Args:
            index: QModelIndex of selected event
        """
        if not index.isValid():
            return

        # Get event from model
        event = self.calendar_model.get_event_at_row(index.row())
        if not event:
            self.details_label.setText("No event data available")
            return

        # Format event details
        details = self._format_event_details(event)
        self.details_label.setText(details)

    def _format_event_details(self, event) -> str:
        """
        Format event details for display.

        Args:
            event: Event object from model

        Returns:
            Formatted string with event details
        """
        # Build details string
        details = []
        details.append(f"Event Type: {event.get('event_type', 'Unknown')}")
        details.append(f"Date: {event.get('date', 'Unknown')}")

        # Add event-specific details
        event_type = event.get('event_type', '')

        if event_type == 'GAME':
            away_team = event.get('away_team', 'Unknown')
            home_team = event.get('home_team', 'Unknown')
            week = event.get('week', 'N/A')
            details.append(f"Matchup: {away_team} @ {home_team}")
            details.append(f"Week: {week}")

        elif event_type in ('DEADLINE', 'WINDOW', 'MILESTONE'):
            description = event.get('description', 'No description available')
            details.append(f"Description: {description}")

        # Add notes if available
        notes = event.get('notes', '')
        if notes:
            details.append(f"Notes: {notes}")

        return "\n".join(details)

    def refresh(self):
        """Refresh the calendar view with latest data."""
        self.load_events()

    def update_dynasty_info(self):
        """Update dynasty info label."""
        if self.controller:
            dynasty_info = self.controller.get_dynasty_info()
            info_text = f"Dynasty: {dynasty_info['dynasty_id']} | Season: {dynasty_info['season']}"
            self.dynasty_label.setText(info_text)
