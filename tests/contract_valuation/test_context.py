"""
Unit tests for contract valuation context models.

Tests JobSecurityContext, ValuationContext, and OwnerContext
validation, factories, and calculations.
"""

import pytest

from contract_valuation.context import (
    JobSecurityContext,
    ValuationContext,
    OwnerContext,
)


class TestJobSecurityContext:
    """Tests for JobSecurityContext dataclass."""

    def test_job_security_score_new_losing_gm(self):
        """Test security score for a new GM with poor record."""
        context = JobSecurityContext(
            tenure_years=1,
            playoff_appearances=0,
            recent_win_pct=0.30,
            owner_patience=0.3
        )

        score = context.calculate_security_score()

        # New GM (0.6 * 0.3) + losing record (0.8 * 0.7) - 0 playoffs - (0.3 * 0.3)
        # = 0.18 + 0.56 - 0 - 0.09 = 0.65
        assert 0.5 <= score <= 0.8  # High pressure
        assert score > 0.5  # Definitely on hot seat

    def test_job_security_score_established_winning_gm(self):
        """Test security score for established GM with good record."""
        context = JobSecurityContext(
            tenure_years=6,
            playoff_appearances=3,
            recent_win_pct=0.65,
            owner_patience=0.9
        )

        score = context.calculate_security_score()

        # Established (0.2 * 0.3) + winning (0.2 * 0.7) - 0.3 playoffs - (0.9 * 0.3)
        # = 0.06 + 0.14 - 0.3 - 0.27 = -0.37 -> clamped to 0.0
        assert score <= 0.1  # Very secure, near floor

    def test_job_security_create_secure_factory(self):
        """Test create_secure factory produces low pressure GM."""
        context = JobSecurityContext.create_secure()

        score = context.calculate_security_score()
        assert score <= 0.2  # Very secure

    def test_job_security_create_hot_seat_factory(self):
        """Test create_hot_seat factory produces high pressure GM."""
        context = JobSecurityContext.create_hot_seat()

        score = context.calculate_security_score()
        assert score >= 0.35  # On the hot seat (moderate-high pressure)


class TestOwnerContext:
    """Tests for OwnerContext dataclass."""

    def test_owner_context_budget_multiplier_aggressive(self):
        """Test aggressive owner has higher spending multiplier."""
        context = OwnerContext(
            dynasty_id="test_dynasty",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="aggressive",
            team_philosophy="win_now",
            win_now_mode=True,
            max_contract_years=6,
            max_guaranteed_pct=0.70
        )

        multiplier = context.get_budget_multiplier()
        assert multiplier == 1.15

    def test_owner_context_budget_multiplier_conservative(self):
        """Test conservative owner has lower spending multiplier."""
        context = OwnerContext(
            dynasty_id="test_dynasty",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="conservative",
            team_philosophy="rebuild",
            win_now_mode=False,
            max_contract_years=4,
            max_guaranteed_pct=0.50
        )

        multiplier = context.get_budget_multiplier()
        assert multiplier == 0.90

    def test_owner_context_from_owner_directives(self):
        """Test creating OwnerContext from owner directives mock."""
        # Create a mock directives object
        class MockDirectives:
            dynasty_id = "mock_dynasty"
            team_id = 15
            budget_stance = "balanced"
            team_philosophy = "maintain"
            max_contract_years = 5
            max_guaranteed_percent = 0.55

        directives = MockDirectives()
        job_security = JobSecurityContext.create_secure()

        context = OwnerContext.from_owner_directives(directives, job_security)

        assert context.dynasty_id == "mock_dynasty"
        assert context.team_id == 15
        assert context.owner_philosophy == "balanced"
        assert context.team_philosophy == "maintain"
        assert context.win_now_mode is False
        assert context.max_contract_years == 5
        assert context.max_guaranteed_pct == 0.55


class TestValuationContext:
    """Tests for ValuationContext dataclass."""

    def test_valuation_context_get_market_rate(self):
        """Test getting market rate for position/tier."""
        context = ValuationContext.create_default_2025()

        # Test QB elite tier
        qb_elite = context.get_market_rate("QB", "elite")
        assert qb_elite == 50_000_000

        # Test WR starter tier
        wr_starter = context.get_market_rate("WR", "starter")
        assert wr_starter == 8_000_000

        # Test case insensitivity
        edge_quality = context.get_market_rate("edge", "quality")
        assert edge_quality == 18_000_000

        # Test missing position returns None
        unknown = context.get_market_rate("UNKNOWN", "starter")
        assert unknown is None

        # Test missing tier returns None
        missing_tier = context.get_market_rate("QB", "superstar")
        assert missing_tier is None