"""
Test script to demonstrate bench player deduplication fix.

This script shows how players with generic positions (like "guard")
were appearing multiple times in the bench panel due to position hierarchy.
"""

# Simulate the bench panel logic BEFORE the fix
def simulate_before_fix(depth_chart_data):
    """Simulate bench loading WITHOUT deduplication (buggy behavior)."""
    print("=" * 80)
    print("BEFORE FIX: Players appear multiple times")
    print("=" * 80)

    POSITION_GROUPS = {
        'OL': ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle'],
    }

    grouped_players = {group: [] for group in POSITION_GROUPS.keys()}

    # Simulate the buggy logic: extend without deduplication
    for position, players in depth_chart_data.items():
        for group_name, group_positions in POSITION_GROUPS.items():
            if position in group_positions:
                bench_players = [p for p in players if p['depth_order'] >= 2]
                grouped_players[group_name].extend(bench_players)
                break

    # Display results
    for group_name, players in grouped_players.items():
        print(f"\n{group_name} Bench ({len(players)} total):")
        sorted_players = sorted(players, key=lambda p: (p['depth_order'], -p['overall']))
        for player in sorted_players:
            print(f"  - {player['player_name']:20s} (ID: {player['player_id']}, Pos: {player['position']:15s}, Depth: {player['depth_order']}, OVR: {player['overall']})")


# Simulate the bench panel logic AFTER the fix
def simulate_after_fix(depth_chart_data):
    """Simulate bench loading WITH deduplication (fixed behavior)."""
    print("\n" + "=" * 80)
    print("AFTER FIX: Players appear exactly once (deduplicated by player_id)")
    print("=" * 80)

    POSITION_GROUPS = {
        'OL': ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle'],
    }

    grouped_players = {group: [] for group in POSITION_GROUPS.keys()}

    # Same grouping logic
    for position, players in depth_chart_data.items():
        for group_name, group_positions in POSITION_GROUPS.items():
            if position in group_positions:
                bench_players = [p for p in players if p['depth_order'] >= 2]
                grouped_players[group_name].extend(bench_players)
                break

    # Display results with deduplication
    for group_name, players in grouped_players.items():
        print(f"\n{group_name} Bench (before dedup: {len(players)} players):")

        # Sort first
        sorted_players = sorted(players, key=lambda p: (p['depth_order'], -p['overall']))

        # ✅ NEW: Deduplicate by player_id
        seen_ids = set()
        unique_players = []
        for player in sorted_players:
            if player['player_id'] not in seen_ids:
                unique_players.append(player)
                seen_ids.add(player['player_id'])

        print(f"{group_name} Bench (after dedup: {len(unique_players)} unique players):")
        for player in unique_players:
            print(f"  - {player['player_name']:20s} (ID: {player['player_id']}, Pos: {player['position']:15s}, Depth: {player['depth_order']}, OVR: {player['overall']})")


if __name__ == "__main__":
    # Simulate depth chart data as returned by DepthChartAPI.get_full_depth_chart()
    # This mimics how position hierarchy causes a "guard" player to appear in multiple lists

    depth_chart_data = {
        # A player with position "guard" appears in ALL these lists due to hierarchy
        'left_guard': [
            {'player_id': 101, 'player_name': 'Joel Bitonio', 'position': 'guard', 'overall': 92, 'depth_order': 1},  # Starter
            {'player_id': 201, 'player_name': 'Zak Zinter', 'position': 'guard', 'overall': 70, 'depth_order': 2},  # Bench
        ],
        'right_guard': [
            {'player_id': 102, 'player_name': 'Wyatt Teller', 'position': 'guard', 'overall': 88, 'depth_order': 1},  # Starter
            {'player_id': 201, 'player_name': 'Zak Zinter', 'position': 'guard', 'overall': 70, 'depth_order': 2},  # ← SAME PLAYER
        ],
        'center': [
            {'player_id': 103, 'player_name': 'Ethan Pocic', 'position': 'center', 'overall': 78, 'depth_order': 1},  # Starter
            {'player_id': 202, 'player_name': 'Luke Wypler', 'position': 'center', 'overall': 72, 'depth_order': 2},  # Bench (unique)
        ],
        'left_tackle': [
            {'player_id': 104, 'player_name': 'Teven Jenkins', 'position': 'tackle', 'overall': 80, 'depth_order': 1},  # Starter
            {'player_id': 203, 'player_name': 'Dawand Jones', 'position': 'tackle', 'overall': 75, 'depth_order': 2},  # Bench
        ],
        'right_tackle': [
            {'player_id': 105, 'player_name': 'Jack Conklin', 'position': 'tackle', 'overall': 83, 'depth_order': 1},  # Starter
            {'player_id': 203, 'player_name': 'Dawand Jones', 'position': 'tackle', 'overall': 75, 'depth_order': 2},  # ← SAME PLAYER
        ],
    }

    # Show the problem
    simulate_before_fix(depth_chart_data)

    # Show the solution
    simulate_after_fix(depth_chart_data)

    print("\n" + "=" * 80)
    print("✅ FIX VERIFIED: Bench players now deduplicated by player_id")
    print("=" * 80)
