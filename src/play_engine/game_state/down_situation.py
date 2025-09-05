"""
Down Situation Tracking System

Handles down progression, first down detection, and turnover situations.
Maintains separation from field position - focuses purely on down/distance logic.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class DownResult(Enum):
    """Possible outcomes from down progression"""
    CONTINUE_DRIVE = "continue_drive"       # Normal down progression
    FIRST_DOWN_ACHIEVED = "first_down"      # Reset to 1st down
    TURNOVER_ON_DOWNS = "turnover_on_downs" # Failed 4th down conversion
    SCORING_DRIVE = "scoring_drive"         # Drive ended with score


@dataclass
class DownState:
    """
    Represents current down and distance situation
    
    Standard NFL down system:
    - current_down: 1-4 (1st down through 4th down)
    - yards_to_go: 1-99+ (yards needed for first down)
    - first_down_line: Yard line where first down is achieved
    """
    current_down: int                    # 1, 2, 3, or 4
    yards_to_go: int                    # Yards needed for first down (1-99+)
    first_down_line: int                # Yard line position for first down
    
    def __post_init__(self):
        """Validate down state data"""
        if not 1 <= self.current_down <= 4:
            raise ValueError(f"Invalid down: {self.current_down}. Must be 1-4.")
        if self.yards_to_go < 1:
            raise ValueError(f"Invalid yards to go: {self.yards_to_go}. Must be >= 1.")
        if not 0 <= self.first_down_line <= 100:
            raise ValueError(f"Invalid first down line: {self.first_down_line}. Must be 0-100.")
    
    def is_fourth_down(self) -> bool:
        """Check if this is 4th down (conversion or turnover situation)"""
        return self.current_down == 4
    
    def is_first_down(self) -> bool:
        """Check if this is 1st down"""
        return self.current_down == 1
    
    def is_short_yardage(self, threshold: int = 3) -> bool:
        """Check if this is a short yardage situation"""
        return self.yards_to_go <= threshold
    
    def is_long_yardage(self, threshold: int = 7) -> bool:
        """Check if this is a long yardage situation"""  
        return self.yards_to_go >= threshold


@dataclass
class DownProgressionResult:
    """
    Result of down progression processing
    
    Contains down situation changes, first down detection, and possession changes
    """
    # Down progression
    new_down_state: Optional[DownState]  # New down situation (None if possession change)
    down_result: DownResult              # Type of down progression result
    
    # First down detection
    first_down_achieved: bool = False    # Did this play achieve a first down?
    yards_past_first_down: int = 0       # Extra yards beyond first down line
    
    # Possession changes
    possession_change: bool = False      # Did possession change?
    turnover_on_downs: bool = False     # Failed 4th down conversion?
    
    # Down events
    down_events: List[str] = None       # ["first_down", "fourth_down_conversion", etc.]
    
    def __post_init__(self):
        """Initialize down events list if not provided"""
        if self.down_events is None:
            self.down_events = []


class DownTracker:
    """
    Processes play results and applies down progression logic
    
    Takes play yardage and current down state to determine:
    - First down achievements
    - Down progression (1st -> 2nd -> 3rd -> 4th)
    - Turnover on downs for failed 4th down conversions
    - New down/distance calculations
    """
    
    def process_play(self, current_down_state: DownState, yards_gained: int,
                    new_field_position: int, is_scoring_play: bool = False) -> DownProgressionResult:
        """
        Process a play result and update down situation
        
        Args:
            current_down_state: Current down and distance
            yards_gained: Actual yards gained from the play
            new_field_position: New yard line position after play
            is_scoring_play: Whether this play resulted in a score
        
        Returns:
            DownProgressionResult with updated down situation
        """
        # Handle scoring plays - drive ends
        if is_scoring_play:
            return DownProgressionResult(
                new_down_state=None,  # Drive over
                down_result=DownResult.SCORING_DRIVE,
                down_events=["scoring_play", "drive_ended"]
            )
        
        # Calculate if first down was achieved
        yards_needed = current_down_state.yards_to_go
        first_down_achieved = yards_gained >= yards_needed
        yards_past_first_down = max(0, yards_gained - yards_needed) if first_down_achieved else 0
        
        if first_down_achieved:
            # First down achieved - reset to 1st and 10
            new_first_down_line = min(100, new_field_position + 10)  # Can't go past goal line
            actual_yards_to_go = new_first_down_line - new_field_position
            
            result = DownProgressionResult(
                new_down_state=DownState(
                    current_down=1,
                    yards_to_go=actual_yards_to_go,
                    first_down_line=new_first_down_line
                ),
                down_result=DownResult.FIRST_DOWN_ACHIEVED,
                first_down_achieved=True,
                yards_past_first_down=yards_past_first_down,
                down_events=["first_down_achieved"]
            )
            
        else:
            # First down not achieved - advance down or turnover
            if current_down_state.is_fourth_down():
                # Failed 4th down conversion - turnover on downs
                result = DownProgressionResult(
                    new_down_state=None,  # Possession changes
                    down_result=DownResult.TURNOVER_ON_DOWNS,
                    possession_change=True,
                    turnover_on_downs=True,
                    down_events=["turnover_on_downs", "possession_change"]
                )
            else:
                # Advance to next down
                new_down = current_down_state.current_down + 1
                new_yards_to_go = current_down_state.yards_to_go - yards_gained
                
                result = DownProgressionResult(
                    new_down_state=DownState(
                        current_down=new_down,
                        yards_to_go=new_yards_to_go,
                        first_down_line=current_down_state.first_down_line
                    ),
                    down_result=DownResult.CONTINUE_DRIVE,
                    down_events=[f"advance_to_{self._ordinal(new_down)}_down"]
                )
        
        return result
    
    def process_penalty(self, current_down_state: DownState, penalty_yards: int,
                       is_automatic_first_down: bool = False) -> DownProgressionResult:
        """
        Handle penalty effects on down situation
        
        Args:
            current_down_state: Current down and distance
            penalty_yards: Yards gained/lost due to penalty (positive = gained)
            is_automatic_first_down: Some penalties award automatic first down
        
        Returns:
            DownProgressionResult with penalty-adjusted down situation
        """
        if is_automatic_first_down:
            # Automatic first down regardless of yards
            return DownProgressionResult(
                new_down_state=DownState(
                    current_down=1,
                    yards_to_go=10,  # Standard first and 10
                    first_down_line=min(100, current_down_state.first_down_line + penalty_yards + 10)
                ),
                down_result=DownResult.FIRST_DOWN_ACHIEVED,
                first_down_achieved=True,
                down_events=["automatic_first_down", "penalty_first_down"]
            )
        
        else:
            # Adjust yards to go based on penalty
            new_yards_to_go = max(1, current_down_state.yards_to_go - penalty_yards)
            new_first_down_line = current_down_state.first_down_line + penalty_yards
            
            return DownProgressionResult(
                new_down_state=DownState(
                    current_down=current_down_state.current_down,
                    yards_to_go=new_yards_to_go,
                    first_down_line=new_first_down_line
                ),
                down_result=DownResult.CONTINUE_DRIVE,
                down_events=["penalty_yardage_adjustment"]
            )
    
    def create_new_drive(self, starting_field_position: int) -> DownState:
        """
        Create a new drive state (1st and 10)
        
        Args:
            starting_field_position: Yard line where new drive begins
        
        Returns:
            DownState for start of new possession
        """
        first_down_line = min(100, starting_field_position + 10)
        actual_yards_to_go = first_down_line - starting_field_position
        
        return DownState(
            current_down=1,
            yards_to_go=actual_yards_to_go,
            first_down_line=first_down_line
        )
    
    def _ordinal(self, number: int) -> str:
        """Convert number to ordinal string (1 -> '1st', 2 -> '2nd', etc.)"""
        ordinal_map = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        return ordinal_map.get(number, f"{number}th")