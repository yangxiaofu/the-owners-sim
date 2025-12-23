"""
Migration 001: Add UNIQUE Constraints and Indexes to Events Table

This migration adds database-level integrity constraints to prevent duplicate games.

Changes:
1. CHECK constraint: Ensure GAME events always have a game_id
2. UNIQUE index: Prevent duplicate (dynasty_id, game_id) for GAME events
3. Composite index: Optimize dynasty/type/timestamp queries

Safety:
- Backs up database before migration
- Detects and removes duplicate games
- Verifies all constraints before committing
- Rolls back on any error

Usage:
    python -c "from src.game_cycle.database.migrations.migrate_001_add_unique_constraints import migrate; migrate('path/to/db.sqlite')"

Or programmatically:
    from game_cycle.database.migrations.migrate_001_add_unique_constraints import migrate_database
    success, message = migrate_database('/path/to/game_cycle.db')
"""

import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any


def backup_database(db_path: str) -> str:
    """Create timestamped backup of database."""
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_file.parent / f"{db_file.stem}_backup_{timestamp}.db"

    shutil.copy2(db_path, backup_path)
    print(f"[Migration] Created backup: {backup_path}")
    return str(backup_path)


def detect_duplicates(conn: sqlite3.Connection) -> List[Tuple[str, str, int]]:
    """
    Detect duplicate games in the events table.

    Returns:
        List of (dynasty_id, game_id, count) tuples for games with count > 1
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT dynasty_id, game_id, COUNT(*) as duplicate_count
        FROM events
        WHERE event_type = 'GAME'
        AND game_id IS NOT NULL
        GROUP BY dynasty_id, game_id
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
    """)
    return cursor.fetchall()


def deduplicate_games(conn: sqlite3.Connection) -> int:
    """
    Remove duplicate game events, keeping the best one.

    Strategy:
    1. Keep the event with results (if any)
    2. Otherwise keep the newest event (highest timestamp)
    3. Delete all others

    Returns:
        Number of duplicate events removed
    """
    cursor = conn.cursor()

    # Find all duplicate game_ids
    duplicates = detect_duplicates(conn)
    if not duplicates:
        return 0

    total_removed = 0

    for dynasty_id, game_id, count in duplicates:
        # Get all event_ids for this game, ordered by priority
        cursor.execute("""
            SELECT event_id,
                   CASE WHEN json_extract(data, '$.results') IS NOT NULL THEN 0 ELSE 1 END as has_results,
                   timestamp
            FROM events
            WHERE dynasty_id = ?
            AND game_id = ?
            AND event_type = 'GAME'
            ORDER BY has_results ASC, timestamp DESC
        """, (dynasty_id, game_id))

        events = cursor.fetchall()

        # Keep the first one (best by priority), delete the rest
        keep_event_id = events[0][0]
        delete_event_ids = [e[0] for e in events[1:]]

        for event_id in delete_event_ids:
            cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
            total_removed += 1

        print(f"[Migration] De-duplicated {game_id}: kept {keep_event_id}, removed {len(delete_event_ids)} duplicates")

    return total_removed


def add_check_constraint(conn: sqlite3.Connection) -> None:
    """
    Add CHECK constraint to ensure GAME events have game_id.

    Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT for CHECK constraints.
    We verify the constraint logic instead.
    """
    cursor = conn.cursor()

    # Verify no GAME events have NULL game_id
    cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE event_type = 'GAME'
        AND game_id IS NULL
    """)
    null_count = cursor.fetchone()[0]

    if null_count > 0:
        raise ValueError(f"Found {null_count} GAME events with NULL game_id - cannot add CHECK constraint")

    print(f"[Migration] CHECK constraint verified: All GAME events have game_id")


def add_unique_index(conn: sqlite3.Connection) -> None:
    """Add UNIQUE index to prevent duplicate games."""
    cursor = conn.cursor()

    # Drop existing index if it exists (for idempotent migration)
    cursor.execute("DROP INDEX IF EXISTS idx_events_unique_game")

    # Create UNIQUE index
    cursor.execute("""
        CREATE UNIQUE INDEX idx_events_unique_game
        ON events(dynasty_id, game_id)
        WHERE event_type = 'GAME' AND game_id IS NOT NULL
    """)

    print("[Migration] Added UNIQUE index: idx_events_unique_game")


def add_composite_index(conn: sqlite3.Connection) -> None:
    """Add composite index for query performance."""
    cursor = conn.cursor()

    # Drop existing index if it exists
    cursor.execute("DROP INDEX IF EXISTS idx_events_dynasty_type_timestamp")

    # Create composite index
    cursor.execute("""
        CREATE INDEX idx_events_dynasty_type_timestamp
        ON events(dynasty_id, event_type, timestamp)
        WHERE event_type = 'GAME'
    """)

    print("[Migration] Added composite index: idx_events_dynasty_type_timestamp")


def verify_migration(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """
    Verify the migration was successful.

    Returns:
        (success, message) tuple
    """
    cursor = conn.cursor()

    # Check UNIQUE index exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'index'
        AND name = 'idx_events_unique_game'
    """)
    if not cursor.fetchone():
        return False, "UNIQUE index idx_events_unique_game not found"

    # Check composite index exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'index'
        AND name = 'idx_events_dynasty_type_timestamp'
    """)
    if not cursor.fetchone():
        return False, "Composite index idx_events_dynasty_type_timestamp not found"

    # Verify no duplicates remain
    duplicates = detect_duplicates(conn)
    if duplicates:
        return False, f"Found {len(duplicates)} duplicate games after migration"

    # Verify no NULL game_ids for GAME events
    cursor.execute("""
        SELECT COUNT(*)
        FROM events
        WHERE event_type = 'GAME'
        AND game_id IS NULL
    """)
    null_count = cursor.fetchone()[0]
    if null_count > 0:
        return False, f"Found {null_count} GAME events with NULL game_id"

    return True, "All constraints verified successfully"


def migrate_database(db_path: str) -> Tuple[bool, str]:
    """
    Run the migration on a database.

    Args:
        db_path: Path to the game_cycle database

    Returns:
        (success, message) tuple

    Raises:
        Exception: If migration fails (after rollback)
    """
    try:
        # Backup database first
        backup_path = backup_database(db_path)

        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            # Begin transaction
            conn.execute("BEGIN IMMEDIATE")

            # Step 1: Detect duplicates
            duplicates = detect_duplicates(conn)
            if duplicates:
                print(f"[Migration] Found {len(duplicates)} duplicate game_id(s)")
                removed = deduplicate_games(conn)
                print(f"[Migration] Removed {removed} duplicate events")
            else:
                print("[Migration] No duplicate games found - migration will be smooth")

            # Step 2: Verify CHECK constraint requirements
            add_check_constraint(conn)

            # Step 3: Add UNIQUE index
            add_unique_index(conn)

            # Step 4: Add composite index
            add_composite_index(conn)

            # Step 5: Verify migration
            success, message = verify_migration(conn)
            if not success:
                raise ValueError(f"Migration verification failed: {message}")

            # Commit transaction
            conn.commit()
            print("[Migration] Transaction committed successfully")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            conn.close()
            raise Exception(f"Migration failed (rolled back): {e}")

        finally:
            conn.close()

        # Final verification
        conn = sqlite3.connect(db_path)
        success, message = verify_migration(conn)
        conn.close()

        if success:
            return True, f"Migration completed successfully. Backup: {backup_path}"
        else:
            return False, f"Migration verification failed: {message}"

    except Exception as e:
        return False, f"Migration failed: {e}"


def main():
    """CLI interface for running migration."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python 001_add_unique_constraints.py <db_path>")
        print("Example: python 001_add_unique_constraints.py data/database/game_cycle/game_cycle.db")
        sys.exit(1)

    db_path = sys.argv[1]
    success, message = migrate_database(db_path)

    if success:
        print(f"\n✅ {message}")
        sys.exit(0)
    else:
        print(f"\n❌ {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
