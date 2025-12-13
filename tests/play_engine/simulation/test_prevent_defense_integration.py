"""Integration tests for prevent defense system."""

import pytest
from unittest.mock import MagicMock, Mock, patch
from src.play_engine.play_calling.defensive_coordinator import (
    DefensiveCoordinator,
    DefensivePhilosophy,
    SituationalDefense
)
from src.play_engine.play_calling.game_situation_analyzer import (
    GameScript,
    GameContext,
    GamePhase
)
from src.play_engine.mechanics.unified_formations import UnifiedDefensiveFormation
from src.play_engine.simulation.pass_plays import PassPlaySimulator
from src.play_engine.simulation.run_plays import RunPlaySimulator


@pytest.fixture
def high_prevent_dc():
    """Create DC with high prevent_defense_usage (0.6)."""
    return DefensiveCoordinator(
        name="Prevent-Heavy DC",
        defensive_situational=SituationalDefense(
            prevent_defense_usage=0.6
        ),
        philosophy=DefensivePhilosophy()
    )


@pytest.fixture
def low_prevent_dc():
    """Create DC with low prevent_defense_usage (0.2)."""
    return DefensiveCoordinator(
        name="No-Prevent DC",
        defensive_situational=SituationalDefense(
            prevent_defense_usage=0.2
        ),
        philosophy=DefensivePhilosophy()
    )


@pytest.fixture
def mock_players():
    """Create mock offensive and defensive players."""
    offensive_players = [MagicMock() for _ in range(11)]
    defensive_players = [MagicMock() for _ in range(11)]

    # Set up basic ratings
    for player in offensive_players:
        player.get_rating = Mock(return_value=75)
        player.primary_position = "lineman"
    for player in defensive_players:
        player.get_rating = Mock(return_value=75)
        player.primary_position = "linebacker"

    return offensive_players, defensive_players


class TestPreventDefenseIntegration:
    """Integration tests for prevent defense system."""

    def test_prevent_triggers_vs_desperation_opponent(self, high_prevent_dc):
        """Test prevent defense triggers vs DESPERATION opponent."""
        # Create game context where WE are winning (opponent is in DESPERATION)
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=21,  # We're up by 21 (opponent is desperate)
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.CONTROL_GAME,  # Our script
            momentum='positive'
        )

        context = {'game_context': game_context}
        formation = UnifiedDefensiveFormation.NICKEL_DEFENSE
        coverage_info = high_prevent_dc.get_coverage_scheme(formation, 'first_down', context)

        # Should trigger prevent defense
        assert coverage_info['primary_coverage'] == 'Prevent'
        assert coverage_info['send_pressure'] is False  # No pressure in prevent

    def test_dc_low_prevent_usage_never_uses_prevent(self, low_prevent_dc):
        """Test DC with low prevent_usage doesn't use prevent vs DESPERATION."""
        # Same scenario as above but with low prevent_usage DC
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=21,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.CONTROL_GAME,
            momentum='positive'
        )

        context = {'game_context': game_context}
        formation = UnifiedDefensiveFormation.NICKEL_DEFENSE
        coverage_info = low_prevent_dc.get_coverage_scheme(formation, 'first_down', context)

        # Should use Cover-2 instead of prevent
        assert coverage_info['primary_coverage'] != 'Prevent'

    def test_prevent_coverage_passed_to_pass_simulator(self, mock_players):
        """Test coverage_scheme is correctly passed to PassPlaySimulator."""
        offensive_players, defensive_players = mock_players

        # Create simulator with Prevent coverage
        sim = PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="shotgun",
            defensive_formation="nickel_defense",
            coverage_scheme="Prevent"
        )

        # Verify coverage_scheme is stored
        assert sim.coverage_scheme == "Prevent"

        # Verify modifiers are applied
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

        # Should have prevent modifiers applied
        assert params['completion_rate'] > base_params['completion_rate']
        assert params['sack_rate'] < base_params['sack_rate']

    def test_prevent_coverage_passed_to_run_simulator(self, mock_players):
        """Test coverage_scheme is correctly passed to RunPlaySimulator."""
        offensive_players, defensive_players = mock_players

        # Set up RB
        from team_management.players.player import Position
        offensive_players[0].primary_position = Position.RB
        offensive_players[0].name = "Test RB"
        offensive_players[0].ratings = {}

        # Set up LBs
        for i in range(3):
            defensive_players[i].primary_position = Position.MIKE if i == 0 else (Position.SAM if i == 1 else Position.WILL)
            defensive_players[i].name = f"Test LB {i}"
            defensive_players[i].ratings = {}

        # Create simulator with Prevent coverage
        sim = RunPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="i_formation",
            defensive_formation="four_three_base",
            coverage_scheme="Prevent"
        )

        # Verify coverage_scheme is stored
        assert sim.coverage_scheme == "Prevent"

        # Verify modifiers are applied
        base_avg_yards = 4.0
        base_variance = 2.0
        avg, var = sim._apply_player_attribute_modifiers(base_avg_yards, base_variance)

        # Should have +1.0 yards from prevent
        assert avg > base_avg_yards + 0.5  # At least 0.5 yards more (accounting for other modifiers)
