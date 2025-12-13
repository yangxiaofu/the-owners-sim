"""
Tests for BoxScoresAPI.

Tests box score insertion, retrieval, and calculation from player stats.
"""

import pytest
import sqlite3
from pathlib import Path

from src.game_cycle.database.box_scores_api import BoxScoresAPI, BoxScore


@pytest.fixture
def test_db(tmp_path) -> str:
    """Create a test database with required schema."""
    db_path = str(tmp_path / "test_box_scores.db")

    with sqlite3.connect(db_path) as conn:
        # Create dynasties table
        conn.execute("""
            CREATE TABLE dynasties (
                dynasty_id TEXT PRIMARY KEY,
                dynasty_name TEXT NOT NULL
            )
        """)

        # Create games table
        conn.execute("""
            CREATE TABLE games (
                game_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            )
        """)

        # Create box_scores table (matching full_schema.sql)
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
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                UNIQUE(game_id, team_id)
            )
        """)
        conn.execute("CREATE INDEX idx_box_scores ON box_scores(dynasty_id, game_id)")

        # Create player_game_stats table for aggregation tests
        conn.execute("""
            CREATE TABLE player_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                passing_yards INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                receiving_yards INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            )
        """)

        # Insert test dynasty
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, dynasty_name) VALUES (?, ?)",
            ("test_dynasty", "Test Dynasty")
        )

        # Insert test game
        conn.execute("""
            INSERT INTO games (
                game_id, dynasty_id, season, week, season_type,
                home_team_id, away_team_id, home_score, away_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("game_2025_1_1_2", "test_dynasty", 2025, 1, "regular_season", 1, 2, 24, 17))

        conn.commit()

    return db_path


@pytest.fixture
def api(test_db) -> BoxScoresAPI:
    """Create BoxScoresAPI with test database."""
    return BoxScoresAPI(test_db)


# -------------------- BoxScore Dataclass Tests --------------------

class TestBoxScoreDataclass:
    """Tests for BoxScore dataclass properties."""

    def test_total_score_calculation(self):
        """Test total score property."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            q1_score=7,
            q2_score=10,
            q3_score=3,
            q4_score=7
        )
        assert box.total_score == 27

    def test_total_score_with_overtime(self):
        """Test total score includes overtime."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            q1_score=7,
            q2_score=7,
            q3_score=7,
            q4_score=7,
            ot_score=3
        )
        assert box.total_score == 31

    def test_third_down_pct(self):
        """Test third down percentage calculation."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            third_down_att=10,
            third_down_conv=4
        )
        assert box.third_down_pct == 0.4

    def test_third_down_pct_zero_attempts(self):
        """Test third down percentage with zero attempts."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            third_down_att=0,
            third_down_conv=0
        )
        assert box.third_down_pct == 0.0

    def test_fourth_down_pct(self):
        """Test fourth down percentage calculation."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            fourth_down_att=2,
            fourth_down_conv=1
        )
        assert box.fourth_down_pct == 0.5

    def test_time_of_possession_str(self):
        """Test time of possession formatting."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            time_of_possession=1830  # 30:30
        )
        assert box.time_of_possession_str == "30:30"

    def test_time_of_possession_str_none(self):
        """Test time of possession when not set."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test"
        )
        assert box.time_of_possession_str == "N/A"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        box = BoxScore(
            game_id="game1",
            team_id=1,
            dynasty_id="test",
            total_yards=350,
            passing_yards=250,
            rushing_yards=100
        )
        result = box.to_dict()

        assert result["game_id"] == "game1"
        assert result["team_id"] == 1
        assert result["total_yards"] == 350
        assert result["passing_yards"] == 250
        assert result["rushing_yards"] == 100


# -------------------- Insert Tests --------------------

class TestBoxScoresInsert:
    """Tests for box score insertion."""

    def test_insert_box_score(self, api, test_db):
        """Test inserting a single box score."""
        box = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            q1_score=7,
            q2_score=10,
            q3_score=0,
            q4_score=7,
            total_yards=320,
            passing_yards=230,
            rushing_yards=90,
            turnovers=1
        )

        result = api.insert_box_score(box)
        assert result is True

        # Verify in database
        with sqlite3.connect(test_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM box_scores WHERE game_id = ? AND team_id = ?",
                ("game_2025_1_1_2", 1)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["total_yards"] == 320
        assert row["passing_yards"] == 230
        assert row["q1_score"] == 7

    def test_insert_game_box_scores(self, api, test_db):
        """Test inserting box scores for both teams."""
        home_box = {
            "q1_score": 7,
            "q2_score": 10,
            "q3_score": 7,
            "q4_score": 0,
            "total_yards": 380,
            "passing_yards": 280,
            "rushing_yards": 100,
            "turnovers": 1
        }
        away_box = {
            "q1_score": 0,
            "q2_score": 10,
            "q3_score": 0,
            "q4_score": 7,
            "total_yards": 290,
            "passing_yards": 200,
            "rushing_yards": 90,
            "turnovers": 2
        }

        result = api.insert_game_box_scores(
            dynasty_id="test_dynasty",
            game_id="game_2025_1_1_2",
            home_team_id=1,
            away_team_id=2,
            home_box=home_box,
            away_box=away_box
        )

        assert result is True

        # Verify both inserted
        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM box_scores WHERE game_id = ?",
                ("game_2025_1_1_2",)
            )
            count = cursor.fetchone()[0]

        assert count == 2

    def test_insert_replaces_existing(self, api, test_db):
        """Test that INSERT OR REPLACE updates existing box score."""
        # Insert first
        box1 = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=300
        )
        api.insert_box_score(box1)

        # Insert again with different stats
        box2 = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=400
        )
        api.insert_box_score(box2)

        # Should only have one record
        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM box_scores WHERE game_id = ? AND team_id = ?",
                ("game_2025_1_1_2", 1)
            )
            count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT total_yards FROM box_scores WHERE game_id = ? AND team_id = ?",
                ("game_2025_1_1_2", 1)
            )
            yards = cursor.fetchone()[0]

        assert count == 1
        assert yards == 400


# -------------------- Query Tests --------------------

class TestBoxScoresQuery:
    """Tests for box score retrieval."""

    def test_get_box_score(self, api, test_db):
        """Test retrieving a single box score."""
        # Insert test data
        box = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=350,
            passing_yards=250,
            rushing_yards=100,
            turnovers=2
        )
        api.insert_box_score(box)

        # Retrieve
        result = api.get_box_score("test_dynasty", "game_2025_1_1_2", 1)

        assert result is not None
        assert result.game_id == "game_2025_1_1_2"
        assert result.team_id == 1
        assert result.total_yards == 350
        assert result.turnovers == 2

    def test_get_box_score_not_found(self, api):
        """Test retrieving non-existent box score."""
        result = api.get_box_score("test_dynasty", "nonexistent", 1)
        assert result is None

    def test_get_game_box_scores(self, api):
        """Test retrieving both box scores for a game."""
        # Insert both teams
        home_box = {
            "total_yards": 400,
            "passing_yards": 300,
            "rushing_yards": 100
        }
        away_box = {
            "total_yards": 280,
            "passing_yards": 180,
            "rushing_yards": 100
        }
        api.insert_game_box_scores(
            "test_dynasty", "game_2025_1_1_2", 1, 2, home_box, away_box
        )

        # Retrieve both
        results = api.get_game_box_scores("test_dynasty", "game_2025_1_1_2")

        assert len(results) == 2
        team_ids = {r.team_id for r in results}
        assert team_ids == {1, 2}

    def test_get_team_box_scores(self, api, test_db):
        """Test retrieving all box scores for a team."""
        # Insert multiple games (start from week 2 since week 1 already exists)
        for week in range(2, 5):
            game_id = f"game_2025_{week}_1_2"
            # Add game to games table
            with sqlite3.connect(test_db) as conn:
                conn.execute("""
                    INSERT INTO games (
                        game_id, dynasty_id, season, week, season_type,
                        home_team_id, away_team_id, home_score, away_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (game_id, "test_dynasty", 2025, week, "regular_season", 1, 2, 24, 17))
                conn.commit()

            box = BoxScore(
                game_id=game_id,
                team_id=1,
                dynasty_id="test_dynasty",
                total_yards=300 + (week * 10)
            )
            api.insert_box_score(box)

        # Also insert for week 1 game (already exists in fixture)
        box = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=310
        )
        api.insert_box_score(box)

        # Retrieve - should have 4 games (weeks 1-4)
        results = api.get_team_box_scores("test_dynasty", 1)

        assert len(results) == 4

    def test_get_team_box_scores_with_season_filter(self, api, test_db):
        """Test filtering team box scores by season."""
        # Insert games for multiple seasons
        for season in [2024, 2025]:
            game_id = f"game_{season}_1_1_2"
            with sqlite3.connect(test_db) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO games (
                        game_id, dynasty_id, season, week, season_type,
                        home_team_id, away_team_id, home_score, away_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (game_id, "test_dynasty", season, 1, "regular_season", 1, 2, 24, 17))
                conn.commit()

            box = BoxScore(
                game_id=game_id,
                team_id=1,
                dynasty_id="test_dynasty",
                total_yards=350
            )
            api.insert_box_score(box)

        # Filter by 2025
        results = api.get_team_box_scores("test_dynasty", 1, season=2025)

        assert len(results) == 1
        assert results[0].game_id == "game_2025_1_1_2"


# -------------------- Aggregation Tests --------------------

class TestBoxScoresAggregation:
    """Tests for calculating box scores from player stats."""

    def test_calculate_from_player_stats(self, api, test_db):
        """Test calculating box score from player_game_stats."""
        # Insert player stats
        with sqlite3.connect(test_db) as conn:
            # QB
            conn.execute("""
                INSERT INTO player_game_stats (
                    dynasty_id, game_id, player_id, team_id,
                    passing_yards, passing_interceptions
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, ("test_dynasty", "game_2025_1_1_2", "qb1", 1, 280, 1))

            # RB
            conn.execute("""
                INSERT INTO player_game_stats (
                    dynasty_id, game_id, player_id, team_id,
                    rushing_yards, rushing_fumbles
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, ("test_dynasty", "game_2025_1_1_2", "rb1", 1, 95, 1))

            conn.commit()

        # Calculate
        result = api.calculate_from_player_stats(
            "test_dynasty", "game_2025_1_1_2", 1
        )

        assert result.passing_yards == 280
        assert result.rushing_yards == 95
        assert result.total_yards == 375  # 280 + 95
        assert result.turnovers == 2  # 1 INT + 1 fumble

    def test_calculate_from_player_stats_no_data(self, api):
        """Test calculation when no player stats exist."""
        result = api.calculate_from_player_stats(
            "test_dynasty", "nonexistent_game", 1
        )

        assert result.total_yards == 0
        assert result.turnovers == 0

    def test_get_or_calculate_uses_stored_first(self, api):
        """Test that get_or_calculate prefers stored box score."""
        # Insert explicit box score
        box = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=999  # Specific value to verify
        )
        api.insert_box_score(box)

        # Should return stored value, not calculate
        result = api.get_or_calculate_box_score(
            "test_dynasty", "game_2025_1_1_2", 1
        )

        assert result.total_yards == 999

    def test_get_or_calculate_falls_back_to_calculation(self, api, test_db):
        """Test fallback to calculation when no stored box score."""
        # Insert player stats but no box score
        with sqlite3.connect(test_db) as conn:
            conn.execute("""
                INSERT INTO player_game_stats (
                    dynasty_id, game_id, player_id, team_id,
                    passing_yards, rushing_yards
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, ("test_dynasty", "game_2025_1_1_2", "qb1", 1, 200, 50))
            conn.commit()

        result = api.get_or_calculate_box_score(
            "test_dynasty", "game_2025_1_1_2", 1
        )

        assert result.total_yards == 250  # 200 + 50

    def test_aggregate_from_player_stats_static_method(self):
        """Test static method for aggregating in-memory player stats."""
        # Simulate player stats list from game simulation
        player_stats = [
            # Team 1 - QB
            {"team_id": 1, "passing_yards": 280, "rushing_yards": 5,
             "passing_interceptions": 1, "rushing_fumbles": 0},
            # Team 1 - RB
            {"team_id": 1, "passing_yards": 0, "rushing_yards": 95,
             "passing_interceptions": 0, "rushing_fumbles": 1},
            # Team 1 - WR
            {"team_id": 1, "receiving_yards": 120, "rushing_yards": 0},
            # Team 2 - QB
            {"team_id": 2, "passing_yards": 200, "rushing_yards": 15,
             "passing_interceptions": 2, "rushing_fumbles": 0},
            # Team 2 - RB
            {"team_id": 2, "passing_yards": 0, "rushing_yards": 80,
             "passing_interceptions": 0, "rushing_fumbles": 0},
        ]

        # Aggregate for team 1
        result = BoxScoresAPI.aggregate_from_player_stats(player_stats, 1)

        assert result["passing_yards"] == 280  # Only QB passing
        assert result["rushing_yards"] == 100  # 5 + 95
        assert result["total_yards"] == 380  # 280 + 100
        assert result["turnovers"] == 2  # 1 INT + 1 fumble

        # Verify team 2 aggregation
        result2 = BoxScoresAPI.aggregate_from_player_stats(player_stats, 2)

        assert result2["passing_yards"] == 200
        assert result2["rushing_yards"] == 95  # 15 + 80
        assert result2["total_yards"] == 295  # 200 + 95
        assert result2["turnovers"] == 2  # 2 INTs

    def test_aggregate_from_player_stats_handles_none_values(self):
        """Test static method handles None and missing values gracefully."""
        player_stats = [
            {"team_id": 1, "passing_yards": None, "rushing_yards": 50},
            {"team_id": 1},  # Missing all fields
        ]

        result = BoxScoresAPI.aggregate_from_player_stats(player_stats, 1)

        assert result["passing_yards"] == 0  # None treated as 0
        assert result["rushing_yards"] == 50
        assert result["total_yards"] == 50
        assert result["turnovers"] == 0


# -------------------- Dynasty Isolation Tests --------------------

class TestDynastyIsolation:
    """Tests for dynasty isolation."""

    def test_box_scores_isolated_by_dynasty(self, test_db):
        """Test that box scores are isolated between dynasties."""
        # Create second dynasty
        with sqlite3.connect(test_db) as conn:
            conn.execute(
                "INSERT INTO dynasties (dynasty_id, dynasty_name) VALUES (?, ?)",
                ("other_dynasty", "Other Dynasty")
            )
            conn.commit()

        api = BoxScoresAPI(test_db)

        # Insert box score for test_dynasty
        box1 = BoxScore(
            game_id="game_2025_1_1_2",
            team_id=1,
            dynasty_id="test_dynasty",
            total_yards=400
        )
        api.insert_box_score(box1)

        # Query from other_dynasty - should not find it
        result = api.get_box_score("other_dynasty", "game_2025_1_1_2", 1)
        assert result is None

        # Query from test_dynasty - should find it
        result = api.get_box_score("test_dynasty", "game_2025_1_1_2", 1)
        assert result is not None
        assert result.total_yards == 400