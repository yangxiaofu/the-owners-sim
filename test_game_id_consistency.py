"""
Test script to verify game_id consistency between scheduled events and completed games.

This test verifies that:
1. GameEvent creates games with the correct game_id
2. SimulationWorkflow persists games with the SAME game_id
3. Calendar deduplication can match scheduled and completed games by game_id
"""

import sys
import os
from datetime import datetime

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from events.game_event import GameEvent
from events.event_database_api import EventDatabaseAPI
from workflows import SimulationWorkflow
import sqlite3

def test_game_id_consistency():
    """Test that game_id remains consistent from event creation to database persistence."""

    print("\n" + "="*80)
    print("TEST: Game ID Consistency (Event → Simulation → Database)")
    print("="*80 + "\n")

    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "1st"  # Use existing dynasty with rosters

    print("Using existing dynasty '1st' with initialized rosters\n")

    # Test 1: Playoff game with explicit game_id
    print("=" * 80)
    print("TEST 1: Playoff Game with Explicit game_id")
    print("=" * 80)

    playoff_game_id = "playoff_2025_test_wild_card_1"
    playoff_game = GameEvent(
        away_team_id=5,
        home_team_id=3,
        game_date=datetime(2026, 2, 10, 20, 0),  # Use future date to avoid conflicts
        week=19,
        dynasty_id=dynasty_id,
        season=2025,
        season_type="playoffs",
        game_type="wildcard",
        game_id=playoff_game_id  # Explicitly set
    )

    print(f"Created GameEvent with game_id: {playoff_game.get_game_id()}")
    assert playoff_game.get_game_id() == playoff_game_id, "GameEvent should store provided game_id"

    # Store event in database
    event_db = EventDatabaseAPI(db_path)
    event_db.insert_event(playoff_game)
    print(f"✅ Event stored in events table with game_id: {playoff_game_id}\n")

    # Simulate the game
    workflow = SimulationWorkflow(
        enable_persistence=True,
        database_path=db_path,
        dynasty_id=dynasty_id,
        verbose_logging=False
    )

    print("Simulating game...")
    result = workflow.execute(playoff_game)

    if not result.simulation_result.success:
        print(f"❌ Game simulation failed")
        return False

    print(f"✅ Game simulated successfully\n")

    # Check database for game_id
    print("Verifying database entry...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT game_id, season_type, away_score, home_score
        FROM games
        WHERE dynasty_id = ? AND game_id = ?
    """, (dynasty_id, playoff_game_id))

    game_row = cursor.fetchone()
    conn.close()

    if game_row:
        db_game_id, db_season_type, away_score, home_score = game_row
        print(f"Found game in database:")
        print(f"  game_id: {db_game_id}")
        print(f"  season_type: {db_season_type}")
        print(f"  score: {away_score}-{home_score}\n")

        if db_game_id == playoff_game_id:
            print("✅ SUCCESS: game_id matches between event and database!")
            print(f"   Expected: {playoff_game_id}")
            print(f"   Got:      {db_game_id}\n")
        else:
            print(f"❌ FAILURE: game_id mismatch!")
            print(f"   Expected: {playoff_game_id}")
            print(f"   Got:      {db_game_id}\n")
            return False

        if db_season_type == "playoffs":
            print("✅ SUCCESS: season_type is correct (playoffs)")
        else:
            print(f"❌ FAILURE: season_type is wrong (expected 'playoffs', got '{db_season_type}')")
            return False
    else:
        print(f"❌ FAILURE: No game found in database with game_id '{playoff_game_id}'")
        return False

    # Test 2: Regular season game with auto-generated game_id
    print("\n" + "=" * 80)
    print("TEST 2: Regular Season Game with Auto-Generated game_id")
    print("=" * 80)

    regular_game = GameEvent(
        away_team_id=7,
        home_team_id=10,
        game_date=datetime(2026, 2, 11, 13, 0),  # Use future date to avoid conflicts
        week=1,
        dynasty_id=dynasty_id,
        season=2025,
        season_type="regular_season"
        # No explicit game_id - should be auto-generated
    )

    auto_game_id = regular_game.get_game_id()
    print(f"Created GameEvent with auto-generated game_id: {auto_game_id}")
    print(f"  (Should be in format: game_YYYYMMDD_<away>_at_<home>)\n")

    # Store and simulate
    event_db.insert_event(regular_game)
    result = workflow.execute(regular_game)

    if not result.simulation_result.success:
        print(f"❌ Game simulation failed")
        return False

    print(f"✅ Game simulated successfully\n")

    # Check database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT game_id, season_type
        FROM games
        WHERE dynasty_id = ? AND game_id = ?
    """, (dynasty_id, auto_game_id))

    game_row = cursor.fetchone()
    conn.close()

    if game_row:
        db_game_id, db_season_type = game_row
        print(f"Found game in database:")
        print(f"  game_id: {db_game_id}")
        print(f"  season_type: {db_season_type}\n")

        if db_game_id == auto_game_id:
            print("✅ SUCCESS: Auto-generated game_id matches!")
            print(f"   Expected: {auto_game_id}")
            print(f"   Got:      {db_game_id}\n")
        else:
            print(f"❌ FAILURE: game_id mismatch!")
            print(f"   Expected: {auto_game_id}")
            print(f"   Got:      {db_game_id}\n")
            return False
    else:
        print(f"❌ FAILURE: No game found in database with game_id '{auto_game_id}'")
        return False

    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print("\n✅ game_id consistency verified!")
    print("   - Playoff games maintain explicit game_ids")
    print("   - Regular season games maintain auto-generated game_ids")
    print("   - Calendar deduplication will now work correctly\n")

    return True

if __name__ == "__main__":
    success = test_game_id_consistency()
    sys.exit(0 if success else 1)
