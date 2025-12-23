"""
Unit tests for modifier chain application.

Tests sequential application of multiple pressure modifiers.
"""

import pytest

from contract_valuation.owner_pressure.chain import (
    apply_modifier_chain,
    create_default_modifier_chain,
)
from contract_valuation.owner_pressure.job_security import JobSecurityModifier
from contract_valuation.owner_pressure.win_now import WinNowModifier
from contract_valuation.owner_pressure.budget_stance import BudgetStanceModifier
from contract_valuation.context import JobSecurityContext, OwnerContext


class TestModifierChain:
    """Tests for apply_modifier_chain function."""

    @pytest.fixture
    def single_modifier(self):
        """Single modifier for testing."""
        return [JobSecurityModifier()]

    @pytest.fixture
    def two_modifiers(self):
        """Two modifiers for testing."""
        return [JobSecurityModifier(), BudgetStanceModifier()]

    @pytest.fixture
    def all_modifiers(self):
        """All three modifiers in order."""
        return [JobSecurityModifier(), WinNowModifier(), BudgetStanceModifier()]

    def test_single_modifier_chain(self, single_modifier, hot_seat_context, base_aav):
        """Test chain works with single modifier."""
        final_aav, total_pct, results = apply_modifier_chain(
            base_aav, hot_seat_context, single_modifier
        )

        assert len(results) == 1
        assert results[0]["modifier_name"] == "job_security"
        assert final_aav > base_aav  # Hot seat pays premium
        assert total_pct > 0

    def test_multiple_modifiers_stack(self, two_modifiers, hot_seat_context, base_aav):
        """Test two modifiers combine correctly."""
        final_aav, total_pct, results = apply_modifier_chain(
            base_aav, hot_seat_context, two_modifiers
        )

        assert len(results) == 2
        assert results[0]["modifier_name"] == "job_security"
        assert results[1]["modifier_name"] == "budget_stance"

        # Second modifier input should be first modifier output
        assert results[1]["input_aav"] == results[0]["output_aav"]

        # Final AAV should match last modifier output
        assert final_aav == results[1]["output_aav"]

    def test_full_chain_all_modifiers(self, all_modifiers, hot_seat_context, base_aav):
        """Test all 3 modifiers applied in order."""
        player_data = {"age": 32}  # Veteran for win-now premium

        final_aav, total_pct, results = apply_modifier_chain(
            base_aav, hot_seat_context, all_modifiers, player_data=player_data
        )

        assert len(results) == 3
        assert results[0]["modifier_name"] == "job_security"
        assert results[1]["modifier_name"] == "win_now"
        assert results[2]["modifier_name"] == "budget_stance"

        # Hot seat + win-now veteran + aggressive = significant increase
        assert final_aav > base_aav
        assert total_pct > 0.20  # Should be significant with all bonuses

    def test_chain_breakdown_structure(self, all_modifiers, secure_context, base_aav):
        """Test result structure is correct."""
        player_data = {"age": 28}

        final_aav, total_pct, results = apply_modifier_chain(
            base_aav, secure_context, all_modifiers, player_data=player_data
        )

        # Check result structure
        assert isinstance(final_aav, int)
        assert isinstance(total_pct, float)
        assert isinstance(results, list)

        # Check each result has required fields
        for result in results:
            assert "modifier_name" in result
            assert "input_aav" in result
            assert "output_aav" in result
            assert "adjustment_pct" in result
            assert "adjustment_dollars" in result
            assert "pressure_level" in result
            assert "description" in result


class TestDefaultModifierChain:
    """Tests for create_default_modifier_chain function."""

    def test_creates_three_modifiers(self):
        """Test default chain has 3 modifiers."""
        chain = create_default_modifier_chain()
        assert len(chain) == 3

    def test_correct_modifier_order(self):
        """Test modifiers are in correct order."""
        chain = create_default_modifier_chain()

        assert isinstance(chain[0], JobSecurityModifier)
        assert isinstance(chain[1], WinNowModifier)
        assert isinstance(chain[2], BudgetStanceModifier)


class TestChainEdgeCases:
    """Tests for edge cases in chain application."""

    def test_empty_chain(self, secure_context, base_aav):
        """Test empty modifier chain returns original values."""
        final_aav, total_pct, results = apply_modifier_chain(
            base_aav, secure_context, []
        )

        assert final_aav == base_aav
        assert total_pct == 0.0
        assert len(results) == 0

    def test_zero_base_aav(self, secure_context):
        """Test chain handles zero base AAV."""
        modifiers = create_default_modifier_chain()
        final_aav, total_pct, results = apply_modifier_chain(
            0, secure_context, modifiers
        )

        assert final_aav == 0
        assert total_pct == 0.0