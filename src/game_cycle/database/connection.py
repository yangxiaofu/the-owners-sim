"""
Database connection for game_cycle.

Provides a lightweight SQLite connection with schema management.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any


class GameCycleDatabase:
    """
    Database connection manager for the game cycle system.

    Handles:
    - Connection management
    - Schema initialization
    - Basic query utilities
    """

    DEFAULT_PATH = "data/database/game_cycle/game_cycle.db"

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connection.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        self.db_path = db_path or self.DEFAULT_PATH
        self._ensure_directory()
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _ensure_schema(self) -> None:
        """Apply database schema if tables don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        conn = self.get_connection()

        # Run migrations BEFORE schema to add missing columns
        # (schema has indexes that depend on these columns existing)
        self._run_pre_schema_migrations()

        conn.executescript(schema_sql)
        conn.commit()

        # Run migrations for existing databases (post-schema)
        self._run_migrations()

    def _run_pre_schema_migrations(self) -> None:
        """
        Run migrations that MUST complete before schema.sql is applied.

        These migrations add columns that schema.sql indexes depend on.
        Without these columns existing first, CREATE INDEX statements will fail.
        """
        conn = self.get_connection()

        # Pre-migration 1: Add is_completed to draft_order if missing
        # Required because schema.sql has: CREATE INDEX idx_draft_order_pending ON draft_order(..., is_completed)
        try:
            cursor = conn.execute("PRAGMA table_info(draft_order)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and 'is_completed' not in columns:
                conn.execute("ALTER TABLE draft_order ADD COLUMN is_completed BOOLEAN DEFAULT FALSE")
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet (new database)

        # Pre-migration 2: Upgrade playoff_bracket schema to include dynasty_id and season
        # Old schema had no dynasty/season isolation - drop and recreate with new schema
        # Playoff data is transient (regenerated each season), safe to lose
        try:
            cursor = conn.execute("PRAGMA table_info(playoff_bracket)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and 'dynasty_id' not in columns:
                # Old schema detected - drop table so schema.sql can recreate with new columns
                conn.execute("DROP TABLE IF EXISTS playoff_bracket")
                conn.commit()
                print("[GameCycleDatabase] Migrated playoff_bracket table to new schema with dynasty/season isolation")
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet (new database)

        # Pre-migration 3: Upgrade standings schema to include dynasty_id and season
        # Old schema had no dynasty/season isolation - drop and recreate with new schema
        # Standings data is regenerated each season, safe to lose
        try:
            cursor = conn.execute("PRAGMA table_info(standings)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and 'dynasty_id' not in columns:
                # Old schema detected - drop table so schema.sql can recreate with new columns
                conn.execute("DROP TABLE IF EXISTS standings")
                conn.commit()
                print("[GameCycleDatabase] Migrated standings table to new schema with dynasty/season isolation")
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet (new database)

    def _run_migrations(self) -> None:
        """Run database migrations for existing databases (post-schema)."""
        conn = self.get_connection()

        # Migration 1: Add roster_player_id to draft_prospects if missing
        try:
            cursor = conn.execute("PRAGMA table_info(draft_prospects)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'roster_player_id' not in columns:
                conn.execute("ALTER TABLE draft_prospects ADD COLUMN roster_player_id INTEGER")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_prospects_roster_player_id ON draft_prospects(roster_player_id)")
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet (new database)

        # Migration 2: Ensure player_progression_history table exists
        # (Added later in schema.sql, older databases may be missing it)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_progression_history'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS player_progression_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        season INTEGER NOT NULL,
                        age INTEGER NOT NULL,
                        position TEXT,
                        team_id INTEGER,
                        age_category TEXT,
                        overall_before INTEGER NOT NULL,
                        overall_after INTEGER NOT NULL,
                        overall_change INTEGER NOT NULL,
                        attribute_changes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(dynasty_id, player_id, season)
                    );
                    CREATE INDEX IF NOT EXISTS idx_progression_dynasty ON player_progression_history(dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_progression_player ON player_progression_history(player_id);
                    CREATE INDEX IF NOT EXISTS idx_progression_season ON player_progression_history(season);
                    CREATE INDEX IF NOT EXISTS idx_progression_player_season ON player_progression_history(player_id, season);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 3: Add player_injuries table for injury system
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_injuries'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS player_injuries (
                        injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        season INTEGER NOT NULL,
                        week_occurred INTEGER NOT NULL,
                        injury_type TEXT NOT NULL,
                        body_part TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        estimated_weeks_out INTEGER NOT NULL,
                        actual_weeks_out INTEGER,
                        occurred_during TEXT NOT NULL,
                        game_id TEXT,
                        play_description TEXT,
                        is_active INTEGER DEFAULT 1,
                        ir_placement_date TEXT,
                        ir_return_date TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_injuries_dynasty ON player_injuries(dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_injuries_player ON player_injuries(dynasty_id, player_id);
                    CREATE INDEX IF NOT EXISTS idx_injuries_active ON player_injuries(dynasty_id, is_active);
                    CREATE INDEX IF NOT EXISTS idx_injuries_season_week ON player_injuries(dynasty_id, season, week_occurred);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 4: Add ir_tracking table
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ir_tracking'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS ir_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
                        season INTEGER NOT NULL,
                        ir_return_slots_used INTEGER DEFAULT 0,
                        UNIQUE(dynasty_id, team_id, season),
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_ir_tracking_team ON ir_tracking(dynasty_id, team_id, season);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 5: Add durability attribute to existing players
        self._migrate_durability_attribute(conn)

        # Migration 5b: Create player_game_stats table if missing
        # CRITICAL: Required for awards calculation (aggregate_season_grades_from_stats)
        # This table was missing from schema.sql but is used by UnifiedDatabaseAPI.stats_insert_game_stats()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_game_stats'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS player_game_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        game_id TEXT NOT NULL,
                        season_type TEXT NOT NULL DEFAULT 'regular_season',
                        player_id TEXT NOT NULL,
                        player_name TEXT,
                        team_id INTEGER NOT NULL,
                        position TEXT,
                        passing_yards INTEGER DEFAULT 0,
                        passing_tds INTEGER DEFAULT 0,
                        passing_attempts INTEGER DEFAULT 0,
                        passing_completions INTEGER DEFAULT 0,
                        passing_interceptions INTEGER DEFAULT 0,
                        passing_sacks INTEGER DEFAULT 0,
                        passing_sack_yards INTEGER DEFAULT 0,
                        passing_rating REAL DEFAULT 0,
                        air_yards INTEGER DEFAULT 0,
                        rushing_yards INTEGER DEFAULT 0,
                        rushing_tds INTEGER DEFAULT 0,
                        rushing_attempts INTEGER DEFAULT 0,
                        rushing_long INTEGER DEFAULT 0,
                        rushing_fumbles INTEGER DEFAULT 0,
                        receiving_yards INTEGER DEFAULT 0,
                        receiving_tds INTEGER DEFAULT 0,
                        receptions INTEGER DEFAULT 0,
                        targets INTEGER DEFAULT 0,
                        receiving_long INTEGER DEFAULT 0,
                        receiving_drops INTEGER DEFAULT 0,
                        yards_after_catch INTEGER DEFAULT 0,
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
                        field_goals_made INTEGER DEFAULT 0,
                        field_goals_attempted INTEGER DEFAULT 0,
                        extra_points_made INTEGER DEFAULT 0,
                        extra_points_attempted INTEGER DEFAULT 0,
                        punts INTEGER DEFAULT 0,
                        punt_yards INTEGER DEFAULT 0,
                        pancakes INTEGER DEFAULT 0,
                        sacks_allowed INTEGER DEFAULT 0,
                        hurries_allowed INTEGER DEFAULT 0,
                        pressures_allowed INTEGER DEFAULT 0,
                        pass_blocks INTEGER DEFAULT 0,
                        run_blocking_grade REAL DEFAULT 0.0,
                        pass_blocking_efficiency REAL DEFAULT 0.0,
                        missed_assignments INTEGER DEFAULT 0,
                        holding_penalties INTEGER DEFAULT 0,
                        false_start_penalties INTEGER DEFAULT 0,
                        downfield_blocks INTEGER DEFAULT 0,
                        double_team_blocks INTEGER DEFAULT 0,
                        chip_blocks INTEGER DEFAULT 0,
                        snap_counts_offense INTEGER DEFAULT 0,
                        snap_counts_defense INTEGER DEFAULT 0,
                        snap_counts_special_teams INTEGER DEFAULT 0,
                        fantasy_points REAL DEFAULT 0,
                        UNIQUE(dynasty_id, game_id, player_id, season_type),
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_player_stats_dynasty ON player_game_stats(dynasty_id, game_id);
                    CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id, dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_player_stats_team_game ON player_game_stats(dynasty_id, team_id, game_id);
                    CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_game_stats(dynasty_id, team_id);
                    CREATE INDEX IF NOT EXISTS idx_player_stats_season_type ON player_game_stats(dynasty_id, season_type);
                ''')
                conn.commit()
                print("[Migration 5b] Created player_game_stats table")
        except sqlite3.OperationalError as e:
            print(f"[Migration 5b] Skipped: {e}")

        # Migration 6: Add pass_blocks column to player_game_stats if missing
        # Required because INSERT statement includes this column
        self._migrate_pass_blocks_column(conn)

        # Migration 7: Add player_personas table (Milestone 6)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_personas'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS player_personas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        persona_type TEXT NOT NULL CHECK(persona_type IN (
                            'ring_chaser', 'hometown_hero', 'money_first', 'big_market',
                            'small_market', 'legacy_builder', 'competitor', 'system_fit'
                        )),
                        money_importance INTEGER DEFAULT 50,
                        winning_importance INTEGER DEFAULT 50,
                        location_importance INTEGER DEFAULT 50,
                        playing_time_importance INTEGER DEFAULT 50,
                        loyalty_importance INTEGER DEFAULT 50,
                        market_size_importance INTEGER DEFAULT 50,
                        coaching_fit_importance INTEGER DEFAULT 50,
                        relationships_importance INTEGER DEFAULT 50,
                        birthplace_state TEXT,
                        college_state TEXT,
                        drafting_team_id INTEGER,
                        career_earnings INTEGER DEFAULT 0,
                        championship_count INTEGER DEFAULT 0,
                        pro_bowl_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                        UNIQUE(dynasty_id, player_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_personas_dynasty ON player_personas(dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_personas_player ON player_personas(dynasty_id, player_id);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 8: Add team_attractiveness table (Milestone 6)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='team_attractiveness'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS team_attractiveness (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
                        season INTEGER NOT NULL,
                        playoff_appearances_5yr INTEGER DEFAULT 0,
                        super_bowl_wins_5yr INTEGER DEFAULT 0,
                        winning_culture_score INTEGER DEFAULT 50,
                        coaching_prestige INTEGER DEFAULT 50,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                        UNIQUE(dynasty_id, team_id, season)
                    );
                    CREATE INDEX IF NOT EXISTS idx_attractiveness_dynasty ON team_attractiveness(dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_attractiveness_team_season ON team_attractiveness(dynasty_id, team_id, season);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 9: Add team_season_history table (Milestone 6)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='team_season_history'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS team_season_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
                        season INTEGER NOT NULL,
                        wins INTEGER NOT NULL,
                        losses INTEGER NOT NULL,
                        made_playoffs INTEGER DEFAULT 0,
                        playoff_round_reached TEXT,
                        won_super_bowl INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                        UNIQUE(dynasty_id, team_id, season)
                    );
                    CREATE INDEX IF NOT EXISTS idx_team_history_dynasty ON team_season_history(dynasty_id);
                    CREATE INDEX IF NOT EXISTS idx_team_history_team ON team_season_history(dynasty_id, team_id, season);
                ''')
                conn.commit()
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 10: Add award_race_tracking table (Milestone 10)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='award_race_tracking'"
            )
            if cursor.fetchone() is None:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS award_race_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dynasty_id TEXT NOT NULL,
                        season INTEGER NOT NULL,
                        week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 18),
                        award_type TEXT NOT NULL CHECK(award_type IN ('mvp', 'opoy', 'dpoy', 'oroy', 'droy')),
                        player_id INTEGER NOT NULL,
                        team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
                        position TEXT NOT NULL,
                        cumulative_score REAL NOT NULL,
                        week_score REAL,
                        rank INTEGER NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                        UNIQUE(dynasty_id, season, week, award_type, player_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_award_race_dynasty_season ON award_race_tracking(dynasty_id, season);
                    CREATE INDEX IF NOT EXISTS idx_award_race_latest ON award_race_tracking(dynasty_id, season, week DESC);
                    CREATE INDEX IF NOT EXISTS idx_award_race_award_type ON award_race_tracking(dynasty_id, season, award_type);
                    CREATE INDEX IF NOT EXISTS idx_award_race_player ON award_race_tracking(dynasty_id, player_id);
                ''')
                conn.commit()
                print("[Migration 10] Added award_race_tracking table")
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 11: Add missing player_game_stats columns
        try:
            cursor = conn.execute("PRAGMA table_info(player_game_stats)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            new_columns = [
                ("air_yards", "INTEGER DEFAULT 0"),
                ("yards_after_catch", "INTEGER DEFAULT 0"),
                ("tackles_for_loss", "INTEGER DEFAULT 0"),
                ("qb_hits", "INTEGER DEFAULT 0"),
                ("qb_pressures", "INTEGER DEFAULT 0"),
                ("false_start_penalties", "INTEGER DEFAULT 0"),
                ("downfield_blocks", "INTEGER DEFAULT 0"),
                ("double_team_blocks", "INTEGER DEFAULT 0"),
                ("chip_blocks", "INTEGER DEFAULT 0"),
                ("snap_counts_offense", "INTEGER DEFAULT 0"),
                ("snap_counts_defense", "INTEGER DEFAULT 0"),
                ("snap_counts_special_teams", "INTEGER DEFAULT 0"),
                ("fantasy_points", "REAL DEFAULT 0"),
            ]

            added = 0
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE player_game_stats ADD COLUMN {col_name} {col_type}")
                    added += 1

            if added > 0:
                conn.commit()
                print(f"[Migration 11] Added {added} columns to player_game_stats")
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

        # Migration 12: Add PFF-critical stats columns for accurate position grading
        try:
            cursor = conn.execute("PRAGMA table_info(player_game_stats)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            pff_columns = [
                # Ball carrier stats (RB/WR grading)
                ("yards_after_contact", "INTEGER DEFAULT 0"),
                # QB advanced stats
                ("pressures_faced", "INTEGER DEFAULT 0"),
                # Tackling stats
                ("missed_tackles", "INTEGER DEFAULT 0"),
            ]

            added = 0
            for col_name, col_type in pff_columns:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE player_game_stats ADD COLUMN {col_name} {col_type}")
                    added += 1

            if added > 0:
                conn.commit()
                print(f"[Migration 12] Added {added} PFF stats columns to player_game_stats")
        except sqlite3.OperationalError:
            pass  # Ignore errors during migration

    def _migrate_pass_blocks_column(self, conn: sqlite3.Connection) -> None:
        """Add pass_blocks column to player_game_stats if missing."""
        try:
            cursor = conn.execute("PRAGMA table_info(player_game_stats)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and 'pass_blocks' not in columns:
                conn.execute("ALTER TABLE player_game_stats ADD COLUMN pass_blocks INTEGER DEFAULT 0")
                conn.commit()
                print("[Migration] Added pass_blocks column to player_game_stats")
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet or other error

    def _migrate_durability_attribute(self, conn: sqlite3.Connection) -> None:
        """Add durability attribute to existing players who don't have it."""
        import json
        import random

        try:
            # Check if any players exist and need durability
            cursor = conn.execute("SELECT id, attributes, positions FROM players LIMIT 1")
            row = cursor.fetchone()
            if row is None:
                return  # No players exist

            attrs = json.loads(row['attributes']) if row['attributes'] else {}
            if 'durability' in attrs:
                return  # Already has durability

            # Add durability to all existing players
            cursor = conn.execute("SELECT id, attributes, positions FROM players")
            updates = []
            for player_row in cursor.fetchall():
                player_id = player_row['id']
                attrs = json.loads(player_row['attributes']) if player_row['attributes'] else {}
                positions = json.loads(player_row['positions']) if player_row['positions'] else []

                # Generate durability based on position
                position = positions[0] if positions else 'unknown'
                durability = self._generate_durability_for_position(position, random)
                attrs['durability'] = durability

                updates.append((json.dumps(attrs), player_id))

            if updates:
                conn.executemany(
                    "UPDATE players SET attributes = ? WHERE id = ?",
                    updates
                )
                conn.commit()
        except (sqlite3.OperationalError, json.JSONDecodeError):
            pass  # Ignore errors during migration

    @staticmethod
    def _generate_durability_for_position(position: str, random_module) -> int:
        """
        Generate durability rating based on position.

        Args:
            position: Player position string
            random_module: Random module for generating values

        Returns:
            Durability rating (60-95 range)
        """
        position_lower = position.lower()

        # Position-based durability ranges
        # RBs take most hits, OL most durable, specialists very durable
        durability_ranges = {
            # Running backs - most injury prone (60-75)
            'running_back': (60, 75),
            'rb': (60, 75),
            'halfback': (60, 75),
            'hb': (60, 75),
            'fullback': (65, 78),
            'fb': (65, 78),

            # Wide receivers/Tight ends - vulnerable (65-80)
            'wide_receiver': (65, 80),
            'wr': (65, 80),
            'tight_end': (65, 80),
            'te': (65, 80),

            # Quarterbacks - moderately protected (70-85)
            'quarterback': (70, 85),
            'qb': (70, 85),

            # Linebackers/DBs - moderate risk (65-82)
            'linebacker': (65, 80),
            'lb': (65, 80),
            'mlb': (65, 80),
            'olb': (65, 80),
            'ilb': (65, 80),
            'lolb': (65, 80),
            'rolb': (65, 80),
            'cornerback': (65, 80),
            'cb': (65, 80),
            'safety': (68, 82),
            'fs': (68, 82),
            'ss': (68, 82),
            's': (68, 82),

            # Defensive line - moderate durability (68-85)
            'defensive_end': (68, 82),
            'de': (68, 82),
            'le': (68, 82),
            're': (68, 82),
            'edge': (68, 82),
            'defensive_tackle': (70, 85),
            'dt': (70, 85),
            'nose_tackle': (70, 85),
            'nt': (70, 85),

            # Offensive line - most durable (72-88)
            'offensive_line': (72, 88),
            'center': (72, 88),
            'c': (72, 88),
            'guard': (72, 88),
            'lg': (72, 88),
            'rg': (72, 88),
            'tackle': (72, 88),
            'lt': (72, 88),
            'rt': (72, 88),
            'offensive_tackle': (72, 88),
            'ot': (72, 88),

            # Specialists - very durable (80-95)
            'kicker': (80, 95),
            'k': (80, 95),
            'punter': (80, 95),
            'p': (80, 95),
            'long_snapper': (80, 95),
            'ls': (80, 95),
            'kick_returner': (65, 80),
            'kr': (65, 80),
            'punt_returner': (65, 80),
            'pr': (65, 80),
        }

        min_dur, max_dur = durability_ranges.get(position_lower, (70, 85))
        return random_module.randint(min_dur, max_dur)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get database connection (creates if needed).

        Returns:
            SQLite connection with row factory set.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency (multiple readers, one writer)
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute SQL and return cursor.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Cursor with results
        """
        conn = self.get_connection()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor

    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        Execute SQL for multiple parameter sets.

        Args:
            sql: SQL statement with placeholders
            params_list: List of parameter tuples

        Returns:
            Cursor
        """
        conn = self.get_connection()
        cursor = conn.executemany(sql, params_list)
        conn.commit()
        return cursor

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute query and return single row.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Single row or None
        """
        cursor = self.get_connection().execute(sql, params)
        return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Execute query and return all rows.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of rows
        """
        cursor = self.get_connection().execute(sql, params)
        return cursor.fetchall()

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.query_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return result is not None

    def row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        result = self.query_one(f"SELECT COUNT(*) as count FROM {table_name}")
        return result['count'] if result else 0

    def __enter__(self) -> "GameCycleDatabase":
        """
        Context manager entry.

        Returns:
            Self for use with 'with' statements.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Context manager exit.

        Commits pending changes and closes connection.
        Does NOT re-raise exceptions.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised

        Returns:
            False to re-raise any exception
        """
        if self._connection:
            if exc_type is None:
                # No exception, commit
                self._connection.commit()
            self.close()
        return False

    def commit(self) -> None:
        """Commit pending changes."""
        if self._connection:
            self._connection.commit()

    def reset(self) -> None:
        """Reset database to empty state (drop all data, keep schema)."""
        conn = self.get_connection()
        conn.execute("DELETE FROM playoff_bracket")
        conn.execute("DELETE FROM schedule")
        conn.execute("DELETE FROM standings")
        conn.execute("DELETE FROM stage_state")
        # Don't delete teams - they're reference data
        conn.commit()
