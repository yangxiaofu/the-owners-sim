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

    def advance_day(self) -> Dict[str, Any]:
        """Delegate to offseason controller for offseason day advancement."""
        # DIAGNOSTIC: Offseason handler entry
        print(f"\n{'='*80}")
        print(f"[OFFSEASON_HANDLER] advance_day() CALLED")
        print(f"{'='*80}")
        print(f"  Delegating to OffseasonController...")
        print(f"")

        result = self.offseason_controller.advance_day()

        # DIAGNOSTIC: Offseason controller result
        print(f"\n[OFFSEASON_HANDLER] OffseasonController returned:")
        print(f"  New date: {result.get('new_date', 'NOT_SET')}")
        print(f"  Phase changed: {result.get('phase_changed', False)}")
        print(f"  New phase: {result.get('new_phase', 'N/A')}")
        print(f"")

        return result
