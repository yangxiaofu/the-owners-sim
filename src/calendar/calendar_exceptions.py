"""
Calendar Exception Classes

Comprehensive exception hierarchy for the Calendar Manager system.
Provides specific error types with error codes and user-friendly messages.
"""

from typing import Optional, Dict, Any
from .date_models import Date


class CalendarException(Exception):
    """
    Base exception for all calendar-related errors.

    Provides error code support and structured error messages.
    """

    def __init__(self, message: str, error_code: Optional[str] = None):
        """
        Initialize calendar exception.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with optional error code."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class InvalidDaysException(CalendarException):
    """
    Exception raised when advancing by invalid number of days.

    Handles negative days, zero days, and excessively large values.
    """

    def __init__(self, days: int, min_days: int = 1, max_days: int = 365):
        """
        Initialize invalid days exception.

        Args:
            days: The invalid number of days that was attempted
            min_days: Minimum allowed days (default: 1)
            max_days: Maximum allowed days (default: 365)
        """
        self.days = days
        self.min_days = min_days
        self.max_days = max_days

        # Determine error type and message
        if days <= 0:
            error_code = "NEGATIVE_DAYS"
            message = (f"Cannot advance by {days} days. "
                      f"Days must be positive (between {min_days} and {max_days}).")
        else:
            error_code = "EXCESSIVE_DAYS"
            message = (f"Cannot advance by {days} days as it "
                      f"exceeds the maximum allowed ({max_days} days). "
                      f"Please use a value between {min_days} and {max_days}.")

        super().__init__(message, error_code)

    @property
    def suggested_range(self) -> str:
        """Get the suggested range of valid days."""
        return f"{self.min_days} to {self.max_days}"


class InvalidDateException(CalendarException):
    """
    Exception raised when date creation or parsing fails.

    Handles invalid date components, malformed strings, and impossible dates.
    """

    def __init__(self, year: Optional[int] = None, month: Optional[int] = None,
                 day: Optional[int] = None, date_string: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        """
        Initialize invalid date exception.

        Args:
            year: Year component (if applicable)
            month: Month component (if applicable)
            day: Day component (if applicable)
            date_string: Original date string (if parsing failed)
            original_error: Original exception that caused this error
        """
        self.year = year
        self.month = month
        self.day = day
        self.date_string = date_string
        self.original_error = original_error

        # Build descriptive error message
        if date_string:
            message = f"Invalid date string: '{date_string}'"
        elif year is not None and month is not None and day is not None:
            message = f"Invalid date: {year}-{month:02d}-{day:02d}"
        else:
            message = "Invalid date provided"

        # Add original error details if available
        if original_error:
            message += f". {str(original_error)}"

        super().__init__(message, "INVALID_DATE")

    @property
    def date_components(self) -> tuple:
        """Get the date components as a tuple."""
        return (self.year, self.month, self.day)


class CalendarStateException(CalendarException):
    """
    Exception raised when calendar is in an invalid or inconsistent state.

    Handles internal state corruption, validation failures, and recovery scenarios.
    """

    def __init__(self, message: str, state_info: Optional[Dict[str, Any]] = None):
        """
        Initialize calendar state exception.

        Args:
            message: Description of the state problem
            state_info: Optional dictionary of current state information
        """
        self.state_info = state_info or {}

        # Build comprehensive error message
        full_message = f"Calendar state error: {message}"

        # Add state information if provided
        if self.state_info:
            state_details = ", ".join(f"{k}={v}" for k, v in self.state_info.items())
            full_message += f". Current state: {state_details}"

        super().__init__(full_message, "INVALID_STATE")


class CalendarConfigurationException(CalendarException):
    """
    Exception raised when calendar configuration is invalid or missing.

    Handles configuration errors, missing settings, and validation failures.
    """

    def __init__(self, message: str, config_key: Optional[str] = None,
                 config_value: Optional[Any] = None):
        """
        Initialize calendar configuration exception.

        Args:
            message: Description of the configuration problem
            config_key: The configuration key that caused the error
            config_value: The invalid configuration value
        """
        self.config_key = config_key
        self.config_value = config_value

        # Build detailed error message
        full_message = f"Calendar configuration error: {message}"

        # Add configuration details if provided
        if config_key:
            full_message += f". Key: '{config_key}'"
        if config_value is not None:
            full_message += f". Value: {config_value}"

        super().__init__(full_message, "INVALID_CONFIG")


class SeasonBoundaryException(CalendarException):
    """
    Exception raised when advancing beyond season boundaries.

    Handles attempts to advance past configured season limits.
    """

    def __init__(self, current_date: Date, target_date: Date,
                 season_end_date: Date, days_attempted: int):
        """
        Initialize season boundary exception.

        Args:
            current_date: Current calendar date
            target_date: Attempted target date
            season_end_date: End of current season
            days_attempted: Number of days that were attempted to advance
        """
        self.current_date = current_date
        self.target_date = target_date
        self.season_end_date = season_end_date
        self.days_attempted = days_attempted

        message = (f"Cannot advance {days_attempted} days from {current_date} "
                  f"to {target_date} as this would exceed the season boundary "
                  f"of {season_end_date}")

        super().__init__(message, "SEASON_BOUNDARY")

    @property
    def max_allowed_days(self) -> int:
        """Calculate the maximum number of days that can be advanced."""
        return self.current_date.days_until(self.season_end_date)


# Exception Handling Utilities

def handle_calendar_exception(exception: CalendarException) -> str:
    """
    Handle calendar exceptions with user-friendly recovery suggestions.

    Args:
        exception: The calendar exception to handle

    Returns:
        User-friendly error message with recovery suggestions
    """
    base_message = str(exception)

    # Add specific recovery suggestions based on exception type
    if isinstance(exception, InvalidDaysException):
        recovery_msg = f"Please use a value between {exception.suggested_range}."
        return f"{base_message} {recovery_msg}"

    elif isinstance(exception, InvalidDateException):
        recovery_msg = "Please check that the date exists and is properly formatted."
        return f"{base_message} {recovery_msg}"

    elif isinstance(exception, SeasonBoundaryException):
        max_days = exception.max_allowed_days
        recovery_msg = f"You can advance at most {max_days} days to reach the season end."
        return f"{base_message} {recovery_msg}"

    elif isinstance(exception, CalendarStateException):
        recovery_msg = "The calendar may need to be reset or re-initialized."
        return f"{base_message} {recovery_msg}"

    elif isinstance(exception, CalendarConfigurationException):
        recovery_msg = "Please check the calendar configuration settings."
        return f"{base_message} {recovery_msg}"

    else:
        # Generic calendar exception
        return f"Calendar error: {base_message}"