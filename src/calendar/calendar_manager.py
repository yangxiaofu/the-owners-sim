"""
Calendar Manager

Main calendar interface that coordinates date tracking and event management.
Provides a clean, simple API for all calendar operations.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Union
import logging

from .event import Event
from .event_manager import EventManager


class CalendarManager:
    """
    Main calendar system interface.

    Coordinates date tracking, event scheduling, and event retrieval.
    Provides a simple, clean API for all calendar operations.
    """

    def __init__(self, start_date: Union[date, datetime],
                 database_path: str = "data/database/nfl_simulation.db",
                 enable_cache: bool = True):
        """
        Initialize the calendar manager.

        Args:
            start_date: Starting date for the calendar
            database_path: Path to SQLite database
            enable_cache: Whether to enable event caching
        """
        # Convert datetime to date if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()

        self.start_date = start_date
        self.current_date = start_date

        # Event management system
        self.event_manager = EventManager(database_path, enable_cache)

        # Logger for debugging
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"CalendarManager initialized with start date: {start_date}")

    def get_current_date(self) -> date:
        """
        Get the current calendar date.

        Returns:
            date: The current date in the calendar
        """
        return self.current_date

    def advance_date(self, days: int = 1) -> date:
        """
        Advance the calendar by a specified number of days.

        Args:
            days: Number of days to advance (default: 1)

        Returns:
            date: The new current date after advancing
        """
        if days < 0:
            self.logger.warning(f"Cannot advance calendar by negative days: {days}")
            return self.current_date

        self.current_date += timedelta(days=days)
        self.logger.debug(f"Advanced calendar to {self.current_date}")
        return self.current_date

    def set_date(self, new_date: Union[date, datetime]) -> date:
        """
        Set the calendar to a specific date.

        Args:
            new_date: Date to set the calendar to

        Returns:
            date: The new current date
        """
        self.current_date = self._convert_to_date(new_date)
        self.logger.debug(f"Set calendar date to {self.current_date}")
        return self.current_date

    def schedule_event(self, event: Event) -> bool:
        """
        Add an event to the calendar.

        Args:
            event: Event to schedule

        Returns:
            bool: True if event was scheduled successfully, False otherwise
        """
        success, error_message = self.event_manager.save_event(event)
        if not success:
            self.logger.warning(f"Failed to schedule event {event.name}: {error_message}")
        return success

    def get_events_for_date(self, target_date: Union[date, datetime]) -> List[Event]:
        """
        Get all events scheduled for a specific date.

        Args:
            target_date: Date to get events for

        Returns:
            List[Event]: List of events scheduled for that date
        """
        target_date = self._convert_to_date(target_date)
        return self.event_manager.get_events_by_date(target_date)

    def get_events_between(self, start_date: Union[date, datetime],
                          end_date: Union[date, datetime]) -> List[Event]:
        """
        Get all events between two dates (inclusive).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List[Event]: List of events in the date range
        """
        start_date = self._convert_to_date(start_date)
        end_date = self._convert_to_date(end_date)
        return self.event_manager.get_events_between(start_date, end_date)

    def remove_event(self, event_id: str) -> bool:
        """
        Remove an event from the calendar.

        Args:
            event_id: Unique ID of the event to remove

        Returns:
            bool: True if event was removed, False if not found
        """
        success, error_message = self.event_manager.delete_event(event_id)
        if not success:
            self.logger.warning(f"Failed to remove event {event_id}: {error_message}")
        return success

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get a specific event by its ID.

        Args:
            event_id: Unique ID of the event

        Returns:
            Optional[Event]: The event if found, None otherwise
        """
        return self.event_manager.get_event_by_id(event_id)

    def has_events_on_date(self, target_date: Union[date, datetime]) -> bool:
        """
        Check if there are any events on a specific date.

        Args:
            target_date: Date to check

        Returns:
            bool: True if there are events on that date, False otherwise
        """
        target_date = self._convert_to_date(target_date)
        events = self.event_manager.get_events_by_date(target_date)
        return len(events) > 0

    def get_next_event_date(self, from_date: Optional[Union[date, datetime]] = None) -> Optional[date]:
        """
        Get the next date that has events scheduled.

        Args:
            from_date: Date to start searching from (default: current date)

        Returns:
            Optional[date]: Next date with events, or None if no future events
        """
        if from_date is None:
            from_date = self.current_date
        else:
            from_date = self._convert_to_date(from_date)

        dates_with_events = self.event_manager.get_dates_with_events()
        future_dates = [d for d in dates_with_events if d > from_date]

        return min(future_dates) if future_dates else None

    def get_previous_event_date(self, from_date: Optional[Union[date, datetime]] = None) -> Optional[date]:
        """
        Get the previous date that had events scheduled.

        Args:
            from_date: Date to start searching from (default: current date)

        Returns:
            Optional[date]: Previous date with events, or None if no past events
        """
        if from_date is None:
            from_date = self.current_date
        else:
            from_date = self._convert_to_date(from_date)

        dates_with_events = self.event_manager.get_dates_with_events()
        past_dates = [d for d in dates_with_events if d < from_date]

        return max(past_dates) if past_dates else None

    def get_calendar_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the calendar state.

        Returns:
            Dict[str, Any]: Summary including current date, total events, etc.
        """
        manager_stats = self.event_manager.get_manager_stats()
        dates_with_events = self.event_manager.get_dates_with_events()

        return {
            "start_date": self.start_date.isoformat(),
            "current_date": self.current_date.isoformat(),
            "total_events": manager_stats.total_events,
            "cached_events": manager_stats.cached_events,
            "dates_with_events": manager_stats.dates_with_events,
            "cache_hit_rate": manager_stats.cache_hit_rate,
            "earliest_event_date": dates_with_events[0].isoformat() if dates_with_events else None,
            "latest_event_date": dates_with_events[-1].isoformat() if dates_with_events else None
        }

    def clear_calendar(self) -> int:
        """
        Remove all events from the calendar.

        Returns:
            int: Number of events that were removed
        """
        cleared_count = self.event_manager.clear_all_events()
        self.logger.info(f"Cleared calendar: {cleared_count} events removed")
        return cleared_count

    def reset_to_date(self, reset_date: Union[date, datetime]) -> None:
        """
        Reset the calendar to a specific date and clear all events.

        Args:
            reset_date: Date to reset the calendar to
        """
        self.current_date = self._convert_to_date(reset_date)
        self.event_manager.clear_all_events()
        self.logger.info(f"Calendar reset to {self.current_date} with all events cleared")

    def _convert_to_date(self, date_input: Union[date, datetime]) -> date:
        """
        Convert datetime to date if needed.

        Args:
            date_input: Date or datetime to convert

        Returns:
            date: Converted date
        """
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input

    def __str__(self) -> str:
        """String representation of the calendar manager."""
        total_events = self.event_manager.get_events_count()
        return f"CalendarManager(current_date={self.current_date}, events={total_events})"

    def __repr__(self) -> str:
        """Detailed representation of the calendar manager."""
        total_events = self.event_manager.get_events_count()
        return (f"CalendarManager(start_date={self.start_date}, "
                f"current_date={self.current_date}, "
                f"events={total_events})")