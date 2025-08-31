from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class PlayResult:
    """Result of a single play execution with enhanced tracking"""
    # Core play information
    play_type: str        # "run", "pass", "punt", "field_goal", "kickoff"
    outcome: str          # "gain", "touchdown", "incomplete", "sack", "fumble", "interception"
    yards_gained: int     # -10 to 80+ yards
    time_elapsed: int     # seconds off clock
    is_turnover: bool     # fumble, interception
    is_score: bool        # touchdown, field goal, safety
    score_points: int     # points scored on this play (0, 2, 3, 6)
    
    # Enhanced tracking information
    primary_player: Optional[str] = None      # Player who carried/caught/threw the ball
    tackler: Optional[str] = None             # Player who made the tackle
    formation: Optional[str] = None           # Offensive formation used
    defensive_call: Optional[str] = None      # Defensive scheme
    play_description: str = ""                # Human-readable play description
    
    # Context information  
    down: int = 0                            # Down when play was executed
    distance: int = 0                        # Distance needed for first down
    field_position: int = 0                  # Yard line where play started
    quarter: int = 0                         # Quarter when play occurred
    game_clock: int = 0                      # Time remaining when play started
    
    # Advanced metrics (for future use)
    pressure_applied: bool = False            # Was QB under pressure
    coverage_beaten: bool = False             # Was defender beaten on the play
    big_play: bool = False                   # 20+ yard gain
    goal_line_play: bool = False             # Play inside 10 yard line
    
    def get_summary(self) -> str:
        """Generate a human-readable summary of the play"""
        if self.play_description:
            return self.play_description
            
        # Generate basic description
        if self.play_type == "run":
            if self.outcome == "touchdown":
                return f"{self.yards_gained}-yard rushing touchdown"
            elif self.outcome == "fumble":
                return f"{self.yards_gained}-yard run, fumble"
            else:
                return f"{self.yards_gained}-yard rush"
        elif self.play_type == "pass":
            if self.outcome == "touchdown":
                return f"{self.yards_gained}-yard passing touchdown"
            elif self.outcome == "interception":
                return "Pass intercepted"
            elif self.outcome == "incomplete":
                return "Pass incomplete"
            elif self.outcome == "sack":
                return f"Sack for {abs(self.yards_gained)} yards"
            else:
                return f"{self.yards_gained}-yard pass completion"
        elif self.play_type == "field_goal":
            if self.outcome == "field_goal":
                return "Field goal good"
            else:
                return "Field goal missed"
        elif self.play_type == "punt":
            return f"{self.yards_gained}-yard punt"
        
        return f"{self.play_type}: {self.outcome} for {self.yards_gained} yards"