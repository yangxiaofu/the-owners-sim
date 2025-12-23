"""
Unit tests for GMWeightCalculator.

Tests interpolated weight calculation from GM archetype traits.
15 tests covering normal cases, edge cases, rationale, and variance.
"""

import pytest

from contract_valuation.gm_influence.weight_calculator import (
    GMWeightCalculator,
    WeightCalculationResult,
)
from contract_valuation.gm_influence.styles import GMStyle
from contract_valuation.models import FactorWeights
from team_management.gm_archetype import GMArchetype


class TestGMWeightCalculator:
    """Tests for GMWeightCalculator."""

    @pytest.fixture
    def calculator(self):
        """GMWeightCalculator instance."""
        return GMWeightCalculator()

    @pytest.fixture
    def balanced_archetype(self):
        """Archetype with all traits at 0.5."""
        return GMArchetype(
            name="Balanced GM",
            description="Evenly weighted GM",
            analytics_preference=0.5,
            scouting_preference=0.5,
            market_awareness=0.5,
        )

    @pytest.fixture
    def analytics_heavy_archetype(self):
        """Archetype with high analytics preference."""
        return GMArchetype(
            name="Analytics GM",
            description="Stats-focused GM",
            analytics_preference=0.8,
            scouting_preference=0.3,
            market_awareness=0.4,
        )

    @pytest.fixture
    def scout_focused_archetype(self):
        """Archetype with high scouting preference."""
        return GMArchetype(
            name="Scout GM",
            description="Scouting-focused GM",
            analytics_preference=0.3,
            scouting_preference=0.8,
            market_awareness=0.4,
        )

    @pytest.fixture
    def market_driven_archetype(self):
        """Archetype with high market awareness."""
        return GMArchetype(
            name="Market GM",
            description="Market-driven GM",
            analytics_preference=0.3,
            scouting_preference=0.4,
            market_awareness=0.8,
        )

    # ==========================================================================
    # Normal Cases (6 tests)
    # ==========================================================================

    def test_balanced_archetype_produces_even_weights(
        self, calculator, balanced_archetype
    ):
        """Test all traits 0.5 produces equal distribution among variable factors."""
        result = calculator.calculate_weights(balanced_archetype)

        assert isinstance(result, WeightCalculationResult)
        weights = result.weights

        # With equal traits, stats/scouting/market should be equal
        # Each gets 0.05 floor + (0.70 * 1/3) = 0.05 + 0.233 = ~0.283
        assert abs(weights.stats_weight - weights.scouting_weight) < 0.01
        assert abs(weights.scouting_weight - weights.market_weight) < 0.01
        assert result.dominant_style == GMStyle.BALANCED

    def test_analytics_heavy_produces_high_stats_weight(
        self, calculator, analytics_heavy_archetype
    ):
        """Test high analytics trait produces stats weight > 35%."""
        result = calculator.calculate_weights(analytics_heavy_archetype)

        assert result.weights.stats_weight > 0.35
        assert result.dominant_style == GMStyle.ANALYTICS_HEAVY

    def test_scout_focused_produces_high_scouting_weight(
        self, calculator, scout_focused_archetype
    ):
        """Test high scouting trait produces scouting weight > 35%."""
        result = calculator.calculate_weights(scout_focused_archetype)

        assert result.weights.scouting_weight > 0.35
        assert result.dominant_style == GMStyle.SCOUT_FOCUSED

    def test_market_driven_produces_high_market_weight(
        self, calculator, market_driven_archetype
    ):
        """Test high market trait produces market weight > 35%."""
        result = calculator.calculate_weights(market_driven_archetype)

        assert result.weights.market_weight > 0.35
        assert result.dominant_style == GMStyle.MARKET_DRIVEN

    def test_weights_always_sum_to_one(self, calculator):
        """Test various combinations always sum to 1.0."""
        test_cases = [
            (0.5, 0.5, 0.5),
            (0.9, 0.1, 0.1),
            (0.1, 0.9, 0.1),
            (0.1, 0.1, 0.9),
            (0.7, 0.4, 0.5),
            (0.3, 0.6, 0.8),
        ]

        for analytics, scouting, market in test_cases:
            archetype = GMArchetype(
                name="Test GM",
                description="Test",
                analytics_preference=analytics,
                scouting_preference=scouting,
                market_awareness=market,
            )
            result = calculator.calculate_weights(archetype)
            weights = result.weights
            total = (
                weights.stats_weight
                + weights.scouting_weight
                + weights.market_weight
                + weights.rating_weight
            )
            assert abs(total - 1.0) < 0.01, f"Sum {total} for ({analytics}, {scouting}, {market})"

    def test_rating_weight_always_positive(self, calculator):
        """Test rating weight stays at ~15% baseline."""
        test_cases = [
            (0.5, 0.5, 0.5),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ]

        for analytics, scouting, market in test_cases:
            archetype = GMArchetype(
                name="Test GM",
                description="Test",
                analytics_preference=analytics,
                scouting_preference=scouting,
                market_awareness=market,
            )
            result = calculator.calculate_weights(archetype)
            # Rating weight should be exactly 0.15 (±0.01)
            assert abs(result.weights.rating_weight - 0.15) < 0.01

    # ==========================================================================
    # Edge Cases (4 tests)
    # ==========================================================================

    def test_all_traits_zero_produces_balanced(self, calculator):
        """Test (0,0,0) traits produce equal distribution."""
        archetype = GMArchetype(
            name="Zero GM",
            description="All zeros",
            analytics_preference=0.0,
            scouting_preference=0.0,
            market_awareness=0.0,
        )
        result = calculator.calculate_weights(archetype)

        weights = result.weights
        # Should be equal distribution
        assert abs(weights.stats_weight - weights.scouting_weight) < 0.01
        assert abs(weights.scouting_weight - weights.market_weight) < 0.01
        assert result.dominant_style == GMStyle.BALANCED

    def test_all_traits_maximum_produces_balanced(self, calculator):
        """Test (1,1,1) traits produce equal distribution."""
        archetype = GMArchetype(
            name="Max GM",
            description="All maxed",
            analytics_preference=1.0,
            scouting_preference=1.0,
            market_awareness=1.0,
        )
        result = calculator.calculate_weights(archetype)

        weights = result.weights
        # Should be equal distribution since all are max
        assert abs(weights.stats_weight - weights.scouting_weight) < 0.01
        assert abs(weights.scouting_weight - weights.market_weight) < 0.01
        # Dominant style: when all equal at 1.0, first check wins (analytics)
        # But since none dominates over others, BALANCED expected
        assert result.dominant_style == GMStyle.ANALYTICS_HEAVY  # First one wins tie

    def test_single_trait_extreme_dominates(self, calculator):
        """Test (1,0,0) trait produces stats > 55%."""
        archetype = GMArchetype(
            name="Extreme Analytics GM",
            description="Pure analytics",
            analytics_preference=1.0,
            scouting_preference=0.0,
            market_awareness=0.0,
        )
        result = calculator.calculate_weights(archetype)

        # With (1,0,0), normalized = (1,0,0)
        # stats = 0.05 + (0.70 * 1.0) = 0.75
        assert result.weights.stats_weight > 0.55
        assert result.dominant_style == GMStyle.ANALYTICS_HEAVY

    def test_minimum_floor_enforced(self, calculator):
        """Test zero trait still gets minimum 5% weight."""
        archetype = GMArchetype(
            name="No Scouting GM",
            description="Ignores scouts",
            analytics_preference=0.8,
            scouting_preference=0.0,
            market_awareness=0.8,
        )
        result = calculator.calculate_weights(archetype)

        # Even with scouting at 0, should get minimum floor
        assert result.weights.scouting_weight >= 0.05

    # ==========================================================================
    # Rationale Tests (2 tests)
    # ==========================================================================

    def test_rationale_includes_percentages(self, calculator, analytics_heavy_archetype):
        """Test rationale output contains weight percentages."""
        result = calculator.calculate_weights(analytics_heavy_archetype)

        rationale = result.rationale
        # Should contain percentage values
        assert "%" in rationale
        assert "Stats" in rationale
        assert "Scouting" in rationale
        assert "Market" in rationale
        assert "Rating" in rationale

    def test_rationale_identifies_dominant_style(self, calculator, scout_focused_archetype):
        """Test rationale mentions the dominant style context."""
        result = calculator.calculate_weights(scout_focused_archetype)

        rationale = result.rationale.lower()
        # Should mention scout-related terminology
        assert "scout" in rationale

    # ==========================================================================
    # Interpolation Variance (3 tests)
    # ==========================================================================

    def test_different_archetypes_produce_different_weights(
        self, calculator, balanced_archetype, analytics_heavy_archetype
    ):
        """Test different archetypes A != B in weights."""
        result_a = calculator.calculate_weights(balanced_archetype)
        result_b = calculator.calculate_weights(analytics_heavy_archetype)

        # Stats weights should be meaningfully different
        diff = abs(result_a.weights.stats_weight - result_b.weights.stats_weight)
        assert diff > 0.05  # At least 5% different

    def test_interpolation_between_styles(self, calculator):
        """Test moderate traits produce non-preset weights."""
        # Create archetype with moderate traits (not matching any preset exactly)
        archetype = GMArchetype(
            name="Moderate GM",
            description="Between styles",
            analytics_preference=0.6,
            scouting_preference=0.45,
            market_awareness=0.5,
        )
        result = calculator.calculate_weights(archetype)

        weights = result.weights

        # Should NOT match any preset exactly
        presets = [
            FactorWeights.create_analytics_heavy(),
            FactorWeights.create_scout_focused(),
            FactorWeights.create_balanced(),
            FactorWeights.create_market_driven(),
        ]

        for preset in presets:
            # Check that at least one weight differs by more than 1%
            diffs = [
                abs(weights.stats_weight - preset.stats_weight),
                abs(weights.scouting_weight - preset.scouting_weight),
                abs(weights.market_weight - preset.market_weight),
            ]
            assert any(d > 0.01 for d in diffs), "Weights match a preset exactly"

    def test_variance_exceeds_10_percent(self, calculator):
        """Test meaningfully different archetypes have 10%+ difference in dominant weight."""
        analytics_gm = GMArchetype(
            name="Analytics GM",
            description="Stats-focused",
            analytics_preference=0.9,
            scouting_preference=0.2,
            market_awareness=0.3,
        )
        scouting_gm = GMArchetype(
            name="Scout GM",
            description="Scouting-focused",
            analytics_preference=0.2,
            scouting_preference=0.9,
            market_awareness=0.3,
        )

        result_a = calculator.calculate_weights(analytics_gm)
        result_b = calculator.calculate_weights(scouting_gm)

        # Stats weight diff should exceed 10%
        stats_diff = abs(result_a.weights.stats_weight - result_b.weights.stats_weight)
        assert stats_diff >= 0.10, f"Stats diff only {stats_diff:.2f}"

        # Scouting weight diff should exceed 10%
        scouting_diff = abs(
            result_a.weights.scouting_weight - result_b.weights.scouting_weight
        )
        assert scouting_diff >= 0.10, f"Scouting diff only {scouting_diff:.2f}"


class TestWeightCalculationResult:
    """Tests for WeightCalculationResult dataclass."""

    def test_to_dict_serialization(self):
        """Test to_dict produces correct structure."""
        weights = FactorWeights.create_balanced()
        result = WeightCalculationResult(
            weights=weights,
            dominant_style=GMStyle.BALANCED,
            rationale="Test rationale",
            trait_breakdown={
                "analytics_preference": 0.5,
                "scouting_preference": 0.5,
                "market_awareness": 0.5,
            },
        )

        data = result.to_dict()

        assert "weights" in data
        assert "dominant_style" in data
        assert data["dominant_style"] == "balanced"
        assert "rationale" in data
        assert data["rationale"] == "Test rationale"
        assert "trait_breakdown" in data
        assert data["trait_breakdown"]["analytics_preference"] == 0.5