"""
Deadline Event

Marks important NFL offseason deadlines (franchise tag deadline, RFA tender deadline, etc.).
These are marker events that trigger on specific dates but don't execute business logic.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date


class DeadlineEvent(BaseEvent):
    """
    Lightweight event marking an NFL offseason deadline.

    This event fires on specific dates to mark important league deadlines.
    It doesn't execute business logic - just provides a marker for when
    certain windows close or decisions must be made.

    Examples:
    - Franchise tag deadline (mid-March)
    - RFA tender deadline (mid-March)
    - Draft declaration deadline (mid-January)
    - Salary cap compliance deadline (mid-March)
    """

    def __init__(
        self,
        deadline_type: str,
        description: str,
        season_year: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize deadline event.

        Args:
            deadline_type: Type of deadline (FRANCHISE_TAG, RFA_TENDER, etc.)
            description: Human-readable description of the deadline
            season_year: NFL season year this deadline applies to
            event_date: Date when the deadline occurs
            event_id: Unique identifier (generated if not provided)
            dynasty_id: Dynasty context for this deadline
        """
        # Convert Date to datetime for BaseEvent
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.deadline_type = deadline_type
        self.description = description
        self.season_year = season_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        """Return event type identifier."""
        return "DEADLINE"

    def simulate(self) -> EventResult:
        """
        Execute deadline event (marker only - no business logic).

        Returns:
            EventResult with success=True and deadline metadata
        """
        # Deadline events are just markers - no execution needed
        # Business logic (if any) happens in response to the deadline
        # (e.g., AI deciding whether to use franchise tag before deadline)

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "deadline_type": self.deadline_type,
                "description": self.description,
                "season_year": self.season_year,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": f"Deadline reached: {self.description}"
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        """Return parameters for event recreation."""
        return {
            "deadline_type": self.deadline_type,
            "description": self.description,
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate deadline event can execute.

        Returns:
            (True, None) - deadlines always valid (just markers)
        """
        # Deadline events are always valid - they're just markers
        return (True, None)

    def get_game_id(self) -> str:
        """
        Return unique identifier for this deadline.

        Format: deadline_{dynasty_id}_{season_year}_{deadline_type}
        """
        return f"deadline_{self.dynasty_id}_{self.season_year}_{self.deadline_type}"

    def __str__(self) -> str:
        """String representation."""
        return f"DeadlineEvent({self.deadline_type} on {self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"DeadlineEvent(deadline_type='{self.deadline_type}', "
            f"event_date={self.event_date}, season_year={self.season_year})"
        )


# Common deadline type constants for convenience
class DeadlineType:
    """Common NFL offseason deadline types."""
    FRANCHISE_TAG = "FRANCHISE_TAG"
    TRANSITION_TAG = "TRANSITION_TAG"
    RFA_TENDER = "RFA_TENDER"
    DRAFT_DECLARATION = "DRAFT_DECLARATION"
    SALARY_CAP_COMPLIANCE = "SALARY_CAP_COMPLIANCE"
    JUNE_1_RELEASES = "JUNE_1_RELEASES"
    ROOKIE_CONTRACT_SIGNING = "ROOKIE_CONTRACT_SIGNING"
    FINAL_ROSTER_CUTS = "FINAL_ROSTER_CUTS"
