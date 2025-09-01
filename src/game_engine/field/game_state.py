from .field_state import FieldState
from .game_clock import GameClock
from .scoreboard import Scoreboard

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
        """Update all state after a play"""
        # Update field position
        field_result = self.field.update_down(play_result.yards_gained)
        
        # Update clock
        self.clock.run_time(play_result.time_elapsed)
        
        # Handle clock stoppage
        if play_result.outcome in ["incomplete", "out_of_bounds", "penalty"]:
            self.clock.stop_clock()
        
        # Update score
        if play_result.is_score:
            if play_result.outcome == "touchdown":
                self.scoreboard.add_touchdown(self.field.possession_team_id)
                # Automatically attempt extra point (YAGNI - simple implementation)
                self._attempt_extra_point(self.field.possession_team_id)
            elif play_result.outcome == "field_goal":
                self.scoreboard.add_field_goal(self.field.possession_team_id)
            elif play_result.outcome == "safety":
                # Safety goes to the other team
                other_team = self._get_other_team_id()
                self.scoreboard.add_safety(other_team)
        
        return field_result
    
    def _attempt_extra_point(self, scoring_team_id: int):
        """
        Attempt extra point conversion after touchdown.
        
        YAGNI implementation: Simple 95% success rate.
        """
        import random
        
        extra_point_success_rate = 0.95
        if random.random() < extra_point_success_rate:
            self.scoreboard.add_extra_point(scoring_team_id)
    
    def _get_other_team_id(self):
        """Get the ID of the team that doesn't have possession"""
        # This will need to be implemented based on your team management
        # For now, just placeholder logic
        if self.field.possession_team_id == self.scoreboard.home_team_id:
            return self.scoreboard.away_team_id
        return self.scoreboard.home_team_id