"""
Strategic Field Goal Decision System

This module implements intelligent field goal decision-making that considers:
1. Distance-based success rate modeling
2. Game situation and context 
3. Coaching archetype philosophies
4. Strategic value calculations

Replaces simple distance thresholds with comprehensive strategic evaluation.
"""

import random
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from ..field.field_state import FieldState
from ..field.game_state import GameState


@dataclass
class FieldGoalDecision:
    """Result of strategic field goal decision analysis"""
    should_attempt: bool
    success_probability: float
    strategic_value: float
    decision_reasoning: str
    alternative_recommendation: str


class FieldGoalStrategicBalance:
    """
    Configuration for strategic field goal decision making
    
    Based on NFL analytics and coaching tendencies for realistic decision-making.
    Distance-based success rates derived from 2020-2024 NFL seasons.
    """
    
    # === DISTANCE-BASED SUCCESS RATE MODELING ===
    DISTANCE_SUCCESS_RATES = {
        "chip_shot": {
            "distance_max": 35,
            "base_success_rate": 0.92,  # 92% success for kicks ≤35 yards
            "description": "High-percentage kicks that should rarely be missed"
        },
        "makeable": {
            "distance_min": 36,
            "distance_max": 45,
            "base_success_rate": 0.85,  # 85% success for 36-45 yard kicks
            "description": "Solid kicks that most NFL kickers can make consistently"
        },
        "long": {
            "distance_min": 46,
            "distance_max": 55,
            "base_success_rate": 0.68,  # 68% success for 46-55 yard kicks
            "description": "Challenging kicks that require leg strength and accuracy"
        },
        "very_long": {
            "distance_min": 56,
            "distance_max": 70,
            "base_success_rate": 0.45,  # 45% success for 56+ yard kicks
            "description": "Low-percentage kicks attempted in specific situations"
        }
    }
    
    # === STRATEGIC VALUE CALCULATION WEIGHTS ===
    STRATEGIC_VALUE_WEIGHTS = {
        "success_probability": 0.40,      # Primary factor - likelihood of making it
        "point_value_impact": 0.35,       # How much the points matter in game context
        "time_situation": 0.15,           # Time remaining considerations
        "field_position_value": 0.10      # Value of field position vs points
    }
    
    # === GAME CONTEXT MULTIPLIERS ===
    GAME_CONTEXT_MULTIPLIERS = {
        # Score differential impact on field goal value
        "score_differential": {
            "fg_ties_game": 1.6,           # Field goal ties the game - very valuable
            "fg_takes_lead": 1.4,          # Field goal takes the lead - valuable
            "fg_extends_lead_close": 1.2,   # Extends lead in close game
            "fg_extends_lead_safe": 0.9,    # Less valuable when already leading comfortably
            "fg_narrows_deficit": 1.1,      # Somewhat valuable when trailing
            "fg_meaningless": 0.6           # Low value when trailing by multiple scores
        },
        
        # Time remaining multipliers
        "time_remaining": {
            "final_2_minutes": 1.3,        # Critical time - points very valuable
            "final_5_minutes": 1.2,        # Important time - increased value
            "second_half": 1.1,            # Later in game - somewhat more valuable
            "first_half": 0.9              # Early in game - slightly less valuable
        },
        
        # Quarter-specific adjustments
        "quarter_context": {
            "end_of_first_half": 1.4,     # Take points before halftime
            "fourth_quarter": 1.3,        # Points crucial in final quarter
            "overtime": 1.8                # Any score wins in overtime
        }
    }
    
    # === ARCHETYPE PHILOSOPHY THRESHOLDS ===
    ARCHETYPE_THRESHOLDS = {
        "conservative": {
            "minimum_success_rate": 0.70,  # Take any field goal ≥70% success
            "red_zone_fg_threshold": 0.60, # More willing to take FGs in red zone
            "philosophy": "prefer_points_over_risk"
        },
        "aggressive": {
            "minimum_success_rate": 0.85,  # Only take "sure thing" field goals
            "red_zone_fg_threshold": 0.90, # Strongly prefer TDs in red zone
            "philosophy": "prefer_touchdowns_over_field_goals"
        },
        "balanced": {
            "minimum_success_rate": 0.75,  # Balanced approach to field goal decisions
            "red_zone_fg_threshold": 0.70, # Moderate preference for TDs in red zone
            "philosophy": "strategic_value_optimization"
        }
    }
    
    # === FIELD GOAL DISTANCE CALCULATION ===
    END_ZONE_DISTANCE = 10              # Distance from goal line to back of end zone
    HOLDER_DISTANCE = 7                 # Distance from line of scrimmage to holder
    
    @classmethod
    def validate_configuration(cls):
        """Validate configuration values make sense"""
        # Check distance ranges don't overlap
        categories = list(cls.DISTANCE_SUCCESS_RATES.keys())
        for i, cat in enumerate(categories[:-1]):
            current = cls.DISTANCE_SUCCESS_RATES[cat]
            next_cat = cls.DISTANCE_SUCCESS_RATES[categories[i + 1]]
            
            if "distance_max" in current and "distance_min" in next_cat:
                if current["distance_max"] >= next_cat["distance_min"]:
                    raise ValueError(f"Distance ranges overlap between {cat} and {categories[i + 1]}")
        
        # Check strategic value weights sum to 1.0
        total_weight = sum(cls.STRATEGIC_VALUE_WEIGHTS.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Strategic value weights must sum to 1.0, got {total_weight}")
        
        # Check success rates are valid probabilities
        for category, data in cls.DISTANCE_SUCCESS_RATES.items():
            rate = data["base_success_rate"]
            if not 0 <= rate <= 1:
                raise ValueError(f"Success rate {rate} for {category} must be between 0 and 1")


# Validate configuration on import
FieldGoalStrategicBalance.validate_configuration()


class StrategicFieldGoalDecisionMaker:
    """
    Intelligent field goal decision maker that considers game situation and coaching philosophy
    
    This class replaces simple distance-based thresholds with comprehensive strategic analysis
    following the same patterns as other play decision systems in the codebase.
    """
    
    def __init__(self):
        """Initialize with configuration validation"""
        FieldGoalStrategicBalance.validate_configuration()
    
    def should_attempt_field_goal(self, field_state: FieldState, game_state: GameState,
                                 coaching_archetype: str, team_id: int) -> FieldGoalDecision:
        """
        Make strategic field goal decision based on comprehensive analysis
        
        Args:
            field_state: Current field position and down/distance
            game_state: Current game state including score and time
            coaching_archetype: Coaching philosophy ("conservative", "aggressive", "balanced")
            team_id: Team making the decision (for score differential calculation)
            
        Returns:
            FieldGoalDecision: Complete analysis with recommendation and reasoning
        """
        
        # Step 1: Calculate field goal distance
        fg_distance = self._calculate_field_goal_distance(field_state)
        
        # Step 2: Determine success probability based on distance
        success_probability = self._calculate_success_probability(fg_distance)
        
        # Step 3: Calculate strategic value of the field goal
        strategic_value = self._calculate_strategic_value(
            success_probability, field_state, game_state, team_id
        )
        
        # Step 4: Apply coaching archetype philosophy
        should_attempt, reasoning = self._apply_archetype_philosophy(
            success_probability, strategic_value, coaching_archetype, field_state, game_state
        )
        
        # Step 5: Determine alternative recommendation
        alternative = self._get_alternative_recommendation(
            should_attempt, field_state, coaching_archetype
        )
        
        return FieldGoalDecision(
            should_attempt=should_attempt,
            success_probability=success_probability,
            strategic_value=strategic_value,
            decision_reasoning=reasoning,
            alternative_recommendation=alternative
        )
    
    def _calculate_field_goal_distance(self, field_state: FieldState) -> int:
        """Calculate field goal distance in yards"""
        return (100 - field_state.field_position) + \
               FieldGoalStrategicBalance.END_ZONE_DISTANCE + \
               FieldGoalStrategicBalance.HOLDER_DISTANCE
    
    def _calculate_success_probability(self, distance: int) -> float:
        """
        Calculate success probability based on distance using realistic NFL data
        
        Args:
            distance: Field goal distance in yards
            
        Returns:
            float: Success probability (0.0 to 1.0)
        """
        
        # Determine distance category
        for category, data in FieldGoalStrategicBalance.DISTANCE_SUCCESS_RATES.items():
            distance_max = data.get("distance_max", float('inf'))
            distance_min = data.get("distance_min", 0)
            
            if distance_min <= distance <= distance_max:
                base_rate = data["base_success_rate"]
                
                # Add slight variance for realism (±3% typical variance)
                variance = random.uniform(-0.03, 0.03)
                return max(0.0, min(1.0, base_rate + variance))
        
        # If distance exceeds all categories, use very low probability
        return 0.20  # 20% for extremely long attempts (70+ yards)
    
    def _calculate_strategic_value(self, success_probability: float, field_state: FieldState,
                                 game_state: GameState, team_id: int) -> float:
        """
        Calculate strategic value of attempting field goal
        
        Combines success probability with game context to determine overall value
        """
        
        # Base strategic value components
        success_value = success_probability * FieldGoalStrategicBalance.STRATEGIC_VALUE_WEIGHTS["success_probability"]
        
        # Calculate point value impact
        point_impact = self._calculate_point_value_impact(game_state, team_id)
        point_value = point_impact * FieldGoalStrategicBalance.STRATEGIC_VALUE_WEIGHTS["point_value_impact"]
        
        # Calculate time situation value
        time_value = self._calculate_time_situation_value(game_state) * \
                    FieldGoalStrategicBalance.STRATEGIC_VALUE_WEIGHTS["time_situation"]
        
        # Calculate field position value (opportunity cost)
        field_pos_value = self._calculate_field_position_value(field_state) * \
                         FieldGoalStrategicBalance.STRATEGIC_VALUE_WEIGHTS["field_position_value"]
        
        return success_value + point_value + time_value + field_pos_value
    
    def _calculate_point_value_impact(self, game_state: GameState, team_id: int) -> float:
        """Calculate how valuable 3 points would be in current game context"""
        
        score_diff = game_state.scoreboard.get_score_differential(team_id)
        multipliers = FieldGoalStrategicBalance.GAME_CONTEXT_MULTIPLIERS["score_differential"]
        
        # Determine score situation and apply appropriate multiplier
        if score_diff == -3:
            return multipliers["fg_ties_game"]      # Field goal ties the game
        elif -2 <= score_diff <= -1:
            return multipliers["fg_takes_lead"]     # Field goal takes the lead
        elif -6 <= score_diff <= 0:
            return multipliers["fg_extends_lead_close"]  # Close game, extending lead
        elif 1 <= score_diff <= 6:
            return multipliers["fg_extends_lead_close"]  # Close game, extending lead
        elif 7 <= score_diff <= 13:
            return multipliers["fg_extends_lead_safe"]   # Safe lead extension
        elif score_diff >= 14:
            return multipliers["fg_meaningless"]    # Already winning big
        elif -13 <= score_diff <= -7:
            return multipliers["fg_narrows_deficit"] # Narrowing deficit
        else:  # score_diff <= -14
            return multipliers["fg_meaningless"]    # Too far behind for FG to matter much
    
    def _calculate_time_situation_value(self, game_state: GameState) -> float:
        """Calculate time-based value multiplier"""
        
        time_remaining = game_state.clock.clock
        quarter = game_state.clock.quarter
        multipliers = FieldGoalStrategicBalance.GAME_CONTEXT_MULTIPLIERS["time_remaining"]
        
        # Overtime - any points are crucial
        if quarter >= 5:
            return FieldGoalStrategicBalance.GAME_CONTEXT_MULTIPLIERS["quarter_context"]["overtime"]
        
        # Fourth quarter considerations
        if quarter == 4:
            if time_remaining <= 120:  # Final 2 minutes
                return multipliers["final_2_minutes"]
            elif time_remaining <= 300:  # Final 5 minutes
                return multipliers["final_5_minutes"]
            else:
                return FieldGoalStrategicBalance.GAME_CONTEXT_MULTIPLIERS["quarter_context"]["fourth_quarter"]
        
        # End of first half
        if quarter == 2 and time_remaining <= 120:
            return FieldGoalStrategicBalance.GAME_CONTEXT_MULTIPLIERS["quarter_context"]["end_of_first_half"]
        
        # Second half vs first half
        if quarter >= 3:
            return multipliers["second_half"]
        else:
            return multipliers["first_half"]
    
    def _calculate_field_position_value(self, field_state: FieldState) -> float:
        """
        Calculate value of current field position vs points
        
        Better field position means higher opportunity cost for settling for FG
        """
        
        # Red zone - high opportunity cost for settling for FG
        if field_state.field_position >= 80:
            return 0.3  # Lower value - should consider going for TD
        
        # Good field position - moderate opportunity cost
        elif field_state.field_position >= 65:
            return 0.6  # Moderate value - reasonable to take points
        
        # Marginal field position - higher value for points
        else:
            return 0.8  # Higher value - good to get any points
    
    def _apply_archetype_philosophy(self, success_probability: float, strategic_value: float,
                                  archetype: str, field_state: FieldState, 
                                  game_state: GameState) -> Tuple[bool, str]:
        """
        Apply coaching archetype philosophy to make final decision
        
        Args:
            success_probability: Calculated success probability
            strategic_value: Overall strategic value
            archetype: Coaching philosophy
            field_state: Current field state
            game_state: Current game state
            
        Returns:
            Tuple[bool, str]: (should_attempt, reasoning)
        """
        
        if archetype not in FieldGoalStrategicBalance.ARCHETYPE_THRESHOLDS:
            archetype = "balanced"  # Default fallback
        
        thresholds = FieldGoalStrategicBalance.ARCHETYPE_THRESHOLDS[archetype]
        min_success = thresholds["minimum_success_rate"]
        philosophy = thresholds["philosophy"]
        
        # Conservative philosophy: Take points when available
        if archetype == "conservative":
            if success_probability >= min_success:
                return True, f"Conservative approach: {success_probability:.1%} success rate meets {min_success:.1%} threshold"
            else:
                return False, f"Conservative approach: {success_probability:.1%} success rate below {min_success:.1%} threshold"
        
        # Aggressive philosophy: Only take sure things, prefer TDs
        elif archetype == "aggressive":
            # In red zone, heavily favor going for TD
            if field_state.field_position >= 80:  # Red zone
                red_zone_threshold = thresholds["red_zone_fg_threshold"]
                if success_probability >= red_zone_threshold:
                    return True, f"Aggressive in red zone: {success_probability:.1%} meets high {red_zone_threshold:.1%} threshold"
                else:
                    return False, f"Aggressive philosophy: Go for TD, {success_probability:.1%} below red zone threshold {red_zone_threshold:.1%}"
            
            # Outside red zone, still prefer high-probability kicks only
            if success_probability >= min_success:
                return True, f"Aggressive approach: {success_probability:.1%} meets high threshold {min_success:.1%}"
            else:
                return False, f"Aggressive approach: {success_probability:.1%} below high threshold {min_success:.1%}"
        
        # Balanced philosophy: Pure strategic value calculation
        else:  # balanced
            # Use strategic value with minimum success probability safeguard
            if success_probability >= min_success and strategic_value >= 0.65:
                return True, f"Balanced approach: Strategic value {strategic_value:.2f} justifies attempt"
            elif success_probability < min_success:
                return False, f"Balanced approach: {success_probability:.1%} below minimum {min_success:.1%}"
            else:
                return False, f"Balanced approach: Strategic value {strategic_value:.2f} too low for attempt"
    
    def _get_alternative_recommendation(self, attempt_fg: bool, field_state: FieldState,
                                      archetype: str) -> str:
        """Provide alternative recommendation if not attempting field goal"""
        
        if attempt_fg:
            return "Attempt field goal"
        
        # Determine best alternative based on situation
        if field_state.yards_to_go <= 3:
            if archetype == "aggressive":
                return "Go for it - high touchdown potential"
            else:
                return "Go for it on short yardage or punt for field position"
        elif field_state.field_position >= 80:
            return "Go for touchdown - red zone opportunity"
        elif field_state.field_position >= 40:
            return "Punt for field position"
        else:
            return "Go for it - limited field position value of punt"