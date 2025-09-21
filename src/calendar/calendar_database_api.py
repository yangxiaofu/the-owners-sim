"""
Calendar Database API

Pure database operations for calendar events.
Handles SQL queries, data serialization, and database error handling.
"""

import json
import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
import sqlite3

from .event import Event
from database.connection import DatabaseConnection


class CalendarDatabaseAPI:
    """
    Database API for calendar event operations.

    Handles all SQL operations for calendar events, following the established
    DatabaseAPI pattern. Provides clean separation between business logic
    and database operations.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize calendar database API.

        Args:
            database_path: Path to SQLite database
        """
        self.db_connection = DatabaseConnection(database_path)
        self.logger = logging.getLogger("CalendarDatabaseAPI")

        # Initialize schema if needed
        self._ensure_schema_exists()

    def _ensure_schema_exists(self) -> None:
        """Ensure calendar events table exists in database."""
        try:
            create_table_sql = '''
                CREATE TABLE IF NOT EXISTS calendar_events (
                    event_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''

            # Create indexes for performance
            create_date_index = '''
                CREATE INDEX IF NOT EXISTS idx_calendar_events_date
                ON calendar_events(event_date)
            '''

            create_date_range_index = '''
                CREATE INDEX IF NOT EXISTS idx_calendar_events_date_range
                ON calendar_events(event_date, event_id)
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                cursor.execute(create_date_index)
                cursor.execute(create_date_range_index)
                conn.commit()

            self.logger.info("Calendar events schema initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize calendar schema: {e}")
            raise

    def insert_event(self, event: Event) -> bool:
        """
        Insert a new event into the database.

        Args:
            event: Event object to insert

        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            insert_sql = '''
                INSERT INTO calendar_events (event_id, name, event_date, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            '''

            metadata_json = json.dumps(event.metadata) if event.metadata else '{}'
            current_time = datetime.now()

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (
                    event.event_id,
                    event.name,
                    event.event_date.isoformat(),
                    metadata_json,
                    current_time.isoformat(),
                    current_time.isoformat()
                ))
                conn.commit()

            self.logger.debug(f"Inserted event {event.event_id}: {event.name}")
            return True

        except sqlite3.IntegrityError as e:
            self.logger.warning(f"Event {event.event_id} already exists: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to insert event {event.event_id}: {e}")
            return False

    def fetch_events_by_date(self, target_date: date) -> List[Event]:
        """
        Fetch all events for a specific date.

        Args:
            target_date: Date to fetch events for

        Returns:
            List[Event]: List of events on that date
        """
        try:
            select_sql = '''
                SELECT event_id, name, event_date, metadata_json
                FROM calendar_events
                WHERE event_date = ?
                ORDER BY name
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (target_date.isoformat(),))
                rows = cursor.fetchall()

            events = []
            for row in rows:
                event = self._row_to_event(row)
                if event:
                    events.append(event)

            self.logger.debug(f"Fetched {len(events)} events for date {target_date}")
            return events

        except Exception as e:
            self.logger.error(f"Failed to fetch events for date {target_date}: {e}")
            return []

    def fetch_events_between(self, start_date: date, end_date: date) -> List[Event]:
        """
        Fetch all events between two dates (inclusive).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List[Event]: List of events in the date range
        """
        try:
            select_sql = '''
                SELECT event_id, name, event_date, metadata_json
                FROM calendar_events
                WHERE event_date >= ? AND event_date <= ?
                ORDER BY event_date, name
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (start_date.isoformat(), end_date.isoformat()))
                rows = cursor.fetchall()

            events = []
            for row in rows:
                event = self._row_to_event(row)
                if event:
                    events.append(event)

            self.logger.debug(f"Fetched {len(events)} events between {start_date} and {end_date}")
            return events

        except Exception as e:
            self.logger.error(f"Failed to fetch events between {start_date} and {end_date}: {e}")
            return []

    def fetch_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Fetch a specific event by its ID.

        Args:
            event_id: Unique ID of the event

        Returns:
            Optional[Event]: The event if found, None otherwise
        """
        try:
            select_sql = '''
                SELECT event_id, name, event_date, metadata_json
                FROM calendar_events
                WHERE event_id = ?
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (event_id,))
                row = cursor.fetchone()

            if row:
                event = self._row_to_event(row)
                self.logger.debug(f"Fetched event {event_id}")
                return event
            else:
                self.logger.debug(f"Event {event_id} not found")
                return None

        except Exception as e:
            self.logger.error(f"Failed to fetch event {event_id}: {e}")
            return None

    def update_event(self, event: Event) -> bool:
        """
        Update an existing event in the database.

        Args:
            event: Event object with updated data

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            update_sql = '''
                UPDATE calendar_events
                SET name = ?, event_date = ?, metadata_json = ?, updated_at = ?
                WHERE event_id = ?
            '''

            metadata_json = json.dumps(event.metadata) if event.metadata else '{}'
            current_time = datetime.now()

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(update_sql, (
                    event.name,
                    event.event_date.isoformat(),
                    metadata_json,
                    current_time.isoformat(),
                    event.event_id
                ))

                rows_affected = cursor.rowcount
                conn.commit()

            if rows_affected > 0:
                self.logger.debug(f"Updated event {event.event_id}")
                return True
            else:
                self.logger.warning(f"Event {event.event_id} not found for update")
                return False

        except Exception as e:
            self.logger.error(f"Failed to update event {event.event_id}: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event from the database.

        Args:
            event_id: Unique ID of the event to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            delete_sql = '''
                DELETE FROM calendar_events
                WHERE event_id = ?
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(delete_sql, (event_id,))

                rows_affected = cursor.rowcount
                conn.commit()

            if rows_affected > 0:
                self.logger.debug(f"Deleted event {event_id}")
                return True
            else:
                self.logger.warning(f"Event {event_id} not found for deletion")
                return False

        except Exception as e:
            self.logger.error(f"Failed to delete event {event_id}: {e}")
            return False

    def event_exists(self, event_id: str) -> bool:
        """
        Check if an event exists in the database.

        Args:
            event_id: Unique ID of the event

        Returns:
            bool: True if event exists, False otherwise
        """
        try:
            check_sql = '''
                SELECT 1 FROM calendar_events
                WHERE event_id = ?
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(check_sql, (event_id,))
                result = cursor.fetchone()

            exists = result is not None
            self.logger.debug(f"Event {event_id} exists: {exists}")
            return exists

        except Exception as e:
            self.logger.error(f"Failed to check if event {event_id} exists: {e}")
            return False

    def get_events_count(self) -> int:
        """
        Get the total number of events in the database.

        Returns:
            int: Total number of events
        """
        try:
            count_sql = 'SELECT COUNT(*) FROM calendar_events'

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(count_sql)
                result = cursor.fetchone()

            count = result[0] if result else 0
            self.logger.debug(f"Total events count: {count}")
            return count

        except Exception as e:
            self.logger.error(f"Failed to get events count: {e}")
            return 0

    def get_dates_with_events(self) -> List[date]:
        """
        Get all dates that have at least one event.

        Returns:
            List[date]: Sorted list of dates with events
        """
        try:
            dates_sql = '''
                SELECT DISTINCT event_date
                FROM calendar_events
                ORDER BY event_date
            '''

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(dates_sql)
                rows = cursor.fetchall()

            dates = []
            for row in rows:
                try:
                    event_date = datetime.fromisoformat(row[0]).date()
                    dates.append(event_date)
                except ValueError as e:
                    self.logger.warning(f"Invalid date format in database: {row[0]}: {e}")

            self.logger.debug(f"Found {len(dates)} dates with events")
            return dates

        except Exception as e:
            self.logger.error(f"Failed to get dates with events: {e}")
            return []

    def clear_all_events(self) -> int:
        """
        Delete all events from the database.

        Returns:
            int: Number of events deleted
        """
        try:
            delete_all_sql = 'DELETE FROM calendar_events'

            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(delete_all_sql)

                rows_affected = cursor.rowcount
                conn.commit()

            self.logger.info(f"Cleared {rows_affected} events from database")
            return rows_affected

        except Exception as e:
            self.logger.error(f"Failed to clear all events: {e}")
            return 0

    def _row_to_event(self, row: Tuple) -> Optional[Event]:
        """
        Convert database row to Event object.

        Args:
            row: Database row tuple (event_id, name, event_date, metadata_json)

        Returns:
            Optional[Event]: Event object or None if conversion fails
        """
        try:
            event_id, name, event_date_str, metadata_json = row

            # Parse date
            event_date = datetime.fromisoformat(event_date_str).date()

            # Parse metadata
            metadata = {}
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON metadata for event {event_id}: {e}")
                    metadata = {}

            # Create Event object
            return Event(
                name=name,
                event_date=event_date,
                event_id=event_id,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Failed to convert database row to Event: {e}")
            return None

    def __str__(self) -> str:
        """String representation of the calendar database API."""
        total_events = self.get_events_count()
        return f"CalendarDatabaseAPI({total_events} events in database)"

    def __repr__(self) -> str:
        """Detailed representation of the calendar database API."""
        return f"CalendarDatabaseAPI(db_path='{self.db_connection.db_path}')"