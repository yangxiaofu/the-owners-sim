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
        dynasty_id: str,
        event_id: Optional[str] = None,
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize deadline event.

        Args:
            deadline_type: Type of deadline (FRANCHISE_TAG, RFA_TENDER, etc.)
            description: Human-readable description of the deadline
            season_year: NFL season year this deadline applies to
            event_date: Date when the deadline occurs
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier (generated if not provided)
            database_path: Path to database for cap validation (default: data/database/nfl_simulation.db)
        """
        # Convert Date to datetime for BaseEvent
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.deadline_type = deadline_type
        self.description = description
        self.season_year = season_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        """Return event type identifier."""
        return "DEADLINE"

    def simulate(self) -> EventResult:
        """
        Execute deadline event with cap compliance checks.

        For SALARY_CAP_COMPLIANCE deadlines, performs full league-wide cap validation.
        For other deadlines, acts as a marker only.

        Returns:
            EventResult with success=True and deadline metadata
        """
        # Handle salary cap compliance deadline with full validation
        if self.deadline_type == DeadlineType.SALARY_CAP_COMPLIANCE:
            try:
                # Import cap system components
                from salary_cap.cap_validator import CapValidator

                # Initialize validator with database path
                validator = CapValidator(database_path=self.database_path)

                # Check all teams for cap compliance
                violations = []
                for team_id in range(1, 33):
                    is_compliant, message = validator.check_league_year_compliance(
                        team_id=team_id,
                        season=self.season_year,
                        dynasty_id=self.dynasty_id
                    )
                    if not is_compliant:
                        violations.append({
                            "team_id": team_id,
                            "violation": message
                        })

                compliant_teams = 32 - len(violations)

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
                        "violations": violations,
                        "compliant_teams": compliant_teams,
                        "total_teams": 32,
                        "message": f"Cap compliance check: {compliant_teams}/32 teams compliant"
                    }
                )

            except Exception as e:
                # If cap validation fails, return error but don't fail event
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,  # Event executes successfully even if validation has errors
                    timestamp=datetime.now(),
                    data={
                        "deadline_type": self.deadline_type,
                        "description": self.description,
                        "season_year": self.season_year,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "error": str(e),
                        "message": f"Deadline reached but cap validation failed: {str(e)}"
                    }
                )

        # Handle franchise tag deadline (marker only)
        elif self.deadline_type == DeadlineType.FRANCHISE_TAG:
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
                    "message": "Franchise tag deadline reached"
                }
            )

        # Handle RFA tender deadline (marker only)
        elif self.deadline_type == DeadlineType.RFA_TENDER:
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
                    "message": "RFA tender deadline reached"
                }
            )

        # Default handling for all other deadline types (marker only)
        else:
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
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
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

        Format: deadline_{season_year}_{deadline_type}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"deadline_{self.season_year}_{self.deadline_type}"

    def __str__(self) -> str:
        """String representation."""
        return f"DeadlineEvent({self.deadline_type} on {self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"DeadlineEvent(deadline_type='{self.deadline_type}', "
            f"event_date={self.event_date}, season_year={self.season_year})"
        )

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'DeadlineEvent':
        """
        Reconstruct DeadlineEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()
                Must contain 'dynasty_id' at top level (from events table column)

        Returns:
            Reconstructed DeadlineEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        # Dynasty ID comes from top-level event_data (events.dynasty_id column)
        dynasty_id = event_data.get('dynasty_id', params.get('dynasty_id', 'default'))

        return cls(
            deadline_type=params['deadline_type'],
            description=params['description'],
            season_year=params['season_year'],
            event_date=Date.from_string(params['event_date']),
            dynasty_id=dynasty_id,
            event_id=event_data['event_id'],
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
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
