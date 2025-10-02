"""
Unit tests for CalendarComponent

Tests for the main CalendarComponent class including date advancement,
validation, thread safety, and error handling.
"""

import pytest
import threading
import time
from datetime import date as PyDate

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.calendar.calendar_component import CalendarComponent, create_calendar, advance_calendar_days
from src.calendar.date_models import Date, DateAdvanceResult
from src.calendar.calendar_exceptions import (
    InvalidDaysException,
    InvalidDateException,
    CalendarStateException
)


class TestCalendarComponent:
    """Test cases for the CalendarComponent class."""

    def test_calendar_creation_with_date_object(self):
        """Test creating calendar with Date object."""
        start_date = Date(2024, 1, 15)
        calendar = CalendarComponent(start_date)

        assert calendar.get_current_date() == start_date
        assert calendar.get_current_season() == 2024

    def test_calendar_creation_with_python_date(self):
        """Test creating calendar with Python date object."""
        start_date = PyDate(2024, 2, 10)
        calendar = CalendarComponent(start_date)

        expected_date = Date(2024, 2, 10)
        assert calendar.get_current_date() == expected_date

    def test_calendar_creation_with_string(self):
        """Test creating calendar with date string."""
        calendar = CalendarComponent("2024-03-20")

        expected_date = Date(2024, 3, 20)
        assert calendar.get_current_date() == expected_date

    def test_calendar_creation_invalid_date(self):
        """Test creating calendar with invalid date raises exception."""
        with pytest.raises(InvalidDateException):
            CalendarComponent("invalid-date")

        with pytest.raises(InvalidDateException):
            CalendarComponent(Date(2024, 2, 30))  # Invalid date

    def test_basic_date_advancement(self):
        """Test basic date advancement functionality."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        result = calendar.advance(10)

        assert isinstance(result, DateAdvanceResult)
        assert result.start_date == Date(2024, 1, 1)
        assert result.end_date == Date(2024, 1, 11)
        assert result.days_advanced == 10
        assert calendar.get_current_date() == Date(2024, 1, 11)

    def test_advance_single_day(self):
        """Test advancing by a single day."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        result = calendar.advance(1)

        assert result.start_date == Date(2024, 1, 15)
        assert result.end_date == Date(2024, 1, 16)
        assert result.days_advanced == 1

    def test_advance_across_month_boundary(self):
        """Test advancing across month boundary."""
        calendar = CalendarComponent(Date(2024, 1, 25))

        result = calendar.advance(10)

        assert result.start_date == Date(2024, 1, 25)
        assert result.end_date == Date(2024, 2, 4)
        assert result.days_advanced == 10

    def test_advance_across_year_boundary(self):
        """Test advancing across year boundary."""
        calendar = CalendarComponent(Date(2023, 12, 25))

        result = calendar.advance(10)

        assert result.start_date == Date(2023, 12, 25)
        assert result.end_date == Date(2024, 1, 4)
        assert result.days_advanced == 10
        assert calendar.get_current_season() == 2024

    def test_advance_leap_year_handling(self):
        """Test advancing through leap year February."""
        calendar = CalendarComponent(Date(2024, 2, 25))

        result = calendar.advance(10)

        assert result.start_date == Date(2024, 2, 25)
        assert result.end_date == Date(2024, 3, 5)  # Crosses Feb 29
        assert result.days_advanced == 10

    def test_advance_invalid_days_negative(self):
        """Test advancing with negative days raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        with pytest.raises(InvalidDaysException, match="Days must be positive"):
            calendar.advance(-5)

    def test_advance_invalid_days_zero(self):
        """Test advancing with zero days raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        with pytest.raises(InvalidDaysException, match="Days must be positive"):
            calendar.advance(0)

    def test_advance_invalid_days_too_large(self):
        """Test advancing with excessively large days raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        with pytest.raises(InvalidDaysException, match="exceeds the maximum allowed"):
            calendar.advance(500)  # Exceeds MAX_ADVANCE_DAYS

    def test_advance_invalid_days_non_integer(self):
        """Test advancing with non-integer days raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        with pytest.raises(InvalidDaysException):
            calendar.advance(7.5)

        with pytest.raises(InvalidDaysException):
            calendar.advance("10")

    def test_multiple_advances(self):
        """Test multiple sequential advances."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # First advance
        result1 = calendar.advance(5)
        assert calendar.get_current_date() == Date(2024, 1, 6)

        # Second advance
        result2 = calendar.advance(10)
        assert calendar.get_current_date() == Date(2024, 1, 16)

        # Verify results are independent
        assert result1.end_date == Date(2024, 1, 6)
        assert result2.start_date == Date(2024, 1, 6)
        assert result2.end_date == Date(2024, 1, 16)

    def test_get_current_date(self):
        """Test getting current date."""
        start_date = Date(2024, 5, 15)
        calendar = CalendarComponent(start_date)

        assert calendar.get_current_date() == start_date

        # After advancement
        calendar.advance(7)
        assert calendar.get_current_date() == Date(2024, 5, 22)

    def test_get_current_season(self):
        """Test getting current season year."""
        calendar = CalendarComponent(Date(2024, 1, 15))
        assert calendar.get_current_season() == 2024

        # After year boundary crossing
        calendar = CalendarComponent(Date(2023, 12, 25))
        calendar.advance(10)
        assert calendar.get_current_season() == 2024

    def test_get_calendar_statistics(self):
        """Test getting calendar statistics."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # Initial statistics
        stats = calendar.get_calendar_statistics()
        assert stats["current_date"] == "2024-01-01"
        assert stats["current_year"] == 2024
        assert stats["total_days_advanced"] == 0
        assert stats["advancement_count"] == 0
        assert stats["average_advance_size"] == 0

        # After some advances
        calendar.advance(10)
        calendar.advance(5)

        stats = calendar.get_calendar_statistics()
        assert stats["total_days_advanced"] == 15
        assert stats["advancement_count"] == 2
        assert stats["average_advance_size"] == 7.5

    def test_reset_calendar(self):
        """Test resetting calendar to new date."""
        calendar = CalendarComponent(Date(2024, 1, 1))
        calendar.advance(30)

        # Reset to new date
        new_date = Date(2024, 6, 15)
        calendar.reset(new_date)

        assert calendar.get_current_date() == new_date
        stats = calendar.get_calendar_statistics()
        assert stats["total_days_advanced"] == 0
        assert stats["advancement_count"] == 0

    def test_reset_calendar_invalid_date(self):
        """Test resetting calendar with invalid date raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        with pytest.raises(InvalidDateException):
            calendar.reset("invalid-date")

    def test_days_since_creation(self):
        """Test getting days since calendar creation."""
        calendar = CalendarComponent(Date(2024, 1, 1))
        assert calendar.days_since_creation() == 0

        calendar.advance(15)
        assert calendar.days_since_creation() == 15

        calendar.advance(10)
        assert calendar.days_since_creation() == 25

    def test_is_same_date(self):
        """Test checking if current date matches another date."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        assert calendar.is_same_date(Date(2024, 1, 15))
        assert calendar.is_same_date("2024-01-15")
        assert calendar.is_same_date(PyDate(2024, 1, 15))

        assert not calendar.is_same_date(Date(2024, 1, 16))
        assert not calendar.is_same_date("invalid-date")

    def test_days_until(self):
        """Test calculating days until target date."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # Future date
        assert calendar.days_until(Date(2024, 1, 11)) == 10
        assert calendar.days_until("2024-01-11") == 10

        # Past date
        assert calendar.days_until(Date(2023, 12, 25)) == -7

        # Same date
        assert calendar.days_until(Date(2024, 1, 1)) == 0

    def test_days_until_invalid_date(self):
        """Test days_until with invalid date raises exception."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        with pytest.raises(InvalidDateException):
            calendar.days_until("invalid-date")

    def test_can_advance(self):
        """Test checking if calendar can advance by specified days."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        assert calendar.can_advance(1)
        assert calendar.can_advance(100)
        assert calendar.can_advance(365)

        assert not calendar.can_advance(0)
        assert not calendar.can_advance(-5)
        assert not calendar.can_advance(500)

    def test_calendar_string_representations(self):
        """Test string representations of calendar."""
        calendar = CalendarComponent(Date(2024, 1, 15))

        str_repr = str(calendar)
        assert "CalendarComponent" in str_repr
        assert "2024-01-15" in str_repr

        repr_str = repr(calendar)
        assert "CalendarComponent" in repr_str
        assert "2024-01-15" in repr_str


class TestCalendarThreadSafety:
    """Test thread safety of CalendarComponent."""

    def test_concurrent_reads(self):
        """Test concurrent read operations are thread-safe."""
        calendar = CalendarComponent(Date(2024, 1, 1))
        results = []
        errors = []

        def read_date():
            try:
                for _ in range(100):
                    date = calendar.get_current_date()
                    results.append(date)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)

        # Start multiple reader threads
        threads = [threading.Thread(target=read_date) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors and all reads should return same date
        assert len(errors) == 0
        assert all(date == Date(2024, 1, 1) for date in results)

    def test_concurrent_advances(self):
        """Test concurrent advance operations are thread-safe."""
        calendar = CalendarComponent(Date(2024, 1, 1))
        results = []
        errors = []

        def advance_calendar():
            try:
                result = calendar.advance(1)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple advance threads
        threads = [threading.Thread(target=advance_calendar) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors and total advancement should be 5 days
        assert len(errors) == 0
        assert len(results) == 5
        assert calendar.get_current_date() == Date(2024, 1, 6)

        # Each result should have advanced by 1 day
        assert all(result.days_advanced == 1 for result in results)

    def test_concurrent_mixed_operations(self):
        """Test mixed concurrent operations are thread-safe."""
        calendar = CalendarComponent(Date(2024, 1, 1))
        read_results = []
        advance_results = []
        errors = []

        def reader():
            try:
                for _ in range(50):
                    date = calendar.get_current_date()
                    stats = calendar.get_calendar_statistics()
                    read_results.append((date, stats))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def advancer():
            try:
                for _ in range(10):
                    result = calendar.advance(1)
                    advance_results.append(result)
                    time.sleep(0.005)
            except Exception as e:
                errors.append(e)

        # Start mixed threads
        reader_threads = [threading.Thread(target=reader) for _ in range(2)]
        advance_threads = [threading.Thread(target=advancer) for _ in range(2)]

        all_threads = reader_threads + advance_threads

        for thread in all_threads:
            thread.start()

        for thread in all_threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have advanced by 20 days total (2 threads × 10 advances × 1 day)
        assert calendar.get_current_date() == Date(2024, 1, 21)

        # All operations should have completed
        assert len(read_results) == 100  # 2 threads × 50 reads
        assert len(advance_results) == 20  # 2 threads × 10 advances


class TestFactoryFunctions:
    """Test factory and utility functions."""

    def test_create_calendar_default(self):
        """Test creating calendar with default date (today)."""
        calendar = create_calendar()

        today = Date.today()
        assert calendar.get_current_date() == today

    def test_create_calendar_with_date(self):
        """Test creating calendar with specific date."""
        start_date = Date(2024, 6, 15)
        calendar = create_calendar(start_date)

        assert calendar.get_current_date() == start_date

    def test_advance_calendar_days_function(self):
        """Test the advance_calendar_days utility function."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        new_date = advance_calendar_days(calendar, 15)

        assert new_date == Date(2024, 1, 16)
        assert calendar.get_current_date() == Date(2024, 1, 16)


class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions."""

    def test_very_large_advances(self):
        """Test advancing by maximum allowed days."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # Maximum allowed advance (365 days)
        result = calendar.advance(365)
        expected_end = Date(2024, 1, 1).add_days(365)
        assert result.end_date == expected_end

    def test_date_arithmetic_edge_cases(self):
        """Test date arithmetic edge cases in calendar."""
        # Start on leap day
        calendar = CalendarComponent(Date(2024, 2, 29))
        result = calendar.advance(1)
        assert result.end_date == Date(2024, 3, 1)

        # Start on last day of year
        calendar = CalendarComponent(Date(2023, 12, 31))
        result = calendar.advance(1)
        assert result.end_date == Date(2024, 1, 1)

    def test_calendar_state_consistency(self):
        """Test that calendar maintains consistent state."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # Perform various operations
        calendar.advance(30)
        calendar.advance(15)
        calendar.reset(Date(2024, 6, 1))
        calendar.advance(10)

        # Calendar should be in valid state
        current_date = calendar.get_current_date()
        assert current_date == Date(2024, 6, 11)

        stats = calendar.get_calendar_statistics()
        assert stats["total_days_advanced"] == 10  # Reset clears history
        assert stats["advancement_count"] == 1

    def test_invalid_state_handling(self):
        """Test handling of invalid internal state."""
        calendar = CalendarComponent(Date(2024, 1, 1))

        # This is testing internal validation - would need to break encapsulation
        # to properly test, but we can verify that normal operations maintain state
        for _ in range(10):
            calendar.advance(1)
            # Each operation should maintain valid state
            assert calendar.get_current_date() is not None
            assert isinstance(calendar.get_current_date(), Date)