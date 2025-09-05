class OffensivePlayType:
    """Constants for offensive play types in football simulation"""
    
    # Core offensive plays
    RUN = "offensive_run"
    PASS = "offensive_pass"
    PLAY_ACTION_PASS = "offensive_play_action"
    SCREEN_PASS = "offensive_screen"
    QUICK_SLANT = "offensive_quick_slant"
    DEEP_BALL = "offensive_deep_ball"
    
    # Special situations
    FIELD_GOAL = "offensive_field_goal"
    PUNT = "offensive_punt"
    KICKOFF = "offensive_kickoff"
    ONSIDE_KICK = "offensive_onside_kick"
    TWO_POINT_CONVERSION = "offensive_two_point"
    KNEEL_DOWN = "offensive_kneel"
    SPIKE = "offensive_spike"
    
    @classmethod
    def get_all_types(cls):
        """Get a list of all available offensive play types"""
        return [
            cls.RUN, cls.PASS, cls.PLAY_ACTION_PASS, cls.SCREEN_PASS,
            cls.QUICK_SLANT, cls.DEEP_BALL, cls.FIELD_GOAL, cls.PUNT,
            cls.KICKOFF, cls.ONSIDE_KICK, cls.TWO_POINT_CONVERSION,
            cls.KNEEL_DOWN, cls.SPIKE
        ]
    
    @classmethod
    def get_core_plays(cls):
        """Get core plays (most commonly used)"""
        return [cls.RUN, cls.PASS, cls.FIELD_GOAL, cls.PUNT]


class PuntPlayType:
    """Constants for punt execution types - used by PuntSimulator for execution-only logic"""
    
    # Punt execution types (received from external play calling systems)
    REAL_PUNT = "punt_real"
    FAKE_PUNT_PASS = "punt_fake_pass" 
    FAKE_PUNT_RUN = "punt_fake_run"
    
    @classmethod
    def get_all_types(cls):
        """Get a list of all available punt execution types"""
        return [cls.REAL_PUNT, cls.FAKE_PUNT_PASS, cls.FAKE_PUNT_RUN]
    
    @classmethod
    def is_fake_punt(cls, punt_type: str) -> bool:
        """Check if punt type is a fake punt"""
        return punt_type in [cls.FAKE_PUNT_PASS, cls.FAKE_PUNT_RUN]