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
    went_out_of_bounds: bool = False     # Whether ball carrier went OOB (stops clock)
    penalty_occurred: bool = False       # Whether there was a penalty
    penalty_yards: int = 0               # Net penalty yards (positive = benefit offense)
    play_negated: bool = False           # Whether penalty negates the play (replay down)
    
    # Possession tracking (new comprehensive system)
    change_of_possession: bool = False   # Whether possession changed teams (broader than turnover)
    
    # Punt-specific tracking (enhanced two-stage system)
    punt_distance: Optional[int] = None  # Stage 1: How far punt traveled
    return_yards: Optional[int] = None   # Stage 2: How far returner advanced
    hang_time: Optional[float] = None    # Stage 1: Punt hang time for coverage
    coverage_pressure: Optional[float] = None  # Stage 1: Coverage quality (0.0-1.0)
    
    # Player statistics field (from core PlayResult)
    player_stats_summary: Optional[object] = None  # Player statistics summary object

    # NEW: Post-play state snapshot (set by DriveManager after processing)
    down_after_play: Optional[int] = None        # Down for NEXT play (1-4)
    distance_after_play: Optional[int] = None    # Yards to go for NEXT play
    field_position_after_play: Optional[int] = None  # Yard line for NEXT play (0-100)
    possession_team_id: Optional[int] = None     # Team with possession after play

    # Penalty enforcement result (set by PenaltyEngine, used by DriveManager)
    enforcement_result: Optional[object] = None  # EnforcementResult from penalty_enforcement module

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

        # Get leaders first to determine play type
        rushing_leader = self.player_stats_summary.get_rushing_leader()
        passing_leader = self.player_stats_summary.get_passing_leader()
        receiving_leader = self.player_stats_summary.get_receiving_leader()

        # Check for scramble plays - QB ran instead of throwing
        is_scramble = 'scramble' in str(self.outcome).lower()

        # Determine if this is a run play (has rushing stats, no passing stats)
        # Scrambles count as run plays for player display purposes
        is_run_play = (rushing_leader is not None and passing_leader is None) or is_scramble

        # Check if this is a sack - multiple detection methods
        # Only applies to PASS plays, never run plays
        # Must align with box_score_dialog.py sack detection for consistency
        is_sack = not is_run_play and (
            'sack' in str(self.outcome).lower() or  # Explicit sack outcome
            (
                self.yards < 0 and
                'pass' in str(self.outcome).lower()  # Negative yard pass = sack
            ) or
            (
                self.yards < 0 and
                self.player_stats_summary.get_pass_rush_leader() and
                self.player_stats_summary.get_pass_rush_leader().sacks > 0
            )
        )

        # Ball carrier for run plays (including scrambles)
        if is_scramble:
            # For scrambles, QB might be tracked as rushing_leader OR passing_leader
            if rushing_leader:
                qb_name = self._extract_last_name(rushing_leader.player_name)
                players.append(qb_name)
            elif passing_leader:
                qb_name = self._extract_last_name(passing_leader.player_name)
                players.append(qb_name)
        elif rushing_leader:
            runner_name = self._extract_last_name(rushing_leader.player_name)
            players.append(runner_name)

        # Check if this is an interception
        is_interception = self.outcome and 'interception' in str(self.outcome).lower()

        # Passer and receiver for pass plays
        # On sacks, only show QB - no receiver (they didn't catch anything)
        # Skip for scrambles - QB already added above
        if is_scramble:
            pass  # Already handled above
        elif is_sack:
            if passing_leader:
                passer_name = self._extract_last_name(passing_leader.player_name)
                players.append(passer_name)
        elif passing_leader and receiving_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            receiver_name = self._extract_last_name(receiving_leader.player_name)
            players.append(f"{passer_name} to {receiver_name}")
        elif passing_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            players.append(passer_name)

        # Interceptor for interceptions
        if is_interception:
            pass_defense_leader = self.player_stats_summary.get_pass_defense_leader()
            if pass_defense_leader:
                interceptor_name = self._extract_last_name(pass_defense_leader.player_name)
                players.append(f"intercepted by {interceptor_name}")

        # Leading tackler for defense - ONLY if not a scoring play
        # You can't tackle someone who scored a touchdown
        is_scoring = self.is_scoring_play or self.points == 6
        leading_tackler = self.player_stats_summary.get_leading_tackler()
        if leading_tackler and not is_scoring:
            tackler_name = self._extract_last_name(leading_tackler.player_name)
            # ONLY use "sacked by" on pass plays with sacks, NEVER on run plays
            if is_sack and not is_run_play:
                players.append(f"sacked by {tackler_name}")
            else:
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
        if "Starting" in full_name or "Backup" in full_name:
            return full_name.split()[-1]  # Return position (QB, RB, etc.)

        parts = full_name.split()
        if len(parts) < 2:
            return full_name

        # Common NFL name suffixes - preserve these with the last name
        suffixes = {'Jr.', 'Jr', 'Sr.', 'Sr', 'II', 'III', 'IV', 'V'}

        # If last word is a suffix, include the word before it
        # e.g., "Patrick Mahomes II" -> "Mahomes II", not "II"
        if parts[-1] in suffixes and len(parts) >= 2:
            return f"{parts[-2]} {parts[-1]}"

        return parts[-1]
    
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
        yards=40,  # ✅ FIX: Reasonable default net punt yards
        time_elapsed=25.0,
        is_punt=True,  # Critical: preserve punt context for drive manager
        penalty_occurred=False,
        punt_distance=40,  # ✅ FIX: Default punt distance for display
        change_of_possession=True  # ✅ FIX: Punts change possession
    )