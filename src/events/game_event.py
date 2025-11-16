"""
Game Event

Wraps FullGameSimulator to implement the BaseEvent interface.
This allows NFL games to be stored and retrieved as generic events.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from events.base_event import BaseEvent, EventResult
from game_management.full_game_simulator import FullGameSimulator


class GameEvent(BaseEvent):
    """
    NFL Game simulation event that wraps FullGameSimulator.

    This class adapts the FullGameSimulator to the BaseEvent interface,
    allowing games to be stored in the generic events table and retrieved
    alongside other event types (media, trades, etc.).

    Key Design:
    - Lazy initialization: FullGameSimulator created only when simulate() is called
    - Wraps existing simulator without modifying its code
    - Implements BaseEvent contract for polymorphic storage/retrieval
    """

    def __init__(
        self,
        away_team_id: int,
        home_team_id: int,
        game_date: datetime,
        week: int,
        dynasty_id: str,
        game_id: Optional[str] = None,
        event_id: Optional[str] = None,
        overtime_type: str = "regular_season",
        season: Optional[int] = None,
        season_type: str = "regular_season",
        game_type: str = "regular"
    ):
        """
        Initialize game event.

        Args:
            away_team_id: Away team ID (1-32)
            home_team_id: Home team ID (1-32)
            game_date: When game is scheduled
            week: Week number in season
            dynasty_id: Dynasty identifier for isolation (REQUIRED)
            game_id: Optional game identifier (auto-generated if not provided)
            event_id: Optional event identifier (auto-generated if not provided)
            overtime_type: Overtime rules ("regular_season" or "playoffs")
            season: Season year (e.g., 2024)
            season_type: Type of season ("preseason", "regular_season", "playoffs")
            game_type: Specific game type ("regular", "wildcard", "divisional", "conference", "super_bowl")
        """
        super().__init__(event_id=event_id, timestamp=game_date, dynasty_id=dynasty_id)
        print(f"[DYNASTY_TRACE] GameEvent.__init__(): away={away_team_id}, home={home_team_id}, dynasty_id={dynasty_id}")

        # Validate team IDs
        if not (1 <= away_team_id <= 32):
            raise ValueError(f"Away team ID must be 1-32, got {away_team_id}")
        if not (1 <= home_team_id <= 32):
            raise ValueError(f"Home team ID must be 1-32, got {home_team_id}")
        if away_team_id == home_team_id:
            raise ValueError("Away and home teams must be different")

        self.away_team_id = away_team_id
        self.home_team_id = home_team_id
        self.game_date = game_date
        self.week = week
        self.overtime_type = overtime_type
        self.season = season or game_date.year
        self.season_type = season_type
        self.game_type = game_type

        # Generate game_id if not provided
        self._game_id = game_id or self._generate_game_id()

        # Lazy initialization - simulator created when simulate() is called
        self._simulator = None
        self._simulation_result = None
        self._cached_result = None  # For result caching after simulation

    def _generate_game_id(self) -> str:
        """Generate unique game identifier"""
        date_str = self.game_date.strftime("%Y%m%d")
        return f"game_{date_str}_{self.away_team_id}_at_{self.home_team_id}"

    def get_event_type(self) -> str:
        """Return event type identifier"""
        return "GAME"

    def get_game_id(self) -> str:
        """Return game identifier for event grouping"""
        return self._game_id

    def simulate(self) -> EventResult:
        """
        Execute NFL game simulation via FullGameSimulator.

        Creates and runs FullGameSimulator, capturing the complete game result
        and converting it to the standardized EventResult format.

        Returns:
            EventResult with game outcome and statistics
        """
        try:
            print(f"\n🏈 Simulating: {self._get_matchup_description()}")

            # Lazy initialization of simulator
            if not self._simulator:
                self._simulator = FullGameSimulator(
                    away_team_id=self.away_team_id,
                    home_team_id=self.home_team_id,
                    dynasty_id=self.dynasty_id,
                    db_path="data/database/nfl_simulation.db",  # TODO: Make configurable
                    overtime_type=self.overtime_type,
                    season_type=self.season_type
                )

            # Run game simulation
            game_result = self._simulator.simulate_game(date=self.game_date)
            self._simulation_result = game_result

            # Extract final score
            final_score = self._simulator.get_final_score()

            # Debug logging for final_score from FullGameSimulator
            print(f"\n[DEBUG GameEvent] final_score from FullGameSimulator:")
            print(f"  winner_id: {final_score.get('winner_id')}")
            print(f"  winner_name: {final_score.get('winner_name')}")
            print(f"  scores: {final_score.get('scores')}")
            print(f"  game_completed: {final_score.get('game_completed')}\n")

            # Build result data
            result_data = {
                "game_id": self._game_id,
                "away_team_id": self.away_team_id,
                "home_team_id": self.home_team_id,
                "away_score": final_score['scores'].get(self.away_team_id, 0),
                "home_score": final_score['scores'].get(self.home_team_id, 0),
                "winner_id": final_score.get('winner_id'),
                "winner_name": final_score.get('winner_name'),
                "total_plays": final_score.get('total_plays', 0),
                "total_drives": final_score.get('total_drives', 0),
                "game_duration_minutes": final_score.get('game_duration_minutes', 0),
                "simulation_time": final_score.get('simulation_time', 0.0),
                "week": self.week,
                "season": self.season,
                "season_type": self.season_type,
                "game_type": self.game_type,
                "game_date": self.game_date.isoformat(),
                # Store full game result for detailed access
                "game_result": game_result
            }

            print(f"✅ Game Complete: {result_data['away_score']}-{result_data['home_score']}")
            if result_data['winner_name']:
                print(f"🏆 Winner: {result_data['winner_name']}")

            result = EventResult(
                event_id=self.event_id,
                event_type="GAME",
                success=True,
                timestamp=self.game_date,
                data=result_data
            )

            # Cache result for later retrieval without re-simulation
            self._cached_result = result

            return result

        except Exception as e:
            error_msg = f"Game simulation failed: {str(e)}"
            print(f"❌ {error_msg}")

            return EventResult(
                event_id=self.event_id,
                event_type="GAME",
                success=False,
                timestamp=self.game_date,
                data={
                    "game_id": self._game_id,
                    "away_team_id": self.away_team_id,
                    "home_team_id": self.home_team_id,
                    "week": self.week,
                    "season": self.season
                },
                error_message=error_msg
            )

    def _get_parameters(self) -> Dict[str, Any]:
        """
        Return parameters needed to replay this game.

        These are the input values needed to recreate the exact game simulation.

        Returns:
            Dictionary with game setup parameters
        """
        return {
            "away_team_id": self.away_team_id,
            "home_team_id": self.home_team_id,
            "week": self.week,
            "season": self.season,
            "season_type": self.season_type,
            "game_type": self.game_type,
            "game_date": self.game_date.isoformat(),
            "overtime_type": self.overtime_type
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        """
        Return results after game simulation.

        Returns None if game hasn't been simulated yet.
        After simulation, returns scores, winner, and statistics.

        Returns:
            Dictionary with game results, or None if not yet simulated
        """
        if not self._cached_result:
            return None

        data = self._cached_result.data

        return {
            "away_score": data.get('away_score', 0),
            "home_score": data.get('home_score', 0),
            "winner_id": data.get('winner_id'),
            "winner_name": data.get('winner_name'),
            "total_plays": data.get('total_plays', 0),
            "total_drives": data.get('total_drives', 0),
            "game_duration_minutes": data.get('game_duration_minutes', 0),
            "simulation_time": data.get('simulation_time', 0.0),
            "simulated_at": self._cached_result.timestamp.isoformat()
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Return additional game context and metadata.

        Returns:
            Dictionary with supplementary information
        """
        return {
            "matchup_description": self._get_matchup_description(),
            "is_playoff_game": self.season_type == "playoffs",
            "game_id": self._game_id
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that game can be simulated.

        Checks:
        - Team IDs are valid (1-32)
        - Teams are different
        - Week number is reasonable
        - Date is valid

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        # Team ID validation
        if not (1 <= self.away_team_id <= 32):
            return False, f"Invalid away_team_id: {self.away_team_id} (must be 1-32)"

        if not (1 <= self.home_team_id <= 32):
            return False, f"Invalid home_team_id: {self.home_team_id} (must be 1-32)"

        if self.away_team_id == self.home_team_id:
            return False, "Away and home teams must be different"

        # Week validation
        if self.week < 1 or self.week > 25:  # Regular season + playoffs
            return False, f"Invalid week number: {self.week} (must be 1-25)"

        # Season type validation
        valid_season_types = ["preseason", "regular_season", "playoffs"]
        if self.season_type not in valid_season_types:
            return False, f"Invalid season_type: {self.season_type} (must be one of {valid_season_types})"

        # Overtime type validation
        valid_overtime_types = ["preseason", "regular_season", "playoffs"]
        if self.overtime_type not in valid_overtime_types:
            return False, f"Invalid overtime_type: {self.overtime_type} (must be one of {valid_overtime_types})"

        return True, None

    def get_matchup_description(self) -> str:
        """Get human-readable matchup description"""
        return self._get_matchup_description()

    def _get_matchup_description(self) -> str:
        """Internal method to generate matchup description"""
        return f"Week {self.week}: Team {self.away_team_id} @ Team {self.home_team_id}"

    def get_simulation_result(self):
        """
        Get the full FullGameSimulator result if simulation has been run.

        Returns:
            GameResult object or None if not yet simulated
        """
        return self._simulation_result

    def get_simulator(self) -> Optional[FullGameSimulator]:
        """
        Get the underlying FullGameSimulator instance.

        Useful for accessing detailed game state, rosters, etc.

        Returns:
            FullGameSimulator instance or None if not yet created
        """
        return self._simulator

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'GameEvent':
        """
        Reconstruct GameEvent from database data.

        Factory method for recreating GameEvent objects from
        Event Database API query results. Handles both old format
        and new three-part structure.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed GameEvent instance
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            # Backward compatibility with old format
            params = data

        game = cls(
            away_team_id=params['away_team_id'],
            home_team_id=params['home_team_id'],
            game_date=datetime.fromisoformat(params['game_date']),
            week=params['week'],
            dynasty_id=event_data.get('dynasty_id') or params.get('dynasty_id'),
            game_id=event_data['game_id'],
            event_id=event_data['event_id'],
            overtime_type=params.get('overtime_type', 'regular_season'),
            season=params.get('season'),
            season_type=params.get('season_type', 'regular_season'),
            game_type=params.get('game_type', 'regular')
        )

        # If results exist in database, restore them (historical data)
        if 'results' in data and data['results']:
            results = data['results']
            # Recreate cached result for display without re-simulation
            game._cached_result = EventResult(
                event_id=event_data['event_id'],
                event_type="GAME",
                success=True,
                timestamp=datetime.fromisoformat(results['simulated_at']),
                data=results
            )

        return game

    def __str__(self) -> str:
        """String representation"""
        return f"GameEvent: {self._get_matchup_description()} ({self.game_date.strftime('%Y-%m-%d')})"

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (
            f"GameEvent(away={self.away_team_id}, home={self.home_team_id}, "
            f"week={self.week}, date={self.game_date}, id={self.event_id})"
        )
