#!/usr/bin/env python3
"""
Remove duplicate player_popularity records, keeping highest score.

This script identifies and removes duplicate records in the player_popularity table
where the same player has multiple entries for the same dynasty/season/week.
This violates the UNIQUE constraint and causes display issues.

Usage:
    python scripts/cleanup_duplicate_popularity.py
"""

import sqlite3
from pathlib import Path


def main():
    """Remove duplicate player_popularity records."""
    # Get database path
    db_path = Path("data/database/game_cycle/game_cycle.db")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Make sure you're running this script from the project root directory.")
        return 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("DUPLICATE PLAYER_POPULARITY CLEANUP")
    print("=" * 80)

    try:
        # Find all duplicates
        cursor.execute("""
            SELECT dynasty_id, player_id, season, week, COUNT(*) as count
            FROM player_popularity
            GROUP BY dynasty_id, player_id, season, week
            HAVING count > 1
        """)

        duplicates = cursor.fetchall()

        if not duplicates:
            print("\n✅ No duplicate records found!")
            print("The player_popularity table is clean.")
            return 0

        print(f"\n⚠️  Found {len(duplicates)} sets of duplicate records")
        print("\nDuplicates by (dynasty_id, player_id, season, week):")
        for dynasty_id, player_id, season, week, count in duplicates:
            print(f"  • Player {player_id}, Week {week}, Season {season}: {count} records")

        # Confirm deletion
        print("\n" + "=" * 80)
        response = input("\nProceed with cleanup? (keeps highest score, deletes others) [y/N]: ").strip().lower()

        if response not in ['y', 'yes']:
            print("Cleanup cancelled. No changes made.")
            return 0

        # For each duplicate, keep the one with highest popularity_score
        total_deleted = 0
        for dynasty_id, player_id, season, week, count in duplicates:
            # Get all records for this player/week
            cursor.execute("""
                SELECT id, popularity_score
                FROM player_popularity
                WHERE dynasty_id = ? AND player_id = ? AND season = ? AND week = ?
                ORDER BY popularity_score DESC
            """, (dynasty_id, player_id, season, week))

            records = cursor.fetchall()
            keep_id = records[0][0]  # Keep highest score
            keep_score = records[0][1]
            delete_ids = [r[0] for r in records[1:]]

            # Delete duplicates
            for del_id in delete_ids:
                cursor.execute("DELETE FROM player_popularity WHERE id = ?", (del_id,))
                total_deleted += 1

            print(f"  ✓ Player {player_id} week {week}: kept id={keep_id} (score={keep_score:.1f}), deleted {len(delete_ids)}")

        conn.commit()

        print("\n" + "=" * 80)
        print(f"✅ Cleanup complete! Deleted {total_deleted} duplicate records")
        print("=" * 80)

        # Verify no duplicates remain
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT dynasty_id, player_id, season, week, COUNT(*) as count
                FROM player_popularity
                GROUP BY dynasty_id, player_id, season, week
                HAVING count > 1
            )
        """)
        remaining = cursor.fetchone()[0]

        if remaining == 0:
            print("\n✅ Verification: No duplicates remaining")
        else:
            print(f"\n⚠️  Warning: {remaining} duplicate sets still exist")

        return 0

    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
