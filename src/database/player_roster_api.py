"""
Player Roster Database API

Manages player rosters in database. JSON files used ONLY for initialization.

Architecture:
- JSON files preserved permanently (never deleted)
- JSON accessed ONLY during dynasty creation (one-time migration)
- Database is SOLE source during gameplay (no fallbacks)
- Dynasty isolation via dynasty_id foreign keys
"""

from typing import List, Dict, Any, Optional
from database.connection import DatabaseConnection
import sqlite3
import json
import logging


class PlayerRosterAPI:
    """Database-only player roster management with fail-fast error handling."""

    def __init__(self, database_path: str, connection: Optional[sqlite3.Connection] = None):
        """
        Initialize player roster API.

        Args:
            database_path: Path to SQLite database
            connection: Optional shared database connection for transaction mode.
                       If provided, all operations use this connection (no auto-commit).
                       If None, operations create their own connections (auto-commit).
        """
        self.db_connection = DatabaseConnection(database_path)
        self.shared_conn = connection  # Use for transaction mode
        self.logger = logging.getLogger("PlayerRosterAPI")
        self._player_id_counter = {}  # Track next player_id per dynasty

    def _get_next_player_id(self, dynasty_id: str) -> int:
        """
        Get next unique player_id for a dynasty.

        Args:
            dynasty_id: Dynasty context

        Returns:
            Next available player_id (auto-incrementing)
        """
        if dynasty_id not in self._player_id_counter:
            # Initialize counter - check database for max existing ID
            query = "SELECT COALESCE(MAX(player_id), 0) as max_id FROM players WHERE dynasty_id = ?"

            if self.shared_conn:
                cursor = self.shared_conn.cursor()
                cursor.execute(query, (dynasty_id,))
                result = cursor.fetchone()
                max_id = result[0] if result else 0
            else:
                result = self.db_connection.execute_query(query, (dynasty_id,))
                max_id = result[0]['max_id'] if result else 0

            self._player_id_counter[dynasty_id] = max_id + 1

        # Return current counter and increment
        player_id = self._player_id_counter[dynasty_id]
        self._player_id_counter[dynasty_id] += 1
        return player_id

    def initialize_dynasty_rosters(self, dynasty_id: str) -> int:
        """
        Load all 32 NFL team rosters from JSON → Database.
        Called ONLY when creating a new dynasty.

        Args:
            dynasty_id: Dynasty to initialize

        Returns:
            Total number of players loaded

        Raises:
            ValueError: If dynasty already has rosters
            FileNotFoundError: If JSON source files missing
            RuntimeError: If initialization fails
        """
        # Prevent re-initialization
        if self.dynasty_has_rosters(dynasty_id):
            raise ValueError(
                f"Dynasty '{dynasty_id}' already has rosters in database. "
                f"Cannot re-initialize. Delete dynasty first to start fresh."
            )

        self.logger.info(f"Initializing rosters for dynasty '{dynasty_id}' from JSON files...")

        # Load from JSON (ONLY time JSON is accessed during gameplay)
        try:
            from team_management.players.player_loader import PlayerDataLoader
            loader = PlayerDataLoader()
        except Exception as e:
            raise FileNotFoundError(f"Failed to load JSON player data: {e}")

        players_inserted = 0
        teams_processed = 0

        # Bulk insert all 32 teams
        for team_id in range(1, 33):
            try:
                real_players = loader.get_players_by_team(team_id)

                if not real_players:
                    self.logger.warning(f"No players found for team {team_id}")
                    continue

                # Insert each player for this team
                for real_player in real_players:
                    # Generate new unique player_id (auto-incrementing)
                    new_player_id = self._get_next_player_id(dynasty_id)

                    # Insert with auto-generated ID and source reference
                    self._insert_player(
                        dynasty_id=dynasty_id,
                        player_id=new_player_id,
                        source_player_id=str(real_player.player_id),
                        first_name=real_player.first_name,
                        last_name=real_player.last_name,
                        number=real_player.number,
                        team_id=team_id,
                        positions=real_player.positions,
                        attributes=real_player.attributes
                    )

                    # Add to roster with new player_id
                    self._add_to_roster(
                        dynasty_id=dynasty_id,
                        team_id=team_id,
                        player_id=new_player_id
                    )

                    players_inserted += 1

                teams_processed += 1
                self.logger.info(f"  Team {team_id}: {len(real_players)} players loaded")

            except Exception as e:
                self.logger.error(f"Failed to load team {team_id}: {e}")
                raise RuntimeError(f"Roster initialization failed at team {team_id}: {e}")

        self.logger.info(
            f"✅ Roster initialization complete: "
            f"{players_inserted} players loaded across {teams_processed} teams"
        )

        return players_inserted

    def dynasty_has_rosters(self, dynasty_id: str) -> bool:
        """
        Check if dynasty has player rosters in database.

        Args:
            dynasty_id: Dynasty to check

        Returns:
            True if dynasty has any players in database
        """
        query = "SELECT COUNT(*) as cnt FROM players WHERE dynasty_id = ?"
        result = self.db_connection.execute_query(query, (dynasty_id,))
        return result[0]['cnt'] > 0

    def get_team_roster(self, dynasty_id: str, team_id: int) -> List[Dict[str, Any]]:
        """
        Load team roster from DATABASE ONLY.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries from database

        Raises:
            ValueError: If no roster found (FAIL FAST - no JSON fallback)
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
                tr.depth_chart_order,
                tr.roster_status
            FROM players p
            JOIN team_rosters tr
                ON p.dynasty_id = tr.dynasty_id
                AND p.player_id = tr.player_id
            WHERE p.dynasty_id = ?
                AND p.team_id = ?
                AND tr.roster_status = 'active'
            ORDER BY tr.depth_chart_order, p.number
        """

        roster = self.db_connection.execute_query(query, (dynasty_id, team_id))

        if not roster:
            raise ValueError(
                f"❌ No roster found in database for dynasty '{dynasty_id}', team {team_id}.\n"
                f"   Database is not initialized. Create a new dynasty to load rosters."
            )

        return roster

    def get_player_by_id(self, dynasty_id: str, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get single player by ID.

        Args:
            dynasty_id: Dynasty context
            player_id: Player ID (auto-generated integer)

        Returns:
            Player dictionary or None if not found
        """
        query = """
            SELECT *
            FROM players
            WHERE dynasty_id = ? AND player_id = ?
        """

        result = self.db_connection.execute_query(query, (dynasty_id, player_id))
        return result[0] if result else None

    def get_roster_count(self, dynasty_id: str, team_id: int) -> int:
        """
        Get count of players on team roster.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)

        Returns:
            Number of players on roster
        """
        query = """
            SELECT COUNT(*) as cnt
            FROM team_rosters
            WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
        """

        result = self.db_connection.execute_query(query, (dynasty_id, team_id))
        return result[0]['cnt'] if result else 0

    def update_player_team(self, dynasty_id: str, player_id: int, new_team_id: int) -> None:
        """
        Move player to different team (trades, signings).

        Args:
            dynasty_id: Dynasty context
            player_id: Player to move (auto-generated integer)
            new_team_id: New team (1-32, or 0 for free agent)
        """
        # Update player's team_id
        update_player_query = """
            UPDATE players
            SET team_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE dynasty_id = ? AND player_id = ?
        """

        self.db_connection.execute_update(
            update_player_query,
            (new_team_id, dynasty_id, player_id)
        )

        # Update roster entry (or remove if free agent)
        if new_team_id == 0:
            # Free agent - remove from team roster
            delete_roster_query = """
                DELETE FROM team_rosters
                WHERE dynasty_id = ? AND player_id = ?
            """
            self.db_connection.execute_update(delete_roster_query, (dynasty_id, player_id))
        else:
            # Update roster entry (or create if doesn't exist)
            # First, try to update existing
            update_roster_query = """
                UPDATE team_rosters
                SET team_id = ?
                WHERE dynasty_id = ? AND player_id = ?
            """
            rows_affected = self.db_connection.execute_update(
                update_roster_query,
                (new_team_id, dynasty_id, player_id)
            )

            # If no rows updated, insert new roster entry
            if rows_affected == 0:
                self._add_to_roster(dynasty_id, new_team_id, player_id)

    def add_generated_player(self, dynasty_id: str, player_data: Dict[str, Any],
                           team_id: int) -> int:
        """
        Add newly generated player to database (draft, free agency, player generation).

        Args:
            dynasty_id: Dynasty context
            player_data: Player attributes dict
                Required keys: first_name, last_name, number, positions, attributes
                Optional keys: player_id (used as source_player_id if provided)
            team_id: Team to add player to (1-32, or 0 for free agent)

        Returns:
            player_id of inserted player (auto-generated integer)

        Raises:
            ValueError: If required player_data fields missing
        """
        required_fields = ['first_name', 'last_name', 'number', 'positions', 'attributes']
        missing_fields = [f for f in required_fields if f not in player_data]

        if missing_fields:
            raise ValueError(f"Missing required player fields: {missing_fields}")

        # Generate new unique player_id (auto-incrementing)
        new_player_id = self._get_next_player_id(dynasty_id)

        # Use provided player_id as source reference, or generate synthetic one
        source_player_id = str(player_data.get('player_id', f'GENERATED_{new_player_id}'))

        # Insert player with auto-generated ID
        self._insert_player(
            dynasty_id=dynasty_id,
            player_id=new_player_id,
            source_player_id=source_player_id,
            first_name=player_data['first_name'],
            last_name=player_data['last_name'],
            number=player_data['number'],
            team_id=team_id,
            positions=player_data['positions'],
            attributes=player_data['attributes']
        )

        # Add to roster if on a team
        if team_id > 0:
            self._add_to_roster(dynasty_id, team_id, new_player_id)

        return new_player_id

    def _insert_player(self, dynasty_id: str, player_id: int,
                      source_player_id: str, first_name: str, last_name: str, number: int,
                      team_id: int, positions: List[str], attributes: Dict) -> None:
        """
        Insert player into database (private method).

        Args:
            dynasty_id: Dynasty context
            player_id: Auto-generated unique player ID (integer)
            source_player_id: Original JSON player_id (for reference)
            first_name: First name
            last_name: Last name
            number: Jersey number
            team_id: Team ID (0-32)
            positions: List of positions player can play
            attributes: Dict of player attributes/ratings
        """
        query = """
            INSERT INTO players
                (dynasty_id, player_id, source_player_id, first_name, last_name, number,
                 team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            dynasty_id,
            player_id,
            source_player_id,
            first_name,
            last_name,
            number,
            team_id,
            json.dumps(positions),
            json.dumps(attributes)
        )

        # Use shared connection if in transaction mode, otherwise create own
        if self.shared_conn:
            cursor = self.shared_conn.cursor()
            cursor.execute(query, params)
        else:
            self.db_connection.execute_update(query, params)

    def _add_to_roster(self, dynasty_id: str, team_id: int,
                       player_id: int, depth_order: int = 99) -> None:
        """
        Add player to team roster (private method).

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            player_id: Player ID (auto-generated integer)
            depth_order: Depth chart position (lower = higher)
        """
        query = """
            INSERT INTO team_rosters
                (dynasty_id, team_id, player_id, depth_chart_order)
            VALUES (?, ?, ?, ?)
        """

        params = (dynasty_id, team_id, player_id, depth_order)

        # Use shared connection if in transaction mode, otherwise create own
        if self.shared_conn:
            cursor = self.shared_conn.cursor()
            cursor.execute(query, params)
        else:
            self.db_connection.execute_update(query, params)
