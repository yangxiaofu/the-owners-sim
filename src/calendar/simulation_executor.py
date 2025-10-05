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

from typing import List, Dict, Any, Optional
from datetime import datetime
from calendar.calendar_component import CalendarComponent
from calendar.season_phase_tracker import GameCompletionEvent, PhaseTransition
from calendar.date_models import Date
from events import EventDatabaseAPI, GameEvent, EventResult
from events.contract_events import FranchiseTagEvent, TransitionTagEvent, PlayerReleaseEvent, ContractRestructureEvent
from events.free_agency_events import UFASigningEvent, RFAOfferSheetEvent
from events.deadline_event import DeadlineEvent
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
        season_year: Optional[int] = None
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
        """
        self.calendar = calendar
        self.event_db = event_db
        self.enable_persistence = enable_persistence
        self.dynasty_id = dynasty_id

        # Extract season year from calendar if not provided
        if season_year is None:
            phase_info = calendar.get_phase_info()
            self.season_year = phase_info.get("season_year", calendar.get_current_date().year)
        else:
            self.season_year = season_year

        # Initialize SimulationWorkflow for 3-stage simulation
        if enable_persistence:
            if not database_path:
                raise ValueError("database_path is required when enable_persistence=True")
            self.workflow = SimulationWorkflow.for_season(
                database_path=database_path,
                dynasty_id=dynasty_id
            )
        else:
            self.workflow = SimulationWorkflow.for_testing()

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
                "current_phase": self.calendar.get_current_phase().value,
                "success": True,
                "message": "No events scheduled for this day"
            }

        print(f"\n📅 Found {len(events_for_day)} event(s) scheduled for {target_date}")

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

                # Reconstruct appropriate event class based on type
                event = self._reconstruct_event(event_data, event_type)

                # Validate preconditions
                is_valid, error_msg = event.validate_preconditions()
                if not is_valid:
                    errors.append(f"Event {event.get_game_id()}: Validation failed - {error_msg}")
                    continue

                # Execute event (different handling for games vs other events)
                if event_type == "GAME":
                    # Games use workflow for statistics persistence
                    workflow_result = self.workflow.execute(event)
                    result = workflow_result.simulation_result
                else:
                    # Other events simulate directly (no workflow needed)
                    result = event.simulate()

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
                    errors.append(f"Event {event.get_game_id()}: Simulation failed - {result.error_message}")
                    events_completed.append({
                        "event_id": event.get_game_id(),
                        "event_type": event_type,
                        "success": False,
                        "error": result.error_message
                    })

            except Exception as e:
                error_msg = f"Event {i}: Unexpected error - {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

        # Summary
        print(f"\n{'='*80}")
        print(f"DAY SIMULATION COMPLETE")
        print(f"{'='*80}")
        print(f"Events Completed: {len([e for e in events_completed if e.get('success', False)])}/{len(events_for_day)}")
        print(f"Current Phase: {self.calendar.get_current_phase().value}")
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
            "current_phase": self.calendar.get_current_phase().value,
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
        playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
        playoff_events = self.event_db.get_events_by_game_id_prefix(
            playoff_prefix,
            event_type="GAME"
        )
        all_events_for_dynasty.extend(playoff_events)

        # Get preseason game events for this specific dynasty/season (future-proofing)
        preseason_prefix = f"preseason_{self.dynasty_id}_{self.season_year}_"
        preseason_events = self.event_db.get_events_by_game_id_prefix(
            preseason_prefix,
            event_type="GAME"
        )
        all_events_for_dynasty.extend(preseason_events)

        # Get ALL game events to extract regular season games (shared across dynasties)
        all_game_events = self.event_db.get_events_by_type("GAME")
        regular_season_events = [
            e for e in all_game_events
            if not e.get('game_id', '').startswith('playoff_')
            and not e.get('game_id', '').startswith('preseason_')
        ]
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

        # Filter by date
        events_for_date = []
        target_date_str = str(target_date)

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
            completion_time=datetime.now(),
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
        """Get current date from calendar."""
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
        """Get comprehensive phase information from calendar."""
        return self.calendar.get_phase_info()
