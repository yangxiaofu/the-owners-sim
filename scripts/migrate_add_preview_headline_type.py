#!/usr/bin/env python3
"""
Migration script to add 'PREVIEW' to headline_type CHECK constraint.

SQLite doesn't support modifying CHECK constraints, so we need to:
1. Create new table with updated constraint
2. Copy data from old table
3. Drop old table
4. Rename new table

Usage:
    python scripts/migrate_add_preview_headline_type.py
"""

import sqlite3
import os
import sys

# Default database path
DEFAULT_DB_PATH = "data/database/game_cycle/game_cycle.db"


def migrate_database(db_path: str) -> bool:
    """Run migration to add PREVIEW headline type."""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='media_headlines'
        """)
        if not cursor.fetchone():
            print("media_headlines table doesn't exist - nothing to migrate")
            return True

        # Create new table with updated CHECK constraint
        print("Creating new table with PREVIEW headline type...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_headlines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                headline_type TEXT NOT NULL CHECK(headline_type IN (
                    'GAME_RECAP', 'BLOWOUT', 'UPSET', 'COMEBACK', 'INJURY', 'MILESTONE',
                    'TRADE', 'SIGNING', 'AWARD', 'RUMOR', 'POWER_RANKING', 'DRAFT', 'PREVIEW'
                )),
                headline TEXT NOT NULL,
                subheadline TEXT,
                body_text TEXT,
                sentiment TEXT CHECK(sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL', 'HYPE', 'CRITICAL')),
                priority INTEGER DEFAULT 50 CHECK(priority BETWEEN 1 AND 100),
                team_ids TEXT,
                player_ids TEXT,
                game_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            )
        """)

        # Copy existing data
        print("Copying existing headlines...")
        cursor.execute("""
            INSERT INTO media_headlines_new
            SELECT * FROM media_headlines
        """)

        rows_copied = cursor.rowcount
        print(f"Copied {rows_copied} headlines")

        # Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE media_headlines")

        # Rename new table
        print("Renaming new table...")
        cursor.execute("ALTER TABLE media_headlines_new RENAME TO media_headlines")

        # Create index (if it existed before)
        print("Recreating indices...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_headlines_lookup
            ON media_headlines(dynasty_id, season, week)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_headlines_type
            ON media_headlines(dynasty_id, headline_type)
        """)

        conn.commit()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False
    finally:
        conn.close()


def main():
    # Get database path from args or use default
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DEFAULT_DB_PATH

    success = migrate_database(db_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
