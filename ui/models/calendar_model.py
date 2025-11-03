"""
Calendar Model for The Owner's Sim UI

Qt table model for displaying calendar events in table views.
"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
from typing import List, Optional, Any, Dict
from datetime import datetime
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import TeamDataLoader


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

        # Team data loader for team name lookups
        self._team_loader = TeamDataLoader()

    def set_events(self, events: List[Dict[str, Any]]):
        """
        Set events data for display.

        Args:
            events: List of event dictionaries from calendar/event system
        """
        self.beginResetModel()
        self._events = sorted(events, key=self._get_sort_key)
        self.endResetModel()

    def _get_sort_key(self, event: Dict[str, Any]) -> float:
        """
        Get sortable key for event timestamp.

        Handles both datetime objects and int/float milliseconds to ensure
        consistent sorting across different timestamp formats.

        Args:
            event: Event dictionary

        Returns:
            Float timestamp in seconds for sorting
        """
        ts = event.get('timestamp')
        if not ts:
            return 0.0

        if isinstance(ts, datetime):
            # Convert datetime to float seconds
            return ts.timestamp()
        elif isinstance(ts, (int, float)):
            # Convert milliseconds to seconds
            return ts / 1000.0
        else:
            # Fallback for unexpected types
            return 0.0

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

        Handles multiple timestamp formats:
        - datetime objects
        - int/float milliseconds
        - string dates

        Args:
            event: Event dictionary

        Returns:
            Formatted date string (YYYY-MM-DD)
        """
        timestamp = event.get('timestamp')
        if not timestamp:
            return "N/A"

        # Handle string format
        if isinstance(timestamp, str):
            # Expected format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            return timestamp.split(' ')[0]

        # Handle datetime object
        if isinstance(timestamp, datetime):
            return timestamp.strftime('%Y-%m-%d')

        # Handle int/float milliseconds
        if isinstance(timestamp, (int, float)):
            try:
                dt = datetime.fromtimestamp(timestamp / 1000.0)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, OSError):
                return "Invalid Date"

        # Fallback for unexpected types
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
            away_id = parameters.get('away_team_id', '?')
            home_id = parameters.get('home_team_id', '?')

            # Look up team names from IDs
            away_team = self._team_loader.get_team_by_id(away_id) if isinstance(away_id, int) else None
            home_team = self._team_loader.get_team_by_id(home_id) if isinstance(home_id, int) else None

            # Format team names (fallback to ID if team not found)
            away_name = f"{away_team.city} {away_team.nickname}" if away_team else f"Team {away_id}"
            home_name = f"{home_team.city} {home_team.nickname}" if home_team else f"Team {home_id}"

            # Determine game type (playoff, preseason, or regular season)
            game_id = event.get('game_id', '')
            week = parameters.get('week', '?')

            # Check if this is a playoff game
            if game_id.startswith('playoff_'):
                # Extract playoff round from game_id
                # Format: playoff_YYYY_round_name_game_number
                # Examples: playoff_2025_wild_card_1, playoff_2025_divisional_1, playoff_2025_super_bowl
                round_label = self._extract_playoff_round(game_id)
                return f"{round_label}: {away_name} @ {home_name}"

            # Check if this is a preseason game
            # Method 1: Check for season_type or game_type parameter
            season_type = parameters.get('season_type', '')
            game_type = parameters.get('game_type', '')

            if season_type == 'preseason' or game_type == 'preseason':
                return f"Preseason Week {week}: {away_name} @ {home_name}"

            # Method 2: Fallback heuristic - check event date
            # If date is in August or early September (before Week 1), assume preseason
            event_date_str = event.get('date', event.get('timestamp', ''))
            if event_date_str:
                try:
                    from datetime import datetime
                    # Parse date string (format: YYYY-MM-DD or ISO format)
                    if isinstance(event_date_str, str):
                        if 'T' in event_date_str:
                            # ISO format with time
                            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                        else:
                            # Simple date format
                            event_date = datetime.strptime(event_date_str[:10], '%Y-%m-%d')

                        # Preseason games are in August
                        # Regular season typically starts in early September
                        if event_date.month == 8:  # August = preseason
                            return f"Preseason Week {week}: {away_name} @ {home_name}"
                        elif event_date.month == 9 and event_date.day < 10 and isinstance(week, int) and week <= 1:
                            # Early September Week 1 could still be preseason Week 4
                            # Only if week is explicitly 1 (preseason Week 4 is sometimes labeled as 1)
                            pass  # Fall through to regular season
                except (ValueError, TypeError):
                    pass  # If date parsing fails, fall through to regular season

            # Default: Regular season game
            return f"Week {week}: {away_name} @ {home_name}"

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

    def _extract_playoff_round(self, game_id: str) -> str:
        """
        Extract and format playoff round name from game_id.

        Playoff game_id format: playoff_{season}_{round_name}_{game_number}
        Examples:
            - playoff_2025_wild_card_1 → "Wild Card"
            - playoff_2025_divisional_1 → "Divisional Round"
            - playoff_2025_conference_1 → "Conference Championship"
            - playoff_2025_super_bowl → "Super Bowl"

        Args:
            game_id: Playoff game identifier

        Returns:
            Formatted playoff round label
        """
        try:
            # Split game_id by underscore
            parts = game_id.split('_')

            # Skip 'playoff' and season year (first 2 parts)
            # Take remaining parts (round name + optional game number)
            remaining = parts[2:]

            # Remove game number if present (last part is digit)
            if remaining and remaining[-1].isdigit():
                round_parts = remaining[:-1]
            else:
                round_parts = remaining

            # Join parts to get round name (e.g., 'wild_card', 'divisional')
            round_name = '_'.join(round_parts)

            # Map round names to display labels
            round_labels = {
                'wild_card': 'Wild Card',
                'divisional': 'Divisional Round',
                'conference': 'Conference Championship',
                'super_bowl': 'Super Bowl'
            }

            # Return formatted label or fallback to title case
            return round_labels.get(round_name, round_name.replace('_', ' ').title())

        except (IndexError, AttributeError):
            # Fallback if game_id format is unexpected
            return 'Playoff Game'

    def _format_status(self, event: Dict[str, Any]) -> str:
        """
        Format event status based on results.

        Shows winning team name with score for completed games.
        Format: "Team Name score-score" (e.g., "Cleveland Browns 45-49")

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
            # Show score with winning team name if available
            away_score = results.get('away_score')
            home_score = results.get('home_score')

            if away_score is not None and home_score is not None:
                # Get team IDs from parameters
                parameters = data.get('parameters', {})
                away_id = parameters.get('away_team_id')
                home_id = parameters.get('home_team_id')

                # Determine winner and format status
                if away_score > home_score:
                    # Away team won
                    winner_team = self._team_loader.get_team_by_id(away_id) if isinstance(away_id, int) else None
                    winner_name = f"{winner_team.city} {winner_team.nickname}" if winner_team else "Away"
                    return f"{winner_name} {away_score}-{home_score}"
                elif home_score > away_score:
                    # Home team won
                    winner_team = self._team_loader.get_team_by_id(home_id) if isinstance(home_id, int) else None
                    winner_name = f"{winner_team.city} {winner_team.nickname}" if winner_team else "Home"
                    return f"{winner_name} {home_score}-{away_score}"
                else:
                    # Tie game
                    return f"Tie {away_score}-{home_score}"
            else:
                return "Completed"

        # All other event types just show completed
        return "Completed"
