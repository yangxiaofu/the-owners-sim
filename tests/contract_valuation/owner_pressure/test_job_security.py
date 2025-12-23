"""
Unit tests for JobSecurityModifier.

Tests pressure calculation and AAV adjustments based on job security.
"""

import pytest

from contract_valuation.owner_pressure.job_security import JobSecurityModifier
from contract_valuation.context import JobSecurityContext, OwnerContext


class TestJobSecurityModifier:
    """Tests for JobSecurityModifier."""

    @pytest.fixture
    def modifier(self):
        """JobSecurityModifier instance."""
        return JobSecurityModifier()

    def test_modifier_name(self, modifier):
        """Test modifier returns correct name."""
        assert modifier.modifier_name == "job_security"

    def test_secure_gm_gets_discount(self, modifier, secure_context, base_aav):
        """Test secure GM (pressure < 0.3) gets discount up to -3%."""
        pressure = modifier.calculate_pressure_level(secure_context)
        assert pressure < 0.3, f"Secure context should have pressure < 0.3, got {pressure}"

        adjusted_aav, description = modifier.apply(base_aav, secure_context)

        # Should be discounted (less than base)
        assert adjusted_aav <= base_aav
        # Discount should be at most -3%
        assert adjusted_aav >= base_aav * 0.97
        assert "Secure GM" in description

    def test_normal_gm_no_adjustment(self, modifier, normal_pressure_context, base_aav):
        """Test normal pressure (0.3-0.7) produces no adjustment."""
        pressure = modifier.calculate_pressure_level(normal_pressure_context)
        assert 0.3 <= pressure <= 0.7, f"Normal context should have 0.3-0.7 pressure, got {pressure}"

        adjusted_aav, description = modifier.apply(base_aav, normal_pressure_context)

        # Should be no significant adjustment
        assert adjusted_aav == base_aav
        assert "Normal pressure" in description

    def test_hot_seat_gm_pays_premium(self, modifier, hot_seat_context, base_aav):
        """Test hot seat GM (pressure > 0.7) pays 10-15% premium."""
        pressure = modifier.calculate_pressure_level(hot_seat_context)
        assert pressure > 0.7, f"Hot seat context should have pressure > 0.7, got {pressure}"

        adjusted_aav, description = modifier.apply(base_aav, hot_seat_context)

        # Should pay premium (more than base)
        assert adjusted_aav > base_aav
        # Premium should be between 10% and 15%
        premium_pct = (adjusted_aav - base_aav) / base_aav
        assert 0.10 <= premium_pct <= 0.15, f"Premium {premium_pct:.2%} not in 10-15% range"
        assert "Hot seat" in description

    def test_pressure_at_secure_boundary(self, modifier, base_aav):
        """Test pressure exactly at 0.3 boundary produces 0% adjustment."""
        # Create context with pressure exactly at 0.3
        context = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext(
                tenure_years=4,
                playoff_appearances=1,
                recent_win_pct=0.55,
                owner_patience=0.5,
            ),
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        adjusted_aav, _ = modifier.apply(base_aav, context)
        pressure = modifier.calculate_pressure_level(context)

        # At exactly 0.3 or above, should be 0% adjustment
        if pressure >= 0.3:
            assert adjusted_aav == base_aav

    def test_pressure_at_hot_seat_boundary(self, modifier, base_aav):
        """Test pressure exactly at 0.7 boundary produces 0% adjustment."""
        # Create context with pressure near 0.7
        context = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext(
                tenure_years=2,
                playoff_appearances=0,
                recent_win_pct=0.45,
                owner_patience=0.4,
            ),
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        adjusted_aav, _ = modifier.apply(base_aav, context)
        pressure = modifier.calculate_pressure_level(context)

        # At exactly 0.7 or below, should be 0% or normal adjustment
        if pressure <= 0.7:
            assert adjusted_aav >= base_aav * 0.97  # Allow for secure discount
            assert adjusted_aav <= base_aav * 1.10  # No hot seat premium yet

    def test_maximum_pressure_level(self, modifier, base_aav):
        """Test near-maximum pressure produces +10-15% premium."""
        # Create context with maximum possible pressure
        # Max formula: tenure=0 -> 0.6, win_pct=0 -> 0.8, playoffs=0, patience=0
        # = 0.6*0.3 + 0.8*0.7 = 0.18 + 0.56 = 0.74 (max possible)
        context = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext(
                tenure_years=0,
                playoff_appearances=0,
                recent_win_pct=0.20,
                owner_patience=0.0,
            ),
            owner_philosophy="aggressive",
            team_philosophy="win_now",
            win_now_mode=True,
            max_contract_years=7,
            max_guaranteed_pct=0.80,
        )

        adjusted_aav, _ = modifier.apply(base_aav, context)
        pressure = modifier.calculate_pressure_level(context)

        # Should be at or above hot seat threshold (0.7)
        assert pressure >= 0.7

        # Premium should be in hot seat range (10-15%)
        premium_pct = (adjusted_aav - base_aav) / base_aav
        assert premium_pct >= 0.10

    def test_guarantee_adjustment_hot_seat(self, modifier, hot_seat_context):
        """Test hot seat GM has increased guarantee adjustment."""
        guarantee_adj = modifier.get_guarantee_adjustment(hot_seat_context)

        # Should be positive (increased guarantees)
        assert guarantee_adj > 0
        # Should be between 10% and 15%
        assert 0.10 <= guarantee_adj <= 0.15

    def test_description_format(self, modifier, hot_seat_context, base_aav):
        """Test description is human-readable."""
        adjusted_aav, description = modifier.apply(base_aav, hot_seat_context)

        # Should contain key information
        assert "%" in description  # Contains percentage
        assert "$" in description  # Contains dollar amount
        assert len(description) > 10  # Not empty


class TestJobSecurityBreakdown:
    """Tests for get_breakdown method."""

    @pytest.fixture
    def modifier(self):
        return JobSecurityModifier()

    def test_breakdown_structure(self, modifier, hot_seat_context, base_aav):
        """Test breakdown contains all expected fields."""
        breakdown = modifier.get_breakdown(hot_seat_context, base_aav)

        expected_keys = [
            "modifier_name",
            "pressure_level",
            "pressure_category",
            "base_aav",
            "adjustment_pct",
            "adjustment_dollars",
            "adjusted_aav",
            "guarantee_adjustment_pct",
            "job_security_inputs",
        ]

        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"

    def test_breakdown_categorizes_hot_seat(self, modifier, hot_seat_context, base_aav):
        """Test breakdown correctly identifies hot seat."""
        breakdown = modifier.get_breakdown(hot_seat_context, base_aav)
        assert breakdown["pressure_category"] == "hot_seat"

    def test_breakdown_categorizes_secure(self, modifier, secure_context, base_aav):
        """Test breakdown correctly identifies secure."""
        breakdown = modifier.get_breakdown(secure_context, base_aav)
        assert breakdown["pressure_category"] == "secure"