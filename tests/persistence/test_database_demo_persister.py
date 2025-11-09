"""
Unit Tests for DatabaseDemoPersister - Season Type Isolation

Tests verify that standings updates properly handle season_type parameter
and maintain separation between preseason, regular_season, and playoffs records.

Critical Bugs Fixed:
1. Missing season_type in INSERT statement
2. Missing season_type in UPDATE WHERE clauses
3. Missing season_type parameter in update_standings()
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from persistence.demo.database_demo_persister import DatabaseDemoPersister
from database.connection import DatabaseConnection


class TestDatabaseDemoPersisterSeasonTypeIsolation:
    """Test suite for season_type handling in standings persistence"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        temp_path = temp_file.name
        temp_file.close()

        # Initialize database schema
        db_conn = DatabaseConnection(temp_path)
        conn = db_conn.get_connection()
        conn.close()

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    @pytest.fixture
    def persister(self, temp_db):
        """Create DatabaseDemoPersister instance"""
        return DatabaseDemoPersister(temp_db)

    def query_standings(self, temp_db, dynasty_id, team_id, season, season_type):
        """Helper: Query standings for specific season_type"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT * FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            (dynasty_id, team_id, season, season_type)
        )
        result = cursor.fetchone()
        conn.close()
        return result

    def test_update_standings_creates_record_with_season_type(self, persister, temp_db):
        """Test 1: Verify INSERT includes season_type column"""
        # Simulate game
        result = persister.update_standings(
            home_team_id=1,
            away_team_id=2,
            home_score=24,
            away_score=17,
            dynasty_id="test_dynasty",
            season=2025,
            season_type="preseason"
        )

        assert result.success, "Standings update should succeed"

        # Verify record has season_type
        home_record = self.query_standings(temp_db, "test_dynasty", 1, 2025, "preseason")
        assert home_record is not None, "Home team preseason standings should exist"

        # Verify no regular_season record created
        regular_record = self.query_standings(temp_db, "test_dynasty", 1, 2025, "regular_season")
        assert regular_record is None, "Should NOT create regular_season record for preseason game"

    def test_update_standings_preseason_vs_regular_season_isolation(self, persister, temp_db):
        """Test 2: Verify preseason and regular_season standings are separate"""
        # Simulate preseason game
        persister.update_standings(
            home_team_id=1, away_team_id=2,
            home_score=21, away_score=14,
            dynasty_id="test_dynasty", season=2025,
            season_type="preseason"
        )

        # Simulate regular season game
        persister.update_standings(
            home_team_id=1, away_team_id=2,
            home_score=27, away_score=24,
            dynasty_id="test_dynasty", season=2025,
            season_type="regular_season"
        )

        # Verify preseason standings
        preseason_record = self.query_standings(temp_db, "test_dynasty", 1, 2025, "preseason")
        assert preseason_record is not None
        # wins column is typically index 4
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT wins FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 1, 2025, "preseason")
        )
        preseason_wins = cursor.fetchone()[0]
        conn.close()
        assert preseason_wins == 1, "Team 1 should have 1 preseason win"

        # Verify regular_season standings separate
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT wins FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 1, 2025, "regular_season")
        )
        regular_wins = cursor.fetchone()[0]
        conn.close()
        assert regular_wins == 1, "Team 1 should have 1 regular_season win (not 2!)"

    def test_update_standings_increments_wins_correctly(self, persister, temp_db):
        """Test 3: Verify UPDATE matches correct row with season_type"""
        # Initial game
        persister.update_standings(
            home_team_id=5, away_team_id=6,
            home_score=28, away_score=21,
            dynasty_id="test_dynasty", season=2025,
            season_type="regular_season"
        )

        # Query database
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT wins, losses FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 5, 2025, "regular_season")
        )
        wins, losses = cursor.fetchone()
        conn.close()

        assert wins == 1, "Home team should have 1 win"
        assert losses == 0, "Home team should have 0 losses"

    def test_update_standings_accumulates_multiple_games(self, persister, temp_db):
        """Test 4: Verify standings accumulate correctly within same season_type"""
        # Simulate 3 preseason games for team 10
        for i in range(3):
            persister.update_standings(
                home_team_id=10, away_team_id=11 + i,
                home_score=24, away_score=17,
                dynasty_id="test_dynasty", season=2025,
                season_type="preseason"
            )

        # Simulate 1 regular season game
        persister.update_standings(
            home_team_id=10, away_team_id=15,
            home_score=31, away_score=28,
            dynasty_id="test_dynasty", season=2025,
            season_type="regular_season"
        )

        # Verify preseason wins = 3
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT wins FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 10, 2025, "preseason")
        )
        preseason_wins = cursor.fetchone()[0]
        assert preseason_wins == 3, "Team 10 should have 3 preseason wins"

        # Verify regular_season wins = 1 (NOT 4!)
        cursor = conn.execute(
            "SELECT wins FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 10, 2025, "regular_season")
        )
        regular_wins = cursor.fetchone()[0]
        conn.close()
        assert regular_wins == 1, "Team 10 should have 1 regular_season win, NOT 4!"

    def test_update_standings_handles_all_season_types(self, persister, temp_db):
        """Test 5: Verify all three season_types work correctly"""
        team_id = 20

        # Preseason game
        persister.update_standings(
            home_team_id=team_id, away_team_id=21,
            home_score=20, away_score=10,
            dynasty_id="test_dynasty", season=2025,
            season_type="preseason"
        )

        # Regular season game
        persister.update_standings(
            home_team_id=team_id, away_team_id=22,
            home_score=30, away_score=27,
            dynasty_id="test_dynasty", season=2025,
            season_type="regular_season"
        )

        # Playoffs game
        persister.update_standings(
            home_team_id=team_id, away_team_id=23,
            home_score=24, away_score=21,
            dynasty_id="test_dynasty", season=2025,
            season_type="playoffs"
        )

        # Verify all three separate records exist
        conn = sqlite3.connect(temp_db)

        cursor = conn.execute(
            "SELECT COUNT(*) FROM standings WHERE dynasty_id=? AND team_id=? AND season=?",
            ("test_dynasty", team_id, 2025)
        )
        count = cursor.fetchone()[0]
        assert count == 3, "Team should have 3 separate standings records (one per season_type)"

        # Verify each has exactly 1 win
        for season_type in ['preseason', 'regular_season', 'playoffs']:
            cursor = conn.execute(
                "SELECT wins FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
                ("test_dynasty", team_id, 2025, season_type)
            )
            wins = cursor.fetchone()[0]
            assert wins == 1, f"Team should have exactly 1 {season_type} win"

        conn.close()

    def test_missing_season_type_defaults_to_regular_season(self, persister, temp_db):
        """Test 8: Verify default season_type is 'regular_season'"""
        # Call without season_type parameter (should default)
        persister.update_standings(
            home_team_id=7, away_team_id=8,
            home_score=21, away_score=14,
            dynasty_id="test_dynasty", season=2025
            # NOTE: No season_type parameter
        )

        # Verify created as regular_season
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 7, 2025, "regular_season")
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Should create regular_season record when season_type not provided"

        # Verify NO preseason record
        cursor = conn.execute(
            "SELECT COUNT(*) FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", 7, 2025, "preseason")
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0, "Should NOT create preseason record"

    def test_standings_isolation_across_all_phases(self, persister, temp_db):
        """Test 10: Verify complete season cycle maintains isolation"""
        team_id = 15

        # Simulate 3 preseason games (all wins)
        for opponent in [16, 17, 18]:
            persister.update_standings(
                home_team_id=team_id, away_team_id=opponent,
                home_score=24, away_score=17,
                dynasty_id="test_dynasty", season=2025,
                season_type="preseason"
            )

        # Simulate 5 regular season games (3 wins, 2 losses)
        for i, (score_home, score_away) in enumerate([(28, 21), (14, 17), (31, 28), (20, 24), (35, 31)]):
            persister.update_standings(
                home_team_id=team_id if i % 2 == 0 else 19,
                away_team_id=19 if i % 2 == 0 else team_id,
                home_score=score_home, away_score=score_away,
                dynasty_id="test_dynasty", season=2025,
                season_type="regular_season"
            )

        # Simulate 2 playoff games (both wins)
        for opponent in [25, 26]:
            persister.update_standings(
                home_team_id=team_id, away_team_id=opponent,
                home_score=31, away_score=28,
                dynasty_id="test_dynasty", season=2025,
                season_type="playoffs"
            )

        # Verify standings
        conn = sqlite3.connect(temp_db)

        # Preseason: 3-0
        cursor = conn.execute(
            "SELECT wins, losses FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", team_id, 2025, "preseason")
        )
        ps_wins, ps_losses = cursor.fetchone()
        assert ps_wins == 3 and ps_losses == 0, "Preseason should be 3-0"

        # Regular season: 3-2
        cursor = conn.execute(
            "SELECT wins, losses FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", team_id, 2025, "regular_season")
        )
        rs_wins, rs_losses = cursor.fetchone()
        assert rs_wins == 3 and rs_losses == 2, "Regular season should be 3-2"

        # Playoffs: 2-0
        cursor = conn.execute(
            "SELECT wins, losses FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", team_id, 2025, "playoffs")
        )
        po_wins, po_losses = cursor.fetchone()
        conn.close()
        assert po_wins == 2 and po_losses == 0, "Playoffs should be 2-0"

    def test_points_accumulation_by_season_type(self, persister, temp_db):
        """Test points_for/against accumulate correctly per season_type"""
        team_id = 12

        # Preseason: score 50 points total
        persister.update_standings(
            home_team_id=team_id, away_team_id=13,
            home_score=50, away_score=10,
            dynasty_id="test_dynasty", season=2025,
            season_type="preseason"
        )

        # Regular season: score 100 points total
        persister.update_standings(
            home_team_id=team_id, away_team_id=14,
            home_score=100, away_score=20,
            dynasty_id="test_dynasty", season=2025,
            season_type="regular_season"
        )

        # Verify points separation
        conn = sqlite3.connect(temp_db)

        cursor = conn.execute(
            "SELECT points_for FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", team_id, 2025, "preseason")
        )
        ps_points = cursor.fetchone()[0]
        assert ps_points == 50, "Preseason points_for should be 50"

        cursor = conn.execute(
            "SELECT points_for FROM standings WHERE dynasty_id=? AND team_id=? AND season=? AND season_type=?",
            ("test_dynasty", team_id, 2025, "regular_season")
        )
        rs_points = cursor.fetchone()[0]
        conn.close()
        assert rs_points == 100, "Regular season points_for should be 100 (NOT 150!)"
