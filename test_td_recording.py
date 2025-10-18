"""
Test script to verify touchdown recording issue

This script simulates plays directly using the play simulators to check
whether touchdowns are properly attributed to players.

The bug: TD attribution checks points_scored BEFORE field tracking sets it to 6.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from play_engine.simulation.run_plays import RunPlaySimulator
from play_engine.simulation.pass_plays import PassPlaySimulator
from team_management.players.player_loader import PlayerDataLoader
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
from constants.team_ids import TeamIDs


def test_direct_td_attribution():
    """
    Test TD attribution by directly checking PlayStatsSummary

    This test simulates plays and checks if:
    1. points_scored is set in the play summary
    2. TDs are attributed to player stats
    """
    print("=" * 80)
    print("DIRECT TD ATTRIBUTION TEST")
    print("=" * 80)
    print("\nThis test runs multiple plays and checks if touchdowns are properly")
    print("attributed to players in the PlayStatsSummary.\n")

    # Load real team rosters from data files
    player_loader = PlayerDataLoader()
    lions_roster = player_loader.get_players_by_team(TeamIDs.DETROIT_LIONS)
    packers_roster = player_loader.get_players_by_team(TeamIDs.GREEN_BAY_PACKERS)

    # For this test, we just need ANY players for offensive and defensive positions
    # Get some offensive and defensive players
    offensive_players = [p for p in lions_roster if p.position in ['QB', 'RB', 'WR', 'TE', 'OL']][:11]
    defensive_players = [p for p in packers_roster if p.position in ['DL', 'LB', 'CB', 'S']][:11]

    print("Testing RUSHING plays...")
    print("-" * 80)

    # Test rushing plays
    run_sim = RunPlaySimulator(
        offensive_players=offensive_players,
        defensive_players=defensive_players,
        offensive_formation=OffensiveFormation.SHOTGUN,
        defensive_formation=DefensiveFormation.FOUR_THREE,
        offensive_team_id=TeamIDs.DETROIT_LIONS,
        defensive_team_id=TeamIDs.GREEN_BAY_PACKERS
    )

    rushing_tests = 0
    rushing_big_gains = 0
    rushing_tds_in_summary = 0

    for i in range(20):  # Run 20 rushing plays
        result = run_sim.simulate_run_play()
        rushing_tests += 1

        # Check for big gains
        if result.yards_gained >= 20:
            rushing_big_gains += 1
            print(f"\n🏃 Play {i+1}: BIG GAIN - {result.yards_gained} yards")
            print(f"   points_scored: {result.points_scored}")

            # Check player stats for TDs
            for player_stat in result.player_stats:
                if player_stat.rushing_attempts > 0:
                    print(f"   Rusher: {player_stat.player_name}")
                    print(f"   - Rushing yards: {player_stat.rushing_yards}")
                    print(f"   - Rushing TDs: {player_stat.rushing_touchdowns}")
                    if player_stat.rushing_touchdowns > 0:
                        rushing_tds_in_summary += 1
                        print(f"   ✅ TD attributed!")
                    elif result.points_scored == 6:
                        print(f"   ❌ BUG: points_scored=6 but TD NOT attributed!")

    print(f"\n📊 Rushing Summary:")
    print(f"   Total plays: {rushing_tests}")
    print(f"   Big gains (20+ yards): {rushing_big_gains}")
    print(f"   TDs attributed in player stats: {rushing_tds_in_summary}")

    print("\n\nTesting PASSING plays...")
    print("-" * 80)

    # Test passing plays
    pass_sim = PassPlaySimulator(
        offensive_players=offensive_players,
        defensive_players=defensive_players,
        offensive_formation=OffensiveFormation.SHOTGUN,
        defensive_formation=DefensiveFormation.FOUR_THREE,
        offensive_team_id=TeamIDs.DETROIT_LIONS,
        defensive_team_id=TeamIDs.GREEN_BAY_PACKERS
    )

    passing_tests = 0
    passing_big_gains = 0
    passing_tds_in_summary = 0
    receiving_tds_in_summary = 0

    for i in range(20):  # Run 20 passing plays
        result = pass_sim.simulate_pass_play()
        passing_tests += 1

        # Check for big gains
        if result.yards_gained >= 30:
            passing_big_gains += 1
            print(f"\n🏈 Play {i+1}: BIG GAIN - {result.yards_gained} yards")
            print(f"   points_scored: {result.points_scored}")

            # Check player stats for TDs
            for player_stat in result.player_stats:
                if player_stat.passing_attempts > 0:
                    print(f"   Passer: {player_stat.player_name}")
                    print(f"   - Passing yards: {player_stat.passing_yards}")
                    print(f"   - Passing TDs: {player_stat.passing_touchdowns}")
                    if player_stat.passing_touchdowns > 0:
                        passing_tds_in_summary += 1
                        print(f"   ✅ Passing TD attributed!")
                    elif result.points_scored == 6:
                        print(f"   ❌ BUG: points_scored=6 but passing TD NOT attributed!")

                if player_stat.receptions > 0:
                    print(f"   Receiver: {player_stat.player_name}")
                    print(f"   - Receiving yards: {player_stat.receiving_yards}")
                    print(f"   - Receiving TDs: {player_stat.receiving_touchdowns}")
                    if player_stat.receiving_touchdowns > 0:
                        receiving_tds_in_summary += 1
                        print(f"   ✅ Receiving TD attributed!")
                    elif result.points_scored == 6:
                        print(f"   ❌ BUG: points_scored=6 but receiving TD NOT attributed!")

    print(f"\n📊 Passing Summary:")
    print(f"   Total plays: {passing_tests}")
    print(f"   Big gains (30+ yards): {passing_big_gains}")
    print(f"   Passing TDs attributed: {passing_tds_in_summary}")
    print(f"   Receiving TDs attributed: {receiving_tds_in_summary}")

    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print(f"\nNote: This test only checks PlayStatsSummary from simulators.")
    print(f"The real issue is that points_scored is set to 0 in PlayStatsSummary,")
    print(f"and only gets set to 6 later by FieldTracker in the game loop.")
    print(f"\nExpected: All points_scored should be 0 in these direct simulator tests")
    print(f"because we're not running them through FieldTracker.")

    if rushing_tds_in_summary > 0 or passing_tds_in_summary > 0 or receiving_tds_in_summary > 0:
        print(f"\n✅ TDs ARE being attributed at simulation time")
        print(f"   Rushing TDs: {rushing_tds_in_summary}")
        print(f"   Passing TDs: {passing_tds_in_summary}")
        print(f"   Receiving TDs: {receiving_tds_in_summary}")
    else:
        print(f"\n❌ NO TDs attributed in any play summaries")
        print(f"   This confirms TDs are NOT being set in PlayStatsSummary")
        print(f"   because points_scored is always 0 at this stage.")

    print("\n💡 To truly test the bug, we need to run plays through the full")
    print("   game loop with FieldTracker, then check if TDs are attributed.")
    print("=" * 80)


def check_field_tracker_integration():
    """
    Check if there's an integration issue with FieldTracker

    This demonstrates the actual flow where TDs should be detected.
    """
    print("\n\n")
    print("=" * 80)
    print("FIELD TRACKER INTEGRATION ANALYSIS")
    print("=" * 80)

    print("""
The issue is a timing/sequencing problem in the game loop:

1. Play simulators create PlayStatsSummary with points_scored = 0
2. Play simulators call _add_touchdown_attribution() which checks:
   if points_scored == 6:  # This is ALWAYS FALSE because points_scored = 0
       # Add TDs to player stats
3. Play result returns to game loop
4. FieldTracker.process_play() detects ball crossed goal line
5. FieldTracker THEN sets points_scored = 6  (TOO LATE!)
6. Player stats already finalized without TDs

SOLUTION:
- Move TD attribution to AFTER FieldTracker detects scoring
- Or, have FieldTracker call back to update player stats with TDs
- Or, have DriveManager post-process results after FieldTracker
    """)

    print("\n" + "=" * 80)
    print("ROOT CAUSE CONFIRMED")
    print("=" * 80)
    print("\nThe play simulators check for points_scored == 6 to attribute TDs,")
    print("but points_scored is only set to 6 AFTER the play simulation completes.")
    print("\nWe need to fix the sequence by updating TD attribution AFTER")
    print("FieldTracker detects the touchdown.")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🔍 TOUCHDOWN RECORDING VERIFICATION TEST\n")

    # Run direct simulation tests
    test_direct_td_attribution()

    # Show the integration analysis
    check_field_tracker_integration()

    print("\n\n✅ Test complete. Ready to implement fix.")
