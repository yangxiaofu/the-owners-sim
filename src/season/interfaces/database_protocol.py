"""
Database Protocol

Defines the interface for database operations.
Enables dependency injection and testing with mock databases.
"""

from typing import Protocol, Dict, Any, List


class DatabaseProtocol(Protocol):
    """
    Protocol for database operations.

    Any class implementing this protocol can perform database queries
    and updates for season data.

    This allows SeasonCycleController to depend on an abstraction
    rather than the concrete DatabaseAPI, enabling:
    - Unit testing with mock databases (no I/O)
    - In-memory test databases
    - Alternative database implementations
    - Dependency injection patterns
    """

    def get_standings(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Get current standings for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary with standings data organized by division
        """
        ...

    def reset_standings(
        self,
        dynasty_id: str,
        season: int
    ) -> None:
        """
        Reset all team standings to 0-0-0 for a new season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        ...

    def update_phase(
        self,
        dynasty_id: str,
        phase: str
    ) -> None:
        """
        Update current phase in dynasty state.

        Args:
            dynasty_id: Dynasty identifier
            phase: New phase ('preseason', 'regular_season', 'playoffs', 'offseason')
        """
        ...

    def get_games_played_count(
        self,
        dynasty_id: str,
        season: int,
        season_type: str = 'regular_season'
    ) -> int:
        """
        Get count of games played for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            season_type: Type of games ('regular_season', 'preseason', 'playoffs')

        Returns:
            Number of games played
        """
        ...

    def save_state(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Save current database state for rollback.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            State snapshot that can be passed to restore_state()
        """
        ...

    def restore_state(self, state_snapshot: Dict[str, Any]) -> None:
        """
        Restore database state from a snapshot (for rollback).

        Args:
            state_snapshot: State snapshot from save_state()
        """
        ...
