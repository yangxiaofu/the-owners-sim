"""
Game Cycle Dynasty Initialization Service.

Initializes game_cycle.db with player and contract data from JSON files.
This is separate from the main.py DynastyInitializationService to maintain
database separation between main.py (nfl_simulation.db) and main2.py (game_cycle.db).

Architecture:
- Loads player rosters from src/data/players/team_*.json
- Creates player records in players table
- Creates team_rosters entries
- Initializes contracts using ContractInitializer pattern
- Dynasty-isolated with dynasty_id as SSOT

Usage:
    initializer = GameCycleInitializer(
        db_path="data/database/game_cycle/game_cycle.db",
        dynasty_id="my_dynasty",
        season=2025
    )
    initializer.initialize_dynasty(team_id=22)  # Detroit Lions
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging


class GameCycleInitializer:
    """
    Initializes game_cycle.db with player roster and contract data.

    Loads data from src/data/players/*.json files and creates:
    - players table entries (all 32 teams + free agents)
    - team_rosters entries (depth chart tracking)
    - player_contracts entries (salary cap data)
    - contract_year_details entries (year-by-year breakdown)

    Dynasty Isolation:
    - All data scoped to dynasty_id
    - player_id auto-generated per dynasty (avoids collisions)
    - Prevents duplicate initialization
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize game cycle initializer.

        Args:
            db_path: Path to game_cycle.db database
            dynasty_id: Dynasty identifier (SSOT for all operations)
            season: Starting season year for contract initialization (default: 2025)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)
        self._player_id_counter = 0  # Track next player_id

    def initialize_dynasty(self, team_id: int) -> bool:
        """
        Initialize dynasty with players and contracts from JSON.

        This method:
        1. Applies schema (creates tables if missing)
        2. Checks if dynasty already initialized (prevents duplicates)
        3. Creates dynasty record
        4. Loads all 32 team rosters from JSON files
        5. Loads free agents from free_agents.json
        6. Creates contracts for all players with contract data

        Args:
            team_id: User's team ID (1-32)

        Returns:
            True if successful

        Raises:
            ValueError: If dynasty already initialized
            FileNotFoundError: If JSON files not found
            RuntimeError: If initialization fails
        """
        self._logger.info(f"Initializing dynasty '{self._dynasty_id}' for team {team_id}")

        conn = sqlite3.connect(self._db_path)
        try:
            # 1. Apply schema
            self._apply_schema(conn)

            # 2. Check if already initialized
            if self._dynasty_exists(conn):
                raise ValueError(
                    f"Dynasty '{self._dynasty_id}' already has data. "
                    f"Cannot re-initialize. Delete dynasty first to start fresh."
                )

            # 3. Create dynasty record
            self._create_dynasty_record(conn, team_id)

            # 4. Load players from JSON (all 32 teams + free agents)
            players_with_contracts = self._load_players_from_json(conn)

            # 5. Create contracts
            self._create_contracts(conn, players_with_contracts)

            # Commit all changes
            conn.commit()

            # 6. Generate draft class for current year (AFTER commit so DraftClassAPI has data)
            self._generate_initial_draft_class()

            self._logger.info(
                f"✅ Dynasty '{self._dynasty_id}' initialized successfully "
                f"({self._player_id_counter} players loaded)"
            )
            return True

        except ValueError:
            # Re-raise ValueError (dynasty already exists) without wrapping
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            self._logger.error(f"Dynasty initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize dynasty: {e}")
        finally:
            conn.close()

    def _apply_schema(self, conn: sqlite3.Connection):
        """
        Ensure required tables exist in the database.

        If DynastyInitializationService already created the schema (which happens
        when using DynastySelectionDialog), we skip applying our schema.
        Only apply full_schema.sql if essential tables are missing.

        Args:
            conn: Database connection
        """
        cursor = conn.cursor()

        # Check if essential tables already exist (from DynastyInitializationService)
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('dynasties', 'players', 'player_contracts')
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}

        required_tables = {'dynasties', 'players', 'player_contracts'}

        if required_tables.issubset(existing_tables):
            self._logger.info("✅ Schema already exists (from DynastyInitializationService)")
            return

        # Tables missing - apply full schema
        project_root = Path(__file__).parent.parent.parent.parent
        schema_path = project_root / "src" / "game_cycle" / "database" / "full_schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        self._logger.info(f"Applying schema from {schema_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Make schema idempotent - convert CREATE TABLE to CREATE TABLE IF NOT EXISTS
        import re
        schema_sql = re.sub(
            r'CREATE TABLE(?!\s+IF\s+NOT\s+EXISTS)',
            'CREATE TABLE IF NOT EXISTS',
            schema_sql,
            flags=re.IGNORECASE
        )
        schema_sql = re.sub(
            r'CREATE INDEX(?!\s+IF\s+NOT\s+EXISTS)',
            'CREATE INDEX IF NOT EXISTS',
            schema_sql,
            flags=re.IGNORECASE
        )
        schema_sql = re.sub(
            r'CREATE UNIQUE INDEX(?!\s+IF\s+NOT\s+EXISTS)',
            'CREATE UNIQUE INDEX IF NOT EXISTS',
            schema_sql,
            flags=re.IGNORECASE
        )

        cursor.executescript(schema_sql)
        self._logger.info("✅ Schema applied successfully")

    def _dynasty_exists(self, conn: sqlite3.Connection) -> bool:
        """
        Check if dynasty already has data.

        Args:
            conn: Database connection

        Returns:
            True if dynasty has players in database
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM players WHERE dynasty_id = ?",
            (self._dynasty_id,)
        )
        count = cursor.fetchone()[0]
        return count > 0

    def _create_dynasty_record(self, conn: sqlite3.Connection, team_id: int):
        """
        Create dynasty and dynasty_state records.

        Args:
            conn: Database connection
            team_id: User's team ID (1-32)
        """
        cursor = conn.cursor()

        # Create dynasty record
        cursor.execute('''
            INSERT INTO dynasties (
                dynasty_id, dynasty_name, owner_name, team_id,
                total_seasons, is_active
            ) VALUES (?, ?, ?, ?, 0, TRUE)
        ''', (
            self._dynasty_id,
            f"Dynasty {self._dynasty_id}",
            "Owner",  # Default owner name
            team_id
        ))

        self._logger.info(f"✅ Created dynasty record for '{self._dynasty_id}' (Team {team_id})")

    def _load_players_from_json(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """
        Load all players from JSON files and insert into database.

        Loads:
        - All 32 team rosters from team_XX_*.json files
        - Free agents from free_agents.json (if exists)

        Args:
            conn: Database connection

        Returns:
            List of players with contract data for later initialization

        Raises:
            FileNotFoundError: If JSON files not found
        """
        # Import PlayerDataLoader to load JSON files
        try:
            from team_management.players.player_loader import PlayerDataLoader
            loader = PlayerDataLoader()
        except Exception as e:
            raise FileNotFoundError(f"Failed to load JSON player data: {e}")

        # Initialize player_id counter
        self._initialize_player_id_counter(conn)

        players_with_contracts = []
        players_inserted = 0
        teams_processed = 0

        # Load all 32 teams
        self._logger.info("Loading player rosters from JSON files...")
        for team_id in range(1, 33):
            try:
                real_players = loader.get_players_by_team(team_id)

                if not real_players:
                    self._logger.warning(f"No players found for team {team_id}")
                    continue

                # Insert each player for this team
                for real_player in real_players:
                    # Generate new unique player_id
                    new_player_id = self._get_next_player_id()

                    # Insert player
                    self._insert_player(
                        conn=conn,
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

                    # Add to team roster
                    self._add_to_roster(
                        conn=conn,
                        team_id=team_id,
                        player_id=new_player_id
                    )

                    # Collect contract data if present
                    if real_player.contract:
                        players_with_contracts.append({
                            'player_id': new_player_id,
                            'team_id': team_id,
                            'contract': real_player.contract
                        })

                    players_inserted += 1

                teams_processed += 1
                self._logger.info(f"  Team {team_id}: {len(real_players)} players loaded")

            except Exception as e:
                self._logger.error(f"Failed to load team {team_id}: {e}")
                raise RuntimeError(f"Roster initialization failed at team {team_id}: {e}")

        # Load free agents (if file exists)
        self._logger.info("Loading free agents from free_agents.json...")
        try:
            free_agents = loader.get_free_agents()

            if free_agents:
                for free_agent in free_agents:
                    # Generate new unique player_id
                    new_player_id = self._get_next_player_id()

                    # Insert free agent with team_id = 0
                    self._insert_player(
                        conn=conn,
                        player_id=new_player_id,
                        source_player_id=str(free_agent.player_id),
                        first_name=free_agent.first_name,
                        last_name=free_agent.last_name,
                        number=free_agent.number if free_agent.number else 0,
                        team_id=0,  # Free agents
                        positions=free_agent.positions,
                        attributes=free_agent.attributes,
                        birthdate=free_agent.birthdate
                    )

                    # Note: Do NOT add to team_rosters - free agents not on team

                    # Collect contract data if present
                    if free_agent.contract:
                        players_with_contracts.append({
                            'player_id': new_player_id,
                            'team_id': 0,
                            'contract': free_agent.contract
                        })

                    players_inserted += 1

                self._logger.info(f"  Free agents: {len(free_agents)} players loaded")
            else:
                self._logger.warning("No free agents found in free_agents.json")

        except Exception as e:
            self._logger.error(f"Failed to load free agents: {e}")
            # Non-critical - continue with team rosters only

        self._logger.info(
            f"✅ Roster loading complete: "
            f"{players_inserted} players across {teams_processed} teams + free agents"
        )

        return players_with_contracts

    def _create_contracts(self, conn: sqlite3.Connection, players_with_contracts: List[Dict[str, Any]]):
        """
        Create contracts for all players with contract data.

        Uses ContractInitializer pattern from salary_cap module.

        Args:
            conn: Database connection
            players_with_contracts: List of dicts with player_id, team_id, contract data
        """
        if not players_with_contracts:
            self._logger.warning("No players with contract data to initialize")
            return

        self._logger.info(f"Initializing contracts for {len(players_with_contracts)} players...")

        try:
            from salary_cap.contract_initializer import ContractInitializer

            # Create contract initializer
            contract_initializer = ContractInitializer(conn)

            # Initialize all contracts from JSON data
            contract_map = contract_initializer.initialize_contracts_from_json(
                dynasty_id=self._dynasty_id,
                season=self._season,
                players_with_contracts=players_with_contracts
            )

            # Link contract_id to players table
            contract_initializer.link_contracts_to_players(contract_map)

            self._logger.info(
                f"✅ Contract initialization complete: {len(contract_map)} contracts created"
            )

        except Exception as e:
            self._logger.error(f"Contract initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize contracts: {e}")

    def _initialize_player_id_counter(self, conn: sqlite3.Connection):
        """
        Initialize player_id counter to avoid collisions.

        Args:
            conn: Database connection
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(player_id), 0) FROM players WHERE dynasty_id = ?",
            (self._dynasty_id,)
        )
        max_id = cursor.fetchone()[0]
        self._player_id_counter = max_id

        self._logger.info(f"Initialized player_id counter to {self._player_id_counter}")

    def _get_next_player_id(self) -> int:
        """
        Get next unique player_id.

        Returns:
            Next available player_id (auto-incrementing)
        """
        self._player_id_counter += 1
        return self._player_id_counter

    def _insert_player(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        source_player_id: str,
        first_name: str,
        last_name: str,
        number: int,
        team_id: int,
        positions: List[str],
        attributes: Dict[str, Any],
        birthdate: Optional[str] = None
    ):
        """
        Insert player into database.

        Args:
            conn: Database connection
            player_id: Auto-generated unique player ID
            source_player_id: Original JSON player_id (for reference)
            first_name: First name
            last_name: Last name
            number: Jersey number
            team_id: Team ID (0-32, 0 = free agent)
            positions: List of positions player can play
            attributes: Dict of player attributes/ratings
            birthdate: Optional birthdate (YYYY-MM-DD)
        """
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO players (
                dynasty_id, player_id, source_player_id,
                first_name, last_name, number, team_id,
                positions, attributes, birthdate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self._dynasty_id,
            player_id,
            source_player_id,
            first_name,
            last_name,
            number,
            team_id,
            json.dumps(positions),
            json.dumps(attributes),
            birthdate
        ))

    def _add_to_roster(
        self,
        conn: sqlite3.Connection,
        team_id: int,
        player_id: int,
        depth_order: int = 99
    ):
        """
        Add player to team roster.

        Args:
            conn: Database connection
            team_id: Team ID (1-32)
            player_id: Player ID (auto-generated)
            depth_order: Depth chart position (lower = higher, default 99)
        """
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO team_rosters (
                dynasty_id, team_id, player_id, depth_chart_order, roster_status
            ) VALUES (?, ?, ?, ?, 'active')
        ''', (
            self._dynasty_id,
            team_id,
            player_id,
            depth_order
        ))

    def _generate_initial_draft_class(self):
        """
        Generate draft class for current season at dynasty initialization.

        This ensures the draft class is available when:
        1. User skips directly to offseason (Jump to Offseason)
        2. First season draft happens

        Also generates next year's draft class for future scouting features.
        """
        try:
            from .draft_service import DraftService

            draft_service = DraftService(
                self._db_path,
                self._dynasty_id,
                self._season
            )

            # Generate CURRENT year's draft class (for first offseason draft)
            current_result = draft_service.ensure_draft_class_exists(draft_year=self._season)
            if current_result.get("generated"):
                self._logger.info(
                    f"✅ Generated {self._season} draft class: "
                    f"{current_result['prospect_count']} prospects"
                )
            elif current_result.get("exists"):
                self._logger.info(
                    f"✅ {self._season} draft class already exists: "
                    f"{current_result['prospect_count']} prospects"
                )
            elif current_result.get("error"):
                self._logger.warning(
                    f"⚠️ Failed to generate {self._season} draft class: "
                    f"{current_result['error']}"
                )

        except Exception as e:
            # Non-critical - draft class can be generated later
            self._logger.warning(f"⚠️ Draft class generation skipped: {e}")
