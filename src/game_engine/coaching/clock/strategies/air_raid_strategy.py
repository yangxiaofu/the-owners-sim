"""
Air Raid Clock Strategy

Fast tempo, hurry-up coaching archetype that emphasizes:
- High-speed offense to maximize possessions  
- No-huddle and hurry-up concepts
- Aggressive tempo especially when trailing
- Quick snaps and rapid play execution
"""

from typing import Dict, Any
from .base_strategy import BaseClockStrategy
from ..config import SituationalAdjustments


class AirRaidStrategy(BaseClockStrategy):
    """
    Fast-tempo coaching archetype that emphasizes speed and maximizing possessions.
    
    Characteristics:
    - Base -2 seconds per play  
    - Additional speed when trailing
    - Faster tempo on pass plays
    - Aggressive no-huddle concepts
    """
    
    def __init__(self):
        """Initialize the air raid strategy."""
        super().__init__('air_raid')
    
    def _get_strategy_specific_adjustments(self, play_type: str, game_context: Dict[str, Any], 
                                         completion_status: str, effective_play_type: str) -> int:
        """
        Get air raid strategy-specific situational adjustments.
        
        Air raid strategy emphasizes speed and aggression, especially when trailing.
        This method adds air raid-specific timing logic on top of the standard adjustments.
        
        Args:
            play_type: Original play type
            game_context: Game situation data
            completion_status: Pass completion status if applicable
            effective_play_type: Processed play type for timing lookup
            
        Returns:
            Additional adjustment in seconds (usually negative for faster tempo)
        """
        # Extract validated game context
        context = self._extract_game_context(game_context)
        quarter = context['quarter']
        clock = context['clock']
        score_differential = context['score_differential']
        down = context['down']
        distance = context['distance']
        field_position = context['field_position']
        timeouts_remaining = context['timeouts_remaining']
        
        adjustment = 0
        
        # Air raid specific logic: extra speed when trailing (beyond standard adjustments)
        if score_differential < 0:  # Trailing
            if score_differential <= -SituationalAdjustments.MEDIUM_LEAD:  # Down by 7+
                adjustment -= 4  # Maximum hurry-up mode (air raid specialty)
            elif score_differential <= -SituationalAdjustments.SMALL_LEAD:  # Down by 3-6
                adjustment -= 2  # Moderate hurry-up
                
        elif score_differential > SituationalAdjustments.MEDIUM_LEAD:  # Leading by 8+
            # Even when ahead, air raid maintains aggressive tempo
            adjustment -= 1  # Still faster than average
        
        # Down and distance considerations (air raid thrives on 3rd down)
        if down >= 3:  # 3rd/4th down
            if distance <= 3:  # Short yardage
                adjustment -= 1  # Quick snap to catch defense off-guard
            else:  # Long yardage - air raid comfort zone
                adjustment -= 2  # Extra fast in obvious passing situations
                
        # Two-minute drill adjustments (air raid specialty)
        if self._is_two_minute_situation(quarter, clock):
            adjustment -= 2  # Master of the two-minute drill (beyond standard adjustment)
            if timeouts_remaining == 0:  # No timeouts left
                adjustment -= 2  # Even faster when can't stop clock
                
        # Fourth quarter crunch time (air raid excels under pressure)
        if self._is_fourth_quarter_crunch_time(quarter, clock):
            if score_differential <= 0:  # Tied or trailing
                adjustment -= 2  # Maximum urgency in clutch moments
            elif score_differential < SituationalAdjustments.MEDIUM_LEAD:  # Small lead
                adjustment -= 1  # Still playing fast to extend lead
                    
        # Red zone adjustments - air raid can struggle in compressed field
        if self._is_red_zone(field_position) and score_differential >= 0:  # Red zone, not desperate
            adjustment += 1  # Slightly slower due to compressed field
            
        return adjustment