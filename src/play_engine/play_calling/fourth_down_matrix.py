"""
Fourth Down Decision Matrix - Situational-Based NFL Decision Making

Replaces the overly aggressive coach-personality-driven system with a realistic
matrix-based approach where field position, distance, and game context drive
decisions, with coach personality as a final modifier.

Based on real NFL 4th down analytics and decision patterns.
"""

from typing import Dict, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class CoachAggressionLevel(Enum):
    """Coach aggression levels for matrix-based decisions"""
    ULTRA_CONSERVATIVE = "ultra_conservative" 
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    ULTRA_AGGRESSIVE = "ultra_aggressive"


class FourthDownDecisionType(Enum):
    """Types of 4th down decisions"""
    GO_FOR_IT = "go_for_it"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"


@dataclass
class FourthDownDecision:
    """Result of 4th down decision analysis"""
    go_for_it_probability: float
    recommendation: FourthDownDecisionType  # Decision type using enum
    confidence: float    # 0.0-1.0, how confident in the decision
    breakdown: Dict[str, float]  # Step-by-step probability breakdown
    factors: Dict[str, Any]      # Contributing factors for analysis


class FourthDownMatrix:
    """Matrix-based 4th down decision system with realistic NFL probabilities"""
    
    # Field Position Base Probabilities (realistic NFL data-driven)
    FIELD_POSITION_MATRIX = {
        # (yard_start, yard_end): base_go_for_it_probability
        (1, 20): 0.01,      # Deep own territory: 1% - Almost never
        (21, 35): 0.03,     # Own territory: 3% - Very rare
        (36, 45): 0.08,     # Own side approaching midfield: 8% - Occasional
        (46, 55): 0.22,     # Midfield zone: 22% - Situational
        (56, 70): 0.45,     # Opponent territory: 45% - Common
        (71, 85): 0.68,     # Approaching red zone: 68% - Likely
        (86, 95): 0.55,     # Red zone: 55% - Reduced due to FG option
        (96, 100): 0.75     # Goal line: 75% - High likelihood
    }
    
    # Distance Multipliers (Critical Factor - Distance to Go)
    DISTANCE_MULTIPLIERS = {
        1: 2.0,     # 4th & 1: Double the probability
        2: 1.4,     # 4th & 2: +40% more likely
        3: 1.0,     # 4th & 3: Baseline reference
        4: 0.6,     # 4th & 4: -40% less likely
        5: 0.35,    # 4th & 5: -65% less likely
        6: 0.25,    # 4th & 6: -75% less likely
        7: 0.15,    # 4th & 7: -85% less likely
        8: 0.10,    # 4th & 8: -90% less likely
        9: 0.05,    # 4th & 9: -95% less likely
        10: 0.02,   # 4th & 10: -98% less likely
        # 10+ yards treated as 10
    }
    
    # Score Differential Modifiers (Game Context)
    SCORE_DIFFERENTIAL_MODIFIERS = {
        'ahead_by_21_plus': 0.2,    # Huge lead: Very conservative
        'ahead_by_14_20': 0.3,      # Big lead: Conservative  
        'ahead_by_8_13': 0.5,       # Moderate lead: Somewhat conservative
        'ahead_by_1_7': 0.8,        # Small lead: Slightly conservative
        'tied': 1.0,                # Tied: Baseline
        'behind_by_1_7': 1.3,       # Small deficit: More aggressive
        'behind_by_8_13': 1.6,      # Moderate deficit: Aggressive
        'behind_by_14_20': 2.0,     # Big deficit: Very aggressive
        'behind_by_21_plus': 2.5,   # Desperate: Maximum aggression
    }
    
    # Time Remaining Modifiers (Urgency Factor)
    TIME_REMAINING_MODIFIERS = {
        'first_half': 0.7,          # First half: Less urgent, be conservative
        'third_quarter': 0.9,       # Third quarter: Slightly less urgent
        'fourth_quarter_15_plus': 1.0,  # Early 4th: Baseline
        'fourth_quarter_10_14': 1.1,    # Mid 4th: Slightly more urgent
        'fourth_quarter_5_9': 1.3,      # Late 4th: More urgent
        'fourth_quarter_2_4': 1.7,      # Two-minute warning zone: Very urgent
        'final_two_minutes': 2.2,       # Final 2 min: Maximum urgency
        'final_minute': 2.8,             # Final minute: Desperation mode
    }
    
    # Coach Personality Modifiers (Final Adjustment, Not Primary Driver)
    COACH_PERSONALITY_MODIFIERS = {
        CoachAggressionLevel.ULTRA_CONSERVATIVE: 0.6,  # -40% (Old school, punt always)
        CoachAggressionLevel.CONSERVATIVE: 0.8,        # -20% (Play it safe)
        CoachAggressionLevel.BALANCED: 1.0,            # Baseline (Situational)
        CoachAggressionLevel.AGGRESSIVE: 1.2,          # +20% (Take calculated risks)
        CoachAggressionLevel.ULTRA_AGGRESSIVE: 1.4,    # +40% (High risk tolerance)
    }
    
    # Special Situation Modifiers (Additional Context)
    SPECIAL_SITUATION_MODIFIERS = {
        'weather_bad': 0.8,         # Rain/snow/wind affects execution
        'weather_extreme': 0.6,     # Severe weather conditions
        'home_field': 1.1,          # Slight boost from crowd support
        'primetime_game': 1.05,     # Slight boost for big stage
        'playoff_game': 1.3,        # Playoffs: More aggressive
        'elimination_game': 1.5,    # Season on the line
        'division_clinched': 0.7,   # Already secured division
        'meaningless_game': 0.8,    # Week 17/18 with nothing at stake
    }
    
    @classmethod
    def get_field_position_base_probability(cls, field_position: int) -> float:
        """
        Get base probability for going for it based on field position
        
        Args:
            field_position: Current field position (1-100 scale)
            
        Returns:
            Base probability (0.0-1.0) for attempting 4th down conversion
        """
        for (start, end), probability in cls.FIELD_POSITION_MATRIX.items():
            if start <= field_position <= end:
                return probability
        
        # Fallback for edge cases
        if field_position <= 20:
            return 0.01
        elif field_position >= 96:
            return 0.75
        else:
            return 0.22  # Midfield default
    
    @classmethod
    def get_distance_multiplier(cls, yards_to_go: int) -> float:
        """
        Get distance multiplier based on yards needed for first down
        
        Args:
            yards_to_go: Yards needed for first down
            
        Returns:
            Multiplier to apply to base probability
        """
        # Cap at 10 yards - anything longer treated the same
        capped_distance = min(yards_to_go, 10)
        return cls.DISTANCE_MULTIPLIERS.get(capped_distance, 0.02)
    
    @classmethod
    def get_score_differential_modifier(cls, score_differential: int) -> float:
        """
        Get modifier based on current score differential
        
        Args:
            score_differential: Points ahead (positive) or behind (negative)
            
        Returns:
            Modifier to apply based on game situation
        """
        if score_differential >= 21:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['ahead_by_21_plus']
        elif score_differential >= 14:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['ahead_by_14_20']
        elif score_differential >= 8:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['ahead_by_8_13']
        elif score_differential >= 1:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['ahead_by_1_7']
        elif score_differential == 0:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['tied']
        elif score_differential >= -7:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['behind_by_1_7']
        elif score_differential >= -13:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['behind_by_8_13']
        elif score_differential >= -20:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['behind_by_14_20']
        else:
            return cls.SCORE_DIFFERENTIAL_MODIFIERS['behind_by_21_plus']
    
    @classmethod
    def get_time_remaining_modifier(cls, time_remaining: int, quarter: int = 4) -> float:
        """
        Get modifier based on time remaining and quarter
        
        Args:
            time_remaining: Seconds remaining in game
            quarter: Current quarter (1-4)
            
        Returns:
            Modifier based on game urgency
        """
        if quarter <= 2:
            return cls.TIME_REMAINING_MODIFIERS['first_half']
        elif quarter == 3:
            return cls.TIME_REMAINING_MODIFIERS['third_quarter']
        else:  # Fourth quarter
            if time_remaining >= 900:      # 15+ minutes (OT)
                return cls.TIME_REMAINING_MODIFIERS['fourth_quarter_15_plus']
            elif time_remaining >= 600:   # 10-14 minutes
                return cls.TIME_REMAINING_MODIFIERS['fourth_quarter_10_14']
            elif time_remaining >= 300:   # 5-9 minutes
                return cls.TIME_REMAINING_MODIFIERS['fourth_quarter_5_9']
            elif time_remaining >= 120:   # 2-4 minutes
                return cls.TIME_REMAINING_MODIFIERS['fourth_quarter_2_4']
            elif time_remaining >= 60:    # 1-2 minutes
                return cls.TIME_REMAINING_MODIFIERS['final_two_minutes']
            else:                         # Under 1 minute
                return cls.TIME_REMAINING_MODIFIERS['final_minute']
    
    @classmethod
    def get_coach_personality_modifier(cls, coach_aggression: CoachAggressionLevel) -> float:
        """
        Get coach personality modifier
        
        Args:
            coach_aggression: Coach's aggression level
            
        Returns:
            Final modifier based on coaching philosophy
        """
        return cls.COACH_PERSONALITY_MODIFIERS.get(coach_aggression, 1.0)
    
    @classmethod
    def calculate_fourth_down_decision(
        cls,
        field_position: int,
        yards_to_go: int,
        score_differential: int = 0,
        time_remaining: int = 900,
        quarter: int = 4,
        coach_aggression: CoachAggressionLevel = CoachAggressionLevel.BALANCED,
        special_situations: list = None
    ) -> FourthDownDecision:
        """
        Calculate comprehensive 4th down decision using matrix approach
        
        Args:
            field_position: Current field position (1-100)
            yards_to_go: Yards needed for first down
            score_differential: Points ahead (+) or behind (-)
            time_remaining: Seconds remaining in game
            quarter: Current quarter (1-4)
            coach_aggression: Coach's aggression level
            special_situations: List of special situation keys
            
        Returns:
            FourthDownDecision with probability, recommendation, and analysis
        """
        if special_situations is None:
            special_situations = []
        
        # Step 1: Base probability from field position (Primary Driver)
        base_prob = cls.get_field_position_base_probability(field_position)
        
        # Step 2: Apply distance multiplier (Most Critical Factor)
        distance_multiplier = cls.get_distance_multiplier(yards_to_go)
        after_distance = base_prob * distance_multiplier
        
        # Step 3: Apply game context modifiers
        score_modifier = cls.get_score_differential_modifier(score_differential)
        time_modifier = cls.get_time_remaining_modifier(time_remaining, quarter)
        after_context = after_distance * score_modifier * time_modifier
        
        # Step 4: Apply special situation modifiers
        special_modifier = 1.0
        for situation in special_situations:
            if situation in cls.SPECIAL_SITUATION_MODIFIERS:
                special_modifier *= cls.SPECIAL_SITUATION_MODIFIERS[situation]
        after_special = after_context * special_modifier
        
        # Step 5: Apply coach personality (Final Fine-Tuning)
        coach_modifier = cls.get_coach_personality_modifier(coach_aggression)
        final_probability = after_special * coach_modifier
        
        # Step 6: Bound checking (ensure realistic range)
        final_probability = max(0.001, min(0.999, final_probability))
        
        # Step 7: Make recommendation based on field position and probability
        # ✅ FIX: Prioritize field goal range check before go-for-it probability
        if field_position >= 65:  # In field goal range (opponent 35-yard line or closer)
            # In field goal range: choose between FIELD_GOAL and GO_FOR_IT
            # Higher threshold for going for it when FG is available
            if final_probability > 0.75 and yards_to_go <= 2:  # Only go for it if very high confidence + short yardage
                recommendation = FourthDownDecisionType.GO_FOR_IT
            else:
                recommendation = FourthDownDecisionType.FIELD_GOAL
        elif final_probability > 0.5:
            # Not in FG range but high go-for-it probability
            recommendation = FourthDownDecisionType.GO_FOR_IT
        else:
            # Not in FG range and low go-for-it probability
            recommendation = FourthDownDecisionType.PUNT
        
        # Step 8: Calculate confidence (distance from 50/50 decision)
        confidence = abs(final_probability - 0.5) * 2
        
        return FourthDownDecision(
            go_for_it_probability=final_probability,
            recommendation=recommendation,
            confidence=confidence,
            breakdown={
                'base_field_position': base_prob,
                'after_distance_multiplier': after_distance,
                'after_score_modifier': after_context,
                'after_time_modifier': after_context,
                'after_special_situations': after_special,
                'final_probability': final_probability
            },
            factors={
                'field_position': field_position,
                'yards_to_go': yards_to_go,
                'score_differential': score_differential,
                'time_remaining': time_remaining,
                'quarter': quarter,
                'coach_aggression': coach_aggression.value,
                'distance_multiplier': distance_multiplier,
                'score_modifier': score_modifier,
                'time_modifier': time_modifier,
                'special_modifier': special_modifier,
                'coach_modifier': coach_modifier,
                'special_situations': special_situations
            }
        )


# Convenience function for external use
def calculate_fourth_down_decision(*args, **kwargs) -> FourthDownDecision:
    """Convenience wrapper for FourthDownMatrix.calculate_fourth_down_decision"""
    return FourthDownMatrix.calculate_fourth_down_decision(*args, **kwargs)