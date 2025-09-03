"""
Field Position Calculator - Pure Field State Calculations

This module contains pure functions to calculate field position changes, downs, 
and yards to go based on play results. All functions are side-effect free.

Based on the current game_orchestrator.py field update logic (lines 174, 230).
"""

from typing import Optional
from dataclasses import dataclass
from game_engine.plays.data_structures import PlayResult
# Import the proper FieldTransition from data_structures
from game_engine.state_transitions.data_structures import FieldTransition


class FieldCalculator:
    """
    Pure calculator for field position, downs, and yards to go changes.
    
    All methods are pure functions that calculate what the new field state
    should be based on the play result and current field state.
    """
    
    def calculate_field_changes(self, play_result: PlayResult, game_state) -> FieldTransition:
        """
        Calculate all field-related changes based on play result.
        
        This replicates the logic from game_orchestrator.py field updates
        but as a pure calculation function.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state with field information
            
        Returns:
            FieldTransition with all calculated field changes
        """
        current_field = game_state.field
        
        # Store previous values for context
        previous_down = current_field.down
        previous_yards_to_go = current_field.yards_to_go
        previous_field_position = current_field.field_position
        
        # Calculate new field position based on yards gained
        new_field_position = self._calculate_new_field_position(
            current_field.field_position,
            play_result.yards_gained
        )
        
        # Check for touchdown - only for plays that actually cross into the end zone
        # or are explicitly marked as touchdown scoring plays (not field goals)
        is_touchdown = ((new_field_position >= 100 and 
                        previous_field_position < 100) or
                       (play_result.is_score and play_result.outcome == "touchdown"))
        
        # Check for safety  
        is_safety = new_field_position <= 0
        
        # Handle special cases first
        # Handle field goals - position stays unchanged (ball goes OVER posts, not through)
        if play_result.play_type == "field_goal":
            return FieldTransition(
                new_yard_line=previous_field_position,  # Field position unchanged
                old_yard_line=previous_field_position,
                yards_gained=0,  # Field goals don't advance ball position
                new_down=1,  # Field goal attempts reset down to 1st
                old_down=previous_down,
                new_yards_to_go=10,  # Reset to 10 yards for new possession
                old_yards_to_go=previous_yards_to_go,
                first_down_achieved=False,  # Field goals don't achieve first downs
                in_end_zone=False,
                at_goal_line=previous_field_position == 100
            )
        
        if is_touchdown:
            return FieldTransition(
                new_yard_line=100,
                old_yard_line=previous_field_position,
                yards_gained=play_result.yards_gained,
                new_down=1,
                old_down=previous_down,
                new_yards_to_go=10,
                old_yards_to_go=previous_yards_to_go,
                first_down_achieved=True,  # Touchdown definitely achieves first down
                in_end_zone=True,
                at_goal_line=True
            )
        
        if is_safety:
            return FieldTransition(
                new_yard_line=0,
                old_yard_line=previous_field_position,
                yards_gained=play_result.yards_gained,
                new_down=1,
                old_down=previous_down,
                new_yards_to_go=10,
                old_yards_to_go=previous_yards_to_go,
                first_down_achieved=False,
                safety_situation=True,
                in_end_zone=True
            )
        
        # Calculate new down and yards to go for normal plays
        new_down, new_yards_to_go, is_first_down, turnover_on_downs = self._calculate_down_and_distance(
            current_field.down,
            current_field.yards_to_go,
            play_result.yards_gained,
            new_field_position
        )
        
        return FieldTransition(
            new_yard_line=new_field_position,
            old_yard_line=previous_field_position,
            yards_gained=play_result.yards_gained,
            new_down=new_down,
            old_down=previous_down,
            new_yards_to_go=new_yards_to_go,
            old_yards_to_go=previous_yards_to_go,
            first_down_achieved=is_first_down,
            in_red_zone=(new_field_position >= 80),
            in_goal_to_go=(100 - new_field_position <= 10)
        )
    
    def _calculate_new_field_position(self, current_position: int, yards_gained: int) -> int:
        """
        Calculate new field position based on yards gained.
        
        Args:
            current_position: Current yard line (0-100)
            yards_gained: Yards gained/lost on play (can be negative)
            
        Returns:
            New field position clamped to valid range (0-100)
        """
        new_position = current_position + yards_gained
        
        # Clamp to valid field bounds
        return max(0, min(100, new_position))
    
    def _calculate_down_and_distance(self, current_down: int, yards_to_go: int, 
                                   yards_gained: int, field_position: int) -> tuple[int, int, bool, bool]:
        """
        Calculate new down and yards to go based on play result.
        
        This replicates the logic from FieldState.update_down() method.
        
        Args:
            current_down: Current down (1-4)
            yards_to_go: Yards needed for first down
            yards_gained: Yards gained on play
            field_position: Current field position for goal line calculations
            
        Returns:
            Tuple of (new_down, new_yards_to_go, is_first_down, turnover_on_downs)
        """
        remaining_yards = yards_to_go - yards_gained
        
        # Check for first down
        if remaining_yards <= 0:
            # First down achieved - use goal line logic to handle "goal to go" situations
            # This prevents NFL.DISTANCE.004 validation errors when close to end zone
            proper_yards_to_go = self.calculate_yards_for_first_down(field_position, 10)
            return 1, proper_yards_to_go, True, False
        
        # Normal down progression
        new_down = current_down + 1
        
        # Check for turnover on downs
        if new_down > 4:
            # Don't return invalid down - keep current down and signal turnover
            # The possession calculator will handle the actual possession change
            return current_down, remaining_yards, False, True
        
        # Apply goal line logic even for non-first-down situations to prevent NFL.DISTANCE.004
        goal_line_yards_to_go = self.calculate_yards_for_first_down(field_position, remaining_yards)
        return new_down, goal_line_yards_to_go, False, False
    
    def is_goal_line_situation(self, field_position: int, yards_to_go: int) -> bool:
        """
        Check if this is a goal line situation (inside 10 yard line).
        
        Args:
            field_position: Current yard line
            yards_to_go: Yards needed for first down
            
        Returns:
            True if in goal line situation
        """
        return field_position >= 90 or (100 - field_position) < yards_to_go
    
    def is_red_zone_situation(self, field_position: int) -> bool:
        """
        Check if this is a red zone situation (inside 20 yard line).
        
        Args:
            field_position: Current yard line
            
        Returns:
            True if in red zone
        """
        return field_position >= 80
    
    def calculate_yards_for_first_down(self, field_position: int, yards_to_go: int) -> int:
        """
        Calculate actual yards needed for first down considering goal line.

        Args:
            field_position: Current yard line
            yards_to_go: Normal yards to go

        Returns:
            Actual yards needed (may be less than yards_to_go near goal line)
        """
        yards_to_endzone = 100 - field_position
        return min(yards_to_go, yards_to_endzone)