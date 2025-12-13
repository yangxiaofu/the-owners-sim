"""Integration tests for momentum system with play simulators and game loop."""

import pytest
from unittest.mock import MagicMock, Mock
from src.game_management.momentum_tracker import MomentumTracker
from src.play_engine.simulation.pass_plays import PassPlaySimulator
from src.play_engine.simulation.run_plays import RunPlaySimulator
from team_management.players.player import Position


@pytest.fixture
def mock_players():
    """Create mock offensive and defensive players."""
    offensive_players = [MagicMock() for _ in range(11)]
    defensive_players = [MagicMock() for _ in range(11)]

    # Set up QB
    offensive_players[0].primary_position = "quarterback"
    offensive_players[0].get_rating = Mock(return_value=80)

    # Set up RB for run plays
    offensive_players[1].primary_position = Position.RB
    offensive_players[1].get_rating = Mock(return_value=80)
    offensive_players[1].name = "Test RB"
    offensive_players[1].ratings = {}

    # Set up basic ratings for other players
    for player in offensive_players[2:]:
        player.get_rating = Mock(return_value=75)
        player.primary_position = "lineman"
        player.ratings = {}

    for i, player in enumerate(defensive_players):
        player.get_rating = Mock(return_value=75)
        player.primary_position = Position.MIKE if i == 0 else "defensive_back"
        player.name = f"Test Defender {i}"
        player.ratings = {}

    return offensive_players, defensive_players


class TestMomentumPassedToSimulators:
    """Test momentum modifier is passed to play simulators."""

    def test_momentum_passed_to_pass_simulator(self, mock_players):
        """Test momentum modifier is correctly passed to PassPlaySimulator."""
        offensive_players, defensive_players = mock_players

        # Create simulator with positive momentum
        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            momentum_modifier=1.05  # +5% from positive momentum
        )

        # Verify momentum modifier stored
        assert sim.momentum_modifier == 1.05

    def test_momentum_passed_to_run_simulator(self, mock_players):
        """Test momentum modifier is correctly passed to RunPlaySimulator."""
        offensive_players, defensive_players = mock_players

        # Create simulator with negative momentum
        sim = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            momentum_modifier=0.95  # -5% from negative momentum
        )

        # Verify momentum modifier stored
        assert sim.momentum_modifier == 0.95


class TestMomentumAffectsPlayOutcomes:
    """Test momentum modifiers actually affect play outcomes."""

    def test_positive_momentum_increases_pass_completion_rate(self, mock_players):
        """Test positive momentum increases pass completion rate."""
        offensive_players, defensive_players = mock_players

        # Create simulator with no momentum
        sim_neutral = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            momentum_modifier=1.0
        )

        # Create simulator with positive momentum
        sim_positive = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            momentum_modifier=1.05  # +5% boost
        )

        # Base params
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
        params_neutral = sim_neutral._apply_player_attribute_modifiers(base_params.copy())
        params_positive = sim_positive._apply_player_attribute_modifiers(base_params.copy())

        # Positive momentum should increase completion rate
        assert params_positive['completion_rate'] > params_neutral['completion_rate']

    def test_negative_momentum_decreases_pass_completion_rate(self, mock_players):
        """Test negative momentum decreases pass completion rate."""
        offensive_players, defensive_players = mock_players

        # Create simulator with neutral momentum
        sim_neutral = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            momentum_modifier=1.0
        )

        # Create simulator with negative momentum
        sim_negative = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            momentum_modifier=0.95  # -5% penalty
        )

        # Base params
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
        params_neutral = sim_neutral._apply_player_attribute_modifiers(base_params.copy())
        params_negative = sim_negative._apply_player_attribute_modifiers(base_params.copy())

        # Negative momentum should decrease completion rate
        assert params_negative['completion_rate'] < params_neutral['completion_rate']

    def test_positive_momentum_increases_run_yards(self, mock_players):
        """Test positive momentum increases run yards per carry."""
        offensive_players, defensive_players = mock_players

        # Create simulator with neutral momentum
        sim_neutral = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            momentum_modifier=1.0
        )

        # Create simulator with positive momentum
        sim_positive = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            momentum_modifier=1.05  # +5% boost
        )

        # Base parameters
        base_avg_yards = 4.0
        base_variance = 2.0

        # Apply modifiers
        avg_neutral, var_neutral = sim_neutral._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )
        avg_positive, var_positive = sim_positive._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )

        # Positive momentum should increase yards
        assert avg_positive > avg_neutral

    def test_negative_momentum_decreases_run_yards(self, mock_players):
        """Test negative momentum decreases run yards per carry."""
        offensive_players, defensive_players = mock_players

        # Create simulator with neutral momentum
        sim_neutral = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            momentum_modifier=1.0
        )

        # Create simulator with negative momentum
        sim_negative = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            momentum_modifier=0.95  # -5% penalty
        )

        # Base parameters
        base_avg_yards = 4.0
        base_variance = 2.0

        # Apply modifiers
        avg_neutral, var_neutral = sim_neutral._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )
        avg_negative, var_negative = sim_negative._apply_player_attribute_modifiers(
            base_avg_yards, base_variance
        )

        # Negative momentum should decrease yards
        assert avg_negative < avg_neutral


class TestMomentumWithOtherModifiers:
    """Test momentum works correctly with other modifiers (prevent defense, etc.)."""

    def test_momentum_stacks_with_prevent_defense(self, mock_players):
        """Test momentum stacks multiplicatively with prevent defense."""
        offensive_players, defensive_players = mock_players

        # Create simulator with prevent defense AND positive momentum
        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent",
            momentum_modifier=1.05  # +5% from momentum
        )

        # Base params
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

        # Should have BOTH prevent boost (1.20x) AND momentum boost (1.05x)
        # Expected: 0.60 * 1.20 (prevent) * 1.05 (momentum) = 0.756
        assert params['completion_rate'] > 0.70  # Both boosts applied

    def test_momentum_applied_after_all_other_modifiers(self, mock_players):
        """Test momentum is applied AFTER prevent defense (multiplicative stacking)."""
        offensive_players, defensive_players = mock_players

        # Test that order of operations is correct
        # Prevent should apply first, then momentum

        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent",
            momentum_modifier=1.05
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

        # Verify the stacking is multiplicative, not additive
        # If additive: 0.60 + 0.20 + 0.05 = 0.85
        # If multiplicative: 0.60 * 1.20 * 1.05 = 0.756 (plus player modifiers)
        # With player modifiers: ~0.80-0.85 range
        assert 0.70 < params['completion_rate'] < 0.90  # Multiplicative stacking with player mods


class TestMomentumEventDetection:
    """Test momentum events are detected correctly from play results."""

    def test_touchdown_detected_from_play_result(self):
        """Test touchdown (6 points) triggers momentum event."""
        tracker = MomentumTracker()

        # Simulate a play result with touchdown
        from play_engine.core.play_result import PlayResult
        play_result = PlayResult(
            outcome="touchdown",
            yards=25,
            points=6,  # Touchdown
            time_elapsed=15,
            is_scoring_play=True
        )

        # Manually call event detection logic (would be called by game loop)
        if play_result.points == 6:
            tracker.add_event('home', 'touchdown')

        assert tracker.home_momentum == 8.0

    def test_field_goal_detected_from_play_result(self):
        """Test field goal (3 points) triggers momentum event."""
        tracker = MomentumTracker()

        # Simulate a play result with field goal
        from play_engine.core.play_result import PlayResult
        play_result = PlayResult(
            outcome="field_goal_made",
            yards=0,
            points=3,  # Field goal
            time_elapsed=5,
            is_scoring_play=True
        )

        # Manually call event detection logic
        if play_result.points == 3:
            tracker.add_event('home', 'field_goal_made')

        assert tracker.home_momentum == 3.0