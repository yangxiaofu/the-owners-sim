"""
Calendar Component

Main calendar management component providing thread-safe date advancement
and comprehensive state tracking for the NFL simulation system.
"""

import threading
from datetime import date as PyDate
from typing import Union, Dict, Any, Optional

from .date_models import Date, DateAdvanceResult, normalize_date
from .calendar_exceptions import (
    InvalidDaysException,
    InvalidDateException,
    CalendarStateException
)


class CalendarComponent:
    """
    Thread-safe calendar component for managing simulation date state.

    Provides date advancement capabilities with comprehensive validation,
    statistics tracking, and concurrent operation support.
    """

    # Constants
    MIN_ADVANCE_DAYS = 1
    MAX_ADVANCE_DAYS = 365

    def __init__(self, start_date: Union[Date, PyDate, str]):
        """
        Initialize calendar component.

        Args:
            start_date: Starting date (Date object, Python date, or string)

        Raises:
            InvalidDateException: If start_date is invalid
        """
        try:
            self._current_date = normalize_date(start_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(start_date), original_error=e)

        self._creation_date = self._current_date
        self._lock = threading.Lock()

        # Statistics tracking
        self._total_days_advanced = 0
        self._advancement_count = 0
        self._max_single_advance = 0

    def advance(self, days: Union[int, float]) -> DateAdvanceResult:
        """
        Advance calendar by specified number of days.

        Args:
            days: Number of days to advance (must be positive integer)

        Returns:
            DateAdvanceResult with advancement details

        Raises:
            InvalidDaysException: If days is invalid
            CalendarStateException: If internal state is corrupted
        """
        # Validate days parameter
        self._validate_days_parameter(days)
        days = int(days)  # Convert to int after validation

        with self._lock:
            try:
                start_date = self._current_date

                # Perform date advancement
                end_date = start_date.add_days(days)

                # Update internal state
                self._current_date = end_date
                self._total_days_advanced += days
                self._advancement_count += 1
                self._max_single_advance = max(self._max_single_advance, days)

                # Create result
                result = DateAdvanceResult(
                    start_date=start_date,
                    end_date=end_date,
                    days_advanced=days
                )

                return result

            except Exception as e:
                # If something went wrong, try to maintain state consistency
                raise CalendarStateException(
                    f"Failed to advance calendar by {days} days",
                    state_info={
                        "current_date": str(self._current_date),
                        "attempted_days": days,
                        "error": str(e)
                    }
                )

    def get_current_date(self) -> Date:
        """
        Get the current calendar date.

        Returns:
            Current Date object (thread-safe)
        """
        with self._lock:
            return self._current_date

    def get_current_season(self) -> int:
        """
        Get the current season year.

        Returns:
            Year of current date
        """
        return self.get_current_date().year

    def get_calendar_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive calendar statistics.

        Returns:
            Dictionary containing calendar usage statistics
        """
        with self._lock:
            current_date = self._current_date
            # Calculate days since creation directly to avoid deadlock
            days_since_creation = self._creation_date.days_until(self._current_date)

            return {
                "current_date": str(current_date),
                "current_year": current_date.year,
                "creation_date": str(self._creation_date),
                "total_days_advanced": self._total_days_advanced,
                "advancement_count": self._advancement_count,
                "average_advance_size": (
                    self._total_days_advanced / self._advancement_count
                    if self._advancement_count > 0 else 0
                ),
                "max_single_advance": self._max_single_advance,
                "days_since_creation": days_since_creation
            }

    def reset(self, new_date: Union[Date, PyDate, str]) -> None:
        """
        Reset calendar to a new date and clear statistics.

        Args:
            new_date: New starting date

        Raises:
            InvalidDateException: If new_date is invalid
        """
        try:
            normalized_date = normalize_date(new_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(new_date), original_error=e)

        with self._lock:
            self._current_date = normalized_date
            self._creation_date = normalized_date
            self._total_days_advanced = 0
            self._advancement_count = 0
            self._max_single_advance = 0

    def days_since_creation(self) -> int:
        """
        Get number of days since calendar was created/reset.

        Returns:
            Days between creation date and current date
        """
        with self._lock:
            return self._creation_date.days_until(self._current_date)

    def is_same_date(self, other_date: Union[Date, PyDate, str]) -> bool:
        """
        Check if current date matches another date.

        Args:
            other_date: Date to compare against

        Returns:
            True if dates match, False otherwise
        """
        try:
            other = normalize_date(other_date)
            return self.get_current_date() == other
        except ValueError:
            return False

    def days_until(self, target_date: Union[Date, PyDate, str]) -> int:
        """
        Calculate days until target date.

        Args:
            target_date: Target date

        Returns:
            Number of days (positive if future, negative if past)

        Raises:
            InvalidDateException: If target_date is invalid
        """
        try:
            target = normalize_date(target_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(target_date), original_error=e)

        current = self.get_current_date()
        return current.days_until(target)

    def can_advance(self, days: Union[int, float]) -> bool:
        """
        Check if calendar can advance by specified days.

        Args:
            days: Number of days to check

        Returns:
            True if advancement is valid, False otherwise
        """
        try:
            self._validate_days_parameter(days)
            return True
        except InvalidDaysException:
            return False

    def _validate_days_parameter(self, days: Union[int, float]) -> None:
        """
        Validate the days parameter for advancement.

        Args:
            days: Days parameter to validate

        Raises:
            InvalidDaysException: If days is invalid
        """
        # Check type
        if not isinstance(days, (int, float)):
            raise InvalidDaysException(
                days=0,  # Placeholder since we can't convert
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        # Check if it's effectively an integer
        if isinstance(days, float) and not days.is_integer():
            raise InvalidDaysException(
                days=int(days),
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        days_int = int(days)

        # Check range
        if days_int < self.MIN_ADVANCE_DAYS:
            raise InvalidDaysException(
                days=days_int,
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        if days_int > self.MAX_ADVANCE_DAYS:
            raise InvalidDaysException(
                days=days_int,
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

    def __str__(self) -> str:
        """String representation of calendar."""
        current = self.get_current_date()
        return f"CalendarComponent(current_date={current})"

    def __repr__(self) -> str:
        """Developer representation of calendar."""
        current = self.get_current_date()
        return f"CalendarComponent(current_date={current!r})"


# Factory Functions

def create_calendar(start_date: Optional[Union[Date, PyDate, str]] = None) -> CalendarComponent:
    """
    Create a new calendar component.

    Args:
        start_date: Starting date (defaults to today if None)

    Returns:
        New CalendarComponent instance
    """
    if start_date is None:
        start_date = Date.today()

    return CalendarComponent(start_date)


def advance_calendar_days(calendar: CalendarComponent, days: int) -> Date:
    """
    Advance calendar and return new date.

    Args:
        calendar: Calendar to advance
        days: Number of days to advance

    Returns:
        New current date after advancement
    """
    calendar.advance(days)
    return calendar.get_current_date()