"""
Test suite for date utilities and helper functions.

Tests date arithmetic operations, formatting functions,
parsing utilities, and date-related helper methods.
"""

import pytest
from datetime import date as PyDate, timedelta
from typing import List, Tuple

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.calendar.date_models import (
    Date, DateAdvanceResult, normalize_date, days_between, is_valid_date
)
from src.calendar.calendar_exceptions import InvalidDateException


class TestDateArithmetic:
    """Test date arithmetic operations and calculations."""

    def test_basic_date_addition(self):
        """Test basic date addition operations."""
        date = Date(2024, 1, 15)

        # Test adding single day
        next_day = date.add_days(1)
        assert next_day == Date(2024, 1, 16)

        # Test adding multiple days
        week_later = date.add_days(7)
        assert week_later == Date(2024, 1, 22)

        # Test adding days across month boundary
        month_boundary = Date(2024, 1, 30)
        next_month = month_boundary.add_days(5)
        assert next_month == Date(2024, 2, 4)

    def test_date_subtraction(self):
        """Test date subtraction operations."""
        date = Date(2024, 1, 15)

        # Test subtracting single day
        prev_day = date.subtract_days(1)
        assert prev_day == Date(2024, 1, 14)

        # Test subtracting multiple days
        week_earlier = date.subtract_days(7)
        assert week_earlier == Date(2024, 1, 8)

        # Test subtracting across month boundary
        month_start = Date(2024, 2, 5)
        prev_month = month_start.subtract_days(10)
        assert prev_month == Date(2024, 1, 26)

    def test_negative_day_addition(self):
        """Test adding negative days (equivalent to subtraction)."""
        date = Date(2024, 3, 15)

        # Adding negative days should subtract
        result = date.add_days(-10)
        expected = date.subtract_days(10)
        assert result == expected
        assert result == Date(2024, 3, 5)

    def test_leap_year_arithmetic(self):
        """Test date arithmetic across leap year boundaries."""
        # 2024 is a leap year
        leap_date = Date(2024, 2, 28)

        # Add one day to Feb 28 in leap year
        next_day = leap_date.add_days(1)
        assert next_day == Date(2024, 2, 29)

        # Add two days to Feb 28 in leap year
        two_days = leap_date.add_days(2)
        assert two_days == Date(2024, 3, 1)

        # Test February in non-leap year (2023)
        non_leap_date = Date(2023, 2, 28)
        next_day_non_leap = non_leap_date.add_days(1)
        assert next_day_non_leap == Date(2023, 3, 1)

    def test_year_boundary_arithmetic(self):
        """Test date arithmetic across year boundaries."""
        year_end = Date(2024, 12, 30)

        # Add days to cross year boundary
        new_year = year_end.add_days(5)
        assert new_year == Date(2025, 1, 4)

        # Subtract days to cross year boundary backwards
        year_start = Date(2024, 1, 3)
        prev_year = year_start.subtract_days(5)
        assert prev_year == Date(2023, 12, 29)

    def test_large_date_operations(self):
        """Test operations with large numbers of days."""
        start_date = Date(2024, 1, 1)

        # Add a full year (365 days for 2024 which is a leap year)
        year_later = start_date.add_days(366)  # 2024 has 366 days
        assert year_later == Date(2025, 1, 1)

        # Subtract a full year
        year_earlier = start_date.subtract_days(365)  # 2023 has 365 days
        assert year_earlier == Date(2023, 1, 1)


class TestDateComparisons:
    """Test date comparison operations."""

    def test_date_equality(self):
        """Test date equality comparisons."""
        date1 = Date(2024, 6, 15)
        date2 = Date(2024, 6, 15)
        date3 = Date(2024, 6, 16)

        assert date1 == date2
        assert not (date1 == date3)
        assert date1 != date3

    def test_date_ordering(self):
        """Test date ordering comparisons."""
        early_date = Date(2024, 1, 15)
        middle_date = Date(2024, 6, 15)
        late_date = Date(2024, 12, 15)

        # Test less than
        assert early_date < middle_date
        assert middle_date < late_date
        assert early_date < late_date

        # Test greater than
        assert late_date > middle_date
        assert middle_date > early_date
        assert late_date > early_date

        # Test less than or equal
        assert early_date <= middle_date
        assert early_date <= early_date

        # Test greater than or equal
        assert late_date >= middle_date
        assert late_date >= late_date

    def test_cross_year_comparisons(self):
        """Test comparisons across year boundaries."""
        dec_2023 = Date(2023, 12, 31)
        jan_2024 = Date(2024, 1, 1)

        assert dec_2023 < jan_2024
        assert jan_2024 > dec_2023
        assert not (dec_2023 == jan_2024)


class TestDateUtilityFunctions:
    """Test utility functions for date operations."""

    def test_days_between_calculation(self):
        """Test days_between utility function."""
        start = Date(2024, 1, 1)
        end = Date(2024, 1, 8)

        # Test positive difference
        days = days_between(start, end)
        assert days == 7

        # Test negative difference (end before start)
        days_reverse = days_between(end, start)
        assert days_reverse == -7

        # Test same dates
        days_same = days_between(start, start)
        assert days_same == 0

    def test_days_between_with_different_input_types(self):
        """Test days_between with different input types."""
        date_obj = Date(2024, 6, 15)
        py_date = PyDate(2024, 6, 20)
        date_string = "2024-06-25"

        # Date to PyDate
        days1 = days_between(date_obj, py_date)
        assert days1 == 5

        # PyDate to Date
        days2 = days_between(py_date, date_obj)
        assert days2 == -5

        # Date to string
        days3 = days_between(date_obj, date_string)
        assert days3 == 10

        # String to Date
        days4 = days_between(date_string, date_obj)
        assert days4 == -10

    def test_days_until_method(self):
        """Test the days_until method on Date objects."""
        start = Date(2024, 3, 1)
        end = Date(2024, 3, 15)

        days = start.days_until(end)
        assert days == 14

        # Test reverse (negative days)
        days_reverse = end.days_until(start)
        assert days_reverse == -14

    def test_normalize_date_function(self):
        """Test the normalize_date utility function."""
        # Test with Date object (should return same object)
        date_obj = Date(2024, 5, 20)
        normalized1 = normalize_date(date_obj)
        assert normalized1 == date_obj
        assert isinstance(normalized1, Date)

        # Test with Python date
        py_date = PyDate(2024, 5, 20)
        normalized2 = normalize_date(py_date)
        assert normalized2 == Date(2024, 5, 20)
        assert isinstance(normalized2, Date)

        # Test with string
        date_string = "2024-05-20"
        normalized3 = normalize_date(date_string)
        assert normalized3 == Date(2024, 5, 20)
        assert isinstance(normalized3, Date)

        # Test with invalid input
        with pytest.raises(ValueError, match="Cannot convert"):
            normalize_date(123)

    def test_is_valid_date_function(self):
        """Test the is_valid_date utility function."""
        # Test valid dates
        assert is_valid_date(2024, 1, 1) == True
        assert is_valid_date(2024, 12, 31) == True
        assert is_valid_date(2024, 2, 29) == True  # Leap year

        # Test invalid dates
        assert is_valid_date(2024, 2, 30) == False  # Feb 30 doesn't exist
        assert is_valid_date(2024, 13, 1) == False  # Month 13 doesn't exist
        assert is_valid_date(2024, 1, 32) == False  # January 32 doesn't exist
        assert is_valid_date(2023, 2, 29) == False  # 2023 is not a leap year

        # Test edge cases
        assert is_valid_date(2024, 4, 31) == False  # April only has 30 days
        assert is_valid_date(2024, 4, 30) == True   # April 30 is valid


class TestDateFormatting:
    """Test date formatting and string representation."""

    def test_date_string_representation(self):
        """Test Date object string representation."""
        date = Date(2024, 7, 4)

        # Test __str__ method
        str_repr = str(date)
        assert str_repr == "2024-07-04"

        # Test __repr__ method
        repr_str = repr(date)
        assert repr_str == "Date(2024, 7, 4)"

    def test_date_format_method(self):
        """Test Date format method with different format strings."""
        date = Date(2024, 7, 4)

        # Test default format (YYYY-MM-DD)
        default_format = date.format()
        assert default_format == "2024-07-04"

        # Test DD/MM/YYYY format
        uk_format = date.format("%d/%m/%Y")
        assert uk_format == "04/07/2024"

        # Test full month name format
        full_format = date.format("%B %d, %Y")
        assert full_format == "July 04, 2024"

        # Test unsupported format (should return string representation)
        unsupported = date.format("%A, %B %d, %Y")
        assert unsupported == "2024-07-04"

    def test_date_parsing_formats(self):
        """Test parsing dates from different string formats."""
        # Test YYYY-MM-DD format
        date1 = Date.from_string("2024-07-04")
        assert date1 == Date(2024, 7, 4)

        # Test DD/MM/YYYY format
        date2 = Date.from_string("04/07/2024", "%d/%m/%Y")
        assert date2 == Date(2024, 7, 4)

        # Test invalid format string
        with pytest.raises(ValueError, match="Unsupported date format"):
            Date.from_string("July 4, 2024", "%B %d, %Y")

        # Test malformed date string
        with pytest.raises(ValueError, match="Cannot parse date string"):
            Date.from_string("not-a-date")


class TestLeapYearUtilities:
    """Test leap year detection and handling."""

    def test_leap_year_detection(self):
        """Test leap year detection method."""
        # Test leap years
        leap_2024 = Date(2024, 1, 1)
        assert leap_2024.is_leap_year() == True

        leap_2000 = Date(2000, 1, 1)
        assert leap_2000.is_leap_year() == True

        # Test non-leap years
        non_leap_2023 = Date(2023, 1, 1)
        assert non_leap_2023.is_leap_year() == False

        non_leap_1900 = Date(1900, 1, 1)
        assert non_leap_1900.is_leap_year() == False

        # Test century years (special case)
        non_leap_1900 = Date(1900, 1, 1)
        assert non_leap_1900.is_leap_year() == False  # Divisible by 100 but not 400

        leap_2000 = Date(2000, 1, 1)
        assert leap_2000.is_leap_year() == True  # Divisible by 400

    def test_february_in_leap_years(self):
        """Test February handling in leap vs non-leap years."""
        # Test leap year February
        leap_feb = Date(2024, 2, 29)
        assert leap_feb.is_leap_year() == True

        # Test adding days across leap February
        feb_28_leap = Date(2024, 2, 28)
        march_1_leap = feb_28_leap.add_days(2)
        assert march_1_leap == Date(2024, 3, 1)

        # Test non-leap year February
        feb_28_non_leap = Date(2023, 2, 28)
        march_1_non_leap = feb_28_non_leap.add_days(1)
        assert march_1_non_leap == Date(2023, 3, 1)


class TestDateAdvanceResult:
    """Test DateAdvanceResult utility class."""

    def test_date_advance_result_creation(self):
        """Test creation of DateAdvanceResult objects."""
        start = Date(2024, 1, 15)
        end = Date(2024, 1, 25)
        days = 10

        result = DateAdvanceResult(
            start_date=start,
            end_date=end,
            days_advanced=days
        )

        assert result.start_date == start
        assert result.end_date == end
        assert result.days_advanced == days
        assert result.advancement_id is not None
        assert result.timestamp is not None

    def test_date_advance_result_validation(self):
        """Test validation in DateAdvanceResult."""
        start = Date(2024, 1, 15)
        end = Date(2024, 1, 25)

        # Test with correct days
        result = DateAdvanceResult(
            start_date=start,
            end_date=end,
            days_advanced=10
        )
        assert result.days_advanced == 10

        # Test with negative days (should raise error)
        with pytest.raises(ValueError, match="Days advanced cannot be negative"):
            DateAdvanceResult(
                start_date=start,
                end_date=end,
                days_advanced=-5
            )

        # Test with mismatched end date
        wrong_end = Date(2024, 1, 20)  # Only 5 days, not 10
        with pytest.raises(ValueError, match="End date.*does not match"):
            DateAdvanceResult(
                start_date=start,
                end_date=wrong_end,
                days_advanced=10
            )

    def test_duration_description(self):
        """Test duration description generation."""
        start = Date(2024, 1, 1)

        # Test various durations
        test_cases = [
            (0, "No time advanced"),
            (1, "1 day"),
            (5, "5 days"),
            (7, "1 week"),
            (14, "2 weeks"),
            (10, "1 week and 3 days"),
            (17, "2 weeks and 3 days"),
            (100, "100 days")
        ]

        for days, expected_description in test_cases:
            end = start.add_days(days)
            result = DateAdvanceResult(
                start_date=start,
                end_date=end,
                days_advanced=days
            )
            assert result.duration_description == expected_description

    def test_date_advance_result_string_representation(self):
        """Test string representation of DateAdvanceResult."""
        start = Date(2024, 6, 1)
        end = Date(2024, 6, 8)
        result = DateAdvanceResult(
            start_date=start,
            end_date=end,
            days_advanced=7
        )

        str_repr = str(result)
        assert "Advanced from 2024-06-01 to 2024-06-08" in str_repr
        assert "1 week" in str_repr


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions in date utilities."""

    def test_month_boundary_edge_cases(self):
        """Test edge cases around month boundaries."""
        # Test months with different day counts
        months_30_days = [4, 6, 9, 11]  # April, June, September, November
        months_31_days = [1, 3, 5, 7, 8, 10, 12]  # Jan, Mar, May, Jul, Aug, Oct, Dec

        for month in months_30_days:
            last_day = Date(2024, month, 30)
            next_day = last_day.add_days(1)
            expected_month = month + 1 if month < 12 else 1
            expected_year = 2024 if month < 12 else 2025
            assert next_day == Date(expected_year, expected_month, 1)

        for month in months_31_days:
            last_day = Date(2024, month, 31)
            next_day = last_day.add_days(1)
            expected_month = month + 1 if month < 12 else 1
            expected_year = 2024 if month < 12 else 2025
            assert next_day == Date(expected_year, expected_month, 1)

    def test_february_edge_cases(self):
        """Test February-specific edge cases."""
        # Test leap year February 29
        feb_29_leap = Date(2024, 2, 29)
        march_1 = feb_29_leap.add_days(1)
        assert march_1 == Date(2024, 3, 1)

        # Test going backwards from March 1 in leap year
        march_1_leap = Date(2024, 3, 1)
        feb_29 = march_1_leap.subtract_days(1)
        assert feb_29 == Date(2024, 2, 29)

        # Test going backwards from March 1 in non-leap year
        march_1_non_leap = Date(2023, 3, 1)
        feb_28 = march_1_non_leap.subtract_days(1)
        assert feb_28 == Date(2023, 2, 28)

    def test_invalid_date_edge_cases(self):
        """Test edge cases with invalid dates."""
        # Test boundary values
        with pytest.raises(InvalidDateException):
            Date(2024, 0, 15)  # Month 0

        with pytest.raises(InvalidDateException):
            Date(2024, 13, 15)  # Month 13

        with pytest.raises(InvalidDateException):
            Date(2024, 1, 0)  # Day 0

        with pytest.raises(InvalidDateException):
            Date(2024, 1, 32)  # Day 32 in January

    def test_large_date_calculations(self):
        """Test calculations with very large date differences."""
        start = Date(2000, 1, 1)
        end = Date(2050, 1, 1)

        # Calculate 50 years difference
        days_diff = start.days_until(end)
        # 50 years * 365.25 days/year ≈ 18263 days
        assert 18200 <= days_diff <= 18300  # Approximate range

        # Test adding large number of days
        far_future = start.add_days(10000)
        assert far_future.year > 2025


if __name__ == "__main__":
    pytest.main([__file__, "-v"])