"""
Migration: Add dynasty_id column to events table

Adds dynasty_id column with foreign key constraint for proper dynasty isolation.
This aligns the events table with the architectural pattern used in all other tables.
"""

import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime


class EventsDynastyIdMigration:
    """Migration to add dynasty_id column to events table."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def up(self):
        """Apply migration: add dynasty_id column."""
        conn = sqlite3.connect(self.db_path)

        try:
            # Step 1: Add dynasty_id column (nullable initially for migration)
            conn.execute('ALTER TABLE events ADD COLUMN dynasty_id TEXT')

            # Step 2: Populate dynasty_id for existing events
            self._migrate_existing_events(conn)

            # Step 3: Make dynasty_id NOT NULL (after population)
            # SQLite doesn't support ALTER COLUMN, so we recreate table
            conn.execute('''
                CREATE TABLE events_new (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    dynasty_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
                )
            ''')

            # Copy data
            conn.execute('''
                INSERT INTO events_new
                SELECT event_id, event_type, timestamp, game_id, dynasty_id, data
                FROM events
            ''')

            # Drop old table and rename
            conn.execute('DROP TABLE events')
            conn.execute('ALTER TABLE events_new RENAME TO events')

            # Step 4: Recreate indexes
            conn.execute('CREATE INDEX idx_events_game_id ON events(game_id)')
            conn.execute('CREATE INDEX idx_events_timestamp ON events(timestamp)')
            conn.execute('CREATE INDEX idx_events_type ON events(event_type)')

            # Step 5: Create new composite index for dynasty-filtered queries
            conn.execute('CREATE INDEX idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
            conn.execute('CREATE INDEX idx_events_dynasty_type ON events(dynasty_id, event_type)')

            conn.commit()
            print("✅ Migration completed successfully")

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def _migrate_existing_events(self, conn: sqlite3.Connection):
        """
        Migrate existing events by inferring dynasty_id.

        Strategy:
        1. For playoff games with dynasty_id in game_id: extract it
        2. For other events: use dynasty_state table to infer from timestamp/season
        3. Default to 'default' if uncertain
        """
        cursor = conn.cursor()

        # Get all events
        cursor.execute('SELECT event_id, game_id, timestamp FROM events')
        events = cursor.fetchall()

        for event_id, game_id, timestamp_ms in events:
            dynasty_id = self._infer_dynasty_id(conn, game_id, timestamp_ms)

            cursor.execute(
                'UPDATE events SET dynasty_id = ? WHERE event_id = ?',
                (dynasty_id, event_id)
            )

        print(f"✅ Migrated {len(events)} existing events")

    def _infer_dynasty_id(
        self,
        conn: sqlite3.Connection,
        game_id: str,
        timestamp_ms: int
    ) -> str:
        """
        Infer dynasty_id from game_id or timestamp.

        Args:
            conn: Database connection
            game_id: Event game_id (may contain dynasty info)
            timestamp_ms: Event timestamp in milliseconds

        Returns:
            Inferred dynasty_id
        """
        # Case 1: Playoff games encode dynasty in game_id
        # Format: "playoff_{dynasty_id}_{season}_{round}_{game}"
        if game_id.startswith('playoff_'):
            parts = game_id.split('_')
            if len(parts) >= 3:
                # Extract dynasty_id (second part)
                return parts[1]

        # Case 2: Check dynasty_state table for active dynasty at this timestamp
        cursor = conn.cursor()

        # Convert timestamp to date
        event_date = datetime.fromtimestamp(timestamp_ms / 1000)
        date_str = event_date.strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT dynasty_id FROM dynasty_state
            WHERE current_date = ?
            LIMIT 1
        ''', (date_str,))

        result = cursor.fetchone()
        if result:
            return result[0]

        # Case 3: Try to find dynasty from games table using game_id
        cursor.execute('''
            SELECT dynasty_id FROM games
            WHERE game_id = ?
            LIMIT 1
        ''', (game_id,))

        result = cursor.fetchone()
        if result:
            return result[0]

        # Case 4: If only one dynasty exists, use it
        cursor.execute('SELECT dynasty_id FROM dynasties LIMIT 2')
        dynasties = cursor.fetchall()
        if len(dynasties) == 1:
            return dynasties[0][0]

        # Case 5: Default fallback (create 'default' if doesn't exist)
        cursor.execute("SELECT dynasty_id FROM dynasties WHERE dynasty_id = 'default'")
        if not cursor.fetchone():
            # Create default dynasty entry
            cursor.execute('''
                INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
                VALUES ('default', 'Default Dynasty', NULL, NULL)
            ''')
            conn.commit()

        return 'default'

    def down(self):
        """Rollback migration: remove dynasty_id column."""
        conn = sqlite3.connect(self.db_path)

        try:
            # Recreate table without dynasty_id
            conn.execute('''
                CREATE TABLE events_rollback (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')

            conn.execute('''
                INSERT INTO events_rollback
                SELECT event_id, event_type, timestamp, game_id, data
                FROM events
            ''')

            conn.execute('DROP TABLE events')
            conn.execute('ALTER TABLE events_rollback RENAME TO events')

            # Recreate original indexes
            conn.execute('CREATE INDEX idx_events_game_id ON events(game_id)')
            conn.execute('CREATE INDEX idx_events_timestamp ON events(timestamp)')
            conn.execute('CREATE INDEX idx_events_type ON events(event_type)')

            conn.commit()
            print("✅ Rollback completed successfully")

        except Exception as e:
            conn.rollback()
            print(f"❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()


if __name__ == '__main__':
    # Run migration
    migration = EventsDynastyIdMigration('data/database/nfl_simulation.db')
    migration.up()
