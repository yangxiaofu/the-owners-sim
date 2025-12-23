"""
Unit tests for OwnerInfluenceCalculator.

Tests auto-approval, contract constraints, position priorities, and FA filtering.
"""

import pytest

from game_cycle.services.owner_influence_calculator import OwnerInfluenceCalculator
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.stage_definitions import StageType


@pytest.fixture
def calculator():
    """Create calculator instance."""
    return OwnerInfluenceCalculator()


@pytest.fixture
def trust_gm_enabled():
    """Directives with trust_gm=True."""
    return OwnerDirectives(
        dynasty_id="test",
        team_id=1,
        season=2025,
        trust_gm=True,
    )


@pytest.fixture
def trust_gm_disabled():
    """Directives with trust_gm=False."""
    return OwnerDirectives(
        dynasty_id="test",
        team_id=1,
        season=2025,
        trust_gm=False,
    )


@pytest.fixture
def aggressive_fa_directives():
    """Directives with aggressive FA philosophy."""
    return OwnerDirectives(
        dynasty_id="test",
        team_id=1,
        season=2025,
        fa_philosophy="aggressive",
        priority_positions=["QB", "EDGE", "WR"],
    )


@pytest.fixture
def conservative_fa_directives():
    """Directives with conservative FA philosophy."""
    return OwnerDirectives(
        dynasty_id="test",
        team_id=1,
        season=2025,
        fa_philosophy="conservative",
        priority_positions=["QB", "EDGE", "WR"],
    )


@pytest.fixture
def contract_constrained_directives():
    """Directives with contract constraints."""
    return OwnerDirectives(
        dynasty_id="test",
        team_id=1,
        season=2025,
        max_contract_years=3,
        max_guaranteed_percent=0.5,
    )


class TestAutoApproval:
    """Tests for should_auto_approve method."""

    def test_should_auto_approve_with_trust_gm_enabled(self, calculator, trust_gm_enabled):
        """Test auto-approval when trust_gm=True."""
        result = calculator.should_auto_approve(
            directives=trust_gm_enabled,
            stage_type=StageType.OFFSEASON_DRAFT
        )
        assert result is True

    def test_should_auto_approve_with_trust_gm_disabled(self, calculator, trust_gm_disabled):
        """Test no auto-approval when trust_gm=False."""
        result = calculator.should_auto_approve(
            directives=trust_gm_disabled,
            stage_type=StageType.OFFSEASON_DRAFT
        )
        assert result is False

    def test_should_auto_approve_applies_to_all_stages(self, calculator, trust_gm_enabled):
        """Test auto-approval works for all offseason stages."""
        stages = [
            StageType.OFFSEASON_FRANCHISE_TAG,
            StageType.OFFSEASON_RESIGNING,
            StageType.OFFSEASON_FREE_AGENCY,
            StageType.OFFSEASON_TRADING,
            StageType.OFFSEASON_DRAFT,
            StageType.OFFSEASON_ROSTER_CUTS,
            StageType.OFFSEASON_WAIVER_WIRE,
        ]

        for stage in stages:
            result = calculator.should_auto_approve(trust_gm_enabled, stage)
            assert result is True, f"Auto-approve failed for {stage}"


class TestContractConstraints:
    """Tests for apply_contract_constraints method."""

    def test_apply_contract_constraints_max_years(self, calculator, contract_constrained_directives):
        """Test max_contract_years constraint application."""
        proposal_details = {
            "contract_years": 5,
            "total_value": 50_000_000,
            "guaranteed_money": 30_000_000,
        }

        result = calculator.apply_contract_constraints(
            proposal_details=proposal_details,
            directives=contract_constrained_directives
        )

        # Verify: Years capped at 3
        assert result["contract_years"] == 3
        assert result["total_value"] == 50_000_000  # Unchanged

    def test_apply_contract_constraints_max_guaranteed(self, calculator, contract_constrained_directives):
        """Test max_guaranteed_percent constraint application."""
        proposal_details = {
            "contract_years": 5,
            "total_value": 50_000_000,
            "guaranteed_money": 40_000_000,  # 80% guaranteed
        }

        result = calculator.apply_contract_constraints(
            proposal_details=proposal_details,
            directives=contract_constrained_directives
        )

        # Verify: Guaranteed capped at 50% of 50M = 25M
        assert result["guaranteed_money"] == 25_000_000
        assert result["total_value"] == 50_000_000  # Unchanged

    def test_apply_contract_constraints_both(self, calculator, contract_constrained_directives):
        """Test both constraints applied together."""
        proposal_details = {
            "contract_years": 5,
            "total_value": 60_000_000,
            "guaranteed_money": 50_000_000,  # 83% guaranteed
        }

        result = calculator.apply_contract_constraints(
            proposal_details=proposal_details,
            directives=contract_constrained_directives
        )

        # Verify: Both constraints applied
        assert result["contract_years"] == 3
        assert result["guaranteed_money"] == 30_000_000  # 50% of 60M

    def test_apply_contract_constraints_no_change_needed(self, calculator):
        """Test constraints don't modify proposal when already compliant."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            max_contract_years=5,
            max_guaranteed_percent=0.75,
        )

        proposal_details = {
            "contract_years": 3,
            "total_value": 30_000_000,
            "guaranteed_money": 20_000_000,  # 67% guaranteed
        }

        result = calculator.apply_contract_constraints(
            proposal_details=proposal_details,
            directives=directives
        )

        # Verify: No changes
        assert result["contract_years"] == 3
        assert result["guaranteed_money"] == 20_000_000

    def test_apply_contract_constraints_with_none_values(self, calculator):
        """Test constraints with None values (no constraints)."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            max_contract_years=5,
            max_guaranteed_percent=0.75,
        )

        proposal_details = {
            "contract_years": 5,
            "total_value": 50_000_000,
            "guaranteed_money": 45_000_000,
        }

        result = calculator.apply_contract_constraints(
            proposal_details=proposal_details,
            directives=directives
        )

        # Verify: Default constraints applied (5 years, 75% guaranteed max)
        assert result["contract_years"] == 5
        assert result["guaranteed_money"] == 37_500_000  # 75% of 50M

    def test_apply_contract_constraints_preserves_original(self, calculator, contract_constrained_directives):
        """Test that original proposal_details dict is not modified."""
        original = {
            "contract_years": 5,
            "total_value": 50_000_000,
            "guaranteed_money": 40_000_000,
        }

        # Make copy to verify it's not mutated
        import copy
        original_copy = copy.deepcopy(original)

        result = calculator.apply_contract_constraints(
            proposal_details=original,
            directives=contract_constrained_directives
        )

        # Verify: Original unchanged, result modified
        assert original == original_copy
        assert result["contract_years"] != original["contract_years"]


class TestPositionPriority:
    """Tests for calculate_position_priority_bonus method."""

    def test_calculate_position_priority_bonus_first_priority(self, calculator):
        """Test 1st priority position gets 0.85 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR"],
        )

        bonus = calculator.calculate_position_priority_bonus("QB", directives)
        assert bonus == 0.85

    def test_calculate_position_priority_bonus_second_priority(self, calculator):
        """Test 2nd priority position gets 0.70 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR"],
        )

        bonus = calculator.calculate_position_priority_bonus("EDGE", directives)
        assert bonus == 0.70

    def test_calculate_position_priority_bonus_third_priority(self, calculator):
        """Test 3rd priority position gets 0.55 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR"],
        )

        bonus = calculator.calculate_position_priority_bonus("WR", directives)
        assert bonus == 0.55

    def test_calculate_position_priority_bonus_fourth_priority(self, calculator):
        """Test 4th priority position gets 0.40 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR", "CB"],
        )

        bonus = calculator.calculate_position_priority_bonus("CB", directives)
        assert bonus == 0.40

    def test_calculate_position_priority_bonus_fifth_priority(self, calculator):
        """Test 5th priority position gets 0.25 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR", "CB", "OT"],
        )

        bonus = calculator.calculate_position_priority_bonus("OT", directives)
        assert bonus == 0.25

    def test_calculate_position_priority_bonus_non_priority(self, calculator):
        """Test non-priority position gets 0.0 bonus."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=["QB", "EDGE", "WR"],
        )

        bonus = calculator.calculate_position_priority_bonus("RB", directives)
        assert bonus == 0.0

    def test_calculate_position_priority_bonus_empty_list(self, calculator):
        """Test empty priority list returns 0.0."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            priority_positions=[],
        )

        bonus = calculator.calculate_position_priority_bonus("QB", directives)
        assert bonus == 0.0


class TestFAOfferMultiplier:
    """Tests for calculate_fa_offer_multiplier method."""

    def test_calculate_fa_offer_multiplier_aggressive(self, calculator, aggressive_fa_directives):
        """Test aggressive philosophy returns 1.15x multiplier."""
        multiplier = calculator.calculate_fa_offer_multiplier(
            base_value=10_000_000,
            directives=aggressive_fa_directives
        )
        assert multiplier == 1.15

    def test_calculate_fa_offer_multiplier_balanced(self, calculator):
        """Test balanced philosophy returns 1.0x multiplier."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            fa_philosophy="balanced",
        )

        multiplier = calculator.calculate_fa_offer_multiplier(
            base_value=10_000_000,
            directives=directives
        )
        assert multiplier == 1.0

    def test_calculate_fa_offer_multiplier_conservative(self, calculator, conservative_fa_directives):
        """Test conservative philosophy returns 0.90x multiplier."""
        multiplier = calculator.calculate_fa_offer_multiplier(
            base_value=10_000_000,
            directives=conservative_fa_directives
        )
        assert multiplier == 0.90


class TestFAPlayerFiltering:
    """Tests for should_pursue_fa_player method."""

    def test_should_pursue_fa_player_aggressive(self, calculator, aggressive_fa_directives):
        """Test aggressive philosophy pursues 70+ OVR threshold."""
        # Should pursue 70+ OVR
        assert calculator.should_pursue_fa_player(70, aggressive_fa_directives) is True
        assert calculator.should_pursue_fa_player(85, aggressive_fa_directives) is True

        # Should not pursue below 70 OVR
        assert calculator.should_pursue_fa_player(69, aggressive_fa_directives) is False
        assert calculator.should_pursue_fa_player(60, aggressive_fa_directives) is False

    def test_should_pursue_fa_player_balanced(self, calculator):
        """Test balanced philosophy pursues 75+ OVR threshold."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            fa_philosophy="balanced",
        )

        # Should pursue 75+ OVR
        assert calculator.should_pursue_fa_player(75, directives) is True
        assert calculator.should_pursue_fa_player(85, directives) is True

        # Should not pursue below 75 OVR
        assert calculator.should_pursue_fa_player(74, directives) is False
        assert calculator.should_pursue_fa_player(70, directives) is False

    def test_should_pursue_fa_player_conservative(self, calculator, conservative_fa_directives):
        """Test conservative philosophy pursues 80+ OVR threshold."""
        # Should pursue 80+ OVR (elite only)
        assert calculator.should_pursue_fa_player(80, conservative_fa_directives) is True
        assert calculator.should_pursue_fa_player(90, conservative_fa_directives) is True

        # Should not pursue below 80 OVR
        assert calculator.should_pursue_fa_player(79, conservative_fa_directives) is False
        assert calculator.should_pursue_fa_player(75, conservative_fa_directives) is False


class TestPlayerLists:
    """Tests for protected/expendable player list methods."""

    def test_is_player_protected(self, calculator):
        """Test protected player identification."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            protected_player_ids=[100, 101, 102],
        )

        assert calculator.is_player_protected(100, directives) is True
        assert calculator.is_player_protected(101, directives) is True
        assert calculator.is_player_protected(200, directives) is False

    def test_is_player_expendable(self, calculator):
        """Test expendable player identification."""
        directives = OwnerDirectives(
            dynasty_id="test",
            team_id=1,
            season=2025,
            expendable_player_ids=[200, 201, 202],
        )

        assert calculator.is_player_expendable(200, directives) is True
        assert calculator.is_player_expendable(201, directives) is True
        assert calculator.is_player_expendable(100, directives) is False


class TestTrustGMAffectedStages:
    """Tests for get_trust_gm_affected_stages method."""

    def test_get_trust_gm_affected_stages(self, calculator):
        """Test that all expected offseason stages are returned."""
        stages = calculator.get_trust_gm_affected_stages()

        # Verify expected stages
        expected_stages = [
            StageType.OFFSEASON_FRANCHISE_TAG,
            StageType.OFFSEASON_RESIGNING,
            StageType.OFFSEASON_FREE_AGENCY,
            StageType.OFFSEASON_TRADING,
            StageType.OFFSEASON_DRAFT,
            StageType.OFFSEASON_ROSTER_CUTS,
            StageType.OFFSEASON_WAIVER_WIRE,
        ]

        for stage in expected_stages:
            assert stage in stages
            assert isinstance(stages[stage], str)
            assert len(stages[stage]) > 0  # Has explanation

    def test_get_trust_gm_affected_stages_has_explanations(self, calculator):
        """Test that all stages have meaningful explanations."""
        stages = calculator.get_trust_gm_affected_stages()

        # All should mention "auto-approve" or similar
        for stage, explanation in stages.items():
            assert "auto-approve" in explanation.lower() or "approve" in explanation.lower()
