"""
Play duration calculation for realistic clock management.

Models realistic time consumption for different play types and offensive tempos.
Based on NFL average play durations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import random


class PlayType(Enum):
    """Play outcome types affecting duration."""
    INCOMPLETE_PASS = "incomplete"
    COMPLETE_PASS_INBOUNDS = "complete_inbounds"
    COMPLETE_PASS_OOB = "complete_oob"
    RUN_PLAY = "run"
    SACK = "sack"
    PENALTY = "penalty"
    TIMEOUT = "timeout"
    SPIKE = "spike"
    FIELD_GOAL = "field_goal"
    PUNT = "punt"
    KICKOFF = "kickoff"


class OffensiveTempo(Enum):
    """Offensive tempo affecting play speed."""
    NORMAL = "normal"
    HURRY_UP = "hurry_up"
    TWO_MINUTE = "two_minute"
    SLOW = "slow"  # Running clock, control game


@dataclass
class PlayDurationConfig:
    """Configuration for play duration calculations."""

    # Base durations (seconds) - NFL averages
    INCOMPLETE_PASS: int = 6
    COMPLETE_PASS_INBOUNDS: int = 7
    COMPLETE_PASS_OOB: int = 6
    RUN_PLAY: int = 8
    SACK: int = 6
    PENALTY: int = 10
    TIMEOUT: int = 100  # NFL timeout = 1:40
    SPIKE: int = 3
    FIELD_GOAL: int = 5
    PUNT: int = 5
    KICKOFF: int = 5

    # Tempo multipliers
    HURRY_UP_MULTIPLIER: float = 0.6   # 40% faster
    TWO_MINUTE_MULTIPLIER: float = 0.5  # 50% faster
    SLOW_MULTIPLIER: float = 1.2        # 20% slower

    # Variance (±20% randomness)
    VARIANCE_PCT: float = 0.2


class PlayDuration:
    """Calculate realistic play duration for clock management."""

    config = PlayDurationConfig()

    @classmethod
    def calculate_duration(
        cls,
        play_type: str,
        tempo: str = "normal",
        clock_should_stop: bool = False,
        apply_variance: bool = True
    ) -> int:
        """
        Calculate seconds elapsed for this play.

        Args:
            play_type: Type of play (from PlayType enum values)
            tempo: Offensive tempo (from OffensiveTempo enum values)
            clock_should_stop: Whether clock stops after play
            apply_variance: Add randomness (±20%)

        Returns:
            Seconds elapsed (integer)
        """
        # Get base duration
        base_duration = cls._get_base_duration(play_type)

        # Apply tempo modifier
        tempo_multiplier = cls._get_tempo_multiplier(tempo)
        adjusted_duration = base_duration * tempo_multiplier

        # Apply variance
        if apply_variance:
            variance = random.uniform(
                -cls.config.VARIANCE_PCT,
                cls.config.VARIANCE_PCT
            )
            adjusted_duration *= (1.0 + variance)

        # Round to integer
        duration = max(1, int(adjusted_duration))

        return duration

    @classmethod
    def _get_base_duration(cls, play_type: str) -> int:
        """Get base duration for play type."""
        duration_map = {
            "incomplete": cls.config.INCOMPLETE_PASS,
            "complete_inbounds": cls.config.COMPLETE_PASS_INBOUNDS,
            "complete_oob": cls.config.COMPLETE_PASS_OOB,
            "run": cls.config.RUN_PLAY,
            "sack": cls.config.SACK,
            "penalty": cls.config.PENALTY,
            "timeout": cls.config.TIMEOUT,
            "spike": cls.config.SPIKE,
            "field_goal": cls.config.FIELD_GOAL,
            "punt": cls.config.PUNT,
            "kickoff": cls.config.KICKOFF,
        }

        return duration_map.get(play_type, cls.config.RUN_PLAY)

    @classmethod
    def _get_tempo_multiplier(cls, tempo: str) -> float:
        """Get tempo multiplier."""
        if tempo == "hurry_up":
            return cls.config.HURRY_UP_MULTIPLIER
        elif tempo == "two_minute":
            return cls.config.TWO_MINUTE_MULTIPLIER
        elif tempo == "slow":
            return cls.config.SLOW_MULTIPLIER
        else:
            return 1.0  # Normal tempo

    @classmethod
    def should_clock_stop(
        cls,
        play_type: str,
        out_of_bounds: bool = False,
        timeout_called: bool = False,
        penalty_stops_clock: bool = False,
        is_spike: bool = False,
        first_down: bool = False,
        under_two_minutes: bool = False
    ) -> bool:
        """
        Determine if clock stops after this play.

        NFL clock rules:
        - Incomplete pass: Clock stops
        - Out of bounds: Clock stops
        - Timeout: Clock stops
        - Spike: Clock stops
        - Penalty (some): Clock stops
        - First down (final 2 min): Clock stops briefly
        - Score: Clock stops

        Args:
            play_type: Type of play
            out_of_bounds: Ball carrier went out of bounds
            timeout_called: Team called timeout
            penalty_stops_clock: Penalty type stops clock
            is_spike: QB spike play
            first_down: Play resulted in first down
            under_two_minutes: Less than 2 minutes remaining

        Returns:
            True if clock stops
        """
        # Explicit clock-stopping events
        if timeout_called or is_spike:
            return True

        # Incomplete pass always stops clock
        if play_type == "incomplete":
            return True

        # Out of bounds stops clock
        if out_of_bounds:
            return True

        # Some penalties stop clock
        if penalty_stops_clock:
            return True

        # First down in final 2 minutes (clock briefly stops to reset chains)
        if first_down and under_two_minutes:
            return True

        # Special plays that stop clock
        if play_type in ["field_goal", "punt", "kickoff"]:
            return True

        return False