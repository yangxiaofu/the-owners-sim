from dataclasses import dataclass
from typing import List, Dict

@dataclass 
class BlockingResult:
    """Result of an individual blocking matchup"""
    blocker_position: str      # "LT", "LG", "C", "RG", "RT", "TE", "FB"
    blocker_rating: int
    defender_position: str     # "LE", "DT", "NT", "RE", "LOLB", "MLB", "ROLB"
    defender_rating: int
    success: bool             # Did the block succeed?
    impact_factor: float      # How much this block affected the play (0.0-1.0)

@dataclass
class RunPlayCall:
    """Detailed specification for a running play"""
    direction: str  # "left", "right", "center", "outside_left", "outside_right"
    play_type: str  # "dive", "power", "sweep", "draw", "counter"
    formation: str  # "I_formation", "shotgun", "singleback", "pistol"
    
    @classmethod
    def default_inside_run(cls):
        return cls(direction="center", play_type="dive", formation="singleback")

@dataclass
class RunResult:
    """Detailed result of a run play simulation"""
    outcome: str              # "gain", "touchdown", "fumble", "safety"
    yards_gained: int
    blocking_results: List[BlockingResult]
    rb_vs_defenders: Dict     # RB success vs unblocked defenders
    play_breakdown: str       # Text description of what happened