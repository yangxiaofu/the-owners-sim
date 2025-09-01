"""
Run Heavy Clock Strategy

Conservative, clock-consuming coaching archetype that emphasizes:
- Slower tempo to control the game
- Clock management through longer play execution
- Extra time consumption when leading to protect leads
"""

from typing import Dict, Any


class RunHeavyStrategy:
    """
    Conservative coaching archetype that emphasizes clock control and methodical offense.
    
    Characteristics:
    - Base +3-5 seconds per play
    - Additional +5 seconds when leading to run clock
    - Slower tempo on run plays
    - Conservative clock management
    """
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed with run-heavy archetype modifications.
        
        Args:
            play_type: Type of play ('run', 'pass', 'kick', 'punt') 
            game_context: Dict containing game situation (quarter, clock, score_differential, etc.)
            completion_status: For pass plays, indicates 'complete', 'incomplete', 'touchdown', 'interception'
            
        Returns:
            Time elapsed in seconds with run-heavy adjustments
        """
        # Base time for different play types
        base_times = {
            'run': 28,          # Further reduced running plays (-4s more)  
            'pass_complete': 13, # Further reduced completed passes (-2s more)
            'pass_incomplete': 10, # Further reduced incomplete passes (-2s more)
            'punt': 15,         # Special teams
            'field_goal': 15,
            'kick': 15,
            'kneel': 40,        # Clock burning
            'spike': 3          # Clock stopping
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
        
        base_time = base_times.get(effective_play_type, 25)  # Default base time
        
        # Base archetype modifier: conservative tempo
        base_adjustment = 4  # +3-5 seconds average
        
        # Play-type specific adjustments
        play_modifiers = {
            'run': +2,      # Extra slow on run plays (bread and butter)
            'pass': +1,     # Slightly slower on passes
            'kick': 0,      # Normal special teams timing
            'punt': 0       # Normal special teams timing
        }
        
        # Apply base run-heavy tempo
        adjusted_time = base_time + base_adjustment + play_modifiers.get(play_type, 0)
        
        # Extract game context variables
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        score_differential = game_context.get('score_differential', 0)
        down = game_context.get('down', 1)
        distance = game_context.get('distance', 10)
        field_position = game_context.get('field_position', 20)
        
        # Run-heavy specific situational logic
        if score_differential > 0:  # Leading
            # Extra clock consumption when ahead
            if quarter >= 3:  # Second half
                adjusted_time += 5
            else:
                adjusted_time += 2
                
        elif score_differential < -7:  # Trailing by more than 7
            # Still conservative, but slightly faster when desperate
            adjusted_time -= 2
        
        # Down and distance considerations
        if down >= 3:  # 3rd/4th down
            adjusted_time += 1  # Extra time for precision
            
        if distance >= 10:  # Long yardage
            adjusted_time += 1  # More deliberate on long downs
            
        # Fourth quarter clock management
        if quarter == 4:
            if clock < 600:  # Final 10 minutes
                if score_differential > 0:  # Leading
                    adjusted_time += 3  # Milk the clock
                elif score_differential == 0:  # Tied
                    adjusted_time += 1  # Slightly more deliberate
                    
        # Two-minute drill adjustments
        if quarter in [2, 4] and clock <= 120:
            if score_differential < 0:  # Trailing
                adjusted_time -= 3  # Need to move faster
            elif score_differential > 7:  # Leading by more than 7
                adjusted_time += 2  # Run more clock
                
        return int(max(8, min(45, adjusted_time)))  # Apply bounds and convert to int