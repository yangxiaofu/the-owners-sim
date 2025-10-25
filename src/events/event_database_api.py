"""
Event Database API

Python implementation of the Event Database API specification.
Provides generic persistence for all event types using SQLite.

Specification Reference: docs/specifications/event_manager_api.md
"""

from typing import List, Optional, Dict, Any
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import logging
from events.base_event import BaseEvent


class EventDatabaseAPI:
    """
    Generic persistence layer for storing and retrieving game events.

    This component provides database operations without knowledge of event types
    or game logic. It implements the Event Database API specification for Python.

    Key Features:
    - Store events of any type in generic table
    - Batch insert with transactions for performance
    - Query by event_id or game_id
    - Automatic schema initialization

    Performance:
    - insertEvent: O(log n) - single write with index update
    - insertEvents: O(m log n) - batch with transaction (10-50x faster)
    - getEventById: O(1) - primary key lookup
    - getEventsByGameId: O(k) - index scan where k = events for that game
    """

    def __init__(self, database_path: str):
        """
        Initialize Event Database API.

        Args:
            database_path: Path to SQLite database file
                          Use ':memory:' for in-memory database
        """
        self.db_path = database_path
        self.logger = logging.getLogger(__name__)

        # Ensure database directory exists
        if database_path != ':memory:':
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._initialize_schema()

        self.logger.info(f"EventDatabaseAPI initialized at {database_path}")

    def _initialize_schema(self):
        """
        Create events table and indexes if they don't exist.

        Schema matches Event Database API specification:
        - event_id: Primary key (VARCHAR)
        - event_type: Event type label (VARCHAR)
        - timestamp: Unix timestamp in milliseconds (BIGINT)
        - game_id: Game identifier for filtering (VARCHAR)
        - dynasty_id: Dynasty identifier for isolation (VARCHAR, NOT NULL)
        - data: JSON event data (TEXT)
        """
        conn = sqlite3.connect(self.db_path)

        try:
            # Create events table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    dynasty_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_game_id ON events(game_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)')

            # Create new composite indexes for dynasty-filtered queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_type ON events(dynasty_id, event_type)')

            conn.commit()
            self.logger.debug("Events table and indexes created successfully")

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error initializing schema: {e}")
            raise

        finally:
            conn.close()

    def insert_event(self, event: BaseEvent) -> BaseEvent:
        """
        Insert a single event into the database.

        Args:
            event: Event object implementing BaseEvent interface

        Returns:
            The original event object on success

        Raises:
            Exception: If database operation fails
        """
        print(f"[DYNASTY_TRACE] EventDatabaseAPI.insert_event(): event_id={event.event_id[:8]}, dynasty_id={event.dynasty_id}")
        try:
            # Convert event to database format
            event_data = event.to_database_format()

            # Validate required fields
            self._validate_event_data(event_data)

            # PLAYOFF EVENT LOGGING: Track when playoff events are saved
            game_id = event_data.get('game_id', '')
            if 'playoff_' in game_id:
                print(f"[PLAYOFF_PERSISTENCE] Saving playoff event to database:")
                print(f"  event_id: {event_data['event_id']}")
                print(f"  game_id: {game_id}")
                print(f"  dynasty_id: {event_data['dynasty_id']}")
                print(f"  event_type: {event_data['event_type']}")
                print(f"  database: {self.db_path}")

            # Insert into database
            conn = sqlite3.connect(self.db_path)

            conn.execute('''
                INSERT INTO events (event_id, event_type, timestamp, game_id, dynasty_id, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event_data['event_id'],
                event_data['event_type'],
                int(event_data['timestamp'].timestamp() * 1000),  # Convert to milliseconds
                event_data['game_id'],
                event_data['dynasty_id'],
                json.dumps(event_data['data'])
            ))

            conn.commit()
            conn.close()

            # Verify playoff event was saved
            if 'playoff_' in game_id:
                # Immediately query back to confirm it's in the database
                verify_conn = sqlite3.connect(self.db_path)
                verify_cursor = verify_conn.cursor()
                verify_cursor.execute(
                    'SELECT COUNT(*) FROM events WHERE game_id = ? AND dynasty_id = ?',
                    (game_id, event_data['dynasty_id'])
                )
                count = verify_cursor.fetchone()[0]
                verify_conn.close()
                print(f"[PLAYOFF_PERSISTENCE] ✅ Verified: {count} event(s) with game_id='{game_id}' in database")

            self.logger.debug(f"Inserted event: {event_data['event_id']} ({event_data['event_type']})")

            return event

        except Exception as e:
            self.logger.error(f"Error inserting event {event.event_id}: {e}")
            raise

    def insert_events(self, events: List[BaseEvent]) -> List[BaseEvent]:
        """
        Insert multiple events in a single transaction.

        All inserts succeed or all fail (atomic operation).
        Significantly faster than multiple insert_event() calls.

        Args:
            events: List of event objects implementing BaseEvent

        Returns:
            List of inserted events

        Raises:
            Exception: If database operation fails (rolls back transaction)
        """
        # [PRESEASON_DEBUG Point 6c] Database Commit
        print(f"\n[PRESEASON_DEBUG Point 6c] EventDatabaseAPI.insert_events() called...")
        print(f"  Events count: {len(events)}")
        print(f"  Database path: {self.db_path}")

        if not events:
            print(f"[PRESEASON_DEBUG Point 6c] ⚠️ No events to insert")
            self.logger.debug("No events to insert")
            return []

        conn = sqlite3.connect(self.db_path)

        try:
            # Start transaction
            print(f"[PRESEASON_DEBUG Point 6c] Starting transaction...")
            conn.execute('BEGIN TRANSACTION')

            # Insert all events
            inserted_count = 0
            for event in events:
                event_data = event.to_database_format()
                self._validate_event_data(event_data)

                conn.execute('''
                    INSERT INTO events (event_id, event_type, timestamp, game_id, dynasty_id, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_data['event_id'],
                    event_data['event_type'],
                    int(event_data['timestamp'].timestamp() * 1000),
                    event_data['game_id'],
                    event_data['dynasty_id'],
                    json.dumps(event_data['data'])
                ))
                inserted_count += 1

            # Commit transaction
            print(f"[PRESEASON_DEBUG Point 6c] Committing transaction...")
            print(f"  Inserted {inserted_count} events")

            conn.execute('COMMIT')
            conn.close()

            print(f"[PRESEASON_DEBUG Point 6c] ✅ COMMIT successful!")
            print(f"  {len(events)} events persisted to database")

            # Verification query
            verify_conn = sqlite3.connect(self.db_path)
            verify_cursor = verify_conn.cursor()

            # Count preseason events for this dynasty
            if len(events) > 0 and 'preseason' in events[0].get_game_id():
                dynasty_id = events[0].dynasty_id
                verify_cursor.execute(
                    "SELECT COUNT(*) FROM events WHERE game_id LIKE 'preseason_%' AND dynasty_id = ?",
                    (dynasty_id,)
                )
                preseason_count = verify_cursor.fetchone()[0]
                print(f"[PRESEASON_DEBUG Point 6c] Verification query:")
                print(f"  Total preseason events in DB for dynasty '{dynasty_id}': {preseason_count}")

            verify_conn.close()

            self.logger.info(f"Batch inserted {len(events)} events")

            return events

        except Exception as e:
            print(f"[PRESEASON_DEBUG Point 6c] ❌ Database insert FAILED!")
            print(f"  Error: {e}")
            print(f"  Rolling back transaction...")

            # Rollback on error
            conn.execute('ROLLBACK')
            conn.close()
            self.logger.error(f"Error in batch insert: {e}")
            raise

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific event by its ID.

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found
            Dictionary format:
            {
                "event_id": str,
                "event_type": str,
                "timestamp": datetime,
                "game_id": str,
                "data": dict
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT * FROM events WHERE event_id = ?',
                (event_id,)
            )

            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)

            return None

        finally:
            conn.close()

    def get_events_by_game_id(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all events for a specific game, ordered chronologically.

        This is the key method for polymorphic event retrieval - it returns
        ALL event types (GAME, MEDIA, TRADE, etc.) for a given game_id.

        Args:
            game_id: Identifier of the game/context

        Returns:
            List of event dictionaries, ordered by timestamp (oldest first)
            Empty list if no events found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT * FROM events WHERE game_id = ? ORDER BY timestamp ASC',
                (game_id,)
            )

            rows = cursor.fetchall()

            events = [self._row_to_dict(row) for row in rows]

            self.logger.debug(f"Retrieved {len(events)} events for game_id: {game_id}")

            return events

        finally:
            conn.close()

    def get_events_by_game_id_and_dynasty(
        self,
        game_id: str,
        dynasty_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events for specific game AND dynasty.

        This is the dynasty-aware version of get_events_by_game_id().
        Use this for duplicate detection in dynasty-isolated scheduling.

        This solves the cross-dynasty contamination issue where playoff games
        from one dynasty would prevent scheduling in another dynasty.

        Args:
            game_id: Game identifier
            dynasty_id: Dynasty identifier

        Returns:
            List of event dictionaries matching both game_id and dynasty_id,
            ordered by timestamp (oldest first)
            Empty list if no matching events found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT * FROM events WHERE game_id = ? AND dynasty_id = ? ORDER BY timestamp ASC',
                (game_id, dynasty_id)
            )

            rows = cursor.fetchall()
            events = [self._row_to_dict(row) for row in rows]

            self.logger.debug(
                f"Retrieved {len(events)} events for game_id: {game_id}, dynasty_id: {dynasty_id}"
            )

            return events

        finally:
            conn.close()

    def delete_playoff_events_by_dynasty(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Delete all playoff events for a specific dynasty and season.

        Useful for cleanup before rescheduling playoffs or resetting dynasty state.
        This allows users to reschedule playoffs without cross-dynasty interference.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of events deleted
        """
        # CRITICAL LOGGING: Track when playoff events are being deleted
        import traceback
        print(f"\n[PLAYOFF_DELETION] ⚠️  delete_playoff_events_by_dynasty() CALLED")
        print(f"[PLAYOFF_DELETION]   dynasty_id: {dynasty_id}")
        print(f"[PLAYOFF_DELETION]   season: {season}")
        print(f"[PLAYOFF_DELETION]   database: {self.db_path}")
        print(f"[PLAYOFF_DELETION]   Call stack:")
        # Print stack trace to see what triggered the deletion
        for line in traceback.format_stack()[:-1]:  # Exclude this frame
            print(f"     {line.strip()}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Count before deleting
            cursor.execute('''
                SELECT COUNT(*) FROM events
                WHERE dynasty_id = ?
                AND game_id LIKE ?
            ''', (dynasty_id, f'playoff_{season}_%'))
            count_before = cursor.fetchone()[0]
            print(f"[PLAYOFF_DELETION]   Events to delete: {count_before}")

            # Delete all playoff games for this dynasty/season
            cursor.execute('''
                DELETE FROM events
                WHERE dynasty_id = ?
                AND game_id LIKE ?
            ''', (dynasty_id, f'playoff_{season}_%'))

            deleted_count = cursor.rowcount
            conn.commit()

            print(f"[PLAYOFF_DELETION]   ✅ Deleted {deleted_count} playoff events")

            self.logger.info(
                f"Deleted {deleted_count} playoff events for dynasty: {dynasty_id}, season: {season}"
            )

            return deleted_count

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error deleting playoff events: {e}")
            raise

        finally:
            conn.close()

    def get_events_by_type(self, event_type: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all events of a specific type.

        Additional query method not in original spec, useful for analytics.

        Args:
            event_type: Type of events to retrieve (e.g., "GAME", "MEDIA")
            limit: Optional limit on number of results

        Returns:
            List of event dictionaries matching the type
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if limit:
                cursor.execute(
                    'SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?',
                    (event_type, limit)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC',
                    (event_type,)
                )

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        finally:
            conn.close()

    def get_events_by_dynasty(
        self,
        dynasty_id: str,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all events for a specific dynasty.

        Primary query method for dynasty-isolated event retrieval.
        Uses indexed equality for fast performance.

        Args:
            dynasty_id: Dynasty identifier
            event_type: Optional filter by event type
            limit: Optional limit on results

        Returns:
            List of event dictionaries, ordered by timestamp DESC
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if event_type:
                query = '''
                    SELECT * FROM events
                    WHERE dynasty_id = ? AND event_type = ?
                    ORDER BY timestamp DESC
                '''
                params = (dynasty_id, event_type)
            else:
                query = '''
                    SELECT * FROM events
                    WHERE dynasty_id = ?
                    ORDER BY timestamp DESC
                '''
                params = (dynasty_id,)

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        finally:
            conn.close()

    def get_events_by_dynasty_and_timestamp(
        self,
        dynasty_id: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events for dynasty within timestamp range.

        Optimized for calendar queries with composite index on (dynasty_id, timestamp).

        Args:
            dynasty_id: Dynasty identifier
            start_timestamp_ms: Start of range (Unix ms)
            end_timestamp_ms: End of range (Unix ms)
            event_type: Optional filter by event type

        Returns:
            List of event dictionaries, ordered by timestamp ASC
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if event_type:
                cursor.execute('''
                    SELECT * FROM events
                    WHERE dynasty_id = ?
                      AND timestamp BETWEEN ? AND ?
                      AND event_type = ?
                    ORDER BY timestamp ASC
                ''', (dynasty_id, start_timestamp_ms, end_timestamp_ms, event_type))
            else:
                cursor.execute('''
                    SELECT * FROM events
                    WHERE dynasty_id = ?
                      AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                ''', (dynasty_id, start_timestamp_ms, end_timestamp_ms))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        finally:
            conn.close()

    def get_events_by_game_id_prefix(
        self,
        prefix: str,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use get_events_by_dynasty() instead.

        This method is kept for backward compatibility but should not be used
        in new code. Dynasty isolation is now handled via the dynasty_id column.

        Retrieve events where game_id starts with the specified prefix.

        Efficient database-level filtering for dynasty-specific queries.
        Useful for isolating events by dynasty, season, or event category.

        Examples:
            # Get all playoff events for dynasty_a in 2024
            events = api.get_events_by_game_id_prefix("playoff_dynasty_a_2024_", "GAME")

            # Get all preseason events for dynasty_b
            events = api.get_events_by_game_id_prefix("preseason_dynasty_b_", "GAME")

            # Get all events (any type) for a specific game series
            events = api.get_events_by_game_id_prefix("playoff_eagles_2024_wild_card_")

        Args:
            prefix: Game ID prefix to match (e.g., "playoff_dynasty_a_2024_")
            event_type: Optional filter by event type (e.g., "GAME", "MEDIA")
                       If None, returns events of all types matching the prefix

        Returns:
            List of event dictionaries matching the criteria, ordered by timestamp DESC

        Performance:
            - Uses SQL LIKE for efficient database-level filtering
            - Leverages game_id index for fast lookups
            - More efficient than loading all events and filtering in Python
        """
        import warnings
        warnings.warn(
            "get_events_by_game_id_prefix() is deprecated. Use get_events_by_dynasty() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if event_type:
                cursor.execute(
                    'SELECT * FROM events WHERE game_id LIKE ? AND event_type = ? ORDER BY timestamp DESC',
                    (f"{prefix}%", event_type)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events WHERE game_id LIKE ? ORDER BY timestamp DESC',
                    (f"{prefix}%",)
                )

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        finally:
            conn.close()

    def get_events_by_timestamp_range(
        self,
        start_timestamp_ms: int,
        end_timestamp_ms: int,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events within a specific timestamp range.

        Efficient database-level filtering for calendar and date-based queries.
        Useful for retrieving events for a specific month, week, or custom date range.

        Examples:
            # Get all events in September 2025
            start = int(datetime(2025, 9, 1).timestamp() * 1000)
            end = int(datetime(2025, 10, 1).timestamp() * 1000)
            events = api.get_events_by_timestamp_range(start, end)

            # Get only game events in a date range
            events = api.get_events_by_timestamp_range(start, end, "GAME")

        Args:
            start_timestamp_ms: Start of range in Unix milliseconds (inclusive)
            end_timestamp_ms: End of range in Unix milliseconds (inclusive)
            event_type: Optional filter by event type (e.g., "GAME", "DEADLINE")
                       If None, returns events of all types in the range

        Returns:
            List of event dictionaries matching the criteria, ordered by timestamp ASC
            Empty list if no events found in range

        Performance:
            - Uses SQL BETWEEN for efficient range queries
            - Leverages timestamp index for fast lookups
            - More efficient than loading all events and filtering in Python
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if event_type:
                cursor.execute(
                    'SELECT * FROM events WHERE timestamp BETWEEN ? AND ? AND event_type = ? ORDER BY timestamp ASC',
                    (start_timestamp_ms, end_timestamp_ms, event_type)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC',
                    (start_timestamp_ms, end_timestamp_ms)
                )

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        finally:
            conn.close()

    def count_events(self, game_id: Optional[str] = None) -> int:
        """
        Count total events, optionally filtered by game_id.

        Args:
            game_id: Optional game identifier to filter by

        Returns:
            Count of events
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if game_id:
                cursor.execute('SELECT COUNT(*) FROM events WHERE game_id = ?', (game_id,))
            else:
                cursor.execute('SELECT COUNT(*) FROM events')

            return cursor.fetchone()[0]

        finally:
            conn.close()

    def update_event(self, event: BaseEvent) -> bool:
        """
        Update an existing event in the database.

        Typically used to add results after simulation:
        1. Store event with parameters only (scheduling)
        2. Simulate later
        3. Update with results (caching)

        Args:
            event: Event object with updated data

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Convert event to database format
            event_data = event.to_database_format()

            # PLAYOFF EVENT LOGGING: Track when playoff events are updated
            game_id = event_data.get('game_id', '')
            if 'playoff_' in game_id:
                print(f"[PLAYOFF_UPDATE] Updating playoff event in database:")
                print(f"  event_id: {event_data['event_id']}")
                print(f"  game_id: {game_id}")
                print(f"  dynasty_id: {event_data['dynasty_id']}")
                print(f"  event_type: {event_data['event_type']}")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE events
                SET event_type = ?,
                    timestamp = ?,
                    game_id = ?,
                    dynasty_id = ?,
                    data = ?
                WHERE event_id = ?
            ''', (
                event_data['event_type'],
                int(event_data['timestamp'].timestamp() * 1000),
                event_data['game_id'],
                event_data['dynasty_id'],
                json.dumps(event_data['data']),
                event_data['event_id']
            ))

            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()

            if affected_rows > 0:
                self.logger.debug(f"Updated event: {event_data['event_id']}")
                if 'playoff_' in game_id:
                    print(f"[PLAYOFF_UPDATE] ✅ Updated {affected_rows} playoff event(s)")
                return True
            else:
                self.logger.warning(f"No event found with ID: {event_data['event_id']}")
                if 'playoff_' in game_id:
                    print(f"[PLAYOFF_UPDATE] ⚠️  WARNING: No playoff event found with ID: {event_data['event_id']}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating event: {e}")
            return False

    def delete_events_by_game_id(self, game_id: str) -> int:
        """
        Delete all events for a specific game.

        Useful for cleanup or testing. Use with caution in production.

        Args:
            game_id: Game identifier

        Returns:
            Number of events deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM events WHERE game_id = ?', (game_id,))
            deleted_count = cursor.rowcount

            conn.commit()

            self.logger.info(f"Deleted {deleted_count} events for game_id: {game_id}")

            return deleted_count

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error deleting events: {e}")
            raise

        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert database row to dictionary format.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with deserialized data
        """
        return {
            'event_id': row['event_id'],
            'event_type': row['event_type'],
            'timestamp': datetime.fromtimestamp(row['timestamp'] / 1000),  # Convert from milliseconds
            'game_id': row['game_id'],
            'dynasty_id': row['dynasty_id'],
            'data': json.loads(row['data'])
        }

    def _validate_event_data(self, event_data: Dict[str, Any]):
        """
        Validate event data has required fields.

        Args:
            event_data: Event dictionary to validate

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['event_id', 'event_type', 'timestamp', 'game_id', 'dynasty_id', 'data']

        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Event data missing required field: {field}")

        if not isinstance(event_data['data'], dict):
            raise ValueError("Event data 'data' field must be a dictionary")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics about stored events
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Total events
            cursor.execute('SELECT COUNT(*) FROM events')
            total_events = cursor.fetchone()[0]

            # Events by type
            cursor.execute('SELECT event_type, COUNT(*) FROM events GROUP BY event_type')
            events_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # Unique games
            cursor.execute('SELECT COUNT(DISTINCT game_id) FROM events')
            unique_games = cursor.fetchone()[0]

            return {
                'total_events': total_events,
                'unique_games': unique_games,
                'events_by_type': events_by_type
            }

        finally:
            conn.close()

    def get_next_offseason_milestone(
        self,
        current_date,  # calendar.date_models.Date
        season_year: int,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get next offseason milestone event after current date.

        Queries all three offseason event types (DEADLINE, WINDOW, MILESTONE)
        and returns the chronologically next event for UI display and simulation control.

        Args:
            current_date: Current calendar date (Date object)
            season_year: Season year for filtering
            dynasty_id: Dynasty identifier for isolation

        Returns:
            Dict with milestone info or None if no more milestones:
            {
                'event_id': str,
                'event_type': 'DEADLINE' | 'WINDOW' | 'MILESTONE',
                'event_date': Date,
                'display_name': str,  # User-friendly name
                'description': str,
                'data': Dict  # Full event data
            }

        Example:
            >>> current = Date(2026, 2, 10)
            >>> milestone = api.get_next_offseason_milestone(current, 2025, "dynasty1")
            >>> print(milestone['display_name'])  # "Scouting Combine"
            >>> print(milestone['event_date'])    # 2026-02-24
        """
        from calendar.date_models import Date

        # Convert current_date to timestamp for query
        # Date → Python date → datetime
        py_date = current_date.to_python_date()
        current_datetime = datetime.combine(py_date, datetime.min.time())
        current_timestamp_ms = int(current_datetime.timestamp() * 1000)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Query for next event after current date
            # Filter by: dynasty_id, season_year (in data JSON), event_type (DEADLINE/WINDOW/MILESTONE)
            # Order by timestamp ASC, limit 1
            cursor.execute('''
                SELECT * FROM events
                WHERE dynasty_id = ?
                  AND timestamp > ?
                  AND event_type IN ('DEADLINE', 'WINDOW', 'MILESTONE')
                ORDER BY timestamp ASC
                LIMIT 1
            ''', (dynasty_id, current_timestamp_ms))

            row = cursor.fetchone()

            if not row:
                return None

            # Convert row to dict
            event_dict = self._row_to_dict(row)
            event_data = event_dict['data']

            # Verify season_year matches (data contains season info in parameters section)
            # Events store data in structure: {"parameters": {...}, "results": {...}, "metadata": {...}}
            params = event_data.get('parameters', {})
            if params.get('season_year') != season_year:
                return None

            # Extract event-specific fields from parameters section
            event_type = event_dict['event_type']

            # Build display name based on event type
            # All event-specific fields are stored in parameters section
            if event_type == 'DEADLINE':
                deadline_type = params.get('deadline_type', '')
                display_name = self._get_deadline_display_name(deadline_type)
            elif event_type == 'WINDOW':
                window_name = params.get('window_name', '')
                window_type = params.get('window_type', 'START')
                display_name = self._get_window_display_name(window_name, window_type)
            elif event_type == 'MILESTONE':
                milestone_type = params.get('milestone_type', '')
                display_name = self._get_milestone_display_name(milestone_type)
            else:
                display_name = 'Next Milestone'

            # Reconstruct Date from timestamp
            # Note: _row_to_dict() already converts timestamp to datetime object
            event_timestamp = event_dict['timestamp']
            event_date = Date(event_timestamp.year, event_timestamp.month, event_timestamp.day)

            return {
                'event_id': event_dict['event_id'],
                'event_type': event_type,
                'event_date': event_date,
                'display_name': display_name,
                'description': params.get('description', ''),
                'data': event_data
            }

        finally:
            conn.close()

    def _get_deadline_display_name(self, deadline_type: str) -> str:
        """Convert deadline type to UI-friendly display name."""
        DEADLINE_NAMES = {
            'FRANCHISE_TAG': 'Franchise Tags',
            'SALARY_CAP_COMPLIANCE': 'Cap Compliance',
            'RFA_TENDER': 'RFA Tenders',
            'FINAL_ROSTER_CUTS': 'Roster Cuts',
            'JUNE_1_RELEASES': 'June 1 Releases'
        }
        return DEADLINE_NAMES.get(deadline_type, deadline_type.replace('_', ' ').title())

    def _get_window_display_name(self, window_name: str, window_type: str) -> str:
        """Convert window name/type to UI-friendly display name."""
        WINDOW_NAMES = {
            ('LEGAL_TAMPERING', 'START'): 'Legal Tampering',
            ('LEGAL_TAMPERING', 'END'): 'Legal Tampering Ends',
            ('FREE_AGENCY', 'START'): 'Free Agency',
            ('FREE_AGENCY', 'END'): 'Free Agency Ends',
            ('OTA_OFFSEASON', 'START'): 'OTAs',
            ('OTA_OFFSEASON', 'END'): 'OTA Conclusion',
            ('MINICAMP', 'START'): 'Minicamp',
            ('MINICAMP', 'END'): 'Minicamp Ends',
            ('TRAINING_CAMP', 'START'): 'Training Camp',
            ('TRAINING_CAMP', 'END'): 'Training Camp Ends',
            ('PRESEASON', 'START'): 'Preseason',
            ('PRESEASON', 'END'): 'Preseason Ends',
        }
        key = (window_name, window_type)
        default = f"{window_name.replace('_', ' ').title()} {window_type.title()}"
        return WINDOW_NAMES.get(key, default)

    def _get_milestone_display_name(self, milestone_type: str) -> str:
        """Convert milestone type to UI-friendly display name."""
        MILESTONE_NAMES = {
            'COMBINE_START': 'Scouting Combine',
            'COMBINE_END': 'Combine Ends',
            'NEW_LEAGUE_YEAR': 'New League Year',
            'DRAFT': 'Draft',
            'DRAFT_ORDER_FINALIZED': 'Draft Order',
            'ROOKIE_MINICAMP': 'Rookie Minicamp',
            'SCHEDULE_RELEASE': 'Schedule Release'
        }
        return MILESTONE_NAMES.get(milestone_type, milestone_type.replace('_', ' ').title())

    def __str__(self) -> str:
        """String representation"""
        return f"EventDatabaseAPI(db_path='{self.db_path}')"

    def __repr__(self) -> str:
        """Detailed representation"""
        return f"EventDatabaseAPI(database_path='{self.db_path}')"
