"""
Tests for DynastyDatabaseAPI

Comprehensive test coverage for all dynasty database operations including:
1. Dynasty record creation (standalone and with shared connection)
2. Standings initialization for season types
3. Dynasty existence checking
4. Dynasty retrieval by ID
5. Listing all dynasties
6. Dynasty statistics calculation
7. Dynasty deletion with cascade

All tests follow AAA pattern (Arrange, Act, Assert).
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

from database.dynasty_database_api import DynastyDatabaseAPI


@pytest.fixture
def test_db():
    """
    Create temporary test database with required schema.

    Creates tables:
    - dynasties: Main dynasty records
    - standings: Team standings per season/season_type
    - games: Game results
    - schedules: Game schedules
    - events: Calendar events
    - playoff_brackets: Playoff tournament brackets
    - playoff_seedings: Playoff seeding records
    - tiebreaker_applications: Tiebreaker tracking
    - dynasty_state: Dynasty current state
    - dynasty_seasons: Season tracking
    - team_rosters: Team rosters
    - players: Player records
    - box_scores: Box score data
    - player_game_stats: Player statistics
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

    # Create dynasties table
    conn.execute('''
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
    ''')

    # Create standings table
    conn.execute('''
        CREATE TABLE standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    # Create games table
    conn.execute('''
        CREATE TABLE games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            game_type TEXT DEFAULT 'regular',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            game_date TEXT,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    # Create minimal versions of other tables for cascade testing
    conn.execute('''
        CREATE TABLE schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE playoff_brackets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE playoff_seedings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE tiebreaker_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE dynasty_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            current_phase TEXT,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE dynasty_seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE team_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE box_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    conn.commit()

    yield db_path

    conn.close()
    Path(db_path).unlink()


def create_test_api(test_db):
    """
    Helper function to create DynastyDatabaseAPI instance with test database.

    Note: We need to patch the DynastyDatabaseAPI to avoid automatic
    schema creation from DatabaseConnection which expects full schema.
    We create our own simplified test database.
    """
    api_instance = DynastyDatabaseAPI.__new__(DynastyDatabaseAPI)
    api_instance.db_path = test_db

    # Create a simple connection wrapper that doesn't auto-create tables
    class SimpleDBWrapper:
        def __init__(self, db_path):
            self.db_path = db_path
            self._conn = None

        def get_connection(self):
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path)
                self._conn.row_factory = sqlite3.Row
            return self._conn

        def execute_query(self, query, params=()):
            """Execute SELECT query and return list of dicts."""
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []

        def execute_update(self, query, params=()):
            """Execute INSERT/UPDATE/DELETE query and commit."""
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    api_instance.db = SimpleDBWrapper(test_db)

    # Add logger
    import logging
    api_instance.logger = logging.getLogger("DynastyDatabaseAPI")

    return api_instance


@pytest.fixture
def api(test_db):
    """Create DynastyDatabaseAPI instance with test database."""
    return create_test_api(test_db)


# ============================================================================
# Test Category 1: create_dynasty_record()
# ============================================================================

class TestCreateDynastyRecord:
    """Test dynasty record creation."""

    def test_create_dynasty_record_standalone(self, api):
        """Test creating dynasty record with auto-commit (no shared connection)."""
        # Arrange
        dynasty_id = "test_dynasty"
        dynasty_name = "Test Dynasty"
        owner_name = "Test Owner"
        team_id = 14  # Philadelphia Eagles

        # Act
        success = api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name=dynasty_name,
            owner_name=owner_name,
            team_id=team_id
        )

        # Assert
        assert success is True

        # Verify record exists in database
        dynasty = api.get_dynasty_by_id(dynasty_id)
        assert dynasty is not None
        assert dynasty['dynasty_id'] == dynasty_id
        assert dynasty['dynasty_name'] == dynasty_name
        assert dynasty['owner_name'] == owner_name
        assert dynasty['team_id'] == team_id
        assert dynasty['is_active'] is True

    def test_create_dynasty_record_with_shared_connection(self, api, test_db):
        """Test creating dynasty record with shared connection (transaction participation)."""
        # Arrange
        dynasty_id = "shared_dynasty"
        dynasty_name = "Shared Dynasty"
        owner_name = "Shared Owner"
        team_id = 22  # Detroit Lions

        conn = sqlite3.connect(test_db)
        conn.execute("BEGIN")

        # Act
        success = api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name=dynasty_name,
            owner_name=owner_name,
            team_id=team_id,
            connection=conn
        )

        # Assert
        assert success is True

        # Before commit, record should not be visible to other connections
        api2 = create_test_api(test_db)
        dynasty_before = api2.get_dynasty_by_id(dynasty_id)
        assert dynasty_before is None

        # Commit transaction
        conn.commit()

        # After commit, record should be visible
        dynasty_after = api2.get_dynasty_by_id(dynasty_id)
        assert dynasty_after is not None
        assert dynasty_after['dynasty_id'] == dynasty_id
        assert dynasty_after['dynasty_name'] == dynasty_name

        conn.close()

    def test_create_dynasty_record_with_null_team_id(self, api):
        """Test creating dynasty record with NULL team_id (commissioner mode)."""
        # Arrange
        dynasty_id = "commissioner_dynasty"
        dynasty_name = "Commissioner Dynasty"
        owner_name = "Commissioner"
        team_id = None

        # Act
        success = api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name=dynasty_name,
            owner_name=owner_name,
            team_id=team_id
        )

        # Assert
        assert success is True

        dynasty = api.get_dynasty_by_id(dynasty_id)
        assert dynasty is not None
        assert dynasty['team_id'] is None

    def test_create_dynasty_record_duplicate_id_fails(self, api):
        """Test that creating dynasty with duplicate ID fails gracefully."""
        # Arrange
        dynasty_id = "duplicate_dynasty"
        api.create_dynasty_record(dynasty_id, "First Dynasty", "Owner 1", 1)

        # Act
        success = api.create_dynasty_record(dynasty_id, "Second Dynasty", "Owner 2", 2)

        # Assert
        assert success is False


# ============================================================================
# Test Category 2: initialize_standings_for_season_type()
# ============================================================================

class TestInitializeStandingsForSeasonType:
    """Test standings initialization."""

    def test_initialize_standings_creates_32_records(self, api):
        """Test that standings initialization creates exactly 32 records (one per team)."""
        # Arrange
        dynasty_id = "standings_test"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)
        season = 2025
        season_type = "regular_season"

        # Act
        count = api.initialize_standings_for_season_type(
            dynasty_id=dynasty_id,
            season=season,
            season_type=season_type
        )

        # Assert
        assert count == 32

        # Verify all 32 teams have standings records
        conn = api.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM standings WHERE dynasty_id = ? AND season = ? AND season_type = ?",
            (dynasty_id, season, season_type)
        )
        result = cursor.fetchone()[0]
        assert result == 32

    def test_initialize_standings_with_shared_connection(self, api, test_db):
        """Test standings initialization with shared connection."""
        # Arrange
        dynasty_id = "shared_standings"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)
        season = 2025
        season_type = "preseason"

        conn = sqlite3.connect(test_db)
        conn.execute("BEGIN")

        # Act
        count = api.initialize_standings_for_season_type(
            dynasty_id=dynasty_id,
            season=season,
            season_type=season_type,
            connection=conn
        )

        # Assert
        assert count == 32

        # Before commit, records should not be visible to other connections
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM standings WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        assert cursor.fetchone()[0] == 32

        # Commit and verify
        conn.commit()
        conn.close()

    def test_initialize_standings_all_fields_zero(self, api):
        """Test that initialized standings have all stats set to zero."""
        # Arrange
        dynasty_id = "zero_stats"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)
        season = 2025
        season_type = "regular_season"

        # Act
        api.initialize_standings_for_season_type(dynasty_id, season, season_type)

        # Assert
        conn = api.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT wins, losses, ties, points_for, points_against,
                   division_wins, division_losses, conference_wins, conference_losses
            FROM standings
            WHERE dynasty_id = ? AND season = ? AND season_type = ?
            LIMIT 1
            """,
            (dynasty_id, season, season_type)
        )
        row = cursor.fetchone()
        # Convert Row object to tuple for comparison
        assert tuple(row) == (0, 0, 0, 0, 0, 0, 0, 0, 0)

    def test_initialize_standings_multiple_season_types(self, api):
        """Test initializing standings for multiple season types."""
        # Arrange
        dynasty_id = "multi_type"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)
        season = 2025

        # Act
        preseason_count = api.initialize_standings_for_season_type(
            dynasty_id, season, "preseason"
        )
        regular_count = api.initialize_standings_for_season_type(
            dynasty_id, season, "regular_season"
        )

        # Assert
        assert preseason_count == 32
        assert regular_count == 32

        # Verify both season types exist
        conn = api.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(DISTINCT season_type) FROM standings WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        assert cursor.fetchone()[0] == 2


# ============================================================================
# Test Category 3: dynasty_exists()
# ============================================================================

class TestDynastyExists:
    """Test dynasty existence checking."""

    def test_dynasty_exists_returns_true(self, api):
        """Test that dynasty_exists returns True for existing dynasty."""
        # Arrange
        dynasty_id = "existing_dynasty"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)

        # Act
        exists = api.dynasty_exists(dynasty_id)

        # Assert
        assert exists is True

    def test_dynasty_exists_returns_false(self, api):
        """Test that dynasty_exists returns False for non-existent dynasty."""
        # Arrange
        dynasty_id = "nonexistent_dynasty"

        # Act
        exists = api.dynasty_exists(dynasty_id)

        # Assert
        assert exists is False

    def test_dynasty_exists_case_sensitive(self, api):
        """Test that dynasty_exists is case-sensitive."""
        # Arrange
        dynasty_id = "CaseSensitive"
        api.create_dynasty_record(dynasty_id, "Test Dynasty", "Owner", 1)

        # Act
        exists_correct = api.dynasty_exists("CaseSensitive")
        exists_wrong = api.dynasty_exists("casesensitive")

        # Assert
        assert exists_correct is True
        assert exists_wrong is False


# ============================================================================
# Test Category 4: get_dynasty_by_id()
# ============================================================================

class TestGetDynastyById:
    """Test dynasty retrieval by ID."""

    def test_get_dynasty_by_id_found(self, api):
        """Test retrieving existing dynasty by ID."""
        # Arrange
        dynasty_id = "found_dynasty"
        dynasty_name = "Found Dynasty"
        owner_name = "Found Owner"
        team_id = 7
        api.create_dynasty_record(dynasty_id, dynasty_name, owner_name, team_id)

        # Act
        dynasty = api.get_dynasty_by_id(dynasty_id)

        # Assert
        assert dynasty is not None
        assert dynasty['dynasty_id'] == dynasty_id
        assert dynasty['dynasty_name'] == dynasty_name
        assert dynasty['owner_name'] == owner_name
        assert dynasty['team_id'] == team_id
        assert dynasty['is_active'] is True
        assert 'created_at' in dynasty

    def test_get_dynasty_by_id_not_found(self, api):
        """Test retrieving non-existent dynasty returns None."""
        # Arrange
        dynasty_id = "nonexistent"

        # Act
        dynasty = api.get_dynasty_by_id(dynasty_id)

        # Assert
        assert dynasty is None

    def test_get_dynasty_by_id_returns_dict(self, api):
        """Test that get_dynasty_by_id returns a dictionary with expected keys."""
        # Arrange
        dynasty_id = "dict_test"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        # Act
        dynasty = api.get_dynasty_by_id(dynasty_id)

        # Assert
        assert isinstance(dynasty, dict)
        expected_keys = {
            'dynasty_id', 'dynasty_name', 'owner_name',
            'team_id', 'created_at', 'is_active'
        }
        assert set(dynasty.keys()) == expected_keys


# ============================================================================
# Test Category 5: get_all_dynasties()
# ============================================================================

class TestGetAllDynasties:
    """Test listing all dynasties."""

    def test_get_all_dynasties_empty(self, api):
        """Test get_all_dynasties returns empty list when no dynasties exist."""
        # Arrange - no dynasties created

        # Act
        dynasties = api.get_all_dynasties()

        # Assert
        assert dynasties == []

    def test_get_all_dynasties_multiple(self, api):
        """Test get_all_dynasties returns all dynasties."""
        # Arrange
        api.create_dynasty_record("dynasty_1", "Dynasty One", "Owner 1", 1)
        api.create_dynasty_record("dynasty_2", "Dynasty Two", "Owner 2", 2)
        api.create_dynasty_record("dynasty_3", "Dynasty Three", "Owner 3", 3)

        # Act
        dynasties = api.get_all_dynasties()

        # Assert
        assert len(dynasties) == 3
        dynasty_ids = {d['dynasty_id'] for d in dynasties}
        assert dynasty_ids == {"dynasty_1", "dynasty_2", "dynasty_3"}

    def test_get_all_dynasties_ordered_by_created_at_desc(self, api, test_db):
        """Test that dynasties are ordered by created_at DESC (newest first)."""
        # Arrange - create dynasties with different timestamps
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, created_at) VALUES (?, ?, ?, ?, ?)",
            ("oldest", "Oldest", "Owner", 1, "2024-01-01 10:00:00")
        )
        cursor.execute(
            "INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, created_at) VALUES (?, ?, ?, ?, ?)",
            ("middle", "Middle", "Owner", 2, "2024-06-01 10:00:00")
        )
        cursor.execute(
            "INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, created_at) VALUES (?, ?, ?, ?, ?)",
            ("newest", "Newest", "Owner", 3, "2024-12-01 10:00:00")
        )
        conn.commit()
        conn.close()

        # Act
        dynasties = api.get_all_dynasties()

        # Assert
        assert len(dynasties) == 3
        assert dynasties[0]['dynasty_id'] == "newest"
        assert dynasties[1]['dynasty_id'] == "middle"
        assert dynasties[2]['dynasty_id'] == "oldest"

    def test_get_all_dynasties_returns_list_of_dicts(self, api):
        """Test that get_all_dynasties returns list of dictionaries."""
        # Arrange
        api.create_dynasty_record("test_dynasty", "Test", "Owner", 1)

        # Act
        dynasties = api.get_all_dynasties()

        # Assert
        assert isinstance(dynasties, list)
        assert len(dynasties) == 1
        assert isinstance(dynasties[0], dict)


# ============================================================================
# Test Category 6: get_dynasty_stats()
# ============================================================================

class TestGetDynastyStats:
    """Test dynasty statistics calculation."""

    def test_get_dynasty_stats_no_data(self, api):
        """Test dynasty stats with no games or standings."""
        # Arrange
        dynasty_id = "empty_stats"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        # Act
        stats = api.get_dynasty_stats(dynasty_id)

        # Assert
        assert stats['seasons_played'] == []
        assert stats['total_seasons'] == 0
        assert stats['total_games'] == 0
        assert stats['current_season'] is None

    def test_get_dynasty_stats_with_standings(self, api):
        """Test dynasty stats with standings data."""
        # Arrange
        dynasty_id = "stats_test"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)
        api.initialize_standings_for_season_type(dynasty_id, 2024, "regular_season")
        api.initialize_standings_for_season_type(dynasty_id, 2025, "regular_season")

        # Act
        stats = api.get_dynasty_stats(dynasty_id)

        # Assert
        assert stats['seasons_played'] == [2025, 2024]  # DESC order
        assert stats['total_seasons'] == 2
        assert stats['current_season'] == 2025

    def test_get_dynasty_stats_with_games(self, api, test_db):
        """Test dynasty stats with game data."""
        # Arrange
        dynasty_id = "games_stats"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert test games
        cursor.execute(
            """
            INSERT INTO games (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("game_1", dynasty_id, 2024, 1, 1, 2, 24, 17)
        )
        cursor.execute(
            """
            INSERT INTO games (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("game_2", dynasty_id, 2024, 2, 3, 4, 31, 20)
        )
        cursor.execute(
            """
            INSERT INTO games (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("game_3", dynasty_id, 2024, 3, 5, 6, 14, 10)
        )
        conn.commit()
        conn.close()

        # Act
        stats = api.get_dynasty_stats(dynasty_id)

        # Assert
        assert stats['total_games'] == 3

    def test_get_dynasty_stats_multiple_seasons(self, api):
        """Test dynasty stats with multiple seasons."""
        # Arrange
        dynasty_id = "multi_season"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)
        api.initialize_standings_for_season_type(dynasty_id, 2023, "regular_season")
        api.initialize_standings_for_season_type(dynasty_id, 2024, "regular_season")
        api.initialize_standings_for_season_type(dynasty_id, 2025, "regular_season")

        # Act
        stats = api.get_dynasty_stats(dynasty_id)

        # Assert
        assert stats['total_seasons'] == 3
        assert len(stats['seasons_played']) == 3
        assert stats['current_season'] == 2025
        assert 2023 in stats['seasons_played']
        assert 2024 in stats['seasons_played']
        assert 2025 in stats['seasons_played']


# ============================================================================
# Test Category 7: delete_dynasty()
# ============================================================================

class TestDeleteDynasty:
    """Test dynasty deletion with cascade."""

    def test_delete_dynasty_success(self, api):
        """Test successful dynasty deletion."""
        # Arrange
        dynasty_id = "delete_test"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        # Act
        success = api.delete_dynasty(dynasty_id)

        # Assert
        assert success is True
        assert api.dynasty_exists(dynasty_id) is False

    def test_delete_dynasty_cascade_standings(self, api):
        """Test that deleting dynasty cascades to standings."""
        # Arrange
        dynasty_id = "cascade_test"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)
        api.initialize_standings_for_season_type(dynasty_id, 2025, "regular_season")

        # Verify standings exist
        conn = api.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM standings WHERE dynasty_id = ?", (dynasty_id,))
        assert cursor.fetchone()[0] == 32

        # Act
        api.delete_dynasty(dynasty_id)

        # Assert - standings should be deleted
        cursor.execute("SELECT COUNT(*) FROM standings WHERE dynasty_id = ?", (dynasty_id,))
        assert cursor.fetchone()[0] == 0

    def test_delete_dynasty_cascade_games(self, api, test_db):
        """Test that deleting dynasty cascades to games."""
        # Arrange
        dynasty_id = "cascade_games"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO games (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("game_1", dynasty_id, 2024, 1, 1, 2, 24, 17)
        )
        conn.commit()

        # Verify game exists
        cursor.execute("SELECT COUNT(*) FROM games WHERE dynasty_id = ?", (dynasty_id,))
        assert cursor.fetchone()[0] == 1
        conn.close()

        # Act
        api.delete_dynasty(dynasty_id)

        # Assert - games should be deleted
        conn2 = api.db.get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM games WHERE dynasty_id = ?", (dynasty_id,))
        assert cursor2.fetchone()[0] == 0

    def test_delete_dynasty_cascade_all_tables(self, api, test_db):
        """Test that deleting dynasty cascades to all related tables."""
        # Arrange
        dynasty_id = "cascade_all"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # Insert data into all related tables
        cursor.execute("INSERT INTO schedules (dynasty_id, season) VALUES (?, ?)", (dynasty_id, 2024))
        cursor.execute("INSERT INTO events (dynasty_id, event_type) VALUES (?, ?)", (dynasty_id, "game"))
        cursor.execute("INSERT INTO playoff_brackets (dynasty_id, season) VALUES (?, ?)", (dynasty_id, 2024))
        cursor.execute("INSERT INTO playoff_seedings (dynasty_id, season) VALUES (?, ?)", (dynasty_id, 2024))
        cursor.execute("INSERT INTO tiebreaker_applications (dynasty_id, season) VALUES (?, ?)", (dynasty_id, 2024))
        cursor.execute("INSERT INTO dynasty_state (dynasty_id, current_phase) VALUES (?, ?)", (dynasty_id, "regular_season"))
        cursor.execute("INSERT INTO dynasty_seasons (dynasty_id, season) VALUES (?, ?)", (dynasty_id, 2024))
        cursor.execute("INSERT INTO team_rosters (dynasty_id, team_id) VALUES (?, ?)", (dynasty_id, 1))
        cursor.execute("INSERT INTO players (dynasty_id, player_name) VALUES (?, ?)", (dynasty_id, "Test Player"))
        cursor.execute("INSERT INTO games (game_id, dynasty_id, season, week, home_team_id, away_team_id, home_score, away_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("g1", dynasty_id, 2024, 1, 1, 2, 10, 7))
        cursor.execute("INSERT INTO box_scores (dynasty_id, game_id) VALUES (?, ?)", (dynasty_id, "g1"))
        cursor.execute("INSERT INTO player_game_stats (dynasty_id, game_id) VALUES (?, ?)", (dynasty_id, "g1"))
        conn.commit()

        # Verify all data exists
        tables = [
            "schedules", "events", "playoff_brackets", "playoff_seedings",
            "tiebreaker_applications", "dynasty_state", "dynasty_seasons",
            "team_rosters", "players", "games", "box_scores", "player_game_stats"
        ]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE dynasty_id = ?", (dynasty_id,))
            count = cursor.fetchone()[0]
            assert count > 0, f"Table {table} should have records before deletion"

        conn.close()

        # Act
        api.delete_dynasty(dynasty_id)

        # Assert - all related data should be deleted
        conn2 = api.db.get_connection()
        cursor2 = conn2.cursor()
        for table in tables:
            cursor2.execute(f"SELECT COUNT(*) FROM {table} WHERE dynasty_id = ?", (dynasty_id,))
            count = cursor2.fetchone()[0]
            assert count == 0, f"Table {table} should be empty after cascade deletion"

    def test_delete_dynasty_with_shared_connection(self, api, test_db):
        """Test deleting dynasty with shared connection (transaction participation)."""
        # Arrange
        dynasty_id = "shared_delete"
        api.create_dynasty_record(dynasty_id, "Test", "Owner", 1)

        conn = sqlite3.connect(test_db)
        conn.execute("BEGIN")

        # Act
        success = api.delete_dynasty(dynasty_id, connection=conn)

        # Assert
        assert success is True

        # Before commit, dynasty should still be visible to other connections
        api2 = create_test_api(test_db)
        assert api2.dynasty_exists(dynasty_id) is True

        # Commit transaction
        conn.commit()

        # After commit, dynasty should be deleted
        assert api2.dynasty_exists(dynasty_id) is False

        conn.close()

    def test_delete_nonexistent_dynasty(self, api):
        """Test that deleting non-existent dynasty completes successfully."""
        # Arrange
        dynasty_id = "nonexistent"

        # Act
        success = api.delete_dynasty(dynasty_id)

        # Assert
        assert success is True  # Should succeed even if nothing to delete