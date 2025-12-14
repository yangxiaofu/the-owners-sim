#!/usr/bin/env python3
"""
Investigation: Khalil Mack Tackle Inflation Bug

Simulates games and logs:
- Tackle attribution per play (primary/assisted)
- Which position category selected player (LB vs DL vs EDGE)
- Snap counts per position group
- Rating values used in weight calculation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import random
from collections import defaultdict
from typing import Dict, List

# Set seed for reproducibility
random.seed(42)

def find_khalil_mack():
    """Load Khalil Mack from player data."""
    from team_management.players.player_loader import PlayerDataLoader

    loader = PlayerDataLoader()
    chargers_players = loader.get_players_by_team(16)  # LA Chargers

    print("=" * 80)
    print("KHALIL MACK PLAYER DATA")
    print("=" * 80)

    for player in chargers_players:
        if 'Mack' in player.full_name and player.primary_position == 'outside_linebacker':
            print(f"\nFound: {player.full_name}")
            print(f"  Position: {player.primary_position}")
            print(f"  Overall: {player.overall_rating}")
            print(f"  Pass Rush: {player.get_attribute('pass_rush', 'N/A')}")
            print(f"  Run Defense: {player.get_attribute('run_defense', 'N/A')}")
            print(f"  Motor: {player.get_attribute('motor', 'N/A')}")
            print(f"  Awareness: {player.get_attribute('awareness', 'N/A')}")
            print(f"  Tackle: {player.get_attribute('tackle', 'N/A')}")
            print(f"  Pursuit: {player.get_attribute('pursuit', 'N/A')}")
            print(f"  Block Shedding: {player.get_attribute('block_shedding', 'N/A')}")
            return player

    print("\nWARNING: Khalil Mack not found on Chargers roster!")
    return None


def simulate_with_logging(num_games=10):
    """Simulate games and log tackle attribution."""
    from game_management.full_game_simulator import FullGameSimulator
    from constants.team_ids import TeamIDs

    results = {
        'games': [],
        'mack_stats': defaultdict(int),
        'olb_stats': defaultdict(lambda: defaultdict(int)),
        'mlb_stats': defaultdict(lambda: defaultdict(int)),
        'de_stats': defaultdict(lambda: defaultdict(int)),
    }

    # Opponent teams to rotate through
    opponents = [
        TeamIDs.BALTIMORE_RAVENS,  # Team 5
        TeamIDs.KANSAS_CITY_CHIEFS,  # Team 14
        TeamIDs.LAS_VEGAS_RAIDERS,  # Team 15
        TeamIDs.DENVER_BRONCOS,  # Team 13
        TeamIDs.BUFFALO_BILLS,  # Team 2
    ]

    print("\n" + "=" * 80)
    print("SIMULATING GAMES")
    print("=" * 80)

    for game_num in range(num_games):
        opponent_id = opponents[game_num % len(opponents)]

        print(f"\n--- Game {game_num + 1}: Chargers vs Team {opponent_id} ---")

        try:
            # Simulate Chargers (16) vs opponent
            simulator = FullGameSimulator(
                home_team_id=TeamIDs.LOS_ANGELES_CHARGERS,  # Chargers
                away_team_id=opponent_id,
                dynasty_id=None,
                db_path=None
            )

            game_result = simulator.simulate_game()

            # Extract stats from game result
            if hasattr(game_result, 'box_score'):
                box_score = game_result.box_score

                # Get defensive stats for Chargers
                if hasattr(box_score, 'player_stats'):
                    for player_stats in box_score.player_stats:
                        if player_stats.get('team_id') == TeamIDs.LOS_ANGELES_CHARGERS:
                            player_name = player_stats.get('player_name', '')
                            position = player_stats.get('position', '')
                            tackles = player_stats.get('tackles_total', 0)
                            assists = player_stats.get('tackles_assist', 0)
                            snaps = player_stats.get('snap_counts_defense', 0)
                            sacks = player_stats.get('sacks', 0.0)

                            # Track Khalil Mack specifically
                            if 'Mack' in player_name and position == 'outside_linebacker':
                                results['mack_stats']['tackles'] += tackles
                                results['mack_stats']['assists'] += assists
                                results['mack_stats']['snaps'] += snaps
                                results['mack_stats']['sacks'] += sacks
                                results['mack_stats']['games'] += 1

                                print(f"  Khalil Mack: {tackles} tackles, {assists} assists, {snaps} snaps, {sacks:.1f} sacks")

                            # Track other OLBs
                            elif position == 'outside_linebacker':
                                results['olb_stats'][player_name]['tackles'] += tackles
                                results['olb_stats'][player_name]['assists'] += assists
                                results['olb_stats'][player_name]['snaps'] += snaps
                                results['olb_stats'][player_name]['games'] += 1

                            # Track MLBs
                            elif 'linebacker' in position and position != 'outside_linebacker':
                                results['mlb_stats'][player_name]['tackles'] += tackles
                                results['mlb_stats'][player_name]['assists'] += assists
                                results['mlb_stats'][player_name]['snaps'] += snaps
                                results['mlb_stats'][player_name]['games'] += 1

                            # Track DEs
                            elif position in ['defensive_end', 'edge']:
                                results['de_stats'][player_name]['tackles'] += tackles
                                results['de_stats'][player_name]['assists'] += assists
                                results['de_stats'][player_name]['snaps'] += snaps
                                results['de_stats'][player_name]['games'] += 1

                results['games'].append({
                    'game_num': game_num + 1,
                    'opponent': opponent_id,
                    'score': f"{box_score.home_score}-{box_score.away_score}"
                })
            else:
                print("  WARNING: No box score found in game result")

        except Exception as e:
            print(f"  ERROR simulating game {game_num + 1}: {e}")
            import traceback
            traceback.print_exc()

    return results


def print_summary(results: Dict):
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    # Khalil Mack stats
    games = results['mack_stats']['games']
    if games > 0:
        print(f"\nKHALIL MACK ({games} games):")
        print(f"  Avg Tackles: {results['mack_stats']['tackles'] / games:.1f} per game")
        print(f"  Avg Assists: {results['mack_stats']['assists'] / games:.1f} per game")
        print(f"  Avg Total: {(results['mack_stats']['tackles'] + results['mack_stats']['assists']) / games:.1f} per game")
        print(f"  Avg Snaps: {results['mack_stats']['snaps'] / games:.1f} per game")
        print(f"  Avg Sacks: {results['mack_stats']['sacks'] / games:.2f} per game")

        # Calculate snap percentage (assuming ~65 defensive plays per game)
        avg_snaps = results['mack_stats']['snaps'] / games
        snap_pct = (avg_snaps / 65) * 100
        print(f"  Estimated Snap %: {snap_pct:.1f}%")
    else:
        print("\nWARNING: No Khalil Mack stats recorded!")

    # Other OLBs
    if results['olb_stats']:
        print(f"\nOTHER OUTSIDE LINEBACKERS:")
        for player_name, stats in sorted(results['olb_stats'].items(),
                                         key=lambda x: x[1]['tackles'], reverse=True):
            games = stats['games']
            if games > 0:
                avg_tackles = stats['tackles'] / games
                avg_assists = stats['assists'] / games
                avg_total = avg_tackles + avg_assists
                avg_snaps = stats['snaps'] / games
                print(f"  {player_name:30s}: {avg_total:4.1f} tackles/game ({avg_tackles:.1f} solo, {avg_assists:.1f} ast, {avg_snaps:.0f} snaps)")

    # MLBs for comparison
    if results['mlb_stats']:
        print(f"\nINSIDE/MIDDLE LINEBACKERS (for comparison):")
        for player_name, stats in sorted(results['mlb_stats'].items(),
                                         key=lambda x: x[1]['tackles'], reverse=True)[:5]:
            games = stats['games']
            if games > 0:
                avg_tackles = stats['tackles'] / games
                avg_assists = stats['assists'] / games
                avg_total = avg_tackles + avg_assists
                avg_snaps = stats['snaps'] / games
                print(f"  {player_name:30s}: {avg_total:4.1f} tackles/game ({avg_tackles:.1f} solo, {avg_assists:.1f} ast, {avg_snaps:.0f} snaps)")

    # DEs for comparison
    if results['de_stats']:
        print(f"\nDEFENSIVE ENDS (for comparison):")
        for player_name, stats in sorted(results['de_stats'].items(),
                                         key=lambda x: x[1]['tackles'], reverse=True)[:5]:
            games = stats['games']
            if games > 0:
                avg_tackles = stats['tackles'] / games
                avg_assists = stats['assists'] / games
                avg_total = avg_tackles + avg_assists
                avg_snaps = stats['snaps'] / games
                print(f"  {player_name:30s}: {avg_total:4.1f} tackles/game ({avg_tackles:.1f} solo, {avg_assists:.1f} ast, {avg_snaps:.0f} snaps)")


def compare_to_nfl_benchmarks(results: Dict):
    """Compare simulation results to 2023 NFL benchmarks."""
    benchmarks = {
        'TJ Watt (OLB)': 10.7,
        'Micah Parsons (OLB)': 8.1,
        'Khalil Mack (OLB)': 6.9,
        'Roquan Smith (MLB)': 13.2,
        'Fred Warner (MLB)': 12.5,
        'Myles Garrett (DE)': 7.2,
    }

    games = results['mack_stats']['games']
    if games == 0:
        print("\nWARNING: No games to compare!")
        return

    mack_avg_total = (results['mack_stats']['tackles'] + results['mack_stats']['assists']) / games

    print("\n" + "=" * 80)
    print("NFL BENCHMARK COMPARISON (2023 Season)")
    print("=" * 80)

    for player, tackles in benchmarks.items():
        diff = mack_avg_total - tackles
        if abs(diff) <= 2:
            status = "✓ OK"
        elif diff > 2:
            status = "✗ HIGH"
        else:
            status = "⚠ LOW"

        print(f"  {player:30s}: {tackles:4.1f} tackles/game   {status} (diff: {diff:+.1f})")

    print(f"\n  {'Simulated Khalil Mack':30s}: {mack_avg_total:4.1f} tackles/game")

    # Verdict
    print("\n" + "-" * 80)
    if mack_avg_total >= 15:
        print("VERDICT: BROKEN - Tackle rate is UNREALISTICALLY HIGH (15+ per game)")
    elif mack_avg_total >= 13:
        print("VERDICT: HIGH - Tackle rate is above elite OLB range (13-15 per game)")
    elif mack_avg_total >= 8:
        print("VERDICT: NORMAL - Tackle rate is within elite OLB range (8-12 per game)")
    elif mack_avg_total >= 5:
        print("VERDICT: LOW - Tackle rate is below expected for elite OLB (5-8 per game)")
    else:
        print("VERDICT: VERY LOW - Tackle rate is unrealistically low (<5 per game)")


if __name__ == "__main__":
    print("Khalil Mack Tackle Rate Investigation")
    print("=" * 80)

    # Find Khalil Mack
    mack = find_khalil_mack()

    if not mack:
        print("\nERROR: Could not find Khalil Mack. Exiting.")
        sys.exit(1)

    # Simulate games
    num_games = 10
    print(f"\nSimulating {num_games} games...")
    results = simulate_with_logging(num_games=num_games)

    # Print summary
    print_summary(results)

    # Compare to NFL benchmarks
    compare_to_nfl_benchmarks(results)

    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)
