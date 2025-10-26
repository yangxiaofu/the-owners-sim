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

        # Current month state - sync to simulation date if available
        self.current_date = self._get_initial_date()

        # Track active filters
        self.active_filters: Set[str] = {"GAME", "DEADLINE", "WINDOW", "MILESTONE", "SCHEDULE_RELEASE"}

        # Build UI
        self._setup_ui()

        # Load initial data
        if self.controller:
            self.load_events()

    def _get_initial_date(self) -> datetime:
        """
        Get initial date for calendar view.

        Tries to sync to simulation date first. If no simulation date exists,
        defaults to September (season start) instead of current real-world month.

        Returns:
            datetime for initial calendar view
        """
        print(f"[DEBUG CalendarView] _get_initial_date() called")
        print(f"[DEBUG CalendarView] Controller exists: {self.controller is not None}")

        if not self.controller:
            print(f"[DEBUG CalendarView] NO CONTROLLER - returning datetime.now() = {datetime.now()}")
            return datetime.now()

        # Try to get simulation date from dynasty state
        sim_date_str = self.controller.get_current_simulation_date()
        print(f"[DEBUG CalendarView] get_current_simulation_date() returned: '{sim_date_str}'")

        if sim_date_str:
            # Parse YYYY-MM-DD format
            parts = sim_date_str.split('-')
            if len(parts) == 3:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    result = datetime(year, month, 1)
                    print(f"[DEBUG CalendarView] Parsed simulation date: {result}")
                    return result
                except (ValueError, IndexError) as e:
                    print(f"[DEBUG CalendarView] Failed to parse date '{sim_date_str}': {e}")
                    pass

        # Fall back to September (NFL season start) of current dynasty season
        # This is better than datetime.now() because new dynasties start in September
        dynasty_info = self.controller.get_dynasty_info()
        season = int(dynasty_info.get('season', 2025))
        fallback_date = datetime(season, 9, 1)  # September 1st of dynasty season
        print(f"[DEBUG CalendarView] Falling back to September: {fallback_date}")
        return fallback_date

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
        filter_label.setStyleSheet("font-weight: bold; color: #333333;")
        filter_bar.addWidget(filter_label)

        # Games filter
        self.games_checkbox = QCheckBox("Games")
        self.games_checkbox.setChecked(True)
        self.games_checkbox.setStyleSheet("color: #333333; font-weight: 500;")
        self.games_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.games_checkbox)

        # Deadlines filter
        self.deadlines_checkbox = QCheckBox("Deadlines")
        self.deadlines_checkbox.setChecked(True)
        self.deadlines_checkbox.setStyleSheet("color: #333333; font-weight: 500;")
        self.deadlines_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.deadlines_checkbox)

        # Windows filter
        self.windows_checkbox = QCheckBox("Windows")
        self.windows_checkbox.setChecked(True)
        self.windows_checkbox.setStyleSheet("color: #333333; font-weight: 500;")
        self.windows_checkbox.stateChanged.connect(self.handle_filter_change)
        filter_bar.addWidget(self.windows_checkbox)

        # Milestones filter
        self.milestones_checkbox = QCheckBox("Milestones")
        self.milestones_checkbox.setChecked(True)
        self.milestones_checkbox.setStyleSheet("color: #333333; font-weight: 500;")
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

        # Adjust column widths for optimal readability
        header = self.event_table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            # Set fixed widths for Date, Type, and Event columns
            # CalendarModel column indices: COL_DATE=0, COL_TYPE=1, COL_EVENT=2, COL_STATUS=3
            self.event_table.setColumnWidth(0, 100)    # Date
            self.event_table.setColumnWidth(1, 80)     # Type
            self.event_table.setColumnWidth(2, 450)    # Event (wide for full team names)
            # Status column (3) stretches to fill remaining space

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
        """Jump to current simulation date (in-game 'today')."""
        # Use same logic as initial date - get simulation date from dynasty state
        self.current_date = self._get_initial_date()
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

        # Get event summary from table model (just to extract event_id)
        event_summary = self.calendar_model.get_event_at_row(index.row())

        if not event_summary:
            self.details_label.setText("No event data available")
            return

        # Extract event ID
        event_id = event_summary.get('event_id')
        if not event_id:
            self.details_label.setText("Event ID not found")
            return

        # ✅ PROPER MVC: Call controller to get FULL event details from database
        full_event_details = self.controller.get_event_details(event_id)

        if not full_event_details:
            self.details_label.setText("Could not load event details")
            return

        # Format with COMPLETE event details
        details = self._format_event_details(full_event_details)
        self.details_label.setText(details)

    def _format_event_details(self, event) -> str:
        """
        Format event details for display.

        Args:
            event: Full event data from database via controller
                   Structure: {event_id, event_type, timestamp, game_id, dynasty_id, data}
                   data = {parameters, results, metadata}

        Returns:
            Formatted string with event details
        """
        if not event:
            return "No event data available"

        # Build details string
        details = []
        event_type = event.get('event_type', 'Unknown')
        timestamp = event.get('timestamp')

        # Format date
        if timestamp:
            if isinstance(timestamp, str):
                date_str = timestamp
            else:
                date_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
        else:
            date_str = 'Unknown'

        details.append(f"Event Type: {event_type}")
        details.append(f"Date: {date_str}")

        # Extract data sections (parameters, results, metadata)
        data = event.get('data', {})
        parameters = data.get('parameters', {})
        results = data.get('results', {})
        metadata = data.get('metadata', {})

        # Add event-specific details based on type
        if event_type == 'GAME':
            # Game parameters
            away_team_id = parameters.get('away_team_id')
            home_team_id = parameters.get('home_team_id')
            week = parameters.get('week', 'N/A')
            season_type = parameters.get('season_type', 'regular_season').replace('_', ' ').title()

            # Get team names for better display
            try:
                from team_management.teams.team_loader import TeamDataLoader
                team_loader = TeamDataLoader()
                away_team = team_loader.get_team_display_name(away_team_id) if away_team_id else "Unknown"
                home_team = team_loader.get_team_display_name(home_team_id) if home_team_id else "Unknown"
            except Exception:
                away_team = f"Team {away_team_id}"
                home_team = f"Team {home_team_id}"

            details.append(f"\nGame Information:")
            details.append(f"Week: {week} ({season_type})")
            details.append(f"Matchup: {away_team} @ {home_team}")

            # Game results (if completed)
            if results:
                away_score = results.get('away_score', 0)
                home_score = results.get('home_score', 0)
                winner_name = results.get('winner_name', 'Unknown')
                total_plays = results.get('total_plays', 0)
                total_drives = results.get('total_drives', 0)
                duration = results.get('game_duration_minutes', 0)

                details.append(f"\nFinal Score:")
                details.append(f"Team {away_team_id}: {away_score}")
                details.append(f"Team {home_team_id}: {home_score}")
                details.append(f"Winner: {winner_name}")
                details.append(f"\nGame Stats:")
                details.append(f"Total Plays: {total_plays}")
                details.append(f"Total Drives: {total_drives}")
                details.append(f"Duration: {duration} minutes")
            else:
                details.append(f"\nStatus: Scheduled (not yet played)")

        elif event_type == 'DEADLINE':
            deadline_type = parameters.get('deadline_type', 'Unknown')
            description = parameters.get('description', 'No description available')
            season_year = parameters.get('season_year', 'N/A')

            details.append(f"\nDeadline Type: {deadline_type}")
            details.append(f"Season: {season_year}")
            details.append(f"Description: {description}")

            # Show results if available
            if results:
                status = results.get('status', 'Unknown')
                details.append(f"Status: {status}")

        elif event_type == 'WINDOW':
            window_type = parameters.get('window_type', 'Unknown')
            description = parameters.get('description', 'No description available')
            start_date = parameters.get('start_date', 'N/A')
            end_date = parameters.get('end_date', 'N/A')

            details.append(f"\nWindow Type: {window_type}")
            details.append(f"Period: {start_date} to {end_date}")
            details.append(f"Description: {description}")

        elif event_type == 'MILESTONE':
            milestone_type = parameters.get('milestone_type', 'Unknown')
            description = parameters.get('description', 'No description available')

            details.append(f"\nMilestone: {milestone_type}")
            details.append(f"Description: {description}")

        else:
            # Generic fallback for unknown event types
            if parameters:
                details.append(f"\nParameters:")
                for key, value in parameters.items():
                    details.append(f"{key}: {value}")
            if results:
                details.append(f"\nResults:")
                for key, value in results.items():
                    details.append(f"{key}: {value}")

        # Add metadata if available
        if metadata:
            details.append(f"\nAdditional Info:")
            for key, value in metadata.items():
                if key not in ['event_id', 'game_id']:  # Skip IDs already shown
                    details.append(f"{key.replace('_', ' ').title()}: {value}")

        return "\n".join(details)

    def refresh(self):
        """Refresh the calendar view with latest data."""
        self.load_events()

    def refresh_current_date(self):
        """
        Refresh current_date from dynasty_state after simulation.

        This ensures the calendar view stays synced with the simulation date
        after day/week advancement. It re-queries the database for the current
        simulation date and reloads events for the new current month.
        """
        print("[DEBUG CalendarView] refresh_current_date() called")

        # Re-sync to current simulation date
        self.current_date = self._get_initial_date()

        print(f"[DEBUG CalendarView] Refreshed current_date to: {self.current_date}")

        # Reload events for the new current month
        self.load_events()

    def update_dynasty_info(self):
        """Update dynasty info label."""
        if self.controller:
            dynasty_info = self.controller.get_dynasty_info()
            info_text = f"Dynasty: {dynasty_info['dynasty_id']} | Season: {dynasty_info['season']}"
            self.dynasty_label.setText(info_text)
