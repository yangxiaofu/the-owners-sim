"""
Tests for FAWaveStateAPI.

Part of Milestone 8: Free Agency Depth - Tollgate 1.
"""
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.fa_wave_state_api import FAWaveStateAPI, WAVE_CONFIGS


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

        CREATE TABLE IF NOT EXISTS fa_wave_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            current_wave INTEGER DEFAULT 0 CHECK(current_wave BETWEEN 0 AND 4),
            current_day INTEGER DEFAULT 1 CHECK(current_day BETWEEN 1 AND 3),
            wave_complete INTEGER DEFAULT 0 CHECK(wave_complete IN (0, 1)),
            post_draft_available INTEGER DEFAULT 0 CHECK(post_draft_available IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, season)
        );

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test_dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield path

    os.unlink(path)


@pytest.fixture
def api(db_path):
    """Create API instance."""
    return FAWaveStateAPI(db_path)


class TestWaveConfiguration:
    """Tests for wave configuration constants."""

    def test_wave_0_is_legal_tampering(self):
        """Wave 0 should be Legal Tampering with no signing."""
        config = WAVE_CONFIGS[0]
        assert config["name"] == "Legal Tampering"
        assert config["signing_allowed"] is False
        assert config["days"] == 1

    def test_wave_1_is_elite(self):
        """Wave 1 should be Elite players (85+)."""
        config = WAVE_CONFIGS[1]
        assert config["name"] == "Wave 1 - Elite"
        assert config["min_ovr"] == 85
        assert config["max_ovr"] == 99
        assert config["days"] == 3
        assert config["signing_allowed"] is True

    def test_wave_2_is_quality(self):
        """Wave 2 should be Quality players (75-84)."""
        config = WAVE_CONFIGS[2]
        assert config["name"] == "Wave 2 - Quality"
        assert config["min_ovr"] == 75
        assert config["max_ovr"] == 84
        assert config["days"] == 2

    def test_wave_3_is_depth(self):
        """Wave 3 should be Depth players (65-74)."""
        config = WAVE_CONFIGS[3]
        assert config["name"] == "Wave 3 - Depth"
        assert config["min_ovr"] == 65
        assert config["max_ovr"] == 74
        assert config["days"] == 2

    def test_wave_4_is_post_draft(self):
        """Wave 4 should be Post-Draft (all remaining)."""
        config = WAVE_CONFIGS[4]
        assert config["name"] == "Post-Draft"
        assert config["min_ovr"] == 0
        assert config["max_ovr"] == 99
        assert config["days"] == 1


class TestInitializeWaveState:
    """Tests for initializing wave state."""

    def test_initialize_creates_state(self, api):
        """Should create initial wave state."""
        state = api.initialize_wave_state("test_dynasty", 2025)

        assert state is not None
        assert state["dynasty_id"] == "test_dynasty"
        assert state["season"] == 2025
        assert state["current_wave"] == 0
        assert state["current_day"] == 1
        assert state["wave_complete"] is False
        assert state["post_draft_available"] is False

    def test_initialize_includes_wave_name(self, api):
        """Should include derived wave info."""
        state = api.initialize_wave_state("test_dynasty", 2025)

        assert state["wave_name"] == "Legal Tampering"
        assert state["days_in_wave"] == 1
        assert state["signing_allowed"] is False

    def test_get_wave_state_returns_none_if_not_initialized(self, api):
        """Should return None if not initialized."""
        state = api.get_wave_state("test_dynasty", 2025)
        assert state is None


class TestAdvanceDay:
    """Tests for advancing days within a wave."""

    def test_advance_day_increments(self, api):
        """Advancing day should increment current_day."""
        api.initialize_wave_state("test_dynasty", 2025)

        # Move to wave 1 which has 3 days
        api.advance_wave("test_dynasty", 2025)
        state = api.get_wave_state("test_dynasty", 2025)
        assert state["current_day"] == 1

        # Advance day
        new_state = api.advance_day("test_dynasty", 2025)
        assert new_state["current_day"] == 2
        assert new_state["wave_complete"] is False

    def test_advance_day_marks_wave_complete(self, api):
        """Advancing past max days should mark wave complete."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.advance_wave("test_dynasty", 2025)  # Wave 1, 3 days

        # Day 1 -> 2
        api.advance_day("test_dynasty", 2025)
        # Day 2 -> 3
        api.advance_day("test_dynasty", 2025)
        # Day 3 -> wave complete
        state = api.advance_day("test_dynasty", 2025)

        assert state["current_day"] == 3
        assert state["wave_complete"] is True

    def test_advance_day_without_init_raises_error(self, api):
        """Advancing without initialization should raise error."""
        with pytest.raises(ValueError):
            api.advance_day("test_dynasty", 2025)


class TestAdvanceWave:
    """Tests for advancing to the next wave."""

    def test_advance_wave_increments(self, api):
        """Advancing wave should increment current_wave."""
        api.initialize_wave_state("test_dynasty", 2025)
        assert api.get_wave_state("test_dynasty", 2025)["current_wave"] == 0

        state = api.advance_wave("test_dynasty", 2025)
        assert state["current_wave"] == 1
        assert state["current_day"] == 1  # Reset to day 1
        assert state["wave_complete"] is False

    def test_advance_wave_updates_wave_info(self, api):
        """Advancing wave should update derived wave info."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.advance_wave("test_dynasty", 2025)

        state = api.get_wave_state("test_dynasty", 2025)
        assert state["wave_name"] == "Wave 1 - Elite"
        assert state["days_in_wave"] == 3
        assert state["signing_allowed"] is True

    def test_cannot_advance_to_wave_4_without_post_draft(self, api):
        """Cannot advance to wave 4 until draft complete."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.advance_wave("test_dynasty", 2025)  # 0 -> 1
        api.advance_wave("test_dynasty", 2025)  # 1 -> 2
        api.advance_wave("test_dynasty", 2025)  # 2 -> 3

        # Wave 3 is the last pre-draft wave
        with pytest.raises(ValueError, match="draft"):
            api.advance_wave("test_dynasty", 2025)


class TestPostDraftWave:
    """Tests for post-draft wave handling."""

    def test_enable_post_draft_wave(self, api):
        """Should enable and advance to post-draft wave."""
        api.initialize_wave_state("test_dynasty", 2025)

        state = api.enable_post_draft_wave("test_dynasty", 2025)

        assert state["current_wave"] == 4
        assert state["current_day"] == 1
        assert state["post_draft_available"] is True
        assert state["wave_name"] == "Post-Draft"

    def test_is_signing_allowed_in_post_draft(self, api):
        """Signing should be allowed in post-draft wave."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.enable_post_draft_wave("test_dynasty", 2025)

        assert api.is_signing_allowed("test_dynasty", 2025) is True


class TestFACompletion:
    """Tests for FA completion tracking."""

    def test_is_fa_complete_false_initially(self, api):
        """FA should not be complete initially."""
        api.initialize_wave_state("test_dynasty", 2025)
        assert api.is_fa_complete("test_dynasty", 2025) is False

    def test_is_fa_complete_after_wave_4(self, api):
        """FA should be complete after wave 4 is done."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.enable_post_draft_wave("test_dynasty", 2025)

        # Complete wave 4
        api.advance_day("test_dynasty", 2025)  # Day 1 -> complete (1 day wave)
        api.mark_wave_complete("test_dynasty", 2025)

        assert api.is_fa_complete("test_dynasty", 2025) is True


class TestResetAndDelete:
    """Tests for reset and delete operations."""

    def test_reset_wave_state(self, api):
        """Should reset to initial state."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.advance_wave("test_dynasty", 2025)
        api.advance_day("test_dynasty", 2025)

        result = api.reset_wave_state("test_dynasty", 2025)
        assert result is True

        state = api.get_wave_state("test_dynasty", 2025)
        assert state["current_wave"] == 0
        assert state["current_day"] == 1
        assert state["wave_complete"] is False

    def test_delete_wave_state(self, api):
        """Should delete wave state."""
        api.initialize_wave_state("test_dynasty", 2025)

        result = api.delete_wave_state("test_dynasty", 2025)
        assert result is True

        state = api.get_wave_state("test_dynasty", 2025)
        assert state is None


class TestHelperMethods:
    """Tests for helper methods."""

    def test_is_signing_allowed_false_in_legal_tampering(self, api):
        """Signing should not be allowed in Legal Tampering."""
        api.initialize_wave_state("test_dynasty", 2025)
        assert api.is_signing_allowed("test_dynasty", 2025) is False

    def test_is_signing_allowed_true_in_waves(self, api):
        """Signing should be allowed in waves 1-4."""
        api.initialize_wave_state("test_dynasty", 2025)
        api.advance_wave("test_dynasty", 2025)  # Wave 1
        assert api.is_signing_allowed("test_dynasty", 2025) is True

    def test_get_wave_config(self, api):
        """Should return wave configuration."""
        config = api.get_wave_config(1)
        assert config["name"] == "Wave 1 - Elite"
        assert config["min_ovr"] == 85

    def test_get_wave_config_unknown(self, api):
        """Should return default for unknown wave."""
        config = api.get_wave_config(99)
        assert config["name"] == "Unknown"
        assert config["signing_allowed"] is False


class TestDynastyIsolation:
    """Tests for dynasty isolation."""

    def test_wave_state_isolated_by_dynasty(self, api, db_path):
        """Wave states should be isolated by dynasty."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        api.initialize_wave_state("test_dynasty", 2025)
        api.initialize_wave_state("other_dynasty", 2025)

        # Advance one but not the other
        api.advance_wave("test_dynasty", 2025)

        test_state = api.get_wave_state("test_dynasty", 2025)
        other_state = api.get_wave_state("other_dynasty", 2025)

        assert test_state["current_wave"] == 1
        assert other_state["current_wave"] == 0
