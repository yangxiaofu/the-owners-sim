"""
Season Phase Tracker

Event-driven season phase management that follows actual NFL game completions
rather than fixed calendar dates. Tracks game results to automatically transition
between season phases based on real events.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import threading

from .date_models import Date
from .calendar_exceptions import CalendarStateException


class SeasonPhase(Enum):
    """NFL season phases based on actual game completion status."""
    PRESEASON = "preseason"
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"
    OFFSEASON = "offseason"


class TransitionType(Enum):
    """Types of phase transitions that can occur."""
    SEASON_START = "season_start"
    REGULAR_SEASON_START = "regular_season_start"
    PLAYOFFS_START = "playoffs_start"
    OFFSEASON_START = "offseason_start"
    PHASE_ROLLOVER = "phase_rollover"


@dataclass(frozen=True)
class GameCompletionEvent:
    """Represents a completed NFL game that may trigger phase transitions."""
    game_id: str
    home_team_id: int
    away_team_id: int
    completion_date: Date
    completion_time: datetime
    week: int
    game_type: str  # "preseason", "regular", "wildcard", "divisional", "conference", "super_bowl"
    season_year: int


@dataclass(frozen=True)
class PhaseTransition:
    """Represents a transition between season phases."""
    transition_type: TransitionType
    from_phase: Optional[SeasonPhase]
    to_phase: SeasonPhase
    trigger_date: Date
    trigger_event: Optional[GameCompletionEvent]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeasonPhaseState:
    """Current state of the season phase tracker."""
    current_phase: SeasonPhase
    phase_start_date: Date
    season_year: int
    completed_games: List[GameCompletionEvent] = field(default_factory=list)
    phase_metadata: Dict[str, Any] = field(default_factory=dict)
    transition_history: List[PhaseTransition] = field(default_factory=list)


class SeasonPhaseTracker:
    """
    Event-driven season phase tracker that monitors game completions
    and automatically transitions between NFL season phases.
    """

    # NFL Season Constants
    REGULAR_SEASON_GAMES_PER_TEAM = 17
    TOTAL_NFL_TEAMS = 32
    TOTAL_REGULAR_SEASON_GAMES = (TOTAL_NFL_TEAMS * REGULAR_SEASON_GAMES_PER_TEAM) // 2  # 272 games

    PLAYOFF_GAMES_BY_ROUND = {
        "wildcard": 6,      # 3 games per conference
        "divisional": 4,    # 2 games per conference
        "conference": 2,    # 1 game per conference
        "super_bowl": 1     # 1 championship game
    }

    TOTAL_PLAYOFF_GAMES = sum(PLAYOFF_GAMES_BY_ROUND.values())  # 13 games

    def __init__(self, initial_date: Date, season_year: int):
        """
        Initialize season phase tracker.

        Args:
            initial_date: Starting date for phase tracking
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
        """
        self._lock = threading.Lock()

        # Initialize state
        self._state = SeasonPhaseState(
            current_phase=SeasonPhase.OFFSEASON,  # Default to offseason
            phase_start_date=initial_date,
            season_year=season_year
        )

        # Event listeners for phase transitions
        self._transition_listeners: List[Callable[[PhaseTransition], None]] = []

        # Game completion tracking
        self._games_by_type: Dict[str, List[GameCompletionEvent]] = {
            "preseason": [],
            "regular": [],
            "wildcard": [],
            "divisional": [],
            "conference": [],
            "super_bowl": []
        }

    def add_transition_listener(self, listener: Callable[[PhaseTransition], None]) -> None:
        """Add a listener for phase transition events."""
        with self._lock:
            self._transition_listeners.append(listener)

    def remove_transition_listener(self, listener: Callable[[PhaseTransition], None]) -> None:
        """Remove a phase transition listener."""
        with self._lock:
            if listener in self._transition_listeners:
                self._transition_listeners.remove(listener)

    def record_game_completion(self, game_event: GameCompletionEvent) -> Optional[PhaseTransition]:
        """
        Record a completed game and check for phase transitions.

        Args:
            game_event: The completed game event

        Returns:
            PhaseTransition if a transition was triggered, None otherwise

        Raises:
            CalendarStateException: If game data is invalid
        """
        with self._lock:
            try:
                # Validate game event
                self._validate_game_event(game_event)

                # Record the game
                self._state.completed_games.append(game_event)
                self._games_by_type[game_event.game_type].append(game_event)

                # Check for phase transitions
                transition = self._check_phase_transition(game_event)

                if transition:
                    self._execute_transition(transition)

                return transition

            except Exception as e:
                raise CalendarStateException(
                    f"Failed to record game completion: {e}",
                    state_info={
                        "current_phase": str(self._state.current_phase),
                        "completed_games_count": len(self._state.completed_games),
                        "game_id": game_event.game_id if game_event else None
                    }
                )

    def get_current_phase(self) -> SeasonPhase:
        """Get the current season phase."""
        with self._lock:
            return self._state.current_phase

    def get_phase_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current phase."""
        with self._lock:
            regular_games = len(self._games_by_type["regular"])
            playoff_games = sum(len(games) for game_type, games in self._games_by_type.items()
                              if game_type in ["wildcard", "divisional", "conference", "super_bowl"])

            return {
                "current_phase": self._state.current_phase.value,
                "phase_start_date": str(self._state.phase_start_date),
                "season_year": self._state.season_year,
                "days_in_current_phase": self._calculate_days_in_phase(),
                "completed_games_total": len(self._state.completed_games),
                "completed_regular_season_games": regular_games,
                "completed_playoff_games": playoff_games,
                "regular_season_completion_percentage": (regular_games / self.TOTAL_REGULAR_SEASON_GAMES) * 100,
                "next_transition_trigger": self._get_next_transition_trigger(),
                "phase_metadata": self._state.phase_metadata.copy()
            }

    def get_games_completed_by_type(self, game_type: str) -> List[GameCompletionEvent]:
        """Get all completed games of a specific type."""
        with self._lock:
            return self._games_by_type.get(game_type, []).copy()

    def get_transition_history(self) -> List[PhaseTransition]:
        """Get the history of all phase transitions."""
        with self._lock:
            return self._state.transition_history.copy()

    def is_phase_transition_pending(self) -> bool:
        """Check if a phase transition is likely to occur soon."""
        with self._lock:
            current_phase = self._state.current_phase

            if current_phase == SeasonPhase.REGULAR_SEASON:
                regular_games = len(self._games_by_type["regular"])
                # Transition pending if 95% of regular season games are complete
                return regular_games >= (self.TOTAL_REGULAR_SEASON_GAMES * 0.95)

            elif current_phase == SeasonPhase.PLAYOFFS:
                playoff_games = sum(len(games) for game_type, games in self._games_by_type.items()
                                  if game_type in ["wildcard", "divisional", "conference"])
                # Transition pending if conference championships are complete
                return len(self._games_by_type["conference"]) == 2

            return False

    def force_phase_transition(self, to_phase: SeasonPhase, trigger_date: Date,
                              metadata: Optional[Dict[str, Any]] = None) -> PhaseTransition:
        """
        Force a phase transition (for testing or manual control).

        Args:
            to_phase: Phase to transition to
            trigger_date: Date of the transition
            metadata: Optional metadata for the transition

        Returns:
            The transition that was executed
        """
        with self._lock:
            transition = PhaseTransition(
                transition_type=TransitionType.PHASE_ROLLOVER,
                from_phase=self._state.current_phase,
                to_phase=to_phase,
                trigger_date=trigger_date,
                trigger_event=None,
                metadata=metadata or {}
            )

            self._execute_transition(transition)
            return transition

    def reset_season(self, new_season_year: int, start_date: Date) -> None:
        """
        Reset the tracker for a new season.

        Args:
            new_season_year: The new season year
            start_date: Starting date for the new season
        """
        with self._lock:
            self._state = SeasonPhaseState(
                current_phase=SeasonPhase.OFFSEASON,
                phase_start_date=start_date,
                season_year=new_season_year
            )

            # Clear game tracking
            for game_type in self._games_by_type:
                self._games_by_type[game_type].clear()

    def _validate_game_event(self, game_event: GameCompletionEvent) -> None:
        """Validate a game completion event."""
        if not game_event.game_id:
            raise ValueError("Game event must have a valid game_id")

        if game_event.game_type not in self._games_by_type:
            raise ValueError(f"Invalid game_type: {game_event.game_type}")

        if game_event.season_year != self._state.season_year:
            raise ValueError(f"Game season year {game_event.season_year} doesn't match tracker year {self._state.season_year}")

    def _check_phase_transition(self, game_event: GameCompletionEvent) -> Optional[PhaseTransition]:
        """Check if the completed game should trigger a phase transition."""
        current_phase = self._state.current_phase

        # Offseason to Preseason
        if (current_phase == SeasonPhase.OFFSEASON and
            game_event.game_type == "preseason"):
            return PhaseTransition(
                transition_type=TransitionType.SEASON_START,
                from_phase=current_phase,
                to_phase=SeasonPhase.PRESEASON,
                trigger_date=game_event.completion_date,
                trigger_event=game_event,
                metadata={"trigger": "first_preseason_game"}
            )

        # Preseason to Regular Season
        elif (current_phase == SeasonPhase.PRESEASON and
              game_event.game_type == "regular" and
              game_event.week == 1):
            return PhaseTransition(
                transition_type=TransitionType.REGULAR_SEASON_START,
                from_phase=current_phase,
                to_phase=SeasonPhase.REGULAR_SEASON,
                trigger_date=game_event.completion_date,
                trigger_event=game_event,
                metadata={"trigger": "first_regular_season_game"}
            )

        # Regular Season to Playoffs
        elif (current_phase == SeasonPhase.REGULAR_SEASON and
              self._is_regular_season_complete()):
            return PhaseTransition(
                transition_type=TransitionType.PLAYOFFS_START,
                from_phase=current_phase,
                to_phase=SeasonPhase.PLAYOFFS,
                trigger_date=game_event.completion_date,
                trigger_event=game_event,
                metadata={
                    "trigger": "regular_season_complete",
                    "total_regular_games": len(self._games_by_type["regular"])
                }
            )

        # Playoffs to Offseason
        elif (current_phase == SeasonPhase.PLAYOFFS and
              game_event.game_type == "super_bowl"):
            return PhaseTransition(
                transition_type=TransitionType.OFFSEASON_START,
                from_phase=current_phase,
                to_phase=SeasonPhase.OFFSEASON,
                trigger_date=game_event.completion_date,
                trigger_event=game_event,
                metadata={"trigger": "super_bowl_complete"}
            )

        return None

    def _is_regular_season_complete(self) -> bool:
        """Check if all regular season games have been completed."""
        return len(self._games_by_type["regular"]) >= self.TOTAL_REGULAR_SEASON_GAMES

    def _execute_transition(self, transition: PhaseTransition) -> None:
        """Execute a phase transition and notify listeners."""
        # Update state
        self._state.current_phase = transition.to_phase
        self._state.phase_start_date = transition.trigger_date
        self._state.transition_history.append(transition)

        # Update phase metadata
        self._state.phase_metadata = transition.metadata.copy()

        # Notify listeners
        for listener in self._transition_listeners:
            try:
                listener(transition)
            except Exception:
                # Don't let listener errors break the transition
                pass

    def _calculate_days_in_phase(self) -> int:
        """Calculate how many days have passed in the current phase."""
        # This would need the current date from the calendar component
        # For now, return 0 as a placeholder
        return 0

    def _get_next_transition_trigger(self) -> str:
        """Get a description of what will trigger the next phase transition."""
        current_phase = self._state.current_phase

        if current_phase == SeasonPhase.OFFSEASON:
            return "First preseason game kickoff"
        elif current_phase == SeasonPhase.PRESEASON:
            return "First regular season game (Week 1)"
        elif current_phase == SeasonPhase.REGULAR_SEASON:
            remaining_games = self.TOTAL_REGULAR_SEASON_GAMES - len(self._games_by_type["regular"])
            return f"Completion of remaining {remaining_games} regular season games"
        elif current_phase == SeasonPhase.PLAYOFFS:
            if len(self._games_by_type["super_bowl"]) == 0:
                return "Super Bowl completion"
            else:
                return "Season complete"

        return "Unknown"

    def __str__(self) -> str:
        """String representation of the tracker."""
        with self._lock:
            return (f"SeasonPhaseTracker(phase={self._state.current_phase.value}, "
                   f"year={self._state.season_year}, "
                   f"games_completed={len(self._state.completed_games)})")

    def __repr__(self) -> str:
        """Developer representation of the tracker."""
        return str(self)