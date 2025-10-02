"""
Simulation Executor

Executes daily NFL simulation by coordinating calendar, events, and game simulation.

This component orchestrates the daily simulation workflow by:
1. Getting the current date from the calendar
2. Retrieving scheduled events for that date from the events database
3. Executing each event (simulating games)
4. Recording game completions for phase tracking
5. Returning a summary of results

This is the execution layer that sits between SeasonManager (high-level API)
and the individual game simulation components.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from calendar.calendar_component import CalendarComponent
from calendar.season_phase_tracker import GameCompletionEvent, PhaseTransition
from calendar.date_models import Date
from events import EventDatabaseAPI, GameEvent, EventResult


class SimulationExecutor:
    """
    Executes daily simulation workflow.

    Orchestrates the interaction between:
    - CalendarComponent (date/time management)
    - EventDatabaseAPI (event storage/retrieval)
    - GameEvent (individual game simulation)
    - SeasonPhaseTracker (phase management via calendar)

    This component is used by SeasonManager to execute scheduled events
    and can be used standalone for testing or demos.
    """

    def __init__(self, calendar: CalendarComponent, event_db: EventDatabaseAPI):
        """
        Initialize simulation executor.

        Args:
            calendar: Calendar component for date management
            event_db: Event database API for event storage/retrieval
        """
        self.calendar = calendar
        self.event_db = event_db

    def simulate_day(self, target_date: Optional[Date] = None) -> Dict[str, Any]:
        """
        Simulate all events for a specific day.

        Args:
            target_date: Date to simulate (uses calendar's current date if None)

        Returns:
            Dictionary with simulation results:
            {
                "date": str,
                "games_count": int,
                "games_played": List[Dict],
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
                "games_count": 0,
                "games_played": [],
                "phase_transitions": [],
                "current_phase": self.calendar.get_current_phase().value,
                "success": True,
                "message": "No events scheduled for this day"
            }

        print(f"\n📅 Found {len(events_for_day)} event(s) scheduled for {target_date}")

        # Simulate each event
        games_played = []
        phase_transitions = []
        errors = []

        for i, event_data in enumerate(events_for_day, 1):
            try:
                print(f"\n{'─'*80}")
                print(f"Event {i}/{len(events_for_day)}")

                # Reconstruct GameEvent from database
                game_event = GameEvent.from_database(event_data)

                # Validate preconditions
                is_valid, error_msg = game_event.validate_preconditions()
                if not is_valid:
                    errors.append(f"Game {game_event.get_game_id()}: Validation failed - {error_msg}")
                    continue

                # Simulate the game
                result = game_event.simulate()

                # Record game completion in phase tracker
                if result.success:
                    transition = self._record_game_completion(game_event, result)
                    if transition:
                        phase_transitions.append(transition)
                        print(f"\n🔄 PHASE TRANSITION: {transition.from_phase.value} → {transition.to_phase.value}")

                    # Store result summary
                    games_played.append({
                        "game_id": game_event.get_game_id(),
                        "matchup": game_event.get_matchup_description(),
                        "away_team_id": game_event.away_team_id,
                        "home_team_id": game_event.home_team_id,
                        "away_score": result.data.get("away_score", 0),
                        "home_score": result.data.get("home_score", 0),
                        "winner_id": result.data.get("winner_id"),
                        "winner_name": result.data.get("winner_name"),
                        "total_plays": result.data.get("total_plays", 0),
                        "success": True
                    })

                    # Update event in database with results
                    self.event_db.update_event(game_event)
                else:
                    errors.append(f"Game {game_event.get_game_id()}: Simulation failed - {result.error_message}")
                    games_played.append({
                        "game_id": game_event.get_game_id(),
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
        print(f"Games Played: {len([g for g in games_played if g.get('success', False)])}/{len(events_for_day)}")
        print(f"Current Phase: {self.calendar.get_current_phase().value}")
        if phase_transitions:
            print(f"Phase Transitions: {len(phase_transitions)}")
        if errors:
            print(f"Errors: {len(errors)}")

        return {
            "date": str(target_date),
            "games_count": len(events_for_day),
            "games_played": games_played,
            "phase_transitions": [self._transition_to_dict(t) for t in phase_transitions],
            "current_phase": self.calendar.get_current_phase().value,
            "phase_info": self.calendar.get_phase_info(),
            "success": len(errors) == 0,
            "errors": errors
        }

    def _get_events_for_date(self, target_date: Date) -> List[Dict[str, Any]]:
        """
        Retrieve all events scheduled for a specific date.

        Args:
            target_date: Date to retrieve events for

        Returns:
            List of event dictionaries from database
        """
        # Get all GAME events from database
        all_game_events = self.event_db.get_events_by_type("GAME")

        # Filter by date
        events_for_date = []
        target_date_str = str(target_date)

        for event_data in all_game_events:
            # Check if game_date in parameters matches target date
            params = event_data['data'].get('parameters', event_data['data'])
            game_date_str = params.get('game_date', '')

            # Extract just the date part (YYYY-MM-DD) from ISO datetime string
            if 'T' in game_date_str:
                game_date_part = game_date_str.split('T')[0]
            else:
                game_date_part = game_date_str[:10] if len(game_date_str) >= 10 else game_date_str

            if game_date_part == target_date_str:
                events_for_date.append(event_data)

        return events_for_date

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
