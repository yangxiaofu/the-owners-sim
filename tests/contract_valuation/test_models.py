"""
Unit tests for contract valuation models.

Tests FactorResult, FactorWeights, ContractOffer, and ValuationResult
validation, factories, and serialization.
"""

import pytest
from datetime import datetime

from contract_valuation.models import (
    FactorResult,
    FactorWeights,
    ContractOffer,
    ValuationResult,
)


class TestFactorResult:
    """Tests for FactorResult dataclass."""

    def test_factor_result_valid_creation(self):
        """Test creating a valid FactorResult."""
        result = FactorResult(
            name="stats_based",
            raw_value=15_000_000,
            confidence=0.85,
            breakdown={"yards_per_game": 100, "tier": "quality"}
        )

        assert result.name == "stats_based"
        assert result.raw_value == 15_000_000
        assert result.confidence == 0.85
        assert result.breakdown["yards_per_game"] == 100

    def test_factor_result_validates_empty_name(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            FactorResult(name="", raw_value=1000, confidence=0.5)

    def test_factor_result_validates_negative_value(self):
        """Test that negative raw_value raises ValueError."""
        with pytest.raises(ValueError, match="raw_value must be a non-negative integer"):
            FactorResult(name="test", raw_value=-1000, confidence=0.5)

    def test_factor_result_validates_confidence_range(self):
        """Test that confidence outside 0.0-1.0 raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            FactorResult(name="test", raw_value=1000, confidence=1.5)

        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            FactorResult(name="test", raw_value=1000, confidence=-0.1)


class TestFactorWeights:
    """Tests for FactorWeights dataclass."""

    def test_factor_weights_valid_creation(self):
        """Test creating valid FactorWeights with default values."""
        weights = FactorWeights()

        assert weights.stats_weight == 0.30
        assert weights.scouting_weight == 0.25
        assert weights.market_weight == 0.25
        assert weights.rating_weight == 0.20

    def test_factor_weights_validates_sum(self):
        """Test that weights not summing to 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            FactorWeights(
                stats_weight=0.5,
                scouting_weight=0.5,
                market_weight=0.5,
                rating_weight=0.5
            )

    def test_factor_weights_factory_analytics_heavy(self):
        """Test analytics_heavy factory produces correct weights."""
        weights = FactorWeights.create_analytics_heavy()

        assert weights.stats_weight == 0.50
        assert weights.scouting_weight == 0.15
        assert weights.market_weight == 0.20
        assert weights.rating_weight == 0.15

        # Verify sum
        total = (weights.stats_weight + weights.scouting_weight +
                 weights.market_weight + weights.rating_weight)
        assert 0.99 <= total <= 1.01


class TestContractOffer:
    """Tests for ContractOffer dataclass."""

    def test_contract_offer_valid_creation(self):
        """Test creating a valid ContractOffer."""
        offer = ContractOffer(
            aav=20_000_000,
            years=4,
            total_value=80_000_000,
            guaranteed=50_000_000,
            signing_bonus=20_000_000,
            guaranteed_pct=0.625
        )

        assert offer.aav == 20_000_000
        assert offer.years == 4
        assert offer.total_value == 80_000_000
        assert offer.guaranteed == 50_000_000

    def test_contract_offer_validates_years_range(self):
        """Test that years outside 1-7 raises ValueError."""
        with pytest.raises(ValueError, match="years must be 1-7"):
            ContractOffer(
                aav=10_000_000,
                years=0,
                total_value=10_000_000,
                guaranteed=5_000_000,
                signing_bonus=2_000_000,
                guaranteed_pct=0.5
            )

        with pytest.raises(ValueError, match="years must be 1-7"):
            ContractOffer(
                aav=10_000_000,
                years=10,
                total_value=100_000_000,
                guaranteed=50_000_000,
                signing_bonus=20_000_000,
                guaranteed_pct=0.5
            )

    def test_contract_offer_validates_guaranteed_exceeds_total(self):
        """Test that guaranteed exceeding total_value raises ValueError."""
        with pytest.raises(ValueError, match="guaranteed .* cannot exceed total_value"):
            ContractOffer(
                aav=10_000_000,
                years=3,
                total_value=30_000_000,
                guaranteed=40_000_000,  # Exceeds total
                signing_bonus=5_000_000,
                guaranteed_pct=1.0
            )


class TestValuationResult:
    """Tests for ValuationResult dataclass."""

    def _create_sample_result(self) -> ValuationResult:
        """Helper to create a valid ValuationResult for testing."""
        offer = ContractOffer(
            aav=20_000_000,
            years=4,
            total_value=80_000_000,
            guaranteed=50_000_000,
            signing_bonus=20_000_000,
            guaranteed_pct=0.625
        )

        factor_result = FactorResult(
            name="stats_based",
            raw_value=18_000_000,
            confidence=0.9,
            breakdown={"tier": "quality"}
        )

        weights = FactorWeights.create_balanced()

        return ValuationResult(
            offer=offer,
            factor_contributions={"stats_based": 6_000_000, "scouting": 5_000_000},
            gm_style="balanced",
            gm_style_description="Balanced approach",
            pressure_level=0.3,
            pressure_adjustment_pct=0.05,
            pressure_description="Moderate pressure: +5%",
            raw_factor_results=[factor_result],
            weights_used=weights,
            base_aav=19_000_000,
            player_id=12345,
            player_name="John Doe",
            position="WR",
            valuation_timestamp=datetime.now().isoformat()
        )

    def test_valuation_result_to_benchmark_format(self):
        """Test to_benchmark_format exports correct fields."""
        result = self._create_sample_result()
        benchmark = result.to_benchmark_format()

        assert benchmark["player_name"] == "John Doe"
        assert benchmark["position"] == "WR"
        assert benchmark["aav"] == 20_000_000
        assert benchmark["years"] == 4
        assert benchmark["total_value"] == 80_000_000
        assert benchmark["guaranteed"] == 50_000_000
        assert benchmark["guaranteed_pct"] == 0.625
        assert benchmark["gm_style"] == "balanced"
        assert benchmark["pressure_level"] == 0.3
        assert benchmark["base_aav"] == 19_000_000
        assert benchmark["adjustment_pct"] == 0.05

    def test_valuation_result_round_trip(self):
        """Test serialization round-trip preserves data."""
        original = self._create_sample_result()

        # Convert to dict and back
        data = original.to_dict()
        restored = ValuationResult.from_dict(data)

        assert restored.offer.aav == original.offer.aav
        assert restored.player_name == original.player_name
        assert restored.gm_style == original.gm_style
        assert restored.pressure_level == original.pressure_level
        assert len(restored.raw_factor_results) == len(original.raw_factor_results)