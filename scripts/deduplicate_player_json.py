#!/usr/bin/env python3
"""
Deduplicate Player JSON Files

This script identifies and removes duplicate players from the source JSON files
in src/data/players/. Duplicates are identified by player name (first_name + last_name).

Deduplication Rules:
1. Within-team duplicates: Keep entry with lower player_id (original source)
2. Cross-team duplicates: Keep entry from team with lower team_id (requires manual review)
3. Team + Free Agent: Keep team entry, remove from free_agents.json
4. Same name different players: Verify by position - if same position, likely duplicate

Usage:
    python scripts/deduplicate_player_json.py --dry-run   # Preview changes
    python scripts/deduplicate_player_json.py --apply     # Apply changes
    python scripts/deduplicate_player_json.py --report    # Show detailed report only
"""

import json
import os
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PLAYERS_DIR = PROJECT_ROOT / "src" / "data" / "players"


def load_all_players() -> Tuple[Dict[str, Dict], Dict[str, List[Dict]]]:
    """
    Load all players from JSON files.

    Returns:
        Tuple of:
        - file_data: {filename: original_json_data}
        - players_by_name: {full_name: [player_entries]}
    """
    file_data = {}
    players_by_name = defaultdict(list)

    # Load team files
    for filepath in sorted(PLAYERS_DIR.glob("team_*.json")):
        team_id = int(filepath.stem.split("_")[1])

        with open(filepath, 'r') as f:
            data = json.load(f)

        file_data[filepath.name] = data

        for player_id, player in data.get("players", {}).items():
            full_name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
            players_by_name[full_name].append({
                'player_id': player_id,
                'player_id_int': int(player_id),
                'team_id': team_id,
                'file': filepath.name,
                'filepath': filepath,
                'positions': player.get('positions', []),
                'data': player,
            })

    # Load free agents
    fa_path = PLAYERS_DIR / "free_agents.json"
    if fa_path.exists():
        with open(fa_path, 'r') as f:
            data = json.load(f)

        file_data["free_agents.json"] = data

        for player_id, player in data.get("players", {}).items():
            full_name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
            players_by_name[full_name].append({
                'player_id': player_id,
                'player_id_int': int(player_id),
                'team_id': 0,  # Free agent
                'file': "free_agents.json",
                'filepath': fa_path,
                'positions': player.get('positions', []),
                'data': player,
            })

    return file_data, players_by_name


def find_duplicates(players_by_name: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """Find all duplicate player names."""
    return {
        name: entries
        for name, entries in players_by_name.items()
        if len(entries) > 1
    }


def positions_overlap(pos1: List[str], pos2: List[str]) -> bool:
    """Check if two position lists have any overlap (likely same player)."""
    # Normalize positions for comparison
    def normalize(pos):
        pos = pos.lower().replace("_", " ")
        # Map variations to standard names
        mappings = {
            "mike linebacker": "linebacker",
            "will linebacker": "linebacker",
            "sam linebacker": "linebacker",
            "middle linebacker": "linebacker",
            "outside linebacker": "linebacker",
            "inside linebacker": "linebacker",
            "free safety": "safety",
            "strong safety": "safety",
            "left tackle": "tackle",
            "right tackle": "tackle",
            "offensive tackle": "tackle",
            "left guard": "guard",
            "right guard": "guard",
            "offensive guard": "guard",
            "nose tackle": "defensive tackle",
            "defensive end": "edge",
        }
        return mappings.get(pos, pos)

    norm1 = {normalize(p) for p in pos1}
    norm2 = {normalize(p) for p in pos2}

    return bool(norm1 & norm2)


def determine_entry_to_keep(entries: List[Dict], name: str) -> Tuple[Dict, List[Dict], str]:
    """
    Determine which entry to keep and which to remove.

    Returns:
        Tuple of (entry_to_keep, entries_to_remove, reason)
    """
    # Sort entries by team_id (0 = free agent last), then by player_id
    sorted_entries = sorted(entries, key=lambda x: (x['team_id'] == 0, x['player_id_int']))

    # Check if all entries are on the same team
    team_ids = {e['team_id'] for e in entries}

    if len(team_ids) == 1:
        # All same team - keep lowest player_id
        keep = sorted_entries[0]
        remove = sorted_entries[1:]
        return keep, remove, "within-team duplicate (keeping lower player_id)"

    # Check if one is a free agent
    team_entries = [e for e in entries if e['team_id'] != 0]
    fa_entries = [e for e in entries if e['team_id'] == 0]

    if team_entries and fa_entries:
        # Keep team entry, remove free agent
        team_entries_sorted = sorted(team_entries, key=lambda x: x['player_id_int'])
        keep = team_entries_sorted[0]
        remove = fa_entries + team_entries_sorted[1:]
        return keep, remove, "team roster preferred over free agent"

    # Cross-team duplicates - check if positions overlap
    # If positions overlap significantly, they're likely the same player
    first = sorted_entries[0]
    all_overlap = all(
        positions_overlap(first['positions'], e['positions'])
        for e in sorted_entries[1:]
    )

    if all_overlap:
        # Same player on multiple teams - keep first (lowest team_id)
        keep = sorted_entries[0]
        remove = sorted_entries[1:]
        return keep, remove, f"cross-team duplicate (keeping team {keep['team_id']})"

    # Different positions - might be different players with same name
    # Flag for manual review but still dedupe if player_ids suggest merge
    if any(e['player_id_int'] >= 35000 for e in entries):
        # 35xxx IDs are from merged source - remove those
        original = [e for e in entries if e['player_id_int'] < 35000]
        merged = [e for e in entries if e['player_id_int'] >= 35000]
        if original:
            keep = sorted(original, key=lambda x: x['player_id_int'])[0]
            remove = merged + [e for e in original if e != keep]
            return keep, remove, "removing merged 35xxx entries"

    # Default: keep lowest player_id
    keep = sorted_entries[0]
    remove = sorted_entries[1:]
    return keep, remove, "default (keeping lowest player_id) - REVIEW RECOMMENDED"


def generate_report(duplicates: Dict[str, List[Dict]], decisions: Dict[str, Tuple]) -> str:
    """Generate a detailed report of duplicates and decisions."""
    lines = []
    lines.append("=" * 80)
    lines.append("PLAYER DEDUPLICATION REPORT")
    lines.append("=" * 80)
    lines.append(f"\nTotal duplicate names found: {len(duplicates)}")
    lines.append(f"Total entries to remove: {sum(len(d[1]) for d in decisions.values())}")
    lines.append("")

    # Group by reason
    by_reason = defaultdict(list)
    for name, (keep, remove, reason) in decisions.items():
        by_reason[reason].append((name, keep, remove))

    for reason, items in sorted(by_reason.items()):
        lines.append("-" * 80)
        lines.append(f"{reason.upper()} ({len(items)} cases)")
        lines.append("-" * 80)

        for name, keep, remove in sorted(items, key=lambda x: x[0]):
            lines.append(f"\n  {name}:")
            lines.append(f"    KEEP: player_id={keep['player_id']}, team={keep['team_id']}, file={keep['file']}")
            for r in remove:
                lines.append(f"    REMOVE: player_id={r['player_id']}, team={r['team_id']}, file={r['file']}")

    return "\n".join(lines)


def apply_deduplication(file_data: Dict, decisions: Dict[str, Tuple]) -> Dict[str, int]:
    """
    Apply deduplication decisions to file data.

    Returns:
        Dict of {filename: count_removed}
    """
    # Build set of (filename, player_id) to remove
    to_remove = set()
    for name, (keep, remove_list, reason) in decisions.items():
        for entry in remove_list:
            to_remove.add((entry['file'], entry['player_id']))

    # Track removals per file
    removals = defaultdict(int)

    for filename, data in file_data.items():
        players = data.get("players", {})
        players_to_delete = []

        for player_id in players:
            if (filename, player_id) in to_remove:
                players_to_delete.append(player_id)

        for player_id in players_to_delete:
            del players[player_id]
            removals[filename] += 1

        # Update total_players count
        if "total_players" in data:
            data["total_players"] = len(players)

    return dict(removals)


def save_files(file_data: Dict):
    """Save modified JSON files."""
    for filename, data in file_data.items():
        filepath = PLAYERS_DIR / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Saved: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate player JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply deduplication changes")
    parser.add_argument("--report", action="store_true", help="Show detailed report only")
    args = parser.parse_args()

    if not any([args.dry_run, args.apply, args.report]):
        parser.print_help()
        print("\nPlease specify --dry-run, --apply, or --report")
        return 1

    print("Loading player data...")
    file_data, players_by_name = load_all_players()

    total_players = sum(len(d.get("players", {})) for d in file_data.values())
    print(f"Loaded {total_players} players from {len(file_data)} files")

    print("\nFinding duplicates...")
    duplicates = find_duplicates(players_by_name)
    print(f"Found {len(duplicates)} duplicate names")

    if not duplicates:
        print("No duplicates found!")
        return 0

    print("\nAnalyzing duplicates...")
    decisions = {}
    for name, entries in duplicates.items():
        keep, remove, reason = determine_entry_to_keep(entries, name)
        decisions[name] = (keep, remove, reason)

    total_to_remove = sum(len(d[1]) for d in decisions.values())
    print(f"Entries to remove: {total_to_remove}")

    # Generate report
    report = generate_report(duplicates, decisions)

    if args.report or args.dry_run:
        print("\n" + report)

    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN - No changes made")
        print("=" * 80)
        print(f"\nWould remove {total_to_remove} duplicate entries")
        print(f"Final player count would be: {total_players - total_to_remove}")
        return 0

    if args.apply:
        print("\nApplying deduplication...")
        removals = apply_deduplication(file_data, decisions)

        print("\nRemovals by file:")
        for filename, count in sorted(removals.items()):
            if count > 0:
                print(f"  {filename}: {count} removed")

        print("\nSaving files...")
        save_files(file_data)

        print("\n" + "=" * 80)
        print("DEDUPLICATION COMPLETE")
        print("=" * 80)
        print(f"Removed {total_to_remove} duplicate entries")
        print(f"Final player count: {total_players - total_to_remove}")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
