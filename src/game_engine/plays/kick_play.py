import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class KickGameBalance:
    """
    Centralized configuration for kicking game balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect kicking game balance.
    Based on 2024 NFL statistics for realistic performance:
    - Extra Point: 95.8% success rate
    - 30-39 yards: 92.9% success rate  
    - 40-49 yards: 85.1% success rate
    - 50+ yards: 73.5% success rate
    - Overall FG: 84.0% success rate
    """
    
    # === CORE EFFECTIVENESS CALCULATION ===
    # How much each factor contributes to kick success (must sum to 1.0)
    KICKER_LEG_STRENGTH_WEIGHT = 0.4   # How much leg strength matters for distance
    KICKER_ACCURACY_WEIGHT = 0.4       # How much accuracy matters for precision
    PROTECTION_WEIGHT = 0.2             # How much O-line protection matters
    
    # === BASE SUCCESS RATES BY DISTANCE (2024 NFL) ===
    EXTRA_POINT_BASE_RATE = 0.958       # 95.8% (20-yard distance)
    SHORT_FG_BASE_RATE = 0.929          # 92.9% (30-39 yards)
    MEDIUM_FG_BASE_RATE = 0.851         # 85.1% (40-49 yards)
    LONG_FG_BASE_RATE = 0.735           # 73.5% (50+ yards)
    
    # === BLOCK PROBABILITY SETTINGS ===
    BASE_BLOCK_RATE = 0.015             # 1.5% baseline block rate (NFL average)
    MAX_BLOCK_RATE = 0.08               # 8% maximum block rate
    PROTECTION_BLOCK_WEIGHT = 0.7       # O-line protection against blocks
    RUSH_BLOCK_WEIGHT = 0.3             # D-line rush contribution to blocks
    
    # === SITUATIONAL MODIFIERS ===
    # Pressure situations
    ICE_THE_KICKER_PENALTY = 0.93       # 7% penalty when iced
    END_OF_HALF_PRESSURE = 0.96         # 4% penalty for end-of-half kicks
    CLUTCH_TIME_PRESSURE = 0.94         # 6% penalty for game-winning kicks
    
    # Environmental factors
    DOME_BONUS = 1.02                   # 2% bonus in domed stadiums
    WIND_PENALTY_PER_MPH = 0.005        # 0.5% penalty per MPH of wind
    ALTITUDE_BONUS_PER_1000FT = 0.002   # 0.2% bonus per 1000ft elevation
    
    # === DISTANCE CALCULATION ===
    END_ZONE_DISTANCE = 10              # Distance to back of end zone
    HOLDER_DISTANCE = 7                 # Distance from line to holder
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense"""
        # Effectiveness weights should sum to 1.0
        total_weight = (cls.KICKER_LEG_STRENGTH_WEIGHT + cls.KICKER_ACCURACY_WEIGHT + 
                       cls.PROTECTION_WEIGHT)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Effectiveness weights must sum to 1.0, got {total_weight}")
        
        # Probabilities should be between 0 and 1
        probabilities = [cls.EXTRA_POINT_BASE_RATE, cls.SHORT_FG_BASE_RATE, 
                        cls.MEDIUM_FG_BASE_RATE, cls.LONG_FG_BASE_RATE, cls.BASE_BLOCK_RATE]
        for prob in probabilities:
            if not 0 <= prob <= 1:
                raise ValueError(f"Probability {prob} must be between 0 and 1")


# Validate configuration on import
KickGameBalance.validate_configuration()


# Distance-Based Kick Situation Matrices (KISS: Simple dictionary structure)
KICK_SITUATION_MATRICES = {
    "extra_point": {
        "distance": 20,
        "base_success": KickGameBalance.EXTRA_POINT_BASE_RATE,
        "kicker_attributes": ["accuracy", "mental_toughness"],
        "time_to_kick": 1.3,
        "block_risk_multiplier": 0.8,    # Lower block risk on XP
        "variance": 0.1                   # Very consistent
    },
    "short_fg": {
        "distance_range": (20, 39),
        "base_success": KickGameBalance.SHORT_FG_BASE_RATE,
        "kicker_attributes": ["accuracy", "leg_strength"],
        "time_to_kick": 1.4,
        "block_risk_multiplier": 1.0,    # Normal block risk
        "variance": 0.15
    },
    "medium_fg": {
        "distance_range": (40, 49),
        "base_success": KickGameBalance.MEDIUM_FG_BASE_RATE,
        "kicker_attributes": ["leg_strength", "accuracy"],
        "time_to_kick": 1.5,
        "block_risk_multiplier": 1.2,    # Slightly higher block risk
        "variance": 0.2
    },
    "long_fg": {
        "distance_range": (50, 70),
        "base_success": KickGameBalance.LONG_FG_BASE_RATE,
        "kicker_attributes": ["leg_strength", "mental_toughness"],
        "time_to_kick": 1.6,
        "block_risk_multiplier": 1.4,    # Higher block risk on long attempts
        "variance": 0.3                   # More variable on long kicks
    }
}


class KickPlay(PlayType):
    """Handles field goal and extra point attempts using distance-based matrices"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a field goal attempt using selected personnel"""
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Calculate kick outcome using distance-based matrix system
        outcome, yards_gained = self._calculate_kick_outcome_from_matrix(
            offense_ratings, defense_ratings, personnel, field_state
        )
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("field_goal", outcome)
        is_turnover = False  # Field goals don't result in turnovers
        is_score = outcome in ["field_goal", "extra_point"]
        score_points = self._calculate_points(outcome)
        
        # Create play result
        play_result = PlayResult(
            play_type="field_goal",
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
    
    def _calculate_kick_distance(self, field_state: FieldState) -> int:
        """Calculate kick distance in yards (field position + end zone + holder)"""
        return (100 - field_state.field_position) + KickGameBalance.END_ZONE_DISTANCE + KickGameBalance.HOLDER_DISTANCE
    
    def _determine_kick_situation(self, distance: int, field_state: FieldState) -> str:
        """SOLID: Single responsibility - classify kick situation based on distance"""
        
        # Extra point detection (goal line or 1-2 yard line)
        if field_state.field_position >= 98 or distance <= 20:
            return "extra_point"
        
        # Distance-based classification
        if distance <= 39:
            return "short_fg"
        elif distance <= 49:
            return "medium_fg"
        else:
            return "long_fg"
    
    def _calculate_kicker_effectiveness_for_situation(self, personnel, kick_situation: str) -> float:
        """SOLID: Single responsibility - calculate kicker effectiveness for specific kick situation"""
        
        # For now, use special_teams rating as kicker proxy
        # TODO: Replace with actual kicker attributes when Kicker player class is implemented
        kicker_rating = getattr(personnel, 'kicker_rating', 70)
        
        # Ensure kicker_rating is a number
        if not isinstance(kicker_rating, (int, float)):
            kicker_rating = 70
        
        if hasattr(personnel, 'kicker_on_field') and personnel.kicker_on_field:
            kicker = personnel.kicker_on_field
            # Use kicker attributes if available
            matrix = KICK_SITUATION_MATRICES[kick_situation]
            total_rating = 0
            
            for attribute in matrix["kicker_attributes"]:
                rating = getattr(kicker, attribute, 50)
                # Ensure rating is a number
                if not isinstance(rating, (int, float)):
                    rating = 50
                total_rating += rating
            
            avg_rating = total_rating / len(matrix["kicker_attributes"])
            return avg_rating / 100  # Normalize to 0-1 range
        
        # Fallback to team special teams rating
        # Normalize to 0-1 range, but assume good baseline for NFL kickers (70-85 range typical)
        return min(1.0, max(0.70, kicker_rating / 100))
    
    def _calculate_block_probability(self, offense_ratings: Dict, defense_ratings: Dict, 
                                   kick_situation: str, distance: int) -> bool:
        """SOLID: Single responsibility - calculate block probability"""
        
        # Step 1: Get protection strength (O-line protects on kicks)
        ol_protection = offense_ratings.get('ol', 50)
        
        # Step 2: Get rush strength (D-line rushes kicks)
        dl_rush = defense_ratings.get('dl', 50)
        
        # Step 3: Calculate base block probability
        matrix = KICK_SITUATION_MATRICES[kick_situation]
        rush_advantage = dl_rush / (ol_protection + 20)  # Avoid division by zero
        
        block_probability = (
            KickGameBalance.BASE_BLOCK_RATE * 
            rush_advantage * 
            matrix["block_risk_multiplier"]
        )
        
        # Step 4: Distance factor - longer kicks have lower trajectory, easier to block
        if distance > 45:
            block_probability *= 1.2  # 20% increase for long kicks
        
        # Cap at reasonable maximum
        block_probability = min(KickGameBalance.MAX_BLOCK_RATE, block_probability)
        
        return random.random() < block_probability
    
    def _apply_kick_situational_modifiers(self, base_success_rate: float, field_state: FieldState, 
                                        personnel, distance: int) -> float:
        """SOLID: Single responsibility - apply game situation modifiers to kick success rate"""
        
        modified_rate = base_success_rate
        
        # Pressure situations
        # TODO: Add game context for these situations when GameState is enhanced
        # For now, use probabilistic approach based on down/time
        
        # End of half pressure (4th down in own territory suggests desperation)
        if field_state.down == 4 and field_state.field_position < 40:
            modified_rate *= KickGameBalance.END_OF_HALF_PRESSURE
        
        # Distance-based accuracy degradation (beyond base matrix)
        if distance > 55:
            distance_penalty = (distance - 55) * 0.01  # 1% per yard beyond 55
            modified_rate *= (1.0 - distance_penalty)
        
        # Environmental factors (placeholder for future weather system)
        # TODO: Add weather, dome detection, altitude when stadium/weather data available
        
        return max(0.0, min(1.0, modified_rate))
    
    def _calculate_kick_outcome_from_matrix(self, offense_ratings: Dict, defense_ratings: Dict,
                                          personnel, field_state: FieldState) -> tuple[str, int]:
        """SOLID: Single responsibility - main kick calculation using distance-based matrix"""
        
        # Step 1: Calculate distance and determine kick situation
        distance = self._calculate_kick_distance(field_state)
        kick_situation = self._determine_kick_situation(distance, field_state)
        matrix = KICK_SITUATION_MATRICES[kick_situation]
        
        # Step 2: Check for block (happens first - can end play immediately)
        if self._calculate_block_probability(offense_ratings, defense_ratings, kick_situation, distance):
            return "blocked_kick", 0
        
        # Step 3: Calculate kicker effectiveness for this situation
        kicker_effectiveness = self._calculate_kicker_effectiveness_for_situation(personnel, kick_situation)
        
        # Step 4: Calculate protection effectiveness (affects composure)
        ol_rating = offense_ratings.get('ol', 50)
        protection_effectiveness = ol_rating / 100.0
        
        # Step 5: Combine all factors (KISS: simple weighted calculation)
        combined_effectiveness = (
            kicker_effectiveness * (KickGameBalance.KICKER_LEG_STRENGTH_WEIGHT + KickGameBalance.KICKER_ACCURACY_WEIGHT) +
            protection_effectiveness * KickGameBalance.PROTECTION_WEIGHT
        )
        
        # Step 6: Apply effectiveness to base success rate
        # Use very gentle approach for kicking - NFL kickers are highly trained specialists
        effectiveness_modifier = 0.98 + (combined_effectiveness - 0.75) * 0.10  # Very gentle
        base_with_effectiveness = matrix["base_success"] * effectiveness_modifier
        
        # Step 7: Apply situational modifiers
        final_success_rate = self._apply_kick_situational_modifiers(
            base_with_effectiveness, field_state, personnel, distance
        )
        
        # Step 8: Add variance for realism (reduced for more consistent kicking)
        variance = random.uniform(1.0 - matrix["variance"] * 0.3, 1.0 + matrix["variance"] * 0.2)
        final_success_rate *= variance
        
        # Step 9: Determine outcome
        if random.random() < final_success_rate:
            outcome_type = "extra_point" if kick_situation == "extra_point" else "field_goal"
            return outcome_type, 0  # No yards gained, just points
        else:
            return "missed_fg", 0
    
    def _simulate_field_goal(self, offense_ratings: Dict, field_state: FieldState) -> tuple[str, int]:
        """Legacy method - kept for backward compatibility"""
        # Redirect to new matrix-based system
        from unittest.mock import Mock
        mock_personnel = Mock()
        mock_personnel.kicker_rating = offense_ratings.get("special_teams", 70)
        
        return self._calculate_kick_outcome_from_matrix(
            offense_ratings, {"dl": 50}, mock_personnel, field_state
        )