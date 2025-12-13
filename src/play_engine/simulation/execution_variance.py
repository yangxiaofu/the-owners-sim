"""
Execution Variance - Play Outcome Randomness

Applies realistic execution variance to play outcomes based on play complexity.
Real NFL games have unpredictability - elite QBs throw bad interceptions, poor WRs
make circus catches. This module models that variance.

Variance Levels:
- Simple plays (dive, quick slant): ±5% variance
- Medium plays (standard routes): ±8% variance
- Complex plays (deep post, four verts): ±12% variance

Usage:
    # Apply variance to completion rate
    adjusted_rate = apply_execution_variance(0.65, play_concept="deep_post")

    # Apply variance to all parameters
    params = {"completion_rate": 0.65, "avg_yards": 12.5}
    params = apply_variance_to_params(params, play_concept="deep_post")
"""

import random
from typing import Dict, Optional


# Play complexity determines variance level
VARIANCE_BY_COMPLEXITY = {
    "simple": 0.05,      # ±5% for dive, quick slant, screen
    "medium": 0.08,      # ±8% for standard routes (most plays)
    "complex": 0.12      # ±12% for deep post, four verts, fade
}

# Map play concepts to complexity
# Simple: Highly predictable, low-risk plays
# Complex: High-difficulty, high-variance plays
# Default: Medium complexity (not explicitly mapped)
PLAY_COMPLEXITY = {
    # Simple plays (±5% variance)
    "dive": "simple",
    "quick_slant": "simple",
    "screen": "simple",
    "hb_toss": "simple",
    "hb_dive": "simple",
    "quick_out": "simple",
    "bubble_screen": "simple",

    # Complex plays (±12% variance)
    "deep_post": "complex",
    "four_verticals": "complex",
    "deep_comeback": "complex",
    "fade": "complex",
    "go_route": "complex",
    "deep_crossing": "complex",
    "corner_route": "complex",
    "double_move": "complex",

    # Medium complexity (±8% variance) - Default
    # Standard routes: slant, out, curl, hook, drag, etc.
}


def get_play_complexity(play_concept: Optional[str]) -> str:
    """
    Get complexity level for play concept.

    Args:
        play_concept: Play concept name (e.g., "deep_post", "dive")

    Returns:
        Complexity level: "simple", "medium", or "complex"
    """
    if play_concept is None:
        return "medium"
    return PLAY_COMPLEXITY.get(play_concept, "medium")


def apply_execution_variance(base_value: float, play_concept: Optional[str] = None,
                             complexity: Optional[str] = None) -> float:
    """
    Apply execution variance to success rate, yards, etc.

    Uses Gaussian distribution to model natural variance in play execution.
    Simple plays are more predictable (lower variance), complex plays are less
    predictable (higher variance).

    Args:
        base_value: Base success rate, yards, etc. (0.0-1.0 for rates, any for yards)
        play_concept: Play concept name (optional, auto-determines complexity)
        complexity: Override complexity level ("simple", "medium", "complex")

    Returns:
        Adjusted value with Gaussian variance applied

    Examples:
        >>> # 65% completion rate on deep post (complex) - could vary ±12%
        >>> apply_execution_variance(0.65, play_concept="deep_post")
        0.58  # (example output, actual varies)

        >>> # 85% completion rate on quick slant (simple) - only varies ±5%
        >>> apply_execution_variance(0.85, play_concept="quick_slant")
        0.87  # (example output, more stable)
    """
    # Determine complexity
    if complexity is None:
        complexity = get_play_complexity(play_concept) if play_concept else "medium"

    variance = VARIANCE_BY_COMPLEXITY.get(complexity, 0.08)

    # Apply Gaussian variance (mean=base_value, std=base_value * variance)
    # This creates a bell curve centered on base_value with spread determined by variance
    adjusted = random.gauss(base_value, base_value * variance)

    # For rates (0.0-1.0), clamp to valid range
    # For yards, allow negative variance (rare bad execution, fumbles)
    if 0.0 <= base_value <= 1.0:
        adjusted = max(0.0, min(1.0, adjusted))

    return adjusted


def apply_variance_to_params(params: Dict, play_concept: Optional[str]) -> Dict:
    """
    Apply execution variance to all relevant play parameters.

    Modifies completion_rate, avg_yards, sack_rate, etc. in-place using the
    play concept's complexity level.

    Args:
        params: Dictionary of play parameters to modify
        play_concept: Play concept name for complexity determination

    Returns:
        Modified params dictionary (modified in-place and returned)

    Example:
        >>> params = {"completion_rate": 0.65, "avg_yards": 12.5, "sack_rate": 0.08}
        >>> apply_variance_to_params(params, "deep_post")
        {'completion_rate': 0.58, 'avg_yards': 11.2, 'sack_rate': 0.09}
    """
    complexity = get_play_complexity(play_concept)

    # Apply variance to success rates
    if "completion_rate" in params:
        params["completion_rate"] = apply_execution_variance(
            params["completion_rate"], complexity=complexity
        )

    if "sack_rate" in params:
        params["sack_rate"] = apply_execution_variance(
            params["sack_rate"], complexity=complexity
        )

    if "interception_rate" in params:
        params["interception_rate"] = apply_execution_variance(
            params["interception_rate"], complexity=complexity
        )

    # Apply variance to yards (can be negative for fumbles/sacks)
    if "avg_yards" in params:
        params["avg_yards"] = apply_execution_variance(
            params["avg_yards"], complexity=complexity
        )

    if "yards_after_catch" in params:
        params["yards_after_catch"] = apply_execution_variance(
            params["yards_after_catch"], complexity=complexity
        )

    # Also apply to air yards and YAC (used by pass_play_config.json)
    if "avg_air_yards" in params:
        params["avg_air_yards"] = apply_execution_variance(
            params["avg_air_yards"], complexity=complexity
        )

    if "avg_yac" in params:
        params["avg_yac"] = apply_execution_variance(
            params["avg_yac"], complexity=complexity
        )

    return params


def can_upset_occur(base_probability: float, complexity: str = "medium") -> bool:
    """
    Check if execution variance causes an upset (low-probability event succeeds).

    This allows 10% success rate plays to occasionally succeed, and 90% success
    rate plays to occasionally fail.

    Args:
        base_probability: Base success probability (0.0-1.0)
        complexity: Play complexity ("simple", "medium", "complex")

    Returns:
        True if variance-adjusted roll succeeds

    Example:
        >>> # 10% success rate play with variance can occasionally succeed
        >>> can_upset_occur(0.10, complexity="complex")  # Has chance to return True
    """
    adjusted_probability = apply_execution_variance(base_probability, complexity=complexity)
    return random.random() < adjusted_probability
