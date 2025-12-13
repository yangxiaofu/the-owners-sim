"""
QB Spike Play Simulation for Clock Management.

Models realistic spike play execution in two-minute drill situations.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

from ..core.play_result import PlayResult
from ..play_types.offensive_types import OffensivePlayType

logger = logging.getLogger(__name__)


class SpikePlaySimulator:
    """
    Simulates QB spike plays.

    NFL Rules for Spike Plays:
    - QB must be under center or in shotgun
    - Ball must be spiked immediately after snap
    - Clock stops (handled by PlayDuration)
    - Consumes one down
    - No yards gained or lost
    - Cannot spike on 4th down
    """

    def simulate_spike(self) -> PlayResult:
        """
        Simulate QB spike play.

        Returns:
            PlayResult with spike outcome (0 yards, down consumed, clock stopped)
        """
        logger.info("Executing spike play - clock management")

        return PlayResult(
            outcome="spike",
            yards=0,  # Spike gains no yards
            points=0,
            time_elapsed=3.0,  # ~3 seconds for spike (defined in PlayDuration.SPIKE)
            is_scoring_play=False,
            is_turnover=False,
            achieved_first_down=False,
            change_of_possession=False,
            # Clock stops after spike (handled by PlayDuration.should_clock_stop(is_spike=True))
            # Down is consumed (handled by DriveManager)
        )

    def can_spike(self, down: int, quarter: int) -> bool:
        """
        Check if spike is legal.

        Args:
            down: Current down (1-4)
            quarter: Current quarter

        Returns:
            True if spike is allowed
        """
        # Cannot spike on 4th down (would lose possession)
        if down == 4:
            logger.warning("Cannot spike on 4th down")
            return False

        return True