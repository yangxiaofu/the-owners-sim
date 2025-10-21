"""
Free Agency Events

Action events for NFL free agency transactions during the offseason.
These include UFA signings, RFA offer sheets, and compensatory pick awards.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date
from salary_cap import EventCapBridge, ContractEventHandler, RFAEventHandler

if TYPE_CHECKING:
    from persistence.transaction_logger import TransactionLogger


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
        base_salaries: list,
        guaranteed_amounts: list,
        season: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None,
        database_path: str = "data/database/nfl_simulation.db",
        transaction_logger: Optional["TransactionLogger"] = None
    ):
        """
        Initialize UFA signing event.

        Args:
            team_id: Team signing the player (1-32)
            player_id: Player being signed
            contract_years: Length of contract in years
            contract_value: Total contract value
            signing_bonus: Signing bonus amount
            base_salaries: Year-by-year base salaries
            guaranteed_amounts: Year-by-year guaranteed amounts
            season: Season year
            event_date: Date of signing
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier
            database_path: Path to database
            transaction_logger: Optional TransactionLogger for automatic logging
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.team_id = team_id
        self.player_id = player_id
        self.contract_years = contract_years
        self.contract_value = contract_value
        self.signing_bonus = signing_bonus
        self.base_salaries = base_salaries
        self.guaranteed_amounts = guaranteed_amounts
        self.season = season
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path
        self.transaction_logger = transaction_logger

    def get_event_type(self) -> str:
        return "UFA_SIGNING"

    def simulate(self) -> EventResult:
        """Execute UFA signing with cap validation and contract creation."""
        try:
            # Initialize cap bridge and handler
            bridge = EventCapBridge(database_path=self.database_path)
            handler = ContractEventHandler(bridge)

            # Prepare event data for handler
            event_data = {
                "player_id": self.player_id,
                "team_id": self.team_id,
                "contract_years": self.contract_years,
                "total_value": self.contract_value,
                "signing_bonus": self.signing_bonus,
                "base_salaries": self.base_salaries,
                "guaranteed_amounts": self.guaranteed_amounts,
                "season": self.season,
                "dynasty_id": self.dynasty_id
            }

            # Execute signing through handler
            result = handler.handle_ufa_signing(event_data)

            if result["success"]:
                avg_per_year = self.contract_value // self.contract_years if self.contract_years > 0 else 0
                message = f"Team {self.team_id} signed UFA player {self.player_id}: {self.contract_years}yr/${self.contract_value:,} (${avg_per_year:,}/yr)"

                event_result = EventResult(
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
                        "base_salaries": self.base_salaries,
                        "guaranteed_amounts": self.guaranteed_amounts,
                        "season": self.season,
                        "avg_per_year": avg_per_year,
                        "contract_id": result.get("contract_id"),
                        "cap_impact": result.get("cap_impact"),
                        "cap_space_remaining": result.get("cap_space_remaining"),
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
                            season=self.season
                        )
                    except Exception as e:
                        # Log error but don't fail the event
                        import logging
                        logging.getLogger(__name__).error(
                            f"Failed to log UFA signing transaction: {e}"
                        )

                return event_result
            else:
                # Cap validation failed
                error_msg = result.get("error_message", "Unknown error")
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "contract_value": self.contract_value,
                        "error_message": error_msg,
                        "dynasty_id": self.dynasty_id
                    }
                )

        except Exception as e:
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=datetime.now(),
                data={
                    "team_id": self.team_id,
                    "player_id": self.player_id,
                    "error_message": f"Failed to execute UFA signing: {str(e)}",
                    "dynasty_id": self.dynasty_id
                }
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "contract_years": self.contract_years,
            "contract_value": self.contract_value,
            "signing_bonus": self.signing_bonus,
            "base_salaries": self.base_salaries,
            "guaranteed_amounts": self.guaranteed_amounts,
            "season": self.season,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        """
        Return unique identifier for this UFA signing.

        Format: ufa_signing_{team_id}_{player_id}_{year}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"ufa_signing_{self.team_id}_{self.player_id}_{self.event_date.year}"

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'UFASigningEvent':
        """
        Reconstruct UFASigningEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()
                Must contain 'dynasty_id' at top level (from events table column)

        Returns:
            Reconstructed UFASigningEvent instance
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
            team_id=params['team_id'],
            player_id=params['player_id'],
            contract_years=params['contract_years'],
            contract_value=params['contract_value'],
            signing_bonus=params['signing_bonus'],
            base_salaries=params['base_salaries'],
            guaranteed_amounts=params['guaranteed_amounts'],
            season=params['season'],
            event_date=Date.from_string(params['event_date']),
            dynasty_id=dynasty_id,
            event_id=event_data['event_id'],
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )


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
        signing_bonus: int,
        base_salaries: list,
        tender_level: str,  # "FIRST_ROUND", "SECOND_ROUND", "ORIGINAL_ROUND", "RIGHT_OF_FIRST_REFUSAL"
        matched: bool,
        season: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None,
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize RFA offer sheet event.

        Args:
            original_team_id: Original team with right to match (1-32)
            signing_team_id: Team making the offer (1-32)
            player_id: Player receiving offer sheet
            offer_amount: Total offer value
            contract_years: Length of contract
            signing_bonus: Signing bonus amount
            base_salaries: Year-by-year base salaries
            tender_level: RFA tender level (determines compensation)
            matched: Whether original team matched the offer
            season: Season year
            event_date: Date of offer/match decision
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.original_team_id = original_team_id
        self.signing_team_id = signing_team_id
        self.player_id = player_id
        self.offer_amount = offer_amount
        self.contract_years = contract_years
        self.signing_bonus = signing_bonus
        self.base_salaries = base_salaries
        self.tender_level = tender_level
        self.matched = matched
        self.season = season
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "RFA_OFFER_SHEET"

    def simulate(self) -> EventResult:
        """Execute RFA offer sheet with cap validation and contract creation."""
        try:
            # Initialize cap bridge and handler
            bridge = EventCapBridge(database_path=self.database_path)
            handler = RFAEventHandler(bridge)

            # Prepare event data for handler
            event_data = {
                "player_id": self.player_id,
                "offering_team_id": self.signing_team_id,
                "original_team_id": self.original_team_id,
                "contract_years": self.contract_years,
                "total_value": self.offer_amount,
                "signing_bonus": self.signing_bonus,
                "base_salaries": self.base_salaries,
                "season": self.season,
                "is_matched": self.matched,
                "dynasty_id": self.dynasty_id
            }

            # Execute offer sheet through handler
            result = handler.handle_offer_sheet(event_data)

            if result["success"]:
                final_team = result["signing_team_id"]
                if self.matched:
                    message = f"Team {self.original_team_id} matched offer sheet for player {self.player_id} (${self.offer_amount:,})"
                else:
                    message = f"Team {self.signing_team_id} signed RFA player {self.player_id} (Team {self.original_team_id} declined to match ${self.offer_amount:,})"

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
                        "signing_bonus": self.signing_bonus,
                        "base_salaries": self.base_salaries,
                        "tender_level": self.tender_level,
                        "matched": self.matched,
                        "final_team_id": final_team,
                        "contract_id": result.get("contract_id"),
                        "cap_impact": result.get("cap_impact"),
                        "season": self.season,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "message": message
                    }
                )
            else:
                # Cap validation failed
                error_msg = result.get("error_message", "Unknown error")
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "original_team_id": self.original_team_id,
                        "signing_team_id": self.signing_team_id,
                        "player_id": self.player_id,
                        "offer_amount": self.offer_amount,
                        "error_message": error_msg,
                        "dynasty_id": self.dynasty_id
                    }
                )

        except Exception as e:
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=datetime.now(),
                data={
                    "original_team_id": self.original_team_id,
                    "signing_team_id": self.signing_team_id,
                    "player_id": self.player_id,
                    "error_message": f"Failed to execute RFA offer sheet: {str(e)}",
                    "dynasty_id": self.dynasty_id
                }
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "original_team_id": self.original_team_id,
            "signing_team_id": self.signing_team_id,
            "player_id": self.player_id,
            "offer_amount": self.offer_amount,
            "contract_years": self.contract_years,
            "signing_bonus": self.signing_bonus,
            "base_salaries": self.base_salaries,
            "tender_level": self.tender_level,
            "matched": self.matched,
            "season": self.season,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        """
        Return unique identifier for this RFA offer sheet.

        Format: rfa_offer_{signing_team_id}_{player_id}_{year}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"rfa_offer_{self.signing_team_id}_{self.player_id}_{self.event_date.year}"

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'RFAOfferSheetEvent':
        """
        Reconstruct RFAOfferSheetEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()
                Must contain 'dynasty_id' at top level (from events table column)

        Returns:
            Reconstructed RFAOfferSheetEvent instance
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
            original_team_id=params['original_team_id'],
            signing_team_id=params['signing_team_id'],
            player_id=params['player_id'],
            offer_amount=params['offer_amount'],
            contract_years=params['contract_years'],
            signing_bonus=params['signing_bonus'],
            base_salaries=params['base_salaries'],
            tender_level=params['tender_level'],
            matched=params['matched'],
            season=params['season'],
            event_date=Date.from_string(params['event_date']),
            dynasty_id=dynasty_id,
            event_id=event_data['event_id'],
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )


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
        dynasty_id: str,
        event_id: Optional[str] = None
    ):
        """
        Initialize compensatory pick award event.

        Args:
            team_id: Team receiving the pick (1-32)
            pick_round: Draft round (3-7)
            pick_number: Overall pick number in draft
            reason: Explanation (e.g., "Lost QB John Doe to Team 5")
            event_date: Date pick is awarded
            dynasty_id: Dynasty context for isolation (REQUIRED)
            event_id: Unique identifier
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

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
        """
        Return unique identifier for this compensatory pick award.

        Format: comp_pick_{team_id}_round{pick_round}_{year}
        Note: dynasty_id is now a separate column, not encoded in game_id
        """
        return f"comp_pick_{self.team_id}_round{self.pick_round}_{self.event_date.year}"
