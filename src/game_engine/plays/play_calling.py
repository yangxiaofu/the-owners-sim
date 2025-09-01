import random
from typing import Dict, Optional
from ..field.field_state import FieldState


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
            "4th_and_short": {"punt": +0.15, "field_goal": +0.15, "run": -0.05, "pass": -0.10},
            "4th_and_medium": {"punt": +0.15, "field_goal": +0.10, "pass": -0.15, "run": -0.10},
            "red_zone": {"field_goal": +0.25, "pass": -0.20, "run": -0.08},
            "deep_territory": {"run": +0.15, "pass": -0.10, "punt": +0.05},
            "3rd_and_long": {"pass": -0.05}           # Slightly more conservative on 3rd and long
        },
        "field_position_modifiers": {
            "own_territory": {"pass": -0.15, "run": +0.10},      # More conservative in own territory
            "opponent_territory": {"field_goal": +0.20, "run": +0.05}, # Take points when available
            "red_zone": {"field_goal": +0.35, "pass": -0.25, "run": -0.12}  # Strongly prefer FGs in red zone
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
    
    def determine_play_type(self, field_state: FieldState, offensive_coordinator: Dict, 
                          defensive_coordinator: Optional[Dict] = None) -> str:
        """
        Determine play type using archetype-based intelligence
        
        Args:
            field_state: Current game situation (down, distance, field position)
            offensive_coordinator: {"archetype": "aggressive", "custom_modifiers": {...}}
            defensive_coordinator: Optional defensive coordinator data for counter-effects
            
        Returns:
            str: Play type ("run", "pass", "punt", "field_goal")
        """
        
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
    
    def _apply_contextual_factors(self, probabilities: Dict[str, float], 
                                field_state: FieldState) -> Dict[str, float]:
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