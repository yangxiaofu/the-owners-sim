"""
Season Cycle Controller

Unified controller orchestrating the complete NFL season cycle from
Week 1 Regular Season → Super Bowl → Offseason.

This controller manages the three distinct phases:
1. REGULAR_SEASON: 272 games across 18 weeks
2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
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
try:
    from calendar.date_models import Date
    from calendar.season_phase_tracker import SeasonPhase
    from calendar.phase_state import PhaseState
except ModuleNotFoundError:
    from src.calendar.date_models import Date
    from src.calendar.season_phase_tracker import SeasonPhase
    from src.calendar.phase_state import PhaseState

from playoff_system.playoff_controller import PlayoffController
from playoff_system.playoff_seeder import PlayoffSeeder
from database.api import DatabaseAPI
from database.draft_class_api import DraftClassAPI
from events import EventDatabaseAPI
from scheduling import RandomScheduleGenerator

# Phase transition system (dependency injection support)
try:
    from season.phase_transition.phase_completion_checker import PhaseCompletionChecker
    from season.phase_transition.phase_transition_manager import PhaseTransitionManager
    from season.phase_transition.models import PhaseTransition, TransitionHandlerKey
    from season.phase_transition.transition_handlers.offseason_to_preseason import OffseasonToPreseasonHandler
except ModuleNotFoundError:
    from src.season.phase_transition.phase_completion_checker import PhaseCompletionChecker
    from src.season.phase_transition.phase_transition_manager import PhaseTransitionManager
    from src.season.phase_transition.models import PhaseTransition, TransitionHandlerKey
    from src.season.phase_transition.transition_handlers.offseason_to_preseason import OffseasonToPreseasonHandler


class SeasonCycleController:
    """
    Unified controller orchestrating complete NFL season simulation cycle.

    Manages three distinct phases:
    1. REGULAR_SEASON: 272 games across 18 weeks
    2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
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
        season_year: int = 2024,
        start_date: Optional[Date] = None,
        initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON,
        enable_persistence: bool = True,
        verbose_logging: bool = True,
        # Dependency injection (optional - for testing)
        phase_completion_checker: Optional[PhaseCompletionChecker] = None,
        phase_transition_manager: Optional[PhaseTransitionManager] = None
    ):
        """
        Initialize season cycle controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            start_date: Dynasty start date - should be ONE DAY BEFORE first game
                       (defaults to Sept 4 for first game on Sept 5)
            initial_phase: Starting phase (REGULAR_SEASON, PLAYOFFS, or OFFSEASON)
                          Used when loading saved dynasty mid-season
            enable_persistence: Whether to save stats to database
            verbose_logging: Whether to print progress messages
            phase_completion_checker: Optional PhaseCompletionChecker for testing
            phase_transition_manager: Optional PhaseTransitionManager for testing
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        print(f"[DYNASTY_TRACE] SeasonCycleController.__init__(): dynasty_id={dynasty_id}")
        self.season_year = season_year
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        self.logger = logging.getLogger(self.__class__.__name__)

        # Default to day before first game (first game is Thursday Sept 5, dynasty starts Wednesday Sept 4)
        if start_date is None:
            start_date = Date(season_year, 9, 4)

        self.start_date = start_date

        # Create shared phase state with correct starting phase (single source of truth)
        self.phase_state = PhaseState(initial_phase)

        # Import SeasonController here to avoid circular imports
        from demo.interactive_season_sim.season_controller import SeasonController

        # Initialize season controller (always starts in regular season)
        self.season_controller = SeasonController(
            database_path=database_path,
            start_date=start_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging,
            phase_state=self.phase_state
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

        # Database API for data retrieval (MUST be initialized before phase-aware initialization)
        self.database_api = DatabaseAPI(database_path)

        # Initialize EventDatabaseAPI for offseason event execution
        self.event_db = EventDatabaseAPI(database_path)

        # Calculate last scheduled regular season game date for flexible end-of-season detection
        self.last_regular_season_game_date = self._get_last_regular_season_game_date()

        # ============ PHASE TRANSITION SYSTEM ============
        # Initialize phase completion checker (dependency injection support)
        if phase_completion_checker is None:
            # Create default checker with injected dependencies
            self.phase_completion_checker = PhaseCompletionChecker(
                get_games_played=lambda: self.total_games_played,
                get_current_date=lambda: self.calendar.get_current_date(),
                get_last_regular_season_game_date=lambda: self.last_regular_season_game_date,
                is_super_bowl_complete=lambda: self._is_super_bowl_complete(),
                calculate_preseason_start=lambda: self._calculate_preseason_start_for_handler(self.season_year + 1)
            )
        else:
            self.phase_completion_checker = phase_completion_checker

        # Initialize phase transition manager (dependency injection support)
        if phase_transition_manager is None:
            # Create OFFSEASON → PRESEASON handler
            offseason_to_preseason_handler = OffseasonToPreseasonHandler(
                generate_preseason=self._generate_preseason_schedule_for_handler,
                generate_regular_season=self._generate_regular_season_schedule_for_handler,
                reset_standings=self._reset_standings_for_handler,
                calculate_preseason_start=self._calculate_preseason_start_for_handler,
                update_database_phase=self._update_database_phase_for_handler,
                dynasty_id=dynasty_id,
                new_season_year=season_year + 1,  # Next season
                verbose_logging=verbose_logging
            )

            # Create default manager with registered handlers
            self.phase_transition_manager = PhaseTransitionManager(
                phase_state=self.phase_state,
                completion_checker=self.phase_completion_checker,
                transition_handlers={
                    TransitionHandlerKey.OFFSEASON_TO_PRESEASON: offseason_to_preseason_handler.execute
                }
            )
        else:
            self.phase_transition_manager = phase_transition_manager

        # Ensure dynasty record exists (required for foreign key constraints)
        self.database_api.db_connection.ensure_dynasty_exists(
            dynasty_id=dynasty_id,
            dynasty_name=f"Dynasty {dynasty_id}",
            owner_name=None,
            team_id=None
        )

        # GENERATE DRAFT CLASS FOR THIS SEASON
        self._generate_draft_class_if_needed()

        # State tracking - set active controller based on initial phase
        # IMPORTANT: This comes AFTER database_api initialization because _restore_playoff_controller() needs it
        if initial_phase == SeasonPhase.PLAYOFFS:
            # Restore playoff controller from database
            self._restore_playoff_controller()
            self.active_controller = self.playoff_controller
        elif initial_phase == SeasonPhase.OFFSEASON:
            # Restore playoff controller so users can review completed bracket
            self._restore_playoff_controller()
            self.active_controller = None  # No active controller in offseason (no more games to simulate)
        else:
            # Regular season - use season controller
            self.active_controller = self.season_controller

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON CYCLE CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {season_year}")
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
        # Handle offseason case
        if self.phase_state.phase == SeasonPhase.OFFSEASON:
            # Execute any scheduled offseason events for this day
            try:
                current_date = self.calendar.get_current_date()

                if self.verbose_logging:
                    print(f"\n[OFFSEASON_DAY] Advancing offseason day: {current_date}")

                # Import SimulationExecutor to trigger events
                from calendar.simulation_executor import SimulationExecutor

                executor = SimulationExecutor(
                    calendar=self.calendar,
                    event_db=self.event_db,
                    database_path=self.database_path,
                    dynasty_id=self.dynasty_id,
                    enable_persistence=self.enable_persistence,
                    season_year=self.season_year,
                    phase_state=self.phase_state
                )

                # Simulate events for current day
                event_results = executor.simulate_day(current_date)

                # Advance calendar
                self.calendar.advance(1)
                self.total_days_simulated += 1

                if self.verbose_logging:
                    print(f"[OFFSEASON_DAY] Calendar advanced successfully to: {self.calendar.get_current_date()}")

                return {
                    "date": str(current_date),
                    "games_played": 0,
                    "events_triggered": event_results.get('events_executed', []),
                    "results": [],
                    "current_phase": "offseason",
                    "phase_transition": None,
                    "success": True,
                    "message": f"Offseason day complete. {len(event_results.get('events_executed', []))} events triggered."
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
                    "message": "Season complete. No more games to simulate."
                }

        # Delegate to active controller
        result = self.active_controller.advance_day()

        # Update statistics
        self.total_games_played += result.get('games_played', 0)
        self.total_days_simulated += 1

        # Check for phase transitions
        phase_transition = self._check_phase_transition()
        if phase_transition:
            result['phase_transition'] = phase_transition

        result['current_phase'] = self.phase_state.phase.value

        return result

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 7 days.

        Returns:
            Dictionary with weekly summary
        """
        if self.phase_state.phase == SeasonPhase.OFFSEASON:
            # Advance offseason by 7 days, collecting any triggered events
            events_triggered = []
            start_date = str(self.calendar.get_current_date())

            for day_num in range(7):
                day_result = self.advance_day()
                if day_result.get('events_triggered'):
                    events_triggered.extend(day_result['events_triggered'])

            end_date = str(self.calendar.get_current_date())

            return {
                "success": True,
                "week_complete": True,
                "current_phase": "offseason",
                "date": end_date,
                "games_played": 0,
                "message": f"Offseason week advanced ({start_date} → {end_date}). {len(events_triggered)} events triggered."
            }

        # Delegate to active controller
        result = self.active_controller.advance_week()

        # Update statistics
        self.total_games_played += result.get('total_games_played', 0)

        # Check for phase transitions
        if self.verbose_logging:
            print(f"\n[DEBUG] advance_week(): Before phase transition check, phase = {self.phase_state.phase.value}")

        phase_transition = self._check_phase_transition()
        if phase_transition:
            result['phase_transition'] = phase_transition
            if self.verbose_logging:
                print(f"[DEBUG] advance_week(): Phase transition occurred: {phase_transition}")

        if self.verbose_logging:
            print(f"[DEBUG] advance_week(): After phase transition check, phase = {self.phase_state.phase.value}")

        result['current_phase'] = self.phase_state.phase.value

        # Add current date to result (matching what advance_day() returns)
        # This ensures UI controllers can properly update the displayed date
        result['date'] = str(self.calendar.get_current_date())

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
            "success": True
        }

    def simulate_to_phase_end(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulate until current phase ends (phase transition detected).

        Stops when phase changes, giving user control at phase boundaries.
        This allows users to review playoff brackets, make offseason decisions, etc.

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
        # NEW: Handle offseason - simulate to next milestone instead of full phase
        if self.phase_state.phase == SeasonPhase.OFFSEASON:
            return self.simulate_to_next_offseason_milestone(progress_callback)

        # Existing code for regular season and playoffs continues below...
        starting_phase = self.phase_state.phase
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played
        weeks_simulated = 0

        if self.verbose_logging:
            title = f"SIMULATING TO END OF {starting_phase.value.upper()}"
            print(f"\n{'='*80}")
            print(f"{title.center(80)}")
            print(f"{'='*80}")

        # Continue until phase changes
        consecutive_empty_weeks = 0
        max_empty_weeks = 3  # Safety valve: stop if 3 weeks pass with no games

        while self.phase_state.phase == starting_phase and self.phase_state.phase != SeasonPhase.OFFSEASON:
            games_before = self.total_games_played
            result = self.advance_week()
            games_after = self.total_games_played
            weeks_simulated += 1

            # Track consecutive empty weeks (no games played)
            if games_after == games_before:
                consecutive_empty_weeks += 1
                if consecutive_empty_weeks >= max_empty_weeks:
                    if self.verbose_logging:
                        print(f"[WARNING] Stopping simulation: {consecutive_empty_weeks} consecutive weeks with no games")
                    break
            else:
                consecutive_empty_weeks = 0  # Reset counter when games are played

            # Progress callback for UI updates
            if progress_callback:
                games_this_iteration = self.total_games_played - initial_games
                progress_callback(weeks_simulated, games_this_iteration)

        return {
            'start_date': str(start_date),
            'end_date': str(self.calendar.get_current_date()),
            'weeks_simulated': weeks_simulated,
            'total_games': self.total_games_played - initial_games,
            'starting_phase': starting_phase.value,
            'ending_phase': self.phase_state.phase.value,
            'phase_transition': self.phase_state.phase != starting_phase,
            'success': True
        }

    def simulate_to_next_offseason_milestone(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulate to next offseason milestone (stops at EVERY milestone).

        Includes ALL events: deadlines, window starts/ends, and milestone markers.
        Gives user control at every major offseason event.

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
                'message': str
            }
        """
        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            return {
                'success': False,
                'message': 'Not in offseason phase',
                'start_date': str(self.calendar.get_current_date()),
                'end_date': str(self.calendar.get_current_date()),
                'days_simulated': 0
            }

        # Query next milestone from event database
        next_milestone = self.event_db.get_next_offseason_milestone(
            current_date=self.calendar.get_current_date(),
            season_year=self.season_year,
            dynasty_id=self.dynasty_id
        )

        if not next_milestone:
            # NO FALLBACK - this is an error condition that must be fixed
            error_msg = (
                f"No offseason milestone found in database!\n\n"
                f"Dynasty: {self.dynasty_id}\n"
                f"Season: {self.season_year}\n"
                f"Current Date: {self.calendar.get_current_date()}\n\n"
                f"This means offseason events were not scheduled during Super Bowl → Offseason transition.\n"
                f"Check terminal output for '[OFFSEASON_EVENTS] Scheduling...' message and any errors."
            )

            if self.verbose_logging:
                print(f"\n{'='*80}")
                print(f"[ERROR] NO OFFSEASON MILESTONES FOUND")
                print(f"{'='*80}")
                print(error_msg)
                print(f"{'='*80}\n")

            return {
                'success': False,
                'message': error_msg,
                'starting_phase': 'offseason',
                'ending_phase': 'offseason',
                'weeks_simulated': 0,
                'total_games': 0,
                'phase_transition': False,
                'days_simulated': 0,
                'events_executed': 0
            }

        # Use simulate_to_date to reach milestone
        milestone_date = next_milestone['event_date']
        result = self.simulate_to_date(milestone_date, execute_events=True, progress_callback=progress_callback)

        # Add milestone-specific info to result
        result['milestone_reached'] = next_milestone['display_name']
        result['milestone_type'] = next_milestone['event_type']
        result['milestone_date'] = str(milestone_date)

        # Add keys UI expects
        result['starting_phase'] = 'offseason'
        result['ending_phase'] = self.phase_state.phase.value
        result['weeks_simulated'] = result['days_simulated'] // 7
        result['total_games'] = result.get('games_played', 0)
        result['phase_transition'] = False

        return result

    def simulate_to_date(
        self,
        target_date: Date,
        execute_events: bool = True,
        progress_callback=None
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
                'success': False,
                'start_date': str(current_date),
                'end_date': str(current_date),
                'days_simulated': 0,
                'events_triggered': [],
                'games_played': 0,
                'message': f'Target date ({target_date}) must be after current date ({current_date})'
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
            if day_result.get('events_triggered'):
                events_triggered.extend(day_result['events_triggered'])

            # Progress callback for UI
            if progress_callback and total_days > 0:
                progress_callback(days_advanced, total_days)

            # Safety check: prevent infinite loops
            if days_advanced > total_days + 7:  # Allow 7-day buffer for tolerance
                self.logger.warning(f"Simulation exceeded expected days ({days_advanced} > {total_days})")
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
            'success': True,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'days_simulated': days_advanced,
            'events_triggered': events_triggered,
            'games_played': games_played,
            'message': f'Simulated {days_advanced} days ({start_date} → {end_date}). {games_played} games, {len(events_triggered)} events.'
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
        next_milestone = self.event_db.get_next_offseason_milestone(
            current_date=current_date,
            season_year=self.season_year,
            dynasty_id=self.dynasty_id
        )

        if not next_milestone:
            return "Next Season"

        return next_milestone['display_name']

    def simulate_to_new_season(self, progress_callback=None) -> Dict[str, Any]:
        """
        Skip all remaining offseason milestones and initialize new season.

        Auto-executes all offseason events (franchise tags, draft, FA, etc.)
        and advances calendar to first Thursday in August (preseason start).

        Args:
            progress_callback: Optional callback(current, total, event_name) for UI progress updates

        Returns:
            Dict with same keys as simulate_to_phase_end() for UI compatibility:
            {
                'success': bool,
                'start_date': str,
                'end_date': str,
                'starting_phase': str,
                'ending_phase': str,
                'weeks_simulated': int,
                'total_games': int,
                'phase_transition': bool,
                'days_simulated': int,
                'events_executed': int,
                'event_list': List[str],
                'new_season_year': int,
                'message': str
            }
        """
        # TODO: Implement full skip-to-new-season logic
        # See docs/plans/season_cycle_controller_implementation_plan.md for details

        if self.phase_state.phase != SeasonPhase.OFFSEASON:
            return {
                'success': False,
                'message': 'Can only skip to new season during offseason',
                'starting_phase': self.phase_state.phase.value,
                'ending_phase': self.phase_state.phase.value,
                'weeks_simulated': 0,
                'total_games': 0,
                'phase_transition': False,
                'days_simulated': 0,
                'events_executed': 0
            }

        if self.verbose_logging:
            print(f"\n[SKIP_TO_NEW_SEASON] TODO: Implement full season skip logic")
            print(f"  Current implementation is placeholder")

        # Placeholder return (will be replaced with full implementation)
        return {
            'success': False,
            'message': 'Skip to new season not yet implemented - see season_cycle_controller_implementation_plan.md',
            'starting_phase': 'offseason',
            'ending_phase': 'offseason',
            'weeks_simulated': 0,
            'total_games': 0,
            'phase_transition': False,
            'days_simulated': 0,
            'events_executed': 0,
            'event_list': [],
            'new_season_year': self.season_year
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
            # Return final standings from database
            return self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

        return self.season_controller.get_current_standings()

    def get_playoff_bracket(self) -> Optional[Dict[str, Any]]:
        """
        Get playoff bracket (available during playoffs and offseason).

        Returns:
            Bracket data or None if not available
        """
        # Only hide bracket during regular season (before playoffs start)
        if self.phase_state.phase == SeasonPhase.REGULAR_SEASON:
            return None

        # Lazy initialization: If playoff controller not initialized but we need it, restore it
        # This handles the case when app restarts during playoffs or offseason
        if not self.playoff_controller and self.phase_state.phase in [SeasonPhase.PLAYOFFS, SeasonPhase.OFFSEASON]:
            try:
                if self.verbose_logging:
                    print(f"[DEBUG] get_playoff_bracket(): playoff_controller is None, attempting restoration...")
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
            "active_controller": type(self.active_controller).__name__ if self.active_controller else None
        }

    # ========== Private Methods ==========

    def _check_phase_transition(self) -> Optional[Dict[str, Any]]:
        """
        Check if phase transition should occur using PhaseTransitionManager.

        Uses the new testable phase transition system with dependency injection.
        Maintains backward compatibility by delegating to existing transition methods.

        Returns:
            Transition info if occurred, None otherwise
        """
        if self.verbose_logging:
            print(f"\n[DEBUG] Checking phase transition (current phase: {self.phase_state.phase.value})")

        # Check if transition is needed (pure logic, no side effects)
        transition = self.phase_transition_manager.check_transition_needed()

        if transition is None:
            # No transition needed
            if self.verbose_logging and self.phase_state.phase == SeasonPhase.PLAYOFFS:
                if not self._is_super_bowl_complete():
                    print(f"[DEBUG] Super Bowl not yet complete, remaining in PLAYOFFS phase")
            return None

        # Transition needed - execute it
        if self.verbose_logging:
            print(f"\n[PHASE_TRANSITION] {transition}")

        # Execute transition using existing methods (backward compatible)
        if transition.from_phase == SeasonPhase.REGULAR_SEASON and transition.to_phase == SeasonPhase.PLAYOFFS:
            self._transition_to_playoffs()
            return {
                "from_phase": "regular_season",
                "to_phase": "playoffs",
                "trigger": transition.trigger
            }

        elif transition.from_phase == SeasonPhase.PLAYOFFS and transition.to_phase == SeasonPhase.OFFSEASON:
            print(f"\n{'='*80}")
            print(f"[SUPER_BOWL_FLOW] Super Bowl complete detected!")
            print(f"[SUPER_BOWL_FLOW] Transitioning from PLAYOFFS → OFFSEASON")
            print(f"{'='*80}")
            self._transition_to_offseason()
            return {
                "from_phase": "playoffs",
                "to_phase": "offseason",
                "trigger": transition.trigger
            }

        elif transition.from_phase == SeasonPhase.OFFSEASON and transition.to_phase == SeasonPhase.PRESEASON:
            print(f"\n{'='*80}")
            print(f"[NEW_SEASON_FLOW] Offseason complete detected!")
            print(f"[NEW_SEASON_FLOW] Current date: {self.calendar.get_current_date()}")
            print(f"[NEW_SEASON_FLOW] Preseason start: {self._calculate_preseason_start_for_handler(self.season_year + 1)}")
            print(f"[NEW_SEASON_FLOW] Transitioning from OFFSEASON → PRESEASON")
            print(f"[NEW_SEASON_FLOW] Generating preseason schedule (48 games)...")
            print(f"[NEW_SEASON_FLOW] Generating regular season schedule (272 games)...")
            print(f"{'='*80}")

            try:
                # Execute the transition via PhaseTransitionManager
                # This calls OffseasonToPreseasonHandler.execute() which:
                # - Generates 48 preseason games
                # - Generates 272 regular season games
                # - Resets all team standings to 0-0-0
                # - Updates database phase to PRESEASON
                result = self.phase_transition_manager.execute_transition(transition)

                # Increment season year for new season
                old_year = self.season_year
                self.season_year += 1

                print(f"\n{'='*80}")
                print(f"[NEW_SEASON_SUCCESS] New season initialized!")
                print(f"  Season: {old_year} → {self.season_year}")
                print(f"  Phase: OFFSEASON → PRESEASON")
                print(f"  Preseason games: 48")
                print(f"  Regular season games: 272")
                print(f"  Teams reset: 32")
                print(f"{'='*80}\n")

                return {
                    "from_phase": "offseason",
                    "to_phase": "preseason",
                    "trigger": transition.trigger,
                    "new_season_year": self.season_year
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
            # Get all GAME events from event database
            all_game_events = self.season_controller.event_db.get_events_by_type("GAME")

            # Filter for regular season games WITH DYNASTY ISOLATION
            regular_season_events = [
                e for e in all_game_events
                # CRITICAL: Only look at this dynasty's games
                if e.get('dynasty_id') == self.dynasty_id
                # Exclude playoff and preseason games
                and not e.get('game_id', '').startswith('playoff_')
                and not e.get('game_id', '').startswith('preseason_')
                # CRITICAL: Only include weeks 1-18 (ignore corrupted future games)
                and 1 <= e.get('data', {}).get('parameters', {}).get('week', 0) <= 18
            ]

            if not regular_season_events:
                # No regular season games scheduled - return season end date as fallback
                self.logger.warning(f"No regular season games found for dynasty {self.dynasty_id}")
                return Date(self.season_year, 12, 31)  # Dec 31 fallback

            # Find the event with the maximum timestamp
            last_event = max(regular_season_events, key=lambda e: e['timestamp'])

            # Convert timestamp to Date
            last_datetime = last_event['timestamp']
            last_date = Date(
                year=last_datetime.year,
                month=last_datetime.month,
                day=last_datetime.day
            )

            if self.verbose_logging:
                game_id = last_event.get('game_id', 'unknown')
                week = last_event.get('data', {}).get('parameters', {}).get('week', '?')
                self.logger.info(f"Last regular season game scheduled for: {last_date} (Week {week}, game_id={game_id})")

            return last_date

        except Exception as e:
            self.logger.error(f"Error calculating last regular season game date: {e}")
            # Fallback to Dec 31 if calculation fails
            return Date(self.season_year, 12, 31)

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
        # PRIMARY CHECK: Have all 272 regular season games been played?
        # This is the most reliable indicator and handles corrupted schedules
        games_played = self.total_games_played
        if games_played >= 272:
            if self.verbose_logging:
                print(f"[DEBUG] Regular season complete: {games_played} games played (threshold: 272)")
            return True

        # FALLBACK CHECK: Has date passed last scheduled regular season game?
        # This handles edge cases where games might not all be played
        current_date = self.calendar.get_current_date()
        date_check = current_date > self.last_regular_season_game_date

        if self.verbose_logging:
            print(f"[DEBUG] Regular season check:")
            print(f"  - Games played: {games_played}/272")
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
                print(f"\n[DEBUG] Checking Super Bowl completion: playoff_controller is None!")
            return False

        super_bowl_games = self.playoff_controller.get_round_games('super_bowl')

        # Check if Super Bowl EXISTS and HAS BEEN PLAYED (has a winner)
        # Game exists but winner_id is None → scheduled but not played yet
        # Game exists and winner_id is set → game has been played
        is_complete = (
            len(super_bowl_games) > 0
            and super_bowl_games[0].get('winner_id') is not None
        )

        # Debug logging
        if self.verbose_logging:
            print(f"\n[DEBUG] _is_super_bowl_complete() called:")
            print(f"  - playoff_controller exists: True")
            print(f"  - Super Bowl games: {super_bowl_games}")
            print(f"  - Super Bowl games count: {len(super_bowl_games)}")
            if super_bowl_games:
                winner_id = super_bowl_games[0].get('winner_id')
                status = super_bowl_games[0].get('status')
                print(f"  - Super Bowl winner_id: {winner_id}")
                print(f"  - Super Bowl status: {status}")
                print(f"  - Is complete (has winner): {is_complete}")
            else:
                print(f"  - Is complete: {is_complete}")

        if is_complete:
            print(f"\n[SUPER_BOWL_FLOW] ✅ Super Bowl has been played!")
            print(f"[SUPER_BOWL_FLOW]    Winner: Team {super_bowl_games[0].get('winner_id')}")
            print(f"[SUPER_BOWL_FLOW]    Ready to transition to OFFSEASON")
        elif len(super_bowl_games) > 0:
            print(f"\n[SUPER_BOWL_FLOW] ⏳ Super Bowl is SCHEDULED but not yet played")
            print(f"[SUPER_BOWL_FLOW]    Status: {super_bowl_games[0].get('status')}")
            print(f"[SUPER_BOWL_FLOW]    Remaining in PLAYOFFS phase")

        return is_complete

    def _transition_to_playoffs(self):
        """Execute transition from regular season to playoffs."""
        # Guard: prevent redundant transitions if already in playoffs
        if self.phase_state.phase == SeasonPhase.PLAYOFFS:
            if self.verbose_logging:
                print(f"\n⚠️  Already in playoffs phase, skipping transition")
            return

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'REGULAR SEASON COMPLETE - PLAYOFFS STARTING'.center(80)}")
            print(f"{'='*80}")

        try:
            # 1. Get final standings from database
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data or not standings_data.get('divisions'):
                self.logger.error("No standings found for playoff seeding")
                raise RuntimeError("Cannot calculate playoff seeding - no standings available")

            # 2. Convert standings to format expected by PlayoffSeeder
            # DatabaseAPI returns standings organized by division/conference
            # Each team_data has: {'team_id': int, 'standing': EnhancedTeamStanding}
            standings_dict = {}
            for division_name, teams in standings_data.get('divisions', {}).items():
                for team_data in teams:
                    team_id = team_data['team_id']
                    # Use the EnhancedTeamStanding object directly from database
                    standings_dict[team_id] = team_data['standing']

            # 3. Calculate playoff seeding using PlayoffSeeder
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict,
                season=self.season_year,
                week=18
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
                phase_state=self.phase_state
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

    def _restore_playoff_controller(self):
        """
        Restore PlayoffController when loading saved dynasty mid-playoffs.

        Called during initialization when phase_state indicates dynasty is in playoffs.
        Reconstructs bracket from existing database events without re-scheduling games.
        """
        # Guard: prevent duplicate initialization
        if self.playoff_controller is not None:
            if self.verbose_logging:
                print(f"⚠️  Playoff controller already initialized, skipping restoration")
            return

        try:
            if self.verbose_logging:
                print(f"\n{'='*80}")
                print(f"{'RESTORING PLAYOFF STATE FROM DATABASE'.center(80)}")
                print(f"{'='*80}")

            # 1. Query database for final standings (needed for seeding)
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data or not standings_data.get('divisions'):
                self.logger.error("No standings found - cannot restore playoff controller")
                raise RuntimeError("Cannot restore playoff bracket - no standings available")

            # 2. Convert standings to format expected by PlayoffSeeder
            standings_dict = {}
            for division_name, teams in standings_data.get('divisions', {}).items():
                for team_data in teams:
                    team_id = team_data['team_id']
                    standings_dict[team_id] = team_data['standing']

            # 3. Calculate playoff seeding
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict,
                season=self.season_year,
                week=18
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
                phase_state=self.phase_state
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
        """Execute transition from playoffs to offseason."""
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON COMPLETE - ENTERING OFFSEASON'.center(80)}")
            print(f"{'='*80}")
            print(f"[DEBUG] _transition_to_offseason() called")
            print(f"[DEBUG] Current phase before transition: {self.phase_state.phase.value}")

        # CRITICAL DIAGNOSTIC: Verify playoff events exist BEFORE transition
        print(f"\n[PLAYOFF_LIFECYCLE] ===== BEFORE OFFSEASON TRANSITION =====")
        playoff_count_before = self.database_api.count_playoff_events(
            dynasty_id=self.dynasty_id,
            season_year=self.season_year
        )
        print(f"[PLAYOFF_LIFECYCLE]   Dynasty: {self.dynasty_id}")
        print(f"[PLAYOFF_LIFECYCLE]   Database: {self.database_path}")
        print(f"[PLAYOFF_LIFECYCLE]   Playoff events in database: {playoff_count_before}")
        if playoff_count_before == 0:
            print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: NO PLAYOFF EVENTS FOUND!")

        try:
            # 1. Get Super Bowl result
            super_bowl_games = self.playoff_controller.get_round_games('super_bowl')
            super_bowl_result = super_bowl_games[0] if super_bowl_games else None

            champion_id = None
            if super_bowl_result:
                champion_id = super_bowl_result.get('winner_id')

            # 2. Update state
            if self.verbose_logging:
                print(f"[DEBUG] Setting phase_state.phase to OFFSEASON...")
            self.phase_state.phase = SeasonPhase.OFFSEASON
            self.active_controller = None  # No active controller in offseason
            if self.verbose_logging:
                print(f"[DEBUG] Current phase after setting: {self.phase_state.phase.value}")

            # Schedule offseason events
            try:
                if self.verbose_logging:
                    print(f"\n[OFFSEASON_EVENTS] Scheduling offseason events...")
                    print(f"  Season year: {self.season_year}")
                    print(f"  Dynasty ID: {self.dynasty_id}")

                from offseason.offseason_event_scheduler import OffseasonEventScheduler

                scheduler = OffseasonEventScheduler()

                # Get Super Bowl date from result
                super_bowl_date = None
                if super_bowl_result and super_bowl_result.get('game_date'):
                    game_date_obj = super_bowl_result['game_date']
                    # Convert to Date if it's a datetime
                    if hasattr(game_date_obj, 'year'):
                        from calendar.date_models import Date
                        super_bowl_date = Date(game_date_obj.year, game_date_obj.month, game_date_obj.day)

                # If no date in result, use current calendar date
                if not super_bowl_date:
                    super_bowl_date = self.calendar.get_current_date()

                if self.verbose_logging:
                    print(f"  Super Bowl date: {super_bowl_date}")

                # Schedule all offseason events
                scheduling_result = scheduler.schedule_offseason_events(
                    super_bowl_date=super_bowl_date,
                    season_year=self.season_year,
                    dynasty_id=self.dynasty_id,
                    event_db=self.season_controller.event_db
                )

                if self.verbose_logging:
                    print(f"\n📅 Offseason Events Scheduled:")
                    print(f"   Deadline Events: {scheduling_result['deadline_events']}")
                    print(f"   Window Events: {scheduling_result['window_events']}")
                    print(f"   Milestone Events: {scheduling_result['milestone_events']}")
                    print(f"   Total Events: {scheduling_result['total_events']}")

            except Exception as e:
                self.logger.error(f"Error scheduling offseason events: {e}")
                if self.verbose_logging:
                    print(f"⚠️  WARNING: Offseason event scheduling failed!")
                    print(f"  Error: {e}")
                    print(f"  This will prevent milestone-based simulation from working correctly.")
                    import traceback
                    traceback.print_exc()
                # Don't silently continue - this is a critical error

            # 3. Generate season summary
            self.season_summary = self._generate_season_summary()

            # 4. Notify user
            if self.verbose_logging:
                if champion_id:
                    from team_management.teams.team_loader import get_team_by_id
                    champion = get_team_by_id(champion_id)
                    print(f"\n🏆 Super Bowl Champion: {champion.full_name}")

                print(f"\n📊 Season Summary Generated")
                print(f"   Total Games: {self.total_games_played}")
                print(f"   Total Days: {self.total_days_simulated}")
                print(f"{'='*80}\n")

            # CRITICAL DIAGNOSTIC: Verify playoff events STILL exist AFTER transition
            print(f"\n[PLAYOFF_LIFECYCLE] ===== AFTER OFFSEASON TRANSITION =====")
            playoff_count_after = self.database_api.count_playoff_events(
                dynasty_id=self.dynasty_id,
                season_year=self.season_year
            )
            print(f"[PLAYOFF_LIFECYCLE]   Playoff events in database: {playoff_count_after}")
            if playoff_count_after == 0:
                print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: PLAYOFF EVENTS DISAPPEARED!")
            elif playoff_count_after != playoff_count_before:
                print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: Event count changed! Before: {playoff_count_before}, After: {playoff_count_after}")
            else:
                print(f"[PLAYOFF_LIFECYCLE]   ✅ Playoff events preserved ({playoff_count_after} events)")

        except Exception as e:
            self.logger.error(f"Error transitioning to offseason: {e}")
            if self.verbose_logging:
                print(f"❌ Offseason transition failed: {e}")
            raise

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

        # Add 14 days (2 weeks)
        wild_card_date = final_reg_season_date.add_days(14)

        # Adjust to next Saturday
        # Use Python's weekday() where Monday=0, Saturday=5, Sunday=6
        while wild_card_date.to_python_date().weekday() != 5:  # 5 = Saturday
            wild_card_date = wild_card_date.add_days(1)
            # Safety check to prevent infinite loop
            if wild_card_date.days_until(final_reg_season_date) > 30:
                # If we've gone more than 30 days, something is wrong
                # Just use the date 14 days out
                wild_card_date = final_reg_season_date.add_days(14)
                break

        return wild_card_date

    def _generate_season_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive season summary.

        Returns:
            Summary with standings, champions, stat leaders
        """
        try:
            # Get final standings
            final_standings = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            # Get Super Bowl winner
            super_bowl_games = self.playoff_controller.get_round_games('super_bowl') if self.playoff_controller else []
            champion_id = super_bowl_games[0]['winner_id'] if super_bowl_games else None

            # Note: Stat leaders queries would require additional DatabaseAPI methods
            # For now, we'll return basic summary
            summary = {
                "season_year": self.season_year,
                "dynasty_id": self.dynasty_id,
                "final_standings": final_standings,
                "super_bowl_champion": champion_id,
                "total_games": self.total_games_played,
                "total_days": self.total_days_simulated,
                "final_date": str(self.calendar.get_current_date())
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
                "error": str(e)
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
        draft_api = DraftClassAPI(self.database_path)

        # Check if draft class already exists (idempotent)
        if draft_api.dynasty_has_draft_class(self.dynasty_id, self.season_year):
            if self.verbose_logging:
                print(f"   Draft class for {self.season_year} already exists")
            return

        # Generate draft class (224 prospects = 7 rounds × 32 teams)
        try:
            draft_class_id = draft_api.generate_draft_class(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if self.verbose_logging:
                print(f"\n🏈 Draft Class Generated:")
                print(f"   Season: {self.season_year}")
                print(f"   Prospects: 224 (7 rounds × 32 teams)")
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
            event_name = event.get('display_name', 'Unknown Event')
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

        # Step 1: Increment season year
        old_year = self.season_year
        self.season_year += 1

        if self.verbose_logging:
            print(f"[NEW_SEASON] Season year: {old_year} → {self.season_year}")

        try:
            # Step 2: Generate preseason schedule
            from ui.domain_models.season_data_model import SeasonDataModel

            season_model = SeasonDataModel(
                db_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            # Generate preseason games (3 weeks, 48 total games)
            generator = RandomScheduleGenerator(
                event_db=self.event_db,
                dynasty_id=self.dynasty_id
            )

            preseason_games = generator.generate_preseason(season_year=self.season_year)

            if self.verbose_logging:
                print(f"[NEW_SEASON] Generated {len(preseason_games)} preseason games (3 weeks)")

            # Step 3: Generate regular season schedule (17 weeks, 272 games)
            # Dynasty starts day before first preseason game
            preseason_start = generator._calculate_preseason_start(self.season_year)
            dynasty_start = preseason_start - timedelta(days=1)

            success, error = season_model.generate_initial_schedule(dynasty_start)

            if not success:
                raise Exception(f"Failed to generate regular season schedule: {error}")

            if self.verbose_logging:
                print(f"[NEW_SEASON] Generated 272 regular season games (17 weeks)")

            # Step 4: Reset standings
            self._reset_all_standings()

            if self.verbose_logging:
                print(f"[NEW_SEASON] Reset all 32 team standings to 0-0-0")

            # Step 5: Update dynasty state
            self.dynasty_api.update_state(
                dynasty_id=self.dynasty_id,
                current_date=str(self.calendar.get_current_date()),
                current_week=0,  # Preseason is week 0
                current_phase='preseason'
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

            # Step 7: Update season controller's year
            self.season_controller.season_year = self.season_year

        except Exception as e:
            # Rollback season year on failure
            self.season_year = old_year

            # Log error
            self.logger.error(f"Failed to initialize season {old_year + 1}: {e}")

            if self.verbose_logging:
                print(f"❌ Season initialization failed: {e}")
                import traceback
                traceback.print_exc()

            # Re-raise with context
            raise Exception(f"Season initialization failed: {e}") from e

    # ========== Phase Transition Helper Methods ==========
    # These methods are used by OffseasonToPreseasonHandler

    def _generate_preseason_schedule_for_handler(self, season_year: int) -> List[Dict[str, Any]]:
        """
        Generate preseason schedule for phase transition handler.

        Args:
            season_year: The season year for schedule generation

        Returns:
            List of 48 preseason game event dictionaries
        """
        generator = RandomScheduleGenerator(
            event_db=self.event_db,
            dynasty_id=self.dynasty_id
        )
        return generator.generate_preseason(season_year=season_year)

    def _generate_regular_season_schedule_for_handler(
        self,
        season_year: int,
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Generate regular season schedule for phase transition handler.

        Args:
            season_year: The season year for schedule generation
            start_date: The first regular season game date (Thursday after Labor Day)

        Returns:
            List of 272 regular season game event dictionaries
        """
        from ui.domain_models.season_data_model import SeasonDataModel

        season_model = SeasonDataModel(
            db_path=self.database_path,
            dynasty_id=self.dynasty_id,
            season=season_year
        )

        # Use existing schedule generation
        dynasty_start = start_date - timedelta(days=1)
        success, error = season_model.generate_initial_schedule(dynasty_start)

        if not success:
            raise RuntimeError(f"Failed to generate regular season schedule: {error}")

        # Retrieve the generated games from event database
        all_events = self.event_db.get_events_by_type("GAME")
        regular_season_games = [
            e for e in all_events
            if e.get('dynasty_id') == self.dynasty_id
            and not e.get('game_id', '').startswith('playoff_')
            and not e.get('game_id', '').startswith('preseason_')
        ]

        return regular_season_games

    def _reset_standings_for_handler(self, season_year: int) -> None:
        """
        Reset all team standings for phase transition handler.

        Args:
            season_year: The season year for standings reset
        """
        # Temporarily update season_year for reset operation
        old_season_year = self.season_year
        self.season_year = season_year

        try:
            self._reset_all_standings()
        finally:
            # Restore original season_year
            self.season_year = old_season_year

    def _calculate_preseason_start_for_handler(self, season_year: int) -> datetime:
        """
        Calculate preseason start date for phase transition handler.

        Args:
            season_year: The season year

        Returns:
            datetime representing preseason start date (typically first Thursday in August)
        """
        generator = RandomScheduleGenerator(
            event_db=self.event_db,
            dynasty_id=self.dynasty_id
        )
        return generator._calculate_preseason_start(season_year)

    def _update_database_phase_for_handler(self, phase: str, season_year: int) -> None:
        """
        Update database phase for phase transition handler.

        Args:
            phase: The new phase name (e.g., "PRESEASON", "OFFSEASON")
            season_year: The season year
        """
        self.dynasty_api.update_state(
            dynasty_id=self.dynasty_id,
            current_date=str(self.calendar.get_current_date()),
            current_week=0 if phase == "PRESEASON" else None,
            current_phase=phase.lower()
        )

    # ========== Existing Helper Methods ==========

    def _reset_all_standings(self):
        """
        Reset all 32 teams to 0-0-0 records for new season.

        Updates standings table with fresh records for new season_year.
        """
        conn = self.database_api.db_connection.get_connection()
        cursor = conn.cursor()

        try:
            for team_id in range(1, 33):
                cursor.execute('''
                    INSERT OR REPLACE INTO standings
                    (dynasty_id, season, team_id, wins, losses, ties,
                     points_for, points_against, division_wins, division_losses,
                     conference_wins, conference_losses, home_wins, home_losses,
                     away_wins, away_losses)
                    VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                ''', (self.dynasty_id, self.season_year, team_id))

            conn.commit()

            if self.verbose_logging:
                print(f"[STANDINGS_RESET] All 32 teams reset to 0-0-0 for season {self.season_year}")

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to reset standings: {e}") from e

    # ==================== Dunder Methods ====================

    def __str__(self) -> str:
        """String representation"""
        return (f"SeasonCycleController(season={self.season_year}, "
                f"phase={self.phase_state.phase.value}, "
                f"games={self.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"SeasonCycleController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
