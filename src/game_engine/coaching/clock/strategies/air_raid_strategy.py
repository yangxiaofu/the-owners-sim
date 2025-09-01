"""
Air Raid Clock Strategy

Fast tempo, hurry-up coaching archetype that emphasizes:
- High-speed offense to maximize possessions  
- No-huddle and hurry-up concepts
- Aggressive tempo especially when trailing
- Quick snaps and rapid play execution
"""

from typing import Dict, Any


class AirRaidStrategy:
    """
    Fast-tempo coaching archetype that emphasizes speed and maximizing possessions.
    
    Characteristics:
    - Base -5 seconds per play  
    - Additional -8 seconds when trailing
    - Faster tempo on pass plays
    - Aggressive no-huddle concepts
    """
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed with air raid archetype modifications.
        
        Args:
            play_type: Type of play ('run', 'pass', 'kick', 'punt')
            game_context: Dict containing game situation (quarter, clock, score_differential, etc.)
            completion_status: For pass plays, whether it was 'complete', 'incomplete', 'touchdown', or 'interception'
            
        Returns:
            Time elapsed in seconds with air raid adjustments
        """
        # Base time for different play types  
        base_times = {
            'run': 28,           # Further reduced base run time (-4s more)
            'pass_complete': 13, # Further reduced completed passes (-2s more)
            'pass_incomplete': 10, # Further reduced incomplete passes (-2s more)
            'punt': 13,          # Quicker special teams
            'field_goal': 13,
            'kick': 13,
            'kneel': 35,         # Still need to burn clock when needed
            'spike': 2           # Lightning fast spikes
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
            
        base_time = base_times.get(effective_play_type, 18)  # Default faster base time
        
        # Base archetype modifier: fast tempo
        base_adjustment = -5  # Base -5 seconds for hurry-up
        
        # Play-type specific adjustments
        play_modifiers = {
            'pass_complete': -3,   # Extra fast on completed passes (bread and butter)
            'pass_incomplete': -3, # Extra fast on incomplete passes too
            'run': -1,             # Faster runs than normal, but not as fast as passes
            'kick': +2,            # Special teams can't be rushed as much
            'punt': +1             # Punt operations need some precision
        }
        
        # Apply base air raid tempo
        adjusted_time = base_time + base_adjustment + play_modifiers.get(effective_play_type, 0)
        
        # Extract game context variables
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        score_differential = game_context.get('score_differential', 0)
        down = game_context.get('down', 1)
        distance = game_context.get('distance', 10)
        field_position = game_context.get('field_position', 20)
        
        # Air raid specific situational logic
        if score_differential < 0:  # Trailing
            # Extra speed when behind - this is where air raid shines
            if score_differential <= -7:  # Down by 7+
                adjusted_time -= 8  # Maximum hurry-up mode
            else:  # Down by 1-6
                adjusted_time -= 4  # Moderate hurry-up
                
        elif score_differential > 7:  # Leading by more than 7
            # Even when ahead, air raid stays aggressive
            adjusted_time -= 2  # Still faster than average, but not as extreme
        
        # Down and distance considerations
        if down >= 3:  # 3rd/4th down
            if distance <= 3:  # Short yardage
                adjusted_time -= 1  # Quick snap to catch defense off-guard
            else:  # Long yardage - air raid comfort zone
                adjusted_time -= 2  # Extra fast in passing situations
                
        # Two-minute drill adjustments (air raid specialty)
        if quarter in [2, 4] and clock <= 120:
            adjusted_time -= 3  # Master of the two-minute drill
            timeouts = game_context.get('timeouts_remaining', 3)
            if timeouts == 0:  # No timeouts left
                adjusted_time -= 2  # Even faster when can't stop clock
                
        # Fourth quarter urgency
        if quarter == 4:
            if clock < 300:  # Final 5 minutes
                if score_differential <= 0:  # Tied or trailing
                    adjusted_time -= 4  # Maximum urgency
                elif score_differential < 7:  # Small lead
                    adjusted_time -= 2  # Still playing fast
                    
        # Red zone adjustments - air raid can struggle here
        if field_position >= 80 and score_differential >= 0:  # Red zone, not trailing
            adjusted_time += 1  # Slightly slower in compressed field
            
        return int(max(8, min(45, adjusted_time)))  # Apply bounds and convert to int