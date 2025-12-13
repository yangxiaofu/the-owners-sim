"""
Penalty Enforcement Calculator - Pure functions for NFL penalty ball placement.

This module provides a single source of truth for all penalty enforcement logic,
implementing realistic NFL rules including:
- Previous spot vs spot of foul enforcement
- Half-distance-to-goal calculations
- Automatic first down handling
- Accept/decline decision logic
- Pre-snap vs during-play vs post-play penalties

All functions are pure (no side effects) for easy unit testing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EnforcementSpot(Enum):
    """Where the penalty yardage is enforced from"""
    PREVIOUS_SPOT = "previous_spot"       # Most penalties - from line of scrimmage
    SPOT_OF_FOUL = "spot_of_foul"         # DPI, some personal fouls
    END_OF_RUN = "end_of_run"             # Personal fouls during run by offense
    SUCCEEDING_SPOT = "succeeding_spot"   # Dead ball fouls, post-play penalties


class PenaltyTiming(Enum):
    """When the penalty occurred relative to the play"""
    PRE_SNAP = "pre_snap"           # False start, encroachment, etc.
    DURING_PLAY = "during_play"     # Holding, DPI, etc.
    POST_PLAY = "post_play"         # Unsportsmanlike, taunting, etc.


@dataclass
class EnforcementResult:
    """
    Pure data output from penalty enforcement calculation.

    All ball placement information needed after a penalty.
    """
    new_yard_line: int              # 0-100 scale (own goal = 0, opp goal = 100)
    new_down: int                   # 1-4
    new_yards_to_go: int            # Distance to first down marker
    is_first_down: bool             # Did this result in a first down?
    enforcement_spot: EnforcementSpot
    penalty_accepted: bool          # Was the penalty accepted?
    yards_enforced: int             # Actual yards assessed (may differ from base due to half-distance)
    replay_down: bool               # Should the down be replayed?

    # Additional context for logging
    penalty_description: str = ""   # Human-readable description


# Penalty configuration - which penalties use which enforcement rules
PENALTY_CONFIG = {
    # Pre-snap penalties (dead ball, replay down)
    "false_start": {
        "base_yards": 5,
        "is_offensive": True,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "delay_of_game": {
        "base_yards": 5,
        "is_offensive": True,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "illegal_formation": {
        "base_yards": 5,
        "is_offensive": True,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "encroachment": {
        "base_yards": 5,
        "is_offensive": False,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "offsides": {
        "base_yards": 5,
        "is_offensive": False,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "neutral_zone_infraction": {
        "base_yards": 5,
        "is_offensive": False,
        "timing": PenaltyTiming.PRE_SNAP,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },

    # During-play offensive penalties
    "offensive_holding": {
        "base_yards": 10,
        "is_offensive": True,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "illegal_block_in_back": {
        "base_yards": 10,
        "is_offensive": True,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "offensive_pass_interference": {
        "base_yards": 10,
        "is_offensive": True,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": False,
        "negates_play": True,
    },
    "intentional_grounding": {
        "base_yards": 10,  # Plus loss of down
        "is_offensive": True,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.SPOT_OF_FOUL,
        "automatic_first_down": False,
        "negates_play": True,
        "loss_of_down": True,
    },

    # During-play defensive penalties
    "defensive_holding": {
        "base_yards": 5,
        "is_offensive": False,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
    "illegal_contact": {
        "base_yards": 5,
        "is_offensive": False,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
    "defensive_pass_interference": {
        "base_yards": 0,  # Spot foul - variable yardage
        "is_offensive": False,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.SPOT_OF_FOUL,
        "automatic_first_down": True,
        "negates_play": False,
        "is_spot_foul": True,
    },

    # Post-play penalties
    "unsportsmanlike_conduct": {
        "base_yards": 15,
        "is_offensive": None,  # Can be either team
        "timing": PenaltyTiming.POST_PLAY,
        "enforcement_spot": EnforcementSpot.SUCCEEDING_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
    "face_mask": {
        "base_yards": 15,
        "is_offensive": None,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
    "unnecessary_roughness": {
        "base_yards": 15,
        "is_offensive": None,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
    "roughing_the_passer": {
        "base_yards": 15,
        "is_offensive": False,
        "timing": PenaltyTiming.DURING_PLAY,
        "enforcement_spot": EnforcementSpot.PREVIOUS_SPOT,
        "automatic_first_down": True,
        "negates_play": False,
    },
}


def calculate_half_distance_yards(
    base_yards: int,
    current_yard_line: int,
    is_offensive_penalty: bool
) -> int:
    """
    Calculate actual penalty yards considering half-distance-to-goal rule.

    NFL Rule: If the penalty would move the ball more than half the distance
    to the goal line, the ball is placed half the distance to the goal instead.

    Args:
        base_yards: Normal penalty yardage (positive value)
        current_yard_line: Current ball position (0-100, 0=own goal, 100=opp goal)
        is_offensive_penalty: True if penalty is against the offense

    Returns:
        Actual yards to enforce (always positive)
    """
    if is_offensive_penalty:
        # Ball moves toward own goal line (yard_line decreases)
        # Distance to own goal = current_yard_line
        distance_to_goal = current_yard_line
    else:
        # Ball moves toward opponent goal line (yard_line increases)
        # Distance to opponent goal = 100 - current_yard_line
        distance_to_goal = 100 - current_yard_line

    half_distance = distance_to_goal // 2

    # Can't enforce more than half the distance, but at least 1 yard
    if base_yards > half_distance:
        return max(1, half_distance)
    return base_yards


def calculate_enforcement(
    penalty_type: str,
    pre_snap_yard_line: int,
    pre_snap_down: int,
    pre_snap_distance: int,
    play_yards: int = 0,
    is_offensive_penalty: Optional[bool] = None,
    spot_of_foul: Optional[int] = None,
    automatic_first_down: Optional[bool] = None,
    custom_yards: Optional[int] = None,
) -> EnforcementResult:
    """
    Calculate ball placement after a penalty using NFL enforcement rules.

    This is a pure function with no side effects - perfect for unit testing.

    Args:
        penalty_type: Type of penalty (e.g., "offensive_holding", "false_start")
        pre_snap_yard_line: Ball position before the play (0-100)
        pre_snap_down: Down before the play (1-4)
        pre_snap_distance: Yards to first down before the play
        play_yards: Yards gained on the play (before penalty)
        is_offensive_penalty: Override for penalty direction (None uses config)
        spot_of_foul: Yard line where penalty occurred (for spot fouls like DPI)
        automatic_first_down: Override for auto first down (None uses config)
        custom_yards: Override penalty yards (None uses config)

    Returns:
        EnforcementResult with complete ball placement information
    """
    # Get penalty configuration
    config = PENALTY_CONFIG.get(penalty_type, {})

    base_yards = custom_yards if custom_yards is not None else config.get("base_yards", 5)
    is_offensive = is_offensive_penalty if is_offensive_penalty is not None else config.get("is_offensive", True)
    timing = config.get("timing", PenaltyTiming.DURING_PLAY)
    enforcement_spot_type = config.get("enforcement_spot", EnforcementSpot.PREVIOUS_SPOT)
    auto_first_down = automatic_first_down if automatic_first_down is not None else config.get("automatic_first_down", False)
    negates_play = config.get("negates_play", False)
    is_spot_foul = config.get("is_spot_foul", False)
    loss_of_down = config.get("loss_of_down", False)

    # Determine enforcement spot yard line
    if is_spot_foul and spot_of_foul is not None:
        enforcement_yard_line = spot_of_foul
    elif enforcement_spot_type == EnforcementSpot.SUCCEEDING_SPOT:
        # Post-play penalties: enforce from where the play ended
        enforcement_yard_line = min(100, max(0, pre_snap_yard_line + play_yards))
    elif enforcement_spot_type == EnforcementSpot.END_OF_RUN:
        enforcement_yard_line = min(100, max(0, pre_snap_yard_line + play_yards))
    else:
        # Previous spot (most common)
        enforcement_yard_line = pre_snap_yard_line

    # Calculate actual yards with half-distance rule
    actual_yards = calculate_half_distance_yards(
        base_yards, enforcement_yard_line, is_offensive
    )

    # Calculate new yard line
    if is_offensive:
        # Offensive penalty: move ball backward (decrease yard line)
        new_yard_line = max(1, enforcement_yard_line - actual_yards)
    else:
        # Defensive penalty: move ball forward (increase yard line)
        new_yard_line = min(99, enforcement_yard_line + actual_yards)

    # Handle spot fouls (like DPI) - ball goes to spot of foul
    if is_spot_foul and spot_of_foul is not None:
        new_yard_line = spot_of_foul
        actual_yards = spot_of_foul - pre_snap_yard_line

    # Determine down and distance
    replay_down = False
    is_first_down = False

    if timing == PenaltyTiming.PRE_SNAP or negates_play:
        # Pre-snap or play-negating: replay the down
        replay_down = True
        new_down = pre_snap_down

        if is_offensive:
            # Offensive penalty: add yards to distance
            new_yards_to_go = pre_snap_distance + actual_yards
        else:
            # Defensive penalty: subtract yards from distance
            new_yards_to_go = max(1, pre_snap_distance - actual_yards)
            # Check if this gives a first down
            if new_yards_to_go <= 0 or auto_first_down:
                is_first_down = True
                new_down = 1
                new_yards_to_go = min(10, 100 - new_yard_line)
    else:
        # During-play or post-play without negation
        if auto_first_down:
            is_first_down = True
            new_down = 1
            new_yards_to_go = min(10, 100 - new_yard_line)
        else:
            # Normal down progression based on original play
            play_end_yard_line = pre_snap_yard_line + play_yards

            if is_offensive:
                # For offensive penalties, we need to recalculate from penalty spot
                new_yards_to_go = pre_snap_distance + actual_yards
                new_down = pre_snap_down  # Replay down for offensive penalties during play
                replay_down = True
            else:
                # Defensive penalty: add yards to play result
                total_yards = play_yards + actual_yards

                # Check if original play + penalty achieves first down
                if total_yards >= pre_snap_distance:
                    is_first_down = True
                    new_down = 1
                    new_yards_to_go = min(10, 100 - new_yard_line)
                else:
                    # Continue with next down
                    new_down = min(4, pre_snap_down + 1)
                    new_yards_to_go = pre_snap_distance - total_yards

    # Handle loss of down (e.g., intentional grounding)
    if loss_of_down and not replay_down:
        new_down = min(4, new_down + 1)

    # Ensure yards_to_go is at least 1 and handles goal-to-go
    if new_yard_line + new_yards_to_go > 100:
        new_yards_to_go = 100 - new_yard_line  # Goal-to-go
    new_yards_to_go = max(1, new_yards_to_go)

    # Build description
    direction = "against offense" if is_offensive else "against defense"
    desc = f"{penalty_type.replace('_', ' ').title()}, {actual_yards} yards {direction}"
    if auto_first_down and not is_offensive:
        desc += ", automatic first down"
    if replay_down:
        desc += ", replay down"

    return EnforcementResult(
        new_yard_line=new_yard_line,
        new_down=new_down,
        new_yards_to_go=new_yards_to_go,
        is_first_down=is_first_down,
        enforcement_spot=enforcement_spot_type,
        penalty_accepted=True,  # Will be overridden by should_accept_penalty
        yards_enforced=actual_yards,
        replay_down=replay_down,
        penalty_description=desc,
    )


def should_accept_penalty(
    penalty_type: str,
    pre_snap_yard_line: int,
    pre_snap_down: int,
    pre_snap_distance: int,
    play_yards: int,
    is_offensive_penalty: Optional[bool] = None,
    spot_of_foul: Optional[int] = None,
) -> tuple[bool, EnforcementResult, EnforcementResult]:
    """
    Determine whether a penalty should be accepted or declined.

    NFL Rule: The non-offending team chooses whether to accept the penalty
    or take the result of the play.

    Args:
        Same as calculate_enforcement, plus play_yards

    Returns:
        Tuple of (should_accept, accepted_result, declined_result)
    """
    # Calculate result if penalty is accepted
    accepted_result = calculate_enforcement(
        penalty_type=penalty_type,
        pre_snap_yard_line=pre_snap_yard_line,
        pre_snap_down=pre_snap_down,
        pre_snap_distance=pre_snap_distance,
        play_yards=play_yards,
        is_offensive_penalty=is_offensive_penalty,
        spot_of_foul=spot_of_foul,
    )

    # Calculate result if penalty is declined (play stands)
    play_end_yard_line = min(100, max(0, pre_snap_yard_line + play_yards))

    # Check if play achieved first down
    play_achieved_first_down = play_yards >= pre_snap_distance

    if play_achieved_first_down:
        declined_down = 1
        declined_distance = min(10, 100 - play_end_yard_line)
        declined_is_first_down = True
    else:
        declined_down = min(4, pre_snap_down + 1)
        declined_distance = max(1, pre_snap_distance - play_yards)
        declined_is_first_down = False

    declined_result = EnforcementResult(
        new_yard_line=play_end_yard_line,
        new_down=declined_down,
        new_yards_to_go=declined_distance,
        is_first_down=declined_is_first_down,
        enforcement_spot=EnforcementSpot.PREVIOUS_SPOT,
        penalty_accepted=False,
        yards_enforced=0,
        replay_down=False,
        penalty_description="Penalty declined",
    )

    # Decision logic: Accept if it results in better field position or down/distance
    config = PENALTY_CONFIG.get(penalty_type, {})
    is_offensive = is_offensive_penalty if is_offensive_penalty is not None else config.get("is_offensive", True)

    if is_offensive:
        # It's an offensive penalty - defense decides
        # Accept if penalty result is worse for offense than play result
        # (lower yard line OR worse down/distance situation)
        accept = (accepted_result.new_yard_line < declined_result.new_yard_line or
                  (accepted_result.new_yard_line == declined_result.new_yard_line and
                   accepted_result.new_yards_to_go > declined_result.new_yards_to_go))
    else:
        # It's a defensive penalty - offense decides
        # Accept if penalty result is better for offense than play result
        # (higher yard line OR better down/distance OR automatic first down)
        accept = (accepted_result.new_yard_line > declined_result.new_yard_line or
                  accepted_result.is_first_down and not declined_result.is_first_down or
                  (accepted_result.new_yard_line == declined_result.new_yard_line and
                   accepted_result.new_yards_to_go < declined_result.new_yards_to_go))

    # Update the accepted flag in results
    if accept:
        accepted_result.penalty_accepted = True
        return (True, accepted_result, declined_result)
    else:
        declined_result.penalty_accepted = False
        accepted_result.penalty_accepted = False
        return (False, accepted_result, declined_result)


def get_final_enforcement(
    penalty_type: str,
    pre_snap_yard_line: int,
    pre_snap_down: int,
    pre_snap_distance: int,
    play_yards: int,
    is_offensive_penalty: Optional[bool] = None,
    spot_of_foul: Optional[int] = None,
    force_accept: bool = False,
) -> EnforcementResult:
    """
    Get the final enforcement result after accept/decline decision.

    This is the main entry point for penalty enforcement - it handles
    the entire flow including the accept/decline decision.

    Args:
        Same as should_accept_penalty
        force_accept: Force acceptance (for pre-snap penalties that can't be declined)

    Returns:
        Final EnforcementResult to apply to the game state
    """
    config = PENALTY_CONFIG.get(penalty_type, {})
    timing = config.get("timing", PenaltyTiming.DURING_PLAY)
    negates_play = config.get("negates_play", False)

    # Pre-snap penalties are automatically enforced (no decline option)
    if timing == PenaltyTiming.PRE_SNAP or force_accept:
        return calculate_enforcement(
            penalty_type=penalty_type,
            pre_snap_yard_line=pre_snap_yard_line,
            pre_snap_down=pre_snap_down,
            pre_snap_distance=pre_snap_distance,
            play_yards=0,  # Play is negated
            is_offensive_penalty=is_offensive_penalty,
            spot_of_foul=spot_of_foul,
        )

    # For other penalties, determine accept/decline
    should_accept, accepted_result, declined_result = should_accept_penalty(
        penalty_type=penalty_type,
        pre_snap_yard_line=pre_snap_yard_line,
        pre_snap_down=pre_snap_down,
        pre_snap_distance=pre_snap_distance,
        play_yards=play_yards,
        is_offensive_penalty=is_offensive_penalty,
        spot_of_foul=spot_of_foul,
    )

    if should_accept:
        return accepted_result
    else:
        return declined_result
