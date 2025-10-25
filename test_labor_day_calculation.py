#!/usr/bin/env python3
"""
Test Labor Day and Regular Season Start Calculation

Verifies that the dynamic Labor Day calculation produces correct dates
for multiple years and that the regular season starts on the first
Thursday after Labor Day.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scheduling import RandomScheduleGenerator
from datetime import datetime


def test_labor_day_calculation():
    """Test Labor Day calculation for years 2024-2030."""
    print("="*80)
    print("LABOR DAY CALCULATION TEST".center(80))
    print("="*80)
    print()

    # Expected Labor Day dates (verified from calendar)
    expected_labor_days = {
        2024: (9, 2),   # September 2, 2024 (Monday)
        2025: (9, 1),   # September 1, 2025 (Monday)
        2026: (9, 7),   # September 7, 2026 (Monday)
        2027: (9, 6),   # September 6, 2027 (Monday)
        2028: (9, 4),   # September 4, 2028 (Monday)
        2029: (9, 3),   # September 3, 2029 (Monday)
        2030: (9, 2),   # September 2, 2030 (Monday)
    }

    # Expected regular season start dates (first Thursday after Labor Day)
    expected_season_starts = {
        2024: (9, 5),   # September 5, 2024 (Thursday)
        2025: (9, 4),   # September 4, 2025 (Thursday)
        2026: (9, 10),  # September 10, 2026 (Thursday)
        2027: (9, 9),   # September 9, 2027 (Thursday)
        2028: (9, 7),   # September 7, 2028 (Thursday)
        2029: (9, 6),   # September 6, 2029 (Thursday)
        2030: (9, 5),   # September 5, 2030 (Thursday)
    }

    all_passed = True

    for year in range(2024, 2031):
        print(f"\nYear {year}:")
        print("-" * 80)

        # Calculate Labor Day
        labor_day = RandomScheduleGenerator._calculate_labor_day(year)
        expected_month, expected_day = expected_labor_days[year]

        # Verify Labor Day is a Monday
        if labor_day.weekday() != 0:
            print(f"  ❌ FAILED: Labor Day is not a Monday (weekday={labor_day.weekday()})")
            all_passed = False
        else:
            print(f"  ✓ Labor Day is Monday (weekday={labor_day.weekday()})")

        # Verify Labor Day date is correct
        if labor_day.month != expected_month or labor_day.day != expected_day:
            print(f"  ❌ FAILED: Labor Day date incorrect")
            print(f"     Expected: {expected_month}/{expected_day}")
            print(f"     Got: {labor_day.month}/{labor_day.day}")
            all_passed = False
        else:
            print(f"  ✓ Labor Day date correct: {labor_day.strftime('%B %d, %Y')}")

        # Calculate regular season start
        season_start = RandomScheduleGenerator._calculate_regular_season_start(year)
        expected_month, expected_day = expected_season_starts[year]

        # Verify season start is a Thursday
        if season_start.weekday() != 3:
            print(f"  ❌ FAILED: Season start is not a Thursday (weekday={season_start.weekday()})")
            all_passed = False
        else:
            print(f"  ✓ Season start is Thursday (weekday={season_start.weekday()})")

        # Verify season start date is correct
        if season_start.month != expected_month or season_start.day != expected_day:
            print(f"  ❌ FAILED: Season start date incorrect")
            print(f"     Expected: {expected_month}/{expected_day}")
            print(f"     Got: {season_start.month}/{season_start.day}")
            all_passed = False
        else:
            print(f"  ✓ Season start date correct: {season_start.strftime('%B %d, %Y')}")

        # Verify season start time is 8:00 PM
        if season_start.hour != 20 or season_start.minute != 0:
            print(f"  ❌ FAILED: Season start time incorrect (expected 20:00, got {season_start.hour}:{season_start.minute:02d})")
            all_passed = False
        else:
            print(f"  ✓ Season start time correct: {season_start.strftime('%I:%M %p')}")

        # Verify season starts AFTER Labor Day
        days_after = (season_start - labor_day).days
        if days_after != 3:
            print(f"  ❌ FAILED: Season doesn't start 3 days after Labor Day (got {days_after} days)")
            all_passed = False
        else:
            print(f"  ✓ Season starts 3 days after Labor Day")

    print()
    print("="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED".center(80))
    else:
        print("❌ SOME TESTS FAILED".center(80))
    print("="*80)
    print()

    return all_passed


def test_preseason_start_calculation():
    """Test preseason start calculation for years 2024-2030."""
    print("="*80)
    print("PRESEASON START CALCULATION TEST".center(80))
    print("="*80)
    print()

    # We need an event_db for the generator (use in-memory)
    from events.event_database_api import EventDatabaseAPI
    event_db = EventDatabaseAPI(":memory:")
    generator = RandomScheduleGenerator(event_db, "test_dynasty")

    all_passed = True

    for year in range(2024, 2031):
        print(f"\nYear {year}:")
        print("-" * 80)

        # Calculate dates
        preseason_start = generator._calculate_preseason_start(year)
        regular_season_start = generator._calculate_regular_season_start(year)

        print(f"  Preseason starts: {preseason_start.strftime('%A, %B %d, %Y at %I:%M %p')}")
        print(f"  Regular season starts: {regular_season_start.strftime('%A, %B %d, %Y at %I:%M %p')}")

        # Verify preseason start is a Thursday
        if preseason_start.weekday() != 3:
            print(f"  ❌ FAILED: Preseason start is not a Thursday (weekday={preseason_start.weekday()})")
            all_passed = False
        else:
            print(f"  ✓ Preseason start is Thursday")

        # Verify preseason starts ~3.5 weeks before regular season
        days_diff = (regular_season_start - preseason_start).days
        if not (20 <= days_diff <= 30):
            print(f"  ❌ FAILED: Preseason doesn't start ~3.5 weeks before regular season (got {days_diff} days)")
            all_passed = False
        else:
            print(f"  ✓ Preseason starts {days_diff} days before regular season (~3.5 weeks)")

        # Verify preseason time is 8:00 PM
        if preseason_start.hour != 20 or preseason_start.minute != 0:
            print(f"  ❌ FAILED: Preseason start time incorrect (expected 20:00, got {preseason_start.hour}:{preseason_start.minute:02d})")
            all_passed = False
        else:
            print(f"  ✓ Preseason start time correct: {preseason_start.strftime('%I:%M %p')}")

    print()
    print("="*80)
    if all_passed:
        print("✅ ALL PRESEASON TESTS PASSED".center(80))
    else:
        print("❌ SOME PRESEASON TESTS FAILED".center(80))
    print("="*80)
    print()

    return all_passed


if __name__ == "__main__":
    print()
    print("╔" + "="*78 + "╗")
    print("║" + "NFL SCHEDULE DATE CALCULATION TEST SUITE".center(78) + "║")
    print("╚" + "="*78 + "╝")
    print()

    # Run both tests
    labor_day_passed = test_labor_day_calculation()
    preseason_passed = test_preseason_start_calculation()

    # Final summary
    print()
    print("="*80)
    print("FINAL RESULTS".center(80))
    print("="*80)
    print(f"  Labor Day Calculation: {'✅ PASSED' if labor_day_passed else '❌ FAILED'}")
    print(f"  Preseason Start Calculation: {'✅ PASSED' if preseason_passed else '❌ FAILED'}")
    print("="*80)
    print()

    # Exit with appropriate code
    if labor_day_passed and preseason_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
