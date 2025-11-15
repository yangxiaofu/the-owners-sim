"""
Simulation Executor

Executes daily NFL simulation by coordinating calendar, events, and simulation.

This component orchestrates the daily simulation workflow by:
1. Getting the current date from the calendar
2. Retrieving scheduled events for that date from the events database
3. Executing each event (games, cap transactions, deadlines, etc.)
4. Recording game completions for phase tracking
5. Returning a summary of results

This is the execution layer that sits between SeasonManager (high-level API)
and the individual event simulation components.

Supported Event Types:
- GAME: NFL game simulations via FullGameSimulator
- FRANCHISE_TAG: Franchise tag applications with cap validation
- TRANSITION_TAG: Transition tag applications with cap validation
- PLAYER_RELEASE: Player releases with dead cap calculations
- CONTRACT_RESTRUCTURE: Contract restructures for cap space
- UFA_SIGNING: Unrestricted free agent signings with cap validation
- RFA_OFFER_SHEET: Restricted free agent offers with matching
- DEADLINE: NFL deadline markers (cap compliance, tag deadlines, etc.)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Use try/except to handle both production and test imports
try:
    from src.calendar.calendar_component import CalendarComponent
    from src.calendar.season_phase_tracker import GameCompletionEvent, PhaseTransition
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from .calendar_component import CalendarComponent
    from .season_phase_tracker import GameCompletionEvent, PhaseTransition
    from .date_models import Date

from events import EventDatabaseAPI, GameEvent, EventResult
from events.contract_events import FranchiseTagEvent, TransitionTagEvent, PlayerReleaseEvent, ContractRestructureEvent
from events.free_agency_events import UFASigningEvent, RFAOfferSheetEvent
from events.deadline_event import DeadlineEvent
from events.milestone_event import MilestoneEvent
from events.schedule_release_event import ScheduleReleaseEvent
from events.window_event import WindowEvent
from workflows import SimulationWorkflow


class SimulationExecutor:
    """
    Executes daily simulation workflow for all event types.

    Orchestrates the interaction between:
    - CalendarComponent (date/time management)
    - EventDatabaseAPI (event storage/retrieval)
    - Event classes (GameEvent, cap events, deadlines, etc.)
    - SeasonPhaseTracker (phase management via calendar)
    - SimulationWorkflow (3-stage simulation with persistence for games)

    Event Handling:
    - Game events use SimulationWorkflow for statistics persistence
    - Cap events simulate directly with cap validation
    - Deadline events execute cap compliance checks or act as markers

    This component is used by SeasonManager to execute scheduled events
    and can be used standalone for testing or demos.
    """

    def __init__(
        self,
        calendar: CalendarComponent,
        event_db: EventDatabaseAPI,
        database_path: Optional[str] = None,
        dynasty_id: str = "default",
        enable_persistence: bool = True,
        season_year: Optional[int] = None,
        phase_state: Optional['PhaseState'] = None,
        verbose_logging: bool = False,
        fast_mode: bool = False
    ):
        """
        Initialize simulation executor.

        Args:
            calendar: Calendar component for date management
            event_db: Event database API for event storage/retrieval
            database_path: Path to database for persistence (required if enable_persistence=True)
            dynasty_id: Dynasty context for data isolation
            enable_persistence: Whether to persist game results to database
            season_year: Season year for filtering dynasty-specific events (extracted from calendar if None)
            phase_state: Optional shared PhaseState object for phase reporting (uses calendar if None)
            verbose_logging: Enable diagnostic logging output (default: False)
            fast_mode: Skip actual simulations, generate fake results for ultra-fast testing
        """
        self.calendar = calendar
        self.event_db = event_db
        self.enable_persistence = enable_persistence
        self.dynasty_id = dynasty_id
        self.phase_state = phase_state  # NEW: Store for phase reporting
        self.verbose_logging = verbose_logging  # Enable diagnostic output
        self.fast_mode = fast_mode  # NEW: Store fast_mode for workflow creation

        # CRITICAL FIX #4: Extract season year from PhaseState (single source of truth)
        if season_year is None:
            phase_info = calendar.get_phase_info()
            self.season_year = phase_info.get("season_year")

            if self.season_year is None:
                # Fallback for legacy/test scenarios where PhaseState missing season_year
                self.season_year = calendar.get_current_date().year
                if verbose_logging:
                    print(
                        f"[WARNING] SimulationExecutor initialized without PhaseState.season_year, "
                        f"falling back to calendar year: {self.season_year}"
                    )
            elif verbose_logging:
                print(f"[SIMULATION_EXECUTOR] Initialized with season_year={self.season_year} from PhaseState")
        else:
            self.season_year = season_year
            if verbose_logging:
                print(f"[SIMULATION_EXECUTOR] Initialized with explicit season_year={self.season_year}")

        # Initialize SimulationWorkflow for 3-stage simulation
        if enable_persistence:
            if not database_path:
                raise ValueError("database_path is required when enable_persistence=True")
            self.workflow = SimulationWorkflow(
                enable_persistence=True,
                database_path=database_path,
                dynasty_id=dynasty_id,
                verbose_logging=True,  # Season simulation verbose logging
                fast_mode=fast_mode
            )
        else:
            self.workflow = SimulationWorkflow(
                enable_persistence=False,
                verbose_logging=False,
                fast_mode=fast_mode
            )

    @classmethod
    def for_testing(
        cls,
        event_db: 'EventDatabaseAPI',
        dynasty_id: str = "test_dynasty",
        enable_persistence: bool = False,
        verbose_logging: bool = False
    ) -> 'SimulationExecutor':
        """
        Create SimulationExecutor optimized for testing.

        Minimal setup with sensible defaults for unit testing:
        - Persistence disabled (no database writes)
        - Verbose logging disabled (quiet tests)
        - Minimal calendar (just for date context)
        - Fast mode enabled (skip actual game simulations)

        Example:
            >>> from src.events.event_database_api import EventDatabaseAPI
            >>> event_db = EventDatabaseAPI(":memory:")
            >>> executor = SimulationExecutor.for_testing(event_db)
            >>> events = [{'event_type': 'FRANCHISE_TAG', ...}]
            >>> result = executor.simulate_events(events)
            >>> assert result['success'] == True

        Args:
            event_db: EventDatabaseAPI instance (can be in-memory)
            dynasty_id: Dynasty identifier for testing (default: "test_dynasty")
            enable_persistence: Whether to save results (default: False)
            verbose_logging: Whether to print logs (default: False)

        Returns:
            Configured SimulationExecutor for testing
        """
        from src.calendar.calendar_component import CalendarComponent
        from src.calendar.date_models import Date

        # Create minimal calendar (just for date context)
        calendar = CalendarComponent(
            start_date=Date.today(),
            season_year=Date.today().year,
            database_api=event_db,
            dynasty_id=dynasty_id
        )

        return cls(
            calendar=calendar,
            event_db=event_db,
            database_path=":memory:",  # In-memory for testing
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging,
            fast_mode=True  # Skip actual game simulations for fast tests
        )

    def simulate_events(
        self,
        events: List[Dict[str, Any]],
        context_date: Optional[Date] = None
    ) -> Dict[str, Any]:
        """
        Simulate a list of events directly (for testing/debugging).

        This method allows testing specific event combinations without
        calendar/database setup. Perfect for:
        - Unit testing offseason event sequences
        - Debugging event combinations
        - Manual event execution
        - Testing event validation logic

        Example:
            >>> executor = SimulationExecutor.for_testing(event_db)
            >>> events = [
            ...     {'event_type': 'FRANCHISE_TAG', 'game_id': 'test1', ...},
            ...     {'event_type': 'UFA_SIGNING', 'game_id': 'test2', ...}
            ... ]
            >>> result = executor.simulate_events(events)
            >>> assert result['success'] == True
            >>> assert len(result['events_completed']) == 2

        Args:
            events: List of event data dictionaries (same structure as from database)
            context_date: Optional date for logging context (defaults to today)

        Returns:
            Dict containing:
            - events_completed: List[Dict] - Successfully completed events
            - phase_transitions: List[Dict] - Phase transitions triggered (games only)
            - errors: List[str] - Error messages
            - success: bool - True if no errors
            - events_count: int - Total events processed
        """
        if context_date is None:
            context_date = Date.today()

        # Delegate to private batch simulation method
        events_completed, phase_transitions, errors = self._simulate_event_batch(
            events,
            context_date
        )

        return {
            "events_completed": events_completed,
            "phase_transitions": [self._transition_to_dict(t) for t in phase_transitions],
            "errors": errors,
            "success": len(errors) == 0,
            "events_count": len(events)
        }

    def _simulate_event_batch(
        self,
        events_for_day: List[Dict[str, Any]],
        target_date: Date
    ) -> Tuple[List[Dict[str, Any]], List['PhaseTransition'], List[str]]:
        """
        Simulate all events in a batch.

        Core simulation logic extracted from simulate_day().
        Handles event reconstruction, validation, execution, and result tracking.

        Args:
            events_for_day: List of event dictionaries (from DB or manual)
            target_date: Date context for logging

        Returns:
            Tuple of (events_completed, phase_transitions, errors)

        Side Effects:
            - Updates events in database via self.event_db.update_event()
            - Records game completions via self.calendar.record_game_completion()
            - Prints extensive logging output
            - May raise RuntimeError for critical event failures
        """
        # Simulate each event
        events_completed = []
        phase_transitions = []
        errors = []

        for i, event_data in enumerate(events_for_day, 1):
            try:
                print(f"\n{'─'*80}")
                print(f"Event {i}/{len(events_for_day)}")

                # Get event type to determine which class to use
                event_type = event_data.get('event_type', 'GAME')
                print(f"Event Type: {event_type}")

                # DEBUG: Check if we're processing SCHEDULE_RELEASE
                if event_type == 'SCHEDULE_RELEASE':
                    print(f"[SCHEDULE_RELEASE_TRIGGERED] 🎯 About to reconstruct SCHEDULE_RELEASE event")

                # Reconstruct appropriate event class based on type
                event = self._reconstruct_event(event_data, event_type)

                # Validate preconditions
                is_valid, error_msg = event.validate_preconditions()
                if not is_valid:
                    error_full = f"Event {event.get_game_id()}: Validation failed - {error_msg}"
                    errors.append(error_full)

                    # DIAGNOSTIC: Print validation failure details
                    print(f"❌ {error_full}")
                    print(f"[VALIDATION_FAILURE] Game ID: {event.get_game_id()}")
                    print(f"[VALIDATION_FAILURE] Event Type: {event_type}")
                    print(f"[VALIDATION_FAILURE] Validation Error: {error_msg}")
                    if hasattr(event, 'season'):
                        print(f"[VALIDATION_FAILURE] Game Season: {event.season}")
                    if hasattr(event, 'away_team_id') and hasattr(event, 'home_team_id'):
                        print(f"[VALIDATION_FAILURE] Matchup: {event.away_team_id} @ {event.home_team_id}")
                    if hasattr(event, 'game_date'):
                        print(f"[VALIDATION_FAILURE] Game Date: {event.game_date}")

                    continue

                # Execute event (different handling for games vs other events)
                if event_type == "GAME":
                    # Games use workflow for statistics persistence
                    workflow_result = self.workflow.execute(event)
                    result = workflow_result.simulation_result
                else:
                    # Other events simulate directly (no workflow needed)
                    # DEBUG: Confirm we're about to simulate SCHEDULE_RELEASE
                    if event_type == 'SCHEDULE_RELEASE':
                        print(f"[SCHEDULE_RELEASE_TRIGGERED] 🚀 About to call SCHEDULE_RELEASE.simulate()")
                    result = event.simulate()
                    # DEBUG: Confirm simulate() returned
                    if event_type == 'SCHEDULE_RELEASE':
                        print(f"[SCHEDULE_RELEASE_TRIGGERED] ✅ SCHEDULE_RELEASE.simulate() returned: {result.success}")
                        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Result data: {result.data}")

                # Record completion and handle results
                if result.success:
                    # Record game completion in phase tracker (games only)
                    if event_type == "GAME":
                        transition = self._record_game_completion(event, result)
                        if transition:
                            phase_transitions.append(transition)
                            print(f"\n🔄 PHASE TRANSITION: {transition.from_phase.value} → {transition.to_phase.value}")

                    # Store result summary (generic for all event types)
                    event_summary = self._create_event_summary(event, result, event_type)
                    events_completed.append(event_summary)

                    # Update event in database with results
                    self.event_db.update_event(event)
                else:
                    # DIAGNOSTIC: Print detailed failure information
                    error_msg = f"Event {event.get_game_id()}: Simulation failed - {result.error_message}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    print(f"[SIMULATION_FAILURE] Game ID: {event.get_game_id()}")
                    print(f"[SIMULATION_FAILURE] Event Type: {event_type}")
                    print(f"[SIMULATION_FAILURE] Error Message: {result.error_message}")
                    if hasattr(event, 'season'):
                        print(f"[SIMULATION_FAILURE] Game Season: {event.season}")
                    if hasattr(event, 'away_team_id') and hasattr(event, 'home_team_id'):
                        print(f"[SIMULATION_FAILURE] Matchup: {event.away_team_id} @ {event.home_team_id}")

                    events_completed.append({
                        "event_id": event.get_game_id(),
                        "event_type": event_type,
                        "success": False,
                        "error": result.error_message
                    })

            except Exception as e:
                import traceback
                import sys

                event_type = event_data.get('event_type', 'unknown')
                error_msg = f"Event {i}: Unexpected error - {str(e)}"
                errors.append(error_msg)

                # FAIL-LOUD: Special handling for critical events
                is_critical_event = event_type in ['SCHEDULE_RELEASE', 'DEADLINE']

                if is_critical_event:
                    print(f"\n{'!'*80}")
                    print(f"🚨 CRITICAL EVENT FAILURE: {event_type}")
                    print(f"{'!'*80}")

                print(f"❌ {error_msg}")
                print(f"[ERROR_DETAIL] Full traceback:")
                traceback.print_exc()

                # Explicit flush to ensure error output is visible immediately
                sys.stdout.flush()
                sys.stderr.flush()

                print(f"[ERROR_DETAIL] Event game_id: {event_data.get('game_id', 'unknown')}")
                print(f"[ERROR_DETAIL] Event type: {event_type}")
                if 'data' in event_data and 'parameters' in event_data['data']:
                    params = event_data['data']['parameters']
                    print(f"[ERROR_DETAIL] Event parameters:")
                    print(f"  - season: {params.get('season', 'NOT SET')}")
                    print(f"  - week: {params.get('week', 'NOT SET')}")
                    print(f"  - away_team: {params.get('away_team_id', 'NOT SET')}")
                    print(f"  - home_team: {params.get('home_team_id', 'NOT SET')}")
                    print(f"  - game_date: {params.get('game_date', 'NOT SET')}")

                if is_critical_event:
                    print(f"{'!'*80}")
                    print(f"🚨 CRITICAL: {event_type} failed - season transition may be incomplete!")
                    print(f"{'!'*80}")
                    sys.stdout.flush()
                    sys.stderr.flush()

                    # For critical events, re-raise to halt execution (fail-loud)
                    raise RuntimeError(
                        f"Critical event {event_type} failed during season transition. "
                        f"Error: {str(e)}. See traceback above for details."
                    ) from e

        return (events_completed, phase_transitions, errors)

    def simulate_day(self, target_date: Optional[Date] = None) -> Dict[str, Any]:
        """
        Simulate all events for a specific day.

        Args:
            target_date: Date to simulate (uses calendar's current date if None)

        Returns:
            Dictionary with simulation results:
            {
                "date": str,
                "events_count": int,
                "events_completed": List[Dict],
                "phase_transitions": List[Dict],
                "current_phase": str,
                "phase_info": Dict,
                "success": bool,
                "errors": List[str]
            }
        """
        # Use current date if not specified
        if target_date is None:
            target_date = self.calendar.get_current_date()

        print(f"\n{'='*80}")
        print(f"SIMULATING DAY: {target_date}")
        print(f"{'='*80}")

        # Get events for this date
        events_for_day = self._get_events_for_date(target_date)

        if not events_for_day:
            return {
                "date": str(target_date),
                "events_count": 0,
                "events_completed": [],
                "phase_transitions": [],
                "current_phase": self._get_current_phase_value(),
                "success": True,
                "message": "No events scheduled for this day"
            }

        print(f"\n📅 Found {len(events_for_day)} event(s) scheduled for {target_date}")

        # DEBUG: Check if SCHEDULE_RELEASE is in the query results
        for evt in events_for_day:
            if evt.get('event_type') == 'SCHEDULE_RELEASE':
                print(f"[SCHEDULE_RELEASE_TRIGGERED] ✅ SCHEDULE_RELEASE event found in database query")
                print(f"[SCHEDULE_RELEASE_TRIGGERED]   Event ID: {evt.get('event_id')}")
                print(f"[SCHEDULE_RELEASE_TRIGGERED]   Event Data: {evt.get('data', {}).get('parameters', {})}")

        # Delegate to batch simulation method
        events_completed, phase_transitions, errors = self._simulate_event_batch(
            events_for_day,
            target_date
        )

        # Summary
        print(f"\n{'='*80}")
        print(f"DAY SIMULATION COMPLETE")
        print(f"{'='*80}")
        print(f"Events Completed: {len([e for e in events_completed if e.get('success', False)])}/{len(events_for_day)}")
        print(f"Current Phase: {self._get_current_phase_value()}")
        if phase_transitions:
            print(f"Phase Transitions: {len(phase_transitions)}")
        if errors:
            print(f"Errors: {len(errors)}")

        # Separate games from other events for backward compatibility
        games_played = [e for e in events_completed if e.get('event_type') == 'GAME']

        return {
            "date": str(target_date),
            "events_count": len(events_for_day),
            "events_completed": events_completed,
            "games_played": games_played,  # Backward compatibility with SeasonController
            "events_executed": events_completed,  # Alternative name for offseason events
            "phase_transitions": [self._transition_to_dict(t) for t in phase_transitions],
            "current_phase": self._get_current_phase_value(),
            "phase_info": self.calendar.get_phase_info(),
            "success": len(errors) == 0,
            "errors": errors
        }

    def _reconstruct_event(self, event_data: Dict[str, Any], event_type: str):
        """
        Reconstruct the appropriate event class from database data.

        Args:
            event_data: Event data from database
            event_type: Type of event to reconstruct

        Returns:
            Reconstructed event instance

        Raises:
            ValueError: If event type is unknown
        """
        if event_type == "GAME":
            return GameEvent.from_database(event_data)
        elif event_type == "FRANCHISE_TAG":
            return FranchiseTagEvent.from_database(event_data)
        elif event_type == "TRANSITION_TAG":
            return TransitionTagEvent.from_database(event_data)
        elif event_type == "PLAYER_RELEASE":
            return PlayerReleaseEvent.from_database(event_data)
        elif event_type == "CONTRACT_RESTRUCTURE":
            return ContractRestructureEvent.from_database(event_data)
        elif event_type == "UFA_SIGNING":
            return UFASigningEvent.from_database(event_data)
        elif event_type == "RFA_OFFER_SHEET":
            return RFAOfferSheetEvent.from_database(event_data)
        elif event_type == "DEADLINE":
            return DeadlineEvent.from_database(event_data)
        elif event_type == "SCHEDULE_RELEASE":
            # DEBUG: Confirm reconstruction
            print(f"[SCHEDULE_RELEASE_TRIGGERED] 🔧 Reconstructing SCHEDULE_RELEASE from database")
            print(f"[SCHEDULE_RELEASE_TRIGGERED]   Dynasty: {event_data.get('dynasty_id')}")
            print(f"[SCHEDULE_RELEASE_TRIGGERED]   Event ID: {event_data.get('event_id')}")
            # Top-level event type for schedule generation (promoted from nested MILESTONE)
            return ScheduleReleaseEvent.from_database(event_data)
        elif event_type == "MILESTONE":
            # Generic informational milestones (DRAFT, COMBINE, etc.)
            return MilestoneEvent.from_database(event_data)
        elif event_type == "WINDOW":
            return WindowEvent.from_database(event_data)
        else:
            raise ValueError(f"Unknown event type: {event_type}")

    def _create_event_summary(self, event, result: EventResult, event_type: str) -> Dict[str, Any]:
        """
        Create a summary dictionary for a completed event.

        Args:
            event: The event instance
            result: The simulation result
            event_type: Type of event

        Returns:
            Dictionary with event summary data
        """
        # Base summary for all events
        summary = {
            "event_id": event.get_game_id(),
            "event_type": event_type,
            "success": True
        }

        # Add type-specific details
        if event_type == "GAME":
            summary.update({
                "matchup": event.get_matchup_description(),
                "away_team_id": event.away_team_id,
                "home_team_id": event.home_team_id,
                "away_score": result.data.get("away_score", 0),
                "home_score": result.data.get("home_score", 0),
                "winner_id": result.data.get("winner_id"),
                "winner_name": result.data.get("winner_name"),
                "total_plays": result.data.get("total_plays", 0)
            })
        elif event_type in ["FRANCHISE_TAG", "TRANSITION_TAG"]:
            summary.update({
                "team_id": result.data.get("team_id"),
                "player_id": result.data.get("player_id"),
                "tag_salary": result.data.get("tag_salary"),
                "message": result.data.get("message")
            })
        elif event_type == "PLAYER_RELEASE":
            summary.update({
                "team_id": result.data.get("team_id"),
                "player_id": result.data.get("player_id"),
                "dead_money": result.data.get("dead_money"),
                "cap_savings": result.data.get("cap_savings"),
                "message": result.data.get("message")
            })
        elif event_type == "CONTRACT_RESTRUCTURE":
            summary.update({
                "team_id": result.data.get("team_id"),
                "player_id": result.data.get("player_id"),
                "cap_savings": result.data.get("cap_savings"),
                "message": result.data.get("message")
            })
        elif event_type in ["UFA_SIGNING", "RFA_OFFER_SHEET"]:
            summary.update({
                "team_id": result.data.get("team_id"),
                "player_id": result.data.get("player_id"),
                "contract_value": result.data.get("contract_value"),
                "message": result.data.get("message")
            })
        elif event_type == "DEADLINE":
            summary.update({
                "deadline_type": result.data.get("deadline_type"),
                "description": result.data.get("description"),
                "message": result.data.get("message")
            })
        else:
            # Generic handling for unknown event types
            summary.update({
                "message": result.data.get("message", "Event completed successfully")
            })

        return summary

    def _get_events_for_date(self, target_date: Date) -> List[Dict[str, Any]]:
        """
        Retrieve all events scheduled for a specific date.

        Filters events by dynasty for dynasty-specific events (playoff games, cap events)
        while keeping regular season games shared across all dynasties.

        Args:
            target_date: Date to retrieve events for

        Returns:
            List of event dictionaries from database
        """
        all_events_for_dynasty = []

        # Get playoff game events for this specific dynasty/season
        # Note: game_id format is "playoff_{season}_{round}_{number}"
        # Dynasty isolation is via dynasty_id column, not game_id
        all_playoff_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )
        playoff_events = [
            e for e in all_playoff_events
            if e.get('game_id', '').startswith(f'playoff_{self.season_year}_')
        ]
        all_events_for_dynasty.extend(playoff_events)

        # Get preseason game events for this specific dynasty/season (future-proofing)
        # Note: game_id format is "preseason_{season}_{week}_{number}"
        # Dynasty isolation is via dynasty_id column, not game_id
        all_preseason_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # During OFFSEASON, preseason games are for NEXT season (season_year + 1)
        # During PRESEASON/regular season, games are for current season
        phase_info = self.calendar.get_phase_info()
        current_phase = phase_info.get("current_phase", "").lower()

        # CRITICAL FIX #3: Always get season_year from PhaseState (single source of truth)
        # PhaseState.to_dict() now includes "season_year" key (added in Fix #1)
        # This eliminates unreliable fallback logic and stale cached values
        current_season_year = phase_info.get("season_year")

        if current_season_year is None:
            # Fallback only for legacy/test scenarios where PhaseState missing season_year
            current_date = self.calendar.get_current_date()
            current_season_year = current_date.year
            if self.verbose_logging:
                print(
                    f"[WARNING] PhaseState missing season_year, falling back to calendar year: {current_season_year}"
                )

        preseason_season = current_season_year + 1 if current_phase == "offseason" else current_season_year

        # DIAGNOSTIC LOGGING
        if self.verbose_logging:
            print(f"\n[GAME_QUERY] Querying games for date {target_date}")
            print(f"  Current phase: {current_phase}")
            print(f"  Season year (from PhaseState): {phase_info.get('season_year')}")
            print(f"  Preseason query year: {preseason_season}")
            print(f"  Query pattern: 'preseason_{preseason_season}_*'")

        preseason_events = [
            e for e in all_preseason_events
            if e.get('game_id', '').startswith(f'preseason_{preseason_season}_')
        ]
        all_events_for_dynasty.extend(preseason_events)

        # Get regular season game events for this specific dynasty
        # During OFFSEASON, regular season games are for NEXT year (e.g., game_2026*)
        # During regular season, games are for current year (e.g., game_2025*)
        regular_season_year = current_season_year + 1 if current_phase == "offseason" else current_season_year
        year_prefix = f"game_{regular_season_year}"

        # DIAGNOSTIC LOGGING
        if self.verbose_logging:
            print(f"  regular_season_year: {regular_season_year}")
            print(f"  year_prefix: '{year_prefix}'")

        # Use dynasty-filtered query for better performance
        all_game_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )
        regular_season_events = [
            e for e in all_game_events
            if not e.get('game_id', '').startswith('playoff_')
            and not e.get('game_id', '').startswith('preseason_')
            and e.get('game_id', '').startswith(year_prefix)
        ]

        # DIAGNOSTIC LOGGING
        if self.verbose_logging:
            print(f"  Total GAME events from DB: {len(all_game_events)}")
            print(f"  After filtering by prefix '{year_prefix}': {len([e for e in all_game_events if e.get('game_id', '').startswith(year_prefix)])}")
            print(f"  After all filters (regular_season_events): {len(regular_season_events)}")
            if len(all_game_events) > 0 and len(regular_season_events) == 0:
                sample_ids = [e.get('game_id', '')[:25] for e in all_game_events[:5]]
                print(f"  ❌ WARNING: 0 games found! Sample game_ids from DB: {sample_ids}")
            elif len(regular_season_events) > 0:
                sample_ids = [e.get('game_id', '')[:25] for e in regular_season_events[:3]]
                print(f"  ✅ Found games: {sample_ids}")

        all_events_for_dynasty.extend(regular_season_events)

        # Get cap-related events (franchise tags, releases, restructures, signings)
        cap_event_types = [
            "FRANCHISE_TAG", "TRANSITION_TAG", "PLAYER_RELEASE",
            "CONTRACT_RESTRUCTURE", "UFA_SIGNING", "RFA_OFFER_SHEET"
        ]
        for event_type in cap_event_types:
            # Cap events are dynasty-specific
            cap_events = self.event_db.get_events_by_type(event_type)
            # Filter by dynasty_id in parameters
            dynasty_cap_events = [
                e for e in cap_events
                if e['data'].get('parameters', {}).get('dynasty_id', 'default') == self.dynasty_id
            ]
            all_events_for_dynasty.extend(dynasty_cap_events)

        # Get deadline events (dynasty-specific)
        deadline_events = self.event_db.get_events_by_type("DEADLINE")
        dynasty_deadline_events = [
            e for e in deadline_events
            if e['data'].get('parameters', {}).get('dynasty_id', 'default') == self.dynasty_id
        ]
        all_events_for_dynasty.extend(dynasty_deadline_events)

        # Get schedule release events (dynasty-specific)
        schedule_release_events = self.event_db.get_events_by_type("SCHEDULE_RELEASE")
        dynasty_schedule_release_events = [
            e for e in schedule_release_events
            if e.get('dynasty_id') == self.dynasty_id
        ]

        # DIAGNOSTIC LOGGING for SCHEDULE_RELEASE
        if self.verbose_logging:
            print(f"  [SCHEDULE_RELEASE] Total from DB: {len(schedule_release_events)}")
            print(f"  [SCHEDULE_RELEASE] After dynasty filter ('{self.dynasty_id}'): {len(dynasty_schedule_release_events)}")
            if len(schedule_release_events) > 0:
                for i, evt in enumerate(schedule_release_events[:3], 1):
                    evt_dynasty = evt.get('dynasty_id', 'MISSING')
                    evt_date = evt['data'].get('parameters', {}).get('event_date', 'NO_DATE')
                    print(f"    Sample {i}: dynasty_id='{evt_dynasty}', event_date='{evt_date}'")

        all_events_for_dynasty.extend(dynasty_schedule_release_events)

        # Get window events (dynasty-specific)
        window_events = self.event_db.get_events_by_type("WINDOW")
        dynasty_window_events = [
            e for e in window_events
            if e.get('dynasty_id') == self.dynasty_id
        ]
        all_events_for_dynasty.extend(dynasty_window_events)

        # Get milestone events (dynasty-specific)
        milestone_events = self.event_db.get_events_by_type("MILESTONE")
        dynasty_milestone_events = [
            e for e in milestone_events
            if e.get('dynasty_id') == self.dynasty_id
        ]
        all_events_for_dynasty.extend(dynasty_milestone_events)

        # Filter by date
        events_for_date = []
        target_date_str = str(target_date)

        # DIAGNOSTIC LOGGING for date filtering
        if self.verbose_logging:
            print(f"  [DATE_FILTER] Target date: '{target_date_str}'")
            print(f"  [DATE_FILTER] Events to filter: {len(all_events_for_dynasty)}")

        for event_data in all_events_for_dynasty:
            # Check if event_date/game_date in parameters matches target date
            params = event_data['data'].get('parameters', event_data['data'])
            # Try both 'game_date' (for games) and 'event_date' (for other events)
            date_str = params.get('game_date') or params.get('event_date', '')

            # Extract just the date part (YYYY-MM-DD) from ISO datetime string
            if 'T' in date_str:
                date_part = date_str.split('T')[0]
            else:
                date_part = date_str[:10] if len(date_str) >= 10 else date_str

            # DIAGNOSTIC: Log SCHEDULE_RELEASE events specifically
            if self.verbose_logging and event_data.get('event_type') == 'SCHEDULE_RELEASE':
                print(f"  [DATE_FILTER] SCHEDULE_RELEASE: date_str='{date_str}', date_part='{date_part}', match={date_part == target_date_str}")

            if date_part == target_date_str:
                events_for_date.append(event_data)

        # DEDUPLICATION: Remove duplicate event_ids (keep first occurrence)
        # This prevents the same event from being simulated multiple times if
        # it was accidentally inserted into the events table more than once
        seen_event_ids = set()
        deduplicated_events = []
        duplicates_removed = 0

        for event_data in events_for_date:
            event_id = event_data.get('event_id', '') or event_data.get('game_id', '')
            if event_id and event_id not in seen_event_ids:
                seen_event_ids.add(event_id)
                deduplicated_events.append(event_data)
            elif event_id in seen_event_ids:
                duplicates_removed += 1

        if duplicates_removed > 0:
            print(f"⚠️  Removed {duplicates_removed} duplicate event(s) for {target_date}")

        # DIAGNOSTIC LOGGING
        if self.verbose_logging:
            print(f"  → Returning {len(deduplicated_events)} events for {target_date}")
            if len(deduplicated_events) > 0:
                event_types = [e.get('event_type', 'UNKNOWN') for e in deduplicated_events]
                print(f"     Event types: {event_types}")

        return deduplicated_events

    def _record_game_completion(self, game_event: GameEvent, result: EventResult) -> Optional[PhaseTransition]:
        """
        Record game completion in the calendar's phase tracker.

        Args:
            game_event: The completed game event
            result: The game simulation result

        Returns:
            PhaseTransition if a transition was triggered, None otherwise
        """
        # Create GameCompletionEvent for phase tracker
        completion_event = GameCompletionEvent(
            game_id=game_event.get_game_id(),
            home_team_id=game_event.home_team_id,
            away_team_id=game_event.away_team_id,
            completion_date=self.calendar.get_current_date(),
            completion_time=game_event.game_date,
            week=game_event.week,
            game_type=self._map_season_type_to_game_type(game_event.season_type),
            season_year=game_event.season
        )

        # Record in calendar's phase tracker
        transition = self.calendar.record_game_completion(completion_event)

        return transition

    def _map_season_type_to_game_type(self, season_type: str) -> str:
        """
        Map season_type to game_type for phase tracker.

        Args:
            season_type: Season type from GameEvent (regular_season, playoffs, preseason)

        Returns:
            Game type for phase tracker
        """
        mapping = {
            "preseason": "preseason",
            "regular_season": "regular",
            "playoffs": "wildcard"  # Default to wildcard, would need more info for specific round
        }
        return mapping.get(season_type, "regular")

    def _transition_to_dict(self, transition: PhaseTransition) -> Dict[str, Any]:
        """Convert PhaseTransition to dictionary for serialization."""
        return {
            "transition_type": transition.transition_type.value,
            "from_phase": transition.from_phase.value if transition.from_phase else None,
            "to_phase": transition.to_phase.value,
            "trigger_date": str(transition.trigger_date),
            "metadata": transition.metadata
        }

    def get_current_date(self) -> Date:
        """Get current date from src.calendar."""
        return self.calendar.get_current_date()

    def advance_calendar(self, days: int) -> Date:
        """
        Advance calendar by specified days.

        Args:
            days: Number of days to advance

        Returns:
            New current date
        """
        result = self.calendar.advance(days)
        return result.end_date

    def get_phase_info(self) -> Dict[str, Any]:
        """Get comprehensive phase information from src.calendar."""
        return self.calendar.get_phase_info()

    def _get_current_phase_value(self) -> str:
        """Get current phase value for reporting."""
        if self.phase_state:
            return self.phase_state.phase.value
        return self.calendar.get_current_phase().value
