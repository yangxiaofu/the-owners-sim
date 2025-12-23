"""
Game Cycle Dynasty Initialization Service.

Initializes game_cycle.db with player and contract data from JSON files.
This service is used by main2.py which uses game_cycle.db exclusively.

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
import re
import sqlite3
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging

# Local imports - external modules
from database.unified_api import UnifiedDatabaseAPI
from team_management.players.player_loader import PlayerDataLoader
from salary_cap.contract_initializer import ContractInitializer

# Relative imports - game_cycle services
from .draft_service import DraftService
from .schedule_service import ScheduleService
from .primetime_scheduler import PrimetimeScheduler
from .trade_service import TradeService
from .personality_generator import PersonalityGenerator

# Relative imports - game_cycle database
from ..database.connection import GameCycleDatabase
from ..database.game_slots_api import GameSlotsAPI
from ..database.rivalry_api import RivalryAPI


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

            # 4b. Initialize depth charts based on overall ratings
            self._initialize_depth_charts(conn)

            # 5. Create contracts
            self._create_contracts(conn, players_with_contracts)

            # Commit all changes
            conn.commit()

            # 6. Generate draft class for current year (AFTER commit so DraftClassAPI has data)
            self._generate_initial_draft_class()

            # 7. Generate regular season schedule for this dynasty
            self._generate_schedule_for_dynasty()

            # 8. Initialize standings for all 32 teams at 0-0-0
            self._initialize_standings()

            # 9. Initialize draft pick ownership for trade system
            self._initialize_pick_ownership()

            # 10. Initialize rivalries for schedule prioritization
            self._initialize_rivalries()

            # 11. Initialize social media personalities (Milestone 14)
            self._initialize_personalities()

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
        # Load JSON files using PlayerDataLoader
        try:
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
                        birthdate=real_player.birthdate,
                        years_pro=real_player.years_pro
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
                        birthdate=free_agent.birthdate,
                        years_pro=free_agent.years_pro
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
        birthdate: Optional[str] = None,
        years_pro: int = 0
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
            years_pro: Years of professional experience
        """
        # Ensure durability attribute exists (for injury system)
        if 'durability' not in attributes:
            position = positions[0] if positions else 'unknown'
            attributes['durability'] = self._generate_durability_for_position(position)

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO players (
                dynasty_id, player_id, source_player_id,
                first_name, last_name, number, team_id,
                positions, attributes, birthdate, years_pro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            birthdate,
            years_pro
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

    def _initialize_depth_charts(self, conn: sqlite3.Connection):
        """
        Initialize depth chart order for all teams based on overall ratings.

        For each position group on each team, players are ranked by their
        overall rating (highest = 1, second highest = 2, etc.).

        This ensures star players like Brock Purdy are properly set as starters
        instead of relying on the default depth_chart_order of 99.

        Args:
            conn: Database connection
        """
        self._logger.info("Initializing depth charts based on overall ratings...")
        cursor = conn.cursor()

        # Get all players grouped by team and primary position
        cursor.execute('''
            SELECT
                p.player_id,
                p.team_id,
                json_extract(p.positions, '$[0]') as primary_position,
                json_extract(p.attributes, '$.overall') as overall
            FROM players p
            JOIN team_rosters tr ON p.dynasty_id = tr.dynasty_id AND p.player_id = tr.player_id
            WHERE p.dynasty_id = ?
              AND p.team_id > 0
              AND tr.roster_status = 'active'
            ORDER BY p.team_id, primary_position, overall DESC
        ''', (self._dynasty_id,))

        players = cursor.fetchall()

        # Group by team_id and position, assign depth_chart_order
        current_team = None
        current_position = None
        depth_order = 1
        updates = []

        for player_id, team_id, position, overall in players:
            if team_id != current_team or position != current_position:
                # New position group - reset depth order
                current_team = team_id
                current_position = position
                depth_order = 1

            updates.append((depth_order, self._dynasty_id, player_id))
            depth_order += 1

        # Batch update depth_chart_order
        cursor.executemany('''
            UPDATE team_rosters
            SET depth_chart_order = ?
            WHERE dynasty_id = ? AND player_id = ?
        ''', updates)

        self._logger.info(f"✅ Depth charts initialized for {len(updates)} players")

    def _generate_initial_draft_class(self):
        """
        Generate draft class for current season at dynasty initialization.

        This ensures the draft class is available when:
        1. User skips directly to offseason (Jump to Offseason)
        2. First season draft happens

        Also generates next year's draft class for future scouting features.
        """
        try:
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

    def _generate_schedule_for_dynasty(self):
        """
        Generate regular season and preseason schedules for this dynasty.

        Creates game events in the events table with proper dynasty_id,
        then assigns primetime slots (TNF, SNF, MNF) via PrimetimeScheduler.
        """
        try:
            schedule_service = ScheduleService(
                self._db_path,
                self._dynasty_id,
                self._season
            )

            game_count = schedule_service.generate_schedule(clear_existing=True)
            self._logger.info(
                f"✅ Generated {self._season} schedule for dynasty '{self._dynasty_id}': "
                f"{game_count} games"
            )

            # Assign primetime slots (TNF, SNF, MNF) for the schedule
            db = GameCycleDatabase(self._db_path)
            try:
                game_slots_api = GameSlotsAPI(db)
                game_events = game_slots_api.get_games_for_primetime_assignment(
                    self._dynasty_id, self._season
                )

                primetime_scheduler = PrimetimeScheduler(db, self._dynasty_id)
                assignments = primetime_scheduler.assign_primetime_games(
                    season=self._season,
                    games=game_events,
                    super_bowl_winner_id=None
                )
                primetime_scheduler.save_assignments(self._season, assignments)
                self._logger.info(
                    f"✅ Assigned primetime slots: {len(assignments)} games"
                )
            finally:
                db.close()

            # Generate preseason schedule (3 weeks × 16 games = 48 games)
            from .schedule_coordinator import ScheduleCoordinator
            coordinator = ScheduleCoordinator(self._db_path, self._dynasty_id)
            preseason_count = coordinator.ensure_preseason_schedule(season=self._season)
            self._logger.info(
                f"✅ Generated {self._season} preseason schedule for dynasty '{self._dynasty_id}': "
                f"{preseason_count} games"
            )

        except Exception as e:
            # Non-critical - schedule can be generated later
            self._logger.warning(f"⚠️ Schedule generation skipped: {e}")

    def _initialize_standings(self):
        """
        Initialize standings for all 32 teams at 0-0-0 for the current season.

        This must be called during dynasty initialization so that:
        - Standings UI has data to display
        - Regular season handler can update standings after games
        """
        try:
            api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)
            success = api.standings_reset(
                season=self._season,
                season_type='regular_season'
            )

            if success:
                self._logger.info(
                    f"✅ Initialized standings for {self._season}: "
                    f"All 32 teams at 0-0-0"
                )
            else:
                self._logger.warning("⚠️ Standings initialization returned False")

        except Exception as e:
            # Non-critical - standings can be created on first game
            self._logger.warning(f"⚠️ Standings initialization skipped: {e}")

    def _initialize_pick_ownership(self):
        """
        Initialize draft pick ownership for the trade system.

        Creates ownership records for current season + 3 future years.
        Each team starts owning their own picks for all 7 rounds.
        This enables the trade system to track pick ownership across trades.
        """
        try:
            trade_service = TradeService(
                self._db_path,
                self._dynasty_id,
                self._season
            )

            # Initialize picks for 4 years total (current + 3 future)
            records = trade_service.initialize_pick_ownership(seasons_ahead=3)
            self._logger.info(
                f"✅ Initialized draft pick ownership for dynasty '{self._dynasty_id}': "
                f"{records} pick records created"
            )

        except Exception as e:
            # Non-critical - pick ownership can be initialized later
            self._logger.warning(f"⚠️ Pick ownership initialization skipped: {e}")

    def _initialize_rivalries(self):
        """
        Initialize team rivalries for the dynasty.

        Creates:
        - 48 division rivalries (6 pairs per division x 8 divisions)
        - 25 historic/geographic rivalries from config file

        Rivalries are used for schedule prioritization and gameplay effects.
        """
        try:
            db = GameCycleDatabase(self._db_path)
            rivalry_api = RivalryAPI(db)

            counts = rivalry_api.initialize_rivalries(self._dynasty_id)
            total = sum(counts.values())

            self._logger.info(
                f"✅ Initialized rivalries for dynasty '{self._dynasty_id}': "
                f"{counts['division']} division, {counts['historic']} historic, "
                f"{counts['geographic']} geographic ({total} total)"
            )

        except Exception as e:
            # Non-critical - rivalries can be initialized later
            self._logger.warning(f"⚠️ Rivalry initialization skipped: {e}")

    def _initialize_personalities(self):
        """
        Initialize social media personalities for the dynasty.

        Creates:
        - 320 fans (10 per team across different archetypes)
        - 32 beat reporters (1 per team)
        - 6 hot-take analysts (league-wide)
        - 4 stats analysts (league-wide)
        Total: 362 personalities

        Personalities are used for social media post generation (Milestone 14).
        """
        try:
            db = GameCycleDatabase(self._db_path)
            personality_gen = PersonalityGenerator(db, self._dynasty_id)

            counts = personality_gen.generate_all_personalities()
            total = sum(counts.values())

            self._logger.info(
                f"✅ Initialized social personalities for dynasty '{self._dynasty_id}': "
                f"{counts['fans']} fans, {counts['beat_reporters']} beat reporters, "
                f"{counts['hot_takes']} hot takes, {counts['stats_analysts']} stats analysts "
                f"({total} total)"
            )

            db.close()

        except Exception as e:
            # Non-critical - personalities can be initialized later
            self._logger.warning(f"⚠️ Social personality initialization skipped: {e}")

    # Class-level cache for durability config
    _durability_config: Optional[Dict[str, List[int]]] = None

    def _generate_durability_for_position(self, position: str) -> int:
        """
        Generate durability rating based on position config.

        Loads durability ranges from src/config/durability_ranges.json.
        Position-based durability ranges reflect injury risk:
        - RBs take most hits, most injury-prone (60-75)
        - WRs/TEs vulnerable to big hits (65-80)
        - QBs moderately protected (70-85)
        - OL most durable, steady physical play (72-88)
        - Specialists very durable, low contact (80-95)

        Args:
            position: Player position string

        Returns:
            Durability rating (60-95 range)
        """
        # Load config once and cache at class level
        if GameCycleInitializer._durability_config is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "durability_ranges.json"
            try:
                with open(config_path) as f:
                    GameCycleInitializer._durability_config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self._logger.warning(f"Failed to load durability config: {e}. Using defaults.")
                GameCycleInitializer._durability_config = {}

        position_lower = position.lower()
        durability_range = GameCycleInitializer._durability_config.get(position_lower, [70, 85])
        min_dur, max_dur = durability_range[0], durability_range[1]
        return random.randint(min_dur, max_dur)
