"""
Migration Script: Add Draft Progress Columns to dynasty_state Table

Adds two columns to the dynasty_state table to support draft save/resume functionality:
- current_draft_pick: INTEGER - Tracks the current pick number (0-262)
- draft_in_progress: INTEGER - Boolean flag (0/1) indicating if draft is active

This migration is idempotent and can be run multiple times safely.
"""

import sqlite3
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def check_column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """
    Check if a column exists in a table.

    Args:
        cursor: SQLite cursor
        table: Table name
        column: Column name

    Returns:
        True if column exists, False otherwise
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate_database(db_path: str) -> bool:
    """
    Add draft progress columns to dynasty_state table.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    connection = None

    try:
        # Connect to database
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        print(f"Connected to database: {db_path}")
        print("Checking current schema...")

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dynasty_state'")
        if not cursor.fetchone():
            print("ERROR: dynasty_state table does not exist!")
            return False

        # Check and add current_draft_pick column
        if check_column_exists(cursor, 'dynasty_state', 'current_draft_pick'):
            print("✓ Column 'current_draft_pick' already exists - skipping")
        else:
            print("Adding column 'current_draft_pick'...")
            cursor.execute("""
                ALTER TABLE dynasty_state
                ADD COLUMN current_draft_pick INTEGER DEFAULT 0
            """)
            print("✓ Column 'current_draft_pick' added successfully")

        # Check and add draft_in_progress column
        if check_column_exists(cursor, 'dynasty_state', 'draft_in_progress'):
            print("✓ Column 'draft_in_progress' already exists - skipping")
        else:
            print("Adding column 'draft_in_progress'...")
            cursor.execute("""
                ALTER TABLE dynasty_state
                ADD COLUMN draft_in_progress INTEGER DEFAULT 0
            """)
            print("✓ Column 'draft_in_progress' added successfully")

        # Commit changes
        connection.commit()
        print("\n✅ Migration completed successfully!")

        # Verify migration
        print("\nVerifying migration...")
        cursor.execute("PRAGMA table_info(dynasty_state)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if 'current_draft_pick' in columns and 'draft_in_progress' in columns:
            print(f"✓ current_draft_pick: {columns['current_draft_pick']}")
            print(f"✓ draft_in_progress: {columns['draft_in_progress']}")
            print("\n✅ Schema verification passed!")
            return True
        else:
            print("❌ Schema verification failed!")
            return False

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        if connection:
            connection.rollback()
            print("Changes rolled back")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if connection:
            connection.rollback()
            print("Changes rolled back")
        return False

    finally:
        if connection:
            connection.close()
            print("\nDatabase connection closed")


def main():
    """Main migration entry point."""
    # Default database path
    db_path = "data/database/nfl_simulation.db"

    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    print("=" * 60)
    print("MIGRATION: Add Draft Progress Columns to dynasty_state")
    print("=" * 60)
    print(f"Database: {db_path}\n")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database file not found: {db_path}")
        print("\nUsage:")
        print(f"  python {os.path.basename(__file__)} [database_path]")
        print(f"\nExample:")
        print(f"  python {os.path.basename(__file__)} data/database/nfl_simulation.db")
        return False

    # Run migration
    success = migrate_database(db_path)

    print("\n" + "=" * 60)
    if success:
        print("MIGRATION STATUS: ✅ SUCCESS")
    else:
        print("MIGRATION STATUS: ❌ FAILED")
    print("=" * 60)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
