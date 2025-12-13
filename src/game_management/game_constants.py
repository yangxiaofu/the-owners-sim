"""
Game Constants for NFL Simulation

Central location for all magic numbers and strings used in game simulation.
This avoids scattered magic values and makes tuning/configuration easier.
"""
from enum import Enum


# =============================================================================
# FIELD POSITION CONSTANTS
# =============================================================================

DEFAULT_TOUCHBACK_YARD_LINE = 25  # Standard touchback starting position
FIRST_DOWN_DISTANCE = 10  # Standard yards needed for first down
FOURTH_DOWN = 4  # Fourth down number
PAT_FIELD_POSITION = 98  # PAT spot: opponent's 2-yard line (98 on 0-100 scale)
PAT_KICK_FIELD_POSITION = 83  # PAT kick position: results in 33-yard attempt


# =============================================================================
# SCORING CONSTANTS
# =============================================================================

TOUCHDOWN_POINTS = 6
FIELD_GOAL_POINTS = 3
SAFETY_POINTS = 2
EXTRA_POINT_POINTS = 1


# =============================================================================
# TIME CONSTANTS
# =============================================================================

QUARTER_DURATION_SECONDS = 900  # 15 minutes per quarter
REGULATION_QUARTERS = 4  # Standard 4 quarters in regulation
PAT_TIME_SECONDS = 3  # Time consumed by PAT attempt
TWO_MINUTES_SECONDS = 120
FIVE_MINUTES_SECONDS = 300
TEN_MINUTES_SECONDS = 600
GAME_DURATION_MINUTES = 240  # 4 hours typical game duration


# =============================================================================
# PLAY THRESHOLD CONSTANTS
# =============================================================================

BIG_PLAY_THRESHOLD_YARDS = 20  # Yards for a play to be considered "big"
SACK_THRESHOLD_YARDS = -3  # Minimum yard loss to be considered a sack


# =============================================================================
# CLUTCH FACTOR CONSTANTS
# =============================================================================

CLOSE_GAME_POINT_THRESHOLD = 7  # Within 7 points = close game
FOURTH_QUARTER_CLOSE_THRESHOLD = 8  # 4th quarter within 8 points = high pressure
FOURTH_QUARTER_MODERATE_THRESHOLD = 10  # 4th quarter within 10 points = moderate
FOURTH_QUARTER_PRESSURE_THRESHOLD = 14  # 4th quarter within 14 points = some pressure


class ClutchPressure:
    """Clutch pressure multiplier values for different game situations."""
    NONE = 0.0
    LOW = 0.3
    MODERATE = 0.4
    HIGH = 0.7
    MAXIMUM = 1.0


# =============================================================================
# CROWD NOISE CONSTANTS
# =============================================================================

HOME_OFFENSE_BASE_NOISE = 30  # Crowd quiet when home team on offense
AWAY_OFFENSE_BASE_NOISE = 60  # Crowd loud when away team on offense
CROWD_LEAD_BONUS = 10  # Extra noise when home team is winning
CROWD_FOURTH_QUARTER_BONUS = 10  # Extra noise in close 4th quarter games
MAX_CROWD_NOISE = 100  # Maximum crowd noise level


# =============================================================================
# WEATHER CONSTANTS
# =============================================================================

class WeatherCondition(Enum):
    """Weather conditions affecting gameplay."""
    CLEAR = "clear"
    RAIN = "rain"
    HEAVY_WIND = "heavy_wind"
    SNOW = "snow"


# Cumulative probability thresholds for weather selection
# clear: 60%, rain: 20%, heavy_wind: 15%, snow: 5%
WEATHER_PROBABILITY_CLEAR = 0.60
WEATHER_PROBABILITY_RAIN = 0.80  # 0.60-0.80 = 20%
WEATHER_PROBABILITY_WIND = 0.95  # 0.80-0.95 = 15%
# snow = 1.0 - 0.95 = 5%


# =============================================================================
# PRIMETIME CONSTANTS
# =============================================================================

PRIMETIME_VARIANCE = 0.15  # Additional outcome variance for primetime games


# =============================================================================
# PLAYBOOK CONSTANTS
# =============================================================================

DEFAULT_PLAYBOOK = "balanced"


# =============================================================================
# TEAM SIDE CONSTANTS
# =============================================================================

class TeamSide(Enum):
    """Identifies home vs away team."""
    HOME = "home"
    AWAY = "away"


# =============================================================================
# MOMENTUM EVENT CONSTANTS
# =============================================================================

class MomentumEvent(Enum):
    """Events that affect team momentum."""
    TOUCHDOWN = "touchdown"
    TURNOVER_GAIN = "turnover_gain"
    TURNOVER_LOSS = "turnover_loss"
    BIG_PLAY_GAIN = "big_play_gain"
    SACK = "sack"
    FIELD_GOAL_MADE = "field_goal_made"
    FIELD_GOAL_BLOCKED = "field_goal_blocked"


# =============================================================================
# PAT OUTCOME CONSTANTS
# =============================================================================

class PATOutcome(Enum):
    """Possible outcomes for Point After Touchdown attempts."""
    MADE = "extra_point_made"
    MISSED = "extra_point_missed"


# =============================================================================
# FORMATION CONSTANTS
# =============================================================================

class SpecialTeamsFormation(Enum):
    """Special teams formations."""
    FIELD_GOAL = "FIELD_GOAL"
    FIELD_GOAL_BLOCK = "FIELD_GOAL_BLOCK"
