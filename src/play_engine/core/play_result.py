"""
Unified PlayResult - Single Source of Truth

This module provides the unified PlayResult class that serves as the single source 
of truth for all play execution results throughout the system. It combines:
- Basic play outcome data (outcome, yards, points, time)
- Rich game state tracking (scoring, turnovers, penalties, special plays)
- Player statistics integration
- Comprehensive helper methods

This eliminates the previous import conflict between core/result.py and 
drive_manager.py PlayResult classes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PlayResult:
    """
    Unified play result representing the outcome of any simulated play.
    
    This class combines functionality from both the original core PlayResult
    and the DriveManager PlayResult to provide a single, comprehensive interface.
    """
    
    # Core fields (present in both original classes)
    outcome: str = "incomplete"           # Play outcome: "rush", "pass_completion", "interception", etc.
    yards: int = 0                       # Net yards gained/lost
    points: int = 0                      # Points scored on this play  
    time_elapsed: float = 0.0            # Seconds elapsed during play
    
    # Rich game state fields (from DriveManager PlayResult)
    is_scoring_play: bool = False        # Whether this play resulted in scoring
    is_turnover: bool = False            # Whether possession changed due to turnover
    turnover_type: Optional[str] = None  # "interception", "fumble", etc.
    achieved_first_down: bool = False    # Whether this play achieved first down
    is_punt: bool = False                # Whether this was a punt play
    is_safety: bool = False              # Whether this resulted in a safety
    penalty_occurred: bool = False       # Whether there was a penalty
    penalty_yards: int = 0               # Net penalty yards (positive = benefit offense)
    
    # Possession tracking (new comprehensive system)
    change_of_possession: bool = False   # Whether possession changed teams (broader than turnover)
    
    # Punt-specific tracking (enhanced two-stage system)
    punt_distance: Optional[int] = None  # Stage 1: How far punt traveled
    return_yards: Optional[int] = None   # Stage 2: How far returner advanced
    hang_time: Optional[float] = None    # Stage 1: Punt hang time for coverage
    coverage_pressure: Optional[float] = None  # Stage 1: Coverage quality (0.0-1.0)
    
    # Player statistics field (from core PlayResult)
    player_stats_summary: Optional[object] = None  # Player statistics summary object
    
    def __str__(self):
        """String representation for debugging"""
        if self.points > 0:
            return f"PlayResult(outcome='{self.outcome}', yards={self.yards}, points={self.points}, time={self.time_elapsed}s)"
        return f"PlayResult(outcome='{self.outcome}', yards={self.yards}, time={self.time_elapsed}s)"
    
    def __repr__(self):
        """Detailed representation"""
        return self.__str__()
    
    # Methods from core PlayResult (player statistics integration)
    def has_player_stats(self) -> bool:
        """Check if player stats are available"""
        return self.player_stats_summary is not None
    
    def get_key_players(self) -> str:
        """Extract key players based on play type - returns formatted string"""
        if not self.has_player_stats():
            return ""
        
        players = []
        
        # Ball carrier for run plays
        rushing_leader = self.player_stats_summary.get_rushing_leader()
        if rushing_leader:
            runner_name = self._extract_last_name(rushing_leader.player_name)
            players.append(runner_name)
        
        # Passer and receiver for pass plays  
        passing_leader = self.player_stats_summary.get_passing_leader()
        receiving_leader = self.player_stats_summary.get_receiving_leader()
        if passing_leader and receiving_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            receiver_name = self._extract_last_name(receiving_leader.player_name)
            players.append(f"{passer_name} to {receiver_name}")
        elif passing_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            players.append(passer_name)
        
        # Leading tackler for defense
        leading_tackler = self.player_stats_summary.get_leading_tackler()
        if leading_tackler:
            tackler_name = self._extract_last_name(leading_tackler.player_name)
            players.append(f"tackled by {tackler_name}")
        
        # Kicker for field goals
        kicker_stats = self.player_stats_summary.get_kicker_stats()
        if kicker_stats:
            kicker_name = self._extract_last_name(kicker_stats.player_name)
            players.append(kicker_name)
        
        return ", ".join(players)
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extract last name from full player name for concise display"""
        # Handle names like "Cleveland Starting QB" -> "QB"
        # or "Deshaun Watson" -> "Watson"
        if "Starting" in full_name or "Backup" in full_name:
            # For generated names like "Cleveland Starting QB"
            return full_name.split()[-1]  # Return position (QB, RB, etc.)
        else:
            # For real names, return last word
            return full_name.split()[-1]
    
    # Methods from DriveManager PlayResult (game state tracking)
    def get_net_yards(self) -> int:
        """Get net yards including penalty effects"""
        return self.yards + self.penalty_yards
    
    def is_missed_field_goal(self) -> bool:
        """Check if this was a missed field goal attempt"""
        if not isinstance(self.outcome, str):
            return False
        
        # All possible missed field goal outcomes
        missed_fg_outcomes = [
            "field_goal_missed_wide_left",
            "field_goal_missed_wide_right", 
            "field_goal_missed_short",
            "field_goal_blocked"
        ]
        return self.outcome in missed_fg_outcomes


def create_failed_punt_result(error_message: str = "punt execution failed") -> 'PlayResult':
    """
    Create a PlayResult for failed punt execution that preserves punt context.
    
    This utility ensures that even when punt execution fails due to errors,
    the resulting PlayResult maintains the is_punt=True flag so the DriveManager
    can correctly classify it as a punt rather than a turnover on downs.
    
    Args:
        error_message: Description of the error that occurred
        
    Returns:
        PlayResult with proper punt failure context
    """
    # Import here to avoid circular imports
    from ..game_state.drive_manager import PuntOutcomeType
    
    return PlayResult(
        outcome=PuntOutcomeType.PUNT_EXECUTION_FAILED.value,
        yards=0,
        time_elapsed=25.0,
        is_punt=True,  # Critical: preserve punt context for drive manager
        penalty_occurred=False
    )