from abc import ABC, abstractmethod
from typing import Dict, Tuple
from ..field.field_state import FieldState
from .data_structures import PlayResult


class PlayType(ABC):
    """Abstract base class for all play types using Strategy pattern"""
    
    @abstractmethod
    def simulate(self, offense_team: Dict, defense_team: Dict, field_state: FieldState) -> PlayResult:
        """
        Simulate the play and return the result
        
        Args:
            offense_team: Dict containing offensive team ratings and data
            defense_team: Dict containing defensive team ratings and data  
            field_state: Current field position, down, distance, etc.
            
        Returns:
            PlayResult: Complete result of the play execution
        """
        pass
    
    def _calculate_time_elapsed(self, play_type: str, outcome: str) -> int:
        """Calculate seconds elapsed for this play (shared logic)"""
        import random
        
        if play_type == "pass" and outcome == "incomplete":
            return random.randint(3, 8)  # Clock stops on incomplete
        elif outcome == "touchdown":
            return random.randint(5, 15)  # Quick scoring plays
        elif play_type in ["punt", "field_goal", "kickoff"]:
            return random.randint(8, 15)  # Special teams plays
        else:
            return random.randint(15, 40)  # Normal running clock
    
    def _calculate_points(self, outcome: str) -> int:
        """Calculate points scored for this outcome (shared logic)"""
        if outcome == "touchdown":
            return 6  # Plus extra point (7 total)
        elif outcome == "field_goal":
            return 3
        elif outcome == "safety":
            return 2
        else:
            return 0