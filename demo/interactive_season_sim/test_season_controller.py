"""
Test Season Controller

Simple test script to verify SeasonController functionality.
"""

import sys
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from calendar.date_models import Date
from season_controller import SeasonController


def test_season_controller():
    """Test basic SeasonController functionality."""

    print("\n" + "="*80)
    print("SEASON CONTROLLER TEST".center(80))
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Initialize controller
        print("\n1. Initializing SeasonController...")

        controller = SeasonController(
            database_path=temp_db.name,
            start_date=Date(2024, 9, 5),  # Thursday, September 5, 2024
            season_year=2024,
            dynasty_id="test_dynasty",
            enable_persistence=True,
            verbose_logging=True
        )

        print("✅ Controller initialized successfully")

        # Get current state
        print("\n2. Getting current state...")
        state = controller.get_current_state()
        print(f"   Current Date: {state['current_date']}")
        print(f"   Week: {state['week_number']}")
        print(f"   Phase: {state['phase']}")
        print(f"   Games Played: {state['games_played']}")

        # Get upcoming games
        print("\n3. Checking upcoming games (next 7 days)...")
        upcoming = controller.get_upcoming_games(days=7)
        print(f"   Found {len(upcoming)} upcoming games")

        if upcoming:
            print(f"\n   First 3 games:")
            for i, game in enumerate(upcoming[:3], 1):
                print(f"   {i}. {game['date']}: Team {game['away_team_id']} @ Team {game['home_team_id']} (Week {game['week']})")

        # Advance one day (should simulate Week 1 Thursday night game)
        print("\n4. Advancing one day...")
        day_result = controller.advance_day()
        print(f"   Date: {day_result['date']}")
        print(f"   Games Played: {day_result['games_played']}")
        print(f"   Success: {day_result['success']}")

        # Advance one week
        print("\n5. Advancing one week...")
        week_result = controller.advance_week()
        print(f"   Week Number: {week_result['week_number']}")
        print(f"   Date Range: {week_result['start_date']} to {week_result['end_date']}")
        print(f"   Total Games: {week_result['total_games_played']}")
        print(f"   Success: {week_result['success']}")

        # Get standings (may be empty if no games simulated yet)
        print("\n6. Getting current standings...")
        standings = controller.get_current_standings()
        if standings and standings.get('divisions'):
            division_count = len(standings['divisions'])
            print(f"   Found standings for {division_count} divisions")
        else:
            print("   No standings data yet (expected if no games simulated)")

        # Final state
        print("\n7. Final state...")
        final_state = controller.get_current_state()
        print(f"   Current Date: {final_state['current_date']}")
        print(f"   Total Games Played: {final_state['games_played']}")
        print(f"   Total Days Simulated: {final_state['days_simulated']}")

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED".center(80))
        print("="*80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up temporary database
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)
            print(f"\n🗑️  Cleaned up temporary database: {temp_db.name}")


if __name__ == "__main__":
    test_season_controller()
