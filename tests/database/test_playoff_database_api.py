"""
Unit Tests for PlayoffDatabaseAPI

Tests playoff database operations including:
- Clearing playoff data (events, brackets, seedings)
- Checking bracket existence
- Checking seeding existence
- Transaction-aware operations
- Dynasty isolation
- Season isolation
- Edge case handling
"""

import pytest
import sqlite3
from datetime import datetime
from typing import Dict

from database.connection import DatabaseConnection
from events.event_database_api import EventDatabaseAPI
from events.game_event import GameEvent


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def playoff_db_path(test_db_path):
    """
    Create test database with playoff-related schema initialized.

    Returns:
        Path to test database with events, playoff_brackets, and playoff_seedings tables
    """
    # Initialize database connection
    db_conn = DatabaseConnection(test_db_path)
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Create dynasties table first (required for foreign keys)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            owner_name TEXT,
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Now we can ensure dynasty exists
    db_conn.ensure_dynasty_exists("test_dynasty")

    # Initialize events table via EventDatabaseAPI
    EventDatabaseAPI(test_db_path)

    # Use actual schema from database (matches migration 006)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playoff_brackets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            round_name TEXT NOT NULL,
            game_number INTEGER NOT NULL,
            conference TEXT,
            home_seed INTEGER NOT NULL,
            away_seed INTEGER NOT NULL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            game_date DATE,
            scheduled_time TIME,
            winner_team_id INTEGER,
            winner_score INTEGER,
            loser_score INTEGER,
            overtime_periods INTEGER DEFAULT 0,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playoff_seedings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            conference TEXT NOT NULL,
            seed_number INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            ties INTEGER DEFAULT 0,
            division_winner BOOLEAN NOT NULL DEFAULT 0,
            tiebreaker_applied TEXT,
            eliminated_teams TEXT,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            strength_of_victory REAL DEFAULT 0.0,
            strength_of_schedule REAL DEFAULT 0.0,
            seeding_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
            UNIQUE(dynasty_id, season, conference, seed_number)
        )
    """)

    conn.commit()

    return test_db_path


@pytest.fixture
def playoff_db_api(playoff_db_path):
    """
    Provides PlayoffDatabaseAPI instance with test database.

    Note: This will import the actual PlayoffDatabaseAPI when it's implemented.
    For now, we create a mock implementation for testing purposes.
    """
    # Import will be: from database.playoff_database_api import PlayoffDatabaseAPI
    # For now, create a simple test implementation
    from database.connection import DatabaseConnection

    class PlayoffDatabaseAPI:
        """Mock implementation of PlayoffDatabaseAPI for testing."""

        def __init__(self, db_path: str):
            self.db_path = db_path
            self.db = DatabaseConnection(db_path)

        def clear_playoff_data(
            self,
            dynasty_id: str,
            season: int,
            connection: sqlite3.Connection = None
        ) -> Dict[str, int]:
            """
            Clear all playoff data for a specific dynasty and season.

            Deletes from 3 tables:
            - events (playoff games only)
            - playoff_brackets
            - playoff_seedings

            Args:
                dynasty_id: Dynasty identifier
                season: Season year
                connection: Optional connection for transaction mode

            Returns:
                Dict with deletion counts:
                {
                    'events_deleted': int,
                    'brackets_deleted': int,
                    'seedings_deleted': int,
                    'total_deleted': int
                }
            """
            try:
                if connection:
                    cursor = connection.cursor()
                else:
                    cursor = self.db.get_connection().cursor()

                # Delete playoff events (game_id starts with 'playoff_<season>_')
                cursor.execute(
                    """
                    DELETE FROM events
                    WHERE dynasty_id = ?
                    AND game_id LIKE ?
                    """,
                    (dynasty_id, f'playoff_{season}_%')
                )
                events_deleted = cursor.rowcount

                # Delete playoff brackets
                cursor.execute(
                    """
                    DELETE FROM playoff_brackets
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (dynasty_id, season)
                )
                brackets_deleted = cursor.rowcount

                # Delete playoff seedings
                cursor.execute(
                    """
                    DELETE FROM playoff_seedings
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (dynasty_id, season)
                )
                seedings_deleted = cursor.rowcount

                if not connection:
                    cursor.connection.commit()

                return {
                    'events_deleted': events_deleted,
                    'brackets_deleted': brackets_deleted,
                    'seedings_deleted': seedings_deleted,
                    'total_deleted': events_deleted + brackets_deleted + seedings_deleted
                }

            except Exception as e:
                if not connection:
                    try:
                        cursor.connection.rollback()
                    except:
                        pass
                # Re-raise for debugging during tests
                raise

        def bracket_exists(self, dynasty_id: str, season: int) -> bool:
            """
            Check if playoff bracket exists for dynasty/season.

            Args:
                dynasty_id: Dynasty identifier
                season: Season year

            Returns:
                True if bracket exists, False otherwise
            """
            try:
                cursor = self.db.get_connection().cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM playoff_brackets
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (dynasty_id, season)
                )
                row = cursor.fetchone()
                return row[0] > 0
            except Exception:
                return False

        def seeding_exists(self, dynasty_id: str, season: int) -> bool:
            """
            Check if playoff seedings exist for dynasty/season.

            Args:
                dynasty_id: Dynasty identifier
                season: Season year

            Returns:
                True if any seedings exist, False otherwise
            """
            try:
                cursor = self.db.get_connection().cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM playoff_seedings
                    WHERE dynasty_id = ? AND season = ?
                    """,
                    (dynasty_id, season)
                )
                row = cursor.fetchone()
                return row[0] > 0
            except Exception:
                return False

    return PlayoffDatabaseAPI(playoff_db_path)


@pytest.fixture
def sample_playoff_data(playoff_db_path, test_dynasty_id, test_season):
    """
    Insert sample playoff data for testing.

    Creates:
    - 4 playoff game events (2 Wild Card, 1 Divisional, 1 Conference)
    - 1 playoff bracket record
    - 12 playoff seeding records (6 AFC, 6 NFC)

    Returns:
        Dict with sample data metadata
    """
    db_conn = DatabaseConnection(playoff_db_path)
    event_api = EventDatabaseAPI(playoff_db_path)

    # Insert playoff events
    playoff_games = [
        (f'playoff_{test_season}_wildcard_1', 7, 9, datetime(2025, 1, 13)),
        (f'playoff_{test_season}_wildcard_2', 8, 10, datetime(2025, 1, 14)),
        (f'playoff_{test_season}_divisional_1', 1, 7, datetime(2025, 1, 20)),
        (f'playoff_{test_season}_conference_1', 1, 5, datetime(2025, 1, 27)),
    ]

    for game_id, home_team, away_team, game_date in playoff_games:
        game_event = GameEvent(
            away_team_id=away_team,
            home_team_id=home_team,
            game_date=game_date,
            week=19,
            dynasty_id=test_dynasty_id,
            game_id=game_id,
            season=test_season,
            season_type='playoffs'
        )
        event_api.insert_event(game_event)

    # Insert playoff brackets (Wild Card round)
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # AFC Wild Card matchups
    cursor.execute(
        """
        INSERT INTO playoff_brackets
        (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (test_dynasty_id, test_season, 'wild_card', 1, 'AFC', 2, 7, 2, 7)
    )

    # NFC Wild Card matchup
    cursor.execute(
        """
        INSERT INTO playoff_brackets
        (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (test_dynasty_id, test_season, 'wild_card', 1, 'NFC', 2, 7, 8, 9)
    )

    # Insert playoff seedings (12 teams: 6 AFC + 6 NFC)
    afc_teams = [1, 2, 3, 4, 5, 6]  # Chiefs, Bills, Ravens, etc.
    nfc_teams = [7, 8, 9, 10, 11, 12]  # Lions, Eagles, 49ers, etc.

    for seed, team_id in enumerate(afc_teams, start=1):
        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'AFC', seed, team_id, 14 - seed, 3, 0, 1)
        )

    for seed, team_id in enumerate(nfc_teams, start=1):
        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'NFC', seed, team_id, 14 - seed, 3, 0, 1)
        )

    conn.commit()

    return {
        'dynasty_id': test_dynasty_id,
        'season': test_season,
        'playoff_games': len(playoff_games),
        'bracket_count': 2,  # 2 Wild Card matchups (1 AFC, 1 NFC)
        'seeding_count': 12
    }


# ============================================================================
# TEST CASES: clear_playoff_data
# ============================================================================


class TestClearPlayoffData:
    """Test clear_playoff_data() method."""

    def test_clear_playoff_data_auto_commit(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test clearing playoff data without providing connection (auto-commit)."""
        # Verify data exists before clearing
        assert playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        # Clear playoff data
        result = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)

        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['total_deleted'] >= 0
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

    def test_clear_playoff_data_transaction_mode(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test clearing playoff data within transaction (shared connection)."""
        # Get connection for transaction
        conn = playoff_db_api.db.get_connection()
        conn.execute("BEGIN")

        try:
            # Clear playoff data within transaction
            result = playoff_db_api.clear_playoff_data(
                test_dynasty_id, test_season, connection=conn
            )

            assert isinstance(result, dict)
            assert 'events_deleted' in result
            assert 'brackets_deleted' in result
            assert 'seedings_deleted' in result
            assert 'total_deleted' in result
            assert result['total_deleted'] >= 0

            # Commit transaction
            conn.commit()

            # Verify data is cleared
            assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
            assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        except Exception:
            conn.rollback()
            raise

    def test_clear_playoff_data_no_data_exists(
        self, playoff_db_api, test_dynasty_id, test_season
    ):
        """Test clearing playoff data when no data exists (edge case)."""
        # Verify no data exists
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        # Should still succeed
        result = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)

        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['total_deleted'] == 0  # No data to delete

    def test_clear_playoff_data_partial_data(
        self, playoff_db_api, playoff_db_path, test_dynasty_id, test_season
    ):
        """Test clearing playoff data when only some tables have data."""
        # Insert only bracket data (no seedings, no events)
        db_conn = DatabaseConnection(playoff_db_path)
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO playoff_brackets
            (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'wild_card', 1, 'AFC', 1, 2, 1, 2)
        )
        conn.commit()

        # Verify partial data exists
        assert playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        # Clear should still work
        result = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)

        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['brackets_deleted'] == 1  # Only bracket data existed
        assert result['seedings_deleted'] == 0
        assert result['total_deleted'] == 1
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)

    def test_clear_playoff_data_multiple_seasons(
        self, playoff_db_api, sample_playoff_data, playoff_db_path,
        test_dynasty_id, test_season
    ):
        """Test that clearing only affects specified season."""
        # Insert playoff data for different season
        season_2026 = test_season + 1

        db_conn = DatabaseConnection(playoff_db_path)
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        # Insert bracket for 2026
        cursor.execute(
            """
            INSERT INTO playoff_brackets
            (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, season_2026, 'wild_card', 1, 'AFC', 1, 2, 1, 2)
        )

        # Insert seeding for 2026
        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, season_2026, 'AFC', 1, 1, 14, 3, 0, 1)
        )

        conn.commit()

        # Clear only 2025 data
        result = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)

        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['total_deleted'] > 0  # Some data was deleted

        # Verify 2025 data is cleared
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        # Verify 2026 data still exists
        assert playoff_db_api.bracket_exists(test_dynasty_id, season_2026)
        assert playoff_db_api.seeding_exists(test_dynasty_id, season_2026)

    def test_clear_playoff_data_multiple_dynasties(
        self, playoff_db_api, sample_playoff_data, playoff_db_path, test_season
    ):
        """Test that clearing only affects specified dynasty."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Ensure both dynasties exist
        db_conn = DatabaseConnection(playoff_db_path)
        db_conn.ensure_dynasty_exists(dynasty_1)
        db_conn.ensure_dynasty_exists(dynasty_2)

        conn = db_conn.get_connection()
        cursor = conn.cursor()

        # Insert playoff data for dynasty_1
        cursor.execute(
            """
            INSERT INTO playoff_brackets
            (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dynasty_1, test_season, 'wild_card', 1, 'AFC', 1, 2, 1, 2)
        )

        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dynasty_1, test_season, 'AFC', 1, 1, 14, 3, 0, 1)
        )

        # Insert playoff data for dynasty_2
        cursor.execute(
            """
            INSERT INTO playoff_brackets
            (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dynasty_2, test_season, 'wild_card', 1, 'AFC', 1, 2, 2, 3)
        )

        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dynasty_2, test_season, 'AFC', 1, 2, 14, 3, 0, 1)
        )

        conn.commit()

        # Clear only dynasty_1 data
        result = playoff_db_api.clear_playoff_data(dynasty_1, test_season)

        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['brackets_deleted'] == 1
        assert result['seedings_deleted'] == 1
        assert result['total_deleted'] == 2

        # Verify dynasty_1 data is cleared
        assert not playoff_db_api.bracket_exists(dynasty_1, test_season)
        assert not playoff_db_api.seeding_exists(dynasty_1, test_season)

        # Verify dynasty_2 data still exists
        assert playoff_db_api.bracket_exists(dynasty_2, test_season)
        assert playoff_db_api.seeding_exists(dynasty_2, test_season)


# ============================================================================
# TEST CASES: bracket_exists
# ============================================================================


class TestBracketExists:
    """Test bracket_exists() method."""

    def test_bracket_exists_true(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test bracket_exists returns True when bracket exists."""
        exists = playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert exists is True

    def test_bracket_exists_false(
        self, playoff_db_api, test_dynasty_id, test_season
    ):
        """Test bracket_exists returns False when bracket doesn't exist."""
        exists = playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert exists is False

    def test_bracket_exists_wrong_dynasty(
        self, playoff_db_api, sample_playoff_data, test_season
    ):
        """Test bracket_exists returns False for different dynasty."""
        wrong_dynasty = "different_dynasty"

        # Ensure dynasty exists (but has no bracket)
        db_conn = playoff_db_api.db
        db_conn.ensure_dynasty_exists(wrong_dynasty)

        exists = playoff_db_api.bracket_exists(wrong_dynasty, test_season)
        assert exists is False

    def test_bracket_exists_wrong_season(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test bracket_exists returns False for different season."""
        wrong_season = test_season + 10

        exists = playoff_db_api.bracket_exists(test_dynasty_id, wrong_season)
        assert exists is False


# ============================================================================
# TEST CASES: seeding_exists
# ============================================================================


class TestSeedingExists:
    """Test seeding_exists() method."""

    def test_seeding_exists_true(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test seeding_exists returns True when seedings exist."""
        exists = playoff_db_api.seeding_exists(test_dynasty_id, test_season)
        assert exists is True

    def test_seeding_exists_false(
        self, playoff_db_api, test_dynasty_id, test_season
    ):
        """Test seeding_exists returns False when no seedings exist."""
        exists = playoff_db_api.seeding_exists(test_dynasty_id, test_season)
        assert exists is False

    def test_seeding_exists_single_seeding(
        self, playoff_db_api, playoff_db_path, test_dynasty_id, test_season
    ):
        """Test seeding_exists returns True with just one seeding record."""
        # Insert single seeding record
        db_conn = DatabaseConnection(playoff_db_path)
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'AFC', 1, 1, 14, 3, 0, 1)
        )
        conn.commit()

        exists = playoff_db_api.seeding_exists(test_dynasty_id, test_season)
        assert exists is True

    def test_seeding_exists_wrong_dynasty(
        self, playoff_db_api, sample_playoff_data, test_season
    ):
        """Test seeding_exists returns False for different dynasty."""
        wrong_dynasty = "different_dynasty"

        # Ensure dynasty exists (but has no seedings)
        db_conn = playoff_db_api.db
        db_conn.ensure_dynasty_exists(wrong_dynasty)

        exists = playoff_db_api.seeding_exists(wrong_dynasty, test_season)
        assert exists is False

    def test_seeding_exists_wrong_season(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test seeding_exists returns False for different season."""
        wrong_season = test_season + 10

        exists = playoff_db_api.seeding_exists(test_dynasty_id, wrong_season)
        assert exists is False


# ============================================================================
# TEST CASES: Integration and Edge Cases
# ============================================================================


class TestIntegrationAndEdgeCases:
    """Test integration scenarios and edge cases."""

    def test_clear_and_check_consistency(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test that clear operation makes both existence checks return False."""
        # Verify data exists
        assert playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert playoff_db_api.seeding_exists(test_dynasty_id, test_season)

        # Clear data
        playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)

        # Both checks should return False
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

    def test_transaction_rollback_on_error(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test that transaction rollback preserves data on error."""
        # Get connection for transaction
        conn = playoff_db_api.db.get_connection()
        conn.execute("BEGIN")

        # Clear playoff data within transaction
        result = playoff_db_api.clear_playoff_data(
            test_dynasty_id, test_season, connection=conn
        )
        assert isinstance(result, dict)
        assert 'events_deleted' in result
        assert 'brackets_deleted' in result
        assert 'seedings_deleted' in result
        assert 'total_deleted' in result
        assert result['total_deleted'] > 0

        # Rollback transaction
        conn.rollback()

        # Verify data still exists (rollback worked)
        assert playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert playoff_db_api.seeding_exists(test_dynasty_id, test_season)

    def test_multiple_clears_idempotent(
        self, playoff_db_api, sample_playoff_data, test_dynasty_id, test_season
    ):
        """Test that multiple clear operations are idempotent."""
        # First clear
        result1 = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)
        assert isinstance(result1, dict)
        assert result1['total_deleted'] > 0  # Data was deleted

        # Second clear (no data exists)
        result2 = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)
        assert isinstance(result2, dict)
        assert result2['total_deleted'] == 0  # No data to delete

        # Third clear (still no data)
        result3 = playoff_db_api.clear_playoff_data(test_dynasty_id, test_season)
        assert isinstance(result3, dict)
        assert result3['total_deleted'] == 0  # No data to delete

        # All should succeed, data should still not exist
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

    def test_bracket_without_seeding(
        self, playoff_db_api, playoff_db_path, test_dynasty_id, test_season
    ):
        """Test scenario where bracket exists but no seedings."""
        # Insert only bracket
        db_conn = DatabaseConnection(playoff_db_path)
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO playoff_brackets
            (dynasty_id, season, round_name, game_number, conference, home_seed, away_seed, home_team_id, away_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'wild_card', 1, 'AFC', 1, 2, 1, 2)
        )
        conn.commit()

        # Bracket exists, seeding doesn't
        assert playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert not playoff_db_api.seeding_exists(test_dynasty_id, test_season)

    def test_seeding_without_bracket(
        self, playoff_db_api, playoff_db_path, test_dynasty_id, test_season
    ):
        """Test scenario where seedings exist but no bracket."""
        # Insert only seedings
        db_conn = DatabaseConnection(playoff_db_path)
        conn = db_conn.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO playoff_seedings
            (dynasty_id, season, conference, seed_number, team_id, wins, losses, ties, division_winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_dynasty_id, test_season, 'AFC', 1, 1, 14, 3, 0, 1)
        )
        conn.commit()

        # Seeding exists, bracket doesn't
        assert not playoff_db_api.bracket_exists(test_dynasty_id, test_season)
        assert playoff_db_api.seeding_exists(test_dynasty_id, test_season)
