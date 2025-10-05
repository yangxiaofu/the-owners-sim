"""
Dynasty State API

Centralized API for all dynasty_state database operations.
Provides clean interface for UI controllers and simulation components.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .connection import DatabaseConnection


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
            Dict with current_date, current_phase, current_week, last_simulated_game_id
            or None if no state exists
        """
        query = """
            SELECT "current_date", "current_phase", "current_week", last_simulated_game_id
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
                'last_simulated_game_id': row['last_simulated_game_id']
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

            # Insert fresh state
            query = """
                INSERT INTO dynasty_state
                (dynasty_id, season, current_date, current_week, current_phase)
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
        last_simulated_game_id: Optional[str] = None
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

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                INSERT OR REPLACE INTO dynasty_state
                (dynasty_id, season, current_date, current_phase, current_week,
                 last_simulated_game_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            rows_affected = self.db.execute_update(
                query,
                (dynasty_id, season, current_date, current_phase, current_week, last_simulated_game_id)
            )

            return rows_affected > 0

        except Exception as e:
            self.logger.error(f"Error updating dynasty state: {e}", exc_info=True)
            return False

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
