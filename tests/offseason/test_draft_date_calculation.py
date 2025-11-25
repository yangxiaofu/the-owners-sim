"""Test NFL Draft date calculation."""

import pytest
from src.calendar.date_models import Date
from src.offseason.offseason_event_scheduler import OffseasonEventScheduler


def test_last_thursday_april_2015():
    """2015: April 30 (5th Thursday)."""
    scheduler = OffseasonEventScheduler()
    result = scheduler._calculate_last_thursday_april(2015)
    expected = Date(2015, 4, 30)
    assert result == expected, f"Expected {expected}, got {result}"


def test_last_thursday_april_2020():
    """2020: April 23 (4th Thursday)."""
    scheduler = OffseasonEventScheduler()
    result = scheduler._calculate_last_thursday_april(2020)
    expected = Date(2020, 4, 23)
    assert result == expected, f"Expected {expected}, got {result}"


def test_last_thursday_april_2021():
    """2021: April 29 (5th Thursday)."""
    scheduler = OffseasonEventScheduler()
    result = scheduler._calculate_last_thursday_april(2021)
    expected = Date(2021, 4, 29)
    assert result == expected, f"Expected {expected}, got {result}"


def test_last_thursday_april_2025():
    """2025: April 24 (4th Thursday)."""
    scheduler = OffseasonEventScheduler()
    result = scheduler._calculate_last_thursday_april(2025)
    expected = Date(2025, 4, 24)
    assert result == expected, f"Expected {expected}, got {result}"


def test_all_historical_dates():
    """Verify all historical dates from 2015-2025."""
    scheduler = OffseasonEventScheduler()

    # Historical NFL Draft dates (verified from research)
    expected_dates = {
        2015: Date(2015, 4, 30),
        2016: Date(2016, 4, 28),
        2017: Date(2017, 4, 27),
        2018: Date(2018, 4, 26),
        2019: Date(2019, 4, 25),
        2020: Date(2020, 4, 23),
        2021: Date(2021, 4, 29),
        2022: Date(2022, 4, 28),
        2023: Date(2023, 4, 27),
        2024: Date(2024, 4, 25),
        2025: Date(2025, 4, 24),
    }

    for year, expected in expected_dates.items():
        result = scheduler._calculate_last_thursday_april(year)
        assert result == expected, f"Year {year}: Expected {expected}, got {result}"


def test_all_are_thursdays():
    """Verify all calculated dates are actually Thursdays."""
    scheduler = OffseasonEventScheduler()

    # Test years 2015-2030
    for year in range(2015, 2031):
        result = scheduler._calculate_last_thursday_april(year)
        py_date = result.to_python_date()

        # Thursday is weekday 3 (Monday=0, Tuesday=1, Wednesday=2, Thursday=3, ...)
        assert py_date.weekday() == 3, f"Year {year}: {result} is not a Thursday (weekday={py_date.weekday()})"


def test_all_in_april():
    """Verify all calculated dates are in April."""
    scheduler = OffseasonEventScheduler()

    # Test years 2015-2030
    for year in range(2015, 2031):
        result = scheduler._calculate_last_thursday_april(year)
        assert result.month == 4, f"Year {year}: {result} is not in April (month={result.month})"


def test_is_last_thursday():
    """Verify calculated dates are the LAST Thursday (with 2020+ April 30 exception)."""
    scheduler = OffseasonEventScheduler()

    # Test years 2015-2030
    for year in range(2015, 2031):
        result = scheduler._calculate_last_thursday_april(year)

        # Check if there's a Thursday after this date in April
        # Try adding 7 days
        next_week = result.add_days(7)

        # Special case: Starting in 2020, NFL avoids April 30 for the draft
        # So for years >= 2020 where April 30 is Thursday, we use April 23 instead
        if year >= 2020 and result.day == 23:
            # Check if April 30 is a Thursday this year
            april_30 = Date(year, 4, 30)
            py_date = april_30.to_python_date()
            if py_date.weekday() == 3:  # April 30 is Thursday
                # This is expected - we use April 23 to avoid May spillover
                continue

        # For all other cases, verify this is the last Thursday
        # If next_week is still in April, then result is NOT the last Thursday
        assert next_week.month != 4, (
            f"Year {year}: {result} is not the last Thursday in April "
            f"(found Thursday {next_week} after it in April)"
        )
