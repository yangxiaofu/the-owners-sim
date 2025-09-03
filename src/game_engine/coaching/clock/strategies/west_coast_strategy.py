"""
West Coast Clock Strategy

Efficient, methodical coaching archetype that emphasizes:
- Precision timing and execution
- Situational awareness in clock management
- Balanced approach with slight efficiency gains
- Smart tempo adjustments based on game flow
"""

from typing import Dict, Any
from .base_strategy import BaseClockStrategy
from ..config import SituationalAdjustments, GameContextThresholds


class WestCoastStrategy(BaseClockStrategy):
    """
    Methodical coaching archetype that emphasizes efficiency and situational precision.
    
    Characteristics:
    - Base +1 second for precision
    - Strong situational adjustments
    - Balanced tempo with smart clock management
    - Adapts well to different game situations
    """
    
    def __init__(self):
        """Initialize the west coast strategy."""
        super().__init__('west_coast')
    
    def _get_strategy_specific_adjustments(self, play_type: str, game_context: Dict[str, Any], 
                                         completion_status: str, effective_play_type: str) -> int:
        """
        Get west coast strategy-specific situational adjustments.
        
        West coast strategy emphasizes precision and intelligent situational awareness.
        This method adds west coast-specific timing logic that focuses on smart adjustments.
        
        Args:
            play_type: Original play type
            game_context: Game situation data
            completion_status: Pass completion status if applicable
            effective_play_type: Processed play type for timing lookup
            
        Returns:
            Additional adjustment in seconds (varies based on situation)
        """
        # Extract validated game context
        context = self._extract_game_context(game_context)
        quarter = context['quarter']
        clock = context['clock']
        score_differential = context['score_differential']
        down = context['down']
        distance = context['distance']
        field_position = context['field_position']
        
        adjustment = 0
        
        # West coast specific situational intelligence
        if abs(score_differential) <= SituationalAdjustments.SMALL_LEAD:  # Close game (±3)
            # West coast excels in close games with precision
            adjustment += 1  # Extra precision in tight games
        elif score_differential > SituationalAdjustments.SMALL_LEAD:  # Leading by 4+
            if quarter >= 3:  # Second half with lead
                adjustment += 1  # Smart tempo control to protect lead
        elif score_differential < -SituationalAdjustments.SMALL_LEAD:  # Trailing by 4+
            # West coast can efficiently speed up when needed
            adjustment -= 2  # Intelligent hurry-up
        
        # Down and distance intelligence (west coast specialty)
        if down == 1:  # First down
            adjustment += 1  # Take time to read defense and make adjustments
        elif down == 2:  # Second down  
            if distance <= GameContextThresholds.SHORT_YARDAGE:  # Manageable distance
                adjustment += 1  # Methodical approach on manageable 2nd downs
            else:  # Longer yardage
                adjustment -= 1  # Pick up tempo to get back on track
        elif down >= 3:  # 3rd/4th down (west coast strength)
            if distance <= GameContextThresholds.SHORT_YARDAGE:  # Short yardage
                adjustment += 2  # Maximum precision on critical short yardage
            else:  # Long yardage - west coast comfort zone
                adjustment -= 1  # Efficient in obvious passing situations
                
        # Field position intelligence
        if field_position <= SituationalAdjustments.OWN_TWENTY:  # Own 20 or deeper
            adjustment += 1  # Conservative and precise in own territory
        elif field_position >= SituationalAdjustments.MIDFIELD:  # Crossing midfield
            adjustment -= 1  # Open up the offense in good field position
            
        # Red zone excellence (west coast strength)
        if self._is_red_zone(field_position):  # Red zone
            adjustment += 1  # Extra precision in scoring position
            if self._is_goal_line(field_position):  # Goal line
                adjustment += 1  # Maximum precision at goal line
                
        # Fourth quarter clock management intelligence
        if quarter == 4:
            if clock < SituationalAdjustments.FINAL_TEN_MINUTES:  # Final 10 minutes
                if score_differential > SituationalAdjustments.MEDIUM_LEAD:  # Big lead
                    adjustment += 2  # Smart clock control
                elif score_differential > 0:  # Small lead
                    adjustment += 1  # Slight control while staying efficient
                elif score_differential == 0:  # Tied
                    # Stay methodical in tie games - no additional adjustment
                    pass
                elif clock < 180:  # Final 3 minutes, trailing
                    adjustment -= 2  # Efficient hurry-up when time is critical
                        
        # Two-minute drill (west coast is solid but not elite here)
        if self._is_two_minute_situation(quarter, clock):
            if score_differential <= 0:  # Need to score
                adjustment -= 1  # Moderate urgency - efficient but not frantic
                
        return adjustment