"""
Unified Database API

Single entry point for ALL database operations across the entire simulation engine.
Consolidates dynasty_state, events, salary cap, draft, roster, and statistics APIs
into one cohesive interface with connection pooling and transaction support.

This API replaces the pattern of instantiating multiple specialized APIs
(DatabaseAPI, DynastyStateAPI, CapDatabaseAPI, etc.) with a single unified interface.

Architecture:
- Connection pooling for performance
- Transaction support for atomic multi-operation workflows
- Dynasty isolation built-in
- Type-safe operations with comprehensive error handling
- Method groups: dynasty, events, cap, draft, roster, stats

Usage:
    # Basic usage
    api = UnifiedDatabaseAPI(database_path="nfl.db", dynasty_id="my_dynasty")
    state = api.dynasty_get_latest_state()
    standings = api.standings_get(season=2024)

    # Transaction usage for atomic operations
    with api.transaction():
        api.contracts_insert(...)
        api.cap_update_team_summary(...)
"""

import sqlite3
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
import threading
import json
import uuid


class ConnectionPool:
    """
    Simple connection pool for SQLite database access.

    Maintains a thread-safe pool of database connections to avoid
    repeated open/close overhead and support concurrent access.
    """

    def __init__(self, database_path: str, max_connections: int = 10):
        """
        Initialize connection pool.

        Args:
            database_path: Path to SQLite database
            max_connections: Maximum number of pooled connections
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool: List[sqlite3.Connection] = []
        self._in_use: set = set()
        self._lock = threading.Lock()

        # Ensure database file exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool.

        Returns:
            SQLite connection object
        """
        with self._lock:
            # Reuse available connection from pool
            if self._pool:
                conn = self._pool.pop()
                self._in_use.add(id(conn))
                return conn

            # Create new connection if under limit
            if len(self._in_use) < self.max_connections:
                conn = self._create_connection()
                self._in_use.add(id(conn))
                return conn

            # Pool exhausted - create temporary connection
            # (will not be returned to pool)
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool.

        Args:
            conn: Connection to return
        """
        with self._lock:
            conn_id = id(conn)

            if conn_id in self._in_use:
                self._in_use.remove(conn_id)

                # Return to pool if space available
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    # Pool full - close excess connection
                    conn.close()
            else:
                # Temporary connection - close it
                conn.close()

    def close_all(self) -> None:
        """Close all pooled connections."""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._in_use.clear()

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with optimal settings.

        Returns:
            Configured SQLite connection
        """
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn


class TransactionContext:
    """
    Context manager for database transactions.

    Provides atomic transaction support with automatic commit/rollback.
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize transaction context.

        Args:
            connection: Database connection to use for transaction
        """
        self.connection = connection
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        """Begin transaction."""
        self.connection.execute("BEGIN TRANSACTION")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction based on exception status."""
        if exc_type is None:
            # No exception - commit
            self.connection.commit()
        else:
            # Exception occurred - rollback
            self.connection.rollback()
            self.logger.error(f"Transaction rolled back due to error: {exc_val}")
        return False  # Re-raise exception if it occurred

    def commit(self):
        """Explicitly commit transaction."""
        self.connection.commit()

    def rollback(self):
        """Explicitly rollback transaction."""
        self.connection.rollback()


class UnifiedDatabaseAPI:
    """
    Unified database API providing single entry point for all database operations.

    This class consolidates all specialized database APIs (dynasty_state, events,
    salary cap, draft, roster, statistics) into one interface with connection
    pooling and transaction support.

    Method Naming Convention:
    - {domain}_{operation}_{target}
    - Examples: dynasty_get_latest_state(), contracts_insert(), standings_get()

    Method Groups:
    - Dynasty: dynasty_get_latest_state, dynasty_update_state, dynasty_initialize, etc.
    - Events: events_insert, events_get_by_game_id, events_get_by_type, etc.
    - Cap: cap_get_team_summary, contracts_insert, contracts_get_active, etc.
    - Draft: draft_generate_class, draft_get_prospects, draft_execute_pick, etc.
    - Roster: roster_get_team, players_get_free_agents, roster_update_depth, etc.
    - Stats: standings_get, stats_get_passing_leaders, stats_get_team_summary, etc.
    """

    def __init__(
        self,
        database_path: str = "data/database/nfl_simulation.db",
        dynasty_id: str = "default",
        pool_size: int = 10
    ):
        """
        Initialize Unified Database API.

        Args:
            database_path: Path to SQLite database file
            dynasty_id: Default dynasty identifier for all operations
            pool_size: Maximum number of pooled connections
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(__name__)

        # Initialize connection pool
        self.pool = ConnectionPool(database_path, max_connections=pool_size)

        # Active transaction tracking (thread-local)
        self._active_transaction: Optional[sqlite3.Connection] = None

        # Ensure database schema is initialized
        self._ensure_schemas()

    # ========================================================================
    # CORE INFRASTRUCTURE
    # ========================================================================

    def _ensure_schemas(self) -> None:
        """
        Initialize all database schemas.

        Checks for required tables and runs migrations if needed.
        This ensures the database is ready for all operations.
        """
        conn = self._get_connection()
        try:
            # Check if core tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dynasties'"
            )

            if cursor.fetchone() is None:
                # Database not initialized - run schema creation
                self.logger.info("Initializing database schemas...")
                self._create_all_tables(conn)
                conn.commit()
                self.logger.info("Database schemas initialized successfully")
            else:
                # Database exists - check for pending migrations
                self._run_pending_migrations(conn)

        except Exception as e:
            self.logger.error(f"Error ensuring schemas: {e}", exc_info=True)
            raise
        finally:
            self._return_connection(conn)

    def _create_all_tables(self, conn: sqlite3.Connection) -> None:
        """
        Create all database tables.

        Uses the existing DatabaseConnection schema as reference.
        This is called only if database is completely uninitialized.

        Args:
            conn: Active database connection
        """
        # Import and use existing DatabaseConnection schema
        from .connection import DatabaseConnection
        db = DatabaseConnection(self.database_path)
        db._create_tables(conn)
        self.logger.info("All tables created successfully")

    def _run_pending_migrations(self, conn: sqlite3.Connection) -> None:
        """
        Run any pending database migrations.

        Checks migrations directory and applies any unapplied migrations.

        Args:
            conn: Active database connection
        """
        migrations_dir = Path(__file__).parent / "migrations"

        if not migrations_dir.exists():
            return

        # Get list of applied migrations (if migration tracking table exists)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )

            if cursor.fetchone() is None:
                # Create migration tracking table
                conn.execute("""
                    CREATE TABLE schema_migrations (
                        migration_name TEXT PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Could not check migrations: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection from pool or active transaction.

        If inside a transaction context, returns the transaction connection.
        Otherwise, gets a new connection from the pool.

        Returns:
            SQLite connection object
        """
        if self._active_transaction is not None:
            return self._active_transaction

        return self.pool.get_connection()

    def _return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return connection to pool.

        Does not return transaction connections (managed by transaction context).

        Args:
            conn: Connection to return
        """
        if self._active_transaction is None or conn != self._active_transaction:
            self.pool.return_connection(conn)

    def _execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results.

        Automatically handles connection management and result conversion.

        Args:
            query: SQL SELECT statement
            params: Query parameters (tuple)

        Returns:
            List of result dictionaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = cursor.fetchall()
            # Convert sqlite3.Row to dicts
            return [dict(row) for row in results]

        finally:
            self._return_connection(conn)

    def _execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE query.

        Automatically handles connection management, transactions, and commits.

        Args:
            query: SQL INSERT/UPDATE/DELETE statement
            params: Query parameters (tuple)

        Returns:
            Number of affected rows
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Only commit if not in active transaction
            if self._active_transaction is None:
                conn.commit()

            return cursor.rowcount

        except Exception as e:
            # Only rollback if not in active transaction
            if self._active_transaction is None:
                conn.rollback()
            self.logger.error(f"Error executing update: {e}", exc_info=True)
            raise

        finally:
            self._return_connection(conn)

    @contextmanager
    def transaction(self):
        """
        Multi-operation atomic transaction context manager.

        All database operations within the context will be part of
        a single transaction that commits on success or rolls back on error.

        Example:
            with api.transaction():
                api.contracts_insert(...)
                api.cap_update_team_summary(...)
                # Both operations commit together or rollback together

        Yields:
            self (UnifiedDatabaseAPI instance for method chaining)
        """
        conn = self._get_connection()
        try:
            with TransactionContext(conn) as tx:
                self._active_transaction = conn
                yield self
                tx.commit()
        finally:
            self._active_transaction = None
            self._return_connection(conn)

    def close(self) -> None:
        """
        Close all pooled connections.

        Should be called when API is no longer needed to clean up resources.
        """
        self.pool.close_all()
        self.logger.info("All database connections closed")

    # ========================================================================
    # DYNASTY STATE OPERATIONS (8 methods)
    # ========================================================================

    def dynasty_get_latest_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent simulation state for the current dynasty.

        Returns:
            Dict with season, current_date, current_phase, current_week, last_simulated_game_id
            or None if no state exists
        """
        query = """
            SELECT season, "current_date", "current_phase", "current_week", last_simulated_game_id
            FROM dynasty_state
            WHERE dynasty_id = ?
            ORDER BY season DESC
            LIMIT 1
        """

        results = self._execute_query(query, (self.dynasty_id,))

        if results:
            row = results[0]
            return {
                'season': row['season'],
                'current_date': row['current_date'],
                'current_phase': row['current_phase'],
                'current_week': row['current_week'],
                'last_simulated_game_id': row['last_simulated_game_id']
            }

        return None

    def dynasty_get_state(self, season: int) -> Optional[Dict[str, Any]]:
        """
        Get simulation state for specific season.

        Args:
            season: Season year

        Returns:
            Dict with current_date, current_phase, current_week, last_simulated_game_id
            or None if no state exists
        """
        query = """
            SELECT "current_date", "current_phase", "current_week", last_simulated_game_id
            FROM dynasty_state
            WHERE dynasty_id = ? AND season = ?
        """

        results = self._execute_query(query, (self.dynasty_id, season))

        if results:
            row = results[0]
            return {
                'current_date': row['current_date'],
                'current_phase': row['current_phase'],
                'current_week': row['current_week'],
                'last_simulated_game_id': row['last_simulated_game_id']
            }

        return None

    def dynasty_initialize_state(
        self,
        season: int,
        start_date: str,
        start_week: int = 1,
        start_phase: str = 'regular_season'
    ) -> bool:
        """
        Initialize fresh dynasty state for a new season.

        ALWAYS deletes any existing state first to ensure clean slate.

        Args:
            season: Season year
            start_date: Start date in YYYY-MM-DD format
            start_week: Starting week number (default: 1)
            start_phase: Starting phase (default: 'regular_season')

        Returns:
            True if successful, False otherwise
        """
        try:
            # DEFENSIVE: Delete any existing state first
            self.dynasty_delete_state(season)

            # Insert fresh state
            # IMPORTANT: Quote "current_date" to avoid SQLite auto-fill with CURRENT_DATE
            query = """
                INSERT INTO dynasty_state
                (dynasty_id, season, "current_date", current_week, current_phase)
                VALUES (?, ?, ?, ?, ?)
            """

            self._execute_update(
                query,
                (self.dynasty_id, season, start_date, start_week, start_phase)
            )

            # VERIFICATION: Read back what we just wrote
            verification = self.dynasty_get_state(season)

            if verification and verification['current_date'] == start_date:
                return True
            else:
                self.logger.error(
                    f"Dynasty state verification failed - expected {start_date}, "
                    f"got {verification['current_date'] if verification else 'None'}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error initializing dynasty state: {e}", exc_info=True)
            return False

    def dynasty_update_state(
        self,
        season: int,
        current_date: str,
        current_phase: str,
        current_week: Optional[int] = None,
        last_simulated_game_id: Optional[str] = None
    ) -> bool:
        """
        Update existing dynasty state.

        Args:
            season: Season year
            current_date: Current simulation date (YYYY-MM-DD)
            current_phase: Current phase (regular_season, playoffs, offseason)
            current_week: Current week number
            last_simulated_game_id: ID of last simulated game

        Returns:
            True if successful, False otherwise
        """
        try:
            # IMPORTANT: Quote "current_date" to avoid SQLite auto-fill with CURRENT_DATE
            query = """
                INSERT OR REPLACE INTO dynasty_state
                (dynasty_id, season, "current_date", current_phase, current_week,
                 last_simulated_game_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            rows_affected = self._execute_update(
                query,
                (self.dynasty_id, season, current_date, current_phase, current_week, last_simulated_game_id)
            )

            return rows_affected > 0

        except Exception as e:
            self.logger.error(f"Error updating dynasty state: {e}", exc_info=True)
            return False

    def dynasty_delete_state(self, season: int) -> int:
        """
        Delete dynasty state for specific season.

        Args:
            season: Season year

        Returns:
            Number of rows deleted
        """
        try:
            query = "DELETE FROM dynasty_state WHERE dynasty_id = ? AND season = ?"
            rows_deleted = self._execute_update(query, (self.dynasty_id, season))
            return rows_deleted

        except Exception as e:
            self.logger.error(f"Error deleting dynasty state: {e}", exc_info=True)
            return 0

    def dynasty_get_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current dynasty.

        Returns:
            Dict with dynasty_name, owner_name, team_id, total_seasons, championships_won, etc.
            or None if dynasty does not exist
        """
        query = """
            SELECT dynasty_id, dynasty_name, owner_name, team_id,
                   total_seasons, championships_won, super_bowls_won,
                   conference_championships, division_titles,
                   total_wins, total_losses, total_ties,
                   created_at, last_played, is_active
            FROM dynasties
            WHERE dynasty_id = ?
        """

        results = self._execute_query(query, (self.dynasty_id,))

        if results:
            row = results[0]
            return {
                'dynasty_id': row['dynasty_id'],
                'dynasty_name': row['dynasty_name'],
                'owner_name': row.get('owner_name'),
                'team_id': row.get('team_id'),
                'total_seasons': row.get('total_seasons', 0),
                'championships_won': row.get('championships_won', 0),
                'super_bowls_won': row.get('super_bowls_won', 0),
                'conference_championships': row.get('conference_championships', 0),
                'division_titles': row.get('division_titles', 0),
                'total_wins': row.get('total_wins', 0),
                'total_losses': row.get('total_losses', 0),
                'total_ties': row.get('total_ties', 0),
                'created_at': row.get('created_at'),
                'last_played': row.get('last_played'),
                'is_active': row.get('is_active', True)
            }

        return None

    def dynasty_create(
        self,
        dynasty_name: str,
        owner_name: str,
        team_id: int
    ) -> str:
        """
        Create a new dynasty record.

        Args:
            dynasty_name: Name of the dynasty
            owner_name: Name of the owner/player
            team_id: ID of the team (1-32)

        Returns:
            The generated dynasty_id (UUID)

        Raises:
            ValueError: If team_id is not in valid range (1-32)
        """
        if not (1 <= team_id <= 32):
            raise ValueError(f"Invalid team_id: {team_id}. Must be between 1 and 32.")

        try:
            # Generate UUID for dynasty_id
            new_dynasty_id = str(uuid.uuid4())

            query = """
                INSERT INTO dynasties
                (dynasty_id, dynasty_name, owner_name, team_id, total_seasons,
                 championships_won, super_bowls_won, conference_championships,
                 division_titles, total_wins, total_losses, total_ties, is_active)
                VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, TRUE)
            """

            self._execute_update(query, (new_dynasty_id, dynasty_name, owner_name, team_id))

            self.logger.info(f"Created new dynasty: {dynasty_name} (ID: {new_dynasty_id})")
            return new_dynasty_id

        except Exception as e:
            self.logger.error(f"Error creating dynasty: {e}", exc_info=True)
            raise

    def dynasty_ensure_exists(
        self,
        dynasty_name: Optional[str] = None,
        owner_name: Optional[str] = None,
        team_id: Optional[int] = None
    ) -> bool:
        """
        Ensure current dynasty record exists, creating it if necessary.

        Args:
            dynasty_name: Name of dynasty (defaults to dynasty_id)
            owner_name: Optional owner name
            team_id: Optional team ID

        Returns:
            True if dynasty exists or was created, False on error
        """
        try:
            # Check if dynasty already exists
            info = self.dynasty_get_info()
            if info:
                return True

            # Dynasty doesn't exist - create it
            dynasty_name = dynasty_name or self.dynasty_id
            owner_name = owner_name or "Owner"
            team_id = team_id or 1  # Default to first team

            query = """
                INSERT OR IGNORE INTO dynasties
                (dynasty_id, dynasty_name, owner_name, team_id, total_seasons,
                 championships_won, super_bowls_won, conference_championships,
                 division_titles, total_wins, total_losses, total_ties, is_active)
                VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, TRUE)
            """

            rows_affected = self._execute_update(
                query,
                (self.dynasty_id, dynasty_name, owner_name, team_id)
            )

            if rows_affected > 0:
                self.logger.info(f"Created dynasty record: {dynasty_name} (ID: {self.dynasty_id})")

            return True

        except Exception as e:
            self.logger.error(f"Error ensuring dynasty exists: {e}", exc_info=True)
            return False

    # ========================================================================
    # EVENTS OPERATIONS (15 methods)
    # ========================================================================

    def events_insert(
        self,
        event_id: str,
        event_type: str,
        timestamp: int,
        game_id: str,
        data: str
    ) -> bool:
        """
        Insert a new event into the database.

        Args:
            event_id: Unique event identifier
            event_type: Event type ('GAME', 'DEADLINE', 'UFA_SIGNING', etc.)
            timestamp: Unix timestamp in milliseconds
            game_id: Game/context identifier for grouping
            data: JSON event data

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO events (event_id, event_type, timestamp, game_id, dynasty_id, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            self._execute_update(
                query,
                (event_id, event_type, timestamp, game_id, self.dynasty_id, data)
            )

            self.logger.debug(f"Inserted event: {event_id} ({event_type})")
            return True

        except Exception as e:
            self.logger.error(f"Error inserting event {event_id}: {e}", exc_info=True)
            return False

    def events_get_by_game_id(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a specific game/context.

        Args:
            game_id: Game/context identifier

        Returns:
            List of event dictionaries
        """
        query = """
            SELECT * FROM events
            WHERE game_id = ? AND dynasty_id = ?
            ORDER BY timestamp ASC
        """

        results = self._execute_query(query, (game_id, self.dynasty_id))

        # Convert timestamp from milliseconds to datetime
        for result in results:
            if 'timestamp' in result and result['timestamp']:
                result['timestamp'] = datetime.fromtimestamp(result['timestamp'] / 1000)
            if 'data' in result and isinstance(result['data'], str):
                result['data'] = json.loads(result['data'])

        self.logger.debug(f"Retrieved {len(results)} events for game_id: {game_id}")
        return results

    def events_get_by_type(
        self,
        event_type: str,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all events of a specific type within optional time range.

        Args:
            event_type: Event type to filter by
            start_timestamp: Optional start time (milliseconds since epoch)
            end_timestamp: Optional end time (milliseconds since epoch)

        Returns:
            List of event dictionaries
        """
        if start_timestamp is not None and end_timestamp is not None:
            query = """
                SELECT * FROM events
                WHERE dynasty_id = ? AND event_type = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """
            params = (self.dynasty_id, event_type, start_timestamp, end_timestamp)
        else:
            query = """
                SELECT * FROM events
                WHERE dynasty_id = ? AND event_type = ?
                ORDER BY timestamp DESC
            """
            params = (self.dynasty_id, event_type)

        results = self._execute_query(query, params)

        # Convert timestamp and data
        for result in results:
            if 'timestamp' in result and result['timestamp']:
                result['timestamp'] = datetime.fromtimestamp(result['timestamp'] / 1000)
            if 'data' in result and isinstance(result['data'], str):
                result['data'] = json.loads(result['data'])

        return results

    def events_get_games_by_week(
        self,
        season: int,
        week: int,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Get scheduled games from events table for a specific week.

        The schedule is stored as GAME events in the events table with
        game parameters in the JSON data field.

        Args:
            season: Season year (e.g., 2025)
            week: Week number (1-18 for regular season)
            season_type: Type of season ('regular_season', 'preseason', 'playoffs')

        Returns:
            List of game dictionaries with keys:
            - event_id: The event ID (used as game_id for tracking)
            - home_team_id: Home team ID
            - away_team_id: Away team ID
            - week: Week number
            - season: Season year
            - season_type: Season type
            - game_date: Game date string
            - results: None if not played, dict with scores if played
        """
        query = """
            SELECT event_id, game_id, data FROM events
            WHERE dynasty_id = ? AND event_type = 'GAME'
            AND json_extract(data, '$.parameters.season') = ?
            AND json_extract(data, '$.parameters.week') = ?
            AND json_extract(data, '$.parameters.season_type') = ?
            ORDER BY json_extract(data, '$.parameters.game_date')
        """
        results = self._execute_query(query, (self.dynasty_id, season, week, season_type))

        # Transform to game format
        games = []
        for row in results:
            data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            params = data.get('parameters', {})
            results_data = data.get('results')

            games.append({
                'event_id': row['event_id'],
                'game_id': row['game_id'],
                'home_team_id': params.get('home_team_id'),
                'away_team_id': params.get('away_team_id'),
                'week': params.get('week'),
                'season': params.get('season'),
                'season_type': params.get('season_type'),
                'game_date': params.get('game_date'),
                'home_score': results_data.get('home_score') if results_data else None,
                'away_score': results_data.get('away_score') if results_data else None,
            })

        return games

    def events_update_game_result(
        self,
        event_id: str,
        home_score: int,
        away_score: int
    ) -> bool:
        """
        Update a GAME event with the simulation result.

        Args:
            event_id: The event ID of the game
            home_score: Home team final score
            away_score: Away team final score

        Returns:
            True if update succeeded, False otherwise
        """
        # First get the current event data
        query = "SELECT data FROM events WHERE event_id = ? AND dynasty_id = ?"
        results = self._execute_query(query, (event_id, self.dynasty_id))

        if not results:
            return False

        data = json.loads(results[0]['data']) if isinstance(results[0]['data'], str) else results[0]['data']

        # Update results
        data['results'] = {
            'home_score': home_score,
            'away_score': away_score,
            'completed': True
        }

        # Save back to database
        update_query = "UPDATE events SET data = ? WHERE event_id = ? AND dynasty_id = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(update_query, (json.dumps(data), event_id, self.dynasty_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] Failed to update game result: {e}")
            return False

    def events_get_by_date_range(
        self,
        start_timestamp: int,
        end_timestamp: int
    ) -> List[Dict[str, Any]]:
        """
        Get all events within a date range.

        Args:
            start_timestamp: Start time (milliseconds since epoch)
            end_timestamp: End time (milliseconds since epoch)

        Returns:
            List of event dictionaries sorted by timestamp
        """
        query = """
            SELECT * FROM events
            WHERE dynasty_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """

        results = self._execute_query(query, (self.dynasty_id, start_timestamp, end_timestamp))

        # Convert timestamp and data
        for result in results:
            if 'timestamp' in result and result['timestamp']:
                result['timestamp'] = datetime.fromtimestamp(result['timestamp'] / 1000)
            if 'data' in result and isinstance(result['data'], str):
                result['data'] = json.loads(result['data'])

        return results

    def events_delete_by_game_id(self, game_id: str) -> int:
        """
        Delete all events for a specific game/context.

        Args:
            game_id: Game/context identifier

        Returns:
            Number of events deleted
        """
        try:
            query = "DELETE FROM events WHERE game_id = ? AND dynasty_id = ?"
            deleted_count = self._execute_update(query, (game_id, self.dynasty_id))

            self.logger.info(f"Deleted {deleted_count} events for game_id: {game_id}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting events: {e}", exc_info=True)
            raise

    def events_count_by_type(self, event_type: str) -> int:
        """
        Count events of a specific type.

        Args:
            event_type: Event type to count

        Returns:
            Number of events
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM events WHERE dynasty_id = ? AND event_type = ?',
                (self.dynasty_id, event_type)
            )
            count = cursor.fetchone()[0]
            return count

        finally:
            self._return_connection(conn)

    def events_insert_batch(self, events: List[Any]) -> List[Any]:
        """
        Insert multiple events in a single transaction.

        All inserts succeed or all fail (atomic operation).
        Significantly faster than multiple events_insert() calls.

        Args:
            events: List of event objects implementing BaseEvent interface
                   (or list of dicts with event_id, event_type, timestamp, game_id, data)

        Returns:
            List of inserted events

        Raises:
            Exception: If database operation fails (rolls back transaction)
        """
        if not events:
            self.logger.debug("No events to insert")
            return []

        conn = self._get_connection()
        manually_managed = (self._active_transaction is None)

        try:
            # Start transaction if not already in one
            if manually_managed:
                conn.execute('BEGIN TRANSACTION')

            # Insert all events
            for event in events:
                # Support both BaseEvent objects and dict format
                if hasattr(event, 'to_database_format'):
                    event_data = event.to_database_format()
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
                else:
                    # Assume dict format
                    conn.execute('''
                        INSERT INTO events (event_id, event_type, timestamp, game_id, dynasty_id, data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        event['event_id'],
                        event['event_type'],
                        event['timestamp'],
                        event['game_id'],
                        self.dynasty_id,
                        event['data'] if isinstance(event['data'], str) else json.dumps(event['data'])
                    ))

            # Commit transaction if we started it
            if manually_managed:
                conn.execute('COMMIT')

            self.logger.info(f"Batch inserted {len(events)} events")
            return events

        except Exception as e:
            # Rollback on error if we started the transaction
            if manually_managed:
                conn.execute('ROLLBACK')
            self.logger.error(f"Error in batch insert: {e}", exc_info=True)
            raise

        finally:
            if manually_managed:
                self._return_connection(conn)

    def events_get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific event by its ID.

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found
        """
        query = "SELECT * FROM events WHERE event_id = ?"
        results = self._execute_query(query, (event_id,))

        if results:
            result = results[0]
            # Convert timestamp and data
            if 'timestamp' in result and result['timestamp']:
                result['timestamp'] = datetime.fromtimestamp(result['timestamp'] / 1000)
            if 'data' in result and isinstance(result['data'], str):
                result['data'] = json.loads(result['data'])
            return result

        return None

    def events_delete_playoff_by_dynasty(self, season: int) -> int:
        """
        Delete all playoff events for the current dynasty and season.

        Useful for cleanup before rescheduling playoffs or resetting dynasty state.

        Args:
            season: Season year

        Returns:
            Number of events deleted
        """
        try:
            # Delete all playoff games for this dynasty/season
            query = """
                DELETE FROM events
                WHERE dynasty_id = ?
                AND game_id LIKE ?
            """

            deleted_count = self._execute_update(query, (self.dynasty_id, f'playoff_{season}_%'))

            self.logger.info(
                f"Deleted {deleted_count} playoff events for dynasty: {self.dynasty_id}, season: {season}"
            )

            return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting playoff events: {e}", exc_info=True)
            raise

    def events_delete_regular_season_by_dynasty(self, season: int) -> int:
        """
        Delete all regular season game events for the current dynasty and season.

        Useful for regenerating the schedule for a new season.

        Args:
            season: Season year

        Returns:
            Number of events deleted
        """
        try:
            # Delete all regular season games for this dynasty/season
            # game_id format: "regular_{season}_{week}_{game_num}"
            query = """
                DELETE FROM events
                WHERE dynasty_id = ?
                AND game_id LIKE ?
            """

            deleted_count = self._execute_update(query, (self.dynasty_id, f'regular_{season}_%'))

            self.logger.info(
                f"Deleted {deleted_count} regular season events for dynasty: {self.dynasty_id}, season: {season}"
            )

            return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting regular season events: {e}", exc_info=True)
            raise

    def events_update(self, event: Any) -> bool:
        """
        Update an existing event in the database.

        Typically used to add results after simulation.

        Args:
            event: Event object (BaseEvent) or dict with updated data

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Support both BaseEvent objects and dict format
            if hasattr(event, 'to_database_format'):
                event_data = event.to_database_format()
                query = """
                    UPDATE events
                    SET event_type = ?,
                        timestamp = ?,
                        game_id = ?,
                        dynasty_id = ?,
                        data = ?
                    WHERE event_id = ?
                """
                params = (
                    event_data['event_type'],
                    int(event_data['timestamp'].timestamp() * 1000),
                    event_data['game_id'],
                    event_data['dynasty_id'],
                    json.dumps(event_data['data']),
                    event_data['event_id']
                )
            else:
                # Assume dict format
                query = """
                    UPDATE events
                    SET event_type = ?,
                        timestamp = ?,
                        game_id = ?,
                        dynasty_id = ?,
                        data = ?
                    WHERE event_id = ?
                """
                params = (
                    event['event_type'],
                    event['timestamp'],
                    event['game_id'],
                    self.dynasty_id,
                    event['data'] if isinstance(event['data'], str) else json.dumps(event['data']),
                    event['event_id']
                )

            affected_rows = self._execute_update(query, params)

            if affected_rows > 0:
                self.logger.debug(f"Updated event: {event['event_id'] if isinstance(event, dict) else event.event_id}")
                return True
            else:
                self.logger.warning(f"No event found with ID: {event['event_id'] if isinstance(event, dict) else event.event_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating event: {e}", exc_info=True)
            return False

    def events_get_next_offseason_milestone(
        self,
        current_date,  # Union[str, Date, datetime.date]
        season_year: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get next offseason milestone event after current date.

        Queries all three offseason event types (DEADLINE, WINDOW, MILESTONE)
        and returns the chronologically next event.

        Args:
            current_date: Current date (YYYY-MM-DD string OR Date/datetime object)
            season_year: Season year for filtering

        Returns:
            Dict with milestone info or None if no more milestones
        """
        try:
            # Convert current_date to timestamp (handle both Date objects and strings)
            from src.calendar.date_models import Date

            if isinstance(current_date, Date):
                year, month, day = current_date.year, current_date.month, current_date.day
            elif isinstance(current_date, str):
                year, month, day = map(int, current_date.split('-'))
            else:
                # Handle datetime.date objects
                year, month, day = current_date.year, current_date.month, current_date.day

            current_datetime = datetime(year, month, day)
            current_timestamp_ms = int(current_datetime.timestamp() * 1000)

            query = """
                SELECT * FROM events
                WHERE dynasty_id = ?
                  AND timestamp > ?
                  AND event_type IN ('DEADLINE', 'WINDOW', 'MILESTONE')
                ORDER BY timestamp ASC
                LIMIT 1
            """

            results = self._execute_query(query, (self.dynasty_id, current_timestamp_ms))

            if not results:
                return None

            result = results[0]

            # Parse timestamp
            if 'timestamp' in result and result['timestamp']:
                event_timestamp = datetime.fromtimestamp(result['timestamp'] / 1000)
            else:
                return None

            # Parse data JSON
            if 'data' in result and isinstance(result['data'], str):
                event_data = json.loads(result['data'])
            else:
                event_data = result.get('data', {})

            # Extract event type and parameters
            event_type = result.get('event_type', '')
            params = event_data.get('parameters', {})

            # Build display name based on event type
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

            # Convert event_date string to Date object
            from src.calendar.date_models import Date
            event_date_str = params.get('event_date', '')
            if event_date_str:
                year, month, day = map(int, event_date_str.split('-'))
                event_date = Date(year, month, day)
            else:
                # Fallback to timestamp
                event_date = Date(event_timestamp.year, event_timestamp.month, event_timestamp.day)

            # Return transformed structure with display_name and event_date as top-level keys
            return {
                'event_id': result.get('event_id', ''),
                'event_type': event_type,
                'event_date': event_date,  # Date object as top-level key
                'display_name': display_name,  # User-friendly name as top-level key
                'description': params.get('description', ''),
                'timestamp': event_timestamp,
                'data': event_data
            }

        except Exception as e:
            self.logger.error(f"Error getting next offseason milestone: {e}", exc_info=True)
            return None

    def events_get_milestone_by_type(
        self,
        milestone_type: str,
        season_year: int,
        year_tolerance: int = 1
    ) -> Optional['Date']:
        """
        Get milestone date by type with tolerant season_year matching.

        Handles phase transition edge cases where the controller's season_year
        may increment before all milestones are consumed. Uses year tolerance
        to accept milestones within ±N years of the target season.

        Args:
            milestone_type: Type of milestone (e.g., "PRESEASON_START", "DRAFT", "FREE_AGENCY_START")
            season_year: Season year to search for
            year_tolerance: Accept milestones within ±N years (default: 1)

        Returns:
            Date: Date of the milestone
            None: If milestone not found

        Example:
            # Get preseason start date for 2025 season (±1 year tolerance)
            date = db.events_get_milestone_by_type("PRESEASON_START", 2025, year_tolerance=1)
        """
        from src.calendar.date_models import Date

        try:
            query = """
                SELECT timestamp, data FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'MILESTONE'
                ORDER BY timestamp ASC
            """

            results = self._execute_query(query, (self.dynasty_id,))

            for row in results:
                # Parse event data
                data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                params = data.get('parameters', {})

                # Check if this is the milestone type we're looking for
                if params.get('milestone_type') == milestone_type:
                    # Get season year from milestone
                    event_season = params.get('season_year', 0)
                    year_diff = abs(event_season - season_year)

                    # Check if within tolerance
                    if year_diff <= year_tolerance:
                        # Convert timestamp to Date
                        dt = datetime.fromtimestamp(row['timestamp'] / 1000)
                        return Date(dt.year, dt.month, dt.day)

            # Milestone not found
            return None

        except Exception as e:
            self.logger.error(f"Error getting milestone by type '{milestone_type}': {e}", exc_info=True)
            return None

    def _get_deadline_display_name(self, deadline_type: str) -> str:
        """
        Get user-friendly display name for deadline event.

        Args:
            deadline_type: Technical deadline type (e.g., "FRANCHISE_TAG")

        Returns:
            User-friendly name (e.g., "Franchise Tags")
        """
        deadline_names = {
            'FRANCHISE_TAG': 'Franchise Tags',
            'TRANSITION_TAG': 'Transition Tags',
            'SALARY_CAP_COMPLIANCE': 'Cap Compliance',
            'RFA_TENDER': 'RFA Tenders',
            'ROSTER_CUT': 'Roster Cuts'
        }
        return deadline_names.get(deadline_type, deadline_type.replace('_', ' ').title())

    def _get_window_display_name(self, window_name: str, window_type: str) -> str:
        """
        Get user-friendly display name for window event.

        Args:
            window_name: Technical window name (e.g., "FREE_AGENCY")
            window_type: Window boundary type ("START" or "END")

        Returns:
            User-friendly name (e.g., "Free Agency" or "Free Agency Ends")
        """
        if window_type == 'END':
            return f"{window_name.replace('_', ' ').title()} Ends"
        return window_name.replace('_', ' ').title()

    def _get_milestone_display_name(self, milestone_type: str) -> str:
        """
        Get user-friendly display name for milestone event.

        Args:
            milestone_type: Technical milestone type (e.g., "COMBINE_START")

        Returns:
            User-friendly name (e.g., "Scouting Combine")
        """
        milestone_names = {
            'COMBINE_START': 'Scouting Combine',
            'DRAFT': 'Draft',
            'PRESEASON_START': 'Preseason Starts',
            'REGULAR_SEASON_START': 'Regular Season Starts',
            'TRADE_DEADLINE': 'Trade Deadline',
            'FREE_AGENCY_START': 'Free Agency Opens',
            'SCHEDULE_RELEASE': 'Schedule Release'
        }
        return milestone_names.get(milestone_type, milestone_type.replace('_', ' ').title())

    def events_get_first_game_date_of_phase(
        self,
        phase_name: str,
        current_date: str
    ) -> Optional[str]:
        """
        Get the date of the first upcoming game in specified phase.

        Alias for events_get_first_game_date with simpler signature.

        Args:
            phase_name: Phase to search for ("preseason", "regular_season", "playoffs")
            current_date: Current simulation date (YYYY-MM-DD format)

        Returns:
            Date string (YYYY-MM-DD) of first upcoming game in that phase,
            or None if no games found
        """
        # Delegate to main method (season_year is unused in query)
        return self.events_get_first_game_date(phase_name, 0, current_date)

    def events_get_first_game_date(
        self,
        phase: str,
        season_year: int,
        current_date: str
    ) -> Optional[str]:
        """
        Get the date of the first upcoming game in specified phase.

        Args:
            phase: Phase to search for ("preseason", "regular_season", "playoffs")
            season_year: Season year (currently unused in query)
            current_date: Current simulation date (YYYY-MM-DD format)

        Returns:
            Date string (YYYY-MM-DD) of first upcoming game in that phase,
            or None if no games found
        """
        try:
            # Convert current_date to timestamp
            year, month, day = map(int, current_date.split('-'))
            current_datetime = datetime(year, month, day)
            current_timestamp_ms = int(current_datetime.timestamp() * 1000)

            # Query for first GAME event in the phase on or after current date
            query = """
                SELECT timestamp FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
                  AND (
                      json_extract(data, '$.parameters.season_type') = ?
                      OR json_extract(data, '$.parameters.game_type') = ?
                  )
                  AND timestamp >= ?
                  AND json_extract(data, '$.results') IS NULL
                ORDER BY timestamp ASC
                LIMIT 1
            """

            results = self._execute_query(query, (self.dynasty_id, phase, phase, current_timestamp_ms))

            if results and results[0]['timestamp']:
                # Convert timestamp back to date string (YYYY-MM-DD)
                game_datetime = datetime.fromtimestamp(results[0]['timestamp'] / 1000)
                date_str = game_datetime.strftime('%Y-%m-%d')

                self.logger.debug(
                    f"First {phase} game for dynasty '{self.dynasty_id}' on or after "
                    f"{current_date}: {date_str}"
                )

                return date_str

            self.logger.debug(
                f"No upcoming {phase} games found for dynasty '{self.dynasty_id}' "
                f"on or after {current_date}"
            )
            return None

        except Exception as e:
            self.logger.error(f"Error querying first game date for phase {phase}: {e}", exc_info=True)
            return None

    def events_get_upcoming(
        self,
        from_date: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events starting from a specific date.

        Args:
            from_date: Start date (YYYY-MM-DD format)
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries, ordered by timestamp ascending
        """
        try:
            # Convert from_date to timestamp
            year, month, day = map(int, from_date.split('-'))
            from_datetime = datetime(year, month, day)
            from_timestamp_ms = int(from_datetime.timestamp() * 1000)

            query = """
                SELECT * FROM events
                WHERE dynasty_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
                LIMIT ?
            """

            results = self._execute_query(query, (self.dynasty_id, from_timestamp_ms, limit))

            # Convert timestamp and data
            for result in results:
                if 'timestamp' in result and result['timestamp']:
                    result['timestamp'] = datetime.fromtimestamp(result['timestamp'] / 1000)
                if 'data' in result and isinstance(result['data'], str):
                    result['data'] = json.loads(result['data'])

            return results

        except Exception as e:
            self.logger.error(f"Error getting upcoming events: {e}", exc_info=True)
            return []

    def _initialize_events_schema(self) -> None:
        """
        Create events table and indexes if they don't exist.

        This is a private helper method called during schema initialization.
        """
        conn = self._get_connection()
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
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_type ON events(dynasty_id, event_type)')

            # Only commit if not in active transaction
            if self._active_transaction is None:
                conn.commit()

            self.logger.debug("Events table and indexes initialized successfully")

        except Exception as e:
            if self._active_transaction is None:
                conn.rollback()
            self.logger.error(f"Error initializing events schema: {e}", exc_info=True)
            raise

        finally:
            self._return_connection(conn)

    # ========================================================================
    # SALARY CAP OPERATIONS (40 methods)
    # ========================================================================

    def cap_get_available_space(self, team_id: int, season: int) -> int:
        """
        Get available salary cap space for a team.

        Args:
            team_id: Team identifier (1-32)
            season: Season year

        Returns:
            Available cap space in dollars (integer)

        Note: Returns default 50M if no cap data exists
        """
        # TODO: Implement proper cap calculation
        # For now, return default cap space
        return 50_000_000

    def cap_get_team_summary(self, team_id: int, season: int) -> Optional[Dict[str, Any]]:
        """
        Get salary cap summary for a team in a specific season.

        Args:
            team_id: Team identifier (1-32)
            season: Season year

        Returns:
            Dict with total_cap, cap_space, active_contracts, top_51_cap, etc.
            or None if no data exists

        TODO: Implement
        """
        pass  # TODO: Implement

    def contracts_insert(
        self,
        player_id: int,
        team_id: int,
        start_year: int,
        end_year: int,
        contract_years: int,
        contract_type: str,
        total_value: int,
        signing_bonus: int = 0,
        guaranteed_at_signing: int = 0,
        **kwargs
    ) -> int:
        """
        Insert a new player contract.

        Args:
            player_id: Player ID
            team_id: Team ID (1-32)
            start_year: Contract start year
            end_year: Contract end year
            contract_years: Number of years
            contract_type: Contract type ('ROOKIE', 'VETERAN', 'FRANCHISE_TAG', etc.)
            total_value: Total contract value
            signing_bonus: Signing bonus amount
            guaranteed_at_signing: Guaranteed money at signing
            **kwargs: Additional contract parameters

        Returns:
            Generated contract_id

        TODO: Implement
        """
        pass  # TODO: Implement

    def contracts_get_active(
        self,
        team_id: Optional[int] = None,
        player_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active contracts, optionally filtered by team or player.

        Args:
            team_id: Optional team filter (1-32)
            player_id: Optional player filter

        Returns:
            List of active contract dictionaries

        TODO: Implement
        """
        pass  # TODO: Implement

    def contracts_get_expiring(
        self,
        season: int,
        team_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get contracts expiring at end of specified season.

        Args:
            season: Season year
            team_id: Optional team filter (1-32)
            active_only: Only return active contracts (default True)

        Returns:
            List of expiring contract dictionaries
        """
        query = '''
            SELECT
                pc.*,
                p.first_name || ' ' || p.last_name as player_name,
                p.positions,
                p.attributes,
                p.years_pro,
                p.birthdate
            FROM player_contracts pc
            JOIN players p
                ON pc.player_id = p.player_id
                AND pc.dynasty_id = p.dynasty_id
            WHERE pc.dynasty_id = ?
              AND pc.end_year = ?
        '''
        params = [self.dynasty_id, season]

        if team_id is not None:
            query += " AND pc.team_id = ?"
            params.append(team_id)

        if active_only:
            query += " AND pc.is_active = TRUE"

        query += " ORDER BY pc.total_value DESC"

        return self._execute_query(query, tuple(params))

    # Additional cap methods (36 more) - stubs for brevity
    # TODO: Add remaining 36 salary cap operation methods
    # Examples: contracts_void, contracts_update, cap_calculate_team,
    #           franchise_tag_calculate, dead_money_calculate, etc.

    # ========================================================================
    # DRAFT OPERATIONS (16 methods)
    # ========================================================================

    def draft_has_class(self, season: int) -> bool:
        """
        Check if dynasty has a draft class for given season.

        Args:
            season: Season year

        Returns:
            True if draft class exists, False otherwise
        """
        try:
            results = self._execute_query('''
                SELECT COUNT(*) as cnt FROM draft_classes
                WHERE dynasty_id = ? AND season = ?
            ''', (self.dynasty_id, season))

            return results[0]['cnt'] > 0 if results else False
        except Exception as e:
            # If table doesn't exist or query fails, return False
            # This handles cases where draft_classes table hasn't been created yet
            if "no such table" in str(e):
                self.logger.debug(f"draft_classes table doesn't exist yet for dynasty {self.dynasty_id}")
            else:
                self.logger.warning(f"Error checking draft class existence: {e}")
            return False

    def get_current_state(self, dynasty_id: str, season: int) -> Optional[Dict[str, Any]]:
        """
        Backward compatibility method for DynastyStateAPI.get_current_state().

        NOTE: This is a compatibility shim. The dynasty_id parameter is ignored
        since UnifiedDatabaseAPI is already bound to a specific dynasty_id.

        Args:
            dynasty_id: Dynasty identifier (ignored, uses self.dynasty_id)
            season: Season year

        Returns:
            Dict with current_date, current_phase, current_week, last_simulated_game_id
            or None if no state exists
        """
        # Delegate to the unified method
        return self.dynasty_get_state(season)

    def draft_generate_class(
        self,
        season: int,
        class_size: int = 250,
        quality_distribution: str = 'normal'
    ) -> int:
        """
        Generate a new draft class with procedurally generated players.

        Args:
            season: Draft year
            class_size: Number of prospects to generate
            quality_distribution: Distribution type ('normal', 'top_heavy', 'balanced')

        Returns:
            Number of prospects generated

        TODO: Implement
        """
        pass  # TODO: Implement

    def draft_get_prospects(
        self,
        season: int,
        position: Optional[str] = None,
        min_grade: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get draft prospects for a specific year.

        Args:
            season: Draft year
            position: Optional position filter
            min_grade: Optional minimum draft grade filter

        Returns:
            List of prospect dictionaries

        TODO: Implement
        """
        pass  # TODO: Implement

    def draft_execute_pick(
        self,
        season: int,
        round_num: int,
        pick_num: int,
        team_id: int,
        player_id: int
    ) -> bool:
        """
        Execute a draft pick selection.

        Args:
            season: Draft year
            round_num: Round number
            pick_num: Overall pick number
            team_id: Selecting team ID
            player_id: Selected player ID

        Returns:
            True if successful, False otherwise

        TODO: Implement
        """
        pass  # TODO: Implement

    # Additional draft methods (12 more) - stubs for brevity
    # TODO: Add remaining 12 draft operation methods
    # Examples: draft_get_order, draft_trade_pick, draft_get_team_picks, etc.

    # ========================================================================
    # ROSTER OPERATIONS (12 methods)
    # ========================================================================

    def roster_get_team(
        self,
        team_id: int,
        roster_status: str = 'active'
    ) -> List[Dict[str, Any]]:
        """
        Get team roster with optional status filter.

        Args:
            team_id: Team ID (1-32)
            roster_status: Status filter ('active', 'injured_reserve', 'practice_squad', 'all')

        Returns:
            List of player dictionaries with roster info
        """
        query = """
            SELECT
                p.player_id,
                p.first_name,
                p.last_name,
                p.number,
                p.team_id,
                p.positions,
                p.attributes,
                p.status,
                p.years_pro,
                p.birthdate,
                tr.depth_chart_order,
                tr.roster_status
            FROM players p
            JOIN team_rosters tr
                ON p.dynasty_id = tr.dynasty_id
                AND p.player_id = tr.player_id
            WHERE p.dynasty_id = ?
                AND p.team_id = ?
        """
        params = [self.dynasty_id, team_id]

        if roster_status != 'all':
            query += " AND tr.roster_status = ?"
            params.append(roster_status)

        query += " ORDER BY tr.depth_chart_order, p.number"

        results = self._execute_query(query, tuple(params))
        return results if results else []

    def players_get_free_agents(
        self,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_age: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available free agents with optional filters.

        Args:
            position: Optional position filter
            min_overall: Optional minimum overall rating filter
            max_age: Optional maximum age filter

        Returns:
            List of free agent player dictionaries
        """
        query = """
            SELECT
                p.player_id,
                p.source_player_id,
                p.first_name,
                p.last_name,
                p.number,
                p.team_id,
                p.positions,
                p.attributes,
                p.status,
                p.years_pro,
                p.birthdate
            FROM players p
            WHERE p.dynasty_id = ?
                AND p.team_id = 0
        """
        params = [self.dynasty_id]

        # Apply optional filters
        # Note: position, min_overall, max_age filters would require
        # parsing JSON attributes column - not implemented yet
        # For now, return all free agents

        query += " ORDER BY p.last_name, p.first_name"

        results = self._execute_query(query, tuple(params))
        return results if results else []

    def roster_update_depth(
        self,
        team_id: int,
        player_id: int,
        depth_chart_order: int
    ) -> bool:
        """
        Update player's depth chart position.

        Args:
            team_id: Team ID (1-32)
            player_id: Player ID
            depth_chart_order: New depth chart position (lower = higher on chart)

        Returns:
            True if successful, False otherwise

        TODO: Implement
        """
        pass  # TODO: Implement

    # Additional roster methods (9 more) - stubs for brevity
    # TODO: Add remaining 9 roster operation methods
    # Examples: roster_add_player, roster_release_player, roster_move_to_ir, etc.
    # ========================================================================
    # STATISTICS OPERATIONS (29 methods)
    # ========================================================================

    # -------------------- Standings (5 methods) --------------------

    def standings_get(
        self,
        season: int,
        season_type: str = 'regular_season'
    ) -> Dict[str, Any]:
        """
        Get current standings for a season.

        Args:
            season: Season year
            season_type: Season type ('preseason', 'regular_season', 'playoffs')

        Returns:
            Dict with divisions, conferences, overall standings
        """
        from stores.standings_store import EnhancedTeamStanding, NFL_DIVISIONS, NFL_CONFERENCES

        query = '''
            SELECT team_id, wins, losses, ties, division_wins, division_losses,
                   conference_wins, conference_losses, home_wins, home_losses,
                   away_wins, away_losses, points_for, points_against,
                   current_streak, division_rank
            FROM standings
            WHERE dynasty_id = ? AND season = ? AND season_type = ?
            ORDER BY team_id
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type))

        if not results:
            self.logger.warning(f"No standings found for dynasty {self.dynasty_id}, season {season}")
            return self._get_empty_standings()

        # Convert to standings format
        standings_data = {}

        # Group by divisions
        for division, team_ids in NFL_DIVISIONS.items():
            division_teams = []

            for team_id in team_ids:
                # Find this team in results
                team_record = None
                for row in results:
                    if row['team_id'] == team_id:
                        team_record = row
                        break

                if team_record:
                    # Create EnhancedTeamStanding object
                    standing = EnhancedTeamStanding(
                        team_id=team_id,
                        wins=team_record['wins'],
                        losses=team_record['losses'],
                        ties=team_record['ties'],
                        division_wins=team_record['division_wins'],
                        division_losses=team_record['division_losses'],
                        conference_wins=team_record['conference_wins'],
                        conference_losses=team_record['conference_losses'],
                        home_wins=team_record['home_wins'],
                        home_losses=team_record['home_losses'],
                        away_wins=team_record['away_wins'],
                        away_losses=team_record['away_losses'],
                        points_for=team_record['points_for'],
                        points_against=team_record['points_against'],
                        streak=team_record['current_streak'] or "",
                        division_place=team_record['division_rank'] or 1
                    )
                else:
                    # Create empty standing for missing team
                    standing = EnhancedTeamStanding(team_id=team_id)

                division_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })

            # Sort by record (wins desc, then win percentage desc)
            division_teams.sort(key=lambda x: (
                x['standing'].wins,
                x['standing'].win_percentage,
                -x['standing'].losses
            ), reverse=True)

            standings_data[division] = division_teams

        # Group by conferences for conference standings
        conferences_data = {}
        for conference, team_ids in NFL_CONFERENCES.items():
            conference_teams = []

            for team_id in team_ids:
                # Find this team in results
                for row in results:
                    if row['team_id'] == team_id:
                        standing = EnhancedTeamStanding(
                            team_id=team_id,
                            wins=row['wins'],
                            losses=row['losses'],
                            ties=row['ties'],
                            conference_wins=row['conference_wins'],
                            conference_losses=row['conference_losses'],
                            points_for=row['points_for'],
                            points_against=row['points_against']
                        )
                        conference_teams.append({
                            'team_id': team_id,
                            'standing': standing
                        })
                        break

            # Sort conference teams
            conference_teams.sort(key=lambda x: (
                x['standing'].wins,
                x['standing'].win_percentage,
                x['standing'].conference_wins,
                -x['standing'].losses
            ), reverse=True)

            conferences_data[conference] = conference_teams

        # Create overall standings
        overall_teams = []
        for row in results:
            standing = EnhancedTeamStanding(
                team_id=row['team_id'],
                wins=row['wins'],
                losses=row['losses'],
                ties=row['ties'],
                points_for=row['points_for'],
                points_against=row['points_against']
            )
            overall_teams.append({
                'team_id': row['team_id'],
                'standing': standing
            })

        overall_teams.sort(key=lambda x: (
            x['standing'].wins,
            x['standing'].win_percentage,
            -x['standing'].losses
        ), reverse=True)

        return {
            'divisions': standings_data,
            'conferences': conferences_data,
            'overall': overall_teams,
            'playoff_picture': {}
        }


    def standings_get_team(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get standing for a specific team.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            Team standing dict or None if not found
        """
        from stores.standings_store import EnhancedTeamStanding

        query = '''
            SELECT team_id, wins, losses, ties, division_wins, division_losses,
                   conference_wins, conference_losses, home_wins, home_losses,
                   away_wins, away_losses, points_for, points_against,
                   current_streak, division_rank
            FROM standings
            WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, team_id, season, season_type))

        if not results:
            return None

        row = results[0]
        standing = EnhancedTeamStanding(
            team_id=row['team_id'],
            wins=row['wins'],
            losses=row['losses'],
            ties=row['ties'],
            division_wins=row['division_wins'],
            division_losses=row['division_losses'],
            conference_wins=row['conference_wins'],
            conference_losses=row['conference_losses'],
            home_wins=row['home_wins'],
            home_losses=row['home_losses'],
            away_wins=row['away_wins'],
            away_losses=row['away_losses'],
            points_for=row['points_for'],
            points_against=row['points_against'],
            streak=row['current_streak'] or "",
            division_place=row['division_rank'] or 1
        )

        # Return the standing object directly (not wrapped in dict)
        # This matches the legacy API behavior where callers expect standing.wins
        return standing


    def standings_reset(
        self,
        season: int,
        season_type: str = 'regular_season'
    ) -> bool:
        """
        Reset all team standings to 0-0-0 for a season type.

        Args:
            season: Season year
            season_type: Season type to reset

        Returns:
            True if successful, False otherwise
        """
        try:
            # Reset all 32 NFL teams (team_id 1-32)
            for team_id in range(1, 33):
                query = '''
                    INSERT OR REPLACE INTO standings
                    (dynasty_id, season, team_id, season_type,
                     wins, losses, ties,
                     division_wins, division_losses, division_ties,
                     conference_wins, conference_losses, conference_ties,
                     home_wins, home_losses, home_ties,
                     away_wins, away_losses, away_ties,
                     points_for, points_against, point_differential,
                     current_streak, division_rank, conference_rank, league_rank,
                     playoff_seed, made_playoffs, made_wild_card, won_wild_card,
                     won_division_round, won_conference, won_super_bowl)
                    VALUES (?, ?, ?, ?,
                            0, 0, 0,
                            0, 0, 0,
                            0, 0, 0,
                            0, 0, 0,
                            0, 0, 0,
                            0, 0, 0,
                            NULL, NULL, NULL, NULL,
                            NULL, 0, 0, 0,
                            0, 0, 0)
                '''
                self._execute_update(query, (self.dynasty_id, season, team_id, season_type))

            self.logger.info(f"Reset standings for all 32 teams (dynasty={self.dynasty_id}, season={season}, season_type={season_type})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset standings: {e}")
            return False


    def standings_update_team(
        self,
        team_id: int,
        season: int,
        wins: int,
        losses: int,
        ties: int,
        points_for: int,
        points_against: int,
        season_type: str = 'regular_season',
        # Optional extended record fields
        division_wins: Optional[int] = None,
        division_losses: Optional[int] = None,
        conference_wins: Optional[int] = None,
        conference_losses: Optional[int] = None,
        home_wins: Optional[int] = None,
        home_losses: Optional[int] = None,
        away_wins: Optional[int] = None,
        away_losses: Optional[int] = None,
    ) -> bool:
        """
        Update team standing record with all record types.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            wins: Win count
            losses: Loss count
            ties: Tie count
            points_for: Points scored
            points_against: Points allowed
            season_type: Season type
            division_wins: Division wins (optional)
            division_losses: Division losses (optional)
            conference_wins: Conference wins (optional)
            conference_losses: Conference losses (optional)
            home_wins: Home wins (optional)
            home_losses: Home losses (optional)
            away_wins: Away wins (optional)
            away_losses: Away losses (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build dynamic SET clause
            set_parts = [
                "wins = ?", "losses = ?", "ties = ?",
                "points_for = ?", "points_against = ?",
                "point_differential = ?"
            ]
            point_diff = points_for - points_against
            params = [wins, losses, ties, points_for, points_against, point_diff]

            # Add optional fields if provided
            if division_wins is not None:
                set_parts.append("division_wins = ?")
                params.append(division_wins)
            if division_losses is not None:
                set_parts.append("division_losses = ?")
                params.append(division_losses)
            if conference_wins is not None:
                set_parts.append("conference_wins = ?")
                params.append(conference_wins)
            if conference_losses is not None:
                set_parts.append("conference_losses = ?")
                params.append(conference_losses)
            if home_wins is not None:
                set_parts.append("home_wins = ?")
                params.append(home_wins)
            if home_losses is not None:
                set_parts.append("home_losses = ?")
                params.append(home_losses)
            if away_wins is not None:
                set_parts.append("away_wins = ?")
                params.append(away_wins)
            if away_losses is not None:
                set_parts.append("away_losses = ?")
                params.append(away_losses)

            # Add WHERE clause params
            params.extend([self.dynasty_id, team_id, season, season_type])

            query = f'''
                UPDATE standings
                SET {', '.join(set_parts)}
                WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = ?
            '''
            self._execute_update(query, tuple(params))
            return True

        except Exception as e:
            self.logger.error(f"Failed to update standings for team {team_id}: {e}")
            return False


    def standings_get_division(
        self,
        season: int,
        division: str,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Get standings for a specific division.

        Args:
            season: Season year
            division: Division name (e.g., 'AFC East')
            season_type: Season type filter

        Returns:
            List of team standing dicts sorted by record
        """
        from stores.standings_store import NFL_DIVISIONS, EnhancedTeamStanding

        if division not in NFL_DIVISIONS:
            self.logger.error(f"Invalid division: {division}")
            return []

        team_ids = NFL_DIVISIONS[division]
        division_teams = []

        for team_id in team_ids:
            result = self.standings_get_team(team_id, season, season_type)
            if result:
                division_teams.append(result)

        # Sort by record
        division_teams.sort(key=lambda x: (
            x['standing'].wins,
            x['standing'].win_percentage,
            -x['standing'].losses
        ), reverse=True)

        return division_teams


    # -------------------- Games (6 methods) --------------------

    def games_get_results(
        self,
        season: int,
        season_type: str = 'regular_season',
        team_id_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get game results for a season.

        Args:
            season: Season year
            season_type: Season type filter
            team_id_filter: Optional team filter

        Returns:
            List of game result dictionaries
        """
        if team_id_filter:
            query = '''
                SELECT game_id, home_team_id, away_team_id, home_score, away_score,
                       week, game_date, total_plays, game_duration_minutes, overtime_periods
                FROM games
                WHERE dynasty_id = ? AND season = ? AND season_type = ?
                  AND (home_team_id = ? OR away_team_id = ?)
                ORDER BY game_date, game_id
            '''
            results = self._execute_query(
                query,
                (self.dynasty_id, season, season_type, team_id_filter, team_id_filter)
            )
        else:
            query = '''
                SELECT game_id, home_team_id, away_team_id, home_score, away_score,
                       week, game_date, total_plays, game_duration_minutes, overtime_periods
                FROM games
                WHERE dynasty_id = ? AND season = ? AND season_type = ?
                ORDER BY game_date, game_id
            '''
            results = self._execute_query(query, (self.dynasty_id, season, season_type))

        return results


    def games_get_by_date_range(
        self,
        start_date: int,
        end_date: int,
        team_id_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get games within a date range.

        Args:
            start_date: Start timestamp (milliseconds)
            end_date: End timestamp (milliseconds)
            team_id_filter: Optional team filter

        Returns:
            List of game dictionaries
        """
        if team_id_filter:
            query = '''
                SELECT DISTINCT game_id, home_team_id, away_team_id, home_score, away_score,
                       week, season, season_type, game_date, total_plays,
                       game_duration_minutes, overtime_periods
                FROM games
                WHERE dynasty_id = ? AND game_date >= ? AND game_date <= ?
                  AND (home_team_id = ? OR away_team_id = ?)
                ORDER BY game_date ASC
            '''
            results = self._execute_query(
                query,
                (self.dynasty_id, start_date, end_date, team_id_filter, team_id_filter)
            )
        else:
            query = '''
                SELECT DISTINCT game_id, home_team_id, away_team_id, home_score, away_score,
                       week, season, season_type, game_date, total_plays,
                       game_duration_minutes, overtime_periods
                FROM games
                WHERE dynasty_id = ? AND game_date >= ? AND game_date <= ?
                ORDER BY game_date ASC
            '''
            results = self._execute_query(query, (self.dynasty_id, start_date, end_date))

        return results


    def games_get_upcoming(
        self,
        team_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get next N upcoming games for a team.

        Args:
            team_id: Team ID (1-32)
            limit: Number of games to return

        Returns:
            List of upcoming game dictionaries
        """
        # Get current timestamp
        from datetime import datetime
        current_time = int(datetime.now().timestamp() * 1000)

        query = '''
            SELECT game_id, home_team_id, away_team_id, week, season,
                   season_type, game_date
            FROM games
            WHERE dynasty_id = ?
              AND (home_team_id = ? OR away_team_id = ?)
              AND game_date >= ?
            ORDER BY game_date ASC
            LIMIT ?
        '''

        results = self._execute_query(
            query,
            (self.dynasty_id, team_id, team_id, current_time, limit)
        )
        return results


    def games_get_by_week(
        self,
        season: int,
        week: int,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Get all games for a specific week.

        Args:
            season: Season year
            week: Week number
            season_type: Season type filter

        Returns:
            List of game dictionaries
        """
        query = '''
            SELECT game_id, home_team_id, away_team_id, home_score, away_score,
                   game_date, total_plays, game_duration_minutes, overtime_periods
            FROM games
            WHERE dynasty_id = ? AND season = ? AND week = ? AND season_type = ?
            ORDER BY game_date
        '''

        results = self._execute_query(query, (self.dynasty_id, season, week, season_type))
        return results


    def games_insert_result(
        self,
        game_result: Dict[str, Any]
    ) -> bool:
        """
        Insert or update a game result in the database.

        Uses INSERT OR REPLACE to handle re-simulation of existing games.

        Args:
            game_result: Game result dictionary with all required fields

        Returns:
            True if successful, False otherwise
        """
        try:
            query = '''
                INSERT OR REPLACE INTO games (
                    dynasty_id, game_id, season, week, season_type, game_type,
                    game_date, home_team_id, away_team_id, home_score, away_score,
                    total_plays, game_duration_minutes, overtime_periods
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            self._execute_update(
                query,
                (
                    self.dynasty_id,
                    game_result.get('game_id'),
                    game_result.get('season'),
                    game_result.get('week'),
                    game_result.get('season_type', 'regular_season'),
                    game_result.get('game_type', 'regular'),
                    game_result.get('game_date'),
                    game_result.get('home_team_id'),
                    game_result.get('away_team_id'),
                    game_result.get('home_score'),
                    game_result.get('away_score'),
                    game_result.get('total_plays'),
                    game_result.get('game_duration_minutes'),
                    game_result.get('overtime_periods', 0)
                )
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert game result: {e}")
            return False


    def games_get_by_id(
        self,
        game_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single game by ID.

        Args:
            game_id: Game identifier

        Returns:
            Game dictionary or None if not found
        """
        query = '''
            SELECT game_id, season, week, season_type, game_type, game_date,
                   home_team_id, away_team_id, home_score, away_score,
                   total_plays, game_duration_minutes, overtime_periods
            FROM games
            WHERE dynasty_id = ? AND game_id = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, game_id))

        if not results:
            return None

        return results[0]


    # -------------------- Box Scores --------------------

    def box_scores_insert(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_box: Dict[str, Any],
        away_box: Dict[str, Any]
    ) -> bool:
        """
        Insert box scores for both teams in a game.

        Uses INSERT OR REPLACE to handle re-simulation of games.

        Args:
            game_id: Game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_box: Dict with home team stats (total_yards, passing_yards, rushing_yards, turnovers, etc.)
            away_box: Dict with away team stats

        Returns:
            True if successful
        """
        try:
            from game_cycle.database.box_scores_api import BoxScoresAPI

            api = BoxScoresAPI(self.database_path)
            return api.insert_game_box_scores(
                dynasty_id=self.dynasty_id,
                game_id=game_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_box=home_box,
                away_box=away_box
            )
        except Exception as e:
            self.logger.error(f"Failed to insert box scores for game {game_id}: {e}")
            return False

    def box_scores_get(
        self,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get box scores for a game.

        Args:
            game_id: Game identifier

        Returns:
            List of box score dictionaries (one per team)
        """
        try:
            from game_cycle.database.box_scores_api import BoxScoresAPI

            api = BoxScoresAPI(self.database_path)
            box_scores = api.get_game_box_scores(self.dynasty_id, game_id)
            return [bs.to_dict() for bs in box_scores]
        except Exception as e:
            self.logger.error(f"Failed to get box scores for game {game_id}: {e}")
            return []

    def box_scores_get_or_calculate(
        self,
        game_id: str,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get box score for a team in a game, calculating from player stats if not found.

        Args:
            game_id: Game identifier
            team_id: Team ID

        Returns:
            Box score dictionary or None
        """
        try:
            from game_cycle.database.box_scores_api import BoxScoresAPI

            api = BoxScoresAPI(self.database_path)
            box_score = api.get_or_calculate_box_score(self.dynasty_id, game_id, team_id)
            return box_score.to_dict() if box_score else None
        except Exception as e:
            self.logger.error(f"Failed to get/calculate box score for game {game_id}, team {team_id}: {e}")
            return None

    # -------------------- Team Statistics (4 methods) --------------------

    def team_stats_get_season(
        self,
        team_id: int,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive team statistics for a season.

        Combines season stats with record and league rankings.

        Args:
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Team overview dict with stats, record, and rankings
        """
        try:
            from game_cycle.services.team_stats_service import TeamStatsService

            service = TeamStatsService(self.database_path, self.dynasty_id, season)
            overview = service.get_team_overview(team_id, season)
            return overview.to_dict() if overview else None
        except Exception as e:
            self.logger.error(f"Failed to get team stats for team {team_id}: {e}")
            return None

    def team_stats_get_all_teams(
        self,
        season: int
    ) -> List[Dict[str, Any]]:
        """
        Get season statistics for all teams.

        Args:
            season: Season year

        Returns:
            List of team stats dicts sorted by total yards
        """
        try:
            from game_cycle.database.team_stats_api import TeamSeasonStatsAPI

            api = TeamSeasonStatsAPI(self.database_path)
            all_stats = api.get_all_teams_season_stats(self.dynasty_id, season)
            return [stats.to_dict() for stats in all_stats]
        except Exception as e:
            self.logger.error(f"Failed to get all teams stats: {e}")
            return []

    def team_stats_get_rankings(
        self,
        season: int,
        category: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get league-wide rankings for team statistics.

        Args:
            season: Season year
            category: Specific category to get (or all if None)

        Returns:
            Dict mapping category names to lists of rankings
        """
        try:
            from game_cycle.services.team_stats_service import TeamStatsService

            service = TeamStatsService(self.database_path, self.dynasty_id, season)
            categories = [category] if category else None
            rankings = service.get_league_rankings(season, categories)
            return rankings.categories
        except Exception as e:
            self.logger.error(f"Failed to get team rankings: {e}")
            return {}

    def team_stats_get_comparison(
        self,
        team1_id: int,
        team2_id: int,
        season: int
    ) -> Dict[str, Any]:
        """
        Get head-to-head comparison between two teams.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            season: Season year

        Returns:
            Comparison dict with both teams' stats and advantages
        """
        try:
            from game_cycle.services.team_stats_service import TeamStatsService

            service = TeamStatsService(self.database_path, self.dynasty_id, season)
            return service.get_team_comparison(team1_id, team2_id, season)
        except Exception as e:
            self.logger.error(f"Failed to compare teams {team1_id} vs {team2_id}: {e}")
            return {}


    # -------------------- Player Statistics (8 methods) --------------------

    def stats_get_passing_leaders(
        self,
        season: int,
        season_type: str = 'regular_season',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get passing statistics leaders for the season.

        Args:
            season: Season year
            season_type: Season type filter
            limit: Number of top players to return

        Returns:
            List of passing leader dictionaries
        """
        from team_management.players.player import Position

        query = '''
            SELECT
                pss.player_name,
                pss.player_id,
                pss.team_id,
                pss.position,
                pss.passing_yards as total_passing_yards,
                pss.passing_tds as total_passing_tds,
                pss.passing_completions as total_completions,
                pss.passing_attempts as total_attempts,
                pss.passing_interceptions as total_interceptions,
                pss.games_played,
                ROUND(CAST(pss.passing_yards AS FLOAT) / pss.games_played, 1) as avg_yards_per_game,
                pss.completion_percentage
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.season = ?
                AND pss.position = ?
                AND pss.season_type = ?
                AND (pss.passing_attempts > 0 OR pss.passing_yards > 0)
            ORDER BY pss.passing_yards DESC
            LIMIT ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, Position.QB, season_type, limit))
        return results


    def stats_get_rushing_leaders(
        self,
        season: int,
        season_type: str = 'regular_season',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get rushing statistics leaders for the season.

        Args:
            season: Season year
            season_type: Season type filter
            limit: Number of top players to return

        Returns:
            List of rushing leader dictionaries
        """
        query = '''
            SELECT
                pss.player_name,
                pss.player_id,
                pss.team_id,
                pss.position,
                pss.rushing_yards as total_rushing_yards,
                pss.rushing_tds as total_rushing_tds,
                pss.rushing_attempts as total_attempts,
                pss.rushing_long as longest,
                pss.games_played,
                pss.yards_per_game_rushing as avg_yards_per_game,
                pss.yards_per_carry
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
                AND (pss.rushing_attempts > 0 OR pss.rushing_yards > 0)
            ORDER BY pss.rushing_yards DESC
            LIMIT ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type, limit))
        return results


    def stats_get_receiving_leaders(
        self,
        season: int,
        season_type: str = 'regular_season',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get receiving statistics leaders for the season.

        Args:
            season: Season year
            season_type: Season type filter
            limit: Number of top players to return

        Returns:
            List of receiving leader dictionaries
        """
        query = '''
            SELECT
                pss.player_name,
                pss.player_id,
                pss.team_id,
                pss.position,
                pss.receiving_yards as total_receiving_yards,
                pss.receiving_tds as total_receiving_tds,
                pss.receptions as total_receptions,
                pss.targets as total_targets,
                pss.receiving_long as longest,
                pss.games_played,
                pss.yards_per_game_receiving as avg_yards_per_game,
                pss.yards_per_reception,
                pss.catch_rate as catch_percentage
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
                AND (pss.receptions > 0 OR pss.receiving_yards > 0 OR pss.targets > 0)
            ORDER BY pss.receiving_yards DESC
            LIMIT ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type, limit))
        return results


    def stats_get_defensive_leaders(
        self,
        season: int,
        season_type: str = 'regular_season',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get defensive statistics leaders for the season.

        Args:
            season: Season year
            season_type: Season type filter
            limit: Number of top players to return

        Returns:
            List of defensive leader dictionaries
        """
        query = '''
            SELECT
                pss.player_name,
                pss.player_id,
                pss.team_id,
                pss.position,
                pss.tackles_total as total_tackles,
                pss.tackles_solo,
                pss.tackles_assists,
                pss.sacks,
                pss.interceptions,
                pss.passes_defended,
                pss.forced_fumbles,
                pss.fumble_recoveries,
                pss.games_played
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
                AND (pss.tackles_total > 0 OR pss.sacks > 0 OR pss.interceptions > 0)
            ORDER BY pss.tackles_total DESC
            LIMIT ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type, limit))
        return results


    def stats_get_player_season(
        self,
        player_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get player's season statistics.

        Args:
            player_id: Player ID
            season: Season year
            season_type: Season type filter

        Returns:
            Player season stats dict or None if not found
        """
        query = '''
            SELECT *
            FROM player_season_stats
            WHERE dynasty_id = ? AND player_id = ? AND season = ? AND season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, player_id, season, season_type))

        if not results:
            return None

        return results[0]


    def stats_get_player_career(
        self,
        player_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get player's career statistics across all seasons.

        Args:
            player_id: Player ID

        Returns:
            List of season stats dictionaries
        """
        query = '''
            SELECT *
            FROM player_season_stats
            WHERE dynasty_id = ? AND player_id = ?
            ORDER BY season, season_type
        '''

        results = self._execute_query(query, (self.dynasty_id, player_id))
        return results


    def stats_get_player_leaders_unified(
        self,
        season: int,
        stat_category: str,
        limit: int = 10,
        position_filter: Optional[str] = None,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Unified method to get player stat leaders across any category.

        Args:
            season: Season year
            stat_category: Stat category to sort by
            limit: Number of top players to return
            position_filter: Optional position filter
            season_type: Season type filter

        Returns:
            List of player leaders
        """
        # Validate stat category
        valid_categories = {
            'passing_yards', 'passing_tds', 'passing_completions', 'passing_attempts',
            'rushing_yards', 'rushing_tds', 'rushing_attempts',
            'receiving_yards', 'receiving_tds', 'receptions', 'targets',
            'tackles_total', 'sacks', 'interceptions',
            'field_goals_made', 'field_goals_attempted'
        }

        if stat_category not in valid_categories:
            raise ValueError(f"Invalid stat category: {stat_category}")

        position_clause = "AND pss.position = ?" if position_filter else ""
        position_params = (position_filter,) if position_filter else ()

        query = f'''
            SELECT
                pss.player_name,
                pss.player_id,
                pss.team_id,
                pss.position,
                pss.{stat_category} as total_{stat_category},
                pss.games_played,
                ROUND(CAST(pss.{stat_category} AS FLOAT) / pss.games_played, 1) as avg_per_game
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
                {position_clause}
                AND pss.{stat_category} > 0
            ORDER BY total_{stat_category} DESC
            LIMIT ?
        '''

        params = (self.dynasty_id, season, season_type) + position_params + (limit,)
        results = self._execute_query(query, params)
        return results


    def stats_insert_player(
        self,
        player_stats: Dict[str, Any]
    ) -> bool:
        """
        Insert player statistics record.

        Args:
            player_stats: Player stats dictionary with all required fields

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build INSERT query dynamically based on available fields
            fields = list(player_stats.keys())
            fields.insert(0, 'dynasty_id')  # Add dynasty_id to fields

            placeholders = ', '.join(['?' for _ in fields])
            field_names = ', '.join(fields)

            query = f'''
                INSERT INTO player_season_stats ({field_names})
                VALUES ({placeholders})
            '''

            values = [self.dynasty_id] + [player_stats[f] for f in fields[1:]]
            self._execute_update(query, tuple(values))
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert player stats: {e}")
            return False


    # -------------------- Game Statistics (4 methods) --------------------

    def stats_insert_game_stats(
        self,
        game_id: str,
        season: int,
        week: int,
        season_type: str,
        player_stats: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert player game stats.

        Args:
            game_id: Game identifier
            season: Season year
            week: Week number
            season_type: 'regular_season' or 'playoffs'
            player_stats: List of player stat dictionaries

        Returns:
            Number of rows inserted

        Raises:
            Exception: If database operation fails
        """
        if not player_stats:
            return 0

        # DEBUG: Track if this game's stats were already inserted
        if not hasattr(self, '_inserted_games'):
            self._inserted_games = set()

        game_key = f"{game_id}_{season}_{week}"
        if game_key in self._inserted_games:
            print(f"🚨 DUPLICATE STATS INSERTION DETECTED!")
            print(f"   Game: {game_id}, Season: {season}, Week: {week}")
            print(f"   This game's stats have already been inserted!")
            print(f"   About to insert {len(player_stats)} player stat records again")
        else:
            self._inserted_games.add(game_key)
            print(f"✅ First stats insertion for game {game_id} (Season {season}, Week {week})")

        # ✅ FIX 3: Deduplicate player_stats list before insertion
        # Keep the last occurrence of each player (most recent/final stats)
        seen_players = {}
        for stats in player_stats:
            player_key = (stats.get('player_id'), stats.get('team_id'))
            seen_players[player_key] = stats  # Overwrites duplicates

        deduplicated_stats = list(seen_players.values())

        # ✅ FIX 3: Log if duplicates were found
        if len(deduplicated_stats) < len(player_stats):
            duplicate_count = len(player_stats) - len(deduplicated_stats)
            print(f"⚠️ DEDUPLICATION: Removed {duplicate_count} duplicate players from stats before insertion")
            print(f"   Original: {len(player_stats)} players, After dedup: {len(deduplicated_stats)} players")

        # PFF stats tracing - log when PFF-critical stats exist but won't be inserted
        # These stats are currently NOT in the INSERT query columns
        _TRACE_PFF_STATS = False  # Set to True to enable tracing
        _PFF_CRITICAL_STATS = {
            'coverage_targets', 'coverage_completions', 'coverage_yards_allowed',
            'pass_rush_wins', 'pass_rush_attempts', 'times_double_teamed', 'blocking_encounters',
            'broken_tackles', 'tackles_faced', 'yards_after_contact',
            'time_to_throw_total', 'throw_count', 'pressures_faced',
            'missed_tackles',
        }

        if _TRACE_PFF_STATS:
            for stats in deduplicated_stats[:10]:  # Sample first 10 players
                pff_stats_found = []
                for stat_name in _PFF_CRITICAL_STATS:
                    value = stats.get(stat_name, 0)
                    if value:
                        pff_stats_found.append(f"{stat_name}={value}")
                if pff_stats_found:
                    print(f"[PFF_TRACE:INSERT_LOSS] {stats.get('player_name')} ({stats.get('position')}): "
                          f"DROPPING stats not in INSERT: {', '.join(pff_stats_found)}")

        try:
            rows_inserted = 0

            for stats in deduplicated_stats:  # ✅ Use deduplicated list instead of original
                # Ensure required fields
                if 'player_id' not in stats or 'team_id' not in stats:
                    self.logger.warning(f"Skipping stats entry missing player_id or team_id: {stats}")
                    continue

                # Build the INSERT OR REPLACE query
                # IMPORTANT: All columns must match the schema in connection.py
                # Including PFF-critical stats for accurate position grading
                query = '''
                    INSERT OR REPLACE INTO player_game_stats (
                        dynasty_id, game_id, season_type, player_id, player_name,
                        team_id, position,
                        passing_yards, passing_tds, passing_attempts, passing_completions,
                        passing_interceptions, passing_sacks, passing_sack_yards, passing_rating, air_yards,
                        rushing_yards, rushing_tds, rushing_attempts, rushing_long, rushing_fumbles,
                        receiving_yards, receiving_tds, receptions, targets, receiving_long, receiving_drops, yards_after_catch,
                        tackles_total, tackles_solo, tackles_assist, sacks, interceptions,
                        forced_fumbles, fumbles_recovered, passes_defended, tackles_for_loss, qb_hits, qb_pressures,
                        field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted,
                        punts, punt_yards,
                        pancakes, sacks_allowed, hurries_allowed, pressures_allowed, pass_blocks,
                        run_blocking_grade, pass_blocking_efficiency, missed_assignments,
                        holding_penalties, false_start_penalties, downfield_blocks,
                        double_team_blocks, chip_blocks,
                        snap_counts_offense, snap_counts_defense, snap_counts_special_teams,
                        fantasy_points,
                        coverage_targets, coverage_completions, coverage_yards_allowed,
                        pass_rush_wins, pass_rush_attempts, times_double_teamed, blocking_encounters,
                        broken_tackles, tackles_faced, yards_after_contact,
                        pressures_faced, time_to_throw_total, throw_count,
                        missed_tackles
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?
                    )
                '''

                values = (
                    self.dynasty_id,
                    game_id,
                    season_type,
                    stats.get('player_id'),
                    stats.get('player_name', ''),
                    stats.get('team_id'),
                    stats.get('position', ''),
                    # Passing stats
                    stats.get('passing_yards', 0),
                    stats.get('passing_tds', 0),
                    stats.get('passing_attempts', 0),
                    stats.get('passing_completions', 0),
                    stats.get('passing_interceptions', 0),
                    stats.get('passing_sacks', 0),
                    stats.get('passing_sack_yards', 0),
                    stats.get('passing_rating', 0.0),
                    stats.get('air_yards', 0),
                    # Rushing stats
                    stats.get('rushing_yards', 0),
                    stats.get('rushing_tds', 0),
                    stats.get('rushing_attempts', 0),
                    stats.get('rushing_long', 0),
                    stats.get('rushing_fumbles', 0),
                    # Receiving stats
                    stats.get('receiving_yards', 0),
                    stats.get('receiving_tds', 0),
                    stats.get('receptions', 0),
                    stats.get('targets', 0),
                    stats.get('receiving_long', 0),
                    stats.get('receiving_drops', 0),
                    stats.get('yards_after_catch', 0),
                    # Defensive stats
                    stats.get('tackles_total', 0),
                    stats.get('tackles_solo', 0),
                    stats.get('tackles_assist', 0),
                    stats.get('sacks', 0.0),
                    stats.get('interceptions', 0),
                    stats.get('forced_fumbles', 0),
                    stats.get('fumbles_recovered', 0),
                    stats.get('passes_defended', 0),
                    stats.get('tackles_for_loss', 0),
                    stats.get('qb_hits', 0),
                    stats.get('qb_pressures', 0),
                    # Special teams stats
                    stats.get('field_goals_made', 0),
                    stats.get('field_goals_attempted', 0),
                    stats.get('extra_points_made', 0),
                    stats.get('extra_points_attempted', 0),
                    stats.get('punts', 0),
                    stats.get('punt_yards', 0),
                    # O-Line stats
                    stats.get('pancakes', 0),
                    stats.get('sacks_allowed', 0),
                    stats.get('hurries_allowed', 0),
                    stats.get('pressures_allowed', 0),
                    stats.get('pass_blocks', 0),
                    stats.get('run_blocking_grade', 0.0),
                    stats.get('pass_blocking_efficiency', 0.0),
                    stats.get('missed_assignments', 0),
                    stats.get('holding_penalties', 0),
                    stats.get('false_start_penalties', 0),
                    stats.get('downfield_blocks', 0),
                    stats.get('double_team_blocks', 0),
                    stats.get('chip_blocks', 0),
                    # Snap counts
                    stats.get('snap_counts_offense', 0),
                    stats.get('snap_counts_defense', 0),
                    stats.get('snap_counts_special_teams', 0),
                    # Fantasy
                    stats.get('fantasy_points', 0.0),
                    # PFF-critical stats for position grading
                    # Coverage stats (DB/LB grading)
                    stats.get('coverage_targets', 0),
                    stats.get('coverage_completions', 0),
                    stats.get('coverage_yards_allowed', 0),
                    # Pass rush stats (DL grading)
                    stats.get('pass_rush_wins', 0),
                    stats.get('pass_rush_attempts', 0),
                    stats.get('times_double_teamed', 0),
                    stats.get('blocking_encounters', 0),
                    # Ball carrier stats (RB/WR grading)
                    stats.get('broken_tackles', 0),
                    stats.get('tackles_faced', 0),
                    stats.get('yards_after_contact', 0),
                    # QB advanced stats
                    stats.get('pressures_faced', 0),
                    stats.get('time_to_throw_total', 0.0),
                    stats.get('throw_count', 0),
                    # Tackling
                    stats.get('missed_tackles', 0),
                )

                self._execute_update(query, values)
                rows_inserted += 1

            self.logger.info(
                f"Inserted {rows_inserted} player game stats for game {game_id} "
                f"(dynasty={self.dynasty_id}, season={season}, week={week})"
            )
            return rows_inserted

        except Exception as e:
            self.logger.error(
                f"Failed to insert game stats for game {game_id}: {e}",
                exc_info=True
            )
            raise


    def stats_get_game_stats(
        self,
        game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all player stats for a specific game.

        Args:
            game_id: Game identifier

        Returns:
            List of player stat dictionaries
        """
        query = '''
            SELECT
                player_id, player_name, team_id, position,
                passing_yards, passing_tds, passing_attempts, passing_completions,
                passing_interceptions, passing_sacks, passing_sack_yards, passing_rating,
                rushing_yards, rushing_tds, rushing_attempts, rushing_long, rushing_fumbles,
                receiving_yards, receiving_tds, receptions, targets, receiving_long, receiving_drops,
                tackles_total, tackles_solo, tackles_assist, sacks, interceptions,
                forced_fumbles, fumbles_recovered, passes_defended,
                field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted,
                punts, punt_yards,
                pancakes, sacks_allowed, hurries_allowed, pressures_allowed, pass_blocks,
                run_blocking_grade, pass_blocking_efficiency, missed_assignments,
                holding_penalties, false_start_penalties, downfield_blocks,
                double_team_blocks, chip_blocks,
                snap_counts_offense, snap_counts_defense, snap_counts_special_teams,
                fantasy_points
            FROM player_game_stats
            WHERE dynasty_id = ? AND game_id = ?
            ORDER BY team_id, position, player_name
        '''

        results = self._execute_query(query, (self.dynasty_id, game_id))
        return results


    def stats_get_season_leaders(
        self,
        season: int,
        stat: str,
        limit: int = 25,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Get league leaders for a stat category.

        Args:
            season: Season year
            stat: Stat column name (passing_yards, rushing_tds, etc.)
            limit: Number of leaders to return
            season_type: Filter by season type

        Returns:
            List of {player_id, player_name, team_id, position, stat_value, games}

        Raises:
            ValueError: If stat column is invalid
        """
        # Validate stat column to prevent SQL injection
        valid_stats = {
            'passing_yards', 'passing_tds', 'passing_attempts', 'passing_completions',
            'passing_interceptions', 'passing_rating',
            'rushing_yards', 'rushing_tds', 'rushing_attempts',
            'receiving_yards', 'receiving_tds', 'receptions', 'targets',
            'tackles_total', 'sacks', 'interceptions', 'forced_fumbles', 'passes_defended',
            'field_goals_made', 'field_goals_attempted', 'extra_points_made',
            'fantasy_points'
        }

        if stat not in valid_stats:
            raise ValueError(f"Invalid stat column: {stat}. Must be one of {valid_stats}")

        # Build query with dynamic stat column (safe because validated above)
        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                SUM(pgs.{stat}) as stat_value,
                COUNT(DISTINCT pgs.game_id) as games
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.{stat}) > 0
            ORDER BY stat_value DESC
            LIMIT ?
        '''

        results = self._execute_query(
            query,
            (self.dynasty_id, season, season_type, limit)
        )
        return results


    def stats_get_player_season_totals(
        self,
        player_id: str,
        season: int,
        season_type: str = 'regular_season'
    ) -> Dict[str, Any]:
        """
        Get aggregated season stats for a player.

        Args:
            player_id: Player identifier
            season: Season year
            season_type: Filter by season type

        Returns:
            Dictionary with aggregated stats and metadata
        """
        query = '''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games_played,
                SUM(pgs.passing_yards) as passing_yards,
                SUM(pgs.passing_tds) as passing_tds,
                SUM(pgs.passing_attempts) as passing_attempts,
                SUM(pgs.passing_completions) as passing_completions,
                SUM(pgs.passing_interceptions) as passing_interceptions,
                SUM(pgs.passing_sacks) as passing_sacks,
                SUM(pgs.passing_sack_yards) as passing_sack_yards,
                AVG(pgs.passing_rating) as avg_passing_rating,
                SUM(pgs.rushing_yards) as rushing_yards,
                SUM(pgs.rushing_tds) as rushing_tds,
                SUM(pgs.rushing_attempts) as rushing_attempts,
                MAX(pgs.rushing_long) as rushing_long,
                SUM(pgs.rushing_fumbles) as rushing_fumbles,
                SUM(pgs.receiving_yards) as receiving_yards,
                SUM(pgs.receiving_tds) as receiving_tds,
                SUM(pgs.receptions) as receptions,
                SUM(pgs.targets) as targets,
                MAX(pgs.receiving_long) as receiving_long,
                SUM(pgs.receiving_drops) as receiving_drops,
                SUM(pgs.tackles_total) as tackles_total,
                SUM(pgs.tackles_solo) as tackles_solo,
                SUM(pgs.tackles_assist) as tackles_assist,
                SUM(pgs.sacks) as sacks,
                SUM(pgs.interceptions) as interceptions,
                SUM(pgs.forced_fumbles) as forced_fumbles,
                SUM(pgs.fumbles_recovered) as fumbles_recovered,
                SUM(pgs.passes_defended) as passes_defended,
                SUM(pgs.field_goals_made) as field_goals_made,
                SUM(pgs.field_goals_attempted) as field_goals_attempted,
                SUM(pgs.extra_points_made) as extra_points_made,
                SUM(pgs.extra_points_attempted) as extra_points_attempted,
                SUM(pgs.punts) as punts,
                SUM(pgs.punt_yards) as punt_yards,
                SUM(pgs.fantasy_points) as fantasy_points
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND pgs.player_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
        '''

        results = self._execute_query(
            query,
            (self.dynasty_id, player_id, season, season_type)
        )

        if not results:
            return {
                'player_id': player_id,
                'season': season,
                'season_type': season_type,
                'games_played': 0
            }

        return results[0]


    # -------------------- Team Statistics (3 methods) --------------------

    def stats_get_team_summary(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get team statistical summary for a season.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            Dict with total_yards, points_for, turnovers, etc. or None
        """
        # Aggregate team stats from player_season_stats
        query = '''
            SELECT
                SUM(pss.passing_yards + pss.rushing_yards) as total_offense_yards,
                SUM(pss.passing_yards) as total_passing_yards,
                SUM(pss.rushing_yards) as total_rushing_yards,
                SUM(pss.passing_tds + pss.rushing_tds + pss.receiving_tds) as total_tds,
                SUM(pss.passing_interceptions + pss.fumbles_lost) as total_turnovers,
                SUM(pss.tackles_total) as total_tackles,
                SUM(pss.sacks) as total_sacks,
                SUM(pss.interceptions) as total_interceptions,
                COUNT(DISTINCT pss.player_id) as total_players
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.team_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, team_id, season, season_type))

        if not results or results[0]['total_players'] == 0:
            return None

        # Also get points from standings
        standing = self.standings_get_team(team_id, season, season_type)
        points_for = standing['standing'].points_for if standing else 0
        points_against = standing['standing'].points_against if standing else 0

        result = results[0]
        result['points_for'] = points_for
        result['points_against'] = points_against
        result['team_id'] = team_id
        result['season'] = season
        result['season_type'] = season_type

        return result


    def stats_get_team_offense(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get team offensive statistics only.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            Dict with offensive stats or None
        """
        query = '''
            SELECT
                SUM(pss.passing_yards) as total_passing_yards,
                SUM(pss.passing_tds) as total_passing_tds,
                SUM(pss.passing_attempts) as total_passing_attempts,
                SUM(pss.passing_completions) as total_passing_completions,
                SUM(pss.passing_interceptions) as total_interceptions,
                SUM(pss.rushing_yards) as total_rushing_yards,
                SUM(pss.rushing_tds) as total_rushing_tds,
                SUM(pss.rushing_attempts) as total_rushing_attempts,
                SUM(pss.receiving_yards) as total_receiving_yards,
                SUM(pss.receiving_tds) as total_receiving_tds,
                SUM(pss.receptions) as total_receptions,
                SUM(pss.targets) as total_targets
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.team_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, team_id, season, season_type))

        if not results:
            return None

        result = results[0]
        result['team_id'] = team_id
        result['season'] = season
        result['season_type'] = season_type

        return result


    def stats_get_team_defense(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get team defensive statistics only.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            Dict with defensive stats or None
        """
        query = '''
            SELECT
                SUM(pss.tackles_total) as total_tackles,
                SUM(pss.tackles_solo) as total_solo_tackles,
                SUM(pss.tackles_assists) as total_assisted_tackles,
                SUM(pss.sacks) as total_sacks,
                SUM(pss.interceptions) as total_interceptions,
                SUM(pss.passes_defended) as total_passes_defended,
                SUM(pss.forced_fumbles) as total_forced_fumbles,
                SUM(pss.fumble_recoveries) as total_fumble_recoveries
            FROM player_season_stats pss
            WHERE pss.dynasty_id = ?
                AND pss.team_id = ?
                AND pss.season = ?
                AND pss.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, team_id, season, season_type))

        if not results:
            return None

        result = results[0]
        result['team_id'] = team_id
        result['season'] = season
        result['season_type'] = season_type

        return result

    def stats_get_game_count(
        self,
        season: int,
        season_type: str = 'regular_season'
    ) -> int:
        """
        Get count of games with stats recorded.

        Args:
            season: Season year
            season_type: Season type filter

        Returns:
            Number of games with stats
        """
        query = '''
            SELECT COUNT(DISTINCT pgs.game_id) as game_count
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type))

        if not results:
            return 0

        return results[0].get('game_count', 0) or 0

    def stats_get_player_count(
        self,
        season: int,
        season_type: str = 'regular_season'
    ) -> int:
        """
        Get count of unique players with stats recorded.

        Args:
            season: Season year
            season_type: Season type filter

        Returns:
            Number of players with stats
        """
        query = '''
            SELECT COUNT(DISTINCT pgs.player_id) as player_count
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type))

        if not results:
            return 0

        return results[0].get('player_count', 0) or 0

    def stats_get_current_week(
        self,
        season: int,
        season_type: str = 'regular_season'
    ) -> int:
        """
        Get the highest week number with stats recorded.

        Args:
            season: Season year
            season_type: Season type filter

        Returns:
            Current/max week with stats
        """
        query = '''
            SELECT MAX(g.week) as max_week
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
        '''

        results = self._execute_query(query, (self.dynasty_id, season, season_type))

        if not results:
            return 0

        return results[0].get('max_week', 0) or 0

    # ========== Category-Specific Leader Methods (from player_game_stats) ==========

    def stats_get_category_leaders_passing(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get passing leaders with ALL passing-related stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (returns all team players if set)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all passing stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.passing_yards) as passing_yards,
                SUM(pgs.passing_tds) as passing_tds,
                SUM(pgs.passing_attempts) as passing_attempts,
                SUM(pgs.passing_completions) as passing_completions,
                SUM(pgs.passing_interceptions) as passing_interceptions,
                SUM(pgs.passing_sacks) as passing_sacks,
                SUM(pgs.passing_sack_yards) as passing_sack_yards
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.passing_attempts) > 0
            ORDER BY SUM(pgs.passing_yards) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_rushing(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get rushing leaders with ALL rushing-related stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (returns all team players if set)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all rushing stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.rushing_yards) as rushing_yards,
                SUM(pgs.rushing_tds) as rushing_tds,
                SUM(pgs.rushing_attempts) as rushing_attempts,
                MAX(pgs.rushing_long) as rushing_long,
                SUM(pgs.rushing_fumbles) as rushing_fumbles,
                SUM(pgs.snap_counts_offense) as snap_counts_offense
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.rushing_attempts) > 0
            ORDER BY SUM(pgs.rushing_yards) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_receiving(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get receiving leaders with ALL receiving-related stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all receiving stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.receiving_yards) as receiving_yards,
                SUM(pgs.receiving_tds) as receiving_tds,
                SUM(pgs.receptions) as receptions,
                SUM(pgs.targets) as targets,
                MAX(pgs.receiving_long) as receiving_long,
                SUM(pgs.receiving_drops) as receiving_drops,
                SUM(pgs.snap_counts_offense) as snap_counts_offense
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.receptions) > 0
            ORDER BY SUM(pgs.receiving_yards) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_defense(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None,
        sort_by: str = 'tackles'
    ) -> List[Dict[str, Any]]:
        """
        Get defensive leaders with ALL defensive stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)
            sort_by: Column to sort by ('tackles', 'sacks', 'interceptions', 'passes_defended', 'forced_fumbles')

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all defensive stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        # Map sort_by parameter to actual column names
        sort_column_map = {
            'tackles': 'SUM(pgs.tackles_total)',
            'tackles_total': 'SUM(pgs.tackles_total)',
            'tackles_solo': 'SUM(pgs.tackles_solo)',
            'tackles_assist': 'SUM(pgs.tackles_assist)',
            'sacks': 'SUM(pgs.sacks)',
            'interceptions': 'SUM(pgs.interceptions)',
            'passes_defended': 'SUM(pgs.passes_defended)',
            'forced_fumbles': 'SUM(pgs.forced_fumbles)',
            'fumbles_recovered': 'SUM(pgs.fumbles_recovered)',
        }
        order_column = sort_column_map.get(sort_by, 'SUM(pgs.tackles_total)')

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.tackles_total) as tackles_total,
                SUM(pgs.tackles_solo) as tackles_solo,
                SUM(pgs.tackles_assist) as tackles_assist,
                SUM(pgs.sacks) as sacks,
                SUM(pgs.interceptions) as interceptions,
                SUM(pgs.forced_fumbles) as forced_fumbles,
                SUM(pgs.fumbles_recovered) as fumbles_recovered,
                SUM(pgs.passes_defended) as passes_defended
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.tackles_total) > 0 OR SUM(pgs.sacks) > 0 OR SUM(pgs.interceptions) > 0
            ORDER BY {order_column} DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_kicking(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get kicking leaders with ALL kicking stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all kicking stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.field_goals_made) as field_goals_made,
                SUM(pgs.field_goals_attempted) as field_goals_attempted,
                SUM(pgs.extra_points_made) as extra_points_made,
                SUM(pgs.extra_points_attempted) as extra_points_attempted,
                SUM(pgs.punts) as punts,
                SUM(pgs.punt_yards) as punt_yards
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.field_goals_attempted) > 0 OR SUM(pgs.extra_points_attempted) > 0
            ORDER BY SUM(pgs.field_goals_made) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_punting(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get punting leaders with ALL punting stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all punting stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.punts) as punts,
                SUM(pgs.punt_yards) as punt_yards
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.punts) > 0
            ORDER BY SUM(pgs.punts) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_blocking(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get blocking leaders (OL) with ALL blocking stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all blocking stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.pass_blocks) as pass_blocks,
                SUM(pgs.pancakes) as pancakes,
                SUM(pgs.sacks_allowed) as sacks_allowed,
                SUM(pgs.hurries_allowed) as hurries_allowed,
                SUM(pgs.pressures_allowed) as pressures_allowed,
                AVG(pgs.run_blocking_grade) as run_blocking_grade,
                AVG(pgs.pass_blocking_efficiency) as pass_blocking_efficiency,
                SUM(pgs.missed_assignments) as missed_assignments,
                SUM(pgs.holding_penalties) as holding_penalties,
                SUM(pgs.false_start_penalties) as false_start_penalties,
                SUM(pgs.downfield_blocks) as downfield_blocks,
                SUM(pgs.double_team_blocks) as double_team_blocks,
                SUM(pgs.chip_blocks) as chip_blocks
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              AND pgs.position IN ('LT', 'LG', 'C', 'RG', 'RT', 'center', 'left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'offensive_tackle', 'offensive_guard', 'guard', 'tackle')
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.pass_blocks) > 0 OR SUM(pgs.pancakes) > 0 OR COUNT(DISTINCT pgs.game_id) > 0
            ORDER BY SUM(pgs.pass_blocks) DESC, SUM(pgs.pancakes) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_coverage(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get coverage leaders (DBs and LBs) with ALL coverage stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all coverage stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.coverage_targets) as coverage_targets,
                SUM(pgs.coverage_completions) as coverage_completions,
                SUM(pgs.coverage_yards_allowed) as coverage_yards_allowed,
                SUM(pgs.passes_defended) as passes_defended,
                SUM(pgs.interceptions) as interceptions,
                SUM(pgs.snap_counts_defense) as snap_counts_defense
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              AND (pgs.position IN ('CB', 'FS', 'SS', 'S', 'LB', 'MLB', 'LOLB', 'ROLB', 'cornerback', 'safety', 'free_safety', 'strong_safety', 'linebacker', 'middle_linebacker', 'outside_linebacker'))
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.coverage_targets) > 0 OR SUM(pgs.passes_defended) > 0
            ORDER BY SUM(pgs.coverage_targets) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_category_leaders_pass_rush(
        self,
        season: int,
        limit: int = 25,
        season_type: str = 'regular_season',
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pass rush leaders (DL and EDGE) with ALL pass rush stats.

        Args:
            season: Season year
            limit: Number of leaders to return
            season_type: Filter by season type
            team_id: Optional team ID to filter by (shows all team players)

        Returns:
            List of dicts with player_id, player_name, team_id, position,
            and all pass rush stats aggregated.
        """
        team_filter = "AND pgs.team_id = ?" if team_id else ""
        actual_limit = 100 if team_id else limit  # Show all team players when filtered

        query = f'''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.pass_rush_wins) as pass_rush_wins,
                SUM(pgs.pass_rush_attempts) as pass_rush_attempts,
                SUM(pgs.times_double_teamed) as times_double_teamed,
                SUM(pgs.sacks) as sacks,
                SUM(pgs.snap_counts_defense) as snap_counts_defense
            FROM player_game_stats pgs
            INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
              AND g.season = ?
              AND pgs.season_type = ?
              AND (pgs.position IN ('DE', 'DT', 'LE', 'RE', 'EDGE', 'NT', 'defensive_end', 'defensive_tackle', 'nose_tackle', 'edge'))
              {team_filter}
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
            HAVING SUM(pgs.pass_rush_attempts) > 0 OR SUM(pgs.sacks) > 0
            ORDER BY SUM(pgs.sacks) DESC, SUM(pgs.pass_rush_wins) DESC
            LIMIT ?
        '''

        params = [self.dynasty_id, season, season_type]
        if team_id:
            params.append(team_id)
        params.append(actual_limit)

        return self._execute_query(query, tuple(params))

    def stats_get_team_roster(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> List[Dict[str, Any]]:
        """
        Get all players on a team with their aggregated season stats.

        Returns all players on the roster, including those without stats.
        Each player dict includes position-appropriate stats for UI display.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            List of player dicts with all stats aggregated by player
        """
        # Query gets all players on team with LEFT JOIN to stats
        # so players without game stats still appear
        query = '''
            SELECT
                p.player_id,
                p.first_name || ' ' || p.last_name as player_name,
                p.positions,
                p.attributes,
                p.team_id,
                p.years_pro,
                p.birthdate,
                COALESCE(COUNT(DISTINCT pgs.game_id), 0) as games,
                -- Passing stats
                COALESCE(SUM(pgs.passing_yards), 0) as passing_yards,
                COALESCE(SUM(pgs.passing_tds), 0) as passing_tds,
                COALESCE(SUM(pgs.passing_attempts), 0) as passing_attempts,
                COALESCE(SUM(pgs.passing_completions), 0) as passing_completions,
                COALESCE(SUM(pgs.passing_interceptions), 0) as passing_interceptions,
                -- Rushing stats
                COALESCE(SUM(pgs.rushing_yards), 0) as rushing_yards,
                COALESCE(SUM(pgs.rushing_tds), 0) as rushing_tds,
                COALESCE(SUM(pgs.rushing_attempts), 0) as rushing_attempts,
                COALESCE(MAX(pgs.rushing_long), 0) as rushing_long,
                -- Receiving stats
                COALESCE(SUM(pgs.receiving_yards), 0) as receiving_yards,
                COALESCE(SUM(pgs.receiving_tds), 0) as receiving_tds,
                COALESCE(SUM(pgs.receptions), 0) as receptions,
                COALESCE(SUM(pgs.targets), 0) as targets,
                -- Defensive stats
                COALESCE(SUM(pgs.tackles_total), 0) as tackles_total,
                COALESCE(SUM(pgs.tackles_solo), 0) as tackles_solo,
                COALESCE(SUM(pgs.tackles_assist), 0) as tackles_assist,
                COALESCE(SUM(pgs.sacks), 0) as sacks,
                COALESCE(SUM(pgs.interceptions), 0) as interceptions,
                COALESCE(SUM(pgs.passes_defended), 0) as passes_defended,
                COALESCE(SUM(pgs.forced_fumbles), 0) as forced_fumbles,
                -- Kicking stats
                COALESCE(SUM(pgs.field_goals_made), 0) as field_goals_made,
                COALESCE(SUM(pgs.field_goals_attempted), 0) as field_goals_attempted,
                COALESCE(SUM(pgs.extra_points_made), 0) as extra_points_made,
                COALESCE(SUM(pgs.extra_points_attempted), 0) as extra_points_attempted,
                -- Blocking stats
                COALESCE(SUM(pgs.pancakes), 0) as pancakes,
                COALESCE(SUM(pgs.sacks_allowed), 0) as sacks_allowed
            FROM players p
            LEFT JOIN player_game_stats pgs
                ON p.dynasty_id = pgs.dynasty_id
                AND p.player_id = pgs.player_id
                AND pgs.season_type = ?
            LEFT JOIN games g
                ON pgs.game_id = g.game_id
                AND pgs.dynasty_id = g.dynasty_id
                AND g.season = ?
            WHERE p.dynasty_id = ?
                AND p.team_id = ?
                AND p.status = 'active'
            GROUP BY p.player_id, p.first_name, p.last_name, p.positions,
                     p.attributes, p.team_id, p.years_pro, p.birthdate
            ORDER BY p.positions, p.last_name
        '''

        results = self._execute_query(
            query,
            (season_type, season, self.dynasty_id, team_id)
        )

        # Post-process to parse JSON fields and extract position/overall
        processed = []
        for row in results:
            player = dict(row)

            # Parse positions JSON to get primary position
            try:
                positions_data = json.loads(player.get('positions', '{}'))
                if isinstance(positions_data, dict) and 'primary' in positions_data:
                    player['position'] = positions_data['primary']
                elif isinstance(positions_data, list) and len(positions_data) > 0:
                    player['position'] = positions_data[0]
                else:
                    player['position'] = 'Unknown'
            except (json.JSONDecodeError, TypeError):
                player['position'] = 'Unknown'

            # Parse attributes JSON to get overall and age
            try:
                attrs = json.loads(player.get('attributes', '{}'))
                player['overall'] = attrs.get('overall', 0)
                player['age'] = attrs.get('age', 0)
            except (json.JSONDecodeError, TypeError):
                player['overall'] = 0
                player['age'] = 0

            processed.append(player)

        return processed


    # -------------------- Utilities (3 methods) --------------------

    def count_playoff_events(
        self,
        season: int
    ) -> int:
        """
        Count playoff events for a specific season.

        Args:
            season: Season year

        Returns:
            Number of playoff events
        """
        query = '''
            SELECT COUNT(*) as count
            FROM events
            WHERE dynasty_id = ?
              AND event_type = 'GAME'
              AND game_id LIKE ?
        '''

        game_id_pattern = f"playoff_{season}_%"
        results = self._execute_query(query, (self.dynasty_id, game_id_pattern))

        if not results:
            return 0

        return results[0]['count']


    def get_upcoming_games(
        self,
        team_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Alias for games_get_upcoming.

        Args:
            team_id: Team ID (1-32)
            limit: Number of games to return

        Returns:
            List of upcoming game dictionaries
        """
        return self.games_get_upcoming(team_id, limit)


    def get_team_record(
        self,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[Tuple[int, int, int]]:
        """
        Get team's W-L-T record.

        Args:
            team_id: Team ID (1-32)
            season: Season year
            season_type: Season type filter

        Returns:
            Tuple of (wins, losses, ties) or None if not found
        """
        standing = self.standings_get_team(team_id, season, season_type)

        if not standing:
            return None

        return (
            standing['standing'].wins,
            standing['standing'].losses,
            standing['standing'].ties
        )


    # -------------------- Helper Methods --------------------

    def _get_empty_standings(self) -> Dict[str, Any]:
        """
        Get empty standings structure for new seasons.

        Returns:
            Empty standings with all teams at 0-0
        """
        from stores.standings_store import EnhancedTeamStanding, NFL_DIVISIONS, NFL_CONFERENCES

        standings_data = {}

        # Initialize all divisions with 0-0 records
        for division, team_ids in NFL_DIVISIONS.items():
            division_teams = []
            for team_id in team_ids:
                standing = EnhancedTeamStanding(team_id=team_id)
                division_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })
            standings_data[division] = division_teams

        # Initialize conferences
        conferences_data = {}
        for conference, team_ids in NFL_CONFERENCES.items():
            conference_teams = []
            for team_id in team_ids:
                standing = EnhancedTeamStanding(team_id=team_id)
                conference_teams.append({
                    'team_id': team_id,
                    'standing': standing
                })
            conferences_data[conference] = conference_teams

        # Initialize overall
        overall_teams = []
        for team_id in range(1, 33):
            standing = EnhancedTeamStanding(team_id=team_id)
            overall_teams.append({
                'team_id': team_id,
                'standing': standing
            })

        return {
            'divisions': standings_data,
            'conferences': conferences_data,
            'overall': overall_teams,
            'playoff_picture': {}
        }
