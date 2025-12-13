"""Tests for box score timeout field persistence."""

import pytest
import sqlite3
import tempfile
import os
from src.game_cycle.database.box_scores_api import BoxScoresAPI, BoxScore


@pytest.fixture
def test_db():
    """Create test database with timeout fields."""
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        with sqlite3.connect(db_path) as conn:
            # Create dynasties
            conn.execute("""
                CREATE TABLE dynasties (
                    dynasty_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    team_id INTEGER NOT NULL,
                    season_year INTEGER NOT NULL DEFAULT 2025,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create games
            conn.execute("""
                CREATE TABLE games (
                    game_id TEXT PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    week INTEGER NOT NULL,
                    home_team_id INTEGER NOT NULL,
                    away_team_id INTEGER NOT NULL,
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
                )
            """)

            # Create box_scores WITH timeout fields
            conn.execute("""
                CREATE TABLE box_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    team_id INTEGER NOT NULL,
                    q1_score INTEGER DEFAULT 0,
                    q2_score INTEGER DEFAULT 0,
                    q3_score INTEGER DEFAULT 0,
                    q4_score INTEGER DEFAULT 0,
                    ot_score INTEGER DEFAULT 0,
                    first_downs INTEGER DEFAULT 0,
                    third_down_att INTEGER DEFAULT 0,
                    third_down_conv INTEGER DEFAULT 0,
                    fourth_down_att INTEGER DEFAULT 0,
                    fourth_down_conv INTEGER DEFAULT 0,
                    total_yards INTEGER DEFAULT 0,
                    passing_yards INTEGER DEFAULT 0,
                    rushing_yards INTEGER DEFAULT 0,
                    turnovers INTEGER DEFAULT 0,
                    penalties INTEGER DEFAULT 0,
                    penalty_yards INTEGER DEFAULT 0,
                    time_of_possession INTEGER,
                    team_timeouts_remaining INTEGER DEFAULT 3,
                    team_timeouts_used_h1 INTEGER DEFAULT 0,
                    team_timeouts_used_h2 INTEGER DEFAULT 0,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                    FOREIGN KEY (game_id) REFERENCES games(game_id),
                    UNIQUE(game_id, team_id)
                )
            """)

            # Insert test data
            conn.execute(
                "INSERT INTO dynasties VALUES (?, ?, ?, ?, datetime('now'))",
                ("test_dynasty", "Test Dynasty", 1, 2025)
            )

            conn.execute("""
                INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("game1", "test_dynasty", 2025, 1, 1, 2, 24, 17))

            conn.commit()

        yield db_path

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def api(test_db):
    """Create BoxScoresAPI."""
    return BoxScoresAPI(test_db)


class TestBoxScoreTimeouts:
    """Test box score timeout field persistence."""

    def test_insert_with_timeout_data(self, api):
        """Test inserting box score with timeout data."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            q1_score=7,
            team_timeouts_remaining=1,
            team_timeouts_used_h1=2,
            team_timeouts_used_h2=0
        )

        result = api.insert_box_score(box)
        assert result is True

    def test_retrieve_timeout_data(self, api):
        """Test retrieving box score with timeout data."""
        # Insert
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=2,
            team_timeouts_used_h1=1,
            team_timeouts_used_h2=0
        )
        api.insert_box_score(box)

        # Retrieve
        retrieved = api.get_box_score("test_dynasty", "game1", 1)

        assert retrieved is not None
        assert retrieved.team_timeouts_remaining == 2
        assert retrieved.team_timeouts_used_h1 == 1
        assert retrieved.team_timeouts_used_h2 == 0

    def test_default_timeout_values(self, api):
        """Test default timeout values when not specified."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty"
        )
        api.insert_box_score(box)

        retrieved = api.get_box_score("test_dynasty", "game1", 1)

        assert retrieved.team_timeouts_remaining == 3
        assert retrieved.team_timeouts_used_h1 == 0
        assert retrieved.team_timeouts_used_h2 == 0

    def test_update_timeout_data(self, api):
        """Test updating timeout data via INSERT OR REPLACE."""
        # Initial
        box1 = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=3
        )
        api.insert_box_score(box1)

        # Update
        box2 = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=0,
            team_timeouts_used_h1=2,
            team_timeouts_used_h2=1
        )
        api.insert_box_score(box2)

        # Verify
        retrieved = api.get_box_score("test_dynasty", "game1", 1)
        assert retrieved.team_timeouts_remaining == 0
        assert retrieved.team_timeouts_used_h1 == 2
        assert retrieved.team_timeouts_used_h2 == 1

    def test_timeout_data_with_full_game_stats(self, api):
        """Test timeout data persists alongside full box score stats."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            q1_score=7,
            q2_score=10,
            q3_score=0,
            q4_score=7,
            first_downs=18,
            total_yards=345,
            passing_yards=220,
            rushing_yards=125,
            turnovers=1,
            team_timeouts_remaining=1,
            team_timeouts_used_h1=1,
            team_timeouts_used_h2=1
        )
        api.insert_box_score(box)

        retrieved = api.get_box_score("test_dynasty", "game1", 1)

        # Verify stats
        assert retrieved.total_score == 24
        assert retrieved.total_yards == 345
        # Verify timeouts
        assert retrieved.team_timeouts_remaining == 1
        assert retrieved.team_timeouts_used_h1 == 1
        assert retrieved.team_timeouts_used_h2 == 1

    def test_timeout_values_within_valid_range(self, api):
        """Test that timeout values are within valid NFL range (0-3)."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=0,
            team_timeouts_used_h1=3,
            team_timeouts_used_h2=3
        )
        api.insert_box_score(box)

        retrieved = api.get_box_score("test_dynasty", "game1", 1)

        assert 0 <= retrieved.team_timeouts_remaining <= 3
        assert 0 <= retrieved.team_timeouts_used_h1 <= 3
        assert 0 <= retrieved.team_timeouts_used_h2 <= 3

    def test_timeout_data_for_both_teams(self, api):
        """Test timeout data tracked separately for home and away teams."""
        home_box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=1,
            team_timeouts_used_h1=2,
            team_timeouts_used_h2=0
        )
        away_box = BoxScore(
            game_id="game1",
            team_id=2,
            dynasty_id="test_dynasty",
            team_timeouts_remaining=3,
            team_timeouts_used_h1=0,
            team_timeouts_used_h2=0
        )

        api.insert_box_score(home_box)
        api.insert_box_score(away_box)

        home_retrieved = api.get_box_score("test_dynasty", "game1", 1)
        away_retrieved = api.get_box_score("test_dynasty", "game1", 2)

        assert home_retrieved.team_timeouts_remaining == 1
        assert away_retrieved.team_timeouts_remaining == 3

    def test_normalize_box_dict_with_timeouts(self, api):
        """Test _normalize_box_dict handles timeout fields."""
        box_dict = {
            "q1_score": 7,
            "total_yards": 300,
            "team_timeouts_remaining": 2,
            "team_timeouts_used_h1": 1
            # team_timeouts_used_h2 missing - should default to 0
        }

        normalized = api._normalize_box_dict(box_dict)

        assert normalized["team_timeouts_remaining"] == 2
        assert normalized["team_timeouts_used_h1"] == 1
        assert normalized["team_timeouts_used_h2"] == 0  # Default

    def test_normalize_box_dict_missing_timeout_fields(self, api):
        """Test _normalize_box_dict provides defaults for missing timeout fields."""
        box_dict = {
            "q1_score": 7,
            "total_yards": 300
            # All timeout fields missing
        }

        normalized = api._normalize_box_dict(box_dict)

        assert normalized["team_timeouts_remaining"] == 3  # Default
        assert normalized["team_timeouts_used_h1"] == 0    # Default
        assert normalized["team_timeouts_used_h2"] == 0    # Default
