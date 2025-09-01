"""
Balanced Clock Strategy

Neutral timing coaching archetype that emphasizes:
- Default NFL tempo without extreme variations
- Minimal archetype-specific modifiers
- Situational awareness without aggressive adjustments
- Serves as baseline for comparison with other archetypes
"""

from typing import Dict, Any


class BalancedStrategy:
    """
    Neutral coaching archetype that represents standard NFL tempo and clock management.
    
    Characteristics:
    - Minimal base adjustments (±0-1 seconds)
    - Relies primarily on situational modifiers
    - Default behavior for most coaching decisions
    - Serves as baseline comparison for other archetypes
    """
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed with balanced archetype modifications.
        
        Args:
            play_type: Type of play ('run', 'pass', 'kick', 'punt')
            game_context: Dict containing game situation (quarter, clock, score_differential, etc.)
            completion_status: For pass plays, status ('complete', 'incomplete', 'touchdown', 'interception')
            
        Returns:
            Time elapsed in seconds with minimal balanced adjustments
        """
        # Base time for different play types (standard NFL timing)
        base_times = {
            'run': 28,      # Further reduced run timing (-4s more)
            'pass_complete': 13,     # Further reduced complete passes (-2s more)
            'pass_incomplete': 10,   # Further reduced incomplete passes (-2s more)
            'punt': 15,     # Standard special teams
            'field_goal': 15,
            'kick': 15,
            'kneel': 40,    # Standard clock control
            'spike': 3      # Standard spike timing
        }
        
        # Handle pass play types with completion status
        if play_type == 'pass' and completion_status:
            if completion_status in ['complete', 'touchdown']:
                effective_play_type = 'pass_complete'
            elif completion_status in ['incomplete', 'interception']:
                effective_play_type = 'pass_incomplete'
            else:
                effective_play_type = 'pass_complete'  # Default to complete
        else:
            effective_play_type = play_type
        
        base_time = base_times.get(effective_play_type, 23)  # Default neutral timing
        
        # Base archetype modifier: neutral/minimal
        base_adjustment = 0  # No significant tempo bias
        
        # Play-type specific adjustments (minimal variations)
        play_modifiers = {
            'pass': 0,      # Neutral timing on passes
            'run': 0,       # Neutral timing on runs  
            'kick': 0,      # Standard special teams timing
            'punt': 0       # Standard special teams timing
        }
        
        # Apply base balanced tempo (essentially unchanged)
        adjusted_time = base_time + base_adjustment + play_modifiers.get(play_type, 0)
        
        # Extract game context variables
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        score_differential = game_context.get('score_differential', 0)
        down = game_context.get('down', 1)
        distance = game_context.get('distance', 10)
        field_position = game_context.get('field_position', 20)
        
        # Minimal balanced-specific situational logic
        if score_differential > 14:  # Leading by 15+
            adjusted_time += 2  # Slight clock control with big lead
            
        elif score_differential < -14:  # Trailing by 15+
            adjusted_time -= 2  # Slight urgency when way behind
            
        # Fourth quarter standard adjustments
        if quarter == 4:
            if clock < 300:  # Final 5 minutes
                if score_differential > 7:  # Leading by 8+
                    adjusted_time += 2  # Standard clock control
                elif score_differential < -7:  # Trailing by 8+
                    adjusted_time -= 2  # Standard hurry-up
                    
        # Down and distance (minimal adjustments)
        if down >= 3 and distance > 10:  # 3rd/4th and long
            adjusted_time -= 1  # Slight urgency on obvious passing downs
            
        if down == 1 and distance == 10:  # Fresh set
            adjusted_time += 1  # Take a moment to assess
            
        # Red zone (standard adjustment)
        if field_position >= 80:  # Red zone
            adjusted_time += 1  # Slight precision increase
            
        # Two-minute warning (standard urgency)
        if quarter in [2, 4] and clock <= 120 and score_differential < 0:
            adjusted_time -= 1  # Standard two-minute drill adjustment
            
        return int(max(8, min(45, adjusted_time)))  # Apply bounds and convert to int