"""
Trade Events

Action events for NFL trade transactions during the regular season.
These include player-for-player trades and player-for-pick trades (future).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING, List
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date

from salary_cap import EventCapBridge, TradeEventHandler
from persistence.transaction_logger import TransactionLogger
from database.player_roster_api import PlayerRosterAPI
from team_management.teams.team_loader import get_team_by_id

if TYPE_CHECKING:
    pass


class PlayerForPlayerTradeEvent(BaseEvent):
    """
    Event for player-for-player trades.

    Executes a trade where Team A sends player(s) to Team B in exchange
    for player(s) from Team B. Validates cap space and executes contract
    transfers.
    """

    def __init__(
        self,
        team1_id: int,
        team2_id: int,
        team1_player_ids: List[str],
        team2_player_ids: List[str],
        season: int,
        event_date: Date,
        dynasty_id: str,
        event_id: Optional[str] = None,
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize player-for-player trade event.

        Args:
            team1_id: First team ID (1-32)
            team2_id: Second team ID (1-32)
            team1_player_ids: List of player IDs from team1 going to team2
            team2_player_ids: List of player IDs from team2 going to team1
            season: Season year
            event_date: Date when trade is executed
            dynasty_id: Dynasty identifier for isolation (REQUIRED)
            event_id: Unique identifier
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.team1_id = team1_id
        self.team2_id = team2_id
        self.team1_player_ids = team1_player_ids
        self.team2_player_ids = team2_player_ids
        self.season = season
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "PLAYER_TRADE"

    def simulate(self) -> EventResult:
        """
        Execute player-for-player trade with full cap integration.

        Validates cap space for both teams and executes contract transfers.

        Returns:
            EventResult with success status and trade details
        """
        try:
            # Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = TradeEventHandler(bridge)

            # Create ValidationMiddleware instance
            from salary_cap.event_integration import ValidationMiddleware
            validator = ValidationMiddleware(
                cap_calculator=bridge.calculator,
                cap_validator=bridge.validator,
                tag_manager=bridge.tag_mgr,
                cap_db=bridge.cap_db
            )

            # Validate trade before execution
            is_valid, error_msg = validator.validate_player_trade(
                team1_id=self.team1_id,
                team2_id=self.team2_id,
                team1_player_ids=self.team1_player_ids,
                team2_player_ids=self.team2_player_ids,
                season=self.season,
                dynasty_id=self.dynasty_id,
                trade_date=self.event_date.to_python_date()
            )

            if not is_valid:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=self.timestamp,
                    data={
                        "team1_id": self.team1_id,
                        "team2_id": self.team2_id,
                        "team1_player_ids": self.team1_player_ids,
                        "team2_player_ids": self.team2_player_ids,
                    },
                    error_message=f"Trade validation failed: {error_msg}"
                )

            # Build event data
            event_data = {
                "team1_id": self.team1_id,
                "team2_id": self.team2_id,
                "team1_player_ids": self.team1_player_ids,
                "team2_player_ids": self.team2_player_ids,
                "season": self.season,
                "trade_date": self.event_date.to_python_date(),
                "dynasty_id": self.dynasty_id
            }

            # Execute trade through handler
            result = handler.handle_player_trade(event_data)

            if not result.get("success"):
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=self.timestamp,
                    data=event_data,
                    error_message=result.get("error_message", "Unknown error during trade execution")
                )

            # Log player transactions to player_transactions table
            transaction_logger = TransactionLogger(self.database_path)
            roster_api = PlayerRosterAPI(self.database_path)

            # Helper function to get team name
            def get_team_name(team_id: int) -> str:
                team = get_team_by_id(team_id)
                return team.full_name if team else f"Team {team_id}"

            # Log team1 players moving to team2
            for player_id in self.team1_player_ids:
                try:
                    player_data = roster_api.get_player_by_id(
                        dynasty_id=self.dynasty_id,
                        player_id=int(player_id)
                    )

                    if player_data:
                        # Parse positions if JSON string
                        positions = player_data.get('positions', [])
                        if isinstance(positions, str):
                            import json
                            positions = json.loads(positions)

                        player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                        position = positions[0] if positions else None

                        transaction_logger.log_transaction(
                            dynasty_id=self.dynasty_id,
                            season=self.season,
                            transaction_type="TRADE",
                            player_id=player_id,
                            player_name=player_name or f"Player {player_id}",
                            position=position,
                            transaction_date=self.event_date.to_python_date(),
                            from_team_id=self.team1_id,
                            to_team_id=self.team2_id,
                            details={"trade_partner": get_team_name(self.team2_id)},
                            event_id=self.event_id
                        )

                except Exception as e:
                    # Log error but don't fail the trade
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to log transaction for player {player_id}: {e}"
                    )

            # Log team2 players moving to team1
            for player_id in self.team2_player_ids:
                try:
                    player_data = roster_api.get_player_by_id(
                        dynasty_id=self.dynasty_id,
                        player_id=int(player_id)
                    )

                    if player_data:
                        # Parse positions if JSON string
                        positions = player_data.get('positions', [])
                        if isinstance(positions, str):
                            import json
                            positions = json.loads(positions)

                        player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                        position = positions[0] if positions else None

                        transaction_logger.log_transaction(
                            dynasty_id=self.dynasty_id,
                            season=self.season,
                            transaction_type="TRADE",
                            player_id=player_id,
                            player_name=player_name or f"Player {player_id}",
                            position=position,
                            transaction_date=self.event_date.to_python_date(),
                            from_team_id=self.team2_id,
                            to_team_id=self.team1_id,
                            details={"trade_partner": get_team_name(self.team1_id)},
                            event_id=self.event_id
                        )

                except Exception as e:
                    # Log error but don't fail the trade
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to log transaction for player {player_id}: {e}"
                    )

            # Success - create result with full trade details
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=True,
                timestamp=self.timestamp,
                data={
                    "team1_id": self.team1_id,
                    "team2_id": self.team2_id,
                    "team1_players_sent": self.team1_player_ids,
                    "team2_players_sent": self.team2_player_ids,
                    "team1_acquired_players": result.get("team1_acquired_players", []),
                    "team2_acquired_players": result.get("team2_acquired_players", []),
                    "team1_net_cap_change": result.get("team1_net_cap_change", 0),
                    "team2_net_cap_change": result.get("team2_net_cap_change", 0),
                    "trade_date": str(self.event_date),
                }
            )

        except Exception as e:
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=self.timestamp,
                data={
                    "team1_id": self.team1_id,
                    "team2_id": self.team2_id,
                    "team1_player_ids": self.team1_player_ids,
                    "team2_player_ids": self.team2_player_ids,
                },
                error_message=f"Trade execution error: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        """Return event parameters for serialization."""
        return {
            "team1_id": self.team1_id,
            "team2_id": self.team2_id,
            "team1_player_ids": self.team1_player_ids,
            "team2_player_ids": self.team2_player_ids,
            "season": self.season,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate preconditions before event can be scheduled.

        Basic validation - detailed validation happens in simulate().
        """
        if self.team1_id == self.team2_id:
            return False, "Cannot trade with same team"
        if not self.team1_player_ids or not self.team2_player_ids:
            return False, "Both teams must send at least one player"
        return True, None

    def __repr__(self) -> str:
        return (
            f"PlayerForPlayerTradeEvent("
            f"team1={self.team1_id}, team2={self.team2_id}, "
            f"team1_players={len(self.team1_player_ids)}, "
            f"team2_players={len(self.team2_player_ids)}, "
            f"date={self.event_date})"
        )
