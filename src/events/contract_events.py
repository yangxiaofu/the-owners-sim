"""
Contract Events

Action events for NFL contract-related transactions during the offseason.
These include franchise tags, transition tags, releases, and restructures.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date


class FranchiseTagEvent(BaseEvent):
    """
    Event for applying a franchise tag to a player.

    The franchise tag allows teams to retain a player for one year at a
    predetermined salary (average of top 5 salaries at the position).
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        tag_type: str,  # "EXCLUSIVE" or "NON_EXCLUSIVE"
        tag_amount: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize franchise tag event.

        Args:
            team_id: Team applying the tag (1-32)
            player_id: Player receiving the tag
            tag_type: "EXCLUSIVE" or "NON_EXCLUSIVE"
            tag_amount: Salary for the tag (calculated from league data)
            event_date: Date when tag is applied
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.tag_type = tag_type
        self.tag_amount = tag_amount
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "FRANCHISE_TAG"

    def simulate(self) -> EventResult:
        """
        Execute franchise tag (placeholder - business logic added later).

        Future: Will update contract database and salary cap tracking.
        """
        # TODO: Integrate with contract/cap system when built
        message = f"Team {self.team_id} applied {self.tag_type} franchise tag to player {self.player_id} for ${self.tag_amount:,}"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "tag_type": self.tag_type,
                "tag_amount": self.tag_amount,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "tag_type": self.tag_type,
            "tag_amount": self.tag_amount,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """Validate tag can be applied (placeholder)."""
        # TODO: Add validation when contract/cap system exists
        # - Check team has cap space
        # - Check player eligibility
        # - Check deadline hasn't passed
        return (True, None)

    def get_game_id(self) -> str:
        return f"franchise_tag_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"


class TransitionTagEvent(BaseEvent):
    """
    Event for applying a transition tag to a player.

    Similar to franchise tag but allows team right of first refusal
    on outside offers without compensation.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        tag_amount: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize transition tag event.

        Args:
            team_id: Team applying the tag (1-32)
            player_id: Player receiving the tag
            tag_amount: Salary for the tag (average of top 10 at position)
            event_date: Date when tag is applied
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.tag_amount = tag_amount
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "TRANSITION_TAG"

    def simulate(self) -> EventResult:
        """Execute transition tag (placeholder)."""
        message = f"Team {self.team_id} applied transition tag to player {self.player_id} for ${self.tag_amount:,}"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "tag_amount": self.tag_amount,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "tag_amount": self.tag_amount,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"transition_tag_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"


class PlayerReleaseEvent(BaseEvent):
    """
    Event for releasing a player from their contract.

    Players can be released pre-June 1 or post-June 1, affecting
    how the cap hit is distributed.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        release_type: str,  # "PRE_JUNE_1" or "POST_JUNE_1"
        cap_savings: int,
        dead_cap: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize player release event.

        Args:
            team_id: Team releasing the player (1-32)
            player_id: Player being released
            release_type: "PRE_JUNE_1" or "POST_JUNE_1"
            cap_savings: Cap space saved by release
            dead_cap: Dead cap hit from release
            event_date: Date of release
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.release_type = release_type
        self.cap_savings = cap_savings
        self.dead_cap = dead_cap
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "PLAYER_RELEASE"

    def simulate(self) -> EventResult:
        """Execute player release (placeholder)."""
        message = f"Team {self.team_id} released player {self.player_id} ({self.release_type}): ${self.cap_savings:,} saved, ${self.dead_cap:,} dead cap"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "release_type": self.release_type,
                "cap_savings": self.cap_savings,
                "dead_cap": self.dead_cap,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "release_type": self.release_type,
            "cap_savings": self.cap_savings,
            "dead_cap": self.dead_cap,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"release_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"


class ContractRestructureEvent(BaseEvent):
    """
    Event for restructuring a player's contract to create cap space.

    Converts base salary to signing bonus, spreading cap hit over future years.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        restructure_amount: int,
        cap_savings_current_year: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize contract restructure event.

        Args:
            team_id: Team restructuring the contract (1-32)
            player_id: Player whose contract is being restructured
            restructure_amount: Amount being converted to bonus
            cap_savings_current_year: Cap space created this year
            event_date: Date of restructure
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.restructure_amount = restructure_amount
        self.cap_savings_current_year = cap_savings_current_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "CONTRACT_RESTRUCTURE"

    def simulate(self) -> EventResult:
        """Execute contract restructure (placeholder)."""
        message = f"Team {self.team_id} restructured player {self.player_id}: ${self.cap_savings_current_year:,} cap space created"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "restructure_amount": self.restructure_amount,
                "cap_savings_current_year": self.cap_savings_current_year,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "restructure_amount": self.restructure_amount,
            "cap_savings_current_year": self.cap_savings_current_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"restructure_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"
