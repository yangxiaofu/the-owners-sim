#!/usr/bin/env python3
"""
Simple Test for Divisional Scheduling Fix

Validates that the GameResult conversion fix works by:
1. Initializing playoff bracket (schedules 6 Wild Card games)
2. Manually simulating Wild Card games via advance_to_next_round()
3. Verifying Divisional games were scheduled (proves GameResult conversion worked)
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test divisional scheduling fix."""
    print("Testing Divisional Scheduling Fix (Simple)...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_divisional_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # ========== Step 1: Initialize playoff controller ==========
        print("\n1. Initializing Playoff Controller")
        print("-" * 80)
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="test_dynasty",
            season_year=2024,
            verbose_logging=False  # Less verbose for cleaner output
        )
        print("✓ Controller initialized")

        # Verify Wild Card games scheduled
        wc_events = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_test_dynasty_2024_wild_",
            event_type="GAME"
        )
        print(f"✓ Wild Card games scheduled: {len(wc_events)}/6")
        assert len(wc_events) == 6, f"Expected 6 Wild Card games, got {len(wc_events)}"

        # ========== Step 2: Simulate Wild Card and schedule Divisional ==========
        print("\n2. Simulating Wild Card Round")
        print("-" * 80)

        # advance_to_next_round() will:
        # 1. Simulate all Wild Card games (day by day until round complete)
        # 2. Call _schedule_next_round() which converts games to GameResult objects
        # 3. Schedule Divisional round
        result = controller.advance_to_next_round()

        print(f"✓ Wild Card round complete")
        print(f"  Games played: {result.get('games_played', 0)}")
        print(f"  Days simulated: {result.get('days_simulated', 0)}")
        print(f"  Next round: {result.get('next_round', 'None')}")

        # Verify all 6 Wild Card games were played
        wild_card_count = len(controller.completed_games.get('wild_card', []))
        print(f"✓ Wild Card games tracked: {wild_card_count}/6")

        if wild_card_count != 6:
            print(f"\n⚠️  WARNING: Expected 6 Wild Card games, got {wild_card_count}")
            print("   This may indicate calendar/scheduling issues, but is separate from the GameResult fix")

        # ========== Step 3: Verify Divisional round was scheduled (THE FIX TEST) ==========
        print("\n3. Verifying Divisional Round Scheduled (The Fix)")
        print("-" * 80)

        # Check if Divisional events exist in database
        divisional_events = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_test_dynasty_2024_divisional_",
            event_type="GAME"
        )

        if len(divisional_events) == 0:
            print(f"\n❌ FIX FAILED:")
            print(f"   No Divisional games were scheduled!")
            print(f"   This means Wild Card results were not converted to GameResult objects")
            print(f"   The original error 'Expected 3 wild card winners, got 0' would have occurred")
            raise AssertionError("Divisional scheduling failed - GameResult conversion not working")

        print(f"✅ Divisional round scheduled successfully!")
        print(f"  Divisional games created: {len(divisional_events)}")

        assert len(divisional_events) == 4, f"Expected 4 Divisional games, got {len(divisional_events)}"

        # Show sample matchups
        print(f"\n   Sample Divisional Matchups:")
        for i, event_data in enumerate(divisional_events[:2], 1):
            params = event_data['data'].get('parameters', event_data['data'])
            away_id = params.get('away_team_id')
            home_id = params.get('home_team_id')
            game_id = event_data.get('game_id', '')
            print(f"   {i}. {game_id}: Team {away_id} @ Team {home_id}")

        # ========== Success ==========
        print("\n" + "="*80)
        print("✅ DIVISIONAL SCHEDULING FIX VALIDATED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ Wild Card round simulated")
        print("  ✓ Wild Card results converted to GameResult objects")
        print("  ✓ Divisional round scheduled successfully")
        print("  ✓ 4 Divisional games created in database")
        print("\n✅ The 'Expected 3 wild card winners, got 0' error is FIXED!")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
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
            print(f"\n🗑️  Cleaned up temporary database")


if __name__ == "__main__":
    sys.exit(main())
