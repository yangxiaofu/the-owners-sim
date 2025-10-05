"""
Calendar Controller for The Owner's Sim UI

Mediates between Calendar View and event database.
Provides access to calendar events with date-based filtering and navigation.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, date, timedelta
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Lazy import to avoid circular dependency issues
if TYPE_CHECKING:
    from events.event_database_api import EventDatabaseAPI


class CalendarController:
    """
    Controller for Calendar view operations.

    Manages event retrieval with date filtering, month navigation,
    and event detail access. Follows the pattern: View → Controller → Database
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize calendar controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize event database API (lazy import to avoid circular dependency)
        from events.event_database_api import EventDatabaseAPI
        self.event_api = EventDatabaseAPI(db_path)

        # Track current view state (start with current month/year)
        today = datetime.now()
        self.current_month = today.month
        self.current_year = today.year

    def get_events_for_month(
        self,
        year: int,
        month: int,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get filtered events for a specific month.

        Uses EventDatabaseAPI to retrieve events and filters by date range.
        Since the API doesn't have a date range method, we query all events
        and filter in memory.

        Args:
            year: Year to query
            month: Month to query (1-12)
            event_types: Optional list of event types to filter by
                        (e.g., ['GAME', 'DEADLINE', 'WINDOW'])
                        If None, returns all event types

        Returns:
            List of event dictionaries matching the criteria, ordered by timestamp
            Each dict contains: event_id, event_type, timestamp, game_id, data
        """
        # Calculate first and last day of month
        # Use timedelta to avoid importing stdlib calendar (shadowed by src/calendar)
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # Strategy: Query events by game_id prefix for this dynasty/season
        # This is more efficient than loading ALL events
        game_id_prefix = f"_{self.dynasty_id}_{self.season}_"

        all_events = []

        if event_types:
            # Query each event type separately
            for event_type in event_types:
                events = self.event_api.get_events_by_game_id_prefix(
                    prefix=game_id_prefix,
                    event_type=event_type
                )
                all_events.extend(events)
        else:
            # Query all event types for this dynasty/season
            all_events = self.event_api.get_events_by_game_id_prefix(
                prefix=game_id_prefix
            )

        # Filter by date range
        filtered_events = [
            event for event in all_events
            if first_day <= event['timestamp'] <= last_day
        ]

        # Sort by timestamp ascending (earliest first)
        filtered_events.sort(key=lambda e: e['timestamp'])

        return filtered_events

    def navigate_month(self, direction: int) -> Dict[str, int]:
        """
        Navigate to previous or next month.

        Handles year rollover automatically (e.g., Dec → Jan, Jan → Dec).
        Updates internal state and returns new month/year.

        Args:
            direction: +1 for next month, -1 for previous month

        Returns:
            Dict with 'month' and 'year' after navigation
        """
        # Calculate new month and year
        new_month = self.current_month + direction
        new_year = self.current_year

        # Handle year rollover
        if new_month > 12:
            new_month = 1
            new_year += 1
        elif new_month < 1:
            new_month = 12
            new_year -= 1

        # Update state
        self.current_month = new_month
        self.current_year = new_year

        return {
            'month': self.current_month,
            'year': self.current_year
        }

    def jump_to_today(self) -> Dict[str, int]:
        """
        Reset view to current month and year.

        Returns:
            Dict with 'month' and 'year' after jumping to today
        """
        today = datetime.now()
        self.current_month = today.month
        self.current_year = today.year

        return {
            'month': self.current_month,
            'year': self.current_year
        }

    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full event details by ID.

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found
            Dict contains: event_id, event_type, timestamp, game_id, data
        """
        return self.event_api.get_event_by_id(event_id)

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }

    def get_current_view_state(self) -> Dict[str, int]:
        """
        Get current month/year being viewed.

        Returns:
            Dict with 'month' and 'year'
        """
        return {
            'month': self.current_month,
            'year': self.current_year
        }

    def get_events_for_current_month(
        self,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get events for currently viewed month.

        Args:
            event_types: Optional list of event types to filter by

        Returns:
            List of event dictionaries for current month/year
        """
        return self.get_events_for_month(
            self.current_year,
            self.current_month,
            event_types
        )

    def get_current_simulation_date(self) -> Optional[str]:
        """
        Get current simulation date from dynasty_state table.

        Returns:
            Current simulation date as string (YYYY-MM-DD) or None if not found
        """
        # Import database connection
        from database.connection import DatabaseConnection

        db = DatabaseConnection(self.db_path)

        query = """
            SELECT current_date
            FROM dynasty_state
            WHERE dynasty_id = ? AND season = ?
        """

        result = db.execute_query(query, (self.dynasty_id, self.season))

        if result:
            return result[0]['current_date']

        return None

    def sync_view_to_simulation_date(self):
        """
        Jump calendar view to current simulation date.

        Updates current_month and current_year to match simulation state.
        """
        sim_date_str = self.get_current_simulation_date()

        if sim_date_str:
            # Parse date string (YYYY-MM-DD)
            parts = sim_date_str.split('-')
            if len(parts) == 3:
                self.current_year = int(parts[0])
                self.current_month = int(parts[1])

                return {
                    'month': self.current_month,
                    'year': self.current_year,
                    'date': sim_date_str
                }

        return None
