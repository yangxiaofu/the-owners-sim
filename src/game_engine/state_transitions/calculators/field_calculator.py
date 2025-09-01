"""
Field Position Calculator - Pure Field State Calculations

This module contains pure functions to calculate field position changes, downs, 
and yards to go based on play results. All functions are side-effect free.

Based on the current game_orchestrator.py field update logic (lines 174, 230).
"""

from typing import Optional
from dataclasses import dataclass
from ...plays.data_structures import PlayResult


@dataclass(frozen=True)
class FieldTransition:
    """
    Immutable representation of field position changes.
    
    Contains all field-related changes that should be applied after a play.
    """
    new_field_position: Optional[int] = None  # New yard line position (0-100)
    new_down: Optional[int] = None            # New down number (1-4)
    new_yards_to_go: Optional[int] = None     # New yards needed for first down
    is_first_down: bool = False               # Whether play resulted in first down
    is_touchdown: bool = False                # Whether play resulted in touchdown
    is_safety: bool = False                   # Whether play resulted in safety
    turnover_on_downs: bool = False           # Whether down limit exceeded
    
    # Additional context for validation/debugging
    yards_gained_on_play: int = 0             # Actual yards gained this play
    previous_down: Optional[int] = None       # Down before the play
    previous_yards_to_go: Optional[int] = None # Yards to go before the play
    previous_field_position: Optional[int] = None # Field position before the play


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
        
        # Check for touchdown
        is_touchdown = new_field_position >= 100
        
        # Check for safety  
        is_safety = new_field_position <= 0
        
        # Handle special cases first
        if is_touchdown:
            return FieldTransition(
                new_field_position=100,
                new_down=1,
                new_yards_to_go=10,
                is_first_down=False,
                is_touchdown=True,
                is_safety=False,
                turnover_on_downs=False,
                yards_gained_on_play=play_result.yards_gained,
                previous_down=previous_down,
                previous_yards_to_go=previous_yards_to_go,
                previous_field_position=previous_field_position
            )
        
        if is_safety:
            return FieldTransition(
                new_field_position=0,
                new_down=1,
                new_yards_to_go=10,
                is_first_down=False,
                is_touchdown=False,
                is_safety=True,
                turnover_on_downs=False,
                yards_gained_on_play=play_result.yards_gained,
                previous_down=previous_down,
                previous_yards_to_go=previous_yards_to_go,
                previous_field_position=previous_field_position
            )
        
        # Calculate new down and yards to go for normal plays
        new_down, new_yards_to_go, is_first_down, turnover_on_downs = self._calculate_down_and_distance(
            current_field.down,
            current_field.yards_to_go,
            play_result.yards_gained
        )
        
        return FieldTransition(
            new_field_position=new_field_position,
            new_down=new_down,
            new_yards_to_go=new_yards_to_go,
            is_first_down=is_first_down,
            is_touchdown=False,
            is_safety=False,
            turnover_on_downs=turnover_on_downs,
            yards_gained_on_play=play_result.yards_gained,
            previous_down=previous_down,
            previous_yards_to_go=previous_yards_to_go,
            previous_field_position=previous_field_position
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
                                   yards_gained: int) -> tuple[int, int, bool, bool]:
        """
        Calculate new down and yards to go based on play result.
        
        This replicates the logic from FieldState.update_down() method.
        
        Args:
            current_down: Current down (1-4)
            yards_to_go: Yards needed for first down
            yards_gained: Yards gained on play
            
        Returns:
            Tuple of (new_down, new_yards_to_go, is_first_down, turnover_on_downs)
        """
        remaining_yards = yards_to_go - yards_gained
        
        # Check for first down
        if remaining_yards <= 0:
            # First down achieved
            return 1, 10, True, False
        
        # Normal down progression
        new_down = current_down + 1
        
        # Check for turnover on downs
        if new_down > 4:
            return new_down, remaining_yards, False, True
        
        return new_down, remaining_yards, False, False
    
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