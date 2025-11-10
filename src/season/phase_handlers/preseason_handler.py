"""Preseason Phase Handler - Delegates to SeasonController."""
from typing import Dict, Any


class PreseasonHandler:
    """Handles daily operations during preseason phase."""

    def __init__(self, season_controller):
        """
        Initialize preseason handler.

        Args:
            season_controller: SeasonController instance for delegation
        """
        self.season_controller = season_controller

    def advance_day(self) -> Dict[str, Any]:
        """Delegate to season controller for preseason day advancement."""
        return self.season_controller.advance_day()
