"""
Draft Events

Action events for NFL draft-related transactions during the offseason.
These include draft picks, UDFA signings, and draft-day trades.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date


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
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
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

    def get_event_type(self) -> str:
        return "DRAFT_PICK"

    def simulate(self) -> EventResult:
        """Execute draft pick (placeholder)."""
        message = f"Team {self.team_id} selected {self.player_name} ({self.position}, {self.college}) with pick #{self.pick_number} (Round {self.round_number})"

        return EventResult(
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
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
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


class DraftTradeEvent(BaseEvent):
    """
    Event for trading draft picks between teams.

    Teams can trade future picks, current picks, or picks + players.
    """

    def __init__(
        self,
        team1_id: int,
        team2_id: int,
        team1_gives_picks: List[Dict[str, Any]],  # List of {round, year, pick_number}
        team2_gives_picks: List[Dict[str, Any]],
        team1_gives_players: List[str],  # List of player_ids (optional)
        team2_gives_players: List[str],
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize draft trade event.

        Args:
            team1_id: First team in trade (1-32)
            team2_id: Second team in trade (1-32)
            team1_gives_picks: Picks team1 trades away
            team2_gives_picks: Picks team2 trades away
            team1_gives_players: Players team1 trades away (optional)
            team2_gives_players: Players team2 trades away (optional)
            event_date: Date of trade
            event_id: Unique identifier
            dynasty_id: Dynasty context for isolation
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.team1_id = team1_id
        self.team2_id = team2_id
        self.team1_gives_picks = team1_gives_picks
        self.team2_gives_picks = team2_gives_picks
        self.team1_gives_players = team1_gives_players
        self.team2_gives_players = team2_gives_players
        self.event_date = event_date
        self.dynasty_id = dynasty_id

    def get_event_type(self) -> str:
        return "DRAFT_TRADE"

    def simulate(self) -> EventResult:
        """Execute draft trade (placeholder)."""
        team1_assets = f"{len(self.team1_gives_picks)} pick(s)"
        if self.team1_gives_players:
            team1_assets += f" + {len(self.team1_gives_players)} player(s)"

        team2_assets = f"{len(self.team2_gives_picks)} pick(s)"
        if self.team2_gives_players:
            team2_assets += f" + {len(self.team2_gives_players)} player(s)"

        message = f"Draft trade: Team {self.team1_id} trades {team1_assets} to Team {self.team2_id} for {team2_assets}"

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "team1_id": self.team1_id,
                "team2_id": self.team2_id,
                "team1_gives_picks": self.team1_gives_picks,
                "team2_gives_picks": self.team2_gives_picks,
                "team1_gives_players": self.team1_gives_players,
                "team2_gives_players": self.team2_gives_players,
                "event_date": str(self.event_date),
                "dynasty_id": self.dynasty_id,
                "message": message
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team1_id": self.team1_id,
            "team2_id": self.team2_id,
            "team1_gives_picks": self.team1_gives_picks,
            "team2_gives_picks": self.team2_gives_picks,
            "team1_gives_players": self.team1_gives_players,
            "team2_gives_players": self.team2_gives_players,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"draft_trade_{self.team1_id}_{self.team2_id}_{self.event_date.year}"
