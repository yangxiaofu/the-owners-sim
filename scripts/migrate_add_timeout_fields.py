#!/usr/bin/env python3
"""
Migration: Add timeout tracking fields to box_scores table.

Adds:
- team_timeouts_remaining: Timeouts left at end of game (0-3)
- team_timeouts_used_h1: Timeouts used in first half (0-3)
- team_timeouts_used_h2: Timeouts used in second half (0-3)
"""

import sqlite3
import sys
import os


def check_column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate_database(db_path: str) -> bool:
    """Add timeout fields to box_scores table."""
    connection = None

    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        print(f"Connected to database: {db_path}")
        print("Adding timeout fields to box_scores table...")

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='box_scores'"
        )
        if not cursor.fetchone():
            print("ERROR: box_scores table does not exist!")
            return False

        # Add team_timeouts_remaining
        if not check_column_exists(cursor, 'box_scores', 'team_timeouts_remaining'):
            print("Adding column 'team_timeouts_remaining'...")
            cursor.execute("""
                ALTER TABLE box_scores
                ADD COLUMN team_timeouts_remaining INTEGER DEFAULT 3
            """)
            print("✓ Column 'team_timeouts_remaining' added")
        else:
            print("• Column 'team_timeouts_remaining' already exists")

        # Add team_timeouts_used_h1
        if not check_column_exists(cursor, 'box_scores', 'team_timeouts_used_h1'):
            print("Adding column 'team_timeouts_used_h1'...")
            cursor.execute("""
                ALTER TABLE box_scores
                ADD COLUMN team_timeouts_used_h1 INTEGER DEFAULT 0
            """)
            print("✓ Column 'team_timeouts_used_h1' added")
        else:
            print("• Column 'team_timeouts_used_h1' already exists")

        # Add team_timeouts_used_h2
        if not check_column_exists(cursor, 'box_scores', 'team_timeouts_used_h2'):
            print("Adding column 'team_timeouts_used_h2'...")
            cursor.execute("""
                ALTER TABLE box_scores
                ADD COLUMN team_timeouts_used_h2 INTEGER DEFAULT 0
            """)
            print("✓ Column 'team_timeouts_used_h2' added")
        else:
            print("• Column 'team_timeouts_used_h2' already exists")

        connection.commit()
        print("\n✅ Migration completed successfully!")
        return True

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()


def main():
    """Main migration entry point."""
    db_path = "data/database/game_cycle/game_cycle.db"

    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    print("=" * 70)
    print("MIGRATION: Add Timeout Fields to box_scores")
    print("=" * 70)
    print(f"Database: {db_path}\n")

    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database file not found: {db_path}")
        return False

    success = migrate_database(db_path)

    print("\n" + "=" * 70)
    if success:
        print("MIGRATION STATUS: ✅ SUCCESS")
    else:
        print("MIGRATION STATUS: ❌ FAILED")
    print("=" * 70)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)