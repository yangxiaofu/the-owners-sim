"""Playoff Phase Handler - Delegates to PlayoffController."""
from typing import Dict, Any


class PlayoffHandler:
    """Handles daily operations during playoff phase."""

    def __init__(self, playoff_controller):
        """
        Initialize playoff handler.

        Args:
            playoff_controller: PlayoffController instance for delegation
        """
        self.playoff_controller = playoff_controller

    def advance_day(self) -> Dict[str, Any]:
        """Delegate to playoff controller for playoff day advancement."""
        return self.playoff_controller.advance_day()
