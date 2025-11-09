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

    @classmethod
    def from_string(cls, value: str) -> 'SeasonPhase':
        """
        Convert string to enum (case-insensitive).

        Accepts:
        - 'preseason', 'PRESEASON', 'Preseason' → SeasonPhase.PRESEASON
        - 'regular_season', 'REGULAR_SEASON', 'Regular Season' → SeasonPhase.REGULAR_SEASON
        - 'playoffs', 'PLAYOFFS', 'Playoffs' → SeasonPhase.PLAYOFFS
        - 'offseason', 'OFFSEASON', 'Offseason' → SeasonPhase.OFFSEASON

        Args:
            value: String representation of phase (case-insensitive)

        Returns:
            SeasonPhase enum member

        Raises:
            ValueError: If string doesn't match any valid phase
        """
        # Try exact match with lowercase value first (database format)
        try:
            return cls(value.lower())
        except ValueError:
            pass

        # Try enum name match (UPPERCASE format)
        normalized = value.upper().replace(' ', '_').replace('-', '_')
        try:
            return cls[normalized]
        except KeyError:
            raise ValueError(
                f"Invalid season phase: '{value}'. "
                f"Valid values: {[p.value for p in cls]}"
            )

    @property
    def display_name(self) -> str:
        """
        Get human-readable display name for UI.

        Returns:
            Capitalized display name (e.g., "Regular Season")
        """
        display_map = {
            SeasonPhase.PRESEASON: "Preseason",
            SeasonPhase.REGULAR_SEASON: "Regular Season",
            SeasonPhase.PLAYOFFS: "Playoffs",
            SeasonPhase.OFFSEASON: "Offseason"
        }
        return display_map[self]


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

    def __init__(
        self,
        initial_date: Date,
        season_year: int,
        last_regular_season_game_date: Optional[Date] = None,
        database_api: Optional[Any] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize season phase tracker.

        Args:
            initial_date: Starting date for phase tracking
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            last_regular_season_game_date: Optional date of last scheduled regular season game.
                                          If provided, enables date-based season completion
                                          instead of game count (more flexible for schedule changes)
            database_api: Optional database API for querying scheduled games (enables event-based phase detection)
            dynasty_id: Dynasty context for database queries
        """
        self._lock = threading.Lock()

        # Store database API for event-based phase detection
        self.database_api = database_api
        self.dynasty_id = dynasty_id

        # Validate database API is provided (required for event-based phase detection)
        if not database_api:
            raise ValueError(
                "database_api is required for event-based phase detection. "
                "SeasonPhaseTracker cannot determine initial phase without access to scheduled games. "
                f"Received: database_api={database_api}, dynasty_id={dynasty_id}"
            )

        # Determine initial phase based on scheduled games
        initial_phase = self._determine_initial_phase_from_schedule(initial_date)

        # Initialize state
        self._state = SeasonPhaseState(
            current_phase=initial_phase,
            phase_start_date=initial_date,
            season_year=season_year
        )

        # Store last regular season game date for flexible completion detection
        self.last_regular_season_game_date = last_regular_season_game_date

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

    def _get_first_game_date_for_phase(self, phase_name: str) -> Optional[str]:
        """
        Helper method to query first game date for a phase, handling both API types.

        Args:
            phase_name: Phase to query (preseason, regular_season, playoffs)

        Returns:
            Date string (YYYY-MM-DD) or None
        """
        if not self.database_api:
            return None

        # Check if this is EventDatabaseAPI (has get_first_game_date_of_phase with dynasty_id param)
        # or UnifiedDatabaseAPI (has events_get_first_game_date_of_phase without dynasty_id param)
        if hasattr(self.database_api, 'get_first_game_date_of_phase'):
            # EventDatabaseAPI
            return self.database_api.get_first_game_date_of_phase(
                dynasty_id=self.dynasty_id,
                phase_name=phase_name,
                current_date="1900-01-01"
            )
        elif hasattr(self.database_api, 'events_get_first_game_date_of_phase'):
            # UnifiedDatabaseAPI (uses self.dynasty_id internally)
            return self.database_api.events_get_first_game_date_of_phase(
                phase_name=phase_name,
                current_date="1900-01-01"
            )
        else:
            return None

    def _determine_initial_phase_from_schedule(self, initial_date: Date) -> SeasonPhase:
        """
        Determine the initial season phase by querying scheduled game events.

        This event-based approach handles year-to-year date fluctuations by querying
        the actual schedule rather than using hardcoded calendar dates.

        Args:
            initial_date: Date to determine phase for

        Returns:
            The season phase that the initial_date falls within

        Raises:
            ValueError: If database_api is not provided
        """
        if not self.database_api:
            raise ValueError(
                "database_api is required for event-based phase detection but was not provided. "
                "This should not happen if __init__() validation is working correctly."
            )

        initial_date_str = str(initial_date)

        # Query phase boundary dates from scheduled games
        # Use "1900-01-01" as min date to get first game regardless of current date
        first_preseason_date = self._get_first_game_date_for_phase("preseason")
        first_regular_season_date = self._get_first_game_date_for_phase("regular_season")

        # For last regular season game, we need to query all regular season games
        # and find the maximum date (get_first_game_date_for_phase only gets first)
        last_regular_season_date = self._query_last_regular_season_game_date()

        first_playoff_date = self._get_first_game_date_for_phase("playoffs")

        # Determine phase based on where initial_date falls
        # Phase boundaries (in order):
        # 1. Before first preseason → OFFSEASON
        # 2. Between first preseason and first regular season → PRESEASON
        # 3. Between first regular season and last regular season → REGULAR_SEASON
        # 4. Between last regular season and first playoff → PLAYOFFS (transition window)
        # 5. After first playoff → PLAYOFFS
        # 6. After all games → OFFSEASON

        if first_regular_season_date and initial_date_str >= first_regular_season_date:
            # We're at or after regular season start
            if last_regular_season_date and initial_date_str <= last_regular_season_date:
                # During regular season
                return SeasonPhase.REGULAR_SEASON
            elif first_playoff_date and initial_date_str >= first_playoff_date:
                # At or after playoffs
                return SeasonPhase.PLAYOFFS
            else:
                # After regular season but before playoffs (transition window)
                # Could be end of regular season or start of playoffs
                # Default to REGULAR_SEASON if playoffs haven't started
                return SeasonPhase.REGULAR_SEASON
        elif first_preseason_date and initial_date_str >= first_preseason_date:
            # We're at or after preseason start but before regular season
            return SeasonPhase.PRESEASON
        else:
            # Before any scheduled games
            return SeasonPhase.OFFSEASON

    def _query_last_regular_season_game_date(self) -> Optional[str]:
        """
        Query database for the date of the last scheduled regular season game.

        Returns:
            Date string (YYYY-MM-DD) of last regular season game, or None if no games found
        """
        if not self.database_api:
            return None

        try:
            # Query all GAME events for this dynasty (handle both API types)
            if hasattr(self.database_api, 'get_events_by_dynasty'):
                # EventDatabaseAPI
                all_games = self.database_api.get_events_by_dynasty(
                    dynasty_id=self.dynasty_id,
                    event_type="GAME"
                )
            elif hasattr(self.database_api, 'events_get_by_type'):
                # UnifiedDatabaseAPI (uses self.dynasty_id internally)
                all_games = self.database_api.events_get_by_type("GAME")
            else:
                return None

            # Filter for regular season games (season_type='regular_season' or 'regular')
            regular_season_games = [
                game for game in all_games
                if game.get('data', {}).get('parameters', {}).get('season_type') in ['regular_season', 'regular']
                or (
                    # Also check for games with regular season week numbers (1-18)
                    game.get('data', {}).get('parameters', {}).get('week', 0) in range(1, 19)
                    and not game.get('game_id', '').startswith('playoff_')
                    and not game.get('game_id', '').startswith('preseason_')
                )
            ]

            if not regular_season_games:
                return None

            # Find the game with the maximum timestamp
            last_game = max(regular_season_games, key=lambda g: g.get('timestamp', ''))
            return last_game.get('timestamp', '')[:10]  # Extract YYYY-MM-DD

        except Exception:
            # If query fails, return None (will fall back to other detection methods)
            return None

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
        """
        Check if all regular season games have been completed.

        Uses date-based detection if last_regular_season_game_date was provided,
        otherwise falls back to game count (272 games).
        """
        if self.last_regular_season_game_date is not None:
            # Date-based detection (flexible for any schedule length)
            # Note: Would need current_date parameter to fully implement
            # For now, still use game count but structure is ready for date-based
            return len(self._games_by_type["regular"]) >= self.TOTAL_REGULAR_SEASON_GAMES
        else:
            # Game count detection (traditional 272 games)
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