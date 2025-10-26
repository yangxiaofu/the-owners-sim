"""
Schedule Generator Protocol

Defines the interface for schedule generation classes.
Enables dependency injection and testing with mock generators.
"""

from typing import Protocol, List, Optional
from datetime import datetime
from events.game_event import GameEvent


class ScheduleGeneratorProtocol(Protocol):
    """
    Protocol for NFL schedule generation.

    Any class implementing this protocol can generate preseason
    and regular season schedules.

    This allows SeasonCycleController to depend on an abstraction
    rather than the concrete RandomScheduleGenerator, enabling:
    - Unit testing with mock generators
    - Alternative schedule generation algorithms
    - Dependency injection patterns
    """

    def generate_preseason(
        self,
        season_year: int,
        seed: Optional[int] = None,
        start_date: Optional['datetime'] = None
    ) -> List[GameEvent]:
        """
        Generate complete preseason schedule (48 games, 3 weeks).

        Args:
            season_year: NFL season year
            seed: Optional random seed for reproducible schedules
            start_date: Optional preseason start date (defaults to calculated date)

        Returns:
            List of 48 GameEvent objects
        """
        ...

    def generate_season(
        self,
        season_year: int,
        start_date: Optional[datetime] = None,
        seed: Optional[int] = None
    ) -> List[GameEvent]:
        """
        Generate complete regular season schedule (272 games, 17 weeks).

        Args:
            season_year: NFL season year
            start_date: Optional custom start date (defaults to dynamic Labor Day calc)
            seed: Optional random seed for reproducible schedules

        Returns:
            List of 272 GameEvent objects
        """
        ...

    def _calculate_preseason_start(self, year: int) -> datetime:
        """
        Calculate preseason start date (~3.5 weeks before regular season).

        Args:
            year: Year to calculate for

        Returns:
            datetime of first preseason game
        """
        ...
