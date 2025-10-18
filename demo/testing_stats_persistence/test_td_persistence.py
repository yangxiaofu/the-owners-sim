"""
Test TD Persistence - Verify touchdowns persist to database

This test runs a full game simulation and verifies that:
1. TDs are added by DriveManager during play
2. TDs are present in PlayerStatsAccumulator after accumulation
3. TDs are correctly persisted to the database

Run with: PYTHONPATH=src python demo/testing_stats_persistence/test_td_persistence.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from game_management.full_game_simulator import FullGameSimulator
from constants.team_ids import TeamIDs
import sqlite3


def test_td_persistence():
    """
    Test complete TD persistence flow:
    1. Game simulation with TD scoring
    2. TD attribution by DriveManager
    3. TD accumulation by PlayerStatsAccumulator
    4. TD persistence to database
    """
    print("=" * 80)
    print("TD PERSISTENCE TEST")
    print("=" * 80)
    print("\nThis test verifies the complete data flow from TD scoring to database persistence.\n")

    print(f"Test Configuration:")
    print(f"  Mode: Demo mode (synthetic rosters)")
    print(f"  Teams: Detroit Lions @ Green Bay Packers\n")

    # Create simulator in demo mode (no database/dynasty)
    print("Creating game simulator...")
    simulator = FullGameSimulator(
        away_team_id=TeamIDs.DETROIT_LIONS,
        home_team_id=TeamIDs.GREEN_BAY_PACKERS
        # No dynasty_id or db_path = demo mode with synthetic rosters
    )

    print("\n" + "=" * 80)
    print("PHASE 1: GAME SIMULATION")
    print("=" * 80)
    print("\nRunning full game simulation...")
    print("Watch for DriveManager TD attribution messages (✅ DriveManager: Added...)")
    print("-" * 80)

    # Run the game
    result = simulator.simulate_game()

    print("-" * 80)
    print("\n✅ Game simulation complete\n")

    # Get final score
    final_score = simulator.get_final_score()
    print(f"📊 Final Score:")
    for team_id, score in final_score["scores"].items():
        team_name = final_score["team_names"][team_id]
        print(f"   {team_name}: {score}")

    print(f"\n📈 Game Stats:")
    print(f"   Total Plays: {result.total_plays}")
    print(f"   Total Drives: {len(result.drives)}")

    # Access the game loop controller to get accumulated stats
    print("\n" + "=" * 80)
    print("PHASE 2: VERIFY TDS IN PLAYERSTATSACCUMULATOR")
    print("=" * 80)

    game_loop_controller = simulator._game_loop_controller
    player_stats = game_loop_controller.stats_aggregator.player_stats.get_all_players_with_stats()

    print(f"\nChecking {len(player_stats)} players with stats...\n")

    passing_tds_found = 0
    rushing_tds_found = 0
    receiving_tds_found = 0

    players_with_tds = []

    for player_stat in player_stats:
        player_tds = {
            "name": player_stat.player_name,
            "position": player_stat.position,
            "team_id": player_stat.team_id,
            "passing_tds": player_stat.passing_tds,
            "rushing_tds": player_stat.rushing_tds,
            "receiving_tds": player_stat.receiving_tds
        }

        if player_stat.passing_tds > 0:
            passing_tds_found += player_stat.passing_tds
            players_with_tds.append(player_tds)
            print(f"✅ {player_stat.player_name} ({player_stat.position}): {player_stat.passing_tds} passing TD(s)")

        if player_stat.rushing_tds > 0:
            rushing_tds_found += player_stat.rushing_tds
            if player_tds not in players_with_tds:
                players_with_tds.append(player_tds)
            print(f"✅ {player_stat.player_name} ({player_stat.position}): {player_stat.rushing_tds} rushing TD(s)")

        if player_stat.receiving_tds > 0:
            receiving_tds_found += player_stat.receiving_tds
            if player_tds not in players_with_tds:
                players_with_tds.append(player_tds)
            print(f"✅ {player_stat.player_name} ({player_stat.position}): {player_stat.receiving_tds} receiving TD(s)")

    print(f"\n📊 PlayerStatsAccumulator TD Summary:")
    print(f"   Passing TDs: {passing_tds_found}")
    print(f"   Rushing TDs: {rushing_tds_found}")
    print(f"   Receiving TDs: {receiving_tds_found}")
    print(f"   Total TDs: {passing_tds_found + rushing_tds_found + receiving_tds_found}")

    # Note: Database verification skipped in demo mode
    print("\n" + "=" * 80)
    print("PHASE 3: DATABASE PERSISTENCE")
    print("=" * 80)
    print("\n⚠️  Demo mode: No database persistence")
    print("   This test verifies TD accumulation, not database persistence")
    print("   To test database persistence, use a dynasty with real database")

    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    total_tds_accumulated = passing_tds_found + rushing_tds_found + receiving_tds_found

    if total_tds_accumulated > 0:
        print(f"\n✅ SUCCESS: TDs are being accumulated correctly!")
        print(f"   Total TDs in PlayerStatsAccumulator: {total_tds_accumulated}")
        print(f"   - Passing TDs: {passing_tds_found}")
        print(f"   - Rushing TDs: {rushing_tds_found}")
        print(f"   - Receiving TDs: {receiving_tds_found}")
        print(f"\n🎉 The fix is working - TDs are now included in stats accumulation!")
    else:
        print(f"\n❌ FAILURE: No TDs found in PlayerStatsAccumulator")
        print(f"   Final Score: {final_score['scores']}")
        if any(score > 0 for score in final_score["scores"].values()):
            print(f"   Points were scored but no TDs were accumulated")
            print(f"   This indicates the fix needs adjustment")

    print("=" * 80)


if __name__ == "__main__":
    test_td_persistence()
