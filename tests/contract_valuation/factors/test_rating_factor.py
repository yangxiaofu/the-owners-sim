"""
Unit tests for RatingFactor.

Tests tier-based valuation and within-tier scaling.
"""

import pytest

from contract_valuation.factors.rating_factor import RatingFactor
from contract_valuation.context import ValuationContext


class TestRatingFactor:
    """Tests for RatingFactor valuation."""

    @pytest.fixture
    def factor(self):
        """RatingFactor instance."""
        return RatingFactor()

    def test_elite_qb_valuation(self, factor, default_context, sample_qb_data):
        """Test Rating 95 QB returns elite tier with appropriate scaling."""
        result = factor.calculate(sample_qb_data, default_context)

        assert result.name == "rating"
        assert result.confidence == 0.85
        assert result.breakdown["tier"] == "elite"
        assert result.breakdown["rating"] == 95

        # Elite QB base rate is 50M, with 95 rating should get ~1.04x scaling
        # 95 is at position 0.5 in tier (90-99 range) -> scale ~1.025
        assert 48_000_000 <= result.raw_value <= 58_000_000

    def test_starter_rb_valuation(self, factor, default_context):
        """Test Rating 75 RB returns starter tier."""
        player_data = {
            "player_id": 100,
            "name": "Test RB",
            "position": "RB",
            "overall_rating": 75,
        }

        result = factor.calculate(player_data, default_context)

        assert result.breakdown["tier"] == "starter"
        assert result.breakdown["rating"] == 75

        # Starter RB base rate is 4M, with mid-tier scaling
        assert 3_500_000 <= result.raw_value <= 4_600_000

    def test_backup_player_valuation(self, factor, default_context):
        """Test Rating 65 returns backup tier."""
        player_data = {
            "player_id": 100,
            "name": "Test Backup",
            "position": "WR",
            "overall_rating": 65,
        }

        result = factor.calculate(player_data, default_context)

        assert result.breakdown["tier"] == "backup"
        # Backup WR base rate is 2M
        assert 1_500_000 <= result.raw_value <= 2_500_000

    def test_rating_scaling_top_of_tier(self, factor, default_context):
        """Test Rating 99 gets maximum within-tier scaling (~1.15x)."""
        player_data = {
            "player_id": 100,
            "name": "Test Elite",
            "position": "CB",
            "overall_rating": 99,
        }

        result = factor.calculate(player_data, default_context)

        # 99 is at position 1.0 in elite tier -> scale = 1.15
        assert result.breakdown["scale_factor"] >= 1.10
        # Elite CB is 22M * 1.15 = ~25.3M
        assert result.raw_value >= 24_000_000

    def test_rating_scaling_bottom_of_tier(self, factor, default_context):
        """Test Rating 90 gets minimum within-tier scaling (~0.90x)."""
        player_data = {
            "player_id": 100,
            "name": "Test Bottom Elite",
            "position": "CB",
            "overall_rating": 90,
        }

        result = factor.calculate(player_data, default_context)

        # 90 is at position 0.0 in elite tier -> scale = 0.90
        assert result.breakdown["scale_factor"] <= 0.95
        # Elite CB is 22M * 0.90 = ~19.8M
        assert result.raw_value <= 21_000_000

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
        # Quality tier uses 2.5% of cap = 255M * 0.025 = 6.375M
        assert result.raw_value > 5_000_000

    def test_invalid_rating_raises_error(self, factor, default_context):
        """Test Rating > 99 raises ValueError."""
        player_data = {
            "player_id": 100,
            "name": "Test Invalid",
            "position": "QB",
            "overall_rating": 105,
        }

        with pytest.raises(ValueError, match="overall_rating must be int 0-99"):
            factor.calculate(player_data, default_context)

    def test_missing_position_raises_error(self, factor, default_context):
        """Test missing position raises ValueError."""
        player_data = {
            "player_id": 100,
            "name": "Test No Position",
            "overall_rating": 85,
        }

        with pytest.raises(ValueError, match="Missing required player_data fields"):
            factor.calculate(player_data, default_context)
