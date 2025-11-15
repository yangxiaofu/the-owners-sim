"""Regular Season Phase Handler - Direct component access."""
from typing import Dict, Any
from src.calendar.calendar_component import CalendarComponent
from src.calendar.simulation_executor import SimulationExecutor
from src.database.api import DatabaseAPI


class RegularSeasonHandler:
    """Handles daily operations during regular season phase."""

    def __init__(
        self,
        calendar: CalendarComponent,
        simulation_executor: SimulationExecutor,
        database_api: DatabaseAPI,
        season_year: int
    ):
        """
        Initialize regular season handler with direct component access.

        Args:
            calendar: Calendar component for date management
            simulation_executor: Executor for running game simulations
            database_api: Database API for data access
            season_year: Current season year
        """
        self.calendar = calendar
        self.simulation_executor = simulation_executor
        self.database_api = database_api
        self.season_year = season_year

        # Add state tracking (previously in demo SeasonController)
        self.current_week = 1
        self.total_games_played = 0
        self.total_days_simulated = 0

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance calendar by 1 day and simulate games.

        Returns:
            Dict containing simulation results and metadata
        """
        # Advance calendar
        advance_result = self.calendar.advance(1)
        current_date = advance_result.end_date

        # Simulate day's games
        simulation_result = self.simulation_executor.simulate_day(current_date)

        # Update statistics
        games_played = len([
            g for g in simulation_result.get('games_played', [])
            if g.get('success', False)
        ])
        self.total_games_played += games_played
        self.total_days_simulated += 1

        # Update week number based on date (simplified - can be enhanced later)
        # NFL weeks run roughly September through early January
        # This is a placeholder - ideally should check game schedule

        return {
            "date": str(current_date),
            "games_played": games_played,
            "results": simulation_result.get('games_played', []),
            "standings_updated": games_played > 0,
            "current_phase": "REGULAR_SEASON",
            "success": simulation_result.get('success', True)
        }

    def get_current_standings(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get current standings from database.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict containing standings data
        """
        return self.database_api.get_standings(
            dynasty_id=dynasty_id,
            season=self.season_year
        )
