class PlayEngineParams:
    """Container for all parameters needed by the play engine"""

    def __init__(self, offensive_players, defensive_players, offensive_play_call, defensive_play_call,
                 offensive_team_id=None, defensive_team_id=None, momentum_modifier=1.0,
                 weather_condition="clear", crowd_noise_level=0, clutch_factor=0.0,
                 primetime_variance=0.0, is_away_team=False, selected_ball_carrier=None,
                 performance_tracker=None, random_event_checker=None,
                 field_position=50, down=1, distance=10):
        """
        Initialize play engine parameters

        Args:
            offensive_players: List of 11 Player objects
            defensive_players: List of 11 Player objects
            offensive_play_call: OffensivePlayCall object with play type and formation
            defensive_play_call: DefensivePlayCall object with play type and formation
            offensive_team_id: Team ID of the offensive team (1-32)
            defensive_team_id: Team ID of the defensive team (1-32)
            momentum_modifier: Performance multiplier from team momentum (0.95 to 1.05)
            weather_condition: Weather condition ("clear", "rain", "snow", "heavy_wind")
            crowd_noise_level: Crowd noise intensity (0-100, 0=quiet, 100=deafening)
            clutch_factor: Clutch pressure level (0.0-1.0 from urgency analyzer)
            primetime_variance: Additional outcome variance for primetime games (0.0-0.15)
            is_away_team: Whether the offensive team is the away team (for crowd noise penalties)
            selected_ball_carrier: Pre-selected RB for run plays (for workload distribution)
            performance_tracker: PlayerPerformanceTracker for hot/cold streaks (Tollgate 7)
            random_event_checker: RandomEventChecker for rare events (Tollgate 7)
            field_position: Current field position (1-100 scale, default 50)
            down: Current down (1-4, default 1)
            distance: Yards to go for first down (default 10)
        """
        self.offensive_players = offensive_players  # List of 11 Player objects
        self.defensive_players = defensive_players  # List of 11 Player objects
        self.offensive_play_call = offensive_play_call
        self.defensive_play_call = defensive_play_call
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id
        self.momentum_modifier = momentum_modifier  # Store momentum modifier

        # Environmental modifiers (Tollgate 6: Environmental & Situational Modifiers)
        self.weather_condition = weather_condition
        self.crowd_noise_level = crowd_noise_level
        self.clutch_factor = clutch_factor
        self.primetime_variance = primetime_variance
        self.is_away_team = is_away_team

        # RB rotation (for workload distribution between starter/backup)
        self.selected_ball_carrier = selected_ball_carrier

        # Variance & Unpredictability (Tollgate 7)
        self.performance_tracker = performance_tracker
        self.random_event_checker = random_event_checker

        # Game Situation (Field Position, Down & Distance)
        self.field_position = field_position
        self.down = down
        self.distance = distance
    
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

    def get_momentum_modifier(self):
        """Get the momentum modifier for offensive team"""
        return self.momentum_modifier

    def get_weather_condition(self):
        """Get the weather condition (clear, rain, snow, heavy_wind)"""
        return self.weather_condition

    def get_crowd_noise_level(self):
        """Get the crowd noise level (0-100)"""
        return self.crowd_noise_level

    def get_clutch_factor(self):
        """Get the clutch pressure factor (0.0-1.0)"""
        return self.clutch_factor

    def get_primetime_variance(self):
        """Get the primetime variance multiplier (0.0-0.15)"""
        return self.primetime_variance

    def is_away_team_offensive(self):
        """Check if the offensive team is the away team"""
        return self.is_away_team

    def get_selected_ball_carrier(self):
        """Get the pre-selected ball carrier for run plays (RB rotation)"""
        return self.selected_ball_carrier

    def get_performance_tracker(self):
        """Get the player performance tracker (hot/cold streaks)"""
        return self.performance_tracker

    def get_random_event_checker(self):
        """Get the random event checker (rare events like blocked punts)"""
        return self.random_event_checker

    def get_field_position(self):
        """Get the current field position (1-100 scale)"""
        return self.field_position

    def get_down(self):
        """Get the current down (1-4)"""
        return self.down

    def get_distance(self):
        """Get the yards to go for first down"""
        return self.distance

    def __str__(self):
        off_count = len(self.offensive_players) if self.offensive_players else 0
        def_count = len(self.defensive_players) if self.defensive_players else 0
        return f"PlayEngineParams(offensive_players={off_count}, defensive_players={def_count})"

    def __repr__(self):
        return self.__str__()