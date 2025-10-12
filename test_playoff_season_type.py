"""
Test script to verify playoff games are saved with season_type='playoffs'.

This test simulates a single playoff game and verifies that:
1. The game is saved to the database
2. The season_type field is 'playoffs' (not 'regular_season')
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
import sqlite3

def test_playoff_season_type():
    """Test that playoff games are saved with season_type='playoffs'."""

    print("\n" + "="*80)
    print("TEST: Playoff Season Type Persistence")
    print("="*80 + "\n")

    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "1st"  # Use existing dynasty with rosters

    # Note: We'll use a unique test game date to identify our test game
    print("Using existing dynasty '1st' with initialized rosters\n")

    # Create a playoff game event with a test date far in the future
    print("Creating playoff game event...")
    game_date = datetime(2026, 2, 1, 13, 0)  # Use Feb 1 for test to avoid conflicts

    playoff_game = GameEvent(
        away_team_id=5,  # Bengals
        home_team_id=3,  # Bills
        game_date=game_date,
        week=19,  # Wild Card week
        dynasty_id=dynasty_id,
        season=2025,
        season_type="playoffs",  # ✅ Playoff game
        game_type="wildcard",
        overtime_type="playoffs"
    )

    print(f"✅ Created: {playoff_game}")
    print(f"   Season Type: {playoff_game.season_type}\n")

    # Store event in database
    print("Storing event in database...")
    event_db = EventDatabaseAPI(db_path)
    event_db.insert_event(playoff_game)
    print("✅ Event stored\n")

    # Simulate the game
    print("Simulating playoff game...")
    print("-" * 80)
    result = playoff_game.simulate()
    print("-" * 80)
    if result.success:
        print(f"✅ Game simulated successfully\n")
    else:
        print(f"❌ Game simulation failed: {result.error_message}\n")
        return False

    # Verify the game was saved to games table with correct season_type
    print("Verifying database entry...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT game_id, season_type, home_score, away_score, game_date
        FROM games
        WHERE dynasty_id = ?
        ORDER BY game_date DESC
        LIMIT 1
    """, (dynasty_id,))

    game_row = cursor.fetchone()
    conn.close()

    if game_row:
        game_id, season_type, home_score, away_score, game_date_ts = game_row
        print(f"Found game in database:")
        print(f"  Game ID: {game_id}")
        print(f"  Season Type: {season_type}")
        print(f"  Score: {away_score}-{home_score}")
        print(f"  Date: {datetime.fromtimestamp(game_date_ts / 1000)}\n")

        if season_type == "playoffs":
            print("✅ SUCCESS: Playoff game saved with season_type='playoffs'")
            print("\n" + "="*80)
            print("TEST PASSED")
            print("="*80 + "\n")
            return True
        else:
            print(f"❌ FAILURE: Expected season_type='playoffs', got '{season_type}'")
            print("\n" + "="*80)
            print("TEST FAILED")
            print("="*80 + "\n")
            return False
    else:
        print("❌ FAILURE: No game found in database")
        print("\n" + "="*80)
        print("TEST FAILED")
        print("="*80 + "\n")
        return False

if __name__ == "__main__":
    success = test_playoff_season_type()
    sys.exit(0 if success else 1)
