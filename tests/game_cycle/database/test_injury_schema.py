"""Tests for injury database schema."""

import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.connection import GameCycleDatabase


class TestInjurySchema:
    """Test injury tables are created correctly."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass  # File may already be deleted

    @pytest.fixture
    def db_with_team(self, temp_db):
        """Create database with a team for FK constraint."""
        db = GameCycleDatabase(temp_db)
        conn = db.get_connection()

        # Insert a team first (required for dynasties FK)
        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (22, 'Detroit Lions', 'DET', 'NFC', 'North')
        """)
        conn.commit()

        yield db, conn

        db.close()

    def test_player_injuries_table_created(self, temp_db):
        """player_injuries table is created."""
        db = GameCycleDatabase(temp_db)
        assert db.table_exists('player_injuries')
        db.close()

    def test_ir_tracking_table_created(self, temp_db):
        """ir_tracking table is created."""
        db = GameCycleDatabase(temp_db)
        assert db.table_exists('ir_tracking')
        db.close()

    def test_player_injuries_columns(self, temp_db):
        """player_injuries has all required columns."""
        db = GameCycleDatabase(temp_db)
        conn = db.get_connection()

        cursor = conn.execute("PRAGMA table_info(player_injuries)")
        columns = {row[1] for row in cursor.fetchall()}

        expected_columns = {
            'injury_id', 'dynasty_id', 'player_id', 'season',
            'week_occurred', 'injury_type', 'body_part', 'severity',
            'estimated_weeks_out', 'actual_weeks_out', 'occurred_during',
            'game_id', 'play_description', 'is_active',
            'ir_placement_date', 'ir_return_date', 'created_at'
        }

        assert expected_columns.issubset(columns)
        db.close()

    def test_ir_tracking_columns(self, temp_db):
        """ir_tracking has all required columns."""
        db = GameCycleDatabase(temp_db)
        conn = db.get_connection()

        cursor = conn.execute("PRAGMA table_info(ir_tracking)")
        columns = {row[1] for row in cursor.fetchall()}

        expected_columns = {
            'id', 'dynasty_id', 'team_id', 'season', 'ir_return_slots_used'
        }

        assert expected_columns.issubset(columns)
        db.close()

    def test_can_insert_injury(self, db_with_team):
        """Can insert injury record."""
        db, conn = db_with_team

        # Create dynasty (team already exists)
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        # Insert injury
        conn.execute("""
            INSERT INTO player_injuries (
                dynasty_id, player_id, season, week_occurred,
                injury_type, body_part, severity,
                estimated_weeks_out, occurred_during
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('test', 100, 2025, 5, 'ankle_sprain', 'ankle', 'minor', 2, 'game'))

        conn.commit()

        # Verify
        result = db.query_one(
            "SELECT * FROM player_injuries WHERE player_id = ?",
            (100,)
        )
        assert result is not None
        assert result['injury_type'] == 'ankle_sprain'
        assert result['severity'] == 'minor'
        assert result['is_active'] == 1

    def test_can_insert_ir_tracking(self, db_with_team):
        """Can insert IR tracking record."""
        db, conn = db_with_team

        # Create dynasty (team already exists)
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        # Insert IR tracking
        conn.execute("""
            INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
            VALUES (?, ?, ?, ?)
        """, ('test', 22, 2025, 3))

        conn.commit()

        # Verify
        result = db.query_one(
            "SELECT * FROM ir_tracking WHERE dynasty_id = ? AND team_id = ?",
            ('test', 22)
        )
        assert result is not None
        assert result['ir_return_slots_used'] == 3

    def test_ir_tracking_unique_constraint(self, db_with_team):
        """IR tracking enforces unique dynasty/team/season."""
        db, conn = db_with_team

        # Create dynasty (team already exists)
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        # Insert first record
        conn.execute("""
            INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
            VALUES (?, ?, ?, ?)
        """, ('test', 22, 2025, 0))
        conn.commit()

        # Try duplicate - should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
                VALUES (?, ?, ?, ?)
            """, ('test', 22, 2025, 1))

    def test_injury_indexes_exist(self, temp_db):
        """Injury indexes are created."""
        db = GameCycleDatabase(temp_db)
        conn = db.get_connection()

        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_injuries%'
        """)
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            'idx_injuries_dynasty',
            'idx_injuries_player',
            'idx_injuries_active',
            'idx_injuries_season_week',
        }

        assert expected_indexes.issubset(indexes)
        db.close()

    def test_foreign_key_constraint(self, temp_db):
        """Foreign key to dynasties is enforced."""
        db = GameCycleDatabase(temp_db)
        conn = db.get_connection()

        # Try to insert injury without dynasty - should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO player_injuries (
                    dynasty_id, player_id, season, week_occurred,
                    injury_type, body_part, severity,
                    estimated_weeks_out, occurred_during
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ('nonexistent', 100, 2025, 5, 'ankle_sprain', 'ankle', 'minor', 2, 'game'))

        db.close()
