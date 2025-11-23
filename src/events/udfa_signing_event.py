"""
UDFA Signing Event

Undrafted free agent signing event.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


class UDFASigningEvent(BaseEvent):
    """
    Event for signing an undrafted free agent after the draft.

    Teams can sign undrafted players immediately after the draft concludes.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        player_name: str,
        position: str,
        college: str,
        signing_bonus: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None
    ):
        """
        Initialize UDFA signing event.

        Args:
            team_id: Team signing the player (1-32)
            player_id: Unique ID for signed player
            player_name: Player's name
            position: Player's position
            college: Player's college
            signing_bonus: Signing bonus amount (typically small)
            event_date: Date of signing
            event_id: Unique identifier
            dynasty_id: Dynasty context for isolation
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.team_id = team_id
        self.player_id = player_id
        self.player_name = player_name
        self.position = position
        self.college = college
        self.signing_bonus = signing_bonus
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "UDFA_SIGNING"

    def simulate(self) -> EventResult:
        """Execute UDFA signing (placeholder)."""
        message = f"Team {self.team_id} signed UDFA {self.player_name} ({self.position}, {self.college}) with ${self.signing_bonus:,} bonus"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "player_name": self.player_name,
                "position": self.position,
                "college": self.college,
                "signing_bonus": self.signing_bonus,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "college": self.college,
            "signing_bonus": self.signing_bonus,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"udfa_signing_{self.team_id}_{self.player_id}_{self.event_date.year}"
