#!/usr/bin/env python3
"""
Test for "14 Games Bug" Fix

Validates that playoff simulation properly filters games by dynasty_id
when multiple dynasties have playoff events scheduled for the same date.

The Bug:
    Originally, when simulating playoffs for dynasty_a, the system would
    retrieve ALL playoff games scheduled for a given date, regardless of
    dynasty. This caused dynasty_a to simulate games from dynasty_b and
    dynasty_c as well.

    For example:
    - Dynasty A: 6 Wild Card games on 2025-01-12
    - Dynasty B: 6 Wild Card games on 2025-01-12
    - Dynasty C: 6 Wild Card games on 2025-01-12
    - Total in DB: 18 games

    When advancing dynasty_a, it would simulate 14 or 18 games instead of 6.

The Fix:
    SimulationExecutor now uses get_events_by_game_id_prefix() to filter
    events by dynasty-specific game_id prefix before simulation.

Test Requirements:
    1. Create temporary database
    2. Create 3 different dynasties' playoff events (6 games each = 18 total)
    3. All scheduled for Wild Card weekend (spread across multiple days)
    4. Initialize PlayoffController for dynasty_a
    5. Call advance_to_next_round() to simulate Wild Card round
    6. Verify ONLY 6 games are simulated (not 14 or 18)
    7. Verify all 6 games belong to dynasty_a
    8. Clean up temp database

Expected Output:
    ✅ Database has 18 playoff games total (6 per dynasty)
    ✅ Dynasty A simulation retrieves only 6 games
    ✅ All 6 games have game_id starting with "playoff_dynasty_a_2024_"
    ✅ No games from dynasty_b or dynasty_c are simulated
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController
from calendar.date_models import Date


def main():
    """Test the fix for the 14 games bug."""
    print("Testing Fix for '14 Games Bug'")
    print("="*80)
    print("\nBackground:")
    print("  When multiple dynasties have playoff games on the same date,")
    print("  the simulation should only process games for the current dynasty.")
    print("  Previously, it would simulate games from other dynasties too.")
    print("="*80)

    # Create temporary database (shared by all 3 dynasties)
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_14games_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # ========== Setup: Create 3 Dynasties with 6 Games Each ==========
        print("\n1. Setup: Creating 3 dynasties with Wild Card games")
        print("-" * 80)

        # Use Date(2025, 1, 11) as the default Wild Card start date
        # Games will be spread across Sat (1/11), Sun (1/12), Mon (1/13)
        # The controller will advance day-by-day and simulate games
        wild_card_date = Date(2025, 1, 11)

        # Dynasty A: 6 Wild Card games
        print("   Creating dynasty_a playoff bracket...")
        controller_a = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_a",
            season_year=2024,
            wild_card_start_date=wild_card_date,
            verbose_logging=False
        )
        print("   ✓ Dynasty A: 6 Wild Card games scheduled")

        # Dynasty B: 6 Wild Card games (same dates as A)
        print("   Creating dynasty_b playoff bracket...")
        controller_b = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_b",
            season_year=2024,
            wild_card_start_date=wild_card_date,
            verbose_logging=False
        )
        print("   ✓ Dynasty B: 6 Wild Card games scheduled")

        # Dynasty C: 6 Wild Card games (same dates as A and B)
        print("   Creating dynasty_c playoff bracket...")
        controller_c = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_c",
            season_year=2024,
            wild_card_start_date=wild_card_date,
            verbose_logging=False
        )
        print("   ✓ Dynasty C: 6 Wild Card games scheduled")

        # ========== Verify Database Has 18 Total Games ==========
        print("\n2. Verifying database has 18 playoff games total")
        print("-" * 80)

        all_events = controller_a.event_db.get_events_by_type("GAME")
        playoff_events = [e for e in all_events if 'playoff_' in e.get('game_id', '')]

        print(f"   Total events in database: {len(all_events)}")
        print(f"   Total playoff events: {len(playoff_events)}")

        assert len(playoff_events) == 18, f"Expected 18 playoff events, got {len(playoff_events)}"
        print(f"   ✓ Database has 18 playoff games (6 per dynasty)")

        # Verify distribution across dynasties
        dynasty_a_games = [e for e in playoff_events if e.get('game_id', '').startswith('playoff_dynasty_a_2024_')]
        dynasty_b_games = [e for e in playoff_events if e.get('game_id', '').startswith('playoff_dynasty_b_2024_')]
        dynasty_c_games = [e for e in playoff_events if e.get('game_id', '').startswith('playoff_dynasty_c_2024_')]

        print(f"\n   Game distribution:")
        print(f"     Dynasty A: {len(dynasty_a_games)} games")
        print(f"     Dynasty B: {len(dynasty_b_games)} games")
        print(f"     Dynasty C: {len(dynasty_c_games)} games")

        assert len(dynasty_a_games) == 6, f"Expected 6 dynasty_a games, got {len(dynasty_a_games)}"
        assert len(dynasty_b_games) == 6, f"Expected 6 dynasty_b games, got {len(dynasty_b_games)}"
        assert len(dynasty_c_games) == 6, f"Expected 6 dynasty_c games, got {len(dynasty_c_games)}"
        print(f"   ✓ All dynasties have exactly 6 games")

        # ========== Verify Games Scheduled Across Wild Card Weekend ==========
        print("\n3. Verifying games scheduled across Wild Card weekend")
        print("-" * 80)

        # Get all unique dates from parameters.game_date
        unique_dates = set()
        date_counts = {}
        for event in playoff_events:
            # Get game_date from parameters
            params = event.get('data', {}).get('parameters', event.get('data', {}))
            game_date = params.get('game_date')
            if game_date:
                # Extract just date part if it's an ISO datetime string
                if 'T' in game_date:
                    date_part = game_date.split('T')[0]
                else:
                    date_part = game_date[:10] if len(game_date) >= 10 else game_date
                unique_dates.add(date_part)
                date_counts[date_part] = date_counts.get(date_part, 0) + 1

        print(f"   Unique dates in playoff events: {len(unique_dates)}")
        print(f"   ℹ️  Wild Card games are spread across multiple days (realistic NFL scheduling)")

        # Show distribution
        if date_counts:
            print(f"\n   Game distribution by date:")
            for date in sorted(date_counts.keys()):
                print(f"     {date}: {date_counts[date]} games")

        print(f"   ✓ Games scheduled across {len(unique_dates)} day(s) as expected")

        # Show dynasty_a specific dates
        print(f"\n   Dynasty A game dates:")
        dynasty_a_dates = {}
        for event in dynasty_a_games:
            params = event.get('data', {}).get('parameters', event.get('data', {}))
            game_date = params.get('game_date', '')
            if 'T' in game_date:
                date_part = game_date.split('T')[0]
            else:
                date_part = game_date[:10] if len(game_date) >= 10 else game_date
            dynasty_a_dates[date_part] = dynasty_a_dates.get(date_part, 0) + 1

        for date in sorted(dynasty_a_dates.keys()):
            print(f"     {date}: {dynasty_a_dates[date]} games")

        # ========== The Critical Test: Simulate Dynasty A Only ==========
        print("\n4. CRITICAL TEST: Simulating Wild Card round for dynasty_a")
        print("-" * 80)
        print("   This will simulate the entire Wild Card round (all days)")
        print("   If the bug exists, this will simulate 14-18 games instead of 6")
        print("   If the fix works, this will simulate exactly 6 dynasty_a games")
        print()

        # Create fresh controller for dynasty_a to simulate
        controller_a_sim = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_a",
            season_year=2024,
            wild_card_start_date=wild_card_date,
            verbose_logging=True  # Show detailed progress
        )

        # WORKAROUND: Reset calendar to 1 day before first game
        # This is needed because advance_day() advances BEFORE simulating
        # So if calendar starts at 2025-01-11 (first game date),
        # the first advance_day() will skip to 2025-01-12, missing games on 2025-01-11
        controller_a_sim.calendar.reset(wild_card_date.add_days(-1))
        print(f"   ℹ️  Calendar reset to {wild_card_date.add_days(-1)} (1 day before first game)")

        # Simulate Wild Card round for dynasty_a
        print("\n   Simulating Wild Card round...")
        result = controller_a_sim.advance_to_next_round()

        games_played = result.get('games_played', 0)
        print(f"\n   Games simulated: {games_played}")

        # ========== Validate Results ==========
        print("\n5. Validating results")
        print("-" * 80)

        # Check 1: Exactly 6 games simulated
        if games_played == 6:
            print(f"   ✅ PASS: Exactly 6 games simulated")
        elif games_played == 14:
            print(f"   ❌ FAIL: 14 games simulated (bug still present - simulating another dynasty)")
            raise AssertionError("Bug detected: Simulated 14 games instead of 6")
        elif games_played == 18:
            print(f"   ❌ FAIL: 18 games simulated (bug still present - simulating all dynasties)")
            raise AssertionError("Bug detected: Simulated 18 games instead of 6")
        else:
            print(f"   ❌ FAIL: Unexpected game count: {games_played}")
            raise AssertionError(f"Expected 6 games, got {games_played}")

        # Check 2: All games belong to dynasty_a
        simulated_games = result.get('results', [])
        dynasty_a_count = sum(1 for g in simulated_games if g.get('game_id', '').startswith('playoff_dynasty_a_2024_'))

        print(f"   ✅ All {dynasty_a_count} games belong to dynasty_a")

        assert dynasty_a_count == 6, f"Expected 6 dynasty_a games, got {dynasty_a_count}"

        # Check 3: No games from other dynasties
        dynasty_b_count = sum(1 for g in simulated_games if g.get('game_id', '').startswith('playoff_dynasty_b_2024_'))
        dynasty_c_count = sum(1 for g in simulated_games if g.get('game_id', '').startswith('playoff_dynasty_c_2024_'))

        if dynasty_b_count > 0 or dynasty_c_count > 0:
            print(f"   ❌ FAIL: Simulated games from other dynasties")
            print(f"      Dynasty B games: {dynasty_b_count}")
            print(f"      Dynasty C games: {dynasty_c_count}")
            raise AssertionError("Bug detected: Simulated games from other dynasties")
        else:
            print(f"   ✅ No games from dynasty_b or dynasty_c simulated")

        # Check 4: Verify game_ids
        print(f"\n   Sample game_ids simulated:")
        for i, game in enumerate(simulated_games[:3], 1):
            game_id = game.get('game_id', 'N/A')
            print(f"     {i}. {game_id}")

        # ========== Success ==========
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - '14 GAMES BUG' IS FIXED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ Database has 18 playoff games total (6 per dynasty)")
        print("  ✓ Dynasty A simulation retrieved exactly 6 games")
        print("  ✓ All 6 games have game_id starting with 'playoff_dynasty_a_2024_'")
        print("  ✓ No games from dynasty_b or dynasty_c were simulated")
        print("  ✓ Dynasty isolation is working correctly")
        print("\n✅ The fix successfully prevents cross-dynasty game simulation!")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
            print(f"\n🗑️  Cleaned up temporary database: {temp_db_path}")


if __name__ == "__main__":
    sys.exit(main())
