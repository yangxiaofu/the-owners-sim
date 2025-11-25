"""Preseason Phase Handler - Direct component access."""
from typing import Dict, Any
from src.calendar.calendar_component import CalendarComponent
from src.calendar.simulation_executor import SimulationExecutor
from src.database.api import DatabaseAPI


class PreseasonHandler:
    """Handles daily operations during preseason phase."""

    def __init__(
        self,
        calendar: CalendarComponent,
        simulation_executor: SimulationExecutor,
        database_api: DatabaseAPI,
        season_year: int
    ):
        """
        Initialize preseason handler with direct component access.

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

        # Add state tracking for consistency with RegularSeasonHandler
        self.total_games_played = 0
        self.total_days_simulated = 0

    def simulate_day(self, current_date) -> Dict[str, Any]:
        """
        Simulate games for the given date (controller manages calendar).

        REFACTORED: No longer advances calendar - controller handles that.
        Handler only simulates games for the date provided by controller.

        Args:
            current_date: Date object for the day to simulate (from controller)

        Returns:
            Dict containing simulation results and metadata
        """
        # DIAGNOSTIC: Preseason handler entry
        print(f"\n{'='*80}")
        print(f"[PRESEASON_HANDLER] simulate_day() CALLED")
        print(f"{'='*80}")
        print(f"  Season year: {self.season_year}")
        print(f"  Date to simulate: {current_date}")
        print(f"  Total games played so far: {self.total_games_played}")
        print(f"  Total days simulated: {self.total_days_simulated}")
        print(f"  NOTE: Calendar managed by controller, not handler")
        print(f"")

        # DIAGNOSTIC: Before simulation call
        print(f"[PRESEASON_HANDLER] Calling simulation_executor.simulate_day({current_date})")
        print(f"")

        # Simulate day's games (no calendar advancement)
        simulation_result = self.simulation_executor.simulate_day(current_date)

        # DIAGNOSTIC: Simulation result
        print(f"\n[PRESEASON_HANDLER] Simulation executor returned:")
        print(f"  Success: {simulation_result.get('success', 'NOT_SET')}")
        print(f"  Events count: {simulation_result.get('events_count', 0)}")
        print(f"  Games played: {len(simulation_result.get('games_played', []))}")
        print(f"  Message: {simulation_result.get('message', 'No message')}")
        if 'errors' in simulation_result and simulation_result['errors']:
            print(f"  Errors: {simulation_result['errors']}")
        print(f"")

        # Update statistics
        games_played = len([
            g for g in simulation_result.get('games_played', [])
            if g.get('success', False)
        ])
        self.total_games_played += games_played
        self.total_days_simulated += 1

        return {
            "date": str(current_date),
            "games_played": games_played,
            "results": simulation_result.get('games_played', []),
            "standings_updated": False,  # Preseason doesn't affect standings
            "current_phase": "PRESEASON",
            "success": simulation_result.get('success', True)
        }

    def get_current_standings(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get current standings from database.

        Note: Preseason doesn't have standings, but providing for consistency.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict containing standings data (empty for preseason)
        """
        return {
            "divisions": {},
            "conference_standings": {},
            "note": "Preseason does not have standings"
        }
