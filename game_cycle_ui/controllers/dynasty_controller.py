"""
Dynasty Controller for Game Cycle UI.

Uses GameCycleInitializer directly - no legacy system dependency.
This ensures NFLScheduleGenerator is used (correct regular_* format)
and primetime slots are assigned during initialization.
"""

import re
import uuid
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class GameCycleDynastyController:
    """
    Controller for dynasty management in the game_cycle system.

    Key difference from legacy DynastyController:
    - Uses GameCycleInitializer (not DynastyInitializationService)
    - Creates events with regular_* format (not game_YYYYMMDD_*)
    - Assigns primetime slots (TNF/SNF/MNF) during initialization
    """

    def __init__(self, db_path: str):
        """
        Initialize the dynasty controller.

        Args:
            db_path: Path to game_cycle.db database
        """
        self._db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Ensure database directory exists."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_dynasties(self) -> List[Dict[str, Any]]:
        """
        Get all existing dynasties.

        Returns:
            List of dynasty dictionaries with metadata
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT dynasty_id, dynasty_name, owner_name, team_id,
                           created_at, total_seasons, is_active
                    FROM dynasties
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return []

    def dynasty_exists(self, dynasty_id: str) -> bool:
        """
        Check if a dynasty ID already exists.

        Args:
            dynasty_id: Dynasty identifier to check

        Returns:
            True if dynasty exists, False otherwise
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM dynasties WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                return cursor.fetchone() is not None
            finally:
                conn.close()
        except sqlite3.OperationalError:
            return False

    def validate_dynasty_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a dynasty name.

        Args:
            name: Dynasty name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not name.strip():
            return (False, "Dynasty name cannot be empty")

        if len(name) < 3:
            return (False, "Dynasty name must be at least 3 characters")

        if len(name) > 50:
            return (False, "Dynasty name must be 50 characters or less")

        # Allow letters, numbers, spaces, hyphens, apostrophes
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'")
        if not all(c in allowed for c in name):
            return (False, "Dynasty name contains invalid characters")

        return (True, None)

    def generate_dynasty_id(self, base_name: str) -> str:
        """
        Generate a unique dynasty ID from a base name.

        Args:
            base_name: Base dynasty name

        Returns:
            Unique dynasty_id string (e.g., "testdynasty" or "testdynasty_001")
        """
        # Sanitize: lowercase, alphanumeric only, max 20 chars
        base_id = re.sub(r'[^a-z0-9]', '', base_name.lower())[:20]

        if not base_id:
            # Fallback for names with no alphanumeric chars
            base_id = f"dynasty{uuid.uuid4().hex[:8]}"

        if not self.dynasty_exists(base_id):
            return base_id

        # Append incrementing suffix until unique
        counter = 1
        while self.dynasty_exists(f"{base_id}_{counter:03d}"):
            counter += 1
            if counter > 999:
                # Fallback to random suffix
                return f"{base_id}_{uuid.uuid4().hex[:6]}"

        return f"{base_id}_{counter:03d}"

    def get_dynasty_info(self, dynasty_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty metadata or None if not found
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT dynasty_id, dynasty_name, owner_name, team_id,
                           created_at, total_seasons, is_active
                    FROM dynasties WHERE dynasty_id = ?
                """, (dynasty_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except sqlite3.OperationalError:
            return None

    def get_dynasty_stats(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get statistics about a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty statistics
        """
        stats = {
            'total_seasons': 0,
            'total_games': 0,
            'current_season': None
        }

        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Get total seasons from dynasty record
                cursor.execute(
                    "SELECT total_seasons FROM dynasties WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                row = cursor.fetchone()
                if row:
                    stats['total_seasons'] = row['total_seasons'] or 0

                # Get game count
                cursor.execute(
                    "SELECT COUNT(*) FROM games WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                row = cursor.fetchone()
                stats['total_games'] = row[0] if row else 0

                # Get current season from dynasty_state or events
                cursor.execute("""
                    SELECT MAX(json_extract(data, '$.parameters.season')) as season
                    FROM events
                    WHERE dynasty_id = ? AND event_type = 'GAME'
                """, (dynasty_id,))
                row = cursor.fetchone()
                if row and row['season']:
                    stats['current_season'] = row['season']

            finally:
                conn.close()
        except sqlite3.OperationalError:
            pass

        return stats

    def create_dynasty(
        self,
        dynasty_name: str,
        owner_name: str = "Owner",
        team_id: Optional[int] = None,
        season: int = 2025
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new dynasty using GameCycleInitializer.

        This method:
        1. Generates unique dynasty_id
        2. Calls GameCycleInitializer which:
           - Creates dynasty record
           - Loads players/contracts from JSON
           - Generates schedule using NFLScheduleGenerator (regular_* format)
           - Assigns primetime slots (TNF/SNF/MNF)
           - Initializes draft class, rivalries, pick ownership
        3. Updates dynasty with correct name/owner

        Args:
            dynasty_name: Display name for the dynasty
            owner_name: Owner's name
            team_id: User's team ID (1-32) or None for commissioner mode
            season: Starting season year

        Returns:
            Tuple of (success, dynasty_id, error_message)
        """
        # Validate name first
        is_valid, error_msg = self.validate_dynasty_name(dynasty_name)
        if not is_valid:
            return (False, "", error_msg)

        # Generate unique ID
        dynasty_id = self.generate_dynasty_id(dynasty_name)

        try:
            # Import here to avoid circular imports
            from game_cycle.services.initialization_service import GameCycleInitializer

            # Use GameCycleInitializer (NOT legacy DynastyInitializationService!)
            # This ensures:
            # - NFLScheduleGenerator creates regular_* format events
            # - PrimetimeScheduler assigns TNF/SNF/MNF slots
            initializer = GameCycleInitializer(
                db_path=self._db_path,
                dynasty_id=dynasty_id,
                season=season
            )

            # Initialize dynasty with all data
            initializer.initialize_dynasty(team_id=team_id or 1)

            # Update dynasty record with actual name and owner
            # (GameCycleInitializer uses default values)
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE dynasties
                    SET dynasty_name = ?, owner_name = ?
                    WHERE dynasty_id = ?
                """, (dynasty_name, owner_name, dynasty_id))
                conn.commit()
            finally:
                conn.close()

            return (True, dynasty_id, None)

        except Exception as e:
            error_message = str(e)
            print(f"[ERROR GameCycleDynastyController] Failed to create dynasty: {error_message}")
            return (False, "", error_message)

    def delete_dynasty(self, dynasty_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a dynasty and all associated data.

        WARNING: This is destructive and cannot be undone.

        Args:
            dynasty_id: Dynasty identifier to delete

        Returns:
            Tuple of (success, error_message)
        """
        try:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Delete from all tables (order matters for foreign keys)
                tables_to_clear = [
                    'play_grades',
                    'player_game_stats',
                    'box_scores',
                    'game_slots',
                    'games',
                    'events',
                    'standings',
                    'player_contracts',
                    'contract_year_details',
                    'team_rosters',
                    'draft_class',
                    'draft_picks',
                    'draft_order',
                    'players',
                    'rivalries',
                    'dynasty_state',
                    'dynasties'
                ]

                for table in tables_to_clear:
                    try:
                        cursor.execute(
                            f"DELETE FROM {table} WHERE dynasty_id = ?",
                            (dynasty_id,)
                        )
                    except sqlite3.OperationalError:
                        # Table might not exist
                        pass

                conn.commit()
                return (True, None)

            finally:
                conn.close()

        except Exception as e:
            return (False, str(e))