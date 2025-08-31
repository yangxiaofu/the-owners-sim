from dataclasses import dataclass
from typing import Optional

@dataclass
class FieldState:
    """Manages ball position, down, and distance"""
    
    def __init__(self):
        self.down = 1
        self.yards_to_go = 10
        self.field_position = 25  # yard line (1-100)
        self.possession_team_id: Optional[int] = None
    
    def update_down(self, yards_gained: int) -> str:
        """Update down and distance based on yards gained"""
        if yards_gained >= self.yards_to_go:
            # First down
            self.down = 1
            self.yards_to_go = 10
        else:
            self.down += 1
            self.yards_to_go -= yards_gained
            
        # Update field position
        self.field_position += yards_gained
        
        # Check for scoring
        if self.field_position >= 100:
            return "touchdown"
        elif self.field_position <= 0:
            return "safety"
        
        return "continue"
    
    def is_fourth_down(self) -> bool:
        """Check if it's 4th down"""
        return self.down == 4
    
    def is_short_yardage(self) -> bool:
        """Check if it's short yardage situation (3 yards or less)"""
        return self.yards_to_go <= 3
    
    def is_goal_line(self) -> bool:
        """Check if offense is in the red zone"""
        return self.field_position >= 80
    
    def get_field_position_text(self) -> str:
        """Get human-readable field position"""
        if self.field_position <= 50:
            return f"Own {self.field_position}"
        else:
            return f"Opp {100 - self.field_position}"