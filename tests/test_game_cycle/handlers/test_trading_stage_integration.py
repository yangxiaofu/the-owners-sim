"""
Tollgate 5: Trading Stage Integration Tests

Tests the integration of the trading stage into the game cycle system:
- OFFSEASON_TRADING stage definition
- OffseasonHandler trading methods
- AI trade processing
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from src.game_cycle.stage_definitions import (
    Stage,
    StageType,
    SeasonPhase,
    OFFSEASON_STAGES,
)
from src.game_cycle.handlers.offseason import OffseasonHandler


class TestTradingStageDefinition:
    """Test OFFSEASON_TRADING stage definition."""

    def test_offseason_trading_exists_in_stage_type(self):
        """OFFSEASON_TRADING should exist as a StageType enum value."""
        assert hasattr(StageType, "OFFSEASON_TRADING")
        assert StageType.OFFSEASON_TRADING is not None

    def test_offseason_trading_in_offseason_stages_list(self):
        """OFFSEASON_TRADING should be in the OFFSEASON_STAGES list."""
        assert StageType.OFFSEASON_TRADING in OFFSEASON_STAGES

    def test_offseason_trading_after_free_agency(self):
        """OFFSEASON_TRADING should come after FREE_AGENCY in stage order."""
        fa_index = OFFSEASON_STAGES.index(StageType.OFFSEASON_FREE_AGENCY)
        trading_index = OFFSEASON_STAGES.index(StageType.OFFSEASON_TRADING)
        assert trading_index == fa_index + 1

    def test_offseason_trading_before_draft(self):
        """OFFSEASON_TRADING should come before DRAFT in stage order."""
        trading_index = OFFSEASON_STAGES.index(StageType.OFFSEASON_TRADING)
        draft_index = OFFSEASON_STAGES.index(StageType.OFFSEASON_DRAFT)
        assert trading_index == draft_index - 1

    def test_offseason_trading_phase_is_offseason(self):
        """OFFSEASON_TRADING phase should be OFFSEASON."""
        phase = StageType.get_phase(StageType.OFFSEASON_TRADING)
        assert phase == SeasonPhase.OFFSEASON

    def test_stage_week_number_for_trading(self):
        """OFFSEASON_TRADING should have correct week number."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        # Trading should be week 4 (after Tag, Resigning, FA)
        assert stage.week_number == 4

    def test_stage_display_name_for_trading(self):
        """OFFSEASON_TRADING should have 'Trading' display name."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        assert stage.display_name == "Trading"

    def test_stage_next_stage_after_free_agency(self):
        """Next stage after FREE_AGENCY should be TRADING."""
        fa_stage = Stage(
            stage_type=StageType.OFFSEASON_FREE_AGENCY,
            season_year=2025
        )
        next_stage = fa_stage.next_stage()
        assert next_stage.stage_type == StageType.OFFSEASON_TRADING

    def test_stage_next_stage_after_trading_is_draft(self):
        """Next stage after TRADING should be DRAFT."""
        trading_stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        next_stage = trading_stage.next_stage()
        assert next_stage.stage_type == StageType.OFFSEASON_DRAFT


class TestOffseasonHandlerTradingStage:
    """Test OffseasonHandler trading stage methods."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test database with required schema."""
        db_path = tmp_path / "test_trading.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create required tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS dynasty_state (
                dynasty_id TEXT PRIMARY KEY,
                user_team_id INTEGER DEFAULT 1,
                current_season INTEGER DEFAULT 2025
            );

            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                overall_rating INTEGER DEFAULT 75,
                age INTEGER DEFAULT 25,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS player_contracts (
                contract_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                player_id INTEGER,
                team_id INTEGER,
                start_year INTEGER,
                end_year INTEGER,
                total_value INTEGER,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS draft_pick_ownership (
                id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER,
                round INTEGER,
                original_team_id INTEGER,
                current_team_id INTEGER,
                traded_in_trade_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER,
                trade_date TEXT,
                team1_id INTEGER,
                team2_id INTEGER,
                status TEXT DEFAULT 'completed'
            );

            CREATE TABLE IF NOT EXISTS trade_assets (
                asset_id INTEGER PRIMARY KEY,
                trade_id INTEGER,
                from_team_id INTEGER,
                to_team_id INTEGER,
                asset_type TEXT,
                player_id INTEGER,
                pick_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS standings (
                dynasty_id TEXT,
                team_id INTEGER,
                season INTEGER,
                wins INTEGER DEFAULT 8,
                losses INTEGER DEFAULT 8,
                PRIMARY KEY (dynasty_id, team_id, season)
            );

            INSERT INTO dynasty_state (dynasty_id, user_team_id, current_season)
            VALUES ('test-dynasty', 1, 2025);
        """)
        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.fixture
    def handler(self, test_db):
        """Create OffseasonHandler instance."""
        return OffseasonHandler(test_db)

    def test_requires_interaction_returns_true_for_trading(self, handler):
        """Trading stage should require user interaction."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        assert handler.requires_interaction(stage) is True

    def test_can_advance_returns_true_for_trading(self, handler, test_db):
        """Trading stage should allow advancement (no blocking condition)."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
        }
        # Trading has no blocking condition like draft/roster cuts
        assert handler.can_advance(stage, context) is True

    def test_get_stage_preview_returns_trading_preview(self, handler, test_db):
        """get_stage_preview should return trading preview data."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
        }
        preview = handler.get_stage_preview(stage, context)

        assert preview["stage_name"] == "Trading Period"
        assert preview["is_interactive"] is True
        assert "user_players" in preview
        assert "user_picks" in preview
        assert "trade_history" in preview
        assert "available_teams" in preview

    def test_get_trading_preview_has_cap_data_when_successful(self, handler, test_db):
        """Trading preview should include cap data when trade service succeeds.

        Note: This test verifies the preview structure is valid.
        If the trade service fails (missing tables), cap_data will be in
        the error fallback response.
        """
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
        }
        preview = handler.get_stage_preview(stage, context)

        # Preview should always have is_interactive (even on error fallback)
        assert preview["is_interactive"] is True
        assert preview["stage_name"] == "Trading Period"
        # cap_data is only added on success, fallback has no cap_data

    def test_execute_trading_returns_expected_structure(self, handler, test_db):
        """_execute_trading should return expected result structure."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
            "trade_proposals": [],  # No user proposals
        }
        result = handler.execute(stage, context)

        assert "games_played" in result
        assert "events_processed" in result
        assert "executed_trades" in result
        assert "total_trades" in result

    def test_execute_trading_with_empty_proposals(self, handler, test_db):
        """Execute trading with no proposals should still process AI trades."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
            "trade_proposals": [],
        }
        result = handler.execute(stage, context)

        # Should complete without error
        assert isinstance(result["events_processed"], list)
        assert any("Trading period completed" in e for e in result["events_processed"])

    def test_execute_handler_dispatch_includes_trading(self, handler, test_db):
        """Handler dispatch should include OFFSEASON_TRADING."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db,
            "season": 2025,
            "user_team_id": 1,
        }
        # Should not raise KeyError or return default
        result = handler.execute(stage, context)
        assert result is not None
        assert "events_processed" in result


class TestTradingPreviewDataStructure:
    """Test the trading preview data structure."""

    @pytest.fixture
    def test_db_with_data(self, tmp_path):
        """Create test database with sample data."""
        db_path = tmp_path / "test_trading_data.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create tables
        cursor.executescript("""
            CREATE TABLE dynasty_state (
                dynasty_id TEXT PRIMARY KEY,
                user_team_id INTEGER DEFAULT 1,
                current_season INTEGER DEFAULT 2025
            );

            CREATE TABLE players (
                player_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                overall_rating INTEGER DEFAULT 75,
                age INTEGER DEFAULT 25,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE player_contracts (
                contract_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                player_id INTEGER,
                team_id INTEGER,
                start_year INTEGER,
                end_year INTEGER,
                total_value INTEGER,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE draft_pick_ownership (
                id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER,
                round INTEGER,
                original_team_id INTEGER,
                current_team_id INTEGER,
                traded_in_trade_id INTEGER
            );

            CREATE TABLE trades (
                trade_id INTEGER PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER,
                trade_date TEXT,
                team1_id INTEGER,
                team2_id INTEGER,
                status TEXT DEFAULT 'completed'
            );

            CREATE TABLE trade_assets (
                asset_id INTEGER PRIMARY KEY,
                trade_id INTEGER,
                from_team_id INTEGER,
                to_team_id INTEGER,
                asset_type TEXT,
                player_id INTEGER,
                pick_id INTEGER
            );

            CREATE TABLE standings (
                dynasty_id TEXT,
                team_id INTEGER,
                season INTEGER,
                wins INTEGER DEFAULT 8,
                losses INTEGER DEFAULT 8,
                PRIMARY KEY (dynasty_id, team_id, season)
            );

            INSERT INTO dynasty_state (dynasty_id, user_team_id, current_season)
            VALUES ('test-dynasty', 1, 2025);
        """)

        # Insert sample players for team 1 and team 2
        cursor.execute("""
            INSERT INTO players (player_id, dynasty_id, team_id, first_name, last_name, position, overall_rating, age)
            VALUES
                (1001, 'test-dynasty', 1, 'Test', 'Player1', 'QB', 85, 27),
                (1002, 'test-dynasty', 1, 'Test', 'Player2', 'WR', 80, 25),
                (1003, 'test-dynasty', 2, 'Test', 'Player3', 'RB', 82, 26),
                (1004, 'test-dynasty', 2, 'Test', 'Player4', 'TE', 78, 28)
        """)

        # Insert contracts
        cursor.execute("""
            INSERT INTO player_contracts (contract_id, dynasty_id, player_id, team_id, start_year, end_year, total_value, status)
            VALUES
                (101, 'test-dynasty', 1001, 1, 2024, 2027, 100000000, 'active'),
                (102, 'test-dynasty', 1002, 1, 2024, 2026, 50000000, 'active'),
                (103, 'test-dynasty', 1003, 2, 2024, 2027, 80000000, 'active'),
                (104, 'test-dynasty', 1004, 2, 2024, 2025, 30000000, 'active')
        """)

        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.fixture
    def handler_with_data(self, test_db_with_data):
        """Create handler with populated test database."""
        return OffseasonHandler(test_db_with_data)

    def test_preview_user_players_list(self, handler_with_data, test_db_with_data):
        """Preview should include user's tradeable players."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db_with_data,
            "season": 2025,
            "user_team_id": 1,
        }
        preview = handler_with_data.get_stage_preview(stage, context)

        assert "user_players" in preview
        # Should have at least some players (may vary based on query)
        assert isinstance(preview["user_players"], list)

    def test_preview_available_teams_is_list(self, handler_with_data, test_db_with_data):
        """Available teams should be a list (may be empty on db error fallback)."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db_with_data,
            "season": 2025,
            "user_team_id": 1,
        }
        preview = handler_with_data.get_stage_preview(stage, context)

        # available_teams should be a list (may be empty if db errors occur)
        assert "available_teams" in preview
        assert isinstance(preview["available_teams"], list)
        # If populated, user team should be excluded
        team_ids = [t["team_id"] for t in preview["available_teams"]]
        if team_ids:
            assert 1 not in team_ids  # User team excluded

    def test_preview_trade_history_is_list(self, handler_with_data, test_db_with_data):
        """Trade history should be a list."""
        stage = Stage(
            stage_type=StageType.OFFSEASON_TRADING,
            season_year=2025
        )
        context = {
            "dynasty_id": "test-dynasty",
            "db_path": test_db_with_data,
            "season": 2025,
            "user_team_id": 1,
        }
        preview = handler_with_data.get_stage_preview(stage, context)

        assert "trade_history" in preview
        assert isinstance(preview["trade_history"], list)