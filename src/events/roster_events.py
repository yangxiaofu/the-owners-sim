"""
Roster Events

Action events for NFL roster management during the offseason.
These include roster cuts, waiver claims, and practice squad moves.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


class RosterCutEvent(BaseEvent):
    """
    Event for cutting a player to reach roster limits.

    Teams must cut down to 53 players before the season starts,
    typically in multiple phases (75→53).
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        cut_type: str,  # "TO_75", "TO_53", "INJURY_SETTLEMENT", "MID_SEASON"
        reason: str,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize roster cut event.

        Args:
            team_id: Team making the cut (1-32)
            player_id: Player being cut
            cut_type: Type of cut (TO_75, TO_53, etc.)
            reason: Explanation (e.g., "Failed to make roster", "Injured")
            event_date: Date of cut
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
        self.cut_type = cut_type
        self.reason = reason
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "ROSTER_CUT"

    def simulate(self) -> EventResult:
        """Execute roster cut (placeholder)."""
        message = f"Team {self.team_id} cut player {self.player_id} ({self.cut_type}): {self.reason}"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "cut_type": self.cut_type,
                "reason": self.reason,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "cut_type": self.cut_type,
            "reason": self.reason,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"roster_cut_{self.team_id}_{self.player_id}_{self.event_date.year}"


class WaiverClaimEvent(BaseEvent):
    """
    Event for claiming a player off waivers.

    When a player is cut, they go through waivers where teams can claim them
    based on waiver priority (inverse of standings).
    """

    def __init__(
        self,
        claiming_team_id: int,
        releasing_team_id: int,
        player_id: str,
        waiver_priority: int,
        claim_successful: bool,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize waiver claim event.

        Args:
            claiming_team_id: Team attempting to claim (1-32)
            releasing_team_id: Team that released the player (1-32)
            player_id: Player on waivers
            waiver_priority: Claiming team's priority (1 = highest)
            claim_successful: Whether claim was successful (highest priority wins)
            event_date: Date of claim
            event_id: Unique identifier
            dynasty_id: Dynasty context for isolation
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.claiming_team_id = claiming_team_id
        self.releasing_team_id = releasing_team_id
        self.player_id = player_id
        self.waiver_priority = waiver_priority
        self.claim_successful = claim_successful
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "WAIVER_CLAIM"

    def simulate(self) -> EventResult:
        """Execute waiver claim (placeholder)."""
        if self.claim_successful:
            message = f"Team {self.claiming_team_id} successfully claimed player {self.player_id} off waivers (priority #{self.waiver_priority})"
        else:
            message = f"Team {self.claiming_team_id} failed to claim player {self.player_id} (priority #{self.waiver_priority} not high enough)"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "claiming_team_id": self.claiming_team_id,
                "releasing_team_id": self.releasing_team_id,
                "player_id": self.player_id,
                "waiver_priority": self.waiver_priority,
                "claim_successful": self.claim_successful,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "claiming_team_id": self.claiming_team_id,
            "releasing_team_id": self.releasing_team_id,
            "player_id": self.player_id,
            "waiver_priority": self.waiver_priority,
            "claim_successful": self.claim_successful,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"waiver_claim_{self.claiming_team_id}_{self.player_id}_{self.event_date.year}"


class PracticeSquadEvent(BaseEvent):
    """
    Event for adding/removing players from practice squad.

    Teams can have up to 16 practice squad players who practice with the team
    but aren't eligible for games (unless elevated).
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        action: str,  # "ADD", "REMOVE", "ELEVATE", "PROTECT"
        reason: str,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize practice squad event.

        Args:
            team_id: Team managing the practice squad (1-32)
            player_id: Player being added/removed/elevated
            action: Type of action (ADD, REMOVE, ELEVATE, PROTECT)
            reason: Explanation
            event_date: Date of action
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
        self.action = action
        self.reason = reason
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "PRACTICE_SQUAD"

    def simulate(self) -> EventResult:
        """Execute practice squad action (placeholder)."""
        action_verb = {
            "ADD": "added to",
            "REMOVE": "removed from",
            "ELEVATE": "elevated from",
            "PROTECT": "protected on"
        }.get(self.action, "modified on")

        message = f"Team {self.team_id} {action_verb} practice squad: player {self.player_id} ({self.reason})"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "action": self.action,
                "reason": self.reason,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "action": self.action,
            "reason": self.reason,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"practice_squad_{self.team_id}_{self.player_id}_{self.action}_{self.event_date.year}"
