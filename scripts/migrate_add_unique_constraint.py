#!/usr/bin/env python3
"""
Migration Script: Add UNIQUE Constraint to player_game_stats

Adds a UNIQUE constraint on (dynasty_id, game_id, player_id, season_type)
to the player_game_stats table in existing databases.

This prevents duplicate stats entries for the same player in the same game.

Usage:
    python scripts/migrate_add_unique_constraint.py [db_path]

If no path is provided, uses the default game cycle database.

IMPORTANT: Run the deduplication script FIRST to remove existing duplicates!
"""

import sqlite3
import sys
from pathlib import Path


def migrate_add_unique_constraint(db_path: str):
    """Add UNIQUE constraint to player_game_stats table."""

    print(f"\n🔍 Opening database: {db_path}")

    if not Path(db_path).exists():
        print(f"❌ Error: Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if there are any duplicates before migration
        cursor.execute("""
            SELECT COUNT(*) FROM player_game_stats
            WHERE id NOT IN (
                SELECT MAX(id) FROM player_game_stats
                GROUP BY dynasty_id, game_id, player_id, season_type
            )
        """)
        duplicate_count = cursor.fetchone()[0]

        if duplicate_count > 0:
            print(f"\n❌ ERROR: Found {duplicate_count:,} duplicate rows!")
            print("   You must run deduplicate_player_stats.py FIRST to remove duplicates.")
            print("   The UNIQUE constraint cannot be added while duplicates exist.")
            conn.close()
            return False

        print("✅ No duplicates found - safe to proceed with migration")

        # Get the current schema
        cursor.execute("PRAGMA table_info(player_game_stats)")
        columns = cursor.fetchall()

        print(f"\n📋 Table has {len(columns)} columns")

        # Create new table with UNIQUE constraint
        print("\n🔧 Creating new table with UNIQUE constraint...")
        cursor.execute("""
            CREATE TABLE player_game_stats_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                player_id TEXT NOT NULL,
                player_name TEXT,
                team_id INTEGER NOT NULL,
                position TEXT,

                -- Passing stats
                passing_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                passing_attempts INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                passing_sacks INTEGER DEFAULT 0,
                passing_sack_yards INTEGER DEFAULT 0,
                passing_rating REAL DEFAULT 0,
                air_yards INTEGER DEFAULT 0,

                -- Rushing stats
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_attempts INTEGER DEFAULT 0,
                rushing_long INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,

                -- Receiving stats
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                targets INTEGER DEFAULT 0,
                receiving_long INTEGER DEFAULT 0,
                receiving_drops INTEGER DEFAULT 0,
                yards_after_catch INTEGER DEFAULT 0,

                -- Defensive stats
                tackles_total INTEGER DEFAULT 0,
                tackles_solo INTEGER DEFAULT 0,
                tackles_assist INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0,
                interceptions INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                tackles_for_loss INTEGER DEFAULT 0,
                qb_hits INTEGER DEFAULT 0,
                qb_pressures INTEGER DEFAULT 0,

                -- Special teams stats
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,
                punts INTEGER DEFAULT 0,
                punt_yards INTEGER DEFAULT 0,

                -- Offensive Line stats
                pass_blocks INTEGER DEFAULT 0,
                pancakes INTEGER DEFAULT 0,
                sacks_allowed INTEGER DEFAULT 0,
                hurries_allowed INTEGER DEFAULT 0,
                pressures_allowed INTEGER DEFAULT 0,
                run_blocking_grade REAL DEFAULT 0.0,
                pass_blocking_efficiency REAL DEFAULT 0.0,
                missed_assignments INTEGER DEFAULT 0,
                holding_penalties INTEGER DEFAULT 0,
                false_start_penalties INTEGER DEFAULT 0,
                downfield_blocks INTEGER DEFAULT 0,
                double_team_blocks INTEGER DEFAULT 0,
                chip_blocks INTEGER DEFAULT 0,

                -- Performance metrics
                snap_counts_offense INTEGER DEFAULT 0,
                snap_counts_defense INTEGER DEFAULT 0,
                snap_counts_special_teams INTEGER DEFAULT 0,

                fantasy_points REAL DEFAULT 0,

                -- ✅ UNIQUE constraint prevents duplicates
                UNIQUE(dynasty_id, game_id, player_id, season_type),

                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            );
        """)

        # Count rows to migrate
        cursor.execute("SELECT COUNT(*) FROM player_game_stats")
        row_count = cursor.fetchone()[0]
        print(f"📊 Copying {row_count:,} rows to new table...")

        # Copy data to new table
        cursor.execute("""
            INSERT INTO player_game_stats_new
            SELECT * FROM player_game_stats;
        """)

        copied_rows = cursor.rowcount
        print(f"✅ Copied {copied_rows:,} rows")

        # Drop old table
        print("\n🗑️  Dropping old table...")
        cursor.execute("DROP TABLE player_game_stats;")

        # Rename new table
        print("🔄 Renaming new table...")
        cursor.execute("ALTER TABLE player_game_stats_new RENAME TO player_game_stats;")

        # Commit changes
        conn.commit()

        # Verify the constraint exists
        cursor.execute("PRAGMA index_list(player_game_stats)")
        indices = cursor.fetchall()

        print(f"\n✅ Migration complete!")
        print(f"   Rows migrated: {copied_rows:,}")
        print(f"   Indices created: {len(indices)}")

        # Show the indices
        if indices:
            print("\n📋 Table indices:")
            for idx in indices:
                print(f"   - {idx[1]} (unique: {bool(idx[2])})")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        print("\nRolling back changes...")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    # Default database path
    default_db_path = "data/database/game_cycle/game_cycle.db"

    # Allow custom path from command line
    db_path = sys.argv[1] if len(sys.argv) > 1 else default_db_path

    print("=" * 70)
    print("     MIGRATION: ADD UNIQUE CONSTRAINT TO player_game_stats")
    print("=" * 70)
    print("\n⚠️  IMPORTANT: Run deduplicate_player_stats.py FIRST!")
    print("   This migration will fail if duplicates exist.\n")

    # Confirm before proceeding
    response = input("Continue with migration? [y/N]: ")
    if response.lower() != 'y':
        print("❌ Migration cancelled by user")
        sys.exit(1)

    success = migrate_add_unique_constraint(db_path)

    if success:
        print("\n✅ Script completed successfully")
        print("\n🎉 The UNIQUE constraint has been added to player_game_stats")
        print("   Future duplicate insertions will be prevented automatically.")
        sys.exit(0)
    else:
        print("\n❌ Script completed with errors")
        sys.exit(1)
