#!/usr/bin/env python3
"""
Database Migration Runner for Phase 1: Season Type Schema

This script applies the season_type migration to existing databases.
It's safe to run multiple times (idempotent).

Usage:
    python scripts/run_migration.py <database_path>

Example:
    python scripts/run_migration.py data/database/nfl_simulation.db
    python scripts/run_migration.py demo/interactive_season_sim/data/season_2024.db
"""

import sys
import sqlite3
import os
from pathlib import Path


def check_migration_needed(db_path: str) -> bool:
    """
    Check if migration is needed for the database.

    Args:
        db_path: Path to the database file

    Returns:
        True if migration needed, False if already migrated
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if season_type column exists in games table
        cursor.execute("PRAGMA table_info(games)")
        games_columns = {row[1] for row in cursor.fetchall()}

        # Check if season_type column exists in player_game_stats table
        cursor.execute("PRAGMA table_info(player_game_stats)")
        stats_columns = {row[1] for row in cursor.fetchall()}

        needs_migration = 'season_type' not in games_columns or 'season_type' not in stats_columns

        return needs_migration

    finally:
        conn.close()


def run_migration(db_path: str) -> bool:
    """
    Run the season_type migration on the specified database.

    Args:
        db_path: Path to the database file

    Returns:
        True if successful, False otherwise
    """
    print(f"\nMigrating database: {db_path}")

    # Read migration SQL
    migration_sql_path = Path(__file__).parent / "migrate_season_type.sql"

    if not migration_sql_path.exists():
        print(f"✗ Error: Migration SQL file not found: {migration_sql_path}")
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

        print("✓ Migration completed successfully")
        return True

    except sqlite3.OperationalError as e:
        # Check if error is due to column already existing
        if "duplicate column name" in str(e).lower():
            print("✓ Migration already applied (columns exist)")
            return True
        else:
            print(f"✗ Migration failed: {e}")
            return False

    except Exception as e:
        print(f"✗ Migration failed: {e}")
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
    print("\nVerifying migration...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check games table
        cursor.execute("PRAGMA table_info(games)")
        games_columns = {row[1] for row in cursor.fetchall()}

        if 'season_type' not in games_columns:
            print("✗ Verification failed: season_type column missing from games table")
            return False

        if 'game_type' not in games_columns:
            print("✗ Verification failed: game_type column missing from games table")
            return False

        # Check player_game_stats table
        cursor.execute("PRAGMA table_info(player_game_stats)")
        stats_columns = {row[1] for row in cursor.fetchall()}

        if 'season_type' not in stats_columns:
            print("✗ Verification failed: season_type column missing from player_game_stats table")
            return False

        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        required_indexes = [
            'idx_games_season_type',
            'idx_games_type',
            'idx_stats_season_type',
            'idx_stats_player_type'
        ]

        missing_indexes = [idx for idx in required_indexes if idx not in indexes]
        if missing_indexes:
            print(f"✗ Verification failed: Missing indexes: {missing_indexes}")
            return False

        # Check data counts
        cursor.execute("SELECT season_type, COUNT(*) FROM games GROUP BY season_type")
        game_counts = cursor.fetchall()

        cursor.execute("SELECT season_type, COUNT(*) FROM player_game_stats GROUP BY season_type")
        stat_counts = cursor.fetchall()

        print("\n✓ Verification passed!")
        print("\nData summary:")
        print("  Games by season_type:")
        for season_type, count in game_counts:
            print(f"    - {season_type}: {count}")

        print("  Player stats by season_type:")
        for season_type, count in stat_counts:
            print(f"    - {season_type}: {count}")

        return True

    finally:
        conn.close()


def main():
    """Main entry point."""
    print("="*70)
    print("Phase 1 Database Migration: Season Type Schema")
    print("="*70)

    if len(sys.argv) < 2:
        print("\nUsage: python scripts/run_migration.py <database_path>")
        print("\nExamples:")
        print("  python scripts/run_migration.py data/database/nfl_simulation.db")
        print("  python scripts/run_migration.py demo/interactive_season_sim/data/season_2024.db")
        return 1

    db_path = sys.argv[1]

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"\n✗ Error: Database file not found: {db_path}")
        return 1

    # Create backup
    backup_path = db_path + ".backup"
    print(f"\nCreating backup: {backup_path}")

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print("✓ Backup created")
    except Exception as e:
        print(f"✗ Failed to create backup: {e}")
        return 1

    # Check if migration is needed
    if not check_migration_needed(db_path):
        print("\n✓ Database is already up to date (season_type columns exist)")
        print("No migration needed.")
        # Clean up backup
        os.remove(backup_path)
        return 0

    # Run migration
    if not run_migration(db_path):
        print("\n✗ Migration failed. Database restored from backup.")
        # Restore backup
        import shutil
        shutil.copy2(backup_path, db_path)
        return 1

    # Verify migration
    if not verify_migration(db_path):
        print("\n✗ Verification failed. Database restored from backup.")
        # Restore backup
        import shutil
        shutil.copy2(backup_path, db_path)
        return 1

    # Success - keep backup
    print(f"\n✓ Migration completed successfully!")
    print(f"  Backup saved at: {backup_path}")
    print(f"  Original database: {db_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
