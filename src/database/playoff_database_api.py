"""
Playoff Database API

Centralized API for all playoff-related database operations.
Provides clean interface for playoff data management and cleanup.
"""

from typing import Optional, Dict, Any
import sqlite3
import logging

from .connection import DatabaseConnection


class PlayoffDatabaseAPI:
    """
    API for managing playoff-related database operations.

    Handles all database operations for playoff-related tables:
    - events table (playoff game events)
    - playoff_brackets table (playoff tournament structure)
    - playoff_seedings table (playoff seeding results)

    This is the SINGLE SOURCE OF TRUTH for playoff database operations.
    All playoff controllers should use this API instead of raw SQL queries.

    Transaction-Aware Design:
    All methods accept an optional `connection` parameter for transaction support.
    - connection=None (default): Auto-commit mode, method manages connection lifecycle
    - connection=<Connection>: Transaction mode, caller manages connection/transaction
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Playoff Database API.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    def clear_playoff_data(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> Dict[str, int]:
        """
        Delete all playoff data for a specific dynasty and season.

        Atomically deletes data from 3 tables:
        1. events table (playoff game events with game_id pattern 'playoff_{season}_%')
        2. playoff_brackets table (playoff tournament structure)
        3. playoff_seedings table (playoff seeding results)

        This is the main cleanup method for regenerating playoff data.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional database connection for transaction support

        Returns:
            Dict with deletion counts:
            {
                'events_deleted': N,
                'brackets_deleted': N,
                'seedings_deleted': N,
                'total_deleted': N
            }

        Examples:
            >>> # Auto-commit mode (connection=None)
            >>> api = PlayoffDatabaseAPI()
            >>> result = api.clear_playoff_data("my_dynasty", 2025)
            >>> print(f"Deleted {result['total_deleted']} total rows")

            >>> # Transaction mode (caller manages connection)
            >>> with TransactionContext(db_path) as conn:
            ...     result = api.clear_playoff_data("my_dynasty", 2025, connection=conn)
            ...     # Transaction commits automatically if no exception
        """
        should_close = False
        if connection is None:
            connection = self.db.get_connection()
            should_close = True

        try:
            cursor = connection.cursor()

            # 1. Delete playoff events (game_id pattern: 'playoff_{season}_%')
            events_query = """
                DELETE FROM events
                WHERE dynasty_id = ? AND game_id LIKE ?
            """
            game_id_pattern = f'playoff_{season}_%'
            cursor.execute(events_query, (dynasty_id, game_id_pattern))
            events_deleted = cursor.rowcount

            # 2. Delete playoff brackets
            brackets_query = """
                DELETE FROM playoff_brackets
                WHERE dynasty_id = ? AND season = ?
            """
            cursor.execute(brackets_query, (dynasty_id, season))
            brackets_deleted = cursor.rowcount

            # 3. Delete playoff seedings
            seedings_query = """
                DELETE FROM playoff_seedings
                WHERE dynasty_id = ? AND season = ?
            """
            cursor.execute(seedings_query, (dynasty_id, season))
            seedings_deleted = cursor.rowcount

            # Calculate total
            total_deleted = events_deleted + brackets_deleted + seedings_deleted

            # Commit if auto-commit mode
            if should_close:
                connection.commit()

            # Log successful deletion
            self.logger.info(
                f"Cleared playoff data for dynasty '{dynasty_id}', season {season}: "
                f"{events_deleted} events, {brackets_deleted} brackets, "
                f"{seedings_deleted} seedings ({total_deleted} total rows)"
            )

            return {
                'events_deleted': events_deleted,
                'brackets_deleted': brackets_deleted,
                'seedings_deleted': seedings_deleted,
                'total_deleted': total_deleted
            }

        except Exception as e:
            self.logger.error(
                f"Error clearing playoff data for dynasty '{dynasty_id}', season {season}: {e}",
                exc_info=True
            )
            raise
        finally:
            if should_close and connection:
                connection.close()

    def bracket_exists(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Check if playoff bracket exists for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional database connection for transaction support

        Returns:
            True if at least one bracket record exists, False otherwise

        Examples:
            >>> api = PlayoffDatabaseAPI()
            >>> if api.bracket_exists("my_dynasty", 2025):
            ...     print("Playoff bracket already generated")
        """
        should_close = False
        if connection is None:
            connection = self.db.get_connection()
            should_close = True

        try:
            cursor = connection.cursor()
            query = """
                SELECT COUNT(*) FROM playoff_brackets
                WHERE dynasty_id = ? AND season = ?
            """
            cursor.execute(query, (dynasty_id, season))
            count = cursor.fetchone()[0]

            exists = count > 0
            self.logger.debug(
                f"Bracket exists check for dynasty '{dynasty_id}', season {season}: {exists} ({count} records)"
            )

            return exists

        except Exception as e:
            self.logger.error(
                f"Error checking bracket existence for dynasty '{dynasty_id}', season {season}: {e}",
                exc_info=True
            )
            raise
        finally:
            if should_close and connection:
                connection.close()

    def seeding_exists(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Check if playoff seedings exist for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional database connection for transaction support

        Returns:
            True if at least one seeding record exists, False otherwise

        Examples:
            >>> api = PlayoffDatabaseAPI()
            >>> if api.seeding_exists("my_dynasty", 2025):
            ...     print("Playoff seedings already calculated")
        """
        should_close = False
        if connection is None:
            connection = self.db.get_connection()
            should_close = True

        try:
            cursor = connection.cursor()
            query = """
                SELECT COUNT(*) FROM playoff_seedings
                WHERE dynasty_id = ? AND season = ?
            """
            cursor.execute(query, (dynasty_id, season))
            count = cursor.fetchone()[0]

            exists = count > 0
            self.logger.debug(
                f"Seeding exists check for dynasty '{dynasty_id}', season {season}: {exists} ({count} records)"
            )

            return exists

        except Exception as e:
            self.logger.error(
                f"Error checking seeding existence for dynasty '{dynasty_id}', season {season}: {e}",
                exc_info=True
            )
            raise
        finally:
            if should_close and connection:
                connection.close()
