from typing import Dict
from game_engine.plays.play_types import PlayType
from game_engine.plays.run_play import RunPlay
from game_engine.plays.pass_play import PassPlay
from game_engine.plays.kick_play import KickPlay
from game_engine.plays.punt_play import PuntPlay
from game_engine.plays.kickoff_play import KickoffPlay


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
        elif play_type == "kickoff":
            return KickoffPlay()
        else:
            raise ValueError(f"Unknown play type: {play_type}")
    
    @staticmethod
    def get_supported_play_types() -> list[str]:
        """Return a list of all supported play types"""
        return ["run", "pass", "field_goal", "punt", "kickoff"]
    
    @staticmethod
    def is_supported_play_type(play_type: str) -> bool:
        """Check if a play type is supported"""
        return play_type in PlayFactory.get_supported_play_types()