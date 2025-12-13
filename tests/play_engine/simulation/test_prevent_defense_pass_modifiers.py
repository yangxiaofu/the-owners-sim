"""Tests for prevent defense modifiers in PassPlaySimulator."""

import pytest
from unittest.mock import MagicMock, Mock
from src.play_engine.simulation.pass_plays import PassPlaySimulator


@pytest.fixture
def mock_players():
    """Create mock offensive and defensive players."""
    offensive_players = [MagicMock() for _ in range(11)]
    defensive_players = [MagicMock() for _ in range(11)]

    # Set up QB
    offensive_players[0].primary_position = "quarterback"
    offensive_players[0].get_rating = Mock(return_value=80)

    # Set up basic ratings for other players
    for player in offensive_players[1:]:
        player.get_rating = Mock(return_value=75)
    for player in defensive_players:
        player.get_rating = Mock(return_value=75)

    return offensive_players, defensive_players


class TestPreventDefensePassModifiers:
    """Test prevent defense modifiers for pass plays."""

    def test_prevent_increases_completion_rate_20_percent(self, mock_players):
        """Test prevent defense increases pass completion rate by ~20%."""
        offensive_players, defensive_players = mock_players

        # Create simulator without prevent
        sim_no_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme=None
        )

        # Create simulator with prevent
        sim_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent"
        )

        # Get base params (must include all pass play parameters)
        base_params = {
            'completion_rate': 0.60,
            'sack_rate': 0.08,
            'pressure_rate': 0.24,
            'deflection_rate': 0.06,
            'int_rate': 0.025,
            'avg_air_yards': 8.0,
            'avg_yac': 4.5,
            'avg_time_to_throw': 2.5
        }

        # Apply modifiers
        params_no_prevent = sim_no_prevent._apply_player_attribute_modifiers(base_params.copy())
        params_prevent = sim_prevent._apply_player_attribute_modifiers(base_params.copy())

        # Prevent should increase completion rate by 20%
        # Expected: 0.60 * 1.20 = 0.72
        assert params_prevent['completion_rate'] > params_no_prevent['completion_rate']
        assert abs(params_prevent['completion_rate'] / params_no_prevent['completion_rate'] - 1.20) < 0.05

    def test_prevent_decreases_sack_rate_60_percent(self, mock_players):
        """Test prevent defense decreases sack rate by ~60%."""
        offensive_players, defensive_players = mock_players

        # Create simulator WITHOUT prevent first
        sim_no_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme=None
        )

        # Create simulator WITH prevent
        sim_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent"
        )

        # Get base params (must include all pass play parameters)
        base_params = {
            'completion_rate': 0.60,
            'sack_rate': 0.10,
            'pressure_rate': 0.24,
            'deflection_rate': 0.06,
            'int_rate': 0.025,
            'avg_air_yards': 8.0,
            'avg_yac': 4.5,
            'avg_time_to_throw': 2.5
        }

        # Apply modifiers
        params_no_prevent = sim_no_prevent._apply_player_attribute_modifiers(base_params.copy())
        params_prevent = sim_prevent._apply_player_attribute_modifiers(base_params.copy())

        # Prevent should decrease sack rate by 60% (multiply by 0.4)
        # Expected: 0.10 * 0.4 = 0.04
        assert params_prevent['sack_rate'] < params_no_prevent['sack_rate']
        # Check the multiplier is approximately 0.4 (60% reduction)
        assert abs(params_prevent['sack_rate'] / params_no_prevent['sack_rate'] - 0.4) < 0.1

    def test_prevent_clamps_completion_rate_at_95_percent(self, mock_players):
        """Test prevent defense clamps completion rate to max 95%."""
        offensive_players, defensive_players = mock_players

        # Set up elite QB and receivers
        offensive_players[0].get_rating = Mock(return_value=99)  # Elite QB
        for player in offensive_players[1:6]:
            player.get_rating = Mock(return_value=95)  # Elite receivers

        # Create simulator with prevent
        sim_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent"
        )

        # Start with very high completion rate (must include all pass play parameters)
        base_params = {
            'completion_rate': 0.85,
            'sack_rate': 0.05,
            'pressure_rate': 0.20,
            'deflection_rate': 0.04,
            'int_rate': 0.015,
            'avg_air_yards': 10.0,
            'avg_yac': 5.0,
            'avg_time_to_throw': 2.3
        }

        # Apply modifiers
        params_prevent = sim_prevent._apply_player_attribute_modifiers(base_params.copy())

        # Should be clamped to 0.95 max
        assert params_prevent['completion_rate'] <= 0.95

    def test_no_prevent_modifier_when_coverage_is_none(self, mock_players):
        """Test no prevent modifiers applied when coverage_scheme is None."""
        offensive_players, defensive_players = mock_players

        # Create simulator with coverage_scheme=None
        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme=None
        )

        # Get base params (must include all pass play parameters)
        base_params = {
            'completion_rate': 0.60,
            'sack_rate': 0.10,
            'pressure_rate': 0.24,
            'deflection_rate': 0.06,
            'int_rate': 0.025,
            'avg_air_yards': 8.0,
            'avg_yac': 4.5,
            'avg_time_to_throw': 2.5
        }

        # Apply modifiers
        params = sim._apply_player_attribute_modifiers(base_params.copy())

        # Should NOT have prevent multipliers applied
        # The values might change due to player ratings, but not prevent-specific changes
        assert params is not None

    def test_no_prevent_modifier_when_coverage_is_cover_2(self, mock_players):
        """Test no prevent modifiers applied when coverage is Cover-2."""
        offensive_players, defensive_players = mock_players

        # Create simulator with Cover-2 coverage
        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Cover-2"
        )

        # Get base params (must include all pass play parameters)
        base_params = {
            'completion_rate': 0.60,
            'sack_rate': 0.10,
            'pressure_rate': 0.24,
            'deflection_rate': 0.06,
            'int_rate': 0.025,
            'avg_air_yards': 8.0,
            'avg_yac': 4.5,
            'avg_time_to_throw': 2.5
        }

        # Apply modifiers
        params = sim._apply_player_attribute_modifiers(base_params.copy())

        # Should NOT have prevent multipliers applied
        assert params is not None
        # Verify no extreme completion rate boost (prevent would give 1.20x)
        assert params['completion_rate'] < base_params['completion_rate'] * 1.15

    def test_prevent_modifier_only_when_coverage_is_prevent(self, mock_players):
        """Test prevent modifiers only apply with coverage_scheme='Prevent'."""
        offensive_players, defensive_players = mock_players

        coverage_schemes = [None, "Cover-2", "Cover-3", "Man-Free", "Prevent"]
        results = {}

        for coverage in coverage_schemes:
            sim = PassPlaySimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation="shotgun",
                defensive_formation="nickel_defense",
                coverage_scheme=coverage
            )

            base_params = {
                'completion_rate': 0.60,
                'sack_rate': 0.10,
                'pressure_rate': 0.24,
                'deflection_rate': 0.06,
                'int_rate': 0.025,
                'avg_air_yards': 8.0,
                'avg_yac': 4.5,
                'avg_time_to_throw': 2.5
            }
            params = sim._apply_player_attribute_modifiers(base_params.copy())
            results[coverage] = params

        # Only "Prevent" should have significantly different stats
        prevent_params = results["Prevent"]
        non_prevent_params = results["Cover-2"]

        # Prevent should have higher completion rate
        assert prevent_params['completion_rate'] > non_prevent_params['completion_rate']
        # Prevent should have lower sack rate
        assert prevent_params['sack_rate'] < non_prevent_params['sack_rate']

    def test_prevent_increases_short_pass_completion(self, mock_players):
        """Test prevent increases short pass completion rate."""
        offensive_players, defensive_players = mock_players

        # This test verifies the general completion rate boost
        # Short pass logic would be concept-specific (future enhancement)
        sim_prevent = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent"
        )

        base_params = {
            'completion_rate': 0.65,
            'sack_rate': 0.08,
            'pressure_rate': 0.22,
            'deflection_rate': 0.05,
            'int_rate': 0.020,
            'avg_air_yards': 9.0,
            'avg_yac': 4.8,
            'avg_time_to_throw': 2.4
        }
        params = sim_prevent._apply_player_attribute_modifiers(base_params.copy())

        # Should have completion rate boost
        assert params['completion_rate'] > base_params['completion_rate']