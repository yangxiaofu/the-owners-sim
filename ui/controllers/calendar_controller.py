"""
Calendar Controller for The Owner's Sim UI

Mediates between Calendar View and event database.
Provides access to calendar events with date-based filtering and navigation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ui.domain_models.calendar_data_model import CalendarDataModel


class CalendarController:
    """
    Controller for Calendar view operations.

    Manages event retrieval with date filtering, month navigation,
    and event detail access. Follows the pattern: View → Controller → Database
    """

    def __init__(self, db_path: str, dynasty_id: str, main_window=None):
        """
        Initialize calendar controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            main_window: Reference to MainWindow for season access (optional)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.main_window = main_window

    @property
    def season(self) -> int:
        """Current season year (proxied from main window)."""
        if self.main_window is not None:
            return self.main_window.season
        return 2025  # Fallback for testing/standalone usage

    def _get_data_model(self) -> CalendarDataModel:
        """
        Lazy-initialized data model with current season.

        Caches the CalendarDataModel instance for performance, as the model now
        uses get_latest_state() which doesn't depend on a specific season value.
        """
        if not hasattr(self, '_data_model_cache'):
            self._data_model_cache = CalendarDataModel(self.db_path, self.dynasty_id, self.season)
        return self._data_model_cache

    def get_events_for_month(
        self,
        year: int,
        month: int,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get filtered events for a specific month (both scheduled and completed).

        Args:
            year: Year to query
            month: Month to query (1-12)
            event_types: Optional list of event types to filter by

        Returns:
            List of event dictionaries matching the criteria, ordered by timestamp
        """
        return self._get_data_model().get_events_for_month(year, month, event_types)

    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full event details by ID.

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found
        """
        return self._get_data_model().get_event_details(event_id)

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season
        """
        return self._get_data_model().get_dynasty_info()

    def get_current_simulation_date(self) -> Optional[str]:
        """
        Get current simulation date from dynasty_state table.

        Returns:
            Current simulation date as string (YYYY-MM-DD) or None if not found
        """
        return self._get_data_model().get_current_simulation_date()
