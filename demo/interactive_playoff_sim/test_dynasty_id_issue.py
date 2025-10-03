#!/usr/bin/env python3
"""
Test Dynasty ID Issue

Reproduces the exact issue the user is experiencing with dynasty IDs
that start with "playoff_" causing double prefix problems.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def test_with_playoff_prefix_dynasty():
    """Test with dynasty_id that starts with 'playoff_' (the problematic case)."""
    print("\n" + "="*80)
    print("TEST 1: Dynasty ID with 'playoff_' prefix (PROBLEMATIC)")
    print("="*80)

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff_prefix.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Use a dynasty_id that starts with "playoff_" (like the auto-generated ones)
        dynasty_id = "playoff_dynasty_20251003_140000"

        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id=dynasty_id,
            season_year=2024,
            verbose_logging=False
        )

        print(f"\nDynasty ID: {dynasty_id}")

        # Simulate Wild Card
        print("\n1. Simulating Wild Card...")
        wc_result = controller.advance_to_next_round()
        print(f"   Wild Card: {wc_result['games_played']} games")

        # Check what game_ids were created
        wc_games = controller.completed_games['wild_card']
        if wc_games:
            sample_game_id = wc_games[0].get('game_id', 'NO ID')
            print(f"   Sample Wild Card game_id: {sample_game_id}")

            # Test detection
            detected = controller._detect_game_round(sample_game_id)
            print(f"   Detected round: {detected}")

        # Check if Divisional was scheduled
        from events.event_database_api import EventDatabaseAPI
        event_db = EventDatabaseAPI(temp_db_path)

        div_prefix = f"playoff_{dynasty_id}_2024_divisional_"
        print(f"\n2. Checking for Divisional events with prefix: {div_prefix}")

        div_events = event_db.get_events_by_game_id_prefix(div_prefix, event_type="GAME")
        print(f"   Divisional events found: {len(div_events)}")

        if div_events:
            sample_div_id = div_events[0].get('game_id', 'NO ID')
            print(f"   Sample Divisional game_id: {sample_div_id}")

            # Check if double prefix exists
            if sample_div_id.startswith("playoff_playoff_"):
                print(f"   ⚠️  DOUBLE PREFIX DETECTED: {sample_div_id[:30]}...")

        # Try to simulate Divisional
        print("\n3. Attempting to simulate Divisional...")
        div_result = controller.advance_to_next_round()
        print(f"   Divisional: {div_result['games_played']} games")
        print(f"   Days simulated: {div_result['days_simulated']}")

        # Check state
        state = controller.get_current_state()
        print(f"\n4. Final State:")
        print(f"   current_round: {state['current_round']}")
        print(f"   active_round: {state['active_round']}")
        print(f"   current_date: {state['current_date']}")

        # Check completed games
        div_completed = controller.completed_games['divisional']
        print(f"   Divisional completed games: {len(div_completed)}")

        if div_result['games_played'] == 0:
            print("\n❌ PROBLEM REPRODUCED: Divisional games did not simulate!")
            return False
        else:
            print("\n✅ Divisional games simulated successfully")
            return True

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def test_with_normal_dynasty():
    """Test with dynasty_id that does NOT start with 'playoff_' (the fix)."""
    print("\n" + "="*80)
    print("TEST 2: Dynasty ID WITHOUT 'playoff_' prefix (FIXED)")
    print("="*80)

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_normal.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Use a dynasty_id that does NOT start with "playoff_"
        dynasty_id = "dynasty_20251003_140000"

        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id=dynasty_id,
            season_year=2024,
            verbose_logging=False
        )

        print(f"\nDynasty ID: {dynasty_id}")

        # Simulate Wild Card
        print("\n1. Simulating Wild Card...")
        wc_result = controller.advance_to_next_round()
        print(f"   Wild Card: {wc_result['games_played']} games")

        # Check what game_ids were created
        wc_games = controller.completed_games['wild_card']
        if wc_games:
            sample_game_id = wc_games[0].get('game_id', 'NO ID')
            print(f"   Sample Wild Card game_id: {sample_game_id}")

            # Check for double prefix
            if sample_game_id.startswith("playoff_playoff_"):
                print(f"   ⚠️  DOUBLE PREFIX: {sample_game_id[:30]}...")
            else:
                print(f"   ✅ Single prefix (correct)")

        # Try to simulate Divisional
        print("\n2. Attempting to simulate Divisional...")
        div_result = controller.advance_to_next_round()
        print(f"   Divisional: {div_result['games_played']} games")
        print(f"   Days simulated: {div_result['days_simulated']}")

        # Check state
        state = controller.get_current_state()
        print(f"\n3. Final State:")
        print(f"   current_round: {state['current_round']}")
        print(f"   active_round: {state['active_round']}")

        # Check completed games
        div_completed = controller.completed_games['divisional']
        print(f"   Divisional completed games: {len(div_completed)}")

        if div_result['games_played'] == 0:
            print("\n❌ Problem still exists with normal dynasty ID")
            return False
        else:
            print("\n✅ Divisional games simulated successfully")
            return True

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def test_event_retrieval_with_double_prefix():
    """Test if event retrieval works with double playoff_ prefix."""
    print("\n" + "="*80)
    print("TEST 3: Event Retrieval with Double Prefix")
    print("="*80)

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_retrieval.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        dynasty_id = "playoff_test_dynasty"

        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id=dynasty_id,
            season_year=2024,
            verbose_logging=False
        )

        print(f"\nDynasty ID: {dynasty_id}")

        # Simulate Wild Card
        wc_result = controller.advance_to_next_round()
        print(f"\nWild Card simulated: {wc_result['games_played']} games")

        # Check how simulation_executor retrieves events
        from calendar.date_models import Date

        # Get the date Divisional should be on
        div_date = Date(2025, 1, 18)
        print(f"\nChecking events for Divisional date: {div_date}")

        # Use the simulation executor's method
        events = controller.simulation_executor._get_events_for_date(div_date)
        print(f"Events found for {div_date}: {len(events)}")

        for event in events:
            game_id = event.get('game_id', 'NO ID')
            print(f"  - {game_id}")

            # Check if it's a divisional game
            if 'divisional' in game_id:
                print(f"    ✅ Divisional game found!")

                # Check the data structure
                params = event['data'].get('parameters', {})
                game_date = params.get('game_date', 'NO DATE')
                print(f"    game_date from params: {game_date}")

        # Now simulate Divisional
        print(f"\nSimulating Divisional...")
        div_result = controller.advance_to_next_round()
        print(f"Divisional simulated: {div_result['games_played']} games")

        return div_result['games_played'] > 0

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def main():
    """Run all diagnostic tests."""
    print("\n" + "="*80)
    print("DYNASTY ID TROUBLESHOOTING TESTS")
    print("="*80)

    results = {}

    # Test 1: With playoff_ prefix (problematic)
    results['playoff_prefix'] = test_with_playoff_prefix_dynasty()

    # Test 2: Without playoff_ prefix (fixed)
    results['normal_prefix'] = test_with_normal_dynasty()

    # Test 3: Event retrieval mechanics
    results['event_retrieval'] = test_event_retrieval_with_double_prefix()

    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    print(f"\n1. Dynasty with 'playoff_' prefix: {'✅ PASS' if results['playoff_prefix'] else '❌ FAIL'}")
    print(f"2. Dynasty without 'playoff_' prefix: {'✅ PASS' if results['normal_prefix'] else '❌ FAIL'}")
    print(f"3. Event retrieval with double prefix: {'✅ PASS' if results['event_retrieval'] else '❌ FAIL'}")

    if not results['playoff_prefix'] and results['normal_prefix']:
        print("\n🔍 ROOT CAUSE CONFIRMED:")
        print("   Dynasty IDs starting with 'playoff_' cause Divisional simulation failure!")
        print("   Fix: Change auto-generated dynasty IDs to NOT start with 'playoff_'")
    elif all(results.values()):
        print("\n✅ All tests passed - issue may be environmental or user-specific")
    else:
        print("\n⚠️  Mixed results - further investigation needed")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
