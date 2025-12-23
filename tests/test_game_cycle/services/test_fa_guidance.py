"""
Unit tests for FAGuidance model methods.

Tests philosophy multipliers and player filtering thresholds.
"""

import pytest

from game_cycle.models.fa_guidance import FAGuidance, FAPhilosophy


class TestGetMaxOfferMultiplier:
    """Tests for get_max_offer_multiplier method."""

    def test_get_max_offer_multiplier_aggressive(self):
        """Test 1.15x multiplier for aggressive philosophy."""
        guidance = FAGuidance(philosophy=FAPhilosophy.AGGRESSIVE)
        multiplier = guidance.get_max_offer_multiplier()
        assert multiplier == 1.15

    def test_get_max_offer_multiplier_balanced(self):
        """Test 1.0x multiplier for balanced philosophy."""
        guidance = FAGuidance(philosophy=FAPhilosophy.BALANCED)
        multiplier = guidance.get_max_offer_multiplier()
        assert multiplier == 1.0

    def test_get_max_offer_multiplier_conservative(self):
        """Test 0.90x multiplier for conservative philosophy."""
        guidance = FAGuidance(philosophy=FAPhilosophy.CONSERVATIVE)
        multiplier = guidance.get_max_offer_multiplier()
        assert multiplier == 0.90


class TestShouldPursuePlayer:
    """Tests for should_pursue_player method."""

    def test_should_pursue_player_aggressive(self):
        """Test 70+ OVR threshold for aggressive."""
        guidance = FAGuidance(philosophy=FAPhilosophy.AGGRESSIVE)

        # Should pursue 70+ OVR
        assert guidance.should_pursue_player(70) is True
        assert guidance.should_pursue_player(75) is True
        assert guidance.should_pursue_player(85) is True
        assert guidance.should_pursue_player(95) is True

        # Should not pursue below 70 OVR
        assert guidance.should_pursue_player(69) is False
        assert guidance.should_pursue_player(65) is False
        assert guidance.should_pursue_player(50) is False

    def test_should_pursue_player_balanced(self):
        """Test 75+ OVR threshold for balanced."""
        guidance = FAGuidance(philosophy=FAPhilosophy.BALANCED)

        # Should pursue 75+ OVR
        assert guidance.should_pursue_player(75) is True
        assert guidance.should_pursue_player(80) is True
        assert guidance.should_pursue_player(90) is True

        # Should not pursue below 75 OVR
        assert guidance.should_pursue_player(74) is False
        assert guidance.should_pursue_player(70) is False
        assert guidance.should_pursue_player(60) is False

    def test_should_pursue_player_conservative(self):
        """Test 80+ OVR threshold for conservative."""
        guidance = FAGuidance(philosophy=FAPhilosophy.CONSERVATIVE)

        # Should pursue 80+ OVR (elite only)
        assert guidance.should_pursue_player(80) is True
        assert guidance.should_pursue_player(85) is True
        assert guidance.should_pursue_player(95) is True

        # Should not pursue below 80 OVR
        assert guidance.should_pursue_player(79) is False
        assert guidance.should_pursue_player(75) is False
        assert guidance.should_pursue_player(70) is False

    def test_should_pursue_player_edge_cases(self):
        """Test edge cases at exact threshold values."""
        aggressive = FAGuidance(philosophy=FAPhilosophy.AGGRESSIVE)
        balanced = FAGuidance(philosophy=FAPhilosophy.BALANCED)
        conservative = FAGuidance(philosophy=FAPhilosophy.CONSERVATIVE)

        # Exactly at threshold should pass
        assert aggressive.should_pursue_player(70) is True
        assert balanced.should_pursue_player(75) is True
        assert conservative.should_pursue_player(80) is True

        # One below threshold should fail
        assert aggressive.should_pursue_player(69) is False
        assert balanced.should_pursue_player(74) is False
        assert conservative.should_pursue_player(79) is False


class TestFAGuidanceValidation:
    """Tests for FAGuidance validation."""

    def test_valid_guidance_creation(self):
        """Test creating guidance with valid values."""
        guidance = FAGuidance(
            philosophy=FAPhilosophy.BALANCED,
            priority_positions=["QB", "EDGE", "WR"],
            wishlist_names=["John Smith"],
            max_contract_years=4,
            max_guaranteed_percent=0.65,
        )

        assert guidance.philosophy == FAPhilosophy.BALANCED
        assert guidance.priority_positions == ["QB", "EDGE", "WR"]
        assert guidance.max_contract_years == 4
        assert guidance.max_guaranteed_percent == 0.65

    def test_invalid_philosophy_raises_error(self):
        """Test that invalid philosophy raises ValueError."""
        with pytest.raises(ValueError, match="philosophy must be FAPhilosophy enum"):
            FAGuidance(philosophy="invalid")

    def test_invalid_max_contract_years_raises_error(self):
        """Test that invalid max_contract_years raises ValueError."""
        with pytest.raises(ValueError, match="max_contract_years must be 1-5"):
            FAGuidance(max_contract_years=0)

        with pytest.raises(ValueError, match="max_contract_years must be 1-5"):
            FAGuidance(max_contract_years=6)

    def test_invalid_max_guaranteed_percent_raises_error(self):
        """Test that invalid max_guaranteed_percent raises ValueError."""
        with pytest.raises(ValueError, match="max_guaranteed_percent must be 0.0-1.0"):
            FAGuidance(max_guaranteed_percent=-0.1)

        with pytest.raises(ValueError, match="max_guaranteed_percent must be 0.0-1.0"):
            FAGuidance(max_guaranteed_percent=1.1)

    def test_too_many_priority_positions_raises_error(self):
        """Test that more than 3 priority positions raises ValueError."""
        with pytest.raises(ValueError, match="priority_positions must have max 3 items"):
            FAGuidance(priority_positions=["QB", "EDGE", "WR", "CB"])

    def test_negative_budget_raises_error(self):
        """Test that negative budget values raise ValueError."""
        with pytest.raises(ValueError, match="Budget for .* must be non-negative"):
            FAGuidance(budget_by_position_group={"QB": -1000000})


class TestFAGuidanceConvenience:
    """Tests for FAGuidance convenience methods."""

    def test_create_default(self):
        """Test creating default guidance."""
        guidance = FAGuidance.create_default()

        assert guidance.philosophy == FAPhilosophy.BALANCED
        assert len(guidance.budget_by_position_group) == 0
        assert len(guidance.priority_positions) == 0
        assert len(guidance.wishlist_names) == 0
        assert guidance.max_contract_years == 5
        assert guidance.max_guaranteed_percent == 0.75

    def test_is_default_true(self):
        """Test is_default returns True for default guidance."""
        guidance = FAGuidance.create_default()
        assert guidance.is_default() is True

    def test_is_default_false_when_modified(self):
        """Test is_default returns False when guidance is modified."""
        # Modify philosophy
        guidance = FAGuidance(philosophy=FAPhilosophy.AGGRESSIVE)
        assert guidance.is_default() is False

        # Modify priority positions
        guidance = FAGuidance(priority_positions=["QB"])
        assert guidance.is_default() is False

        # Modify contract years
        guidance = FAGuidance(max_contract_years=3)
        assert guidance.is_default() is False

        # Modify guaranteed percent
        guidance = FAGuidance(max_guaranteed_percent=0.5)
        assert guidance.is_default() is False

    def test_to_dict(self):
        """Test converting guidance to dictionary."""
        guidance = FAGuidance(
            philosophy=FAPhilosophy.AGGRESSIVE,
            priority_positions=["QB", "EDGE"],
            wishlist_names=["John Smith"],
            max_contract_years=4,
            max_guaranteed_percent=0.65,
            budget_by_position_group={"QB": 40_000_000},
        )

        result = guidance.to_dict()

        assert result["philosophy"] == "aggressive"
        assert result["priority_positions"] == ["QB", "EDGE"]
        assert result["wishlist_names"] == ["John Smith"]
        assert result["max_contract_years"] == 4
        assert result["max_guaranteed_percent"] == 0.65
        assert result["budget_by_position_group"] == {"QB": 40_000_000}


class TestFAGuidanceBudgets:
    """Tests for budget allocations."""

    def test_empty_budget_allows_full_discretion(self):
        """Test that empty budget dict means no constraints."""
        guidance = FAGuidance(budget_by_position_group={})
        assert len(guidance.budget_by_position_group) == 0

    def test_budget_by_position_group(self):
        """Test setting budgets by position group."""
        budgets = {
            "QB": 40_000_000,
            "OL": 30_000_000,
            "DL": 25_000_000,
            "Secondary": 20_000_000,
            "Skill": 15_000_000,
            "Special Teams": 5_000_000,
        }

        guidance = FAGuidance(budget_by_position_group=budgets)

        assert guidance.budget_by_position_group == budgets
        assert guidance.budget_by_position_group["QB"] == 40_000_000
        assert guidance.budget_by_position_group["OL"] == 30_000_000


class TestFAGuidanceWishlistAndPriorities:
    """Tests for wishlist and priority positions."""

    def test_priority_positions_up_to_3(self):
        """Test that up to 3 priority positions are allowed."""
        guidance = FAGuidance(priority_positions=["QB", "EDGE", "WR"])
        assert len(guidance.priority_positions) == 3
        assert guidance.priority_positions == ["QB", "EDGE", "WR"]

    def test_wishlist_names(self):
        """Test storing wishlist player names."""
        guidance = FAGuidance(wishlist_names=["John Smith", "Mike Jones", "Tom Wilson"])
        assert len(guidance.wishlist_names) == 3
        assert "John Smith" in guidance.wishlist_names

    def test_empty_wishlist_and_priorities(self):
        """Test that empty lists are allowed."""
        guidance = FAGuidance(priority_positions=[], wishlist_names=[])
        assert len(guidance.priority_positions) == 0
        assert len(guidance.wishlist_names) == 0
