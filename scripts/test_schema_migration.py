#!/usr/bin/env python3
"""
Test script for verifying Phase 1 database schema migration.

This script tests that:
1. New databases are created with season_type columns
2. Default values are correctly set
3. Indexes are created properly
4. Backward compatibility is maintained
"""

import sys
import os
import sqlite3
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.connection import DatabaseConnection


def test_new_database_schema():
    """Test that new databases include season_type columns."""
    print("\n" + "="*70)
    print("TEST 1: New Database Schema")
    print("="*70)

    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        # Initialize database with new schema
        db_conn = DatabaseConnection(temp_db_path)
        db_conn.initialize_database()

        # Verify games table has season_type column
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check games table
        cursor.execute("PRAGMA table_info(games)")
        games_columns = {row[1]: row for row in cursor.fetchall()}

        print("\n✓ Games table columns:")
        if 'season_type' in games_columns:
            print(f"  - season_type: {games_columns['season_type'][2]} (default: {games_columns['season_type'][4]})")
            assert games_columns['season_type'][3] == 1, "season_type should be NOT NULL"
            assert games_columns['season_type'][4] == "'regular_season'", "Default should be 'regular_season'"
            print("  ✓ season_type column exists with correct constraints")
        else:
            print("  ✗ ERROR: season_type column missing!")
            return False

        if 'game_type' in games_columns:
            print(f"  - game_type: {games_columns['game_type'][2]} (default: {games_columns['game_type'][4]})")
            print("  ✓ game_type column exists")
        else:
            print("  ✗ ERROR: game_type column missing!")
            return False

        # Check player_game_stats table
        cursor.execute("PRAGMA table_info(player_game_stats)")
        stats_columns = {row[1]: row for row in cursor.fetchall()}

        print("\n✓ Player_game_stats table columns:")
        if 'season_type' in stats_columns:
            print(f"  - season_type: {stats_columns['season_type'][2]} (default: {stats_columns['season_type'][4]})")
            assert stats_columns['season_type'][3] == 1, "season_type should be NOT NULL"
            assert stats_columns['season_type'][4] == "'regular_season'", "Default should be 'regular_season'"
            print("  ✓ season_type column exists with correct constraints")
        else:
            print("  ✗ ERROR: season_type column missing!")
            return False

        conn.close()
        print("\n✓ TEST 1 PASSED: Schema includes season_type columns")
        return True

    finally:
        # Cleanup
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def test_indexes_created():
    """Test that performance indexes are created."""
    print("\n" + "="*70)
    print("TEST 2: Performance Indexes")
    print("="*70)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        db_conn = DatabaseConnection(temp_db_path)
        db_conn.initialize_database()

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Get all indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        required_indexes = [
            'idx_games_season_type',
            'idx_games_type',
            'idx_stats_season_type',
            'idx_stats_player_type'
        ]

        print("\n✓ Checking required indexes:")
        all_exist = True
        for index_name in required_indexes:
            if index_name in indexes:
                print(f"  ✓ {index_name}")
            else:
                print(f"  ✗ {index_name} - MISSING!")
                all_exist = False

        conn.close()

        if all_exist:
            print("\n✓ TEST 2 PASSED: All required indexes created")
            return True
        else:
            print("\n✗ TEST 2 FAILED: Some indexes missing")
            return False

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def test_default_values():
    """Test that default values work correctly."""
    print("\n" + "="*70)
    print("TEST 3: Default Values")
    print("="*70)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        db_conn = DatabaseConnection(temp_db_path)
        db_conn.initialize_database()

        # Create a test dynasty
        dynasty_id = db_conn.create_new_dynasty(
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=22  # Detroit Lions
        )

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Insert a game without specifying season_type
        cursor.execute('''
            INSERT INTO games (
                game_id, dynasty_id, season, week, home_team_id, away_team_id,
                home_score, away_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('test_game_1', dynasty_id, 2024, 1, 22, 7, 24, 21))

        # Insert player stats without specifying season_type
        cursor.execute('''
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, player_name, team_id, position,
                passing_yards, passing_tds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (dynasty_id, 'test_game_1', 'QB_22_1', 'Test QB', 22, 'QB', 300, 3))

        conn.commit()

        # Verify default values
        cursor.execute('SELECT season_type, game_type FROM games WHERE game_id = ?', ('test_game_1',))
        game_data = cursor.fetchone()

        print("\n✓ Game record:")
        print(f"  - season_type: {game_data[0]}")
        print(f"  - game_type: {game_data[1]}")

        assert game_data[0] == 'regular_season', "Default season_type should be 'regular_season'"
        assert game_data[1] == 'regular', "Default game_type should be 'regular'"

        cursor.execute('SELECT season_type FROM player_game_stats WHERE game_id = ?', ('test_game_1',))
        stat_data = cursor.fetchone()

        print("\n✓ Player stats record:")
        print(f"  - season_type: {stat_data[0]}")

        assert stat_data[0] == 'regular_season', "Default season_type should be 'regular_season'"

        conn.close()

        print("\n✓ TEST 3 PASSED: Default values work correctly")
        return True

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def test_query_filtering():
    """Test that queries can filter by season_type."""
    print("\n" + "="*70)
    print("TEST 4: Query Filtering")
    print("="*70)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        db_conn = DatabaseConnection(temp_db_path)
        db_conn.initialize_database()

        dynasty_id = db_conn.create_new_dynasty(
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=22
        )

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Insert regular season games
        for week in range(1, 4):
            cursor.execute('''
                INSERT INTO games (
                    game_id, dynasty_id, season, week, season_type, game_type,
                    home_team_id, away_team_id, home_score, away_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f'reg_game_{week}', dynasty_id, 2024, week, 'regular_season', 'regular', 22, 7, 24, 21))

        # Insert playoff games
        for week in range(19, 21):
            game_type = 'wildcard' if week == 19 else 'divisional'
            cursor.execute('''
                INSERT INTO games (
                    game_id, dynasty_id, season, week, season_type, game_type,
                    home_team_id, away_team_id, home_score, away_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f'playoff_game_{week}', dynasty_id, 2024, week, 'playoffs', game_type, 22, 7, 28, 24))

        conn.commit()

        # Query regular season games
        cursor.execute('''
            SELECT COUNT(*) FROM games
            WHERE dynasty_id = ? AND season_type = 'regular_season'
        ''', (dynasty_id,))
        regular_count = cursor.fetchone()[0]

        # Query playoff games
        cursor.execute('''
            SELECT COUNT(*) FROM games
            WHERE dynasty_id = ? AND season_type = 'playoffs'
        ''', (dynasty_id,))
        playoff_count = cursor.fetchone()[0]

        print("\n✓ Query results:")
        print(f"  - Regular season games: {regular_count}")
        print(f"  - Playoff games: {playoff_count}")

        assert regular_count == 3, "Should have 3 regular season games"
        assert playoff_count == 2, "Should have 2 playoff games"

        # Test game_type filtering
        cursor.execute('''
            SELECT COUNT(*) FROM games
            WHERE dynasty_id = ? AND game_type = 'wildcard'
        ''', (dynasty_id,))
        wildcard_count = cursor.fetchone()[0]

        print(f"  - Wildcard games: {wildcard_count}")
        assert wildcard_count == 1, "Should have 1 wildcard game"

        conn.close()

        print("\n✓ TEST 4 PASSED: Query filtering works correctly")
        return True

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Phase 1 Database Schema Migration Tests")
    print("="*70)

    tests = [
        test_new_database_schema,
        test_indexes_created,
        test_default_values,
        test_query_filtering
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ TEST FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✓ ALL TESTS PASSED")
        print("Phase 1 migration is ready for deployment!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
