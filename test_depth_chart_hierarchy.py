"""
Test script to verify position hierarchy integration with depth chart.

Checks that generic position players (like "guard" and "tackle") now appear
in specific position slots (like "left_guard", "right_guard", "left_tackle", "right_tackle").
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from depth_chart.depth_chart_api import DepthChartAPI
from constants.position_hierarchy import PositionHierarchy

# Test configuration
DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "first"  # Use dynasty with actual player data
TEAM_ID = 22  # Detroit Lions

def test_position_hierarchy():
    """Test position hierarchy methods."""
    print("=" * 80)
    print("TESTING POSITION HIERARCHY")
    print("=" * 80)

    # Test is_a relationships
    print("\n1. Testing IS-A relationships:")
    print(f"  left_guard IS-A guard: {PositionHierarchy.is_a('left_guard', 'guard')}")
    print(f"  left_guard IS-A offensive_line: {PositionHierarchy.is_a('left_guard', 'offensive_line')}")
    print(f"  left_guard IS-A linebacker: {PositionHierarchy.is_a('left_guard', 'linebacker')}")

    # Test get_children
    print("\n2. Testing get_children:")
    print(f"  guard children: {PositionHierarchy.get_children('guard')}")
    print(f"  tackle children: {PositionHierarchy.get_children('tackle')}")
    print(f"  offensive_line children: {PositionHierarchy.get_children('offensive_line')}")

    # Test get_ancestors
    print("\n3. Testing get_ancestors:")
    print(f"  left_guard ancestors: {PositionHierarchy.get_ancestors('left_guard')}")
    print(f"  right_tackle ancestors: {PositionHierarchy.get_ancestors('right_tackle')}")


def test_depth_chart_api():
    """Test depth chart API with position hierarchy."""
    print("\n" + "=" * 80)
    print("TESTING DEPTH CHART API WITH HIERARCHY")
    print("=" * 80)

    api = DepthChartAPI(DB_PATH)

    # Test offensive line positions
    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']

    print(f"\nTeam {TEAM_ID} (Detroit Lions) - Offensive Line Depth Chart:")
    print("-" * 80)

    for position in ol_positions:
        players = api.get_position_depth_chart(DYNASTY_ID, TEAM_ID, position)
        print(f"\n{position.replace('_', ' ').title()}:")
        if players:
            for player in players:
                print(f"  {player['depth_order']:2d}. {player['player_name']:30s} "
                      f"(OVR: {player['overall']:2d})")
        else:
            print("  [No players]")


def test_full_depth_chart():
    """Test full depth chart with position aggregation."""
    print("\n" + "=" * 80)
    print("TESTING FULL DEPTH CHART WITH POSITION AGGREGATION")
    print("=" * 80)

    api = DepthChartAPI(DB_PATH)
    full_chart = api.get_full_depth_chart(DYNASTY_ID, TEAM_ID)

    # Check offensive line positions
    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']

    print(f"\nTeam {TEAM_ID} (Detroit Lions) - Full Depth Chart Keys:")
    print("-" * 80)

    for position in ol_positions:
        if position in full_chart:
            player_count = len(full_chart[position])
            print(f"{position.replace('_', ' ').title():20s}: {player_count} player(s)")
            for player in full_chart[position]:
                print(f"  - {player['player_name']:30s} (OVR: {player['overall']:2d}, Pos: {player['position']})")
        else:
            print(f"{position.replace('_', ' ').title():20s}: [No players]")

    # Show all unique positions in full chart
    print(f"\nAll position keys in full chart: {sorted(full_chart.keys())}")


if __name__ == "__main__":
    try:
        test_position_hierarchy()
        test_depth_chart_api()
        test_full_depth_chart()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
