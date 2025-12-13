"""Tests for persona-related database schema."""

import os
import pytest
import sqlite3
import tempfile
from src.game_cycle.database.connection import GameCycleDatabase


class TestPlayerPersonasTable:
    """Tests for player_personas table schema."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        yield db, path
        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def db_with_team(self, temp_db):
        """Create database with a team for FK constraint."""
        db, path = temp_db
        conn = db.get_connection()

        # Insert a team first (required for dynasties FK)
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.commit()

        yield db, conn

    def test_table_exists(self, temp_db):
        """player_personas table is created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='player_personas'"
        )
        assert cursor.fetchone() is not None

    def test_required_columns(self, temp_db):
        """player_personas has all required columns."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute("PRAGMA table_info(player_personas)")
        columns = {row[1] for row in cursor.fetchall()}

        expected = {
            "id",
            "dynasty_id",
            "player_id",
            "persona_type",
            "money_importance",
            "winning_importance",
            "location_importance",
            "playing_time_importance",
            "loyalty_importance",
            "market_size_importance",
            "coaching_fit_importance",
            "relationships_importance",
            "birthplace_state",
            "college_state",
            "drafting_team_id",
            "career_earnings",
            "championship_count",
            "pro_bowl_count",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_indexes_exist(self, temp_db):
        """Persona indexes are created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_personas%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_personas_dynasty" in indexes
        assert "idx_personas_player" in indexes

    def test_persona_type_constraint(self, db_with_team):
        """persona_type has CHECK constraint for valid values."""
        db, conn = db_with_team

        # First create a dynasty for FK constraint
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        # Valid value should work
        conn.execute(
            """
            INSERT INTO player_personas (dynasty_id, player_id, persona_type)
            VALUES ('test', 100, 'ring_chaser')
        """
        )
        conn.commit()

        # Invalid value should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO player_personas (dynasty_id, player_id, persona_type)
                VALUES ('test', 101, 'invalid_type')
            """
            )

    def test_importance_range_constraint(self, db_with_team):
        """Importance values have CHECK constraints (0-100)."""
        db, conn = db_with_team

        # Create dynasty for FK
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test Dynasty')
        """
        )
        conn.commit()

        # Invalid importance value (>100) should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO player_personas (dynasty_id, player_id, persona_type, money_importance)
                VALUES ('test', 102, 'money_first', 150)
            """
            )

    def test_unique_dynasty_player_constraint(self, db_with_team):
        """Dynasty + player_id combination must be unique."""
        db, conn = db_with_team

        # Create dynasty for FK
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test Dynasty')
        """
        )

        # Insert first record
        conn.execute(
            """
            INSERT INTO player_personas (dynasty_id, player_id, persona_type)
            VALUES ('test', 100, 'ring_chaser')
        """
        )
        conn.commit()

        # Duplicate should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO player_personas (dynasty_id, player_id, persona_type)
                VALUES ('test', 100, 'money_first')
            """
            )


class TestTeamAttractivenessTable:
    """Tests for team_attractiveness table schema."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        yield db, path
        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def db_with_team(self, temp_db):
        """Create database with a team for FK constraint."""
        db, path = temp_db
        conn = db.get_connection()

        # Insert a team first (required for dynasties FK)
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.commit()

        yield db, conn

    def test_table_exists(self, temp_db):
        """team_attractiveness table is created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='team_attractiveness'"
        )
        assert cursor.fetchone() is not None

    def test_required_columns(self, temp_db):
        """team_attractiveness has all required columns."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute("PRAGMA table_info(team_attractiveness)")
        columns = {row[1] for row in cursor.fetchall()}

        expected = {
            "id",
            "dynasty_id",
            "team_id",
            "season",
            "playoff_appearances_5yr",
            "super_bowl_wins_5yr",
            "winning_culture_score",
            "coaching_prestige",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_indexes_exist(self, temp_db):
        """Team attractiveness indexes are created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_attractiveness%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_attractiveness_dynasty" in indexes
        assert "idx_attractiveness_team_season" in indexes

    def test_unique_dynasty_team_season(self, db_with_team):
        """Dynasty + team_id + season combination must be unique."""
        db, conn = db_with_team

        # Create dynasty for FK
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test Dynasty')
        """
        )

        # Insert first record
        conn.execute(
            """
            INSERT INTO team_attractiveness (dynasty_id, team_id, season)
            VALUES ('test', 10, 2025)
        """
        )
        conn.commit()

        # Duplicate should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO team_attractiveness (dynasty_id, team_id, season)
                VALUES ('test', 10, 2025)
            """
            )


class TestTeamSeasonHistoryTable:
    """Tests for team_season_history table schema."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = GameCycleDatabase(path)
        yield db, path
        db.close()
        try:
            os.unlink(path)
        except OSError:
            pass

    @pytest.fixture
    def db_with_teams(self, temp_db):
        """Create database with multiple teams for FK constraint."""
        db, path = temp_db
        conn = db.get_connection()

        # Insert teams (required for dynasties FK and team_season_history)
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (10, 'Dallas Cowboys', 'DAL', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (11, 'New York Giants', 'NYG', 'NFC', 'East')
        """
        )
        conn.execute(
            """
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (12, 'Philadelphia Eagles', 'PHI', 'NFC', 'East')
        """
        )
        conn.commit()

        yield db, conn

    def test_table_exists(self, temp_db):
        """team_season_history table is created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='team_season_history'"
        )
        assert cursor.fetchone() is not None

    def test_required_columns(self, temp_db):
        """team_season_history has all required columns."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute("PRAGMA table_info(team_season_history)")
        columns = {row[1] for row in cursor.fetchall()}

        expected = {
            "id",
            "dynasty_id",
            "team_id",
            "season",
            "wins",
            "losses",
            "made_playoffs",
            "playoff_round_reached",
            "won_super_bowl",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_indexes_exist(self, temp_db):
        """Team history indexes are created."""
        db, _ = temp_db
        conn = db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_team_history%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_team_history_dynasty" in indexes
        assert "idx_team_history_team" in indexes

    def test_playoff_round_constraint(self, db_with_teams):
        """playoff_round_reached has CHECK constraint for valid values."""
        db, conn = db_with_teams

        # First create a dynasty for FK constraint
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test')
        """
        )
        conn.commit()

        # Valid value should work
        conn.execute(
            """
            INSERT INTO team_season_history
            (dynasty_id, team_id, season, wins, losses, playoff_round_reached)
            VALUES ('test', 10, 2025, 12, 5, 'divisional')
        """
        )
        conn.commit()

        # NULL is also valid (didn't make playoffs)
        conn.execute(
            """
            INSERT INTO team_season_history
            (dynasty_id, team_id, season, wins, losses, playoff_round_reached)
            VALUES ('test', 11, 2025, 5, 12, NULL)
        """
        )
        conn.commit()

        # Invalid value should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO team_season_history
                (dynasty_id, team_id, season, wins, losses, playoff_round_reached)
                VALUES ('test', 12, 2025, 10, 7, 'invalid_round')
            """
            )

    def test_team_id_constraint(self, db_with_teams):
        """team_id must be 1-32."""
        db, conn = db_with_teams

        # Create dynasty for FK
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test')
        """
        )
        conn.commit()

        # Invalid team_id should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO team_season_history
                (dynasty_id, team_id, season, wins, losses)
                VALUES ('test', 50, 2025, 10, 7)
            """
            )

    def test_unique_dynasty_team_season(self, db_with_teams):
        """Dynasty + team_id + season combination must be unique."""
        db, conn = db_with_teams

        # Create dynasty for FK
        conn.execute(
            """
            INSERT INTO dynasties (dynasty_id, team_id, name)
            VALUES ('test', 10, 'Test')
        """
        )

        # Insert first record
        conn.execute(
            """
            INSERT INTO team_season_history
            (dynasty_id, team_id, season, wins, losses)
            VALUES ('test', 10, 2025, 12, 5)
        """
        )
        conn.commit()

        # Duplicate should fail
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO team_season_history
                (dynasty_id, team_id, season, wins, losses)
                VALUES ('test', 10, 2025, 13, 4)
            """
            )