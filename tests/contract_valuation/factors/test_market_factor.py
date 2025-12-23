"""
Unit tests for MarketFactor.

Tests market heat multipliers and contract year premiums.
"""

import pytest

from contract_valuation.factors.market_factor import MarketFactor
from contract_valuation.context import ValuationContext


class TestMarketFactor:
    """Tests for MarketFactor valuation."""

    @pytest.fixture
    def factor(self):
        """MarketFactor instance."""
        return MarketFactor()

    def test_elite_qb_market_rate(self, factor, default_context, sample_qb_data):
        """Test Elite QB gets 50M * 1.20 heat multiplier (calibrated to NFL 2024)."""
        result = factor.calculate(sample_qb_data, default_context)

        assert result.name == "market"
        assert result.confidence == 0.90
        assert result.breakdown["market_heat"] == 1.20

        # Elite QB base 50M * 1.20 heat = 60M, then rating adj
        assert 52_000_000 <= result.raw_value <= 68_000_000

    def test_rb_market_devaluation(self, factor, default_context, sample_rb_data):
        """Test RB gets 1.0x heat (calibrated - less severe devaluation)."""
        result = factor.calculate(sample_rb_data, default_context)

        assert result.breakdown["market_heat"] == 1.00
        # Quality RB base 8M * 1.0 = 8M, plus contract year
        assert result.breakdown["position"] == "RB"

    def test_contract_year_premium(self, factor, default_context, sample_rb_data):
        """Test contract year adds 5%."""
        result = factor.calculate(sample_rb_data, default_context)

        assert result.breakdown["contract_year"] is True
        assert result.breakdown["contract_year_premium"] == 1.05

        # Compare without contract year
        no_contract_year = sample_rb_data.copy()
        no_contract_year["contract_year"] = False
        result_no_cy = factor.calculate(no_contract_year, default_context)

        # Contract year result should be ~5% higher
        assert result.raw_value > result_no_cy.raw_value
        ratio = result.raw_value / result_no_cy.raw_value
        assert 1.03 <= ratio <= 1.07

    def test_edge_rusher_premium(self, factor, default_context, edge_rusher_data):
        """Test EDGE gets 1.18x heat (calibrated to NFL 2024)."""
        result = factor.calculate(edge_rusher_data, default_context)

        # LOLB maps to EDGE
        assert result.breakdown["mapped_position"] == "EDGE"
        assert result.breakdown["market_heat"] == 1.18

    def test_unknown_position_fallback(self, factor, default_context):
        """Test unknown position uses cap percentage fallback."""
        player_data = {
            "player_id": 100,
            "name": "Test Unknown",
            "position": "UNKNOWN",
            "overall_rating": 85,
        }

        result = factor.calculate(player_data, default_context)

        assert result.breakdown["fallback_used"] is True
        assert result.confidence == 0.80  # Lower for fallback

    def test_rating_within_tier_scaling(self, factor, default_context):
        """Test 98 rating produces higher value than 90 in elite tier."""
        high_rating = {
            "player_id": 100,
            "name": "Test High",
            "position": "WR",
            "overall_rating": 98,
        }
        low_rating = {
            "player_id": 101,
            "name": "Test Low",
            "position": "WR",
            "overall_rating": 90,
        }

        high_result = factor.calculate(high_rating, default_context)
        low_result = factor.calculate(low_rating, default_context)

        assert high_result.raw_value > low_result.raw_value
        assert high_result.breakdown["rating_adjustment"] > low_result.breakdown["rating_adjustment"]

    def test_position_group_mapping(self, factor, default_context):
        """Test LOLB maps to EDGE for heat multiplier."""
        player_data = {
            "player_id": 100,
            "name": "Test LOLB",
            "position": "LOLB",
            "overall_rating": 85,
        }

        result = factor.calculate(player_data, default_context)

        assert result.breakdown["mapped_position"] == "EDGE"
        assert result.breakdown["market_heat"] == 1.18

    def test_starter_tier_valuation(self, factor, default_context):
        """Test 75 rating gets starter market rate."""
        player_data = {
            "player_id": 100,
            "name": "Test Starter",
            "position": "TE",
            "overall_rating": 75,
        }

        result = factor.calculate(player_data, default_context)

        assert result.breakdown["tier"] == "starter"
        # TE starter base is 6M
        assert 5_000_000 <= result.raw_value <= 7_000_000
