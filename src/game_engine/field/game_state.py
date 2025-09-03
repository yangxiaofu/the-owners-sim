from game_engine.field.field_state import FieldState
from game_engine.field.game_clock import GameClock
from game_engine.field.scoreboard import Scoreboard

class GameState:
    """Unified game state coordinator"""
    
    def __init__(self, is_playoff_game: bool = False):
        self.field = FieldState()
        self.clock = GameClock(is_playoff_game)
        self.scoreboard = Scoreboard()
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        # Check clock-based game ending first
        clock_game_over = self.clock.is_game_over()
        
        # In overtime, game ends immediately if someone scores
        if self.clock.quarter >= 5:  # In overtime
            if not self.scoreboard.is_tied():
                return True  # Game ends when team scores in OT
        
        # Otherwise, use clock-based logic
        return clock_game_over
    
    def get_context_for_blocking(self) -> dict:
        """Get context information for blocking strategies"""
        return {
            'down': self.field.down,
            'yards_to_go': self.field.yards_to_go,
            'field_position': self.field.field_position,
            'quarter': self.clock.quarter,
            'time_remaining': self.clock.clock
        }
    
    def update_after_play(self, play_result) -> str:
        """LEGACY METHOD - DEPRECATED
        
        WARNING: This method is deprecated and should not be used.
        All game state updates now go through the GameStateManager and 
        state transition system to prevent dual-system conflicts.
        
        Use: GameStateManager.process_play_result() instead
        """
        # SAFETY: Prevent accidental usage of this deprecated method
        import warnings
        warnings.warn(
            "update_after_play() is deprecated. Use GameStateManager.process_play_result() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        print(f"🚨 DEPRECATED: update_after_play() called! This should use GameStateManager instead.")
        
        # Only handle non-scoring updates to prevent dual-system conflicts
        field_result = self.field.update_down(play_result.yards_gained)
        self.clock.run_time(play_result.time_elapsed)
        
        if play_result.outcome in ["incomplete", "out_of_bounds", "penalty"]:
            self.clock.stop_clock()
        
        # SCORING INTENTIONALLY REMOVED: Handled by state transition system
        # This prevents the dual scoring system bug that caused 1-point scores
        
        return field_result
    
    # _attempt_extra_point() REMOVED: This legacy method was part of the old
    # dual scoring system that caused 1-point bugs. Extra point attempts are now
    # handled atomically by the state transition system with coaching decisions.
    
    # _get_other_team_id() REMOVED: This was only used by the legacy scoring system.
    # The state transition system uses proper team resolution via TransitionContext.