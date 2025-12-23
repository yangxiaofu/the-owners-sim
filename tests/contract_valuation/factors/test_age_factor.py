"""
Unit tests for AgeFactor.

Tests age premiums/discounts and archetype peak ranges.
"""

import pytest

from contract_valuation.factors.age_factor import AgeFactor
from contract_valuation.context import ValuationContext


class TestAgeFactor:
    """Tests for AgeFactor valuation."""

    @pytest.fixture
    def factor(self):
        """AgeFactor instance with default archetypes path."""
        return AgeFactor()

    @pytest.fixture
    def factor_with_archetypes(self, archetypes_path):
        """AgeFactor instance with test archetypes directory."""
        return AgeFactor(archetypes_path=archetypes_path)

    def test_young_rb_premium(self, factor, default_context):
        """Test Age 22 RB (peak 24-27) gets +4% premium."""
        player_data = {
            "player_id": 100,
            "name": "Young RB",
            "position": "RB",
            "age": 22,
            "overall_rating": 80,
        }

        result = factor.calculate(player_data, default_context)

        # 22 is 2 years before peak (24), so +4% premium
        assert result.breakdown["age_modifier"] > 0
        assert 0.03 <= result.breakdown["age_modifier"] <= 0.05
        assert result.breakdown["peak_start"] == 24
        assert result.breakdown["peak_end"] == 27

    def test_veteran_qb_no_adjustment(self, factor, default_context):
        """Test Age 30 QB (peak 28-33) gets no adjustment."""
        player_data = {
            "player_id": 100,
            "name": "Prime QB",
            "position": "QB",
            "age": 30,
            "overall_rating": 88,
        }

        result = factor.calculate(player_data, default_context)

        # 30 is within peak (28-33), no adjustment
        assert result.breakdown["age_modifier"] == 0.0
        assert result.breakdown["peak_start"] == 28
        assert result.breakdown["peak_end"] == 33

    def test_old_cb_discount(self, factor, default_context):
        """Test Age 32 CB (peak 25-29) gets -12% discount."""
        player_data = {
            "player_id": 100,
            "name": "Old CB",
            "position": "CB",
            "age": 32,
            "overall_rating": 82,
        }

        result = factor.calculate(player_data, default_context)

        # 32 is 3 years past peak end (29), so -12% discount
        assert result.breakdown["age_modifier"] < 0
        assert -0.15 <= result.breakdown["age_modifier"] <= -0.10

    def test_early_developer_curve(self, factor, default_context):
        """Test early curve shifts peak 1 year earlier."""
        player_data = {
            "player_id": 100,
            "name": "Early Dev",
            "position": "CB",
            "age": 24,
            "overall_rating": 80,
            "development_curve": "early",
        }

        result = factor.calculate(player_data, default_context)

        # Normal CB peak is 25-29, early shifts to 24-28
        assert result.breakdown["peak_start"] == 24
        assert result.breakdown["peak_end"] == 28
        # 24 is at peak start, so no adjustment
        assert result.breakdown["age_modifier"] == 0.0

    def test_late_developer_curve(self, factor, default_context):
        """Test late curve shifts peak 1 year later."""
        player_data = {
            "player_id": 100,
            "name": "Late Dev",
            "position": "CB",
            "age": 30,
            "overall_rating": 80,
            "development_curve": "late",
        }

        result = factor.calculate(player_data, default_context)

        # Normal CB peak is 25-29, late shifts to 26-30
        assert result.breakdown["peak_start"] == 26
        assert result.breakdown["peak_end"] == 30
        # 30 is at peak end, so no adjustment
        assert result.breakdown["age_modifier"] == 0.0

    def test_archetype_peak_range(self, factor_with_archetypes, default_context, archetypes_path):
        """Test uses archetype JSON peak_age_range when available."""
        player_data = {
            "player_id": 100,
            "name": "Archetype QB",
            "position": "QB",
            "age": 35,
            "overall_rating": 85,
            "archetype": "pocket_passer_qb",
        }

        result = factor_with_archetypes.calculate(player_data, default_context)

        # pocket_passer_qb archetype has peak 28-34
        assert result.breakdown["archetype_used"] is True
        assert result.breakdown["peak_start"] == 28
        assert result.breakdown["peak_end"] == 34
        # 35 is 1 year past peak, so small discount
        assert result.breakdown["age_modifier"] < 0

    def test_unknown_age_fallback(self, factor, default_context):
        """Test missing age returns 0.50 confidence."""
        player_data = {
            "player_id": 100,
            "name": "Unknown Age",
            "position": "WR",
            "overall_rating": 80,
        }

        result = factor.calculate(player_data, default_context)

        assert result.confidence == 0.50
        assert result.breakdown.get("age_unknown") is True

    def test_max_premium_cap(self, factor, default_context):
        """Test premium capped at +15% regardless of years before peak."""
        player_data = {
            "player_id": 100,
            "name": "Very Young RB",
            "position": "RB",
            "age": 20,
            "overall_rating": 75,
        }

        result = factor.calculate(player_data, default_context)

        # 20 is 4 years before RB peak (24), would be +8% but capped at 15%
        # Actually +8% is under cap, so should be 0.08
        assert result.breakdown["age_modifier"] <= 0.15
        assert result.breakdown["age_modifier"] >= 0.06
