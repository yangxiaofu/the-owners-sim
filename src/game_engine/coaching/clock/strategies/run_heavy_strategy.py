"""
Run Heavy Clock Strategy

Conservative, clock-consuming coaching archetype that emphasizes:
- Slower tempo to control the game
- Clock management through longer play execution
- Extra time consumption when leading to protect leads
"""

from typing import Dict, Any
from .base_strategy import BaseClockStrategy
from ..config import SituationalAdjustments, GameContextThresholds


class RunHeavyStrategy(BaseClockStrategy):
    """
    Conservative coaching archetype that emphasizes clock control and methodical offense.
    
    Characteristics:
    - Base +2 seconds per play
    - Additional time consumption when leading to run clock
    - Slower tempo on run plays  
    - Conservative clock management
    """
    
    def __init__(self):
        """Initialize the run heavy strategy."""
        super().__init__('run_heavy')
    
    def _get_strategy_specific_adjustments(self, play_type: str, game_context: Dict[str, Any], 
                                         completion_status: str, effective_play_type: str) -> int:
        """
        Get run heavy strategy-specific situational adjustments.
        
        Run heavy strategy emphasizes clock control and methodical play,
        especially when leading. This method adds run heavy-specific timing logic.
        
        Args:
            play_type: Original play type
            game_context: Game situation data
            completion_status: Pass completion status if applicable
            effective_play_type: Processed play type for timing lookup
            
        Returns:
            Additional adjustment in seconds (usually positive for slower tempo)
        """
        # Extract validated game context
        context = self._extract_game_context(game_context)
        quarter = context['quarter']
        clock = context['clock']
        score_differential = context['score_differential']
        down = context['down']
        distance = context['distance']
        
        adjustment = 0
        
        # Run heavy specific logic: extra clock consumption when ahead
        if score_differential > 0:  # Leading
            if quarter >= 3:  # Second half - really milk the clock
                adjustment += 2  # Extra deliberate tempo when protecting lead
            else:
                adjustment += 1  # Slight clock control in first half
                
        elif score_differential < -SituationalAdjustments.MEDIUM_LEAD:  # Trailing by 8+
            # Even run heavy needs some urgency when desperate
            adjustment -= 2  # Increased urgency but still methodical
        
        # Down and distance considerations (run heavy likes precision)
        if down >= 3:  # 3rd/4th down
            adjustment += 1  # Extra time for precision on critical downs
            
        if distance >= GameContextThresholds.LONG_YARDAGE:  # 10+ yards
            adjustment += 1  # More deliberate on long yardage situations
            
        # Fourth quarter clock management (run heavy specialty)
        if quarter == 4:
            if clock < SituationalAdjustments.FINAL_TEN_MINUTES:  # Final 10 minutes
                if score_differential > 0:  # Leading
                    adjustment += 3  # Maximum clock control mode
                elif score_differential == 0:  # Tied
                    adjustment += 1  # Slightly more deliberate
                    
        # Two-minute drill adjustments (run heavy struggles here)
        if self._is_two_minute_situation(quarter, clock):
            if score_differential < 0:  # Trailing - forced to change philosophy
                adjustment -= 3  # Urgency overrides natural tempo
            elif score_differential > SituationalAdjustments.MEDIUM_LEAD:  # Big lead
                adjustment += 2  # Run even more clock if possible
                
        return adjustment