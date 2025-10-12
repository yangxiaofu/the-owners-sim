#!/usr/bin/env python3
"""
Playoff Duplication Test

Tests that playoff initialization doesn't create duplicate games when
the PlayoffController is initialized multiple times (e.g., after app restart).

This test:
1. Creates a mock dynasty with fake standings
2. Initializes PlayoffController #1 (should schedule 6 games)
3. Destroys PlayoffController #1
4. Initializes PlayoffController #2 (should reuse existing 6 games)
5. Verifies NO duplicates were created

Run with: PYTHONPATH=src python demo/playoff_tester_demo/playoff_duplication_test.py
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from mock_standings_generator import MockStandingsGenerator
from verify_duplicates import DuplicateChecker

from playoff_system.playoff_controller import PlayoffController
from playoff_system.playoff_seeder import PlayoffSeeder
from calendar.date_models import Date
from database.connection import DatabaseConnection


def test_playoff_duplication():
    """
    Main test function.

    Tests that playoff initialization is idempotent (safe to call multiple times).
    """
    print("\n" + "="*80)
    print("🧪 PLAYOFF DUPLICATION TEST")
    print("="*80)

    # Test configuration
    # Use temporary file instead of :memory: to allow multiple connections
    temp_db = tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False)
    TEST_DB = temp_db.name
    temp_db.close()

    DYNASTY_ID = "test_dynasty"
    SEASON = 2024
    WILD_CARD_DATE = Date(2025, 1, 18)

    test_passed = True
    error_messages = []

    try:
        # Step 1: Create test database with dynasty
        print("\n[1/7] Creating test database...")
        db_conn = DatabaseConnection(TEST_DB)
        db_conn.initialize_database()  # Initialize schema first
        db_conn.ensure_dynasty_exists(
            dynasty_id=DYNASTY_ID,
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=22  # Detroit Lions
        )
        print("     ✅ Database created")

        # Step 2: Generate mock standings
        print("\n[2/7] Generating mock standings...")
        generator = MockStandingsGenerator(seed=42)  # Seed for reproducibility
        standings = generator.generate_standings()
        print(f"     ✅ Generated {len(standings)} team standings")

        # Step 3: Calculate playoff seeding
        print("\n[3/7] Calculating playoff seeding...")
        seeder = PlayoffSeeder()
        playoff_seeding = seeder.calculate_seeding(
            standings=standings,
            season=SEASON,
            week=18
        )
        print(f"     ✅ Seeding calculated (AFC: {len(playoff_seeding.afc.seeds)} seeds, "
              f"NFC: {len(playoff_seeding.nfc.seeds)} seeds)")

        # Step 4: Initialize PlayoffController #1
        print("\n[4/7] Initializing PlayoffController #1...")
        controller1 = PlayoffController(
            database_path=TEST_DB,
            dynasty_id=DYNASTY_ID,
            season_year=SEASON,
            wild_card_start_date=WILD_CARD_DATE,
            initial_seeding=playoff_seeding,
            enable_persistence=True,
            verbose_logging=False  # Suppress detailed logs for cleaner output
        )
        print("     ✅ PlayoffController #1 initialized")

        # Check games after first initialization
        checker = DuplicateChecker(TEST_DB)
        games_after_first = checker.count_playoff_games(DYNASTY_ID, SEASON)
        print(f"     📊 Playoff games in database: {games_after_first}")

        if games_after_first != 6:
            test_passed = False
            error_messages.append(
                f"Expected 6 Wild Card games after first init, got {games_after_first}"
            )

        # Step 5: Destroy controller and reinitialize
        print("\n[5/7] Destroying PlayoffController #1...")
        del controller1
        print("     ✅ Controller destroyed")

        # Step 6: Initialize PlayoffController #2 (simulates app restart)
        print("\n[6/7] Initializing PlayoffController #2 (simulating reload)...")
        controller2 = PlayoffController(
            database_path=TEST_DB,
            dynasty_id=DYNASTY_ID,
            season_year=SEASON,
            wild_card_start_date=WILD_CARD_DATE,
            initial_seeding=playoff_seeding,
            enable_persistence=True,
            verbose_logging=False
        )
        print("     ✅ PlayoffController #2 initialized")

        # Step 7: Verify no duplicates
        print("\n[7/7] Checking for duplicates...")
        games_after_second = checker.count_playoff_games(DYNASTY_ID, SEASON)
        print(f"     📊 Playoff games in database: {games_after_second}")

        # Run full duplicate check
        results = checker.check_all(DYNASTY_ID, SEASON)
        duplicates = results['duplicates']

        if duplicates:
            test_passed = False
            error_messages.append(
                f"Found {len(duplicates)} duplicate game_id(s): {[d['game_id'] for d in duplicates]}"
            )

        if games_after_second != games_after_first:
            test_passed = False
            error_messages.append(
                f"Game count changed from {games_after_first} to {games_after_second} after reload"
            )

        # Print results
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)

        print(f"\nPlayoff games after 1st init: {games_after_first}")
        print(f"Playoff games after 2nd init: {games_after_second}")
        print(f"Duplicates found: {len(duplicates)}")

        if duplicates:
            print("\nDuplicate game_ids:")
            for dup in duplicates:
                print(f"  ❌ {dup['game_id']}: {dup['count']} occurrences")

        games_by_round = results['games_by_round']
        print("\nGames by round:")
        for round_name in ['wild_card', 'divisional', 'conference', 'super_bowl']:
            count = games_by_round.get(round_name, 0)
            print(f"  {round_name:12s}: {count}")

        print("\n" + "="*80)
        if test_passed:
            print("✅ TEST PASSED: No duplicates detected!")
            print("   Playoff initialization is idempotent.")
        else:
            print("❌ TEST FAILED:")
            for msg in error_messages:
                print(f"   - {msg}")
        print("="*80)

        # Clean up
        del controller2

        return test_passed

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST ERROR")
        print("="*80)
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80)
        return False
    finally:
        # Clean up temporary database file
        try:
            if os.path.exists(TEST_DB):
                os.unlink(TEST_DB)
        except:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    success = test_playoff_duplication()
    sys.exit(0 if success else 1)
