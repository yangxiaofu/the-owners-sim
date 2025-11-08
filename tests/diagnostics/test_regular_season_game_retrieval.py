"""
Diagnostic test for regular season game retrieval bug.

Tests the exact flow from advance_day() → simulate_day() → _get_events_for_date()
to pinpoint where games are being lost.

Usage:
    PYTHONPATH=src python tests/diagnostics/test_regular_season_game_retrieval.py
"""
import sys
from pathlib import Path

# Add src and demo paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "demo" / "interactive_season_sim"))

from calendar.date_models import Date
from calendar.calendar_component import CalendarComponent
from calendar.simulation_executor import SimulationExecutor
from events.event_database_api import EventDatabaseAPI
from database.connection import DatabaseConnection
import sqlite3
import json


def test_game_retrieval(db_path: str, dynasty_id: str, test_date: Date):
    """
    Test if games can be found for a specific date.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty to test
        test_date: Date to test game retrieval for
    """
    print(f"\n{'=' * 80}")
    print(f"DIAGNOSTIC TEST: Regular Season Game Retrieval")
    print(f"{'=' * 80}")
    print(f"Database: {db_path}")
    print(f"Dynasty: {dynasty_id}")
    print(f"Test Date: {test_date}")

    # STEP 1: Check what games exist in database for this date
    print(f"\n[STEP 1] Querying database directly for games on {test_date}")
    print("-" * 80)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query for games on this specific date
    cursor.execute("""
        SELECT game_id, dynasty_id, data
        FROM events
        WHERE event_type = 'GAME'
        AND dynasty_id = ?
        AND (
            json_extract(data, '$.parameters.game_date') LIKE ?
            OR json_extract(data, '$.parameters.event_date') LIKE ?
        )
    """, (dynasty_id, f"{test_date}%", f"{test_date}%"))

    games_on_date = cursor.fetchall()
    print(f"  Games found in database for {test_date}: {len(games_on_date)}")

    if len(games_on_date) > 0:
        for game in games_on_date:
            data = json.loads(game['data'])
            params = data.get('parameters', {})
            print(f"    - {game['game_id']}")
            print(f"      Home: {params.get('home_team_id')} Away: {params.get('away_team_id')}")
            print(f"      Week: {params.get('week')} Season: {params.get('season')}")
    else:
        print(f"    ❌ No games found! Checking what dates DO have games...")

        # Find what dates have games
        cursor.execute("""
            SELECT
                json_extract(data, '$.parameters.game_date') as game_date,
                COUNT(*) as count
            FROM events
            WHERE event_type = 'GAME'
            AND dynasty_id = ?
            AND game_id LIKE 'game_%'
            GROUP BY game_date
            ORDER BY game_date
            LIMIT 10
        """, (dynasty_id,))

        dates_with_games = cursor.fetchall()
        print(f"\n    First 10 dates with regular season games:")
        for row in dates_with_games:
            print(f"      {row['game_date'][:10]}: {row['count']} games")

    conn.close()

    # STEP 2: Test calendar.get_phase_info()
    print(f"\n[STEP 2] Testing calendar phase_info")
    print("-" * 80)

    # Create event database API for phase detection
    event_db = EventDatabaseAPI(db_path)

    # Create calendar starting before test date with database API for event-based phase detection
    start_date = Date(test_date.year, test_date.month, max(1, test_date.day - 1))
    calendar = CalendarComponent(
        start_date=start_date,
        season_year=test_date.year,
        database_api=event_db,
        dynasty_id=dynasty_id
    )

    # Advance to test date
    calendar.advance(1)
    current_date = calendar.get_current_date()

    print(f"  Calendar current date: {current_date}")
    print(f"  Target test date: {test_date}")
    print(f"  Dates match: {str(current_date) == str(test_date)}")

    phase_info = calendar.get_phase_info()
    print(f"\n  phase_info keys: {list(phase_info.keys())}")
    print(f"  current_phase: {phase_info.get('current_phase')}")
    print(f"  season_year: {phase_info.get('season_year')}")
    print(f"  current_week: {phase_info.get('current_week')}")

    if 'season_year' not in phase_info:
        print(f"\n  ❌ WARNING: 'season_year' is MISSING from phase_info!")
        print(f"     This will cause season_year to fall back to cached value")

    # STEP 3: Test SimulationExecutor._get_events_for_date()
    print(f"\n[STEP 3] Testing SimulationExecutor._get_events_for_date()")
    print("-" * 80)

    # Use the same event_db instance created in STEP 2
    executor = SimulationExecutor(
        calendar=calendar,
        event_db=event_db,
        database_path=db_path,
        dynasty_id=dynasty_id,
        enable_persistence=False,
        season_year=test_date.year,
        verbose_logging=True  # Enable diagnostic output
    )

    print(f"  executor.season_year (cached at init): {executor.season_year}")
    print(f"  executor.dynasty_id: {executor.dynasty_id}")
    print(f"\n  Calling _get_events_for_date({test_date})...")

    # This will print diagnostic output due to verbose_logging=True
    events_for_date = executor._get_events_for_date(test_date)

    print(f"\n  → Events returned: {len(events_for_date)}")

    if len(events_for_date) > 0:
        print(f"  ✅ SUCCESS: Found {len(events_for_date)} events")
        for idx, evt in enumerate(events_for_date[:5], 1):
            event_type = evt.get('event_type', 'UNKNOWN')
            game_id = evt.get('game_id', 'N/A')
            print(f"    {idx}. {event_type}: {game_id}")
    else:
        print(f"  ❌ FAILURE: No events found!")

    # STEP 4: Test simulate_day()
    print(f"\n[STEP 4] Testing SimulationExecutor.simulate_day()")
    print("-" * 80)

    result = executor.simulate_day(test_date)

    print(f"  simulate_day() result:")
    print(f"    success: {result.get('success')}")
    print(f"    events_count: {result.get('events_count')}")
    print(f"    games_played: {len(result.get('games_played', []))}")
    print(f"    errors: {result.get('errors', [])}")

    if result.get('events_count', 0) == 0:
        print(f"\n  ❌ FAILURE: simulate_day() found 0 events")
        print(f"\n  ROOT CAUSE ANALYSIS:")
        print(f"    1. Check if games exist in DB for {test_date}: {len(games_on_date) > 0}")
        print(f"    2. Check if phase_info has season_year: {'season_year' in phase_info}")
        print(f"    3. Check _get_events_for_date() returned events: {len(events_for_date) > 0}")

        if len(games_on_date) > 0 and len(events_for_date) == 0:
            print(f"\n  🔍 IDENTIFIED ISSUE:")
            print(f"     Games exist in database but _get_events_for_date() didn't find them")
            print(f"     Check the diagnostic output above for year_prefix mismatch")
    else:
        print(f"  ✅ SUCCESS: simulate_day() processed {result.get('events_count')} events")

    print(f"\n{'=' * 80}")
    print(f"DIAGNOSTIC TEST COMPLETE")
    print(f"{'=' * 80}\n")

    return {
        'games_in_db': len(games_on_date),
        'events_found': len(events_for_date),
        'events_simulated': result.get('events_count', 0),
        'phase_has_season_year': 'season_year' in phase_info,
        'success': len(events_for_date) == len(games_on_date) and result.get('success', False)
    }


def run_interactive_test():
    """Interactive test that prompts for dynasty and date."""
    import os

    db_path = "data/database/nfl_simulation.db"

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print(f"   Please run from project root directory")
        return

    print("\n" + "=" * 80)
    print("INTERACTIVE DIAGNOSTIC TEST")
    print("=" * 80)

    # Get list of dynasties
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dynasty_id FROM events ORDER BY dynasty_id")
    dynasties = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not dynasties:
        print(f"❌ No dynasties found in database")
        return

    print(f"\nAvailable dynasties:")
    for idx, dynasty in enumerate(dynasties, 1):
        print(f"  {idx}. {dynasty}")

    # Get user input
    dynasty_id = input(f"\nEnter dynasty ID (or press Enter for '{dynasties[0]}'): ").strip()
    if not dynasty_id:
        dynasty_id = dynasties[0]

    date_input = input(f"Enter test date (YYYY-MM-DD) or press Enter for 2025-09-05: ").strip()
    if not date_input:
        test_date = Date(2025, 9, 5)
    else:
        try:
            year, month, day = map(int, date_input.split('-'))
            test_date = Date(year, month, day)
        except ValueError:
            print(f"❌ Invalid date format. Using 2025-09-05")
            test_date = Date(2025, 9, 5)

    # Run test
    result = test_game_retrieval(db_path, dynasty_id, test_date)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"  Games in database:        {result['games_in_db']}")
    print(f"  Events found by executor: {result['events_found']}")
    print(f"  Events simulated:         {result['events_simulated']}")
    print(f"  Phase has season_year:    {result['phase_has_season_year']}")
    print(f"  Overall success:          {'✅ PASS' if result['success'] else '❌ FAIL'}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_interactive_test()
