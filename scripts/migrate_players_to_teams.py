#!/usr/bin/env python3
"""
Player Data Migration Script
============================

Migrates the large players.json file into team-based files for better organization.
Splits players by team_id into individual JSON files in src/data/players/ directory.

Usage:
    python migrate_players_to_teams.py [--dry-run] [--test-teams team1,team2,...]

Options:
    --dry-run: Preview changes without writing files
    --test-teams: Only migrate specific teams (comma-separated team IDs)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import argparse
from collections import defaultdict

# Add src to path to import constants
sys.path.insert(0, 'src')
from constants.team_ids import TeamIDs

def get_team_name_by_id(team_id: int) -> str:
    """Get team name from team ID using the constants"""
    team_mapping = {
        1: "buffalo_bills",
        2: "miami_dolphins",
        3: "new_england_patriots",
        4: "new_york_jets",
        5: "baltimore_ravens",
        6: "cincinnati_bengals",
        7: "cleveland_browns",
        8: "pittsburgh_steelers",
        9: "houston_texans",
        10: "indianapolis_colts",
        11: "jacksonville_jaguars",
        12: "tennessee_titans",
        13: "denver_broncos",
        14: "kansas_city_chiefs",
        15: "las_vegas_raiders",
        16: "los_angeles_chargers",
        17: "dallas_cowboys",
        18: "new_york_giants",
        19: "philadelphia_eagles",
        20: "washington_commanders",
        21: "chicago_bears",
        22: "detroit_lions",
        23: "green_bay_packers",
        24: "minnesota_vikings",
        25: "atlanta_falcons",
        26: "carolina_panthers",
        27: "new_orleans_saints",
        28: "tampa_bay_buccaneers",
        29: "arizona_cardinals",
        30: "los_angeles_rams",
        31: "san_francisco_49ers",
        32: "seattle_seahawks"
    }
    return team_mapping.get(team_id, f"team_{team_id}")

def get_team_display_name(team_id: int) -> str:
    """Get display name for team"""
    display_mapping = {
        1: "Buffalo Bills",
        2: "Miami Dolphins",
        3: "New England Patriots",
        4: "New York Jets",
        5: "Baltimore Ravens",
        6: "Cincinnati Bengals",
        7: "Cleveland Browns",
        8: "Pittsburgh Steelers",
        9: "Houston Texans",
        10: "Indianapolis Colts",
        11: "Jacksonville Jaguars",
        12: "Tennessee Titans",
        13: "Denver Broncos",
        14: "Kansas City Chiefs",
        15: "Las Vegas Raiders",
        16: "Los Angeles Chargers",
        17: "Dallas Cowboys",
        18: "New York Giants",
        19: "Philadelphia Eagles",
        20: "Washington Commanders",
        21: "Chicago Bears",
        22: "Detroit Lions",
        23: "Green Bay Packers",
        24: "Minnesota Vikings",
        25: "Atlanta Falcons",
        26: "Carolina Panthers",
        27: "New Orleans Saints",
        28: "Tampa Bay Buccaneers",
        29: "Arizona Cardinals",
        30: "Los Angeles Rams",
        31: "San Francisco 49ers",
        32: "Seattle Seahawks"
    }
    return display_mapping.get(team_id, f"Team {team_id}")

def load_players_data(players_file: str) -> Dict[str, Any]:
    """Load players data from JSON file"""
    try:
        with open(players_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Players file not found: {players_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in players file: {e}")

def group_players_by_team(players_data: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    """Group players by team_id"""
    teams = defaultdict(list)
    players_dict = players_data.get('players', {})

    for player_id, player_data in players_dict.items():
        team_id = player_data.get('team_id')
        if team_id is None:
            print(f"Warning: Player {player_id} has no team_id, skipping")
            continue

        # Store player with their ID as a key in the data
        teams[team_id].append((player_id, player_data))

    return teams

def create_team_file_data(team_id: int, players: List[tuple]) -> Dict[str, Any]:
    """Create team file data structure"""
    team_name = get_team_display_name(team_id)

    # Convert players list back to dictionary format
    players_dict = {}
    for player_id, player_data in players:
        players_dict[player_id] = player_data

    return {
        "team_id": team_id,
        "team_name": team_name,
        "total_players": len(players),
        "players": players_dict
    }

def write_team_file(output_dir: str, team_id: int, team_data: Dict[str, Any], dry_run: bool = False) -> str:
    """Write team data to file"""
    team_name = get_team_name_by_id(team_id)
    filename = f"team_{team_id:02d}_{team_name}.json"
    filepath = os.path.join(output_dir, filename)

    if dry_run:
        print(f"[DRY RUN] Would write {team_data['total_players']} players to {filepath}")
        return filepath

    with open(filepath, 'w') as f:
        json.dump(team_data, f, indent=2)

    print(f"Created {filepath} with {team_data['total_players']} players")
    return filepath

def validate_migration(original_data: Dict[str, Any], teams_data: Dict[int, List[tuple]], test_teams: List[int] = None) -> bool:
    """Validate that migration preserves all data"""
    original_players = original_data.get('players', {})

    if test_teams:
        # For test teams, only validate the selected teams
        expected_players = {}
        for player_id, player_data in original_players.items():
            if player_data.get('team_id') in test_teams:
                expected_players[player_id] = player_data

        original_count = len(expected_players)
        original_ids = set(expected_players.keys())
        print(f"Validation (test teams {test_teams}): Expected players: {original_count}")
    else:
        # For full migration, validate all players
        original_count = len(original_players)
        original_ids = set(original_players.keys())
        print(f"Validation (full migration): Original players: {original_count}")

    migrated_count = sum(len(players) for players in teams_data.values())
    print(f"Migrated players: {migrated_count}")

    if original_count != migrated_count:
        print(f"ERROR: Player count mismatch! Expected: {original_count}, Migrated: {migrated_count}")
        return False

    # Check that all player IDs are preserved
    migrated_ids = set()
    for team_players in teams_data.values():
        for player_id, _ in team_players:
            migrated_ids.add(player_id)

    if original_ids != migrated_ids:
        missing_ids = original_ids - migrated_ids
        extra_ids = migrated_ids - original_ids
        if missing_ids:
            print(f"ERROR: Missing player IDs: {missing_ids}")
        if extra_ids:
            print(f"ERROR: Extra player IDs: {extra_ids}")
        return False

    print("✓ Validation passed: All expected players preserved")
    return True

def main():
    parser = argparse.ArgumentParser(description="Migrate players.json to team-based files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    parser.add_argument("--test-teams", help="Only migrate specific teams (comma-separated team IDs)")
    args = parser.parse_args()

    # File paths
    players_file = "src/data/players.json"
    output_dir = "src/data/players"

    print("Player Data Migration Script")
    print("=" * 40)
    print(f"Source file: {players_file}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Load original data
    print("Loading players data...")
    try:
        original_data = load_players_data(players_file)
    except Exception as e:
        print(f"Error loading players data: {e}")
        return 1

    # Group players by team
    print("Grouping players by team...")
    teams_data = group_players_by_team(original_data)

    print(f"Found {len(teams_data)} teams with players:")
    for team_id in sorted(teams_data.keys()):
        team_name = get_team_display_name(team_id)
        player_count = len(teams_data[team_id])
        print(f"  Team {team_id:2d}: {team_name:<25} ({player_count:2d} players)")
    print()

    # Filter teams if requested
    test_team_ids = None
    if args.test_teams:
        test_team_ids = [int(t.strip()) for t in args.test_teams.split(",")]
        teams_data = {tid: teams_data[tid] for tid in test_team_ids if tid in teams_data}
        print(f"Filtering to test teams: {test_team_ids}")
        print()

    # Validate before migration
    if not validate_migration(original_data, teams_data, test_team_ids):
        print("Validation failed, aborting migration")
        return 1

    # Create output directory
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Write team files
    print("Creating team files...")
    created_files = []

    for team_id in sorted(teams_data.keys()):
        players = teams_data[team_id]
        team_data = create_team_file_data(team_id, players)
        filepath = write_team_file(output_dir, team_id, team_data, args.dry_run)
        created_files.append(filepath)

    print()
    print(f"Migration complete! Created {len(created_files)} team files")

    if not args.dry_run:
        print("\nNext steps:")
        print("1. Test the new PlayerDataLoader with team-based files")
        print("2. Update any code that directly references players.json")
        print("3. Archive the original players.json file")
        print("4. Update documentation")

    return 0

if __name__ == "__main__":
    sys.exit(main())