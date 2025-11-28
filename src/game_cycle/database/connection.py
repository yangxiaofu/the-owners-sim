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
        conn.executescript(schema_sql)
        conn.commit()

        # Run migrations for existing databases
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Run database migrations for existing databases."""
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

    def reset(self) -> None:
        """Reset database to empty state (drop all data, keep schema)."""
        conn = self.get_connection()
        conn.execute("DELETE FROM playoff_bracket")
        conn.execute("DELETE FROM schedule")
        conn.execute("DELETE FROM standings")
        conn.execute("DELETE FROM stage_state")
        # Don't delete teams - they're reference data
        conn.commit()
