#!/usr/bin/env python3
"""
Test Full Playoff Progression

Validates that the complete playoff workflow operates correctly:
1. Wild Card round initializes and simulates
2. Divisional round automatically schedules based on Wild Card results
3. Conference round automatically schedules based on Divisional results
4. Super Bowl automatically schedules based on Conference results

Tests the fix where _schedule_next_round() now uses get_active_round() instead
of self.current_round to determine which round's results to use.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test complete playoff progression."""
    print("Testing Full Playoff Progression...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_progression_test.db')
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
            verbose_logging=True  # Enable verbose logging to see workflow
        )
        print("✓ Controller initialized")

        # ========== Step 2: Simulate Wild Card Round ==========
        print("\n2. Simulating Wild Card Round")
        print("-" * 80)
        wc_result = controller.advance_to_next_round()

        wc_games = wc_result.get('games_played', 0)
        print(f"✓ Wild Card complete: {wc_games} games")

        if wc_games == 0:
            print("❌ No Wild Card games simulated - calendar/scheduling issue")
            return 1

        # Check state after Wild Card
        state = controller.get_current_state()
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")

        # Verify Divisional is scheduled
        if wc_result.get('next_round_scheduled'):
            print(f"✓ Next round scheduled: {wc_result.get('next_round', 'Unknown')}")
        else:
            print("❌ Divisional round NOT scheduled after Wild Card")
            return 1

        # ========== Step 3: Simulate Divisional Round ==========
        print("\n3. Simulating Divisional Round")
        print("-" * 80)
        div_result = controller.advance_to_next_round()

        div_games = div_result.get('games_played', 0)
        print(f"✓ Divisional complete: {div_games} games")

        if div_games == 0:
            print("❌ CRITICAL: No Divisional games simulated")
            print("   This indicates _schedule_next_round() fix didn't work")
            return 1

        # Check state after Divisional
        state = controller.get_current_state()
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")

        # Verify Conference is scheduled
        if div_result.get('next_round_scheduled'):
            print(f"✓ Next round scheduled: {div_result.get('next_round', 'Unknown')}")
        else:
            print("❌ Conference round NOT scheduled after Divisional")
            return 1

        # ========== Step 4: Simulate Conference Round ==========
        print("\n4. Simulating Conference Round")
        print("-" * 80)
        conf_result = controller.advance_to_next_round()

        conf_games = conf_result.get('games_played', 0)
        print(f"✓ Conference complete: {conf_games} games")

        if conf_games == 0:
            print("❌ No Conference games simulated")
            return 1

        # Check state after Conference
        state = controller.get_current_state()
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")

        # Verify Super Bowl is scheduled
        if conf_result.get('next_round_scheduled'):
            print(f"✓ Next round scheduled: {conf_result.get('next_round', 'Unknown')}")
        else:
            print("❌ Super Bowl NOT scheduled after Conference")
            return 1

        # ========== Step 5: Simulate Super Bowl ==========
        print("\n5. Simulating Super Bowl")
        print("-" * 80)
        sb_result = controller.advance_to_next_round()

        sb_games = sb_result.get('games_played', 0)
        print(f"✓ Super Bowl complete: {sb_games} games")

        if sb_games == 0:
            print("❌ No Super Bowl game simulated")
            return 1

        # Check final state
        state = controller.get_current_state()
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")

        # ========== Success Summary ==========
        print("\n" + "="*80)
        print("✅ FULL PLAYOFF PROGRESSION VALIDATED")
        print("="*80)
        print("\nPlayoff Summary:")
        print(f"  ✓ Wild Card: {wc_games} games")
        print(f"  ✓ Divisional: {div_games} games")
        print(f"  ✓ Conference: {conf_games} games")
        print(f"  ✓ Super Bowl: {sb_games} games")
        print(f"  ✓ Total Games: {wc_games + div_games + conf_games + sb_games}")
        print(f"\n✅ All rounds automatically scheduled and simulated correctly!")
        print(f"✅ The _schedule_next_round() fix is working!")

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
