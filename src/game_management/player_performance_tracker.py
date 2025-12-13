"""
Player Performance Tracker - Hot/Cold Streak System

Tracks per-player performance streaks within a single game. Players develop
hot/cold states based on consecutive successes/failures that affect their
performance modifiers.

Streaks:
- 4-5 consecutive successes → ON_FIRE (+15% performance boost)
- 4-5 consecutive failures → ICE_COLD (-15% performance penalty)
- Breaking the streak returns to NEUTRAL (1.0x modifier)

NOTE: Streaks reset at the start of each game (no carryover between games)
"""

from enum import Enum
from typing import Dict, Optional


class PerformanceState(Enum):
    """Player performance state based on recent streak"""
    NEUTRAL = "neutral"      # 1.0x modifier (default)
    ON_FIRE = "on_fire"      # 1.15x modifier (+15% boost)
    ICE_COLD = "ice_cold"    # 0.85x modifier (-15% penalty)


class PlayerPerformanceTracker:
    """
    Tracks per-player hot/cold streaks within a single game.

    Usage:
        tracker = PlayerPerformanceTracker()

        # After successful play
        state = tracker.record_success(player_id=7)
        if state == PerformanceState.ON_FIRE:
            print("Player is on fire!")

        # Get performance modifier
        modifier = tracker.get_modifier(player_id=7)  # Returns 0.85, 1.0, or 1.15

        # Reset at game start
        tracker.reset_all()
    """

    def __init__(self):
        """Initialize tracker with empty player states"""
        # {player_id: {"state": PerformanceState, "streak": int}}
        # streak > 0 = consecutive successes, streak < 0 = consecutive failures
        self.player_states: Dict[int, Dict] = {}

    def record_success(self, player_id: int) -> PerformanceState:
        """
        Record successful play for player, update streak.

        Args:
            player_id: Unique player identifier

        Returns:
            Updated PerformanceState for the player
        """
        if player_id not in self.player_states:
            self.player_states[player_id] = {
                "state": PerformanceState.NEUTRAL,
                "streak": 0
            }

        player_data = self.player_states[player_id]

        # If coming off failure streak, reset to neutral
        if player_data["streak"] < 0:
            player_data["streak"] = 1
            player_data["state"] = PerformanceState.NEUTRAL
        else:
            # Continue success streak
            player_data["streak"] += 1

        # Check for ON_FIRE threshold (4+ consecutive successes)
        if player_data["streak"] >= 4:
            player_data["state"] = PerformanceState.ON_FIRE

        return player_data["state"]

    def record_failure(self, player_id: int) -> PerformanceState:
        """
        Record failed play for player, update streak.

        Args:
            player_id: Unique player identifier

        Returns:
            Updated PerformanceState for the player
        """
        if player_id not in self.player_states:
            self.player_states[player_id] = {
                "state": PerformanceState.NEUTRAL,
                "streak": 0
            }

        player_data = self.player_states[player_id]

        # If coming off success streak, reset to neutral
        if player_data["streak"] > 0:
            player_data["streak"] = -1
            player_data["state"] = PerformanceState.NEUTRAL
        else:
            # Continue failure streak
            player_data["streak"] -= 1

        # Check for ICE_COLD threshold (4+ consecutive failures)
        if player_data["streak"] <= -4:
            player_data["state"] = PerformanceState.ICE_COLD

        return player_data["state"]

    def get_modifier(self, player_id: int) -> float:
        """
        Get performance modifier for player.

        Args:
            player_id: Unique player identifier

        Returns:
            Performance modifier (0.85 for ICE_COLD, 1.0 for NEUTRAL, 1.15 for ON_FIRE)
        """
        if player_id not in self.player_states:
            return 1.0

        state = self.player_states[player_id]["state"]

        if state == PerformanceState.ON_FIRE:
            return 1.15
        elif state == PerformanceState.ICE_COLD:
            return 0.85
        else:
            return 1.0

    def get_state(self, player_id: int) -> PerformanceState:
        """
        Get current performance state for player.

        Args:
            player_id: Unique player identifier

        Returns:
            Current PerformanceState (NEUTRAL if player not tracked)
        """
        if player_id not in self.player_states:
            return PerformanceState.NEUTRAL
        return self.player_states[player_id]["state"]

    def get_streak(self, player_id: int) -> int:
        """
        Get current streak count for player.

        Args:
            player_id: Unique player identifier

        Returns:
            Streak count (positive = successes, negative = failures, 0 = no streak)
        """
        if player_id not in self.player_states:
            return 0
        return self.player_states[player_id]["streak"]

    def reset_all(self):
        """
        Reset all player streaks.

        Called at the start of each game to prevent carryover between games.
        """
        self.player_states = {}

    def __repr__(self):
        """Debug representation showing all tracked players"""
        return f"PlayerPerformanceTracker({len(self.player_states)} players tracked)"
