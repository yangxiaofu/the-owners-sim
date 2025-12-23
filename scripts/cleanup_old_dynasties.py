#!/usr/bin/env python3
"""
Cleanup old test dynasty data from game_cycle.db.

This script identifies all dynasties in the database and allows
you to delete data from old/unused dynasties.

Usage:
    PYTHONPATH=src python scripts/cleanup_old_dynasties.py
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Tables to clean up
TABLES_TO_CLEAN = [
    'player_popularity',
    'player_popularity_events',
    'player_season_grades',
]


def get_db_path() -> Path:
    """Get the path to the game_cycle database."""
    # Assuming script is run from project root
    db_path = Path("data/database/game_cycle/game_cycle.db")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Make sure you're running this script from the project root directory.")
        sys.exit(1)

    return db_path


def get_dynasties_summary(conn: sqlite3.Connection) -> Dict[str, Dict[str, int]]:
    """
    Query each table for dynasty_ids and record counts.

    Returns:
        Dict mapping dynasty_id to table name to count
        Example: {"test123": {"player_popularity": 50, "player_season_grades": 1157}}
    """
    cursor = conn.cursor()
    summary = {}

    for table in TABLES_TO_CLEAN:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if not cursor.fetchone():
            print(f"Warning: Table '{table}' does not exist, skipping...")
            continue

        # Get counts per dynasty
        cursor.execute(
            f"SELECT dynasty_id, COUNT(*) FROM {table} GROUP BY dynasty_id"
        )

        for dynasty_id, count in cursor.fetchall():
            if dynasty_id not in summary:
                summary[dynasty_id] = {}
            summary[dynasty_id][table] = count

    return summary


def display_dynasties(summary: Dict[str, Dict[str, int]]) -> List[str]:
    """
    Display formatted table of all dynasties found.

    Returns:
        List of dynasty_ids in display order
    """
    if not summary:
        print("\nNo dynasty data found in database.")
        return []

    print("\n" + "="*80)
    print("DYNASTIES FOUND IN DATABASE")
    print("="*80)

    dynasty_ids = sorted(summary.keys())

    for idx, dynasty_id in enumerate(dynasty_ids, start=1):
        total_records = sum(summary[dynasty_id].values())
        print(f"\n{idx}. {dynasty_id} (Total: {total_records:,} records)")

        for table, count in sorted(summary[dynasty_id].items()):
            print(f"   - {table}: {count:,} records")

    print("\n" + "="*80)

    return dynasty_ids


def prompt_dynasty_selection(dynasty_ids: List[str]) -> str:
    """
    Prompt user to select which dynasty to keep.

    Returns:
        Selected dynasty_id
    """
    while True:
        try:
            choice = input(f"\nWhich dynasty do you want to KEEP? (1-{len(dynasty_ids)}, or 'q' to quit): ").strip()

            if choice.lower() == 'q':
                print("Exiting without making changes.")
                sys.exit(0)

            idx = int(choice) - 1
            if 0 <= idx < len(dynasty_ids):
                return dynasty_ids[idx]
            else:
                print(f"Please enter a number between 1 and {len(dynasty_ids)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")


def confirm_deletion(
    keep_dynasty: str,
    delete_dynasties: List[str],
    summary: Dict[str, Dict[str, int]]
) -> bool:
    """
    Show what will be deleted and ask for confirmation.

    Returns:
        True if user confirms, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"DELETION PLAN")
    print(f"{'='*80}")
    print(f"\nKeeping dynasty: {keep_dynasty}")
    print(f"\nDeleting dynasties:")

    total_to_delete = 0
    for dynasty_id in delete_dynasties:
        dynasty_total = sum(summary[dynasty_id].values())
        total_to_delete += dynasty_total
        print(f"\n  {dynasty_id} ({dynasty_total:,} total records)")

        for table, count in sorted(summary[dynasty_id].items()):
            print(f"    - {table}: {count:,} records")

    print(f"\n{'='*80}")
    print(f"Total records to delete: {total_to_delete:,}")
    print(f"{'='*80}")

    while True:
        response = input("\nProceed with deletion? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def delete_dynasty_data(
    conn: sqlite3.Connection,
    delete_dynasties: List[str],
    summary: Dict[str, Dict[str, int]]
) -> Dict[str, int]:
    """
    Execute DELETE queries for non-selected dynasties.

    Returns:
        Dict mapping table name to count of deleted records
    """
    cursor = conn.cursor()
    deletion_summary = {}

    for table in TABLES_TO_CLEAN:
        total_deleted = 0

        for dynasty_id in delete_dynasties:
            if table in summary.get(dynasty_id, {}):
                print(f"Deleting {summary[dynasty_id][table]:,} records from {table} (dynasty: {dynasty_id})...")

                cursor.execute(
                    f"DELETE FROM {table} WHERE dynasty_id = ?",
                    (dynasty_id,)
                )

                deleted = cursor.rowcount
                total_deleted += deleted

        if total_deleted > 0:
            deletion_summary[table] = total_deleted

    # Commit all deletions
    conn.commit()

    return deletion_summary


def show_deletion_summary(deletion_summary: Dict[str, int]):
    """Display summary of deleted records."""
    print(f"\n{'='*80}")
    print("DELETION COMPLETE")
    print(f"{'='*80}")

    total_deleted = sum(deletion_summary.values())

    for table, count in sorted(deletion_summary.items()):
        print(f"✓ Deleted {count:,} records from {table}")

    print(f"\nTotal records deleted: {total_deleted:,}")
    print(f"{'='*80}")
    print("\nCleanup successful! You can now recalculate popularity with a clean dynasty.")


def main():
    """Main execution flow."""
    print("\n" + "="*80)
    print("DYNASTY CLEANUP UTILITY")
    print("="*80)

    # Get database path
    db_path = get_db_path()
    print(f"\nConnecting to: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Get summary of all dynasties
        print("\nScanning database for dynasties...")
        summary = get_dynasties_summary(conn)

        if not summary:
            print("\nNo dynasty data found. Nothing to clean up.")
            return 0

        # Display dynasties
        dynasty_ids = display_dynasties(summary)

        if len(dynasty_ids) == 1:
            print(f"\nOnly one dynasty found ({dynasty_ids[0]}). Nothing to clean up.")
            return 0

        # Prompt for selection
        keep_dynasty = prompt_dynasty_selection(dynasty_ids)
        delete_dynasties = [d for d in dynasty_ids if d != keep_dynasty]

        # Confirm deletion
        if not confirm_deletion(keep_dynasty, delete_dynasties, summary):
            print("\nDeletion cancelled. No changes made.")
            return 0

        # Execute deletion
        print("\nDeleting data...")
        deletion_summary = delete_dynasty_data(conn, delete_dynasties, summary)

        # Show results
        show_deletion_summary(deletion_summary)

        return 0

    except Exception as e:
        print(f"\nError during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
