"""
Calendar System Tests

Unit tests for the Calendar Manager Phase 1.1 and 1.2 implementation.

Test modules:
- test_date_models: Tests for Date and DateAdvanceResult classes
- test_calendar_component: Tests for CalendarComponent functionality
- test_calendar_exceptions: Tests for exception classes and handling
- test_season_phase_tracker: Tests for season phase tracking and transitions

To run all calendar tests:
    pytest tests/calendar/

To run specific test module:
    pytest tests/calendar/test_date_models.py
    pytest tests/calendar/test_calendar_component.py
    pytest tests/calendar/test_calendar_exceptions.py
    pytest tests/calendar/test_season_phase_tracker.py
"""

__version__ = "1.2.0"
__test_modules__ = [
    "test_date_models",
    "test_calendar_component",
    "test_calendar_exceptions",
    "test_season_phase_tracker"
]