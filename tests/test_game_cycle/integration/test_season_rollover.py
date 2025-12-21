"""
Integration test for Season Rollover (Season 1 → Season 2)

Tests the complete flow of advancing from one season to the next:
- OFFSEASON_WAIVER_WIRE (Season 1) → REGULAR_WEEK_1 (Season 2)
- Verifies SSOT (dynasty_state.season) is incremented
- Verifies standings are initialized to 0-0 for all teams
- Verifies UI displays correct season and standings

Relates to: Fix for Season 2 Week 1 standings bug (SSOT pattern)
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from game_cycle.stage_controller import StageController
from game_cycle.stage_definitions import Stage, StageType
from database.dynasty_state_api import DynastyStateAPI


class TestSeasonRollover:
    """Integration tests for season transition (Season 1 → Season 2)."""

    @pytest.fixture
    def test_db_path(self):
        """Create a temporary test database with full schema."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Create minimal schema for testing
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # dynasty_state table (SSOT for season)
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

        # standings table
        cursor.execute("""
            CREATE TABLE standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                ties INTEGER NOT NULL DEFAULT 0,
                points_for INTEGER NOT NULL DEFAULT 0,
                points_against INTEGER NOT NULL DEFAULT 0,
                point_differential INTEGER NOT NULL DEFAULT 0,
                division_wins INTEGER NOT NULL DEFAULT 0,
                division_losses INTEGER NOT NULL DEFAULT 0,
                division_ties INTEGER NOT NULL DEFAULT 0,
                conference_wins INTEGER NOT NULL DEFAULT 0,
                conference_losses INTEGER NOT NULL DEFAULT 0,
                conference_ties INTEGER NOT NULL DEFAULT 0,
                UNIQUE(dynasty_id, season, team_id, season_type)
            )
        """)

        # dynasties table (for foreign key reference)
        cursor.execute("""
            CREATE TABLE dynasties (
                dynasty_id TEXT PRIMARY KEY,
                dynasty_name TEXT NOT NULL,
                owner_name TEXT,
                team_id INTEGER NOT NULL,
                season_year INTEGER NOT NULL DEFAULT 2025,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert test dynasty
        cursor.execute("""
            INSERT INTO dynasties
            (dynasty_id, dynasty_name, owner_name, team_id, season_year)
            VALUES ('test_dynasty', 'Test Dynasty', 'Test Owner', 1, 2024)
        """)

        # stage_state table (for StageController persistence)
        cursor.execute("""
            CREATE TABLE stage_state (
                dynasty_id TEXT NOT NULL,
                stage_type TEXT NOT NULL,
                season_year INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dynasty_id)
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

    def _initialize_season_1_state(self, db_path: str, dynasty_id: str):
        """Initialize Season 1 at OFFSEASON_WAIVER_WIRE stage with standings."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Set dynasty_state to Season 1 (2024)
        # Set week to a high number to ensure we're past all offseason stages
        # (StageController will load actual stage from stage_state table)
        cursor.execute("""
            INSERT INTO dynasty_state
            (dynasty_id, season, current_date, current_phase, current_week)
            VALUES (?, 2024, '2025-07-31', 'offseason', 12)
        """, (dynasty_id,))

        # Set stage to OFFSEASON_WAIVER_WIRE
        cursor.execute("""
            INSERT INTO stage_state
            (dynasty_id, stage_type, season_year, completed)
            VALUES (?, 'OFFSEASON_WAIVER_WIRE', 2024, 0)
        """, (dynasty_id,))

        # Create Season 1 standings with non-zero records (simulating completed season)
        # Team 1 (user's team): 12-5
        cursor.execute("""
            INSERT INTO standings
            (dynasty_id, season, team_id, season_type, wins, losses, ties)
            VALUES (?, 2024, 1, 'regular_season', 12, 5, 0)
        """, (dynasty_id,))

        # Team 2: 11-6
        cursor.execute("""
            INSERT INTO standings
            (dynasty_id, season, team_id, season_type, wins, losses, ties)
            VALUES (?, 2024, 2, 'regular_season', 11, 6, 0)
        """, (dynasty_id,))

        # Teams 3-32: Various records
        for team_id in range(3, 33):
            wins = 8
            losses = 9
            cursor.execute("""
                INSERT INTO standings
                (dynasty_id, season, team_id, season_type, wins, losses, ties)
                VALUES (?, 2024, ?, 'regular_season', ?, ?, 0)
            """, (dynasty_id, team_id, wins, losses))

        conn.commit()
        conn.close()

    def _get_standings_count(self, db_path: str, dynasty_id: str, season: int) -> int:
        """Get count of standings records for a given season."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM standings
            WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season'
        """, (dynasty_id, season))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _get_team_record(self, db_path: str, dynasty_id: str, season: int, team_id: int):
        """Get a team's W-L-T record for a given season."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wins, losses, ties FROM standings
            WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = 'regular_season'
        """, (dynasty_id, season, team_id))
        row = cursor.fetchone()
        conn.close()
        return row

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    def test_season_rollover_increments_ssot(self, test_db_path):
        """
        Verify advancing from waiver wire to Week 1 increments season SSOT.

        Flow:
        1. Start at OFFSEASON_WAIVER_WIRE (Season 2024)
        2. Advance to REGULAR_WEEK_1 (should become Season 2025)
        3. Verify dynasty_state.season = 2025
        """
        dynasty_id = 'test_dynasty'

        # Setup: Initialize Season 1 state
        self._initialize_season_1_state(test_db_path, dynasty_id)

        # Verify initial season is 2024
        api = DynastyStateAPI(test_db_path)
        state = api.get_latest_state(dynasty_id)
        assert state['season'] == 2024

        # Create StageController and advance to next stage
        controller = StageController(
            db_path=test_db_path,
            dynasty_id=dynasty_id
        )

        # Current stage should be OFFSEASON_WAIVER_WIRE
        current = controller.current_stage
        assert current.stage_type == StageType.OFFSEASON_WAIVER_WIRE
        assert current.season_year == 2024

        # Advance to next stage (REGULAR_WEEK_1 of Season 2)
        next_stage = controller.advance_to_next_stage()

        # Verify new stage is REGULAR_WEEK_1 with season 2025
        assert next_stage is not None
        assert next_stage.stage_type == StageType.REGULAR_WEEK_1
        assert next_stage.season_year == 2025

        # Verify SSOT (dynasty_state.season) was incremented to 2025
        state = api.get_latest_state(dynasty_id)
        assert state['season'] == 2025

    def test_season_rollover_initializes_standings(self, test_db_path):
        """
        Verify advancing to Season 2 initializes 0-0 standings for all 32 teams.

        Flow:
        1. Start at OFFSEASON_WAIVER_WIRE (Season 1 with old standings)
        2. Advance to REGULAR_WEEK_1 (Season 2)
        3. Verify 32 teams have 0-0 records for Season 2
        """
        dynasty_id = 'test_dynasty'

        # Setup: Initialize Season 1 state with standings
        self._initialize_season_1_state(test_db_path, dynasty_id)

        # Verify Season 1 standings exist (32 teams)
        season_1_count = self._get_standings_count(test_db_path, dynasty_id, 2024)
        assert season_1_count == 32

        # Verify Team 1 has 12-5 record in Season 1
        team_1_s1 = self._get_team_record(test_db_path, dynasty_id, 2024, 1)
        assert team_1_s1 == (12, 5, 0)

        # Create StageController and advance to Season 2
        controller = StageController(
            db_path=test_db_path,
            dynasty_id=dynasty_id
        )

        controller.advance_to_next_stage()

        # Verify Season 2 standings exist (32 teams)
        season_2_count = self._get_standings_count(test_db_path, dynasty_id, 2025)
        assert season_2_count == 32

        # Verify ALL teams have 0-0 records in Season 2
        for team_id in range(1, 33):
            record = self._get_team_record(test_db_path, dynasty_id, 2025, team_id)
            assert record == (0, 0, 0), f"Team {team_id} should have 0-0-0 record, got {record}"

    def test_season_rollover_preserves_season_1_standings(self, test_db_path):
        """
        Verify Season 1 standings are preserved (not deleted) when advancing to Season 2.

        This ensures historical data is maintained.
        """
        dynasty_id = 'test_dynasty'

        # Setup: Initialize Season 1 state
        self._initialize_season_1_state(test_db_path, dynasty_id)

        # Verify Season 1 standings exist
        season_1_count_before = self._get_standings_count(test_db_path, dynasty_id, 2024)
        assert season_1_count_before == 32

        # Advance to Season 2
        controller = StageController(
            db_path=test_db_path,
            dynasty_id=dynasty_id
        )
        controller.advance_to_next_stage()

        # Verify Season 1 standings still exist
        season_1_count_after = self._get_standings_count(test_db_path, dynasty_id, 2024)
        assert season_1_count_after == 32

        # Verify Season 1 records unchanged
        team_1_s1 = self._get_team_record(test_db_path, dynasty_id, 2024, 1)
        assert team_1_s1 == (12, 5, 0)

    def test_season_rollover_full_flow(self, test_db_path):
        """
        Full integration test simulating the bug scenario:
        - User completes Season 1 (12-5 record)
        - Advances through offseason to Week 1 of Season 2
        - UI should show 0-0 standings, NOT 12-5

        This is the original bug that was being fixed.
        """
        dynasty_id = 'test_dynasty'

        # Setup: Complete Season 1
        self._initialize_season_1_state(test_db_path, dynasty_id)

        # Create controller
        controller = StageController(
            db_path=test_db_path,
            dynasty_id=dynasty_id
        )

        # Verify we're at waiver wire (end of Season 1)
        assert controller.current_stage.stage_type == StageType.OFFSEASON_WAIVER_WIRE
        assert controller.current_stage.season_year == 2024

        # Advance to Season 2 Week 1 (this is where the bug occurred)
        next_stage = controller.advance_to_next_stage()

        # Verify we're at Week 1 of Season 2
        assert next_stage.stage_type == StageType.REGULAR_WEEK_1
        assert next_stage.season_year == 2025

        # Verify SSOT is Season 2
        api = DynastyStateAPI(test_db_path)
        state = api.get_latest_state(dynasty_id)
        assert state['season'] == 2025

        # Verify UI would get correct standings (0-0, not 12-5)
        standings = controller.get_standings()

        # Should have 32 teams
        assert len(standings) >= 32

        # User's team (team_id=1) should show 0-0, NOT 12-5
        user_team_standings = next((s for s in standings if s['team_id'] == 1), None)
        assert user_team_standings is not None
        assert user_team_standings['wins'] == 0
        assert user_team_standings['losses'] == 0
        assert user_team_standings['ties'] == 0

        # All other teams should also be 0-0
        for team in standings:
            assert team['wins'] == 0
            assert team['losses'] == 0
            assert team['ties'] == 0
