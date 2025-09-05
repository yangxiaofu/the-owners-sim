class PuntOutcome:
    """Constants for all possible punt play outcomes"""
    
    # Real punt outcomes (based on NFL research)
    FAIR_CATCH = "punt_fair_catch"              # Returner signals fair catch
    PUNT_RETURN = "punt_return"                 # Normal return attempt with yardage
    TOUCHBACK = "punt_touchback"                # Punt into end zone, ball at 25-yard line
    OUT_OF_BOUNDS = "punt_out_of_bounds"        # Punt goes out of bounds
    COFFIN_CORNER = "punt_coffin_corner"        # Strategic out of bounds near goal line
    DOWNED = "punt_downed"                      # Coverage team downs ball before end zone
    MUFFED = "punt_muffed"                      # Returner touches but doesn't control (live ball)
    BLOCKED = "punt_blocked"                    # Punt blocked at line of scrimmage
    ILLEGAL_TOUCHING = "punt_illegal_touching"  # Punting team touches first (first touching violation)
    
    # Fake punt outcomes
    FAKE_SUCCESS = "punt_fake_success"          # Fake punt successful (pass/run)
    FAKE_FAILED = "punt_fake_failed"            # Fake punt failed
    FAKE_INTERCEPTION = "punt_fake_interception" # Fake punt pass intercepted
    
    # Penalty-related outcomes
    PRE_SNAP_PENALTY = "punt_pre_snap_penalty"   # Pre-snap penalty negates play
    PENALTY_NEGATED = "punt_penalty_negated"     # During-play penalty affects outcome
    
    @classmethod
    def get_all_outcomes(cls):
        """Get a list of all possible punt outcomes"""
        return [
            cls.FAIR_CATCH, cls.PUNT_RETURN, cls.TOUCHBACK, cls.OUT_OF_BOUNDS,
            cls.COFFIN_CORNER, cls.DOWNED, cls.MUFFED, cls.BLOCKED, 
            cls.ILLEGAL_TOUCHING, cls.FAKE_SUCCESS, cls.FAKE_FAILED,
            cls.FAKE_INTERCEPTION, cls.PRE_SNAP_PENALTY, cls.PENALTY_NEGATED
        ]
    
    @classmethod 
    def get_real_punt_outcomes(cls):
        """Get outcomes specific to real punt attempts"""
        return [
            cls.FAIR_CATCH, cls.PUNT_RETURN, cls.TOUCHBACK, cls.OUT_OF_BOUNDS,
            cls.COFFIN_CORNER, cls.DOWNED, cls.MUFFED, cls.BLOCKED, cls.ILLEGAL_TOUCHING
        ]
    
    @classmethod
    def get_fake_punt_outcomes(cls):
        """Get outcomes specific to fake punt attempts"""
        return [cls.FAKE_SUCCESS, cls.FAKE_FAILED, cls.FAKE_INTERCEPTION]
    
    @classmethod
    def get_penalty_outcomes(cls):
        """Get penalty-related outcomes"""
        return [cls.PRE_SNAP_PENALTY, cls.PENALTY_NEGATED]
    
    @classmethod
    def is_successful_punt(cls, outcome: str) -> bool:
        """Check if punt outcome is considered successful for punting team"""
        successful_outcomes = [
            cls.FAIR_CATCH, cls.TOUCHBACK, cls.OUT_OF_BOUNDS, cls.COFFIN_CORNER,
            cls.DOWNED, cls.ILLEGAL_TOUCHING  # Illegal touching gives receiving team choice but pins them
        ]
        return outcome in successful_outcomes
    
    @classmethod
    def involves_return(cls, outcome: str) -> bool:
        """Check if outcome involves a return attempt"""
        return outcome in [cls.PUNT_RETURN, cls.MUFFED]
    
    @classmethod
    def is_turnover(cls, outcome: str) -> bool:
        """Check if outcome results in a turnover"""
        return outcome in [cls.BLOCKED, cls.FAKE_INTERCEPTION, cls.MUFFED]