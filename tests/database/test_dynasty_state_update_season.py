"""
Tests for DynastyStateAPI.update_season() Method

Validates season SSOT update functionality for game cycle season transitions.
Tests the new method:
- update_season(): Update season field in dynasty_state table

Test Coverage:
- Season SSOT update (increment season number)
- Multiple season records (updates most recent only)
- Non-existent dynasty handling
- Database persistence verification
- Timestamp updates
- Fail-loud behavior (raises exception on failure)

Relates to: Fix for Season 2 Week 1 standings bug
"""

import pytest
import sqlite3
import os
import tempfile

from database.dynasty_state_api import DynastyStateAPI
from database.sync_exceptions import CalendarSyncPersistenceException


class TestDynastyStateUpdateSeason:
    """Test DynastyStateAPI.update_season() functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary test database with dynasty_state table."""
        # Create temporary database file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Create schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE dynasty_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                current_date TEXT NOT NULL,
                current_phase TEXT NOT NULL,
                current_week INTEGER,
                last_simulated_game_id TEXT,
                current_draft_pick INTEGER DEFAULT 0,
                draft_in_progress INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(dynasty_id, season)
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    # ========================================================================
    # UPDATE_SEASON() TESTS
    # ========================================================================

    def test_update_season_increments_ssot(self, temp_db):
        """Verify update_season() increments the season SSOT in database."""
        # Setup: Insert initial dynasty state for season 2024
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('test_dynasty', 2024, '2025-02-15', 'offseason', NULL)
        """)
        conn.commit()
        conn.close()

        # Execute: Update season to 2025
        api = DynastyStateAPI(temp_db)
        result = api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: Returns True for success
        assert result is True

        # Verify: Season updated in database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT season FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 2025

    def test_update_season_updates_timestamp(self, temp_db):
        """Verify update_season() updates the updated_at timestamp."""
        # Setup: Insert initial dynasty state
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week, updated_at)
            VALUES ('test_dynasty', 2024, '2025-02-15', 'offseason', NULL, '2025-01-01 00:00:00')
        """)
        conn.commit()

        # Get initial timestamp
        cursor.execute("""
            SELECT updated_at FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
        """)
        initial_timestamp = cursor.fetchone()[0]
        conn.close()

        # Execute: Update season
        api = DynastyStateAPI(temp_db)
        api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: Timestamp changed
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT updated_at FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
        """)
        new_timestamp = cursor.fetchone()[0]
        conn.close()

        assert new_timestamp != initial_timestamp

    def test_update_season_updates_most_recent_only(self, temp_db):
        """Verify update_season() updates only the most recent dynasty_state record."""
        # Setup: Insert multiple dynasty state records for different seasons
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('test_dynasty', 2023, '2024-02-15', 'offseason', NULL)
        """)
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('test_dynasty', 2024, '2025-02-15', 'offseason', NULL)
        """)
        conn.commit()
        conn.close()

        # Execute: Update season to 2025
        api = DynastyStateAPI(temp_db)
        api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: Only the most recent record (2024) was updated to 2025
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT season FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
            ORDER BY season DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0][0] == 2025  # Most recent updated to 2025
        assert rows[1][0] == 2023  # Older record unchanged

    def test_update_season_nonexistent_dynasty_raises_exception(self, temp_db):
        """Verify update_season() raises exception for non-existent dynasty."""
        # Setup: Empty database (no dynasty state)
        api = DynastyStateAPI(temp_db)

        # Execute & Verify: Should raise CalendarSyncPersistenceException
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_season(dynasty_id='nonexistent_dynasty', season=2025)

        # Verify exception details
        assert exc_info.value.operation == "season_update"
        assert exc_info.value.sync_point == "update_season"
        assert "nonexistent_dynasty" in str(exc_info.value.state_info)

    def test_update_season_preserves_other_fields(self, temp_db):
        """Verify update_season() doesn't modify other dynasty_state fields."""
        # Setup: Insert initial dynasty state with specific values
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week, last_simulated_game_id)
            VALUES ('test_dynasty', 2024, '2025-02-15', 'offseason', 5, 'game_123')
        """)
        conn.commit()
        conn.close()

        # Execute: Update season only
        api = DynastyStateAPI(temp_db)
        api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: Season field updated, row count unchanged (not creating new record)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Check only one record exists (not creating duplicates)
        cursor.execute("""
            SELECT COUNT(*) FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
        """)
        count = cursor.fetchone()[0]
        assert count == 1  # Still only one record

        # Check season was updated
        cursor.execute("""
            SELECT season, current_phase, current_week, last_simulated_game_id
            FROM dynasty_state
            WHERE dynasty_id = 'test_dynasty'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 2025  # season updated
        assert row[1] == 'offseason'  # current_phase unchanged
        assert row[2] == 5  # current_week unchanged
        assert row[3] == 'game_123'  # last_simulated_game_id unchanged

    def test_update_season_integration_with_get_latest_state(self, temp_db):
        """Verify update_season() integrates with get_latest_state()."""
        # Setup: Insert initial dynasty state
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('test_dynasty', 2024, '2025-02-15', 'offseason', NULL)
        """)
        conn.commit()
        conn.close()

        # Execute: Update season
        api = DynastyStateAPI(temp_db)
        api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: get_latest_state() returns updated season
        state = api.get_latest_state(dynasty_id='test_dynasty')

        assert state is not None
        assert state['season'] == 2025
        assert state['current_phase'] == 'offseason'

    def test_update_season_from_2024_to_2025(self, temp_db):
        """Integration test: Simulate Season 1 (2024) → Season 2 (2025) transition."""
        # Setup: Season 1 complete (waiver wire stage)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('test_dynasty', 2024, '2025-07-31', 'offseason', NULL)
        """)
        conn.commit()
        conn.close()

        # Execute: Advance to Season 2
        api = DynastyStateAPI(temp_db)
        result = api.update_season(dynasty_id='test_dynasty', season=2025)

        # Verify: Season incremented correctly
        assert result is True

        state = api.get_latest_state(dynasty_id='test_dynasty')
        assert state['season'] == 2025

    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================

    def test_update_season_multiple_dynasties(self, temp_db):
        """Verify update_season() only updates the specified dynasty."""
        # Setup: Insert dynasty states for multiple dynasties
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('dynasty_a', 2024, '2025-02-15', 'offseason', NULL)
        """)
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES ('dynasty_b', 2024, '2025-02-15', 'offseason', NULL)
        """)
        conn.commit()
        conn.close()

        # Execute: Update only dynasty_a
        api = DynastyStateAPI(temp_db)
        api.update_season(dynasty_id='dynasty_a', season=2025)

        # Verify: Only dynasty_a updated
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dynasty_id, season FROM dynasty_state
            ORDER BY dynasty_id
        """)
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == ('dynasty_a', 2025)  # Updated
        assert rows[1] == ('dynasty_b', 2024)  # Unchanged
