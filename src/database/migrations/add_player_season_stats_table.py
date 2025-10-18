"""
Migration: Add player_season_stats table and backfill from player_game_stats

Creates aggregated season statistics table for improved leaderboard performance.
Follows industry-standard two-tier architecture (game stats + season stats).

Schema Version: 2.5.0

Usage:
    # Apply migration (default - dry run)
    PYTHONPATH=src python src/database/migrations/add_player_season_stats_table.py

    # Apply with actual changes (commit)
    PYTHONPATH=src python src/database/migrations/add_player_season_stats_table.py --commit

    # Rollback migration
    PYTHONPATH=src python src/database/migrations/add_player_season_stats_table.py --rollback

    # Rollback with commit
    PYTHONPATH=src python src/database/migrations/add_player_season_stats_table.py --rollback --commit
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PlayerSeasonStatsMigration:
    """Migration to add player_season_stats table with backfill capability."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dry_run = True

    def up(self, commit: bool = False):
        """
        Apply migration: create player_season_stats table and backfill data.

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

            # Step 1: Check if table already exists
            if self._table_exists(conn, "player_season_stats"):
                print("⚠️  Table 'player_season_stats' already exists")
                print("    Skipping table creation")
                table_created = False
            else:
                # Step 2: Create table
                print("📦 Creating player_season_stats table...")
                self._create_table(conn)
                print("✅ Table created successfully")
                table_created = True

            # Step 3: Create indexes
            print("\n📦 Creating performance indexes...")
            self._create_indexes(conn)
            print("✅ Indexes created successfully")

            # Step 4: Get dynasties and seasons to backfill
            print("\n📦 Analyzing database for backfill requirements...")
            dynasties_seasons = self._get_dynasties_and_seasons(conn)

            if not dynasties_seasons:
                print("⚠️  No game data found to backfill")
                if self.dry_run:
                    conn.rollback()
                else:
                    conn.commit()
                return

            total_dynasties = len(set(d for d, _ in dynasties_seasons))
            total_seasons = len(dynasties_seasons)
            print(f"✅ Found {total_dynasties} dynasties with {total_seasons} seasons")

            # Step 5: Backfill data
            print(f"\n📦 Starting backfill process...")
            self._backfill_season_stats(conn, dynasties_seasons)

            # Step 6: Validate results
            print("\n📦 Validating backfilled data...")
            validation_results = self._validate_backfill(conn, dynasties_seasons)
            self._print_validation_results(validation_results)

            # Step 7: Final statistics
            print("\n📊 Migration Statistics:")
            self._print_final_statistics(conn)

            # Step 8: Commit or rollback
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
        Rollback migration: drop player_season_stats table.

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
            print("COMMIT ROLLBACK MODE - Table will be dropped")
            print("=" * 80)
            print()

        conn = sqlite3.connect(self.db_path)

        try:
            conn.execute("BEGIN TRANSACTION")

            # Check if table exists
            if not self._table_exists(conn, "player_season_stats"):
                print("⚠️  Table 'player_season_stats' does not exist")
                print("    Nothing to rollback")
                conn.rollback()
                return

            # Get count before dropping
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM player_season_stats")
            record_count = cursor.fetchone()[0]

            print(f"📦 Dropping player_season_stats table ({record_count} records)...")

            # Drop indexes first
            indexes = [
                "idx_season_stats_dynasty_season",
                "idx_season_stats_passing_leaders",
                "idx_season_stats_rushing_leaders",
                "idx_season_stats_receiving_leaders",
                "idx_season_stats_player_lookup"
            ]

            for index_name in indexes:
                try:
                    conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                    print(f"  ✅ Dropped index: {index_name}")
                except Exception as e:
                    print(f"  ⚠️  Error dropping index {index_name}: {e}")

            # Drop table
            conn.execute("DROP TABLE player_season_stats")
            print("✅ Table dropped successfully")

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

    def _create_table(self, conn: sqlite3.Connection):
        """Create player_season_stats table."""
        conn.execute('''
            CREATE TABLE player_season_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL,        -- Most recent team
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

    def _create_indexes(self, conn: sqlite3.Connection):
        """Create performance indexes for player_season_stats."""
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

    def _get_dynasties_and_seasons(self, conn: sqlite3.Connection) -> List[Tuple[str, int]]:
        """Get all dynasty/season combinations that have game data."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT g.dynasty_id, g.season
            FROM games g
            WHERE EXISTS (
                SELECT 1 FROM player_game_stats pgs
                WHERE pgs.game_id = g.game_id
                AND pgs.dynasty_id = g.dynasty_id
            )
            ORDER BY g.dynasty_id, g.season
        ''')
        return cursor.fetchall()

    def _backfill_season_stats(self, conn: sqlite3.Connection, dynasties_seasons: List[Tuple[str, int]]):
        """
        Backfill player_season_stats from player_game_stats for all dynasties and seasons.

        Args:
            conn: Database connection
            dynasties_seasons: List of (dynasty_id, season) tuples to process
        """
        total = len(dynasties_seasons)
        processed = 0

        for dynasty_id, season in dynasties_seasons:
            processed += 1
            print(f"\n[{processed}/{total}] Processing dynasty '{dynasty_id}', season {season}...")

            # Aggregate stats for this dynasty/season
            player_stats = self._aggregate_player_stats(conn, dynasty_id, season)

            if not player_stats:
                print(f"  ⚠️  No player stats found")
                continue

            # Insert/update season stats
            inserted, updated = self._upsert_season_stats(conn, player_stats, dynasty_id, season)
            print(f"  ✅ Processed {len(player_stats)} players ({inserted} inserted, {updated} updated)")

    def _aggregate_player_stats(
        self,
        conn: sqlite3.Connection,
        dynasty_id: str,
        season: int
    ) -> List[Dict]:
        """
        Aggregate player stats from player_game_stats for a dynasty/season.

        Returns:
            List of player stat dictionaries
        """
        cursor = conn.cursor()

        # Aggregate stats by player_id (handles duplicate player_ids by summing)
        cursor.execute('''
            SELECT
                dynasty_id,
                player_id,
                player_name,
                MAX(team_id) as team_id,  -- Most recent team
                position,
                ? as season,

                -- Game counts
                COUNT(DISTINCT game_id) as games_played,
                0 as games_started,  -- Not tracked in game stats

                -- Passing
                SUM(passing_attempts) as passing_attempts,
                SUM(passing_completions) as passing_completions,
                SUM(passing_yards) as passing_yards,
                SUM(passing_tds) as passing_tds,
                SUM(passing_interceptions) as passing_interceptions,
                SUM(COALESCE(passing_sacks, 0)) as sacks_taken,

                -- Rushing
                SUM(rushing_attempts) as rushing_attempts,
                SUM(rushing_yards) as rushing_yards,
                SUM(rushing_tds) as rushing_tds,
                MAX(COALESCE(rushing_long, 0)) as rushing_long,
                SUM(COALESCE(rushing_fumbles, 0)) as rushing_fumbles,

                -- Receiving
                SUM(targets) as targets,
                SUM(receptions) as receptions,
                SUM(receiving_yards) as receiving_yards,
                SUM(receiving_tds) as receiving_tds,
                MAX(COALESCE(receiving_long, 0)) as receiving_long,
                SUM(COALESCE(receiving_drops, 0)) as receiving_fumbles,

                -- Defense
                SUM(tackles_total) as tackles_total,
                SUM(COALESCE(tackles_solo, 0)) as tackles_solo,
                SUM(COALESCE(tackles_assist, 0)) as tackles_assists,
                SUM(sacks) as sacks,
                SUM(interceptions) as interceptions,
                SUM(COALESCE(passes_defended, 0)) as passes_defended,
                SUM(COALESCE(forced_fumbles, 0)) as forced_fumbles,
                SUM(COALESCE(fumbles_recovered, 0)) as fumbles_recovered,
                0 as defensive_tds,  -- Not tracked separately

                -- Special teams
                SUM(field_goals_made) as field_goals_made,
                SUM(field_goals_attempted) as field_goals_attempted,
                0 as field_goal_long,  -- Not tracked
                SUM(extra_points_made) as extra_points_made,
                SUM(extra_points_attempted) as extra_points_attempted

            FROM player_game_stats
            WHERE dynasty_id = ? AND game_id IN (
                SELECT game_id FROM games WHERE dynasty_id = ? AND season = ?
            )
            GROUP BY dynasty_id, player_id, player_name, position
        ''', (season, dynasty_id, dynasty_id, season))

        rows = cursor.fetchall()

        # Convert to list of dicts and calculate computed stats
        player_stats = []
        for row in rows:
            stats = dict(row)

            # Calculate computed stats
            self._calculate_computed_stats(stats)

            player_stats.append(stats)

        return player_stats

    def _calculate_computed_stats(self, stats: Dict):
        """Calculate computed statistics in-place."""
        # Passing computed stats
        if stats['passing_attempts'] > 0:
            stats['completion_percentage'] = round(
                (stats['passing_completions'] / stats['passing_attempts']) * 100, 1
            )
            stats['yards_per_attempt'] = round(
                stats['passing_yards'] / stats['passing_attempts'], 1
            )
            stats['passer_rating'] = self._calculate_passer_rating(
                stats['passing_attempts'],
                stats['passing_completions'],
                stats['passing_yards'],
                stats['passing_tds'],
                stats['passing_interceptions']
            )
        else:
            stats['completion_percentage'] = 0.0
            stats['yards_per_attempt'] = 0.0
            stats['passer_rating'] = 0.0

        # Rushing computed stats
        if stats['rushing_attempts'] > 0:
            stats['yards_per_carry'] = round(
                stats['rushing_yards'] / stats['rushing_attempts'], 1
            )
        else:
            stats['yards_per_carry'] = 0.0

        if stats['games_played'] > 0:
            stats['yards_per_game_rushing'] = round(
                stats['rushing_yards'] / stats['games_played'], 1
            )
            stats['yards_per_game_receiving'] = round(
                stats['receiving_yards'] / stats['games_played'], 1
            )
        else:
            stats['yards_per_game_rushing'] = 0.0
            stats['yards_per_game_receiving'] = 0.0

        # Receiving computed stats
        if stats['targets'] > 0:
            stats['catch_rate'] = round(
                (stats['receptions'] / stats['targets']) * 100, 1
            )
            stats['yards_per_target'] = round(
                stats['receiving_yards'] / stats['targets'], 1
            )
        else:
            stats['catch_rate'] = 0.0
            stats['yards_per_target'] = 0.0

        if stats['receptions'] > 0:
            stats['yards_per_reception'] = round(
                stats['receiving_yards'] / stats['receptions'], 1
            )
        else:
            stats['yards_per_reception'] = 0.0

        # Special teams computed stats
        if stats['field_goals_attempted'] > 0:
            stats['field_goal_percentage'] = round(
                (stats['field_goals_made'] / stats['field_goals_attempted']) * 100, 1
            )
        else:
            stats['field_goal_percentage'] = 0.0

        if stats['extra_points_attempted'] > 0:
            stats['extra_point_percentage'] = round(
                (stats['extra_points_made'] / stats['extra_points_attempted']) * 100, 1
            )
        else:
            stats['extra_point_percentage'] = 0.0

    def _calculate_passer_rating(
        self,
        attempts: int,
        completions: int,
        yards: int,
        tds: int,
        ints: int
    ) -> float:
        """Calculate NFL passer rating."""
        if attempts == 0:
            return 0.0

        # Component calculations (NFL formula)
        a = min(max((completions / attempts - 0.3) * 5, 0), 2.375)
        b = min(max((yards / attempts - 3) * 0.25, 0), 2.375)
        c = min(max((tds / attempts) * 20, 0), 2.375)
        d = min(max(2.375 - (ints / attempts) * 25, 0), 2.375)

        rating = ((a + b + c + d) / 6) * 100
        return round(rating, 1)

    def _upsert_season_stats(
        self,
        conn: sqlite3.Connection,
        player_stats: List[Dict],
        dynasty_id: str,
        season: int
    ) -> Tuple[int, int]:
        """
        Insert or update player season stats.

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        cursor = conn.cursor()
        inserted = 0
        updated = 0

        for stats in player_stats:
            # Check if record exists
            cursor.execute('''
                SELECT stat_id FROM player_season_stats
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
            ''', (dynasty_id, stats['player_id'], season))

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute('''
                    UPDATE player_season_stats
                    SET
                        player_name = ?,
                        team_id = ?,
                        position = ?,
                        games_played = ?,
                        games_started = ?,
                        passing_attempts = ?,
                        passing_completions = ?,
                        passing_yards = ?,
                        passing_tds = ?,
                        passing_interceptions = ?,
                        sacks_taken = ?,
                        completion_percentage = ?,
                        yards_per_attempt = ?,
                        passer_rating = ?,
                        rushing_attempts = ?,
                        rushing_yards = ?,
                        rushing_tds = ?,
                        rushing_long = ?,
                        rushing_fumbles = ?,
                        yards_per_carry = ?,
                        yards_per_game_rushing = ?,
                        targets = ?,
                        receptions = ?,
                        receiving_yards = ?,
                        receiving_tds = ?,
                        receiving_long = ?,
                        receiving_fumbles = ?,
                        catch_rate = ?,
                        yards_per_reception = ?,
                        yards_per_target = ?,
                        yards_per_game_receiving = ?,
                        tackles_total = ?,
                        tackles_solo = ?,
                        tackles_assists = ?,
                        sacks = ?,
                        interceptions = ?,
                        passes_defended = ?,
                        forced_fumbles = ?,
                        fumbles_recovered = ?,
                        defensive_tds = ?,
                        field_goals_made = ?,
                        field_goals_attempted = ?,
                        field_goal_long = ?,
                        extra_points_made = ?,
                        extra_points_attempted = ?,
                        field_goal_percentage = ?,
                        extra_point_percentage = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE stat_id = ?
                ''', (
                    stats['player_name'], stats['team_id'], stats['position'],
                    stats['games_played'], stats['games_started'],
                    stats['passing_attempts'], stats['passing_completions'], stats['passing_yards'],
                    stats['passing_tds'], stats['passing_interceptions'], stats['sacks_taken'],
                    stats['completion_percentage'], stats['yards_per_attempt'], stats['passer_rating'],
                    stats['rushing_attempts'], stats['rushing_yards'], stats['rushing_tds'],
                    stats['rushing_long'], stats['rushing_fumbles'],
                    stats['yards_per_carry'], stats['yards_per_game_rushing'],
                    stats['targets'], stats['receptions'], stats['receiving_yards'],
                    stats['receiving_tds'], stats['receiving_long'], stats['receiving_fumbles'],
                    stats['catch_rate'], stats['yards_per_reception'], stats['yards_per_target'],
                    stats['yards_per_game_receiving'],
                    stats['tackles_total'], stats['tackles_solo'], stats['tackles_assists'],
                    stats['sacks'], stats['interceptions'], stats['passes_defended'],
                    stats['forced_fumbles'], stats['fumbles_recovered'], stats['defensive_tds'],
                    stats['field_goals_made'], stats['field_goals_attempted'], stats['field_goal_long'],
                    stats['extra_points_made'], stats['extra_points_attempted'],
                    stats['field_goal_percentage'], stats['extra_point_percentage'],
                    existing[0]
                ))
                updated += 1
            else:
                # Insert new record (49 columns - stat_id is AUTOINCREMENT, last_updated has DEFAULT)
                cursor.execute('''
                    INSERT INTO player_season_stats (
                        dynasty_id, player_id, player_name, team_id, position, season,
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
                        field_goal_percentage, extra_point_percentage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dynasty_id, stats['player_id'], stats['player_name'], stats['team_id'],
                    stats['position'], season,
                    stats['games_played'], stats['games_started'],
                    stats['passing_attempts'], stats['passing_completions'], stats['passing_yards'],
                    stats['passing_tds'], stats['passing_interceptions'], stats['sacks_taken'],
                    stats['completion_percentage'], stats['yards_per_attempt'], stats['passer_rating'],
                    stats['rushing_attempts'], stats['rushing_yards'], stats['rushing_tds'],
                    stats['rushing_long'], stats['rushing_fumbles'],
                    stats['yards_per_carry'], stats['yards_per_game_rushing'],
                    stats['targets'], stats['receptions'], stats['receiving_yards'],
                    stats['receiving_tds'], stats['receiving_long'], stats['receiving_fumbles'],
                    stats['catch_rate'], stats['yards_per_reception'], stats['yards_per_target'],
                    stats['yards_per_game_receiving'],
                    stats['tackles_total'], stats['tackles_solo'], stats['tackles_assists'],
                    stats['sacks'], stats['interceptions'], stats['passes_defended'],
                    stats['forced_fumbles'], stats['fumbles_recovered'], stats['defensive_tds'],
                    stats['field_goals_made'], stats['field_goals_attempted'], stats['field_goal_long'],
                    stats['extra_points_made'], stats['extra_points_attempted'],
                    stats['field_goal_percentage'], stats['extra_point_percentage']
                ))
                inserted += 1

        return inserted, updated

    def _validate_backfill(
        self,
        conn: sqlite3.Connection,
        dynasties_seasons: List[Tuple[str, int]]
    ) -> Dict:
        """
        Validate that season stats match game stats aggregations.

        Returns:
            Dictionary with validation results
        """
        results = {
            'total_validated': 0,
            'mismatches': [],
            'success': True
        }

        cursor = conn.cursor()

        for dynasty_id, season in dynasties_seasons:
            # Sample validation: check passing yards for QBs
            cursor.execute('''
                SELECT
                    pss.player_id,
                    pss.player_name,
                    pss.passing_yards as season_yards,
                    (
                        SELECT SUM(passing_yards)
                        FROM player_game_stats pgs
                        JOIN games g ON pgs.game_id = g.game_id
                        WHERE pgs.dynasty_id = pss.dynasty_id
                        AND pgs.player_id = pss.player_id
                        AND g.season = pss.season
                    ) as game_yards_sum
                FROM player_season_stats pss
                WHERE pss.dynasty_id = ? AND pss.season = ?
                AND pss.passing_yards > 0
            ''', (dynasty_id, season))

            for row in cursor.fetchall():
                results['total_validated'] += 1
                if row['season_yards'] != row['game_yards_sum']:
                    results['success'] = False
                    results['mismatches'].append({
                        'dynasty_id': dynasty_id,
                        'season': season,
                        'player_id': row['player_id'],
                        'player_name': row['player_name'],
                        'season_total': row['season_yards'],
                        'game_sum': row['game_yards_sum']
                    })

        return results

    def _print_validation_results(self, results: Dict):
        """Print validation results."""
        if results['success']:
            print(f"✅ Validation passed ({results['total_validated']} records checked)")
        else:
            print(f"⚠️  Validation found {len(results['mismatches'])} mismatches:")
            for mismatch in results['mismatches'][:5]:  # Show first 5
                print(f"  - {mismatch['player_name']} ({mismatch['dynasty_id']}, {mismatch['season']})")
                print(f"    Season total: {mismatch['season_total']}, Game sum: {mismatch['game_sum']}")

            if len(results['mismatches']) > 5:
                print(f"  ... and {len(results['mismatches']) - 5} more")

    def _print_final_statistics(self, conn: sqlite3.Connection):
        """Print final migration statistics."""
        cursor = conn.cursor()

        # Total records
        cursor.execute("SELECT COUNT(*) FROM player_season_stats")
        total_records = cursor.fetchone()[0]
        print(f"  Total season stat records: {total_records}")

        # Records by dynasty
        cursor.execute('''
            SELECT dynasty_id, COUNT(*) as count
            FROM player_season_stats
            GROUP BY dynasty_id
        ''')
        print(f"\n  Records by dynasty:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]} records")

        # Top passers sample
        cursor.execute('''
            SELECT player_name, team_id, season, passing_yards
            FROM player_season_stats
            WHERE passing_yards > 0
            ORDER BY passing_yards DESC
            LIMIT 5
        ''')
        print(f"\n  Top 5 passing seasons (sample):")
        for row in cursor.fetchall():
            print(f"    {row[0]} (Team {row[1]}, {row[2]}): {row[3]} yards")


def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate player_season_stats table with backfill"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes (default is dry run)"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (drop table)"
    )
    parser.add_argument(
        "--db-path",
        default="data/database/nfl_simulation.db",
        help="Path to database file (default: data/database/nfl_simulation.db)"
    )

    args = parser.parse_args()

    migration = PlayerSeasonStatsMigration(args.db_path)

    if args.rollback:
        migration.down(commit=args.commit)
    else:
        migration.up(commit=args.commit)


if __name__ == "__main__":
    main()
