"""
Migration: Add season_type column to player_season_stats table

Adds season_type column to support separate tracking of regular season and playoff stats.
Updates UNIQUE constraint and backfills existing records with 'regular_season'.

Schema Version: 2.5.1

Usage:
    # Dry run (preview changes)
    PYTHONPATH=src python src/database/migrations/add_season_type_column.py

    # Apply migration
    PYTHONPATH=src python src/database/migrations/add_season_type_column.py --commit

    # Rollback migration
    PYTHONPATH=src python src/database/migrations/add_season_type_column.py --rollback --commit
"""

import sqlite3
import sys
from pathlib import Path


class AddSeasonTypeColumnMigration:
    """Migration to add season_type column to player_season_stats."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dry_run = True

    def up(self, commit: bool = False):
        """
        Apply migration: add season_type column and update UNIQUE constraint.

        Args:
            commit: If True, commit changes. If False, dry run only.
        """
        self.dry_run = not commit

        if self.dry_run:
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
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Step 1: Check if table exists
            if not self._table_exists(conn, "player_season_stats"):
                print("❌ Table 'player_season_stats' does not exist")
                print("   Run add_player_season_stats_table.py migration first")
                conn.rollback()
                return

            # Step 2: Check if column already exists
            if self._column_exists(conn, "player_season_stats", "season_type"):
                print("⚠️  Column 'season_type' already exists")
                print("   Migration has already been applied")
                conn.rollback()
                return

            # Step 3: Get record count before migration
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM player_season_stats")
            record_count = cursor.fetchone()[0]
            print(f"📊 Found {record_count} existing records")

            # Step 4: Create temporary table with new schema
            print("\n📦 Creating temporary table with new schema...")
            self._create_temp_table(conn)
            print("✅ Temporary table created")

            # Step 5: Copy data to temporary table
            print("\n📦 Copying data to temporary table...")
            rows_copied = self._copy_data_to_temp(conn)
            print(f"✅ Copied {rows_copied} records")

            # Step 6: Drop old table
            print("\n📦 Dropping old table...")
            conn.execute("DROP TABLE player_season_stats")
            print("✅ Old table dropped")

            # Step 7: Rename temporary table
            print("\n📦 Renaming temporary table...")
            conn.execute("ALTER TABLE player_season_stats_temp RENAME TO player_season_stats")
            print("✅ Table renamed")

            # Step 8: Recreate indexes
            print("\n📦 Recreating indexes...")
            self._recreate_indexes(conn)
            print("✅ Indexes recreated")

            # Step 9: Verify migration
            print("\n📦 Verifying migration...")
            self._verify_migration(conn, record_count)
            print("✅ Migration verified")

            # Step 10: Commit or rollback
            if self.dry_run:
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
        Rollback migration: remove season_type column.

        Args:
            commit: If True, commit changes. If False, dry run only.
        """
        self.dry_run = not commit

        if self.dry_run:
            print("=" * 80)
            print("DRY RUN ROLLBACK MODE - No changes will be committed")
            print("Use --commit flag to apply rollback")
            print("=" * 80)
            print()
        else:
            print("=" * 80)
            print("COMMIT ROLLBACK MODE - Removing season_type column")
            print("=" * 80)
            print()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            conn.execute("BEGIN TRANSACTION")

            # Check if table exists
            if not self._table_exists(conn, "player_season_stats"):
                print("❌ Table 'player_season_stats' does not exist")
                conn.rollback()
                return

            # Check if column exists
            if not self._column_exists(conn, "player_season_stats", "season_type"):
                print("⚠️  Column 'season_type' does not exist")
                print("   Migration has not been applied yet")
                conn.rollback()
                return

            # Get record count
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM player_season_stats")
            record_count = cursor.fetchone()[0]
            print(f"📊 Found {record_count} existing records")

            # Create temp table with old schema (without season_type)
            print("\n📦 Creating temporary table with old schema...")
            self._create_temp_table_old_schema(conn)
            print("✅ Temporary table created")

            # Copy data (excluding season_type)
            print("\n📦 Copying data to temporary table...")
            rows_copied = self._copy_data_to_temp_old_schema(conn)
            print(f"✅ Copied {rows_copied} records")

            # Drop current table
            print("\n📦 Dropping current table...")
            conn.execute("DROP TABLE player_season_stats")
            print("✅ Table dropped")

            # Rename temp table
            print("\n📦 Renaming temporary table...")
            conn.execute("ALTER TABLE player_season_stats_temp RENAME TO player_season_stats")
            print("✅ Table renamed")

            # Recreate old indexes
            print("\n📦 Recreating original indexes...")
            self._recreate_old_indexes(conn)
            print("✅ Indexes recreated")

            if self.dry_run:
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
            import traceback
            traceback.print_exc()
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
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns

    def _create_temp_table(self, conn: sqlite3.Connection):
        """Create temporary table with new schema including season_type."""
        conn.execute('''
            CREATE TABLE player_season_stats_temp (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                position TEXT NOT NULL,
                season INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',

                -- Game counts
                games_played INTEGER DEFAULT 0,
                games_started INTEGER DEFAULT 0,

                -- Passing (raw stats)
                passing_attempts INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                sacks_taken INTEGER DEFAULT 0,

                -- Passing (computed stats)
                completion_percentage REAL DEFAULT 0.0,
                yards_per_attempt REAL DEFAULT 0.0,
                passer_rating REAL DEFAULT 0.0,

                -- Rushing (raw stats)
                rushing_attempts INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_long INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,

                -- Rushing (computed stats)
                yards_per_carry REAL DEFAULT 0.0,
                yards_per_game_rushing REAL DEFAULT 0.0,

                -- Receiving (raw stats)
                targets INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receiving_long INTEGER DEFAULT 0,
                receiving_fumbles INTEGER DEFAULT 0,

                -- Receiving (computed stats)
                catch_rate REAL DEFAULT 0.0,
                yards_per_reception REAL DEFAULT 0.0,
                yards_per_target REAL DEFAULT 0.0,
                yards_per_game_receiving REAL DEFAULT 0.0,

                -- Defense (raw stats)
                tackles_total INTEGER DEFAULT 0,
                tackles_solo INTEGER DEFAULT 0,
                tackles_assists INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0.0,
                interceptions INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                defensive_tds INTEGER DEFAULT 0,

                -- Special teams (raw stats)
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                field_goal_long INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,

                -- Special teams (computed stats)
                field_goal_percentage REAL DEFAULT 0.0,
                extra_point_percentage REAL DEFAULT 0.0,

                -- Metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(dynasty_id, player_id, season, season_type),
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            )
        ''')

    def _copy_data_to_temp(self, conn: sqlite3.Connection) -> int:
        """Copy data from old table to new table with season_type defaulted to 'regular_season'."""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO player_season_stats_temp (
                stat_id, dynasty_id, player_id, player_name, team_id, position, season,
                season_type, games_played, games_started,
                passing_attempts, passing_completions, passing_yards, passing_tds,
                passing_interceptions, sacks_taken,
                completion_percentage, yards_per_attempt, passer_rating,
                rushing_attempts, rushing_yards, rushing_tds, rushing_long, rushing_fumbles,
                yards_per_carry, yards_per_game_rushing,
                targets, receptions, receiving_yards, receiving_tds, receiving_long, receiving_fumbles,
                catch_rate, yards_per_reception, yards_per_target, yards_per_game_receiving,
                tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
                passes_defended, forced_fumbles, fumbles_recovered, defensive_tds,
                field_goals_made, field_goals_attempted, field_goal_long,
                extra_points_made, extra_points_attempted,
                field_goal_percentage, extra_point_percentage,
                last_updated
            )
            SELECT
                stat_id, dynasty_id, player_id, player_name, team_id, position, season,
                'regular_season' as season_type, games_played, games_started,
                passing_attempts, passing_completions, passing_yards, passing_tds,
                passing_interceptions, sacks_taken,
                completion_percentage, yards_per_attempt, passer_rating,
                rushing_attempts, rushing_yards, rushing_tds, rushing_long, rushing_fumbles,
                yards_per_carry, yards_per_game_rushing,
                targets, receptions, receiving_yards, receiving_tds, receiving_long, receiving_fumbles,
                catch_rate, yards_per_reception, yards_per_target, yards_per_game_receiving,
                tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
                passes_defended, forced_fumbles, fumbles_recovered, defensive_tds,
                field_goals_made, field_goals_attempted, field_goal_long,
                extra_points_made, extra_points_attempted,
                field_goal_percentage, extra_point_percentage,
                last_updated
            FROM player_season_stats
        ''')
        return cursor.rowcount

    def _recreate_indexes(self, conn: sqlite3.Connection):
        """Recreate indexes with season_type support."""
        indexes = [
            ("idx_season_stats_dynasty_season",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_dynasty_season ON player_season_stats(dynasty_id, season)"),

            ("idx_season_stats_season_type",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_season_type ON player_season_stats(dynasty_id, season, season_type)"),

            ("idx_season_stats_passing_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_passing_leaders ON player_season_stats(dynasty_id, season, passing_yards DESC)"),

            ("idx_season_stats_rushing_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_rushing_leaders ON player_season_stats(dynasty_id, season, rushing_yards DESC)"),

            ("idx_season_stats_receiving_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_receiving_leaders ON player_season_stats(dynasty_id, season, receiving_yards DESC)"),

            ("idx_season_stats_player_lookup",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_player_lookup ON player_season_stats(dynasty_id, player_id, season)")
        ]

        for index_name, create_sql in indexes:
            try:
                conn.execute(create_sql)
                print(f"  ✅ Created index: {index_name}")
            except Exception as e:
                print(f"  ⚠️  Error creating index {index_name}: {e}")

    def _verify_migration(self, conn: sqlite3.Connection, expected_count: int):
        """Verify that migration was successful."""
        cursor = conn.cursor()

        # Check record count
        cursor.execute("SELECT COUNT(*) FROM player_season_stats")
        actual_count = cursor.fetchone()[0]

        if actual_count != expected_count:
            raise Exception(f"Record count mismatch: expected {expected_count}, got {actual_count}")

        print(f"  ✅ Record count verified: {actual_count} records")

        # Check season_type values
        cursor.execute("SELECT DISTINCT season_type FROM player_season_stats")
        season_types = [row[0] for row in cursor.fetchall()]

        if season_types != ['regular_season']:
            raise Exception(f"Unexpected season_type values: {season_types}")

        print(f"  ✅ All records have season_type='regular_season'")

        # Check UNIQUE constraint
        cursor.execute('''
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='player_season_stats'
        ''')
        schema = cursor.fetchone()[0]

        if 'UNIQUE(dynasty_id, player_id, season, season_type)' not in schema:
            raise Exception("UNIQUE constraint not found in schema")

        print(f"  ✅ UNIQUE constraint includes season_type")

    def _create_temp_table_old_schema(self, conn: sqlite3.Connection):
        """Create temporary table with old schema (without season_type) for rollback."""
        conn.execute('''
            CREATE TABLE player_season_stats_temp (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                position TEXT NOT NULL,
                season INTEGER NOT NULL,

                -- Game counts
                games_played INTEGER DEFAULT 0,
                games_started INTEGER DEFAULT 0,

                -- Passing (raw stats)
                passing_attempts INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                sacks_taken INTEGER DEFAULT 0,

                -- Passing (computed stats)
                completion_percentage REAL DEFAULT 0.0,
                yards_per_attempt REAL DEFAULT 0.0,
                passer_rating REAL DEFAULT 0.0,

                -- Rushing (raw stats)
                rushing_attempts INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_long INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,

                -- Rushing (computed stats)
                yards_per_carry REAL DEFAULT 0.0,
                yards_per_game_rushing REAL DEFAULT 0.0,

                -- Receiving (raw stats)
                targets INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receiving_long INTEGER DEFAULT 0,
                receiving_fumbles INTEGER DEFAULT 0,

                -- Receiving (computed stats)
                catch_rate REAL DEFAULT 0.0,
                yards_per_reception REAL DEFAULT 0.0,
                yards_per_target REAL DEFAULT 0.0,
                yards_per_game_receiving REAL DEFAULT 0.0,

                -- Defense (raw stats)
                tackles_total INTEGER DEFAULT 0,
                tackles_solo INTEGER DEFAULT 0,
                tackles_assists INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0.0,
                interceptions INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                defensive_tds INTEGER DEFAULT 0,

                -- Special teams (raw stats)
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                field_goal_long INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,

                -- Special teams (computed stats)
                field_goal_percentage REAL DEFAULT 0.0,
                extra_point_percentage REAL DEFAULT 0.0,

                -- Metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(dynasty_id, player_id, season),
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            )
        ''')

    def _copy_data_to_temp_old_schema(self, conn: sqlite3.Connection) -> int:
        """Copy data excluding season_type column."""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO player_season_stats_temp (
                stat_id, dynasty_id, player_id, player_name, team_id, position, season,
                games_played, games_started,
                passing_attempts, passing_completions, passing_yards, passing_tds,
                passing_interceptions, sacks_taken,
                completion_percentage, yards_per_attempt, passer_rating,
                rushing_attempts, rushing_yards, rushing_tds, rushing_long, rushing_fumbles,
                yards_per_carry, yards_per_game_rushing,
                targets, receptions, receiving_yards, receiving_tds, receiving_long, receiving_fumbles,
                catch_rate, yards_per_reception, yards_per_target, yards_per_game_receiving,
                tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
                passes_defended, forced_fumbles, fumbles_recovered, defensive_tds,
                field_goals_made, field_goals_attempted, field_goal_long,
                extra_points_made, extra_points_attempted,
                field_goal_percentage, extra_point_percentage,
                last_updated
            )
            SELECT
                stat_id, dynasty_id, player_id, player_name, team_id, position, season,
                games_played, games_started,
                passing_attempts, passing_completions, passing_yards, passing_tds,
                passing_interceptions, sacks_taken,
                completion_percentage, yards_per_attempt, passer_rating,
                rushing_attempts, rushing_yards, rushing_tds, rushing_long, rushing_fumbles,
                yards_per_carry, yards_per_game_rushing,
                targets, receptions, receiving_yards, receiving_tds, receiving_long, receiving_fumbles,
                catch_rate, yards_per_reception, yards_per_target, yards_per_game_receiving,
                tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
                passes_defended, forced_fumbles, fumbles_recovered, defensive_tds,
                field_goals_made, field_goals_attempted, field_goal_long,
                extra_points_made, extra_points_attempted,
                field_goal_percentage, extra_point_percentage,
                last_updated
            FROM player_season_stats
            WHERE season_type = 'regular_season'
        ''')
        return cursor.rowcount

    def _recreate_old_indexes(self, conn: sqlite3.Connection):
        """Recreate original indexes without season_type."""
        indexes = [
            ("idx_season_stats_dynasty_season",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_dynasty_season ON player_season_stats(dynasty_id, season)"),

            ("idx_season_stats_passing_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_passing_leaders ON player_season_stats(dynasty_id, season, passing_yards DESC)"),

            ("idx_season_stats_rushing_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_rushing_leaders ON player_season_stats(dynasty_id, season, rushing_yards DESC)"),

            ("idx_season_stats_receiving_leaders",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_receiving_leaders ON player_season_stats(dynasty_id, season, receiving_yards DESC)"),

            ("idx_season_stats_player_lookup",
             "CREATE INDEX IF NOT EXISTS idx_season_stats_player_lookup ON player_season_stats(dynasty_id, player_id, season)")
        ]

        for index_name, create_sql in indexes:
            try:
                conn.execute(create_sql)
                print(f"  ✅ Created index: {index_name}")
            except Exception as e:
                print(f"  ⚠️  Error creating index {index_name}: {e}")


def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add season_type column to player_season_stats table"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes (default is dry run)"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (remove season_type column)"
    )
    parser.add_argument(
        "--db-path",
        default="data/database/nfl_simulation.db",
        help="Path to database file (default: data/database/nfl_simulation.db)"
    )

    args = parser.parse_args()

    migration = AddSeasonTypeColumnMigration(args.db_path)

    if args.rollback:
        migration.down(commit=args.commit)
    else:
        migration.up(commit=args.commit)


if __name__ == "__main__":
    main()
