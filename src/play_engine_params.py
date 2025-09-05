class PlayEngineParams:
    """Container for all parameters needed by the play engine"""
    
    def __init__(self, offensive_players, defensive_players, offensive_playCallParams, defensive_playCallParams):
        self.offensive_players = offensive_players  # List of 11 Player objects
        self.defensive_players = defensive_players  # List of 11 Player objects
        self.offensive_playCallParams = offensive_playCallParams
        self.defensive_playCallParams = defensive_playCallParams
    
    def get_offensive_play(self):
        """Get the offensive play call params"""
        return self.offensive_playCallParams
    
    def get_defensive_play(self):
        """Get the defensive play call params"""
        return self.defensive_playCallParams
    
    def get_offensive_players(self):
        """Get the offensive players (11-man unit)"""
        return self.offensive_players
    
    def get_defensive_players(self):
        """Get the defensive players (11-man unit)"""
        return self.defensive_players
    
    def __str__(self):
        off_count = len(self.offensive_players) if self.offensive_players else 0
        def_count = len(self.defensive_players) if self.defensive_players else 0
        return f"PlayEngineParams(offensive_players={off_count}, defensive_players={def_count})"
    
    def __repr__(self):
        return self.__str__()