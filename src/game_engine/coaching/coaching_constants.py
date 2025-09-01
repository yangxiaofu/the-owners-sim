"""
Coaching system constants and configuration

This module contains all the configuration data for the coaching system including
personality templates, adaptation thresholds, and behavioral parameters.
Game designers can tune these values to adjust coaching behavior and realism.
"""

# === COACH PERSONALITY TEMPLATES ===
# Each personality defines base tendencies and modifiers for coaching decisions
COACH_PERSONALITIES = {
    'innovative': {
        'name': 'Innovative',
        'description': 'Embraces new strategies and unconventional play calls',
        'base_tendencies': {
            'run_tendency': 0.45,        # Slightly pass-heavy
            'aggression': 0.75,          # High risk tolerance
            'fourth_down_aggression': 0.70,
            'two_point_tendency': 0.60,
            'trick_play_tendency': 0.25, # High trick play usage
            'blitz_frequency': 0.65,     # Above average blitzing
            'coverage_preference': 0.6,  # Slight man coverage preference (0.0 = zone, 1.0 = man)
            'timeout_conservation': 0.4, # Less conservative with timeouts
        },
        'situational_modifiers': {
            'red_zone_aggression': 1.3,   # Very aggressive in red zone
            'late_game_conservatism': 0.7, # Less conservative late
            'trailing_aggression': 1.4,   # Very aggressive when behind
            'leading_conservatism': 0.8,  # Less conservative when ahead
        },
        'adaptation_speed': 0.8,          # Quick to adapt
        'opponent_memory': 0.9,           # Strong memory of opponent tendencies
        'pressure_resistance': 0.7,       # Good under pressure
    },
    
    'traditional': {
        'name': 'Traditional', 
        'description': 'Relies on proven strategies and conservative play calling',
        'base_tendencies': {
            'run_tendency': 0.55,        # Run-heavy approach
            'aggression': 0.35,          # Conservative
            'fourth_down_aggression': 0.25,
            'two_point_tendency': 0.20,
            'trick_play_tendency': 0.05, # Rarely uses trick plays
            'blitz_frequency': 0.35,     # Below average blitzing
            'coverage_preference': 0.3,  # Prefers zone coverage
            'timeout_conservation': 0.8, # Very conservative with timeouts
        },
        'situational_modifiers': {
            'red_zone_aggression': 0.9,   # Slightly less aggressive in red zone
            'late_game_conservatism': 1.4, # Very conservative late
            'trailing_aggression': 1.1,   # Slightly more aggressive when behind
            'leading_conservatism': 1.3,  # Very conservative when ahead
        },
        'adaptation_speed': 0.4,          # Slow to adapt
        'opponent_memory': 0.6,           # Moderate memory
        'pressure_resistance': 0.8,       # Steady under pressure
    },
    
    'aggressive': {
        'name': 'Aggressive',
        'description': 'Favors high-risk, high-reward strategies',
        'base_tendencies': {
            'run_tendency': 0.40,        # Pass-heavy
            'aggression': 0.85,          # Very aggressive
            'fourth_down_aggression': 0.80,
            'two_point_tendency': 0.70,
            'trick_play_tendency': 0.20,
            'blitz_frequency': 0.75,     # High blitzing
            'coverage_preference': 0.7,  # Prefers man coverage
            'timeout_conservation': 0.3, # Aggressive timeout usage
        },
        'situational_modifiers': {
            'red_zone_aggression': 1.4,   # Very aggressive in red zone
            'late_game_conservatism': 0.6, # Less conservative late
            'trailing_aggression': 1.5,   # Extremely aggressive when behind
            'leading_conservatism': 0.9,  # Still aggressive when ahead
        },
        'adaptation_speed': 0.6,          # Moderate adaptation
        'opponent_memory': 0.7,           # Good memory
        'pressure_resistance': 0.6,       # Can be affected by pressure
    },
    
    'defensive_minded': {
        'name': 'Defensive-Minded',
        'description': 'Emphasizes defense and field position',
        'base_tendencies': {
            'run_tendency': 0.60,        # Run-heavy to control clock
            'aggression': 0.30,          # Very conservative on offense
            'fourth_down_aggression': 0.20,
            'two_point_tendency': 0.15,
            'trick_play_tendency': 0.03,
            'blitz_frequency': 0.50,     # Balanced defensive approach
            'coverage_preference': 0.4,  # Slight zone preference
            'timeout_conservation': 0.9, # Very conservative timeouts
        },
        'situational_modifiers': {
            'red_zone_aggression': 0.8,   # Conservative in red zone
            'late_game_conservatism': 1.5, # Extremely conservative late
            'trailing_aggression': 1.2,   # Moderate increase when behind
            'leading_conservatism': 1.4,  # Very conservative when ahead
        },
        'adaptation_speed': 0.5,          # Moderate adaptation
        'opponent_memory': 0.8,           # Strong defensive memory
        'pressure_resistance': 0.9,       # Very steady under pressure
    },
    
    'balanced': {
        'name': 'Balanced',
        'description': 'Uses a well-rounded approach adapting to situations',
        'base_tendencies': {
            'run_tendency': 0.50,        # Perfectly balanced
            'aggression': 0.55,          # Moderate aggression
            'fourth_down_aggression': 0.45,
            'two_point_tendency': 0.40,
            'trick_play_tendency': 0.10,
            'blitz_frequency': 0.50,     # Balanced blitzing
            'coverage_preference': 0.5,  # No coverage preference
            'timeout_conservation': 0.6, # Moderate timeout usage
        },
        'situational_modifiers': {
            'red_zone_aggression': 1.1,   # Slightly more aggressive
            'late_game_conservatism': 1.1, # Slightly more conservative
            'trailing_aggression': 1.3,   # Good adjustment when behind
            'leading_conservatism': 1.1,  # Slightly more conservative ahead
        },
        'adaptation_speed': 0.7,          # Good adaptation
        'opponent_memory': 0.7,           # Good memory
        'pressure_resistance': 0.8,       # Good under pressure
    },
    
    'adaptive': {
        'name': 'Adaptive',
        'description': 'Quickly adjusts strategy based on game flow and opponent',
        'base_tendencies': {
            'run_tendency': 0.48,        # Slightly pass-favored base
            'aggression': 0.60,          # Above average aggression
            'fourth_down_aggression': 0.50,
            'two_point_tendency': 0.45,
            'trick_play_tendency': 0.15,
            'blitz_frequency': 0.55,     # Slightly above average
            'coverage_preference': 0.5,  # No base preference
            'timeout_conservation': 0.5, # Moderate usage
        },
        'situational_modifiers': {
            'red_zone_aggression': 1.2,   # Adaptable aggression
            'late_game_conservatism': 1.0, # No base bias
            'trailing_aggression': 1.4,   # Strong adaptation when behind
            'leading_conservatism': 1.2,  # Good adaptation when ahead
        },
        'adaptation_speed': 1.0,          # Maximum adaptation speed
        'opponent_memory': 1.0,           # Perfect opponent memory
        'pressure_resistance': 0.7,       # Good under pressure
    }
}

# === ADAPTATION THRESHOLDS ===
# When coaches should adapt their strategies based on game situations
ADAPTATION_THRESHOLDS = {
    # Score differential thresholds for strategy changes
    'score_differential': {
        'major_trailing': -14,     # Down by 14+ points
        'moderate_trailing': -7,   # Down by 7-13 points
        'close_game': 7,          # Within 7 points either way
        'moderate_leading': 14,    # Up by 7-13 points
        'major_leading': 21,      # Up by 14+ points
    },
    
    # Play effectiveness thresholds for tactical adjustments
    'effectiveness': {
        'struggling_threshold': 0.3,     # Below 30% effectiveness
        'average_threshold': 0.5,        # 50% effectiveness baseline
        'dominating_threshold': 0.7,     # Above 70% effectiveness
        'sample_size_minimum': 5,        # Minimum plays before adapting
    },
    
    # Momentum and tempo thresholds
    'momentum': {
        'strong_positive': 0.7,          # Strong positive momentum
        'moderate_positive': 0.3,        # Moderate positive momentum
        'neutral': 0.0,                  # Neutral momentum
        'moderate_negative': -0.3,       # Moderate negative momentum
        'strong_negative': -0.7,         # Strong negative momentum
    },
    
    # Time-based adaptation thresholds
    'time_based': {
        'early_game': 2700,              # First 45 minutes (2700 seconds)
        'mid_game': 1800,                # Middle 30 minutes
        'late_game': 900,                # Final 15 minutes
        'critical_time': 300,            # Final 5 minutes
        'desperation_time': 120,         # Final 2 minutes
    },
    
    # Field position adaptation
    'field_position': {
        'own_redzone': 20,               # Own 20 or closer
        'own_territory': 50,             # Own side of field
        'midfield': 60,                  # Between 40-yard lines
        'opponent_territory': 80,        # Opponent side
        'opponent_redzone': 100,         # Opponent 20 or closer
    }
}

# === OPPONENT MEMORY BONUSES ===
# How much coaches remember and adapt to specific opponents
OPPONENT_MEMORY_BONUSES = {
    'division_rival': 0.3,              # +30% adaptation vs division rivals
    'recent_opponent': 0.2,             # +20% vs teams faced in last 8 games
    'playoff_opponent': 0.25,           # +25% vs playoff opponents
    'same_season': 0.15,                # +15% vs teams faced this season
    'coaching_history': 0.1,            # +10% based on coaching history
}

# === EXPERIENCE MULTIPLIERS ===
# How coaching experience affects decision-making
EXPERIENCE_MULTIPLIERS = {
    'rookie_coach': {                   # 0-2 years experience
        'pressure_resistance': 0.6,
        'adaptation_speed': 0.7,
        'decision_consistency': 0.8,
        'timeout_management': 0.7,
    },
    'experienced_coach': {              # 3-9 years experience  
        'pressure_resistance': 0.8,
        'adaptation_speed': 0.9,
        'decision_consistency': 1.0,
        'timeout_management': 1.0,
    },
    'veteran_coach': {                  # 10+ years experience
        'pressure_resistance': 1.0,
        'adaptation_speed': 1.1,
        'decision_consistency': 1.2,
        'timeout_management': 1.3,
    }
}

# === PERSONNEL PACKAGE PREFERENCES ===
# Base tendencies for personnel package usage by personality
PERSONNEL_PREFERENCES = {
    'innovative': {
        'base_11_personnel': 0.45,       # 3 WR, 1 TE, 1 RB
        'base_12_personnel': 0.25,       # 2 WR, 2 TE, 1 RB  
        'base_21_personnel': 0.15,       # 2 WR, 1 TE, 2 RB
        'base_10_personnel': 0.15,       # 4 WR, 0 TE, 1 RB
    },
    'traditional': {
        'base_11_personnel': 0.35,
        'base_12_personnel': 0.35,       # Heavy TE usage
        'base_21_personnel': 0.25,       # Heavy run formations
        'base_10_personnel': 0.05,
    },
    'aggressive': {
        'base_11_personnel': 0.50,
        'base_12_personnel': 0.20,
        'base_21_personnel': 0.10,
        'base_10_personnel': 0.20,       # Spread formations
    },
    'defensive_minded': {
        'base_11_personnel': 0.30,
        'base_12_personnel': 0.40,
        'base_21_personnel': 0.25,
        'base_10_personnel': 0.05,
    },
    'balanced': {
        'base_11_personnel': 0.40,
        'base_12_personnel': 0.30,
        'base_21_personnel': 0.20,
        'base_10_personnel': 0.10,
    },
    'adaptive': {
        'base_11_personnel': 0.35,
        'base_12_personnel': 0.30,
        'base_21_personnel': 0.20,
        'base_10_personnel': 0.15,
    }
}

# === COACHING DECISION WEIGHTS ===
# How much different factors influence coaching decisions
DECISION_WEIGHTS = {
    'play_calling': {
        'down_and_distance': 0.35,       # Primary factor
        'field_position': 0.20,          # Secondary factor
        'score_differential': 0.25,      # Important factor
        'time_remaining': 0.15,          # Situational factor
        'weather': 0.05,                 # Minor factor
    },
    
    'fourth_down': {
        'field_position': 0.40,          # Most important
        'score_differential': 0.30,      # Very important  
        'time_remaining': 0.20,          # Important
        'kicker_confidence': 0.10,       # Minor factor
    },
    
    'timeout_usage': {
        'time_pressure': 0.50,           # Primary driver
        'scoring_opportunity': 0.25,     # Secondary
        'momentum_shift': 0.15,          # Tertiary
        'information_gathering': 0.10,   # Minor
    }
}

# === COACHING EFFECTIVENESS RANGES ===
# Performance ranges for different coaching aspects
COACHING_EFFECTIVENESS = {
    'play_calling': {
        'elite': (0.85, 1.0),           # Top 10% of coaches
        'good': (0.70, 0.84),           # Above average
        'average': (0.50, 0.69),        # Average NFL coach
        'below_average': (0.35, 0.49),  # Below average
        'poor': (0.20, 0.34),           # Bottom tier
    },
    
    'game_management': {
        'elite': (0.90, 1.0),
        'good': (0.75, 0.89),
        'average': (0.55, 0.74),
        'below_average': (0.40, 0.54),
        'poor': (0.25, 0.39),
    },
    
    'player_motivation': {
        'elite': (0.80, 1.0),
        'good': (0.65, 0.79),
        'average': (0.45, 0.64),
        'below_average': (0.30, 0.44),
        'poor': (0.15, 0.29),
    }
}

# === SITUATIONAL COACHING MODIFIERS ===
# How different game situations affect coaching decisions
SITUATIONAL_MODIFIERS = {
    'weather_conditions': {
        'clear': 1.0,
        'light_rain': 0.95,
        'heavy_rain': 0.85,
        'snow': 0.80,
        'wind_light': 0.90,
        'wind_heavy': 0.75,
    },
    
    'dome_vs_outdoor': {
        'dome_advantage': 1.05,          # 5% boost in dome
        'outdoor_penalty': 0.98,         # Slight penalty outdoors
        'cold_weather_penalty': 0.90,    # 10% penalty in cold
    },
    
    'playoff_pressure': {
        'wild_card': 1.1,                # 10% intensity boost
        'divisional': 1.15,              # 15% intensity boost  
        'championship': 1.2,             # 20% intensity boost
        'super_bowl': 1.25,              # 25% intensity boost
    }
}

# === COACHING PHILOSOPHY COMPATIBILITY ===
# How well different coaching styles work with personnel types
PHILOSOPHY_COMPATIBILITY = {
    'offensive_system_fit': {
        'west_coast': {
            'required_qb_accuracy': 0.8,
            'required_qb_decision': 0.75,
            'wr_route_running_bonus': 0.2,
            'te_receiving_bonus': 0.15,
        },
        'vertical_passing': {
            'required_qb_arm_strength': 0.8,
            'required_wr_speed': 0.75,
            'deep_ball_accuracy_bonus': 0.25,
            'oline_protection_requirement': 0.8,
        },
        'ground_and_pound': {
            'required_rb_power': 0.8,
            'required_oline_run_block': 0.85,
            'fb_usage_bonus': 0.3,
            'play_action_effectiveness': 0.2,
        },
        'spread_offense': {
            'required_qb_mobility': 0.7,
            'required_wr_depth': 0.8,
            'slot_receiver_bonus': 0.25,
            'tempo_bonus': 0.2,
        }
    }
}