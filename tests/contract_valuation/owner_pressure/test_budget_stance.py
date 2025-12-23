"""
Unit tests for BudgetStanceModifier.

Tests budget multiplier and constraint validation.
"""

import pytest

from contract_valuation.owner_pressure.budget_stance import BudgetStanceModifier
from contract_valuation.context import JobSecurityContext, OwnerContext


class TestBudgetStanceModifier:
    """Tests for BudgetStanceModifier."""

    @pytest.fixture
    def modifier(self):
        """BudgetStanceModifier instance."""
        return BudgetStanceModifier()

    def test_modifier_name(self, modifier):
        """Test modifier returns correct name."""
        assert modifier.modifier_name == "budget_stance"

    def test_aggressive_multiplier(self, modifier, aggressive_context, base_aav):
        """Test aggressive owner applies 1.15x multiplier (+15%)."""
        adjusted_aav, description = modifier.apply(base_aav, aggressive_context)

        expected_aav = int(base_aav * 1.15)
        assert adjusted_aav == expected_aav
        assert "Aggressive" in description

    def test_balanced_multiplier(self, modifier, secure_context, base_aav):
        """Test balanced owner applies 1.00x multiplier (0%)."""
        # secure_context has balanced philosophy
        adjusted_aav, description = modifier.apply(base_aav, secure_context)

        assert adjusted_aav == base_aav
        assert "Balanced" in description

    def test_conservative_multiplier(self, modifier, conservative_context, base_aav):
        """Test conservative owner applies 0.90x multiplier (-10%)."""
        adjusted_aav, description = modifier.apply(base_aav, conservative_context)

        expected_aav = int(base_aav * 0.90)
        assert adjusted_aav == expected_aav
        assert "Conservative" in description

    def test_max_years_constraint(self, modifier, conservative_context):
        """Test get_max_years returns correct constraint."""
        max_years = modifier.get_max_years(conservative_context)
        assert max_years == 4  # conservative_context has max_contract_years=4

    def test_max_guaranteed_constraint(self, modifier, conservative_context):
        """Test get_max_guaranteed_pct returns correct constraint."""
        max_pct = modifier.get_max_guaranteed_pct(conservative_context)
        assert max_pct == 0.50  # conservative_context has max_guaranteed_pct=0.50

    def test_validate_constraint_violations(self, modifier, conservative_context):
        """Test validate_constraints detects exceeded limits."""
        # Conservative context: max_years=4, max_guaranteed=0.50
        result = modifier.validate_constraints(
            proposed_years=6,
            proposed_guaranteed_pct=0.70,
            context=conservative_context,
        )

        assert result["years_valid"] is False
        assert result["guaranteed_valid"] is False
        assert "years_exceeded" in result["violations"]
        assert "guaranteed_exceeded" in result["violations"]
        assert result["is_valid"] is False

    def test_validate_constraints_valid(self, modifier, aggressive_context):
        """Test validate_constraints passes valid contract."""
        # Aggressive context: max_years=6, max_guaranteed=0.70
        result = modifier.validate_constraints(
            proposed_years=5,
            proposed_guaranteed_pct=0.60,
            context=aggressive_context,
        )

        assert result["years_valid"] is True
        assert result["guaranteed_valid"] is True
        assert len(result["violations"]) == 0
        assert result["is_valid"] is True


class TestBudgetStancePressure:
    """Tests for pressure level calculation."""

    @pytest.fixture
    def modifier(self):
        return BudgetStanceModifier()

    def test_aggressive_pressure_level(self, modifier, aggressive_context):
        """Test aggressive has high pressure (0.8)."""
        pressure = modifier.calculate_pressure_level(aggressive_context)
        assert pressure == 0.8

    def test_balanced_pressure_level(self, modifier, secure_context):
        """Test balanced has moderate pressure (0.5)."""
        pressure = modifier.calculate_pressure_level(secure_context)
        assert pressure == 0.5

    def test_conservative_pressure_level(self, modifier, conservative_context):
        """Test conservative has low pressure (0.2)."""
        pressure = modifier.calculate_pressure_level(conservative_context)
        assert pressure == 0.2


class TestBudgetStanceBreakdown:
    """Tests for get_breakdown method."""

    @pytest.fixture
    def modifier(self):
        return BudgetStanceModifier()

    def test_breakdown_structure(self, modifier, aggressive_context, base_aav):
        """Test breakdown contains all expected fields."""
        breakdown = modifier.get_breakdown(aggressive_context, base_aav)

        expected_keys = [
            "modifier_name",
            "pressure_level",
            "owner_philosophy",
            "budget_multiplier",
            "base_aav",
            "adjustment_pct",
            "adjustment_dollars",
            "adjusted_aav",
            "max_contract_years",
            "max_guaranteed_pct",
            "rationale",
        ]

        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"

    def test_breakdown_rationale_aggressive(self, modifier, aggressive_context, base_aav):
        """Test rationale for aggressive owner."""
        breakdown = modifier.get_breakdown(aggressive_context, base_aav)
        assert "overpay" in breakdown["rationale"].lower()

    def test_breakdown_rationale_conservative(self, modifier, conservative_context, base_aav):
        """Test rationale for conservative owner."""
        breakdown = modifier.get_breakdown(conservative_context, base_aav)
        assert "value" in breakdown["rationale"].lower()