"""Regular Season Phase Handler - Delegates to SeasonController."""
from typing import Dict, Any


class RegularSeasonHandler:
    """Handles daily operations during regular season phase."""

    def __init__(self, season_controller):
        """
        Initialize regular season handler.

        Args:
            season_controller: SeasonController instance for delegation
        """
        self.season_controller = season_controller

    def advance_day(self) -> Dict[str, Any]:
        """Delegate to season controller for regular season day advancement."""
        return self.season_controller.advance_day()
