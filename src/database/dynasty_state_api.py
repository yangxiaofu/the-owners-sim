"""
Dynasty State API

Centralized API for all dynasty_state database operations.
Provides clean interface for UI controllers and simulation components.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .connection import DatabaseConnection
from .sync_exceptions import CalendarSyncPersistenceException


class DynastyStateAPI:
    """
    API for managing dynasty simulation state.

    Handles all database operations for the dynasty_state table,
    which tracks current simulation date, phase, and week for each dynasty.

    This is the SINGLE SOURCE OF TRUTH for dynasty_state operations.
    All UI controllers should use this API instead of raw SQL queries.
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Dynasty State API.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def derive_season_from_date(date_str: str) -> int:
        """
        Derive NFL season year from date string.

        This is the database layer's implementation of year-from-date conversion.
        Should match PhaseBoundaryDetector.derive_season_year() logic.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            NFL season year

        Examples:
            derive_season_from_date("2025-08-01") → 2025
            derive_season_from_date("2026-01-15") → 2025  # Playoffs of 2025 season
            derive_season_from_date("2026-07-31") → 2025  # Offseason of 2025
            derive_season_from_date("2026-08-01") → 2026  # New season!
        """
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        # Season year boundary: August 1st
        # Aug-Dec: current year, Jan-Jul: previous year
        if date_obj.month >= 8:
            return date_obj.year
        else:
            return date_obj.year - 1

    def get_current_state(
        self,
        dynasty_id: str,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get current simulation state for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict with current_date, current_phase, current_week, last_simulated_game_id,
            current_draft_pick, draft_in_progress or None if no state exists
        """
        query = """
            SELECT "current_date", "current_phase", "current_week", last_simulated_game_id,
                   current_draft_pick, draft_in_progress
            FROM dynasty_state
            WHERE dynasty_id = ? AND season = ?
        """

        result = self.db.execute_query(query, (dynasty_id, season))

        if result:
            row = result[0]
            state = {
                'current_date': row['current_date'],
                'current_phase': row['current_phase'],
                'current_week': row['current_week'],
                'last_simulated_game_id': row['last_simulated_game_id'],
                'current_draft_pick': row.get('current_draft_pick', 0),
                'draft_in_progress': bool(row.get('draft_in_progress', 0))
            }
            return state

        return None

    def get_latest_state(
        self,
        dynasty_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent simulation state for a dynasty (without specifying season).

        This is the SINGLE SOURCE OF TRUTH method for loading dynasty state.
        It retrieves the most recent season's state based on the season column.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with season, current_date, current_phase, current_week, last_simulated_game_id,
            current_draft_pick, draft_in_progress or None if no state exists for this dynasty

        Examples:
            >>> api = DynastyStateAPI()
            >>> state = api.get_latest_state("my_dynasty")
            >>> if state:
            ...     print(f"Season: {state['season']}, Phase: {state['current_phase']}")
            ...     if state['draft_in_progress']:
            ...         print(f"Draft in progress at pick {state['current_draft_pick']}")
        """
        query = """
            SELECT season, "current_date", "current_phase", "current_week", last_simulated_game_id,
                   current_draft_pick, draft_in_progress
            FROM dynasty_state
            WHERE dynasty_id = ?
            ORDER BY season DESC
            LIMIT 1
        """

        result = self.db.execute_query(query, (dynasty_id,))

        if result:
            row = result[0]
            state = {
                'season': row['season'],
                'current_date': row['current_date'],
                'current_phase': row['current_phase'],
                'current_week': row['current_week'],
                'last_simulated_game_id': row['last_simulated_game_id'],
                'current_draft_pick': row.get('current_draft_pick', 0),
                'draft_in_progress': bool(row.get('draft_in_progress', 0))
            }
            return state

        return None

    def initialize_state(
        self,
        dynasty_id: str,
        season: int,
        start_date: str,
        start_week: int = 1,
        start_phase: str = 'regular_season'
    ) -> bool:
        """
        Initialize fresh dynasty state.

        ALWAYS deletes any existing state first to ensure clean slate.
        This prevents stale data from corrupting new dynasties.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            start_date: Start date in YYYY-MM-DD format
            start_week: Starting week number (default: 1)
            start_phase: Starting phase (default: 'regular_season')

        Returns:
            True if successful, False otherwise
        """
        try:
            # DEFENSIVE: Delete any existing state first
            self.delete_state(dynasty_id, season)

            # Validate season matches start_date (defensive check)
            derived_season = self.derive_season_from_date(start_date)
            if season != derived_season:
                self.logger.warning(
                    f"Season/date mismatch during initialization!\n"
                    f"  Provided season: {season}\n"
                    f"  Start date: {start_date}\n"
                    f"  Derived season from date: {derived_season}\n"
                    f"  Using derived season to maintain consistency."
                )
                season = derived_season

            # Insert fresh state
            # IMPORTANT: Quote "current_date" to avoid SQLite auto-fill with CURRENT_DATE
            query = """
                INSERT INTO dynasty_state
                (dynasty_id, season, "current_date", current_week, current_phase)
                VALUES (?, ?, ?, ?, ?)
            """

            self.db.execute_update(
                query,
                (dynasty_id, season, start_date, start_week, start_phase)
            )

            # VERIFICATION: Read back what we just wrote
            verification = self.get_current_state(dynasty_id, season)

            if verification and verification['current_date'] == start_date:
                return True
            else:
                self.logger.error(f"Dynasty state verification failed - expected {start_date}, got {verification['current_date'] if verification else 'None'}")
                return False

        except Exception as e:
            self.logger.error(f"Error initializing dynasty state: {e}", exc_info=True)
            return False

    def update_state(
        self,
        dynasty_id: str,
        season: int,
        current_date: str,
        current_phase: str,
        current_week: Optional[int] = None,
        last_simulated_game_id: Optional[str] = None,
        connection: Optional[Any] = None
    ) -> bool:
        """
        Update existing dynasty state.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            current_date: Current simulation date (YYYY-MM-DD)
            current_phase: Current phase (regular_season, playoffs, offseason)
            current_week: Current week number
            last_simulated_game_id: ID of last simulated game
            connection: Optional SQLite connection for transaction support.
                        If provided, executes within existing transaction.
                        If None, creates new connection (default behavior).

        Returns:
            True if successful

        Raises:
            CalendarSyncPersistenceException: If database update fails (fail-loud)
        """
        try:
            # Validate season matches current_date (defensive check)
            derived_season = self.derive_season_from_date(current_date)
            if season != derived_season:
                self.logger.warning(
                    f"Season/date mismatch detected!\n"
                    f"  Provided season: {season}\n"
                    f"  Current date: {current_date}\n"
                    f"  Derived season from date: {derived_season}\n"
                    f"  Using derived season to maintain consistency."
                )
                # Auto-correct: use derived season
                season = derived_season

            # IMPORTANT: Quote "current_date" to avoid SQLite auto-fill with CURRENT_DATE
            query = """
                INSERT OR REPLACE INTO dynasty_state
                (dynasty_id, season, "current_date", current_phase, current_week,
                 last_simulated_game_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            # Execute using provided connection (transaction support) or create new connection
            if connection:
                # Use provided connection (part of transaction)
                cursor = connection.cursor()
                cursor.execute(query, (dynasty_id, season, current_date, current_phase, current_week, last_simulated_game_id))
                rows_affected = cursor.rowcount
            else:
                # Legacy behavior: create new connection
                rows_affected = self.db.execute_update(
                    query,
                    (dynasty_id, season, current_date, current_phase, current_week, last_simulated_game_id)
                )

            # FAIL-LOUD: If no rows affected, dynasty/season doesn't exist
            if rows_affected == 0:
                self.logger.error(
                    f"Dynasty state update failed - no rows affected!\n"
                    f"  Dynasty ID: {dynasty_id}\n"
                    f"  Season: {season}\n"
                    f"  Date: {current_date}\n"
                    f"  Phase: {current_phase}",
                    exc_info=True
                )
                raise CalendarSyncPersistenceException(
                    operation="dynasty_state_update",
                    sync_point="update_state",
                    state_info={
                        "dynasty_id": dynasty_id,
                        "season": season,
                        "current_date": current_date,
                        "current_phase": current_phase,
                        "current_week": current_week,
                        "reason": "No rows affected - dynasty/season may not exist"
                    }
                )

            return True

        except CalendarSyncPersistenceException:
            # Re-raise our custom exception without wrapping
            raise

        except Exception as e:
            # Log and wrap database errors
            self.logger.error(f"Error updating dynasty state: {e}", exc_info=True)
            raise CalendarSyncPersistenceException(
                operation="dynasty_state_update",
                sync_point="update_state",
                state_info={
                    "dynasty_id": dynasty_id,
                    "season": season,
                    "current_date": current_date,
                    "current_phase": current_phase,
                    "current_week": current_week,
                    "error": str(e)
                }
            ) from e

    def update_draft_progress(
        self,
        dynasty_id: str,
        season: int,
        current_pick: int,
        in_progress: bool
    ) -> bool:
        """
        Update draft progress for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            current_pick: Current draft pick number (0-262, 0 means not started)
            in_progress: Whether draft is currently active

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If current_pick is out of valid range (0-262)
        """
        # Validate draft pick range
        if not (0 <= current_pick <= 262):
            raise ValueError(
                f"Invalid draft pick number: {current_pick}. Must be 0-262."
            )

        try:
            query = """
                UPDATE dynasty_state
                SET current_draft_pick = ?,
                    draft_in_progress = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE dynasty_id = ? AND season = ?
            """

            # Convert boolean to integer (SQLite doesn't have boolean type)
            in_progress_int = 1 if in_progress else 0

            rows_affected = self.db.execute_update(
                query,
                (current_pick, in_progress_int, dynasty_id, season)
            )

            if rows_affected == 0:
                self.logger.warning(
                    f"Draft progress update affected 0 rows - dynasty/season may not exist.\n"
                    f"  Dynasty ID: {dynasty_id}\n"
                    f"  Season: {season}\n"
                    f"  Pick: {current_pick}\n"
                    f"  In Progress: {in_progress}"
                )
                return False

            self.logger.info(
                f"Draft progress updated: {dynasty_id} S{season} - Pick {current_pick}, "
                f"Active: {in_progress}"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error updating draft progress: {e}\n"
                f"  Dynasty ID: {dynasty_id}\n"
                f"  Season: {season}\n"
                f"  Pick: {current_pick}\n"
                f"  In Progress: {in_progress}",
                exc_info=True
            )
            return False

    def update_season(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """
        Update the season in dynasty_state (SSOT for current season).

        This is the canonical way to advance to a new season.
        Should only be called when transitioning from offseason to new regular season.

        Updates the most recent dynasty_state record's season field to the new value.
        This method is used by StageController when transitioning from
        OFFSEASON_WAIVER_WIRE to REGULAR_WEEK_1.

        Args:
            dynasty_id: Dynasty identifier
            season: New season number to set

        Returns:
            True if successful, False otherwise

        Raises:
            CalendarSyncPersistenceException: If database update fails (fail-loud)

        Examples:
            >>> api = DynastyStateAPI()
            >>> api.update_season("my_dynasty", 2026)  # Advance to season 2026
        """
        try:
            # Update the most recent dynasty_state record's season field
            query = '''
                UPDATE dynasty_state
                SET season = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE dynasty_id = ?
                    AND id = (
                        SELECT id FROM dynasty_state
                        WHERE dynasty_id = ?
                        ORDER BY season DESC, updated_at DESC
                        LIMIT 1
                    )
            '''

            rows_affected = self.db.execute_update(query, (season, dynasty_id, dynasty_id))

            # FAIL-LOUD: If no rows affected, dynasty doesn't exist
            if rows_affected == 0:
                self.logger.error(
                    f"Season SSOT update failed - no rows affected!\n"
                    f"  Dynasty ID: {dynasty_id}\n"
                    f"  New Season: {season}\n"
                    f"  Reason: Dynasty may not exist or no state records found"
                )
                raise CalendarSyncPersistenceException(
                    operation="season_update",
                    sync_point="update_season",
                    state_info={
                        "dynasty_id": dynasty_id,
                        "season": season,
                        "reason": "No rows affected - dynasty may not exist"
                    }
                )

            self.logger.info(f"Updated season SSOT to {season} for dynasty {dynasty_id}")
            return True

        except CalendarSyncPersistenceException:
            # Re-raise our custom exception without wrapping
            raise

        except Exception as e:
            # Log and wrap database errors
            self.logger.error(f"Error updating season SSOT: {e}", exc_info=True)
            raise CalendarSyncPersistenceException(
                operation="season_update",
                sync_point="update_season",
                state_info={
                    "dynasty_id": dynasty_id,
                    "season": season,
                    "error": str(e)
                }
            ) from e

    def delete_state(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Delete dynasty state for a specific dynasty and season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of rows deleted
        """
        try:
            query = "DELETE FROM dynasty_state WHERE dynasty_id = ? AND season = ?"
            rows_deleted = self.db.execute_update(query, (dynasty_id, season))
            return rows_deleted

        except Exception as e:
            self.logger.error(f"Error deleting dynasty state: {e}", exc_info=True)
            return 0

    def get_current_date(
        self,
        dynasty_id: str,
        season: int
    ) -> Optional[str]:
        """
        Convenience method to get just the current simulation date.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Current date string (YYYY-MM-DD) or None if no state exists
        """
        state = self.get_current_state(dynasty_id, season)
        if state:
            return state['current_date']
        return None


