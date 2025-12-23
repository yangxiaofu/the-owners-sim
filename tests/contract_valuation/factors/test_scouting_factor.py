"""
Unit tests for ScoutingFactor.

Tests attribute synthesis and scouting grade calculations.
"""

import pytest

from contract_valuation.factors.scouting_factor import ScoutingFactor
from contract_valuation.context import ValuationContext


class TestScoutingFactor:
    """Tests for ScoutingFactor valuation."""

    @pytest.fixture
    def factor(self):
        """ScoutingFactor instance."""
        return ScoutingFactor()

    def test_elite_prospect_high_potential(self, factor, default_context, young_player_data):
        """Test Age 24 with 95 potential gets premium valuation."""
        # young_player_data has potential 92
        result = factor.calculate(young_player_data, default_context)

        assert result.name == "scouting"
        assert result.breakdown["is_young"] is True
        assert result.breakdown["potential"] == 92

        # Young player should have upside factored in
        assert "upside" in result.breakdown
        assert result.breakdown["upside"] > result.breakdown["overall"]

    def test_veteran_weights_current_ability(self, factor, default_context, veteran_player_data):
        """Test Age 31+ weights current attrs at 45%."""
        result = factor.calculate(veteran_player_data, default_context)

        assert result.breakdown["is_young"] is False
        # Veteran composite should be more influenced by position grade
        assert result.breakdown["position_grade"] > 0

    def test_position_specific_attributes(self, factor, default_context, sample_qb_data):
        """Test QB arm_strength and accuracy weighted higher."""
        result = factor.calculate(sample_qb_data, default_context)

        # QB should have position_grade based on accuracy, arm_strength, etc.
        assert result.breakdown["position"] == "QB"
        assert result.breakdown["position_grade"] >= 90  # Elite QB attrs

    def test_missing_key_attributes(self, factor, default_context):
        """Test missing attrs uses overall as fallback."""
        player_data = {
            "player_id": 100,
            "name": "Missing Attrs",
            "position": "CB",
            "attributes": {
                "overall": 80,
                # Missing coverage, speed, press, etc.
            },
        }

        result = factor.calculate(player_data, default_context)

        # Should use overall as fallback for position grade
        assert result.breakdown["position_grade"] == 80
        assert result.confidence < 0.70  # Lower confidence due to missing attrs

    def test_birthdate_age_extraction(self, factor, default_context):
        """Test calculates age from YYYY-MM-DD birthdate."""
        player_data = {
            "player_id": 100,
            "name": "Birthdate Test",
            "position": "WR",
            "birthdate": "1998-06-15",
            "attributes": {
                "overall": 82,
                "speed": 90,
                "hands": 85,
                "route_running": 80,
                "release": 78,
                "potential": 85,
            },
        }

        result = factor.calculate(player_data, default_context)

        # Context is 2025, birthdate 1998 = age 27
        assert result.breakdown["age"] == 27
        assert result.breakdown["is_young"] is False

    def test_young_player_potential_boost(self, factor, default_context):
        """Test young player with high potential gets boosted AAV."""
        young_high_potential = {
            "player_id": 100,
            "name": "Young Star",
            "position": "WR",
            "age": 23,
            "attributes": {
                "overall": 75,
                "speed": 92,
                "hands": 78,
                "route_running": 72,
                "release": 70,
                "acceleration": 90,
                "strength": 68,
                "agility": 88,
                "stamina": 82,
                "awareness": 70,
                "potential": 95,  # High potential
            },
        }

        young_low_potential = {
            "player_id": 101,
            "name": "Young Average",
            "position": "WR",
            "age": 23,
            "attributes": {
                "overall": 75,
                "speed": 92,
                "hands": 78,
                "route_running": 72,
                "release": 70,
                "acceleration": 90,
                "strength": 68,
                "agility": 88,
                "stamina": 82,
                "awareness": 70,
                "potential": 78,  # Lower potential
            },
        }

        high_result = factor.calculate(young_high_potential, default_context)
        low_result = factor.calculate(young_low_potential, default_context)

        # High potential should result in higher composite and AAV
        assert high_result.breakdown["composite_grade"] > low_result.breakdown["composite_grade"]
        assert high_result.raw_value > low_result.raw_value

    def test_low_potential_veteran(self, factor, default_context):
        """Test low potential caps veteran valuation."""
        player_data = {
            "player_id": 100,
            "name": "Low Ceiling Vet",
            "position": "LB",
            "age": 30,
            "attributes": {
                "overall": 80,
                "tackling": 82,
                "coverage": 75,
                "awareness": 85,
                "speed": 78,
                "pursuit": 80,
                "strength": 80,
                "agility": 76,
                "stamina": 78,
                "discipline": 82,
                "composure": 80,
                "potential": 80,  # Low ceiling
            },
        }

        result = factor.calculate(player_data, default_context)

        # Veteran with low potential shouldn't get huge value
        assert result.breakdown["is_young"] is False
        # Quality tier expected
        assert result.breakdown["tier"] in ["starter", "quality"]

    def test_no_attributes_returns_fallback(self, factor, default_context):
        """Test empty attrs returns 0.35 confidence."""
        player_data = {
            "player_id": 100,
            "name": "No Attrs",
            "position": "CB",
            "attributes": {},
        }

        result = factor.calculate(player_data, default_context)

        assert result.confidence == 0.35
        assert result.breakdown.get("no_attributes") is True
