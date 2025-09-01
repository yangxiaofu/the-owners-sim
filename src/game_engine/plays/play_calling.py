import random
from typing import Dict, Optional, TYPE_CHECKING, Any
from ..field.field_state import FieldState
from .strategic_field_goal_decision import StrategicFieldGoalDecisionMaker, FieldGoalDecision

if TYPE_CHECKING:
    from ..coaching.clock.context.game_context import GameContext


class PlayCallingBalance:
    """
    Centralized configuration for coaching archetype balance - easy for game designers to tune
    
    This class contains all the magic numbers that affect play calling intelligence.
    Adjust these values to change coaching behavior:
    - Higher risk_tolerance = more aggressive 4th down decisions
    - Stronger situation_modifiers = more realistic coaching responses
    - Defensive influence factors affect counter-play calling
    
    Following the established pattern from PuntGameBalance and PassGameBalance.
    """
    
    # === BASE SITUATION PROBABILITIES (NFL Averages) ===
    BASE_PLAY_TENDENCIES = {
        "1st_and_10": {"run": 0.45, "pass": 0.55},
        "1st_and_short": {"run": 0.65, "pass": 0.35},
        "2nd_and_short": {"run": 0.65, "pass": 0.35}, 
        "2nd_and_medium": {"run": 0.42, "pass": 0.58},
        "2nd_and_long": {"run": 0.25, "pass": 0.75},
        "3rd_and_short": {"run": 0.55, "pass": 0.45},
        "3rd_and_medium": {"run": 0.35, "pass": 0.65},
        "3rd_and_long": {"pass": 0.75, "run": 0.25},
        "4th_and_short": {"run": 0.30, "pass": 0.15, "field_goal": 0.30, "punt": 0.25},
        "4th_and_medium": {"punt": 0.40, "field_goal": 0.45, "pass": 0.10, "run": 0.05},
        "4th_and_long": {"punt": 0.85, "field_goal": 0.10, "pass": 0.05}
    }
    
    # === DISTANCE THRESHOLDS ===
    SHORT_YARDAGE_THRESHOLD = 3        # 3 or fewer yards = short
    MEDIUM_YARDAGE_MIN = 4             # 4-7 yards = medium  
    MEDIUM_YARDAGE_MAX = 7
    LONG_YARDAGE_THRESHOLD = 8         # 8+ yards = long
    
    # === FIELD POSITION THRESHOLDS ===
    RED_ZONE_THRESHOLD = 80            # Field position 80+ = red zone
    DEEP_TERRITORY_THRESHOLD = 20      # Field position 20- = deep territory
    FIELD_GOAL_RANGE_THRESHOLD = 65    # Field position 65+ = field goal range
    
    # === CONTEXTUAL INFLUENCE WEIGHTS ===
    FIELD_POSITION_WEIGHT = 0.15       # How much field position affects decisions
    SCORE_DIFFERENTIAL_WEIGHT = 0.10   # How much score affects risk-taking
    TIME_REMAINING_WEIGHT = 0.12       # How much clock affects urgency
    PERSONNEL_MATCHUP_WEIGHT = 0.08    # How much personnel affects decisions
    
    # === ARCHETYPE MODIFIER LIMITS ===
    MAX_SITUATION_MODIFIER = 0.30      # Maximum modifier any archetype can apply
    MIN_PROBABILITY = 0.01             # Minimum probability for any play type
    MAX_PROBABILITY = 0.95             # Maximum probability for any play type
    
    # === DEFENSIVE INFLUENCE FACTORS ===
    DEFENSIVE_PRESSURE_IMPACT = 0.20   # How much defensive pressure affects offense
    COVERAGE_SCHEME_IMPACT = 0.15      # How much coverage affects play selection
    RUN_DEFENSE_IMPACT = 0.18          # How much run defense affects run/pass ratio
    
    # === TWO-POINT CONVERSION CONFIGURATION ===
    TWO_POINT_BASE_RATES = {           # Base probability of attempting 2-point conversion
        "conservative": 0.02,           # 2% base rate
        "aggressive": 0.12,             # 12% base rate
        "west_coast": 0.06,             # 6% base rate
        "run_heavy": 0.08,              # 8% base rate
        "air_raid": 0.10,               # 10% base rate
        "balanced": 0.04                # 4% base rate
    }
    
    # Score differential multipliers for 2-point attempts
    SCORE_DIFFERENTIAL_MULTIPLIERS = {
        "down_by_1": 4.0,               # 4.0x multiplier when down by 1
        "down_by_2": 3.5,               # 3.5x multiplier when down by 2
        "down_by_8": 2.5,               # 2.5x multiplier when down by 8
        "down_by_14": 2.0,              # 2.0x multiplier when down by 14
        "leading": 0.3                  # 0.3x multiplier when leading
    }
    
    # Time urgency multipliers for 2-point attempts
    TIME_URGENCY_MULTIPLIERS = {
        "final_2_minutes": 1.8,         # 1.8x multiplier in final 2 minutes
        "final_5_minutes": 1.4,         # 1.4x multiplier in final 5 minutes
        "overtime": 1.6                 # 1.6x multiplier in overtime
    }
    
    # === GAME CONTEXT DETECTION THRESHOLDS ===
    DESPERATION_MODE_SCORE_THRESHOLD = -7    # Score differential <= -7 triggers desperation
    DESPERATION_MODE_TIME_THRESHOLD = 300    # 5 minutes remaining
    PROTECT_LEAD_SCORE_THRESHOLD = 3         # Score differential >= 3 triggers protect lead
    PROTECT_LEAD_TIME_THRESHOLD = 600        # 10 minutes remaining
    TWO_MINUTE_DRILL_THRESHOLD = 120         # 2 minutes remaining
    END_OF_HALF_THRESHOLD = 120              # 2 minutes remaining in quarter 2 or 4
    OVERTIME_QUARTER_START = 5               # Quarter 5+ is overtime
    CLOSE_GAME_THRESHOLD = 7                 # Score differential within 7 points
    
    # === GAME CONTEXT MODIFIER WEIGHTS ===
    CONTEXT_MODIFIER_STRENGTH = 0.20        # How strongly context affects play calling
    DESPERATION_MODIFIER_STRENGTH = 0.30     # Extra strength for desperation situations
    PROTECT_LEAD_MODIFIER_STRENGTH = 0.25    # Extra strength for protecting leads
    
    # === 4TH DOWN CONTEXT OVERRIDE CONSTANTS ===
    # Desperation mode overrides
    DESPERATION_PUNT_REDUCTION = 0.60
    DESPERATION_GO_FOR_IT_INCREASE = 0.60
    TRAILING_7_PLUS_TIME_THRESHOLD = 300  # 5:00 remaining
    
    # Protect lead modifiers  
    PROTECT_LEAD_PUNT_INCREASE = 0.25  # Increased from 0.15 for stronger lead protection
    PROTECT_LEAD_SCORE_THRESHOLD = 3   # Lead by 3+ points
    PROTECT_LEAD_TIME_THRESHOLD = 600  # 10:00 remaining
    
    # Time urgency factors
    UNDER_2_MIN_PUNT_MULTIPLIER = 0.2
    UNDER_2_MIN_GO_FOR_IT_MULTIPLIER = 2.0
    UNDER_5_MIN_DOWN_7_PUNT_MULTIPLIER = 0.4
    UNDER_5_MIN_DOWN_7_GO_FOR_IT_MULTIPLIER = 1.6
    
    # Red zone critical context
    RED_ZONE_FG_VS_TD_SCORE_WEIGHT = 0.70  # Increased from 0.50 for much stronger TD emphasis
    RED_ZONE_TIME_PRESSURE_WEIGHT = 0.40   # Increased from 0.30 for stronger urgency
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense (following punt_play.py pattern)"""
        # Base probabilities should sum to 1.0 for each situation
        for situation, probs in cls.BASE_PLAY_TENDENCIES.items():
            total = sum(probs.values())
            if abs(total - 1.0) > 0.001:
                raise ValueError(f"Probabilities for {situation} must sum to 1.0, got {total}")
        
        # Weights should be reasonable
        weights = [cls.FIELD_POSITION_WEIGHT, cls.SCORE_DIFFERENTIAL_WEIGHT,
                  cls.TIME_REMAINING_WEIGHT, cls.PERSONNEL_MATCHUP_WEIGHT]
        for weight in weights:
            if not 0 <= weight <= 1:
                raise ValueError(f"Weight {weight} must be between 0 and 1")
        
        # Thresholds should make sense
        if cls.MEDIUM_YARDAGE_MIN <= cls.SHORT_YARDAGE_THRESHOLD:
            raise ValueError("Medium yardage min must be greater than short yardage threshold")
        if cls.LONG_YARDAGE_THRESHOLD <= cls.MEDIUM_YARDAGE_MAX:
            raise ValueError("Long yardage threshold must be greater than medium yardage max")


# Validate configuration on import (following established pattern)
PlayCallingBalance.validate_configuration()


# Coaching Archetype Matchup Matrix Configuration (following PUNT_SITUATION_MATRICES pattern)
OFFENSIVE_ARCHETYPES = {
    "conservative": {
        "philosophy": "minimize_risk_maximize_field_position",
        "risk_tolerance": 0.25,
        "4th_down_aggressiveness": 0.12,           # 12% 4th down conversion attempts (NFL: Conservative coaches <15%)
        "red_zone_passing": 0.25,                  # 25% red zone pass attempts, prefer field goals
        "situation_modifiers": {
            "4th_and_short": {"punt": +0.15, "field_goal": +0.10, "run": -0.02, "pass": -0.05},
            "4th_and_medium": {"punt": +0.20, "field_goal": +0.15, "pass": -0.05, "run": -0.03},
            "red_zone": {"field_goal": +0.20, "pass": -0.08, "run": -0.03},
            "deep_territory": {"run": +0.10, "pass": -0.05, "punt": +0.03},
            "3rd_and_long": {"pass": -0.02}           # Slightly more conservative on 3rd and long
        },
        "field_position_modifiers": {
            "own_territory": {"pass": -0.08, "run": +0.08},      # More conservative in own territory
            "opponent_territory": {"field_goal": +0.15, "run": +0.03}, # Take points when available
            "red_zone": {"field_goal": +0.25, "pass": -0.12, "run": -0.05}  # Strongly prefer FGs in red zone
        },
        "game_situation_modifiers": {
            "leading": {"run": +0.10, "pass": -0.08},            # Run clock when ahead
            "close_game": {"punt": +0.05, "field_goal": +0.08}   # Take points in close games
        }
    },
    
    "aggressive": {
        "philosophy": "maximum_scoring_opportunities",
        "risk_tolerance": 0.75,
        "4th_down_aggressiveness": 0.25,           # 25% 4th down conversion attempts (NFL: Aggressive coaches 35-55%)
        "red_zone_passing": 0.80,                  # 80% red zone touchdown attempts (NFL: Aggressive coaches >80%)
        "field_goal_philosophy": {
            "approach": "prefer_touchdowns_over_field_goals",
            "minimum_success_rate": 0.85,          # Only take "sure thing" field goals
            "red_zone_fg_threshold": 0.90,         # Strongly prefer TDs in red zone
            "long_fg_willingness": 0.75,           # Willing to try long FGs instead of punting
            "game_situation_modifier": 0.8         # 20% reduction to FG preference, prefer TDs
        },
        "situation_modifiers": {
            "4th_and_short": {"run": +0.06, "pass": +0.04, "punt": -0.04, "field_goal": -0.02},
            "4th_and_medium": {"punt": -0.03, "pass": +0.02, "run": +0.01, "field_goal": -0.01},
            "red_zone": {"pass": +0.25, "run": +0.05, "field_goal": -0.25},
            "3rd_and_long": {"pass": +0.10},                     # More aggressive passing
            "goal_line": {"pass": +0.15, "run": +0.10}           # Go for touchdowns
        },
        "field_position_modifiers": {
            "opponent_territory": {"pass": +0.15, "run": +0.05}, # Aggressive in opponent territory
            "own_territory": {"pass": +0.05}                     # Still willing to throw from own end
        },
        "game_situation_modifiers": {
            "trailing": {"pass": +0.20, "4th_down": +0.25},      # Aggressive when behind
            "close_game": {"pass": +0.10, "field_goal": -0.10}   # Go for TDs instead of FGs
        }
    },
    
    "west_coast": {
        "philosophy": "short_passing_precision_offense",
        "short_pass_emphasis": 0.80,               # 80% short pass preference (NFL: West Coast >75% short completion)
        "play_action_frequency": 0.35,             # 35% play action usage
        "yac_emphasis": 0.70,                      # Yards after catch focus
        "situation_modifiers": {
            "1st_and_10": {"pass": +0.20, "run": -0.15},         # Establish passing rhythm early
            "2nd_and_medium": {"pass": +0.15, "run": -0.10},     # Keep passing chains moving
            "3rd_and_medium": {"pass": +0.10},                   # High-percentage passes on 3rd down
            "3rd_and_short": {"pass": +0.05}                     # Even 3rd and short can be passes
        },
        "route_preferences": {
            "short_routes": +0.30,                  # Slants, hitches, screens
            "intermediate_routes": +0.15,           # 10-15 yard patterns
            "deep_routes": -0.20                    # Less emphasis on deep balls
        },
        "personnel_preferences": {
            "3wr_sets": +0.25,                      # 3+ receiver sets preferred
            "rb_receiving": +0.20                   # Running back receiving emphasis
        }
    },
    
    "run_heavy": {
        "philosophy": "ground_and_pound_control",
        "run_pass_ratio": 0.60,                    # 60% run plays (NFL: Run-heavy >55%)
        "power_formation_preference": 0.65,        # Prefer power running formations
        "time_of_possession_focus": 0.75,          # Control the clock
        "field_goal_philosophy": {
            "approach": "prefer_points_over_risk",
            "minimum_success_rate": 0.72,          # Conservative but not as much as pure conservative
            "red_zone_fg_threshold": 0.65,         # Moderate willingness to take FGs in red zone
            "long_fg_willingness": 0.45,           # Less willing to attempt long FGs
            "game_situation_modifier": 1.15        # 15% boost to FG preference, fits control philosophy
        },
        "situation_modifiers": {
            "1st_and_10": {"run": +0.25, "pass": -0.20},         # Establish run early
            "2nd_and_short": {"run": +0.20, "pass": -0.15},      # Keep running on short yardage
            "3rd_and_short": {"run": +0.15, "pass": -0.10},      # Run on 3rd and short
            "goal_line": {"run": +0.25, "pass": -0.20},          # Power run near goal line
            "red_zone": {"run": +0.15, "pass": -0.10}            # Run-heavy in red zone
        },
        "formation_preferences": {
            "power_i": +0.30,                       # I-formation power running
            "heavy_sets": +0.25,                    # Multiple tight ends/fullback
            "shotgun": -0.20                        # Less shotgun formation usage
        },
        "game_situation_modifiers": {
            "leading": {"run": +0.20, "pass": -0.15},            # Run to control clock when ahead
            "bad_weather": {"run": +0.25, "pass": -0.20}         # Run in bad conditions
        }
    },
    
    "air_raid": {
        "philosophy": "high_tempo_passing_attack",
        "pass_frequency": 0.70,                    # 70% pass attempts (NFL: Air Raid 68-82%)
        "deep_pass_frequency": 0.25,               # 25% deep passes (NFL: Air Raid >20%)
        "tempo_preference": 0.80,                  # High-tempo offense preference
        "field_goal_philosophy": {
            "approach": "prefer_touchdowns_over_field_goals",
            "minimum_success_rate": 0.78,          # Moderately aggressive with field goals
            "red_zone_fg_threshold": 0.85,         # Strong preference for TDs in red zone
            "long_fg_willingness": 0.70,           # Willing to try long FGs, fits aggressive nature
            "game_situation_modifier": 0.9         # 10% reduction to FG preference, prefer scoring TDs
        },
        "situation_modifiers": {
            "1st_and_10": {"pass": +0.17, "run": -0.14},         # Pass on first down but realistic
            "2nd_and_long": {"pass": +0.17, "run": -0.14},       # Pass-heavy on 2nd and long
            "3rd_and_medium": {"pass": +0.14, "run": -0.10},     # Pass-heavy on 3rd down
            "red_zone": {"pass": +0.17, "run": -0.14}            # Throw for TDs in red zone
        },
        "route_distribution": {
            "deep_routes": +0.25,                   # More vertical routes
            "intermediate_routes": +0.15,           # Medium-depth passes
            "short_routes": -0.05                   # Fewer short passes than West Coast
        },
        "game_situation_modifiers": {
            "trailing": {"pass": +0.25, "deep_routes": +0.15},   # Air it out when behind
            "garbage_time": {"pass": +0.30, "deep_routes": +0.20} # High volume when game is decided
        }
    },
    
    "balanced": {
        "philosophy": "situational_football",
        "adaptability": 0.85,                      # High situational adaptability
        "no_extreme_tendencies": True,             # Balanced approach to all situations
        "field_goal_philosophy": {
            "approach": "strategic_value_optimization",
            "minimum_success_rate": 0.75,          # Pure strategic value calculation
            "red_zone_fg_threshold": 0.70,         # Moderate preference for TDs in red zone
            "long_fg_willingness": 0.55,           # Balanced approach to long attempts
            "game_situation_modifier": 1.0         # No bias, pure strategic evaluation
        },
        "situation_modifiers": {
            # Minimal modifiers - stick close to base tendencies
            "4th_and_short": {"run": +0.05, "pass": +0.05, "field_goal": +0.02},
            "red_zone": {"pass": +0.05, "run": +0.05},
            "3rd_and_long": {"pass": +0.05}
        },
        "game_situation_modifiers": {
            "leading": {"run": +0.05},                            # Slightly more conservative when ahead
            "trailing": {"pass": +0.05}                          # Slightly more aggressive when behind
        }
    }
}


# Defensive Archetype Matrix Configuration (influences offensive decision-making)
DEFENSIVE_ARCHETYPES = {
    "blitz_heavy": {
        "philosophy": "pressure_the_quarterback",
        "pressure_frequency": 0.65,                # 65% pressure rate (NFL: Pressure defenses >35%)
        "blitz_rate": 0.40,                        # 40% blitz rate
        "pass_rush_strength": 0.85,                # Strong pass rush emphasis
        "offensive_counter_effects": {
            # How this defensive archetype influences offensive play calling
            "quick_passes": +0.15,                  # Force quick throws to counter pressure
            "screen_frequency": +0.10,              # More screens vs blitz-heavy teams
            "run_frequency": -0.05,                 # Less time for traditional run plays
            "deep_passes": -0.20,                   # Harder to go deep vs constant pressure
            "play_action": -0.10,                   # Risky to use play action vs pressure
            "shotgun_formation": +0.15              # Need quick release formations
        },
        "situational_pressure": {
            "3rd_and_long": +0.25,                  # Extra pressure on obvious passing downs
            "red_zone": +0.15,                      # Increase pressure near goal line
            "2_minute_drill": +0.20                 # Maximum pressure in hurry-up situations
        }
    },
    
    "run_stuffing": {
        "philosophy": "stop_the_ground_game",
        "run_defense_strength": 0.90,              # Elite run defense
        "gap_control_emphasis": 0.85,              # Strong gap integrity
        "interior_line_strength": 0.88,            # Powerful defensive interior
        "offensive_counter_effects": {
            "pass_frequency": +0.20,                # Force passing game vs strong run defense
            "outside_runs": +0.15,                  # Avoid interior running attacks
            "power_runs": -0.25,                    # Counter interior defensive strength
            "stretch_runs": +0.10,                  # Try to get outside the tackle box
            "draw_plays": -0.15,                    # Draw plays less effective vs gap control
            "short_passes": +0.10                   # Quick passes as run replacement
        },
        "formation_counters": {
            "heavy_formations": -0.20,              # Less effective vs run-stopping personnel
            "spread_formations": +0.15              # Spread them out to create run lanes
        }
    },
    
    "zone_coverage": {
        "philosophy": "prevent_big_plays",
        "coverage_strength": 0.85,                 # Strong zone coverage
        "underneath_coverage": 0.90,               # Excellent short-area coverage
        "deep_safety_help": 0.88,                  # Strong safety coverage deep
        "offensive_counter_effects": {
            "underneath_passes": +0.20,             # Exploit zone weaknesses underneath
            "deep_passes": -0.15,                   # Harder to go deep vs zone coverage
            "crossing_routes": +0.15,               # Attack zone seams and holes
            "comeback_routes": +0.10,               # Routes that sit in zone holes
            "vertical_routes": -0.10,               # Vertical routes less effective vs zones
            "run_frequency": +0.08                  # More running vs zone-heavy defenses
        },
        "zone_weaknesses": {
            "seam_routes": +0.20,                   # Attack seams between zones
            "rub_routes": +0.15,                    # Pick plays effective vs zone
            "flood_concepts": +0.12                 # Overload zones with multiple receivers
        }
    },
    
    "man_coverage": {
        "philosophy": "eliminate_individual_receivers",
        "man_coverage_strength": 0.88,             # Strong individual coverage
        "press_coverage": 0.75,                    # Physical coverage at line
        "cornerback_strength": 0.85,               # Elite cornerback play
        "offensive_counter_effects": {
            "pick_plays": +0.25,                    # Screens and picks vs man coverage
            "speed_routes": +0.15,                  # Use speed to beat man coverage
            "motion_plays": +0.12,                  # Motion to create mismatches
            "bunch_formations": +0.10,              # Tight formations create picks
            "comeback_routes": -0.15,               # Harder vs tight man coverage
            "run_frequency": +0.05                  # Slightly more running vs man coverage
        },
        "coverage_vulnerabilities": {
            "crossing_routes": +0.18,               # Crosses can lose man coverage
            "double_moves": +0.15,                  # Route breaks can beat man coverage
            "speed_mismatches": +0.20               # Fast receivers vs slower defenders
        }
    },
    
    "bend_dont_break": {
        "philosophy": "prevent_touchdowns_force_field_goals",
        "red_zone_strength": 0.90,                 # Elite red zone defense
        "takeaway_emphasis": 0.75,                  # Focus on creating turnovers
        "situational_toughness": 0.85,             # Strong in critical situations
        "offensive_counter_effects": {
            "red_zone_aggression": +0.15,           # Need to be more aggressive near goal
            "field_goals": -0.10,                   # Harder to settle for field goals
            "conservative_calls": -0.05,            # Can't be as conservative vs bend-don't-break
            "4th_down_attempts": +0.08,             # More likely to go for it on 4th
            "end_zone_fades": +0.12,                # More fade routes vs tight coverage
            "quick_slants": +0.15                   # Quick routes vs tight red zone coverage
        },
        "red_zone_specialization": {
            "goal_line_stands": 0.92,               # Elite goal line defense
            "red_zone_turnovers": 0.30,             # High turnover rate in red zone
            "field_goal_forcing": 0.75              # Force field goals instead of TDs
        }
    },
    
    "balanced_defense": {
        "philosophy": "no_major_weaknesses",
        "overall_strength": 0.75,                  # Solid across all areas
        "adaptability": 0.85,                      # Can adjust to offensive schemes
        "no_major_vulnerabilities": True,          # No glaring weaknesses to exploit
        "offensive_counter_effects": {
            # Minimal counter-effects - balanced defense doesn't force major adjustments
            "situational_awareness": +0.05,         # Must be more situationally aware
            "execution_emphasis": +0.08             # Execution becomes more important
        }
    }
}


class PlayCaller:
    """
    Handles intelligent play calling based on coaching archetypes
    
    This class follows the same pattern as PuntPlay, PassPlay, etc. - containing the main
    simulation logic while using the centralized configuration classes and matrices.
    """
    
    def __init__(self):
        """Initialize the play caller with validation"""
        PlayCallingBalance.validate_configuration()
        self.strategic_fg_decision_maker = StrategicFieldGoalDecisionMaker()
    
    def determine_play_type(self, field_state: FieldState, offensive_coordinator: Dict, 
                          defensive_coordinator: Optional[Dict] = None,
                          score_differential: int = 0) -> str:
        """
        Determine play type using archetype-based intelligence
        
        Args:
            field_state: Current game situation (down, distance, field position)
            offensive_coordinator: {"archetype": "aggressive", "custom_modifiers": {...}}
            defensive_coordinator: Optional defensive coordinator data for counter-effects
            score_differential: Current score differential (positive = leading)
            
        Returns:
            str: Play type ("run", "pass", "punt", "field_goal")
        """
        
        # Store score differential for context overrides
        self._current_score_differential = score_differential
        
        # Step 1: Classify current game situation (following _determine_punt_situation pattern)
        situation = self._classify_game_situation(field_state)
        
        # Step 2: Get base probabilities for this situation
        if situation not in PlayCallingBalance.BASE_PLAY_TENDENCIES:
            # Fallback to balanced situation if not found
            situation = "1st_and_10" if field_state.down == 1 else "2nd_and_medium"
        
        base_probabilities = PlayCallingBalance.BASE_PLAY_TENDENCIES[situation].copy()
        
        # Step 3: Apply offensive archetype modifiers (like effectiveness calculation in other plays)
        modified_probabilities = self._apply_offensive_archetype(
            base_probabilities, offensive_coordinator, field_state
        )
        
        # Step 4: Apply defensive influence (like coverage effectiveness in punt plays)
        if defensive_coordinator:
            modified_probabilities = self._apply_defensive_influence(
                modified_probabilities, defensive_coordinator, field_state
            )
        
        # Step 5: Apply contextual factors (field position, score, time)
        final_probabilities = self._apply_contextual_factors(
            modified_probabilities, field_state
        )
        
        # Step 6: Normalize probabilities and make weighted selection
        return self._make_weighted_selection(final_probabilities)
    
    def determine_play_type_with_context(self, game_state, offensive_coordinator: Dict,
                                       defensive_coordinator: Optional[Dict] = None) -> str:
        """
        Enhanced play type determination with full game context detection
        
        This method provides the complete game context detection functionality.
        Use this when full game_state is available for optimal context-aware play calling.
        
        Args:
            game_state: Complete game state with clock, scoreboard, field info
            offensive_coordinator: {"archetype": "aggressive", "team_id": 123, "custom_modifiers": {...}}
            defensive_coordinator: Optional defensive coordinator data for counter-effects
            
        Returns:
            str: Play type ("run", "pass", "punt", "field_goal")
        """
        
        # Extract field state for compatibility with existing pipeline
        field_state = game_state.field if hasattr(game_state, 'field') else game_state
        
        # Step 1: Classify current game situation
        situation = self._classify_game_situation(field_state)
        
        # Step 2: Get base probabilities for this situation
        if situation not in PlayCallingBalance.BASE_PLAY_TENDENCIES:
            situation = "1st_and_10" if field_state.down == 1 else "2nd_and_medium"
        
        base_probabilities = PlayCallingBalance.BASE_PLAY_TENDENCIES[situation].copy()
        
        # Step 3: Apply offensive archetype modifiers
        modified_probabilities = self._apply_offensive_archetype(
            base_probabilities, offensive_coordinator, field_state
        )
        
        # Step 4: Apply defensive influence
        if defensive_coordinator:
            modified_probabilities = self._apply_defensive_influence(
                modified_probabilities, defensive_coordinator, field_state
            )
        
        # Step 5: Detect game context and apply context-specific factors
        offensive_team_id = offensive_coordinator.get("team_id")
        game_context = self.detect_game_context(game_state, offensive_team_id) if offensive_team_id else "normal_game"
        
        final_probabilities = self._apply_contextual_factors(
            modified_probabilities, field_state, game_context, game_state, offensive_team_id
        )
        
        # Step 6: Normalize probabilities and make weighted selection
        return self._make_weighted_selection(final_probabilities)
    
    def _classify_game_situation(self, field_state: FieldState) -> str:
        """
        Classify current game situation for play calling
        
        Following the pattern from _determine_punt_situation in punt_play.py
        """
        down = field_state.down
        yards_to_go = field_state.yards_to_go
        
        # 4th down situations (similar to emergency punt logic)
        if down == 4:
            if yards_to_go <= PlayCallingBalance.SHORT_YARDAGE_THRESHOLD:
                return "4th_and_short"
            elif yards_to_go <= PlayCallingBalance.MEDIUM_YARDAGE_MAX:
                return "4th_and_medium" 
            else:
                return "4th_and_long"
        
        # 3rd down situations
        elif down == 3:
            if yards_to_go <= PlayCallingBalance.SHORT_YARDAGE_THRESHOLD:
                return "3rd_and_short"
            elif yards_to_go <= PlayCallingBalance.MEDIUM_YARDAGE_MAX:
                return "3rd_and_medium"
            else:
                return "3rd_and_long"
        
        # 2nd down situations  
        elif down == 2:
            if yards_to_go <= PlayCallingBalance.SHORT_YARDAGE_THRESHOLD:
                return "2nd_and_short"
            elif yards_to_go <= PlayCallingBalance.MEDIUM_YARDAGE_MAX:
                return "2nd_and_medium"
            else:
                return "2nd_and_long"
        
        # 1st down situations
        else:  # down == 1
            if yards_to_go <= PlayCallingBalance.SHORT_YARDAGE_THRESHOLD:
                return "1st_and_short"  # Goal line or short yardage
            else:
                return "1st_and_10"     # Standard first down
    
    def _apply_offensive_archetype(self, base_probabilities: Dict[str, float], 
                                 coordinator: Dict, field_state: FieldState) -> Dict[str, float]:
        """
        Apply offensive archetype modifiers to base probabilities
        
        Following the pattern from _calculate_punter_effectiveness_for_situation
        """
        archetype_name = coordinator.get("archetype", "balanced")
        
        if archetype_name not in OFFENSIVE_ARCHETYPES:
            # Invalid archetype, return base probabilities unchanged
            return base_probabilities
        
        archetype = OFFENSIVE_ARCHETYPES[archetype_name]
        modified_probs = base_probabilities.copy()
        
        # Apply situation-specific modifiers
        situation_modifiers = archetype.get("situation_modifiers", {})
        
        # Check for specific situation matches
        situation = self._classify_game_situation(field_state)
        if situation in situation_modifiers:
            for play_type, modifier in situation_modifiers[situation].items():
                if play_type in modified_probs:
                    modified_probs[play_type] += modifier
        
        # Apply field position modifiers
        field_position_modifiers = archetype.get("field_position_modifiers", {})
        
        # Determine field position context
        if field_state.field_position <= PlayCallingBalance.DEEP_TERRITORY_THRESHOLD:
            position_context = "own_territory"
        elif field_state.field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD:
            position_context = "red_zone"  
        elif field_state.field_position >= PlayCallingBalance.FIELD_GOAL_RANGE_THRESHOLD:
            position_context = "opponent_territory"
        else:
            position_context = "midfield"
        
        if position_context in field_position_modifiers:
            for play_type, modifier in field_position_modifiers[position_context].items():
                if play_type in modified_probs:
                    modified_probs[play_type] += modifier
        
        # Apply custom modifiers from coordinator data
        custom_modifiers = coordinator.get("custom_modifiers", {})
        for modifier_key, modifier_value in custom_modifiers.items():
            # Apply custom modifiers based on situation (this can be extended)
            if modifier_key == "red_zone_aggression" and field_state.field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD:
                modified_probs["pass"] = modified_probs.get("pass", 0) + modifier_value
                modified_probs["field_goal"] = modified_probs.get("field_goal", 0) - modifier_value * 0.7
        
        # Apply 4th down context overrides when score differential is available
        if field_state.down == 4 and hasattr(self, '_current_score_differential'):
            modified_probs = self._apply_context_overrides(
                modified_probs, field_state, archetype_name
            )
        
        return modified_probs
    
    def _apply_defensive_influence(self, probabilities: Dict[str, float], 
                                 defensive_coordinator: Dict, field_state: FieldState) -> Dict[str, float]:
        """
        Apply defensive archetype influence on offensive play calling
        
        Following the pattern from _calculate_coverage_effectiveness in punt plays
        """
        defensive_archetype = defensive_coordinator.get("archetype", "balanced_defense")
        
        if defensive_archetype not in DEFENSIVE_ARCHETYPES:
            return probabilities
        
        defense = DEFENSIVE_ARCHETYPES[defensive_archetype]
        modified_probs = probabilities.copy()
        
        # Apply offensive counter-effects
        counter_effects = defense.get("offensive_counter_effects", {})
        
        for effect_type, modifier in counter_effects.items():
            # Apply effects based on type
            if effect_type == "pass_frequency":
                modified_probs["pass"] = modified_probs.get("pass", 0) + modifier
                modified_probs["run"] = modified_probs.get("run", 0) - modifier
            elif effect_type == "run_frequency":
                modified_probs["run"] = modified_probs.get("run", 0) + modifier
                modified_probs["pass"] = modified_probs.get("pass", 0) - modifier
            elif effect_type == "quick_passes":
                # Quick passes increase overall pass frequency slightly
                modified_probs["pass"] = modified_probs.get("pass", 0) + modifier * 0.5
            elif effect_type == "deep_passes":
                # Deep pass reduction affects pass frequency
                modified_probs["pass"] = modified_probs.get("pass", 0) + modifier
        
        return modified_probs
    
    def detect_game_context(self, game_state, offensive_team_id: int) -> str:
        """
        Detect current game context based on score, time, field position, and quarter
        
        Args:
            game_state: Complete game state with clock, scoreboard, and field info
            offensive_team_id: ID of the team with possession for score differential calculation
            
        Returns:
            str: Context mode ("desperation_mode", "protect_lead", "two_minute_drill", 
                "end_of_half", "overtime", "red_zone_critical", "normal_game")
        """
        try:
            # Extract context information
            quarter = getattr(game_state.clock, 'quarter', 1) if hasattr(game_state, 'clock') else 1
            time_remaining = getattr(game_state.clock, 'clock', 900) if hasattr(game_state, 'clock') else 900
            field_position = getattr(game_state.field, 'field_position', 50) if hasattr(game_state, 'field') else 50
            
            # Calculate score differential
            score_diff = 0
            if hasattr(game_state, 'scoreboard') and hasattr(game_state.scoreboard, 'get_score_differential'):
                score_diff = game_state.scoreboard.get_score_differential(offensive_team_id)
            
            # Context detection logic - order matters for priority
            
            # 1. Overtime takes precedence over everything
            if quarter >= PlayCallingBalance.OVERTIME_QUARTER_START:
                return "overtime"
            
            # 2. Desperation mode - trailing significantly with little time
            if (score_diff <= PlayCallingBalance.DESPERATION_MODE_SCORE_THRESHOLD and 
                time_remaining <= PlayCallingBalance.DESPERATION_MODE_TIME_THRESHOLD):
                return "desperation_mode"
            
            # 3. Two minute drill - any close game in final 2 minutes
            if (time_remaining <= PlayCallingBalance.TWO_MINUTE_DRILL_THRESHOLD and
                abs(score_diff) <= PlayCallingBalance.CLOSE_GAME_THRESHOLD):
                return "two_minute_drill"
            
            # 4. End of half - final 2 minutes of 2nd or 4th quarter
            if (quarter in [2, 4] and 
                time_remaining <= PlayCallingBalance.END_OF_HALF_THRESHOLD):
                return "end_of_half"
            
            # 5. Protect lead - ahead with limited time (and late in game)
            if (score_diff >= PlayCallingBalance.PROTECT_LEAD_SCORE_THRESHOLD and
                time_remaining <= PlayCallingBalance.PROTECT_LEAD_TIME_THRESHOLD and
                quarter >= 4):  # Only in 4th quarter or later
                return "protect_lead"
            
            # 6. Red zone critical - in red zone during close game or desperation
            if (field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD and
                (abs(score_diff) <= PlayCallingBalance.CLOSE_GAME_THRESHOLD or 
                 score_diff <= PlayCallingBalance.DESPERATION_MODE_SCORE_THRESHOLD)):
                return "red_zone_critical"
            
            # 7. Default to normal game flow
            return "normal_game"
            
        except Exception as e:
            # Fallback to normal game if context detection fails
            return "normal_game"
    
    def _apply_contextual_factors(self, probabilities: Dict[str, float], 
                                field_state: FieldState, game_context: str = "normal_game", 
                                game_state=None, team_id=None) -> Dict[str, float]:
        """
        Apply game context factors (score, time, weather, etc.)
        
        This can be extended to include more contextual information as it becomes available
        """
        # For now, just apply basic field position logic
        modified_probs = probabilities.copy()
        
        # Red zone adjustments - more aggressive near goal line
        if field_state.field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD:
            # Increase pass attempts in red zone (go for TDs)
            modified_probs["pass"] = modified_probs.get("pass", 0) + 0.05
            # Reduce punting in red zone (should rarely punt from red zone)
            modified_probs["punt"] = max(0.01, modified_probs.get("punt", 0) - 0.10)
        
        # Deep territory adjustments - more conservative
        elif field_state.field_position <= PlayCallingBalance.DEEP_TERRITORY_THRESHOLD:
            # Slightly more conservative in own territory
            modified_probs["run"] = modified_probs.get("run", 0) + 0.03
            modified_probs["pass"] = modified_probs.get("pass", 0) - 0.02
        
        return modified_probs
    
    def _make_weighted_selection(self, probabilities: Dict[str, float]) -> str:
        """
        Make weighted random selection from probabilities
        
        Following the same pattern used in other play type selections
        """
        # Ensure no negative probabilities and enforce limits
        for play_type in probabilities:
            probabilities[play_type] = max(
                PlayCallingBalance.MIN_PROBABILITY,
                min(PlayCallingBalance.MAX_PROBABILITY, probabilities[play_type])
            )
        
        # Normalize probabilities to sum to 1.0
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            for play_type in probabilities:
                probabilities[play_type] /= total_prob
        else:
            # Fallback to equal probabilities if something went wrong
            equal_prob = 1.0 / len(probabilities)
            for play_type in probabilities:
                probabilities[play_type] = equal_prob
        
        # Make weighted random selection
        random_value = random.random()
        cumulative_prob = 0.0
        
        for play_type, prob in probabilities.items():
            cumulative_prob += prob
            if random_value <= cumulative_prob:
                return play_type
        
        # Fallback (should never reach here with proper normalization)
        return list(probabilities.keys())[0]
    
    def should_attempt_two_point_conversion(self, offensive_coordinator: Dict, 
                                          game_context: 'GameContext') -> bool:
        """
        Determine whether to attempt a two-point conversion after a touchdown.
        
        Uses archetype base rates modified by score differential and time urgency.
        Integrates with the existing context detection framework.
        
        Args:
            offensive_coordinator: {"archetype": "aggressive", "custom_modifiers": {...}}
            game_context: GameContext object containing situational analysis
            
        Returns:
            bool: True if should attempt two-point conversion, False for extra point
        """
        archetype_name = offensive_coordinator.get("archetype", "balanced")
        
        # Get base rate for this archetype
        base_rate = PlayCallingBalance.TWO_POINT_BASE_RATES.get(archetype_name, 0.04)
        
        # Calculate final probability with modifiers
        final_probability = self._calculate_two_point_probability(
            base_rate, game_context, offensive_coordinator
        )
        
        # Make decision based on final probability
        return random.random() < final_probability
    
    def _calculate_two_point_probability(self, base_rate: float, 
                                       game_context: 'GameContext',
                                       coordinator: Dict) -> float:
        """
        Calculate final two-point conversion probability using context modifiers.
        
        Args:
            base_rate: Base archetype probability
            game_context: Current game context for situational analysis
            coordinator: Coordinator data for custom modifiers
            
        Returns:
            float: Final probability (0.0 to 1.0)
        """
        probability = base_rate
        
        # Apply score differential modifiers
        probability *= self._get_score_differential_modifier(game_context)
        
        # Apply time urgency modifiers
        probability *= self._get_time_urgency_modifier(game_context)
        
        # Apply custom coordinator modifiers if present
        custom_modifiers = coordinator.get("custom_modifiers", {})
        two_point_aggression = custom_modifiers.get("two_point_aggression", 1.0)
        probability *= two_point_aggression
        
        # Ensure probability stays within reasonable bounds
        probability = max(0.001, min(0.95, probability))
        
        return probability
    
    def _get_score_differential_modifier(self, game_context: 'GameContext') -> float:
        """
        Get score differential modifier for two-point conversion probability.
        
        Args:
            game_context: Current game context
            
        Returns:
            float: Multiplier based on score differential
        """
        diff = game_context.score_differential
        
        # Check specific score differentials that matter for two-point decisions
        if diff == -1:
            return PlayCallingBalance.SCORE_DIFFERENTIAL_MULTIPLIERS["down_by_1"]
        elif diff == -2:
            return PlayCallingBalance.SCORE_DIFFERENTIAL_MULTIPLIERS["down_by_2"]
        elif diff == -8:
            return PlayCallingBalance.SCORE_DIFFERENTIAL_MULTIPLIERS["down_by_8"]
        elif diff == -14:
            return PlayCallingBalance.SCORE_DIFFERENTIAL_MULTIPLIERS["down_by_14"]
        elif diff > 0:
            return PlayCallingBalance.SCORE_DIFFERENTIAL_MULTIPLIERS["leading"]
        else:
            # Default multiplier for other score differentials
            if diff < -14:
                # Very far behind - moderate increase in two-point attempts
                return 1.8
            elif -14 < diff < -8:
                # Moderately behind - slight increase
                return 1.5
            elif -8 < diff < -2:
                # Somewhat behind - slight increase
                return 1.3
            else:
                # Other situations - neutral
                return 1.0
    
    def _get_time_urgency_modifier(self, game_context: 'GameContext') -> float:
        """
        Get time urgency modifier for two-point conversion probability.
        
        Args:
            game_context: Current game context
            
        Returns:
            float: Multiplier based on time situation
        """
        multiplier = 1.0
        
        # Check for overtime (quarter > 4)
        if game_context.quarter > 4:
            multiplier *= PlayCallingBalance.TIME_URGENCY_MULTIPLIERS["overtime"]
        
        # Check for time-based urgency in regulation
        elif game_context.quarter == 4:  # 4th quarter only
            if game_context.time_remaining <= 120:  # Final 2 minutes
                multiplier *= PlayCallingBalance.TIME_URGENCY_MULTIPLIERS["final_2_minutes"]
            elif game_context.time_remaining <= 300:  # Final 5 minutes
                multiplier *= PlayCallingBalance.TIME_URGENCY_MULTIPLIERS["final_5_minutes"]
        
        # End of half scenarios (2nd quarter final 2 minutes)
        elif game_context.quarter == 2 and game_context.time_remaining <= 120:
            multiplier *= PlayCallingBalance.TIME_URGENCY_MULTIPLIERS["final_2_minutes"]
        
        return multiplier
    
    def _apply_context_overrides(self, probabilities: Dict[str, float], 
                               field_state: FieldState, archetype_name: str) -> Dict[str, float]:
        """
        Apply 4th down context overrides based on game situation.
        
        This is the primary method that orchestrates all context-based modifications
        for 4th down decisions, implementing the complete context override system.
        
        Args:
            probabilities: Current play type probabilities
            field_state: Current game situation (down, distance, field position)
            archetype_name: Offensive coordinator archetype
            
        Returns:
            Dict[str, float]: Modified probabilities with context overrides applied
        """
        # Only apply to 4th down situations
        if field_state.down != 4:
            return probabilities
            
        modified_probs = probabilities.copy()
        
        # Create simplified game context from available data
        game_context = self._create_simplified_context(field_state)
        
        # Apply desperation mode overrides (highest priority)
        if self._is_desperation_mode(game_context):
            modified_probs = self._apply_desperation_mode_overrides(
                modified_probs, archetype_name
            )
        
        # Apply protect lead modifiers (only if not in desperation)
        elif self._should_protect_lead(game_context):
            modified_probs = self._apply_protect_lead_modifiers(
                modified_probs, archetype_name
            )
        
        # Apply time urgency factors
        if self._is_time_critical(game_context):
            modified_probs = self._apply_time_urgency_factors(
                modified_probs, game_context
            )
        
        # Apply red zone critical context
        if self._is_red_zone_critical(field_state, game_context):
            modified_probs = self._apply_red_zone_context(
                modified_probs, game_context
            )
        
        return modified_probs
    
    def _create_simplified_context(self, field_state: FieldState) -> Dict[str, Any]:
        """
        Create simplified game context from available field state data.
        
        Uses lazy import to avoid circular dependencies with GameContext.
        """
        try:
            # Lazy import to avoid circular dependency
            from ..coaching.clock.context.game_context import GameContext
            
            # Create basic context with available data
            context = GameContext(
                possession_team_id=1,  # Dummy value for override calculations
                quarter=4,  # Assume 4th quarter for context overrides
                time_remaining=self._estimate_time_remaining(),
                field_position=field_state.field_position,
                score_differential=getattr(self, '_current_score_differential', 0),
                down=field_state.down,
                yards_to_go=field_state.yards_to_go
            )
            
            return {
                'quarter': context.quarter,
                'time_remaining': context.time_remaining,
                'field_position': context.field_position,
                'score_differential': context.score_differential,
                'down': context.down,
                'yards_to_go': context.yards_to_go
            }
            
        except (ImportError, TypeError):
            # Fallback if GameContext is not available
            return {
                'quarter': 4,  # Conservative assumption
                'time_remaining': 300,  # 5 minutes - reasonable default
                'field_position': field_state.field_position,
                'score_differential': getattr(self, '_current_score_differential', 0),
                'down': field_state.down,
                'yards_to_go': field_state.yards_to_go
            }
    
    def _estimate_time_remaining(self) -> float:
        """Estimate time remaining for context overrides when not available"""
        # Conservative estimates for 4th down decision making
        score_diff = getattr(self, '_current_score_differential', 0)
        
        if score_diff <= -7:  # Trailing significantly
            return 240  # 4 minutes - desperation territory
        elif score_diff >= 3:  # Leading
            return 480  # 8 minutes - protect lead territory
        else:
            return 360  # 6 minutes - neutral default
    
    def _is_desperation_mode(self, game_context: Dict[str, Any]) -> bool:
        """
        Identify desperation scenarios requiring aggressive 4th down decisions.
        
        Args:
            game_context: Simplified game context dictionary
            
        Returns:
            bool: True if in desperation mode
        """
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        # Desperation: trailing by 7+ with 5 minutes or less
        return (score_diff <= -7 and 
                time_remaining <= PlayCallingBalance.TRAILING_7_PLUS_TIME_THRESHOLD)
    
    def _should_protect_lead(self, game_context: Dict[str, Any]) -> bool:
        """
        Identify lead protection scenarios requiring conservative 4th down decisions.
        
        Args:
            game_context: Simplified game context dictionary
            
        Returns:
            bool: True if should protect lead
        """
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        # Protect lead: leading by 3+ with 10 minutes or less  
        return (score_diff >= PlayCallingBalance.PROTECT_LEAD_SCORE_THRESHOLD and
                time_remaining <= PlayCallingBalance.PROTECT_LEAD_TIME_THRESHOLD)
    
    def _is_time_critical(self, game_context: Dict[str, Any]) -> bool:
        """
        Identify time-critical situations requiring urgent 4th down decisions.
        
        Args:
            game_context: Simplified game context dictionary
            
        Returns:
            bool: True if time is critical
        """
        time_remaining = game_context.get('time_remaining', 900)
        score_diff = game_context.get('score_differential', 0)
        
        # Time critical scenarios
        under_2_min = time_remaining <= 120
        under_5_min_trailing_7 = (time_remaining <= 300 and score_diff <= -7)
        
        return under_2_min or under_5_min_trailing_7
    
    def _is_red_zone_critical(self, field_state: FieldState, 
                            game_context: Dict[str, Any]) -> bool:
        """
        Identify red zone critical situations for enhanced touchdown emphasis.
        
        Args:
            field_state: Current field state
            game_context: Simplified game context dictionary
            
        Returns:
            bool: True if red zone decisions are critical
        """
        in_red_zone = field_state.field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        # Red zone critical: in red zone during close game or when trailing with limited time
        close_game = abs(score_diff) <= 7
        trailing_with_time_pressure = score_diff < 0 and time_remaining <= 600
        
        return in_red_zone and (close_game or trailing_with_time_pressure)
    
    def _apply_desperation_mode_overrides(self, probabilities: Dict[str, float],
                                        archetype_name: str) -> Dict[str, float]:
        """
        Apply desperation mode overrides for aggressive 4th down decisions.
        
        Args:
            probabilities: Current play type probabilities
            archetype_name: Offensive coordinator archetype
            
        Returns:
            Dict[str, float]: Modified probabilities with desperation overrides
        """
        modified_probs = probabilities.copy()
        
        # Reduce punt probability dramatically
        if "punt" in modified_probs:
            punt_reduction = PlayCallingBalance.DESPERATION_PUNT_REDUCTION
            if archetype_name == "conservative":
                # Even conservative coaches become aggressive in desperation
                punt_reduction = 0.70  # 70% reduction for conservative in desperation
            
            original_punt = modified_probs["punt"]
            modified_probs["punt"] *= (1 - punt_reduction)
            punt_decrease = original_punt - modified_probs["punt"]
            
            # Redistribute punt probability to go-for-it options
            if "run" in modified_probs and "pass" in modified_probs:
                # Split between run and pass based on archetype
                if archetype_name == "run_heavy":
                    modified_probs["run"] += punt_decrease * 0.6
                    modified_probs["pass"] += punt_decrease * 0.4
                elif archetype_name in ["air_raid", "west_coast"]:
                    modified_probs["pass"] += punt_decrease * 0.6
                    modified_probs["run"] += punt_decrease * 0.4
                else:
                    # Balanced distribution
                    modified_probs["run"] += punt_decrease * 0.5
                    modified_probs["pass"] += punt_decrease * 0.5
        
        return modified_probs
    
    def _apply_protect_lead_modifiers(self, probabilities: Dict[str, float],
                                    archetype_name: str) -> Dict[str, float]:
        """
        Apply protect lead modifiers for conservative 4th down decisions.
        
        Args:
            probabilities: Current play type probabilities
            archetype_name: Offensive coordinator archetype
            
        Returns:
            Dict[str, float]: Modified probabilities with lead protection
        """
        modified_probs = probabilities.copy()
        
        # Increase punt frequency when protecting lead
        if "punt" in modified_probs:
            punt_increase = PlayCallingBalance.PROTECT_LEAD_PUNT_INCREASE
            
            # Conservative coaches punt even more when protecting lead
            if archetype_name == "conservative":
                punt_increase = 0.25  # 25% increase for conservative
            elif archetype_name == "aggressive":
                punt_increase = 0.20  # Increased from 0.10 - even aggressive coaches protect leads
            
            original_punt = modified_probs["punt"]
            modified_probs["punt"] += punt_increase
            
            # Reduce go-for-it attempts proportionally
            if "run" in modified_probs and "pass" in modified_probs:
                total_go_for_it = modified_probs["run"] + modified_probs["pass"]
                if total_go_for_it > 0:
                    reduction_factor = punt_increase / total_go_for_it
                    modified_probs["run"] *= (1 - reduction_factor * 0.6)
                    modified_probs["pass"] *= (1 - reduction_factor * 0.4)
        
        return modified_probs
    
    def _apply_time_urgency_factors(self, probabilities: Dict[str, float],
                                  game_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Apply time urgency factors for critical game situations.
        
        Args:
            probabilities: Current play type probabilities
            game_context: Simplified game context dictionary
            
        Returns:
            Dict[str, float]: Modified probabilities with time urgency
        """
        modified_probs = probabilities.copy()
        time_remaining = game_context.get('time_remaining', 900)
        score_diff = game_context.get('score_differential', 0)
        
        # Under 2 minutes trailing - maximum urgency
        if time_remaining <= 120 and score_diff < 0:
            if "punt" in modified_probs:
                modified_probs["punt"] *= PlayCallingBalance.UNDER_2_MIN_PUNT_MULTIPLIER
                punt_reduction = modified_probs["punt"]
                
                # Heavily favor passing for hurry-up offense
                if "pass" in modified_probs:
                    modified_probs["pass"] += punt_reduction * 0.6
                if "run" in modified_probs:
                    modified_probs["run"] += punt_reduction * 0.4
        
        # Under 5 minutes down 7+ - moderate urgency
        elif time_remaining <= 300 and score_diff <= -7:
            if "punt" in modified_probs:
                modified_probs["punt"] *= PlayCallingBalance.UNDER_5_MIN_DOWN_7_PUNT_MULTIPLIER
                punt_reduction = modified_probs["punt"]
                
                # Balanced run/pass distribution
                if "pass" in modified_probs:
                    modified_probs["pass"] += punt_reduction * 0.55
                if "run" in modified_probs:
                    modified_probs["run"] += punt_reduction * 0.45
        
        return modified_probs
    
    def _apply_red_zone_context(self, probabilities: Dict[str, float],
                              game_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Apply red zone critical context for touchdown emphasis.
        
        Args:
            probabilities: Current play type probabilities
            game_context: Simplified game context dictionary
            
        Returns:
            Dict[str, float]: Modified probabilities with red zone context
        """
        modified_probs = probabilities.copy()
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        # When trailing by more than a field goal, reduce field goal attempts
        if score_diff < -3:
            if "field_goal" in modified_probs:
                fg_reduction = modified_probs["field_goal"] * PlayCallingBalance.RED_ZONE_FG_VS_TD_SCORE_WEIGHT
                modified_probs["field_goal"] -= fg_reduction
                
                # Redistribute to touchdown attempts
                if "pass" in modified_probs:
                    modified_probs["pass"] += fg_reduction * 0.6
                if "run" in modified_probs:
                    modified_probs["run"] += fg_reduction * 0.4
        
        # Time pressure integration for red zone decisions
        if time_remaining <= 300:  # Under 5 minutes
            if "field_goal" in modified_probs and score_diff <= 0:  # Trailing or tied
                fg_reduction = modified_probs["field_goal"] * PlayCallingBalance.RED_ZONE_TIME_PRESSURE_WEIGHT
                modified_probs["field_goal"] -= fg_reduction
                
                # Favor touchdown attempts under time pressure
                if "pass" in modified_probs:
                    modified_probs["pass"] += fg_reduction * 0.7
                if "run" in modified_probs:
                    modified_probs["run"] += fg_reduction * 0.3
        
        return modified_probs