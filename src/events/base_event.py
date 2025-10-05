"""
Base Event Interface

Abstract base class defining the contract for all simulation events.
All event types (GameEvent, MediaEvent, TradeEvent, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class EventResult:
    """
    Standardized result from any event execution.

    All events return this consistent structure after simulation,
    regardless of their specific implementation details.
    """
    event_id: str
    event_type: str
    success: bool
    timestamp: datetime
    data: Dict[str, Any]
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "error_message": self.error_message
        }


class BaseEvent(ABC):
    """
    Abstract base class for all simulation events.

    This interface ensures all events can be stored in the generic events table
    and retrieved polymorphically. Each event type implements its own simulation
    logic while adhering to this common interface.

    Design Pattern: Template Method + Strategy Pattern
    - Template: Common event lifecycle (validate -> simulate -> persist)
    - Strategy: Each event type implements its own simulation behavior
    """

    def __init__(
        self,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        dynasty_id: Optional[str] = None
    ):
        """
        Initialize base event properties.

        Args:
            event_id: Unique identifier (generated if not provided)
            timestamp: Event timestamp (defaults to now)
            dynasty_id: Dynasty identifier for isolation (REQUIRED for persistence)
        """
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        self.dynasty_id = dynasty_id

    @abstractmethod
    def get_event_type(self) -> str:
        """
        Return the event type identifier.

        This value is stored in the database and used to reconstruct
        the correct event class when loading from persistence.

        Examples: "GAME", "MEDIA", "TRADE", "INJURY", "DRAFT"

        Returns:
            String identifier for this event type
        """
        pass

    @abstractmethod
    def simulate(self) -> EventResult:
        """
        Execute the event and return standardized result.

        This is where the event's core behavior is implemented.
        - GameEvent: Runs FullGameSimulator
        - MediaEvent: Generates AI content
        - TradeEvent: Processes player/pick exchanges

        Returns:
            EventResult with success status and event-specific data
        """
        pass

    @abstractmethod
    def _get_parameters(self) -> Dict[str, Any]:
        """
        Return parameters needed to recreate/replay this event.

        These are the input values that define how to execute the event.
        Examples:
        - GameEvent: team_ids, week, date
        - TradeEvent: player_ids, teams involved
        - ScoutingEvent: scout_type, target_positions

        For events with no meaningful parameters (pure result events),
        return an empty dict or minimal context.

        Returns:
            Dictionary of parameters for event recreation
        """
        pass

    def _get_results(self) -> Optional[Dict[str, Any]]:
        """
        Return results after event simulation/execution.

        This is optional and should return None if the event hasn't
        been simulated yet. After simulation, return the outcomes.

        Examples:
        - GameEvent: scores, winner, statistics
        - ScoutingEvent: scouting reports (the primary value)
        - MediaEvent: generated article text

        For events stored before execution, this returns None.
        After execution, subclasses can cache results here.

        Returns:
            Dictionary of results, or None if not yet executed
        """
        return None

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Return additional event metadata/context.

        Optional supplementary information about the event that doesn't
        fit cleanly into parameters or results.

        Examples:
        - matchup_description, is_playoff_game, is_division_game
        - generated_by, ai_model_version
        - importance_score, fan_interest_level

        Returns:
            Dictionary of metadata (empty dict if no metadata)
        """
        return {}

    def to_database_format(self) -> Dict[str, Any]:
        """
        Convert event to database storage format using three-part structure.

        Uses a hybrid approach with three sections:
        1. parameters: Input values for replay/scheduling
        2. results: Output after simulation (optional, cached)
        3. metadata: Additional context

        This allows both:
        - Parameterized events (GameEvent) to be scheduled then simulated
        - Result events (ScoutingEvent) to store their output

        Returns:
            Dictionary matching EventDatabaseAPI schema with structured data:
            {
                "event_id": str,
                "event_type": str,
                "timestamp": datetime,
                "game_id": str,
                "dynasty_id": str,
                "data": {
                    "parameters": dict,
                    "results": dict | None,
                    "metadata": dict
                }
            }

        Raises:
            ValueError: If dynasty_id is not set (required for persistence)
        """
        if not self.dynasty_id:
            raise ValueError("dynasty_id is required for event persistence")

        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "timestamp": self.timestamp,
            "game_id": self.get_game_id(),
            "dynasty_id": self.dynasty_id,
            "data": {
                "parameters": self._get_parameters(),
                "results": self._get_results(),
                "metadata": self._get_metadata()
            }
        }

    @abstractmethod
    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that event can execute successfully.

        Check all prerequisites before attempting simulation:
        - Required data present and valid
        - Teams/players exist
        - Business rules satisfied

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error description") if invalid
        """
        pass

    def get_game_id(self) -> str:
        """
        Return the game/context ID this event belongs to.

        This groups related events together for retrieval.
        Default implementation can be overridden by subclasses.

        Returns:
            Game identifier string
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_game_id() or override default behavior"
        )

    def store_result(self, result: EventResult) -> None:
        """
        Store simulation result in the event for caching.

        This allows events to be simulated once, then the results cached
        for future retrieval without re-simulation.

        Subclasses should override _get_results() to return cached data.

        Args:
            result: EventResult from simulate() call
        """
        # Default implementation stores in protected attribute
        # Subclasses can override this behavior
        self._cached_result = result

    def __str__(self) -> str:
        """String representation of event"""
        return f"{self.get_event_type()}Event(id={self.event_id})"

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"{self.__class__.__name__}(event_id='{self.event_id}', timestamp={self.timestamp})"


@dataclass
class EventMetadata:
    """
    Optional metadata for events.

    Provides additional context that can be attached to any event type.
    """
    season: Optional[int] = None
    week: Optional[int] = None
    dynasty_id: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "season": self.season,
            "week": self.week,
            "dynasty_id": self.dynasty_id,
            "tags": self.tags,
            "notes": self.notes
        }
