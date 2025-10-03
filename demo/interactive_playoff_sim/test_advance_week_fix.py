#!/usr/bin/env python3
"""
Test Advance Week Fix

Validates that advance_week() works correctly after simulating a round.
Tests the fix for "string indices must be integers, not 'str'" error.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test advance_week after simulating a round."""
    print("Testing Advance Week Fix...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_week_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # ========== Step 1: Initialize and simulate Wild Card round ==========
        print("\n1. Initializing and Simulating Wild Card Round")
        print("-" * 80)
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="test_dynasty",
            season_year=2024,
            verbose_logging=False
        )
        print("✓ Controller initialized")

        # Simulate Wild Card round
        print("✓ Simulating Wild Card round...")
        wc_result = controller.advance_to_next_round()
        print(f"✓ Wild Card complete: {wc_result.get('games_played', 0)} games")

        # ========== Step 2: Call advance_week() (THE FIX TEST) ==========
        print("\n2. Testing advance_week() After Round Simulation")
        print("-" * 80)

        try:
            result = controller.advance_week()

            # Validate return structure
            assert 'start_date' in result, "Missing 'start_date' key"
            assert 'end_date' in result, "Missing 'end_date' key"
            assert 'total_games_played' in result, "Missing 'total_games_played' key"
            assert 'daily_results' in result, "Missing 'daily_results' key"
            assert 'current_round' in result, "Missing 'current_round' key"
            assert 'rounds_completed' in result, "Missing 'rounds_completed' key"
            assert 'success' in result, "Missing 'success' key"

            print(f"✓ advance_week() returned valid dictionary")
            print(f"  Start date: {result['start_date']}")
            print(f"  End date: {result['end_date']}")
            print(f"  Games played: {result['total_games_played']}")
            print(f"  Current round: {result['current_round']}")

            # Validate rounds_completed is a list of strings
            rounds_completed = result.get('rounds_completed', [])
            print(f"  Rounds completed: {len(rounds_completed)}")

            for round_name in rounds_completed:
                assert isinstance(round_name, str), f"round_name should be string, got {type(round_name)}"
                print(f"    - {round_name.replace('_', ' ').title()}")

            # Validate daily_results structure
            daily_results = result.get('daily_results', [])
            print(f"  Daily results: {len(daily_results)} days")

            # Extract games from daily_results (like the UI does)
            all_games = []
            for day_result in daily_results:
                all_games.extend(day_result.get('results', []))

            print(f"  Total games from daily_results: {len(all_games)}")

            print("\n✓ All validations passed!")

        except KeyError as e:
            print(f"\n❌ KeyError (missing key): {e}")
            raise
        except TypeError as e:
            if "string indices must be integers" in str(e):
                print(f"\n❌ ORIGINAL BUG DETECTED: {e}")
                print("   The fix didn't work - still treating strings as dicts")
                raise
            else:
                raise

        # ========== Success ==========
        print("\n" + "="*80)
        print("✅ ADVANCE WEEK FIX VALIDATED")
        print("="*80)
        print("\nKey validations:")
        print("  ✓ advance_week() returns correct dictionary structure")
        print("  ✓ rounds_completed is list of strings (not dicts)")
        print("  ✓ Game results can be extracted from daily_results")
        print("  ✓ No 'string indices must be integers' error")
        print("\n✅ The advance_week() error is FIXED!")

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
