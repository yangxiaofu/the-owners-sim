"""
Event Manager

Business logic layer for calendar event management.
Handles validation, caching, and coordination between CalendarManager and database.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .event import Event
from .calendar_database_api import CalendarDatabaseAPI


@dataclass
class EventManagerStats:
    """Statistics about the event manager state."""
    total_events: int
    cached_events: int
    dates_with_events: int
    cache_hit_rate: float


class EventManager:
    """
    Business logic layer for calendar event management.

    Handles event validation, caching, error handling, and coordinates
    between the CalendarManager and the database layer.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db",
                 enable_cache: bool = True, cache_size_limit: int = 1000):
        """
        Initialize the event manager.

        Args:
            database_path: Path to SQLite database
            enable_cache: Whether to enable in-memory caching
            cache_size_limit: Maximum number of events to cache
        """
        self.database_api = CalendarDatabaseAPI(database_path)
        self.logger = logging.getLogger("EventManager")

        # Caching configuration
        self.enable_cache = enable_cache
        self.cache_size_limit = cache_size_limit

        # Cache storage: date -> list of events
        self._date_cache: Dict[date, List[Event]] = {}
        self._id_cache: Dict[str, Event] = {}

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

        self.logger.info(f"EventManager initialized (cache: {enable_cache}, limit: {cache_size_limit})")

    def save_event(self, event: Event) -> Tuple[bool, Optional[str]]:
        """
        Validate and save an event.

        Args:
            event: Event to save

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Validate the event
            is_valid, error_message = self._validate_event(event)
            if not is_valid:
                self.logger.warning(f"Event validation failed: {error_message}")
                return False, error_message

            # Check for duplicates
            if self.database_api.event_exists(event.event_id):
                error_msg = f"Event with ID {event.event_id} already exists"
                self.logger.warning(error_msg)
                return False, error_msg

            # Save to database
            success = self.database_api.insert_event(event)
            if not success:
                error_msg = "Failed to save event to database"
                self.logger.error(error_msg)
                return False, error_msg

            # Update cache
            if self.enable_cache:
                self._add_to_cache(event)

            self.logger.info(f"Successfully saved event: {event.name} on {event.event_date}")
            return True, None

        except Exception as e:
            error_msg = f"Unexpected error saving event: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def get_events_by_date(self, target_date: date) -> List[Event]:
        """
        Get all events for a specific date.

        Args:
            target_date: Date to get events for

        Returns:
            List[Event]: List of events on that date
        """
        try:
            # Check cache first
            if self.enable_cache and target_date in self._date_cache:
                self._cache_hits += 1
                self.logger.debug(f"Cache hit for date {target_date}")
                return self._date_cache[target_date].copy()

            # Cache miss - fetch from database
            self._cache_misses += 1
            events = self.database_api.fetch_events_by_date(target_date)

            # Update cache
            if self.enable_cache:
                self._update_date_cache(target_date, events)

            self.logger.debug(f"Retrieved {len(events)} events for date {target_date}")
            return events

        except Exception as e:
            self.logger.error(f"Error retrieving events for date {target_date}: {e}")
            return []

    def get_events_between(self, start_date: date, end_date: date) -> List[Event]:
        """
        Get all events between two dates (inclusive).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List[Event]: List of events in the date range
        """
        try:
            # Validate date range
            if start_date > end_date:
                self.logger.warning(f"Invalid date range: {start_date} > {end_date}")
                return []

            # For small ranges, try to use cache
            if self.enable_cache and (end_date - start_date).days <= 7:
                cached_events = self._get_cached_events_in_range(start_date, end_date)
                if cached_events is not None:
                    self._cache_hits += 1
                    return cached_events

            # Cache miss or large range - fetch from database
            self._cache_misses += 1
            events = self.database_api.fetch_events_between(start_date, end_date)

            # Update cache for small ranges
            if self.enable_cache and (end_date - start_date).days <= 7:
                self._cache_events_by_date(events)

            self.logger.debug(f"Retrieved {len(events)} events between {start_date} and {end_date}")
            return events

        except Exception as e:
            self.logger.error(f"Error retrieving events between {start_date} and {end_date}: {e}")
            return []

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get a specific event by its ID.

        Args:
            event_id: Unique ID of the event

        Returns:
            Optional[Event]: The event if found, None otherwise
        """
        try:
            # Check cache first
            if self.enable_cache and event_id in self._id_cache:
                self._cache_hits += 1
                self.logger.debug(f"Cache hit for event ID {event_id}")
                return self._id_cache[event_id]

            # Cache miss - fetch from database
            self._cache_misses += 1
            event = self.database_api.fetch_event_by_id(event_id)

            # Update cache
            if self.enable_cache and event:
                self._add_to_cache(event)

            if event:
                self.logger.debug(f"Retrieved event {event_id}: {event.name}")
            else:
                self.logger.debug(f"Event {event_id} not found")

            return event

        except Exception as e:
            self.logger.error(f"Error retrieving event {event_id}: {e}")
            return None

    def delete_event(self, event_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete an event.

        Args:
            event_id: Unique ID of the event to delete

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Check if event exists
            event = self.get_event_by_id(event_id)
            if not event:
                error_msg = f"Event {event_id} not found"
                self.logger.warning(error_msg)
                return False, error_msg

            # Delete from database
            success = self.database_api.delete_event(event_id)
            if not success:
                error_msg = "Failed to delete event from database"
                self.logger.error(error_msg)
                return False, error_msg

            # Remove from cache
            if self.enable_cache:
                self._remove_from_cache(event)

            self.logger.info(f"Successfully deleted event: {event.name}")
            return True, None

        except Exception as e:
            error_msg = f"Unexpected error deleting event {event_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def update_event(self, event: Event) -> Tuple[bool, Optional[str]]:
        """
        Update an existing event.

        Args:
            event: Event with updated data

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Validate the event
            is_valid, error_message = self._validate_event(event)
            if not is_valid:
                self.logger.warning(f"Event validation failed: {error_message}")
                return False, error_message

            # Get original event for cache cleanup
            original_event = self.get_event_by_id(event.event_id)
            if not original_event:
                error_msg = f"Event {event.event_id} not found for update"
                self.logger.warning(error_msg)
                return False, error_msg

            # Update in database
            success = self.database_api.update_event(event)
            if not success:
                error_msg = "Failed to update event in database"
                self.logger.error(error_msg)
                return False, error_msg

            # Update cache
            if self.enable_cache:
                # Remove old version from cache
                self._remove_from_cache(original_event)
                # Add updated version to cache
                self._add_to_cache(event)

            self.logger.info(f"Successfully updated event: {event.name}")
            return True, None

        except Exception as e:
            error_msg = f"Unexpected error updating event {event.event_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def event_exists(self, event_id: str) -> bool:
        """
        Check if an event exists.

        Args:
            event_id: Unique ID of the event

        Returns:
            bool: True if event exists, False otherwise
        """
        # Check cache first
        if self.enable_cache and event_id in self._id_cache:
            return True

        # Check database
        return self.database_api.event_exists(event_id)

    def get_events_count(self) -> int:
        """
        Get the total number of events.

        Returns:
            int: Total number of events
        """
        return self.database_api.get_events_count()

    def get_dates_with_events(self) -> List[date]:
        """
        Get all dates that have at least one event.

        Returns:
            List[date]: Sorted list of dates with events
        """
        return self.database_api.get_dates_with_events()

    def clear_all_events(self) -> int:
        """
        Delete all events.

        Returns:
            int: Number of events deleted
        """
        try:
            # Clear database
            deleted_count = self.database_api.clear_all_events()

            # Clear cache
            if self.enable_cache:
                self._clear_cache()

            self.logger.info(f"Cleared all events: {deleted_count} events deleted")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error clearing all events: {e}")
            return 0

    def get_manager_stats(self) -> EventManagerStats:
        """
        Get statistics about the event manager.

        Returns:
            EventManagerStats: Current statistics
        """
        total_events = self.get_events_count()
        cached_events = len(self._id_cache) if self.enable_cache else 0
        dates_with_events = len(self.get_dates_with_events())

        # Calculate cache hit rate
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = (self._cache_hits / total_requests) if total_requests > 0 else 0.0

        return EventManagerStats(
            total_events=total_events,
            cached_events=cached_events,
            dates_with_events=dates_with_events,
            cache_hit_rate=cache_hit_rate
        )

    def clear_cache(self) -> int:
        """
        Clear the in-memory cache.

        Returns:
            int: Number of cached events cleared
        """
        if not self.enable_cache:
            return 0

        cleared_count = len(self._id_cache)
        self._clear_cache()
        self.logger.info(f"Cleared cache: {cleared_count} events removed")
        return cleared_count

    def _validate_event(self, event: Event) -> Tuple[bool, Optional[str]]:
        """
        Validate an event before saving/updating.

        Args:
            event: Event to validate

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check required fields
        if not event.name or not event.name.strip():
            return False, "Event name is required"

        if not event.event_id or not event.event_id.strip():
            return False, "Event ID is required"

        if not event.event_date:
            return False, "Event date is required"

        # Validate date is not too far in past or future
        today = date.today()
        if event.event_date < today - timedelta(days=365 * 5):  # 5 years ago
            return False, "Event date cannot be more than 5 years in the past"

        if event.event_date > today + timedelta(days=365 * 10):  # 10 years ahead
            return False, "Event date cannot be more than 10 years in the future"

        # Validate metadata if present
        if event.metadata:
            try:
                # Try to serialize metadata to ensure it's JSON-serializable
                import json
                json.dumps(event.metadata)
            except (TypeError, ValueError):
                return False, "Event metadata must be JSON-serializable"

        return True, None

    def _add_to_cache(self, event: Event) -> None:
        """Add an event to the cache."""
        if not self.enable_cache:
            return

        # Check cache size limit
        if len(self._id_cache) >= self.cache_size_limit:
            self._evict_cache_entries()

        # Add to ID cache
        self._id_cache[event.event_id] = event

        # Add to date cache
        event_date = event.event_date
        if event_date not in self._date_cache:
            self._date_cache[event_date] = []
        self._date_cache[event_date].append(event)

    def _remove_from_cache(self, event: Event) -> None:
        """Remove an event from the cache."""
        if not self.enable_cache:
            return

        # Remove from ID cache
        self._id_cache.pop(event.event_id, None)

        # Remove from date cache
        event_date = event.event_date
        if event_date in self._date_cache:
            self._date_cache[event_date] = [
                e for e in self._date_cache[event_date] if e.event_id != event.event_id
            ]
            # Remove empty date entries
            if not self._date_cache[event_date]:
                del self._date_cache[event_date]

    def _update_date_cache(self, target_date: date, events: List[Event]) -> None:
        """Update the date cache with events for a specific date."""
        if not self.enable_cache:
            return

        self._date_cache[target_date] = events.copy()

        # Also update ID cache
        for event in events:
            if len(self._id_cache) < self.cache_size_limit:
                self._id_cache[event.event_id] = event

    def _cache_events_by_date(self, events: List[Event]) -> None:
        """Cache events organized by date."""
        if not self.enable_cache:
            return

        # Group events by date
        events_by_date: Dict[date, List[Event]] = {}
        for event in events:
            if event.event_date not in events_by_date:
                events_by_date[event.event_date] = []
            events_by_date[event.event_date].append(event)

        # Update cache
        for event_date, date_events in events_by_date.items():
            self._update_date_cache(event_date, date_events)

    def _get_cached_events_in_range(self, start_date: date, end_date: date) -> Optional[List[Event]]:
        """Try to get events in a date range from cache."""
        if not self.enable_cache:
            return None

        cached_events = []
        current_date = start_date

        while current_date <= end_date:
            if current_date not in self._date_cache:
                # Cache miss for this date
                return None

            cached_events.extend(self._date_cache[current_date])
            current_date += timedelta(days=1)

        return cached_events

    def _evict_cache_entries(self) -> None:
        """Evict entries from cache when size limit is reached."""
        # Simple LRU-like eviction: remove 25% of entries
        evict_count = max(1, len(self._id_cache) // 4)

        # Remove oldest entries (arbitrary choice for simplicity)
        events_to_remove = list(self._id_cache.values())[:evict_count]

        for event in events_to_remove:
            self._remove_from_cache(event)

    def _clear_cache(self) -> None:
        """Clear all cache data."""
        self._date_cache.clear()
        self._id_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def __str__(self) -> str:
        """String representation of the event manager."""
        stats = self.get_manager_stats()
        return f"EventManager({stats.total_events} events, cache: {self.enable_cache})"

    def __repr__(self) -> str:
        """Detailed representation of the event manager."""
        return (f"EventManager(total_events={self.get_events_count()}, "
                f"cache_enabled={self.enable_cache}, "
                f"cache_limit={self.cache_size_limit})")