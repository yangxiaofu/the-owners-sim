import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class PuntGameBalance:
    """
    Centralized configuration for punt game balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect punting game balance.
    Based on 2024 NFL statistics for realistic performance:
    - Average net punt: 45.8 yards
    - Average gross punt: 47.4 yards  
    - Touchback rate: 28%
    - Block rate: 0.6%
    - Return TD rate: 0.3%
    """
    
    # === CORE EFFECTIVENESS CALCULATION ===
    # How much each factor contributes to punt success (must sum to 1.0)
    PUNTER_LEG_STRENGTH_WEIGHT = 0.3    # Distance capability (0.0-1.0)
    PUNTER_HANG_TIME_WEIGHT = 0.3       # Coverage time (0.0-1.0)
    PUNTER_ACCURACY_WEIGHT = 0.2        # Placement ability (0.0-1.0)
    COVERAGE_EFFECTIVENESS_WEIGHT = 0.2  # Special teams coverage (0.0-1.0)
    
    # === BASE PUNT STATISTICS (2024 NFL) ===
    AVERAGE_NET_PUNT = 45.8             # NFL average net punt distance
    AVERAGE_GROSS_PUNT = 47.4           # Before returns
    TOUCHBACK_RATE = 0.28               # 28% touchback rate
    BLOCK_RATE = 0.006                  # 0.6% baseline block rate
    RETURN_TD_RATE = 0.003              # 0.3% return touchdown rate
    SHANK_RATE = 0.02                   # 2% poor punt rate
    
    # === BLOCK PROBABILITY SETTINGS ===
    MAX_BLOCK_RATE = 0.05               # 5% maximum block rate
    PROTECTION_BLOCK_WEIGHT = 0.7       # O-line protection against blocks
    RUSH_BLOCK_WEIGHT = 0.3             # D-line rush contribution to blocks
    
    # === SITUATIONAL MODIFIERS ===
    # Field position effects
    DEEP_TERRITORY_DISTANCE_BONUS = 1.1    # 10% distance bonus from own 20 or less
    SHORT_FIELD_PLACEMENT_BONUS = 1.3      # 30% placement bonus near opponent goal
    EMERGENCY_PUNT_BLOCK_RISK = 2.0        # 2x block risk when rushed
    DEEP_TERRITORY_THRESHOLD = 20          # Field position considered "deep territory"
    SHORT_FIELD_THRESHOLD = 40             # Opponent field position for placement focus
    
    # Pressure situations
    FOURTH_AND_LONG_PRESSURE = 0.95        # 5% penalty for desperation punts
    END_OF_HALF_COMPOSURE = 0.97           # 3% penalty for end-of-half punts
    
    # === RETURN AND COVERAGE ===
    BASE_RETURN_YARDS = 8.5                # NFL average punt return
    MAX_RETURN_YARDS = 85                  # Maximum return yardage
    COVERAGE_IMPACT_MULTIPLIER = 0.8       # How much coverage affects returns
    FAIR_CATCH_BASE_RATE = 0.42            # 42% fair catch rate to meet NFL benchmarks
    
    # === VARIANCE AND CONSISTENCY ===
    BASE_VARIANCE_MIN = 0.8                # Minimum variance multiplier
    BASE_VARIANCE_MAX = 1.2                # Maximum variance multiplier
    
    # === EFFECTIVENESS MODIFIERS ===
    EFFECTIVENESS_BASE_MODIFIER = 0.98     # Base effectiveness modifier (less harsh penalty)
    EFFECTIVENESS_TARGET = 0.72            # Target effectiveness for average teams
    EFFECTIVENESS_SCALE_FACTOR = 0.15      # Reduced impact of effectiveness deviation
    
    # === RETURN YARDS CALCULATION ===
    NET_RETURN_BASE = 2.0                  # Base return yards for net calculation (NFL: 47.4→45.8 = 1.6 diff)
    NET_RETURN_MAX = 15                    # Maximum return yards
    COVERAGE_REDUCTION_FACTOR = 0.5        # How much coverage reduces returns
    SITUATION_BONUS_FACTOR = 0.3           # How much situation affects returns
    RETURN_VARIANCE_MIN = 0.8              # Minimum return variance
    RETURN_VARIANCE_MAX = 1.2              # Maximum return variance
    
    # === OUTCOME PROBABILITIES ===
    OUT_OF_BOUNDS_BASE_CHANCE = 0.3        # Base chance for out of bounds on short punts
    NON_TOUCHBACK_END_ZONE_POSITION = 95   # Field position when punt reaches end zone but not touchback
    
    # === MINIMUM VALUES ===
    MIN_PUNT_DISTANCE = 20                 # Minimum punt distance
    MIN_SHANK_DISTANCE = 15                # Minimum distance on shanked punts
    SHANK_DISTANCE_MULTIPLIER = 0.6        # Multiplier for shanked punt distance
    
    # === THRESHOLDS AND BUFFERS ===
    EMERGENCY_YARDS_THRESHOLD = 15         # 4th down yards needed for emergency punt
    BLOCKED_PUNT_MAX_YARDS = 10            # Maximum yards on blocked punt
    PROTECTION_BUFFER = 20                 # Buffer to avoid division by zero in block calculation
    RETURN_TD_COVERAGE_FACTOR = 0.8        # How much coverage affects return TD risk
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense"""
        # Effectiveness weights should sum to 1.0
        total_weight = (cls.PUNTER_LEG_STRENGTH_WEIGHT + cls.PUNTER_HANG_TIME_WEIGHT + 
                       cls.PUNTER_ACCURACY_WEIGHT + cls.COVERAGE_EFFECTIVENESS_WEIGHT)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Effectiveness weights must sum to 1.0, got {total_weight}")
        
        # Probabilities should be between 0 and 1
        probabilities = [cls.TOUCHBACK_RATE, cls.BLOCK_RATE, cls.RETURN_TD_RATE, 
                        cls.SHANK_RATE, cls.FAIR_CATCH_BASE_RATE]
        for prob in probabilities:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability {prob} must be between 0 and 1")


# Validate configuration on import
PuntGameBalance.validate_configuration()


# Punt Situation Matchup Matrix Configuration (KISS: Simple dictionary structure)
PUNT_SITUATION_MATRICES = {
    "deep_punt": {
        "punter_attributes": ["leg_strength", "hang_time"],
        "base_distance": 50.0,              # Enhanced distance from deep territory for touchback potential
        "placement_effectiveness": 0.6,     # Limited placement focus - just get distance
        "block_risk_multiplier": 1.2,       # Higher block risk from deep (longer snap)
        "return_vulnerability": 1.1,        # More vulnerable to returns (distance vs hang time)
        "fair_catch_modifier": 0.9,         # Less likely to fair catch on long punts
        "variance": 1.0                     # Full variance range (0.8-1.2)
    },
    "midfield_punt": {
        "punter_attributes": ["hang_time", "accuracy"],
        "base_distance": 46.0,              # Enhanced distance for better touchback potential
        "placement_effectiveness": 0.8,     # Moderate placement focus
        "block_risk_multiplier": 1.0,       # Normal block risk
        "return_vulnerability": 1.0,        # Standard return vulnerability
        "fair_catch_modifier": 1.0,         # Normal fair catch rate
        "variance": 1.0                     # Full variance range (0.8-1.2)
    },
    "short_punt": {
        "punter_attributes": ["accuracy", "placement"],
        "base_distance": 44.0,              # Enhanced distance for touchback potential while maintaining placement focus
        "placement_effectiveness": 1.4,     # High placement bonus - coffin corner focus
        "block_risk_multiplier": 0.8,       # Lower block risk (shorter field, quicker operation)
        "return_vulnerability": 0.7,        # Less vulnerable (better placement, coverage time)
        "fair_catch_modifier": 1.2,         # More fair catches due to placement
        "variance": 1.0                     # Full variance for touchback potential (0.8-1.2)
    },
    "emergency_punt": {
        "punter_attributes": ["leg_strength", "composure"],
        "base_distance": 40.0,              # Rushed punt - moderate distance
        "placement_effectiveness": 0.4,     # Poor placement under pressure
        "block_risk_multiplier": 2.0,       # Very high block risk (4th & long, rushed)
        "return_vulnerability": 1.5,        # High vulnerability to returns
        "fair_catch_modifier": 0.8,         # Less fair catches (poor placement)
        "variance": 1.0                     # Full variance range (0.8-1.2) - high pressure situation
    }
}


class PuntPlay(PlayType):
    """Handles punt simulation logic"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a punt using selected personnel"""
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense") 
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Use situational punt matrix algorithm
        outcome, yards_gained = self._calculate_punt_outcome_from_matrix(
            offense_ratings, defense_ratings, personnel, field_state
        )
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("punt", outcome)
        is_turnover = outcome == "punt_return_td"  # Return TD is technically a turnover for offense
        is_score = outcome == "punt_return_td"     # Only return TDs score directly
        score_points = self._calculate_points(outcome)
        
        # Create play result
        play_result = PlayResult(
            play_type="punt",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points
        )
        
        # Populate situational context from field state
        self._populate_situational_context(play_result, field_state)
        
        return play_result
    
    def _determine_punt_situation(self, field_state: FieldState) -> str:
        """SOLID: Single responsibility - classify punt situation based on field position and game context"""
        
        # Emergency punt situations (4th and very long)
        if field_state.down == 4 and field_state.yards_to_go > PuntGameBalance.EMERGENCY_YARDS_THRESHOLD:
            return "emergency_punt"
        
        # Short field situations (near opponent goal)
        if field_state.field_position >= PuntGameBalance.SHORT_FIELD_THRESHOLD:
            return "short_punt"
        
        # Deep territory situations (own 20 or less)
        if field_state.field_position <= PuntGameBalance.DEEP_TERRITORY_THRESHOLD:
            return "deep_punt"
        
        # Standard midfield punt
        return "midfield_punt"
    
    def _calculate_punter_effectiveness_for_situation(self, personnel, punt_situation: str) -> float:
        """SOLID: Single responsibility - calculate punter effectiveness for specific punt situation"""
        
        # For now, use special_teams rating as punter proxy
        # TODO: Replace with actual punter attributes when Punter player class is implemented
        punter_rating = getattr(personnel, 'punter_rating', 70)
        
        # Ensure punter_rating is a number
        if not isinstance(punter_rating, (int, float)):
            punter_rating = 70
        
        if hasattr(personnel, 'punter_on_field') and personnel.punter_on_field:
            punter = personnel.punter_on_field
            # Use punter attributes if available
            matrix = PUNT_SITUATION_MATRICES[punt_situation]
            total_rating = 0
            
            for attribute in matrix["punter_attributes"]:
                rating = getattr(punter, attribute, 50)
                # Ensure rating is a number
                if not isinstance(rating, (int, float)):
                    rating = 50
                total_rating += rating
            
            avg_rating = total_rating / len(matrix["punter_attributes"])
            return avg_rating / 100  # Normalize to 0-1 range
        
        # Fallback to team special teams rating
        return punter_rating / 100
    
    def _calculate_coverage_effectiveness(self, personnel, offense_ratings: Dict) -> float:
        """SOLID: Single responsibility - calculate special teams coverage effectiveness"""
        
        # Use special teams rating as coverage proxy
        coverage_rating = offense_ratings.get('special_teams', 50)
        
        # Ensure coverage_rating is a number
        if not isinstance(coverage_rating, (int, float)):
            coverage_rating = 50
        
        # TODO: When individual coverage players are implemented, calculate based on:
        # - Coverage team speed and tackling ability
        # - Formation and coverage scheme
        # - Individual player ratings for coverage specialists
        
        return coverage_rating / 100  # Normalize to 0-1 range
    
    def _calculate_block_probability(self, offense_ratings: Dict, defense_ratings: Dict, 
                                   punt_situation: str) -> bool:
        """SOLID: Single responsibility - calculate punt block probability"""
        
        # Step 1: Get protection strength (special teams O-line protection)
        ol_protection = offense_ratings.get('special_teams', 50)  # Use ST rating for now
        
        # Step 2: Get rush strength (D-line rush on punts)
        dl_rush = defense_ratings.get('dl', 50)
        
        # Step 3: Calculate base block probability
        matrix = PUNT_SITUATION_MATRICES[punt_situation]
        rush_advantage = dl_rush / (ol_protection + PuntGameBalance.PROTECTION_BUFFER)
        
        block_probability = (
            PuntGameBalance.BLOCK_RATE * 
            rush_advantage * 
            matrix["block_risk_multiplier"]
        )
        
        # Cap at reasonable maximum
        block_probability = min(PuntGameBalance.MAX_BLOCK_RATE, block_probability)
        
        return random.random() < block_probability
    
    def _apply_punt_situational_modifiers(self, base_distance: float, field_state: FieldState, 
                                        punt_situation: str) -> float:
        """SOLID: Single responsibility - apply game situation modifiers to punt distance/effectiveness"""
        
        modified_distance = base_distance
        
        # Field position modifiers
        if field_state.field_position <= PuntGameBalance.DEEP_TERRITORY_THRESHOLD:
            # Deep territory - focus on distance
            modified_distance *= PuntGameBalance.DEEP_TERRITORY_DISTANCE_BONUS
        elif field_state.field_position >= PuntGameBalance.SHORT_FIELD_THRESHOLD:
            # Short field - placement more important than pure distance
            # This will be handled in placement effectiveness, not raw distance
            pass
        
        # Pressure situation modifiers
        DESPERATION_PUNT_THRESHOLD = 10  # 4th down yards for desperation punt
        if field_state.down == 4 and field_state.yards_to_go > DESPERATION_PUNT_THRESHOLD:
            # 4th and long - desperation punt
            modified_distance *= PuntGameBalance.FOURTH_AND_LONG_PRESSURE
        
        # TODO: Add game context modifiers when GameState is enhanced:
        # - End of half pressure
        # - Score differential impact
        # - Time remaining considerations
        
        return max(0.0, modified_distance)
    
    def _determine_punt_outcome(self, gross_distance: int, punt_situation: str, 
                              coverage_effectiveness: float, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - determine final punt outcome with realistic probabilities"""
        
        matrix = PUNT_SITUATION_MATRICES[punt_situation]
        
        # Check for touchback (punt into end zone)
        end_zone_position = field_state.field_position + gross_distance
        if end_zone_position >= 100:
            # Punt reaches end zone - strong chance of touchback
            if random.random() < PuntGameBalance.TOUCHBACK_RATE:
                touchback_distance = 100 - field_state.field_position
                return "touchback", touchback_distance
            # If not touchback, ball is downed at ~5 yard line
            return "punt", PuntGameBalance.NON_TOUCHBACK_END_ZONE_POSITION
        
        # Check for shank/poor punt
        if random.random() < PuntGameBalance.SHANK_RATE / matrix["placement_effectiveness"]:
            # Poor punt - reduced distance and worse field position
            shank_distance = max(PuntGameBalance.MIN_SHANK_DISTANCE, 
                               int(gross_distance * PuntGameBalance.SHANK_DISTANCE_MULTIPLIER))
            return "shank", shank_distance
        
        # Check for return touchdown
        return_td_risk = (PuntGameBalance.RETURN_TD_RATE * 
                         matrix["return_vulnerability"] * 
                         (1.0 - coverage_effectiveness * PuntGameBalance.RETURN_TD_COVERAGE_FACTOR))
        
        if random.random() < return_td_risk:
            return "punt_return_td", gross_distance
        
        # Check for fair catch (much less aggressive)
        fair_catch_prob = (PuntGameBalance.FAIR_CATCH_BASE_RATE * 
                          matrix["fair_catch_modifier"] * 
                          min(1.0, matrix["placement_effectiveness"]))  # Cap at 1.0
        
        if random.random() < fair_catch_prob:
            return "fair_catch", gross_distance
        
        # Determine if punt went out of bounds (good placement)
        if (punt_situation == "short_punt" and 
            random.random() < PuntGameBalance.OUT_OF_BOUNDS_BASE_CHANCE * matrix["placement_effectiveness"]):
            return "out_of_bounds", gross_distance
        
        # Standard punt with return
        return_yards = self._calculate_return_yards(coverage_effectiveness, matrix)
        final_distance = max(0, gross_distance - return_yards)
        
        return "punt", final_distance
    
    def _calculate_return_yards(self, coverage_effectiveness: float, matrix: Dict) -> int:
        """YAGNI: Simple return yards calculation"""
        
        # Start with much lower base return for net punt calculation
        # NFL: Gross punt 47.4, net punt 45.8 = only ~1.6 yard difference on average
        base_return = PuntGameBalance.NET_RETURN_BASE
        
        # Coverage effectiveness reduces return yards (good coverage = less return yards)
        coverage_reduction = base_return * coverage_effectiveness * PuntGameBalance.COVERAGE_REDUCTION_FACTOR
        
        # Situation vulnerability increases return yards (poor punt situation = more return yards)  
        situation_bonus = base_return * (matrix["return_vulnerability"] - 1.0) * PuntGameBalance.SITUATION_BONUS_FACTOR
        
        total_return = base_return - coverage_reduction + situation_bonus
        
        # Add minimal variance
        variance = random.uniform(PuntGameBalance.RETURN_VARIANCE_MIN, PuntGameBalance.RETURN_VARIANCE_MAX)
        final_return = total_return * variance
        
        return max(0, min(PuntGameBalance.NET_RETURN_MAX, int(final_return)))
    
    def _calculate_punt_outcome_from_matrix(self, offense_ratings: Dict, defense_ratings: Dict,
                                          personnel, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - main punt calculation using situational matrix"""
        
        # Step 1: Determine punt situation and get matrix
        punt_situation = self._determine_punt_situation(field_state)
        matrix = PUNT_SITUATION_MATRICES[punt_situation]
        
        # Step 2: Check for block (happens first - can end play immediately)
        if self._calculate_block_probability(offense_ratings, defense_ratings, punt_situation):
            # Blocked punt - minimal distance, potentially dangerous
            block_distance = random.randint(0, PuntGameBalance.BLOCKED_PUNT_MAX_YARDS)
            return "blocked_punt", block_distance
        
        # Step 3: Calculate punter effectiveness for this situation
        punter_effectiveness = self._calculate_punter_effectiveness_for_situation(personnel, punt_situation)
        
        # Step 4: Calculate coverage effectiveness
        coverage_effectiveness = self._calculate_coverage_effectiveness(personnel, offense_ratings)
        
        # Step 5: Combine all factors (KISS: simple weighted calculation)
        combined_effectiveness = (
            punter_effectiveness * (PuntGameBalance.PUNTER_LEG_STRENGTH_WEIGHT + 
                                   PuntGameBalance.PUNTER_HANG_TIME_WEIGHT + 
                                   PuntGameBalance.PUNTER_ACCURACY_WEIGHT) +
            coverage_effectiveness * PuntGameBalance.COVERAGE_EFFECTIVENESS_WEIGHT
        )
        
        # Step 6: Apply effectiveness to base distance
        # Use gentler approach - average effectiveness (0.72) should yield close to base distance
        effectiveness_modifier = (PuntGameBalance.EFFECTIVENESS_BASE_MODIFIER + 
                                (combined_effectiveness - PuntGameBalance.EFFECTIVENESS_TARGET) * 
                                PuntGameBalance.EFFECTIVENESS_SCALE_FACTOR)
        base_with_effectiveness = matrix["base_distance"] * effectiveness_modifier
        
        # Step 7: Apply situational modifiers
        adjusted_distance = self._apply_punt_situational_modifiers(
            base_with_effectiveness, field_state, punt_situation
        )
        
        # Step 8: Add variance for realism
        min_variance = PuntGameBalance.BASE_VARIANCE_MIN
        max_variance = min_variance + (PuntGameBalance.BASE_VARIANCE_MAX - min_variance) * matrix["variance"]
        variance = random.uniform(min_variance, max_variance)
        final_gross_distance = adjusted_distance * variance
        
        # Step 9: Calculate net distance (gross distance is before returns)
        gross_yards = max(PuntGameBalance.MIN_PUNT_DISTANCE, int(final_gross_distance))
        
        # Step 10: Determine final outcome and calculate net yardage
        return self._determine_punt_outcome(gross_yards, punt_situation, coverage_effectiveness, field_state)
    
    def _simulate_punt(self, offense_ratings: Dict, defense_ratings: Dict, field_state: FieldState) -> tuple[str, int]:
        """Legacy method - kept for backward compatibility"""
        # Redirect to new matrix-based system
        from unittest.mock import Mock
        mock_personnel = Mock()
        mock_personnel.punter_rating = offense_ratings.get("special_teams", 70)
        
        return self._calculate_punt_outcome_from_matrix(
            offense_ratings, defense_ratings, mock_personnel, field_state
        )