"""
Simple test to verify TD attribution fix in DriveManager

This script runs a single game and checks if TDs are being recorded
in the player stats after the DriveManager fix.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from game_management.full_game_simulator import FullGameSimulator
from constants.team_ids import TeamIDs


def main():
    print("=" * 80)
    print("TD ATTRIBUTION FIX VERIFICATION TEST")
    print("=" * 80)
    print("\nRunning a single game to verify TD attribution is working...\n")

    # Create simulator (demo mode with synthetic rosters - no database)
    simulator = FullGameSimulator(
        away_team_id=TeamIDs.DETROIT_LIONS,
        home_team_id=TeamIDs.GREEN_BAY_PACKERS
    )

    print(f"Simulating: Detroit Lions @ Green Bay Packers\n")
    print("Looking for TD attribution messages from DriveManager...\n")
    print("-" * 80)

    # Run the simulation
    result = simulator.simulate_game()

    print("-" * 80)
    print("\n📊 GAME COMPLETE")
    print("=" * 80)

    # Check the box score for TDs
    if result and hasattr(result, 'box_score'):
        box_score = result.box_score

        print(f"\n🏈 Final Score:")
        print(f"   Away: {box_score.away_score}")
        print(f"   Home: {box_score.home_score}")

        print(f"\n📈 Checking player stats for TDs...")

        # Check away team stats
        print(f"\n  {box_score.away_team_name}:")
        rushing_tds = 0
        passing_tds = 0
        receiving_tds = 0

        for stat in box_score.away_player_stats:
            if hasattr(stat, 'rushing_touchdowns') and stat.rushing_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.rushing_touchdowns} rushing TD(s)")
                rushing_tds += stat.rushing_touchdowns
            if hasattr(stat, 'passing_touchdowns') and stat.passing_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.passing_touchdowns} passing TD(s)")
                passing_tds += stat.passing_touchdowns
            if hasattr(stat, 'receiving_touchdowns') and stat.receiving_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.receiving_touchdowns} receiving TD(s)")
                receiving_tds += stat.receiving_touchdowns

        # Check home team stats
        print(f"\n  {box_score.home_team_name}:")
        for stat in box_score.home_player_stats:
            if hasattr(stat, 'rushing_touchdowns') and stat.rushing_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.rushing_touchdowns} rushing TD(s)")
                rushing_tds += stat.rushing_touchdowns
            if hasattr(stat, 'passing_touchdowns') and stat.passing_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.passing_touchdowns} passing TD(s)")
                passing_tds += stat.passing_touchdowns
            if hasattr(stat, 'receiving_touchdowns') and stat.receiving_touchdowns > 0:
                print(f"    ✅ {stat.player_name}: {stat.receiving_touchdowns} receiving TD(s)")
                receiving_tds += stat.receiving_touchdowns

        # Summary
        print(f"\n" + "=" * 80)
        print("VERDICT")
        print("=" * 80)
        total_tds = rushing_tds + passing_tds + receiving_tds
        if total_tds > 0:
            print(f"\n✅ SUCCESS! Found {total_tds} touchdown(s) attributed to players:")
            print(f"   - Rushing TDs: {rushing_tds}")
            print(f"   - Passing TDs: {passing_tds}")
            print(f"   - Receiving TDs: {receiving_tds}")
            print(f"\n🎉 The TD attribution fix is working correctly!")
        else:
            print(f"\n❌ FAILURE: No TDs were attributed to any players")
            print(f"   Final score: {box_score.away_score} - {box_score.home_score}")
            if box_score.away_score > 0 or box_score.home_score > 0:
                print(f"   Points were scored but not attributed as TDs")
                print(f"   This may indicate the fix needs adjustment")
            else:
                print(f"   No points scored in the game (rare but possible)")

        print("=" * 80)

    else:
        print("❌ Could not retrieve box score from game result")


if __name__ == "__main__":
    main()
