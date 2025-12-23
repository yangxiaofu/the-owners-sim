#!/usr/bin/env python3
"""
Defensive Snap Count Audit Script

Audits defensive player playing time across all position groups to identify
issues with snap distribution and sack attribution.

Usage:
    PYTHONPATH=src python scripts/audit_defensive_snaps.py

This script:
1. Simulates a full game between two teams
2. Tracks snap counts by position group
3. Audits elite pass rushers (90+ pass_rush rating)
4. Analyzes sack attribution
5. Verifies position mapping between roster and formations
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from team_management.personnel import TeamRosterGenerator
from team_management.players.player import Position
from play_engine.mechanics.formations import DefensiveFormation
from constants.position_abbreviations import get_position_limit_with_aliases, POSITION_ALIASES
from game_management.full_game_simulator import FullGameSimulator


# Position groups for analysis
DEFENSIVE_POSITION_GROUPS = {
    "Defensive End (DE)": ["defensive_end"],
    "Defensive Tackle (DT)": ["defensive_tackle", "nose_tackle"],
    "MIKE Linebacker": ["mike_linebacker"],
    "SAM Linebacker": ["sam_linebacker"],
    "WILL Linebacker": ["will_linebacker"],
    "Inside Linebacker (ILB)": ["inside_linebacker"],
    "Outside Linebacker (OLB)": ["outside_linebacker"],
    "Cornerback (CB)": ["cornerback", "nickel_cornerback"],
    "Free Safety (FS)": ["free_safety"],
    "Strong Safety (SS)": ["strong_safety"],
}


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def analyze_roster_positions(roster: List) -> Dict[str, List]:
    """Organize roster by position and analyze depth chart."""
    position_groups = defaultdict(list)

    for player in roster:
        pos = getattr(player, 'primary_position', 'unknown')
        depth_order = getattr(player, 'depth_chart_order', 99)
        overall = player.get_rating('overall') if hasattr(player, 'get_rating') else 0
        pass_rush = player.get_rating('pass_rush') if hasattr(player, 'get_rating') else 0

        position_groups[pos].append({
            'name': getattr(player, 'name', 'Unknown'),
            'position': pos,
            'depth_chart_order': depth_order,
            'overall': overall,
            'pass_rush': pass_rush,
            'player': player
        })

    # Sort each group by depth chart order
    for pos in position_groups:
        position_groups[pos].sort(key=lambda p: (p['depth_chart_order'], -p['overall']))

    return dict(position_groups)


def check_formation_requirements():
    """Check formation personnel requirements and position mapping."""
    print_header("FORMATION PERSONNEL REQUIREMENTS")

    formations = [
        ("4-3 Base", DefensiveFormation.FOUR_THREE),
        ("3-4 Base", DefensiveFormation.THREE_FOUR),
        ("Nickel", DefensiveFormation.NICKEL),
        ("Dime", DefensiveFormation.DIME),
    ]

    for name, formation in formations:
        print_subheader(name)
        personnel = DefensiveFormation.get_personnel_requirements(formation)

        if not personnel:
            print(f"  ⚠️  No personnel requirements found for formation: {formation}")
            continue

        total = 0
        for pos, count in sorted(personnel.items(), key=lambda x: -x[1]):
            print(f"  {pos:25s}: {count}")
            total += count
        print(f"  {'TOTAL':25s}: {total}")

        if total != 11:
            print(f"  ⚠️  WARNING: Formation requires {total} players, expected 11!")


def check_position_aliases():
    """Check position alias definitions."""
    print_header("POSITION ALIAS CONFIGURATION")

    print_subheader("Defined Aliases")
    for generic, specifics in POSITION_ALIASES.items():
        print(f"  {generic:25s} → {', '.join(specifics)}")

    print_subheader("Missing Aliases (Potential Issues)")
    # Check if defensive_end has any aliases
    de_aliases = []
    for generic, specifics in POSITION_ALIASES.items():
        if 'defensive_end' in specifics:
            de_aliases.append(generic)

    if not de_aliases:
        print("  ✓ defensive_end has NO aliases defined - players must have exact position match")
    else:
        print(f"  defensive_end is aliased by: {de_aliases}")


def simulate_game_and_collect_stats(home_team_id: int, away_team_id: int) -> Dict[str, Any]:
    """Simulate a full game and collect detailed player statistics."""
    print_header(f"SIMULATING GAME: Team {away_team_id} @ Team {home_team_id}")

    # Use synthetic rosters for demo (no database required)
    simulator = FullGameSimulator(
        away_team_id=away_team_id,
        home_team_id=home_team_id,
        dynasty_id=None,  # Use synthetic rosters
        db_path=None
    )

    print(f"  Home Team: {simulator.home_team.city} {simulator.home_team.nickname}")
    print(f"  Away Team: {simulator.away_team.city} {simulator.away_team.nickname}")
    print(f"  Home Roster: {len(simulator.home_roster)} players")
    print(f"  Away Roster: {len(simulator.away_roster)} players")

    # Run the simulation
    print("\n  Simulating game...")
    game_result = simulator.simulate_game()

    print(f"\n  Final Score: {simulator.away_team.nickname} {game_result.final_score.get(away_team_id, 0)} - "
          f"{simulator.home_team.nickname} {game_result.final_score.get(home_team_id, 0)}")
    print(f"  Total Plays: {game_result.total_plays}")

    return {
        'game_result': game_result,
        'home_roster': simulator.home_roster,
        'away_roster': simulator.away_roster,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'player_stats': game_result.player_stats
    }


def analyze_defensive_snaps(game_data: Dict[str, Any]):
    """Analyze defensive snap distribution by position."""
    print_header("DEFENSIVE SNAP DISTRIBUTION")

    player_stats = game_data.get('player_stats', [])

    if not player_stats:
        print("  ⚠️  No player stats available from game simulation!")
        return

    # Organize stats by position
    position_stats = defaultdict(list)

    for stat in player_stats:
        if isinstance(stat, dict):
            pos = stat.get('position', 'unknown')
            def_snaps = stat.get('defensive_snaps', 0) or stat.get('snap_counts_defense', 0) or 0
            off_snaps = stat.get('offensive_snaps', 0) or stat.get('snap_counts_offense', 0) or 0

            # Only include players with defensive snaps or who are defensive positions
            if def_snaps > 0 or pos in [
                'defensive_end', 'defensive_tackle', 'nose_tackle',
                'mike_linebacker', 'sam_linebacker', 'will_linebacker',
                'inside_linebacker', 'outside_linebacker',
                'cornerback', 'nickel_cornerback', 'free_safety', 'strong_safety'
            ]:
                position_stats[pos].append({
                    'name': stat.get('player_name', 'Unknown'),
                    'position': pos,
                    'defensive_snaps': def_snaps,
                    'offensive_snaps': off_snaps,
                    'sacks': stat.get('sacks', 0),
                    'tackles': stat.get('tackles', 0) or stat.get('tackles_total', 0),
                    'qb_hits': stat.get('qb_hits', 0),
                    'qb_pressures': stat.get('qb_pressures', 0),
                })

    # Print by position group
    for group_name, positions in DEFENSIVE_POSITION_GROUPS.items():
        print_subheader(group_name)

        group_players = []
        for pos in positions:
            group_players.extend(position_stats.get(pos, []))

        if not group_players:
            print(f"  No players found at {positions}")
            continue

        # Sort by defensive snaps
        group_players.sort(key=lambda p: -p['defensive_snaps'])

        print(f"  {'Player':<30} {'Pos':<12} {'D-Snaps':<10} {'Sacks':<8} {'Tackles':<8} {'QB Hits':<8}")
        print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")

        for player in group_players:
            print(f"  {player['name']:<30} {player['position']:<12} "
                  f"{player['defensive_snaps']:<10} {player['sacks']:<8.1f} "
                  f"{player['tackles']:<8} {player['qb_hits']:<8}")

        # Summarize
        total_snaps = sum(p['defensive_snaps'] for p in group_players)
        total_sacks = sum(p['sacks'] for p in group_players)
        print(f"  {'TOTAL':<30} {'':<12} {total_snaps:<10} {total_sacks:<8.1f}")


def analyze_elite_pass_rushers(game_data: Dict[str, Any]):
    """Analyze elite pass rushers (90+ pass_rush rating)."""
    print_header("ELITE PASS RUSHER AUDIT (90+ Pass Rush Rating)")

    # Combine both rosters
    all_rosters = game_data.get('home_roster', []) + game_data.get('away_roster', [])
    player_stats = game_data.get('player_stats', [])

    # Create stats lookup by player name
    stats_by_name = {}
    for stat in player_stats:
        if isinstance(stat, dict):
            name = stat.get('player_name', '')
            stats_by_name[name] = stat

    # Find elite pass rushers
    elite_rushers = []
    for player in all_rosters:
        pass_rush = player.get_rating('pass_rush') if hasattr(player, 'get_rating') else 0
        overall = player.get_rating('overall') if hasattr(player, 'get_rating') else 0

        if pass_rush >= 90:
            name = getattr(player, 'name', 'Unknown')
            pos = getattr(player, 'primary_position', 'unknown')
            depth = getattr(player, 'depth_chart_order', 99)

            # Get game stats
            stat = stats_by_name.get(name, {})
            def_snaps = stat.get('defensive_snaps', 0) or stat.get('snap_counts_defense', 0) or 0
            sacks = stat.get('sacks', 0)
            qb_hits = stat.get('qb_hits', 0)

            elite_rushers.append({
                'name': name,
                'position': pos,
                'pass_rush': pass_rush,
                'overall': overall,
                'depth_order': depth,
                'snaps': def_snaps,
                'sacks': sacks,
                'qb_hits': qb_hits,
            })

    if not elite_rushers:
        print("  No elite pass rushers (90+ rating) found in rosters")
        print("  Note: Synthetic rosters use random ratings - elite players may not exist")
        return

    # Sort by pass_rush rating
    elite_rushers.sort(key=lambda p: -p['pass_rush'])

    print(f"  {'Player':<30} {'Pos':<12} {'P.Rush':<8} {'Depth':<6} {'Snaps':<8} {'Sacks':<8} {'QB Hits':<8}")
    print(f"  {'-'*30} {'-'*12} {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*8}")

    for player in elite_rushers:
        # Flag if elite player got 0 snaps
        snap_warning = "⚠️ " if player['snaps'] == 0 else ""
        print(f"  {player['name']:<30} {player['position']:<12} "
              f"{player['pass_rush']:<8} {player['depth_order']:<6} "
              f"{snap_warning}{player['snaps']:<8} {player['sacks']:<8.1f} {player['qb_hits']:<8}")

    # Summary statistics
    print_subheader("Elite Rusher Summary")
    total_elite = len(elite_rushers)
    with_snaps = sum(1 for p in elite_rushers if p['snaps'] > 0)
    total_sacks = sum(p['sacks'] for p in elite_rushers)

    print(f"  Total elite rushers:     {total_elite}")
    print(f"  With defensive snaps:    {with_snaps}")
    print(f"  Without snaps:           {total_elite - with_snaps}")
    print(f"  Combined sacks:          {total_sacks:.1f}")

    if total_elite - with_snaps > 0:
        print(f"\n  ⚠️  WARNING: {total_elite - with_snaps} elite pass rusher(s) got 0 snaps!")


def analyze_sack_leaders(game_data: Dict[str, Any]):
    """Analyze sack attribution to identify top performers."""
    print_header("SACK ATTRIBUTION ANALYSIS")

    player_stats = game_data.get('player_stats', [])

    # Collect all players with sacks
    sack_leaders = []
    for stat in player_stats:
        if isinstance(stat, dict):
            sacks = stat.get('sacks', 0)
            if sacks > 0:
                sack_leaders.append({
                    'name': stat.get('player_name', 'Unknown'),
                    'position': stat.get('position', 'unknown'),
                    'sacks': sacks,
                    'qb_hits': stat.get('qb_hits', 0),
                    'qb_pressures': stat.get('qb_pressures', 0),
                    'tackles_for_loss': stat.get('tackles_for_loss', 0),
                })

    if not sack_leaders:
        print("  No sacks recorded in this game")
        return

    # Sort by sacks
    sack_leaders.sort(key=lambda p: -p['sacks'])

    print(f"  {'Player':<30} {'Pos':<15} {'Sacks':<8} {'QB Hits':<10} {'Pressures':<10} {'TFL':<8}")
    print(f"  {'-'*30} {'-'*15} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

    for player in sack_leaders[:15]:  # Top 15
        print(f"  {player['name']:<30} {player['position']:<15} "
              f"{player['sacks']:<8.1f} {player['qb_hits']:<10} "
              f"{player['qb_pressures']:<10} {player['tackles_for_loss']:<8}")

    # Position breakdown
    print_subheader("Sacks by Position")
    pos_sacks = defaultdict(float)
    for player in sack_leaders:
        pos_sacks[player['position']] += player['sacks']

    for pos, sacks in sorted(pos_sacks.items(), key=lambda x: -x[1]):
        print(f"  {pos:<25}: {sacks:.1f} sacks")


def verify_position_mapping(roster: List):
    """Verify that roster positions match formation requirements."""
    print_header("POSITION MAPPING VERIFICATION")

    # Get all positions used in formations
    formation_positions = set()
    for formation in [DefensiveFormation.FOUR_THREE, DefensiveFormation.THREE_FOUR,
                      DefensiveFormation.NICKEL, DefensiveFormation.DIME]:
        personnel = DefensiveFormation.get_personnel_requirements(formation)
        formation_positions.update(personnel.keys())

    print_subheader("Formation Required Positions")
    for pos in sorted(formation_positions):
        print(f"  - {pos}")

    # Get all positions in roster
    roster_positions = set()
    for player in roster:
        pos = getattr(player, 'primary_position', 'unknown')
        roster_positions.add(pos)

    print_subheader("Roster Positions Found")
    for pos in sorted(roster_positions):
        in_formation = "✓" if pos in formation_positions else "⚠️ NOT IN FORMATIONS"
        count = sum(1 for p in roster if getattr(p, 'primary_position', '') == pos)
        print(f"  - {pos:<25} ({count} players) {in_formation}")

    # Check for mismatches
    print_subheader("Position Matching Issues")

    missing_from_roster = formation_positions - roster_positions
    if missing_from_roster:
        print(f"  ⚠️  Formation positions NOT in roster: {missing_from_roster}")
    else:
        print(f"  ✓  All formation positions have roster players")

    extra_in_roster = roster_positions - formation_positions
    if extra_in_roster:
        print(f"  ℹ️  Roster positions not in base formations: {extra_in_roster}")
        print(f"      (These may use position aliases or be special teams)")


def audit_real_player_data():
    """Audit real player data from JSON files to find Myles Garrett and other elite rushers."""
    print_header("REAL PLAYER DATA AUDIT")

    from team_management.players.player_loader import PlayerDataLoader

    try:
        loader = PlayerDataLoader()
        print(f"  Loaded {len(loader)} real players")

        # Find Cleveland Browns (team_id=7)
        browns_players = loader.get_players_by_team(7)
        print(f"\n  Cleveland Browns: {len(browns_players)} players")

        # Find all defensive ends
        all_des = loader.get_players_by_position('defensive_end')
        print(f"  Total DEs in database: {len(all_des)}")

        # Find elite pass rushers
        print_subheader("Elite Pass Rushers (90+ pass_rush)")
        elite_rushers = []
        for player in loader._players_by_id.values():
            pass_rush = player.get_attribute('pass_rush', 0)
            if pass_rush >= 90:
                elite_rushers.append(player)

        elite_rushers.sort(key=lambda p: -p.get_attribute('pass_rush', 0))

        print(f"  {'Player':<25} {'Team':<6} {'Pos':<15} {'OVR':<6} {'P.Rush':<8}")
        print(f"  {'-'*25} {'-'*6} {'-'*15} {'-'*6} {'-'*8}")

        for player in elite_rushers[:20]:
            pos = player.primary_position if hasattr(player, 'primary_position') else player.positions[0]
            print(f"  {player.full_name:<25} {player.team_id:<6} {pos:<15} "
                  f"{player.overall_rating:<6} {player.get_attribute('pass_rush'):<8}")

        # Specifically look for Myles Garrett
        print_subheader("Myles Garrett Lookup")
        myles = loader.search_players_by_name('Garrett')
        for player in myles:
            if 'Myles' in player.first_name or 'Myles' in player.full_name:
                print(f"  Found: {player.full_name}")
                print(f"    Team ID: {player.team_id}")
                print(f"    Position(s): {player.positions}")
                print(f"    Overall: {player.overall_rating}")
                print(f"    Pass Rush: {player.get_attribute('pass_rush')}")
                print(f"    Power Moves: {player.get_attribute('power_moves')}")
                print(f"    Finesse Moves: {player.get_attribute('finesse_moves')}")

        return elite_rushers

    except Exception as e:
        print(f"  ⚠️  Could not load real player data: {e}")
        return []


def run_full_audit():
    """Run the complete defensive snap audit."""
    print("\n" + "=" * 80)
    print("  DEFENSIVE PLAYER SNAP COUNT AUDIT")
    print("  Analyzing snap distribution for all defensive position groups")
    print("=" * 80)

    # 0. First audit real player data to find elite rushers
    elite_rushers = audit_real_player_data()

    # 1. Check formation requirements
    check_formation_requirements()

    # 2. Check position aliases
    check_position_aliases()

    # 3. Simulate a game (Browns vs 49ers as example)
    # Cleveland Browns = 7, San Francisco 49ers = 31
    game_data = simulate_game_and_collect_stats(home_team_id=7, away_team_id=31)

    # 4. Analyze rosters before looking at stats
    print_header("HOME TEAM ROSTER ANALYSIS")
    home_positions = analyze_roster_positions(game_data['home_roster'])
    for pos, players in sorted(home_positions.items()):
        print(f"\n  {pos} ({len(players)} players):")
        for p in players[:3]:  # Show top 3
            print(f"    #{p['depth_chart_order']}: {p['name']} (OVR: {p['overall']}, Pass Rush: {p['pass_rush']})")

    # 5. Analyze defensive snaps
    analyze_defensive_snaps(game_data)

    # 6. Audit elite pass rushers
    analyze_elite_pass_rushers(game_data)

    # 7. Analyze sack leaders
    analyze_sack_leaders(game_data)

    # 8. Verify position mapping
    verify_position_mapping(game_data['home_roster'])

    # Final recommendations
    print_header("RECOMMENDATIONS")
    print("""
  Based on the audit, check for these potential issues:

  1. DEPTH CHART ORDER: Ensure defensive starters have depth_chart_order=1
     - If all positions have depth_chart_order=1, players sort by overall
     - DEs should be early in the sorted roster to get snaps

  2. POSITION MAPPING: Verify roster positions match formation requirements
     - defensive_end should map to DE slots in 4-3/3-4
     - Check for misspelled or non-standard position strings

  3. SACK ATTRIBUTION: Elite rushers (90+ pass_rush) should dominate sacks
     - They get 2.0x weight multiplier + position bonus
     - If they're not leading, check if they're getting snaps

  4. FORMATION SELECTION: Check which formations are being called
     - Different formations use different position mixes
     - 4-3 uses DE/DT/LB, 3-4 uses more OLB

  Run this script with DEBUG=1 environment variable for more detailed output.
""")


if __name__ == "__main__":
    run_full_audit()
