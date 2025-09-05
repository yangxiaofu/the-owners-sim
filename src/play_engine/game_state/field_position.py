"""
Field Position Tracking System

Handles field position management, boundary detection, and scoring logic.
Maintains separation from down/distance tracking - focuses purely on ball placement.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class FieldZone(Enum):
    """Field zones for strategic analysis"""
    OWN_END_ZONE = "own_end_zone"          # Own 0-yard line (safety risk)
    OWN_GOAL_LINE = "own_goal_line"        # Own 1-20 yard lines  
    OWN_TERRITORY = "own_territory"        # Own 21-49 yard lines
    MIDFIELD = "midfield"                  # 50-yard line area (45-55)
    OPPONENT_TERRITORY = "opponent_territory"  # Opponent 49-21 yard lines
    RED_ZONE = "red_zone"                  # Opponent 20-1 yard lines
    OPPONENT_END_ZONE = "opponent_end_zone"    # Opponent 0-yard line (touchdown)


@dataclass
class FieldPosition:
    """
    Represents current ball position on the field
    
    Field coordinate system:
    - yard_line: 0-100 (0 = own goal line, 100 = opponent goal line)
    - possession_team: Which team currently has the ball
    - field_zone: Strategic zone classification for the position
    """
    yard_line: int                    # 0-100 field position
    possession_team: str              # Team name/ID that has possession
    field_zone: FieldZone            # Strategic zone classification
    
    def __post_init__(self):
        """Validate field position data"""
        if not 0 <= self.yard_line <= 100:
            raise ValueError(f"Invalid yard_line: {self.yard_line}. Must be 0-100.")
        
        # Auto-calculate field zone if not provided correctly
        self.field_zone = self._calculate_field_zone()
    
    def _calculate_field_zone(self) -> FieldZone:
        """Calculate field zone based on yard line position"""
        if self.yard_line == 0:
            return FieldZone.OWN_END_ZONE
        elif 1 <= self.yard_line <= 20:
            return FieldZone.OWN_GOAL_LINE  
        elif 21 <= self.yard_line <= 45:
            return FieldZone.OWN_TERRITORY
        elif 46 <= self.yard_line <= 54:
            return FieldZone.MIDFIELD
        elif 55 <= self.yard_line <= 79:
            return FieldZone.OPPONENT_TERRITORY
        elif 80 <= self.yard_line <= 99:
            return FieldZone.RED_ZONE
        else:  # yard_line == 100
            return FieldZone.OPPONENT_END_ZONE
    
    def distance_to_goal(self) -> int:
        """Distance to opponent's goal line"""
        return 100 - self.yard_line
    
    def distance_to_own_goal(self) -> int:
        """Distance to own goal line"""
        return self.yard_line
    
    def is_in_red_zone(self) -> bool:
        """Check if position is in red zone (within 20 yards of opponent goal)"""
        return self.field_zone in [FieldZone.RED_ZONE, FieldZone.OPPONENT_END_ZONE]
    
    def is_in_own_territory(self) -> bool:
        """Check if position is in own half of field"""
        return self.yard_line < 50


@dataclass  
class FieldResult:
    """
    Result of field position processing
    
    Contains both the raw play mechanics result and field-adjusted reality
    """
    # Original play mechanics (preserved)
    raw_yards_gained: int             # Yards from play simulation
    
    # Field-adjusted reality
    actual_yards_gained: int          # Yards after field boundary constraints
    new_field_position: FieldPosition # Updated ball position
    
    # Scoring and special events
    is_scored: bool = False          # Did this play result in scoring?
    scoring_type: Optional[str] = None    # "touchdown", "safety", "touchback"
    points_scored: int = 0           # Points awarded (6 for TD, 2 for safety, etc.)
    
    # Field events
    field_events: List[str] = None   # ["crossed_goal_line", "safety", etc.]
    possession_change: bool = False  # Did possession change due to field events?
    
    def __post_init__(self):
        """Initialize field events list if not provided"""
        if self.field_events is None:
            self.field_events = []


class FieldTracker:
    """
    Processes play results and applies field position logic
    
    Takes raw play results and calculates field-constrained reality including:
    - Ball position updates with boundary constraints
    - Touchdown detection when ball crosses goal line  
    - Safety detection when ball goes behind own goal line
    - Touchback handling for special teams plays
    """
    
    def process_play(self, current_position: FieldPosition, raw_yards_gained: int, 
                    play_type: str = "normal") -> FieldResult:
        """
        Process a play result and update field position
        
        Args:
            current_position: Current ball position
            raw_yards_gained: Yards from play simulation (can exceed field boundaries)
            play_type: Type of play for special handling ("normal", "punt", "kickoff", etc.)
        
        Returns:
            FieldResult with updated position and any scoring/special events
        """
        # Calculate target position from raw yards
        target_yard_line = current_position.yard_line + raw_yards_gained
        
        # Initialize result with raw data
        result = FieldResult(
            raw_yards_gained=raw_yards_gained,
            actual_yards_gained=raw_yards_gained,  # Will be adjusted
            new_field_position=current_position,   # Will be updated
            field_events=[]
        )
        
        # Apply field boundary constraints and detect scoring
        if target_yard_line >= 100:
            # Ball crossed opponent goal line - TOUCHDOWN
            result.actual_yards_gained = 100 - current_position.yard_line
            result.new_field_position = FieldPosition(
                yard_line=100,
                possession_team=current_position.possession_team,
                field_zone=FieldZone.OPPONENT_END_ZONE
            )
            result.is_scored = True
            result.scoring_type = "touchdown"
            result.points_scored = 6
            result.field_events.append("touchdown")
            result.possession_change = True  # Scoring team kicks off
            
        elif target_yard_line <= 0:
            # Ball went behind own goal line - SAFETY
            result.actual_yards_gained = -current_position.yard_line
            result.new_field_position = FieldPosition(
                yard_line=0,
                possession_team=current_position.possession_team,
                field_zone=FieldZone.OWN_END_ZONE  
            )
            result.is_scored = True
            result.scoring_type = "safety"
            result.points_scored = 2  # Points awarded to OPPONENT
            result.field_events.append("safety")
            result.possession_change = True  # Team that got safety kicks off
            
        else:
            # Normal field position update
            result.actual_yards_gained = raw_yards_gained
            result.new_field_position = FieldPosition(
                yard_line=target_yard_line,
                possession_team=current_position.possession_team,
                field_zone=FieldZone.OWN_TERRITORY  # Will be auto-calculated
            )
        
        # Add field zone change events
        if result.new_field_position.field_zone != current_position.field_zone:
            result.field_events.append(f"entered_{result.new_field_position.field_zone.value}")
        
        return result
    
    def process_turnover(self, current_position: FieldPosition, 
                        turnover_type: str = "fumble") -> FieldResult:
        """
        Handle possession change at current field position
        
        Args:
            current_position: Where the turnover occurred
            turnover_type: "fumble", "interception", "turnover_on_downs", etc.
        
        Returns:
            FieldResult with possession flipped and field position reversed
        """
        # Flip field position perspective (25 yard line becomes 75 yard line for new team)  
        flipped_yard_line = 100 - current_position.yard_line
        
        result = FieldResult(
            raw_yards_gained=0,  # Turnover itself doesn't gain yards
            actual_yards_gained=0,
            new_field_position=FieldPosition(
                yard_line=flipped_yard_line,
                possession_team="opposing_team",  # This would be provided by caller
                field_zone=FieldZone.OWN_TERRITORY  # Will be auto-calculated
            ),
            possession_change=True,
            field_events=[turnover_type, "possession_change"]
        )
        
        return result