"""
Balanced Clock Strategy

Neutral timing coaching archetype that emphasizes:
- Default NFL tempo without extreme variations
- Minimal archetype-specific modifiers
- Situational awareness without aggressive adjustments
- Serves as baseline for comparison with other archetypes
"""

from typing import Dict, Any
from .base_strategy import BaseClockStrategy


class BalancedStrategy(BaseClockStrategy):
    """
    Neutral coaching archetype that represents standard NFL tempo and clock management.
    
    Characteristics:
    - Minimal base adjustments (±0-1 seconds)
    - Relies primarily on situational modifiers
    - Default behavior for most coaching decisions
    - Serves as baseline comparison for other archetypes
    """
    
    def __init__(self):
        """Initialize the balanced strategy."""
        super().__init__('balanced')
    
    def _get_strategy_specific_adjustments(self, play_type: str, game_context: Dict[str, Any], 
                                         completion_status: str, effective_play_type: str) -> int:
        """
        Get balanced strategy-specific situational adjustments.
        
        Balanced strategy relies mostly on the standard situational adjustments
        with only minimal strategy-specific modifications.
        
        Args:
            play_type: Original play type
            game_context: Game situation data
            completion_status: Pass completion status if applicable
            effective_play_type: Processed play type for timing lookup
            
        Returns:
            Additional adjustment in seconds (always minimal for balanced)
        """
        # Extract validated game context
        context = self._extract_game_context(game_context)
        quarter = context['quarter']
        clock = context['clock']
        score_differential = context['score_differential']
        down = context['down']
        distance = context['distance']
        
        adjustment = 0
        
        # Balanced strategy has minimal specific adjustments beyond the standard ones
        # Most timing comes from the centralized situational adjustments
        
        # Only a few balanced-specific fine-tunings
        if down == 1 and distance == 10:  # Fresh set of downs
            adjustment += 1  # Take a moment to assess the defense
            
        # Two-minute drill adjustment (balanced approach)
        if self._is_two_minute_situation(quarter, clock) and score_differential < 0:
            adjustment -= 1  # Standard two-minute urgency
        
        return adjustment