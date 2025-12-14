#!/usr/bin/env python3
"""
Test Script: Validate Week 1 Tackle Rates After Coverage LB Fix

Tests that elite LBs average 10-12 tackles/game (not 20-24) after:
- Elite multiplier reduced from 2.0x to 1.3x
- Coverage LB base weight reduced from 45% to 35%

Expected Results:
✅ Elite LBs: 10-12 tackles/game
✅ Good LBs: 6-8 tackles/game
✅ No player exceeds 15 tackles in a single game
✅ More balanced distribution (not dominated by 1-2 elite players)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import random
from collections import defaultdict
from typing import Dict, List

# Set seed for reproducibility
random.seed(42)

def simulate_week1():
    """Simulate all Week 1 games and extract tackle stats."""
    from game_management.full_game_simulator import FullGameSimulator
    from constants.team_ids import TeamIDs

    # Week 1 matchups (example - could use real schedule)
    week1_matchups = [
        (TeamIDs.DETROIT_LIONS, TeamIDs.KANSAS_CITY_CHIEFS),  # Sunday Night Football
        (TeamIDs.DALLAS_COWBOYS, TeamIDs.NEW_YORK_GIANTS),    # Division rivalry
        (TeamIDs.GREEN_BAY_PACKERS, TeamIDs.CHICAGO_BEARS),   # Division rivalry
        (TeamIDs.BUFFALO_BILLS, TeamIDs.NEW_YORK_JETS),       # Division rivalry
        (TeamIDs.PHILADELPHIA_EAGLES, TeamIDs.NEW_ENGLAND_PATRIOTS),
        (TeamIDs.BALTIMORE_RAVENS, TeamIDs.HOUSTON_TEXANS),
        (TeamIDs.PITTSBURGH_STEELERS, TeamIDs.CINCINNATI_BENGALS),
        (TeamIDs.SAN_FRANCISCO_49ERS, TeamIDs.LOS_ANGELES_RAMS),
        (TeamIDs.MIAMI_DOLPHINS, TeamIDs.LOS_ANGELES_CHARGERS),
        (TeamIDs.CLEVELAND_BROWNS, TeamIDs.JACKSONVILLE_JAGUARS),
        (TeamIDs.ATLANTA_FALCONS, TeamIDs.CAROLINA_PANTHERS),
        (TeamIDs.TENNESSEE_TITANS, TeamIDs.NEW_ORLEANS_SAINTS),
        (TeamIDs.SEATTLE_SEAHAWKS, TeamIDs.DENVER_BRONCOS),
        (TeamIDs.LAS_VEGAS_RAIDERS, TeamIDs.MINNESOTA_VIKINGS),
        (TeamIDs.TAMPA_BAY_BUCCANEERS, TeamIDs.WASHINGTON_COMMANDERS),
        (TeamIDs.ARIZONA_CARDINALS, TeamIDs.INDIANAPOLIS_COLTS),
    ]

    all_player_stats = []
    games_completed = 0

    print("=" * 80)
    print("SIMULATING WEEK 1 GAMES")
    print("=" * 80)

    for game_num, (home_id, away_id) in enumerate(week1_matchups, 1):
        print(f"\n--- Game {game_num}: {home_id} vs {away_id} ---")

        try:
            simulator = FullGameSimulator(
                home_team_id=home_id,
                away_team_id=away_id,
                dynasty_id=None,
                db_path=None
            )

            game_result = simulator.simulate_game()
            games_completed += 1

            # Extract player stats
            if hasattr(game_result, 'box_score') and hasattr(game_result.box_score, 'player_stats'):
                for player_stats in game_result.box_score.player_stats:
                    tackles_solo = player_stats.get('tackles_total', 0)
                    tackles_assist = player_stats.get('tackles_assist', 0)
                    total_tackles = tackles_solo + tackles_assist

                    # Only track defensive players with tackles
                    if total_tackles > 0:
                        all_player_stats.append({
                            'name': player_stats.get('player_name', 'Unknown'),
                            'position': player_stats.get('position', 'Unknown'),
                            'team_id': player_stats.get('team_id'),
                            'solo': tackles_solo,
                            'assist': tackles_assist,
                            'total': total_tackles,
                            'snaps': player_stats.get('snap_counts_defense', 0),
                        })

                print(f"  ✓ Complete - Extracted {len([s for s in all_player_stats if s.get('team_id') in [home_id, away_id]])} player stats")
            else:
                print(f"  ⚠ No player stats found")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print(f"SIMULATION COMPLETE: {games_completed} of {len(week1_matchups)} games")
    print(f"{'=' * 80}")

    return all_player_stats


def analyze_tackle_distribution(player_stats: List[Dict]):
    """Analyze tackle distribution and identify issues."""

    # Group by position
    lb_stats = defaultdict(list)
    dl_stats = defaultdict(list)
    db_stats = defaultdict(list)

    lb_positions = ['linebacker', 'inside_linebacker', 'outside_linebacker',
                    'mike_linebacker', 'sam_linebacker', 'will_linebacker',
                    'olb', 'ilb', 'mlb']
    dl_positions = ['defensive_end', 'defensive_tackle', 'nose_tackle', 'de', 'dt', 'nt', 'edge']
    db_positions = ['cornerback', 'cb', 'safety', 'free_safety', 'strong_safety', 'fs', 'ss']

    for stat in player_stats:
        pos = stat['position'].lower()
        name = stat['name']

        if any(lb_pos in pos for lb_pos in lb_positions):
            lb_stats[name].append(stat)
        elif any(dl_pos in pos for dl_pos in dl_positions):
            dl_stats[name].append(stat)
        elif any(db_pos in pos for db_pos in db_positions):
            db_stats[name].append(stat)

    # Aggregate stats per player (in case of duplicates)
    def aggregate_stats(stats_dict):
        aggregated = {}
        for name, stat_list in stats_dict.items():
            total_tackles = sum(s['total'] for s in stat_list)
            total_solo = sum(s['solo'] for s in stat_list)
            total_assist = sum(s['assist'] for s in stat_list)
            total_snaps = sum(s['snaps'] for s in stat_list)
            games = len(stat_list)

            aggregated[name] = {
                'position': stat_list[0]['position'],
                'total': total_tackles,
                'solo': total_solo,
                'assist': total_assist,
                'snaps': total_snaps,
                'games': games,
                'avg_per_game': total_tackles / games if games > 0 else 0
            }
        return aggregated

    lb_aggregated = aggregate_stats(lb_stats)
    dl_aggregated = aggregate_stats(dl_stats)
    db_aggregated = aggregate_stats(db_stats)

    return lb_aggregated, dl_aggregated, db_aggregated


def print_results(lb_stats: Dict, dl_stats: Dict, db_stats: Dict):
    """Print formatted results with NFL comparisons."""

    print("\n" + "=" * 80)
    print("TOP LINEBACKERS (Week 1 Performance)")
    print("=" * 80)

    # Sort by total tackles
    top_lbs = sorted(lb_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:15]

    print(f"\n{'Player':<30} {'Pos':<20} {'Solo':<6} {'Ast':<6} {'Total':<6} {'Snaps':<6}")
    print("-" * 80)

    for name, stats in top_lbs:
        print(f"{name:<30} {stats['position']:<20} {stats['solo']:<6} {stats['assist']:<6} "
              f"{stats['total']:<6} {stats['snaps']:<6}")

    # Analyze distribution
    print("\n" + "=" * 80)
    print("TACKLE DISTRIBUTION ANALYSIS")
    print("=" * 80)

    if top_lbs:
        max_tackles = top_lbs[0][1]['total']
        players_over_15 = [lb for lb in top_lbs if lb[1]['total'] > 15]
        players_12_to_15 = [lb for lb in top_lbs if 12 <= lb[1]['total'] <= 15]
        players_8_to_12 = [lb for lb in top_lbs if 8 <= lb[1]['total'] < 12]

        print(f"\n  Max tackles (single game): {max_tackles}")
        print(f"  Players with 15+ tackles: {len(players_over_15)}")
        print(f"  Players with 12-15 tackles: {len(players_12_to_15)}")
        print(f"  Players with 8-12 tackles: {len(players_8_to_12)}")

        if players_over_15:
            print(f"\n  ⚠ WARNING: {len(players_over_15)} players exceeded 15 tackles!")
            for name, stats in players_over_15:
                print(f"    - {name}: {stats['total']} tackles")

    # NFL Benchmarks (2023 Season - Week 1 averages)
    print("\n" + "=" * 80)
    print("NFL BENCHMARK COMPARISON (2023 Week 1 Averages)")
    print("=" * 80)

    benchmarks = {
        'Elite LBs (Top 5)': (10, 12),
        'Good LBs (Top 10-20)': (7, 9),
        'Average LBs': (5, 7),
    }

    print(f"\n{'Category':<30} {'Expected Range':<20} {'Status'}")
    print("-" * 80)

    for category, (min_val, max_val) in benchmarks.items():
        print(f"{category:<30} {min_val}-{max_val} tackles")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    if not top_lbs:
        print("\n❌ FAIL: No linebacker data found!")
    elif max_tackles > 18:
        print(f"\n❌ FAIL: Max tackles ({max_tackles}) is UNREALISTICALLY HIGH (expected <15)")
        print("   Elite LBs should average 10-12 tackles, not 18+")
    elif len(players_over_15) > 2:
        print(f"\n⚠ WARNING: {len(players_over_15)} players exceeded 15 tackles")
        print("   This is more than expected (should be 0-1 per week league-wide)")
    elif max_tackles >= 12 and max_tackles <= 15:
        print(f"\n✅ PASS: Max tackles ({max_tackles}) is within elite range (12-15)")
        print("   Tackle distribution appears realistic!")
    elif max_tackles >= 8 and max_tackles < 12:
        print(f"\n✅ GOOD: Max tackles ({max_tackles}) is reasonable (8-12)")
        print("   Might be slightly low for elite performers, but realistic overall")
    else:
        print(f"\n⚠ ATTENTION: Max tackles ({max_tackles}) is LOW")
        print("   Elite LBs should be getting 10-12 tackles per game")


if __name__ == "__main__":
    print("Week 1 Tackle Rate Validation")
    print("Testing fixes for excessive linebacker tackle rates")
    print()

    # Run simulation
    player_stats = simulate_week1()

    if not player_stats:
        print("\n❌ ERROR: No player stats collected!")
        sys.exit(1)

    # Analyze distribution
    lb_stats, dl_stats, db_stats = analyze_tackle_distribution(player_stats)

    # Print results
    print_results(lb_stats, dl_stats, db_stats)

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
