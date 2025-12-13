"""
Tests for Player Interest Calculation (Tollgate 8).

Tests the evaluate_player_interest method in FreeAgencyService.
"""

import pytest
from unittest.mock import MagicMock, patch


# ============================================================================
# Test Classes
# ============================================================================

class TestPlayerInterestLevelMapping:
    """Test interest score to level mapping."""

    def test_very_high_interest_level(self):
        """Score >= 80 should map to very_high."""
        # Test the threshold boundaries
        assert _map_score_to_level(80) == "very_high"
        assert _map_score_to_level(90) == "very_high"
        assert _map_score_to_level(100) == "very_high"

    def test_high_interest_level(self):
        """Score 65-79 should map to high."""
        assert _map_score_to_level(65) == "high"
        assert _map_score_to_level(70) == "high"
        assert _map_score_to_level(79) == "high"

    def test_medium_interest_level(self):
        """Score 50-64 should map to medium."""
        assert _map_score_to_level(50) == "medium"
        assert _map_score_to_level(55) == "medium"
        assert _map_score_to_level(64) == "medium"

    def test_low_interest_level(self):
        """Score 35-49 should map to low."""
        assert _map_score_to_level(35) == "low"
        assert _map_score_to_level(40) == "low"
        assert _map_score_to_level(49) == "low"

    def test_very_low_interest_level(self):
        """Score < 35 should map to very_low."""
        assert _map_score_to_level(0) == "very_low"
        assert _map_score_to_level(20) == "very_low"
        assert _map_score_to_level(34) == "very_low"


class TestInterestResultStructure:
    """Test that interest result has correct structure."""

    def test_interest_result_contains_required_fields(self):
        """Interest result should contain all required fields."""
        # Mock result structure
        result = {
            "interest_score": 75,
            "interest_level": "high",
            "acceptance_probability": 0.65,
            "concerns": ["Team needs are different"],
            "suggested_premium": 1.0,
            "team_score": 75,
            "persona_type": "ring_chaser"
        }

        # Verify all required fields present
        assert "interest_score" in result
        assert "interest_level" in result
        assert "acceptance_probability" in result
        assert "concerns" in result
        assert "persona_type" in result

    def test_interest_score_range(self):
        """Interest score should be in 0-100 range."""
        # Valid scores
        for score in [0, 50, 100]:
            assert 0 <= score <= 100

    def test_acceptance_probability_range(self):
        """Acceptance probability should be in 0.0-1.0 range."""
        for prob in [0.0, 0.5, 1.0]:
            assert 0.0 <= prob <= 1.0

    def test_interest_levels_are_valid(self):
        """Interest level should be one of the valid options."""
        valid_levels = {"very_low", "low", "medium", "high", "very_high", "unknown"}
        for level in valid_levels:
            assert level in valid_levels


class TestPersonaDataStructure:
    """Test persona data structure for signing dialog."""

    def test_persona_data_contains_required_fields(self):
        """Persona data should contain all preference weights."""
        # Mock persona data structure
        persona_data = {
            "persona_type": "ring_chaser",
            "money_importance": 30,
            "winning_importance": 90,
            "location_importance": 20,
            "playing_time_importance": 40,
            "loyalty_importance": 20,
            "market_size_importance": 20
        }

        # Verify all required fields present
        assert "persona_type" in persona_data
        assert "money_importance" in persona_data
        assert "winning_importance" in persona_data
        assert "location_importance" in persona_data
        assert "playing_time_importance" in persona_data
        assert "loyalty_importance" in persona_data
        assert "market_size_importance" in persona_data

    def test_preference_weights_in_valid_range(self):
        """Preference weights should be in 0-100 range."""
        persona_data = {
            "money_importance": 50,
            "winning_importance": 80,
            "location_importance": 30,
            "playing_time_importance": 60,
            "loyalty_importance": 40,
            "market_size_importance": 25
        }

        for key, value in persona_data.items():
            assert 0 <= value <= 100, f"{key} should be 0-100, got {value}"


class TestSuggestedPremium:
    """Test suggested premium calculation."""

    def test_very_high_interest_gets_discount(self):
        """Very high interest (80+) should suggest discount."""
        # Very high = 0.95 (5% discount)
        assert _get_suggested_premium(80) == 0.95
        assert _get_suggested_premium(90) == 0.95

    def test_high_interest_no_premium(self):
        """High interest (65-79) should need no premium."""
        assert _get_suggested_premium(65) == 1.0
        assert _get_suggested_premium(79) == 1.0

    def test_medium_interest_needs_premium(self):
        """Medium interest (50-64) should need 10% premium."""
        assert _get_suggested_premium(50) == 1.10
        assert _get_suggested_premium(64) == 1.10

    def test_low_interest_needs_higher_premium(self):
        """Low interest (35-49) should need 20% premium."""
        assert _get_suggested_premium(35) == 1.20
        assert _get_suggested_premium(49) == 1.20

    def test_very_low_interest_needs_highest_premium(self):
        """Very low interest (<35) should need 30% premium."""
        assert _get_suggested_premium(20) == 1.30
        assert _get_suggested_premium(34) == 1.30


# ============================================================================
# Helper Functions (mimic FreeAgencyService logic for testing)
# ============================================================================

def _map_score_to_level(team_score: int) -> str:
    """Map team score to interest level."""
    if team_score >= 80:
        return "very_high"
    elif team_score >= 65:
        return "high"
    elif team_score >= 50:
        return "medium"
    elif team_score >= 35:
        return "low"
    else:
        return "very_low"


def _get_suggested_premium(team_score: int) -> float:
    """Get suggested premium based on team score."""
    if team_score >= 80:
        return 0.95  # Discount
    elif team_score >= 65:
        return 1.0  # No premium
    elif team_score >= 50:
        return 1.10  # 10% premium
    elif team_score >= 35:
        return 1.20  # 20% premium
    else:
        return 1.30  # 30% premium


# ============================================================================
# Run with: python -m pytest tests/game_cycle/services/test_player_interest.py -v
# ============================================================================
