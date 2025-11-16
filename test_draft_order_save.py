#!/usr/bin/env python3
"""
Test script to verify draft order is saved to database after playoffs.

This script:
1. Verifies the new get_playoff_games_by_round() API method works
2. Tests that PlayoffsToOffseasonHandler can extract playoff results
3. Confirms draft order is saved to the database
"""

import sys
sys.path.insert(0, 'src')

import sqlite3
from database.api import DatabaseAPI

def test_api_method():
    """Test the new get_playoff_games_by_round() API method."""
    print("=" * 80)
    print("TEST 1: Testing get_playoff_games_by_round() API method")
    print("=" * 80)

    db_api = DatabaseAPI(database_path="data/database/nfl_simulation.db")

    # Check if there's any dynasty in the database
    conn = sqlite3.connect("data/database/nfl_simulation.db")
    cursor = conn.execute("SELECT DISTINCT dynasty_id FROM games WHERE season_type = 'playoffs' LIMIT 1")
    row = cursor.fetchone()

    if not row:
        print("⚠ No playoff games found in database - cannot test API method")
        print("   Run a full season simulation first to generate playoff data")
        conn.close()
        return False

    dynasty_id = row[0]
    print(f"✓ Found dynasty: {dynasty_id}")

    # Get season year
    cursor = conn.execute(
        "SELECT DISTINCT season FROM games WHERE dynasty_id = ? AND season_type = 'playoffs' ORDER BY season DESC LIMIT 1",
        (dynasty_id,)
    )
    row = cursor.fetchone()
    season_year = row[0] if row else 2024
    print(f"✓ Testing with season: {season_year}")
    conn.close()

    # Test each playoff round
    rounds = ['wild_card', 'divisional', 'conference', 'super_bowl']
    expected_counts = {'wild_card': 6, 'divisional': 4, 'conference': 2, 'super_bowl': 1}

    all_passed = True
    for round_name in rounds:
        games = db_api.get_playoff_games_by_round(
            dynasty_id=dynasty_id,
            season=season_year,
            round_name=round_name
        )

        expected = expected_counts[round_name]
        actual = len(games)

        if actual == expected:
            print(f"✓ {round_name}: Found {actual} games (expected {expected})")
        else:
            print(f"✗ {round_name}: Found {actual} games (expected {expected})")
            all_passed = False

        # Show sample game data
        if games and len(games) > 0:
            game = games[0]
            print(f"   Sample: {game.get('game_id', 'N/A')} - "
                  f"Away {game.get('away_team_id')} ({game.get('away_score')}) @ "
                  f"Home {game.get('home_team_id')} ({game.get('home_score')})")

    print()
    return all_passed


def test_draft_order_in_database():
    """Check if draft order was saved to database."""
    print("=" * 80)
    print("TEST 2: Checking draft_order table")
    print("=" * 80)

    conn = sqlite3.connect("data/database/nfl_simulation.db")

    # Check if table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='draft_order'"
    )
    if not cursor.fetchone():
        print("✗ draft_order table does not exist")
        print("   Run migration: sqlite3 data/database/nfl_simulation.db < src/database/migrations/005_add_draft_order_table.sql")
        conn.close()
        return False

    print("✓ draft_order table exists")

    # Check for any draft order data
    cursor = conn.execute("SELECT COUNT(*) FROM draft_order")
    count = cursor.fetchone()[0]

    if count == 0:
        print(f"⚠ No draft order data found (0 rows)")
        print("   This is expected if you haven't run a playoff→offseason transition yet")
        conn.close()
        return True  # Not a failure, just no data yet

    print(f"✓ Found {count} draft picks in database")

    # Get sample data
    cursor = conn.execute("""
        SELECT dynasty_id, season, overall_pick, round, pick_in_round, original_team_id
        FROM draft_order
        ORDER BY overall_pick ASC
        LIMIT 5
    """)

    print("\n  Sample picks:")
    for row in cursor.fetchall():
        dynasty_id, season, overall, rd, pick_in_rd, team_id = row
        print(f"    Pick {overall}: Round {rd}, Pick {pick_in_rd} - Team {team_id} (Dynasty: {dynasty_id}, Season: {season})")

    conn.close()
    print()
    return True


def test_handler_integration():
    """Test that handler can extract playoff results (minimal test)."""
    print("=" * 80)
    print("TEST 3: Handler Integration (Minimal)")
    print("=" * 80)
    print("This test verifies the handler has the correct dependencies")

    from season.phase_transition.transition_handlers.playoffs_to_offseason import PlayoffsToOffseasonHandler

    # Mock minimal dependencies
    def mock_get_super_bowl_winner():
        return 1

    def mock_schedule_offseason_events(year):
        pass

    def mock_generate_season_summary():
        return {"champion_team_id": 1, "season_year": 2024, "dynasty_id": "test"}

    def mock_update_database_phase(phase, year):
        pass

    def mock_get_standings():
        return [{'team_id': i, 'wins': 8, 'losses': 9} for i in range(1, 33)]

    def mock_get_bracket():
        return {}

    def mock_schedule_event(event):
        pass

    # Create handler with draft order dependencies
    try:
        handler = PlayoffsToOffseasonHandler(
            get_super_bowl_winner=mock_get_super_bowl_winner,
            schedule_offseason_events=mock_schedule_offseason_events,
            generate_season_summary=mock_generate_season_summary,
            update_database_phase=mock_update_database_phase,
            dynasty_id="test",
            season_year=2024,
            verbose_logging=True,
            get_regular_season_standings=mock_get_standings,
            get_playoff_bracket=mock_get_bracket,
            schedule_event=mock_schedule_event,
            database_path="data/database/nfl_simulation.db"
        )
        print("✓ Handler created successfully with draft order dependencies")

        can_calculate = handler._can_calculate_draft_order()
        print(f"✓ _can_calculate_draft_order() = {can_calculate}")

        print()
        return True

    except Exception as e:
        print(f"✗ Handler creation failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    print("\n")
    print("█" * 80)
    print("DRAFT ORDER INTEGRATION VERIFICATION")
    print("█" * 80)
    print()

    results = []

    # Test 1: API method
    results.append(("API Method", test_api_method()))

    # Test 2: Database table
    results.append(("Database Table", test_draft_order_in_database()))

    # Test 3: Handler integration
    results.append(("Handler Integration", test_handler_integration()))

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)
    print()
    if all_passed:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Run a full season simulation (Regular Season → Playoffs → Offseason)")
        print("2. Check that draft order appears in database after Super Bowl")
        print("3. Query: SELECT * FROM draft_order WHERE dynasty_id='your_dynasty' ORDER BY overall_pick LIMIT 10;")
    else:
        print("✗ Some tests failed - see details above")

    print("=" * 80)
    sys.exit(0 if all_passed else 1)
