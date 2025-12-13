"""
Integration tests for OwnerService.

Part of Milestone 13: Owner Review, Tollgate 4.
Tests end-to-end functionality of the owner service layer.
"""

import os
import sqlite3
import tempfile
import pytest

from src.game_cycle.services.owner_service import OwnerService


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables manually (without FK enforcement)
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS team_staff_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            season INTEGER NOT NULL,
            gm_id TEXT NOT NULL,
            gm_name TEXT NOT NULL,
            gm_archetype_key TEXT NOT NULL,
            gm_custom_traits TEXT,
            gm_history TEXT,
            gm_hire_season INTEGER NOT NULL,
            hc_id TEXT NOT NULL,
            hc_name TEXT NOT NULL,
            hc_archetype_key TEXT NOT NULL,
            hc_custom_traits TEXT,
            hc_history TEXT,
            hc_hire_season INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, season)
        );

        CREATE TABLE IF NOT EXISTS staff_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            season INTEGER NOT NULL,
            candidate_id TEXT NOT NULL,
            staff_type TEXT NOT NULL CHECK(staff_type IN ('GM', 'HC')),
            name TEXT NOT NULL,
            archetype_key TEXT NOT NULL,
            custom_traits TEXT,
            history TEXT,
            is_selected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
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
            -- Tollgate 1: Offseason Directives fields
            team_philosophy TEXT DEFAULT 'maintain' CHECK(team_philosophy IN ('win_now', 'maintain', 'rebuild')),
            budget_stance TEXT DEFAULT 'moderate' CHECK(budget_stance IN ('aggressive', 'moderate', 'conservative')),
            protected_player_ids TEXT DEFAULT '[]',
            expendable_player_ids TEXT DEFAULT '[]',
            owner_notes TEXT DEFAULT '',
            trust_gm INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, season)
        );

        CREATE INDEX IF NOT EXISTS idx_staff_assignments_dynasty ON team_staff_assignments(dynasty_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_staff_assignments_season ON team_staff_assignments(dynasty_id, season);
        CREATE INDEX IF NOT EXISTS idx_staff_candidates_dynasty ON staff_candidates(dynasty_id, team_id, season);
        CREATE INDEX IF NOT EXISTS idx_staff_candidates_type ON staff_candidates(dynasty_id, staff_type);
        CREATE INDEX IF NOT EXISTS idx_owner_directives_dynasty ON owner_directives(dynasty_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_owner_directives_season ON owner_directives(dynasty_id, season);

        -- Insert test dynasty
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def service(db_path):
    """Create an OwnerService instance."""
    return OwnerService(db_path, 'test-dynasty', 2025)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def team_id():
    """Standard test team ID."""
    return 1


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


# ============================================
# Tests for get_current_staff
# ============================================

class TestGetCurrentStaff:
    """Tests for get_current_staff method."""

    def test_returns_none_for_new_dynasty(self, service, team_id):
        """New dynasty has no staff assignment."""
        result = service.get_current_staff(team_id)
        assert result is None

    def test_returns_staff_after_initialization(self, service, team_id):
        """Returns gm/hc after initialize_default_staff."""
        service.initialize_default_staff(team_id)
        result = service.get_current_staff(team_id)

        assert result is not None
        assert "gm" in result
        assert "hc" in result

    def test_returns_correct_staff_data(self, service, team_id):
        """Returned staff has all required fields."""
        service.initialize_default_staff(team_id)
        result = service.get_current_staff(team_id)

        # Check GM fields
        gm = result["gm"]
        assert hasattr(gm, "staff_id") or "staff_id" in gm.__dict__
        assert hasattr(gm, "name")
        assert hasattr(gm, "archetype_key")

        # Check HC fields
        hc = result["hc"]
        assert hasattr(hc, "staff_id") or "staff_id" in hc.__dict__
        assert hasattr(hc, "name")
        assert hasattr(hc, "archetype_key")


# ============================================
# Tests for fire_gm
# ============================================

class TestFireGM:
    """Tests for fire_gm method."""

    def test_generates_3_to_5_candidates(self, service, team_id):
        """fire_gm returns 3-5 candidates."""
        # Initialize staff first so there's something to fire
        service.initialize_default_staff(team_id)

        candidates = service.fire_gm(team_id)
        assert 3 <= len(candidates) <= 5

    def test_excludes_current_archetype(self, service, team_id):
        """Candidates don't include fired GM's archetype."""
        service.initialize_default_staff(team_id)
        current = service.get_current_staff(team_id)
        current_archetype = current["gm"].archetype_key

        candidates = service.fire_gm(team_id)
        archetypes = [c["archetype_key"] for c in candidates]
        assert current_archetype not in archetypes

    def test_saves_candidates_to_database(self, service, team_id):
        """Candidates are retrievable after fire_gm."""
        service.initialize_default_staff(team_id)
        fired_candidates = service.fire_gm(team_id)

        retrieved = service.get_gm_candidates(team_id)
        assert len(retrieved) == len(fired_candidates)

    def test_candidates_have_required_fields(self, service, team_id):
        """Each candidate has staff_id, name, archetype_key, etc."""
        service.initialize_default_staff(team_id)
        candidates = service.fire_gm(team_id)

        for c in candidates:
            assert "staff_id" in c
            assert "name" in c
            assert "archetype_key" in c
            assert "custom_traits" in c
            assert "history" in c


# ============================================
# Tests for hire_gm
# ============================================

class TestHireGM:
    """Tests for hire_gm method."""

    def test_updates_staff_assignment(self, service, team_id):
        """hire_gm updates database with selected candidate."""
        service.initialize_default_staff(team_id)
        candidates = service.fire_gm(team_id)
        candidate_id = candidates[0]["staff_id"]

        hired = service.hire_gm(team_id, candidate_id)
        assert hired["staff_id"] == candidate_id

        # Verify in database
        current = service.get_current_staff(team_id)
        assert current["gm"].staff_id == candidate_id

    def test_clears_candidates_after_hire(self, service, team_id):
        """Candidate pool is cleared after hiring."""
        service.initialize_default_staff(team_id)
        candidates = service.fire_gm(team_id)
        candidate_id = candidates[0]["staff_id"]

        service.hire_gm(team_id, candidate_id)

        remaining = service.get_gm_candidates(team_id)
        assert len(remaining) == 0

    def test_raises_for_invalid_candidate(self, service, team_id):
        """ValueError raised for non-existent candidate_id."""
        service.initialize_default_staff(team_id)
        service.fire_gm(team_id)

        with pytest.raises(ValueError, match="not found"):
            service.hire_gm(team_id, "invalid-uuid")

    def test_preserves_current_hc(self, service, team_id):
        """Hiring GM doesn't change HC assignment."""
        service.initialize_default_staff(team_id)
        original_hc_id = service.get_current_staff(team_id)["hc"].staff_id

        candidates = service.fire_gm(team_id)
        service.hire_gm(team_id, candidates[0]["staff_id"])

        new_hc_id = service.get_current_staff(team_id)["hc"].staff_id
        assert new_hc_id == original_hc_id


# ============================================
# Tests for Directives
# ============================================

class TestDirectives:
    """Tests for directive management."""

    def test_get_returns_none_initially(self, service, team_id):
        """No directives exist for new dynasty."""
        result = service.get_directives(team_id)
        assert result is None

    def test_save_and_get_roundtrip(self, service, team_id):
        """Saved directives can be retrieved."""
        directives = {
            "target_wins": 10,
            "draft_strategy": "bpa",
            "priority_positions": ["QB", "EDGE"],
        }
        service.save_directives(team_id, directives)

        result = service.get_directives(team_id)
        assert result is not None
        assert result["target_wins"] == 10
        assert result["draft_strategy"] == "bpa"

    def test_directives_for_next_season(self, service, team_id, season):
        """Directives are saved for season + 1."""
        directives = {"target_wins": 12}
        service.save_directives(team_id, directives)

        # Service is for 2025, directives should be for 2026
        result = service.get_directives(team_id)
        assert result["season"] == season + 1

    def test_directives_persist_all_fields(self, service, team_id):
        """All directive fields are persisted correctly."""
        directives = {
            "target_wins": 11,
            "priority_positions": ["CB", "WR", "TE"],
            "fa_wishlist": ["Player A"],
            "draft_wishlist": ["Prospect X", "Prospect Y"],
            "draft_strategy": "position_focus",
            "fa_philosophy": "aggressive",
            "max_contract_years": 4,
            "max_guaranteed_percent": 0.65,
        }
        service.save_directives(team_id, directives)

        result = service.get_directives(team_id)
        assert result["target_wins"] == 11
        assert result["priority_positions"] == ["CB", "WR", "TE"]
        assert result["draft_strategy"] == "position_focus"
        assert result["fa_philosophy"] == "aggressive"
        assert result["max_contract_years"] == 4
        assert result["max_guaranteed_percent"] == 0.65


# ============================================
# Tests for Initialization
# ============================================

class TestInitialization:
    """Tests for staff initialization."""

    def test_initialize_default_staff(self, service, team_id):
        """Creates default GM and HC."""
        result = service.initialize_default_staff(team_id)

        assert "gm" in result
        assert "hc" in result
        assert result["gm"]["name"] == "Default GM"
        assert result["hc"]["name"] == "Default HC"

    def test_ensure_staff_exists_creates_defaults(self, service, team_id):
        """Creates defaults when no staff exists."""
        result = service.ensure_staff_exists(team_id)

        assert result is not None
        assert "gm" in result or hasattr(result.get("gm"), "name")

    def test_ensure_staff_exists_returns_existing(self, service, team_id):
        """Returns existing staff without modification."""
        # Initialize first
        service.initialize_default_staff(team_id)
        original = service.get_current_staff(team_id)
        original_gm_id = original["gm"].staff_id

        # Call ensure_staff_exists
        result = service.ensure_staff_exists(team_id)
        new_gm_id = result["gm"].staff_id if hasattr(result["gm"], "staff_id") else result["gm"]["staff_id"]

        assert new_gm_id == original_gm_id


# ============================================
# Tests for HC Operations
# ============================================

class TestHCOperations:
    """Tests for Head Coach operations."""

    def test_fire_hc_generates_candidates(self, service, team_id):
        """fire_hc works same as fire_gm."""
        service.initialize_default_staff(team_id)

        candidates = service.fire_hc(team_id)
        assert 3 <= len(candidates) <= 5

        for c in candidates:
            assert "staff_id" in c
            assert "name" in c
            assert "archetype_key" in c

    def test_hire_hc_updates_assignment(self, service, team_id):
        """hire_hc updates database correctly."""
        service.initialize_default_staff(team_id)
        original_gm_id = service.get_current_staff(team_id)["gm"].staff_id

        candidates = service.fire_hc(team_id)
        candidate_id = candidates[0]["staff_id"]

        hired = service.hire_hc(team_id, candidate_id)
        assert hired["staff_id"] == candidate_id

        # Verify HC updated and GM preserved
        current = service.get_current_staff(team_id)
        assert current["hc"].staff_id == candidate_id
        assert current["gm"].staff_id == original_gm_id
