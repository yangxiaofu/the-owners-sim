"""
Unit tests for stats_calculator utilities.

Tests all NFL statistical calculation functions.
"""

import pytest
from src.utils.stats_calculator import (
    calculate_passer_rating,
    calculate_completion_percentage,
    calculate_yards_per_attempt,
    calculate_yards_per_carry,
    calculate_yards_per_reception,
    calculate_catch_rate,
    calculate_touchdown_rate,
    calculate_interception_rate,
    calculate_field_goal_percentage,
    calculate_net_yards_per_punt,
    calculate_sack_rate,
)


class TestPasserRating:
    """Tests for NFL passer rating calculation."""

    def test_zero_attempts(self):
        """Rating should be 0 when no passes thrown."""
        rating = calculate_passer_rating(0, 0, 0, 0, 0)
        assert rating == 0.0

    def test_perfect_passer_rating(self):
        """Perfect passer rating should be 158.3."""
        # Perfect: 100% completion, 12.5+ YPA, 11.875%+ TD rate, 0% INT rate
        rating = calculate_passer_rating(30, 30, 400, 5, 0)
        assert 158.0 <= rating <= 158.4  # Allow small float variance

    def test_good_performance(self):
        """Good QB performance should yield rating ~120."""
        # 66.7% completion, 10 YPA, 10% TD rate, 3.3% INT rate
        rating = calculate_passer_rating(20, 30, 300, 3, 1)
        assert 115.0 <= rating <= 130.0

    def test_average_performance(self):
        """Average QB performance should yield rating ~80-90."""
        # 60% completion, 7 YPA, 3.3% TD rate, 3.3% INT rate
        rating = calculate_passer_rating(18, 30, 210, 1, 1)
        assert 75.0 <= rating <= 95.0

    def test_poor_performance(self):
        """Poor QB performance should yield rating ~35-50."""
        # 50% completion, 5 YPA, 0% TD rate, 6.7% INT rate
        rating = calculate_passer_rating(15, 30, 150, 0, 2)
        assert 35.0 <= rating <= 50.0

    def test_real_world_example_mahomes(self):
        """Test with Patrick Mahomes-like elite stats."""
        # 67% completion, 8.5 YPA, 7% TD rate, 1.5% INT rate
        rating = calculate_passer_rating(320, 480, 4100, 35, 7)
        assert 105.0 <= rating <= 115.0

    def test_component_clamping(self):
        """Components should be clamped to [0, 2.375] range."""
        # Ultra-high efficiency (should clamp at max)
        rating1 = calculate_passer_rating(30, 30, 500, 10, 0)
        # Another perfect scenario
        rating2 = calculate_passer_rating(25, 25, 400, 8, 0)
        # Both should be near 158.3 (max rating)
        assert 155.0 <= rating1 <= 158.4
        assert 155.0 <= rating2 <= 158.4


class TestCompletionPercentage:
    """Tests for completion percentage calculation."""

    def test_zero_attempts(self):
        assert calculate_completion_percentage(0, 0) == 0.0

    def test_perfect_completion(self):
        assert calculate_completion_percentage(20, 20) == 100.0

    def test_typical_completion(self):
        pct = calculate_completion_percentage(20, 30)
        assert 66.0 <= pct <= 67.0


class TestYardsPerAttempt:
    """Tests for yards per attempt calculations."""

    def test_zero_attempts(self):
        assert calculate_yards_per_attempt(0, 0) == 0.0

    def test_passing_ypa(self):
        ypa = calculate_yards_per_attempt(300, 30)
        assert ypa == 10.0

    def test_rushing_ypc(self):
        ypc = calculate_yards_per_carry(120, 25)
        assert ypc == 4.8


class TestYardsPerReception:
    """Tests for yards per reception calculation."""

    def test_zero_receptions(self):
        assert calculate_yards_per_reception(0, 0) == 0.0

    def test_typical_ypr(self):
        ypr = calculate_yards_per_reception(150, 10)
        assert ypr == 15.0

    def test_deep_threat_ypr(self):
        ypr = calculate_yards_per_reception(400, 20)
        assert ypr == 20.0


class TestCatchRate:
    """Tests for catch rate calculation."""

    def test_zero_targets(self):
        assert calculate_catch_rate(0, 0) == 0.0

    def test_perfect_catch_rate(self):
        assert calculate_catch_rate(10, 10) == 100.0

    def test_typical_catch_rate(self):
        rate = calculate_catch_rate(8, 10)
        assert rate == 80.0


class TestTouchdownRate:
    """Tests for touchdown rate calculation."""

    def test_zero_attempts(self):
        assert calculate_touchdown_rate(0, 0) == 0.0

    def test_typical_td_rate(self):
        rate = calculate_touchdown_rate(3, 30)
        assert rate == 10.0

    def test_high_td_rate(self):
        rate = calculate_touchdown_rate(5, 25)
        assert rate == 20.0


class TestInterceptionRate:
    """Tests for interception rate calculation."""

    def test_zero_attempts(self):
        assert calculate_interception_rate(0, 0) == 0.0

    def test_typical_int_rate(self):
        rate = calculate_interception_rate(2, 30)
        assert 6.6 <= rate <= 6.7

    def test_zero_interceptions(self):
        rate = calculate_interception_rate(0, 30)
        assert rate == 0.0


class TestFieldGoalPercentage:
    """Tests for field goal percentage calculation."""

    def test_zero_attempts(self):
        assert calculate_field_goal_percentage(0, 0) == 0.0

    def test_perfect_kicker(self):
        assert calculate_field_goal_percentage(30, 30) == 100.0

    def test_typical_kicker(self):
        pct = calculate_field_goal_percentage(28, 32)
        assert pct == 87.5


class TestNetYardsPerPunt:
    """Tests for net yards per punt calculation."""

    def test_zero_punts(self):
        assert calculate_net_yards_per_punt(0, 0, 0) == 0.0

    def test_no_returns(self):
        nypp = calculate_net_yards_per_punt(450, 10, 0)
        assert nypp == 45.0

    def test_with_returns(self):
        nypp = calculate_net_yards_per_punt(450, 10, 50)
        assert nypp == 40.0

    def test_negative_net(self):
        """Net can be negative if returns exceed gross yards."""
        nypp = calculate_net_yards_per_punt(200, 10, 300)
        assert nypp == -10.0


class TestSackRate:
    """Tests for sack rate calculation."""

    def test_zero_attempts(self):
        assert calculate_sack_rate(0, 0) == 0.0

    def test_typical_sack_rate(self):
        rate = calculate_sack_rate(3, 30)
        assert rate == 10.0

    def test_zero_sacks(self):
        rate = calculate_sack_rate(0, 30)
        assert rate == 0.0
