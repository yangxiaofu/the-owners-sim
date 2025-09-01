"""
FieldTransition - Field Position, Downs, and Yards to Go Changes

This data structure represents all changes to field position, down and distance,
and first down status. It contains all the information needed to update the
field state after a play execution.

Key responsibilities:
- Track field position changes (0-100 yard line)
- Manage down progression (1st, 2nd, 3rd, 4th down)
- Calculate yards to go for first down
- Determine first down achievements
- Handle goal line and red zone situations
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class FirstDownReason(Enum):
    """Enumeration of reasons why a first down was achieved."""
    YARDS_GAINED = "yards_gained"
    PENALTY = "penalty"
    TURNOVER = "turnover"
    KICKOFF = "kickoff"
    PUNT = "punt"
    TOUCHDOWN = "touchdown"
    

@dataclass(frozen=True)
class FieldTransition:
    """
    Immutable representation of field position and down/distance changes.
    
    This object contains all the data needed to update field position,
    down and distance after a play. All field positions are represented
    as yard lines from 0-100 (0 = goal line, 100 = opposite goal line).
    
    Attributes:
        # Field Position
        new_yard_line: New field position (0-100, where 0 is goal line)
        old_yard_line: Previous field position for reference
        yards_gained: Net yards gained on the play (can be negative)
        
        # Down and Distance
        new_down: New down number (1-4)
        old_down: Previous down number for reference
        new_yards_to_go: Yards needed for first down
        old_yards_to_go: Previous yards to go for reference
        
        # First Down Information
        first_down_achieved: Whether a first down was earned
        first_down_reason: Why the first down was achieved (if applicable)
        automatic_first_down: Whether this was an automatic first down (penalty)
        
        # Special Field Situations
        in_red_zone: Whether the new position is in red zone (20 yard line or closer)
        in_goal_to_go: Whether the new situation is goal-to-go (10 yards or less to goal)
        at_goal_line: Whether the team is at the goal line (1 yard or less)
        crossed_midfield: Whether the team crossed the 50-yard line this play
        
        # End Zone and Safety Information
        in_end_zone: Whether the play ended in the end zone
        safety_situation: Whether this creates a safety situation
        touchback_situation: Whether this creates a touchback situation
        
        # Measurement and Review
        requires_measurement: Whether this play requires an official measurement
        spot_under_review: Whether the ball spot is under review
        
        # Field Direction (for possession changes)
        field_direction_changed: Whether the field direction flipped (for turnovers)
        attacking_direction: Direction team is attacking ('left' or 'right' or None)
    """
    
    # Field Position
    new_yard_line: int
    old_yard_line: int
    yards_gained: int
    
    # Down and Distance
    new_down: int
    old_down: int
    new_yards_to_go: int
    old_yards_to_go: int
    
    # First Down Information
    first_down_achieved: bool = False
    first_down_reason: Optional[FirstDownReason] = None
    automatic_first_down: bool = False
    
    # Special Field Situations
    in_red_zone: bool = False
    in_goal_to_go: bool = False
    at_goal_line: bool = False
    crossed_midfield: bool = False
    
    # End Zone and Safety Information
    in_end_zone: bool = False
    safety_situation: bool = False
    touchback_situation: bool = False
    
    # Measurement and Review
    requires_measurement: bool = False
    spot_under_review: bool = False
    
    # Field Direction
    field_direction_changed: bool = False
    attacking_direction: Optional[str] = None
    
    def __post_init__(self):
        """Validate field position and calculate derived fields."""
        # Validate field position bounds
        if not (0 <= self.new_yard_line <= 100):
            raise ValueError(f"Field position must be 0-100, got {self.new_yard_line}")
        
        if not (0 <= self.old_yard_line <= 100):
            raise ValueError(f"Old field position must be 0-100, got {self.old_yard_line}")
        
        # Validate down numbers
        if not (1 <= self.new_down <= 4):
            raise ValueError(f"Down must be 1-4, got {self.new_down}")
        
        if not (1 <= self.old_down <= 4):
            raise ValueError(f"Old down must be 1-4, got {self.old_down}")
        
        # Calculate derived field situation flags
        object.__setattr__(self, 'in_red_zone', self.new_yard_line <= 20)
        object.__setattr__(self, 'in_goal_to_go', self.new_yards_to_go <= 10 and self.new_yard_line <= 10)
        object.__setattr__(self, 'at_goal_line', self.new_yard_line <= 1)
        
        # Check if team crossed midfield (50-yard line)
        if self.old_yard_line > 50 and self.new_yard_line <= 50:
            object.__setattr__(self, 'crossed_midfield', True)
        elif self.old_yard_line < 50 and self.new_yard_line >= 50:
            object.__setattr__(self, 'crossed_midfield', True)
    
    def get_field_position_description(self) -> str:
        """Return a human-readable description of the field position."""
        if self.in_end_zone:
            return "End Zone"
        elif self.at_goal_line:
            return "Goal Line"
        elif self.in_goal_to_go:
            return f"Goal To Go ({self.new_yard_line} yard line)"
        elif self.in_red_zone:
            return f"Red Zone ({self.new_yard_line} yard line)"
        elif self.new_yard_line == 50:
            return "50 Yard Line"
        elif self.new_yard_line > 50:
            return f"Own {100 - self.new_yard_line} Yard Line"
        else:
            return f"Opponent {self.new_yard_line} Yard Line"
    
    def get_down_and_distance(self) -> str:
        """Return the standard down and distance notation."""
        if self.in_goal_to_go:
            return f"{self.get_down_ordinal()} and Goal"
        else:
            return f"{self.get_down_ordinal()} and {self.new_yards_to_go}"
    
    def get_down_ordinal(self) -> str:
        """Return the ordinal representation of the down (1st, 2nd, 3rd, 4th)."""
        ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        return ordinals.get(self.new_down, f"{self.new_down}th")
    
    def is_long_yardage(self) -> bool:
        """Return True if this is a long yardage situation (7+ yards to go)."""
        return self.new_yards_to_go >= 7
    
    def is_short_yardage(self) -> bool:
        """Return True if this is a short yardage situation (3 or fewer yards)."""
        return self.new_yards_to_go <= 3
    
    def is_fourth_down(self) -> bool:
        """Return True if this is 4th down."""
        return self.new_down == 4
    
    def is_first_down(self) -> bool:
        """Return True if this is 1st down."""
        return self.new_down == 1
    
    def get_yards_gained_description(self) -> str:
        """Return a description of the yards gained."""
        if self.yards_gained > 0:
            return f"Gained {self.yards_gained} yards"
        elif self.yards_gained < 0:
            return f"Lost {abs(self.yards_gained)} yards"
        else:
            return "No gain"
    
    def get_field_situation_summary(self) -> str:
        """Return a summary of special field situations."""
        situations = []
        
        if self.in_end_zone:
            situations.append("End Zone")
        elif self.at_goal_line:
            situations.append("Goal Line")
        elif self.in_goal_to_go:
            situations.append("Goal To Go")
        elif self.in_red_zone:
            situations.append("Red Zone")
        
        if self.crossed_midfield:
            situations.append("Crossed Midfield")
        
        if self.requires_measurement:
            situations.append("Measurement Required")
        
        if self.safety_situation:
            situations.append("Safety")
        
        if self.touchback_situation:
            situations.append("Touchback")
        
        return ", ".join(situations) if situations else "Normal field position"
    
    def get_summary(self) -> str:
        """Return a complete summary of this field transition."""
        parts = [
            self.get_yards_gained_description(),
            f"to {self.get_field_position_description()}",
            self.get_down_and_distance()
        ]
        
        if self.first_down_achieved:
            parts.append("FIRST DOWN")
        
        return " - ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this field transition to a dictionary."""
        return {
            'field_position': {
                'new_yard_line': self.new_yard_line,
                'old_yard_line': self.old_yard_line,
                'yards_gained': self.yards_gained,
                'field_description': self.get_field_position_description()
            },
            'down_and_distance': {
                'new_down': self.new_down,
                'old_down': self.old_down,
                'new_yards_to_go': self.new_yards_to_go,
                'old_yards_to_go': self.old_yards_to_go,
                'down_distance_notation': self.get_down_and_distance()
            },
            'first_down_info': {
                'first_down_achieved': self.first_down_achieved,
                'first_down_reason': self.first_down_reason.value if self.first_down_reason else None,
                'automatic_first_down': self.automatic_first_down
            },
            'field_situations': {
                'in_red_zone': self.in_red_zone,
                'in_goal_to_go': self.in_goal_to_go,
                'at_goal_line': self.at_goal_line,
                'crossed_midfield': self.crossed_midfield,
                'in_end_zone': self.in_end_zone,
                'safety_situation': self.safety_situation,
                'touchback_situation': self.touchback_situation
            },
            'special_flags': {
                'requires_measurement': self.requires_measurement,
                'spot_under_review': self.spot_under_review,
                'field_direction_changed': self.field_direction_changed,
                'attacking_direction': self.attacking_direction
            },
            'summary': self.get_summary(),
            'field_situation_summary': self.get_field_situation_summary()
        }