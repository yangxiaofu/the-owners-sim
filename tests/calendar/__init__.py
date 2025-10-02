"""
Calendar System Tests

Comprehensive test suite for the Calendar Manager Phase 1.1, 1.2, and 1.3 implementation.

This test suite provides complete coverage of the Calendar Manager system with organized
test categories as specified in the Phase 1.3 Basic Testing Framework plan.

## Test Categories

### Unit Tests (Individual method testing)
- test_date_models: Tests for Date and DateAdvanceResult classes
- test_calendar_exceptions: Tests for exception classes and handling
- test_date_utils: Tests for date arithmetic utilities and helper functions

### Integration Tests (Component interaction testing)
- test_calendar_component: Tests for CalendarComponent core functionality
- test_season_phase_tracker: Tests for season phase tracking and transitions
- test_season_structure: Tests for NFL season structure and phase logic

### Edge Case Tests (Boundary conditions and error scenarios)
All test modules include comprehensive edge case testing including:
- Leap year handling and February boundary conditions
- Year and month boundary transitions
- Invalid input validation and error handling
- Large date calculations and extreme values
- Thread safety and concurrent operations

## Test Modules

Core Calendar Framework (Phase 1.1):
- test_date_models: Date and DateAdvanceResult classes (24 tests)
- test_calendar_component: CalendarComponent functionality (35 tests)
- test_calendar_exceptions: Exception handling and error scenarios (37 tests)

Season Phase Management (Phase 1.2):
- test_season_phase_tracker: Event-driven phase tracking (23 tests)

Basic Testing Framework (Phase 1.3):
- test_season_structure: NFL season structure and phase logic (21 tests)
- test_date_utils: Date arithmetic utilities and helpers (27 tests)

## Usage

To run all calendar tests:
    pytest tests/calendar/

To run tests by category:
    pytest tests/calendar/test_date_models.py tests/calendar/test_calendar_exceptions.py tests/calendar/test_date_utils.py  # Unit tests
    pytest tests/calendar/test_calendar_component.py tests/calendar/test_season_phase_tracker.py tests/calendar/test_season_structure.py  # Integration tests

To run specific test module:
    pytest tests/calendar/test_date_models.py
    pytest tests/calendar/test_calendar_component.py
    pytest tests/calendar/test_calendar_exceptions.py
    pytest tests/calendar/test_season_phase_tracker.py
    pytest tests/calendar/test_season_structure.py
    pytest tests/calendar/test_date_utils.py

To run with verbose output:
    pytest tests/calendar/ -v

To run specific test patterns:
    pytest tests/calendar/ -k "leap_year"  # All leap year tests
    pytest tests/calendar/ -k "edge_case"  # All edge case tests
    pytest tests/calendar/ -k "season"     # All season-related tests
"""

__version__ = "1.3.0"
__test_modules__ = [
    # Unit Tests
    "test_date_models",
    "test_calendar_exceptions",
    "test_date_utils",
    # Integration Tests
    "test_calendar_component",
    "test_season_phase_tracker",
    "test_season_structure"
]

# Test categories for organized testing
__unit_tests__ = [
    "test_date_models",
    "test_calendar_exceptions",
    "test_date_utils"
]

__integration_tests__ = [
    "test_calendar_component",
    "test_season_phase_tracker",
    "test_season_structure"
]

# Test statistics
__total_tests__ = 167  # 24 + 35 + 37 + 23 + 21 + 27
__phase_1_1_tests__ = 96   # 24 + 35 + 37
__phase_1_2_tests__ = 23   # 23
__phase_1_3_tests__ = 48   # 21 + 27