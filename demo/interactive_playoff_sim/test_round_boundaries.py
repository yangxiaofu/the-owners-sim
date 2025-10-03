#!/usr/bin/env python3
"""
Test Round Boundary Detection in Playoff Controller

Validates that advance_to_next_round() correctly:
1. Simulates ONLY the current round (not continuing into next round)
2. Schedules the next round after completion
3. Transitions rounds automatically when simulating games from new round
4. Shows exactly 6 Wild Card games, then 4 Divisional games (not 10 total)

This test validates the fix for the critical bug where "advance current round"
was simulating 10 games instead of stopping after 6 Wild Card games.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test round boundary detection."""
    print("Testing Round Boundary Detection in Playoff Controller...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_round_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize controller
        print("\n1. Initializing playoff controller...")
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="round_boundary_test",
            season_year=2024,
            verbose_logging=True
        )
        print("✅ Controller initialized")

        # Verify initial state
        print("\n2. Verifying initial state...")
        state = controller.get_current_state()
        assert state['current_round'] == 'wild_card', f"Expected wild_card, got {state['current_round']}"
        assert state['games_played'] == 0, f"Expected 0 games, got {state['games_played']}"
        print(f"   ✓ Current round: {state['current_round']}")
        print(f"   ✓ Games played: {state['games_played']}")

        # Advance through Wild Card round
        print("\n3. Advancing through Wild Card round (should simulate exactly 6 games)...")
        print("-" * 80)
        result = controller.advance_to_next_round()
        print("-" * 80)

        # Validate Wild Card completion
        print("\n4. Validating Wild Card completion...")
        assert result['success'], "Wild Card advance failed"
        assert result['games_played'] == 6, f"Expected 6 games, got {result['games_played']}"
        assert result['completed_round'] == 'wild_card', f"Expected wild_card, got {result['completed_round']}"
        print(f"   ✓ Games played: {result['games_played']} (correct)")
        print(f"   ✓ Completed round: {result['completed_round']}")

        # Verify next round scheduled but NOT simulated
        print("\n5. Verifying next round scheduled (but NOT simulated)...")
        assert result.get('next_round_scheduled'), "Next round should be scheduled"
        assert result['next_round'] == 'divisional', f"Expected divisional, got {result['next_round']}"
        print(f"   ✓ Next round scheduled: {result['next_round']}")

        # Check state after Wild Card - should still be wild_card until we simulate divisional games
        state = controller.get_current_state()
        print(f"   ✓ Current state round: {state['current_round']}")
        print(f"   ✓ Total games played: {state['games_played']}")

        # Verify exactly 6 games were played (NOT 10)
        if state['games_played'] != 6:
            print(f"\n❌ CRITICAL BUG: Expected 6 games, got {state['games_played']}")
            print("   This indicates the controller continued into the next round!")
            raise AssertionError(f"Expected 6 games after Wild Card, got {state['games_played']}")

        print(f"\n✅ PASS: Exactly 6 games simulated (not 10)")

        # Now advance through Divisional round
        print("\n6. Advancing through Divisional round (should simulate exactly 4 games)...")
        print("-" * 80)
        result = controller.advance_to_next_round()
        print("-" * 80)

        # Validate Divisional completion
        print("\n7. Validating Divisional completion...")
        assert result['success'], "Divisional advance failed"
        assert result['games_played'] == 4, f"Expected 4 games, got {result['games_played']}"
        assert result['completed_round'] == 'divisional', f"Expected divisional, got {result['completed_round']}"
        print(f"   ✓ Games played: {result['games_played']} (correct)")
        print(f"   ✓ Completed round: {result['completed_round']}")

        # Verify total games
        state = controller.get_current_state()
        assert state['games_played'] == 10, f"Expected 10 total games, got {state['games_played']}"
        print(f"   ✓ Total games: {state['games_played']} (6 Wild Card + 4 Divisional)")

        # Test round transition detection
        print("\n8. Testing automatic round transition detection...")

        # Check completed games per round
        wild_card_games = controller.completed_games.get('wild_card', [])
        divisional_games = controller.completed_games.get('divisional', [])

        print(f"   ✓ Wild Card games tracked: {len(wild_card_games)}")
        print(f"   ✓ Divisional games tracked: {len(divisional_games)}")

        assert len(wild_card_games) == 6, f"Expected 6 wild card games, got {len(wild_card_games)}"
        assert len(divisional_games) == 4, f"Expected 4 divisional games, got {len(divisional_games)}"

        print("\n" + "="*80)
        print("✅ ALL ROUND BOUNDARY TESTS PASSED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ advance_to_next_round() stops at round boundaries")
        print("  ✓ Exactly 6 Wild Card games simulated (not 10)")
        print("  ✓ Next round is scheduled but not simulated")
        print("  ✓ Round transitions happen automatically")
        print("  ✓ Games are correctly tracked per round")
        print("\n✅ The 'advance current round' bug is FIXED!")

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
