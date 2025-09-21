class PlayEngineParams:
    """Container for all parameters needed by the play engine"""
    
    def __init__(self, offensive_players, defensive_players, offensive_play_call, defensive_play_call,
                 offensive_team_id=None, defensive_team_id=None):
        """
        Initialize play engine parameters

        Args:
            offensive_players: List of 11 Player objects
            defensive_players: List of 11 Player objects
            offensive_play_call: OffensivePlayCall object with play type and formation
            defensive_play_call: DefensivePlayCall object with play type and formation
            offensive_team_id: Team ID of the offensive team (1-32)
            defensive_team_id: Team ID of the defensive team (1-32)
        """
        self.offensive_players = offensive_players  # List of 11 Player objects
        self.defensive_players = defensive_players  # List of 11 Player objects
        self.offensive_play_call = offensive_play_call
        self.defensive_play_call = defensive_play_call
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id
    
    def get_offensive_play_call(self):
        """Get the offensive play call object"""
        return self.offensive_play_call
    
    def get_defensive_play_call(self):
        """Get the defensive play call object"""
        return self.defensive_play_call
    
    def get_offensive_players(self):
        """Get the offensive players (11-man unit)"""
        return self.offensive_players
    
    def get_defensive_players(self):
        """Get the defensive players (11-man unit)"""
        return self.defensive_players

    def get_offensive_team_id(self):
        """Get the offensive team ID"""
        return self.offensive_team_id

    def get_defensive_team_id(self):
        """Get the defensive team ID"""
        return self.defensive_team_id
    
    def __str__(self):
        off_count = len(self.offensive_players) if self.offensive_players else 0
        def_count = len(self.defensive_players) if self.defensive_players else 0
        return f"PlayEngineParams(offensive_players={off_count}, defensive_players={def_count})"
    
    def __repr__(self):
        return self.__str__()