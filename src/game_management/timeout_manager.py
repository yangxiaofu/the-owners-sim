"""
Timeout management for NFL games.

Handles timeout tracking, usage validation, and halftime resets per NFL rules.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimeoutState:
    """Current timeout state for both teams."""
    home_timeouts: int = 3
    away_timeouts: int = 3
    timeout_called_this_play: Optional[int] = None  # Team ID that called timeout

    def get_timeouts_remaining(self, team_id: int, home_team_id: int) -> int:
        """Get timeouts remaining for a team."""
        if team_id == home_team_id:
            return self.home_timeouts
        return self.away_timeouts

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "home_timeouts": self.home_timeouts,
            "away_timeouts": self.away_timeouts,
            "timeout_called_this_play": self.timeout_called_this_play
        }


class TimeoutManager:
    """
    Manages timeouts for an NFL game.

    NFL Rules:
    - Each team gets 3 timeouts per half
    - Timeouts reset to 3 at halftime (start of Q3)
    - Timeouts do NOT carry over between halves
    - Teams can call timeout when they have possession or on defense
    """

    def __init__(self, home_team_id: int, away_team_id: int):
        """
        Initialize timeout manager.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
        """
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.state = TimeoutState()

        logger.info(f"TimeoutManager initialized: Home={home_team_id}, Away={away_team_id}")

    def can_use_timeout(self, team_id: int) -> bool:
        """
        Check if team can use a timeout.

        Args:
            team_id: Team requesting timeout

        Returns:
            True if team has timeouts remaining
        """
        timeouts = self.state.get_timeouts_remaining(team_id, self.home_team_id)
        return timeouts > 0

    def use_timeout(self, team_id: int) -> bool:
        """
        Use a timeout for the specified team.

        Args:
            team_id: Team calling timeout

        Returns:
            True if timeout was successfully used, False if none remaining
        """
        if not self.can_use_timeout(team_id):
            logger.warning(f"Team {team_id} attempted to use timeout with none remaining")
            return False

        # Deduct timeout
        if team_id == self.home_team_id:
            self.state.home_timeouts -= 1
            logger.info(f"Home team timeout used. Remaining: {self.state.home_timeouts}")
        else:
            self.state.away_timeouts -= 1
            logger.info(f"Away team timeout used. Remaining: {self.state.away_timeouts}")

        # Mark that timeout was called this play
        self.state.timeout_called_this_play = team_id

        return True

    def reset_timeouts_for_half(self) -> None:
        """
        Reset timeouts to 3 for each team at halftime.

        Called at the start of the 3rd quarter per NFL rules.
        """
        self.state.home_timeouts = 3
        self.state.away_timeouts = 3
        self.state.timeout_called_this_play = None

        logger.info("Timeouts reset to 3 for both teams at halftime")

    def clear_timeout_flag(self) -> None:
        """Clear the timeout_called_this_play flag after processing."""
        self.state.timeout_called_this_play = None

    def get_timeouts_remaining(self, team_id: int) -> int:
        """
        Get number of timeouts remaining for a team.

        Args:
            team_id: Team to check

        Returns:
            Number of timeouts remaining (0-3)
        """
        return self.state.get_timeouts_remaining(team_id, self.home_team_id)

    def get_timeouts_used(self, team_id: int) -> int:
        """
        Get number of timeouts used by a team this half.

        Args:
            team_id: Team to check

        Returns:
            Number of timeouts used (0-3)
        """
        return 3 - self.get_timeouts_remaining(team_id)

    def to_dict(self) -> Dict:
        """Export timeout state for persistence."""
        return self.state.to_dict()