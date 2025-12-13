"""
Grading Constants

Position-specific weights, thresholds, EPA lookup tables, and grade boundaries
for the PFF-style player grading system.
"""

from typing import Dict, Set

# =============================================================================
# GRADE BOUNDARIES
# =============================================================================

# Grade scale definitions
GRADE_ELITE = 90.0  # 90-100: Elite (top 5% of plays)
GRADE_ABOVE_AVERAGE = 80.0  # 80-89: Above Average (positive contribution)
GRADE_NEUTRAL = 60.0  # 60-79: Neutral (expected performance)
GRADE_BELOW_AVERAGE = 40.0  # 40-59: Below Average (negative contribution)
GRADE_POOR = 0.0  # 0-39: Poor (significant negative impact)

# Baseline grade (neutral play)
BASELINE_GRADE = 60.0

# Positive play threshold
POSITIVE_PLAY_THRESHOLD = 70.0

# Grade bounds
MIN_GRADE = 0.0
MAX_GRADE = 100.0


# =============================================================================
# POSITION GROUPS
# =============================================================================

# Offensive positions
OFFENSIVE_POSITIONS: Set[str] = {
    "QB",
    "RB",
    "FB",
    "WR",
    "TE",
    "LT",
    "LG",
    "C",
    "RG",
    "RT",
}

# Defensive positions
DEFENSIVE_POSITIONS: Set[str] = {
    "LE",
    "DT",
    "RE",
    "EDGE",
    "LOLB",
    "MLB",
    "ROLB",
    "CB",
    "FS",
    "SS",
}

# Special teams positions
SPECIAL_TEAMS_POSITIONS: Set[str] = {"K", "P", "LS", "KR", "PR"}

# Position group mappings
POSITION_GROUP_MAP: Dict[str, str] = {
    # Quarterbacks
    "QB": "QB",
    "QUARTERBACK": "QB",
    # Running backs
    "RB": "RB",
    "FB": "RB",
    "RUNNING_BACK": "RB",
    "FULLBACK": "RB",
    # Receivers
    "WR": "WR",
    "TE": "WR",  # TE uses similar grading to WR with blocking emphasis
    "WIDE_RECEIVER": "WR",
    "TIGHT_END": "WR",
    # Offensive line (abbreviations)
    "LT": "OL",
    "LG": "OL",
    "C": "OL",
    "RG": "OL",
    "RT": "OL",
    # Offensive line (full names - used by play engine)
    "LEFT_TACKLE": "OL",
    "LEFT_GUARD": "OL",
    "CENTER": "OL",
    "RIGHT_GUARD": "OL",
    "RIGHT_TACKLE": "OL",
    # Defensive line (abbreviations)
    "LE": "DL",
    "DT": "DL",
    "RE": "DL",
    "NT": "DL",
    "DE": "DL",
    "EDGE": "DL",
    # Defensive line (full names)
    "DEFENSIVE_END": "DL",
    "DEFENSIVE_TACKLE": "DL",
    "NOSE_TACKLE": "DL",
    # Linebackers (abbreviations)
    "LOLB": "LB",
    "MLB": "LB",
    "ROLB": "LB",
    "ILB": "LB",
    "OLB": "LB",
    # Linebackers (full names)
    "LINEBACKER": "LB",
    "INSIDE_LINEBACKER": "LB",
    "OUTSIDE_LINEBACKER": "LB",
    "MIKE_LINEBACKER": "LB",
    "SAM_LINEBACKER": "LB",
    "WILL_LINEBACKER": "LB",
    "MIDDLE_LINEBACKER": "LB",
    # Defensive backs (abbreviations)
    "CB": "DB",
    "FS": "DB",
    "SS": "DB",
    "NCB": "DB",
    # Defensive backs (full names)
    "CORNERBACK": "DB",
    "FREE_SAFETY": "DB",
    "STRONG_SAFETY": "DB",
    "SAFETY": "DB",
    "NICKEL_CORNERBACK": "DB",
    # Special teams
    "K": "ST",
    "P": "ST",
    "LS": "ST",
    "KR": "ST",
    "PR": "ST",
    "KICKER": "ST",
    "PUNTER": "ST",
    "LONG_SNAPPER": "ST",
}


# =============================================================================
# POSITION-SPECIFIC COMPONENT WEIGHTS
# =============================================================================

# Component weights must sum to 1.0 for each position group

QB_COMPONENT_WEIGHTS: Dict[str, float] = {
    "accuracy": 0.30,  # Completion quality, throw placement
    "decision": 0.25,  # Read progressions, avoiding mistakes
    "pocket_presence": 0.20,  # Avoiding pressure, extending plays
    "deep_ball": 0.15,  # Deep passing accuracy and touch
    "mobility": 0.10,  # Scrambling and rushing ability
}

RB_COMPONENT_WEIGHTS: Dict[str, float] = {
    "vision": 0.25,  # Finding holes, reading blocks
    "elusiveness": 0.25,  # Breaking tackles, making defenders miss
    "power": 0.20,  # Yards after contact, short yardage
    "pass_blocking": 0.15,  # Blitz pickup, chip blocks
    "receiving": 0.15,  # Route running, hands
}

WR_COMPONENT_WEIGHTS: Dict[str, float] = {
    "route_running": 0.25,  # Precision, timing, breaks
    "separation": 0.25,  # Getting open, creating space
    "contested_catches": 0.20,  # High-point catches, jump balls
    "blocking": 0.15,  # Run blocking, stalk blocking
    "yac": 0.15,  # Yards after catch ability
}

# TE has more emphasis on blocking than WR
TE_COMPONENT_WEIGHTS: Dict[str, float] = {
    "route_running": 0.20,
    "separation": 0.20,
    "contested_catches": 0.15,
    "blocking": 0.30,  # Higher blocking weight for TEs
    "yac": 0.15,
}

OL_COMPONENT_WEIGHTS: Dict[str, float] = {
    "pass_blocking": 0.45,  # Pass protection
    "run_blocking": 0.45,  # Run blocking
    "penalties": 0.10,  # Penalty avoidance (negative impact)
}

DL_COMPONENT_WEIGHTS: Dict[str, float] = {
    "pass_rush": 0.40,  # Getting to the QB
    "run_defense": 0.40,  # Stopping the run
    "versatility": 0.20,  # Ability to do both well
}

LB_COMPONENT_WEIGHTS: Dict[str, float] = {
    "coverage": 0.30,  # Pass coverage ability
    "tackling": 0.30,  # Tackling efficiency
    "blitzing": 0.20,  # Pass rush when blitzing
    "run_fits": 0.20,  # Gap discipline, run defense
}

DB_COMPONENT_WEIGHTS: Dict[str, float] = {
    "coverage": 0.40,  # Man and zone coverage
    "ball_skills": 0.25,  # Interceptions, pass breakups
    "tackling": 0.20,  # Tackling in space
    "zone_awareness": 0.15,  # Reading routes, zone discipline
}

ST_COMPONENT_WEIGHTS: Dict[str, float] = {
    "accuracy": 0.50,  # FG accuracy or punt placement
    "distance": 0.30,  # FG distance or punt yardage
    "clutch": 0.20,  # Performance in critical situations
}

# Master mapping of position groups to weights
POSITION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "QB": QB_COMPONENT_WEIGHTS,
    "RB": RB_COMPONENT_WEIGHTS,
    "WR": WR_COMPONENT_WEIGHTS,
    "TE": TE_COMPONENT_WEIGHTS,
    "OL": OL_COMPONENT_WEIGHTS,
    "DL": DL_COMPONENT_WEIGHTS,
    "LB": LB_COMPONENT_WEIGHTS,
    "DB": DB_COMPONENT_WEIGHTS,
    "ST": ST_COMPONENT_WEIGHTS,
    "K": ST_COMPONENT_WEIGHTS,
    "P": ST_COMPONENT_WEIGHTS,
}


# =============================================================================
# CONTEXT MODIFIERS
# =============================================================================

# Context modifiers adjust grades based on game situation

CONTEXT_MODIFIERS: Dict[str, float] = {
    # Clutch situations (4th quarter, close game within 8 points)
    "clutch": 1.10,
    # Red zone (inside opponent's 20-yard line)
    "red_zone": 1.05,
    # Critical downs (3rd and 4th down)
    "critical_down": 1.05,
    # Garbage time (4th quarter, score differential > 21)
    "garbage_time": 0.90,
    # Goal line (inside 5-yard line)
    "goal_line": 1.08,
    # Two-minute warning situations
    "two_minute": 1.07,
}


# =============================================================================
# EPA (EXPECTED POINTS ADDED) LOOKUP TABLE
# =============================================================================

# EPA values by field position (yard line from own goal)
# Based on historical NFL data approximations
EPA_BY_YARD_LINE: Dict[int, float] = {
    # Own territory (negative/low EP)
    1: -1.50,
    5: -1.20,
    10: -0.80,
    15: -0.50,
    20: -0.30,
    25: -0.10,
    30: 0.10,
    35: 0.30,
    40: 0.50,
    45: 0.80,
    50: 1.00,
    # Opponent territory (increasing EP)
    55: 1.30,
    60: 1.60,
    65: 2.00,
    70: 2.50,
    75: 3.00,
    80: 3.50,
    85: 4.20,
    90: 5.00,
    95: 5.80,
    99: 6.50,
}

# Down multipliers for EPA calculation
# 1st down has highest EP, decreases as downs progress
EPA_DOWN_MULTIPLIER: Dict[int, float] = {
    1: 1.00,
    2: 0.90,
    3: 0.70,
    4: 0.30,
}


# =============================================================================
# SUCCESS RATE THRESHOLDS
# =============================================================================

# Percentage of yards to go that must be gained for a "successful" play
SUCCESS_RATE_THRESHOLDS: Dict[int, float] = {
    1: 0.40,  # 1st down: gain 40% of yards to go
    2: 0.50,  # 2nd down: gain 50% of yards to go
    3: 1.00,  # 3rd down: must convert (100%)
    4: 1.00,  # 4th down: must convert (100%)
}


# =============================================================================
# GRADE ADJUSTMENTS FOR SPECIFIC OUTCOMES
# =============================================================================

# Adjustments to baseline grade for specific play outcomes

# QB-specific adjustments
QB_ADJUSTMENTS: Dict[str, float] = {
    "completion_short": 12.0,  # 0-9 air yards
    "completion_intermediate": 18.0,  # 10-19 air yards
    "completion_deep": 25.0,  # 20+ air yards
    "incompletion": -10.0,
    "interception": -30.0,
    "sack_taken": -10.0,
    "sack_avoided_under_pressure": 15.0,
    "touchdown_pass": 10.0,  # Additional bonus
    "dropped_pass": 5.0,  # Credit for good throw
    "pressure_completion": 10.0,  # Completing under pressure
}

# RB-specific adjustments
RB_ADJUSTMENTS: Dict[str, float] = {
    "positive_yards": 10.0,  # 1-3 yards
    "chunk_play": 18.0,  # 4-9 yards
    "explosive_play": 25.0,  # 10+ yards
    "negative_yards": -12.0,
    "fumble": -25.0,
    "touchdown_rush": 10.0,
    "broken_tackle": 8.0,
    "yards_after_contact_bonus": 5.0,  # Per 2+ YAC
}

# WR/TE-specific adjustments
WR_ADJUSTMENTS: Dict[str, float] = {
    "catch_short": 10.0,
    "catch_intermediate": 15.0,
    "catch_deep": 22.0,
    "catch_contested": 12.0,  # Additional for contested
    "drop": -15.0,
    "fumble": -25.0,
    "touchdown_catch": 10.0,
    "yac_bonus": 5.0,  # Per 5+ YAC
    "pancake_block": 12.0,
}

# OL-specific adjustments
OL_ADJUSTMENTS: Dict[str, float] = {
    "clean_pocket": 8.0,
    "pancake": 15.0,
    "downfield_block": 10.0,
    "double_team_success": 8.0,
    "pressure_allowed": -10.0,
    "hurry_allowed": -5.0,
    "sack_allowed": -25.0,
    "holding_penalty": -20.0,
    "false_start": -15.0,
}

# DL-specific adjustments
DL_ADJUSTMENTS: Dict[str, float] = {
    "sack": 25.0,
    "qb_hit": 15.0,
    "qb_pressure": 10.0,
    "tackle_for_loss": 18.0,
    "run_stuff": 12.0,  # Stop at or behind line
    "missed_tackle": -15.0,
    "blown_assignment": -12.0,
}

# LB-specific adjustments
LB_ADJUSTMENTS: Dict[str, float] = {
    "solo_tackle": 10.0,
    "assisted_tackle": 5.0,
    "tackle_for_loss": 15.0,
    "sack": 22.0,
    "pass_defended": 15.0,
    "interception": 25.0,
    "forced_fumble": 20.0,
    "coverage_success": 12.0,  # Tight coverage, no catch
    "missed_tackle": -15.0,
    "coverage_bust": -18.0,
}

# DB-specific adjustments
DB_ADJUSTMENTS: Dict[str, float] = {
    "pass_defended": 18.0,
    "interception": 28.0,
    "solo_tackle": 8.0,
    "forced_fumble": 20.0,
    "coverage_tight": 10.0,  # Coverage without allowing catch
    "touchdown_allowed": -25.0,
    "big_play_allowed": -15.0,  # 20+ yard play
    "missed_tackle": -18.0,
    "pass_interference": -20.0,
}


# =============================================================================
# MINIMUM SNAP THRESHOLDS
# =============================================================================

# Minimum snaps required to qualify for rankings
MIN_SNAPS_FOR_GAME_GRADE = 5
MIN_SNAPS_FOR_SEASON_RANKING = 100
MIN_GAMES_FOR_SEASON_RANKING = 4

# Minimum snaps per game to qualify for grade leaders (dynamic: weeks_played * this value)
# Requires ~20 snaps per game average to appear in leaderboards
MIN_SNAPS_PER_GAME_FOR_LEADERS = 20


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_position_group(position: str) -> str:
    """Get the position group for a given position."""
    return POSITION_GROUP_MAP.get(position.upper(), "UNKNOWN")


def get_component_weights(position: str) -> Dict[str, float]:
    """Get component weights for a position."""
    group = get_position_group(position)
    return POSITION_WEIGHTS.get(group, {})


def is_offensive_position(position: str) -> bool:
    """Check if a position is an offensive position."""
    return position.upper() in OFFENSIVE_POSITIONS


def is_defensive_position(position: str) -> bool:
    """Check if a position is a defensive position."""
    return position.upper() in DEFENSIVE_POSITIONS


def clamp_grade(grade: float) -> float:
    """Clamp a grade to valid bounds (0-100)."""
    return max(MIN_GRADE, min(MAX_GRADE, grade))


def get_grade_tier(grade: float) -> str:
    """Get the tier name for a grade value."""
    if grade >= GRADE_ELITE:
        return "Elite"
    elif grade >= GRADE_ABOVE_AVERAGE:
        return "Above Average"
    elif grade >= GRADE_NEUTRAL:
        return "Average"
    elif grade >= GRADE_BELOW_AVERAGE:
        return "Below Average"
    else:
        return "Poor"
