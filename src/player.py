class Position:
    """Football position constants"""
    
    # Offensive positions
    QB = "quarterback"
    RB = "running_back"
    FB = "fullback"
    WR = "wide_receiver"
    TE = "tight_end"
    LT = "left_tackle"
    LG = "left_guard"
    C = "center"
    RG = "right_guard"
    RT = "right_tackle"
    
    # Defensive positions
    # Defensive Line
    DE = "defensive_end"
    DT = "defensive_tackle"
    NT = "nose_tackle"
    LEO = "leo"  # Weak-side DE in some schemes
    
    # Linebackers (4-3 scheme)
    MIKE = "mike_linebacker"    # Middle linebacker
    SAM = "sam_linebacker"      # Strong-side linebacker  
    WILL = "will_linebacker"    # Weak-side linebacker
    
    # Linebackers (3-4 scheme)
    ILB = "inside_linebacker"   # Inside linebacker (3-4)
    OLB = "outside_linebacker"  # Outside linebacker (3-4)
    
    # Secondary
    CB = "cornerback"
    NCB = "nickel_cornerback"   # Slot cornerback
    FS = "free_safety"
    SS = "strong_safety"
    
    # Special teams
    K = "kicker"
    P = "punter"
    LS = "long_snapper"
    H = "holder"
    KR = "kick_returner"
    PR = "punt_returner"
    
    @classmethod
    def get_offensive_positions(cls):
        """Get all offensive positions"""
        return [cls.QB, cls.RB, cls.FB, cls.WR, cls.TE, cls.LT, cls.LG, cls.C, cls.RG, cls.RT]
    
    @classmethod
    def get_defensive_positions(cls):
        """Get all defensive positions"""
        return [cls.DE, cls.DT, cls.NT, cls.LEO, cls.MIKE, cls.SAM, cls.WILL, 
                cls.ILB, cls.OLB, cls.CB, cls.NCB, cls.FS, cls.SS]
    
    @classmethod
    def get_offensive_line_positions(cls):
        """Get offensive line positions"""
        return [cls.LT, cls.LG, cls.C, cls.RG, cls.RT]


class Player:
    """Represents a football player with position and ratings"""
    
    def __init__(self, name, number, primary_position, ratings=None):
        self.name = name
        self.number = number
        self.primary_position = primary_position
        self.ratings = ratings or {}
        
        # Set default ratings based on position
        self._set_default_ratings()
    
    def _set_default_ratings(self):
        """Set default ratings for the player's position"""
        default_ratings = {
            # General ratings (all positions)
            "overall": 75,
            "speed": 75,
            "strength": 75,
            "agility": 75,
            "awareness": 75,
            
            # Position-specific ratings
            Position.QB: {"accuracy": 75, "arm_strength": 75, "mobility": 75},
            Position.RB: {"carrying": 75, "vision": 75, "elusiveness": 75},
            Position.WR: {"catching": 75, "route_running": 75, "release": 75},
            Position.TE: {"catching": 70, "blocking": 75, "route_running": 70},
            Position.LT: {"pass_blocking": 75, "run_blocking": 75, "technique": 75},
            Position.LG: {"pass_blocking": 75, "run_blocking": 75, "technique": 75},
            Position.C: {"pass_blocking": 75, "run_blocking": 75, "snap_timing": 75},
            Position.RG: {"pass_blocking": 75, "run_blocking": 75, "technique": 75},
            Position.RT: {"pass_blocking": 75, "run_blocking": 75, "technique": 75},
            Position.DE: {"pass_rush": 75, "run_defense": 75, "technique": 75},
            Position.DT: {"pass_rush": 70, "run_defense": 80, "strength": 80},
            Position.NT: {"pass_rush": 65, "run_defense": 85, "strength": 85},
            Position.LEO: {"pass_rush": 80, "run_defense": 70, "speed": 80},
            
            # 4-3 Linebackers
            Position.MIKE: {"coverage": 65, "run_defense": 85, "tackling": 85},
            Position.SAM: {"coverage": 60, "run_defense": 80, "tackling": 80},
            Position.WILL: {"coverage": 70, "run_defense": 75, "speed": 80},
            
            # 3-4 Linebackers
            Position.ILB: {"coverage": 65, "run_defense": 80, "tackling": 80},
            Position.OLB: {"coverage": 65, "pass_rush": 80, "run_defense": 75},
            
            # Secondary
            Position.CB: {"coverage": 85, "speed": 85, "press": 75},
            Position.NCB: {"coverage": 80, "speed": 80, "agility": 85},
            Position.FS: {"coverage": 80, "range": 85, "ball_skills": 80},
            Position.SS: {"coverage": 75, "run_support": 80, "tackling": 80},
            Position.K: {"kick_power": 75, "kick_accuracy": 75, "pressure": 70},
            Position.P: {"punt_power": 75, "punt_accuracy": 75, "hang_time": 75}
        }
        
        # Apply position-specific defaults
        if self.primary_position in default_ratings:
            for rating, value in default_ratings[self.primary_position].items():
                if rating not in self.ratings:
                    self.ratings[rating] = value
        
        # Apply general defaults
        for rating in ["overall", "speed", "strength", "agility", "awareness"]:
            if rating not in self.ratings:
                self.ratings[rating] = 75
    
    def get_rating(self, rating_type):
        """Get a specific rating for this player"""
        return self.ratings.get(rating_type, 50)  # Default to 50 if rating doesn't exist
    
    def can_play_position(self, position):
        """Check if player can play a specific position"""
        # For now, players can only play their primary position
        # Could be extended to allow versatile players
        return self.primary_position == position
    
    def get_effectiveness_at_position(self, position):
        """Get player effectiveness rating at a specific position (0-100)"""
        if position == self.primary_position:
            return self.get_rating("overall")
        else:
            # Reduced effectiveness at non-primary positions
            return max(30, self.get_rating("overall") - 25)
    
    def __str__(self):
        return f"#{self.number} {self.name} ({self.primary_position}) - {self.get_rating('overall')} OVR"
    
    def __repr__(self):
        return f"Player('{self.name}', {self.number}, '{self.primary_position}', overall={self.get_rating('overall')})"