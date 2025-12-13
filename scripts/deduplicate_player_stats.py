#!/usr/bin/env python3
"""
Deduplicate Player Stats Script

Removes duplicate player_game_stats rows from the database,
keeping only the most recent entry (highest ID) for each player/game combination.

Usage:
    python scripts/deduplicate_player_stats.py [db_path]

If no path is provided, uses the default game cycle database.
"""

import sqlite3
import sys
from pathlib import Path


def deduplicate_player_stats(db_path: str):
    """Remove duplicate player_game_stats rows, keeping most recent."""

    print(f"\n🔍 Opening database: {db_path}")

    if not Path(db_path).exists():
        print(f"❌ Error: Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count total rows before
        cursor.execute("SELECT COUNT(*) FROM player_game_stats")
        total_before = cursor.fetchone()[0]
        print(f"📊 Total rows before deduplication: {total_before:,}")

        # Count duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM player_game_stats
            WHERE id NOT IN (
                SELECT MAX(id) FROM player_game_stats
                GROUP BY dynasty_id, game_id, player_id, season_type
            )
        """)
        duplicate_count = cursor.fetchone()[0]

        if duplicate_count == 0:
            print("✅ No duplicates found! Database is clean.")
            conn.close()
            return True

        print(f"⚠️  Found {duplicate_count:,} duplicate rows to remove")

        # Show some examples of duplicates
        print("\n📋 Sample duplicates:")
        cursor.execute("""
            SELECT player_id, player_name, game_id, COUNT(*) as cnt
            FROM player_game_stats
            GROUP BY player_id, game_id
            HAVING cnt > 1
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"   - {row[1]} (ID: {row[0]}), Game: {row[2]}, Count: {row[3]}")

        # Confirm before deletion
        response = input(f"\n❓ Delete {duplicate_count:,} duplicate rows? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Deduplication cancelled by user")
            conn.close()
            return False

        # Delete duplicates, keeping row with MAX(id)
        print("\n🗑️  Deleting duplicates...")
        cursor.execute("""
            DELETE FROM player_game_stats
            WHERE id NOT IN (
                SELECT MAX(id) FROM player_game_stats
                GROUP BY dynasty_id, game_id, player_id, season_type
            )
        """)

        deleted_count = cursor.rowcount
        conn.commit()

        # Count total rows after
        cursor.execute("SELECT COUNT(*) FROM player_game_stats")
        total_after = cursor.fetchone()[0]

        # Verify no more duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM player_game_stats
            WHERE id NOT IN (
                SELECT MAX(id) FROM player_game_stats
                GROUP BY dynasty_id, game_id, player_id, season_type
            )
        """)
        remaining_duplicates = cursor.fetchone()[0]

        print(f"\n✅ Deduplication complete!")
        print(f"   Rows before:  {total_before:,}")
        print(f"   Rows deleted: {deleted_count:,}")
        print(f"   Rows after:   {total_after:,}")
        print(f"   Remaining duplicates: {remaining_duplicates}")

        if remaining_duplicates == 0:
            print("\n🎉 Success! All duplicates removed.")
        else:
            print(f"\n⚠️  Warning: {remaining_duplicates} duplicates still remain")

        conn.close()
        return remaining_duplicates == 0

    except Exception as e:
        print(f"\n❌ Error during deduplication: {e}")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    # Default database path
    default_db_path = "data/database/game_cycle/game_cycle.db"

    # Allow custom path from command line
    db_path = sys.argv[1] if len(sys.argv) > 1 else default_db_path

    print("=" * 60)
    print("     PLAYER STATS DEDUPLICATION SCRIPT")
    print("=" * 60)

    success = deduplicate_player_stats(db_path)

    if success:
        print("\n✅ Script completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Script completed with errors")
        sys.exit(1)
