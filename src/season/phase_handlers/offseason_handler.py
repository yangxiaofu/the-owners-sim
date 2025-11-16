"""Offseason Phase Handler - Delegates to OffseasonController."""
from typing import Dict, Any


class OffseasonHandler:
    """Handles daily operations during offseason phase."""

    def __init__(self, offseason_controller):
        """
        Initialize offseason handler.

        Args:
            offseason_controller: OffseasonController instance for delegation
        """
        self.offseason_controller = offseason_controller

    def simulate_day(self, current_date) -> Dict[str, Any]:
        """
        Simulate offseason activities for the given date (delegates to OffseasonController).

        REFACTORED: No longer delegates advance_day() - delegates simulate_day().
        OffseasonController will be refactored in Phase 4 to accept current_date.

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
        print(f"  Delegating to OffseasonController.simulate_day({current_date})...")
        print(f"")

        # Delegate to OffseasonController.simulate_day() with current_date
        result = self.offseason_controller.simulate_day(current_date)

        # DIAGNOSTIC: Offseason controller result
        print(f"\n[OFFSEASON_HANDLER] OffseasonController returned:")
        print(f"  New date: {result.get('new_date', 'NOT_SET')}")
        print(f"  Phase changed: {result.get('phase_changed', False)}")
        print(f"  New phase: {result.get('new_phase', 'N/A')}")
        print(f"")

        return result
