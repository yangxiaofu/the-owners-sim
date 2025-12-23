"""
Unit tests for WinNowModifier.

Tests adjustments based on team philosophy and player age.
"""

import pytest

from contract_valuation.owner_pressure.win_now import WinNowModifier
from contract_valuation.context import JobSecurityContext, OwnerContext


class TestWinNowModifier:
    """Tests for WinNowModifier."""

    @pytest.fixture
    def modifier(self):
        """WinNowModifier instance."""
        return WinNowModifier()

    def test_modifier_name(self, modifier):
        """Test modifier returns correct name."""
        assert modifier.modifier_name == "win_now"

    def test_win_now_veteran_premium(self, modifier, win_now_context, base_aav):
        """Test win-now team pays +12% premium for veterans (31+)."""
        player_age = 32
        adjusted_aav, description = modifier.apply(base_aav, win_now_context, player_age=player_age)

        # Should pay premium
        assert adjusted_aav > base_aav
        # Premium should be +12%
        premium_pct = (adjusted_aav - base_aav) / base_aav
        assert abs(premium_pct - 0.12) < 0.01, f"Expected +12%, got {premium_pct:.2%}"
        assert "veteran" in description.lower()

    def test_win_now_prime_premium(self, modifier, win_now_context, base_aav):
        """Test win-now team pays +5% premium for prime players (26-30)."""
        player_age = 28
        adjusted_aav, description = modifier.apply(base_aav, win_now_context, player_age=player_age)

        # Should pay premium
        assert adjusted_aav > base_aav
        # Premium should be +5%
        premium_pct = (adjusted_aav - base_aav) / base_aav
        assert abs(premium_pct - 0.05) < 0.01, f"Expected +5%, got {premium_pct:.2%}"
        assert "prime" in description.lower()

    def test_win_now_young_discount(self, modifier, win_now_context, base_aav):
        """Test win-now team discounts young players (<26) by -5%."""
        player_age = 23
        adjusted_aav, description = modifier.apply(base_aav, win_now_context, player_age=player_age)

        # Should discount
        assert adjusted_aav < base_aav
        # Discount should be -5%
        discount_pct = (adjusted_aav - base_aav) / base_aav
        assert abs(discount_pct - (-0.05)) < 0.01, f"Expected -5%, got {discount_pct:.2%}"
        assert "young" in description.lower()

    def test_rebuild_veteran_discount(self, modifier, rebuild_context, base_aav):
        """Test rebuilding team discounts veterans (31+) by -10%."""
        player_age = 33
        adjusted_aav, description = modifier.apply(base_aav, rebuild_context, player_age=player_age)

        # Should discount
        assert adjusted_aav < base_aav
        # Discount should be -10%
        discount_pct = (adjusted_aav - base_aav) / base_aav
        assert abs(discount_pct - (-0.10)) < 0.01, f"Expected -10%, got {discount_pct:.2%}"

    def test_rebuild_young_premium(self, modifier, rebuild_context, base_aav):
        """Test rebuilding team pays +8% premium for young players (<26)."""
        player_age = 22
        adjusted_aav, description = modifier.apply(base_aav, rebuild_context, player_age=player_age)

        # Should pay premium
        assert adjusted_aav > base_aav
        # Premium should be +8%
        premium_pct = (adjusted_aav - base_aav) / base_aav
        assert abs(premium_pct - 0.08) < 0.01, f"Expected +8%, got {premium_pct:.2%}"

    def test_maintain_neutral_adjustments(self, modifier, normal_pressure_context, base_aav):
        """Test maintaining team has moderate adjustments."""
        # Young: +3%
        adjusted_young, _ = modifier.apply(base_aav, normal_pressure_context, player_age=23)
        young_pct = (adjusted_young - base_aav) / base_aav
        assert abs(young_pct - 0.03) < 0.01

        # Prime: 0%
        adjusted_prime, _ = modifier.apply(base_aav, normal_pressure_context, player_age=28)
        assert adjusted_prime == base_aav

        # Veteran: -3%
        adjusted_vet, _ = modifier.apply(base_aav, normal_pressure_context, player_age=32)
        vet_pct = (adjusted_vet - base_aav) / base_aav
        assert abs(vet_pct - (-0.03)) < 0.01

    def test_age_category_boundaries(self, modifier, win_now_context, base_aav):
        """Test age category boundaries (25, 26, 30, 31)."""
        # Age 25 should be young
        assert modifier._get_age_category(25) == "young"

        # Age 26 should be prime
        assert modifier._get_age_category(26) == "prime"

        # Age 30 should be prime
        assert modifier._get_age_category(30) == "prime"

        # Age 31 should be veteran
        assert modifier._get_age_category(31) == "veteran"

    def test_win_now_mode_flag_effect(self, modifier, base_aav):
        """Test win_now_mode=True boosts pressure by +0.1."""
        # Context without win_now_mode
        context_off = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="balanced",
            team_philosophy="win_now",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        # Context with win_now_mode
        context_on = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="balanced",
            team_philosophy="win_now",
            win_now_mode=True,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        pressure_off = modifier.calculate_pressure_level(context_off)
        pressure_on = modifier.calculate_pressure_level(context_on)

        # win_now_mode should boost pressure by 0.1
        assert abs((pressure_on - pressure_off) - 0.1) < 0.01


class TestWinNowNoAge:
    """Tests for WinNowModifier without player age."""

    @pytest.fixture
    def modifier(self):
        return WinNowModifier()

    def test_no_age_no_adjustment(self, modifier, win_now_context, base_aav):
        """Test no age provided results in no adjustment."""
        adjusted_aav, description = modifier.apply(base_aav, win_now_context, player_age=None)
        assert adjusted_aav == base_aav
        assert "no age" in description.lower()


class TestWinNowBreakdown:
    """Tests for get_breakdown method."""

    @pytest.fixture
    def modifier(self):
        return WinNowModifier()

    def test_breakdown_structure(self, modifier, win_now_context, base_aav):
        """Test breakdown contains all expected fields."""
        breakdown = modifier.get_breakdown(win_now_context, base_aav, player_age=28)

        expected_keys = [
            "modifier_name",
            "pressure_level",
            "team_philosophy",
            "win_now_mode",
            "player_age",
            "age_category",
            "base_aav",
            "adjustment_pct",
            "adjustment_dollars",
            "adjusted_aav",
            "rationale",
        ]

        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"

    def test_breakdown_rationale_win_now_veteran(self, modifier, win_now_context, base_aav):
        """Test rationale for win-now veteran."""
        breakdown = modifier.get_breakdown(win_now_context, base_aav, player_age=32)
        assert "veteran" in breakdown["rationale"].lower()
        assert "premium" in breakdown["rationale"].lower()