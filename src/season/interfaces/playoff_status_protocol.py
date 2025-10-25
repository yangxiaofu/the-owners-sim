"""
Playoff Status Protocol

Defines the interface for playoff status checking.
Enables dependency injection and testing with mock playoff controllers.
"""

from typing import Protocol, List, Dict, Any, Optional


class PlayoffStatusProtocol(Protocol):
    """
    Protocol for checking playoff status and completion.

    Any class implementing this protocol can check playoff game status
    and determine if playoffs are complete.

    This allows SeasonCycleController to depend on an abstraction
    rather than the concrete PlayoffController, enabling:
    - Unit testing with mock playoff status
    - Testing Super Bowl completion logic without running playoffs
    - Dependency injection patterns
    """

    def is_super_bowl_complete(self) -> bool:
        """
        Check if Super Bowl has been played (not just scheduled).

        CRITICAL: Must check if game has a winner, not just if it exists.

        Returns:
            True if Super Bowl has been simulated and has a winner
        """
        ...

    def get_round_games(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific playoff round.

        Args:
            round_name: Round name ('wild_card', 'divisional', 'conference', 'super_bowl')

        Returns:
            List of game dictionaries for the round
        """
        ...

    def get_super_bowl_winner(self) -> Optional[int]:
        """
        Get Super Bowl winner team ID.

        Returns:
            Team ID of winner, or None if Super Bowl not played
        """
        ...

    def is_playoffs_started(self) -> bool:
        """
        Check if playoffs have started.

        Returns:
            True if playoff bracket has been created
        """
        ...
