class PlayEngineParams:
    """Container for all parameters needed by the play engine"""
    
    def __init__(self, offensive_team, defensive_team, offensive_playCallParams, defensive_playCallParams):
        self.offensive_team = offensive_team
        self.defensive_team = defensive_team
        self.offensive_playCallParams = offensive_playCallParams
        self.defensive_playCallParams = defensive_playCallParams
    
    def get_offensive_play(self):
        """Get the offensive play call params"""
        return self.offensive_playCallParams
    
    def get_defensive_play(self):
        """Get the defensive play call params"""
        return self.defensive_playCallParams
    
    def get_offensive_team(self):
        """Get the offensive team"""
        return self.offensive_team
    
    def get_defensive_team(self):
        """Get the defensive team"""
        return self.defensive_team
    
    def __str__(self):
        return f"PlayEngineParams(offensive_team={self.offensive_team}, defensive_team={self.defensive_team})"
    
    def __repr__(self):
        return self.__str__()