#!/usr/bin/env python3
"""
Test Team Name Display in Playoff Results

Validates that team names (not "Unknown") are displayed in game results.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id

# Import display function
try:
    from display_utils import display_playoff_game_results
except:
    from demo.interactive_playoff_sim.display_utils import display_playoff_game_results


def main():
    """Test team name display."""
    print("Testing Team Name Display in Playoff Results...")
    print("="*80)

    # Create mock game results with team IDs (as returned by SimulationExecutor)
    mock_results = [
        {
            'away_team_id': TeamIDs.KANSAS_CITY_CHIEFS,  # Team 7
            'home_team_id': TeamIDs.BUFFALO_BILLS,        # Team 3
            'away_score': 24,
            'home_score': 31,
            'away_seed': 3,
            'home_seed': 2,
            'round_name': 'divisional',
            'conference': 'AFC',
            'success': True
        },
        {
            'away_team_id': TeamIDs.SAN_FRANCISCO_49ERS,  # Team 25
            'home_team_id': TeamIDs.PHILADELPHIA_EAGLES,  # Team 21
            'away_score': 28,
            'home_score': 21,
            'round_name': 'conference',
            'conference': 'NFC',
            'success': True
        }
    ]

    # Verify team names can be loaded
    print("\n1. Verifying team data...")
    for result in mock_results:
        away_id = result['away_team_id']
        home_id = result['home_team_id']

        away_team = get_team_by_id(away_id)
        home_team = get_team_by_id(home_id)

        print(f"   Team {away_id}: {away_team.full_name if away_team else 'NOT FOUND'}")
        print(f"   Team {home_id}: {home_team.full_name if home_team else 'NOT FOUND'}")

    # Display game results using the display function
    print("\n2. Testing display_playoff_game_results()...")
    print("="*80)
    display_playoff_game_results(mock_results)

    # Check if it worked
    print("="*80)
    print("\n✅ TEST COMPLETE")
    print("\nIf you see team names (not 'Unknown') above, the fix is working!")
    print("Expected teams:")
    print("  - Kansas City Chiefs")
    print("  - Buffalo Bills")
    print("  - San Francisco 49ers")
    print("  - Philadelphia Eagles")


if __name__ == "__main__":
    main()
