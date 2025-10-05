"""
Migration: Add game_date column to games table

Adds game_date timestamp column to games table for calendar integration.
This allows querying games by date for historical calendar display.
"""

import sqlite3
from pathlib import Path
from typing import Optional


class GamesGameDateMigration:
    """Migration to add game_date column to games table."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def up(self):
        """Apply migration: add game_date column."""
        conn = sqlite3.connect(self.db_path)

        try:
            print("📦 Adding game_date column to games table...")

            # Step 1: Add game_date column (nullable initially for migration)
            conn.execute('ALTER TABLE games ADD COLUMN game_date INTEGER')
            print("✅ Added game_date column")

            # Step 2: Backfill game_date from events table where possible
            print("📦 Backfilling game_date from events table...")
            result = conn.execute('''
                UPDATE games
                SET game_date = (
                    SELECT timestamp
                    FROM events
                    WHERE events.game_id = games.game_id
                    AND events.dynasty_id = games.dynasty_id
                    LIMIT 1
                )
                WHERE game_date IS NULL
            ''')

            backfilled_count = result.rowcount
            print(f"✅ Backfilled {backfilled_count} game dates from events table")

            # Step 3: For games without matching events, try to estimate from week/season
            # NFL regular season typically starts first Thursday of September
            print("📦 Estimating dates for remaining games...")
            conn.execute('''
                UPDATE games
                SET game_date = (
                    -- Estimate: September 5 + (week-1)*7 days, converted to milliseconds
                    -- This is rough but better than NULL
                    CAST((
                        strftime('%s', season || '-09-05') + ((week - 1) * 7 * 86400)
                    ) * 1000 AS INTEGER)
                )
                WHERE game_date IS NULL AND season_type = 'regular_season'
            ''')

            # For playoff games, estimate based on typical playoff schedule
            conn.execute('''
                UPDATE games
                SET game_date = (
                    -- Wild card: Week 19 (mid-January)
                    -- Divisional: Week 20
                    -- Conference: Week 21
                    -- Super Bowl: Week 22 (early February)
                    CAST((
                        strftime('%s', (season + 1) || '-01-10') + ((week - 19) * 7 * 86400)
                    ) * 1000 AS INTEGER)
                )
                WHERE game_date IS NULL AND season_type = 'playoffs'
            ''')

            estimated_count = conn.execute(
                'SELECT COUNT(*) FROM games WHERE game_date IS NOT NULL'
            ).fetchone()[0]
            print(f"✅ Estimated dates for games (total with dates: {estimated_count})")

            # Step 4: Create index for efficient date-range queries
            print("📦 Creating index on (dynasty_id, game_date)...")
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_games_dynasty_date
                ON games(dynasty_id, game_date)
            ''')
            print("✅ Created index idx_games_dynasty_date")

            # Commit all changes
            conn.commit()
            print("\n✅ Migration completed successfully!")

            # Report statistics
            total_games = conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
            games_with_dates = conn.execute(
                'SELECT COUNT(*) FROM games WHERE game_date IS NOT NULL'
            ).fetchone()[0]
            games_without_dates = total_games - games_with_dates

            print(f"\nStatistics:")
            print(f"  Total games: {total_games}")
            print(f"  Games with dates: {games_with_dates}")
            print(f"  Games without dates: {games_without_dates}")

        except Exception as e:
            conn.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def down(self):
        """Rollback migration: remove game_date column."""
        conn = sqlite3.connect(self.db_path)

        try:
            print("📦 Rolling back: Removing game_date column...")

            # SQLite doesn't support DROP COLUMN directly
            # Need to recreate table without game_date column

            # Step 1: Create new table without game_date
            conn.execute('''
                CREATE TABLE games_old (
                    game_id TEXT PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    week INTEGER NOT NULL,
                    season_type TEXT NOT NULL DEFAULT 'regular_season',
                    game_type TEXT DEFAULT 'regular',
                    home_team_id INTEGER NOT NULL,
                    away_team_id INTEGER NOT NULL,
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    total_plays INTEGER,
                    game_duration_minutes INTEGER,
                    overtime_periods INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
                )
            ''')

            # Step 2: Copy data (excluding game_date)
            conn.execute('''
                INSERT INTO games_old
                SELECT
                    game_id, dynasty_id, season, week, season_type, game_type,
                    home_team_id, away_team_id, home_score, away_score,
                    total_plays, game_duration_minutes, overtime_periods, created_at
                FROM games
            ''')

            # Step 3: Drop new table
            conn.execute('DROP TABLE games')

            # Step 4: Rename old table back
            conn.execute('ALTER TABLE games_old RENAME TO games')

            # Step 5: Recreate indexes (without game_date index)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_dynasty ON games(dynasty_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_week ON games(week)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_dynasty_season ON games(dynasty_id, season, week)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_season_type ON games(dynasty_id, season, season_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_games_type ON games(game_type)')

            conn.commit()
            print("✅ Rollback completed successfully!")

        except Exception as e:
            conn.rollback()
            print(f"❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()


def main():
    """Run migration on default database."""
    import sys

    db_path = "data/database/nfl_simulation.db"

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("Rolling back migration...")
        migration = GamesGameDateMigration(db_path)
        migration.down()
    else:
        print("Applying migration...")
        migration = GamesGameDateMigration(db_path)
        migration.up()


if __name__ == "__main__":
    main()
