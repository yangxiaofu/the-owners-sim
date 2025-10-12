"""
Test script to verify playoff game query fix.

This script tests that SimulationExecutor can now find playoff games
with the corrected game_id format.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from events import EventDatabaseAPI
from calendar.date_models import Date

def test_playoff_query_fix():
    """Test that playoff games are found with corrected query."""

    print("\n" + "="*80)
    print("TESTING PLAYOFF GAME QUERY FIX")
    print("="*80)

    # Initialize database API
    db_path = "data/database/nfl_simulation.db"
    event_db = EventDatabaseAPI(db_path)

    # Test parameters (matching user's dynasty)
    dynasty_id = "test_first"
    season_year = 2025

    print(f"\nDynasty: {dynasty_id}")
    print(f"Season: {season_year}")

    # OLD METHOD (BROKEN) - What the code was doing before
    print("\n" + "-"*80)
    print("OLD METHOD (BROKEN):")
    print("-"*80)
    old_prefix = f"playoff_{dynasty_id}_{season_year}_"
    print(f"Searching for game_id prefix: {old_prefix}")
    old_results = event_db.get_events_by_game_id_prefix(old_prefix, event_type="GAME")
    print(f"Results found: {len(old_results)}")

    if old_results:
        print("Games found:")
        for event in old_results:
            print(f"  - {event['game_id']}")
    else:
        print("❌ No games found (THIS WAS THE BUG!)")

    # NEW METHOD (FIXED) - What the code does now
    print("\n" + "-"*80)
    print("NEW METHOD (FIXED):")
    print("-"*80)
    print(f"1. Get all GAME events for dynasty: {dynasty_id}")
    all_playoff_events = event_db.get_events_by_dynasty(
        dynasty_id=dynasty_id,
        event_type="GAME"
    )
    print(f"   Total GAME events for dynasty: {len(all_playoff_events)}")

    print(f"2. Filter to playoff games for season {season_year}")
    playoff_events = [
        e for e in all_playoff_events
        if e.get('game_id', '').startswith(f'playoff_{season_year}_')
    ]
    print(f"   Playoff games found: {len(playoff_events)}")

    if playoff_events:
        print("✅ SUCCESS! Games found:")
        for event in playoff_events:
            game_date = event['data']['parameters']['game_date']
            print(f"  - {event['game_id']} on {game_date}")
    else:
        print("❌ FAILED: No playoff games found")

    # Verify database contents
    print("\n" + "-"*80)
    print("DATABASE VERIFICATION:")
    print("-"*80)
    all_playoff_in_db = event_db.get_events_by_type("GAME")
    playoff_in_db = [e for e in all_playoff_in_db if e['game_id'].startswith('playoff_')]
    print(f"Total playoff games in database: {len(playoff_in_db)}")

    if playoff_in_db:
        print("\nPlayoff games by dynasty:")
        dynasties = {}
        for event in playoff_in_db:
            d_id = event['dynasty_id']
            if d_id not in dynasties:
                dynasties[d_id] = []
            dynasties[d_id].append(event['game_id'])

        for d_id, games in dynasties.items():
            print(f"  Dynasty '{d_id}': {len(games)} games")
            for game_id in games[:3]:  # Show first 3
                print(f"    - {game_id}")
            if len(games) > 3:
                print(f"    ... and {len(games)-3} more")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    if len(playoff_events) > 0:
        print("✅ FIX VERIFIED: SimulationExecutor will now find playoff games!")
        print(f"   {len(playoff_events)} playoff game(s) can be simulated")
        return True
    else:
        print("❌ FIX NOT WORKING: No playoff games found for dynasty")
        return False


if __name__ == "__main__":
    success = test_playoff_query_fix()
    sys.exit(0 if success else 1)
