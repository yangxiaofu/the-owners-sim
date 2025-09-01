from abc import ABC, abstractmethod
from typing import Dict, Any
from ...plays.data_structures import PlayResult
from ...field.game_state import GameState


class ClockStrategy(ABC):
    """
    Abstract base class for coaching archetype-driven clock management strategies.
    
    Each concrete implementation represents how different coaching archetypes
    handle time consumption decisions during plays.
    """
    
    @abstractmethod
    def calculate_time_elapsed(self, play_result: PlayResult, game_context: Dict[str, Any]) -> int:
        """
        Calculate the time elapsed for a play based on coaching archetype.
        
        Args:
            play_result: The result of the executed play
            game_context: Current game state information including:
                - down: Current down (1-4)
                - yards_to_go: Yards needed for first down
                - field_position: Current field position
                - quarter: Current quarter (1-4)
                - time_remaining: Time remaining in current period
                - score_differential: Point difference (positive if leading)
                - timeouts_remaining: Timeouts available
                
        Returns:
            int: Time elapsed in seconds
        """
        pass
    
    @abstractmethod
    def get_archetype_name(self) -> str:
        """
        Get the name of the coaching archetype this strategy represents.
        
        Returns:
            str: The archetype name (e.g., "Conservative", "Aggressive", "Adaptive")
        """
        pass