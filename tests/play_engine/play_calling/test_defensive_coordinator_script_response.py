"""Tests for DefensiveCoordinator game script response."""

import pytest
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


class TestDefensiveScriptResponse:
    """Test defensive coordinator response to opponent game script."""

    def test_prevent_vs_desperation_opponent(self, high_prevent_dc):
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

    def test_no_prevent_low_usage_dc(self, low_prevent_dc):
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
        assert coverage_info['primary_coverage'] == 'Cover-2'

    def test_opponent_script_inference_correct(self, high_prevent_dc):
        """Test _infer_opponent_script correctly flips score differential."""
        # When we're up by 21, opponent is down by 21 (DESPERATION)
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=21,  # We're winning
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.CONTROL_GAME,
            momentum='positive'
        )

        opponent_script = high_prevent_dc._infer_opponent_script(game_context)

        # Opponent should be in DESPERATION (down by 21 in 4th quarter late)
        assert opponent_script == GameScript.DESPERATION

    def test_normal_coverage_vs_competitive(self, high_prevent_dc):
        """Test normal coverage vs COMPETITIVE opponent (tied game)."""
        # Tied game - both teams in COMPETITIVE script
        game_context = GameContext(
            quarter=3,
            time_remaining=900,
            score_differential=0,  # Tied
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.THIRD_QUARTER,
            game_script=GameScript.COMPETITIVE,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        formation = UnifiedDefensiveFormation.FOUR_THREE_BASE
        coverage_info = high_prevent_dc.get_coverage_scheme(formation, 'first_down', context)

        # Should use normal coverage, not prevent
        assert coverage_info['primary_coverage'] != 'Prevent'

    def test_opponent_control_game_when_we_trail(self, high_prevent_dc):
        """Test opponent inferred as CONTROL_GAME when we're losing."""
        # When we're down by 14, opponent is up by 14 (CONTROL_GAME/PROTECT_LEAD)
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=-14,  # We're losing
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.COMEBACK_MODE,
            momentum='negative'
        )

        opponent_script = high_prevent_dc._infer_opponent_script(game_context)

        # Opponent should be in PROTECT_LEAD or CONTROL_GAME
        assert opponent_script in [GameScript.PROTECT_LEAD, GameScript.CONTROL_GAME]

    def test_backward_compatible_without_game_context(self, high_prevent_dc):
        """Test DC works without game_context (backward compatible)."""
        # No game_context in context dict
        context = {}
        formation = UnifiedDefensiveFormation.FOUR_THREE_BASE
        coverage_info = high_prevent_dc.get_coverage_scheme(formation, 'first_down', context)

        # Should still return valid coverage based on philosophy alone
        assert 'primary_coverage' in coverage_info
        assert 'send_pressure' in coverage_info
