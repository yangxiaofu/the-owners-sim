"""
Unit tests for OwnerDirectivesAPI.

Part of Milestone 13: Owner Review, Tollgate 2: Database API Classes.
"""
import json
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.owner_directives_api import OwnerDirectivesAPI
from src.game_cycle.models.owner_directives import OwnerDirectives


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS owner_directives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            season INTEGER NOT NULL,
            target_wins INTEGER CHECK(target_wins BETWEEN 0 AND 17),
            priority_positions TEXT,
            fa_wishlist TEXT,
            draft_wishlist TEXT,
            draft_strategy TEXT DEFAULT 'balanced',
            fa_philosophy TEXT DEFAULT 'balanced',
            max_contract_years INTEGER DEFAULT 5,
            max_guaranteed_percent REAL DEFAULT 0.75,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, season)
        );

        CREATE INDEX IF NOT EXISTS idx_owner_directives_dynasty ON owner_directives(dynasty_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_owner_directives_season ON owner_directives(dynasty_id, season);

        -- Insert test dynasty
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other-dynasty', 'Other Dynasty', 2);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def db(db_path):
    """Create a GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create an OwnerDirectivesAPI instance."""
    return OwnerDirectivesAPI(db)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


# ============================================
# Tests for get_directives
# ============================================

class TestGetDirectives:
    """Tests for get_directives method."""

    def test_get_returns_none_for_missing(self, api, dynasty_id, season):
        """Getting non-existent directives should return None."""
        result = api.get_directives(dynasty_id, team_id=1, season=season)
        assert result is None

    def test_get_returns_directives_when_exists(self, api, dynasty_id, season):
        """Getting existing directives should return OwnerDirectives."""
        # Save first
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            target_wins=10,
            draft_strategy="bpa",
        )
        api.save_directives(directives)

        # Get and verify
        result = api.get_directives(dynasty_id, team_id=1, season=season)
        assert result is not None
        assert isinstance(result, OwnerDirectives)
        assert result.target_wins == 10
        assert result.draft_strategy == "bpa"

    def test_get_deserializes_json_fields(self, api, dynasty_id, season):
        """JSON array fields should be deserialized correctly."""
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            priority_positions=["QB", "EDGE", "CB"],
            fa_wishlist=["Player A", "Player B"],
            draft_wishlist=["Prospect X"],
        )
        api.save_directives(directives)

        result = api.get_directives(dynasty_id, team_id=1, season=season)
        assert result.priority_positions == ["QB", "EDGE", "CB"]
        assert result.fa_wishlist == ["Player A", "Player B"]
        assert result.draft_wishlist == ["Prospect X"]


# ============================================
# Tests for save_directives
# ============================================

class TestSaveDirectives:
    """Tests for save_directives method."""

    def test_save_inserts_new(self, api, dynasty_id, season):
        """Saving new directives should insert a row."""
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=5,
            season=season,
            target_wins=12,
        )
        result = api.save_directives(directives)
        assert result is True

        # Verify saved
        fetched = api.get_directives(dynasty_id, team_id=5, season=season)
        assert fetched is not None
        assert fetched.target_wins == 12

    def test_save_updates_existing(self, api, dynasty_id, season):
        """Saving existing directives should update the row."""
        # First save
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            target_wins=8,
            draft_strategy="balanced",
        )
        api.save_directives(directives)

        # Update
        directives.target_wins = 12
        directives.draft_strategy = "bpa"
        api.save_directives(directives)

        # Verify updated
        result = api.get_directives(dynasty_id, team_id=1, season=season)
        assert result.target_wins == 12
        assert result.draft_strategy == "bpa"

    def test_save_serializes_json_fields(self, api, db, dynasty_id, season):
        """List fields should be serialized to JSON."""
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            priority_positions=["QB", "WR"],
        )
        api.save_directives(directives)

        # Verify raw JSON in database
        row = db.query_one(
            "SELECT priority_positions FROM owner_directives WHERE dynasty_id = ? AND team_id = ? AND season = ?",
            (dynasty_id, 1, season)
        )
        assert row is not None
        assert json.loads(row['priority_positions']) == ["QB", "WR"]


# ============================================
# Tests for clear_directives
# ============================================

class TestClearDirectives:
    """Tests for clear_directives method."""

    def test_clear_removes_existing(self, api, dynasty_id, season):
        """Clearing should delete the row and return 1."""
        # Save first
        directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
        )
        api.save_directives(directives)

        # Clear
        deleted = api.clear_directives(dynasty_id, team_id=1, season=season)
        assert deleted == 1

        # Verify gone
        result = api.get_directives(dynasty_id, team_id=1, season=season)
        assert result is None

    def test_clear_returns_zero_for_missing(self, api, dynasty_id, season):
        """Clearing non-existent row should return 0."""
        deleted = api.clear_directives(dynasty_id, team_id=99, season=season)
        assert deleted == 0


# ============================================
# Tests for dynasty isolation
# ============================================

class TestDynastyIsolation:
    """Tests for dynasty isolation pattern."""

    def test_directives_isolated_by_dynasty(self, api, season):
        """Directives for different dynasties should be isolated."""
        # Save for test-dynasty
        directives1 = OwnerDirectives(
            dynasty_id="test-dynasty",
            team_id=1,
            season=season,
            target_wins=10,
        )
        api.save_directives(directives1)

        # Save for other-dynasty
        directives2 = OwnerDirectives(
            dynasty_id="other-dynasty",
            team_id=1,
            season=season,
            target_wins=5,
        )
        api.save_directives(directives2)

        # Verify isolation
        result1 = api.get_directives("test-dynasty", team_id=1, season=season)
        result2 = api.get_directives("other-dynasty", team_id=1, season=season)
        assert result1.target_wins == 10
        assert result2.target_wins == 5

    def test_directives_isolated_by_team(self, api, dynasty_id, season):
        """Directives for different teams should be isolated."""
        # Save for team 1
        api.save_directives(OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=season,
            target_wins=10,
        ))

        # Save for team 2
        api.save_directives(OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=2,
            season=season,
            target_wins=6,
        ))

        # Verify isolation
        result1 = api.get_directives(dynasty_id, team_id=1, season=season)
        result2 = api.get_directives(dynasty_id, team_id=2, season=season)
        assert result1.target_wins == 10
        assert result2.target_wins == 6

    def test_directives_isolated_by_season(self, api, dynasty_id):
        """Directives for different seasons should be isolated."""
        # Save for 2025
        api.save_directives(OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=2025,
            target_wins=10,
        ))

        # Save for 2026
        api.save_directives(OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=1,
            season=2026,
            target_wins=12,
        ))

        # Verify isolation
        result1 = api.get_directives(dynasty_id, team_id=1, season=2025)
        result2 = api.get_directives(dynasty_id, team_id=1, season=2026)
        assert result1.target_wins == 10
        assert result2.target_wins == 12


# ============================================
# Tests for roundtrip serialization
# ============================================

class TestRoundtrip:
    """Tests for full roundtrip serialization."""

    def test_full_roundtrip(self, api, dynasty_id, season):
        """Full save -> get roundtrip should preserve all data."""
        original = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=15,
            season=season,
            target_wins=9,
            priority_positions=["EDGE", "CB", "WR"],
            fa_wishlist=["Player A", "Player B"],
            draft_wishlist=["Prospect X"],
            draft_strategy="position_focus",
            fa_philosophy="conservative",
            max_contract_years=3,
            max_guaranteed_percent=0.5,
        )
        api.save_directives(original)

        result = api.get_directives(dynasty_id, team_id=15, season=season)
        assert result.dynasty_id == original.dynasty_id
        assert result.team_id == original.team_id
        assert result.season == original.season
        assert result.target_wins == original.target_wins
        assert result.priority_positions == original.priority_positions
        assert result.fa_wishlist == original.fa_wishlist
        assert result.draft_wishlist == original.draft_wishlist
        assert result.draft_strategy == original.draft_strategy
        assert result.fa_philosophy == original.fa_philosophy
        assert result.max_contract_years == original.max_contract_years
        assert result.max_guaranteed_percent == original.max_guaranteed_percent
