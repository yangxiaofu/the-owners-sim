"""
Clock Strategy Timing Constants

Centralized configuration for all clock-related timing values used across
different coaching strategies. This makes it easy for designers to adjust
game pacing without hunting through multiple files.

All timing values are in seconds.
"""

from typing import Dict, Any


# =============================================================================
# BASE PLAY TIMING
# =============================================================================

class BasePlayTimes:
    """Base time for different play types across all strategies."""
    
    # Standard play times (in seconds)
    RUN = 32
    PASS_COMPLETE = 20  
    PASS_INCOMPLETE = 16
    PUNT = 18
    FIELD_GOAL = 18
    KICK = 18
    KNEEL = 42
    SPIKE = 4
    
    # Default fallback timing
    DEFAULT = 26
    
    @classmethod
    def get_base_times_dict(cls) -> Dict[str, int]:
        """Get all base times as a dictionary."""
        return {
            'run': cls.RUN,
            'pass_complete': cls.PASS_COMPLETE,
            'pass_incomplete': cls.PASS_INCOMPLETE,
            'punt': cls.PUNT,
            'field_goal': cls.FIELD_GOAL,
            'kick': cls.KICK,
            'kneel': cls.KNEEL,
            'spike': cls.SPIKE
        }


# =============================================================================
# STRATEGY ARCHETYPE MODIFIERS
# =============================================================================

class ArchetypeModifiers:
    """Base tempo adjustments for different coaching archetypes."""
    
    # Base adjustments applied to all plays
    BALANCED = 0        # Neutral baseline
    AIR_RAID = -2       # Faster tempo
    RUN_HEAVY = 2       # Slower, more methodical  
    WEST_COAST = 1      # Slightly methodical for precision
    
    # Play-specific modifiers by archetype
    PLAY_MODIFIERS = {
        'balanced': {
            'run': 0,
            'pass_complete': 0,
            'pass_incomplete': 0,
            'punt': 0,
            'field_goal': 0,
            'kick': 0
        },
        'air_raid': {
            'run': -1,
            'pass_complete': -3,
            'pass_incomplete': -3,
            'punt': 1,
            'field_goal': 2,
            'kick': 2
        },
        'run_heavy': {
            'run': 2,
            'pass_complete': 1,
            'pass_incomplete': 1,
            'punt': 0,
            'field_goal': 0,
            'kick': 0
        },
        'west_coast': {
            'run': 1,
            'pass_complete': 0,
            'pass_incomplete': 0,
            'punt': 0,
            'field_goal': 0,
            'kick': 0
        }
    }


# =============================================================================
# SITUATIONAL TIMING ADJUSTMENTS
# =============================================================================

class SituationalAdjustments:
    """Timing adjustments based on game situation."""
    
    # Score differential thresholds (points)
    SMALL_LEAD = 3
    MEDIUM_LEAD = 7  
    LARGE_LEAD = 14
    
    # Time thresholds (seconds)
    TWO_MINUTE_WARNING = 120
    FINAL_FIVE_MINUTES = 300
    FINAL_TEN_MINUTES = 600
    
    # Field position thresholds (yard line)
    OWN_TWENTY = 20
    MIDFIELD = 50
    RED_ZONE = 80
    GOAL_LINE = 95
    
    # Score-based adjustments (seconds)
    LEADING_LARGE_ADJUSTMENT = 3      # Extra clock control with big lead
    TRAILING_LARGE_ADJUSTMENT = -4    # Extra urgency when way behind
    LEADING_SMALL_ADJUSTMENT = 1      # Slight clock control
    TRAILING_SMALL_ADJUSTMENT = -2    # Slight urgency
    
    # Quarter-based adjustments
    FOURTH_QUARTER_LEAD_ADJUSTMENT = 2    # Clock control in 4th with lead
    FOURTH_QUARTER_TRAIL_ADJUSTMENT = -3  # Urgency in 4th when trailing
    TWO_MINUTE_DRILL_ADJUSTMENT = -2      # General two-minute urgency
    
    # Down and distance
    THIRD_DOWN_LONG_ADJUSTMENT = -1      # Urgency on 3rd and long
    FIRST_DOWN_ADJUSTMENT = 1            # Extra time to assess on 1st down
    RED_ZONE_ADJUSTMENT = 1              # Extra precision near goal line
    
    # Special situations
    NO_TIMEOUTS_ADJUSTMENT = -2          # Extra urgency with no timeouts
    HURRY_UP_ADJUSTMENT = -3             # General hurry-up situations
    CLOCK_CONTROL_ADJUSTMENT = 2         # Intentional clock management


# =============================================================================
# TIMING BOUNDS AND VALIDATION
# =============================================================================

class TimingBounds:
    """Minimum and maximum timing constraints."""
    
    MIN_PLAY_TIME = 8       # Absolute minimum seconds per play
    MAX_PLAY_TIME = 45      # Absolute maximum seconds per play
    
    # Target play counts per game for validation
    TARGET_MIN_PLAYS_PER_GAME = 120
    TARGET_MAX_PLAYS_PER_GAME = 180
    
    # Quarter length (seconds)
    QUARTER_LENGTH = 900    # 15 minutes
    REGULATION_TIME = 3600  # 60 minutes total
    
    @classmethod
    def enforce_bounds(cls, time_value: int) -> int:
        """Enforce minimum and maximum timing bounds."""
        return max(cls.MIN_PLAY_TIME, min(cls.MAX_PLAY_TIME, time_value))


# =============================================================================
# CONTEXT THRESHOLDS FOR DECISION MAKING  
# =============================================================================

class GameContextThresholds:
    """Thresholds for different game situations that affect timing decisions."""
    
    # Timeout thresholds
    NO_TIMEOUTS = 0
    FEW_TIMEOUTS = 1
    
    # Distance thresholds
    SHORT_YARDAGE = 3
    MEDIUM_YARDAGE = 7
    LONG_YARDAGE = 10
    
    # Quarters for special timing
    FIRST_HALF_QUARTERS = [1, 2]
    SECOND_HALF_QUARTERS = [3, 4] 
    CRUNCH_TIME_QUARTERS = [2, 4]  # Quarters with two-minute warnings


# =============================================================================
# DESIGNER-FRIENDLY CONFIGURATION
# =============================================================================

class DesignerConfig:
    """
    High-level configuration settings that designers can easily adjust
    to change overall game pacing and feel.
    """
    
    # Overall game pacing multiplier (1.0 = normal, 0.8 = faster, 1.2 = slower)
    GAME_PACE_MULTIPLIER = 1.0
    
    # How much strategies should differ from each other (0.0 = identical, 1.0 = full difference)
    STRATEGY_DIFFERENTIATION = 1.0
    
    # How much game situation should affect timing (0.0 = no effect, 1.0 = full effect)
    SITUATIONAL_IMPACT = 1.0
    
    # Target number of plays per game (adjusts all base times proportionally)
    TARGET_PLAYS_PER_GAME = 135  # Reduced by 10% from 150 to decrease play count
    
    @classmethod
    def apply_global_adjustments(cls, base_time: int) -> int:
        """Apply global designer adjustments to any timing value."""
        adjusted = base_time * cls.GAME_PACE_MULTIPLIER
        
        # Adjust based on target play count
        current_target = 150  # Current baseline
        if cls.TARGET_PLAYS_PER_GAME != current_target:
            # Inversely proportional: more plays = less time per play
            adjustment_factor = current_target / cls.TARGET_PLAYS_PER_GAME
            adjusted *= adjustment_factor
            
        return int(round(adjusted))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_effective_play_type(play_type: str, completion_status: str = None) -> str:
    """
    Convert play type and completion status into effective play type for timing lookup.
    
    Args:
        play_type: Base play type ('run', 'pass', 'kick', 'punt')
        completion_status: For passes ('complete', 'incomplete', 'touchdown', 'interception')
        
    Returns:
        Effective play type for timing calculations
    """
    if play_type == 'pass' and completion_status:
        if completion_status in ['complete', 'touchdown']:
            return 'pass_complete'
        elif completion_status in ['incomplete', 'interception']:
            return 'pass_incomplete'
        else:
            return 'pass_complete'  # Default to complete
    
    return play_type


def calculate_situational_adjustment(game_context: Dict[str, Any], archetype: str = 'balanced') -> int:
    """
    Calculate total situational timing adjustment based on game context.
    
    Args:
        game_context: Dictionary with game situation data
        archetype: Coaching archetype name
        
    Returns:
        Total adjustment in seconds (positive = slower, negative = faster)
    """
    quarter = game_context.get('quarter', 1)
    clock = game_context.get('clock', 900)
    score_differential = game_context.get('score_differential', 0)
    down = game_context.get('down', 1)
    distance = game_context.get('distance', 10)
    field_position = game_context.get('field_position', 20)
    timeouts_remaining = game_context.get('timeouts_remaining', 3)
    
    adjustment = 0
    
    # Score differential adjustments
    if score_differential > SituationalAdjustments.LARGE_LEAD:
        adjustment += SituationalAdjustments.LEADING_LARGE_ADJUSTMENT
    elif score_differential > SituationalAdjustments.SMALL_LEAD:
        adjustment += SituationalAdjustments.LEADING_SMALL_ADJUSTMENT
    elif score_differential < -SituationalAdjustments.LARGE_LEAD:
        adjustment += SituationalAdjustments.TRAILING_LARGE_ADJUSTMENT
    elif score_differential < -SituationalAdjustments.SMALL_LEAD:
        adjustment += SituationalAdjustments.TRAILING_SMALL_ADJUSTMENT
    
    # Fourth quarter urgency
    if quarter == 4:
        if clock < SituationalAdjustments.FINAL_FIVE_MINUTES:
            if score_differential > SituationalAdjustments.SMALL_LEAD:
                adjustment += SituationalAdjustments.FOURTH_QUARTER_LEAD_ADJUSTMENT
            elif score_differential < -SituationalAdjustments.SMALL_LEAD:
                adjustment += SituationalAdjustments.FOURTH_QUARTER_TRAIL_ADJUSTMENT
    
    # Two-minute warning
    if quarter in GameContextThresholds.CRUNCH_TIME_QUARTERS and clock <= SituationalAdjustments.TWO_MINUTE_WARNING:
        if score_differential <= 0:  # Need to score
            adjustment += SituationalAdjustments.TWO_MINUTE_DRILL_ADJUSTMENT
            if timeouts_remaining == GameContextThresholds.NO_TIMEOUTS:
                adjustment += SituationalAdjustments.NO_TIMEOUTS_ADJUSTMENT
    
    # Down and distance
    if down >= 3 and distance > GameContextThresholds.LONG_YARDAGE:
        adjustment += SituationalAdjustments.THIRD_DOWN_LONG_ADJUSTMENT
    elif down == 1 and distance == 10:
        adjustment += SituationalAdjustments.FIRST_DOWN_ADJUSTMENT
    
    # Field position
    if field_position >= SituationalAdjustments.RED_ZONE:
        adjustment += SituationalAdjustments.RED_ZONE_ADJUSTMENT
    
    # Apply situational impact multiplier
    adjustment = int(adjustment * DesignerConfig.SITUATIONAL_IMPACT)
    
    return adjustment