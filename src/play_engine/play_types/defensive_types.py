class DefensivePlayType:
    """Constants for defensive play types in football simulation"""
    
    # Coverage types
    COVER_0 = "defensive_cover_0"  # No deep help, all-out pressure
    COVER_1 = "defensive_cover_1"  # Man-to-man with 1 high safety
    COVER_2 = "defensive_cover_2"  # Zone with 2 high safeties
    COVER_3 = "defensive_cover_3"  # 3 deep zones
    MAN_COVERAGE = "defensive_man_coverage"
    ZONE_COVERAGE = "defensive_zone_coverage"
    
    # Rush/Pressure types
    FOUR_MAN_RUSH = "defensive_four_man_rush"
    BLITZ = "defensive_blitz"  # 5+ rushers
    CORNER_BLITZ = "defensive_corner_blitz"
    SAFETY_BLITZ = "defensive_safety_blitz"
    A_GAP_BLITZ = "defensive_a_gap_blitz"
    EDGE_RUSH = "defensive_edge_rush"
    
    # Run defense
    RUN_STUFF = "defensive_run_stuff"  # Run-stopping alignment
    GAP_CONTROL = "defensive_gap_control"
    PURSUIT_DEFENSE = "defensive_pursuit"
    
    # Special situations
    GOAL_LINE_DEFENSE = "defensive_goal_line"
    PREVENT_DEFENSE = "defensive_prevent"  # Deep coverage, give up short
    NICKEL_DEFENSE = "defensive_nickel"  # 5 DBs
    DIME_DEFENSE = "defensive_dime"  # 6 DBs
    
    @classmethod
    def get_all_types(cls):
        """Get a list of all available defensive play types"""
        return [
            cls.COVER_0, cls.COVER_1, cls.COVER_2, cls.COVER_3,
            cls.MAN_COVERAGE, cls.ZONE_COVERAGE, cls.FOUR_MAN_RUSH,
            cls.BLITZ, cls.CORNER_BLITZ, cls.SAFETY_BLITZ, cls.A_GAP_BLITZ,
            cls.EDGE_RUSH, cls.RUN_STUFF, cls.GAP_CONTROL, cls.PURSUIT_DEFENSE,
            cls.GOAL_LINE_DEFENSE, cls.PREVENT_DEFENSE, cls.NICKEL_DEFENSE,
            cls.DIME_DEFENSE
        ]
    
    @classmethod
    def get_core_defenses(cls):
        """Get core defensive plays (most commonly used)"""
        return [cls.COVER_2, cls.COVER_3, cls.BLITZ, cls.FOUR_MAN_RUSH]