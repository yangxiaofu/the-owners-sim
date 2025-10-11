"""
Dynasty Controller for The Owner's Sim UI

Mediates between Dynasty Selection UI and database for dynasty management.
Handles dynasty creation, validation, and retrieval operations.
"""

from typing import List, Dict, Any, Optional, Tuple
import sys
import os
from datetime import datetime

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.connection import DatabaseConnection


class DynastyController:
    """
    Controller for Dynasty management operations.

    Manages dynasty lifecycle: creation, validation, retrieval.
    Follows the pattern: Dialog → Controller → Database

    Separation of concerns:
    - DynastyController: Dynasty CRUD operations (THIS)
    - SeasonController: Season management and calendar operations
    - LeagueController: League-wide statistics
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize dynasty controller.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)

    def list_existing_dynasties(self) -> List[Dict[str, Any]]:
        """
        Get all existing dynasties from database.

        Returns:
            List of dicts with dynasty metadata:
            - dynasty_id: Unique dynasty identifier
            - dynasty_name: Display name
            - owner_name: Owner's name
            - team_id: User's team (nullable)
            - created_at: Creation timestamp
            - is_active: Active status
        """
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
                'dynasty_id': row[0],
                'dynasty_name': row[1],
                'owner_name': row[2],
                'team_id': row[3],
                'created_at': row[4],
                'is_active': bool(row[5])
            })

        return dynasties

    def dynasty_exists(self, dynasty_id: str) -> bool:
        """
        Check if a dynasty ID already exists.

        Args:
            dynasty_id: Dynasty identifier to check

        Returns:
            True if dynasty exists, False otherwise
        """
        query = "SELECT COUNT(*) FROM dynasties WHERE dynasty_id = ?"
        result = self.db.execute_query(query, (dynasty_id,))
        return result[0][0] > 0 if result else False

    def validate_dynasty_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a dynasty name for creation.

        Args:
            name: Dynasty name to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid
        """
        # Check for empty/whitespace only
        if not name or name.strip() == "":
            return (False, "Dynasty name cannot be empty")

        # Check length constraints
        if len(name) < 3:
            return (False, "Dynasty name must be at least 3 characters")

        if len(name) > 50:
            return (False, "Dynasty name must be 50 characters or less")

        # Check for special characters (allow letters, numbers, spaces, hyphens, apostrophes)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'")
        if not all(c in allowed_chars for c in name):
            return (False, "Dynasty name contains invalid characters (use letters, numbers, spaces, hyphens, apostrophes only)")

        return (True, None)

    def generate_unique_dynasty_id(self, base_name: str) -> str:
        """
        Generate a unique dynasty ID from a base name.

        Strategy:
        1. Convert name to lowercase, replace spaces with underscores
        2. If unique, return it
        3. If not, append _001, _002, etc. until unique

        Args:
            base_name: Base dynasty name

        Returns:
            Unique dynasty_id string
        """
        # Sanitize base name
        base_id = base_name.lower().strip()
        base_id = base_id.replace(" ", "_")
        base_id = base_id.replace("'", "")
        base_id = base_id.replace("-", "_")

        # Remove any non-alphanumeric characters (except underscores)
        base_id = ''.join(c for c in base_id if c.isalnum() or c == '_')

        # Try base ID first
        if not self.dynasty_exists(base_id):
            return base_id

        # Append incrementing suffix until unique
        counter = 1
        while True:
            candidate_id = f"{base_id}_{counter:03d}"
            if not self.dynasty_exists(candidate_id):
                return candidate_id
            counter += 1

            # Safety check - prevent infinite loop
            if counter > 999:
                # Fall back to large counter (highly unlikely to be reached)
                import random
                random_suffix = random.randint(10000, 99999)
                return f"{base_id}_{random_suffix}"

    def create_dynasty(
        self,
        dynasty_name: str,
        owner_name: str = "User",
        team_id: Optional[int] = None,
        season: int = 2025
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new dynasty with initialization.

        Args:
            dynasty_name: Display name for the dynasty
            owner_name: Owner's name (default: "User")
            team_id: User's team ID 1-32 (optional)
            season: Starting season year (default: 2025)

        Returns:
            Tuple of (success, dynasty_id, error_message)
            - (True, dynasty_id, None) if successful
            - (False, "", "error message") if failed
        """
        # Validate dynasty name
        is_valid, error_msg = self.validate_dynasty_name(dynasty_name)
        if not is_valid:
            return (False, "", error_msg)

        # Generate unique dynasty ID
        dynasty_id = self.generate_unique_dynasty_id(dynasty_name)

        # Create dynasty in database with initialization
        # Everything in one transaction for atomicity
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # Step 1: Create dynasty record
            cursor.execute('''
                INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, is_active)
                VALUES (?, ?, ?, ?, TRUE)
            ''', (dynasty_id, dynasty_name, owner_name, team_id))

            # Step 2: Initialize standings for all 32 NFL teams (0-0-0 records)
            for tid in range(1, 33):
                cursor.execute('''
                    INSERT INTO standings
                    (dynasty_id, season, team_id, wins, losses, ties,
                     points_for, points_against, division_wins, division_losses,
                     conference_wins, conference_losses)
                    VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                ''', (dynasty_id, season, tid))

            # Step 3: Initialize player rosters from JSON → Database (ONE-TIME)
            print(f"📥 Initializing player rosters for dynasty '{dynasty_id}'...")
            print(f"   Loading from JSON files (one-time migration)...")

            from database.player_roster_api import PlayerRosterAPI
            # Pass shared connection so all operations use same transaction
            roster_api = PlayerRosterAPI(self.db_path, connection=conn)

            players_loaded = roster_api.initialize_dynasty_rosters(dynasty_id, season)

            print(f"✅ Loaded {players_loaded} players from JSON → Database")
            print(f"   Rosters for all 32 teams initialized")

            # Step 3.5: Auto-generate depth charts for all 32 teams
            print(f"📊 Auto-generating depth charts for all 32 teams...")
            from depth_chart.depth_chart_api import DepthChartAPI
            depth_chart_api = DepthChartAPI(self.db_path)

            depth_charts_created = 0
            for team_id in range(1, 33):
                # Pass shared connection to avoid database lock
                success = depth_chart_api.auto_generate_depth_chart(dynasty_id, team_id, connection=conn)
                if success:
                    depth_charts_created += 1
                else:
                    print(f"[WARNING] Failed to generate depth chart for team {team_id}")

            print(f"✅ Depth charts auto-generated for {depth_charts_created}/32 teams (sorted by overall rating)")

            # Step 4: Commit dynasty + standings + rosters + depth charts atomically
            # Must commit BEFORE schedule generation (which creates its own connections)
            conn.commit()
            print(f"✅ Dynasty '{dynasty_id}' committed to database")

            # Step 5: Generate initial season schedule (separate transaction)
            # Note: Schedule generation creates its own database connections
            # so we must commit the dynasty first to avoid database locks
            try:
                from .season_controller import SeasonController
                season_controller = SeasonController(
                    db_path=self.db_path,
                    dynasty_id=dynasty_id,
                    season=season
                )

                schedule_success, schedule_error = season_controller.generate_initial_schedule()
                if not schedule_success:
                    print(f"[WARNING DynastyController] Schedule generation failed: {schedule_error}")
                    # Dynasty creation succeeded, but schedule generation failed
                    # User can manually generate schedule later
            except Exception as schedule_ex:
                print(f"[WARNING DynastyController] Schedule generation error: {schedule_ex}")
                # Non-critical - dynasty is already committed

            # Step 6: CRITICAL - Verify dynasty_state was created by schedule generation
            # This ensures next load will have proper state
            from database.dynasty_state_api import DynastyStateAPI
            dynasty_state_api = DynastyStateAPI(self.db_path)

            state = dynasty_state_api.get_current_state(dynasty_id, season)
            if not state:
                print(f"[WARNING DynastyController] Dynasty state missing after schedule generation!")
                print(f"[INFO DynastyController] Creating fallback dynasty_state...")

                # Create dynasty_state as fallback (Sept 4 - one day before first games)
                fallback_success = dynasty_state_api.initialize_state(
                    dynasty_id=dynasty_id,
                    season=season,
                    start_date=f"{season}-09-04",
                    start_week=1,
                    start_phase='regular_season'
                )

                if fallback_success:
                    print(f"✅ Fallback dynasty_state created successfully")
                else:
                    print(f"[ERROR DynastyController] CRITICAL: Failed to create dynasty_state!")
                    print(f"Dynasty '{dynasty_id}' may have persistence issues on next load")
            else:
                print(f"✅ Dynasty state verified: {state['current_date']}")

            return (True, dynasty_id, None)

        except Exception as e:
            # Rollback entire transaction on any failure
            conn.rollback()
            error_message = f"Failed to create dynasty: {str(e)}"
            print(f"[ERROR DynastyController] {error_message}")
            return (False, "", error_message)

    def get_dynasty_info(self, dynasty_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty metadata or None if not found
        """
        query = """
            SELECT dynasty_id, dynasty_name, owner_name, team_id,
                   created_at, is_active
            FROM dynasties
            WHERE dynasty_id = ?
        """

        result = self.db.execute_query(query, (dynasty_id,))

        if not result:
            return None

        row = result[0]
        return {
            'dynasty_id': row[0],
            'dynasty_name': row[1],
            'owner_name': row[2],
            'team_id': row[3],
            'created_at': row[4],
            'is_active': bool(row[5])
        }

    def get_dynasty_stats(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get statistics about a dynasty (seasons played, games, etc.).

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty statistics
        """
        # Query for seasons played
        seasons_query = """
            SELECT DISTINCT season
            FROM standings
            WHERE dynasty_id = ?
            ORDER BY season DESC
        """
        seasons_result = self.db.execute_query(seasons_query, (dynasty_id,))
        seasons_played = [row[0] for row in seasons_result] if seasons_result else []

        # Query for total games played
        games_query = """
            SELECT COUNT(*)
            FROM games
            WHERE dynasty_id = ?
        """
        games_result = self.db.execute_query(games_query, (dynasty_id,))
        total_games = games_result[0][0] if games_result else 0

        return {
            'seasons_played': seasons_played,
            'total_seasons': len(seasons_played),
            'total_games': total_games,
            'current_season': seasons_played[0] if seasons_played else None
        }

    def delete_dynasty(self, dynasty_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a dynasty and all associated data.

        WARNING: This is a destructive operation that cannot be undone.

        Args:
            dynasty_id: Dynasty identifier to delete

        Returns:
            Tuple of (success, error_message)
            - (True, None) if successful
            - (False, "error message") if failed
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # Delete in reverse order of foreign key dependencies
            # CASCADE delete should handle most of this, but being explicit

            # Delete player rosters
            cursor.execute("DELETE FROM team_rosters WHERE dynasty_id = ?", (dynasty_id,))

            # Delete players
            cursor.execute("DELETE FROM players WHERE dynasty_id = ?", (dynasty_id,))

            # Delete box scores
            cursor.execute("DELETE FROM box_scores WHERE dynasty_id = ?", (dynasty_id,))

            # Delete player game stats
            cursor.execute("DELETE FROM player_game_stats WHERE dynasty_id = ?", (dynasty_id,))

            # Delete games
            cursor.execute("DELETE FROM games WHERE dynasty_id = ?", (dynasty_id,))

            # Delete standings
            cursor.execute("DELETE FROM standings WHERE dynasty_id = ?", (dynasty_id,))

            # Delete schedules
            cursor.execute("DELETE FROM schedules WHERE dynasty_id = ?", (dynasty_id,))

            # Delete events
            cursor.execute("DELETE FROM events WHERE dynasty_id = ?", (dynasty_id,))

            # Delete playoff data
            cursor.execute("DELETE FROM playoff_brackets WHERE dynasty_id = ?", (dynasty_id,))
            cursor.execute("DELETE FROM playoff_seedings WHERE dynasty_id = ?", (dynasty_id,))
            cursor.execute("DELETE FROM tiebreaker_applications WHERE dynasty_id = ?", (dynasty_id,))

            # Delete dynasty state and seasons
            cursor.execute("DELETE FROM dynasty_state WHERE dynasty_id = ?", (dynasty_id,))
            cursor.execute("DELETE FROM dynasty_seasons WHERE dynasty_id = ?", (dynasty_id,))

            # Finally, delete dynasty record
            cursor.execute("DELETE FROM dynasties WHERE dynasty_id = ?", (dynasty_id,))

            conn.commit()
            return (True, None)

        except Exception as e:
            conn.rollback()
            error_message = f"Failed to delete dynasty: {str(e)}"
            print(f"[ERROR DynastyController] {error_message}")
            return (False, error_message)
