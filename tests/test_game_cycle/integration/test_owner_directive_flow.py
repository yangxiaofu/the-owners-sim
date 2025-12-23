"""
Integration tests for owner directive flow.

Tests directives from Strategic Direction → Draft/FA preview display.
Verifies end-to-end flow from database storage to service usage.
"""

import pytest
import tempfile
import os
import sqlite3

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.owner_directives_api import OwnerDirectivesAPI
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.services.directive_loader import DirectiveLoader
from game_cycle.services.owner_influence_calculator import OwnerInfluenceCalculator
from game_cycle.handlers.offseason import OffseasonHandler
from game_cycle.stage_definitions import Stage, StageType


@pytest.fixture
def test_db_path(monkeypatch):
    """Create temporary database for testing with foreign keys disabled."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Monkeypatch GameCycleDatabase to disable foreign keys for testing
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
def sample_directives_aggressive():
    """Create aggressive owner directives for testing."""
    return OwnerDirectives(
        dynasty_id="test_dynasty",
        team_id=22,  # Detroit Lions
        season=2026,
        target_wins=14,
        priority_positions=["QB", "EDGE", "WR"],
        fa_wishlist=["Elite WR", "Star EDGE"],
        draft_wishlist=["Top QB Prospect"],
        draft_strategy="bpa",
        fa_philosophy="aggressive",
        max_contract_years=3,
        max_guaranteed_percent=0.5,
        team_philosophy="win_now",
        budget_stance="aggressive",
        protected_player_ids=[100, 101],
        expendable_player_ids=[200],
        owner_notes="Go all in this year",
        trust_gm=True,
    )


@pytest.fixture
def sample_directives_conservative():
    """Create conservative owner directives for testing."""
    return OwnerDirectives(
        dynasty_id="test_dynasty",
        team_id=1,
        season=2026,
        target_wins=10,
        priority_positions=["OL", "DL"],
        fa_wishlist=[],
        draft_wishlist=[],
        draft_strategy="balanced",
        fa_philosophy="conservative",
        max_contract_years=4,
        max_guaranteed_percent=0.65,
        team_philosophy="rebuild",
        budget_stance="conservative",
        protected_player_ids=[],
        expendable_player_ids=[],
        owner_notes="Build through draft",
        trust_gm=False,
    )


class TestDirectiveFlowEndToEnd:
    """Integration tests for directive flow from database to preview."""

    def test_directive_flow_end_to_end(self, test_db_path, sample_directives_aggressive):
        """
        Test directives from Strategic Direction → Draft/FA display.

        Steps:
        1. Create dynasty and save directives via OwnerDirectivesAPI
        2. Load Draft preview - verify directives in preview['owner_directives']
        3. Verify priority_positions, draft_strategy present
        4. Load FA preview - verify directives in preview['owner_directives']
        5. Verify fa_philosophy, max_contract_years, max_guaranteed_percent present
        6. Test trust_gm auto-approval in Draft preview
        7. Test trust_gm auto-approval in FA preview
        """
        # Step 1: Save directives to database
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives_aggressive)

        # Verify directives saved correctly
        loaded = api.get_directives("test_dynasty", 22, 2026)
        assert loaded is not None
        assert loaded.trust_gm is True
        assert loaded.fa_philosophy == "aggressive"
        assert loaded.draft_strategy == "bpa"

        # Step 2: Load directives using DirectiveLoader
        loader = DirectiveLoader(test_db_path)
        directives = loader.load_directives("test_dynasty", 22, 2025, apply_season_offset=True)

        assert directives is not None
        assert directives.season == 2026
        assert directives.priority_positions == ["QB", "EDGE", "WR"]
        assert directives.fa_wishlist == ["Elite WR", "Star EDGE"]
        assert directives.draft_wishlist == ["Top QB Prospect"]

        # Step 3: Verify conversion to DraftDirection
        draft_direction = loader.load_for_draft("test_dynasty", 22, 2025)
        assert draft_direction is not None
        assert draft_direction.priority_positions == ["QB", "EDGE", "WR"]
        assert str(draft_direction.strategy.value) == "bpa"

        # Step 4: Verify conversion to FAGuidance
        fa_guidance = loader.load_for_fa("test_dynasty", 22, 2025)
        assert fa_guidance is not None
        assert str(fa_guidance.philosophy.value) == "aggressive"
        assert fa_guidance.priority_positions == ["QB", "EDGE", "WR"]
        assert fa_guidance.wishlist_names == ["Elite WR", "Star EDGE"]
        assert fa_guidance.max_contract_years == 3
        assert fa_guidance.max_guaranteed_percent == 0.5

        # Step 5: Test trust_gm auto-approval
        calculator = OwnerInfluenceCalculator()
        assert calculator.should_auto_approve(directives, StageType.OFFSEASON_DRAFT) is True
        assert calculator.should_auto_approve(directives, StageType.OFFSEASON_FREE_AGENCY) is True

        # Step 6: Verify directives_dict format for UI display
        directives_dict = directives.to_dict()
        assert directives_dict["trust_gm"] is True
        assert directives_dict["priority_positions"] == ["QB", "EDGE", "WR"]
        assert directives_dict["fa_philosophy"] == "aggressive"
        assert directives_dict["draft_strategy"] == "bpa"
        assert directives_dict["max_contract_years"] == 3
        assert directives_dict["max_guaranteed_percent"] == 0.5

    def test_contract_constraints_enforced_in_proposals(self, test_db_path):
        """Test that max_contract_years and max_guaranteed_percent are enforced."""
        # Create directives with max_contract_years=3, max_guaranteed_percent=0.5
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            max_contract_years=3,
            max_guaranteed_percent=0.5,
        )

        # Save to database
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(directives)

        # Load and verify constraints
        loader = DirectiveLoader(test_db_path)
        loaded = loader.load_directives("test", 1, 2025, apply_season_offset=True)

        # Apply contract constraints to proposal
        calculator = OwnerInfluenceCalculator()
        proposal = {
            "contract_years": 5,
            "total_value": 50_000_000,
            "guaranteed_money": 40_000_000,  # 80% guaranteed
        }

        constrained = calculator.apply_contract_constraints(proposal, loaded)

        # Verify constraints applied
        assert constrained["contract_years"] == 3  # Capped at max_contract_years
        assert constrained["guaranteed_money"] == 25_000_000  # Capped at 50% of 50M

    def test_directive_flow_with_no_directives(self, test_db_path):
        """Test graceful handling when no directives exist."""
        # No directives saved to database

        # Try to load directives
        loader = DirectiveLoader(test_db_path)
        directives = loader.load_directives("nonexistent", 1, 2025)

        # Should return None
        assert directives is None

        # Load for draft should return None
        draft_direction = loader.load_for_draft("nonexistent", 1, 2025)
        assert draft_direction is None

        # Load for FA should return None
        fa_guidance = loader.load_for_fa("nonexistent", 1, 2025)
        assert fa_guidance is None

        # Trust GM helper should return False
        directives, trust_gm = loader.load_with_trust_gm("nonexistent", 1, 2025)
        assert directives is None
        assert trust_gm is False

    def test_directive_flow_with_trust_gm_disabled(self, test_db_path, sample_directives_conservative):
        """Test directive flow when trust_gm is disabled."""
        # Save directives with trust_gm=False
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives_conservative)

        # Load directives
        loader = DirectiveLoader(test_db_path)
        directives = loader.load_directives("test_dynasty", 1, 2025, apply_season_offset=True)

        assert directives is not None
        assert directives.trust_gm is False

        # Verify auto-approval is disabled
        calculator = OwnerInfluenceCalculator()
        assert calculator.should_auto_approve(directives, StageType.OFFSEASON_DRAFT) is False
        assert calculator.should_auto_approve(directives, StageType.OFFSEASON_FREE_AGENCY) is False

    def test_priority_position_bonuses(self, test_db_path, sample_directives_aggressive):
        """Test that priority positions receive correct bonuses."""
        # Save directives
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives_aggressive)

        # Load directives
        loader = DirectiveLoader(test_db_path)
        directives = loader.load_directives("test_dynasty", 22, 2025, apply_season_offset=True)

        # Calculate position bonuses
        calculator = OwnerInfluenceCalculator()

        # 1st priority (QB) should get 0.85
        qb_bonus = calculator.calculate_position_priority_bonus("QB", directives)
        assert qb_bonus == 0.85

        # 2nd priority (EDGE) should get 0.70
        edge_bonus = calculator.calculate_position_priority_bonus("EDGE", directives)
        assert edge_bonus == 0.70

        # 3rd priority (WR) should get 0.55
        wr_bonus = calculator.calculate_position_priority_bonus("WR", directives)
        assert wr_bonus == 0.55

        # Non-priority (RB) should get 0.0
        rb_bonus = calculator.calculate_position_priority_bonus("RB", directives)
        assert rb_bonus == 0.0

    def test_fa_philosophy_multipliers(self, test_db_path, sample_directives_aggressive):
        """Test FA philosophy multipliers are applied correctly."""
        # Save aggressive directives
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives_aggressive)

        # Load and convert to FA guidance
        loader = DirectiveLoader(test_db_path)
        fa_guidance = loader.load_for_fa("test_dynasty", 22, 2025)

        # Verify aggressive philosophy
        assert fa_guidance.get_max_offer_multiplier() == 1.15

        # Verify player pursuit threshold (70+ OVR for aggressive)
        assert fa_guidance.should_pursue_player(70) is True
        assert fa_guidance.should_pursue_player(85) is True
        assert fa_guidance.should_pursue_player(69) is False

    def test_protected_and_expendable_players(self, test_db_path, sample_directives_aggressive):
        """Test protected and expendable player lists."""
        # Save directives
        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(sample_directives_aggressive)

        # Load directives
        loader = DirectiveLoader(test_db_path)
        directives = loader.load_directives("test_dynasty", 22, 2025, apply_season_offset=True)

        # Verify protected players
        calculator = OwnerInfluenceCalculator()
        assert calculator.is_player_protected(100, directives) is True
        assert calculator.is_player_protected(101, directives) is True
        assert calculator.is_player_protected(999, directives) is False

        # Verify expendable players
        assert calculator.is_player_expendable(200, directives) is True
        assert calculator.is_player_expendable(100, directives) is False  # Protected, not expendable

    def test_season_offset_logic(self, test_db_path):
        """Test that season offset is correctly applied for offseason stages."""
        # Save directives for season 2026
        directives_2026 = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            draft_strategy="bpa",
        )

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(directives_2026)

        # Load with season 2025 + offset=True (should load 2026)
        loader = DirectiveLoader(test_db_path)
        loaded_with_offset = loader.load_directives("test", 1, 2025, apply_season_offset=True)
        assert loaded_with_offset is not None
        assert loaded_with_offset.season == 2026

        # Load with season 2025 + offset=False (should return None)
        loaded_without_offset = loader.load_directives("test", 1, 2025, apply_season_offset=False)
        assert loaded_without_offset is None

        # Load with season 2026 + offset=False (should load 2026)
        loaded_exact = loader.load_directives("test", 1, 2026, apply_season_offset=False)
        assert loaded_exact is not None
        assert loaded_exact.season == 2026

    def test_multiple_teams_directive_isolation(self, test_db_path):
        """Test that directives are isolated by team_id."""
        # Save directives for team 1
        directives_team1 = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            draft_strategy="bpa",
            fa_philosophy="aggressive",
        )

        # Save directives for team 2
        directives_team2 = OwnerDirectives(
            dynasty_id="test",
            team_id=2,
            season=2026,
            draft_strategy="needs_based",
            fa_philosophy="conservative",
        )

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(directives_team1)
        api.save_directives(directives_team2)

        # Load team 1 directives
        loader = DirectiveLoader(test_db_path)
        team1_loaded = loader.load_directives("test", 1, 2026, apply_season_offset=False)
        assert team1_loaded.draft_strategy == "bpa"
        assert team1_loaded.fa_philosophy == "aggressive"

        # Load team 2 directives
        team2_loaded = loader.load_directives("test", 2, 2026, apply_season_offset=False)
        assert team2_loaded.draft_strategy == "needs_based"
        assert team2_loaded.fa_philosophy == "conservative"

    def test_directive_update_replaces_old_values(self, test_db_path):
        """Test that saving directives replaces old values (upsert behavior)."""
        # Save initial directives
        initial = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            draft_strategy="bpa",
            trust_gm=False,
        )

        db = GameCycleDatabase(test_db_path)
        api = OwnerDirectivesAPI(db)
        api.save_directives(initial)

        # Update directives
        updated = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2026,
            draft_strategy="needs_based",
            trust_gm=True,
        )
        api.save_directives(updated)

        # Load and verify updated values
        loader = DirectiveLoader(test_db_path)
        loaded = loader.load_directives("test", 1, 2026, apply_season_offset=False)
        assert loaded.draft_strategy == "needs_based"
        assert loaded.trust_gm is True

    def test_fa_guidance_max_3_priority_positions(self, test_db_path):
        """Test that FA guidance respects max 3 priority positions."""
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

        # Load as FA guidance
        loader = DirectiveLoader(test_db_path)
        fa_guidance = loader.load_for_fa("test", 1, 2025)

        # Should only have first 3 positions
        assert len(fa_guidance.priority_positions) == 3
        assert fa_guidance.priority_positions == ["QB", "EDGE", "WR"]

    def test_draft_direction_all_strategies(self, test_db_path):
        """Test all draft strategy conversions."""
        from game_cycle.models.draft_direction import DraftStrategy

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
            draft_direction = loader.load_for_draft("test", 1, 2025)
            assert draft_direction.strategy == expected_enum

    def test_fa_guidance_all_philosophies(self, test_db_path):
        """Test all FA philosophy conversions."""
        from game_cycle.models.fa_guidance import FAPhilosophy

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
            fa_guidance = loader.load_for_fa("test", 1, 2025)
            assert fa_guidance.philosophy == expected_enum
