"""
Milestone Event

Marks informational milestones in the NFL offseason (Super Bowl completion, Combine dates, etc.).
These are purely informational events with no executable logic.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


class MilestoneEvent(BaseEvent):
    """
    Lightweight event marking an NFL offseason milestone.

    Milestones are significant dates that don't require execution logic
    but are important for tracking the offseason timeline:
    - Super Bowl completion
    - Pro Bowl date
    - NFL Combine dates
    - League meetings
    - Schedule release
    - Hall of Fame induction

    These events provide context and help with phase tracking.
    """

    def __init__(
        self,
        milestone_type: str,
        description: str,
        season_year: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize milestone event.

        Args:
            milestone_type: Type of milestone (SUPER_BOWL, COMBINE, etc.)
            description: Human-readable description
            season_year: NFL season year
            event_date: Date when milestone occurs
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier (generated if not provided)
            metadata: Optional additional context (e.g., Super Bowl winner)
        """
        # Convert Date to datetime for BaseEvent
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.milestone_type = milestone_type
        self.description = description
        self.season_year = season_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.milestone_metadata = metadata or {}

    def get_event_type(self) -> str:
        """Return event type identifier."""
        return "MILESTONE"

    def simulate(self) -> EventResult:
        """
        Execute milestone event (informational only - no business logic).

        Returns:
            EventResult with success=True and milestone metadata
        """
        # Milestone events are purely informational
        # They mark significant dates but don't execute logic

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "milestone_type": self.milestone_type,
                "description": self.description,
                "season_year": self.season_year,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "metadata": self.milestone_metadata,
                "message": f"Milestone reached: {self.description}"
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        """Return parameters for event recreation."""
        return {
            "milestone_type": self.milestone_type,
            "description": self.description,
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "metadata": self.milestone_metadata
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """Return milestone-specific metadata."""
        return self.milestone_metadata

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate milestone event can execute.

        Returns:
            (True, None) - milestones always valid (just markers)
        """
        # Milestone events are always valid - they're informational only
        return (True, None)

    def get_game_id(self) -> str:
        """
        Return unique identifier for this milestone.

        Format: milestone_{season_year}_{milestone_type}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"milestone_{self.season_year}_{self.milestone_type}"

    def __str__(self) -> str:
        """String representation."""
        return f"MilestoneEvent({self.milestone_type} on {self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"MilestoneEvent(milestone_type='{self.milestone_type}', "
            f"event_date={self.event_date}, season_year={self.season_year})"
        )

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'MilestoneEvent':
        """
        Reconstruct MilestoneEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI with:
                - dynasty_id: At top level (from events table column)
                - data: Nested dict with parameters/results/metadata

        Returns:
            Reconstructed MilestoneEvent instance
        """
        data = event_data['data']

        # Handle three-part structure (parameters/results/metadata)
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        # Dynasty ID from top-level event_data (events.dynasty_id column)
        dynasty_id = event_data.get('dynasty_id', params.get('dynasty_id', 'default'))

        # Parse event_date from string
        event_date_str = params.get('event_date', '')
        event_date_parts = event_date_str.split('-')
        event_date = Date(int(event_date_parts[0]), int(event_date_parts[1]), int(event_date_parts[2]))

        return cls(
            milestone_type=params.get('milestone_type', 'UNKNOWN'),
            description=params.get('description', ''),
            season_year=params.get('season_year', 2025),
            event_date=event_date,
            dynasty_id=dynasty_id,
            event_id=event_data.get('event_id'),
            metadata=params.get('metadata')
        )


# Common milestone type constants for convenience
class MilestoneType:
    """Common NFL offseason milestone types."""
    SUPER_BOWL = "SUPER_BOWL"
    PRO_BOWL = "PRO_BOWL"
    COMBINE_START = "COMBINE_START"
    COMBINE_END = "COMBINE_END"
    LEAGUE_MEETINGS = "LEAGUE_MEETINGS"
    SCHEDULE_RELEASE = "SCHEDULE_RELEASE"
    HALL_OF_FAME_INDUCTION = "HALL_OF_FAME_INDUCTION"
    DRAFT_ORDER_FINALIZED = "DRAFT_ORDER_FINALIZED"
    COMP_PICKS_AWARDED = "COMP_PICKS_AWARDED"
