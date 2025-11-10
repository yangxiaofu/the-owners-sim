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
        return self.offseason_controller.advance_day()
