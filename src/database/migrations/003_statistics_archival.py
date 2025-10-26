"""
Migration: Add statistics archival tables and archived flags

Creates infrastructure for statistics preservation system:
- season_archives table: Stores season metadata and champions
- archival_config table: Per-dynasty retention policy configuration
- Adds 'archived' flag to games and player_game_stats tables

Schema Version: 2.6.0

Usage:
    # Apply migration (dry run)
    PYTHONPATH=src python src/database/migrations/003_statistics_archival.py

    # Apply with actual changes (commit)
    PYTHONPATH=src python src/database/migrations/003_statistics_archival.py --commit

    # Rollback migration
    PYTHONPATH=src python src/database/migrations/003_statistics_archival.py --rollback --commit
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple


class StatisticsArchivalMigration:
    """Migration to add statistics archival infrastructure."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def up(self, commit: bool = False):
        """
        Apply migration: create archival tables and add archived columns.

        Args:
            commit: If True, commit changes. If False, dry run only.
        """
        dry_run = not commit

        if dry_run:
            print("=" * 80)
            print("DRY RUN MODE - No changes will be committed")
            print("Use --commit flag to apply changes")
            print("=" * 80)
            print()
        else:
            print("=" * 80)
            print("COMMIT MODE - Changes will be applied to database")
            print("=" * 80)
            print()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            conn.execute("BEGIN TRANSACTION")

            # Step 1: Create season_archives table
            if self._table_exists(conn, "season_archives"):
                print("⚠️  Table 'season_archives' already exists, skipping")
            else:
                print("📦 Creating season_archives table...")
                self._create_season_archives_table(conn)
                print("✅ season_archives table created")

            # Step 2: Create archival_config table
            if self._table_exists(conn, "archival_config"):
                print("⚠️  Table 'archival_config' already exists, skipping")
            else:
                print("📦 Creating archival_config table...")
                self._create_archival_config_table(conn)
                print("✅ archival_config table created")

            # Step 3: Add archived column to games table
            if self._column_exists(conn, "games", "archived"):
                print("⚠️  Column 'archived' already exists in games table, skipping")
            else:
                print("📦 Adding 'archived' column to games table...")
                conn.execute("ALTER TABLE games ADD COLUMN archived BOOLEAN DEFAULT FALSE")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_games_archived ON games(archived)")
                print("✅ Added 'archived' column to games table")

            # Step 4: Add archived column to player_game_stats table
            if self._column_exists(conn, "player_game_stats", "archived"):
                print("⚠️  Column 'archived' already exists in player_game_stats table, skipping")
            else:
                print("📦 Adding 'archived' column to player_game_stats table...")
                conn.execute("ALTER TABLE player_game_stats ADD COLUMN archived BOOLEAN DEFAULT FALSE")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_player_game_stats_archived ON player_game_stats(archived)")
                print("✅ Added 'archived' column to player_game_stats table")

            # Step 5: Initialize archival config for existing dynasties
            print("\n📦 Initializing archival config for existing dynasties...")
            dynasties = self._get_existing_dynasties(conn)
            if dynasties:
                self._initialize_archival_configs(conn, dynasties)
                print(f"✅ Initialized archival config for {len(dynasties)} dynasties")
            else:
                print("⚠️  No existing dynasties found")

            # Final commit or rollback
            if dry_run:
                print("\n" + "=" * 80)
                print("DRY RUN COMPLETE - Rolling back all changes")
                print("Use --commit flag to apply changes")
                print("=" * 80)
                conn.rollback()
            else:
                print("\n" + "=" * 80)
                print("COMMITTING CHANGES...")
                conn.commit()
                print("✅ Migration completed successfully!")
                print("=" * 80)

        except Exception as e:
            conn.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            conn.close()

    def down(self, commit: bool = False):
        """
        Rollback migration: drop archival tables and remove archived columns.

        Args:
            commit: If True, commit changes. If False, dry run only.
        """
        dry_run = not commit

        if dry_run:
            print("=" * 80)
            print("DRY RUN ROLLBACK MODE - No changes will be committed")
            print("Use --commit flag to apply rollback")
            print("=" * 80)
            print()
        else:
            print("=" * 80)
            print("COMMIT ROLLBACK MODE - Tables will be dropped")
            print("=" * 80)
            print()

        conn = sqlite3.connect(self.db_path)

        try:
            conn.execute("BEGIN TRANSACTION")

            # Drop archival_config table
            if self._table_exists(conn, "archival_config"):
                print("📦 Dropping archival_config table...")
                conn.execute("DROP TABLE archival_config")
                print("✅ archival_config table dropped")

            # Drop season_archives table
            if self._table_exists(conn, "season_archives"):
                print("📦 Dropping season_archives table...")
                conn.execute("DROP TABLE season_archives")
                print("✅ season_archives table dropped")

            # Note: SQLite doesn't support DROP COLUMN directly
            # We would need to recreate tables without the archived column
            # For now, just document that archived columns remain but unused
            print("\n⚠️  Note: 'archived' columns in games and player_game_stats remain")
            print("    SQLite doesn't support DROP COLUMN. These columns are harmless.")
            print("    They default to FALSE and won't affect existing queries.")

            if dry_run:
                print("\n" + "=" * 80)
                print("DRY RUN ROLLBACK COMPLETE - Rolling back all changes")
                print("Use --commit flag to apply rollback")
                print("=" * 80)
                conn.rollback()
            else:
                print("\n" + "=" * 80)
                print("COMMITTING ROLLBACK...")
                conn.commit()
                print("✅ Rollback completed successfully!")
                print("=" * 80)

        except Exception as e:
            conn.rollback()
            print(f"\n❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists in database."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        ''', (table_name,))
        return cursor.fetchone() is not None

    def _column_exists(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Check if column exists in table."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(col[1] == column_name for col in columns)

    def _create_season_archives_table(self, conn: sqlite3.Connection):
        """Create season_archives table."""
        conn.execute('''
            CREATE TABLE season_archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,

                -- Champions
                super_bowl_champion INTEGER,  -- team_id
                afc_champion INTEGER,
                nfc_champion INTEGER,

                -- Individual awards
                mvp_player_id TEXT,
                offensive_poy TEXT,
                defensive_poy TEXT,
                offensive_rookie_of_year TEXT,
                defensive_rookie_of_year TEXT,
                comeback_player TEXT,
                coach_of_year INTEGER,  -- team_id

                -- Season records (JSON)
                season_records TEXT,  -- JSON: {"most_passing_yards": {"player": "QB_1", "value": 5477}, ...}

                -- Team records
                best_record_team_id INTEGER,
                best_record_wins INTEGER,
                best_record_losses INTEGER,

                -- Metadata
                games_played INTEGER DEFAULT 272,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Constraints
                UNIQUE(dynasty_id, season),
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        conn.execute("CREATE INDEX idx_season_archives_dynasty ON season_archives(dynasty_id)")
        conn.execute("CREATE INDEX idx_season_archives_season ON season_archives(season)")
        conn.execute("CREATE INDEX idx_season_archives_champion ON season_archives(super_bowl_champion)")

    def _create_archival_config_table(self, conn: sqlite3.Connection):
        """Create archival_config table."""
        conn.execute('''
            CREATE TABLE archival_config (
                dynasty_id TEXT PRIMARY KEY,

                -- Policy configuration
                policy_type TEXT DEFAULT 'keep_n_seasons',  -- 'keep_all' | 'keep_n_seasons' | 'summary_only'
                retention_seasons INTEGER DEFAULT 3,  -- Number of seasons to keep in hot storage
                auto_archive BOOLEAN DEFAULT TRUE,  -- Automatically archive on season end

                -- Statistics
                last_archival_season INTEGER,  -- Last season that was archived
                last_archival_timestamp TIMESTAMP,
                total_seasons_archived INTEGER DEFAULT 0,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Constraints
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                CHECK (policy_type IN ('keep_all', 'keep_n_seasons', 'summary_only')),
                CHECK (retention_seasons >= 0),
                CHECK (retention_seasons <= 100)  -- Sanity check
            )
        ''')

    def _get_existing_dynasties(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of existing dynasty IDs."""
        cursor = conn.cursor()
        cursor.execute("SELECT dynasty_id FROM dynasties")
        return [row[0] for row in cursor.fetchall()]

    def _initialize_archival_configs(self, conn: sqlite3.Connection, dynasties: List[str]):
        """Initialize archival config for existing dynasties."""
        for dynasty_id in dynasties:
            # Check if config already exists
            cursor = conn.cursor()
            cursor.execute("SELECT dynasty_id FROM archival_config WHERE dynasty_id = ?", (dynasty_id,))

            if not cursor.fetchone():
                # Create default config
                conn.execute('''
                    INSERT INTO archival_config (dynasty_id, policy_type, retention_seasons, auto_archive)
                    VALUES (?, 'keep_n_seasons', 3, TRUE)
                ''', (dynasty_id,))
                print(f"  ✅ Initialized config for dynasty '{dynasty_id}'")


def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate statistics archival tables and columns"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes (default is dry run)"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (drop tables)"
    )
    parser.add_argument(
        "--db-path",
        default="data/database/nfl_simulation.db",
        help="Path to database file (default: data/database/nfl_simulation.db)"
    )

    args = parser.parse_args()

    migration = StatisticsArchivalMigration(args.db_path)

    if args.rollback:
        migration.down(commit=args.commit)
    else:
        migration.up(commit=args.commit)


if __name__ == "__main__":
    main()
