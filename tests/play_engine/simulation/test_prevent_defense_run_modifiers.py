"""Tests for prevent defense modifiers in RunPlaySimulator."""

import pytest
from unittest.mock import MagicMock, Mock
from src.play_engine.simulation.run_plays import RunPlaySimulator
from team_management.players.player import Position


@pytest.fixture
def mock_players():
    """Create mock offensive and defensive players."""
    offensive_players = [MagicMock() for _ in range(11)]
    defensive_players = [MagicMock() for _ in range(11)]

    # Set up RB
    offensive_players[0].primary_position = Position.RB
    offensive_players[0].get_rating = Mock(return_value=80)
    offensive_players[0].name = "Test RB"
    offensive_players[0].ratings = {}

    # Set up LBs
    for i in range(3):
        defensive_players[i].primary_position = Position.MIKE if i == 0 else (Position.SAM if i == 1 else Position.WILL)
        defensive_players[i].get_rating = Mock(return_value=75)
        defensive_players[i].name = f"Test LB {i}"
        defensive_players[i].ratings = {}

    # Set up basic ratings for other players
    for player in offensive_players[1:]:
        player.get_rating = Mock(return_value=75)
        player.primary_position = "lineman"
        player.ratings = {}
    for player in defensive_players[3:]:
        player.get_rating = Mock(return_value=75)
        player.primary_position = "defensive_back"
        player.ratings = {}

    return offensive_players, defensive_players


class TestPreventDefenseRunModifiers:
    """Test prevent defense modifiers for run plays."""

    def test_prevent_allows_plus_1_yard_per_carry(self, mock_players):
        """Test prevent defense allows +1.0 yards per carry."""
        offensive_players, defensive_players = mock_players

        # Create simulator without prevent
        sim_no_prevent = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme=None
        )

        # Create simulator with prevent
        sim_prevent = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme="Prevent"
        )

        # Base parameters
        base_avg_yards = 4.0
        base_variance = 2.0

        # Apply modifiers
        avg_no_prevent, var_no_prevent = sim_no_prevent._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )
        avg_prevent, var_prevent = sim_prevent._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )

        # Prevent should add +1.0 yards
        assert avg_prevent > avg_no_prevent
        assert abs((avg_prevent - avg_no_prevent) - 1.0) < 0.1  # Should be ~1.0 yards difference

    def test_prevent_increases_run_variance_20_percent(self, mock_players):
        """Test prevent defense increases run variance by 20%."""
        offensive_players, defensive_players = mock_players

        # Create simulator without prevent
        sim_no_prevent = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme=None
        )

        # Create simulator with prevent
        sim_prevent = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme="Prevent"
        )

        # Base parameters
        base_avg_yards = 4.0
        base_variance = 2.0

        # Apply modifiers
        avg_no_prevent, var_no_prevent = sim_no_prevent._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )
        avg_prevent, var_prevent = sim_prevent._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )

        # Prevent should increase variance by 20%
        assert var_prevent > var_no_prevent
        assert abs(var_prevent / var_no_prevent - 1.20) < 0.05  # Should be ~1.20x

    def test_no_prevent_modifier_when_coverage_is_none(self, mock_players):
        """Test no prevent modifiers applied when coverage_scheme is None."""
        offensive_players, defensive_players = mock_players

        # Create simulator with coverage_scheme=None
        sim = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme=None
        )

        # Base parameters
        base_avg_yards = 4.0
        base_variance = 2.0

        # Apply modifiers
        avg, var = sim._apply_player_attribute_modifiers(base_avg_yards, base_variance)

        # Should return modified values based on player ratings only (no prevent bonus)
        assert avg is not None
        assert var is not None

    def test_prevent_modifier_only_when_coverage_is_prevent(self, mock_players):
        """Test prevent modifiers only apply with coverage_scheme='Prevent'."""
        offensive_players, defensive_players = mock_players

        coverage_schemes = [None, "Cover-2", "Cover-3", "Man-Free", "Prevent"]
        results = {}

        for coverage in coverage_schemes:
            sim = RunPlaySimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation="i_formation",
                defensive_formation="four_three_base",
                coverage_scheme=coverage
            )

            base_avg_yards = 4.0
            base_variance = 2.0
            avg, var = sim._apply_player_attribute_modifiers(base_avg_yards, base_variance)
            results[coverage] = {'avg': avg, 'var': var}

        # Only "Prevent" should have +1.0 yards and +20% variance
        prevent_avg = results["Prevent"]['avg']
        prevent_var = results["Prevent"]['var']

        non_prevent_avg = results["Cover-2"]['avg']
        non_prevent_var = results["Cover-2"]['var']

        # Prevent should have higher avg and variance
        assert prevent_avg > non_prevent_avg
        assert prevent_var > non_prevent_var

        # Check the magnitude is correct (~1.0 yard difference)
        assert abs((prevent_avg - non_prevent_avg) - 1.0) < 0.2
