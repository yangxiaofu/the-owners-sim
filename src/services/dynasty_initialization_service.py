"""
Dynasty Initialization Service

Orchestrates complete dynasty initialization workflow.
Coordinates multiple database APIs and subsystems for atomic dynasty creation.

This service follows the Phase 3 service extraction pattern:
- Dependency injection of all APIs
- Business logic orchestration only
- No direct SQL (delegates to database APIs)
- Returns standardized result dicts
"""

import logging
import time
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime

from database.dynasty_database_api import DynastyDatabaseAPI
from database.player_roster_api import PlayerRosterAPI
from database.dynasty_state_api import DynastyStateAPI
from database.playoff_database_api import PlayoffDatabaseAPI
from database.connection import DatabaseConnection
from depth_chart.depth_chart_api import DepthChartAPI
from calendar.season_phase_tracker import SeasonPhase


class DynastyInitializationService:
    """
    Service for orchestrating complete dynasty initialization.

    Responsibilities:
    - Create dynasty record
    - Initialize standings (preseason + regular season)
    - Load player rosters from JSON
    - Generate depth charts
    - Coordinate schedule generation
    - Verify dynasty state initialization
    - Trigger AI offseason simulation

    Dependencies (injected):
    - DynastyDatabaseAPI: Dynasty CRUD operations
    - PlayerRosterAPI: Player roster management
    - DepthChartAPI: Depth chart generation
    - DynastyStateAPI: Dynasty state management
    - PlayoffDatabaseAPI: Playoff data management
    - Logger: Logging instance
    """

    def __init__(
        self,
        db_path: str,
        dynasty_database_api: Optional[DynastyDatabaseAPI] = None,
        player_roster_api: Optional[PlayerRosterAPI] = None,
        depth_chart_api: Optional[DepthChartAPI] = None,
        dynasty_state_api: Optional[DynastyStateAPI] = None,
        playoff_database_api: Optional[PlayoffDatabaseAPI] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Dynasty Initialization Service.

        Args:
            db_path: Path to SQLite database
            dynasty_database_api: Optional DynastyDatabaseAPI instance (lazy init if None)
            player_roster_api: Optional PlayerRosterAPI instance (lazy init if None)
            depth_chart_api: Optional DepthChartAPI instance (lazy init if None)
            dynasty_state_api: Optional DynastyStateAPI instance (lazy init if None)
            playoff_database_api: Optional PlayoffDatabaseAPI instance (lazy init if None)
            logger: Optional logger instance (creates default if None)
        """
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)

        # Lazy initialization of dependencies (allows mocking in tests)
        self._dynasty_db_api = dynasty_database_api
        self._player_roster_api = player_roster_api
        self._depth_chart_api = depth_chart_api
        self._dynasty_state_api = dynasty_state_api
        self._playoff_db_api = playoff_database_api

        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @property
    def dynasty_db_api(self) -> DynastyDatabaseAPI:
        """Lazy-initialize DynastyDatabaseAPI."""
        if self._dynasty_db_api is None:
            self._dynasty_db_api = DynastyDatabaseAPI(self.db_path)
        return self._dynasty_db_api

    @property
    def player_roster_api(self) -> PlayerRosterAPI:
        """Lazy-initialize PlayerRosterAPI."""
        if self._player_roster_api is None:
            self._player_roster_api = PlayerRosterAPI(self.db_path)
        return self._player_roster_api

    @property
    def depth_chart_api(self) -> DepthChartAPI:
        """Lazy-initialize DepthChartAPI."""
        if self._depth_chart_api is None:
            self._depth_chart_api = DepthChartAPI(self.db_path)
        return self._depth_chart_api

    @property
    def dynasty_state_api(self) -> DynastyStateAPI:
        """Lazy-initialize DynastyStateAPI."""
        if self._dynasty_state_api is None:
            self._dynasty_state_api = DynastyStateAPI(self.db_path)
        return self._dynasty_state_api

    @property
    def playoff_db_api(self) -> PlayoffDatabaseAPI:
        """Lazy-initialize PlayoffDatabaseAPI."""
        if self._playoff_db_api is None:
            self._playoff_db_api = PlayoffDatabaseAPI(self.db_path)
        return self._playoff_db_api

    def _reset_standings(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Reset standings to 0-0-0 for preseason + regular season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            connection: Optional shared connection for transaction participation

        Returns:
            Total standings records created (64 expected: 32 preseason + 32 regular)

        Raises:
            Exception: If standings count doesn't match expected (32 per season type)
        """
        print(f"📊 Resetting standings for season {season}...")

        # Initialize PRESEASON standings (32 teams)
        preseason_count = self.dynasty_db_api.initialize_standings_for_season_type(
            dynasty_id=dynasty_id,
            season=season,
            season_type='preseason',
            connection=connection
        )

        if preseason_count != 32:
            raise Exception(f"Expected 32 preseason standings, got {preseason_count}")

        # Initialize REGULAR SEASON standings (32 teams)
        regular_count = self.dynasty_db_api.initialize_standings_for_season_type(
            dynasty_id=dynasty_id,
            season=season,
            season_type='regular_season',
            connection=connection
        )

        if regular_count != 32:
            raise Exception(f"Expected 32 regular season standings, got {regular_count}")

        total_count = preseason_count + regular_count
        print(f"✅ Standings reset: {total_count} records ({preseason_count} preseason + {regular_count} regular)")

        return total_count

    def _clear_playoff_data(
        self,
        dynasty_id: str,
        season: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Clear all playoff data for a specific season.

        REFACTORED: Now delegates to PlayoffDatabaseAPI for modular reuse.

        Deletes from:
        - events table (playoff GameEvents with game_id pattern)
        - playoff_brackets table
        - playoff_seedings table

        Args:
            dynasty_id: Dynasty identifier
            season: Season year to clear
            connection: Optional shared connection for transaction participation

        Returns:
            Number of records deleted

        Example:
            >>> service = DynastyInitializationService(db_path="nfl.db")
            >>> deleted = service._clear_playoff_data("my_dynasty", 2025)
            >>> print(f"Deleted {deleted} playoff records")
        """
        # Delegate to PlayoffDatabaseAPI
        result = self.playoff_db_api.clear_playoff_data(
            dynasty_id=dynasty_id,
            season=season,
            connection=connection
        )

        # Extract total_deleted count for backward compatibility
        return result['total_deleted']

    def initialize_dynasty(
        self,
        dynasty_id: str,
        dynasty_name: str,
        owner_name: str,
        team_id: Optional[int],
        season: int
    ) -> Dict[str, Any]:
        """
        Initialize complete dynasty with all required data.

        Workflow:
        1. Create dynasty record
        2. Initialize preseason standings (32 teams)
        3. Initialize regular season standings (32 teams)
        4. Load player rosters from JSON (all 32 teams + free agents)
        5. Generate depth charts (all 32 teams)
        6. Initialize player contracts
        7. COMMIT (critical - must happen before schedule generation)
        8. Generate schedule (separate transaction)
        9. Verify dynasty state exists
        10. Run AI offseason simulation (separate transaction)

        Args:
            dynasty_id: Unique dynasty identifier
            dynasty_name: Display name
            owner_name: Owner's name
            team_id: User's team ID (1-32) or None
            season: Starting season year

        Returns:
            Dict with initialization results:
            {
                'success': bool,
                'dynasty_id': str,
                'players_loaded': int,
                'depth_charts_created': int,
                'schedule_generated': bool,
                'state_initialized': bool,
                'offseason_simulated': bool,
                'total_duration': float,
                'error_message': Optional[str]
            }

        Raises:
            Exception: Re-raises any exception after logging for fail-loud behavior
        """
        start_time = time.time()

        self.logger.info(f"Starting dynasty initialization: {dynasty_id}")
        print(f"\n{'='*80}")
        print(f"🏈 DYNASTY INITIALIZATION: {dynasty_name}")
        print(f"{'='*80}")

        result = {
            'success': False,
            'dynasty_id': dynasty_id,
            'players_loaded': 0,
            'depth_charts_created': 0,
            'schedule_generated': False,
            'state_initialized': False,
            'offseason_simulated': False,
            'total_duration': 0.0,
            'error_message': None
        }

        conn = None

        try:
            # Get shared connection for atomic transaction
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()

            # ===== TRANSACTION BLOCK 1: Core Dynasty Setup =====
            # All operations in this block share the same transaction

            # Step 1: Create dynasty record
            print(f"📝 Step 1: Creating dynasty record...")
            dynasty_created = self.dynasty_db_api.create_dynasty_record(
                dynasty_id=dynasty_id,
                dynasty_name=dynasty_name,
                owner_name=owner_name,
                team_id=team_id,
                connection=conn
            )

            if not dynasty_created:
                raise Exception("Failed to create dynasty record")

            print(f"✅ Dynasty record created: {dynasty_id}")

            # Step 2-3: Reset standings (DRY - reusable method)
            print(f"📊 Step 2-3: Initializing standings...")
            total_standings = self._reset_standings(
                dynasty_id=dynasty_id,
                season=season,
                connection=conn
            )

            # Step 4: Load player rosters from JSON → Database
            print(f"📥 Step 4: Loading player rosters from JSON...")
            print(f"   (This may take 10-15 seconds for all 32 teams + free agents)")

            # Pass shared connection for transaction safety
            self.player_roster_api.shared_conn = conn

            players_loaded = self.player_roster_api.initialize_dynasty_rosters(
                dynasty_id=dynasty_id,
                season=season
            )

            result['players_loaded'] = players_loaded
            print(f"✅ Player rosters loaded: {players_loaded} players")

            # Step 5: Generate depth charts for all 32 teams
            print(f"📋 Step 5: Auto-generating depth charts (all 32 teams)...")

            depth_charts_created = 0
            for tid in range(1, 33):
                success = self.depth_chart_api.auto_generate_depth_chart(
                    dynasty_id=dynasty_id,
                    team_id=tid,
                    connection=conn
                )
                if success:
                    depth_charts_created += 1

            result['depth_charts_created'] = depth_charts_created
            print(f"✅ Depth charts created: {depth_charts_created}/32 teams")

            if depth_charts_created < 32:
                self.logger.warning(f"Only {depth_charts_created}/32 depth charts created")

            # Step 6: Initialize player contracts
            print(f"💰 Step 6: Initializing player contracts...")

            try:
                from salary_cap.contract_initializer import ContractInitializer

                contract_initializer = ContractInitializer(
                    db_path=self.db_path,
                    dynasty_id=dynasty_id,
                    season_year=season,
                    shared_connection=conn  # Use shared connection
                )

                contracts_created = contract_initializer.initialize_all_team_contracts()
                print(f"✅ Contracts initialized: {contracts_created} contracts")

            except Exception as contract_error:
                self.logger.warning(f"Contract initialization failed: {contract_error}")
                print(f"⚠️  Contract initialization failed (non-critical): {contract_error}")

            # Step 7: COMMIT - Critical transaction boundary
            print(f"💾 Step 7: Committing dynasty to database...")
            conn.commit()
            print(f"✅ Dynasty committed successfully")

            # ===== SEPARATE TRANSACTION: Schedule Generation =====
            # Must happen AFTER commit to avoid database locks

            print(f"📅 Step 8: Generating season schedule...")
            print(f"   (Preseason: 48 games, Regular Season: 272 games)")

            try:
                # Import here to avoid circular dependencies
                from ui.controllers.season_controller import SeasonController

                season_controller = SeasonController(
                    db_path=self.db_path,
                    dynasty_id=dynasty_id,
                    season=season
                )

                schedule_success, schedule_error = season_controller.generate_initial_schedule()

                if schedule_success:
                    result['schedule_generated'] = True
                    print(f"✅ Schedule generated successfully")
                else:
                    self.logger.error(f"Schedule generation failed: {schedule_error}")
                    print(f"❌ Schedule generation failed: {schedule_error}")

            except Exception as schedule_error:
                self.logger.error(f"Schedule generation error: {schedule_error}", exc_info=True)
                print(f"❌ Schedule generation error: {schedule_error}")

            # ===== VERIFICATION: Dynasty State =====

            print(f"🔍 Step 9: Verifying dynasty state...")

            state = self.dynasty_state_api.get_current_state(dynasty_id, season)

            if state:
                result['state_initialized'] = True
                print(f"✅ Dynasty state verified: {state['current_date']}")
            else:
                # Create fallback dynasty_state
                self.logger.warning("Dynasty state missing - creating fallback")
                print(f"⚠️  Dynasty state missing - creating fallback...")

                fallback_success = self.dynasty_state_api.initialize_state(
                    dynasty_id=dynasty_id,
                    season=season,
                    start_date=f"{season}-08-01",
                    start_week=1,
                    start_phase=SeasonPhase.PRESEASON.value
                )

                if fallback_success:
                    result['state_initialized'] = True
                    print(f"✅ Fallback dynasty state created")
                else:
                    self.logger.error("CRITICAL: Failed to create dynasty state")
                    print(f"❌ CRITICAL: Failed to create dynasty state")

            # ===== SEPARATE TRANSACTION: AI Offseason Simulation =====

            print(f"🤖 Step 10: Simulating AI offseason...")

            try:
                from offseason.offseason_controller import OffseasonController

                offseason_controller = OffseasonController(
                    database_path=self.db_path,
                    dynasty_id=dynasty_id,
                    season_year=season,
                    user_team_id=team_id if team_id else 1,
                    super_bowl_date=datetime(season + 1, 2, 9),
                    enable_persistence=True,
                    verbose_logging=False  # Reduce console spam
                )

                offseason_result = offseason_controller.simulate_ai_full_offseason(
                    user_team_id=team_id if team_id else 1
                )

                result['offseason_simulated'] = True
                print(f"✅ AI offseason simulation complete:")
                print(f"   - Franchise tags: {offseason_result['franchise_tags_applied']}")
                print(f"   - Free agent signings: {offseason_result['free_agent_signings']}")
                print(f"   - Roster cuts: {offseason_result['roster_cuts_made']}")
                print(f"   - Total transactions: {offseason_result['total_transactions']}")

            except Exception as offseason_error:
                self.logger.warning(f"AI offseason simulation failed: {offseason_error}")
                print(f"⚠️  AI offseason simulation failed (non-critical): {offseason_error}")

            # ===== SUCCESS =====

            result['success'] = True
            result['total_duration'] = time.time() - start_time

            print(f"\n{'='*80}")
            print(f"✅ DYNASTY INITIALIZATION COMPLETE")
            print(f"{'='*80}")
            print(f"Dynasty ID: {dynasty_id}")
            print(f"Players Loaded: {result['players_loaded']}")
            print(f"Depth Charts: {result['depth_charts_created']}/32")
            print(f"Schedule: {'Generated' if result['schedule_generated'] else 'Failed'}")
            print(f"State: {'Initialized' if result['state_initialized'] else 'Failed'}")
            print(f"Offseason: {'Simulated' if result['offseason_simulated'] else 'Skipped'}")
            print(f"Duration: {result['total_duration']:.2f}s")
            print(f"{'='*80}\n")

            self.logger.info(f"Dynasty initialization successful: {dynasty_id} ({result['total_duration']:.2f}s)")

            return result

        except Exception as e:
            # Rollback transaction on failure
            if conn:
                conn.rollback()

            error_message = f"Dynasty initialization failed: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            result['success'] = False
            result['error_message'] = error_message
            result['total_duration'] = time.time() - start_time

            print(f"\n{'='*80}")
            print(f"❌ DYNASTY INITIALIZATION FAILED")
            print(f"{'='*80}")
            print(f"Error: {error_message}")
            print(f"Duration: {result['total_duration']:.2f}s")
            print(f"{'='*80}\n")

            # Re-raise exception for fail-loud behavior
            raise

    def prepare_next_season(
        self,
        dynasty_id: str,
        current_season: int,
        next_season: int
    ) -> Dict[str, Any]:
        """
        Prepare dynasty for next season transition.

        Multi-year season cycle preparation workflow:
        1. Clear playoff data from completed season (events, brackets, seedings)
        2. Reset standings to 0-0-0 for next season (preseason + regular)
        3. Update dynasty_state.season_year (atomic increment)

        This method is idempotent and transaction-safe for use in:
        - Offseason → Preseason transition handlers
        - Manual season rollover operations
        - Multi-year dynasty simulation loops

        Args:
            dynasty_id: Dynasty identifier
            current_season: Completed season year (for playoff cleanup)
            next_season: New season year (for standings reset)

        Returns:
            Dict with preparation results:
            {
                'success': bool,
                'dynasty_id': str,
                'current_season': int,
                'next_season': int,
                'playoff_records_deleted': int,
                'standings_created': int,
                'season_year_updated': bool,
                'total_duration': float,
                'error_message': Optional[str]
            }

        Raises:
            Exception: Re-raises any exception after logging for fail-loud behavior

        Example:
            >>> service = DynastyInitializationService(db_path="nfl.db")
            >>> result = service.prepare_next_season(
            ...     dynasty_id="my_dynasty",
            ...     current_season=2025,
            ...     next_season=2026
            ... )
            >>> print(f"Ready for season {result['next_season']}")
        """
        start_time = time.time()

        self.logger.info(f"Starting season transition: {current_season} → {next_season}")
        print(f"\n{'='*80}")
        print(f"🔄 SEASON TRANSITION: {current_season} → {next_season}")
        print(f"{'='*80}")

        result = {
            'success': False,
            'dynasty_id': dynasty_id,
            'current_season': current_season,
            'next_season': next_season,
            'playoff_records_deleted': 0,
            'standings_created': 0,
            'season_year_updated': False,
            'total_duration': 0.0,
            'error_message': None
        }

        conn = None

        try:
            # Get shared connection for atomic transaction
            conn = self.db_connection.get_connection()

            # ===== TRANSACTION BLOCK: Season Transition =====
            # All operations share the same transaction for atomicity

            # Step 1: Clear playoff data from completed season
            print(f"🗑️  Step 1: Clearing playoff data from season {current_season}...")
            playoff_deleted = self._clear_playoff_data(
                dynasty_id=dynasty_id,
                season=current_season,
                connection=conn
            )
            result['playoff_records_deleted'] = playoff_deleted

            # Step 2: Reset standings for next season (0-0-0)
            print(f"📊 Step 2: Resetting standings for season {next_season}...")
            standings_created = self._reset_standings(
                dynasty_id=dynasty_id,
                season=next_season,
                connection=conn
            )
            result['standings_created'] = standings_created

            # Step 3: Update dynasty_state.season_year (atomic increment)
            print(f"📅 Step 3: Updating dynasty state to season {next_season}...")

            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dynasty_state
                SET season_year = ?
                WHERE dynasty_id = ?
            """, (next_season, dynasty_id))

            if cursor.rowcount == 0:
                raise Exception(f"Dynasty state not found for dynasty_id: {dynasty_id}")

            result['season_year_updated'] = True
            print(f"✅ Dynasty state updated: season_year = {next_season}")

            # Step 4: COMMIT - Critical transaction boundary
            print(f"💾 Step 4: Committing season transition...")
            conn.commit()
            print(f"✅ Season transition committed successfully")

            # ===== SUCCESS =====

            result['success'] = True
            result['total_duration'] = time.time() - start_time

            print(f"\n{'='*80}")
            print(f"✅ SEASON TRANSITION COMPLETE")
            print(f"{'='*80}")
            print(f"Dynasty ID: {dynasty_id}")
            print(f"Season: {current_season} → {next_season}")
            print(f"Playoff Records Deleted: {result['playoff_records_deleted']}")
            print(f"Standings Created: {result['standings_created']}")
            print(f"Season Year Updated: {result['season_year_updated']}")
            print(f"Duration: {result['total_duration']:.2f}s")
            print(f"{'='*80}\n")

            self.logger.info(f"Season transition successful: {current_season} → {next_season} ({result['total_duration']:.2f}s)")

            return result

        except Exception as e:
            # Rollback transaction on failure
            if conn:
                conn.rollback()

            error_message = f"Season transition failed: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            result['success'] = False
            result['error_message'] = error_message
            result['total_duration'] = time.time() - start_time

            print(f"\n{'='*80}")
            print(f"❌ SEASON TRANSITION FAILED")
            print(f"{'='*80}")
            print(f"Error: {error_message}")
            print(f"Duration: {result['total_duration']:.2f}s")
            print(f"{'='*80}\n")

            # Re-raise exception for fail-loud behavior
            raise