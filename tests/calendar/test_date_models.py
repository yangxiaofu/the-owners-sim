"""
Unit tests for Calendar Date Models

Tests for Date class, DateAdvanceResult, and related utility functions.
Covers basic functionality, edge cases, and error conditions.
"""

import pytest
from datetime import date as PyDate, datetime

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.calendar.date_models import (
    Date, DateAdvanceResult, normalize_date, days_between, is_valid_date
)
from src.calendar.calendar_exceptions import InvalidDateException


class TestDate:
    """Test cases for the Date class."""

    def test_date_creation_valid(self):
        """Test creating valid dates."""
        date = Date(2024, 1, 15)
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 15

    def test_date_creation_invalid(self):
        """Test creating invalid dates raises InvalidDateException."""
        with pytest.raises(InvalidDateException, match="Invalid date"):
            Date(2024, 2, 30)  # February 30th doesn't exist

        with pytest.raises(InvalidDateException, match="Invalid date"):
            Date(2024, 13, 1)  # Month 13 doesn't exist

        with pytest.raises(InvalidDateException, match="Invalid date"):
            Date(2024, 1, 32)  # January 32nd doesn't exist

    def test_date_from_python_date(self):
        """Test creating Date from Python date object."""
        py_date = PyDate(2024, 3, 15)
        date = Date.from_python_date(py_date)
        assert date.year == 2024
        assert date.month == 3
        assert date.day == 15

    def test_date_today(self):
        """Test creating Date from today."""
        today = Date.today()
        py_today = PyDate.today()
        assert today.year == py_today.year
        assert today.month == py_today.month
        assert today.day == py_today.day

    def test_date_from_string(self):
        """Test creating Date from string."""
        date = Date.from_string("2024-05-15")
        assert date.year == 2024
        assert date.month == 5
        assert date.day == 15

        # Test custom format
        date = Date.from_string("15/05/2024", "%d/%m/%Y")
        assert date.year == 2024
        assert date.month == 5
        assert date.day == 15

    def test_date_from_string_invalid(self):
        """Test creating Date from invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse date string"):
            Date.from_string("invalid-date")

        with pytest.raises(InvalidDateException, match="Invalid date"):
            Date.from_string("2024-13-01")  # Invalid month

    def test_date_to_python_date(self):
        """Test converting Date to Python date."""
        date = Date(2024, 6, 20)
        py_date = date.to_python_date()
        assert isinstance(py_date, PyDate)
        assert py_date.year == 2024
        assert py_date.month == 6
        assert py_date.day == 20

    def test_date_add_days(self):
        """Test adding days to a date."""
        date = Date(2024, 1, 15)

        # Add positive days
        new_date = date.add_days(10)
        assert new_date == Date(2024, 1, 25)

        # Add days crossing month boundary
        new_date = date.add_days(20)
        assert new_date == Date(2024, 2, 4)

        # Add days crossing year boundary
        date = Date(2023, 12, 25)
        new_date = date.add_days(10)
        assert new_date == Date(2024, 1, 4)

        # Add negative days (going backwards)
        date = Date(2024, 2, 10)
        new_date = date.add_days(-15)
        assert new_date == Date(2024, 1, 26)

    def test_date_subtract_days(self):
        """Test subtracting days from a date."""
        date = Date(2024, 2, 15)
        new_date = date.subtract_days(10)
        assert new_date == Date(2024, 2, 5)

        # Cross month boundary
        new_date = date.subtract_days(20)
        assert new_date == Date(2024, 1, 26)

    def test_date_days_until(self):
        """Test calculating days between dates."""
        start_date = Date(2024, 1, 1)
        end_date = Date(2024, 1, 11)

        assert start_date.days_until(end_date) == 10
        assert end_date.days_until(start_date) == -10

        # Same date
        assert start_date.days_until(start_date) == 0

    def test_date_is_leap_year(self):
        """Test leap year detection."""
        assert Date(2024, 1, 1).is_leap_year()  # 2024 is leap year
        assert not Date(2023, 1, 1).is_leap_year()  # 2023 is not
        assert Date(2000, 1, 1).is_leap_year()  # 2000 is leap year
        assert not Date(1900, 1, 1).is_leap_year()  # 1900 is not (century rule)

    def test_date_format(self):
        """Test date formatting."""
        date = Date(2024, 3, 5)

        # Default format
        assert date.format() == "2024-03-05"

        # Custom format
        assert date.format("%d/%m/%Y") == "05/03/2024"
        assert date.format("%B %d, %Y") == "March 05, 2024"

    def test_date_string_representation(self):
        """Test string representations of Date."""
        date = Date(2024, 1, 5)

        assert str(date) == "2024-01-05"
        assert repr(date) == "Date(2024, 1, 5)"

    def test_date_comparisons(self):
        """Test date comparison operations."""
        date1 = Date(2024, 1, 1)
        date2 = Date(2024, 1, 15)
        date3 = Date(2024, 1, 1)

        # Less than
        assert date1 < date2
        assert not date2 < date1

        # Less than or equal
        assert date1 <= date2
        assert date1 <= date3

        # Greater than
        assert date2 > date1
        assert not date1 > date2

        # Greater than or equal
        assert date2 >= date1
        assert date1 >= date3

        # Equality
        assert date1 == date3
        assert not date1 == date2

    def test_date_leap_year_edge_cases(self):
        """Test leap year handling in date arithmetic."""
        # February 28 to March 1 in leap year
        date = Date(2024, 2, 28)
        next_day = date.add_days(1)
        assert next_day == Date(2024, 2, 29)

        next_day = next_day.add_days(1)
        assert next_day == Date(2024, 3, 1)

        # February 28 to March 1 in non-leap year
        date = Date(2023, 2, 28)
        next_day = date.add_days(1)
        assert next_day == Date(2023, 3, 1)

    def test_date_immutability(self):
        """Test that Date objects are immutable."""
        date = Date(2024, 1, 15)

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            date.year = 2025


class TestDateAdvanceResult:
    """Test cases for DateAdvanceResult class."""

    def test_date_advance_result_creation(self):
        """Test creating DateAdvanceResult."""
        start_date = Date(2024, 1, 1)
        end_date = Date(2024, 1, 8)

        result = DateAdvanceResult(
            start_date=start_date,
            end_date=end_date,
            days_advanced=7
        )

        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.days_advanced == 7
        assert result.events_triggered == []
        assert result.transitions_crossed == []

    def test_date_advance_result_validation(self):
        """Test DateAdvanceResult validation."""
        start_date = Date(2024, 1, 1)
        end_date = Date(2024, 1, 8)

        # Valid result
        result = DateAdvanceResult(
            start_date=start_date,
            end_date=end_date,
            days_advanced=7
        )
        assert result.days_advanced == 7

        # Invalid: negative days
        with pytest.raises(ValueError, match="Days advanced cannot be negative"):
            DateAdvanceResult(
                start_date=start_date,
                end_date=end_date,
                days_advanced=-1
            )

        # Invalid: end date doesn't match advancement
        with pytest.raises(ValueError, match="End date .* does not match expected date"):
            DateAdvanceResult(
                start_date=start_date,
                end_date=Date(2024, 1, 10),  # Should be 8th for 7 days
                days_advanced=7
            )

    def test_date_advance_result_duration_description(self):
        """Test duration description formatting."""
        start_date = Date(2024, 1, 1)

        # 0 days
        result = DateAdvanceResult(start_date, start_date, 0)
        assert result.duration_description == "No time advanced"

        # 1 day
        result = DateAdvanceResult(start_date, start_date.add_days(1), 1)
        assert result.duration_description == "1 day"

        # Multiple days < 7
        result = DateAdvanceResult(start_date, start_date.add_days(5), 5)
        assert result.duration_description == "5 days"

        # Exactly 1 week
        result = DateAdvanceResult(start_date, start_date.add_days(7), 7)
        assert result.duration_description == "1 week"

        # Multiple weeks
        result = DateAdvanceResult(start_date, start_date.add_days(14), 14)
        assert result.duration_description == "2 weeks"

        # Weeks and days
        result = DateAdvanceResult(start_date, start_date.add_days(10), 10)
        assert result.duration_description == "1 week and 3 days"

        # Large number of days
        result = DateAdvanceResult(start_date, start_date.add_days(100), 100)
        assert result.duration_description == "100 days"

    def test_date_advance_result_string_representation(self):
        """Test string representation of DateAdvanceResult."""
        start_date = Date(2024, 1, 1)
        end_date = Date(2024, 1, 8)

        result = DateAdvanceResult(start_date, end_date, 7)
        str_repr = str(result)

        assert "2024-01-01" in str_repr
        assert "2024-01-08" in str_repr
        assert "1 week" in str_repr


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_normalize_date(self):
        """Test normalizing various date inputs."""
        # Date object
        date_obj = Date(2024, 1, 15)
        assert normalize_date(date_obj) == date_obj

        # Python date object
        py_date = PyDate(2024, 1, 15)
        normalized = normalize_date(py_date)
        assert normalized == Date(2024, 1, 15)

        # String
        normalized = normalize_date("2024-01-15")
        assert normalized == Date(2024, 1, 15)

        # Invalid input
        with pytest.raises(ValueError, match="Cannot convert"):
            normalize_date(12345)

    def test_days_between(self):
        """Test calculating days between various date inputs."""
        start = Date(2024, 1, 1)
        end = Date(2024, 1, 11)

        # Date objects
        assert days_between(start, end) == 10

        # Mixed types
        assert days_between("2024-01-01", end) == 10
        assert days_between(start, "2024-01-11") == 10

        # Python date objects
        py_start = PyDate(2024, 1, 1)
        py_end = PyDate(2024, 1, 11)
        assert days_between(py_start, py_end) == 10

    def test_is_valid_date(self):
        """Test date validation function."""
        # Valid dates
        assert is_valid_date(2024, 1, 15)
        assert is_valid_date(2024, 2, 29)  # Leap year
        assert is_valid_date(2024, 12, 31)

        # Invalid dates
        assert not is_valid_date(2024, 2, 30)  # February 30th
        assert not is_valid_date(2023, 2, 29)  # Feb 29 in non-leap year
        assert not is_valid_date(2024, 13, 1)  # Month 13
        assert not is_valid_date(2024, 1, 32)  # January 32nd
        assert not is_valid_date(2024, 0, 15)  # Month 0
        assert not is_valid_date(2024, 1, 0)   # Day 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_year_boundary_transitions(self):
        """Test year boundary crossing."""
        # December 31 to January 1
        date = Date(2023, 12, 31)
        next_day = date.add_days(1)
        assert next_day == Date(2024, 1, 1)

        # January 1 to December 31 (going backwards)
        date = Date(2024, 1, 1)
        prev_day = date.add_days(-1)
        assert prev_day == Date(2023, 12, 31)

    def test_month_boundary_transitions(self):
        """Test month boundary crossing for various months."""
        # January 31 to February 1
        date = Date(2024, 1, 31)
        next_day = date.add_days(1)
        assert next_day == Date(2024, 2, 1)

        # April 30 to May 1 (30-day month)
        date = Date(2024, 4, 30)
        next_day = date.add_days(1)
        assert next_day == Date(2024, 5, 1)

    def test_large_date_arithmetic(self):
        """Test date arithmetic with large numbers."""
        date = Date(2024, 1, 1)

        # Add a full year (365 days for non-leap year starting point)
        future_date = date.add_days(366)  # 2024 is leap year
        assert future_date == Date(2025, 1, 1)

        # Subtract a large number
        past_date = date.add_days(-365)
        assert past_date == Date(2023, 1, 1)

    def test_extreme_dates(self):
        """Test with extreme date values."""
        # Very old date
        old_date = Date(1900, 1, 1)
        new_date = old_date.add_days(1)
        assert new_date == Date(1900, 1, 2)

        # Far future date
        future_date = Date(2100, 12, 31)
        new_date = future_date.add_days(1)
        assert new_date == Date(2101, 1, 1)

    def test_date_arithmetic_consistency(self):
        """Test that date arithmetic is consistent and reversible."""
        original_date = Date(2024, 6, 15)

        # Add then subtract should return to original
        modified_date = original_date.add_days(100)
        restored_date = modified_date.add_days(-100)
        assert restored_date == original_date

        # Subtract then add should return to original
        modified_date = original_date.add_days(-50)
        restored_date = modified_date.add_days(50)
        assert restored_date == original_date