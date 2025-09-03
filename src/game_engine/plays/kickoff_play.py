import random
from typing import Dict, Tuple
from game_engine.plays.play_types import PlayType
from game_engine.plays.data_structures import PlayResult
from game_engine.field.field_state import FieldState


class KickoffGameBalance:
    """
    Centralized configuration for kickoff game balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect kickoff game balance.
    Based on 2025 NFL Dynamic Kickoff rules and statistics:
    - Return rate: 32.8% (2024 season with new rules)
    - Average return yards: ~22.5 yards
    - Touchback rate: ~40% estimated
    - Onside recovery: ~12% success rate
    """
    
    # === CORE EFFECTIVENESS CALCULATION ===
    # How much each factor contributes to kickoff success (must sum to 1.0)
    KICKER_EFFECTIVENESS_WEIGHT = 0.3      # Kicker leg strength/accuracy matters
    COVERAGE_EFFECTIVENESS_WEIGHT = 0.4     # Coverage team speed/tackling most important
    RETURNER_EFFECTIVENESS_WEIGHT = 0.3     # Returner speed/vision/elusiveness
    
    # === 2025 NFL DYNAMIC KICKOFF RULES ===
    END_ZONE_TOUCHBACK_LINE = 35           # New 2025 rule: end zone touchbacks to 35
    LANDING_ZONE_TOUCHBACK_LINE = 20       # Landing zone -> end zone touchbacks to 20
    SHORT_KICK_TOUCHBACK_LINE = 40         # Short kicks/out of bounds to 40
    
    # === STATISTICAL BASELINES ===
    BASE_RETURN_RATE = 0.33                # 2024 season average return rate
    AVERAGE_RETURN_YARDS = 22.5            # NFL average under new rules
    BASE_TOUCHBACK_RATE = 0.40             # Estimated baseline touchback rate
    
    # === COVERAGE AND TIMING ===
    COVERAGE_ARRIVAL_TIME = 4.2            # Seconds for coverage to arrive at return point
    HANG_TIME_IMPACT_FACTOR = 0.8          # How much hang time affects coverage effectiveness
    
    # === BREAKAWAY LOGIC ===
    BREAKAWAY_MIN_YARDS = 30               # Minimum return yards for breakaway chance
    BREAKAWAY_BASE_CHANCE = 0.08           # 8% base breakaway probability
    BREAKAWAY_SPEED_BONUS = 0.002          # Bonus per returner speed point above 80
    BREAKAWAY_YARDS_MIN = 25               # Minimum bonus yards on breakaway
    BREAKAWAY_YARDS_MAX = 60               # Maximum bonus yards on breakaway
    
    # === SPECIAL SITUATIONS ===
    ONSIDE_BASE_RECOVERY_RATE = 0.12       # NFL onside kick recovery rate
    FUMBLE_ON_RETURN_RATE = 0.015          # 1.5% fumble rate on returns
    OUT_OF_BOUNDS_PENALTY_RATE = 0.05      # 5% chance kick goes out of bounds
    
    # === STRATEGY SELECTION PROBABILITIES ===
    ONSIDE_DESPERATION_CHANCE = 0.15       # 15% chance of onside in desperation
    LANDING_ZONE_LATE_GAME_CHANCE = 0.12   # Reduced from 15% to 12% to favor deep kicks
    SQUIB_KICK_CHANCE = 0.03               # Reduced from 5% to 3% to favor deep kicks
    SHORT_KICK_CHANCE = 0.02               # Reduced from 3% to 2% to favor deep kicks
    
    # === KICK PLACEMENT SETTINGS ===
    BASE_KICK_SUCCESS_RATE = 0.85          # 85% base chance of hitting target zone
    EFFECTIVENESS_BASE_MODIFIER = 0.9      # Base effectiveness modifier
    EFFECTIVENESS_SKILL_FACTOR = 0.4       # How much skill affects effectiveness
    EFFECTIVENESS_THRESHOLD = 0.7          # Skill threshold for effectiveness calculation
    KICK_VARIANCE_FACTOR = 0.3             # Variance factor for kick placement
    
    # === MISSED TARGET PROBABILITIES ===
    DEEP_KICK_LANDING_ZONE_CHANCE = 0.7    # 70% chance deep kick lands in landing zone when missed
    LANDING_ZONE_SHORT_CHANCE = 0.6        # 60% chance landing zone kick goes short when missed
    
    # === TOUCHBACK RULE FACTORS ===
    LANDING_ZONE_END_ZONE_FACTOR = 0.6     # Factor for landing zone kicks going to end zone
    DOWNED_VS_RETURN_CHANCE = 0.5          # 50% chance of downing vs return in end zone
    
    # === RETURN EFFECTIVENESS SETTINGS ===
    RETURN_EFFECTIVENESS_BASE = 0.8        # Base return effectiveness modifier
    RETURN_EFFECTIVENESS_RANGE = 0.4       # Range of effectiveness modification (0.8-1.2)
    RETURN_VARIANCE_MIN = 0.6              # Minimum return variance multiplier
    RETURN_VARIANCE_FACTOR = 0.4           # Return variance factor
    
    # === RETURN OUTCOME SETTINGS ===
    MIN_RETURN_YARDS = 5                   # Minimum return yards possible
    MAX_FIELD_POSITION = 95                # Maximum field position (goal line)
    FUMBLE_RECOVERY_POSITION_FACTOR = 0.7  # Factor for fumble recovery position
    MIN_FUMBLE_RECOVERY_POSITION = 20      # Minimum fumble recovery position
    
    # === RETURN TOUCHDOWN SETTINGS ===
    RETURN_TD_MIN_YARDS = 75               # Minimum yards for TD chance
    RETURN_TD_CHANCE = 0.02                # 2% TD chance on long returns
    TOUCHDOWN_FIELD_POSITION = 100         # Field position for touchdowns
    
    # === COVERAGE CALCULATION SETTINGS ===
    DEFAULT_COVERAGE_RATING = 70           # Default coverage team rating
    COVERAGE_EFFECTIVENESS_HANG_TIME_BASE = 1.0  # Base hang time effectiveness
    NET_EFFECTIVENESS_PENALTY_BUFFER = 0.3  # Buffer to avoid harsh penalties
    NET_EFFECTIVENESS_MIN = 0.3            # Minimum net effectiveness
    NET_EFFECTIVENESS_MAX = 1.5            # Maximum net effectiveness
    
    # === PLAYER RATING DEFAULTS ===
    DEFAULT_PLAYER_RATING = 50             # Default rating for missing attributes
    DEFAULT_KICKER_BASELINE = 70           # Better baseline for kickers
    DEFAULT_ST_RATING = 70                 # Default special teams rating
    DEFAULT_RETURNER_SPEED = 75            # Default returner speed
    KICKER_SPECIALIST_BONUS = 5            # Bonus for kicker specialists
    NORMALIZE_FACTOR = 100.0               # Factor to normalize ratings to 0-1 range
    
    # === ONSIDE KICK SETTINGS ===
    ONSIDE_HANDS_TEAM_ADVANTAGE = 1.3     # Hands team advantage multiplier
    ONSIDE_RECOVERY_FIELD_POSITION = 45   # Field position when kicking team recovers
    ONSIDE_RECOVERY_YARDS = 15             # Yards gained when kicking team recovers
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense"""
        # Effectiveness weights should sum to 1.0
        total_weight = (cls.KICKER_EFFECTIVENESS_WEIGHT + cls.COVERAGE_EFFECTIVENESS_WEIGHT + 
                       cls.RETURNER_EFFECTIVENESS_WEIGHT)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Effectiveness weights must sum to 1.0, got {total_weight}")
        
        # Probabilities should be between 0 and 1
        probabilities = [
            cls.BASE_RETURN_RATE, cls.BASE_TOUCHBACK_RATE, cls.BREAKAWAY_BASE_CHANCE,
            cls.ONSIDE_BASE_RECOVERY_RATE, cls.FUMBLE_ON_RETURN_RATE, cls.OUT_OF_BOUNDS_PENALTY_RATE,
            cls.ONSIDE_DESPERATION_CHANCE, cls.LANDING_ZONE_LATE_GAME_CHANCE, cls.SQUIB_KICK_CHANCE,
            cls.SHORT_KICK_CHANCE, cls.BASE_KICK_SUCCESS_RATE, cls.DEEP_KICK_LANDING_ZONE_CHANCE,
            cls.LANDING_ZONE_SHORT_CHANCE, cls.DOWNED_VS_RETURN_CHANCE, cls.RETURN_TD_CHANCE
        ]
        for prob in probabilities:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability {prob} must be between 0 and 1")


# Validate configuration on import
KickoffGameBalance.validate_configuration()


# Kickoff Strategy Matrices (KISS: Simple dictionary structure)
KICKOFF_STRATEGY_MATRICES = {
    "deep_kick": {
        "target_zone": "end_zone",
        "base_touchback_chance": 0.68,    # Solution 1: Precision tuning for return rate compliance
        "base_return_yards": 23.5,    # Increased slightly to target 22.5 average
        "kicker_attributes": ["leg_strength", "accuracy"],
        "returner_attributes": ["speed", "vision", "elusiveness"],
        "coverage_effectiveness": 1.0,
        "hang_time": 4.5,
        "variance": 0.8,
        "breakaway_threshold": 85
    },
    "landing_zone_kick": {
        "target_zone": "landing_zone", 
        "base_touchback_chance": 0.15,     # Most eventually go to end zone
        "base_return_yards": 25.0,         # Slightly better field position
        "kicker_attributes": ["accuracy", "technique"],
        "returner_attributes": ["acceleration", "vision"],
        "coverage_effectiveness": 0.9,     # Less time for coverage setup
        "hang_time": 4.2,
        "variance": 1.0,
        "breakaway_threshold": 82
    },
    "short_kick": {
        "target_zone": "short_zone",       # Beyond landing zone, before setup zone
        "base_touchback_chance": 0.0,      # No touchbacks possible
        "base_return_yards": 35.0,         # Great field position for returner
        "kicker_attributes": ["accuracy", "technique"],
        "returner_attributes": ["hands", "acceleration"],
        "coverage_effectiveness": 0.7,     # Coverage gets there faster
        "hang_time": 3.8,
        "variance": 1.2,
        "breakaway_threshold": 80
    },
    "squib_kick": {
        "target_zone": "squib_zone",       # Ground ball to around 30-40 yard line
        "base_touchback_chance": 0.0,
        "base_return_yards": 18.0,         # Poor return yards but predictable
        "kicker_attributes": ["technique", "accuracy"], 
        "returner_attributes": ["hands", "vision"],
        "coverage_effectiveness": 1.3,     # Coverage team has advantage
        "hang_time": 2.5,                  # Low kick, fast coverage arrival
        "variance": 0.6,
        "breakaway_threshold": 90          # Very hard to break away on squib
    },
    "onside_kick": {
        "target_zone": "onside_zone",      # 10-15 yard area for recovery battle
        "base_recovery_chance": KickoffGameBalance.ONSIDE_BASE_RECOVERY_RATE,
        "base_touchback_chance": 0.0,      # Onside kicks never result in touchbacks
        "base_return_yards": 45.0,         # If recovered by return team, great field position
        "kicker_attributes": ["technique", "accuracy"],
        "returner_attributes": ["hands", "awareness"],
        "coverage_effectiveness": 0.3,     # Coverage team focused on recovery, not tackling
        "hang_time": 2.0,
        "variance": 1.5,
        "breakaway_threshold": 75
    }
}


class KickoffPlay(PlayType):
    """Handles kickoff and return simulation using 2025 NFL Dynamic Kickoff rules"""
    
    def _extract_player_ratings(self, personnel, team_type: str) -> Dict:
        """Override to use simplified ratings for kickoff plays"""
        # For kickoffs, we primarily use special teams ratings
        if hasattr(personnel, 'special_teams_rating'):
            base_rating = personnel.special_teams_rating
        else:
            base_rating = KickoffGameBalance.DEFAULT_ST_RATING
        
        return {
            'special_teams': base_rating,
            'ol': base_rating,  # For protection on kicks
            'dl': base_rating,  # For rush on kicks
            'lb': base_rating,  # General coverage
            'db': base_rating   # Coverage/return team
        }
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a kickoff play using selected personnel"""
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")  # Kicking team
        defense_ratings = self._extract_player_ratings(personnel, "defense")  # Return team
        
        # Determine kickoff strategy based on game situation
        kick_strategy = self._determine_kick_strategy(field_state, personnel)
        
        # Simulate the kickoff and return
        outcome, yards_gained, final_field_position = self._simulate_kickoff_and_return(
            offense_ratings, defense_ratings, personnel, kick_strategy, field_state
        )
        
        # Calculate time elapsed and other result properties
        time_elapsed = self._calculate_time_elapsed("kickoff", outcome)
        is_turnover = outcome in ["fumble", "onside_recovery"]
        is_score = outcome == "touchdown"  # Rare but possible on kickoff return
        score_points = self._calculate_points(outcome)
        
        # Create play result
        play_result = PlayResult(
            play_type="kickoff",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points,
            final_field_position=final_field_position
        )
        
        # Populate situational context from field state
        self._populate_situational_context(play_result, field_state)
        
        return play_result
    
    def _determine_kick_strategy(self, field_state: FieldState, personnel) -> str:
        """SOLID: Single responsibility - determine kickoff strategy based on game situation"""
        
        # TODO: When game context (score, time remaining) is available, use more sophisticated logic
        # For now, use probabilistic approach with some situational awareness
        
        # Onside kick situations (when trailing late - simplified logic for now)
        if field_state.down == 4 and field_state.field_position < 50:  # Desperation situation proxy
            if random.random() < KickoffGameBalance.ONSIDE_DESPERATION_CHANCE:
                return "onside_kick"
        
        # Late game situations might favor coverage opportunities
        if field_state.down >= 3:  # Late in drive might indicate late in game
            if random.random() < KickoffGameBalance.LANDING_ZONE_LATE_GAME_CHANCE:
                return "landing_zone_kick"
        
        # Squib kick in windy conditions (placeholder for weather system)
        if random.random() < KickoffGameBalance.SQUIB_KICK_CHANCE:
            return "squib_kick"
        
        # Short kick if special teams mismatch favors coverage (placeholder)
        if random.random() < KickoffGameBalance.SHORT_KICK_CHANCE:
            return "short_kick"
        
        # Default to deep kick (most common)
        return "deep_kick"
    
    def _simulate_kickoff_and_return(self, offense_ratings: Dict, defense_ratings: Dict,
                                   personnel, kick_strategy: str, field_state: FieldState) -> Tuple[str, int, int]:
        """SOLID: Single responsibility - main kickoff simulation using strategy matrix"""
        
        matrix = KICKOFF_STRATEGY_MATRICES[kick_strategy]
        
        # Step 1: Handle special case - onside kick
        if kick_strategy == "onside_kick":
            return self._simulate_onside_kick(offense_ratings, defense_ratings, matrix)
        
        # Step 2: Determine kick outcome and landing zone
        kick_outcome = self._simulate_kick_placement(personnel, kick_strategy, matrix)
        
        # Step 3: Apply 2025 NFL Dynamic Kickoff Rules for touchbacks
        touchback_result = self._check_touchback_rules(kick_outcome, matrix)
        if touchback_result:
            return touchback_result
        
        # Step 4: Simulate return attempt (mandatory for landing zone kicks)
        return self._simulate_return_attempt(
            offense_ratings, defense_ratings, personnel, kick_outcome, matrix
        )
    
    def _simulate_kick_placement(self, personnel, kick_strategy: str, matrix: Dict) -> Dict:
        """SOLID: Single responsibility - simulate where the kick lands"""
        
        # Calculate kicker effectiveness for this strategy
        kicker_effectiveness = self._calculate_kicker_effectiveness(personnel, kick_strategy, matrix)
        
        # Determine if kick goes out of bounds (penalty situation)
        if random.random() < KickoffGameBalance.OUT_OF_BOUNDS_PENALTY_RATE * (KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE - kicker_effectiveness):
            return {"zone": "out_of_bounds", "yards": 0}
        
        # Base kick placement with kicker effectiveness modifier
        base_success = KickoffGameBalance.BASE_KICK_SUCCESS_RATE
        effectiveness_modifier = KickoffGameBalance.EFFECTIVENESS_BASE_MODIFIER + (kicker_effectiveness - KickoffGameBalance.EFFECTIVENESS_THRESHOLD) * KickoffGameBalance.EFFECTIVENESS_SKILL_FACTOR
        placement_success = base_success * effectiveness_modifier
        
        # Add variance for realism
        variance = random.uniform(KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE - matrix["variance"] * KickoffGameBalance.KICK_VARIANCE_FACTOR, KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE + matrix["variance"] * KickoffGameBalance.KICK_VARIANCE_FACTOR)
        final_placement = placement_success * variance
        
        # Determine landing zone based on strategy and effectiveness
        if random.random() < final_placement:
            target_zone = matrix["target_zone"]
        else:
            # Missed target - determine alternative landing zone
            target_zone = self._determine_missed_target_zone(kick_strategy)
        
        return {
            "zone": target_zone,
            "strategy": kick_strategy,
            "effectiveness": kicker_effectiveness
        }
    
    def _determine_missed_target_zone(self, kick_strategy: str) -> str:
        """Helper method to determine where kick lands when missing target"""
        
        if kick_strategy == "deep_kick":
            # Deep kick that's short usually lands in landing zone
            return "landing_zone" if random.random() < KickoffGameBalance.DEEP_KICK_LANDING_ZONE_CHANCE else "short_zone"
        elif kick_strategy == "landing_zone_kick":
            # Landing zone kick can go short or long
            return "short_zone" if random.random() < KickoffGameBalance.LANDING_ZONE_SHORT_CHANCE else "end_zone"
        else:
            # Other strategies usually just fall short
            return "short_zone"
    
    def _check_touchback_rules(self, kick_outcome: Dict, matrix: Dict) -> Tuple[str, int, int]:
        """SOLID: Single responsibility - apply 2025 NFL touchback rules"""
        
        zone = kick_outcome["zone"]
        
        # Out of bounds = 40-yard line touchback
        if zone == "out_of_bounds":
            return "touchback", 0, KickoffGameBalance.SHORT_KICK_TOUCHBACK_LINE
        
        # Short kicks = 40-yard line touchback  
        if zone == "short_zone":
            return "touchback", 0, KickoffGameBalance.SHORT_KICK_TOUCHBACK_LINE
        
        # End zone kicks - check if downed or returned
        if zone == "end_zone":
            touchback_chance = matrix["base_touchback_chance"]
            if random.random() < touchback_chance:
                return "touchback", 0, KickoffGameBalance.END_ZONE_TOUCHBACK_LINE
            # If not downed, it's returned from end zone
        
        # Landing zone kicks that go to end zone
        if zone == "landing_zone":
            # Some landing zone kicks bounce/roll into end zone
            goes_to_end_zone_chance = matrix["base_touchback_chance"] * KickoffGameBalance.LANDING_ZONE_END_ZONE_FACTOR
            if random.random() < goes_to_end_zone_chance:
                # Can be downed for 20-yard touchback or returned
                if random.random() < KickoffGameBalance.DOWNED_VS_RETURN_CHANCE:
                    return "touchback", 0, KickoffGameBalance.LANDING_ZONE_TOUCHBACK_LINE
        
        # No touchback - must be returned
        return None
    
    def _simulate_return_attempt(self, offense_ratings: Dict, defense_ratings: Dict,
                               personnel, kick_outcome: Dict, matrix: Dict) -> Tuple[str, int, int]:
        """SOLID: Single responsibility - simulate the kickoff return"""
        
        # Step 1: Calculate return effectiveness (coverage vs returner matchup)
        return_effectiveness = self._calculate_return_effectiveness(
            offense_ratings, defense_ratings, personnel, kick_outcome, matrix
        )
        
        # Step 2: Calculate base return yards with effectiveness modifier
        base_yards = matrix["base_return_yards"]
        effectiveness_modifier = KickoffGameBalance.RETURN_EFFECTIVENESS_BASE + (return_effectiveness * KickoffGameBalance.RETURN_EFFECTIVENESS_RANGE)
        return_yards = base_yards * effectiveness_modifier
        
        # Step 3: Add variance for realism
        variance = random.uniform(KickoffGameBalance.RETURN_VARIANCE_MIN, KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE + matrix["variance"] * KickoffGameBalance.RETURN_VARIANCE_FACTOR)
        return_yards *= variance
        
        # Step 4: Check for breakaway potential
        if self._check_breakaway_potential(personnel, return_yards, matrix):
            breakaway_bonus = random.uniform(
                KickoffGameBalance.BREAKAWAY_YARDS_MIN, 
                KickoffGameBalance.BREAKAWAY_YARDS_MAX
            )
            return_yards += breakaway_bonus
        
        # Step 5: Check for fumble
        if random.random() < KickoffGameBalance.FUMBLE_ON_RETURN_RATE:
            return "fumble", 0, max(KickoffGameBalance.MIN_FUMBLE_RECOVERY_POSITION, int(return_yards * KickoffGameBalance.FUMBLE_RECOVERY_POSITION_FACTOR))
        
        # Step 6: Determine final outcome
        final_yards = max(KickoffGameBalance.MIN_RETURN_YARDS, int(return_yards))
        final_field_position = min(KickoffGameBalance.MAX_FIELD_POSITION, final_yards)
        
        # Check for touchdown (rare but possible)
        if final_yards >= KickoffGameBalance.RETURN_TD_MIN_YARDS and random.random() < KickoffGameBalance.RETURN_TD_CHANCE:
            return "touchdown", final_yards, KickoffGameBalance.TOUCHDOWN_FIELD_POSITION
        
        return "gain", final_yards, final_field_position
    
    def _calculate_return_effectiveness(self, offense_ratings: Dict, defense_ratings: Dict,
                                      personnel, kick_outcome: Dict, matrix: Dict) -> float:
        """Calculate how effective the return will be based on coverage vs returner matchup"""
        
        # Coverage team effectiveness (special teams unit)
        coverage_rating = offense_ratings.get('special_teams', KickoffGameBalance.DEFAULT_COVERAGE_RATING)
        coverage_effectiveness = (coverage_rating / KickoffGameBalance.NORMALIZE_FACTOR) * matrix["coverage_effectiveness"]
        
        # Apply hang time factor - more hang time = better coverage
        hang_time_factor = matrix["hang_time"] / KickoffGameBalance.COVERAGE_ARRIVAL_TIME
        coverage_effectiveness *= (KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE + hang_time_factor * KickoffGameBalance.HANG_TIME_IMPACT_FACTOR)
        
        # Returner effectiveness
        returner_rating = self._get_returner_effectiveness(personnel, matrix)
        
        # Calculate net return advantage (similar to blocking effectiveness in run_play.py)
        net_effectiveness = returner_rating / (coverage_effectiveness + KickoffGameBalance.NET_EFFECTIVENESS_PENALTY_BUFFER)
        
        return min(KickoffGameBalance.NET_EFFECTIVENESS_MAX, max(KickoffGameBalance.NET_EFFECTIVENESS_MIN, net_effectiveness))
    
    def _get_returner_effectiveness(self, personnel, matrix: Dict) -> float:
        """Calculate returner effectiveness for this kick strategy"""
        
        # Try to get dedicated returner first
        returner = getattr(personnel, 'returner_on_field', None)
        
        if returner:
            # Use returner attributes if available
            total_rating = 0
            for attribute in matrix["returner_attributes"]:
                rating = getattr(returner, attribute, KickoffGameBalance.DEFAULT_PLAYER_RATING)
                if not isinstance(rating, (int, float)):
                    rating = KickoffGameBalance.DEFAULT_PLAYER_RATING
                total_rating += rating
            
            avg_rating = total_rating / len(matrix["returner_attributes"])
            return avg_rating / KickoffGameBalance.NORMALIZE_FACTOR
        
        # Fallback to team special teams rating
        team_st_rating = getattr(personnel, 'special_teams_rating', KickoffGameBalance.DEFAULT_ST_RATING)
        if not isinstance(team_st_rating, (int, float)):
            team_st_rating = KickoffGameBalance.DEFAULT_ST_RATING
        
        return team_st_rating / KickoffGameBalance.NORMALIZE_FACTOR
    
    def _calculate_kicker_effectiveness(self, personnel, kick_strategy: str, matrix: Dict) -> float:
        """Calculate kicker effectiveness for this kick strategy"""
        
        # Try to get dedicated kicker first
        kicker = getattr(personnel, 'kicker_on_field', None)
        
        if kicker:
            # Use kicker attributes if available
            total_rating = 0
            for attribute in matrix["kicker_attributes"]:
                rating = getattr(kicker, attribute, KickoffGameBalance.DEFAULT_KICKER_BASELINE)
                if not isinstance(rating, (int, float)):
                    rating = KickoffGameBalance.DEFAULT_KICKER_BASELINE
                total_rating += rating
            
            avg_rating = total_rating / len(matrix["kicker_attributes"])
            return avg_rating / KickoffGameBalance.NORMALIZE_FACTOR
        
        # Fallback to team special teams rating
        team_st_rating = getattr(personnel, 'special_teams_rating', KickoffGameBalance.DEFAULT_ST_RATING)
        if not isinstance(team_st_rating, (int, float)):
            team_st_rating = KickoffGameBalance.DEFAULT_ST_RATING
        
        # Kickers are specialists - boost baseline slightly
        return min(KickoffGameBalance.COVERAGE_EFFECTIVENESS_HANG_TIME_BASE, (team_st_rating + KickoffGameBalance.KICKER_SPECIALIST_BONUS) / KickoffGameBalance.NORMALIZE_FACTOR)
    
    def _check_breakaway_potential(self, personnel, current_yards: float, matrix: Dict) -> bool:
        """Check if returner has breakaway potential on this return"""
        
        if current_yards < KickoffGameBalance.BREAKAWAY_MIN_YARDS:
            return False
        
        # Get returner speed rating
        returner = getattr(personnel, 'returner_on_field', None)
        if returner:
            speed = getattr(returner, 'speed', KickoffGameBalance.DEFAULT_RETURNER_SPEED)
            if not isinstance(speed, (int, float)):
                speed = KickoffGameBalance.DEFAULT_RETURNER_SPEED
        else:
            speed = KickoffGameBalance.DEFAULT_RETURNER_SPEED
        
        # Check against strategy-specific threshold
        if speed >= matrix["breakaway_threshold"]:
            # Base chance plus speed bonus
            speed_bonus = (speed - matrix["breakaway_threshold"]) * KickoffGameBalance.BREAKAWAY_SPEED_BONUS
            breakaway_chance = KickoffGameBalance.BREAKAWAY_BASE_CHANCE + speed_bonus
            return random.random() < breakaway_chance
        
        return False
    
    def _simulate_onside_kick(self, offense_ratings: Dict, defense_ratings: Dict, matrix: Dict) -> Tuple[str, int, int]:
        """Special handling for onside kick attempts"""
        
        # Calculate kicker technique vs hands team preparation
        kicker_rating = offense_ratings.get('special_teams', KickoffGameBalance.DEFAULT_ST_RATING)
        hands_team_rating = defense_ratings.get('special_teams', KickoffGameBalance.DEFAULT_ST_RATING)
        
        # Onside kicks favor the receiving team heavily
        kicker_effectiveness = kicker_rating / KickoffGameBalance.NORMALIZE_FACTOR
        hands_effectiveness = (hands_team_rating / KickoffGameBalance.NORMALIZE_FACTOR) * KickoffGameBalance.ONSIDE_HANDS_TEAM_ADVANTAGE
        
        recovery_chance = matrix["base_recovery_chance"] * (kicker_effectiveness / hands_effectiveness)
        
        if random.random() < recovery_chance:
            # Kicking team recovers - great field position for them
            return "onside_recovery", KickoffGameBalance.ONSIDE_RECOVERY_YARDS, KickoffGameBalance.ONSIDE_RECOVERY_FIELD_POSITION
        else:
            # Return team gets the ball - excellent field position
            return "gain", int(matrix["base_return_yards"]), int(matrix["base_return_yards"])