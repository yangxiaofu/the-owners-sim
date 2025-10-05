"""
Calendar Model for The Owner's Sim UI

Qt table model for displaying calendar events in table views.
"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
from typing import List, Optional, Any, Dict
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class CalendarModel(QAbstractTableModel):
    """
    Qt table model for displaying calendar events.

    Displays event information in a sortable table format with color-coded rows
    based on event type (GAME, DEADLINE, WINDOW, MILESTONE).
    """

    # Column indices
    COL_DATE = 0
    COL_TYPE = 1
    COL_EVENT = 2
    COL_STATUS = 3

    # Color coding for event types
    COLOR_GAME = QColor("#C8E6FF")      # Light blue
    COLOR_DEADLINE = QColor("#FFC8C8")  # Light red
    COLOR_WINDOW = QColor("#FFFFC8")    # Light yellow
    COLOR_MILESTONE = QColor("#DCFFDC") # Light green

    def __init__(self, parent=None):
        """Initialize calendar model."""
        super().__init__(parent)
        self._events: List[Dict[str, Any]] = []

        # Column headers
        self._headers = ["Date", "Type", "Event", "Status"]

    def set_events(self, events: List[Dict[str, Any]]):
        """
        Set events data for display.

        Args:
            events: List of event dictionaries from calendar/event system
        """
        self.beginResetModel()
        self._events = sorted(events, key=lambda e: e.get('timestamp', ''))
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows (events)."""
        if parent.isValid():
            return 0
        return len(self._events)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None

        if role not in (Qt.DisplayRole, Qt.TextAlignmentRole, Qt.BackgroundRole):
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._events):
            return None

        event = self._events[row]

        # Background color based on event type
        if role == Qt.BackgroundRole:
            event_type = event.get('event_type', '').upper()

            if event_type == 'GAME':
                return self.COLOR_GAME
            elif event_type == 'DEADLINE':
                return self.COLOR_DEADLINE
            elif event_type == 'WINDOW':
                return self.COLOR_WINDOW
            elif event_type == 'MILESTONE':
                return self.COLOR_MILESTONE

            return None

        if role == Qt.TextAlignmentRole:
            # Left-align Event column, center others
            if col == self.COL_EVENT:
                return Qt.AlignLeft | Qt.AlignVCenter
            return Qt.AlignCenter

        # Display role
        if col == self.COL_DATE:
            return self._format_date(event)

        elif col == self.COL_TYPE:
            return event.get('event_type', 'UNKNOWN').upper()

        elif col == self.COL_EVENT:
            return self._format_event_description(event)

        elif col == self.COL_STATUS:
            return self._format_status(event)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]

        elif orientation == Qt.Vertical:
            return str(section + 1)

        return None

    def get_event_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        """
        Get event dict at given row index.

        Args:
            row: Row index

        Returns:
            Event dictionary or None if invalid row
        """
        if 0 <= row < len(self._events):
            return self._events[row]
        return None

    def clear(self):
        """Clear all data from model."""
        self.beginResetModel()
        self._events = []
        self.endResetModel()

    def _format_date(self, event: Dict[str, Any]) -> str:
        """
        Format event date for display.

        Args:
            event: Event dictionary

        Returns:
            Formatted date string
        """
        timestamp = event.get('timestamp')
        if not timestamp:
            return "N/A"

        # Handle both string and datetime formats
        if isinstance(timestamp, str):
            # Expected format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            return timestamp.split(' ')[0]

        # If it's a datetime object
        try:
            return timestamp.strftime('%Y-%m-%d')
        except:
            return str(timestamp)

    def _format_event_description(self, event: Dict[str, Any]) -> str:
        """
        Format event description based on event type.

        Extracts relevant information from event.data.parameters to create
        a human-readable description.

        Args:
            event: Event dictionary

        Returns:
            Formatted event description
        """
        event_type = event.get('event_type', '').upper()
        data = event.get('data', {})
        parameters = data.get('parameters', {})

        if event_type == 'GAME':
            # Format: "Team {away} @ Team {home}"
            away_id = parameters.get('away_team_id', '?')
            home_id = parameters.get('home_team_id', '?')
            week = parameters.get('week', '?')
            return f"Week {week}: Team {away_id} @ Team {home_id}"

        elif event_type == 'DEADLINE':
            # Use description field from parameters
            return parameters.get('description', 'Deadline Event')

        elif event_type == 'WINDOW':
            # Format: "{window_name} {window_type}"
            window_name = parameters.get('window_name', 'Unknown Window')
            window_type = parameters.get('window_type', 'Unknown')
            return f"{window_name} {window_type}"

        elif event_type == 'MILESTONE':
            # Use description field from parameters
            return parameters.get('description', 'Milestone Event')

        # Fallback: try to get a description from parameters or data
        return parameters.get('description', data.get('description', 'Unknown Event'))

    def _format_status(self, event: Dict[str, Any]) -> str:
        """
        Format event status based on results.

        Args:
            event: Event dictionary

        Returns:
            Formatted status string
        """
        data = event.get('data', {})
        results = data.get('results')

        # If no results, event is scheduled
        if not results:
            return "Scheduled"

        event_type = event.get('event_type', '').upper()

        if event_type == 'GAME':
            # Show score if available
            away_score = results.get('away_score')
            home_score = results.get('home_score')

            if away_score is not None and home_score is not None:
                return f"{away_score}-{home_score}"
            else:
                return "Completed"

        # All other event types just show completed
        return "Completed"
