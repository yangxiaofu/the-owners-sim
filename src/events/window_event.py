"""
Window Event

Marks the start/end of NFL offseason time windows (Legal Tampering, Free Agency, etc.).
These events track when specific phases of the offseason begin and end.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date


class WindowEvent(BaseEvent):
    """
    Lightweight event marking the start or end of an NFL offseason window.

    Windows are time periods during which certain activities can occur:
    - Legal Tampering Period (2 days before Free Agency)
    - Free Agency Period (March - end of season)
    - Draft Preparation Window
    - OTA/Minicamp Windows
    - Training Camp Period

    Each window has a START and END event.
    """

    def __init__(
        self,
        window_name: str,
        window_type: str,  # "START" or "END"
        description: str,
        season_year: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None
    ):
        """
        Initialize window event.

        Args:
            window_name: Name of the window (LEGAL_TAMPERING, FREE_AGENCY, etc.)
            window_type: "START" or "END"
            description: Human-readable description
            season_year: NFL season year
            event_date: Date when window starts/ends
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier (generated if not provided)
        """
        # Convert Date to datetime for BaseEvent
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.window_name = window_name
        self.window_type = window_type
        self.description = description
        self.season_year = season_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id

        # Validate window_type
        if window_type not in ["START", "END"]:
            raise ValueError(f"window_type must be 'START' or 'END', got: {window_type}")

    def get_event_type(self) -> str:
        """Return event type identifier."""
        return "WINDOW"

    def simulate(self) -> EventResult:
        """
        Execute window event (logs window opening/closing).

        Returns:
            EventResult with success=True and window state metadata
        """
        # Window events mark phase transitions in the offseason
        # Future: Could update global window state tracker here

        action = "opened" if self.window_type == "START" else "closed"
        message = f"{self.window_name} window {action}: {self.description}"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "window_name": self.window_name,
                "window_type": self.window_type,
                "description": self.description,
                "season_year": self.season_year,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message,
                "window_active": self.window_type == "START"
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        """Return parameters for event recreation."""
        return {
            "window_name": self.window_name,
            "window_type": self.window_type,
            "description": self.description,
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate window event can execute.

        Returns:
            (True, None) - window events always valid (just markers)
        """
        # Window events are always valid - they're just phase markers
        return (True, None)

    def get_game_id(self) -> str:
        """
        Return unique identifier for this window event.

        Format: window_{season_year}_{window_name}_{START|END}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"window_{self.season_year}_{self.window_name}_{self.window_type}"

    def __str__(self) -> str:
        """String representation."""
        return f"WindowEvent({self.window_name} {self.window_type} on {self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"WindowEvent(window_name='{self.window_name}', "
            f"window_type='{self.window_type}', event_date={self.event_date})"
        )


# Common window name constants for convenience
class WindowName:
    """Common NFL offseason window names."""
    LEGAL_TAMPERING = "LEGAL_TAMPERING"
    FREE_AGENCY = "FREE_AGENCY"
    DRAFT_PREPARATION = "DRAFT_PREPARATION"
    OTA_OFFSEASON = "OTA_OFFSEASON"
    MINICAMP = "MINICAMP"
    TRAINING_CAMP = "TRAINING_CAMP"
    PRESEASON = "PRESEASON"
    ROSTER_REDUCTION = "ROSTER_REDUCTION"
