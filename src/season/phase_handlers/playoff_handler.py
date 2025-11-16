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

    def simulate_day(self, current_date) -> Dict[str, Any]:
        """
        Simulate playoff games for the given date (delegates to PlayoffController).

        REFACTORED: Delegates to PlayoffController.simulate_day(current_date).
        PlayoffController no longer advances calendar - controller handles it.

        Args:
            current_date: Date object for the day to simulate (from controller)

        Returns:
            Dict containing simulation results and metadata
        """
        # Delegate to PlayoffController.simulate_day() with current_date
        return self.playoff_controller.simulate_day(current_date)
