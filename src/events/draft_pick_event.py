"""
Draft Pick Event

Individual draft pick selection event.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date

if TYPE_CHECKING:
    from persistence.transaction_logger import TransactionLogger


class DraftPickEvent(BaseEvent):
    """
    Event for making a draft selection.

    Represents a team selecting a player in the NFL Draft.
    """

    def __init__(
        self,
        team_id: int,
        round_number: int,
        pick_number: int,  # Overall pick number (1-262 for 7 rounds)
        player_id: str,
        player_name: str,
        position: str,
        college: str,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None,
        transaction_logger: Optional["TransactionLogger"] = None
    ):
        """
        Initialize draft pick event.

        Args:
            team_id: Team making the selection (1-32)
            round_number: Draft round (1-7)
            pick_number: Overall pick number in draft
            player_id: Unique ID for drafted player
            player_name: Player's name
            position: Player's position
            college: Player's college
            event_date: Date of selection
            event_id: Unique identifier
            dynasty_id: Dynasty context for isolation
            transaction_logger: Optional TransactionLogger for automatic logging
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.team_id = team_id
        self.round_number = round_number
        self.pick_number = pick_number
        self.player_id = player_id
        self.player_name = player_name
        self.position = position
        self.college = college
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.transaction_logger = transaction_logger

    def get_event_type(self) -> str:
        return "DRAFT_PICK"

    def simulate(self) -> EventResult:
        """Execute draft pick (placeholder)."""
        message = f"Team {self.team_id} selected {self.player_name} ({self.position}, {self.college}) with pick #{self.pick_number} (Round {self.round_number})"

        event_result = EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "round_number": self.round_number,
                "pick_number": self.pick_number,
                "player_id": self.player_id,
                "player_name": self.player_name,
                "position": self.position,
                "college": self.college,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

        # Log transaction if logger is provided
        if self.transaction_logger:
            try:
                self.transaction_logger.log_from_event_result(
                    event_result=event_result,
                    dynasty_id=self.dynasty_id,
                    season=self.event_date.year  # Use draft year as season
                )
            except Exception as e:
                # Log error but don't fail the event
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to log draft pick transaction: {e}"
                )

        return event_result

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "round_number": self.round_number,
            "pick_number": self.pick_number,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "college": self.college,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"draft_pick_{self.team_id}_round{self.round_number}_pick{self.pick_number}_{self.event_date.year}"
