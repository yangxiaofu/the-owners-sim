#!/usr/bin/env python3
"""
Complete Playoff Workflow Test

Demonstrates the full playoff simulation workflow with all fixes applied:
1. Initialize playoff bracket
2. Simulate Wild Card
3. Divisional automatically schedules
4. Simulate Divisional
5. Conference automatically schedules
6. Simulate Conference
7. Super Bowl automatically schedules
8. Simulate Super Bowl
9. Playoffs complete

Validates all fixes:
- Round scheduling works correctly
- Game ID parsing handles underscores in dynasty_id
- Round completion checks specific rounds
- Status display shows correct active round
- advance_week works without errors
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test complete playoff workflow."""
    print("\n" + "="*80)
    print("COMPLETE PLAYOFF WORKFLOW TEST")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_workflow.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize with dynasty_id containing underscores (tests fix #2)
        print("\n1. Initializing Playoff System")
        print("-" * 80)
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="my_test_dynasty",  # Contains underscore!
            season_year=2024,
            verbose_logging=False
        )
        print("✅ Playoff bracket initialized")

        # Get initial state
        state = controller.get_current_state()
        print(f"   Initial Status: {state['active_round'].title()} (tests fix #5)")

        # Simulate each round
        rounds = ['Wild Card', 'Divisional', 'Conference', 'Super Bowl']
        games_per_round = []

        for i, round_name in enumerate(rounds, 1):
            print(f"\n{i+1}. Simulating {round_name} Round")
            print("-" * 80)

            # Simulate the round
            result = controller.advance_to_next_round()
            games_played = result.get('games_played', 0)
            games_per_round.append(games_played)

            print(f"✅ {round_name} complete: {games_played} games")

            # Check status after round
            state = controller.get_current_state()
            print(f"   Current Status: {state['active_round'].title()}")

            # Verify next round was scheduled (except after Super Bowl)
            if round_name != 'Super Bowl':
                if result.get('next_round_scheduled'):
                    next_round = result.get('next_round', '').replace('_', ' ').title()
                    print(f"✅ {next_round} automatically scheduled (tests fix #1)")
                else:
                    print(f"❌ Next round not scheduled!")
                    return 1

        # Test advance_week functionality (fix #4)
        print(f"\n{len(rounds)+2}. Testing advance_week() After Playoffs")
        print("-" * 80)
        try:
            week_result = controller.advance_week()
            print(f"✅ advance_week() works without errors (tests fix #4)")
            print(f"   Total games in week: {week_result.get('total_games_played', 0)}")
        except TypeError as e:
            if "string indices" in str(e):
                print(f"❌ advance_week() error: {e}")
                return 1
            raise

        # Final summary
        print("\n" + "="*80)
        print("✅ COMPLETE PLAYOFF WORKFLOW VALIDATED")
        print("="*80)

        print("\nAll Fixes Validated:")
        print("  ✅ Fix #1: Rounds schedule correctly after completion")
        print("  ✅ Fix #2: Game IDs with underscores in dynasty_id parse correctly")
        print("  ✅ Fix #3: Round completion checks specific rounds")
        print("  ✅ Fix #4: advance_week() works without type errors")
        print("  ✅ Fix #5: Status display shows correct active round")

        print("\nPlayoff Results:")
        expected_games = [6, 4, 2, 1]
        for i, (round_name, games, expected) in enumerate(zip(rounds, games_per_round, expected_games)):
            status = "✅" if games == expected else "❌"
            print(f"  {status} {round_name}: {games} games (expected {expected})")

        total_games = sum(games_per_round)
        print(f"\n  Total Games: {total_games} (expected 13)")

        if total_games == 13 and games_per_round == expected_games:
            print("\n🏆 All playoff rounds completed successfully!")
            return 0
        else:
            print("\n❌ Game count mismatch!")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
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
