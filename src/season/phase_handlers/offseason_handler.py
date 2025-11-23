"""Offseason Phase Handler - Delegates to OffseasonController."""
from typing import Dict, Any
from src.calendar.simulation_executor import SimulationExecutor


class OffseasonHandler:
    """Handles daily operations during offseason phase."""

    def __init__(self, offseason_controller, simulation_executor: SimulationExecutor):
        """
        Initialize offseason handler.

        Args:
            offseason_controller: OffseasonController instance for delegation
            simulation_executor: SimulationExecutor for executing offseason events
        """
        self.offseason_controller = offseason_controller
        self.simulation_executor = simulation_executor

    def simulate_day(self, current_date) -> Dict[str, Any]:
        """
        Simulate offseason activities for the given date.

        Executes two responsibilities:
        1. Execute offseason events (draft, free agency, etc.) via SimulationExecutor
        2. Track offseason phase and deadlines via OffseasonController

        Args:
            current_date: Date object for the day to simulate (from controller)

        Returns:
            Dict containing simulation results and metadata
        """
        # DIAGNOSTIC: Offseason handler entry
        print(f"\n{'='*80}")
        print(f"[OFFSEASON_HANDLER] simulate_day() CALLED")
        print(f"{'='*80}")
        print(f"  Date to simulate: {current_date}")
        print(f"")

        # STEP 1: Execute offseason events (draft, free agency, etc.)
        print(f"[OFFSEASON_HANDLER] Executing offseason events via SimulationExecutor...")
        event_result = self.simulation_executor.simulate_day(current_date)
        events_executed = len(event_result.get('events_executed', []))
        print(f"[OFFSEASON_HANDLER] Events executed: {events_executed}")
        print(f"")

        # STEP 2: Track offseason phase and deadlines
        print(f"[OFFSEASON_HANDLER] Delegating to OffseasonController for phase tracking...")
        controller_result = self.offseason_controller.simulate_day(current_date)

        # DIAGNOSTIC: Controller result
        print(f"\n[OFFSEASON_HANDLER] OffseasonController returned:")
        print(f"  New date: {controller_result.get('new_date', 'NOT_SET')}")
        print(f"  Phase changed: {controller_result.get('phase_changed', False)}")
        print(f"  New phase: {controller_result.get('new_phase', 'N/A')}")
        print(f"")

        # Merge results: controller result + event execution data
        result = controller_result.copy()
        result['events_executed'] = event_result.get('events_executed', [])
        result['games_played'] = 0  # No games during offseason
        result['results'] = []
        result['success'] = event_result.get('success', True)

        return result
