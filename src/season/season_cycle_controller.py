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
from datetime import timedelta, datetime
from typing import Dict, List, Any, Optional

# Use try/except to handle both production and test imports
# Try src.calendar first to avoid conflict with Python's builtin calendar module
try:
    from src.calendar.date_models import Date
    from src.calendar.season_phase_tracker import SeasonPhase
    from src.calendar.phase_state import PhaseState
except (ModuleNotFoundError, ImportError):
    from src.calendar.date_models import Date
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
            phase_completion_checker: Optional PhaseCompletionChecker for testing
            phase_transition_manager: Optional PhaseTransitionManager for testing
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging
        self.fast_mode = fast_mode

        self.logger = logging.getLogger(self.__class__.__name__)

        print(
            f"[DYNASTY_TRACE] SeasonCycleController.__init__(): dynasty_id={dynasty_id}"
        )

        # ============ PHASE 2: DATABASE-FIRST LOADING ============
        # Initialize UnifiedDatabaseAPI FIRST (needed for loading)
        self.db = UnifiedDatabaseAPI(database_path, dynasty_id)

        # Initialize EventDatabaseAPI (needed for game validation in handlers)
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
                phase_map = {
                    PhaseNames.DB_REGULAR_SEASON: SeasonPhase.REGULAR_SEASON,
                    PhaseNames.DB_PRESEASON: SeasonPhase.PRESEASON,
                    PhaseNames.DB_PLAYOFFS: SeasonPhase.PLAYOFFS,
                    PhaseNames.DB_OFFSEASON: SeasonPhase.OFFSEASON,
                }
                initial_phase = phase_map.get(db_phase, SeasonPhase.REGULAR_SEASON)

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

        # Create shared phase state with correct starting phase (single source of truth)
        self.phase_state = PhaseState(initial_phase)

        # Import SeasonController here to avoid circular imports
        from demo.interactive_season_sim.season_controller import SeasonController

        # Initialize season controller (always starts in regular season)
        self.season_controller = SeasonController(
            database_path=database_path,
            start_date=start_date,
            season_year=self.season_year,  # Phase 2: Use database-loaded value
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging,
            phase_state=self.phase_state,
        )

        # Access the shared calendar from season controller
        self.calendar = self.season_controller.calendar

        # Playoff controller created when needed
        self.playoff_controller: Optional[PlayoffController] = None

        # Season summary (generated in offseason)
        self.season_summary: Optional[Dict[str, Any]] = None

        # Statistics
        self.total_games_played = 0
        self.total_days_simulated = 0

        # Calculate last scheduled regular season game date for flexible end-of-season detection
        self.last_regular_season_game_date = self._get_last_regular_season_game_date()

        # ============ PHASE TRANSITION SYSTEM ============
        # Initialize phase completion checker (dependency injection support)
        if phase_completion_checker is None:
            # Create default checker with injected dependencies
            self.phase_completion_checker = PhaseCompletionChecker(
                get_games_played=lambda: self._get_phase_specific_games_played(),  # ✅ Phase-specific, not cumulative!
                get_current_date=lambda: self.calendar.get_current_date(),
                get_last_regular_season_game_date=lambda: self.last_regular_season_game_date,
                get_last_preseason_game_date=lambda: self._get_last_preseason_game_date(),
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
            )

            # Create OFFSEASON → PRESEASON handler
            offseason_to_preseason_handler = OffseasonToPreseasonHandler(
                generate_preseason=self._generate_preseason_schedule_for_handler,
                generate_regular_season=self._generate_regular_season_schedule_for_handler,
                reset_standings=self._reset_standings_for_handler,
                calculate_preseason_start=self._calculate_preseason_start_for_handler,
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

        # Register season_controller to be updated when year changes
        self.year_synchronizer.register_callback(
            "season_controller",
            lambda year: setattr(self.season_controller, "season_year", year),
        )

        # Register simulation_executor (inside season_controller) to be updated
        # CRITICAL: This fixes preseason game simulation in the following season
        # Without this, executor has old year and can't find games with new year prefix
        self.year_synchronizer.register_callback(
            "simulation_executor",
            lambda year: setattr(
                self.season_controller.simulation_executor, "season_year", year
            ),
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
            # Regular season - use season controller
            self.active_controller = self.season_controller

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

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 day.

        Returns:
            Dictionary with results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "current_phase": str,
                "phase_transition": Optional[Dict],
                "success": bool
            }
        """
        # Phase 5: Auto-recovery guard before daily simulation
        self._auto_recover_year_from_database("Before daily simulation")

        # Handle offseason case
        if self.phase_state.phase.value == "offseason":
            # Execute any scheduled offseason events for this day
            try:
                current_date = self.calendar.get_current_date()

                if self.verbose_logging:
                    print(f"\n[OFFSEASON_DAY] Advancing offseason day: {current_date}")

                # Import SimulationExecutor to trigger events
                try:
                    from src.calendar.simulation_executor import SimulationExecutor
                except (ModuleNotFoundError, ImportError):
                    from src.calendar.simulation_executor import SimulationExecutor

                executor = SimulationExecutor(
                    calendar=self.calendar,
                    event_db=self.event_db,
                    database_path=self.database_path,
                    dynasty_id=self.dynasty_id,
                    enable_persistence=self.enable_persistence,
                    season_year=self.season_year,
                    phase_state=self.phase_state,
                )

                # Simulate events for current day
                event_results = executor.simulate_day(current_date)

                # Advance calendar
                self.calendar.advance(1)
                self.total_days_simulated += 1

                if self.verbose_logging:
                    print(
                        f"[OFFSEASON_DAY] Calendar advanced successfully to: {self.calendar.get_current_date()}"
                    )

                # Check for phase transitions (OFFSEASON → PRESEASON)
                phase_transition = self._check_phase_transition()

                return {
                    "date": str(current_date),
                    "games_played": 0,
                    "events_triggered": event_results.get("events_executed", []),
                    "results": [],
                    "current_phase": self.phase_state.phase.value,
                    "phase_transition": phase_transition,
                    "success": True,
                    "message": f"Offseason day complete. {len(event_results.get('events_executed', []))} events triggered.",
                }

            except Exception as e:
                self.logger.error(f"Error during offseason day advancement: {e}")
                # Fallback to basic advancement
                self.calendar.advance(1)
                self.total_days_simulated += 1

                return {
                    "date": str(self.calendar.get_current_date()),
                    "games_played": 0,
                    "results": [],
                    "current_phase": "offseason",
                    "phase_transition": None,
                    "success": True,
                    "message": "Season complete. No more games to simulate.",
                }

        # Delegate to active controller
        result = self.active_controller.advance_day()

        # Update statistics
        self.total_games_played += result.get("games_played", 0)
        self.total_days_simulated += 1

        # Phase 1.7: AI Transaction Evaluation (preseason, regular season, offseason)
        if self.phase_state.phase in [
            SeasonPhase.PRESEASON,
            SeasonPhase.REGULAR_SEASON,
            SeasonPhase.OFFSEASON,
        ]:
            # Use TransactionService for evaluation (Phase 3: Service Extraction)
            service = self._get_transaction_service()
            current_week = self._calculate_current_week()
            executed_trades = service.evaluate_daily_for_all_teams(
                current_phase=self.phase_state.phase.value,
                current_week=current_week,
                verbose_logging=self.verbose_logging,
            )
            result["transactions_executed"] = executed_trades
            result["num_trades"] = len(executed_trades)

        # Check for phase transitions
        phase_transition = self._check_phase_transition()
        if phase_transition:
            result["phase_transition"] = phase_transition

        result["current_phase"] = self.phase_state.phase.value

        return result

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 7 days.

        Returns:
            Dictionary with weekly summary
        """
        # Phase 5: Auto-recovery guard before weekly simulation
        self._auto_recover_year_from_database("Before weekly simulation")

        if self.phase_state.phase.value == "offseason":
            # Advance offseason by 7 days, collecting any triggered events
            events_triggered = []
            start_date = str(self.calendar.get_current_date())
            phase_transition = None  # Track if transition occurred during week

            for day_num in range(7):
                day_result = self.advance_day()
                if day_result.get("events_triggered"):
                    events_triggered.extend(day_result["events_triggered"])
                # Capture transition if it occurred during any day
                if day_result.get("phase_transition"):
                    phase_transition = day_result["phase_transition"]

            end_date = str(self.calendar.get_current_date())

            return {
                "success": True,
                "week_complete": True,
                "current_phase": self.phase_state.phase.value,
                "phase_transition": phase_transition,
                "date": end_date,
                "games_played": 0,
                "message": f"Offseason week advanced ({start_date} → {end_date}). {len(events_triggered)} events triggered.",
            }

        # Regular season, preseason, and playoffs: Loop 7 times calling advance_day()
        # This ensures AI transaction evaluation runs once per day (7 times per week)
        # matching the offseason pattern
        start_date = str(self.calendar.get_current_date())
        total_games = 0
        all_results = []
        all_transactions = []
        phase_transition = None  # Track if transition occurred during week

        if self.verbose_logging:
            print(f"\n[DIAG advance_week] START")
            print(f"[DIAG advance_week] Current phase: {self.phase_state.phase.value}")

        for day_num in range(7):
            if self.verbose_logging:
                print(f"[DIAG advance_week] Day {day_num + 1}/7")
            day_result = self.advance_day()

            # Accumulate game results
            games_played = day_result.get("games_played", 0)
            total_games += games_played

            if day_result.get("results"):
                all_results.extend(day_result["results"])

            # Accumulate AI transactions (regular season only)
            if day_result.get("transactions_executed"):
                all_transactions.extend(day_result["transactions_executed"])

            # Capture transition if it occurred during any day
            if day_result.get("phase_transition"):
                phase_transition = day_result["phase_transition"]
                if self.verbose_logging:
                    print(f"[DIAG advance_week] *** PHASE TRANSITION DETECTED on day {day_num + 1} ***")
                    print(f"[DIAG advance_week] Transition data: {phase_transition}")
                    print(f"[DIAG advance_week] BREAKING day loop")
                # Stop advancing days after a phase transition occurs
                # This prevents simulating into the next phase
                break

        end_date = str(self.calendar.get_current_date())

        if self.verbose_logging:
            print(f"\n[DIAG advance_week] END")
            print(f"[DIAG advance_week] Week complete ({start_date} → {end_date})")
            print(f"[DIAG advance_week] Total games: {total_games}, AI trades: {len(all_transactions)}")
            print(f"[DIAG advance_week] Current phase: {self.phase_state.phase.value}")
            print(f"[DIAG advance_week] phase_transition variable: {phase_transition}")
            print(f"[DIAG advance_week] Will return phase_transition={phase_transition}")

        return {
            "success": True,
            "week_complete": True,
            "current_phase": self.phase_state.phase.value,
            "phase_transition": phase_transition,
            "date": end_date,
            "games_played": total_games,
            "total_games_played": total_games,  # Match SeasonController return format
            "results": all_results,
            "transactions_executed": all_transactions,
            "num_trades": len(all_transactions),
            "message": f"Week complete ({start_date} → {end_date}). {total_games} games, {len(all_transactions)} trades.",
        }

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
        Simulate until current phase ends (stops BEFORE next phase begins).

        Uses look-ahead to detect upcoming phase transition and stops on the day
        BEFORE the first game of the next phase. This gives users control at phase
        boundaries without overshooting into the next phase.

        Args:
            progress_callback: Optional callback(week_num, games_played) for UI progress updates

        Returns:
            Summary dict with weeks_simulated, total_games, phase_transition info:
            {
                'start_date': str,
                'end_date': str,
                'weeks_simulated': int,
                'total_games': int,
                'starting_phase': str,
                'ending_phase': str,
                'phase_transition': bool,
                'success': bool
            }
        """
        # Handle offseason separately (existing code - keep this)
        if self.phase_state.phase.value == "offseason":
            return self.simulate_to_next_offseason_milestone(progress_callback)

        # Setup (existing code - keep this)
        starting_phase = self.phase_state.phase
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played
        weeks_simulated = 0

        if self.verbose_logging:
            title = f"SIMULATING TO END OF {starting_phase.value.upper()}"
            print(f"\n{'='*80}")
            print(f"{title.center(80)}")
            print(f"{'='*80}")

        # NEW: Determine next phase and query its first game date
        next_phase_map = {
            SeasonPhase.PRESEASON: PhaseNames.DB_REGULAR_SEASON,
            SeasonPhase.REGULAR_SEASON: PhaseNames.DB_PLAYOFFS,
            SeasonPhase.PLAYOFFS: PhaseNames.DB_OFFSEASON,
            SeasonPhase.OFFSEASON: PhaseNames.DB_PRESEASON,  # Complete the cycle for multi-season support
        }

        next_phase_name = next_phase_map.get(starting_phase)
        target_stop_date = None

        if next_phase_name and next_phase_name != "offseason":
            # Query first game of next phase
            first_game_date = self.db.events_get_first_game_date_of_phase(
                phase_name=next_phase_name,
                current_date=str(self.calendar.get_current_date()),
            )

            if first_game_date:
                # Calculate day before first game (our stop point)
                first_game_dt = datetime.strptime(first_game_date, "%Y-%m-%d")
                stop_date_dt = first_game_dt - timedelta(days=1)
                target_stop_date = stop_date_dt.strftime("%Y-%m-%d")

                if self.verbose_logging:
                    print(
                        f"[LOOK_AHEAD] First {next_phase_name} game: {first_game_date}"
                    )
                    print(f"[LOOK_AHEAD] Will stop on: {target_stop_date} (day before)")

        # NEW: Simulation loop with look-ahead stop condition
        consecutive_empty_weeks = 0
        max_empty_weeks = 3
        loop_iteration = 0  # For diagnostic tracking

        if self.verbose_logging:
            print(f"\n[DIAG simulate_to_phase_end] STARTING LOOP")
            print(f"[DIAG simulate_to_phase_end] Starting phase: {starting_phase.value}")
            print(f"[DIAG simulate_to_phase_end] Target stop date: {target_stop_date}")

        while True:
            loop_iteration += 1
            current_date_str = str(self.calendar.get_current_date())

            if self.verbose_logging:
                print(f"\n[DIAG simulate_to_phase_end] === ITERATION {loop_iteration} ===")
                print(f"[DIAG simulate_to_phase_end] Current date: {current_date_str}")
                print(f"[DIAG simulate_to_phase_end] Current phase: {self.phase_state.phase.value}")

            # STOP CONDITION 1: Check if NEXT week would exceed target (prevent overshoot)
            if target_stop_date:
                current_py_date = self.calendar.get_current_date().to_python_date()
                target_py_date = datetime.strptime(target_stop_date, "%Y-%m-%d").date()

                # Estimate where next week would end (current + 7 days)
                next_week_end_estimate = current_py_date + timedelta(days=7)

                # Stop if current >= target OR next week would exceed target
                if current_py_date >= target_py_date:
                    if self.verbose_logging:
                        print(
                            f"[STOP] Reached target date: {current_date_str} >= {target_stop_date}"
                        )
                    break
                elif next_week_end_estimate >= target_py_date:
                    if self.verbose_logging:
                        print(
                            f"[STOP] Preventing overshoot: current={current_date_str}, target={target_stop_date}"
                        )
                        print(
                            f"[STOP] Next week would end around {next_week_end_estimate}, which exceeds target"
                        )
                    break

            # STOP CONDITION 2: Phase already changed (safety fallback)
            if self.phase_state.phase != starting_phase:
                if self.verbose_logging:
                    print(
                        f"[STOP] Phase changed: {starting_phase.value} -> {self.phase_state.phase.value}"
                    )
                break

            # STOP CONDITION 3: Offseason reached (safety)
            if self.phase_state.phase.value == "offseason":
                break

            # Advance one week (only if we didn't break above)
            games_before = self.total_games_played
            result = self.advance_week()
            games_after = self.total_games_played
            weeks_simulated += 1

            if self.verbose_logging:
                print(f"[DIAG simulate_to_phase_end] advance_week() returned")
                print(f"[DIAG simulate_to_phase_end] Result keys: {list(result.keys())}")
                print(f"[DIAG simulate_to_phase_end] phase_transition in result: {'phase_transition' in result}")
                if 'phase_transition' in result:
                    print(f"[DIAG simulate_to_phase_end] phase_transition value: {result.get('phase_transition')}")
                print(f"[DIAG simulate_to_phase_end] Phase after advance_week: {self.phase_state.phase.value}")
                print(f"[DIAG simulate_to_phase_end] Games played this week: {games_after - games_before}")

            # PRIMARY CHECK: Did advance_week() detect a phase transition?
            # This catches transitions immediately when advance_week() breaks its day loop
            if self.verbose_logging:
                print(f"[DIAG simulate_to_phase_end] PRIMARY CHECK - result.get('phase_transition'): {result.get('phase_transition')}")

            if result.get("phase_transition"):
                if self.verbose_logging:
                    print(f"[STOP] PRIMARY CHECK TRIGGERED!")
                    print(f"[STOP] Phase transition detected in advance_week() result")
                    print(f"[STOP] Transition: {result['phase_transition']}")
                break

            # FALLBACK CHECK: Did the phase_state change during the week?
            # This is a safety check in case phase transition occurred mid-week
            if self.verbose_logging:
                print(f"[DIAG simulate_to_phase_end] FALLBACK CHECK - phase_state.phase: {self.phase_state.phase.value}, starting_phase: {starting_phase.value}")
                print(f"[DIAG simulate_to_phase_end] FALLBACK CHECK - phases equal: {self.phase_state.phase == starting_phase}")

            if self.phase_state.phase != starting_phase:
                if self.verbose_logging:
                    print(f"[STOP] FALLBACK CHECK TRIGGERED!")
                    print(f"[STOP] Phase changed during week: {starting_phase.value} -> {self.phase_state.phase.value}")
                break

            # Track consecutive empty weeks (safety valve)
            if games_after == games_before:
                consecutive_empty_weeks += 1
                if consecutive_empty_weeks >= max_empty_weeks:
                    if self.verbose_logging:
                        print(
                            f"[WARNING] Stopping: {consecutive_empty_weeks} consecutive weeks with no games"
                        )
                    break
            else:
                consecutive_empty_weeks = 0

            # Progress callback for UI updates
            if progress_callback:
                games_this_iteration = self.total_games_played - initial_games
                progress_callback(weeks_simulated, games_this_iteration)

            # Diagnostic: If we reach here, no break was triggered
            if self.verbose_logging:
                print(f"[DIAG simulate_to_phase_end] No break triggered - CONTINUING TO NEXT ITERATION")
                print(f"[DIAG simulate_to_phase_end] Will loop again (iteration {loop_iteration + 1})\n")

        # Return summary with next_phase information for UI
        return {
            "start_date": str(start_date),
            "end_date": str(self.calendar.get_current_date()),
            "weeks_simulated": weeks_simulated,
            "total_games": self.total_games_played - initial_games,
            "starting_phase": starting_phase.value,
            "ending_phase": self.phase_state.phase.value,
            "next_phase": next_phase_name,  # Phase we're about to enter (for UI message)
            "phase_transition": self.phase_state.phase != starting_phase,
            "success": True,
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
                else:
                    # No transition occurred - truly an error state
                    current_date = self.calendar.get_current_date()
                    self.logger.warning(
                        f"No offseason milestone found and offseason not complete. "
                        f"Current date: {current_date}. This may indicate a database or calendar configuration issue."
                    )
                    error_msg = (
                        f"No offseason milestone found and offseason not complete.\n\n"
                        f"Current date: {current_date}\n"
                        f"This may indicate missing milestones in the database or a calendar configuration issue."
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

        # Detect if transition occurred during simulation
        transition_occurred = self.phase_state.phase.value != starting_phase

        if transition_occurred:
            self.logger.info(
                f"Phase transition occurred during simulation to {next_milestone['display_name']}"
            )

        # Add milestone-specific info to result
        result["milestone_reached"] = next_milestone["display_name"]
        result["milestone_type"] = next_milestone["event_type"]
        result["milestone_date"] = str(milestone_date)

        # Add keys UI expects
        result["starting_phase"] = starting_phase
        result["ending_phase"] = self.phase_state.phase.value
        result["weeks_simulated"] = result["days_simulated"] // 7
        result["total_games"] = result.get("games_played", 0)
        result["phase_transition"] = transition_occurred
        result["transition_occurred"] = transition_occurred

        return result

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

        Returns:
            Display name like "Franchise Tags", "Free Agency", "Draft", etc.
            Returns "Next Season" if no more milestones.
        """
        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            return "Next Phase"

        current_date = self.calendar.get_current_date()
        next_milestone = self.db.events_get_next_offseason_milestone(
            current_date=current_date, season_year=self.season_year
        )

        if not next_milestone:
            return "Next Season"

        return next_milestone["display_name"]

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

        return self.season_controller.get_current_standings()

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
            from offseason.draft_class_api import DraftClassDatabaseAPI

            # Create DraftManager for draft class generation
            draft_manager = DraftManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id
            )

            # Create DraftClassDatabaseAPI for validation
            draft_api = DraftClassDatabaseAPI(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id
            )

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
            print(
                f"[NEW_SEASON_FLOW] Preseason start: {self._calculate_preseason_start_for_handler(self.season_year + 1)}"
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

                # Update database phase (year already updated by synchronizer)
                if self.verbose_logging:
                    print(f"[PHASE_TRANSITION] Updating database phase: PRESEASON")

                self.db.dynasty_update_state(
                    season=self.season_year,  # Already updated by synchronizer
                    current_date=str(self.calendar.get_current_date()),
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
                    self.active_controller = self.season_controller

                    if self.verbose_logging:
                        print(
                            f"[PHASE_TRANSITION] Phase state updated: OFFSEASON → PRESEASON"
                        )
                        print(
                            f"[PHASE_TRANSITION] Active controller set: season_controller"
                        )

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

    def _get_last_regular_season_game_date(self) -> Date:
        """
        Query event database to find the date of the last scheduled regular season game.

        This provides flexible end-of-season detection that adapts to any schedule length
        (17 weeks, 18 weeks, etc.) without code changes.

        Filters:
        - Only this dynasty's games (dynasty_id)
        - Only regular season games (exclude playoffs/preseason)
        - Only reasonable weeks (weeks 1-18 to avoid corrupted data)

        Returns:
            Date of the last scheduled regular season game for this dynasty
        """
        try:
            # Use API to get ONLY this dynasty's GAME events (10-100x faster with database filtering)
            dynasty_game_events = self.season_controller.event_db.get_events_by_dynasty(
                dynasty_id=self.dynasty_id, event_type="GAME"
            )

            # Filter for regular season games WITH SEASON FILTERING
            regular_season_events = [
                e
                for e in dynasty_game_events
                # CRITICAL: Only look at this season's games (multi-season support)
                # Use the 'season' field from parameters, NOT timestamp.year
                # (NFL seasons span calendar years: Sept 2025 → Jan 2026 are both "2025 season")
                # This ensures Week 15-18 games (January 2026) are included for 2025 season
                if e.get("data", {}).get("parameters", {}).get("season")
                == self.season_year
                # Exclude playoff and preseason games
                and not e.get("game_id", "").startswith(GameIDPrefixes.PLAYOFF)
                and not e.get("game_id", "").startswith(GameIDPrefixes.PRESEASON)
                # CRITICAL: Only include weeks 1-18 (ignore corrupted future games)
                and 1 <= e.get("data", {}).get("parameters", {}).get("week", 0) <= 18
            ]

            if not regular_season_events:
                # No regular season games scheduled - return season end date as fallback
                self.logger.warning(
                    f"No regular season games found for dynasty {self.dynasty_id}"
                )
                return Date(self.season_year, 12, 31)  # Dec 31 fallback

            # Find the event with the maximum timestamp
            last_event = max(regular_season_events, key=lambda e: e["timestamp"])

            # Convert timestamp to Date
            last_datetime = last_event["timestamp"]
            last_date = Date(
                year=last_datetime.year,
                month=last_datetime.month,
                day=last_datetime.day,
            )

            if self.verbose_logging:
                game_id = last_event.get("game_id", "unknown")
                week = last_event.get("data", {}).get("parameters", {}).get("week", "?")
                self.logger.info(
                    f"Last regular season game scheduled for: {last_date} (Week {week}, game_id={game_id})"
                )

            return last_date

        except Exception as e:
            self.logger.error(f"Error calculating last regular season game date: {e}")
            # Fallback to Dec 31 if calculation fails
            return Date(self.season_year, 12, 31)

    def _get_last_preseason_game_date(self) -> Date:
        """
        Query event database to find the date of the last scheduled preseason game.

        This provides flexible end-of-preseason detection that adapts to any schedule length
        (3 weeks, 4 weeks, etc.) without code changes.

        Filters:
        - Only this dynasty's games (dynasty_id)
        - Only preseason games (game_id starts with 'preseason_' OR season_type='preseason')
        - Only reasonable weeks (weeks 1-4 to avoid corrupted data)

        Returns:
            Date of the last scheduled preseason game for this dynasty
        """
        try:
            if self.verbose_logging:
                print(f"\n[DIAG] _get_last_preseason_game_date()")
                print(f"  self.season_year: {self.season_year}")
                print(f"  PhaseNames.DB_PRESEASON: {PhaseNames.DB_PRESEASON}")
                print(f"  GameIDPrefixes.PRESEASON: {GameIDPrefixes.PRESEASON}")

            # Use API to get ONLY this dynasty's GAME events (10-100x faster with database filtering)
            dynasty_game_events = self.db.events_get_by_type(event_type="GAME")

            if self.verbose_logging:
                print(f"  Total GAME events: {len(dynasty_game_events)}")

            # Filter for preseason games WITH SEASON FILTERING
            preseason_events = [
                e
                for e in dynasty_game_events
                # CRITICAL: Only look at this season's games (multi-season support)
                # Use the 'season' field from parameters, NOT timestamp.year
                # (NFL seasons span calendar years: Sept 2025 → Jan 2026 are both "2025 season")
                if e.get("data", {}).get("parameters", {}).get("season")
                == self.season_year
                # Include preseason games (check both game_id and season_type)
                and (
                    e.get("game_id", "").startswith(GameIDPrefixes.PRESEASON)
                    or e.get("data", {}).get("parameters", {}).get("season_type")
                    == PhaseNames.DB_PRESEASON
                    or e.get("data", {}).get("parameters", {}).get("game_type")
                    == PhaseNames.DB_PRESEASON
                )
                # CRITICAL: Only include weeks 1-4 (ignore corrupted future games)
                and 1 <= e.get("data", {}).get("parameters", {}).get("week", 0) <= 4
            ]

            if self.verbose_logging:
                print(f"  Filtered preseason events: {len(preseason_events)}")
                if len(preseason_events) == 0 and dynasty_game_events:
                    print(f"  [WARNING] No preseason events found! Debugging...")
                    sample = dynasty_game_events[0]
                    print(f"    Sample game_id: {sample.get('game_id')}")
                    print(f"    Sample season: {sample.get('data', {}).get('parameters', {}).get('season')}")
                    print(f"    Sample season_type: {sample.get('data', {}).get('parameters', {}).get('season_type')}")
                    print(f"    Sample week: {sample.get('data', {}).get('parameters', {}).get('week')}")
                    print(f"    Does game_id start with '{GameIDPrefixes.PRESEASON}'? {sample.get('game_id', '').startswith(GameIDPrefixes.PRESEASON)}")

            if not preseason_events:
                # No preseason games scheduled - return early September as fallback
                self.logger.warning(
                    f"No preseason games found for dynasty {self.dynasty_id}"
                )
                return Date(
                    self.season_year, 9, 3
                )  # Sept 3 fallback (day before regular season typically starts)

            # Find the event with the maximum timestamp
            last_event = max(preseason_events, key=lambda e: e["timestamp"])

            # Convert timestamp to Date
            last_datetime = last_event["timestamp"]
            last_date = Date(
                year=last_datetime.year,
                month=last_datetime.month,
                day=last_datetime.day,
            )

            if self.verbose_logging:
                game_id = last_event.get("game_id", "unknown")
                week = last_event.get("data", {}).get("parameters", {}).get("week", "?")
                self.logger.info(
                    f"Last preseason game scheduled for: {last_date} (Week {week}, game_id={game_id})"
                )

            return last_date

        except Exception as e:
            self.logger.error(f"Error calculating last preseason game date: {e}")
            # Fallback to Sept 3 if calculation fails
            return Date(self.season_year, 9, 3)

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
            wild_card_date = self._calculate_wild_card_date()

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

            # The season controller is already the active controller
            # (we don't need to switch controllers like we do for playoffs)
            self.active_controller = self.season_controller

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

            # 6. Share calendar for date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # 7. Set as active controller
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ PlayoffController restored successfully")
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

    def _calculate_wild_card_date(self) -> Date:
        """
        Calculate Wild Card weekend start date.

        NFL Scheduling:
        - Week 18 typically ends Sunday, January 6-7
        - Wild Card starts 2 weeks later (Saturday, January 18-19)

        Returns:
            Wild Card Saturday date
        """
        # Get date of last regular season game (Week 18 Sunday)
        # IMPORTANT: Use actual last game date, not current calendar date
        # This ensures playoffs always start 2 weeks after last game,
        # regardless of when phase transition is detected
        final_reg_season_date = self.last_regular_season_game_date

        # Add SeasonConstants.PLAYOFF_DELAY_DAYS days (2 weeks)
        wild_card_date = final_reg_season_date.add_days(
            SeasonConstants.PLAYOFF_DELAY_DAYS
        )

        # Adjust to next Saturday
        # Use Python's weekday() where Monday=0, Saturday=SeasonConstants.WILD_CARD_WEEKDAY, Sunday=6
        while (
            wild_card_date.to_python_date().weekday()
            != SeasonConstants.WILD_CARD_WEEKDAY
        ):  # SeasonConstants.WILD_CARD_WEEKDAY = Saturday
            wild_card_date = wild_card_date.add_days(1)
            # Safety check to prevent infinite loop
            if (
                wild_card_date.days_until(final_reg_season_date)
                > SeasonConstants.DATE_ADJUSTMENT_SAFETY_LIMIT
            ):
                # If we've gone more than SeasonConstants.DATE_ADJUSTMENT_SAFETY_LIMIT days, something is wrong
                # Just use the date SeasonConstants.PLAYOFF_DELAY_DAYS days out
                wild_card_date = final_reg_season_date.add_days(
                    SeasonConstants.PLAYOFF_DELAY_DAYS
                )
                break

        return wild_card_date

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
                 → Generate 2024 draft class in Sept 2024
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

    def _calculate_preseason_start_for_handler(self, season_year: int) -> datetime:
        """
        Calculate preseason start date for phase transition handler.

        Args:
            season_year: The season year

        Returns:
            datetime representing preseason start date (typically first Thursday in August)
        """
        generator = RandomScheduleGenerator(
            event_db=self.event_db, dynasty_id=self.dynasty_id
        )
        return generator._calculate_preseason_start(season_year)  # Returns datetime

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
        wild_card_date = self._calculate_wild_card_date()

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

        Uses the season/phase controller's tracked week number which is
        automatically maintained during week advancement.

        Returns:
            int: Current week number (1-18 for regular season, 1-4 for preseason, 0 for other phases)
        """
        if self.phase_state.phase == SeasonPhase.REGULAR_SEASON:
            # Use SeasonController's tracked week (most reliable)
            return (
                self.season_controller.current_week
                if hasattr(self.season_controller, "current_week")
                else 0
            )
        elif self.phase_state.phase == SeasonPhase.PRESEASON:
            # Preseason weeks are 1-4
            return (
                self.season_controller.current_week
                if hasattr(self.season_controller, "current_week")
                else 0
            )
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
                season_year=self.season_year, season_type=season_type
            )

            if self.verbose_logging:
                print(
                    f"[STANDINGS_RESET] All 32 teams reset to 0-0-0 for season {self.season_year} ({season_type})"
                )

        except Exception as e:
            raise Exception(f"Failed to reset standings: {e}") from e

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
