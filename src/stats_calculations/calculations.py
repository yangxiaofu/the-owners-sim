"""
Statistical Calculation Functions for The Owner's Sim

Pure functions for complex NFL statistical calculations.
All functions handle edge cases (division by zero, invalid inputs).
"""


def calculate_passer_rating(
    completions: int, attempts: int, yards: int, touchdowns: int, interceptions: int
) -> float:
    """
    Calculate NFL passer rating using official formula.

    Formula:
    - Component A: ((completions/attempts) - 0.3) * 5
    - Component B: ((yards/attempts) - 3) * 0.25
    - Component C: (touchdowns/attempts) * 20
    - Component D: 2.375 - ((interceptions/attempts) * 25)

    Each component clamped to [0.0, 2.375]
    Rating = ((A + B + C + D) / 6) * 100
    Clamped to [0.0, 158.3] (perfect rating)

    Args:
        completions: Pass completions
        attempts: Pass attempts
        yards: Passing yards
        touchdowns: Passing TDs
        interceptions: Interceptions thrown

    Returns:
        Passer rating (0.0 - 158.3)
    """
    # Edge case: no attempts
    if attempts == 0:
        return 0.0

    # Calculate each component
    # Component A: Completion percentage component
    comp_percentage = completions / attempts
    a = ((comp_percentage - 0.3) * 5)

    # Component B: Yards per attempt component
    yards_per_attempt = yards / attempts
    b = ((yards_per_attempt - 3) * 0.25)

    # Component C: Touchdown percentage component
    td_percentage = touchdowns / attempts
    c = (td_percentage * 20)

    # Component D: Interception percentage component
    int_percentage = interceptions / attempts
    d = 2.375 - (int_percentage * 25)

    # Clamp each component to [0.0, 2.375]
    a = max(0.0, min(2.375, a))
    b = max(0.0, min(2.375, b))
    c = max(0.0, min(2.375, c))
    d = max(0.0, min(2.375, d))

    # Calculate final rating
    rating = ((a + b + c + d) / 6) * 100

    # Clamp to [0.0, 158.3] (perfect rating)
    rating = max(0.0, min(158.3, rating))

    return round(rating, 1)


def calculate_yards_per_carry(yards: int, attempts: int) -> float:
    """
    Calculate rushing yards per carry (safe division).

    Args:
        yards: Rushing yards
        attempts: Rushing attempts

    Returns:
        Yards per carry (0.0 if no attempts)
    """
    return safe_divide(yards, attempts, default=0.0)


def calculate_catch_rate(receptions: int, targets: int) -> float:
    """
    Calculate catch rate percentage (0-100).

    Args:
        receptions: Number of receptions
        targets: Number of targets

    Returns:
        Catch rate percentage (0-100)
    """
    if targets == 0:
        return 0.0
    return round((receptions / targets) * 100, 1)


def calculate_yards_per_reception(yards: int, receptions: int) -> float:
    """
    Calculate yards per reception.

    Args:
        yards: Receiving yards
        receptions: Number of receptions

    Returns:
        Yards per reception (0.0 if no receptions)
    """
    return safe_divide(yards, receptions, default=0.0)


def calculate_yards_per_attempt(yards: int, attempts: int) -> float:
    """
    Calculate yards per attempt.

    Args:
        yards: Total yards (passing or rushing)
        attempts: Total attempts

    Returns:
        Yards per attempt (0.0 if no attempts)
    """
    return safe_divide(yards, attempts, default=0.0)


def calculate_fg_percentage(made: int, attempted: int) -> float:
    """
    Calculate field goal percentage (0-100).

    Args:
        made: Field goals made
        attempted: Field goals attempted

    Returns:
        Field goal percentage (0-100)
    """
    if attempted == 0:
        return 0.0
    return round((made / attempted) * 100, 1)


def calculate_xp_percentage(made: int, attempted: int) -> float:
    """
    Calculate extra point percentage (0-100).

    Args:
        made: Extra points made
        attempted: Extra points attempted

    Returns:
        Extra point percentage (0-100)
    """
    if attempted == 0:
        return 0.0
    return round((made / attempted) * 100, 1)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide, returning default if denominator is 0.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is 0

    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    result = numerator / denominator
    return round(result, 1)
