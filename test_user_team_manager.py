#!/usr/bin/env python3
"""
Basic test script for UserTeamManager functionality.

Tests the core functionality of the UserTeamManager class to verify it works
correctly with the existing dynasty and team systems.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from user_team.user_team_manager import UserTeamManager
from simulation.dynasty_context import DynastyContext
from constants.team_ids import TeamIDs


def test_user_team_manager():
    """Test UserTeamManager functionality."""
    print("=" * 60)
    print("🏈 UserTeamManager Test")
    print("=" * 60)
    print()

    # Initialize dynasty context for testing
    dynasty_context = DynastyContext()
    dynasty_context.initialize_dynasty("Test Dynasty", 2025)

    # Create UserTeamManager
    user_team_manager = UserTeamManager(dynasty_context)
    print("✅ UserTeamManager created successfully")
    print()

    # Test 1: Initially no team should be set
    print("Test 1: Initial state")
    print(f"  Has team: {user_team_manager.has_user_team()}")
    print(f"  Team ID: {user_team_manager.get_user_team_id()}")
    print(f"  Team name: {user_team_manager.get_user_team_name()}")
    print()

    # Test 2: Set user team to Detroit Lions
    print("Test 2: Setting user team to Detroit Lions")
    try:
        user_team_manager.set_user_team(TeamIDs.DETROIT_LIONS)
        print("✅ Team set successfully")

        print(f"  Has team: {user_team_manager.has_user_team()}")
        print(f"  Team ID: {user_team_manager.get_user_team_id()}")
        print(f"  Team name: {user_team_manager.get_user_team_name()}")
        print(f"  Abbreviation: {user_team_manager.get_user_team_abbreviation()}")

        # Test is_user_team method
        print(f"  Is Lions user team: {user_team_manager.is_user_team(TeamIDs.DETROIT_LIONS)}")
        print(f"  Is Packers user team: {user_team_manager.is_user_team(TeamIDs.GREEN_BAY_PACKERS)}")

    except Exception as e:
        print(f"❌ Error setting team: {e}")
    print()

    # Test 3: Get team object
    print("Test 3: Getting full team object")
    team = user_team_manager.get_user_team()
    if team:
        print(f"  Team object: {team}")
        print(f"  City: {team.city}")
        print(f"  Nickname: {team.nickname}")
        print(f"  Conference: {team.conference}")
        print(f"  Division: {team.division}")
    else:
        print("  No team object found")
    print()

    # Test 4: Get division rivals
    print("Test 4: Getting division rivals")
    rivals = user_team_manager.get_division_rivals()
    print(f"  Division rivals count: {len(rivals)}")
    for rival in rivals:
        print(f"    - {rival.full_name}")
    print()

    # Test 5: Get summary
    print("Test 5: Getting summary")
    summary = user_team_manager.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print()

    # Test 6: Error handling
    print("Test 6: Error handling")
    try:
        user_team_manager.set_user_team(99)  # Invalid team ID
        print("❌ Should have thrown error for invalid team ID")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")

    try:
        user_team_manager.set_user_team(-5)  # Invalid team ID
        print("❌ Should have thrown error for negative team ID")
    except ValueError as e:
        print(f"✅ Correctly caught error: {e}")
    print()

    # Test 7: Clear team
    print("Test 7: Clearing user team")
    user_team_manager.clear_user_team()
    print(f"  Has team after clear: {user_team_manager.has_user_team()}")
    print(f"  Team ID after clear: {user_team_manager.get_user_team_id()}")
    print()

    # Test 8: String representations
    print("Test 8: String representations")
    user_team_manager.set_user_team(TeamIDs.GREEN_BAY_PACKERS)
    print(f"  str(): {str(user_team_manager)}")
    print(f"  repr(): {repr(user_team_manager)}")
    print()

    print("=" * 60)
    print("🎉 All UserTeamManager tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_user_team_manager()