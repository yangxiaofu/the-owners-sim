"""
Unit tests for DirectiveLoader.

Tests loading owner directives with season offset logic and error handling.
"""

import pytest
import tempfile
import os
import sqlite3

from game_cycle.services.directive_loader import DirectiveLoader
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.draft_direction import DraftDirection, DraftStrategy
from game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy
from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.owner_directives_api import OwnerDirectivesAPI


@pytest.fixture
def test_db_path(monkeypatch):
    """Create temporary database for testing with foreign keys disabled."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Monkeypatch GameCycleDatabase to disable foreign keys for testing
    original_get_connection = GameCycleDatabase.get_connection

    def patched_get_connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            # Disable foreign keys for testing
            self._connection.execute("PRAGMA foreign_keys = OFF")
            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    monkeypatch.setattr(GameCycleDatabase, "get_connection", patched_get_connection)

    # Initialize database with schema
    db = GameCycleDatabase(path)
    db.get_connection()  # Trigger initialization

    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def sample_directives():
    """Create sample owner directives for testing."""
    return OwnerDirectives(
        dynasty_id="test_dynasty",
        team_id=22,  # Detroit Lions
        season=2026,
        target_wins=12,
        priority_positions=["QB", "EDGE", "WR"],
        fa_wishlist=["John Smith", "Mike Jones"],
        draft_wishlist=["Tom Wilson"],
        draft_strategy="bpa",
        fa_philosophy="aggressive",
        max_contract_years=4,
        max_guaranteed_percent=0.65,
        team_philosophy="win_now",
        budget_stance="aggressive",
        protected_player_ids=[100, 101],
        expendable_player_ids=[200, 201, 202],
        owner_notes="Go all in this year",
        trust_gm=True,
    )


class TestDirectiveLoader:
    """Tests for DirectiveLoader class."""

    def test_load_directives_with_valid_data(self, test_db_path, sample_directives):
        """Test loading directives with valid dynasty/team/season."""
        # Setup: Save directives to database
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load directives
        loader = DirectiveLoader(test_db_path)
        result = loader.load_directives(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2026,
            apply_season_offset=False
        )

        # Verify: All fields match
        assert result is not None
        assert result.dynasty_id == "test_dynasty"
        assert result.team_id == 22
        assert result.season == 2026
        assert result.target_wins == 12
        assert result.priority_positions == ["QB", "EDGE", "WR"]
        assert result.fa_wishlist == ["John Smith", "Mike Jones"]
        assert result.draft_wishlist == ["Tom Wilson"]
        assert result.draft_strategy == "bpa"
        assert result.fa_philosophy == "aggressive"
        assert result.max_contract_years == 4
        assert result.max_guaranteed_percent == 0.65
        assert result.team_philosophy == "win_now"
        assert result.budget_stance == "aggressive"
        assert result.protected_player_ids == [100, 101]
        assert result.expendable_player_ids == [200, 201, 202]
        assert result.owner_notes == "Go all in this year"
        assert result.trust_gm is True

    def test_load_directives_with_missing_data(self, test_db_path):
        """Test loading when no directives exist (should return None)."""
        loader = DirectiveLoader(test_db_path)
        result = loader.load_directives(
            dynasty_id="nonexistent_dynasty",
            team_id=1,
            season=2025,
            apply_season_offset=False
        )
        assert result is None

    def test_load_directives_season_offset_applied(self, test_db_path, sample_directives):
        """Test that season+1 is used when apply_season_offset=True."""
        # Setup: Save directives for season 2026
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load with season 2025 + offset (should load 2026 data)
        loader = DirectiveLoader(test_db_path)
        result = loader.load_directives(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2025,  # Current season
            apply_season_offset=True  # Will load 2025 + 1 = 2026
        )

        # Verify: Loaded directives from season 2026
        assert result is not None
        assert result.season == 2026
        assert result.target_wins == 12

    def test_load_directives_season_offset_not_applied(self, test_db_path, sample_directives):
        """Test that season is used when apply_season_offset=False."""
        # Setup: Save directives for season 2026
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load with season 2026, no offset
        loader = DirectiveLoader(test_db_path)
        result = loader.load_directives(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2026,
            apply_season_offset=False
        )

        # Verify: Loaded directives from season 2026
        assert result is not None
        assert result.season == 2026

        # Test: Load with season 2025, no offset (should return None)
        result = loader.load_directives(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2025,
            apply_season_offset=False
        )
        assert result is None

    def test_load_for_draft(self, test_db_path, sample_directives):
        """Test conversion to DraftDirection."""
        # Setup: Save directives
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load for draft (should apply season offset)
        loader = DirectiveLoader(test_db_path)
        result = loader.load_for_draft(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2025  # Will load 2025+1=2026
        )

        # Verify: Returns DraftDirection with correct values
        assert result is not None
        assert isinstance(result, DraftDirection)
        assert result.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE
        assert result.priority_positions == ["QB", "EDGE", "WR"]
        assert result.watchlist_prospect_ids == []  # Names stored, IDs resolved at runtime

    def test_load_for_draft_with_no_directives(self, test_db_path):
        """Test load_for_draft returns None when no directives exist."""
        loader = DirectiveLoader(test_db_path)
        result = loader.load_for_draft(
            dynasty_id="nonexistent",
            team_id=1,
            season=2025
        )
        assert result is None

    def test_load_for_fa(self, test_db_path, sample_directives):
        """Test conversion to FAGuidance."""
        # Setup: Save directives
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load for FA (should apply season offset)
        loader = DirectiveLoader(test_db_path)
        result = loader.load_for_fa(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2025  # Will load 2025+1=2026
        )

        # Verify: Returns FAGuidance with correct values
        assert result is not None
        assert isinstance(result, FAGuidance)
        assert result.philosophy == FAPhilosophy.AGGRESSIVE
        assert result.priority_positions == ["QB", "EDGE", "WR"]  # Max 3
        assert result.wishlist_names == ["John Smith", "Mike Jones"]
        assert result.max_contract_years == 4
        assert result.max_guaranteed_percent == 0.65

    def test_load_for_fa_with_no_directives(self, test_db_path):
        """Test load_for_fa returns None when no directives exist."""
        loader = DirectiveLoader(test_db_path)
        result = loader.load_for_fa(
            dynasty_id="nonexistent",
            team_id=1,
            season=2025
        )
        assert result is None

    def test_load_with_trust_gm(self, test_db_path, sample_directives):
        """Test loading with trust_gm flag extraction."""
        # Setup: Save directives with trust_gm=True
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives)

        # Test: Load with trust_gm helper (applies season offset by default)
        loader = DirectiveLoader(test_db_path)
        directives, trust_gm = loader.load_with_trust_gm(
            dynasty_id="test_dynasty",
            team_id=22,
            season=2025  # Will load 2025+1=2026
        )

        # Verify: Both directives and trust_gm returned
        assert directives is not None
        assert trust_gm is True
        assert directives.trust_gm is True

    def test_load_with_trust_gm_false(self, test_db_path):
        """Test trust_gm flag when directives don't exist."""
        loader = DirectiveLoader(test_db_path)
        directives, trust_gm = loader.load_with_trust_gm(
            dynasty_id="nonexistent",
            team_id=1,
            season=2025
        )

        # Verify: Directives None, trust_gm False
        assert directives is None
        assert trust_gm is False

    def test_load_directives_handles_database_error(self, test_db_path):
        """Test error handling when database operations fail."""
        # Use invalid path to trigger error
        loader = DirectiveLoader("/invalid/path/to/database.db")

        # Should return None on error, not raise exception
        result = loader.load_directives(
            dynasty_id="test",
            team_id=1,
            season=2025
        )
        assert result is None

    def test_load_for_draft_with_different_strategies(self, test_db_path):
        """Test all draft strategy conversions."""
        strategies = {
            "bpa": DraftStrategy.BEST_PLAYER_AVAILABLE,
            "balanced": DraftStrategy.BALANCED,
            "needs_based": DraftStrategy.NEEDS_BASED,
            "position_focus": DraftStrategy.POSITION_FOCUS,
        }

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        loader = DirectiveLoader(test_db_path)

        for strategy_str, expected_enum in strategies.items():
            # Create directives with this strategy
            directives = OwnerDirectives(
                dynasty_id="test",
                team_id=1,
                season=2026,
                draft_strategy=strategy_str,
            )
            api.save_directives(directives)

            # Load and verify conversion
            result = loader.load_for_draft("test", 1, 2025)
            assert result.strategy == expected_enum

    def test_load_for_fa_with_different_philosophies(self, test_db_path):
        """Test all FA philosophy conversions."""
        philosophies = {
            "aggressive": FAPhilosophy.AGGRESSIVE,
            "balanced": FAPhilosophy.BALANCED,
            "conservative": FAPhilosophy.CONSERVATIVE,
        }

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        loader = DirectiveLoader(test_db_path)

        for philosophy_str, expected_enum in philosophies.items():
            # Create directives with this philosophy
            directives = OwnerDirectives(
                dynasty_id="test",
                team_id=1,
                season=2026,
                fa_philosophy=philosophy_str,
            )
            api.save_directives(directives)

            # Load and verify conversion
            result = loader.load_for_fa("test", 1, 2025)
            assert result.philosophy == expected_enum

    def test_load_for_fa_respects_max_3_priority_positions(self, test_db_path):
        """Test that FA guidance only takes first 3 priority positions."""
        # Create directives with 5 priority positions
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            priority_positions=["QB", "EDGE", "WR", "CB", "OT"],
        )

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(directives)

        # Load for FA
        loader = DirectiveLoader(test_db_path)
        result = loader.load_for_fa("test", 1, 2025)

        # Verify: Only first 3 positions
        assert len(result.priority_positions) == 3
        assert result.priority_positions == ["QB", "EDGE", "WR"]
