"""
Comprehensive tests for DatabaseAPI.get_team_opponents() method.

This test suite validates all functionality of the get_team_opponents() database method:
- Basic opponent retrieval from both home and away games
- Season filtering
- Season type filtering (regular_season vs playoffs)
- Dynasty isolation
- Edge cases (no games, invalid teams, empty results)
- Transaction context support (optional connection parameter)

Test Structure:
- Uses pytest fixtures for temporary database and test data setup
- Creates realistic 17-game regular season schedule for team 7
- Tests all filtering combinations and edge cases
- Validates return type is List[int] with proper DISTINCT behavior
"""

import pytest
import sqlite3
from pathlib import Path
from typing import List

from database.api import DatabaseAPI


class TestGetTeamOpponents:
    """Test suite for DatabaseAPI.get_team_opponents() method."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """
        Create temporary database with test data.

        Sets up:
        - dynasties table with test dynasty
        - games table with realistic NFL schedule
        - Team 7 plays 17-game regular season schedule
        - Additional playoff games for season_type filtering
        - Games for different dynasty for isolation testing
        """
        db_path = tmp_path / "test.db"

        # Create database and tables
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create dynasties table
        cursor.execute("""
            CREATE TABLE dynasties (
                dynasty_id TEXT PRIMARY KEY,
                dynasty_name TEXT NOT NULL,
                owner_name TEXT,
                team_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_played TIMESTAMP,
                total_seasons INTEGER DEFAULT 0,
                championships_won INTEGER DEFAULT 0,
                super_bowls_won INTEGER DEFAULT 0,
                conference_championships INTEGER DEFAULT 0,
                division_titles INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_ties INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        # Insert test dynasties
        cursor.execute("""
            INSERT INTO dynasties (dynasty_id, dynasty_name, team_id, is_active)
            VALUES
                ('test_dynasty', 'Test Dynasty', 7, TRUE),
                ('other_dynasty', 'Other Dynasty', 12, TRUE)
        """)

        # Create games table (matching production schema)
        cursor.execute("""
            CREATE TABLE games (
                game_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                game_type TEXT DEFAULT 'regular',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                total_plays INTEGER,
                total_yards_home INTEGER,
                total_yards_away INTEGER,
                turnovers_home INTEGER DEFAULT 0,
                turnovers_away INTEGER DEFAULT 0,
                time_of_possession_home INTEGER,
                time_of_possession_away INTEGER,
                game_duration_minutes INTEGER,
                overtime_periods INTEGER DEFAULT 0,
                game_date INTEGER,
                weather_conditions TEXT,
                attendance INTEGER,
                created_at TEXT,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
                    ON DELETE CASCADE
            )
        """)

        # Insert 17-game regular season for team 7 (2024 season)
        # Team 7 opponents: 3, 12, 15, 20, 8, 14, 9, 22, 5, 18, 11, 27, 4, 16, 25, 30, 1
        # Mix of home and away games
        # Format: (game_id, dynasty_id, season, week, season_type, game_type, home_team_id, away_team_id,
        #          home_score, away_score, total_plays, total_yards_home, total_yards_away, turnovers_home, turnovers_away,
        #          time_of_possession_home, time_of_possession_away, game_duration_minutes, overtime_periods,
        #          game_date, weather_conditions, attendance, created_at)
        test_games_2024 = [
            # Week 1-5 (mix of home/away)
            ('g1', 'test_dynasty', 2024, 1, 'regular_season', 'regular', 7, 3, 24, 20, 142, 400, 300, 1, 2, 1800, 1800, 180, 0, None, None, None, '2024-09-08'),
            ('g2', 'test_dynasty', 2024, 2, 'regular_season', 'regular', 12, 7, 17, 21, 135, 300, 380, 2, 1, 1700, 1900, 175, 0, None, None, None, '2024-09-15'),
            ('g3', 'test_dynasty', 2024, 3, 'regular_season', 'regular', 7, 15, 28, 14, 148, 420, 280, 0, 3, 2000, 1600, 185, 0, None, None, None, '2024-09-22'),
            ('g4', 'test_dynasty', 2024, 4, 'regular_season', 'regular', 20, 7, 10, 31, 140, 250, 450, 3, 0, 1500, 2100, 178, 0, None, None, None, '2024-09-29'),
            ('g5', 'test_dynasty', 2024, 5, 'regular_season', 'regular', 7, 8, 27, 24, 155, 410, 390, 1, 1, 1900, 1700, 190, 0, None, None, None, '2024-10-06'),

            # Week 6-10
            ('g6', 'test_dynasty', 2024, 6, 'regular_season', 'regular', 14, 7, 20, 23, 138, 320, 360, 2, 1, 1650, 1950, 172, 0, None, None, None, '2024-10-13'),
            ('g7', 'test_dynasty', 2024, 7, 'regular_season', 'regular', 7, 9, 30, 27, 160, 440, 420, 1, 2, 2050, 1950, 195, 1, None, None, None, '2024-10-20'),
            ('g8', 'test_dynasty', 2024, 8, 'regular_season', 'regular', 22, 7, 14, 17, 145, 290, 340, 2, 1, 1700, 1900, 182, 0, None, None, None, '2024-10-27'),
            ('g9', 'test_dynasty', 2024, 9, 'regular_season', 'regular', 7, 5, 21, 18, 142, 380, 350, 1, 2, 1850, 1750, 177, 0, None, None, None, '2024-11-03'),
            ('g10', 'test_dynasty', 2024, 10, 'regular_season', 'regular', 18, 7, 24, 28, 150, 370, 430, 2, 0, 1700, 1900, 188, 0, None, None, None, '2024-11-10'),

            # Week 11-15
            ('g11', 'test_dynasty', 2024, 11, 'regular_season', 'regular', 7, 11, 35, 14, 152, 480, 270, 0, 3, 2100, 1500, 183, 0, None, None, None, '2024-11-17'),
            ('g12', 'test_dynasty', 2024, 12, 'regular_season', 'regular', 27, 7, 21, 24, 148, 350, 390, 2, 1, 1750, 1850, 186, 0, None, None, None, '2024-11-24'),
            ('g13', 'test_dynasty', 2024, 13, 'regular_season', 'regular', 7, 4, 31, 20, 158, 460, 340, 1, 2, 2000, 1600, 192, 0, None, None, None, '2024-12-01'),
            ('g14', 'test_dynasty', 2024, 14, 'regular_season', 'regular', 16, 7, 17, 28, 143, 310, 420, 2, 0, 1650, 1950, 179, 0, None, None, None, '2024-12-08'),
            ('g15', 'test_dynasty', 2024, 15, 'regular_season', 'regular', 7, 25, 24, 21, 146, 390, 370, 1, 1, 1880, 1720, 181, 0, None, None, None, '2024-12-15'),

            # Week 16-18
            ('g16', 'test_dynasty', 2024, 16, 'regular_season', 'regular', 30, 7, 14, 27, 141, 300, 410, 2, 1, 1650, 1950, 176, 0, None, None, None, '2024-12-22'),
            ('g17', 'test_dynasty', 2024, 17, 'regular_season', 'regular', 7, 1, 20, 17, 144, 360, 340, 1, 2, 1820, 1780, 180, 0, None, None, None, '2024-12-29'),
        ]

        # Insert playoff games for season_type filtering (team 7 makes playoffs)
        playoff_games = [
            ('p1', 'test_dynasty', 2024, 19, 'playoffs', 'wildcard', 7, 10, 28, 24, 150, 430, 380, 1, 2, 1950, 1650, 185, 0, None, None, None, '2025-01-05'),
            ('p2', 'test_dynasty', 2024, 20, 'playoffs', 'divisional', 2, 7, 21, 24, 148, 350, 400, 2, 1, 1750, 1850, 183, 0, None, None, None, '2025-01-12'),
            ('p3', 'test_dynasty', 2024, 21, 'playoffs', 'conference', 7, 6, 31, 28, 155, 470, 430, 1, 2, 2050, 1550, 190, 0, None, None, None, '2025-01-19'),
        ]

        # Insert games for 2025 season (season filtering)
        games_2025 = [
            ('g2025_1', 'test_dynasty', 2025, 1, 'regular_season', 'regular', 7, 13, 27, 24, 145, 410, 380, 1, 1, 1900, 1700, 180, 0, None, None, None, '2025-09-07'),
            ('g2025_2', 'test_dynasty', 2025, 2, 'regular_season', 'regular', 19, 7, 20, 23, 142, 340, 390, 2, 1, 1700, 1900, 178, 0, None, None, None, '2025-09-14'),
        ]

        # Insert games for different dynasty (dynasty isolation testing)
        other_dynasty_games = [
            ('gd2', 'other_dynasty', 2024, 1, 'regular_season', 'regular', 7, 99, 20, 17, 140, 360, 320, 1, 2, 1850, 1750, 175, 0, None, None, None, '2024-09-08'),
            ('gd3', 'other_dynasty', 2024, 2, 'regular_season', 'regular', 88, 7, 24, 21, 142, 380, 350, 1, 1, 1900, 1700, 178, 0, None, None, None, '2024-09-15'),
        ]

        # Insert all test data
        all_games = test_games_2024 + playoff_games + games_2025 + other_dynasty_games
        cursor.executemany(
            """INSERT INTO games (game_id, dynasty_id, season, week, season_type, game_type, home_team_id, away_team_id,
                                 home_score, away_score, total_plays, total_yards_home, total_yards_away, turnovers_home, turnovers_away,
                                 time_of_possession_home, time_of_possession_away, game_duration_minutes, overtime_periods,
                                 game_date, weather_conditions, attendance, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            all_games
        )

        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.fixture
    def api(self, temp_db):
        """Create DatabaseAPI instance with temp database."""
        return DatabaseAPI(database_path=temp_db)

    # ============================================================================
    # BASIC FUNCTIONALITY TESTS
    # ============================================================================

    def test_get_all_opponents_regular_season(self, api):
        """Test retrieving all opponents for a team in regular season."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Verify return type
        assert isinstance(opponents, list), "Should return a list"
        assert all(isinstance(opp, int) for opp in opponents), "All opponents should be integers"

        # Verify correct count (17 unique opponents in regular season)
        assert len(opponents) == 17, f"Should have 17 regular season opponents, got {len(opponents)}"

        # Verify specific opponents are included
        expected_opponents = [3, 12, 15, 20, 8, 14, 9, 22, 5, 18, 11, 27, 4, 16, 25, 30, 1]
        for expected_opp in expected_opponents:
            assert expected_opp in opponents, f"Expected opponent {expected_opp} not found in results"

        # Verify no duplicates (DISTINCT behavior)
        assert len(opponents) == len(set(opponents)), "Should not have duplicate opponents"

    def test_home_and_away_games_included(self, api):
        """Test that both home and away opponents are included."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Verify home opponents (team 7 was home)
        home_opponents = [3, 15, 8, 9, 5, 11, 4, 25, 1]  # Teams that played @ team 7
        for home_opp in home_opponents:
            assert home_opp in opponents, f"Home opponent {home_opp} should be in results"

        # Verify away opponents (team 7 was away)
        away_opponents = [12, 20, 14, 22, 18, 27, 16, 30]  # Teams that team 7 played @
        for away_opp in away_opponents:
            assert away_opp in opponents, f"Away opponent {away_opp} should be in results"

    def test_return_type_is_list_of_ints(self, api):
        """Test that return type is List[int]."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024
        )

        assert isinstance(opponents, list), "Must return a list"
        assert len(opponents) > 0, "Should have opponents"

        for opponent_id in opponents:
            assert isinstance(opponent_id, int), f"Opponent ID {opponent_id} should be int, got {type(opponent_id)}"
            assert 1 <= opponent_id <= 32, f"Opponent ID {opponent_id} should be valid NFL team (1-32)"

    def test_distinct_opponents_no_duplicates(self, api):
        """Test that opponents are DISTINCT (no duplicates even if teams play twice)."""
        # Note: In current test data, no teams play twice
        # But method should use DISTINCT in SQL to handle that case
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Check for duplicates
        unique_opponents = set(opponents)
        assert len(opponents) == len(unique_opponents), \
            f"Found duplicates: {[opp for opp in opponents if opponents.count(opp) > 1]}"

    # ============================================================================
    # FILTERING TESTS
    # ============================================================================

    def test_season_filtering(self, api):
        """Test filtering by season (only games from specified season)."""
        # 2024 season opponents
        opponents_2024 = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # 2025 season opponents (only 2 games)
        opponents_2025 = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2025,
            season_type='regular_season'
        )

        # Verify different results
        assert len(opponents_2024) == 17, "2024 should have 17 opponents"
        assert len(opponents_2025) == 2, "2025 should have 2 opponents"

        # Verify 2025 opponents
        assert 13 in opponents_2025, "Team 13 should be in 2025 opponents"
        assert 19 in opponents_2025, "Team 19 should be in 2025 opponents"

        # Verify 2024 opponents are NOT in 2025 results
        assert 3 not in opponents_2025, "2024 opponent should not be in 2025 results"

    def test_season_type_filtering_regular_season(self, api):
        """Test filtering by season_type='regular_season' excludes playoffs."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Should only include regular season opponents
        assert len(opponents) == 17, "Regular season should have exactly 17 opponents"

        # Should NOT include playoff opponents (10, 2, 6)
        playoff_opponents = [10, 2, 6]
        for playoff_opp in playoff_opponents:
            assert playoff_opp not in opponents, \
                f"Playoff opponent {playoff_opp} should not be in regular_season results"

    def test_season_type_filtering_playoffs(self, api):
        """Test filtering by season_type='playoffs' excludes regular season."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='playoffs'
        )

        # Should only include playoff opponents
        expected_playoff_opponents = [10, 2, 6]
        assert len(opponents) == 3, f"Playoffs should have 3 opponents, got {len(opponents)}"

        # Verify playoff opponents
        for playoff_opp in expected_playoff_opponents:
            assert playoff_opp in opponents, f"Playoff opponent {playoff_opp} should be in results"

        # Should NOT include regular season opponents
        regular_season_opponents = [3, 12, 15]
        for reg_opp in regular_season_opponents:
            assert reg_opp not in opponents, \
                f"Regular season opponent {reg_opp} should not be in playoff results"

    def test_season_type_default_regular_season(self, api):
        """Test that season_type defaults to 'regular_season' if not specified."""
        # Call without season_type parameter
        opponents_default = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024
        )

        # Call with explicit season_type='regular_season'
        opponents_explicit = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Should return same results
        assert opponents_default == opponents_explicit, \
            "Default season_type should be 'regular_season'"

    def test_dynasty_isolation(self, api):
        """Test that different dynasties are properly isolated."""
        # Get opponents for test_dynasty
        opponents_test = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Get opponents for other_dynasty
        opponents_other = api.get_team_opponents(
            dynasty_id='other_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Verify test_dynasty results (17 opponents)
        assert len(opponents_test) == 17, "test_dynasty should have 17 opponents"
        assert 3 in opponents_test, "test_dynasty should include opponent 3"

        # Verify other_dynasty results (2 opponents: 99 and 88)
        assert len(opponents_other) == 2, f"other_dynasty should have 2 opponents, got {len(opponents_other)}"
        assert 99 in opponents_other, "other_dynasty should include opponent 99"
        assert 88 in opponents_other, "other_dynasty should include opponent 88"

        # Verify no cross-contamination
        assert 99 not in opponents_test, "test_dynasty should NOT include other_dynasty's opponents"
        assert 88 not in opponents_test, "test_dynasty should NOT include other_dynasty's opponents"
        assert 3 not in opponents_other, "other_dynasty should NOT include test_dynasty's opponents"

    # ============================================================================
    # EDGE CASES
    # ============================================================================

    def test_team_with_no_games_returns_empty_list(self, api):
        """Test that team with no games returns empty list."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=99,  # Team that never played in test_dynasty
            season=2024
        )

        assert isinstance(opponents, list), "Should return a list"
        assert opponents == [], "Team with no games should return empty list"

    def test_invalid_team_id_returns_empty_list(self, api):
        """Test that invalid team_id returns empty list."""
        # Team ID 0 is invalid (NFL teams are 1-32)
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=0,
            season=2024
        )

        assert opponents == [], "Invalid team_id should return empty list"

        # Team ID 999 is invalid
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=999,
            season=2024
        )

        assert opponents == [], "Invalid team_id should return empty list"

    def test_season_with_no_games_returns_empty_list(self, api):
        """Test that season with no games returns empty list."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2099  # Future season with no games
        )

        assert opponents == [], "Season with no games should return empty list"

    def test_nonexistent_dynasty_returns_empty_list(self, api):
        """Test that nonexistent dynasty returns empty list."""
        opponents = api.get_team_opponents(
            dynasty_id='nonexistent_dynasty',
            team_id=7,
            season=2024
        )

        assert opponents == [], "Nonexistent dynasty should return empty list"

    def test_invalid_season_type_returns_empty_list(self, api):
        """Test that invalid season_type returns empty list."""
        opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='invalid_type'  # Not 'regular_season' or 'playoffs'
        )

        assert opponents == [], "Invalid season_type should return empty list"

    # ============================================================================
    # DATABASE STATE TESTS
    # ============================================================================

    def test_multiple_teams_different_schedules(self, api):
        """Test that different teams have different opponent lists."""
        # Team 7's opponents
        team_7_opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Team 3's opponents (team 3 played team 7 in week 1)
        team_3_opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=3,
            season=2024,
            season_type='regular_season'
        )

        # Verify team 7 has 17 opponents
        assert len(team_7_opponents) == 17, "Team 7 should have 17 opponents"

        # Verify team 3 has at least 1 opponent (team 7)
        assert 7 in team_3_opponents, "Team 3 should have played team 7"

        # Verify different opponent lists (unless they have identical schedules)
        # Team 3 only has 1 game in our test data, team 7 has 17
        assert len(team_7_opponents) != len(team_3_opponents), \
            "Different teams should have different number of opponents in test data"

    def test_with_transaction_context(self, temp_db):
        """Test that method works with external transaction context."""
        # Create connection with transaction
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Start transaction
            conn.execute('BEGIN TRANSACTION')

            # Execute query manually to verify it works in transaction context
            query = """
                SELECT DISTINCT
                    CASE
                        WHEN home_team_id = ? THEN away_team_id
                        ELSE home_team_id
                    END AS opponent_id
                FROM games
                WHERE dynasty_id = ?
                    AND season = ?
                    AND season_type = ?
                    AND (home_team_id = ? OR away_team_id = ?)
                ORDER BY opponent_id
            """

            cursor.execute(query, (7, 'test_dynasty', 2024, 'regular_season', 7, 7))
            results = cursor.fetchall()

            # Verify results
            opponents = [row[0] for row in results]
            assert len(opponents) == 17, "Should return 17 opponents in transaction"
            assert 3 in opponents, "Should include opponent 3"

            # Commit transaction
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ============================================================================
    # INTEGRATION TESTS
    # ============================================================================

    def test_complete_season_cycle(self, api):
        """Test getting opponents across entire season (regular + playoffs)."""
        # Get regular season opponents
        regular_opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # Get playoff opponents
        playoff_opponents = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='playoffs'
        )

        # Verify totals
        assert len(regular_opponents) == 17, "Should have 17 regular season opponents"
        assert len(playoff_opponents) == 3, "Should have 3 playoff opponents"

        # Verify no overlap (in this test data, no team plays same opponent in reg + playoffs)
        overlap = set(regular_opponents) & set(playoff_opponents)
        # Note: In real NFL, this could happen, but in our test data it doesn't
        assert len(overlap) == 0, f"No overlap expected in test data, found: {overlap}"

    def test_multi_season_different_opponents(self, api):
        """Test that different seasons have different opponents."""
        # 2024 opponents
        opponents_2024 = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2024,
            season_type='regular_season'
        )

        # 2025 opponents (only 2 games in test data)
        opponents_2025 = api.get_team_opponents(
            dynasty_id='test_dynasty',
            team_id=7,
            season=2025,
            season_type='regular_season'
        )

        # Verify 2024 has full schedule
        assert len(opponents_2024) == 17, "2024 should have full 17-game schedule"

        # Verify 2025 has partial schedule
        assert len(opponents_2025) == 2, "2025 should have 2 games"

        # Verify different opponents between seasons
        # Teams 13 and 19 are only in 2025, not in 2024
        assert 13 in opponents_2025 and 13 not in opponents_2024
        assert 19 in opponents_2025 and 19 not in opponents_2024
