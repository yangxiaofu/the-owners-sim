"""
Contract Events

Action events for NFL contract-related transactions during the offseason.
These include franchise tags, transition tags, releases, and restructures.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_event import BaseEvent, EventResult
from calendar.date_models import Date
from salary_cap import EventCapBridge, TagEventHandler, ContractEventHandler, ReleaseEventHandler


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
        player_position: str,
        season: int,
        tag_type: str,  # "FRANCHISE_EXCLUSIVE" or "FRANCHISE_NON_EXCLUSIVE"
        tag_amount: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default",
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize franchise tag event.

        Args:
            team_id: Team applying the tag (1-32)
            player_id: Player receiving the tag
            player_position: Player's position (QB, WR, etc.)
            season: Season year
            tag_type: "FRANCHISE_EXCLUSIVE" or "FRANCHISE_NON_EXCLUSIVE"
            tag_amount: Salary for the tag (calculated from league data)
            event_date: Date when tag is applied
            event_id: Unique identifier
            dynasty_id: Dynasty context
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.player_position = player_position
        self.season = season
        self.tag_type = tag_type
        self.tag_amount = tag_amount
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "FRANCHISE_TAG"

    def simulate(self) -> EventResult:
        """
        Execute franchise tag with full cap integration.

        Creates franchise tag contract and validates cap compliance.
        """
        try:
            # Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = TagEventHandler(bridge)

            # Build event data
            event_data = {
                "team_id": self.team_id,
                "player_id": self.player_id,
                "player_position": self.player_position,
                "season": self.season,
                "tag_type": self.tag_type,
                "tag_date": self.event_date.to_python_date(),
                "dynasty_id": self.dynasty_id
            }

            # Execute through handler
            result = handler.handle_franchise_tag(event_data)

            if result["success"]:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "player_position": self.player_position,
                        "tag_type": self.tag_type,
                        "tag_salary": result["tag_salary"],
                        "contract_id": result["contract_id"],
                        "cap_impact": result["cap_impact"],
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "message": f"Applied {self.tag_type} franchise tag: ${result['tag_salary']:,}"
                    }
                )
            else:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "tag_type": self.tag_type,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id
                    },
                    error_message=result.get("error_message", "Unknown error")
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
                    "tag_type": self.tag_type,
                    "event_date": str(self.event_date),
                    "dynasty_id": self.dynasty_id
                },
                error_message=f"Franchise tag failed: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "player_position": self.player_position,
            "season": self.season,
            "tag_type": self.tag_type,
            "tag_amount": self.tag_amount,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
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

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'FranchiseTagEvent':
        """
        Reconstruct FranchiseTagEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed FranchiseTagEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        return cls(
            team_id=params['team_id'],
            player_id=params['player_id'],
            player_position=params['player_position'],
            season=params['season'],
            tag_type=params['tag_type'],
            tag_amount=params.get('tag_amount', 0),
            event_date=Date.from_string(params['event_date']),
            event_id=event_data['event_id'],
            dynasty_id=params.get('dynasty_id', 'default'),
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )


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
        player_position: str,
        season: int,
        tag_amount: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default",
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize transition tag event.

        Args:
            team_id: Team applying the tag (1-32)
            player_id: Player receiving the tag
            player_position: Player's position (QB, WR, etc.)
            season: Season year
            tag_amount: Salary for the tag (average of top 10 at position)
            event_date: Date when tag is applied
            event_id: Unique identifier
            dynasty_id: Dynasty context
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.player_position = player_position
        self.season = season
        self.tag_amount = tag_amount
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "TRANSITION_TAG"

    def simulate(self) -> EventResult:
        """
        Execute transition tag with full cap integration.

        Creates transition tag contract and validates cap compliance.
        """
        try:
            # Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = TagEventHandler(bridge)

            # Build event data
            event_data = {
                "team_id": self.team_id,
                "player_id": self.player_id,
                "player_position": self.player_position,
                "season": self.season,
                "tag_date": self.event_date.to_python_date(),
                "dynasty_id": self.dynasty_id
            }

            # Execute through handler
            result = handler.handle_transition_tag(event_data)

            if result["success"]:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "player_position": self.player_position,
                        "tag_salary": result["tag_salary"],
                        "contract_id": result["contract_id"],
                        "cap_impact": result["cap_impact"],
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "message": f"Applied transition tag: ${result['tag_salary']:,}"
                    }
                )
            else:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id
                    },
                    error_message=result.get("error_message", "Unknown error")
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
                    "event_date": str(self.event_date),
                    "dynasty_id": self.dynasty_id
                },
                error_message=f"Transition tag failed: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "player_position": self.player_position,
            "season": self.season,
            "tag_amount": self.tag_amount,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"transition_tag_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'TransitionTagEvent':
        """
        Reconstruct TransitionTagEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed TransitionTagEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        return cls(
            team_id=params['team_id'],
            player_id=params['player_id'],
            player_position=params['player_position'],
            season=params['season'],
            tag_amount=params.get('tag_amount', 0),
            event_date=Date.from_string(params['event_date']),
            event_id=event_data['event_id'],
            dynasty_id=params.get('dynasty_id', 'default'),
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )


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
        contract_id: int,
        release_type: str,  # "PRE_JUNE_1" or "POST_JUNE_1"
        cap_savings: int,
        dead_cap: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default",
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize player release event.

        Args:
            team_id: Team releasing the player (1-32)
            player_id: Player being released
            contract_id: Contract ID to terminate
            release_type: "PRE_JUNE_1" or "POST_JUNE_1"
            cap_savings: Cap space saved by release
            dead_cap: Dead cap hit from release
            event_date: Date of release
            event_id: Unique identifier
            dynasty_id: Dynasty context
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.contract_id = contract_id
        self.release_type = release_type
        self.cap_savings = cap_savings
        self.dead_cap = dead_cap
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "PLAYER_RELEASE"

    def simulate(self) -> EventResult:
        """
        Execute player release with full cap integration.

        Terminates contract and calculates dead money impact.
        """
        try:
            # Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = ReleaseEventHandler(bridge)

            # Determine if June 1 designation should be used
            june_1_designation = self.release_type == "POST_JUNE_1"

            # Build event data
            event_data = {
                "contract_id": self.contract_id,
                "release_date": self.event_date.to_python_date(),
                "june_1_designation": june_1_designation,
                "dynasty_id": self.dynasty_id
            }

            # Execute through handler
            result = handler.handle_player_release(event_data)

            if result["success"]:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "contract_id": self.contract_id,
                        "release_type": self.release_type,
                        "dead_money": result["dead_money"],
                        "cap_savings": result["cap_savings"],
                        "cap_space_available": result["cap_space_available"],
                        "june_1_designation": result["june_1_designation"],
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "message": f"Released player ({self.release_type}): ${result['cap_savings']:,} saved, ${result['dead_money']:,} dead cap"
                    }
                )
            else:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "contract_id": self.contract_id,
                        "release_type": self.release_type,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id
                    },
                    error_message=result.get("error_message", "Unknown error")
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
                    "contract_id": self.contract_id,
                    "release_type": self.release_type,
                    "event_date": str(self.event_date),
                    "dynasty_id": self.dynasty_id
                },
                error_message=f"Player release failed: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "contract_id": self.contract_id,
            "release_type": self.release_type,
            "cap_savings": self.cap_savings,
            "dead_cap": self.dead_cap,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"release_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'PlayerReleaseEvent':
        """
        Reconstruct PlayerReleaseEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed PlayerReleaseEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        return cls(
            team_id=params['team_id'],
            player_id=params['player_id'],
            contract_id=params['contract_id'],
            release_type=params['release_type'],
            cap_savings=params.get('cap_savings', 0),
            dead_cap=params.get('dead_cap', 0),
            event_date=Date.from_string(params['event_date']),
            event_id=event_data['event_id'],
            dynasty_id=params.get('dynasty_id', 'default'),
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )


class ContractRestructureEvent(BaseEvent):
    """
    Event for restructuring a player's contract to create cap space.

    Converts base salary to signing bonus, spreading cap hit over future years.
    """

    def __init__(
        self,
        team_id: int,
        player_id: str,
        contract_id: int,
        year_to_restructure: int,
        restructure_amount: int,
        cap_savings_current_year: int,
        event_date: Date,
        event_id: Optional[str] = None,
        dynasty_id: str = "default",
        database_path: str = "data/database/nfl_simulation.db"
    ):
        """
        Initialize contract restructure event.

        Args:
            team_id: Team restructuring the contract (1-32)
            player_id: Player whose contract is being restructured
            contract_id: Contract ID to restructure
            year_to_restructure: Which year to restructure (1-based)
            restructure_amount: Amount being converted to bonus
            cap_savings_current_year: Cap space created this year
            event_date: Date of restructure
            event_id: Unique identifier
            dynasty_id: Dynasty context
            database_path: Path to database
        """
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime)

        self.team_id = team_id
        self.player_id = player_id
        self.contract_id = contract_id
        self.year_to_restructure = year_to_restructure
        self.restructure_amount = restructure_amount
        self.cap_savings_current_year = cap_savings_current_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path

    def get_event_type(self) -> str:
        return "CONTRACT_RESTRUCTURE"

    def simulate(self) -> EventResult:
        """
        Execute contract restructure with full cap integration.

        Converts base salary to signing bonus, creating cap space.
        """
        try:
            # Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = ContractEventHandler(bridge)

            # Build event data
            event_data = {
                "contract_id": self.contract_id,
                "year_to_restructure": self.year_to_restructure,
                "amount_to_convert": self.restructure_amount,
                "dynasty_id": self.dynasty_id
            }

            # Execute through handler
            result = handler.handle_contract_restructure(event_data)

            if result["success"]:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "contract_id": self.contract_id,
                        "year_to_restructure": self.year_to_restructure,
                        "restructure_amount": self.restructure_amount,
                        "cap_savings": result["cap_savings"],
                        "new_cap_hits": result["new_cap_hits"],
                        "dead_money_increase": result["dead_money_increase"],
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "message": f"Restructured contract: ${result['cap_savings']:,} cap space created"
                    }
                )
            else:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={
                        "team_id": self.team_id,
                        "player_id": self.player_id,
                        "contract_id": self.contract_id,
                        "year_to_restructure": self.year_to_restructure,
                        "restructure_amount": self.restructure_amount,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id
                    },
                    error_message=result.get("error_message", "Unknown error")
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
                    "contract_id": self.contract_id,
                    "year_to_restructure": self.year_to_restructure,
                    "restructure_amount": self.restructure_amount,
                    "event_date": str(self.event_date),
                    "dynasty_id": self.dynasty_id
                },
                error_message=f"Contract restructure failed: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "player_id": self.player_id,
            "contract_id": self.contract_id,
            "year_to_restructure": self.year_to_restructure,
            "restructure_amount": self.restructure_amount,
            "cap_savings_current_year": self.cap_savings_current_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "database_path": self.database_path
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_game_id(self) -> str:
        return f"restructure_{self.dynasty_id}_{self.team_id}_{self.player_id}_{self.event_date.year}"

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'ContractRestructureEvent':
        """
        Reconstruct ContractRestructureEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed ContractRestructureEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        return cls(
            team_id=params['team_id'],
            player_id=params['player_id'],
            contract_id=params['contract_id'],
            year_to_restructure=params['year_to_restructure'],
            restructure_amount=params['restructure_amount'],
            cap_savings_current_year=params.get('cap_savings_current_year', 0),
            event_date=Date.from_string(params['event_date']),
            event_id=event_data['event_id'],
            dynasty_id=params.get('dynasty_id', 'default'),
            database_path=params.get('database_path', 'data/database/nfl_simulation.db')
        )
