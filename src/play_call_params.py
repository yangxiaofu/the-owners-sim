class PlayCallParams:
    """Container for play call parameters"""
    
    def __init__(self, play_type, side=None):
        self.play_type = play_type
        self.side = side  # 'offense' or 'defense', can be inferred from play_type
        
        # Auto-detect side based on play_type string prefix
        if self.side is None:
            if isinstance(play_type, str):
                if play_type.startswith('offensive_'):
                    self.side = 'offense'
                elif play_type.startswith('defensive_'):
                    self.side = 'defense'
    
    def get_play_type(self):
        """Get the play type"""
        return self.play_type
    
    def get_side(self):
        """Get the side (offense/defense)"""
        return self.side
    
    def is_offensive(self):
        """Check if this is an offensive play"""
        return self.side == 'offense'
    
    def is_defensive(self):
        """Check if this is a defensive play"""
        return self.side == 'defense'
    
    def __str__(self):
        return f"PlayCallParams(play_type='{self.play_type}', side='{self.side}')"
    
    def __repr__(self):
        return self.__str__()