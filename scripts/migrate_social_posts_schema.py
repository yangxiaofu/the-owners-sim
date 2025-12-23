#!/usr/bin/env python3
"""
Migrate social_posts table to support additional event types.

This script updates the CHECK constraint on the event_type column to include
new event types like FRANCHISE_TAG, PLAYOFF_GAME, SUPER_BOWL, etc.

Usage:
    python scripts/migrate_social_posts_schema.py
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DB_PATH = Path(__file__).parent.parent / "data" / "database" / "game_cycle" / "game_cycle.db"


def migrate_social_posts_table():
    """Migrate the social_posts table to support new event types."""

    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        print("   No migration needed (will use new schema when created)")
        return

    print(f"🔧 Migrating database at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='social_posts'
        """)
        if not cursor.fetchone():
            print("✅ No social_posts table found (will use new schema)")
            return

        # Check current schema
        cursor.execute("PRAGMA table_info(social_posts)")
        columns = cursor.fetchall()
        print(f"📊 Found social_posts table with {len(columns)} columns")

        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM social_posts")
        record_count = cursor.fetchone()[0]
        print(f"📝 Backing up {record_count} existing social posts...")

        # Step 1: Create temporary table with new schema
        print("🔨 Creating temporary table with updated schema...")
        cursor.execute("""
            CREATE TABLE social_posts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                personality_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                post_text TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN (
                    'GAME_RESULT', 'PLAYOFF_GAME', 'SUPER_BOWL',
                    'TRADE', 'SIGNING', 'FRANCHISE_TAG', 'RESIGNING',
                    'CUT', 'WAIVER_CLAIM', 'DRAFT', 'DRAFT_PICK',
                    'AWARD', 'HOF_INDUCTION', 'INJURY', 'RUMOR', 'TRAINING_CAMP'
                )),
                sentiment REAL NOT NULL CHECK(sentiment BETWEEN -1.0 AND 1.0),
                likes INTEGER DEFAULT 0 CHECK(likes >= 0),
                retweets INTEGER DEFAULT 0 CHECK(retweets >= 0),
                event_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                FOREIGN KEY (personality_id) REFERENCES social_personalities(id) ON DELETE CASCADE
            )
        """)

        # Step 2: Copy data from old table to new table
        if record_count > 0:
            print(f"📋 Copying {record_count} records to new table...")
            cursor.execute("""
                INSERT INTO social_posts_new
                    (id, dynasty_id, personality_id, season, week, post_text,
                     event_type, sentiment, likes, retweets, event_metadata, created_at)
                SELECT
                    id, dynasty_id, personality_id, season, week, post_text,
                    event_type, sentiment, likes, retweets, event_metadata, created_at
                FROM social_posts
            """)

        # Step 3: Drop old table
        print("🗑️  Dropping old table...")
        cursor.execute("DROP TABLE social_posts")

        # Step 4: Rename new table
        print("✏️  Renaming new table...")
        cursor.execute("ALTER TABLE social_posts_new RENAME TO social_posts")

        # Step 5: Recreate indexes
        print("🔍 Recreating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_social_posts_dynasty_season_week
            ON social_posts(dynasty_id, season, week)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_social_posts_dynasty_season_week_desc
            ON social_posts(dynasty_id, season DESC, week DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_social_posts_personality
            ON social_posts(personality_id)
        """)

        # Commit changes
        conn.commit()

        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM social_posts")
        new_count = cursor.fetchone()[0]

        if new_count == record_count:
            print(f"✅ Migration successful! {new_count} records preserved.")
            print("\n📋 New event types now supported:")
            print("   - FRANCHISE_TAG")
            print("   - PLAYOFF_GAME")
            print("   - SUPER_BOWL")
            print("   - RESIGNING")
            print("   - WAIVER_CLAIM")
            print("   - DRAFT_PICK (in addition to DRAFT)")
            print("   - HOF_INDUCTION")
            print("   - TRAINING_CAMP")
        else:
            print(f"⚠️  Warning: Record count mismatch!")
            print(f"   Before: {record_count}, After: {new_count}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Social Posts Schema Migration")
    print("=" * 60)
    migrate_social_posts_table()
    print("=" * 60)
