"""
Debug script to inspect the actual stats structure returned by the game simulator.
"""

import os
import sys
import json

# Add paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from game_management.full_game_simulator import FullGameSimulator


def run_single_game_debug():
    """Run a single game and dump the stats structure."""
    print("=" * 80)
    print("DEBUGGING STATS STRUCTURE")
    print("=" * 80)

    # Simulate one game
    simulator = FullGameSimulator(
        away_team_id=1,
        home_team_id=2,
        dynasty_id=None,
        db_path=None
    )

    game_result = simulator.simulate_game()

    # Get the stats
    all_stats = {}
    if hasattr(simulator, '_game_loop_controller') and simulator._game_loop_controller:
        stats_agg = simulator._game_loop_controller.stats_aggregator
        if stats_agg:
            all_stats = stats_agg.get_all_statistics()

    print("\n" + "=" * 80)
    print("TOP-LEVEL KEYS IN all_stats:")
    print("=" * 80)
    for key in all_stats.keys():
        print(f"  - {key}: {type(all_stats[key])}")

    # Check game_info structure
    print("\n" + "=" * 80)
    print("GAME_INFO STRUCTURE:")
    print("=" * 80)
    game_info = all_stats.get('game_info', {})
    if isinstance(game_info, dict):
        for key, value in game_info.items():
            if isinstance(value, dict):
                print(f"  {key}: {{")
                for k, v in value.items():
                    print(f"    {k}: {v}")
                print("  }")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  game_info is NOT a dict, it's: {type(game_info)}")
        print(f"  Value: {game_info}")

    # Check situational_stats specifically
    print("\n" + "=" * 80)
    print("SITUATIONAL_STATS (the key data we need):")
    print("=" * 80)
    situational_stats = game_info.get('situational_stats', {}) if isinstance(game_info, dict) else {}
    if situational_stats:
        for key, value in situational_stats.items():
            print(f"  {key}: {value}")
    else:
        print("  EMPTY or NOT FOUND!")
        print(f"  game_info type: {type(game_info)}")
        print(f"  game_info keys: {game_info.keys() if isinstance(game_info, dict) else 'N/A'}")

    # Check team_statistics structure
    print("\n" + "=" * 80)
    print("TEAM_STATISTICS STRUCTURE:")
    print("=" * 80)
    team_stats = all_stats.get('team_statistics', {})
    for team_key in ['home_team', 'away_team']:
        print(f"\n  {team_key}:")
        team_data = team_stats.get(team_key, {})
        if isinstance(team_data, dict):
            # Show key fields we care about
            important_fields = [
                'total_yards', 'passing_yards', 'rushing_yards', 'first_downs',
                'turnovers', 'sacks', 'penalties', 'penalty_yards'
            ]
            for field in important_fields:
                value = team_data.get(field, 'NOT FOUND')
                print(f"    {field}: {value}")
        else:
            print(f"    NOT A DICT: {type(team_data)}")

    # Check player_statistics for kicker
    print("\n" + "=" * 80)
    print("KICKER STATS (checking field names):")
    print("=" * 80)
    player_stats = all_stats.get('player_statistics', {})
    all_players = player_stats.get('all_players', [])

    kickers = [p for p in all_players if p.get('position') == 'kicker']
    if kickers:
        for k in kickers[:2]:  # Show first 2 kickers
            print(f"\n  Kicker: {k.get('player_name', 'Unknown')}")
            # Show all numeric stats
            for key, value in k.items():
                if isinstance(value, (int, float)) and value != 0:
                    print(f"    {key}: {value}")
    else:
        print("  No kickers found!")
        # Show what positions exist
        positions = set(p.get('position', 'UNK') for p in all_players)
        print(f"  Available positions: {sorted(positions)}")

    # Final summary
    print("\n" + "=" * 80)
    print("GAME RESULT SUMMARY:")
    print("=" * 80)
    print(f"  Final Score: {game_result.final_score}")
    print(f"  Total Plays: {game_result.total_plays}")
    print(f"  Total Drives: {game_result.total_drives}")

    return all_stats


if __name__ == "__main__":
    run_single_game_debug()