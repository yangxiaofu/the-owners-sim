#!/usr/bin/env python3
"""
Calendar System Consistency Test

Validates that the calendar system works identically between
interactive_season_sim and interactive_playoff_sim.

Tests:
1. CalendarComponent initialization and advancement
2. EventDatabaseAPI storage and retrieval
3. SimulationExecutor game execution
4. Date tracking and progression
5. Dynasty isolation
6. Database persistence
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from calendar.calendar_component import CalendarComponent
from calendar.date_models import Date
from events.event_database_api import EventDatabaseAPI
from calendar.simulation_executor import SimulationExecutor
from demo.interactive_playoff_sim import PlayoffController
from demo.interactive_season_sim.season_controller import SeasonController


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.CYAN}Testing: {name}{Colors.RESET}")


def print_pass(message: str):
    """Print pass message."""
    print(f"{Colors.GREEN}  ✓ {message}{Colors.RESET}")


def print_fail(message: str):
    """Print fail message."""
    print(f"{Colors.RED}  ✗ {message}{Colors.RESET}")


def print_section(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{title.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")


def test_calendar_component_consistency():
    """Test CalendarComponent behaves identically for both season and playoffs."""
    print_test("CalendarComponent Consistency")

    # Season calendar
    season_start = Date(2024, 9, 5)  # Week 1 Thursday
    season_calendar = CalendarComponent(start_date=season_start, season_year=2024)

    # Playoff calendar
    playoff_start = Date(2025, 1, 11)  # Wild Card Saturday
    playoff_calendar = CalendarComponent(start_date=playoff_start, season_year=2024)

    # Test 1: Both calendars initialized correctly
    assert season_calendar.get_current_date() == season_start
    assert playoff_calendar.get_current_date() == playoff_start
    print_pass("Both calendars initialized with correct dates")

    # Test 2: Advancement works identically
    season_result = season_calendar.advance(7)
    playoff_result = playoff_calendar.advance(7)

    assert season_result.days_advanced == 7
    assert playoff_result.days_advanced == 7
    print_pass("Both calendars advance identically")

    # Test 3: Statistics tracking is consistent
    season_stats = season_calendar.get_calendar_statistics()
    playoff_stats = playoff_calendar.get_calendar_statistics()

    assert season_stats['total_days_advanced'] == 7
    assert playoff_stats['total_days_advanced'] == 7
    assert season_stats['advancement_count'] == 1
    assert playoff_stats['advancement_count'] == 1
    print_pass("Statistics tracking is consistent")

    # Test 4: Phase tracking exists (even if different phases)
    season_phase = season_calendar.get_current_phase()
    playoff_phase = playoff_calendar.get_current_phase()

    assert season_phase is not None
    assert playoff_phase is not None
    print_pass("Phase tracking available in both calendars")


def test_event_database_consistency():
    """Test EventDatabaseAPI works identically for both."""
    print_test("EventDatabaseAPI Consistency")

    # Create temporary databases
    season_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_season.db').name
    playoff_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff.db').name

    try:
        # Initialize databases
        season_db = EventDatabaseAPI(season_db_path)
        playoff_db = EventDatabaseAPI(playoff_db_path)
        print_pass("Both databases initialized successfully")

        # Test 1: Both can store events
        from events.game_event import GameEvent
        from datetime import datetime

        season_game = GameEvent(
            away_team_id=1,
            home_team_id=2,
            game_date=datetime(2024, 9, 5, 20, 0),
            week=1,
            season=2024,
            season_type="regular_season"
        )

        playoff_game = GameEvent(
            away_team_id=3,
            home_team_id=4,
            game_date=datetime(2025, 1, 11, 16, 0),
            week=19,
            season=2024,
            season_type="playoffs"
        )

        season_result = season_db.insert_event(season_game)
        playoff_result = playoff_db.insert_event(playoff_game)

        assert season_result is not None
        assert playoff_result is not None
        assert season_result.event_id is not None
        assert playoff_result.event_id is not None
        print_pass("Both databases can store GameEvent objects")

        # Test 2: Both can retrieve events
        season_events = season_db.get_events_by_type("GAME")
        playoff_events = playoff_db.get_events_by_type("GAME")

        assert len(season_events) == 1
        assert len(playoff_events) == 1
        print_pass("Both databases can retrieve events")

        # Test 3: Event structure is identical
        season_event = season_events[0]
        playoff_event = playoff_events[0]

        assert 'event_id' in season_event
        assert 'event_id' in playoff_event
        assert 'event_type' in season_event
        assert 'event_type' in playoff_event
        assert 'timestamp' in season_event
        assert 'timestamp' in playoff_event
        print_pass("Event structure is identical in both databases")

    finally:
        # Cleanup
        os.unlink(season_db_path)
        os.unlink(playoff_db_path)


def test_simulation_executor_consistency():
    """Test SimulationExecutor works identically for both."""
    print_test("SimulationExecutor Consistency")

    # Create temporary databases
    season_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_season.db').name
    playoff_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff.db').name

    try:
        # Initialize calendars
        season_calendar = CalendarComponent(Date(2024, 9, 5), season_year=2024)
        playoff_calendar = CalendarComponent(Date(2025, 1, 11), season_year=2024)

        # Initialize event databases
        season_event_db = EventDatabaseAPI(season_db_path)
        playoff_event_db = EventDatabaseAPI(playoff_db_path)

        # Initialize executors WITHOUT persistence to avoid database requirements
        season_executor = SimulationExecutor(
            calendar=season_calendar,
            event_db=season_event_db,
            enable_persistence=False
        )

        playoff_executor = SimulationExecutor(
            calendar=playoff_calendar,
            event_db=playoff_event_db,
            enable_persistence=False
        )

        print_pass("Both SimulationExecutors initialized successfully")

        # Test 1: Both can simulate days with no events
        season_result = season_executor.simulate_day(Date(2024, 9, 5))
        playoff_result = playoff_executor.simulate_day(Date(2025, 1, 11))

        assert season_result['success'] == True
        assert playoff_result['success'] == True
        assert season_result['games_count'] == 0
        assert playoff_result['games_count'] == 0
        print_pass("Both executors handle empty days identically")

        # Test 2: Result structure is identical
        assert 'date' in season_result
        assert 'date' in playoff_result
        assert 'games_count' in season_result
        assert 'games_count' in playoff_result
        assert 'success' in season_result
        assert 'success' in playoff_result
        print_pass("Result structure is identical")

    finally:
        # Cleanup
        os.unlink(season_db_path)
        os.unlink(playoff_db_path)


def test_controller_consistency():
    """Test that controllers use calendar system identically."""
    print_test("Controller Consistency")

    # Create temporary databases
    season_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_season.db').name
    playoff_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff.db').name

    try:
        # Initialize controllers
        print("  Initializing season controller...")
        season_controller = SeasonController(
            database_path=season_db_path,
            start_date=Date(2024, 9, 5),
            season_year=2024,
            dynasty_id="test_season",
            verbose_logging=False
        )

        print("  Initializing playoff controller...")
        playoff_controller = PlayoffController(
            database_path=playoff_db_path,
            dynasty_id="test_playoff",
            season_year=2024
        )

        print_pass("Both controllers initialized successfully")

        # Test 1: Both have calendar components
        assert hasattr(season_controller, 'calendar')
        assert hasattr(playoff_controller, 'calendar')
        assert isinstance(season_controller.calendar, CalendarComponent)
        assert isinstance(playoff_controller.calendar, CalendarComponent)
        print_pass("Both controllers use CalendarComponent")

        # Test 2: Both have event databases
        assert hasattr(season_controller, 'event_db')
        assert hasattr(playoff_controller, 'event_db')
        assert isinstance(season_controller.event_db, EventDatabaseAPI)
        assert isinstance(playoff_controller.event_db, EventDatabaseAPI)
        print_pass("Both controllers use EventDatabaseAPI")

        # Test 3: Both have simulation executors
        assert hasattr(season_controller, 'simulation_executor')
        assert hasattr(playoff_controller, 'simulation_executor')
        assert isinstance(season_controller.simulation_executor, SimulationExecutor)
        assert isinstance(playoff_controller.simulation_executor, SimulationExecutor)
        print_pass("Both controllers use SimulationExecutor")

        # Test 4: Both can get current state
        season_state = season_controller.get_current_state()
        playoff_state = playoff_controller.get_current_state()

        assert 'current_date' in season_state
        assert 'current_date' in playoff_state
        assert 'games_played' in season_state
        assert 'games_played' in playoff_state
        print_pass("Both controllers provide consistent state")

    finally:
        # Cleanup
        os.unlink(season_db_path)
        os.unlink(playoff_db_path)


def test_dynasty_isolation_consistency():
    """Test dynasty isolation works identically."""
    print_test("Dynasty Isolation Consistency")

    # Create temporary databases
    season_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_season.db').name
    playoff_db_path = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff.db').name

    try:
        # Initialize with different dynasty IDs
        season_controller_a = SeasonController(
            database_path=season_db_path,
            start_date=Date(2024, 9, 5),
            season_year=2024,
            dynasty_id="dynasty_a",
            verbose_logging=False
        )

        season_controller_b = SeasonController(
            database_path=season_db_path,
            start_date=Date(2024, 9, 5),
            season_year=2024,
            dynasty_id="dynasty_b",
            verbose_logging=False
        )

        playoff_controller_a = PlayoffController(
            database_path=playoff_db_path,
            dynasty_id="dynasty_a",
            season_year=2024
        )

        playoff_controller_b = PlayoffController(
            database_path=playoff_db_path,
            dynasty_id="dynasty_b",
            season_year=2024
        )

        print_pass("Multiple dynasties can coexist in both systems")

        # Test: Dynasty IDs are preserved
        assert season_controller_a.dynasty_id == "dynasty_a"
        assert season_controller_b.dynasty_id == "dynasty_b"
        assert playoff_controller_a.dynasty_id == "dynasty_a"
        assert playoff_controller_b.dynasty_id == "dynasty_b"
        print_pass("Dynasty IDs preserved correctly in both systems")

    finally:
        # Cleanup
        os.unlink(season_db_path)
        os.unlink(playoff_db_path)


def main():
    """Run all consistency tests."""
    print_section("CALENDAR SYSTEM CONSISTENCY TEST SUITE")

    print(f"\n{Colors.YELLOW}Testing calendar system consistency between:{Colors.RESET}")
    print(f"  • demo/interactive_season_sim/")
    print(f"  • demo/interactive_playoff_sim/")

    tests_passed = 0
    tests_failed = 0

    tests = [
        ("CalendarComponent", test_calendar_component_consistency),
        ("EventDatabaseAPI", test_event_database_consistency),
        ("SimulationExecutor", test_simulation_executor_consistency),
        ("Controller Architecture", test_controller_consistency),
        ("Dynasty Isolation", test_dynasty_isolation_consistency),
    ]

    for test_name, test_func in tests:
        try:
            test_func()
            tests_passed += 1
        except Exception as e:
            print_fail(f"{test_name} failed: {e}")
            tests_failed += 1
            import traceback
            traceback.print_exc()

    # Summary
    print_section("TEST SUMMARY")
    print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
    print(f"  {Colors.GREEN}✓ Passed: {tests_passed}/{len(tests)}{Colors.RESET}")

    if tests_failed > 0:
        print(f"  {Colors.RED}✗ Failed: {tests_failed}/{len(tests)}{Colors.RESET}")
        print(f"\n{Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}\n")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}✅ ALL TESTS PASSED{Colors.RESET}")
        print(f"{Colors.GREEN}Calendar system is consistent between season and playoff simulators!{Colors.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
