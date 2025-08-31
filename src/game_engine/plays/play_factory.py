from typing import Dict
from .play_types import PlayType
from .run_play import RunPlay
from .pass_play import PassPlay
from .kick_play import KickPlay
from .punt_play import PuntPlay


class PlayFactory:
    """Factory class to create appropriate PlayType instances using Strategy pattern"""
    
    @staticmethod
    def create_play(play_type: str, config: Dict = None) -> PlayType:
        """
        Create and return the appropriate PlayType instance
        
        Args:
            play_type: Type of play ("run", "pass", "field_goal", "punt", etc.)
            config: Optional configuration dict (reserved for future use)
            
        Returns:
            PlayType: Instance of the appropriate play class
            
        Raises:
            ValueError: If play_type is not recognized
        """
        config = config or {}
        
        if play_type == "run":
            return RunPlay()
        elif play_type == "pass":
            return PassPlay()
        elif play_type == "field_goal":
            return KickPlay()
        elif play_type == "punt":
            return PuntPlay()
        else:
            raise ValueError(f"Unknown play type: {play_type}")
    
    @staticmethod
    def get_supported_play_types() -> list[str]:
        """Return a list of all supported play types"""
        return ["run", "pass", "field_goal", "punt"]
    
    @staticmethod
    def is_supported_play_type(play_type: str) -> bool:
        """Check if a play type is supported"""
        return play_type in PlayFactory.get_supported_play_types()