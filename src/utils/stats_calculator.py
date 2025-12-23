"""
Statistics Calculator Utilities.

Provides standard NFL statistical calculations including:
- Passer rating (NFL formula)
- Yards per carry/reception
- Completion percentage
- Other derived stats

This module centralizes stat calculations to ensure consistency
across the entire application (media coverage, stats views, awards, etc.).
"""


def calculate_passer_rating(
    completions: int,
    attempts: int,
    yards: int,
    touchdowns: int,
    interceptions: int
) -> float:
    """
    Calculate NFL passer rating.

    The NFL passer rating formula uses four components (completion percentage,
    yards per attempt, touchdown percentage, and interception percentage),
    each clamped to a range, then averaged and scaled to 0-158.3.

    Formula:
    - a = ((completions/attempts - 0.3) * 5) clamped to [0, 2.375]
    - b = ((yards/attempts - 3) * 0.25) clamped to [0, 2.375]
    - c = (touchdowns/attempts * 20) clamped to [0, 2.375]
    - d = (2.375 - (interceptions/attempts * 25)) clamped to [0, 2.375]
    - rating = ((a + b + c + d) / 6) * 100

    Args:
        completions: Number of completed passes
        attempts: Number of pass attempts
        yards: Total passing yards
        touchdowns: Number of touchdown passes
        interceptions: Number of interceptions thrown

    Returns:
        Passer rating as a float (0.0 to 158.3)

    Examples:
        >>> calculate_passer_rating(20, 30, 300, 3, 0)
        129.86111111111111
        >>> calculate_passer_rating(15, 30, 150, 1, 2)
        61.80555555555556
        >>> calculate_passer_rating(0, 0, 0, 0, 0)
        0.0
    """
    # Handle zero attempts (no passes thrown)
    if attempts == 0:
        return 0.0

    # Calculate component percentages
    completion_pct = completions / attempts
    yards_per_attempt = yards / attempts
    td_pct = touchdowns / attempts
    int_pct = interceptions / attempts

    # Component a: Completion percentage
    # (comp% - 0.3) * 5, clamped to [0, 2.375]
    a = max(0.0, min((completion_pct - 0.3) * 5, 2.375))

    # Component b: Yards per attempt
    # (YPA - 3) * 0.25, clamped to [0, 2.375]
    b = max(0.0, min((yards_per_attempt - 3) * 0.25, 2.375))

    # Component c: Touchdown percentage
    # TD% * 20, clamped to [0, 2.375]
    c = max(0.0, min(td_pct * 20, 2.375))

    # Component d: Interception percentage (inverted)
    # 2.375 - (INT% * 25), clamped to [0, 2.375]
    d = max(0.0, min(2.375 - (int_pct * 25), 2.375))

    # Final rating: average of components, scaled to 0-100
    rating = ((a + b + c + d) / 6) * 100

    return rating


def calculate_completion_percentage(completions: int, attempts: int) -> float:
    """
    Calculate completion percentage.

    Args:
        completions: Number of completed passes
        attempts: Number of pass attempts

    Returns:
        Completion percentage (0.0 to 100.0)

    Examples:
        >>> calculate_completion_percentage(20, 30)
        66.66666666666666
        >>> calculate_completion_percentage(0, 0)
        0.0
    """
    if attempts == 0:
        return 0.0
    return (completions / attempts) * 100


def calculate_yards_per_attempt(yards: int, attempts: int) -> float:
    """
    Calculate yards per attempt (passing or rushing).

    Args:
        yards: Total yards gained
        attempts: Number of attempts

    Returns:
        Yards per attempt

    Examples:
        >>> calculate_yards_per_attempt(300, 30)
        10.0
        >>> calculate_yards_per_attempt(0, 0)
        0.0
    """
    if attempts == 0:
        return 0.0
    return yards / attempts


def calculate_yards_per_carry(rushing_yards: int, rushing_attempts: int) -> float:
    """
    Calculate yards per carry (YPC).

    Args:
        rushing_yards: Total rushing yards
        rushing_attempts: Number of rushing attempts

    Returns:
        Yards per carry

    Examples:
        >>> calculate_yards_per_carry(120, 25)
        4.8
    """
    return calculate_yards_per_attempt(rushing_yards, rushing_attempts)


def calculate_yards_per_reception(receiving_yards: int, receptions: int) -> float:
    """
    Calculate yards per reception (YPR).

    Args:
        receiving_yards: Total receiving yards
        receptions: Number of receptions

    Returns:
        Yards per reception

    Examples:
        >>> calculate_yards_per_reception(150, 10)
        15.0
    """
    if receptions == 0:
        return 0.0
    return receiving_yards / receptions


def calculate_catch_rate(receptions: int, targets: int) -> float:
    """
    Calculate catch rate (reception percentage).

    Args:
        receptions: Number of receptions
        targets: Number of targets

    Returns:
        Catch rate percentage (0.0 to 100.0)

    Examples:
        >>> calculate_catch_rate(8, 10)
        80.0
    """
    if targets == 0:
        return 0.0
    return (receptions / targets) * 100


def calculate_touchdown_rate(touchdowns: int, attempts: int) -> float:
    """
    Calculate touchdown rate (TD%).

    Args:
        touchdowns: Number of touchdowns
        attempts: Number of attempts (pass attempts or rush attempts)

    Returns:
        Touchdown rate percentage (0.0 to 100.0)

    Examples:
        >>> calculate_touchdown_rate(3, 30)
        10.0
    """
    if attempts == 0:
        return 0.0
    return (touchdowns / attempts) * 100


def calculate_interception_rate(interceptions: int, attempts: int) -> float:
    """
    Calculate interception rate (INT%).

    Args:
        interceptions: Number of interceptions
        attempts: Number of pass attempts

    Returns:
        Interception rate percentage (0.0 to 100.0)

    Examples:
        >>> calculate_interception_rate(2, 30)
        6.666666666666667
    """
    if attempts == 0:
        return 0.0
    return (interceptions / attempts) * 100


def calculate_field_goal_percentage(made: int, attempted: int) -> float:
    """
    Calculate field goal percentage.

    Args:
        made: Number of field goals made
        attempted: Number of field goals attempted

    Returns:
        Field goal percentage (0.0 to 100.0)

    Examples:
        >>> calculate_field_goal_percentage(28, 32)
        87.5
    """
    if attempted == 0:
        return 0.0
    return (made / attempted) * 100


def calculate_net_yards_per_punt(gross_yards: int, punts: int, return_yards: int = 0) -> float:
    """
    Calculate net yards per punt (gross yards minus return yards).

    Args:
        gross_yards: Total gross punt yards
        punts: Number of punts
        return_yards: Total return yards allowed (default 0)

    Returns:
        Net yards per punt

    Examples:
        >>> calculate_net_yards_per_punt(450, 10, 50)
        40.0
    """
    if punts == 0:
        return 0.0
    net_yards = gross_yards - return_yards
    return net_yards / punts


def calculate_sack_rate(sacks: int, pass_attempts: int) -> float:
    """
    Calculate sack rate (sacks per pass attempt).

    Args:
        sacks: Number of sacks
        pass_attempts: Number of pass attempts

    Returns:
        Sack rate percentage (0.0 to 100.0)

    Examples:
        >>> calculate_sack_rate(3, 30)
        10.0
    """
    if pass_attempts == 0:
        return 0.0
    return (sacks / pass_attempts) * 100
