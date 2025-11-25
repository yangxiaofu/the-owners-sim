"""
Migration Script: Add Prospect-to-Player Mapping Column

Adds roster_player_id column to the draft_prospects table to track which roster
player each draft prospect became after being drafted and converted.

Column Details:
- roster_player_id: INTEGER - Final player_id assigned when prospect converted to roster
- DEFAULT NULL: Indicates prospect not yet converted (still in draft pool or undrafted)
- Non-NULL: Points to players.player_id for converted prospects

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


def check_index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    """
    Check if an index exists.

    Args:
        cursor: SQLite cursor
        index_name: Index name

    Returns:
        True if index exists, False otherwise
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None


def migrate_database(db_path: str) -> bool:
    """
    Add roster_player_id column and indexes to draft_prospects table.

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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='draft_prospects'")
        if not cursor.fetchone():
            print("ERROR: draft_prospects table does not exist!")
            print("Please run the draft tables migration first (add_draft_tables.sql)")
            return False

        # Check and add roster_player_id column
        if check_column_exists(cursor, 'draft_prospects', 'roster_player_id'):
            print("✓ Column 'roster_player_id' already exists - skipping")
        else:
            print("Adding column 'roster_player_id'...")
            cursor.execute("""
                ALTER TABLE draft_prospects
                ADD COLUMN roster_player_id INTEGER DEFAULT NULL
            """)
            print("✓ Column 'roster_player_id' added successfully")

        # Create index for roster_player_id lookups
        if check_index_exists(cursor, 'idx_prospects_roster_player'):
            print("✓ Index 'idx_prospects_roster_player' already exists - skipping")
        else:
            print("Creating index 'idx_prospects_roster_player'...")
            cursor.execute("""
                CREATE INDEX idx_prospects_roster_player
                ON draft_prospects(roster_player_id)
            """)
            print("✓ Index 'idx_prospects_roster_player' created successfully")

        # Create composite index for dynasty-aware reverse lookups
        if check_index_exists(cursor, 'idx_prospects_mapping'):
            print("✓ Index 'idx_prospects_mapping' already exists - skipping")
        else:
            print("Creating index 'idx_prospects_mapping'...")
            cursor.execute("""
                CREATE INDEX idx_prospects_mapping
                ON draft_prospects(dynasty_id, roster_player_id)
                WHERE roster_player_id IS NOT NULL
            """)
            print("✓ Index 'idx_prospects_mapping' created successfully")

        # Commit changes
        connection.commit()
        print("\n✅ Migration completed successfully!")

        # Verify migration
        print("\nVerifying migration...")
        cursor.execute("PRAGMA table_info(draft_prospects)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        verification_passed = True

        # Check column
        if 'roster_player_id' in columns:
            print(f"✓ roster_player_id: {columns['roster_player_id']}")
        else:
            print("✗ roster_player_id column missing!")
            verification_passed = False

        # Check indexes
        required_indexes = ['idx_prospects_roster_player', 'idx_prospects_mapping']
        for idx in required_indexes:
            if idx in indexes:
                print(f"✓ {idx}: exists")
            else:
                print(f"✗ {idx}: missing!")
                verification_passed = False

        if verification_passed:
            print("\n✅ Schema verification passed!")
            return True
        else:
            print("\n❌ Schema verification failed!")
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

    print("=" * 70)
    print("MIGRATION: Add Prospect-to-Player Mapping Column")
    print("=" * 70)
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
