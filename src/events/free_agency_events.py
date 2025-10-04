"""
Free Agency Events

Action events for NFL free agency transactions during the offseason.
These include UFA signings, RFA offer sheets, and compensatory pick awards.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date


class UFASigningEvent(BaseEvent):
    """
    Event for signing an unrestricted free agent.

    UFA players can sign with any team without compensation to their former team.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        contract_years: int,
        contract_value: int,
        signing_bonus: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize UFA signing event.

        Args:
            team_id: Team signing the player (1-32)
            player_id: Player being signed
            contract_years: Length of contract in years
            contract_value: Total contract value
            signing_bonus: Signing bonus amount
            event_date: Date of signing
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
        self.contract_years = contract_years
        self.contract_value = contract_value
        self.signing_bonus = signing_bonus
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "UFA_SIGNING"

    def simulate(self) -> EventResult:
        """Execute UFA signing (placeholder)."""
        avg_per_year = self.contract_value // self.contract_years if self.contract_years > 0 else 0
        message = f"Team {self.team_id} signed UFA player {self.player_id}: {self.contract_years}yr/${self.contract_value:,} (${avg_per_year:,}/yr)"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "contract_years": self.contract_years,
                "contract_value": self.contract_value,
                "signing_bonus": self.signing_bonus,
                "avg_per_year": avg_per_year,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "contract_years": self.contract_years,
            "contract_value": self.contract_value,
            "signing_bonus": self.signing_bonus,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"ufa_signing_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"


class RFAOfferSheetEvent(BaseEvent):
    """
    Event for restricted free agent offer sheet signing and matching.

    RFA players can receive offers from other teams, but original team
    can match the offer and retain the player.
    """

    def __init__(
        self,
        original_team_id: int,
        signing_team_id: int,
        player_id: str,
        offer_amount: int,
        contract_years: int,
        tender_level: str,  # "FIRST_ROUND", "SECOND_ROUND", "ORIGINAL_ROUND", "RIGHT_OF_FIRST_REFUSAL"
        matched: bool,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize RFA offer sheet event.

        Args:
            original_team_id: Original team with right to match (1-32)
            signing_team_id: Team making the offer (1-32)
            player_id: Player receiving offer sheet
            offer_amount: Total offer value
            contract_years: Length of contract
            tender_level: RFA tender level (determines compensation)
            matched: Whether original team matched the offer
            event_date: Date of offer/match decision
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.original_team_id = original_team_id
        self.signing_team_id = signing_team_id
        self.player_id = player_id
        self.offer_amount = offer_amount
        self.contract_years = contract_years
        self.tender_level = tender_level
        self.matched = matched
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "RFA_OFFER_SHEET"

    def simulate(self) -> EventResult:
        """Execute RFA offer sheet (placeholder)."""
        if self.matched:
            message = f"Team {self.original_team_id} matched offer sheet for player {self.player_id} (${self.offer_amount:,})"
            final_team = self.original_team_id
        else:
            message = f"Team {self.signing_team_id} signed RFA player {self.player_id} (Team {self.original_team_id} declined to match ${self.offer_amount:,})"
            final_team = self.signing_team_id

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "original_team_id": self.original_team_id,
                "signing_team_id": self.signing_team_id,
                "player_id": self.player_id,
                "offer_amount": self.offer_amount,
                "contract_years": self.contract_years,
                "tender_level": self.tender_level,
                "matched": self.matched,
                "final_team_id": final_team,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "original_team_id": self.original_team_id,
            "signing_team_id": self.signing_team_id,
            "player_id": self.player_id,
            "offer_amount": self.offer_amount,
            "contract_years": self.contract_years,
            "tender_level": self.tender_level,
            "matched": self.matched,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"rfa_offer_{self.dynasty_id}_{self.signing_team_id}_{self.player_id}_{self.event_date.year}"


class CompensatoryPickEvent(BaseEvent):
    """
    Event for awarding compensatory draft picks.

    Teams that lose more/better free agents than they sign receive
    compensatory picks in the draft (rounds 3-7).
    """

    def __init__(
        self,
        team_id: int,
        pick_round: int,
        pick_number: int,
        reason: str,  # Description of what triggered the comp pick
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize compensatory pick award event.

        Args:
            team_id: Team receiving the pick (1-32)
            pick_round: Draft round (3-7)
            pick_number: Overall pick number in draft
            reason: Explanation (e.g., "Lost QB John Doe to Team 5")
            event_date: Date pick is awarded
            event_id: Unique identifier
            dynasty_id: Dynasty context
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.pick_round = pick_round
        self.pick_number = pick_number
        self.reason = reason
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "COMPENSATORY_PICK"

    def simulate(self) -> EventResult:
        """Execute compensatory pick award (placeholder)."""
        message = f"Team {self.team_id} awarded compensatory pick: Round {self.pick_round}, Pick #{self.pick_number} ({self.reason})"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "pick_round": self.pick_round,
                "pick_number": self.pick_number,
                "reason": self.reason,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "pick_round": self.pick_round,
            "pick_number": self.pick_number,
            "reason": self.reason,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"comp_pick_{self.dynasty_id}_{self.team_id}_round{self.pick_round}_{self.event_date.year}"
