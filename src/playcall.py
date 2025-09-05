import random
from play_engine.play_types.offensive_types import OffensivePlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from play_call_params import PlayCallParams

class PlayCall:
    """Simple dummy class that generates random play calls"""
    
    def __init__(self, team, side='offense'):
        self.team = team
        self.side = side  # 'offense' or 'defense'
    
    def randomGenerate(self):
        """Generate a random play call based on side"""
        if self.side == 'offense':
            plays = OffensivePlayType.get_core_plays()  # Use core plays for simplicity
            selected_play_type = random.choice(plays)
        else:  # defense
            plays = DefensivePlayType.get_core_defenses()  # Use core defenses
            selected_play_type = random.choice(plays)
            
        return PlayCallParams(selected_play_type)