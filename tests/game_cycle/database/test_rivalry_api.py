"""
Tests for RivalryAPI and Rivalry model.

Part of Milestone 11: Schedule & Rivalries, Tollgate 1.
Covers dataclass validation, CRUD operations, initialization, and dynasty isolation.
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from src.game_cycle.models.rivalry import (
    RivalryType,
    Rivalry,
    DIVISION_TEAMS,
    DIVISION_NAMES,
)
from src.game_cycle.database.rivalry_api import RivalryAPI
from src.game_cycle.database.connection import GameCycleDatabase


@pytest.fixture
def db_path():
    """Create a temporary database with the schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025
        );

        CREATE TABLE IF NOT EXISTS rivalries (
            rivalry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_a_id INTEGER NOT NULL CHECK(team_a_id BETWEEN 1 AND 32),
            team_b_id INTEGER NOT NULL CHECK(team_b_id BETWEEN 1 AND 32),
            rivalry_type TEXT NOT NULL CHECK(rivalry_type IN ('division', 'historic', 'geographic', 'recent')),
            rivalry_name TEXT NOT NULL,
            intensity INTEGER NOT NULL DEFAULT 50 CHECK(intensity BETWEEN 1 AND 100),
            is_protected INTEGER DEFAULT 0 CHECK(is_protected IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(team_a_id < team_b_id),
            CHECK(team_a_id != team_b_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_a_id, team_b_id)
        );

        CREATE INDEX idx_rivalries_dynasty ON rivalries(dynasty_id);
        CREATE INDEX idx_rivalries_team_a ON rivalries(dynasty_id, team_a_id);
        CREATE INDEX idx_rivalries_team_b ON rivalries(dynasty_id, team_b_id);

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test_dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield path

    os.unlink(path)


@pytest.fixture
def db(db_path):
    """Create GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create RivalryAPI instance."""
    return RivalryAPI(db)


# ============================================================================
# Rivalry Dataclass Tests
# ============================================================================

class TestRivalryDataclass:
    """Tests for Rivalry dataclass validation and methods."""

    def test_create_valid_rivalry(self):
        """Should create rivalry with valid parameters."""
        rivalry = Rivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="AFC East Division Rivalry",
            intensity=70,
        )
        assert rivalry.team_a_id == 1
        assert rivalry.team_b_id == 2
        assert rivalry.rivalry_type == RivalryType.DIVISION
        assert rivalry.rivalry_name == "AFC East Division Rivalry"
        assert rivalry.intensity == 70
        assert rivalry.is_protected is False

    def test_auto_swap_team_ids_when_reversed(self):
        """Should auto-swap team IDs to enforce team_a < team_b."""
        rivalry = Rivalry(
            team_a_id=10,
            team_b_id=5,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test Rivalry",
        )
        assert rivalry.team_a_id == 5
        assert rivalry.team_b_id == 10

    def test_default_intensity_is_50(self):
        """Default intensity should be 50."""
        rivalry = Rivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Test Rivalry",
        )
        assert rivalry.intensity == 50

    def test_invalid_team_a_id_below_range(self):
        """Should raise error for team_a_id < 1."""
        with pytest.raises(ValueError, match="team_a_id must be 1-32"):
            Rivalry(
                team_a_id=0,
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
            )

    def test_invalid_team_b_id_above_range(self):
        """Should raise error for team_b_id > 32."""
        with pytest.raises(ValueError, match="team_b_id must be 1-32"):
            Rivalry(
                team_a_id=1,
                team_b_id=33,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
            )

    def test_same_team_ids_raises_error(self):
        """Should raise error when team_a == team_b."""
        with pytest.raises(ValueError, match="must be different"):
            Rivalry(
                team_a_id=5,
                team_b_id=5,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
            )

    def test_invalid_intensity_below_range(self):
        """Should raise error for intensity < 1."""
        with pytest.raises(ValueError, match="intensity must be 1-100"):
            Rivalry(
                team_a_id=1,
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
                intensity=0,
            )

    def test_invalid_intensity_above_range(self):
        """Should raise error for intensity > 100."""
        with pytest.raises(ValueError, match="intensity must be 1-100"):
            Rivalry(
                team_a_id=1,
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
                intensity=101,
            )

    def test_empty_rivalry_name_raises_error(self):
        """Should raise error for empty rivalry name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Rivalry(
                team_a_id=1,
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="",
            )

    def test_whitespace_rivalry_name_raises_error(self):
        """Should raise error for whitespace-only rivalry name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Rivalry(
                team_a_id=1,
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="   ",
            )

    def test_invalid_rivalry_type_raises_error(self):
        """Should raise error for non-enum rivalry type."""
        with pytest.raises(ValueError, match="must be RivalryType enum"):
            Rivalry(
                team_a_id=1,
                team_b_id=2,
                rivalry_type="division",  # String instead of enum
                rivalry_name="Test",
            )

    def test_non_integer_team_id_raises_error(self):
        """Should raise error for non-integer team ID."""
        with pytest.raises(ValueError, match="must be integers"):
            Rivalry(
                team_a_id="1",
                team_b_id=2,
                rivalry_type=RivalryType.DIVISION,
                rivalry_name="Test",
            )


class TestRivalryMethods:
    """Tests for Rivalry instance methods."""

    def test_involves_team_returns_true_for_team_a(self):
        """involves_team should return True for team_a."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.involves_team(5) is True

    def test_involves_team_returns_true_for_team_b(self):
        """involves_team should return True for team_b."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.involves_team(8) is True

    def test_involves_team_returns_false_for_other(self):
        """involves_team should return False for non-participating team."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.involves_team(10) is False

    def test_get_opponent_from_team_a(self):
        """get_opponent should return team_b when given team_a."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.get_opponent(5) == 8

    def test_get_opponent_from_team_b(self):
        """get_opponent should return team_a when given team_b."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.get_opponent(8) == 5

    def test_get_opponent_returns_none_for_non_participant(self):
        """get_opponent should return None for non-participating team."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
        )
        assert rivalry.get_opponent(10) is None

    def test_intensity_level_legendary(self):
        """intensity_level should return 'Legendary' for >= 90."""
        rivalry = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=95,
        )
        assert rivalry.intensity_level == "Legendary"

    def test_intensity_level_intense(self):
        """intensity_level should return 'Intense' for 75-89."""
        rivalry = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        assert rivalry.intensity_level == "Intense"

    def test_intensity_level_competitive(self):
        """intensity_level should return 'Competitive' for 50-74."""
        rivalry = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=60,
        )
        assert rivalry.intensity_level == "Competitive"

    def test_intensity_level_developing(self):
        """intensity_level should return 'Developing' for 25-49."""
        rivalry = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=30,
        )
        assert rivalry.intensity_level == "Developing"

    def test_intensity_level_mild(self):
        """intensity_level should return 'Mild' for < 25."""
        rivalry = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=10,
        )
        assert rivalry.intensity_level == "Mild"

    def test_str_representation(self):
        """__str__ should return readable format."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Ravens vs Steelers",
            intensity=92,
        )
        result = str(rivalry)
        assert "Ravens vs Steelers" in result
        assert "Team 5 vs Team 8" in result
        assert "historic" in result
        assert "92" in result


class TestRivalryConversion:
    """Tests for Rivalry conversion methods."""

    def test_to_db_dict(self):
        """to_db_dict should convert to database-ready format."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test Rivalry",
            intensity=85,
            is_protected=True,
        )
        result = rivalry.to_db_dict()
        assert result['team_a_id'] == 5
        assert result['team_b_id'] == 8
        assert result['rivalry_type'] == 'historic'
        assert result['rivalry_name'] == 'Test Rivalry'
        assert result['intensity'] == 85
        assert result['is_protected'] == 1

    def test_to_dict(self):
        """to_dict should convert to serializable format."""
        rivalry = Rivalry(
            rivalry_id=42,
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test Rivalry",
            intensity=85,
            is_protected=True,
            created_at="2025-01-01 00:00:00",
        )
        result = rivalry.to_dict()
        assert result['rivalry_id'] == 42
        assert result['team_a_id'] == 5
        assert result['team_b_id'] == 8
        assert result['rivalry_type'] == 'historic'
        assert result['rivalry_name'] == 'Test Rivalry'
        assert result['intensity'] == 85
        assert result['is_protected'] is True
        assert result['created_at'] == "2025-01-01 00:00:00"

    def test_from_db_row(self):
        """from_db_row should create Rivalry from dict."""
        row = {
            'rivalry_id': 42,
            'team_a_id': 5,
            'team_b_id': 8,
            'rivalry_type': 'historic',
            'rivalry_name': 'Test Rivalry',
            'intensity': 85,
            'is_protected': 1,
            'created_at': '2025-01-01 00:00:00',
        }
        rivalry = Rivalry.from_db_row(row)
        assert rivalry.rivalry_id == 42
        assert rivalry.team_a_id == 5
        assert rivalry.team_b_id == 8
        assert rivalry.rivalry_type == RivalryType.HISTORIC
        assert rivalry.rivalry_name == 'Test Rivalry'
        assert rivalry.intensity == 85
        assert rivalry.is_protected is True

    def test_from_db_row_with_zero_protected(self):
        """from_db_row should handle is_protected=0."""
        row = {
            'rivalry_id': 42,
            'team_a_id': 5,
            'team_b_id': 8,
            'rivalry_type': 'division',
            'rivalry_name': 'Test',
            'intensity': 70,
            'is_protected': 0,
        }
        rivalry = Rivalry.from_db_row(row)
        assert rivalry.is_protected is False


class TestDivisionMappings:
    """Tests for division team mappings."""

    def test_division_teams_has_8_divisions(self):
        """Should have 8 divisions."""
        assert len(DIVISION_TEAMS) == 8

    def test_each_division_has_4_teams(self):
        """Each division should have 4 teams."""
        for div_id, teams in DIVISION_TEAMS.items():
            assert len(teams) == 4, f"Division {div_id} has {len(teams)} teams"

    def test_all_32_teams_covered(self):
        """All 32 teams should be in exactly one division."""
        all_teams = []
        for teams in DIVISION_TEAMS.values():
            all_teams.extend(teams)
        assert len(all_teams) == 32
        assert len(set(all_teams)) == 32  # No duplicates
        assert min(all_teams) == 1
        assert max(all_teams) == 32

    def test_division_names_has_8_divisions(self):
        """Should have 8 division names."""
        assert len(DIVISION_NAMES) == 8

    def test_division_names_match_teams(self):
        """Division names should match team mappings."""
        assert set(DIVISION_NAMES.keys()) == set(DIVISION_TEAMS.keys())


# ============================================================================
# RivalryAPI Query Tests
# ============================================================================

class TestGetRivalry:
    """Tests for get_rivalry method."""

    def test_get_rivalry_by_id(self, api):
        """Should retrieve rivalry by ID."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Ravens vs Steelers",
            intensity=92,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.get_rivalry("test_dynasty", rivalry_id)
        assert result is not None
        assert result.rivalry_id == rivalry_id
        assert result.team_a_id == 5
        assert result.team_b_id == 8

    def test_get_rivalry_not_found(self, api):
        """Should return None for non-existent rivalry."""
        result = api.get_rivalry("test_dynasty", 99999)
        assert result is None


class TestGetRivalryBetweenTeams:
    """Tests for get_rivalry_between_teams method."""

    def test_get_rivalry_between_teams(self, api):
        """Should find rivalry between two teams."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
            intensity=85,
        )
        api.create_rivalry("test_dynasty", rivalry)

        result = api.get_rivalry_between_teams("test_dynasty", 5, 8)
        assert result is not None
        assert result.team_a_id == 5
        assert result.team_b_id == 8

    def test_get_rivalry_between_teams_reversed_order(self, api):
        """Should find rivalry regardless of team order."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
            intensity=85,
        )
        api.create_rivalry("test_dynasty", rivalry)

        # Query with reversed order
        result = api.get_rivalry_between_teams("test_dynasty", 8, 5)
        assert result is not None
        assert result.team_a_id == 5
        assert result.team_b_id == 8

    def test_get_rivalry_between_teams_not_found(self, api):
        """Should return None when no rivalry exists."""
        result = api.get_rivalry_between_teams("test_dynasty", 1, 2)
        assert result is None


class TestGetRivalriesForTeam:
    """Tests for get_rivalries_for_team method."""

    def test_get_rivalries_for_team(self, api):
        """Should get all rivalries for a team."""
        # Team 5 has rivalries with teams 8 and 6
        rivalry1 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="R1", intensity=90,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=6,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="R2", intensity=70,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        results = api.get_rivalries_for_team("test_dynasty", 5)
        assert len(results) == 2
        # Should be sorted by intensity descending
        assert results[0].intensity == 90
        assert results[1].intensity == 70

    def test_get_rivalries_for_team_as_team_b(self, api):
        """Should find rivalries where team is team_b."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=85,
        )
        api.create_rivalry("test_dynasty", rivalry)

        results = api.get_rivalries_for_team("test_dynasty", 8)
        assert len(results) == 1
        assert results[0].team_a_id == 5

    def test_get_rivalries_for_team_with_type_filter(self, api):
        """Should filter by rivalry type."""
        rivalry1 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Historic", intensity=90,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=6,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Division", intensity=70,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        results = api.get_rivalries_for_team(
            "test_dynasty", 5,
            rivalry_type=RivalryType.DIVISION
        )
        assert len(results) == 1
        assert results[0].rivalry_type == RivalryType.DIVISION

    def test_get_rivalries_for_team_empty(self, api):
        """Should return empty list for team with no rivalries."""
        results = api.get_rivalries_for_team("test_dynasty", 15)
        assert results == []


class TestGetAllRivalries:
    """Tests for get_all_rivalries method."""

    def test_get_all_rivalries(self, api):
        """Should get all rivalries for dynasty."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="R1", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="R2", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        results = api.get_all_rivalries("test_dynasty")
        assert len(results) == 2
        # Should be sorted by intensity descending
        assert results[0].intensity == 90

    def test_get_all_rivalries_with_type_filter(self, api):
        """Should filter by rivalry type."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Division", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Historic", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        results = api.get_all_rivalries("test_dynasty", RivalryType.HISTORIC)
        assert len(results) == 1
        assert results[0].rivalry_type == RivalryType.HISTORIC


class TestGetProtectedRivalries:
    """Tests for get_protected_rivalries method."""

    def test_get_protected_rivalries(self, api):
        """Should get only protected rivalries."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Not Protected", intensity=70,
            is_protected=False,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Protected", intensity=95,
            is_protected=True,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        results = api.get_protected_rivalries("test_dynasty")
        assert len(results) == 1
        assert results[0].is_protected is True
        assert results[0].rivalry_name == "Protected"


class TestGetRivalryCount:
    """Tests for get_rivalry_count method."""

    def test_get_rivalry_count(self, api):
        """Should count all rivalries."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="R1", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="R2", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        count = api.get_rivalry_count("test_dynasty")
        assert count == 2

    def test_get_rivalry_count_with_type_filter(self, api):
        """Should count by rivalry type."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Division", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Historic", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        count = api.get_rivalry_count("test_dynasty", RivalryType.DIVISION)
        assert count == 1

    def test_get_rivalry_count_empty(self, api):
        """Should return 0 for no rivalries."""
        count = api.get_rivalry_count("test_dynasty")
        assert count == 0


# ============================================================================
# RivalryAPI Update Tests
# ============================================================================

class TestCreateRivalry:
    """Tests for create_rivalry method."""

    def test_create_rivalry_returns_id(self, api):
        """Creating a rivalry should return the rivalry ID."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test Rivalry",
            intensity=85,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)
        assert rivalry_id is not None
        assert rivalry_id > 0

    def test_create_rivalry_stores_all_fields(self, api):
        """All fields should be stored correctly."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Ravens vs Steelers",
            intensity=92,
            is_protected=True,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.get_rivalry("test_dynasty", rivalry_id)
        assert result.team_a_id == 5
        assert result.team_b_id == 8
        assert result.rivalry_type == RivalryType.HISTORIC
        assert result.rivalry_name == "Ravens vs Steelers"
        assert result.intensity == 92
        assert result.is_protected is True

    def test_create_duplicate_rivalry_raises_error(self, api):
        """Creating duplicate rivalry should raise error."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="First", intensity=80,
        )
        api.create_rivalry("test_dynasty", rivalry)

        duplicate = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.DIVISION,  # Different type
            rivalry_name="Second", intensity=70,
        )
        with pytest.raises(ValueError, match="already exists"):
            api.create_rivalry("test_dynasty", duplicate)


class TestCreateRivalriesBatch:
    """Tests for create_rivalries_batch method."""

    def test_create_rivalries_batch(self, api):
        """Should create multiple rivalries at once."""
        rivalries = [
            Rivalry(team_a_id=1, team_b_id=2, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="R1", intensity=70),
            Rivalry(team_a_id=3, team_b_id=4, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="R2", intensity=70),
            Rivalry(team_a_id=5, team_b_id=6, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="R3", intensity=70),
        ]

        count = api.create_rivalries_batch("test_dynasty", rivalries)
        assert count == 3

        all_rivalries = api.get_all_rivalries("test_dynasty")
        assert len(all_rivalries) == 3

    def test_create_rivalries_batch_empty_list(self, api):
        """Should handle empty list gracefully."""
        count = api.create_rivalries_batch("test_dynasty", [])
        assert count == 0

    def test_create_rivalries_batch_skips_duplicates(self, api):
        """Should skip duplicate rivalries using INSERT OR IGNORE."""
        rivalries1 = [
            Rivalry(team_a_id=1, team_b_id=2, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="R1", intensity=70),
        ]
        api.create_rivalries_batch("test_dynasty", rivalries1)

        # Try to create again with same teams
        rivalries2 = [
            Rivalry(team_a_id=1, team_b_id=2, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="Duplicate", intensity=80),
            Rivalry(team_a_id=3, team_b_id=4, rivalry_type=RivalryType.DIVISION,
                    rivalry_name="New", intensity=70),
        ]
        count = api.create_rivalries_batch("test_dynasty", rivalries2)
        # Returns 2 (number of items passed), but only 1 new inserted
        assert count == 2

        all_rivalries = api.get_all_rivalries("test_dynasty")
        assert len(all_rivalries) == 2


class TestUpdateIntensity:
    """Tests for update_intensity method."""

    def test_update_intensity(self, api):
        """Should update rivalry intensity."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=70,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.update_intensity("test_dynasty", rivalry_id, 95)
        assert result is True

        updated = api.get_rivalry("test_dynasty", rivalry_id)
        assert updated.intensity == 95

    def test_update_intensity_out_of_range(self, api):
        """Should raise error for out-of-range intensity."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=70,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        with pytest.raises(ValueError, match="intensity must be 1-100"):
            api.update_intensity("test_dynasty", rivalry_id, 150)

    def test_update_intensity_nonexistent(self, api):
        """Should return False for non-existent rivalry."""
        result = api.update_intensity("test_dynasty", 99999, 80)
        assert result is False


class TestUpdateProtectedStatus:
    """Tests for update_protected_status method."""

    def test_update_protected_status_to_true(self, api):
        """Should set protected status to True."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=70,
            is_protected=False,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.update_protected_status("test_dynasty", rivalry_id, True)
        assert result is True

        updated = api.get_rivalry("test_dynasty", rivalry_id)
        assert updated.is_protected is True

    def test_update_protected_status_to_false(self, api):
        """Should set protected status to False."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=95,
            is_protected=True,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.update_protected_status("test_dynasty", rivalry_id, False)
        assert result is True

        updated = api.get_rivalry("test_dynasty", rivalry_id)
        assert updated.is_protected is False


class TestDeleteRivalry:
    """Tests for delete_rivalry method."""

    def test_delete_rivalry(self, api):
        """Should delete a rivalry."""
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=70,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        result = api.delete_rivalry("test_dynasty", rivalry_id)
        assert result is True

        deleted = api.get_rivalry("test_dynasty", rivalry_id)
        assert deleted is None

    def test_delete_nonexistent_rivalry(self, api):
        """Should return False for non-existent rivalry."""
        result = api.delete_rivalry("test_dynasty", 99999)
        assert result is False


class TestClearRivalries:
    """Tests for clear_rivalries method."""

    def test_clear_all_rivalries(self, api):
        """Should clear all rivalries for dynasty."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="R1", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="R2", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        count = api.clear_rivalries("test_dynasty")
        assert count == 2

        all_rivalries = api.get_all_rivalries("test_dynasty")
        assert len(all_rivalries) == 0

    def test_clear_rivalries_by_type(self, api):
        """Should clear only rivalries of specified type."""
        rivalry1 = Rivalry(
            team_a_id=1, team_b_id=2,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Division", intensity=70,
        )
        rivalry2 = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Historic", intensity=90,
        )
        api.create_rivalry("test_dynasty", rivalry1)
        api.create_rivalry("test_dynasty", rivalry2)

        count = api.clear_rivalries("test_dynasty", RivalryType.DIVISION)
        assert count == 1

        remaining = api.get_all_rivalries("test_dynasty")
        assert len(remaining) == 1
        assert remaining[0].rivalry_type == RivalryType.HISTORIC


# ============================================================================
# Initialization Tests
# ============================================================================

class TestGenerateDivisionRivalries:
    """Tests for division rivalry generation."""

    def test_generate_division_rivalries_count(self, api):
        """Should generate 48 division rivalries (8 divisions x 6 pairs)."""
        rivalries = api._generate_division_rivalries()
        assert len(rivalries) == 48

    def test_division_rivalries_all_type_division(self, api):
        """All generated rivalries should be DIVISION type."""
        rivalries = api._generate_division_rivalries()
        for rivalry in rivalries:
            assert rivalry.rivalry_type == RivalryType.DIVISION

    def test_division_rivalries_intensity_70(self, api):
        """All division rivalries should have intensity 70."""
        rivalries = api._generate_division_rivalries()
        for rivalry in rivalries:
            assert rivalry.intensity == 70

    def test_division_rivalries_not_protected(self, api):
        """Division rivalries should not be protected (games already guaranteed)."""
        rivalries = api._generate_division_rivalries()
        for rivalry in rivalries:
            assert rivalry.is_protected is False

    def test_division_rivalries_team_ordering(self, api):
        """All rivalries should have team_a < team_b."""
        rivalries = api._generate_division_rivalries()
        for rivalry in rivalries:
            assert rivalry.team_a_id < rivalry.team_b_id

    def test_division_rivalries_have_names(self, api):
        """All rivalries should have division names."""
        rivalries = api._generate_division_rivalries()
        for rivalry in rivalries:
            assert "Division Rivalry" in rivalry.rivalry_name


class TestInitializeRivalries:
    """Tests for initialize_rivalries method."""

    def test_initialize_creates_division_rivalries(self, api):
        """Should create all 48 division rivalries."""
        # Use a non-existent config to only test division generation
        counts = api.initialize_rivalries(
            "test_dynasty",
            config_path="/non/existent/path.json"
        )

        assert counts['division'] == 48
        assert counts['historic'] == 0
        assert counts['geographic'] == 0

        total = api.get_rivalry_count("test_dynasty")
        assert total == 48

    def test_initialize_loads_from_config(self, api):
        """Should load historic/geographic rivalries from config."""
        # Get the actual config path
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        config_path = project_root / "src" / "config" / "rivalries.json"

        if config_path.exists():
            counts = api.initialize_rivalries(
                "test_dynasty",
                config_path=str(config_path)
            )

            # Should have 48 division + some historic/geographic
            assert counts['division'] == 48
            # Config has 15 historic and 10 geographic
            # But some may overlap with division rivalries
            total = counts['division'] + counts['historic'] + counts['geographic']
            assert total >= 48

    def test_initialize_idempotent(self, api):
        """Calling initialize twice should not duplicate rivalries."""
        counts1 = api.initialize_rivalries(
            "test_dynasty",
            config_path="/non/existent/path.json"
        )
        counts2 = api.initialize_rivalries(
            "test_dynasty",
            config_path="/non/existent/path.json"
        )

        # Second call should not add more division rivalries
        assert counts2['division'] == 48

        total = api.get_rivalry_count("test_dynasty")
        # Should still be 48, not 96
        assert total == 48


# ============================================================================
# Dynasty Isolation Tests
# ============================================================================

class TestDynastyIsolation:
    """Tests for dynasty isolation of rivalry data."""

    def test_rivalries_isolated_by_dynasty(self, api, db_path):
        """Rivalries should be isolated by dynasty."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        # Create rivalry in each dynasty
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        api.create_rivalry("test_dynasty", rivalry)

        same_rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Other Test", intensity=90,
        )
        api.create_rivalry("other_dynasty", same_rivalry)

        # Query each dynasty
        test_rivalries = api.get_all_rivalries("test_dynasty")
        other_rivalries = api.get_all_rivalries("other_dynasty")

        assert len(test_rivalries) == 1
        assert len(other_rivalries) == 1
        assert test_rivalries[0].rivalry_name == "Test"
        assert other_rivalries[0].rivalry_name == "Other Test"

    def test_get_rivalry_isolated(self, api, db_path):
        """get_rivalry should respect dynasty isolation."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        # Should not find in other dynasty
        result = api.get_rivalry("other_dynasty", rivalry_id)
        assert result is None

    def test_update_intensity_isolated(self, api, db_path):
        """update_intensity should respect dynasty isolation."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        # Try to update from other dynasty
        result = api.update_intensity("other_dynasty", rivalry_id, 95)
        assert result is False

        # Original should be unchanged
        original = api.get_rivalry("test_dynasty", rivalry_id)
        assert original.intensity == 80

    def test_delete_rivalry_isolated(self, api, db_path):
        """delete_rivalry should respect dynasty isolation."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        rivalry_id = api.create_rivalry("test_dynasty", rivalry)

        # Try to delete from other dynasty
        result = api.delete_rivalry("other_dynasty", rivalry_id)
        assert result is False

        # Original should still exist
        original = api.get_rivalry("test_dynasty", rivalry_id)
        assert original is not None

    def test_clear_rivalries_isolated(self, api, db_path):
        """clear_rivalries should only clear for specified dynasty."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        # Create rivalries in both dynasties
        rivalry = Rivalry(
            team_a_id=5, team_b_id=8,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test", intensity=80,
        )
        api.create_rivalry("test_dynasty", rivalry)
        api.create_rivalry("other_dynasty", rivalry)

        # Clear only test_dynasty
        api.clear_rivalries("test_dynasty")

        # test_dynasty should be empty
        test_count = api.get_rivalry_count("test_dynasty")
        assert test_count == 0

        # other_dynasty should still have rivalry
        other_count = api.get_rivalry_count("other_dynasty")
        assert other_count == 1