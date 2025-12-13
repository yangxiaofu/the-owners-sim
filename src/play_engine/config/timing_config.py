"""
NFL Realistic Timing Configuration

Centralizes all play timing parameters for easy designer tweaking.
Times include full play clock cycle: huddle + snap count + play execution + getting set.
"""

class NFLTimingConfig:
    """Centralized timing configuration for all play types"""
    
    # Run plays - includes huddle, snap, execution, tackling, getting back up
    RUN_PLAY_MIN_SECONDS = 25
    RUN_PLAY_MAX_SECONDS = 40
    
    # Pass plays - includes huddle, snap, routes, completion/incompletion, getting set
    PASS_PLAY_MIN_SECONDS = 15  
    PASS_PLAY_MAX_SECONDS = 40
    
    # Field goal attempts - includes setup, snap, hold, kick
    FIELD_GOAL_MIN_SECONDS = 3
    FIELD_GOAL_MAX_SECONDS = 5
    FAKE_FIELD_GOAL_MIN_SECONDS = 15  # If fake, treated like normal play
    FAKE_FIELD_GOAL_MAX_SECONDS = 40
    
    # Punt plays - includes setup, snap, punt, coverage, return
    PUNT_MIN_SECONDS = 10
    PUNT_MAX_SECONDS = 20
    FAKE_PUNT_MIN_SECONDS = 15  # If fake, treated like normal play  
    FAKE_PUNT_MAX_SECONDS = 40
    
    # Kickoff plays - includes setup, kick, coverage, return, touchback
    KICKOFF_MIN_SECONDS = 5   # Current values look good based on user feedback
    KICKOFF_MAX_SECONDS = 8

    # Extra point attempts - includes setup, snap, hold, kick
    EXTRA_POINT_MIN_SECONDS = 3
    EXTRA_POINT_MAX_SECONDS = 5
    TWO_POINT_CONVERSION_MIN_SECONDS = 15  # Similar to normal play
    TWO_POINT_CONVERSION_MAX_SECONDS = 25

    @classmethod
    def get_run_play_timing(cls):
        """Get run play timing range"""
        return cls.RUN_PLAY_MIN_SECONDS, cls.RUN_PLAY_MAX_SECONDS
    
    @classmethod  
    def get_pass_play_timing(cls):
        """Get pass play timing range"""
        return cls.PASS_PLAY_MIN_SECONDS, cls.PASS_PLAY_MAX_SECONDS
        
    @classmethod
    def get_field_goal_timing(cls, is_fake=False):
        """Get field goal timing range"""
        if is_fake:
            return cls.FAKE_FIELD_GOAL_MIN_SECONDS, cls.FAKE_FIELD_GOAL_MAX_SECONDS
        return cls.FIELD_GOAL_MIN_SECONDS, cls.FIELD_GOAL_MAX_SECONDS
    
    @classmethod
    def get_punt_timing(cls, is_fake=False):
        """Get punt timing range""" 
        if is_fake:
            return cls.FAKE_PUNT_MIN_SECONDS, cls.FAKE_PUNT_MAX_SECONDS
        return cls.PUNT_MIN_SECONDS, cls.PUNT_MAX_SECONDS
        
    @classmethod
    def get_kickoff_timing(cls):
        """Get kickoff timing range"""
        return cls.KICKOFF_MIN_SECONDS, cls.KICKOFF_MAX_SECONDS

    @classmethod
    def get_extra_point_timing(cls, is_two_point=False):
        """Get extra point timing range"""
        if is_two_point:
            return cls.TWO_POINT_CONVERSION_MIN_SECONDS, cls.TWO_POINT_CONVERSION_MAX_SECONDS
        return cls.EXTRA_POINT_MIN_SECONDS, cls.EXTRA_POINT_MAX_SECONDS