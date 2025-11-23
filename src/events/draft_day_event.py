"""
Draft Day Event

NFL Draft simulation orchestrator event.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_event import BaseEvent, EventResult

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


class DraftDayEvent(BaseEvent):
    """
    NFL Draft simulation orchestrator event.

    This event wraps DraftManager.simulate_draft() to execute the complete
    7-round NFL draft with AI team selections and optional user manual picks.

    Key Design:
    - Lazy initialization: DraftManager created only when simulate() is called
    - Wraps existing draft logic without modifying DraftManager code
    - Implements BaseEvent contract for polymorphic storage/retrieval
    - Supports both fully automated (all AI) and semi-automated (user + AI) drafts
    """

    def __init__(
        self,
        season_year: int,
        event_date: Date,
        dynasty_id: str,
        database_path: str = "data/database/nfl_simulation.db",
        user_team_id: Optional[int] = None,
        user_picks: Optional[Dict[int, str]] = None,
        verbose: bool = False,
        event_id: Optional[str] = None
    ):
        """
        Initialize draft day event orchestrator.

        Args:
            season_year: NFL season year (e.g., 2024)
            event_date: Date when draft occurs
            dynasty_id: Dynasty context for isolation (REQUIRED)
            database_path: Path to SQLite database
            user_team_id: User's team ID (1-32) for manual selections (None = fetch from dynasties table)
            user_picks: Optional dict mapping {overall_pick: player_id} for manual picks
            verbose: If True, print pick-by-pick results during simulation
            event_id: Unique identifier (auto-generated if not provided)
        """
        # Convert Date to datetime for BaseEvent
        event_datetime = datetime.combine(
            event_date.to_python_date(),
            datetime.min.time()
        )
        super().__init__(event_id=event_id, timestamp=event_datetime, dynasty_id=dynasty_id)

        self.season_year = season_year
        self.event_date = event_date
        self.dynasty_id = dynasty_id
        self.database_path = database_path
        self._user_team_id = user_team_id  # Private: use property for access
        self.user_picks = user_picks or {}
        self.verbose = verbose

        # Lazy initialization
        self._draft_manager = None
        self._cached_result = None

    @property
    def user_team_id(self) -> int:
        """
        Get user team ID dynamically from dynasty record.

        Returns cached value if provided at initialization, otherwise
        queries dynasties table to fetch current user team.

        Returns:
            int: User's controlled team ID (1-32)

        Raises:
            ValueError: If dynasty not found or user_team_id not set
        """
        # Return cached value if explicitly provided
        if self._user_team_id is not None:
            return self._user_team_id

        # Fetch from database
        from database.dynasty_database_api import DynastyDatabaseAPI

        dynasty_api = DynastyDatabaseAPI(self.database_path)
        dynasty = dynasty_api.get_dynasty_by_id(self.dynasty_id)

        if dynasty and dynasty.get('team_id'):
            return dynasty['team_id']

        # Fallback error
        raise ValueError(
            f"No user_team_id found for dynasty '{self.dynasty_id}'. "
            f"Dynasty must have team_id set in dynasties table."
        )

    def get_event_type(self) -> str:
        """Return event type identifier."""
        return "DRAFT_DAY"

    def simulate(self) -> EventResult:
        """
        Execute full 7-round NFL draft simulation.

        Orchestrates DraftManager.simulate_draft() and wraps results
        in standardized EventResult format.

        If draft has already been completed interactively (all picks executed),
        this method skips re-execution and returns a success result.

        Returns:
            EventResult with draft results and summary statistics
        """
        try:
            # Check if draft already completed (via interactive dialog)
            if self._is_draft_already_completed():
                import logging
                logging.getLogger(__name__).info(
                    f"Draft for season {self.season_year} already completed interactively. "
                    f"Skipping automated execution."
                )

                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "season_year": self.season_year,
                        "event_date": str(self.event_date),
                        "dynasty_id": self.dynasty_id,
                        "total_picks": 224,  # 7 rounds × 32 teams
                        "draft_type": "interactive",
                        "message": f"{self.season_year} NFL Draft already completed (interactive)"
                    }
                )

            # Lazy initialization of DraftManager
            if self._draft_manager is None:
                from offseason.draft_manager import DraftManager

                self._draft_manager = DraftManager(
                    database_path=self.database_path,
                    dynasty_id=self.dynasty_id,
                    season_year=self.season_year,
                    enable_persistence=True  # Always persist draft picks
                )

            # Run full draft simulation
            draft_results = self._draft_manager.simulate_draft(
                user_team_id=self.user_team_id or 1,  # Default to team 1 if None
                user_picks=self.user_picks,
                verbose=self.verbose
            )

            # Build summary statistics
            result_data = self._build_result_data(draft_results)

            # Cache result
            self._cached_result = EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=True,
                timestamp=datetime.now(),
                data=result_data
            )

            return self._cached_result

        except Exception as e:
            # Error handling with descriptive message
            import logging
            logging.getLogger(__name__).error(
                f"Draft simulation failed: {e}",
                exc_info=True
            )

            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=datetime.now(),
                data={
                    "season_year": self.season_year,
                    "event_date": str(self.event_date),
                    "dynasty_id": self.dynasty_id
                },
                error_message=f"Draft simulation failed: {str(e)}"
            )

    def _is_draft_already_completed(self) -> bool:
        """
        Check if draft has already been executed (all picks completed).

        Queries draft_order table to see if all 224 picks have been executed.

        Returns:
            True if all picks are executed, False otherwise
        """
        try:
            from database.draft_order_database_api import DraftOrderDatabaseAPI

            draft_order_api = DraftOrderDatabaseAPI(self.database_path)
            picks = draft_order_api.get_draft_order(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not picks:
                # No draft order exists yet
                return False

            # Check if all picks have been executed
            all_executed = all(pick.is_executed for pick in picks)

            if all_executed:
                import logging
                logging.getLogger(__name__).info(
                    f"Draft order for season {self.season_year} already complete: "
                    f"{len(picks)} picks executed"
                )

            return all_executed

        except Exception as e:
            # If error checking, assume draft not completed (fail-safe)
            import logging
            logging.getLogger(__name__).warning(
                f"Error checking draft completion status: {e}. Assuming not completed."
            )
            return False

    def _build_result_data(self, draft_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build comprehensive result data from draft picks.

        Args:
            draft_results: List of pick dicts from simulate_draft()

        Returns:
            Dictionary with draft summary and all picks
        """
        # Calculate summary statistics
        total_picks = len(draft_results)
        picks_by_round: Dict[int, int] = {}
        picks_by_team: Dict[int, int] = {}

        for pick in draft_results:
            round_num = pick['round']
            team_id = pick['team_id']

            # Count by round
            picks_by_round[round_num] = picks_by_round.get(round_num, 0) + 1

            # Count by team
            picks_by_team[team_id] = picks_by_team.get(team_id, 0) + 1

        return {
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "dynasty_id": self.dynasty_id,
            "total_picks": total_picks,
            "picks_by_round": picks_by_round,
            "picks_by_team": picks_by_team,
            "all_picks": draft_results,  # Full pick-by-pick data
            "user_team_id": self.user_team_id,
            "manual_picks_count": len(self.user_picks),
            "message": f"{self.season_year} NFL Draft complete: {total_picks} picks executed"
        }

    def _get_parameters(self) -> Dict[str, Any]:
        """Return parameters needed to replay this draft."""
        return {
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "database_path": self.database_path,
            "user_team_id": self.user_team_id,
            "user_picks": self.user_picks,
            "verbose": self.verbose,
            "dynasty_id": self.dynasty_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that draft can be simulated.

        Checks:
        - Season year is valid
        - User team ID is valid (if provided)

        Returns:
            (True, None) if valid, (False, error_message) otherwise
        """
        # Season year validation
        if self.season_year < 1960 or self.season_year > 2100:
            return False, f"Invalid season_year: {self.season_year} (must be 1960-2100)"

        # User team validation
        if self.user_team_id is not None:
            if not (1 <= self.user_team_id <= 32):
                return False, f"Invalid user_team_id: {self.user_team_id} (must be 1-32)"

        return True, None

    def get_game_id(self) -> str:
        """Return draft identifier for event grouping."""
        return f"draft_{self.season_year}_{self.dynasty_id}"

    def get_matchup_description(self) -> str:
        """Get human-readable draft description."""
        return f"{self.season_year} NFL Draft"

    def __str__(self) -> str:
        """String representation."""
        return f"DraftDayEvent: {self.season_year} NFL Draft ({self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"DraftDayEvent(season={self.season_year}, date={self.event_date}, "
            f"dynasty={self.dynasty_id}, user_team={self._user_team_id})"
        )

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'DraftDayEvent':
        """
        Reconstruct DraftDayEvent from database storage.

        Args:
            event_data: Event dictionary from EventDatabaseAPI with structure:
                {
                    'event_id': str,
                    'event_type': str,
                    'timestamp': int,
                    'dynasty_id': str,
                    'data': {
                        'parameters': {
                            'season_year': int,
                            'event_date': str,
                            'database_path': str,
                            'user_team_id': int,
                            'user_picks': dict,
                            'verbose': bool,
                            'dynasty_id': str
                        },
                        'results': dict or None,
                        'metadata': dict
                    }
                }

        Returns:
            Reconstructed DraftDayEvent instance
        """
        params = event_data['data']['parameters']

        return cls(
            season_year=params['season_year'],
            event_date=Date.from_string(params['event_date']),
            dynasty_id=params['dynasty_id'],
            database_path=params.get('database_path', 'data/database/nfl_simulation.db'),
            user_team_id=params.get('user_team_id'),
            user_picks=params.get('user_picks', {}),
            verbose=params.get('verbose', False),
            event_id=event_data['event_id']
        )
