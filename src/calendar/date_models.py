"""
Calendar Date Models

Core date classes and utilities for the Calendar Manager system.
Provides immutable date representation with robust arithmetic operations.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date as PyDate, datetime
from typing import Union, Any
import uuid
import calendar as stdlib_calendar  # Avoid naming conflict with our package


@dataclass(frozen=True)
class Date:
    """
    Immutable date representation with robust arithmetic operations.

    Wraps Python's date class to provide a clean interface with
    validation and utility methods for calendar operations.
    """
    year: int
    month: int  # 1-12
    day: int    # 1-31

    def __post_init__(self):
        """Validate date components during creation."""
        if not is_valid_date(self.year, self.month, self.day):
            # Import here to avoid circular import
            from .calendar_exceptions import InvalidDateException
            raise InvalidDateException(year=self.year, month=self.month, day=self.day)

    @classmethod
    def from_python_date(cls, py_date: PyDate) -> Date:
        """Create Date from Python date object."""
        return cls(py_date.year, py_date.month, py_date.day)

    @classmethod
    def today(cls) -> Date:
        """Create Date representing today."""
        today = PyDate.today()
        return cls.from_python_date(today)

    @classmethod
    def from_string(cls, date_str: str, format_str: str = "%Y-%m-%d") -> Date:
        """Create Date from string representation."""
        try:
            # Manual parsing for YYYY-MM-DD format to avoid calendar module conflict
            if format_str == "%Y-%m-%d" and len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                try:
                    year = int(date_str[:4])
                    month = int(date_str[5:7])
                    day = int(date_str[8:10])
                    return cls(year, month, day)
                except ValueError:
                    pass

            # Manual parsing for DD/MM/YYYY format
            if format_str == "%d/%m/%Y" and len(date_str) == 10 and date_str[2] == '/' and date_str[5] == '/':
                try:
                    day = int(date_str[:2])
                    month = int(date_str[3:5])
                    year = int(date_str[6:10])
                    return cls(year, month, day)
                except ValueError:
                    pass

            # If no manual parsing worked, raise error
            raise ValueError(f"Unsupported date format '{format_str}' or invalid date string '{date_str}'")

        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot parse date string '{date_str}' with format '{format_str}': {e}")

    def to_python_date(self) -> PyDate:
        """Convert to Python date object."""
        return PyDate(self.year, self.month, self.day)

    def to_python_datetime(self, hour: int = 19, minute: int = 0, second: int = 0) -> datetime:
        """
        Convert Date to datetime with specified time components.

        Args:
            hour: Hour of day (0-23), defaults to 19 (7:00 PM - typical game time)
            minute: Minute (0-59), defaults to 0
            second: Second (0-59), defaults to 0

        Returns:
            datetime object with this date and specified time

        Example:
            >>> date = Date(2025, 9, 5)
            >>> dt = date.to_python_datetime()  # 2025-09-05 19:00:00
            >>> dt_custom = date.to_python_datetime(hour=13, minute=30)  # 2025-09-05 13:30:00
        """
        return datetime(self.year, self.month, self.day, hour, minute, second)

    def add_days(self, days: int) -> Date:
        """Add specified number of days (can be negative)."""
        py_date = self.to_python_date()
        from datetime import timedelta
        new_py_date = py_date + timedelta(days=days)
        return Date.from_python_date(new_py_date)

    def subtract_days(self, days: int) -> Date:
        """Subtract specified number of days."""
        return self.add_days(-days)

    def days_until(self, other_date: Date) -> int:
        """Calculate number of days between this date and another."""
        py_date1 = self.to_python_date()
        py_date2 = other_date.to_python_date()
        delta = py_date2 - py_date1
        return delta.days

    def is_leap_year(self) -> bool:
        """Check if this date's year is a leap year."""
        year = self.year
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    def format(self, format_str: str = "%Y-%m-%d") -> str:
        """Format date as string."""
        # Manual formatting to avoid calendar module conflicts
        if format_str == "%Y-%m-%d":
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        elif format_str == "%d/%m/%Y":
            return f"{self.day:02d}/{self.month:02d}/{self.year:04d}"
        elif format_str == "%B %d, %Y":
            months = ["", "January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
            return f"{months[self.month]} {self.day:02d}, {self.year:04d}"
        else:
            # For unsupported formats, fall back to basic representation
            return str(self)

    def __str__(self) -> str:
        """String representation (YYYY-MM-DD format)."""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Date({self.year}, {self.month}, {self.day})"

    def __lt__(self, other: Date) -> bool:
        """Less than comparison."""
        return self.to_python_date() < other.to_python_date()

    def __le__(self, other: Date) -> bool:
        """Less than or equal comparison."""
        return self.to_python_date() <= other.to_python_date()

    def __gt__(self, other: Date) -> bool:
        """Greater than comparison."""
        return self.to_python_date() > other.to_python_date()

    def __ge__(self, other: Date) -> bool:
        """Greater than or equal comparison."""
        return self.to_python_date() >= other.to_python_date()

    def __eq__(self, other: Any) -> bool:
        """Equality comparison."""
        if not isinstance(other, Date):
            return False
        return (self.year == other.year and
                self.month == other.month and
                self.day == other.day)


@dataclass(frozen=True)
class DateAdvanceResult:
    """
    Result of a date advancement operation.

    Provides comprehensive tracking of date advancement including
    validation, unique identification, and duration descriptions.
    """
    start_date: Date
    end_date: Date
    days_advanced: int
    advancement_id: str = None
    timestamp: datetime = None
    events_triggered: list = None
    transitions_crossed: list = None

    def __post_init__(self):
        """Validate and initialize result data."""
        # Set defaults for mutable fields
        if self.advancement_id is None:
            object.__setattr__(self, 'advancement_id', str(uuid.uuid4()))

        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())

        if self.events_triggered is None:
            object.__setattr__(self, 'events_triggered', [])

        if self.transitions_crossed is None:
            object.__setattr__(self, 'transitions_crossed', [])

        # Validate advancement
        if self.days_advanced < 0:
            raise ValueError("Days advanced cannot be negative")

        # Validate that end date matches expected advancement
        expected_end_date = self.start_date.add_days(self.days_advanced)
        if self.end_date != expected_end_date:
            raise ValueError(
                f"End date {self.end_date} does not match expected date "
                f"{expected_end_date} for {self.days_advanced} days from {self.start_date}"
            )

    @property
    def duration_description(self) -> str:
        """Human-readable description of the advancement duration."""
        if self.days_advanced == 0:
            return "No time advanced"
        elif self.days_advanced == 1:
            return "1 day"
        elif self.days_advanced < 7:
            return f"{self.days_advanced} days"
        elif self.days_advanced == 7:
            return "1 week"
        elif self.days_advanced % 7 == 0:
            weeks = self.days_advanced // 7
            return f"{weeks} weeks"
        elif self.days_advanced < 14:
            extra_days = self.days_advanced - 7
            return f"1 week and {extra_days} days"
        elif self.days_advanced < 100:
            weeks = self.days_advanced // 7
            extra_days = self.days_advanced % 7
            if extra_days == 0:
                return f"{weeks} weeks"
            else:
                return f"{weeks} weeks and {extra_days} days"
        else:
            return f"{self.days_advanced} days"

    def __str__(self) -> str:
        """String representation of advancement result."""
        return (f"Advanced from {self.start_date} to {self.end_date} "
                f"({self.duration_description})")


# Utility Functions

def normalize_date(date_input: Union[Date, PyDate, str]) -> Date:
    """
    Convert various date inputs to Date object.

    Args:
        date_input: Date object, Python date, or date string

    Returns:
        Date object

    Raises:
        ValueError: If input cannot be converted to Date
    """
    # Use duck typing to handle Date objects imported from different paths
    # Check if it's a Date-like object by class name and attributes
    if hasattr(date_input, '__class__') and date_input.__class__.__name__ == 'Date':
        # It's a Date object (possibly imported from different path)
        # Convert to ensure we have the right type
        if hasattr(date_input, 'year') and hasattr(date_input, 'month') and hasattr(date_input, 'day'):
            return Date(year=date_input.year, month=date_input.month, day=date_input.day)
    elif isinstance(date_input, Date):
        return date_input
    elif isinstance(date_input, PyDate):
        return Date.from_python_date(date_input)
    elif isinstance(date_input, str):
        return Date.from_string(date_input)

    raise ValueError(f"Cannot convert {type(date_input)} to Date")


def days_between(start_date: Union[Date, PyDate, str],
                 end_date: Union[Date, PyDate, str]) -> int:
    """
    Calculate days between two dates.

    Args:
        start_date: Starting date (various formats accepted)
        end_date: Ending date (various formats accepted)

    Returns:
        Number of days between dates (positive if end > start)
    """
    start = normalize_date(start_date)
    end = normalize_date(end_date)
    return start.days_until(end)


def is_valid_date(year: int, month: int, day: int) -> bool:
    """
    Check if the given date components form a valid date.

    Args:
        year: Year (any valid year)
        month: Month (1-12)
        day: Day (1-31, depending on month)

    Returns:
        True if valid date, False otherwise
    """
    try:
        PyDate(year, month, day)
        return True
    except (ValueError, TypeError):
        return False