"""
Test script to verify Divisional Round scheduling after Wild Card completion.

Tests dynasty '9th' to ensure database-driven round progression works correctly.
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from playoff_system.playoff_controller import PlayoffController
from events.event_database_api import EventDatabaseAPI

def test_divisional_scheduling():
    """Test that Divisional Round schedules correctly after Wild Card completion."""

    print("\n" + "="*80)
    print("TESTING: Divisional Round Scheduling for Dynasty 'default'")
    print("="*80 + "\n")

    # Initialize controller for dynasty 'default' (has completed WC games)
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "default"
    season = 2025

    print(f"Database: {db_path}")
    print(f"Dynasty: {dynasty_id}")
    print(f"Season: {season}\n")

    # Create controller
    controller = PlayoffController(
        database_path=db_path,
        dynasty_id=dynasty_id,
        season_year=season,
        enable_persistence=True,
        verbose_logging=True
    )

    print("\n" + "-"*80)
    print("STEP 1: Check current state")
    print("-"*80)

    state = controller.get_current_state()
    print(f"\nCurrent Round: {state['current_round']}")
    print(f"Calendar Date: {state['current_date']}")

    print("\nRound Progress:")
    for round_name in ['wild_card', 'divisional', 'conference', 'super_bowl']:
        progress = state['round_progress'][round_name]
        print(f"  {round_name:12} - {progress['games_completed']}/{progress['games_expected']} games "
              f"{'✅ COMPLETE' if progress['complete'] else '⏳ INCOMPLETE'}")

    print("\n" + "-"*80)
    print("STEP 2: Query database directly for Wild Card games")
    print("-"*80)

    event_db = EventDatabaseAPI(db_path)
    all_events = event_db.get_events_by_dynasty(dynasty_id, event_type="GAME")

    wild_card_games = [e for e in all_events if e.get('game_id', '').startswith(f'playoff_{season}_wild_card_')]
    print(f"\nFound {len(wild_card_games)} Wild Card games in database")

    # Check which have results
    completed_wc = [g for g in wild_card_games if g.get('results')]
    print(f"  {len(completed_wc)} have results (completed)")
    print(f"  {len(wild_card_games) - len(completed_wc)} are scheduled but not played")

    if len(completed_wc) >= 6:
        print("\n✅ Wild Card round is COMPLETE (6/6 games)")
    else:
        print(f"\n⚠️ Wild Card round is INCOMPLETE ({len(completed_wc)}/6 games)")

    print("\n" + "-"*80)
    print("STEP 3: Check active round (should be 'divisional' if WC complete)")
    print("-"*80)

    active_round = controller.get_active_round()
    print(f"\nActive round: {active_round}")

    if active_round == 'divisional':
        print("✅ Correctly detected divisional as active round")
    elif active_round == 'wild_card':
        print("❌ Still shows wild_card as active (BUG)")
    else:
        print(f"⚠️ Unexpected active round: {active_round}")

    print("\n" + "-"*80)
    print("STEP 4: Check for existing Divisional Round games")
    print("-"*80)

    divisional_games = [e for e in all_events if e.get('game_id', '').startswith(f'playoff_{season}_divisional_')]
    print(f"\nFound {len(divisional_games)} Divisional Round games in database")

    if len(divisional_games) == 0:
        print("⚠️ No Divisional games scheduled yet")
        print("\nThis means _schedule_next_round() has not run yet.")
        print("Let's try advancing to trigger scheduling...")

        print("\n" + "-"*80)
        print("STEP 5: Advance simulation to trigger scheduling")
        print("-"*80)

        result = controller.advance_week()

        print(f"\nAdvance result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message')}")

        # Check again for Divisional games
        all_events = event_db.get_events_by_dynasty(dynasty_id, event_type="GAME")
        divisional_games = [e for e in all_events if e.get('game_id', '').startswith(f'playoff_{season}_divisional_')]

        print(f"\nAfter advance_week():")
        print(f"  Divisional games in database: {len(divisional_games)}")

        if len(divisional_games) == 4:
            print("\n✅ SUCCESS: Divisional Round scheduled correctly (4 games)")

            print("\nScheduled games:")
            for game in divisional_games:
                game_id = game.get('game_id', 'unknown')
                away = game.get('parameters', {}).get('away_team_id', '?')
                home = game.get('parameters', {}).get('home_team_id', '?')
                game_date = game.get('date', 'unknown')
                print(f"  {game_id}: Team {away} @ Team {home} on {game_date}")
        elif len(divisional_games) == 0:
            print("\n❌ FAILURE: Divisional Round NOT scheduled")
            print("This indicates the fix did not work as expected.")
        else:
            print(f"\n⚠️ PARTIAL: Only {len(divisional_games)}/4 Divisional games scheduled")

    elif len(divisional_games) == 4:
        print("✅ Divisional Round already scheduled (4 games)")

        print("\nScheduled games:")
        for game in divisional_games:
            game_id = game.get('game_id', 'unknown')
            away = game.get('parameters', {}).get('away_team_id', '?')
            home = game.get('parameters', {}).get('home_team_id', '?')
            game_date = game.get('date', 'unknown')
            has_result = '✅' if game.get('results') else '⏳'
            print(f"  {has_result} {game_id}: Team {away} @ Team {home} on {game_date}")

    else:
        print(f"⚠️ Unexpected number of Divisional games: {len(divisional_games)}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_divisional_scheduling()
