"""
Dynasty Database API

Centralized API for all dynasty-related database operations.
Provides clean interface for dynasty CRUD and standings initialization.

This is the SINGLE SOURCE OF TRUTH for dynasty database operations.
All controllers and services should use this API instead of raw SQL queries.
"""

from typing import Optional, Dict, Any, List
import logging
import sqlite3

from .connection import DatabaseConnection


class DynastyDatabaseAPI:
    """
    API for managing dynasty database operations.

    Handles all database operations for the dynasties table and related
    standings initialization operations.

    This API follows the transaction-aware pattern:
    - Accepts optional `connection` parameter for transaction participation
    - Creates own connection when not provided
    - Returns dicts for UI flexibility
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Dynasty Database API.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_dynasty_record(
        self,
        dynasty_id: str,
        dynasty_name: str,
        owner_name: str,
        team_id: Optional[int] = None,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Create a new dynasty record in the database.

        Args:
            dynasty_id: Unique dynasty identifier (lowercase, underscores)
            dynasty_name: Display name for the dynasty
            owner_name: Owner's name
            team_id: User's team ID (1-32) or None for commissioner mode
            connection: Optional shared connection for transaction participation

        Returns:
            True if successful, False otherwise

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> success = api.create_dynasty_record(
            ...     dynasty_id="eagles_dynasty",
            ...     dynasty_name="Eagles Dynasty",
            ...     owner_name="User",
            ...     team_id=22
            ... )
            >>> assert success
        """
        try:
            query = """
                INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, is_active)
                VALUES (?, ?, ?, ?, TRUE)
            """

            if connection:
                # Use shared connection (transaction participation)
                cursor = connection.cursor()
                cursor.execute(query, (dynasty_id, dynasty_name, owner_name, team_id))
                # Don't commit - let caller manage transaction
                self.logger.debug(f"Created dynasty record: {dynasty_id} (shared transaction)")
            else:
                # Use own connection (auto-commit)
                self.db.execute_update(query, (dynasty_id, dynasty_name, owner_name, team_id))
                self.logger.info(f"Created dynasty record: {dynasty_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error creating dynasty record: {e}", exc_info=True)
            return False

    def initialize_standings_for_season_type(
        self,
        dynasty_id: str,
        season: int,
        season_type: str,
        connection: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Initialize 0-0-0 standings for all 32 NFL teams for a specific season type.

        Creates 32 standings records (one per team) with zero wins/losses/ties.
        This method should be called twice for each season:
        - Once with season_type='preseason'
        - Once with season_type='regular_season'

        Args:
            dynasty_id: Dynasty identifier
            season: Season year (e.g., 2025)
            season_type: 'preseason', 'regular_season', or 'playoffs'
            connection: Optional shared connection for transaction participation

        Returns:
            Number of standings records created (should be 32)

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> # Initialize preseason standings
            >>> count = api.initialize_standings_for_season_type(
            ...     dynasty_id="eagles_dynasty",
            ...     season=2025,
            ...     season_type="preseason"
            ... )
            >>> assert count == 32
        """
        try:
            if connection:
                cursor = connection.cursor()
            else:
                cursor = self.db.get_connection().cursor()

            # Insert 32 standings records (team_id 1-32)
            query = """
                INSERT INTO standings
                (dynasty_id, season, team_id, season_type, wins, losses, ties,
                 points_for, points_against, division_wins, division_losses,
                 conference_wins, conference_losses)
                VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            """

            records_created = 0
            for team_id in range(1, 33):
                cursor.execute(query, (dynasty_id, season, team_id, season_type))
                records_created += 1

            if not connection:
                # Auto-commit if using own connection
                cursor.connection.commit()

            self.logger.info(
                f"Initialized {records_created} {season_type} standings for dynasty {dynasty_id}, season {season}"
            )

            return records_created

        except Exception as e:
            self.logger.error(
                f"Error initializing standings for {season_type}: {e}",
                exc_info=True
            )
            if not connection:
                cursor.connection.rollback()
            return 0

    def dynasty_exists(self, dynasty_id: str) -> bool:
        """
        Check if a dynasty ID already exists in the database.

        Args:
            dynasty_id: Dynasty identifier to check

        Returns:
            True if dynasty exists, False otherwise

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> exists = api.dynasty_exists("eagles_dynasty")
            >>> if not exists:
            ...     # Safe to create new dynasty
            ...     pass
        """
        try:
            query = "SELECT COUNT(*) as count FROM dynasties WHERE dynasty_id = ?"
            result = self.db.execute_query(query, (dynasty_id,))

            if result and len(result) > 0:
                count = result[0]['count']
                return count > 0

            return False

        except Exception as e:
            self.logger.error(f"Error checking dynasty existence: {e}", exc_info=True)
            return False

    def get_dynasty_by_id(self, dynasty_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty metadata:
            {
                'dynasty_id': str,
                'dynasty_name': str,
                'owner_name': str,
                'team_id': Optional[int],
                'created_at': str,
                'is_active': bool
            }
            Or None if not found

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> dynasty = api.get_dynasty_by_id("eagles_dynasty")
            >>> if dynasty:
            ...     print(f"Owner: {dynasty['owner_name']}")
        """
        try:
            query = """
                SELECT dynasty_id, dynasty_name, owner_name, team_id,
                       created_at, is_active
                FROM dynasties
                WHERE dynasty_id = ?
            """

            result = self.db.execute_query(query, (dynasty_id,))

            if not result or len(result) == 0:
                return None

            row = result[0]
            return {
                'dynasty_id': row['dynasty_id'],
                'dynasty_name': row['dynasty_name'],
                'owner_name': row['owner_name'],
                'team_id': row['team_id'],
                'created_at': row['created_at'],
                'is_active': bool(row['is_active'])
            }

        except Exception as e:
            self.logger.error(f"Error getting dynasty by ID: {e}", exc_info=True)
            return None

    def get_all_dynasties(self) -> List[Dict[str, Any]]:
        """
        Get all existing dynasties from database.

        Returns:
            List of dicts with dynasty metadata, ordered by created_at DESC

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> dynasties = api.get_all_dynasties()
            >>> for dynasty in dynasties:
            ...     print(f"{dynasty['dynasty_name']} - {dynasty['owner_name']}")
        """
        try:
            query = """
                SELECT dynasty_id, dynasty_name, owner_name, team_id,
                       created_at, is_active
                FROM dynasties
                ORDER BY created_at DESC
            """

            results = self.db.execute_query(query)

            dynasties = []
            for row in results:
                dynasties.append({
                    'dynasty_id': row['dynasty_id'],
                    'dynasty_name': row['dynasty_name'],
                    'owner_name': row['owner_name'],
                    'team_id': row['team_id'],
                    'created_at': row['created_at'],
                    'is_active': bool(row['is_active'])
                })

            return dynasties

        except Exception as e:
            self.logger.error(f"Error getting all dynasties: {e}", exc_info=True)
            return []

    def get_dynasty_stats(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get statistics about a dynasty (seasons played, games, etc.).

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty statistics:
            {
                'seasons_played': List[int],     # List of season years
                'total_seasons': int,            # Count of seasons
                'total_games': int,              # Count of games played
                'current_season': Optional[int]  # Most recent season
            }

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> stats = api.get_dynasty_stats("eagles_dynasty")
            >>> print(f"Seasons played: {stats['total_seasons']}")
        """
        try:
            # Query for seasons played
            seasons_query = """
                SELECT DISTINCT season
                FROM standings
                WHERE dynasty_id = ?
                ORDER BY season DESC
            """
            seasons_result = self.db.execute_query(seasons_query, (dynasty_id,))
            seasons_played = [row['season'] for row in seasons_result] if seasons_result else []

            # Query for total games played
            games_query = """
                SELECT COUNT(*) as count
                FROM games
                WHERE dynasty_id = ?
            """
            games_result = self.db.execute_query(games_query, (dynasty_id,))
            total_games = games_result[0]['count'] if games_result else 0

            return {
                'seasons_played': seasons_played,
                'total_seasons': len(seasons_played),
                'total_games': total_games,
                'current_season': seasons_played[0] if seasons_played else None
            }

        except Exception as e:
            self.logger.error(f"Error getting dynasty stats: {e}", exc_info=True)
            return {
                'seasons_played': [],
                'total_seasons': 0,
                'total_games': 0,
                'current_season': None
            }

    def delete_dynasty(
        self,
        dynasty_id: str,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Delete a dynasty and all associated data.

        WARNING: This is a destructive operation that cannot be undone.
        Deletes all related data in proper dependency order.

        Args:
            dynasty_id: Dynasty identifier to delete
            connection: Optional shared connection for transaction participation

        Returns:
            True if successful, False otherwise

        Example:
            >>> api = DynastyDatabaseAPI()
            >>> success = api.delete_dynasty("old_dynasty")
            >>> assert success
        """
        try:
            if connection:
                cursor = connection.cursor()
            else:
                cursor = self.db.get_connection().cursor()

            # Delete in reverse order of foreign key dependencies
            # CASCADE delete should handle most of this, but being explicit

            delete_operations = [
                ("team_rosters", "DELETE FROM team_rosters WHERE dynasty_id = ?"),
                ("players", "DELETE FROM players WHERE dynasty_id = ?"),
                ("box_scores", "DELETE FROM box_scores WHERE dynasty_id = ?"),
                ("player_game_stats", "DELETE FROM player_game_stats WHERE dynasty_id = ?"),
                ("games", "DELETE FROM games WHERE dynasty_id = ?"),
                ("standings", "DELETE FROM standings WHERE dynasty_id = ?"),
                ("schedules", "DELETE FROM schedules WHERE dynasty_id = ?"),
                ("events", "DELETE FROM events WHERE dynasty_id = ?"),
                ("playoff_brackets", "DELETE FROM playoff_brackets WHERE dynasty_id = ?"),
                ("playoff_seedings", "DELETE FROM playoff_seedings WHERE dynasty_id = ?"),
                ("tiebreaker_applications", "DELETE FROM tiebreaker_applications WHERE dynasty_id = ?"),
                ("dynasty_state", "DELETE FROM dynasty_state WHERE dynasty_id = ?"),
                ("dynasty_seasons", "DELETE FROM dynasty_seasons WHERE dynasty_id = ?"),
                ("dynasties", "DELETE FROM dynasties WHERE dynasty_id = ?"),
            ]

            for table_name, query in delete_operations:
                try:
                    cursor.execute(query, (dynasty_id,))
                    self.logger.debug(f"Deleted {table_name} records for dynasty {dynasty_id}")
                except sqlite3.OperationalError as e:
                    # Table might not exist - that's okay
                    self.logger.debug(f"Skipping {table_name}: {e}")

            if not connection:
                # Auto-commit if using own connection
                cursor.connection.commit()

            self.logger.info(f"Deleted dynasty: {dynasty_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting dynasty: {e}", exc_info=True)
            if not connection:
                cursor.connection.rollback()
            return False