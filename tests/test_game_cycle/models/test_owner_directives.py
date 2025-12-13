"""Unit tests for OwnerDirectives model."""
import pytest
from src.game_cycle.models.owner_directives import OwnerDirectives
from src.game_cycle.models.draft_direction import DraftStrategy
from src.game_cycle.models.fa_guidance import FAPhilosophy


class TestOwnerDirectivesSerialization:
    """Tests for to_dict and from_dict methods."""

    def test_to_dict_basic(self):
        """Verify to_dict returns all fields with correct types."""
        directives = OwnerDirectives(
            dynasty_id="test-dynasty",
            team_id=1,
            season=2025,
            target_wins=10,
            priority_positions=["QB", "WR"],
            draft_strategy="needs_based",
            fa_philosophy="aggressive",
        )
        result = directives.to_dict()
        assert result["dynasty_id"] == "test-dynasty"
        assert result["team_id"] == 1
        assert result["season"] == 2025
        assert result["target_wins"] == 10
        assert result["priority_positions"] == ["QB", "WR"]
        assert result["draft_strategy"] == "needs_based"
        assert result["fa_philosophy"] == "aggressive"

    def test_to_dict_copies_lists(self):
        """Verify to_dict creates copies of list fields (not references)."""
        original_positions = ["QB", "WR"]
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            priority_positions=original_positions
        )
        result = directives.to_dict()
        result["priority_positions"].append("RB")
        assert directives.priority_positions == ["QB", "WR"]  # Unchanged

    def test_from_dict_basic(self):
        """Verify from_dict creates valid OwnerDirectives."""
        data = {
            "dynasty_id": "test-dynasty",
            "team_id": 5,
            "season": 2026,
            "target_wins": 12,
            "draft_strategy": "bpa",
        }
        directives = OwnerDirectives.from_dict(data)
        assert directives.dynasty_id == "test-dynasty"
        assert directives.team_id == 5
        assert directives.target_wins == 12
        assert directives.draft_strategy == "bpa"

    def test_from_dict_with_defaults(self):
        """Verify from_dict applies defaults for missing optional fields."""
        data = {"dynasty_id": "test", "team_id": 1, "season": 2025}
        directives = OwnerDirectives.from_dict(data)
        assert directives.target_wins is None
        assert directives.priority_positions == []
        assert directives.draft_strategy == "balanced"
        assert directives.fa_philosophy == "balanced"
        assert directives.max_contract_years == 5

    def test_roundtrip_serialization(self):
        """Verify to_dict -> from_dict preserves all data."""
        original = OwnerDirectives(
            dynasty_id="test", team_id=15, season=2025,
            target_wins=9,
            priority_positions=["EDGE", "CB", "WR"],
            fa_wishlist=["Player A", "Player B"],
            draft_wishlist=["Prospect X"],
            draft_strategy="position_focus",
            fa_philosophy="conservative",
            max_contract_years=3,
            max_guaranteed_percent=0.5,
        )
        restored = OwnerDirectives.from_dict(original.to_dict())
        assert restored.dynasty_id == original.dynasty_id
        assert restored.team_id == original.team_id
        assert restored.target_wins == original.target_wins
        assert restored.priority_positions == original.priority_positions
        assert restored.draft_strategy == original.draft_strategy


class TestOwnerDirectivesValidation:
    """Tests for __post_init__ validation."""

    def test_validate_team_id_valid_range(self):
        """Verify team_id 1-32 passes validation."""
        for team_id in [1, 16, 32]:
            directives = OwnerDirectives(
                dynasty_id="test", team_id=team_id, season=2025
            )
            assert directives.team_id == team_id

    def test_validate_team_id_invalid_low(self):
        """Verify team_id 0 raises ValueError."""
        with pytest.raises(ValueError, match="team_id must be 1-32"):
            OwnerDirectives(dynasty_id="test", team_id=0, season=2025)

    def test_validate_team_id_invalid_high(self):
        """Verify team_id 33 raises ValueError."""
        with pytest.raises(ValueError, match="team_id must be 1-32"):
            OwnerDirectives(dynasty_id="test", team_id=33, season=2025)

    def test_validate_target_wins_valid(self):
        """Verify target_wins 0-17 passes validation."""
        for wins in [0, 8, 17]:
            directives = OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025, target_wins=wins
            )
            assert directives.target_wins == wins

    def test_validate_target_wins_none_allowed(self):
        """Verify target_wins None passes validation."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025, target_wins=None
        )
        assert directives.target_wins is None

    def test_validate_target_wins_invalid(self):
        """Verify target_wins 18 raises ValueError."""
        with pytest.raises(ValueError, match="target_wins must be 0-17"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025, target_wins=18
            )

    def test_validate_priority_positions_max(self):
        """Verify 6+ priority positions raises ValueError."""
        with pytest.raises(ValueError, match="priority_positions max 5"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                priority_positions=["QB", "RB", "WR", "TE", "OL", "DL"]
            )

    def test_validate_draft_strategy_invalid(self):
        """Verify invalid draft_strategy raises ValueError."""
        with pytest.raises(ValueError, match="draft_strategy must be one of"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                draft_strategy="invalid_strategy"
            )

    def test_validate_fa_philosophy_invalid(self):
        """Verify invalid fa_philosophy raises ValueError."""
        with pytest.raises(ValueError, match="fa_philosophy must be one of"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                fa_philosophy="invalid_philosophy"
            )

    def test_validate_max_contract_years_invalid(self):
        """Verify max_contract_years outside 1-5 raises ValueError."""
        with pytest.raises(ValueError, match="max_contract_years must be 1-5"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                max_contract_years=6
            )

    def test_validate_max_guaranteed_percent_invalid(self):
        """Verify max_guaranteed_percent outside 0-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_guaranteed_percent must be"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                max_guaranteed_percent=1.5
            )


class TestOwnerDirectivesConversion:
    """Tests for to_draft_direction and to_fa_guidance."""

    def test_to_draft_direction_bpa(self):
        """Verify 'bpa' maps to DraftStrategy.BEST_PLAYER_AVAILABLE."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            draft_strategy="bpa"
        )
        dd = directives.to_draft_direction()
        assert dd.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE

    def test_to_draft_direction_all_strategies(self):
        """Verify all draft_strategy strings map correctly."""
        mapping = {
            "bpa": DraftStrategy.BEST_PLAYER_AVAILABLE,
            "balanced": DraftStrategy.BALANCED,
            "needs_based": DraftStrategy.NEEDS_BASED,
            "position_focus": DraftStrategy.POSITION_FOCUS,
        }
        for strategy_str, expected_enum in mapping.items():
            directives = OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                draft_strategy=strategy_str
            )
            assert directives.to_draft_direction().strategy == expected_enum

    def test_to_draft_direction_copies_positions(self):
        """Verify priority_positions copied to DraftDirection."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            priority_positions=["QB", "EDGE", "CB"]
        )
        dd = directives.to_draft_direction()
        assert dd.priority_positions == ["QB", "EDGE", "CB"]

    def test_to_fa_guidance_all_philosophies(self):
        """Verify all fa_philosophy strings map correctly."""
        mapping = {
            "aggressive": FAPhilosophy.AGGRESSIVE,
            "balanced": FAPhilosophy.BALANCED,
            "conservative": FAPhilosophy.CONSERVATIVE,
        }
        for phil_str, expected_enum in mapping.items():
            directives = OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                fa_philosophy=phil_str
            )
            assert directives.to_fa_guidance().philosophy == expected_enum

    def test_to_fa_guidance_position_cap_at_3(self):
        """Verify FA guidance caps priority_positions at 3."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            priority_positions=["QB", "RB", "WR", "TE", "OL"]  # 5 positions
        )
        fg = directives.to_fa_guidance()
        assert len(fg.priority_positions) == 3
        assert fg.priority_positions == ["QB", "RB", "WR"]

    def test_to_fa_guidance_includes_contract_params(self):
        """Verify FA guidance includes contract constraints."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            max_contract_years=3,
            max_guaranteed_percent=0.6,
        )
        fg = directives.to_fa_guidance()
        assert fg.max_contract_years == 3
        assert fg.max_guaranteed_percent == 0.6


class TestOwnerDirectivesFactory:
    """Tests for factory methods and helpers."""

    def test_create_default(self):
        """Verify create_default returns balanced defaults."""
        directives = OwnerDirectives.create_default(
            dynasty_id="test", team_id=10, season=2025
        )
        assert directives.dynasty_id == "test"
        assert directives.team_id == 10
        assert directives.target_wins is None
        assert directives.draft_strategy == "balanced"
        assert directives.fa_philosophy == "balanced"

    def test_is_default_true(self):
        """Verify is_default returns True for unmodified directives."""
        directives = OwnerDirectives.create_default(
            dynasty_id="test", team_id=1, season=2025
        )
        assert directives.is_default() is True

    def test_is_default_false_with_changes(self):
        """Verify is_default returns False when modified."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            target_wins=10  # Non-default value
        )
        assert directives.is_default() is False


class TestOwnerDirectivesExtensionFields:
    """Tests for Tollgate 1 extension fields: team_philosophy, budget_stance, etc."""

    def test_new_field_defaults(self):
        """Verify new fields have correct default values."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025
        )
        assert directives.team_philosophy == "maintain"
        assert directives.budget_stance == "moderate"
        assert directives.protected_player_ids == []
        assert directives.expendable_player_ids == []
        assert directives.owner_notes == ""
        assert directives.trust_gm is False

    def test_validate_team_philosophy_valid(self):
        """Verify valid team_philosophy values pass validation."""
        for philosophy in ["win_now", "maintain", "rebuild"]:
            directives = OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                team_philosophy=philosophy
            )
            assert directives.team_philosophy == philosophy

    def test_validate_team_philosophy_invalid(self):
        """Verify invalid team_philosophy raises ValueError."""
        with pytest.raises(ValueError, match="team_philosophy must be one of"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                team_philosophy="invalid"
            )

    def test_validate_budget_stance_valid(self):
        """Verify valid budget_stance values pass validation."""
        for stance in ["aggressive", "moderate", "conservative"]:
            directives = OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                budget_stance=stance
            )
            assert directives.budget_stance == stance

    def test_validate_budget_stance_invalid(self):
        """Verify invalid budget_stance raises ValueError."""
        with pytest.raises(ValueError, match="budget_stance must be one of"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                budget_stance="invalid"
            )

    def test_validate_protected_players_max(self):
        """Verify more than 5 protected players raises ValueError."""
        with pytest.raises(ValueError, match="protected_player_ids max 5"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                protected_player_ids=[1, 2, 3, 4, 5, 6]
            )

    def test_validate_expendable_players_max(self):
        """Verify more than 10 expendable players raises ValueError."""
        with pytest.raises(ValueError, match="expendable_player_ids max 10"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                expendable_player_ids=list(range(11))
            )

    def test_validate_no_overlap_protected_expendable(self):
        """Verify same player in both lists raises ValueError."""
        with pytest.raises(ValueError, match="protected and expendable"):
            OwnerDirectives(
                dynasty_id="test", team_id=1, season=2025,
                protected_player_ids=[1, 2],
                expendable_player_ids=[2, 3, 4]
            )

    def test_to_dict_includes_new_fields(self):
        """Verify to_dict includes all new fields."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            team_philosophy="win_now",
            budget_stance="aggressive",
            protected_player_ids=[100, 200],
            expendable_player_ids=[300, 400, 500],
            owner_notes="Trade for picks",
            trust_gm=True
        )
        result = directives.to_dict()
        assert result["team_philosophy"] == "win_now"
        assert result["budget_stance"] == "aggressive"
        assert result["protected_player_ids"] == [100, 200]
        assert result["expendable_player_ids"] == [300, 400, 500]
        assert result["owner_notes"] == "Trade for picks"
        assert result["trust_gm"] is True

    def test_from_dict_parses_new_fields(self):
        """Verify from_dict correctly parses new fields."""
        data = {
            "dynasty_id": "test",
            "team_id": 1,
            "season": 2025,
            "team_philosophy": "rebuild",
            "budget_stance": "conservative",
            "protected_player_ids": [10],
            "expendable_player_ids": [20, 30],
            "owner_notes": "Notes here",
            "trust_gm": True
        }
        directives = OwnerDirectives.from_dict(data)
        assert directives.team_philosophy == "rebuild"
        assert directives.budget_stance == "conservative"
        assert directives.protected_player_ids == [10]
        assert directives.expendable_player_ids == [20, 30]
        assert directives.owner_notes == "Notes here"
        assert directives.trust_gm is True

    def test_from_dict_new_field_defaults(self):
        """Verify from_dict applies defaults for missing new fields."""
        data = {"dynasty_id": "test", "team_id": 1, "season": 2025}
        directives = OwnerDirectives.from_dict(data)
        assert directives.team_philosophy == "maintain"
        assert directives.budget_stance == "moderate"
        assert directives.protected_player_ids == []
        assert directives.expendable_player_ids == []
        assert directives.owner_notes == ""
        assert directives.trust_gm is False

    def test_create_default_includes_new_fields(self):
        """Verify create_default sets correct defaults for new fields."""
        directives = OwnerDirectives.create_default(
            dynasty_id="test", team_id=1, season=2025
        )
        assert directives.team_philosophy == "maintain"
        assert directives.budget_stance == "moderate"
        assert directives.protected_player_ids == []
        assert directives.expendable_player_ids == []
        assert directives.owner_notes == ""
        assert directives.trust_gm is False

    def test_is_default_true_with_new_fields(self):
        """Verify is_default returns True when new fields are default."""
        directives = OwnerDirectives.create_default(
            dynasty_id="test", team_id=1, season=2025
        )
        assert directives.is_default() is True

    def test_is_default_false_with_team_philosophy(self):
        """Verify is_default returns False when team_philosophy changed."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            team_philosophy="win_now"
        )
        assert directives.is_default() is False

    def test_is_default_false_with_protected_players(self):
        """Verify is_default returns False when protected_player_ids set."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            protected_player_ids=[100]
        )
        assert directives.is_default() is False

    def test_is_default_false_with_trust_gm(self):
        """Verify is_default returns False when trust_gm is True."""
        directives = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            trust_gm=True
        )
        assert directives.is_default() is False

    def test_roundtrip_with_new_fields(self):
        """Verify to_dict -> from_dict preserves all new fields."""
        original = OwnerDirectives(
            dynasty_id="test", team_id=1, season=2025,
            team_philosophy="rebuild",
            budget_stance="aggressive",
            protected_player_ids=[1, 2, 3],
            expendable_player_ids=[10, 20],
            owner_notes="Focus on youth",
            trust_gm=True
        )
        restored = OwnerDirectives.from_dict(original.to_dict())
        assert restored.team_philosophy == original.team_philosophy
        assert restored.budget_stance == original.budget_stance
        assert restored.protected_player_ids == original.protected_player_ids
        assert restored.expendable_player_ids == original.expendable_player_ids
        assert restored.owner_notes == original.owner_notes
        assert restored.trust_gm == original.trust_gm
