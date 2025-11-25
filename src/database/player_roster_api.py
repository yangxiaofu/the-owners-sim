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
            # Check if draft_prospects table exists (it's created later during draft class generation)
            check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='draft_prospects'"

            if self.shared_conn:
                cursor = self.shared_conn.cursor()
                cursor.execute(check_query)
                draft_table_exists = cursor.fetchone() is not None
            else:
                result = self.db_connection.execute_query(check_query)
                draft_table_exists = len(result) > 0

            # Initialize counter - check BOTH tables if draft_prospects exists
            # This prevents ID collisions when draft prospects are created before rosters
            if draft_table_exists:
                # Query BOTH tables for maximum player_id
                query = """
                    SELECT COALESCE(
                        MAX(COALESCE(
                            (SELECT MAX(player_id) FROM players WHERE dynasty_id = ?),
                            (SELECT MAX(player_id) FROM draft_prospects WHERE dynasty_id = ?)
                        )), 0
                    ) as max_id
                """
                params = (dynasty_id, dynasty_id)
            else:
                # Fallback: Query ONLY players table (draft_prospects doesn't exist yet)
                query = "SELECT COALESCE(MAX(player_id), 0) as max_id FROM players WHERE dynasty_id = ?"
                params = (dynasty_id,)

            if self.shared_conn:
                cursor = self.shared_conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                max_id = result[0] if result else 0
            else:
                result = self.db_connection.execute_query(query, params)
                max_id = result[0]['max_id'] if result else 0

            self._player_id_counter[dynasty_id] = max_id + 1

        # Return current counter and increment
        player_id = self._player_id_counter[dynasty_id]
        self._player_id_counter[dynasty_id] += 1
        return player_id

    def initialize_dynasty_rosters(self, dynasty_id: str, season: int = 2025) -> int:
        """
        Load all 32 NFL team rosters + free agents from JSON → Database.
        Called ONLY when creating a new dynasty.

        Args:
            dynasty_id: Dynasty to initialize
            season: Starting season year for contract initialization (default: 2025)

        Returns:
            Total number of players loaded (team rosters + free agents)

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
        players_with_contracts = []  # Collect players with contract data

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
                        attributes=real_player.attributes,
                        birthdate=real_player.birthdate
                    )

                    # Add to roster with new player_id
                    self._add_to_roster(
                        dynasty_id=dynasty_id,
                        team_id=team_id,
                        player_id=new_player_id
                    )

                    # Collect contract data for later initialization
                    if real_player.contract:
                        players_with_contracts.append({
                            'player_id': new_player_id,
                            'team_id': team_id,
                            'contract': real_player.contract
                        })

                    players_inserted += 1

                teams_processed += 1
                self.logger.info(f"  Team {team_id}: {len(real_players)} players loaded")

            except Exception as e:
                self.logger.error(f"Failed to load team {team_id}: {e}")
                raise RuntimeError(f"Roster initialization failed at team {team_id}: {e}")

        self.logger.info(
            f"✅ Team roster initialization complete: "
            f"{players_inserted} players loaded across {teams_processed} teams"
        )

        # Load free agents (team_id = 0 in database)
        self.logger.info("📥 Loading free agents from free_agents.json...")
        try:
            free_agents = loader.get_free_agents()

            if free_agents:
                for free_agent in free_agents:
                    # Generate new unique player_id
                    new_player_id = self._get_next_player_id(dynasty_id)

                    # Insert free agent with team_id = 0 (no team)
                    self._insert_player(
                        dynasty_id=dynasty_id,
                        player_id=new_player_id,
                        source_player_id=str(free_agent.player_id),
                        first_name=free_agent.first_name,
                        last_name=free_agent.last_name,
                        number=free_agent.number if free_agent.number else 0,  # Use 0 if no number
                        team_id=0,  # Free agents have team_id = 0
                        positions=free_agent.positions,
                        attributes=free_agent.attributes,
                        birthdate=free_agent.birthdate
                    )

                    # NOTE: Do NOT add to team_rosters table - free agents aren't on any team

                    # Collect contract data if present (though free agents typically have null contracts)
                    if free_agent.contract:
                        players_with_contracts.append({
                            'player_id': new_player_id,
                            'team_id': 0,  # Free agents use team_id = 0
                            'contract': free_agent.contract
                        })

                    players_inserted += 1

                self.logger.info(f"✅ Free agent loading complete: {len(free_agents)} free agents loaded")
            else:
                self.logger.warning("⚠️  No free agents found in free_agents.json")

        except Exception as e:
            self.logger.error(f"Failed to load free agents: {e}")
            # Non-critical - continue with team rosters only

        self.logger.info(
            f"✅ Roster initialization complete: "
            f"{players_inserted} total players loaded ({teams_processed} teams + free agents)"
        )

        # Initialize contracts for all players
        if players_with_contracts:
            self._initialize_contracts(
                dynasty_id=dynasty_id,
                season=season,
                players_with_contracts=players_with_contracts
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
        return dict(result[0])['cnt'] > 0 if result else False

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
                p.birthdate,
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

        return roster  # Already converted to dicts by execute_query()

    def get_full_roster(self, dynasty_id: str, team_id: int) -> List[Dict[str, Any]]:
        """
        Load FULL team roster (active + inactive players).

        Unlike get_team_roster(), this method returns ALL players on the roster
        regardless of roster_status. Use for UI display and roster management.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries with all roster players (active + inactive)

        Raises:
            ValueError: If no roster found (database not initialized)
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
            ORDER BY tr.depth_chart_order, p.number
        """

        roster = self.db_connection.execute_query(query, (dynasty_id, team_id))

        if not roster:
            raise ValueError(
                f"❌ No roster found in database for dynasty '{dynasty_id}', team {team_id}.\n"
                f"   Database is not initialized. Create a new dynasty to load rosters."
            )

        return roster  # Already converted to dicts by execute_query()

    def get_free_agents(self, dynasty_id: str) -> List[Dict[str, Any]]:
        """
        Get all free agent players (players not on any team).

        Args:
            dynasty_id: Dynasty context

        Returns:
            List of player dictionaries for free agents (team_id = 0)
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
            ORDER BY p.last_name, p.first_name
        """

        free_agents = self.db_connection.execute_query(query, (dynasty_id,))
        return free_agents  # Already converted to dicts by execute_query()

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
        return result[0] if result else None  # Already converted to dict by execute_query()

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
        return dict(result[0])['cnt'] if result else 0

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
            attributes=player_data['attributes'],
            birthdate=player_data.get('birthdate')  # Optional birthdate
        )

        # Add to roster if on a team
        if team_id > 0:
            self._add_to_roster(dynasty_id, team_id, new_player_id)

        return new_player_id

    def _insert_player(self, dynasty_id: str, player_id: int,
                      source_player_id: str, first_name: str, last_name: str, number: int,
                      team_id: int, positions: List[str], attributes: Dict,
                      birthdate: Optional[str] = None) -> None:
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
            birthdate: Optional birthdate in YYYY-MM-DD format
        """
        query = """
            INSERT INTO players
                (dynasty_id, player_id, source_player_id, first_name, last_name, number,
                 team_id, positions, attributes, birthdate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(attributes),
            birthdate
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

    def _initialize_contracts(
        self,
        dynasty_id: str,
        season: int,
        players_with_contracts: List[Dict[str, Any]]
    ):
        """
        Initialize player contracts from JSON data (private method).

        Args:
            dynasty_id: Dynasty context
            season: Starting season year for contract initialization
            players_with_contracts: List of dicts with player_id, team_id, contract data
        """
        from salary_cap.contract_initializer import ContractInitializer

        # Use shared connection if in transaction mode, otherwise create own
        conn = self.shared_conn if self.shared_conn else self.db_connection.get_connection()

        try:
            contract_initializer = ContractInitializer(conn)

            # Create all contracts from JSON data
            contract_map = contract_initializer.initialize_contracts_from_json(
                dynasty_id=dynasty_id,
                season=season,
                players_with_contracts=players_with_contracts
            )

            # Link contract_id to players table
            contract_initializer.link_contracts_to_players(contract_map)

            self.logger.info(
                f"✅ Contract initialization complete: {len(contract_map)} contracts created"
            )

        except Exception as e:
            self.logger.error(f"Contract initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize contracts: {e}")
