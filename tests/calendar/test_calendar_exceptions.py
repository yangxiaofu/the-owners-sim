"""
Unit tests for Calendar Exceptions

Tests for all calendar exception classes including error messages,
error codes, and exception handling utilities.
"""

import pytest

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.calendar.calendar_exceptions import (
    CalendarException,
    InvalidDaysException,
    InvalidDateException,
    CalendarStateException,
    CalendarConfigurationException,
    SeasonBoundaryException,
    handle_calendar_exception
)
from src.calendar.date_models import Date


class TestCalendarException:
    """Test cases for the base CalendarException class."""

    def test_calendar_exception_basic(self):
        """Test basic CalendarException creation."""
        exception = CalendarException("Test error message")

        assert str(exception) == "Test error message"
        assert exception.message == "Test error message"
        assert exception.error_code is None

    def test_calendar_exception_with_error_code(self):
        """Test CalendarException with error code."""
        exception = CalendarException("Test error", "TEST_ERROR")

        assert str(exception) == "[TEST_ERROR] Test error"
        assert exception.message == "Test error"
        assert exception.error_code == "TEST_ERROR"

    def test_calendar_exception_inheritance(self):
        """Test that CalendarException inherits from Exception."""
        exception = CalendarException("Test error")

        assert isinstance(exception, Exception)
        assert isinstance(exception, CalendarException)


class TestInvalidDaysException:
    """Test cases for InvalidDaysException."""

    def test_invalid_days_negative(self):
        """Test InvalidDaysException for negative days."""
        exception = InvalidDaysException(-5)

        assert "Cannot advance by -5 days" in str(exception)
        assert "Days must be positive" in str(exception)
        assert exception.error_code == "NEGATIVE_DAYS"
        assert exception.days == -5
        assert exception.min_days == 1
        assert exception.max_days == 365

    def test_invalid_days_zero(self):
        """Test InvalidDaysException for zero days."""
        exception = InvalidDaysException(0)

        assert "Cannot advance by 0 days" in str(exception)
        assert "Days must be positive" in str(exception)
        assert exception.error_code == "NEGATIVE_DAYS"

    def test_invalid_days_too_large(self):
        """Test InvalidDaysException for excessive days."""
        exception = InvalidDaysException(500)

        assert "Cannot advance by 500 days" in str(exception)
        assert "exceeds the maximum allowed" in str(exception)
        assert exception.error_code == "EXCESSIVE_DAYS"
        assert exception.days == 500

    def test_invalid_days_custom_limits(self):
        """Test InvalidDaysException with custom limits."""
        exception = InvalidDaysException(50, min_days=1, max_days=30)

        assert exception.min_days == 1
        assert exception.max_days == 30
        assert "between 1 and 30" in str(exception)

    def test_invalid_days_suggested_range(self):
        """Test suggested_range property."""
        exception = InvalidDaysException(500, min_days=1, max_days=365)
        assert exception.suggested_range == "1 to 365"

        exception = InvalidDaysException(100, min_days=5, max_days=50)
        assert exception.suggested_range == "5 to 50"

    def test_invalid_days_inheritance(self):
        """Test InvalidDaysException inheritance."""
        exception = InvalidDaysException(-1)

        assert isinstance(exception, CalendarException)
        assert isinstance(exception, InvalidDaysException)


class TestInvalidDateException:
    """Test cases for InvalidDateException."""

    def test_invalid_date_with_components(self):
        """Test InvalidDateException with date components."""
        exception = InvalidDateException(year=2024, month=13, day=1)

        assert "Invalid date: 2024-13-01" in str(exception)
        assert exception.error_code == "INVALID_DATE"
        assert exception.year == 2024
        assert exception.month == 13
        assert exception.day == 1

    def test_invalid_date_with_string(self):
        """Test InvalidDateException with date string."""
        exception = InvalidDateException(date_string="invalid-date")

        assert "Invalid date string: 'invalid-date'" in str(exception)
        assert exception.date_string == "invalid-date"

    def test_invalid_date_with_original_error(self):
        """Test InvalidDateException with original error."""
        original_error = ValueError("day is out of range for month")
        exception = InvalidDateException(
            year=2024, month=2, day=30,
            original_error=original_error
        )

        assert "Invalid date: 2024-02-30" in str(exception)
        assert "day is out of range for month" in str(exception)
        assert exception.original_error is original_error

    def test_invalid_date_components_property(self):
        """Test date_components property."""
        exception = InvalidDateException(year=2024, month=2, day=30)
        assert exception.date_components == (2024, 2, 30)

    def test_invalid_date_minimal(self):
        """Test InvalidDateException with minimal information."""
        exception = InvalidDateException()
        assert "Invalid date provided" in str(exception)


class TestCalendarStateException:
    """Test cases for CalendarStateException."""

    def test_calendar_state_basic(self):
        """Test basic CalendarStateException."""
        exception = CalendarStateException("Calendar is corrupted")

        assert "Calendar state error: Calendar is corrupted" in str(exception)
        assert exception.error_code == "INVALID_STATE"

    def test_calendar_state_with_info(self):
        """Test CalendarStateException with state info."""
        state_info = {
            "current_date": "2024-01-01",
            "total_advances": 5,
            "last_operation": "advance"
        }
        exception = CalendarStateException("State inconsistent", state_info)

        error_str = str(exception)
        assert "Calendar state error: State inconsistent" in error_str
        assert "current_date=2024-01-01" in error_str
        assert "total_advances=5" in error_str
        assert "last_operation=advance" in error_str
        assert exception.state_info == state_info

    def test_calendar_state_empty_info(self):
        """Test CalendarStateException with empty state info."""
        exception = CalendarStateException("Error occurred", {})

        assert "Calendar state error: Error occurred" in str(exception)
        assert exception.state_info == {}


class TestCalendarConfigurationException:
    """Test cases for CalendarConfigurationException."""

    def test_calendar_config_basic(self):
        """Test basic CalendarConfigurationException."""
        exception = CalendarConfigurationException("Invalid configuration")

        assert "Calendar configuration error: Invalid configuration" in str(exception)
        assert exception.error_code == "INVALID_CONFIG"

    def test_calendar_config_with_key(self):
        """Test CalendarConfigurationException with config key."""
        exception = CalendarConfigurationException(
            "Missing required setting",
            config_key="season_start_date"
        )

        error_str = str(exception)
        assert "Calendar configuration error: Missing required setting" in error_str
        assert "Key: 'season_start_date'" in error_str
        assert exception.config_key == "season_start_date"

    def test_calendar_config_with_key_and_value(self):
        """Test CalendarConfigurationException with key and value."""
        exception = CalendarConfigurationException(
            "Invalid value",
            config_key="max_season_weeks",
            config_value=100
        )

        error_str = str(exception)
        assert "Calendar configuration error: Invalid value" in error_str
        assert "Key: 'max_season_weeks'" in error_str
        assert "Value: 100" in error_str
        assert exception.config_key == "max_season_weeks"
        assert exception.config_value == 100


class TestSeasonBoundaryException:
    """Test cases for SeasonBoundaryException."""

    def test_season_boundary_basic(self):
        """Test basic SeasonBoundaryException."""
        current_date = Date(2024, 1, 15)
        target_date = Date(2024, 3, 1)
        season_end_date = Date(2024, 2, 15)

        exception = SeasonBoundaryException(
            current_date=current_date,
            target_date=target_date,
            season_end_date=season_end_date,
            days_attempted=45
        )

        error_str = str(exception)
        assert "Cannot advance 45 days from 2024-01-15 to 2024-03-01" in error_str
        assert "exceed the season boundary of 2024-02-15" in error_str
        assert exception.error_code == "SEASON_BOUNDARY"

    def test_season_boundary_max_allowed_days(self):
        """Test max_allowed_days property."""
        current_date = Date(2024, 1, 1)
        target_date = Date(2024, 2, 15)
        season_end_date = Date(2024, 1, 31)

        exception = SeasonBoundaryException(
            current_date=current_date,
            target_date=target_date,
            season_end_date=season_end_date,
            days_attempted=45
        )

        # 30 days from Jan 1 to Jan 31
        assert exception.max_allowed_days == 30

    def test_season_boundary_properties(self):
        """Test SeasonBoundaryException properties."""
        current_date = Date(2024, 1, 1)
        target_date = Date(2024, 2, 1)
        season_end_date = Date(2024, 1, 15)

        exception = SeasonBoundaryException(
            current_date=current_date,
            target_date=target_date,
            season_end_date=season_end_date,
            days_attempted=31
        )

        assert exception.current_date == current_date
        assert exception.target_date == target_date
        assert exception.season_end_date == season_end_date
        assert exception.days_attempted == 31


class TestExceptionHandling:
    """Test exception handling utilities."""

    def test_handle_invalid_days_exception(self):
        """Test handling InvalidDaysException."""
        exception = InvalidDaysException(-5, min_days=1, max_days=365)
        message = handle_calendar_exception(exception)

        assert "Cannot advance by -5 days" in message
        assert "Please use a value between 1 to 365" in message

    def test_handle_invalid_date_exception(self):
        """Test handling InvalidDateException."""
        exception = InvalidDateException(date_string="invalid-date")
        message = handle_calendar_exception(exception)

        assert "Invalid date string: 'invalid-date'" in message
        assert "Please check that the date exists" in message

    def test_handle_season_boundary_exception(self):
        """Test handling SeasonBoundaryException."""
        current_date = Date(2024, 1, 1)
        target_date = Date(2024, 2, 1)
        season_end_date = Date(2024, 1, 15)

        exception = SeasonBoundaryException(
            current_date=current_date,
            target_date=target_date,
            season_end_date=season_end_date,
            days_attempted=31
        )

        message = handle_calendar_exception(exception)

        assert "Cannot advance 31 days" in message
        assert "You can advance at most 14 days" in message

    def test_handle_calendar_state_exception(self):
        """Test handling CalendarStateException."""
        exception = CalendarStateException("Calendar corrupted")
        message = handle_calendar_exception(exception)

        assert "Calendar state error: Calendar corrupted" in message
        assert "may need to be reset" in message

    def test_handle_calendar_config_exception(self):
        """Test handling CalendarConfigurationException."""
        exception = CalendarConfigurationException("Invalid config")
        message = handle_calendar_exception(exception)

        assert "Calendar configuration error: Invalid config" in message
        assert "Please check the calendar configuration" in message

    def test_handle_generic_calendar_exception(self):
        """Test handling generic CalendarException."""
        exception = CalendarException("Generic error")
        message = handle_calendar_exception(exception)

        assert "Calendar error: Generic error" in message


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_calendar_exception(self):
        """Test that all custom exceptions inherit from CalendarException."""
        exceptions = [
            InvalidDaysException(-1),
            InvalidDateException(),
            CalendarStateException("test"),
            CalendarConfigurationException("test"),
            SeasonBoundaryException(
                Date(2024, 1, 1), Date(2024, 2, 1),
                Date(2024, 1, 15), 31
            )
        ]

        for exception in exceptions:
            assert isinstance(exception, CalendarException)
            assert isinstance(exception, Exception)

    def test_exception_error_codes(self):
        """Test that exceptions have appropriate error codes."""
        exceptions_and_codes = [
            (InvalidDaysException(-1), "NEGATIVE_DAYS"),
            (InvalidDaysException(500), "EXCESSIVE_DAYS"),
            (InvalidDateException(), "INVALID_DATE"),
            (CalendarStateException("test"), "INVALID_STATE"),
            (CalendarConfigurationException("test"), "INVALID_CONFIG"),
            (SeasonBoundaryException(
                Date(2024, 1, 1), Date(2024, 2, 1),
                Date(2024, 1, 15), 31
            ), "SEASON_BOUNDARY")
        ]

        for exception, expected_code in exceptions_and_codes:
            assert exception.error_code == expected_code


class TestExceptionMessages:
    """Test exception message formatting."""

    def test_exception_messages_are_helpful(self):
        """Test that exception messages provide helpful information."""
        # Test various exception types
        exceptions = [
            InvalidDaysException(-5),
            InvalidDaysException(500),
            InvalidDateException(year=2024, month=13, day=1),
            CalendarStateException("test error", {"key": "value"}),
            CalendarConfigurationException("test", "config_key", "config_value"),
        ]

        for exception in exceptions:
            message = str(exception)
            # All messages should be non-empty and descriptive
            assert len(message) > 10
            assert "error" in message.lower() or "invalid" in message.lower() or "cannot" in message.lower()

    def test_exception_messages_contain_context(self):
        """Test that exception messages contain relevant context."""
        # InvalidDaysException should mention the invalid value
        exception = InvalidDaysException(-5)
        assert "-5" in str(exception)

        # InvalidDateException should mention the invalid date
        exception = InvalidDateException(year=2024, month=13, day=1)
        assert "2024-13-01" in str(exception)

        # SeasonBoundaryException should mention all relevant dates
        exception = SeasonBoundaryException(
            Date(2024, 1, 1), Date(2024, 2, 1),
            Date(2024, 1, 15), 31
        )
        message = str(exception)
        assert "2024-01-01" in message
        assert "2024-02-01" in message
        assert "2024-01-15" in message
        assert "31" in message