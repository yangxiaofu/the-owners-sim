"""
Calendar Protocol

Defines the interface for calendar operations.
Enables dependency injection and testing with mock calendars.
"""

from typing import Protocol
from calendar.date_models import Date


class CalendarProtocol(Protocol):
    """
    Protocol for calendar operations.

    Any class implementing this protocol can track simulation dates
    and advance time.

    This allows SeasonCycleController to depend on an abstraction
    rather than a concrete Calendar, enabling:
    - Unit testing with mock calendars (no real dates)
    - Fast-forward time for testing
    - Time travel for test scenarios
    - Dependency injection patterns
    """

    def get_current_date(self) -> Date:
        """
        Get current simulation date.

        Returns:
            Current Date object
        """
        ...

    def advance(self, days: int) -> Date:
        """
        Advance calendar by specified number of days.

        Args:
            days: Number of days to advance

        Returns:
            New current date after advancement
        """
        ...

    def get_last_regular_season_game_date(self) -> Date:
        """
        Get the date of the last scheduled regular season game.

        Returns:
            Date of last regular season game
        """
        ...

    def set_date(self, date: Date) -> None:
        """
        Set calendar to specific date (useful for testing).

        Args:
            date: Date to set calendar to
        """
        ...
