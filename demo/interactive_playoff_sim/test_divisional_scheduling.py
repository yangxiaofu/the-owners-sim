#!/usr/bin/env python3
"""
Test Divisional Scheduling Fix

Validates that Wild Card winners are properly converted to GameResult objects
and passed to PlayoffScheduler for Divisional round scheduling.

This test reproduces the error:
"❌ Divisional scheduling failed: Expected 3 wild card winners, got 0"
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test divisional scheduling with Wild Card results."""
    print("Testing Divisional Scheduling Fix...")
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
            verbose_logging=True
        )
        print("✓ Controller initialized with random Wild Card bracket")

        # ========== Step 2: Simulate all playoff games to trigger the fix ==========
        print("\n2. Simulating Playoffs to Test Divisional Scheduling")
        print("-" * 80)

        # Debug: Check what Wild Card games exist before simulation
        wc_events_before = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_{controller.dynasty_id}_{controller.season_year}_wild_",
            event_type="GAME"
        )
        print(f"Wild Card events in database before simulation: {len(wc_events_before)}")

        # Use simulate_to_super_bowl which will:
        # 1. Simulate all 6 Wild Card games
        # 2. Call _schedule_next_round() with Wild Card results (THE FIX POINT)
        # 3. Continue to simulate Divisional and beyond
        result = controller.simulate_to_super_bowl()

        print(f"\n✅ All playoffs simulated")
        print(f"   Total games: {result.get('total_games', 0)}")
        print(f"   Wild Card games tracked: {len(controller.completed_games['wild_card'])}/6")

        # Debug: Check what Wild Card games exist after simulation
        wc_events_after = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_{controller.dynasty_id}_{controller.season_year}_wild_",
            event_type="GAME"
        )
        print(f"   Wild Card events in database after simulation: {len(wc_events_after)}")

        # ========== Step 3: Verify Wild Card results exist ==========
        print("\n3. Verifying Wild Card Results")
        print("-" * 80)
        wild_card_games = controller.completed_games['wild_card']
        print(f"   Total Wild Card games: {len(wild_card_games)}")

        assert len(wild_card_games) == 6, f"Expected 6 Wild Card games, got {len(wild_card_games)}"

        # Count winners by conference
        afc_winners = []
        nfc_winners = []

        for game in wild_card_games:
            winner_id = game.get('winner_id')
            if winner_id:
                # Simple heuristic: AFC teams are typically IDs 1-16, NFC are 17-32
                # This is a rough approximation for testing
                if winner_id <= 16:
                    afc_winners.append(winner_id)
                else:
                    nfc_winners.append(winner_id)

        print(f"   AFC Wild Card winners: {len(afc_winners)} teams")
        print(f"   NFC Wild Card winners: {len(nfc_winners)} teams")
        print(f"   ✓ Wild Card results ready for Divisional scheduling")

        # ========== Step 4: Verify Divisional Round was scheduled (THE FIX TEST) ==========
        print("\n4. Verifying Divisional Round Scheduled (Testing the Fix)")
        print("-" * 80)

        # advance_to_next_round() should have already scheduled the Divisional round
        # This is where the fix is tested - if it worked, Divisional games will exist

        divisional_events = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_{controller.dynasty_id}_{controller.season_year}_divisional_",
            event_type="GAME"
        )

        if len(divisional_events) == 0:
            print(f"\n   ❌ ORIGINAL ERROR DETECTED:")
            print(f"      No Divisional games were scheduled!")
            print(f"      This means Wild Card results were not converted to GameResult objects")
            raise AssertionError("Expected 3 wild card winners, got 0 - FIX FAILED")

        print(f"   ✓ Divisional round scheduled successfully!")
        print(f"   ✓ Divisional games created: {len(divisional_events)}")

        assert len(divisional_events) == 4, f"Expected 4 Divisional games, got {len(divisional_events)}"

        # Show matchups
        print(f"\n   Divisional Round Matchups:")
        for event_data in divisional_events:
            params = event_data['data'].get('parameters', event_data['data'])
            away_id = params.get('away_team_id')
            home_id = params.get('home_team_id')
            game_id = event_data.get('game_id', '')
            print(f"     - {game_id}: Team {away_id} @ Team {home_id}")

        # ========== Success ==========
        print("\n" + "="*80)
        print("✅ DIVISIONAL SCHEDULING FIX VALIDATED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ 6 Wild Card games simulated successfully")
        print("  ✓ Wild Card results converted to GameResult objects")
        print("  ✓ Divisional round scheduled with proper matchups")
        print("  ✓ 4 Divisional games created")
        print("\n✅ The 'Expected 3 wild card winners, got 0' error is FIXED!")

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
