"""
Season Cycle Controller

Unified controller orchestrating the complete NFL season cycle from
Week 1 Regular Season → Super Bowl → Offseason.

This controller manages the three distinct phases:
1. REGULAR_SEASON: 272 games across 18 weeks (SeasonConstants.REGULAR_SEASON_GAME_COUNT, SeasonConstants.REGULAR_SEASON_WEEKS)
2. PLAYOFFS: 13 games (SeasonConstants.PLAYOFF_GAME_COUNT) (Wild Card → Super Bowl)
3. OFFSEASON: Post-season state with summary (future: draft, free agency, training camp)

Responsibilities:
- Coordinate SeasonController (regular season) and PlayoffController (playoffs)
- Handle automatic phase transitions
- Maintain calendar continuity across phases
- Preserve dynasty isolation
- Provide unified API for day/week advancement
- Support complete annual simulation cycle

This is a production-ready controller that should be used for full season simulations.
For individual phase control, use SeasonController or PlayoffController directly.
"""

import logging
import traceback
from datetime import timedelta, datetime, date
from typing import Dict, List, Any, Optional, Callable

# Use try/except to handle both production and test imports
# Try src.calendar first to avoid conflict with Python's builtin calendar module
try:
    from src.calendar.date_models import Date, normalize_date
    from src.calendar.season_phase_tracker import SeasonPhase
    from src.calendar.phase_state import PhaseState
except (ModuleNotFoundError, ImportError):
    from src.calendar.date_models import Date, normalize_date
    from src.calendar.season_phase_tracker import SeasonPhase
    from src.calendar.phase_state import PhaseState

from playoff_system.playoff_controller import PlayoffController
from playoff_system.playoff_seeder import PlayoffSeeder
from database.unified_api import UnifiedDatabaseAPI
from events.event_database_api import EventDatabaseAPI
from scheduling import RandomScheduleGenerator
from offseason.offseason_event_scheduler import OffseasonEventScheduler
from src.season.season_year_validator import SeasonYearValidator
from src.season.season_year_synchronizer import SeasonYearSynchronizer
from src.season.season_constants import SeasonConstants, PhaseNames, GameIDPrefixes
from transactions.models import AssetType
from transactions.transaction_timing_validator import TransactionTimingValidator
from services import TransactionService, extract_playoff_champions

# Phase transition system (dependency injection support)
try:
    from season.phase_transition.phase_completion_checker import PhaseCompletionChecker
    from season.phase_transition.phase_transition_manager import PhaseTransitionManager
    from season.phase_transition.models import PhaseTransition, TransitionHandlerKey
    from season.phase_transition.transition_handlers.preseason_to_regular_season import (
        PreseasonToRegularSeasonHandler,
    )
    from season.phase_transition.transition_handlers.regular_to_playoffs import (
        RegularToPlayoffsHandler,
    )
    from season.phase_transition.transition_handlers.offseason_to_preseason import (
        OffseasonToPreseasonHandler,
    )
    from season.phase_transition.transition_handlers.playoffs_to_offseason import (
        PlayoffsToOffseasonHandler,
    )
except ModuleNotFoundError:
    from src.season.phase_transition.phase_completion_checker import (
        PhaseCompletionChecker,
    )
    from src.season.phase_transition.phase_transition_manager import (
        PhaseTransitionManager,
    )
    from src.season.phase_transition.models import PhaseTransition, TransitionHandlerKey
    from src.season.phase_transition.transition_handlers.preseason_to_regular_season import (
        PreseasonToRegularSeasonHandler,
    )
    from src.season.phase_transition.transition_handlers.regular_to_playoffs import (
        RegularToPlayoffsHandler,
    )
    from src.season.phase_transition.transition_handlers.offseason_to_preseason import (
        OffseasonToPreseasonHandler,
    )
    from src.season.phase_transition.transition_handlers.playoffs_to_offseason import (
        PlayoffsToOffseasonHandler,
    )


class SeasonCycleController:
    """
    Unified controller orchestrating complete NFL season simulation cycle.

    Manages three distinct phases:
    1. REGULAR_SEASON: 272 games across 18 weeks (SeasonConstants.REGULAR_SEASON_GAME_COUNT, SeasonConstants.REGULAR_SEASON_WEEKS)
    2. PLAYOFFS: 13 games (SeasonConstants.PLAYOFF_GAME_COUNT) (Wild Card → Super Bowl)
    3. OFFSEASON: Post-season state with summary

    Usage:
        # Create controller
        controller = SeasonCycleController(
            database_path="season_2024.db",
            dynasty_id="my_dynasty",
            season_year=2024
        )

        # Advance by day
        result = controller.advance_day()

        # Advance by week
        weekly_result = controller.advance_week()

        # Simulate to end
        summary = controller.simulate_to_end()

        # Check current phase
        phase = controller.get_current_phase()
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str = "default",
        season_year: Optional[int] = None,  # Phase 2: Now optional, loads from DB
        start_date: Optional[Date] = None,
        initial_phase: Optional[
            SeasonPhase
        ] = None,  # Phase 2: Now optional, loads from DB
        enable_persistence: bool = True,
        verbose_logging: bool = True,
        fast_mode: bool = False,
        skip_transactions: bool = False,
        skip_offseason_events: bool = False,
        # Dependency injection (optional - for testing)
        phase_completion_checker: Optional[PhaseCompletionChecker] = None,
        phase_transition_manager: Optional[PhaseTransitionManager] = None,
    ):
        """
        Initialize season cycle controller.

        PHASE 2: Database-First Loading (BREAKING CHANGE)
        - season_year now OPTIONAL - loads from database if not provided
        - initial_phase now OPTIONAL - loads from database if not provided
        - Database is SINGLE SOURCE OF TRUTH for existing dynasties

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024). Optional - loads from database if None.
                        Only provide for NEW dynasties. For existing dynasties, omit to load from DB.
            start_date: Dynasty start date - should be ONE DAY BEFORE first game
                       (defaults to Sept 4 for first game on Sept 5)
            initial_phase: Starting phase (REGULAR_SEASON, PLAYOFFS, or OFFSEASON).
                          Optional - loads from database if None.
            enable_persistence: Whether to save stats to database
            verbose_logging: Whether to print progress messages
            fast_mode: Skip actual simulations, generate fake results for ultra-fast testing
            skip_transactions: Skip AI transaction evaluation (no trade analysis)
            skip_offseason_events: Skip offseason event processing (faster offseason)
            phase_completion_checker: Optional PhaseCompletionChecker for testing
            phase_transition_manager: Optional PhaseTransitionManager for testing
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging
        self.fast_mode = fast_mode
        self.skip_transactions = skip_transactions
        self.skip_offseason_events = skip_offseason_events

        self.logger = logging.getLogger(self.__class__.__name__)

        print(
            f"[DYNASTY_TRACE] SeasonCycleController.__init__(): dynasty_id={dynasty_id}"
        )

        # ============ PHASE 2: DATABASE-FIRST LOADING ============
        # Initialize UnifiedDatabaseAPI FIRST (needed for loading)
        self.db = UnifiedDatabaseAPI(database_path, dynasty_id)

        # Initialize EventDatabaseAPI (needed for game validation in handlers)
        # NOTE: Dynasty isolation handled via event.dynasty_id attribute on event objects
        self.event_db = EventDatabaseAPI(database_path)

        # Initialize SeasonYearValidator for drift detection
        self.season_year_validator = SeasonYearValidator(logger=self.logger)

        # Try to load from database (SINGLE SOURCE OF TRUTH)
        db_state = self.db.dynasty_get_latest_state()

        if db_state:
            # Existing dynasty - load from database
            db_season = db_state["season"]
            db_phase = db_state["current_phase"]

            if verbose_logging:
                print(f"[DATABASE_LOAD] Loading existing dynasty from database:")
                print(f"  Dynasty ID: {dynasty_id}")
                print(f"  Season: {db_season}")
                print(f"  Phase: {db_phase}")

            # Warn if caller provided conflicting season_year
            if season_year is not None and season_year != db_season:
                self.logger.warning(
                    f"[DATABASE_OVERRIDE] Provided season_year={season_year} conflicts with "
                    f"database season={db_season}. Using database value (SINGLE SOURCE OF TRUTH)."
                )

            # Database is authoritative - use its values
            self.season_year = 0  # Placeholder
            self._set_season_year(
                db_season, "Controller initialization (loaded from database)"
            )

            # Load phase from database if not explicitly provided
            if initial_phase is None:
                # Map database phase string to SeasonPhase enum
                # CASE-INSENSITIVE: Database may store "PRESEASON" or "preseason"
                phase_map = {
                    "regular_season": SeasonPhase.REGULAR_SEASON,
                    "preseason": SeasonPhase.PRESEASON,
                    "playoffs": SeasonPhase.PLAYOFFS,
                    "offseason": SeasonPhase.OFFSEASON,
                }
                initial_phase = phase_map.get(db_phase.lower(), SeasonPhase.REGULAR_SEASON)

        else:
            # New dynasty - use provided values or defaults
            final_season_year = season_year if season_year is not None else 2024

            if verbose_logging:
                print(f"[NEW_DYNASTY] Creating new dynasty:")
                print(f"  Dynasty ID: {dynasty_id}")
                print(f"  Season: {final_season_year}")

            self.season_year = 0  # Placeholder
            self._set_season_year(
                final_season_year, "Controller initialization (new dynasty)"
            )

            # Use provided phase or default to PRESEASON
            if initial_phase is None:
                initial_phase = SeasonPhase.PRESEASON

        # ============ END PHASE 2 ============

        # Default to preseason start date (August 1st for preseason beginning)
        if start_date is None:
            start_date = Date(self.season_year, 8, 1)

        self.start_date = start_date

        # Create shared phase state with correct starting phase and season year (single source of truth)
        self.phase_state = PhaseState(initial_phase, season_year=self.season_year)

        # Import core components directly (no demo dependency)
        from src.calendar.calendar_component import CalendarComponent
        from src.calendar.simulation_executor import SimulationExecutor
        from src.database.api import DatabaseAPI

        # Ensure database directory exists
        from pathlib import Path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Ensure dynasty exists in database (auto-create if needed)
        from database.connection import DatabaseConnection
        db_conn = DatabaseConnection(database_path)
        db_conn.ensure_dynasty_exists(dynasty_id)

        # Initialize database_api for standings and statistics
        self.database_api = DatabaseAPI(database_path)

        # Initialize calendar component with event database for phase detection
        self.calendar = CalendarComponent(
            start_date=start_date,
            season_year=self.season_year,
            phase_state=self.phase_state,
            database_api=self.event_db,
            dynasty_id=dynasty_id
        )

        # Initialize simulation executor for game execution
        self.simulation_executor = SimulationExecutor(
            calendar=self.calendar,
            event_db=self.event_db,
            database_path=database_path,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            season_year=self.season_year,
            phase_state=self.phase_state,
            verbose_logging=verbose_logging,
            fast_mode=fast_mode,
            skip_offseason_events=skip_offseason_events
        )

        # Track week number and statistics (previously tracked by demo controller)
        self.current_week = 1

        # Playoff controller created when needed
        self.playoff_controller: Optional[PlayoffController] = None

        # Season summary (generated in offseason)
        self.season_summary: Optional[Dict[str, Any]] = None

        # Statistics
        self.total_games_played = 0
        self.total_days_simulated = 0

        # Initialize PhaseBoundaryDetector for centralized phase boundary detection
        from src.calendar.phase_boundary_detector import PhaseBoundaryDetector
        self.boundary_detector = PhaseBoundaryDetector(
            event_db=self.event_db,
            dynasty_id=self.dynasty_id,
            get_season_year=lambda: self.season_year,  # Dynamic callable (SSOT)
            db=self.db,
            calendar=self.calendar,
            logger=self.logger,
            cache_results=True  # Enable caching for performance
        )

        # Calculate last scheduled regular season game date for flexible end-of-season detection
        # Now using PhaseBoundaryDetector for centralized boundary logic
        # NOTE: May be None if schedule hasn't been generated yet (new dynasties)
        try:
            self.last_regular_season_game_date = self.boundary_detector.get_last_game_date(SeasonPhase.REGULAR_SEASON)
        except ValueError:
            # No games scheduled yet - this is expected for new dynasties before schedule generation
            self.last_regular_season_game_date = None
            if verbose_logging:
                print(f"[INIT] No regular season games scheduled yet (dynasty: {dynasty_id}, season: {self.season_year})")

        # ============ OFFSEASON CONTROLLER ============
        # Initialize offseason controller for consistent phase abstraction
        from src.season.offseason_controller import OffseasonController
        self.offseason_controller = OffseasonController(
            calendar=self.calendar,
            event_db=self.event_db,
            database_path=database_path,
            dynasty_id=dynasty_id,
            season_year=self.season_year,
            phase_state=self.phase_state,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging,
            logger=self.logger,
        )

        # ============ PHASE HANDLERS (STRATEGY PATTERN) ============
        # Initialize phase handlers for unified phase management
        from src.season.phase_handlers import (
            PreseasonHandler,
            RegularSeasonHandler,
            PlayoffHandler,
            OffseasonHandler,
        )

        # Note: Playoff handler initialized later when playoff_controller is created
        # Phase handlers now receive components directly (no demo dependency)
        self.phase_handlers = {
            SeasonPhase.PRESEASON: PreseasonHandler(
                calendar=self.calendar,
                simulation_executor=self.simulation_executor,
                database_api=self.database_api,
                season_year=self.season_year
            ),
            SeasonPhase.REGULAR_SEASON: RegularSeasonHandler(
                calendar=self.calendar,
                simulation_executor=self.simulation_executor,
                database_api=self.database_api,
                season_year=self.season_year
            ),
            SeasonPhase.OFFSEASON: OffseasonHandler(
                offseason_controller=self.offseason_controller,
                simulation_executor=self.simulation_executor
            ),
            # PLAYOFFS handler added dynamically when playoff_controller is created
        }

        # ============ PHASE TRANSITION SYSTEM ============
        # Initialize phase completion checker (dependency injection support)
        if phase_completion_checker is None:
            # Create default checker with injected dependencies
            # Now using PhaseBoundaryDetector for centralized boundary logic
            self.phase_completion_checker = PhaseCompletionChecker(
                get_games_played=lambda: self._get_phase_specific_games_played(),  # ✅ Phase-specific, not cumulative!
                get_current_date=lambda: self.calendar.get_current_date(),
                get_last_regular_season_game_date=lambda: self.boundary_detector.get_last_game_date(SeasonPhase.REGULAR_SEASON),
                get_last_preseason_game_date=lambda: self.boundary_detector.get_last_game_date(SeasonPhase.PRESEASON),
                is_super_bowl_complete=lambda: self._is_super_bowl_complete(),
                calculate_preseason_start=lambda: self._get_preseason_start_from_milestone(),
            )
        else:
            self.phase_completion_checker = phase_completion_checker

        # Initialize phase transition manager (dependency injection support)
        if phase_transition_manager is None:
            # Create PRESEASON → REGULAR_SEASON handler
            preseason_to_regular_season_handler = PreseasonToRegularSeasonHandler(
                update_database_phase=self._update_database_phase_for_handler,
                dynasty_id=dynasty_id,
                season_year=self.season_year,  # Phase 2: Use database-loaded value
                verbose_logging=verbose_logging,
            )

            # Create REGULAR_SEASON → PLAYOFFS handler
            regular_to_playoffs_handler = RegularToPlayoffsHandler(
                get_standings=self._get_standings_for_handler,
                seed_playoffs=self._seed_playoffs_for_handler,
                create_playoff_controller=self._create_playoff_controller_for_handler,
                update_database_phase=self._update_database_phase_for_handler,
                dynasty_id=dynasty_id,
                season_year=self.season_year,
                verbose_logging=verbose_logging,
            )

            # Create PLAYOFFS → OFFSEASON handler
            playoffs_to_offseason_handler = PlayoffsToOffseasonHandler(
                get_super_bowl_winner=self._get_super_bowl_winner_for_handler,
                schedule_offseason_events=self._schedule_offseason_events_for_handler,
                generate_season_summary=self._generate_season_summary_for_handler,
                update_database_phase=self._update_database_phase_for_handler,
                dynasty_id=dynasty_id,
                season_year=self.season_year,  # Phase 2: Use database-loaded value
                verbose_logging=verbose_logging,
                # Draft order calculation parameters
                get_regular_season_standings=self._get_regular_season_standings_for_handler,
                get_playoff_bracket=self._get_playoff_bracket_for_handler,
                schedule_event=self._schedule_event_for_handler,
                database_path=self.database_path,
            )

            # Create OFFSEASON → PRESEASON handler
            offseason_to_preseason_handler = OffseasonToPreseasonHandler(
                generate_preseason=self._generate_preseason_schedule_for_handler,
                generate_regular_season=self._generate_regular_season_schedule_for_handler,
                reset_standings=self._reset_standings_for_handler,
                # Using PhaseBoundaryDetector for centralized boundary logic
                calculate_preseason_start=lambda year: self.boundary_detector.get_phase_start_date(
                    SeasonPhase.PRESEASON, season_year=year
                ).to_python_datetime(),
                execute_year_transition=self._execute_year_transition_for_handler,
                update_database_phase=self._update_database_phase_for_handler,
                dynasty_id=dynasty_id,
                new_season_year=self.season_year
                + 1,  # Phase 2: Use database-loaded value + 1
                event_db=self.event_db,  # For game validation
                verbose_logging=verbose_logging,
            )

            # Create default manager with registered handlers
            self.phase_transition_manager = PhaseTransitionManager(
                phase_state=self.phase_state,
                completion_checker=self.phase_completion_checker,
                transition_handlers={
                    TransitionHandlerKey.PRESEASON_TO_REGULAR_SEASON: preseason_to_regular_season_handler.execute,
                    TransitionHandlerKey.REGULAR_SEASON_TO_PLAYOFFS: regular_to_playoffs_handler.execute,
                    TransitionHandlerKey.PLAYOFFS_TO_OFFSEASON: playoffs_to_offseason_handler.execute,
                    TransitionHandlerKey.OFFSEASON_TO_PRESEASON: offseason_to_preseason_handler.execute,
                },
            )
        else:
            self.phase_transition_manager = phase_transition_manager

        # ============ PHASE 3: ATOMIC SYNCHRONIZATION ============
        # Initialize season year synchronizer for atomic updates across all components
        self.year_synchronizer = SeasonYearSynchronizer(
            get_current_year=lambda: self.season_year,
            set_controller_year=self._set_season_year,
            update_database_year=self._update_database_year,
            dynasty_id=self.dynasty_id,
            logger=self.logger,
        )

        # Register simulation_executor to be updated when year changes
        # CRITICAL: This fixes preseason game simulation in the following season
        # Without this, executor has old year and can't find games with new year prefix
        self.year_synchronizer.register_callback(
            "simulation_executor",
            lambda year: setattr(self.simulation_executor, "season_year", year),
        )

        if self.verbose_logging:
            status = self.year_synchronizer.get_registry_status()
            print(f"[PHASE_3] SeasonYearSynchronizer initialized:")
            print(f"  Current year: {status['current_year']}")
            print(f"  Registered components: {status['registered_components']}")

        # ============ END PHASE 3 ============

        # Ensure dynasty record exists (required for foreign key constraints)
        self.db.dynasty_ensure_exists(
            dynasty_name=f"Dynasty {dynasty_id}", owner_name=None, team_id=None
        )

        # GENERATE DRAFT CLASS FOR THIS SEASON
        self._generate_draft_class_if_needed()

        # Phase 5: Auto-recovery guard after controller initialization
        self._auto_recover_year_from_database("After controller initialization")

        # State tracking - set active controller based on initial phase
        # IMPORTANT: This comes AFTER database_api initialization because _restore_playoff_controller() needs it
        if initial_phase.value == "playoffs":
            # Restore playoff controller from database
            self._restore_playoff_controller()
            self.active_controller = self.playoff_controller
        elif initial_phase.value == "offseason":
            # Restore playoff controller so users can review completed bracket
            self._restore_playoff_controller()
            self.active_controller = (
                None  # No active controller in offseason (no more games to simulate)
            )
        else:
            # Preseason/Regular season - phase handlers manage simulation
            self.active_controller = None

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON CYCLE CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {self.season_year}")  # Phase 2: Use database-loaded value
            print(f"Start Date: {start_date}")
            print(f"Dynasty: {dynasty_id}")
            print(f"Database: {database_path}")
            print(f"Current Phase: {self.phase_state.phase.value}")
            print(f"Persistence: {'ENABLED' if enable_persistence else 'DISABLED'}")
            print(f"{'='*80}")

    # ========== Public API ==========

    def _build_offseason_complete_result(
        self, starting_phase: str, starting_year: int
    ) -> Dict[str, Any]:
        """
        Build success result dict when offseason completes and transitions to preseason.

        Args:
            starting_phase: Phase at start of operation
            starting_year: Season year at start of operation

        Returns:
            Success result dictionary with transition metadata
        """
        self.logger.info(
            f"Offseason complete! Transitioned from season {starting_year} to {self.season_year}"
        )
        return {
            "success": True,
            "message": f"Offseason complete! Transitioned from {starting_phase.upper()} to {self.phase_state.phase.value.upper()}. New season {self.season_year} initialized.",
            "starting_phase": starting_phase,
            "ending_phase": self.phase_state.phase.value,
            "starting_year": starting_year,
            "season_year": self.season_year,
            "transition_occurred": True,
            "new_season": True,
            "weeks_simulated": 0,
            "total_games": 0,
            "days_simulated": 0,
            "events_executed": 0,
            "start_date": str(self.calendar.get_current_date()),
            "end_date": str(self.calendar.get_current_date()),
        }

    def _handle_no_milestone_found(self, starting_phase: str) -> Dict[str, Any]:
        """
        Handle case where no offseason milestone exists.

        Attempts to get preseason start date and builds user-friendly error message
        with guidance on how to proceed.

        Args:
            starting_phase: Phase at start of operation

        Returns:
            Error result dict with guidance for user
        """
        current_date = self.calendar.get_current_date()

        # Get preseason start date for user guidance
        try:
            preseason_start = self._get_preseason_start_date()
            days_until = (preseason_start - current_date).days
            preseason_date_str = preseason_start.strftime("%b %d, %Y")

            self.logger.warning(
                f"No offseason milestone found. Waiting for preseason to start. "
                f"Current date: {current_date}. Preseason starts: {preseason_date_str} ({days_until} days)."
            )

            error_msg = (
                f"No more offseason milestones.\n\n"
                f"Current date: {current_date.strftime('%b %d, %Y')}\n"
                f"Preseason starts: {preseason_date_str}\n"
                f"Days remaining: {days_until}\n\n"
                f"Use 'Advance Day' or 'Advance Week' to continue."
            )
        except Exception as e:
            # Fallback if we can't determine preseason start
            self.logger.warning(
                f"No offseason milestone found and cannot determine preseason start. "
                f"Current date: {current_date}. Error: {e}"
            )
            error_msg = (
                f"No offseason milestone found and offseason not complete.\n\n"
                f"Current date: {current_date}\n"
                f"Unable to determine preseason start date. This may indicate a database or calendar configuration issue."
            )

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"[ERROR] NO OFFSEASON MILESTONES FOUND")
            print(f"{'='*80}")
            print(error_msg)
            print(f"{'='*80}\n")

        return {
            "success": False,
            "message": error_msg,
            "starting_phase": starting_phase,
            "ending_phase": self.phase_state.phase.value,
            "season_year": self.season_year,
            "transition_occurred": False,
            "error_type": "incomplete_offseason_no_milestones",
            "weeks_simulated": 0,
            "total_games": 0,
            "days_simulated": 0,
            "events_executed": 0,
            "start_date": str(self.calendar.get_current_date()),
            "end_date": str(self.calendar.get_current_date()),
        }

    def _enrich_milestone_result(
        self,
        result: Dict[str, Any],
        next_milestone: Dict[str, Any],
        starting_phase: str,
        starting_year: int,
    ) -> Dict[str, Any]:
        """
        Add milestone-specific metadata to simulation result.

        Detects phase transitions and adds UI-expected keys.

        Args:
            result: Base simulation result dict
            next_milestone: Milestone event that was reached
            starting_phase: Phase at start of operation
            starting_year: Season year at start of operation

        Returns:
            Enriched result dict with milestone metadata
        """
        # Detect if transition occurred during simulation
        transition_occurred = self.phase_state.phase.value != starting_phase

        if transition_occurred:
            self.logger.info(
                f"Phase transition occurred during simulation to {next_milestone['display_name']}"
            )

        # Add milestone-specific info to result
        result["milestone_reached"] = next_milestone["display_name"]
        result["milestone_type"] = next_milestone["event_type"]
        result["milestone_date"] = str(next_milestone["event_date"])

        # Add keys UI expects
        result["starting_phase"] = starting_phase
        result["ending_phase"] = self.phase_state.phase.value
        result["weeks_simulated"] = result["days_simulated"] // 7
        result["total_games"] = result.get("games_played", 0)
        result["phase_transition"] = transition_occurred
        result["transition_occurred"] = transition_occurred

        return result

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 day using phase handler strategy pattern.

        REFACTORED: Controller now owns calendar advancement.
        - Controller advances calendar ONCE at the start
        - Handlers renamed to simulate_day(current_date) and never touch calendar
        - Eliminates double-advance bug on phase transition days

        Unified phase handling: routes to appropriate phase handler based on current phase.
        All phases (preseason, regular season, playoffs, offseason) now use consistent
        controller → handler delegation pattern.

        Returns:
            Dictionary with results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "current_phase": str,
                "phase_transition": Optional[Dict],
                "success": bool,
                "message": str,
                "transactions_executed": List (regular season only),
                "num_trades": int (regular season only)
            }
        """
        # Guard: Auto-recovery before simulation
        self._auto_recover_year_from_database("Before daily simulation")

        # DIAGNOSTIC: Log entry to advance_day
        print(f"\n{'='*100}")
        print(f"[DIAGNOSTIC] advance_day() ENTRY")
        print(f"{'='*100}")
        print(f"[DIAGNOSTIC] Current date BEFORE advance: {self.calendar.get_current_date()}")
        print(f"[DIAGNOSTIC] Current phase: {self.phase_state.phase.value}")
        print(f"[DIAGNOSTIC] Season year: {self.season_year}")
        dynasty_state = self.db.dynasty_get_latest_state()
        if dynasty_state:
            print(f"[DIAGNOSTIC] Database phase: {dynasty_state.get('current_phase', 'UNKNOWN')}")
            print(f"[DIAGNOSTIC] Database date: {dynasty_state.get('current_date', 'UNKNOWN')}")
            print(f"[DIAGNOSTIC] Database season: {dynasty_state.get('season', 'UNKNOWN')}")
        else:
            print(f"[DIAGNOSTIC] Database state: NO STATE FOUND")
        print(f"{'='*100}\n")

        # CRITICAL FIX: Controller advances calendar ONCE before everything else
        # This prevents double-advance bug on transition days (e.g., Aug 4→5)
        self.calendar.advance(days=1)
        current_date = self.calendar.get_current_date()

        print(f"\n[CALENDAR_ADVANCE] Controller advanced calendar by 1 day")
        print(f"  New current date: {current_date}")
        print(f"")

        # Check for phase transitions using NEW date
        # If transition occurs, we'll use the NEW phase handler for today's simulation
        phase_transition = self._check_phase_transition()

        if phase_transition and self.verbose_logging:
            print(f"\n[PHASE_TRANSITION] Transition occurred on {current_date}")
            print(f"  From: {phase_transition.get('from_phase')}")
            print(f"  To: {phase_transition.get('to_phase')}")
            print(f"  Will use {phase_transition.get('to_phase')} handler to simulate {current_date}")

        # DIAGNOSTIC: Log handler selection
        print(f"\n[DIAGNOSTIC] HANDLER SELECTION")
        print(f"  Phase transition occurred? {phase_transition is not None}")
        if phase_transition:
            print(f"  Transition: {phase_transition.get('from_phase')} → {phase_transition.get('to_phase')}")
        print(f"  Current phase (for handler selection): {self.phase_state.phase.value}")
        print(f"  Available handlers: {list(self.phase_handlers.keys())}")

        # Get phase-specific handler (Strategy Pattern)
        # If transition occurred above, this gets the NEW phase handler
        handler = self.phase_handlers.get(self.phase_state.phase)

        print(f"  Selected handler: {type(handler).__name__ if handler else 'None'}")
        print(f"")

        if handler is None:
            raise ValueError(
                f"No phase handler found for phase: {self.phase_state.phase}. "
                f"Available handlers: {list(self.phase_handlers.keys())}"
            )

        # Execute phase-specific simulation via handler
        # Handler ONLY simulates the given date - it does NOT advance calendar
        result = handler.simulate_day(current_date)

        # DIAGNOSTIC: Log handler result
        print(f"\n[DIAGNOSTIC] HANDLER RESULT")
        print(f"  Handler: {type(handler).__name__}")
        print(f"  Simulated date: {current_date}")
        print(f"  Games played: {result.get('games_played', 0)}")
        print(f"  Results count: {len(result.get('results', []))}")
        print(f"  Success: {result.get('success', 'NOT_SET')}")
        print(f"  Calendar date unchanged: {self.calendar.get_current_date()}")
        print(f"")

        # Update statistics (common for all phases)
        self.total_games_played += result.get("games_played", 0)
        self.total_days_simulated += 1

        # Transaction evaluation (trade window validation)
        # Note: Uses TransactionTimingValidator to check if trades are allowed
        # Trades allowed: Offseason (after Mar 12), Preseason, Regular Season (until Week 9 Tue)
        validator = TransactionTimingValidator(self.season_year)
        current_week = self._calculate_current_week()
        current_date_py = self.calendar.get_current_date().to_python_date()

        is_trade_allowed, reason = validator.is_trade_allowed(
            current_date=current_date_py,
            current_phase=self.phase_state.phase,
            current_week=current_week
        )

        if is_trade_allowed and not self.skip_transactions:
            # Use TransactionService for evaluation (Phase 3: Service Extraction)
            service = self._get_transaction_service()
            executed_trades = service.evaluate_daily_for_all_teams(
                current_phase=self.phase_state.phase.value,
                current_week=current_week,
                verbose_logging=self.verbose_logging,
            )
            result["transactions_executed"] = executed_trades
            result["num_trades"] = len(executed_trades)
        elif self.verbose_logging:
            if not is_trade_allowed:
                print(f"[TRADE_WINDOW] Trades not allowed: {reason}")
            elif self.skip_transactions:
                print(f"[TRADE_WINDOW] Transaction AI skipped (skip_transactions=True)")

        # Check for phase transitions AFTER handler execution (if not already transitioned)
        # This handles game-count-based transitions (e.g., regular season → playoffs after 272 games)
        # Skip if transition already occurred before handler (e.g., offseason → preseason on date)
        if not phase_transition:
            phase_transition = self._check_phase_transition()
            if phase_transition and self.verbose_logging:
                print(f"\n[PHASE_TRANSITION_AFTER_HANDLER] Transition occurred after handler execution")
                print(f"  From: {phase_transition.get('from_phase')}")
                print(f"  To: {phase_transition.get('to_phase')}")

        # Add transition to result if it occurred (either before or after handler)
        if phase_transition:
            result["phase_transition"] = phase_transition

        # Ensure current phase is always in result
        result["current_phase"] = self.phase_state.phase.value

        return result

    def advance_week(
        self,
        checkpoint_callback: Optional[Callable[[int, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Advance simulation by up to 7 days with optional daily checkpoints.

        Stops early if phase transition or milestone occurs.
        advance_day() handles all phase-specific logic and event simulation.

        Args:
            checkpoint_callback: Optional callback called after each day.
                                Signature: callback(day_num, day_result)
                                If callback raises exception, week simulation aborts
                                and returns partial results.

        Returns:
            Dictionary with weekly summary
        """
        # Single guard at entry point
        self._auto_recover_year_from_database("Before weekly simulation")

        start_date = str(self.calendar.get_current_date())

        # DIAGNOSTIC LOGGING: Always log phase state at advance_week entry
        print(f"\n[WEEK ENTRY] ===== advance_week() START =====")
        print(f"[WEEK ENTRY] Start date: {start_date}")
        print(f"[WEEK ENTRY] Phase: {self.phase_state.phase.value}")
        print(f"[WEEK ENTRY] skip_offseason_events: {self.skip_offseason_events}")
        print(f"[WEEK ENTRY] ====================================\n")

        # Simple loop - advance_day() does all the work
        daily_results = []
        milestone_info = None  # Track milestone if detected

        if self.verbose_logging:
            print(f"\n[WEEK] Starting week from {start_date}, phase={self.phase_state.phase.value}")

        for day_num in range(7):
            current_loop_date = self.calendar.get_current_date()
            print(f"\n[WEEK] ==== Day {day_num + 1}/7 ====")
            print(f"[WEEK] Current calendar date: {current_loop_date}")

            if self.verbose_logging:
                print(f"[WEEK] Day {day_num + 1}/7")

            # advance_day() handles: phase detection, event extraction, simulation, transitions
            print(f"[WEEK] Executing advance_day()...")
            day_result = self.advance_day()
            daily_results.append(day_result)
            print(f"[WEEK] advance_day() complete, new date: {self.calendar.get_current_date()}")

            # Call checkpoint callback after each day (if provided)
            if checkpoint_callback:
                try:
                    checkpoint_callback(day_num, day_result)
                except Exception as e:
                    # Checkpoint callback failed - abort week simulation
                    print(f"[WEEK] ❌ Checkpoint callback failed on day {day_num + 1}: {e}")
                    logging.error(f"Checkpoint callback failed on day {day_num}: {e}")
                    # Return partial results with error info
                    return self._aggregate_week_results(
                        daily_results,
                        start_date,
                        str(self.calendar.get_current_date()),
                        None  # No milestone info on checkpoint failure
                    )

            # Always stop on phase transitions (checked AFTER execution)
            if day_result.get("phase_transition"):
                print(f"[WEEK] Phase transition detected - STOPPING WEEK EARLY")
                if self.verbose_logging:
                    print(f"[WEEK] Phase transition on day {day_num + 1} - stopping week early")
                break

        end_date = str(self.calendar.get_current_date())

        # Aggregate results from daily calls
        week_summary = self._aggregate_week_results(daily_results, start_date, end_date, milestone_info)

        if self.verbose_logging:
            print(f"[WEEK] Week complete: {start_date} → {end_date}")
            print(f"[WEEK] Games: {week_summary['games_played']}, Trades: {week_summary['num_trades']}")
            print(f"[WEEK] Phase transition: {week_summary.get('phase_transition') is not None}")

        return week_summary

    def advance_days(self, num_days: int, checkpoint_callback=None) -> Dict[str, Any]:
        """
        Advance simulation by exactly N days (no early stopping for milestones).

        Unlike advance_week(), this method does NOT check for milestones or stop early.
        It simulates exactly the specified number of days, only stopping for phase
        transitions. This method is used by the UI layer for fine-grained simulation
        control (e.g., simulating up to but not including a milestone date).

        Args:
            num_days: Number of days to simulate (1-365)
            checkpoint_callback: Optional callback(day_num, day_result) for incremental persistence

        Returns:
            Dictionary with simulation results:
            {
                'success': bool,
                'days_simulated': int,
                'date': str,                  # Final date
                'current_phase': str,
                'games_played': int,
                'num_trades': int,
                'daily_results': List[Dict],
                'phase_transition': Optional[Dict],  # If phase changed
                'message': str
            }

        Raises:
            ValueError: If num_days < 1 or > 365

        Examples:
            # Simulate 3 days before Draft Day
            result = controller.advance_days(3)

            # Then handle Draft Day in UI
            # Then simulate 4 more days
            result = controller.advance_days(4)
        """
        if num_days < 1 or num_days > 365:
            raise ValueError(f"num_days must be 1-365, got {num_days}")

        start_date = str(self.calendar.get_current_date())
        daily_results = []

        print(f"\n[DAYS] ===== Simulating {num_days} days =====")
        print(f"[DAYS] Start date: {start_date}")

        for day_num in range(num_days):
            if self.verbose_logging:
                current = str(self.calendar.get_current_date())
                print(f"\n[DAYS] --- Day {day_num + 1}/{num_days}: {current} ---")

            # No milestone checks - just simulate
            day_result = self.advance_day()
            daily_results.append(day_result)

            # Execute checkpoint callback if provided
            if checkpoint_callback:
                try:
                    checkpoint_callback(day_num, day_result)
                except Exception as e:
                    # Checkpoint callback failed - abort simulation
                    print(f"[DAYS] ❌ Checkpoint callback failed on day {day_num + 1}: {e}")
                    logging.error(f"Checkpoint callback failed on day {day_num}: {e}")
                    # Return partial results with error info
                    return self._aggregate_days_results(
                        daily_results,
                        start_date,
                        str(self.calendar.get_current_date()),
                        checkpoint_failed=True
                    )

            # Stop early only on phase transitions (not milestones)
            if day_result.get("phase_transition"):
                print(f"[DAYS] Phase transition detected on day {day_num + 1} - STOPPING EARLY")
                break

        end_date = str(self.calendar.get_current_date())

        # Aggregate results from daily calls
        result = self._aggregate_days_results(daily_results, start_date, end_date)

        if self.verbose_logging:
            print(f"[DAYS] Complete: {start_date} → {end_date}")
            print(f"[DAYS] Days simulated: {result['days_simulated']}")
            print(f"[DAYS] Games: {result['games_played']}, Trades: {result['num_trades']}")

        return result

    def _aggregate_days_results(
        self,
        daily_results: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        checkpoint_failed: bool = False
    ) -> Dict[str, Any]:
        """
        Aggregate daily results for advance_days() method.

        Args:
            daily_results: List of results from each advance_day() call
            start_date: Start date
            end_date: End date
            checkpoint_failed: True if checkpoint callback failed

        Returns:
            Dictionary with aggregated results
        """
        # Count games and trades
        total_games = sum(len(day.get('results', [])) for day in daily_results)
        total_trades = sum(day.get('num_trades', 0) for day in daily_results)

        # Check for phase transition in any day
        phase_transition = None
        for day in daily_results:
            if day.get('phase_transition'):
                phase_transition = day['phase_transition']
                break

        return {
            'success': not checkpoint_failed,
            'days_simulated': len(daily_results),
            'date': end_date,
            'current_phase': self.phase_state.phase.value,
            'games_played': total_games,
            'num_trades': total_trades,
            'daily_results': daily_results,
            'phase_transition': phase_transition,
            'message': f"Simulated {len(daily_results)} days: {start_date} → {end_date}" +
                      (f" (checkpoint failed)" if checkpoint_failed else "")
        }

    def _aggregate_week_results(
        self,
        daily_results: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        milestone_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate daily results into weekly summary.

        Args:
            daily_results: List of results from each advance_day() call
            start_date: Week start date
            end_date: Week end date
            milestone_info: Milestone detection info if week stopped early

        Returns:
            Dictionary with aggregated weekly results including milestone info
        """
        # Accumulate from daily results
        total_games = sum(r.get("games_played", 0) for r in daily_results)
        all_results = []
        all_transactions = []
        events_triggered = []
        phase_transition = None

        for day_result in daily_results:
            # Collect game results
            if day_result.get("results"):
                all_results.extend(day_result["results"])

            # Collect transactions
            if day_result.get("transactions_executed"):
                all_transactions.extend(day_result["transactions_executed"])

            # Collect events (offseason)
            if day_result.get("events_triggered"):
                events_triggered.extend(day_result["events_triggered"])

            # Capture phase transition (only one per week)
            if day_result.get("phase_transition"):
                phase_transition = day_result["phase_transition"]

        # Build summary message
        if events_triggered:
            message = f"Week complete ({start_date} → {end_date}). {len(events_triggered)} events triggered."
        else:
            message = f"Week complete ({start_date} → {end_date}). {total_games} games, {len(all_transactions)} trades."

        result = {
            "success": True,
            "week_complete": True,
            "current_phase": self.phase_state.phase.value,
            "phase_transition": phase_transition,
            "date": end_date,
            "games_played": total_games,
            "total_games_played": total_games,
            "results": all_results,
            "transactions_executed": all_transactions,
            "num_trades": len(all_transactions),
            "events_triggered": events_triggered,
            "message": message,
            "days_simulated": len(daily_results),
        }

        # Add milestone info if detected (week stopped early)
        if milestone_info:
            result['milestone_detected'] = True
            result['milestone_type'] = milestone_info['milestone_type']
            result['milestone_date'] = milestone_info['milestone_date']
        else:
            result['milestone_detected'] = False

        return result

    def simulate_to_end(self) -> Dict[str, Any]:
        """
        Simulate entire remaining season (all phases).

        Continues until offseason reached.

        Returns:
            Complete season summary
        """
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATING TO END OF SEASON'.center(80)}")
            print(f"{'='*80}")

        # Continue until offseason
        while self.phase_state.phase != SeasonPhase.OFFSEASON:
            self.advance_week()

        return {
            "start_date": str(start_date),
            "end_date": str(self.calendar.get_current_date()),
            "total_games": self.total_games_played - initial_games,
            "final_phase": self.phase_state.phase.value,
            "season_summary": self.season_summary,
            "success": True,
        }

    def simulate_to_phase_end(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulate until current phase ends (detected by phase transition).

        Uses dynamic detection - runs day-by-day until PhaseCompletionChecker
        triggers a phase transition. No pre-calculation of end dates required.

        Args:
            progress_callback: Optional callback(week_num, games_played) for progress updates

        Returns:
            Dict with success, dates, statistics, and phase transition info
        """
        starting_phase = self.phase_state.phase
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played

        days_simulated = 0
        MAX_DAYS = 365  # Safety limit to prevent infinite loops

        if self.verbose_logging:
            print(f"\n[SIMULATE_TO_PHASE_END] Starting: {starting_phase.value.upper()}")
            print(f"[SIMULATE_TO_PHASE_END] Will simulate until phase transition detected")

        # Simulate day-by-day until phase changes
        while days_simulated < MAX_DAYS:
            day_result = self.advance_day()
            days_simulated += 1

            # Progress callback
            if progress_callback:
                current_weeks = days_simulated // 7
                current_games = self.total_games_played - initial_games
                progress_callback(current_weeks, current_games)

            # Check if phase transitioned
            if day_result.get("phase_transition"):
                if self.verbose_logging:
                    print(f"[SIMULATE_TO_PHASE_END] Phase transition detected after {days_simulated} days")
                break

            # Double-check phase hasn't changed (belt and suspenders)
            if self.phase_state.phase != starting_phase:
                if self.verbose_logging:
                    print(f"[SIMULATE_TO_PHASE_END] Phase changed: {starting_phase.value} → {self.phase_state.phase.value}")
                break

        # Build result
        end_date = self.calendar.get_current_date()
        ending_phase = self.phase_state.phase
        games_played = self.total_games_played - initial_games
        weeks_simulated = days_simulated // 7

        # Check if we hit safety limit
        if days_simulated >= MAX_DAYS:
            return self._create_failure_result(
                f"Safety limit reached ({MAX_DAYS} days) without phase transition",
                start_date
            )

        return {
            "success": True,
            "message": f"Simulated to end of {starting_phase.value}",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "days_simulated": days_simulated,
            "weeks_simulated": weeks_simulated,
            "total_games": games_played,
            "starting_phase": starting_phase.value,
            "ending_phase": ending_phase.value,
            "phase_transition": ending_phase != starting_phase,
        }

    def simulate_to_next_offseason_milestone(
        self, progress_callback=None
    ) -> Dict[str, Any]:
        """
        Simulate to next offseason milestone (stops at EVERY milestone).

        Includes ALL events: deadlines, window starts/ends, and milestone markers.
        Gives user control at every major offseason event.

        If no more offseason milestones exist, checks if offseason is complete
        and automatically transitions to PRESEASON (new season).

        Now uses generic simulate_to_date() method for implementation.

        Args:
            progress_callback: Optional callback(days_advanced, total_days) for UI progress updates

        Returns:
            {
                'start_date': str,
                'end_date': str,
                'days_simulated': int,
                'milestone_reached': str,  # Display name
                'milestone_type': str,     # Event type
                'milestone_date': str,
                'events_triggered': List,
                'success': bool,
                'message': str,
                'transition_occurred': bool,  # Whether phase transition happened
                'new_season': bool  # Whether new season was initialized
            }
        """
        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            return {
                "success": False,
                "message": "Not in offseason phase",
                "start_date": str(self.calendar.get_current_date()),
                "end_date": str(self.calendar.get_current_date()),
                "days_simulated": 0,
            }

        starting_phase = self.phase_state.phase.value
        starting_year = self.season_year

        # Query next milestone from event database
        next_milestone = self.db.events_get_next_offseason_milestone(
            current_date=self.calendar.get_current_date(), season_year=self.season_year
        )

        if not next_milestone:
            # No more offseason milestones - check if offseason is complete
            self.logger.info(
                "No more offseason milestones found. Checking if offseason is complete..."
            )

            try:
                # Check if we should transition to next season
                transition_result = self._check_phase_transition()

                if transition_result and transition_result.get("to_phase"):
                    # Transition happened (OFFSEASON → PRESEASON)
                    return self._build_offseason_complete_result(starting_phase, starting_year)
                else:
                    # No transition occurred - waiting for preseason start
                    return self._handle_no_milestone_found(starting_phase)
            except Exception as e:
                self.logger.error(f"Transition check failed: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Phase transition check failed: {str(e)}",
                    "starting_phase": starting_phase,
                    "ending_phase": self.phase_state.phase.value,
                    "error_type": "transition_check_exception",
                    "weeks_simulated": 0,
                    "total_games": 0,
                    "days_simulated": 0,
                    "events_executed": 0,
                    "start_date": str(self.calendar.get_current_date()),
                    "end_date": str(self.calendar.get_current_date()),
                }

        # Use simulate_to_date to reach milestone
        milestone_date = next_milestone["event_date"]  # Already a Date object
        result = self.simulate_to_date(
            milestone_date, execute_events=True, progress_callback=progress_callback
        )

        # Enrich result with milestone metadata and return
        return self._enrich_milestone_result(result, next_milestone, starting_phase, starting_year)

    def simulate_to_date(
        self, target_date: Date, execute_events: bool = True, progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generic simulation advancing day-by-day to target date.

        This is the core simulation method that all other simulation methods use.
        Handles offseason, regular season, and playoffs uniformly.

        Args:
            target_date: Date to simulate until
            execute_events: Whether to execute events encountered (default True)
            progress_callback: Optional callback(current_day, total_days) for UI

        Returns:
            {
                'success': bool,
                'start_date': str,
                'end_date': str,
                'days_simulated': int,
                'events_triggered': List[Dict],
                'games_played': int,
                'message': str
            }
        """
        # Validate target_date is in future
        current_date = self.calendar.get_current_date()
        if target_date <= current_date:
            return {
                "success": False,
                "start_date": str(current_date),
                "end_date": str(current_date),
                "days_simulated": 0,
                "events_triggered": [],
                "games_played": 0,
                "message": f"Target date ({target_date}) must be after current date ({current_date})",
            }

        # Track start state
        start_date = current_date
        initial_games = self.total_games_played
        events_triggered = []

        # Calculate total days for progress tracking
        target_py_date = target_date.to_python_date()
        start_py_date = start_date.to_python_date()
        total_days = (target_py_date - start_py_date).days
        days_advanced = 0

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATING TO DATE'.center(80)}")
            print(f"{'='*80}")
            print(f"From: {start_date}")
            print(f"To: {target_date}")
            print(f"Total Days: {total_days}")
            print(f"Execute Events: {execute_events}")
            print(f"{'='*80}")

        # Day-by-day loop until target reached
        while self.calendar.get_current_date() < target_date:
            # Advance one day (handles events if execute_events via advance_day's SimulationExecutor)
            day_result = self.advance_day()
            days_advanced += 1

            # Collect events triggered
            if day_result.get("events_triggered"):
                events_triggered.extend(day_result["events_triggered"])

            # Progress callback for UI
            if progress_callback and total_days > 0:
                progress_callback(days_advanced, total_days)

            # Safety check: prevent infinite loops
            if days_advanced > total_days + 7:  # Allow 7-day buffer for tolerance
                self.logger.warning(
                    f"Simulation exceeded expected days ({days_advanced} > {total_days})"
                )
                break

        end_date = self.calendar.get_current_date()
        games_played = self.total_games_played - initial_games

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATION TO DATE COMPLETE'.center(80)}")
            print(f"{'='*80}")
            print(f"Start: {start_date}")
            print(f"End: {end_date}")
            print(f"Days: {days_advanced}")
            print(f"Games: {games_played}")
            print(f"Events: {len(events_triggered)}")
            print(f"{'='*80}")

        return {
            "success": True,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "days_simulated": days_advanced,
            "events_triggered": events_triggered,
            "games_played": games_played,
            "message": f"Simulated {days_advanced} days ({start_date} → {end_date}). {games_played} games, {len(events_triggered)} events.",
        }

    def get_next_offseason_milestone_name(self) -> str:
        """
        Get display name for next offseason milestone (for UI button text).

        DEPRECATED: Use get_next_milestone_action() instead for more detailed info.

        Returns:
            Display name like "Franchise Tags", "Free Agency", "Draft", etc.
            Returns descriptive text if no more milestones (e.g., "Next Season", "Wait 62 days").
        """
        # Use new action logic for consistency
        action = self.get_next_milestone_action()

        # Return milestone name if available, otherwise use action text
        return action.get("milestone_name", action["text"])

    def get_next_milestone_action(self) -> Dict[str, Any]:
        """
        Determine what action the "Next Milestone" button should take.

        Analyzes current state to determine what action is available:
        - simulate_to_milestone: Next offseason milestone exists
        - start_preseason: Preseason start date reached
        - wait: Waiting for preseason to begin
        - disabled: Not in offseason phase

        Returns:
            Dict with action information:
            {
                'action': str - Action type (simulate_to_milestone|start_preseason|wait|disabled)
                'text': str - Button text to display
                'tooltip': str - Detailed tooltip text
                'enabled': bool - Whether button should be enabled
                'milestone_name': str - Milestone name (if applicable)
                'milestone_date': str - Milestone date in "MMM DD, YYYY" format (if applicable)
                'days_remaining': int - Days until milestone/preseason (if applicable)
            }
        """
        # Check if in offseason phase
        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            return {
                "action": "disabled",
                "text": "Not in Offseason",
                "tooltip": f"Currently in {self.phase_state.phase.value.replace('_', ' ').title()}",
                "enabled": False,
            }

        current_date = self.calendar.get_current_date()

        # Validate current_date (fix: Issue #3 - None check)
        if not current_date:
            self.logger.error("Failed to get current date from calendar")
            return {
                "action": "disabled",
                "text": "Error",
                "tooltip": "Unable to determine current date. Check database configuration.",
                "enabled": False,
            }

        # Check for next milestone
        next_milestone = self.db.events_get_next_offseason_milestone(
            current_date=current_date, season_year=self.season_year
        )

        if next_milestone:
            # Milestone exists - can simulate to it
            milestone_date = next_milestone["event_date"]  # Date object
            milestone_date = normalize_date(milestone_date)  # Fix: Ensure Date compatibility across import paths
            milestone_name = next_milestone["display_name"]

            # Calculate days remaining (fix: Issue #5 - use days_until() method)
            days_away = current_date.days_until(milestone_date)

            # Edge case: milestone already passed or is today (fix: Issue #6)
            if days_away <= 0:
                self.logger.warning(
                    f"Milestone {milestone_name} is today or has passed (days_away={days_away}). "
                    f"Skipping to check for next milestone."
                )
                # Treat as no milestone - will fall through to preseason check
                next_milestone = None
            else:
                # Format date for display (fix: Issue #1 - use to_python_date())
                date_str = milestone_date.to_python_date().strftime("%b %d, %Y")

                # Build tooltip with details
                tooltip = (
                    f"Simulate to: {milestone_name}\n"
                    f"Date: {date_str}\n"
                    f"Days away: {days_away}"
                )

                return {
                    "action": "simulate_to_milestone",
                    "text": f"Sim to {milestone_name}",
                    "tooltip": tooltip,
                    "enabled": True,
                    "milestone_name": milestone_name,
                    "milestone_date": date_str,
                    "days_remaining": days_away,
                }

        # If we reach here, no valid future milestone exists
        # Check if ready for preseason
        try:
            preseason_start = self._get_preseason_start_date()
        except Exception as e:
            # If we can't determine preseason start, show error state
            self.logger.error(f"Failed to determine preseason start date: {e}")
            return {
                "action": "disabled",
                "text": "Error",
                "tooltip": "Unable to determine preseason start date. Check database configuration.",
                "enabled": False,
            }

        # Normalize preseason_start to ensure Date compatibility across import paths
        preseason_start = normalize_date(preseason_start)

        # Check if preseason start reached
        if current_date >= preseason_start:
            return {
                "action": "start_preseason",
                "text": "Start Preseason",
                "tooltip": "All offseason milestones complete. Ready to transition to preseason.",
                "enabled": True,
            }

        # Waiting for preseason - calculate days remaining (fix: Issue #5 - use days_until())
        days_until = current_date.days_until(preseason_start)
        # Format date for display (fix: Issue #1 - use to_python_date())
        preseason_date_str = preseason_start.to_python_date().strftime("%b %d, %Y")

        # Build detailed tooltip
        tooltip = (
            f"No milestones remaining.\n"
            f"Preseason starts: {preseason_date_str}\n"
            f"Days remaining: {days_until}\n\n"
            f"Use 'Advance Day' or 'Advance Week' to continue."
        )

        return {
            "action": "wait",
            "text": f"Wait {days_until} days",
            "tooltip": tooltip,
            "enabled": False,  # Disable button when waiting
            "days_remaining": days_until,
            "preseason_start": preseason_date_str,
        }

    def simulate_to_new_season(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulates through all remaining offseason events until preseason starts.

        This is a convenience method that repeatedly calls simulate_to_next_offseason_milestone()
        until the OFFSEASON→PRESEASON transition occurs.

        Args:
            progress_callback: Optional callback(current, total, event_name) for UI progress updates

        Returns:
            dict: Simulation result with aggregated information about all milestones
                  processed and the final transition to new season.
                  {
                      'success': bool,
                      'start_date': str,
                      'end_date': str,
                      'starting_phase': str,
                      'ending_phase': str,
                      'starting_year': int,
                      'ending_year': int,
                      'weeks_simulated': int,
                      'total_games': int,
                      'phase_transition': bool,
                      'days_simulated': int,
                      'events_executed': int,
                      'event_list': List[str],
                      'milestones_processed': List[Dict],
                      'total_milestones': int,
                      'total_days': int,
                      'message': str
                  }
        """
        starting_phase = self.phase_state.phase.value
        starting_year = self.season_year
        starting_date = self.calendar.get_current_date()

        # Validate we're in offseason
        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            self.logger.warning(
                f"Cannot simulate to new season from {starting_phase.upper()} phase"
            )
            return {
                "success": False,
                "message": f"Cannot simulate to new season from {starting_phase.upper()} phase. Must be in OFFSEASON.",
                "starting_phase": starting_phase,
                "ending_phase": starting_phase,
                "weeks_simulated": 0,
                "total_games": 0,
                "phase_transition": False,
                "days_simulated": 0,
                "events_executed": 0,
                "event_list": [],
            }

        self.logger.info(
            f"Starting simulate_to_new_season from {starting_date}, season {starting_year}"
        )

        milestones_processed = []
        total_days = 0
        all_events = []
        max_iterations = 50  # Safety limit

        for iteration in range(max_iterations):
            result = self.simulate_to_next_offseason_milestone(
                progress_callback=progress_callback
            )

            if not result["success"]:
                error_type = result.get("error_type")

                if error_type == "incomplete_offseason_no_milestones":
                    self.logger.error(
                        f"Unexpected incomplete offseason state after {iteration} iterations"
                    )
                    return {
                        "success": False,
                        "message": f"Simulation stalled: {result['message']}\n\nProcessed {len(milestones_processed)} milestones before error.",
                        "starting_phase": starting_phase,
                        "ending_phase": self.phase_state.phase.value,
                        "milestones_processed": milestones_processed,
                        "total_days": total_days,
                        "weeks_simulated": total_days // 7,
                        "total_games": 0,
                        "phase_transition": False,
                        "days_simulated": total_days,
                        "events_executed": len(all_events),
                        "event_list": all_events,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Simulation failed: {result['message']}",
                        "starting_phase": starting_phase,
                        "ending_phase": self.phase_state.phase.value,
                        "milestones_processed": milestones_processed,
                        "total_days": total_days,
                        "weeks_simulated": total_days // 7,
                        "total_games": 0,
                        "phase_transition": False,
                        "days_simulated": total_days,
                        "events_executed": len(all_events),
                        "event_list": all_events,
                    }

            # Track milestone if one was processed
            if "milestone_reached" in result:
                milestones_processed.append(
                    {
                        "name": result["milestone_reached"],
                        "date": result["milestone_date"],
                        "days_simulated": result.get("days_simulated", 0),
                    }
                )
                total_days += result.get("days_simulated", 0)
                self.logger.info(
                    f"Processed milestone {len(milestones_processed)}: {result['milestone_reached']}"
                )

            # Track events
            if "events_triggered" in result:
                for event in result["events_triggered"]:
                    event_name = event.get(
                        "display_name", event.get("event_type", "Unknown")
                    )
                    all_events.append(event_name)

            # Check if transition to new season occurred
            if result.get("transition_occurred") or result.get("new_season"):
                ending_date = self.calendar.get_current_date()
                self.logger.info(
                    f"Successfully completed offseason! Transitioned from season {starting_year} to {self.season_year}. "
                    f"Processed {len(milestones_processed)} milestones in {total_days} days."
                )
                return {
                    "success": True,
                    "message": f"Successfully simulated to new season! Transitioned from season {starting_year} to {self.season_year}.",
                    "starting_phase": starting_phase,
                    "ending_phase": self.phase_state.phase.value,
                    "starting_year": starting_year,
                    "ending_year": self.season_year,
                    "starting_date": str(starting_date),
                    "ending_date": str(ending_date),
                    "start_date": str(starting_date),
                    "end_date": str(ending_date),
                    "milestones_processed": milestones_processed,
                    "total_milestones": len(milestones_processed),
                    "total_days": total_days,
                    "weeks_simulated": total_days // 7,
                    "total_games": 0,
                    "phase_transition": True,
                    "days_simulated": total_days,
                    "events_executed": len(all_events),
                    "event_list": all_events,
                    "new_season_year": self.season_year,
                }

        # Should never reach here unless we hit max iterations
        self.logger.error(
            f"simulate_to_new_season exceeded {max_iterations} iterations"
        )
        return {
            "success": False,
            "message": f"Exceeded {max_iterations} iterations without transitioning. Possible infinite loop.",
            "starting_phase": starting_phase,
            "ending_phase": self.phase_state.phase.value,
            "milestones_processed": milestones_processed,
            "iterations": max_iterations,
            "weeks_simulated": 0,
            "total_games": 0,
            "phase_transition": False,
            "days_simulated": total_days,
            "events_executed": len(all_events),
            "event_list": all_events,
        }

    def get_current_phase(self) -> SeasonPhase:
        """Get current season phase."""
        return self.phase_state.phase

    def get_current_standings(self) -> Dict[str, Any]:
        """
        Get current standings (only available during regular season).

        Returns:
            Standings organized by division/conference
        """
        if self.phase_state.phase != SeasonPhase.REGULAR_SEASON:
            # Return final regular season standings from database
            return self.db.standings_get(
                season=self.season_year, season_type=PhaseNames.DB_REGULAR_SEASON
            )

        # Delegate to the current phase handler
        current_handler = self.phase_handlers.get(self.phase_state.phase)
        if current_handler and hasattr(current_handler, 'get_current_standings'):
            return current_handler.get_current_standings(dynasty_id=self.dynasty_id)
        else:
            # Fallback to direct database query
            return self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

    def get_playoff_bracket(self) -> Optional[Dict[str, Any]]:
        """
        Get playoff bracket (available during playoffs and offseason).

        Returns:
            Bracket data or None if not available
        """
        # Only hide bracket during regular season (before playoffs start)
        if self.phase_state.phase.value == "regular_season":
            return None

        # Lazy initialization: If playoff controller not initialized but we need it, restore it
        # This handles the case when app restarts during playoffs or offseason
        if not self.playoff_controller and self.phase_state.phase.value in [
            "playoffs",
            "offseason",
        ]:
            try:
                if self.verbose_logging:
                    print(
                        f"[DEBUG] get_playoff_bracket(): playoff_controller is None, attempting restoration..."
                    )
                self._restore_playoff_controller()
            except Exception as e:
                self.logger.error(f"Failed to restore playoff controller: {e}")
                if self.verbose_logging:
                    print(f"[ERROR] Failed to restore playoff controller: {e}")
                return None

        if not self.playoff_controller:
            return None

        return self.playoff_controller.get_current_bracket()

    def get_current_state(self) -> Dict[str, Any]:
        """Get comprehensive current state."""
        return {
            "current_phase": self.phase_state.phase.value,
            "current_date": str(self.calendar.get_current_date()),
            "season_year": self.season_year,
            "dynasty_id": self.dynasty_id,
            "total_games_played": self.total_games_played,
            "total_days_simulated": self.total_days_simulated,
            "active_controller": (
                type(self.active_controller).__name__
                if self.active_controller
                else None
            ),
        }

    # ========== Private Methods ==========

    def _get_transaction_service(self) -> TransactionService:
        """
        Lazy initialization factory for TransactionService.

        Creates TransactionService on first use with dependency injection pattern.
        The service receives shared dependencies from controller (UnifiedDatabaseAPI,
        CalendarManager, Logger) to leverage connection pooling and dynasty isolation.

        Returns:
            TransactionService: Initialized transaction service instance
        """
        if not hasattr(self, "_transaction_service"):
            from transactions.transaction_ai_manager import TransactionAIManager

            # Create AI manager with debug mode
            transaction_ai = TransactionAIManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                debug_mode=True,  # Enable debug mode for UI debug log window
            )

            # Create service with dependency injection
            self._transaction_service = TransactionService(
                db=self.db,
                calendar=self.calendar,
                transaction_ai=transaction_ai,
                logger=self.logger,
                dynasty_id=self.dynasty_id,
                database_path=self.database_path,
                season_year=self.season_year,
            )

        return self._transaction_service

    def _get_contract_transition_service(self) -> "ContractTransitionService":
        """
        Lazy initialization factory for ContractTransitionService.

        Creates ContractTransitionService on first use with dependency injection pattern.
        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.

        Returns:
            ContractTransitionService: Initialized contract transition service instance
        """
        if not hasattr(self, "_contract_transition_service"):
            from services.contract_transition_service import ContractTransitionService
            from salary_cap.cap_database_api import CapDatabaseAPI

            # Create CapDatabaseAPI for contract operations
            cap_api = CapDatabaseAPI(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id
            )

            # Create service with dependency injection
            self._contract_transition_service = ContractTransitionService(
                cap_api=cap_api,
                dynasty_id=self.dynasty_id
            )

        return self._contract_transition_service

    def _get_draft_preparation_service(self) -> "DraftPreparationService":
        """
        Lazy initialization factory for DraftPreparationService.

        Creates DraftPreparationService on first use with dependency injection pattern.
        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.

        Returns:
            DraftPreparationService: Initialized draft preparation service instance
        """
        if not hasattr(self, "_draft_preparation_service"):
            from services.draft_preparation_service import DraftPreparationService
            from offseason.draft_manager import DraftManager
            from database.draft_class_api import DraftClassAPI

            # Create DraftManager for draft class generation
            draft_manager = DraftManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season_year=self.season_year,
                enable_persistence=self.enable_persistence
            )

            # Create DraftClassAPI for validation
            draft_api = DraftClassAPI(database_path=self.database_path)

            # Create service with dependency injection
            self._draft_preparation_service = DraftPreparationService(
                draft_manager=draft_manager,
                draft_api=draft_api,
                dynasty_id=self.dynasty_id
            )

        return self._draft_preparation_service

    def _get_season_transition_service(self) -> "SeasonTransitionService":
        """
        Lazy initialization factory for SeasonTransitionService.

        Creates SeasonTransitionService on first use with dependency injection pattern.
        Orchestrates year transitions using ContractTransitionService and DraftPreparationService.
        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.

        Returns:
            SeasonTransitionService: Initialized season transition service instance
        """
        if not hasattr(self, "_season_transition_service"):
            from services.season_transition_service import SeasonTransitionService

            # Create service with dependency injection
            # Uses other services (lazy-initialized via getters)
            self._season_transition_service = SeasonTransitionService(
                contract_service=self._get_contract_transition_service(),
                draft_service=self._get_draft_preparation_service(),
                dynasty_id=self.dynasty_id
            )

        return self._season_transition_service

    def _set_season_year(self, new_year: int, reason: str) -> None:
        """
        Logged setter for season_year (Phase 1: Observation).

        This method wraps all season_year modifications with detailed logging
        to track when and why the year changes. This helps diagnose
        desynchronization issues between controller and database.

        Args:
            new_year: New season year value
            reason: Human-readable explanation of why year is changing
                   Examples: "Initial load from database"
                           "OFFSEASON→PRESEASON transition"
                           "Rollback due to transition failure"

        Note:
            This is Part of Phase 1 (Observation & Validation) - adds visibility
            without changing behavior. In later phases, this will be replaced with
            SeasonYearSynchronizer for atomic database updates.
        """
        old_year = self.season_year
        self.season_year = new_year

        # Log all changes for debugging desynchronization
        if old_year != new_year:
            self.logger.info(
                f"[YEAR_CHANGE] {old_year} → {new_year} | "
                f"Reason: {reason} | "
                f"Dynasty: {self.dynasty_id}"
            )

            if self.verbose_logging:
                # Phase may not be initialized yet during construction
                phase_str = (
                    self.phase_state.phase.value
                    if hasattr(self, "phase_state")
                    else "not initialized"
                )
                print(
                    f"[YEAR_CHANGE] Season year changed: {old_year} → {new_year}\n"
                    f"  Reason: {reason}\n"
                    f"  Dynasty: {self.dynasty_id}\n"
                    f"  Phase: {phase_str}"
                )
        else:
            # No-op assignment (same value)
            self.logger.debug(
                f"[YEAR_NO_CHANGE] {old_year} (unchanged) | "
                f"Reason: {reason} | "
                f"Dynasty: {self.dynasty_id}"
            )

    def _derive_season_year_from_date(self, date: Date) -> int:
        """
        Derive season year from calendar date.

        Delegates to PhaseBoundaryDetector for centralized logic.

        Args:
            date: Calendar date

        Returns:
            NFL season year derived from date
        """
        return self.boundary_detector.derive_season_year(date)

    def _validate_season_year_matches_date(self) -> None:
        """
        Validate that season_year matches current calendar date.

        Defensive check to catch drift between stored season_year
        and what should be derived from current_date.

        Raises:
            RuntimeError: If season_year doesn't match derived year from date
        """
        current_date = self.calendar.get_current_date()
        derived_year = self._derive_season_year_from_date(current_date)

        if self.season_year != derived_year:
            raise RuntimeError(
                f"Season year drift detected!\n"
                f"  Stored season_year: {self.season_year}\n"
                f"  Current date: {current_date}\n"
                f"  Derived year from date: {derived_year}\n"
                f"  Drift amount: {self.season_year - derived_year} years"
            )

    def _auto_recover_year_from_database(self, context: str = "Unknown") -> bool:
        """
        Auto-recover season_year from database if drift detected (Phase 5: Protective Guards).

        This protective guard detects when in-memory season_year has drifted
        from the database source of truth and automatically recovers by loading
        the correct year from the database.

        Process:
        1. Validate current year against database
        2. If drift detected and recovery possible:
           - Log warning with drift details
           - Load correct year from database
           - Update in-memory season_year via synchronizer
           - Return True (recovery performed)
        3. If no drift or recovery not possible:
           - Return False (no recovery needed/possible)

        Args:
            context: Context string for logging (e.g., "Before phase transition")

        Returns:
            True if recovery was performed, False if not needed or not possible

        Examples:
            >>> # Before critical operation
            >>> if self._auto_recover_year_from_database("Before game simulation"):
            ...     print("Year drift was auto-corrected")
        """
        is_synced, db_year, can_recover = (
            self.season_year_validator.validate_with_recovery(
                controller_year=self.season_year,
                dynasty_id=self.dynasty_id,
                dynasty_api=self.db,  # Phase 2: dynasty_api consolidated into UnifiedDatabaseAPI
            )
        )

        if is_synced:
            # No drift detected - all good
            return False

        if not can_recover:
            # Drift detected but no database state to recover from
            self.logger.error(
                f"[AUTO_RECOVERY_FAILED] Season year drift detected but cannot recover:\n"
                f"  Context: {context}\n"
                f"  Controller Year: {self.season_year}\n"
                f"  Database Year: {db_year}\n"
                f"  Reason: No valid database state found\n"
                f"  Action: Continuing with controller year (may cause issues)"
            )
            return False

        # Drift detected and recovery is possible
        drift_amount = abs(self.season_year - db_year)
        drift_direction = "ahead" if self.season_year > db_year else "behind"

        self.logger.warning(
            f"[AUTO_RECOVERY] Season year drift detected - auto-recovering:\n"
            f"  Context: {context}\n"
            f"  Controller Year (WRONG): {self.season_year}\n"
            f"  Database Year (CORRECT): {db_year}\n"
            f"  Drift: {drift_amount} year(s) {drift_direction}\n"
            f"  Dynasty: {self.dynasty_id}\n"
            f"  Action: Loading correct year from database"
        )

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"⚠️  AUTO-RECOVERY: Season year drift detected!")
            print(f"{'='*80}")
            print(f"Context: {context}")
            print(f"Wrong value (in-memory): {self.season_year}")
            print(f"Correct value (database): {db_year}")
            print(f"Recovering to database value...")
            print(f"{'='*80}\n")

        # Perform recovery - use synchronizer for atomic update
        old_year = self.season_year
        self.year_synchronizer.synchronize_year(
            db_year,
            f"Auto-recovery from drift (was {old_year}, corrected to {db_year}) - {context}",
        )

        self.logger.info(
            f"[AUTO_RECOVERY_SUCCESS] ✓ Season year recovered: "
            f"{old_year} → {db_year} ({context})"
        )

        return True

    def _update_database_year(self, new_year: int) -> None:
        """
        Update database dynasty_state.season to new year (Phase 3: Atomic Synchronization).

        This method is called by SeasonYearSynchronizer to update the database
        as part of atomic year synchronization. It updates ONLY the season field,
        preserving other state (current_date, current_phase, current_week).

        Args:
            new_year: New season year to write to database

        Raises:
            Exception: If database update fails
        """
        try:
            # Get current state to preserve other fields
            current_state = self.db.dynasty_get_latest_state()

            if not current_state:
                self.logger.warning(
                    f"[DB_UPDATE_YEAR] No existing state found for dynasty '{self.dynasty_id}'. "
                    f"Creating new state with season={new_year}"
                )
                # Initialize new state if none exists
                self.db.dynasty_initialize_state(
                    season=new_year,
                    start_date=str(self.calendar.get_current_date()),
                    start_week=0,
                    start_phase=self.phase_state.phase.value.lower(),
                )
            else:
                # Update existing state with new season
                self.db.dynasty_update_state(
                    season=new_year,  # Only changing season
                    current_date=current_state["current_date"],
                    current_phase=current_state["current_phase"],
                    current_week=current_state.get("current_week"),
                    last_simulated_game_id=current_state.get("last_simulated_game_id"),
                )

            self.logger.debug(
                f"[DB_UPDATE_YEAR] Database dynasty_state.season updated to {new_year} "
                f"for dynasty '{self.dynasty_id}'"
            )

        except Exception as e:
            self.logger.error(
                f"[DB_UPDATE_YEAR] Failed to update database year to {new_year}: {e}",
                exc_info=True,
            )
            raise

    def _check_phase_transition(self) -> Optional[Dict[str, Any]]:
        """
        Check if phase transition should occur using PhaseTransitionManager.

        Uses the new testable phase transition system with dependency injection.
        Maintains backward compatibility by delegating to existing transition methods.

        Returns:
            Transition info if occurred, None otherwise
        """
        # Phase 1.3: Validate year sync before phase transition
        self.season_year_validator.log_validation_report(
            controller_year=self.season_year,
            dynasty_id=self.dynasty_id,
            dynasty_api=self.db,  # Phase 2: dynasty_api consolidated into UnifiedDatabaseAPI
            context="Before phase transition check",
        )

        # Phase 5: Auto-recovery guard before phase transition
        self._auto_recover_year_from_database("Before phase transition check")

        if self.verbose_logging:
            print(
                f"\n[DEBUG] Checking phase transition (current phase: {self.phase_state.phase.value})"
            )

        # [PRESEASON_DEBUG Point 1] Transition Detection Check
        print(f"\n[PRESEASON_DEBUG Point 1] Checking transition detection...")
        print(f"  Current phase: {self.phase_state.phase.value}")
        print(f"  Phase object: {self.phase_state.phase}")
        print(f"  Phase type: {type(self.phase_state.phase)}")
        print(f"  SeasonPhase.PRESEASON: {SeasonPhase.PRESEASON}")
        print(f"  Are they equal? {self.phase_state.phase.value == 'preseason'}")
        print(f"  Current date: {self.calendar.get_current_date()}")
        print(f"  Dynasty ID: {self.dynasty_id}")

        # Check if transition is needed (pure logic, no side effects)
        transition = self.phase_transition_manager.check_transition_needed()

        print(f"[PRESEASON_DEBUG Point 1] Transition result: {transition}")
        if transition:
            print(f"  From: {transition.from_phase.value}")
            print(f"  To: {transition.to_phase.value}")
            print(f"  Trigger: {transition.trigger}")
        else:
            print(f"  No transition needed")

        if transition is None:
            # No transition needed
            if self.verbose_logging and self.phase_state.phase.value == "playoffs":
                if not self._is_super_bowl_complete():
                    print(
                        f"[DEBUG] Super Bowl not yet complete, remaining in PLAYOFFS phase"
                    )
            return None

        # Transition needed - execute it
        if self.verbose_logging:
            print(f"\n[PHASE_TRANSITION] {transition}")

        # Execute transition using existing methods (backward compatible)
        if (
            transition.from_phase.value == "preseason"
            and transition.to_phase.value == "regular_season"
        ):
            self._transition_to_regular_season()
            return {
                "from_phase": "preseason",
                "to_phase": "regular_season",
                "trigger": transition.trigger,
            }

        elif (
            transition.from_phase.value == "regular_season"
            and transition.to_phase.value == "playoffs"
        ):
            self._transition_to_playoffs()
            return {
                "from_phase": "regular_season",
                "to_phase": "playoffs",
                "trigger": transition.trigger,
            }

        elif (
            transition.from_phase.value == "playoffs"
            and transition.to_phase.value == "offseason"
        ):
            print(f"\n{'='*80}")
            print(f"[SUPER_BOWL_FLOW] Super Bowl complete detected!")
            print(f"[SUPER_BOWL_FLOW] Transitioning from PLAYOFFS → OFFSEASON")
            print(f"[SUPER_BOWL_FLOW] Using PlayoffsToOffseasonHandler")
            print(f"{'='*80}")

            # Use handler system instead of direct method call
            success = self.phase_transition_manager.execute_transition(transition)

            if not success:
                raise RuntimeError("PLAYOFFS → OFFSEASON transition failed")

            print(f"[SUPER_BOWL_FLOW] ✓ Transition completed successfully")

            return {
                "from_phase": "playoffs",
                "to_phase": "offseason",
                "trigger": transition.trigger,
                "success": True
            }

        elif (
            transition.from_phase.value == "offseason"
            and transition.to_phase.value == "preseason"
        ):
            # [PRESEASON_DEBUG Point 2] OFFSEASON→PRESEASON Case Match
            print(f"\n[PRESEASON_DEBUG Point 2] ✅ OFFSEASON→PRESEASON case matched!")
            print(f"  Current year: {self.season_year}")
            print(f"  New season year: {self.season_year + 1}")
            print(f"  Dynasty ID: {self.dynasty_id}")

            print(f"\n{'='*80}")
            print(f"[NEW_SEASON_FLOW] Offseason complete detected!")
            print(f"[NEW_SEASON_FLOW] Current date: {self.calendar.get_current_date()}")
            # Using PhaseBoundaryDetector for centralized boundary logic
            print(
                f"[NEW_SEASON_FLOW] Preseason start: {self.boundary_detector.get_phase_start_date(SeasonPhase.PRESEASON, season_year=self.season_year + 1)}"
            )
            print(f"[NEW_SEASON_FLOW] Transitioning from OFFSEASON → PRESEASON")
            print(
                f"[NEW_SEASON_FLOW] Generating preseason schedule ({SeasonConstants.PRESEASON_GAME_COUNT} games)..."
            )
            print(
                f"[NEW_SEASON_FLOW] Generating regular season schedule ({SeasonConstants.REGULAR_SEASON_GAME_COUNT} games)..."
            )
            print(f"{'='*80}")

            try:
                # [PRESEASON_DEBUG Point 3] Execute Transition Call
                print(f"\n[PRESEASON_DEBUG Point 3] Calling execute_transition()...")
                print(f"  Transition: {transition}")
                print(
                    f"  Handler registered: {self.phase_transition_manager.has_handler(TransitionHandlerKey.OFFSEASON_TO_PRESEASON)}"
                )

                # Execute the transition via PhaseTransitionManager
                # Phase 3: Use synchronizer for atomic year increment across all components
                # This prevents retrigger even if transition fails partway through
                old_year = self.season_year
                old_phase = self.phase_state.phase

                # PHASE 3: Atomic year synchronization
                new_year = self.year_synchronizer.increment_year(
                    "OFFSEASON→PRESEASON transition (new season begins)"
                )

                # NEW SEASON INITIALIZATION: Clear previous season state
                if self.verbose_logging:
                    print(
                        f"\n[NEW_SEASON_INIT] Initializing new season {self.season_year}"
                    )
                    print(
                        f"[NEW_SEASON_INIT] Clearing playoff state from previous season"
                    )

                # Clear playoff controller (removes previous season's bracket data)
                self.playoff_controller = None

                # MULTI-SEASON CRITICAL: Reset game counters for new season
                # Without this reset, phase completion detection breaks in Season 2+
                # (e.g., Season 1 ends with 333 games, Season 2 preseason would check 333 >= 48 → TRUE immediately)
                old_game_count = self.total_games_played
                self.total_games_played = 0
                self.total_days_simulated = 0

                if self.verbose_logging:
                    print(
                        f"[NEW_SEASON_INIT] Game counters reset: {old_game_count} → 0"
                    )

                # NOTE: Season statistics are archived during PLAYOFFS→OFFSEASON transition
                # See _transition_to_offseason() method for archival implementation

                if self.verbose_logging:
                    print(
                        f"[NEW_SEASON_INIT] Previous season ({old_year}) state cleared"
                    )
                    print(
                        f"[NEW_SEASON_INIT] Ready for {self.season_year} season initialization"
                    )

                # Derive season year from current calendar date (natural advancement)
                # Calendar has already advanced naturally through daily simulation
                # No need to "jump" calendar - it's already at the correct date
                current_date = self.calendar.get_current_date()
                correct_year = self._derive_season_year_from_date(current_date)

                if self.verbose_logging:
                    print(f"\n[YEAR_DERIVATION] Current date: {current_date}")
                    print(f"[YEAR_DERIVATION] Derived season year: {correct_year}")
                    print(f"[YEAR_DERIVATION] Previous season year: {self.season_year}")

                if correct_year != self.season_year:
                    self.year_synchronizer.synchronize_year(
                        correct_year,
                        f"Derived from calendar date {current_date} (OFFSEASON→PRESEASON)"
                    )
                    if self.verbose_logging:
                        print(f"[YEAR_SYNC] Season year updated: {self.season_year - 1} → {self.season_year}")
                else:
                    if self.verbose_logging:
                        print(f"[YEAR_SYNC] Season year already correct ({correct_year}), no update needed")

                # CRITICAL FIX #2: Update PhaseState with new season year
                # This ensures SimulationExecutor queries for correct year games
                self.phase_state.season_year = self.season_year

                if self.verbose_logging:
                    print(f"[PHASE_STATE] Updated season_year to {self.season_year}")

                # Update database phase (year already updated by synchronizer)
                if self.verbose_logging:
                    print(f"[PHASE_TRANSITION] Updating database phase: PRESEASON")

                self.db.dynasty_update_state(
                    season=self.season_year,  # Already updated by synchronizer
                    current_date=str(self.calendar.get_current_date()),  # Now correctly at preseason start
                    current_phase="PRESEASON",
                    current_week=0,
                )

                if self.verbose_logging:
                    print(
                        f"[PHASE_TRANSITION] Database updated - now executing transition"
                    )

                try:
                    # This calls OffseasonToPreseasonHandler.execute() which:
                    # - Generates SeasonConstants.PRESEASON_GAME_COUNT preseason games
                    # - Generates SeasonConstants.REGULAR_SEASON_GAME_COUNT regular season games
                    # - Resets all team standings to 0-0-0
                    result = self.phase_transition_manager.execute_transition(
                        transition
                    )

                    print(
                        f"[PRESEASON_DEBUG Point 3] ✅ execute_transition() completed successfully"
                    )
                    print(
                        f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                    )

                    # CRITICAL: Update phase state and active controller after successful transition
                    # This matches the pattern in _transition_to_playoffs() and _transition_to_offseason()
                    self.phase_state.phase = SeasonPhase.PRESEASON
                    self.active_controller = None  # Phase handlers manage preseason

                    if self.verbose_logging:
                        print(
                            f"[PHASE_TRANSITION] Phase state updated: OFFSEASON → PRESEASON"
                        )
                        print(
                            f"[PHASE_TRANSITION] Active controller set: None (phase handlers active)"
                        )

                    # Validate season_year matches date (defensive check)
                    self._validate_season_year_matches_date()

                except Exception as e:
                    # Rollback database state if transition fails
                    if self.verbose_logging:
                        print(
                            f"[PHASE_TRANSITION] Transition failed - rolling back database"
                        )

                    self._set_season_year(
                        old_year, f"Rollback due to transition failure: {e}"
                    )
                    self.db.dynasty_update_state(
                        season=old_year,
                        current_date=str(self.calendar.get_current_date()),
                        current_phase=old_phase.value,
                        current_week=0,
                    )

                    raise  # Re-raise the exception after rollback

                print(f"\n{'='*80}")
                print(f"[NEW_SEASON_SUCCESS] New season initialized!")
                print(f"  Season: {old_year} → {self.season_year}")
                print(f"  Phase: OFFSEASON → PRESEASON")
                print(f"  Preseason games: {SeasonConstants.PRESEASON_GAME_COUNT}")
                print(
                    f"  Regular season games: {SeasonConstants.REGULAR_SEASON_GAME_COUNT}"
                )
                print(f"  Teams reset: 32")
                print(f"{'='*80}\n")

                return {
                    "from_phase": "offseason",
                    "to_phase": "preseason",
                    "trigger": transition.trigger,
                    "new_season_year": self.season_year,
                }

            except Exception as e:
                print(f"\n{'='*80}")
                print(f"[NEW_SEASON_ERROR] Preseason schedule generation failed!")
                print(f"  Error: {e}")
                print(f"{'='*80}\n")
                raise

        return None

    def _get_preseason_games_completed(self) -> int:
        """
        Get count of COMPLETED preseason games for current season.

        This method queries the database for completed preseason games,
        ensuring phase completion detection only counts preseason games,
        not regular season or playoff games.

        Returns:
            Number of preseason games with results (completed games only)
        """
        try:
            if self.verbose_logging:
                print(f"\n[DIAG] _get_preseason_games_completed()")
                print(f"  self.season_year: {self.season_year}")
                print(f"  self.dynasty_id: {self.dynasty_id}")

            # Use API to get ONLY this dynasty's GAME events (10-100x faster with database filtering)
            dynasty_game_events = self.db.events_get_by_type(event_type="GAME")

            if self.verbose_logging:
                print(f"  Total GAME events from API: {len(dynasty_game_events)}")
                if dynasty_game_events:
                    sample = dynasty_game_events[0]
                    print(f"  Sample event structure:")
                    print(f"    - game_id: {sample.get('game_id')}")
                    print(f"    - has 'data' key: {'data' in sample}")
                    if 'data' in sample:
                        print(f"    - data.parameters.season: {sample.get('data', {}).get('parameters', {}).get('season')}")
                        print(f"    - data.parameters.season_type: {sample.get('data', {}).get('parameters', {}).get('season_type')}")
                        print(f"    - has results: {sample.get('data', {}).get('results') is not None}")

            completed_preseason_games = [
                e
                for e in dynasty_game_events
                if e.get("data", {}).get("parameters", {}).get("season")
                == self.season_year
                and e.get("data", {}).get("parameters", {}).get("season_type")
                == "preseason"
                and e.get("data", {}).get("results") is not None  # Must be completed
            ]

            count = len(completed_preseason_games)

            if self.verbose_logging:
                print(f"  Filtered completed preseason games: {count}")
                print(f"  Expected: 48")
                if count == 0:
                    print(f"  [WARNING] No games found! Checking why...")
                    # Check each condition separately
                    matching_season = [e for e in dynasty_game_events if e.get("data", {}).get("parameters", {}).get("season") == self.season_year]
                    matching_type = [e for e in dynasty_game_events if e.get("data", {}).get("parameters", {}).get("season_type") == "preseason"]
                    has_results = [e for e in dynasty_game_events if e.get("data", {}).get("results") is not None]
                    print(f"    - Events matching season={self.season_year}: {len(matching_season)}")
                    print(f"    - Events matching season_type='preseason': {len(matching_type)}")
                    print(f"    - Events with results: {len(has_results)}")
                self.logger.debug(f"Preseason games completed: {count}/48")

            return count

        except Exception as e:
            self.logger.error(f"Error counting preseason games: {e}")
            return 0

    def _get_regular_season_games_completed(self) -> int:
        """
        Get count of COMPLETED regular season games for current season.

        This method queries the database for completed regular season games,
        ensuring phase completion detection only counts regular season games,
        not preseason or playoff games.

        Critical for multi-phase seasons:
        - After 3 weeks preseason (48 games) + 14 weeks regular (224 games) = 272 total
        - Without this filter, total_games_played = 272 would trigger completion early
        - With this filter, only counts the 224 regular season games, continues to 272

        Returns:
            Number of regular season games with results (completed games only)
        """
        try:
            # Use API to get ONLY this dynasty's GAME events (10-100x faster with database filtering)
            dynasty_game_events = self.db.events_get_by_type(event_type="GAME")

            completed_regular_games = [
                e
                for e in dynasty_game_events
                if e.get("data", {}).get("parameters", {}).get("season")
                == self.season_year
                and e.get("data", {}).get("parameters", {}).get("season_type")
                == PhaseNames.DB_REGULAR_SEASON
                and e.get("data", {}).get("results") is not None  # Must be completed
            ]

            count = len(completed_regular_games)

            if self.verbose_logging:
                self.logger.debug(
                    f"Regular season games completed: {count}/{SeasonConstants.REGULAR_SEASON_GAME_COUNT}"
                )

            return count

        except Exception as e:
            self.logger.error(f"Error counting regular season games: {e}")
            return 0

    def _get_phase_specific_games_played(self) -> int:
        """
        Get game count for CURRENT phase only.

        Returns count of completed games in the current phase this season,
        excluding games from other phases. This ensures accurate phase completion
        detection when cumulative game counters include games from multiple phases.

        Phase-specific counting prevents bugs like:
        - Preseason (48 games) + 14 weeks regular (224 games) = 272 total
        - Without phase filtering: 272 >= 272 → thinks regular season is complete!
        - With phase filtering: only counts 224 regular season games → continues correctly

        Returns:
            Number of completed games in current phase for current season
        """
        current_phase = self.phase_state.phase.value

        if current_phase == "preseason":
            return self._get_preseason_games_completed()
        elif current_phase == "regular_season":
            return self._get_regular_season_games_completed()
        elif current_phase == "playoffs":
            # Playoffs use Super Bowl completion check, not game count
            # Return 0 to avoid false positives from game count threshold
            return 0
        elif current_phase == "offseason":
            # Offseason has no games
            return 0
        else:
            self.logger.warning(f"Unknown phase: {current_phase}, returning 0 games")
            return 0

    def _is_regular_season_complete(self) -> bool:
        """
        Check if regular season is complete.

        Uses a hybrid approach for reliability:
        1. Primary: Check if 272 games have been played (most reliable)
        2. Fallback: Check if current date is after last scheduled game

        This handles both normal completion and edge cases (corrupted schedules).

        Returns:
            True if regular season is complete (either by game count or date)
        """
        # PRIMARY CHECK: Have all SeasonConstants.REGULAR_SEASON_GAME_COUNT regular season games been played?
        # This is the most reliable indicator and handles corrupted schedules
        games_played = self.total_games_played
        if games_played >= SeasonConstants.REGULAR_SEASON_GAME_COUNT:
            if self.verbose_logging:
                print(
                    f"[DEBUG] Regular season complete: {games_played} games played (threshold: {SeasonConstants.REGULAR_SEASON_GAME_COUNT})"
                )
            return True

        # FALLBACK CHECK: Has date passed last scheduled regular season game?
        # This handles edge cases where games might not all be played
        # NOTE: If no games scheduled yet, can't use date check
        if self.last_regular_season_game_date is None:
            if self.verbose_logging:
                print(f"[DEBUG] Regular season check: No scheduled games yet, using game count only")
            return False  # Can't determine completion without schedule

        current_date = self.calendar.get_current_date()
        date_check = current_date > self.last_regular_season_game_date

        if self.verbose_logging:
            print(f"[DEBUG] Regular season check:")
            print(
                f"  - Games played: {games_played}/{SeasonConstants.REGULAR_SEASON_GAME_COUNT}"
            )
            print(f"  - Current date: {current_date}")
            print(f"  - Last scheduled game: {self.last_regular_season_game_date}")
            print(f"  - Date check result: {date_check}")

        return date_check

    def _is_super_bowl_complete(self) -> bool:
        """
        Check if Super Bowl has been PLAYED (not just scheduled).

        CRITICAL: This must check if the game has a winner, not just if it exists.
        The Super Bowl game is SCHEDULED after Conference Championships complete,
        but it hasn't been PLAYED yet at that point.

        Returns:
            True only if Super Bowl has been simulated and has a winner_id
        """
        if not self.playoff_controller:
            if self.verbose_logging:
                print(
                    f"\n[DEBUG] Checking Super Bowl completion: playoff_controller is None!"
                )
            return False

        super_bowl_games = self.playoff_controller.get_round_games("super_bowl")

        # Check if Super Bowl EXISTS and HAS BEEN PLAYED (has a winner)
        # Game exists but winner_id is None → scheduled but not played yet
        # Game exists and winner_id is set → game has been played
        is_complete = (
            len(super_bowl_games) > 0
            and super_bowl_games[0].get("winner_id") is not None
        )

        # Debug logging
        if self.verbose_logging:
            print(f"\n[DEBUG] _is_super_bowl_complete() called:")
            print(f"  - playoff_controller exists: True")
            print(f"  - Super Bowl games: {super_bowl_games}")
            print(f"  - Super Bowl games count: {len(super_bowl_games)}")
            if super_bowl_games:
                winner_id = super_bowl_games[0].get("winner_id")
                status = super_bowl_games[0].get("status")
                print(f"  - Super Bowl winner_id: {winner_id}")
                print(f"  - Super Bowl status: {status}")
                print(f"  - Is complete (has winner): {is_complete}")
            else:
                print(f"  - Is complete: {is_complete}")

        if is_complete:
            print(f"\n[SUPER_BOWL_FLOW] ✅ Super Bowl has been played!")
            print(
                f"[SUPER_BOWL_FLOW]    Winner: Team {super_bowl_games[0].get('winner_id')}"
            )
            print(f"[SUPER_BOWL_FLOW]    Ready to transition to OFFSEASON")
        elif len(super_bowl_games) > 0:
            print(f"\n[SUPER_BOWL_FLOW] ⏳ Super Bowl is SCHEDULED but not yet played")
            print(f"[SUPER_BOWL_FLOW]    Status: {super_bowl_games[0].get('status')}")
            print(f"[SUPER_BOWL_FLOW]    Remaining in PLAYOFFS phase")

        return is_complete

    def _transition_to_playoffs(self):
        """Execute transition from regular season to playoffs."""
        # Guard: prevent redundant transitions if already in playoffs
        if self.phase_state.phase.value == "playoffs":
            if self.verbose_logging:
                print(f"\n⚠️  Already in playoffs phase, skipping transition")
            return

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'REGULAR SEASON COMPLETE - PLAYOFFS STARTING'.center(80)}")
            print(f"{'='*80}")

        try:
            # 1. Get final regular season standings from database
            standings_data = self.db.standings_get(
                season=self.season_year, season_type=PhaseNames.DB_REGULAR_SEASON
            )

            if not standings_data or not standings_data.get("divisions"):
                self.logger.error(
                    "No regular season standings found for playoff seeding"
                )
                raise RuntimeError(
                    "Cannot calculate playoff seeding - no standings available"
                )

            # 2. Convert standings to format expected by PlayoffSeeder
            # DatabaseAPI returns standings organized by division/conference
            # Each team_data has: {'team_id': int, 'standing': EnhancedTeamStanding}
            standings_dict = {}
            for division_name, teams in standings_data.get("divisions", {}).items():
                for team_data in teams:
                    team_id = team_data["team_id"]
                    # Use the EnhancedTeamStanding object directly from database
                    standings_dict[team_id] = team_data["standing"]

            # 3. Calculate playoff seeding using PlayoffSeeder
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict,
                season=self.season_year,
                week=SeasonConstants.REGULAR_SEASON_WEEKS,
            )

            if self.verbose_logging:
                print(f"\n📋 Playoff Seeding Calculated")
                print(f"\nAFC Seeds:")
                for seed in playoff_seeding.afc.seeds:
                    print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")
                print(f"\nNFC Seeds:")
                for seed in playoff_seeding.nfc.seeds:
                    print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

            # 4. Calculate Wild Card start date
            # Using PhaseBoundaryDetector for centralized boundary logic
            wild_card_date = self.boundary_detector.get_playoff_start_date()

            if self.verbose_logging:
                print(f"\n📅 Wild Card Weekend: {wild_card_date}")

            # 5. Initialize PlayoffController with real seeding and shared calendar
            self.playoff_controller = PlayoffController(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season_year=self.season_year,
                wild_card_start_date=wild_card_date,
                initial_seeding=playoff_seeding,  # Pass real seeding from regular season!
                enable_persistence=self.enable_persistence,
                verbose_logging=self.verbose_logging,
                phase_state=self.phase_state,
                fast_mode=self.fast_mode
            )

            # Replace the playoff controller's calendar with the shared calendar
            # to maintain date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # Initialize playoff phase handler now that playoff_controller is created
            from src.season.phase_handlers import PlayoffHandler
            self.phase_handlers[SeasonPhase.PLAYOFFS] = PlayoffHandler(self.playoff_controller)

            # Override the playoff controller's random seeding with real seeding
            self.playoff_controller.original_seeding = playoff_seeding

            # Note: PlayoffController.__init__() already handles Wild Card scheduling
            # via _initialize_playoff_bracket(), which checks for existing playoff games
            # and either schedules new games OR reconstructs bracket from existing games.
            # No need to schedule here - that would bypass the duplicate check!

            # 6. Update state
            self.phase_state.phase = SeasonPhase.PLAYOFFS
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ Playoff transition complete")
                print(f"   PlayoffController initialized and bracket ready")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error transitioning to playoffs: {e}")
            if self.verbose_logging:
                print(f"❌ Playoff transition failed: {e}")
            raise

    def _transition_to_regular_season(self):
        """Execute transition from preseason to regular season."""
        # Guard: prevent redundant transitions if already in regular season
        if self.phase_state.phase == SeasonPhase.REGULAR_SEASON:
            if self.verbose_logging:
                print(f"\n⚠️  Already in regular season phase, skipping transition")
            return

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'PRESEASON COMPLETE - REGULAR SEASON STARTING'.center(80)}")
            print(f"{'='*80}")

        try:
            # Update phase state
            self.phase_state.phase = SeasonPhase.REGULAR_SEASON

            # Phase handlers manage regular season simulation
            self.active_controller = None

            if self.verbose_logging:
                print(f"\n✅ Regular season transition complete")
                print(f"   Season ready to begin Week 1")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error transitioning to regular season: {e}")
            if self.verbose_logging:
                print(f"❌ Regular season transition failed: {e}")
            raise

    def _restore_playoff_controller(self):
        """
        Restore PlayoffController when loading saved dynasty mid-playoffs.

        Called during initialization when phase_state indicates dynasty is in playoffs.
        Reconstructs bracket from existing database events without re-scheduling games.
        """
        # Phase 1.3: Validate year sync before playoff controller restoration
        self.season_year_validator.log_validation_report(
            controller_year=self.season_year,
            dynasty_id=self.dynasty_id,
            dynasty_api=self.db,  # Phase 2: dynasty_api consolidated into UnifiedDatabaseAPI
            context="Before playoff controller restoration",
        )

        # Guard: prevent duplicate initialization
        if self.playoff_controller is not None:
            if self.verbose_logging:
                print(
                    f"⚠️  Playoff controller already initialized, skipping restoration"
                )
            return

        try:
            if self.verbose_logging:
                print(f"\n{'='*80}")
                print(f"{'RESTORING PLAYOFF STATE FROM DATABASE'.center(80)}")
                print(f"{'='*80}")

            # 1. Query database for final regular season standings (needed for seeding)
            standings_data = self.db.standings_get(
                season=self.season_year, season_type=PhaseNames.DB_REGULAR_SEASON
            )

            if not standings_data or not standings_data.get("divisions"):
                self.logger.error(
                    "No regular season standings found - cannot restore playoff controller"
                )
                raise RuntimeError(
                    "Cannot restore playoff bracket - no standings available"
                )

            # 2. Convert standings to format expected by PlayoffSeeder
            standings_dict = {}
            for division_name, teams in standings_data.get("divisions", {}).items():
                for team_data in teams:
                    team_id = team_data["team_id"]
                    standings_dict[team_id] = team_data["standing"]

            # 3. Calculate playoff seeding
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict, season=self.season_year, week=18
            )

            # 4. Estimate Wild Card date (mid-January)
            # When restoring, exact date matters less since games already scheduled
            wild_card_date = Date(self.season_year + 1, 1, 18)

            if self.verbose_logging:
                print(f"\n📋 Playoff Seeding Restored")
                print(f"📅 Wild Card Weekend: {wild_card_date}")

            # 5. Initialize PlayoffController
            # The controller's __init__ will detect existing playoff games and reconstruct bracket
            self.playoff_controller = PlayoffController(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season_year=self.season_year,
                wild_card_start_date=wild_card_date,
                initial_seeding=playoff_seeding,
                enable_persistence=self.enable_persistence,
                verbose_logging=self.verbose_logging,
                phase_state=self.phase_state,
                fast_mode=self.fast_mode
            )

            # CRITICAL VALIDATION: Ensure created controller has correct season_year
            # This prevents stale playoff data from showing in new seasons
            if self.playoff_controller.season_year != self.season_year:
                self.logger.error(
                    f"Playoff controller season mismatch! "
                    f"Expected season {self.season_year}, "
                    f"got {self.playoff_controller.season_year}. "
                    f"Clearing playoff controller."
                )
                if self.verbose_logging:
                    print(
                        f"❌ SEASON MISMATCH: playoff_controller.season_year={self.playoff_controller.season_year}, "
                        f"expected={self.season_year}"
                    )
                self.playoff_controller = None
                return

            # 6. Share calendar for date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # Initialize playoff phase handler now that playoff_controller is created
            from src.season.phase_handlers import PlayoffHandler
            self.phase_handlers[SeasonPhase.PLAYOFFS] = PlayoffHandler(self.playoff_controller)

            # 7. Set as active controller
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ PlayoffController restored successfully")
                print(f"   Season Year: {self.playoff_controller.season_year}")
                print(f"   Bracket reconstructed from existing database events")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error restoring playoff controller: {e}")
            if self.verbose_logging:
                print(f"❌ Playoff restoration failed: {e}")
            raise

    def _transition_to_offseason(self):
        """
        OBSOLETE: This method is replaced by PlayoffsToOffseasonHandler.

        The PLAYOFFS → OFFSEASON transition is now handled by the phase transition
        system via PlayoffsToOffseasonHandler. This method is kept temporarily for
        reference during migration but should never be called in production code.

        See:
        - PlayoffsToOffseasonHandler (src/season/phase_transition/transition_handlers/playoffs_to_offseason.py)
        - PhaseTransitionManager (src/season/phase_transition/phase_transition_manager.py)
        - Lines 1710-1716 in this file for correct transition usage

        Migration Guide:
        Instead of calling this method directly, use:
            transition = PhaseTransition(
                from_phase=SeasonPhase.PLAYOFFS,
                to_phase=SeasonPhase.OFFSEASON,
                trigger="playoffs_complete"
            )
            self.phase_transition_manager.execute_transition(transition)

        Raises:
            NotImplementedError: Always raised to prevent accidental usage
        """
        raise NotImplementedError(
            "This method is obsolete and should not be called. "
            "Use PlayoffsToOffseasonHandler via phase_transition_manager.execute_transition() instead. "
            "See lines 1710-1716 in season_cycle_controller.py for correct usage."
        )

    def _generate_season_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive season summary.

        Returns:
            Summary with standings, champions, stat leaders
        """
        try:
            # Get final regular season standings
            final_standings = self.db.standings_get(
                season=self.season_year, season_type=PhaseNames.DB_REGULAR_SEASON
            )

            # Get Super Bowl winner
            super_bowl_games = (
                self.playoff_controller.get_round_games("super_bowl")
                if self.playoff_controller
                else []
            )
            champion_id = super_bowl_games[0]["winner_id"] if super_bowl_games else None

            # Note: Stat leaders queries would require additional DatabaseAPI methods
            # For now, we'll return basic summary
            summary = {
                "season_year": self.season_year,
                "dynasty_id": self.dynasty_id,
                "final_standings": final_standings,
                "super_bowl_champion": champion_id,
                "total_games": self.total_games_played,
                "total_days": self.total_days_simulated,
                "final_date": str(self.calendar.get_current_date()),
            }

            # Try to get stat leaders if methods exist
            try:
                # These would be future enhancements to DatabaseAPI
                # For now, they're placeholders
                summary["regular_season_leaders"] = {}
                summary["playoff_leaders"] = {}
            except Exception as e:
                self.logger.warning(f"Could not retrieve stat leaders: {e}")

            return summary

        except Exception as e:
            self.logger.error(f"Error generating season summary: {e}")
            return {
                "season_year": self.season_year,
                "dynasty_id": self.dynasty_id,
                "error": str(e),
            }

    def _generate_draft_class_if_needed(self):
        """
        Generate draft class for this season if it doesn't exist.

        Called once during SeasonCycleController initialization to ensure
        draft prospects are available for scouting throughout the season.

        The draft class is for the current season year and will be drafted
        in April of the following calendar year.

        Example: 2024 season (Sept 2024 → Feb 2025)
                 → Generate 2025 draft class in Sept 2024
                 → Draft occurs April 2025
                 → Drafted players join teams for 2025 season
        """
        # Check if draft class already exists (idempotent)
        if self.db.draft_has_class(self.season_year):
            if self.verbose_logging:
                print(f"   Draft class for {self.season_year} already exists")
            return

        # Generate draft class (224 prospects = 7 rounds × 32 teams)
        try:
            draft_class_id = self.db.draft_generate_class(season=self.season_year)

            if self.verbose_logging:
                print(f"\n🏈 Draft Class Generated:")
                print(f"   Season: {self.season_year}")
                print(
                    f"   Prospects: {SeasonConstants.DRAFT_TOTAL_PROSPECTS} ({SeasonConstants.DRAFT_ROUNDS} rounds × {SeasonConstants.NFL_TEAMS_COUNT} teams)"
                )
                print(f"   Draft Class ID: {draft_class_id}")

        except Exception as e:
            self.logger.error(f"Error generating draft class: {e}")
            if self.verbose_logging:
                print(f"⚠️  Warning: Could not generate draft class: {e}")

    # ==================== Skip to New Season Helper Methods (TODO) ====================

    def _get_remaining_offseason_events_until_preseason(self) -> List[Dict]:
        """
        Get all offseason events from current date until PRESEASON_START.

        Returns:
            List of event dicts in chronological order

        TODO: Implement this method
        See docs/plans/season_cycle_controller_implementation_plan.md for details
        """
        # Placeholder implementation
        if self.verbose_logging:
            print(f"[TODO] _get_remaining_offseason_events_until_preseason()")
        return []

    def _execute_offseason_event_auto(self, event: Dict[str, Any]):
        """
        Auto-execute offseason event in background (AI mode).

        For now, this is a placeholder. Full implementation would:
        - Franchise tags: Apply tags to top players
        - Draft: Simulate draft with AI teams
        - Free agency: Run FA signing algorithm
        - Roster cuts: AI teams cut to 53-man

        Args:
            event: Event dict with type, subtype, metadata

        TODO: Implement actual event execution logic
        See docs/plans/season_cycle_controller_implementation_plan.md for details
        """
        if self.verbose_logging:
            event_name = event.get("display_name", "Unknown Event")
            print(f"[TODO] _execute_offseason_event_auto({event_name})")

    def _initialize_next_season(self):
        """
        DEPRECATED: This method is no longer called.

        Season initialization now handled by OffseasonToPreseasonHandler
        in the phase transition system (see line 1938: phase_transition_manager.execute_transition).

        This method contains a bug at line ~2927 where dynasty_update_state is called
        without the required 'season' parameter. Not fixing since method is unused.

        Can be safely removed in future cleanup.

        ---

        Initialize new season after offseason completes.

        Steps:
        1. Increment season_year
        2. Generate preseason schedule (3 weeks, 48 games)
        3. Generate regular season schedule (17 weeks, 272 games)
        4. Reset all 32 team standings to 0-0-0
        5. Update dynasty_state
        6. Transition phase to PRESEASON
        7. Reinitialize season_controller
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'INITIALIZING NEXT SEASON'.center(80)}")
            print(f"{'='*80}")

        # Step 1: Increment season year (Phase 3: Use synchronizer)
        old_year = self.season_year
        new_year = self.year_synchronizer.increment_year(
            "_initialize_next_season called"
        )

        if self.verbose_logging:
            print(f"[NEW_SEASON] Season year: {old_year} → {self.season_year}")

        try:
            # Step 2: Generate preseason schedule
            from ui.domain_models.season_data_model import SeasonDataModel

            season_model = SeasonDataModel(
                db_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season=self.season_year,
            )

            # Generate preseason games (3 weeks, 48 total games)
            generator = RandomScheduleGenerator(
                event_db=self.event_db, dynasty_id=self.dynasty_id
            )

            preseason_games = generator.generate_preseason(season_year=self.season_year)

            if self.verbose_logging:
                print(
                    f"[NEW_SEASON] Generated {len(preseason_games)} preseason games (3 weeks)"
                )

            # Step 3: Generate regular season schedule (17 weeks, 272 games)
            # Dynasty starts day before first preseason game
            preseason_start = generator._calculate_preseason_start(self.season_year)
            dynasty_start = preseason_start - timedelta(days=1)

            success, error = season_model.generate_initial_schedule(dynasty_start)

            if not success:
                raise Exception(f"Failed to generate regular season schedule: {error}")

            if self.verbose_logging:
                print(f"[NEW_SEASON] Generated 272 regular season games (17 weeks)")

            # Step 4: Reset standings (for preseason)
            self._reset_all_standings(season_type="preseason")

            if self.verbose_logging:
                print(f"[NEW_SEASON] Reset all 32 team preseason standings to 0-0-0")

            # Step 5: Update dynasty state
            self.db.dynasty_update_state(
                current_date=str(self.calendar.get_current_date()),
                current_week=0,  # Preseason is week 0
                current_phase="preseason",
            )

            if self.verbose_logging:
                print(f"[NEW_SEASON] Updated dynasty_state to preseason")

            # Step 6: Transition phase to PRESEASON
            self.phase_state.phase = SeasonPhase.PRESEASON
            self.active_controller = self.season_controller

            if self.verbose_logging:
                print(f"[NEW_SEASON] Phase: OFFSEASON → PRESEASON")
                print(f"[NEW_SEASON] Season {self.season_year} ready!")
                print(f"{'='*80}\n")

            # Step 7: Season controller year automatically updated by synchronizer (Phase 3)
            # No manual propagation needed - SeasonYearSynchronizer handles all registered components

        except Exception as e:
            # Rollback season year on failure
            self._set_season_year(
                old_year, f"Rollback after _initialize_next_season failure: {e}"
            )

            # Log error
            self.logger.error(f"Failed to initialize season {old_year + 1}: {e}")

            if self.verbose_logging:
                print(f"❌ Season initialization failed: {e}")
                import traceback

                traceback.print_exc()

            # Re-raise with context
            raise Exception(f"Season initialization failed: {e}") from e

    # ========== Phase Transition Helper Methods ==========
    # These methods are used by PlayoffsToOffseasonHandler and OffseasonToPreseasonHandler

    def _get_super_bowl_winner_for_handler(self) -> int:
        """
        Get Super Bowl winner team ID for PlayoffsToOffseasonHandler.

        Returns:
            Team ID of Super Bowl champion
        """
        return self.playoff_controller.get_super_bowl_winner()

    def _schedule_offseason_events_for_handler(self, season_year: int) -> None:
        """
        Schedule offseason events for PlayoffsToOffseasonHandler.

        Args:
            season_year: Current season year that just ended
        """
        scheduler = OffseasonEventScheduler()

        # Get Super Bowl date from playoff controller
        super_bowl_date = self.playoff_controller.get_super_bowl_date()

        # Schedule all offseason events
        scheduler.schedule_offseason_events(
            super_bowl_date=super_bowl_date,
            season_year=season_year,
            dynasty_id=self.dynasty_id,
            event_db=self.event_db,
        )

    def _generate_season_summary_for_handler(self) -> Dict[str, Any]:
        """
        Generate season summary for PlayoffsToOffseasonHandler.

        Returns:
            Dictionary with season summary data
        """
        return {
            "champion_team_id": self.playoff_controller.get_super_bowl_winner(),
            "season_year": self.season_year,
            "dynasty_id": self.dynasty_id,
        }

    def _get_regular_season_standings_for_handler(self) -> List[Any]:
        """
        Get regular season standings for draft order calculation.

        Returns:
            List of team standings dicts with team_id, wins, losses, ties, win_percentage
        """
        standings_dict = self.db.standings_get(
            season=self.season_year,
            season_type="regular_season"
        )

        # Extract overall standings list and convert to expected format
        overall_standings = standings_dict.get('overall', [])

        result = []
        for team_data in overall_standings:
            standing = team_data['standing']
            result.append({
                'team_id': team_data['team_id'],
                'wins': standing.wins,
                'losses': standing.losses,
                'ties': standing.ties,
                'win_percentage': standing.win_percentage
            })

        return result

    def _get_playoff_bracket_for_handler(self) -> Dict[str, Any]:
        """
        Get playoff bracket for draft order calculation.

        Returns:
            Playoff bracket dictionary with all rounds and results
        """
        return self.playoff_controller.get_current_bracket()

    def _schedule_event_for_handler(self, event: Any) -> None:
        """
        Schedule an event (for draft order milestone).

        Args:
            event: Event object to schedule
        """
        self.event_db.insert_event(event)

    def _generate_preseason_schedule_for_handler(
        self, season_year: int
    ) -> List[Dict[str, Any]]:
        """
        Generate preseason schedule for phase transition handler.

        Idempotent: Safe to call multiple times - returns existing games if found.
        Mimics regular season generation pattern.

        Args:
            season_year: The season year for schedule generation

        Returns:
            List of 48 preseason game event dictionaries
        """
        # Phase 5: Auto-recovery guard before schedule generation
        self._auto_recover_year_from_database("Before preseason schedule generation")

        # Check if preseason schedule already exists (prevent duplicates)
        all_events = self.db.events_get_by_type(event_type="GAME")

        preseason_games = [
            e
            for e in all_events
            if e.get("game_id", "").startswith(GameIDPrefixes.PRESEASON)
            and e.get("data", {}).get("parameters", {}).get("season") == season_year
        ]

        if len(preseason_games) == 48:
            if self.verbose_logging:
                print(
                    f"[SCHEDULE_IDEMPOTENCY] Preseason schedule already exists for {season_year}"
                )
                print(f"  Found {len(preseason_games)} games - returning existing")
            return preseason_games

        # Generate schedule if it doesn't exist
        print(f"\n[PRESEASON_DEBUG Point 5.1] Creating RandomScheduleGenerator...")
        print(f"  Season year: {season_year}")
        print(f"  Dynasty ID: {self.dynasty_id}")
        print(f"  Event DB: {self.event_db}")

        # Get preseason start date from milestone (single source of truth)
        preseason_start_date = self._get_preseason_start_from_milestone()

        # Convert Date to datetime for schedule generator
        from datetime import datetime

        preseason_start_datetime = datetime(
            preseason_start_date.year,
            preseason_start_date.month,
            preseason_start_date.day,
            19,
            0,  # 7:00 PM default start time
        )

        print(
            f"[PRESEASON_DEBUG Point 5.1] Using milestone date: {preseason_start_datetime.strftime('%Y-%m-%d')}"
        )

        generator = RandomScheduleGenerator(
            event_db=self.event_db, dynasty_id=self.dynasty_id
        )

        print(
            f"[PRESEASON_DEBUG Point 5.1] Calling generate_preseason() with start_date..."
        )
        games = generator.generate_preseason(
            season_year=season_year, start_date=preseason_start_datetime
        )

        print(f"[PRESEASON_DEBUG Point 5.1] ✅ generate_preseason() completed")
        print(f"  Games returned: {len(games)}")

        return games

    def _generate_regular_season_schedule_for_handler(
        self, season_year: int, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Generate regular season schedule for phase transition handler.

        Idempotent: Safe to call multiple times - returns existing games if found.
        Mimics SeasonDataModel.generate_initial_schedule() pattern.

        Args:
            season_year: The season year for schedule generation
            start_date: The first regular season game date (Thursday after Labor Day)

        Returns:
            List of 272 regular season game event dictionaries
        """
        # Phase 5: Auto-recovery guard before schedule generation
        self._auto_recover_year_from_database(
            "Before regular season schedule generation"
        )

        # Check if regular season schedule already exists (prevent duplicates)
        all_events = self.db.events_get_by_type(event_type="GAME")

        regular_season_games = [
            e
            for e in all_events
            if not e.get("game_id", "").startswith(GameIDPrefixes.PLAYOFF)
            and not e.get("game_id", "").startswith(GameIDPrefixes.PRESEASON)
            and e.get("data", {}).get("parameters", {}).get("season") == season_year
        ]

        if len(regular_season_games) == SeasonConstants.REGULAR_SEASON_GAME_COUNT:
            if self.verbose_logging:
                print(
                    f"[SCHEDULE_IDEMPOTENCY] Regular season schedule already exists for {season_year}"
                )
                print(f"  Found {len(regular_season_games)} games - returning existing")
            return regular_season_games

        # Generate schedule if it doesn't exist
        from ui.domain_models.season_data_model import SeasonDataModel

        season_model = SeasonDataModel(
            db_path=self.database_path, dynasty_id=self.dynasty_id, season=season_year
        )

        # Use existing schedule generation
        dynasty_start = start_date - timedelta(days=1)
        success, error = season_model.generate_initial_schedule(dynasty_start)

        if not success:
            raise RuntimeError(f"Failed to generate regular season schedule: {error}")

        # Retrieve the generated games from event database
        all_events = self.db.events_get_by_type(event_type="GAME")

        regular_season_games = [
            e
            for e in all_events
            if not e.get("game_id", "").startswith(GameIDPrefixes.PLAYOFF)
            and not e.get("game_id", "").startswith(GameIDPrefixes.PRESEASON)
            and e.get("data", {}).get("parameters", {}).get("season") == season_year
        ]

        return regular_season_games

    def _reset_standings_for_handler(
        self, season_year: int, season_type: str = PhaseNames.DB_REGULAR_SEASON
    ) -> None:
        """
        Reset all team standings for phase transition handler.

        Args:
            season_year: The season year for standings reset
            season_type: Type of season to reset ("preseason", "regular_season", "playoffs")
        """
        # Temporarily update season_year for reset operation
        old_season_year = self.season_year
        self._set_season_year(
            season_year,
            f"Temporary assignment for standings reset (year={season_year})",
        )

        try:
            self._reset_all_standings(season_type=season_type)
        finally:
            # Restore original season_year
            self._set_season_year(
                old_season_year,
                f"Restore after standings reset (back to {old_season_year})",
            )

    def _get_preseason_start_from_milestone(self) -> Date:
        """
        Get preseason start date from database milestone (single source of truth).

        Uses EventDatabaseAPI to query for PRESEASON_START milestone with tolerant
        season_year matching. This handles phase transition edge cases where the
        controller's season_year may increment before all milestones are consumed.

        Returns:
            Date representing preseason start date from database milestone

        Raises:
            RuntimeError: If milestone not found in database (should never happen)
        """
        # Use EventDatabaseAPI instead of direct SQL (proper separation of concerns)
        milestone_date = self.db.events_get_milestone_by_type(
            milestone_type="PRESEASON_START",
            season_year=self.season_year,
            year_tolerance=1,  # Accept ±1 year to handle phase transitions
        )

        if not milestone_date:
            raise RuntimeError(
                f"PRESEASON_START milestone not found for season {self.season_year}. "
                f"Milestone must exist in database - check offseason event scheduling. "
                f"Dynasty: {self.dynasty_id}"
            )

        return milestone_date

    def _get_preseason_start_date(self) -> Date:
        """
        Get preseason start date with fallback calculation.

        Tries to get date from database PRESEASON_START milestone first.
        Falls back to calculation if milestone not found.

        Returns:
            Date representing when preseason begins

        Raises:
            RuntimeError: Only if both database query and fallback calculation fail
        """
        try:
            # Try database milestone first (preferred source)
            return self._get_preseason_start_from_milestone()
        except RuntimeError:
            # Fallback to calculation if milestone missing
            self.logger.warning(
                f"PRESEASON_START milestone not found in database for season {self.season_year}. "
                f"Using fallback calculation."
            )
            # Import here to avoid circular dependency
            from calendar.phase_boundary_detector import PhaseBoundaryDetector
            detector = PhaseBoundaryDetector(database_path=self.db_path)
            return detector._calculate_preseason_start(self.season_year)

    def _update_database_phase_for_handler(self, phase: str, season_year: int) -> None:
        """
        Update database phase for phase transition handler.

        Args:
            phase: The new phase name (e.g., "PRESEASON", "OFFSEASON")
            season_year: The season year
        """
        # Phase 5: Auto-recovery guard before database phase update
        self._auto_recover_year_from_database("Before database phase update")

        self.db.dynasty_update_state(
            season=season_year,  # Required first positional argument
            current_date=str(self.calendar.get_current_date()),
            current_phase=phase.lower(),
            current_week=0 if phase == "PRESEASON" else None,
        )

    def _get_standings_for_handler(self, dynasty_id: str, season_year: int) -> Dict[str, Any]:
        """
        Get final regular season standings from database.

        Required by RegularToPlayoffsHandler to calculate playoff seeding.

        Args:
            dynasty_id: Dynasty identifier
            season_year: Season year to query standings for

        Returns:
            Dict mapping team_id to standing dict with wins/losses/ties

        Raises:
            RuntimeError: If no standings found for season
        """
        standings_data = self.db.standings_get(
            season=season_year,
            season_type=PhaseNames.DB_REGULAR_SEASON
        )

        if not standings_data or not standings_data.get("divisions"):
            raise RuntimeError(
                f"No regular season standings found for dynasty '{dynasty_id}', "
                f"season {season_year}"
            )

        # Convert to format expected by PlayoffSeeder
        standings_dict = {}
        for division_name, teams in standings_data.get("divisions", {}).items():
            for team_data in teams:
                team_id = team_data["team_id"]
                standings_dict[team_id] = team_data["standing"]

        return standings_dict

    def _seed_playoffs_for_handler(self, standings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seed playoff bracket from regular season standings.

        Required by RegularToPlayoffsHandler to create playoff bracket.

        Args:
            standings: Dict mapping team_id to standing dict

        Returns:
            PlayoffSeeding object with AFC/NFC seeds
        """
        seeder = PlayoffSeeder()
        playoff_seeding = seeder.calculate_seeding(
            standings=standings,
            season=self.season_year,
            week=SeasonConstants.REGULAR_SEASON_WEEKS,
        )

        if self.verbose_logging:
            print(f"\n📋 Playoff Seeding Calculated")
            print(f"\nAFC Seeds:")
            for seed in playoff_seeding.afc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")
            print(f"\nNFC Seeds:")
            for seed in playoff_seeding.nfc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

        return playoff_seeding

    def _create_playoff_controller_for_handler(self, seeding: Dict[str, Any]) -> PlayoffController:
        """
        Create playoff controller with seeded bracket.

        Required by RegularToPlayoffsHandler to initialize playoff phase.

        Args:
            seeding: PlayoffSeeding object from _seed_playoffs_for_handler

        Returns:
            PlayoffController instance ready for playoff simulation
        """
        # Using PhaseBoundaryDetector for centralized boundary logic
        wild_card_date = self.boundary_detector.get_playoff_start_date()

        if self.verbose_logging:
            print(f"\n📅 Wild Card Weekend: {wild_card_date}")

        playoff_controller = PlayoffController(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id,
            season_year=self.season_year,
            wild_card_start_date=wild_card_date,
            initial_seeding=seeding,
            enable_persistence=self.enable_persistence,
            verbose_logging=self.verbose_logging,
            phase_state=self.phase_state,
            fast_mode=self.fast_mode
        )

        # Share calendar and set references
        playoff_controller.calendar = self.calendar
        playoff_controller.simulation_executor.calendar = self.calendar
        playoff_controller.original_seeding = seeding

        self.playoff_controller = playoff_controller
        self.active_controller = playoff_controller

        if self.verbose_logging:
            print(f"\n✅ Playoff controller created successfully")

        return playoff_controller

    def _increment_contracts_for_handler(self, season_year: int) -> Dict[str, Any]:
        """
        Increment contract years and handle expirations for OffseasonToPreseasonHandler.

        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.
        Delegates to ContractTransitionService for contract lifecycle management.

        Args:
            season_year: New season year after increment (e.g., 2025)

        Returns:
            Dict with contract transition results (total, active, expired counts)
        """
        contract_service = self._get_contract_transition_service()
        return contract_service.increment_all_contracts(season_year)

    def _prepare_draft_for_handler(self, season_year: int) -> Dict[str, Any]:
        """
        Generate draft class for upcoming season for OffseasonToPreseasonHandler.

        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.
        Delegates to DraftPreparationService for draft class generation (synchronous, ~2-5s).

        Args:
            season_year: Season year for draft class (e.g., 2025)

        Returns:
            Dict with draft preparation results (draft_class_id, total_players, timing)
        """
        draft_service = self._get_draft_preparation_service()
        return draft_service.prepare_draft_class(season_year, size=300)

    def _execute_year_transition_for_handler(
        self, old_year: int, new_year: int
    ) -> Dict[str, Any]:
        """
        Execute complete year transition orchestration for OffseasonToPreseasonHandler.

        Part of Milestone 1: Complete Multi-Year Season Cycle implementation.
        Orchestrates:
        1. Season year increment (via SeasonYearSynchronizer)
        2. Contract transitions (increment years, handle expirations)
        3. Draft class generation (300 prospects)

        Args:
            old_year: Previous season year (e.g., 2024)
            new_year: New season year (e.g., 2025)

        Returns:
            Dict with complete transition results (all 3 steps)
        """
        season_transition_service = self._get_season_transition_service()
        return season_transition_service.execute_year_transition(
            old_year=old_year,
            new_year=new_year,
            synchronizer=self.year_synchronizer
        )

    # ========== AI Transaction Helper Methods (Phase 1.7) ==========

    def _calculate_current_week(self) -> int:
        """
        Calculate current NFL week number.

        Uses the phase handler's tracked week number which is
        automatically maintained during week advancement.

        Returns:
            int: Current week number (1-18 for regular season, 1-4 for preseason, 0 for other phases)
        """
        if self.phase_state.phase == SeasonPhase.REGULAR_SEASON:
            # Get week from regular season handler
            handler = self.phase_handlers.get(SeasonPhase.REGULAR_SEASON)
            return handler.current_week if handler and hasattr(handler, "current_week") else 0
        elif self.phase_state.phase == SeasonPhase.PRESEASON:
            # Get week from preseason handler (weeks 1-4)
            handler = self.phase_handlers.get(SeasonPhase.PRESEASON)
            return handler.current_week if handler and hasattr(handler, "current_week") else 0
        else:
            # Playoffs, offseason, etc.
            return 0

    # ========== Existing Helper Methods ==========

    def _reset_all_standings(self, season_type: str = PhaseNames.DB_REGULAR_SEASON):
        """
        Reset all 32 teams to 0-0-0 records for new season.

        Us1es DatabaseAPI to reset standings table with fresh records for new season_year.

        Args:
            season_type: Type of season to reset ("preseason", "regular_season", "playoffs")
        """
        try:
            self.db.standings_reset(
                season=self.season_year, season_type=season_type
            )

            if self.verbose_logging:
                print(
                    f"[STANDINGS_RESET] All 32 teams reset to 0-0-0 for season {self.season_year} ({season_type})"
                )

        except Exception as e:
            raise Exception(f"Failed to reset standings: {e}") from e

    def _create_failure_result(self, message: str, start_date: Date) -> Dict[str, Any]:
        """
        Create standardized failure response for simulation errors.

        Args:
            message: Error message describing why simulation failed
            start_date: Date when simulation was attempted

        Returns:
            Failure dict with standard structure
        """
        return {
            "success": False,
            "message": message,
            "start_date": str(start_date),
            "end_date": str(start_date),
            "weeks_simulated": 0,
            "total_games": 0,
            "starting_phase": self.phase_state.phase.value,
            "ending_phase": self.phase_state.phase.value,
            "phase_transition": False,
        }

    # ==================== Dunder Methods ====================

    def __str__(self) -> str:
        """String representation"""
        return (
            f"SeasonCycleController(season={self.season_year}, "
            f"phase={self.phase_state.phase.value}, "
            f"games={self.total_games_played})"
        )

    def __repr__(self) -> str:
        """Detailed representation"""
        return (
            f"SeasonCycleController(database_path='{self.database_path}', "
            f"season_year={self.season_year}, "
            f"dynasty_id='{self.dynasty_id}')"
        )

    def close(self):
        """Close database connections"""
        if hasattr(self, "db"):
            self.db.close()
