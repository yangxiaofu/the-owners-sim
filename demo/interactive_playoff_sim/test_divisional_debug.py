#!/usr/bin/env python3
"""
Debug Divisional Round Issue

Adds verbose debug output to understand why Divisional games aren't simulating.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Debug divisional round issue."""
    print("Debugging Divisional Round Issue...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_debug.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize playoff controller
        print("\n1. Initializing Playoff Controller")
        print("-" * 80)
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="debug_dynasty",
            season_year=2024,
            verbose_logging=False  # Disable verbose to reduce noise
        )
        print("✓ Controller initialized")

        # Simulate Wild Card Round
        print("\n2. Simulating Wild Card Round")
        print("-" * 80)
        wc_result = controller.advance_to_next_round()
        print(f"✓ Wild Card: {wc_result.get('games_played', 0)} games played")

        # Check state after Wild Card
        state = controller.get_current_state()
        print(f"\nState after Wild Card:")
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")
        print(f"  current_date: {state['current_date']}")

        # Check completed games
        wc_games = controller.completed_games['wild_card']
        print(f"\n  Wild Card completed games: {len(wc_games)}")
        for game in wc_games[:2]:  # Show first 2
            print(f"    - {game.get('matchup', 'Unknown')}: {game.get('winner_name', 'Unknown')} wins")

        # Check if Divisional is scheduled
        from events.event_database_api import EventDatabaseAPI

        event_db = EventDatabaseAPI(temp_db_path)

        div_events = event_db.get_events_by_game_id_prefix(
            f"playoff_debug_dynasty_2024_divisional_",
            event_type="GAME"
        )
        print(f"\n  Divisional events scheduled: {len(div_events)}")
        for event in div_events[:2]:  # Show first 2
            params = event['data'].get('parameters', event['data'])
            game_date = params.get('game_date', 'Unknown')
            game_id = event.get('game_id', 'Unknown')
            print(f"    - {game_id}: {game_date}")

        # Now try to simulate Divisional
        print("\n3. Attempting to Simulate Divisional Round")
        print("-" * 80)

        # Check active round before simulating
        active_before = controller.get_active_round()
        print(f"Active round before simulation: {active_before}")

        # Get current date
        current_date = controller.calendar.get_current_date()
        print(f"Current calendar date: {current_date}")

        # Manually check if we can find Divisional games for upcoming dates
        print("\nChecking for Divisional games on upcoming dates:")
        for i in range(-10, 15):  # Check both past and future
            check_date = current_date.add_days(i)
            events = controller.simulation_executor._get_events_for_date(check_date)
            playoff_events = [e for e in events if 'divisional' in e.get('game_id', '')]
            if playoff_events:
                print(f"  {check_date}: {len(playoff_events)} Divisional game(s) found")
                for event in playoff_events[:1]:
                    params = event['data'].get('parameters', event['data'])
                    print(f"    Event game_date: {params.get('game_date', 'NO DATE')}")

        # Now simulate Divisional
        div_result = controller.advance_to_next_round()
        print(f"\n✓ Divisional simulation complete")
        print(f"  Games played: {div_result.get('games_played', 0)}")
        print(f"  Days simulated: {div_result.get('days_simulated', 0)}")

        # Check state after attempted Divisional simulation
        state = controller.get_current_state()
        print(f"\nState after Divisional attempt:")
        print(f"  current_round: {state['current_round']}")
        print(f"  active_round: {state['active_round']}")
        print(f"  current_date: {state['current_date']}")

        # Check completed games in all rounds
        print(f"\nCompleted games by round:")
        for round_name in ['wild_card', 'divisional', 'conference', 'super_bowl']:
            games = controller.completed_games[round_name]
            print(f"  {round_name}: {len(games)} games")
            if games:
                for game in games[:2]:
                    game_id = game.get('game_id', 'NO ID')
                    print(f"    - {game_id}")
                    # Test detection
                    detected = controller._detect_game_round(game_id)
                    print(f"      Detected round: {detected}")

        return 0

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
