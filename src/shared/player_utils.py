"""
Player Utility Functions

Shared utility functions for player data processing and calculations.
"""

from datetime import date
from typing import Optional


def calculate_player_age(birthdate: str, current_date: str) -> int:
    """
    Calculate player age from birthdate and current game date.

    Uses accurate date arithmetic to determine age, accounting for whether
    the player's birthday has occurred yet in the current year.

    Args:
        birthdate: Player birthdate in "YYYY-MM-DD" format (e.g., "1992-03-10")
        current_date: Current simulation date in "YYYY-MM-DD" format (e.g., "2025-09-04")

    Returns:
        Age in years (integer)

    Examples:
        >>> calculate_player_age("1992-03-10", "2025-09-04")
        33
        >>> calculate_player_age("1992-09-10", "2025-09-04")
        32  # Birthday hasn't happened yet this year
        >>> calculate_player_age("1999-12-31", "2025-01-01")
        25  # Birthday just passed

    Raises:
        ValueError: If date strings are in invalid format

    Notes:
        - Leap years are handled automatically by datetime
        - Age is calculated as: current_year - birth_year, minus 1 if birthday hasn't occurred
        - Returns 0 if birthdate is in the future (edge case)
    """
    try:
        # Parse date strings manually (avoids calendar module import conflict)
        # Expected format: "YYYY-MM-DD"
        birth_parts = birthdate.split('-')
        current_parts = current_date.split('-')

        if len(birth_parts) != 3 or len(current_parts) != 3:
            raise ValueError("Date must be in YYYY-MM-DD format")

        # Create date objects using date() constructor (avoids strptime's calendar dependency)
        birth_date_obj = date(int(birth_parts[0]), int(birth_parts[1]), int(birth_parts[2]))
        current_date_obj = date(int(current_parts[0]), int(current_parts[1]), int(current_parts[2]))

        # Calculate age
        age = current_date_obj.year - birth_date_obj.year

        # Adjust if birthday hasn't occurred yet this year
        # Check if current month/day is before birth month/day
        if (current_date_obj.month, current_date_obj.day) < (birth_date_obj.month, birth_date_obj.day):
            age -= 1

        # Edge case: birthdate is in the future
        if age < 0:
            return 0

        return age

    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid date format: {e}. Expected YYYY-MM-DD format.")


def estimate_age_from_years_pro(years_pro: int, rookie_age: int = 22) -> int:
    """
    Estimate player age from years of professional experience.

    Fallback method for players without birthdate data.
    Assumes average rookie age of 22 years old.

    Args:
        years_pro: Number of years player has been in NFL
        rookie_age: Assumed rookie age (default: 22)

    Returns:
        Estimated age in years

    Examples:
        >>> estimate_age_from_years_pro(0)
        22  # Rookie
        >>> estimate_age_from_years_pro(5)
        27  # 5th year player
        >>> estimate_age_from_years_pro(10)
        32  # 10th year veteran

    Notes:
        - This is an ESTIMATE and less accurate than birthdate calculation
        - Real rookies range from 21-24 years old typically
        - Use calculate_player_age() when birthdate is available
    """
    return rookie_age + years_pro


def get_player_age(
    birthdate: Optional[str] = None,
    current_date: Optional[str] = None,
    years_pro: int = 0,
    rookie_age: int = 22
) -> int:
    """
    Get player age using birthdate if available, otherwise estimate from years_pro.

    Convenience method that automatically chooses the best age calculation method
    based on available data.

    Args:
        birthdate: Player birthdate in "YYYY-MM-DD" format (optional)
        current_date: Current simulation date in "YYYY-MM-DD" format (optional)
        years_pro: Years of professional experience (fallback)
        rookie_age: Assumed rookie age for estimation (default: 22)

    Returns:
        Player age in years

    Examples:
        >>> get_player_age(birthdate="1992-03-10", current_date="2025-09-04")
        33  # Uses accurate birthdate calculation
        >>> get_player_age(years_pro=5)
        27  # Falls back to estimation
        >>> get_player_age()
        22  # Default rookie age

    Notes:
        - Prefers birthdate calculation when both dates are provided
        - Falls back to years_pro estimation if birthdate missing
        - Safe to call with missing data (returns sensible defaults)
    """
    if birthdate and current_date:
        try:
            return calculate_player_age(birthdate, current_date)
        except ValueError:
            # If birthdate parsing fails, fall back to estimation
            pass

    # Fallback to years_pro estimation
    return estimate_age_from_years_pro(years_pro, rookie_age)
