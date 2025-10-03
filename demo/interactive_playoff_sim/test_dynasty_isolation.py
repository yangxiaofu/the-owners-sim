#!/usr/bin/env python3
"""
Test Dynasty Isolation in Playoff Controller

Validates that:
1. First run schedules 6 Wild Card games
2. Second run (same dynasty) reuses existing games (no duplicates)
3. Different dynasty creates separate games (proper isolation)
4. Each dynasty can have unique playoff brackets
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test dynasty isolation."""
    print("Testing Dynasty Isolation in Playoff Controller...")
    print("="*80)

    # Create temporary database (shared by all tests)
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_dynasty_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # ========== Test 1: First Run - Dynasty A ==========
        print("\n1. First Run - Dynasty A")
        print("-" * 80)
        controller_a1 = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_a",
            season_year=2024,
            verbose_logging=False
        )

        # Check how many events were created
        events_a1 = controller_a1.event_db.get_events_by_type("GAME")
        playoff_events_a1 = [e for e in events_a1 if 'playoff_' in e.get('game_id', '')]

        print(f"   Total events in database: {len(events_a1)}")
        print(f"   Playoff events: {len(playoff_events_a1)}")
        print(f"   ✓ Expected: 6 Wild Card games scheduled")

        assert len(playoff_events_a1) == 6, f"Expected 6 playoff events, got {len(playoff_events_a1)}"

        # Verify all are dynasty_a games
        dynasty_a_games = [e for e in playoff_events_a1 if e.get('game_id', '').startswith('playoff_dynasty_a_2024_')]
        assert len(dynasty_a_games) == 6, f"Expected 6 dynasty_a games, got {len(dynasty_a_games)}"
        print(f"   ✓ All 6 games belong to dynasty_a")

        # ========== Test 2: Second Run - Same Dynasty A ==========
        print("\n2. Second Run - Dynasty A (should reuse existing games)")
        print("-" * 80)
        controller_a2 = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_a",
            season_year=2024,
            verbose_logging=False
        )

        # Check events again - should still be 6
        events_a2 = controller_a2.event_db.get_events_by_type("GAME")
        playoff_events_a2 = [e for e in events_a2 if 'playoff_' in e.get('game_id', '')]

        print(f"   Total events in database: {len(events_a2)}")
        print(f"   Playoff events: {len(playoff_events_a2)}")

        assert len(playoff_events_a2) == 6, f"Expected 6 playoff events (no duplicates), got {len(playoff_events_a2)}"
        print(f"   ✓ No duplicate games created")
        print(f"   ✓ Reused existing dynasty_a bracket")

        # ========== Test 3: Different Dynasty B ==========
        print("\n3. First Run - Dynasty B (should create separate games)")
        print("-" * 80)
        controller_b1 = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="dynasty_b",
            season_year=2024,
            verbose_logging=False
        )

        # Check events - should now be 12 total (6 for A, 6 for B)
        events_b1 = controller_b1.event_db.get_events_by_type("GAME")
        playoff_events_b1 = [e for e in events_b1 if 'playoff_' in e.get('game_id', '')]

        print(f"   Total events in database: {len(events_b1)}")
        print(f"   Playoff events: {len(playoff_events_b1)}")

        assert len(playoff_events_b1) == 12, f"Expected 12 playoff events (6 per dynasty), got {len(playoff_events_b1)}"

        # Verify isolation - 6 for dynasty_a, 6 for dynasty_b
        dynasty_a_games_final = [e for e in playoff_events_b1 if e.get('game_id', '').startswith('playoff_dynasty_a_2024_')]
        dynasty_b_games = [e for e in playoff_events_b1 if e.get('game_id', '').startswith('playoff_dynasty_b_2024_')]

        assert len(dynasty_a_games_final) == 6, f"Expected 6 dynasty_a games, got {len(dynasty_a_games_final)}"
        assert len(dynasty_b_games) == 6, f"Expected 6 dynasty_b games, got {len(dynasty_b_games)}"

        print(f"   ✓ Dynasty A: {len(dynasty_a_games_final)} games")
        print(f"   ✓ Dynasty B: {len(dynasty_b_games)} games")
        print(f"   ✓ Dynasties properly isolated")

        # ========== Test 4: Verify game_ids are unique per dynasty ==========
        print("\n4. Verifying game_id uniqueness")
        print("-" * 80)

        all_game_ids = [e.get('game_id', '') for e in playoff_events_b1]
        unique_game_ids = set(all_game_ids)

        assert len(all_game_ids) == len(unique_game_ids), "Duplicate game_ids detected!"
        print(f"   ✓ All {len(unique_game_ids)} game_ids are unique")

        # Show sample game_ids
        print(f"\n   Sample Dynasty A game_ids:")
        for game_id in sorted([e.get('game_id', '') for e in dynasty_a_games_final])[:3]:
            print(f"     - {game_id}")

        print(f"\n   Sample Dynasty B game_ids:")
        for game_id in sorted([e.get('game_id', '') for e in dynasty_b_games])[:3]:
            print(f"     - {game_id}")

        # ========== Success ==========
        print("\n" + "="*80)
        print("✅ ALL DYNASTY ISOLATION TESTS PASSED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ First run schedules 6 Wild Card games")
        print("  ✓ Second run (same dynasty) reuses existing games (no duplicates)")
        print("  ✓ Different dynasty creates separate 6 games")
        print("  ✓ Each dynasty has unique game_ids")
        print("  ✓ Multiple dynasties can coexist in same database")
        print("\n✅ Dynasty isolation is working correctly!")

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
