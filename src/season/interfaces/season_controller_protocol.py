"""
Season Controller Protocol

Defines the interface for season controller classes.
Enables dependency injection and testing with mock controllers.
"""

from typing import Protocol, Dict, Any


class SeasonControllerProtocol(Protocol):
    """
    Protocol for season controller classes.

    Any class implementing this protocol can control regular season simulation.

    This allows SeasonCycleController to depend on an abstraction
    rather than a concrete SeasonController, enabling:
    - Unit testing with mock controllers
    - Alternative season simulation implementations
    - Dependency injection patterns
    """

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 day.

        Returns:
            Dictionary with simulation results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "success": bool
            }
        """
        ...

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 week.

        Returns:
            Dictionary with simulation results:
            {
                "week": int,
                "games_played": int,
                "results": List[Dict],
                "success": bool
            }
        """
        ...

    def get_current_week(self) -> int:
        """
        Get current week number.

        Returns:
            Week number (1-18)
        """
        ...

    def is_season_complete(self) -> bool:
        """
        Check if regular season is complete.

        Returns:
            True if all games played, False otherwise
        """
        ...
