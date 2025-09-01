"""
Clock Calculator - Pure Time Management Calculations

This module contains pure functions to calculate clock changes based on 
play results. Handles time elapsed, clock stoppage, and quarter advancement.

Based on the game_orchestrator.py clock logic (lines 160-161, 225-226) 
and game_state.py clock updates (lines 33-37).
"""

from typing import Optional
from dataclasses import dataclass
from ...plays.data_structures import PlayResult


@dataclass(frozen=True)
class ClockTransition:
    """
    Immutable representation of clock changes.
    
    Contains all clock-related changes that should be applied after a play.
    """
    time_elapsed: int = 0                         # Seconds to subtract from clock
    should_stop_clock: bool = False               # Whether clock should stop
    should_advance_quarter: bool = False          # Whether to advance quarter
    new_quarter: Optional[int] = None             # New quarter number if advancing
    new_clock_time: Optional[int] = None          # New clock time after changes
    
    # Clock stoppage reasons
    clock_stop_reason: Optional[str] = None       # Why clock stopped
    
    # Context information
    previous_clock_time: Optional[int] = None     # Clock time before play
    previous_quarter: Optional[int] = None        # Quarter before play
    is_two_minute_warning: bool = False           # Whether this triggers 2-minute warning
    is_end_of_half: bool = False                  # Whether this ends a half
    is_end_of_game: bool = False                  # Whether this ends the game


class ClockCalculator:
    """
    Pure calculator for clock and time management changes.
    
    All methods calculate what clock changes should occur based on
    play results and current game state, without actually changing anything.
    """
    
    def calculate_clock_changes(self, play_result: PlayResult, game_state) -> ClockTransition:
        """
        Calculate clock changes based on play result.
        
        This replicates the logic from game_orchestrator.py and game_state.py
        clock management as pure calculation functions.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state with clock information
            
        Returns:
            ClockTransition with calculated clock changes
        """
        current_clock = game_state.clock
        current_time = current_clock.clock
        current_quarter = current_clock.quarter
        
        # Calculate time elapsed from play
        time_elapsed = play_result.time_elapsed
        
        # Calculate new clock time
        new_clock_time = current_time - time_elapsed
        
        # Determine if clock should stop
        should_stop_clock, stop_reason = self._should_stop_clock(play_result)
        
        # Check for quarter advancement
        should_advance_quarter = new_clock_time <= 0
        new_quarter = None
        if should_advance_quarter:
            new_quarter = self._calculate_new_quarter(current_quarter)
            # Reset clock for new quarter
            new_clock_time = self._get_quarter_time(new_quarter)
        
        # Check for special timing situations
        is_two_minute_warning = self._is_two_minute_warning(current_time, new_clock_time, current_quarter)
        is_end_of_half = self._is_end_of_half(current_quarter, should_advance_quarter)
        is_end_of_game = self._is_end_of_game(current_quarter, should_advance_quarter)
        
        return ClockTransition(
            time_elapsed=time_elapsed,
            should_stop_clock=should_stop_clock,
            should_advance_quarter=should_advance_quarter,
            new_quarter=new_quarter,
            new_clock_time=max(0, new_clock_time),  # Don't go negative
            clock_stop_reason=stop_reason,
            previous_clock_time=current_time,
            previous_quarter=current_quarter,
            is_two_minute_warning=is_two_minute_warning,
            is_end_of_half=is_end_of_half,
            is_end_of_game=is_end_of_game
        )
    
    def _should_stop_clock(self, play_result: PlayResult) -> tuple[bool, Optional[str]]:
        """
        Determine if the clock should stop based on play outcome.
        
        Based on game_state.py lines 36-37.
        
        Returns:
            Tuple of (should_stop, reason)
        """
        # Clock stops for incomplete passes, out of bounds, penalties
        if play_result.outcome in ["incomplete", "out_of_bounds", "penalty"]:
            return True, play_result.outcome
        
        # Clock stops for turnovers
        if play_result.is_turnover:
            return True, "turnover"
        
        # Clock stops for scores
        if play_result.is_score:
            return True, "score"
        
        # Clock stops for timeouts (if that's tracked in PlayResult)
        if hasattr(play_result, 'timeout_called') and play_result.timeout_called:
            return True, "timeout"
        
        # Clock stops for first downs (in some situations)
        if hasattr(play_result, 'first_down') and play_result.first_down:
            # Clock typically stops briefly for first down measurement
            return True, "first_down"
        
        # Clock runs normally
        return False, None
    
    def _calculate_new_quarter(self, current_quarter: int) -> int:
        """
        Calculate what the new quarter should be.
        
        Args:
            current_quarter: Current quarter (1-4, or overtime)
            
        Returns:
            New quarter number
        """
        if current_quarter < 4:
            return current_quarter + 1
        else:
            # Overtime - this would need more complex logic
            return current_quarter + 1  # Simple overtime increment
    
    def _get_quarter_time(self, quarter: int) -> int:
        """
        Get the starting time for a given quarter.
        
        Args:
            quarter: Quarter number
            
        Returns:
            Starting time in seconds for that quarter
        """
        if quarter <= 4:
            return 900  # 15 minutes = 900 seconds for regular quarters
        else:
            return 900  # 15 minutes for overtime (NFL rules vary)
    
    def _is_two_minute_warning(self, previous_time: int, new_time: int, quarter: int) -> bool:
        """
        Check if this play triggers the two-minute warning.
        
        Args:
            previous_time: Clock time before play
            new_time: Clock time after play
            quarter: Current quarter
            
        Returns:
            True if this triggers two-minute warning
        """
        # Two-minute warning occurs at end of 2nd and 4th quarters
        if quarter not in [2, 4]:
            return False
        
        # Check if we crossed the 2:00 mark
        return previous_time > 120 and new_time <= 120
    
    def _is_end_of_half(self, quarter: int, advancing_quarter: bool) -> bool:
        """
        Check if this ends a half.
        
        Args:
            quarter: Current quarter
            advancing_quarter: Whether we're advancing to next quarter
            
        Returns:
            True if this ends a half
        """
        if not advancing_quarter:
            return False
        
        # End of 2nd quarter ends first half
        # End of 4th quarter ends second half (regulation)
        return quarter in [2, 4]
    
    def _is_end_of_game(self, quarter: int, advancing_quarter: bool) -> bool:
        """
        Check if this ends the game.
        
        Args:
            quarter: Current quarter
            advancing_quarter: Whether we're advancing to next quarter
            
        Returns:
            True if this could end the game
        """
        if not advancing_quarter:
            return False
        
        # Game ends after 4th quarter (unless overtime needed)
        # This is simplified - real logic would check score differential
        return quarter >= 4
    
    def calculate_remaining_time_in_quarter(self, current_time: int) -> str:
        """
        Format remaining time in quarter as MM:SS string.
        
        Args:
            current_time: Current clock time in seconds
            
        Returns:
            Formatted time string
        """
        minutes = current_time // 60
        seconds = current_time % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def calculate_time_usage_rate(self, total_time_elapsed: int, plays_run: int) -> float:
        """
        Calculate average time per play.
        
        Args:
            total_time_elapsed: Total time used in game
            plays_run: Total number of plays
            
        Returns:
            Average seconds per play
        """
        if plays_run == 0:
            return 0.0
        return total_time_elapsed / plays_run
    
    def is_hurry_up_situation(self, time_remaining: int, quarter: int, score_difference: int) -> bool:
        """
        Determine if team should be in hurry-up mode.
        
        Args:
            time_remaining: Time left in quarter/game
            quarter: Current quarter
            score_difference: Score difference (positive if ahead)
            
        Returns:
            True if team should hurry up
        """
        # Hurry up in last 2 minutes if losing
        if quarter >= 4 and time_remaining <= 120 and score_difference < 0:
            return True
        
        # Hurry up if very little time left and need to score
        if time_remaining <= 60 and score_difference <= 0:
            return True
        
        return False
    
    def should_kneel_down(self, time_remaining: int, quarter: int, score_difference: int, 
                         downs_remaining: int) -> bool:
        """
        Determine if team should kneel down to run out clock.
        
        Args:
            time_remaining: Time left in game
            quarter: Current quarter
            score_difference: Score difference (positive if ahead)
            downs_remaining: Downs left to work with
            
        Returns:
            True if team should kneel down
        """
        # Only kneel in 4th quarter when ahead
        if quarter != 4 or score_difference <= 0:
            return False
        
        # Kneel if time remaining is less than what can be run off with remaining downs
        # Assume ~40 seconds per kneel down
        estimated_time_to_run = downs_remaining * 40
        
        return time_remaining <= estimated_time_to_run