#!/usr/bin/env python3
"""
Database Migration Runner: Add season_type to standings table

This script applies migration 003 which adds season_type support to the standings table,
enabling separate tracking of regular season and playoff records.

Usage:
    python scripts/run_standings_migration.py <database_path>
    python scripts/run_standings_migration.py data/database/*.db  # Apply to all

Example:
    python scripts/run_standings_migration.py data/database/interactive_demo.db
"""

import sys
import sqlite3
import os
from pathlib import Path
import glob


def check_migration_needed(db_path: str) -> bool:
    """
    Check if migration is needed for the database.

    Args:
        db_path: Path to the database file

    Returns:
        True if migration needed, False if already migrated
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if standings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='standings'")
        if not cursor.fetchone():
            print(f"  ⚠️  Standings table not found - database might be empty")
            conn.close()
            return False

        # Check if season_type column exists in standings table
        cursor.execute("PRAGMA table_info(standings)")
        standings_columns = {row[1] for row in cursor.fetchall()}

        needs_migration = 'season_type' not in standings_columns
        conn.close()

        return needs_migration

    except Exception as e:
        print(f"  ❌ Error checking database: {e}")
        return False


def run_migration(db_path: str) -> bool:
    """
    Run the standings season_type migration on the specified database.

    Args:
        db_path: Path to the database file

    Returns:
        True if successful, False otherwise
    """
    # Read migration SQL
    migration_sql_path = Path(__file__).parent.parent / "src" / "database" / "migrations" / "003_add_season_type_to_standings.sql"

    if not migration_sql_path.exists():
        print(f"  ❌ Migration SQL file not found: {migration_sql_path}")
        return False

    with open(migration_sql_path, 'r') as f:
        migration_sql = f.read()

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")

        # Execute migration (it's wrapped in a transaction in the SQL file)
        conn.executescript(migration_sql)

        print("  ✅ Migration completed successfully")
        return True

    except sqlite3.OperationalError as e:
        # Check if error is due to column already existing
        if "duplicate column name" in str(e).lower():
            print("  ✅ Migration already applied (season_type column exists)")
            return True
        else:
            print(f"  ❌ Migration failed: {e}")
            return False

    except Exception as e:
        print(f"  ❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()


def verify_migration(db_path: str) -> bool:
    """
    Verify that the migration was successful.

    Args:
        db_path: Path to the database file

    Returns:
        True if verification passed, False otherwise
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check standings table
        cursor.execute("PRAGMA table_info(standings)")
        standings_columns = {row[1] for row in cursor.fetchall()}

        if 'season_type' not in standings_columns:
            print("  ❌ Verification failed: season_type column missing from standings table")
            return False

        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        required_indexes = [
            'idx_standings_unique',
            'idx_standings_season_type',
            'idx_standings_team_season_type'
        ]

        missing_indexes = [idx for idx in required_indexes if idx not in indexes]
        if missing_indexes:
            print(f"  ⚠️  Warning: Missing indexes: {missing_indexes} (non-critical)")

        # Check data counts
        cursor.execute("SELECT season_type, COUNT(*) FROM standings GROUP BY season_type")
        standing_counts = cursor.fetchall()

        print("  ✅ Verification passed!")
        if standing_counts:
            print("  📊 Standings by season_type:")
            for season_type, count in standing_counts:
                print(f"      - {season_type}: {count} records")
        else:
            print("  📊 No standings records yet (empty database)")

        return True

    except Exception as e:
        print(f"  ❌ Verification error: {e}")
        return False

    finally:
        conn.close()


def migrate_database(db_path: str) -> bool:
    """
    Migrate a single database file.

    Args:
        db_path: Path to database file

    Returns:
        True if successful
    """
    print(f"\n📄 Processing: {db_path}")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"  ❌ Database file not found")
        return False

    # Create backup
    backup_path = db_path + ".backup_standings"
    print(f"  💾 Creating backup...")

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"  ✅ Backup created: {backup_path}")
    except Exception as e:
        print(f"  ❌ Failed to create backup: {e}")
        return False

    # Check if migration is needed
    if not check_migration_needed(db_path):
        print("  ✅ Database is already up to date (season_type column exists)")
        # Clean up backup
        os.remove(backup_path)
        return True

    # Run migration
    if not run_migration(db_path):
        print("  ❌ Migration failed. Restoring from backup...")
        # Restore backup
        import shutil
        shutil.copy2(backup_path, db_path)
        print("  ✅ Database restored from backup")
        return False

    # Verify migration
    if not verify_migration(db_path):
        print("  ❌ Verification failed. Restoring from backup...")
        # Restore backup
        import shutil
        shutil.copy2(backup_path, db_path)
        print("  ✅ Database restored from backup")
        return False

    # Success - remove backup
    os.remove(backup_path)
    print(f"  ✅ Migration completed successfully!")

    return True


def main():
    """Main entry point."""
    print("="*80)
    print("Database Migration: Add season_type to standings table".center(80))
    print("="*80)

    if len(sys.argv) < 2:
        print("\n❌ No database files specified!")
        print("\nUsage:")
        print("  python scripts/run_standings_migration.py <database_path>")
        print("  python scripts/run_standings_migration.py data/database/*.db")
        print("\nExamples:")
        print("  python scripts/run_standings_migration.py data/database/interactive_demo.db")
        print("  python scripts/run_standings_migration.py data/database/*.db")
        return 1

    # Handle glob patterns
    db_paths = []
    for arg in sys.argv[1:]:
        if '*' in arg:
            # Expand glob pattern
            expanded = glob.glob(arg)
            db_paths.extend(expanded)
        else:
            db_paths.append(arg)

    # Filter for .db files
    db_paths = [p for p in db_paths if p.endswith('.db')]

    if not db_paths:
        print("\n❌ No valid database files found!")
        return 1

    print(f"\n📋 Found {len(db_paths)} database file(s) to process")

    # Migrate each database
    success_count = 0
    skip_count = 0
    fail_count = 0

    for db_path in db_paths:
        result = migrate_database(db_path)
        if result:
            # Check if it was already migrated
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(standings)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()

            if 'season_type' in columns:
                success_count += 1
            else:
                skip_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"\n{'='*80}")
    print("MIGRATION SUMMARY".center(80))
    print(f"{'='*80}")
    print(f"  ✅ Successfully migrated: {success_count}")
    print(f"  ⏭️  Already up-to-date: {skip_count}")
    print(f"  ❌ Failed: {fail_count}")
    print(f"{'='*80}\n")

    if fail_count > 0:
        print("⚠️  Some migrations failed. Check the output above for details.")
        return 1

    print("✅ All databases migrated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
