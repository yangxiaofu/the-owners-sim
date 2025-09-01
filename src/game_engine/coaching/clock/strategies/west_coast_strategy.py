"""
West Coast Clock Strategy

Efficient, methodical coaching archetype that emphasizes:
- Precision timing and execution
- Situational awareness in clock management
- Balanced approach with slight efficiency gains
- Smart tempo adjustments based on game flow
"""

from typing import Dict, Any


class WestCoastStrategy:
    """
    Methodical coaching archetype that emphasizes efficiency and situational precision.
    
    Characteristics:
    - Base +1-2 seconds for precision
    - Strong situational adjustments
    - Balanced tempo with smart clock management
    - Adapts well to different game situations
    """
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed with west coast archetype modifications.
        
        Args:
            play_type: Type of play ('run', 'pass', 'kick', 'punt')
            game_context: Dict containing game situation (quarter, clock, score_differential, etc.)
            completion_status: For pass plays, whether it was 'complete', 'incomplete', 'touchdown', or 'interception'
            
        Returns:
            Time elapsed in seconds with west coast adjustments
        """
        # Base time for different play types
        base_times = {
            'run': 33,           # Increased to reduce play count
            'pass_complete': 21, # Increased to reduce play count
            'pass_incomplete': 17, # Increased to reduce play count
            'punt': 18,          # Increased to reduce play count
            'field_goal': 18,    # Increased to reduce play count
            'kick': 18,          # Increased to reduce play count
            'kneel': 43,         # Increased to reduce play count
            'spike': 4           # Minimal increase
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
            
        base_time = base_times.get(effective_play_type, 28)  # Default methodical timing (increased)
        
        # Base archetype modifier: methodical precision
        base_adjustment = 1  # +1 second for precision and reads (reduced from +2)
        
        # Play-type specific adjustments
        play_modifiers = {
            'pass_complete': 0,   # Neutral on completed passes (system strength)
            'pass_incomplete': 0, # Neutral on incomplete passes
            'run': +1,            # Slightly slower on runs for precision
            'kick': 0,            # Normal special teams timing
            'punt': 0             # Normal special teams timing
        }
        
        # Apply base west coast tempo
        adjusted_time = base_time + base_adjustment + play_modifiers.get(effective_play_type, 0)
        
        # Extract game context variables
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        score_differential = game_context.get('score_differential', 0)
        down = game_context.get('down', 1)
        distance = game_context.get('distance', 10)
        field_position = game_context.get('field_position', 20)
        
        # West coast specific situational logic
        if score_differential > 3:  # Leading by 4+
            if quarter >= 3:  # Second half with lead
                adjusted_time += 1  # Control tempo to protect lead (reduced from +2)
            else:
                adjusted_time += 1  # Slight tempo control (unchanged)
                
        elif score_differential < -3:  # Trailing by 4+
            # West coast can speed up when needed
            adjusted_time -= 4  # Efficient hurry-up (increased from -3)
            
        elif abs(score_differential) <= 3:  # Close game
            # West coast excels in close games with precision
            adjusted_time += 1  # Extra precision in tight games
        
        # Down and distance intelligence
        if down == 1:  # First down
            adjusted_time += 1  # Take time to assess defense
        elif down == 2:  # Second down  
            if distance <= 5:  # Manageable
                adjusted_time += 1  # Methodical approach
            else:  # Long yardage
                adjusted_time -= 1  # Pick up tempo
        elif down >= 3:  # 3rd/4th down
            if distance <= 3:  # Short yardage
                adjusted_time += 2  # Extra precision on critical downs
            else:  # Long yardage
                adjusted_time -= 1  # Efficient passing game
                
        # Field position intelligence
        if field_position <= 20:  # Own 20 or deeper
            adjusted_time += 1  # Conservative in own territory
        elif field_position >= 50:  # Crossing midfield
            adjusted_time -= 1  # Open up the offense
            
        # Red zone excellence (west coast strength)
        if field_position >= 80:  # Red zone
            adjusted_time += 1  # Extra precision in scoring position (reduced from +2)
            if field_position >= 95:  # Goal line
                adjusted_time += 1  # Maximum precision at goal line (unchanged)
                
        # Fourth quarter clock management intelligence
        if quarter == 4:
            if clock < 600:  # Final 10 minutes
                if score_differential > 7:  # Comfortable lead
                    adjusted_time += 2  # Control clock (reduced from +3)
                elif score_differential > 0:  # Small lead
                    adjusted_time += 1  # Slight control (unchanged)
                elif score_differential == 0:  # Tied
                    # Stay methodical in tie games
                    pass  # No adjustment - stick to base precision
                else:  # Trailing
                    if clock < 180:  # Final 3 minutes
                        adjusted_time -= 2  # Efficient hurry-up
                        
        # Two-minute drill (west coast is solid but not elite here)
        if quarter in [2, 4] and clock <= 120:
            if score_differential <= 0:  # Need score
                adjusted_time -= 1  # Moderate urgency
                
        return int(max(8, min(45, adjusted_time)))  # Apply bounds for target play count