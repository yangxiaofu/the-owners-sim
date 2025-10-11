"""
Diagnostic script to test depth chart API with 'second' dynasty.
This will help identify why the UI shows "Empty" for all positions.
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from depth_chart.depth_chart_api import DepthChartAPI
from constants.position_hierarchy import PositionHierarchy
import json

# Test configuration
DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "second"  # The dynasty shown in screenshot
TEAM_ID = 22  # Detroit Lions

def test_raw_database_query():
    """Test raw database query to see what's actually in the database."""
    print("=" * 80)
    print("STEP 1: RAW DATABASE QUERY")
    print("=" * 80)

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get offensive line players
    query = """
        SELECT
            p.player_id,
            p.first_name || ' ' || p.last_name as player_name,
            p.positions,
            tr.depth_chart_order,
            p.attributes
        FROM players p
        JOIN team_rosters tr
            ON p.dynasty_id = tr.dynasty_id
            AND p.player_id = tr.player_id
        WHERE p.dynasty_id = ?
            AND p.team_id = ?
            AND (p.positions LIKE '%tackle%'
                 OR p.positions LIKE '%guard%'
                 OR p.positions LIKE '%center%')
        ORDER BY p.positions, tr.depth_chart_order
        LIMIT 15
    """

    cursor.execute(query, (DYNASTY_ID, TEAM_ID))
    results = cursor.fetchall()

    print(f"\nFound {len(results)} offensive line players in database:")
    for row in results:
        player_id, name, positions_json, depth_order, attrs_json = row
        positions = json.loads(positions_json)
        attrs = json.loads(attrs_json)
        print(f"  {name:30s} | Positions: {positions} | Depth: {depth_order} | OVR: {attrs.get('overall', 0)}")

    conn.close()


def test_api_get_position_depth_chart():
    """Test the API's get_position_depth_chart method."""
    print("\n" + "=" * 80)
    print("STEP 2: TEST API get_position_depth_chart()")
    print("=" * 80)

    api = DepthChartAPI(DB_PATH)

    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']

    for position in ol_positions:
        print(f"\nQuerying: {position}")
        players = api.get_position_depth_chart(DYNASTY_ID, TEAM_ID, position)
        print(f"  Result: {len(players)} player(s)")
        for player in players[:3]:  # Show first 3
            print(f"    - {player['player_name']:30s} (OVR: {player['overall']:2d}, Depth: {player['depth_order']})")


def test_api_get_full_depth_chart():
    """Test the API's get_full_depth_chart method."""
    print("\n" + "=" * 80)
    print("STEP 3: TEST API get_full_depth_chart()")
    print("=" * 80)

    api = DepthChartAPI(DB_PATH)
    full_chart = api.get_full_depth_chart(DYNASTY_ID, TEAM_ID)

    print(f"\nTotal position keys returned: {len(full_chart)}")
    print(f"Position keys: {sorted(full_chart.keys())}")

    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']

    print("\nOffensive Line Positions:")
    for position in ol_positions:
        if position in full_chart:
            print(f"  {position:20s}: {len(full_chart[position])} player(s)")
            for player in full_chart[position][:2]:  # Show first 2
                print(f"    - {player['player_name']:30s} (OVR: {player['overall']:2d}, Pos: {player['position']})")
        else:
            print(f"  {position:20s}: KEY NOT FOUND ❌")


def test_position_hierarchy_matching():
    """Test position hierarchy matching logic."""
    print("\n" + "=" * 80)
    print("STEP 4: TEST POSITION HIERARCHY MATCHING")
    print("=" * 80)

    # Test what positions should match for each OL slot
    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']

    print("\nExpected position matches:")
    for position in ol_positions:
        # Simulate _get_positions_matching_query logic
        matching = [position]
        parent = PositionHierarchy.get_parent(position)
        while parent and parent not in ['offense', 'defense', 'special_teams']:
            matching.append(parent)
            parent = PositionHierarchy.get_parent(parent)

        print(f"  {position:20s} should match: {matching}")


def test_actual_player_positions():
    """Test what positions are actually stored in the database."""
    print("\n" + "=" * 80)
    print("STEP 5: ACTUAL PLAYER POSITIONS IN DATABASE")
    print("=" * 80)

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get unique first positions for OL players
    query = """
        SELECT DISTINCT p.positions
        FROM players p
        JOIN team_rosters tr
            ON p.dynasty_id = tr.dynasty_id
            AND p.player_id = tr.player_id
        WHERE p.dynasty_id = ?
            AND p.team_id = ?
            AND (p.positions LIKE '%tackle%'
                 OR p.positions LIKE '%guard%'
                 OR p.positions LIKE '%center%')
    """

    cursor.execute(query, (DYNASTY_ID, TEAM_ID))
    results = cursor.fetchall()

    print(f"\nUnique position arrays for OL players:")
    for row in results:
        positions = json.loads(row[0])
        primary = positions[0] if positions else None
        print(f"  Primary position: {primary:30s} | Full array: {positions}")

    conn.close()


def test_hierarchy_with_multiposition_players():
    """Test if hierarchy handles multi-position players correctly."""
    print("\n" + "=" * 80)
    print("STEP 6: MULTI-POSITION PLAYER HANDLING")
    print("=" * 80)

    # Sample multi-position player
    sample_positions = ["center", "guard"]
    primary = sample_positions[0]

    print(f"\nSample player with positions: {sample_positions}")
    print(f"Primary position: {primary}")

    # What positions should this player appear under?
    api = DepthChartAPI(DB_PATH)
    matching = api._get_matching_positions_for_player(primary)

    print(f"Player should appear under these positions: {matching}")

    # Does this include left_guard and right_guard?
    if "left_guard" in matching:
        print("  ✅ Will appear in left_guard slot")
    else:
        print("  ❌ Will NOT appear in left_guard slot")

    if "right_guard" in matching:
        print("  ✅ Will appear in right_guard slot")
    else:
        print("  ❌ Will NOT appear in right_guard slot")


if __name__ == "__main__":
    try:
        test_raw_database_query()
        test_api_get_position_depth_chart()
        test_api_get_full_depth_chart()
        test_position_hierarchy_matching()
        test_actual_player_positions()
        test_hierarchy_with_multiposition_players()

        print("\n" + "=" * 80)
        print("✅ DIAGNOSTIC COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
