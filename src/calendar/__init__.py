"""
Calendar Manager

NFL simulation calendar system providing date management and advancement
capabilities with comprehensive validation and thread-safe operations.

Public API:
    Classes:
        - Date: Immutable date representation
        - DateAdvanceResult: Advancement result tracking
        - CalendarComponent: Main calendar management class

    Exceptions:
        - CalendarException: Base calendar exception
        - InvalidDaysException: Invalid days parameter
        - InvalidDateException: Invalid date creation
        - CalendarStateException: Calendar state errors
        - CalendarConfigurationException: Configuration errors
        - SeasonBoundaryException: Season boundary violations

    Factory Functions:
        - create_calendar(): Create new calendar
        - advance_calendar_days(): Advance and return new date

    Utilities:
        - normalize_date(): Convert various date inputs to Date
        - days_between(): Calculate days between dates
        - is_valid_date(): Validate date components
        - handle_calendar_exception(): User-friendly error handling

Example Usage:
    >>> from calendar import create_calendar, Date
    >>> calendar = create_calendar(Date(2024, 1, 1))
    >>> result = calendar.advance(10)
    >>> print(f"Advanced to {result.end_date}")
    Advanced to 2024-01-11
"""

# Core classes
from .date_models import (
    Date,
    DateAdvanceResult,
    normalize_date,
    days_between,
    is_valid_date
)

from .calendar_component import (
    CalendarComponent,
    create_calendar,
    advance_calendar_days
)

from .calendar_exceptions import (
    CalendarException,
    InvalidDaysException,
    InvalidDateException,
    CalendarStateException,
    CalendarConfigurationException,
    SeasonBoundaryException,
    handle_calendar_exception
)

# Version information
__version__ = "1.1.0"
__author__ = "NFL Simulation Team"
__description__ = "Calendar Manager for NFL Simulation System"

# Public API exports
__all__ = [
    # Core classes
    "Date",
    "DateAdvanceResult",
    "CalendarComponent",

    # Factory functions
    "create_calendar",
    "advance_calendar_days",

    # Utility functions
    "normalize_date",
    "days_between",
    "is_valid_date",

    # Exception classes
    "CalendarException",
    "InvalidDaysException",
    "InvalidDateException",
    "CalendarStateException",
    "CalendarConfigurationException",
    "SeasonBoundaryException",

    # Exception utilities
    "handle_calendar_exception",

    # Metadata
    "__version__",
    "__author__",
    "__description__"
]

# Convenience imports for common usage patterns
def today() -> Date:
    """Get today's date as a Date object."""
    return Date.today()

def calendar_from_today() -> CalendarComponent:
    """Create a calendar starting from today."""
    return create_calendar()

def calendar_from_string(date_str: str) -> CalendarComponent:
    """Create a calendar from a date string (YYYY-MM-DD)."""
    return create_calendar(date_str)

# Add convenience functions to public API
__all__.extend([
    "today",
    "calendar_from_today",
    "calendar_from_string"
])