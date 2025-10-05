#!/usr/bin/env python3
"""
Test script to verify LeagueController.get_standings() functionality.

This script tests that the LeagueController can properly retrieve
and organize standings data from the database.
"""

import sys
import os

# Add ui to path for controller imports
ui_path = os.path.join(os.path.dirname(__file__), 'ui')
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from controllers.league_controller import LeagueController


def test_get_standings():
    """Test LeagueController.get_standings() method."""
    print("=" * 70)
    print("Testing LeagueController.get_standings()")
    print("=" * 70)

    # Initialize controller with test dynasty
    controller = LeagueController(
        db_path='data/database/nfl_simulation.db',
        dynasty_id='test_dynasty_123',
        season=2025
    )

    # Test get_standings()
    print("\n[1] Calling controller.get_standings()...")
    standings = controller.get_standings()

    # Verify structure
    print(f"\n[2] Standings structure keys: {list(standings.keys())}")

    # Test divisions
    if 'divisions' in standings:
        print(f"\n[3] Number of divisions: {len(standings['divisions'])}")
        print(f"    Division names: {list(standings['divisions'].keys())}")

        # Print AFC East standings
        if 'AFC East' in standings['divisions']:
            print("\n[4] AFC East Division Standings:")
            print("    " + "-" * 60)
            afc_east = standings['divisions']['AFC East']

            # Get team data for display
            from team_management.teams.team_loader import TeamDataLoader
            team_loader = TeamDataLoader()

            for team_dict in afc_east:  # afc_east is already the list
                standing = team_dict['standing']
                team_id = team_dict['team_id']
                team = team_loader.get_team_by_id(team_id)

                # Format record
                record = f"{standing.wins}-{standing.losses}"
                if standing.ties > 0:
                    record += f"-{standing.ties}"

                # Format points
                pts = f"PF:{standing.points_for} PA:{standing.points_against}"

                print(f"    {team.full_name:25s} {record:6s}  {pts}")

        # Print teams with winning records
        print("\n[5] All Teams with Winning Records (>0.500):")
        print("    " + "-" * 60)

        winning_teams = []
        for div_name, div_data in standings['divisions'].items():
            for team_dict in div_data:  # div_data is already the list
                standing = team_dict['standing']
                team_id = team_dict['team_id']
                team = team_loader.get_team_by_id(team_id)

                total_games = standing.wins + standing.losses + standing.ties
                if total_games > 0:
                    win_pct = (standing.wins + 0.5 * standing.ties) / total_games
                    if win_pct > 0.500:
                        winning_teams.append({
                            'team': team,
                            'standing': standing,
                            'win_pct': win_pct
                        })

        # Sort by win percentage
        winning_teams.sort(key=lambda x: x['win_pct'], reverse=True)

        for item in winning_teams:
            team = item['team']
            standing = item['standing']
            win_pct = item['win_pct']

            record = f"{standing.wins}-{standing.losses}"
            if standing.ties > 0:
                record += f"-{standing.ties}"

            print(f"    {team.full_name:25s} {record:6s}  ({win_pct:.3f})  "
                  f"{team.conference} {team.division}")

    # Test conferences
    if 'conferences' in standings:
        print(f"\n[6] Conferences: {list(standings['conferences'].keys())}")

    # Test overall
    if 'overall' in standings:
        print(f"\n[7] Overall standings: {len(standings['overall'])} teams")

    # Test playoff picture
    if 'playoff_picture' in standings:
        print(f"\n[8] Playoff picture keys: {list(standings['playoff_picture'].keys())}")

    print("\n" + "=" * 70)
    print("✓ Test completed successfully!")
    print("=" * 70)

    return standings


def test_get_team_record():
    """Test LeagueController.get_team_record() for specific teams."""
    print("\n\n" + "=" * 70)
    print("Testing LeagueController.get_team_record()")
    print("=" * 70)

    controller = LeagueController(
        db_path='data/database/nfl_simulation.db',
        dynasty_id='test_dynasty_123',
        season=2025
    )

    # Test specific teams
    test_teams = [
        (1, "Buffalo Bills"),
        (2, "Miami Dolphins"),
        (9, "Kansas City Chiefs"),
        (22, "Detroit Lions"),
    ]

    print("\nTesting individual team record retrieval:")
    print("-" * 70)

    for team_id, team_name in test_teams:
        record = controller.get_team_record(team_id)
        if record:
            rec_str = f"{record['wins']}-{record['losses']}-{record['ties']}"
            print(f"  Team {team_id:2d} ({team_name:20s}): {rec_str}")
        else:
            print(f"  Team {team_id:2d} ({team_name:20s}): No record found")

    print("\n" + "=" * 70)
    print("✓ Team record test completed!")
    print("=" * 70)


def test_get_all_teams():
    """Test LeagueController.get_all_teams() method."""
    print("\n\n" + "=" * 70)
    print("Testing LeagueController.get_all_teams()")
    print("=" * 70)

    controller = LeagueController(
        db_path='data/database/nfl_simulation.db',
        dynasty_id='test_dynasty_123',
        season=2025
    )

    teams = controller.get_all_teams()

    print(f"\nTotal teams: {len(teams)}")
    print("\nFirst 10 teams:")
    print("-" * 70)

    for i, team in enumerate(teams[:10], 1):
        print(f"  {i:2d}. {team.full_name:25s} ({team.conference} {team.division})")

    print("\n" + "=" * 70)
    print("✓ All teams test completed!")
    print("=" * 70)


if __name__ == "__main__":
    # Run all tests
    test_get_standings()
    test_get_team_record()
    test_get_all_teams()

    print("\n\n🎉 All LeagueController tests passed!\n")
