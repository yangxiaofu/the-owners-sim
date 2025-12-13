"""
Unit tests for StaffAPI.

Part of Milestone 13: Owner Review, Tollgate 2: Database API Classes.
"""
import json
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.staff_api import StaffAPI
from src.game_cycle.models.staff_member import StaffMember, StaffCandidate, StaffType


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

        CREATE INDEX IF NOT EXISTS idx_staff_assignments_dynasty ON team_staff_assignments(dynasty_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_staff_assignments_season ON team_staff_assignments(dynasty_id, season);
        CREATE INDEX IF NOT EXISTS idx_staff_candidates_dynasty ON staff_candidates(dynasty_id, team_id, season);
        CREATE INDEX IF NOT EXISTS idx_staff_candidates_type ON staff_candidates(dynasty_id, staff_type);

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
    """Create a StaffAPI instance."""
    return StaffAPI(db)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


@pytest.fixture
def sample_gm():
    """Sample GM StaffMember."""
    return StaffMember(
        staff_id="gm-001",
        staff_type=StaffType.GM,
        name="John Smith",
        archetype_key="win_now",
        custom_traits={"aggression": 0.8},
        history="Former scout",
        hire_season=2023,
    )


@pytest.fixture
def sample_hc():
    """Sample HC StaffMember."""
    return StaffMember(
        staff_id="hc-001",
        staff_type=StaffType.HEAD_COACH,
        name="Bill Coach",
        archetype_key="balanced",
        custom_traits={"risk_tolerance": 0.6},
        history="Former coordinator",
        hire_season=2024,
    )


# ============================================
# Tests for get_staff_assignment
# ============================================

class TestStaffAssignment:
    """Tests for staff assignment methods."""

    def test_get_returns_none_for_missing(self, api, dynasty_id, season):
        """Getting non-existent assignment should return None."""
        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)
        assert result is None

    def test_get_returns_gm_and_hc(self, api, dynasty_id, season, sample_gm, sample_hc):
        """Getting existing assignment should return dict with gm and hc."""
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)
        assert result is not None
        assert 'gm' in result
        assert 'hc' in result
        assert isinstance(result['gm'], StaffMember)
        assert isinstance(result['hc'], StaffMember)

    def test_save_inserts_new(self, api, dynasty_id, season, sample_gm, sample_hc):
        """Saving new assignment should insert a row."""
        result = api.save_staff_assignment(dynasty_id, team_id=5, season=season, gm=sample_gm, hc=sample_hc)
        assert result is True

        fetched = api.get_staff_assignment(dynasty_id, team_id=5, season=season)
        assert fetched is not None
        assert fetched['gm'].name == "John Smith"

    def test_save_updates_existing(self, api, dynasty_id, season, sample_gm, sample_hc):
        """Saving existing assignment should update the row."""
        # First save
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        # Update with new HC
        new_hc = StaffMember(
            staff_id="hc-002",
            staff_type=StaffType.HEAD_COACH,
            name="New Coach",
            archetype_key="rebuilder",
            hire_season=2025,
        )
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=new_hc)

        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)
        assert result['hc'].name == "New Coach"
        assert result['hc'].archetype_key == "rebuilder"

    def test_roundtrip_preserves_data(self, api, dynasty_id, season, sample_gm, sample_hc):
        """Full roundtrip should preserve all staff data."""
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)

        # Verify GM
        gm = result['gm']
        assert gm.staff_id == sample_gm.staff_id
        assert gm.staff_type == StaffType.GM
        assert gm.name == sample_gm.name
        assert gm.archetype_key == sample_gm.archetype_key
        assert gm.custom_traits == sample_gm.custom_traits
        assert gm.history == sample_gm.history
        assert gm.hire_season == sample_gm.hire_season

        # Verify HC
        hc = result['hc']
        assert hc.staff_id == sample_hc.staff_id
        assert hc.staff_type == StaffType.HEAD_COACH
        assert hc.name == sample_hc.name


# ============================================
# Tests for staff candidates
# ============================================

class TestCandidates:
    """Tests for candidate pool methods."""

    def test_get_returns_empty_list(self, api, dynasty_id, season):
        """Getting non-existent candidates should return empty list."""
        result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert result == []

    def test_get_returns_candidates(self, api, dynasty_id, season):
        """Getting existing candidates should return list."""
        candidates = [
            StaffCandidate(staff_id="c1", name="Candidate 1", archetype_key="win_now"),
            StaffCandidate(staff_id="c2", name="Candidate 2", archetype_key="balanced"),
        ]
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=candidates)

        result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert len(result) == 2
        assert all(isinstance(c, StaffCandidate) for c in result)
        assert result[0].name == "Candidate 1"
        assert result[1].name == "Candidate 2"

    def test_get_filters_by_staff_type(self, api, dynasty_id, season):
        """Candidates should be filtered by staff type."""
        gm_candidates = [StaffCandidate(staff_id="gm1", name="GM Candidate", archetype_key="win_now")]
        hc_candidates = [StaffCandidate(staff_id="hc1", name="HC Candidate", archetype_key="balanced")]

        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=gm_candidates)
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH, candidates=hc_candidates)

        gm_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        hc_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH)

        assert len(gm_result) == 1
        assert gm_result[0].name == "GM Candidate"
        assert len(hc_result) == 1
        assert hc_result[0].name == "HC Candidate"

    def test_save_clears_old_first(self, api, dynasty_id, season):
        """Saving candidates should clear old candidates first."""
        # Save initial
        initial = [StaffCandidate(staff_id="old", name="Old Candidate", archetype_key="win_now")]
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=initial)

        # Save new (should replace)
        new = [StaffCandidate(staff_id="new", name="New Candidate", archetype_key="balanced")]
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=new)

        result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert len(result) == 1
        assert result[0].name == "New Candidate"

    def test_save_multiple_candidates(self, api, dynasty_id, season):
        """Saving multiple candidates should insert all."""
        candidates = [
            StaffCandidate(staff_id=f"c{i}", name=f"Candidate {i}", archetype_key="balanced")
            for i in range(5)
        ]
        count = api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=candidates)

        assert count == 5
        result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert len(result) == 5

    def test_clear_by_type(self, api, dynasty_id, season):
        """Clearing by type should only delete that type."""
        gm_candidates = [StaffCandidate(staff_id="gm1", name="GM", archetype_key="win_now")]
        hc_candidates = [StaffCandidate(staff_id="hc1", name="HC", archetype_key="balanced")]

        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=gm_candidates)
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH, candidates=hc_candidates)

        # Clear only GM
        deleted = api.clear_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert deleted == 1

        # Verify GM gone, HC remains
        gm_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        hc_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH)
        assert len(gm_result) == 0
        assert len(hc_result) == 1

    def test_clear_all(self, api, dynasty_id, season):
        """Clearing without type should delete all."""
        gm_candidates = [StaffCandidate(staff_id="gm1", name="GM", archetype_key="win_now")]
        hc_candidates = [StaffCandidate(staff_id="hc1", name="HC", archetype_key="balanced")]

        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=gm_candidates)
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH, candidates=hc_candidates)

        # Clear all
        deleted = api.clear_candidates(dynasty_id, team_id=1, season=season, staff_type=None)
        assert deleted == 2

        # Verify all gone
        gm_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        hc_result = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.HEAD_COACH)
        assert len(gm_result) == 0
        assert len(hc_result) == 0

    def test_mark_selected(self, api, dynasty_id, season):
        """Marking candidate selected should update is_selected."""
        candidates = [
            StaffCandidate(staff_id="c1", name="Candidate 1", archetype_key="win_now", is_selected=False),
        ]
        api.save_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM, candidates=candidates)

        result = api.mark_candidate_selected(dynasty_id, candidate_id="c1")
        assert result is True

        fetched = api.get_candidates(dynasty_id, team_id=1, season=season, staff_type=StaffType.GM)
        assert fetched[0].is_selected is True


# ============================================
# Tests for dynasty isolation
# ============================================

class TestDynastyIsolation:
    """Tests for dynasty isolation pattern."""

    def test_assignments_isolated(self, api, season, sample_gm, sample_hc):
        """Staff assignments should be isolated by dynasty."""
        # Save for test-dynasty
        api.save_staff_assignment("test-dynasty", team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        # Save for other-dynasty with different staff
        other_gm = StaffMember(staff_id="other-gm", staff_type=StaffType.GM, name="Other GM", archetype_key="rebuilder", hire_season=2020)
        other_hc = StaffMember(staff_id="other-hc", staff_type=StaffType.HEAD_COACH, name="Other HC", archetype_key="balanced", hire_season=2020)
        api.save_staff_assignment("other-dynasty", team_id=1, season=season, gm=other_gm, hc=other_hc)

        # Verify isolation
        result1 = api.get_staff_assignment("test-dynasty", team_id=1, season=season)
        result2 = api.get_staff_assignment("other-dynasty", team_id=1, season=season)
        assert result1['gm'].name == "John Smith"
        assert result2['gm'].name == "Other GM"

    def test_candidates_isolated(self, api, season):
        """Candidates should be isolated by dynasty."""
        # Save for test-dynasty
        api.save_candidates("test-dynasty", team_id=1, season=season, staff_type=StaffType.GM,
                           candidates=[StaffCandidate(staff_id="t1", name="Test Candidate", archetype_key="win_now")])

        # Save for other-dynasty
        api.save_candidates("other-dynasty", team_id=1, season=season, staff_type=StaffType.GM,
                           candidates=[StaffCandidate(staff_id="o1", name="Other Candidate", archetype_key="balanced")])

        # Verify isolation
        result1 = api.get_candidates("test-dynasty", team_id=1, season=season, staff_type=StaffType.GM)
        result2 = api.get_candidates("other-dynasty", team_id=1, season=season, staff_type=StaffType.GM)
        assert result1[0].name == "Test Candidate"
        assert result2[0].name == "Other Candidate"


# ============================================
# Tests for JSON field handling
# ============================================

class TestJSONFields:
    """Tests for JSON field serialization."""

    def test_custom_traits_serialized(self, api, db, dynasty_id, season, sample_gm, sample_hc):
        """Custom traits should be serialized to JSON."""
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        # Verify raw JSON in database
        row = db.query_one(
            "SELECT gm_custom_traits FROM team_staff_assignments WHERE dynasty_id = ? AND team_id = ?",
            (dynasty_id, 1)
        )
        assert row is not None
        traits = json.loads(row['gm_custom_traits'])
        assert traits == {"aggression": 0.8}

    def test_custom_traits_deserialized(self, api, dynasty_id, season, sample_gm, sample_hc):
        """Custom traits should be deserialized from JSON."""
        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=sample_gm, hc=sample_hc)

        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)
        assert result['gm'].custom_traits == {"aggression": 0.8}
        assert result['hc'].custom_traits == {"risk_tolerance": 0.6}

    def test_empty_traits_handled(self, api, dynasty_id, season):
        """Empty custom traits should be handled correctly."""
        gm = StaffMember(staff_id="gm1", staff_type=StaffType.GM, name="GM", archetype_key="balanced", hire_season=2025)
        hc = StaffMember(staff_id="hc1", staff_type=StaffType.HEAD_COACH, name="HC", archetype_key="balanced", hire_season=2025)

        api.save_staff_assignment(dynasty_id, team_id=1, season=season, gm=gm, hc=hc)

        result = api.get_staff_assignment(dynasty_id, team_id=1, season=season)
        assert result['gm'].custom_traits == {}
        assert result['hc'].custom_traits == {}
