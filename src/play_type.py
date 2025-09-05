class PlayType:
    """Constants for different play types in football simulation"""
    
    RUN = "run"
    PASS = "pass"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"
    KICKOFF = "kickoff"
    
    @classmethod
    def get_all_types(cls):
        """Get a list of all available play types"""
        return [cls.RUN, cls.PASS, cls.PUNT, cls.FIELD_GOAL, cls.KICKOFF]