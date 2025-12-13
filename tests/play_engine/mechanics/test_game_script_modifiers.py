"""Tests for GameScriptModifiers - game script enforcement system."""

import pytest
from src.play_engine.mechanics.game_script_modifiers import GameScriptModifiers
from src.play_engine.play_calling.game_situation_analyzer import GameScript


class TestRunPassMultipliers:
    """Test run/pass adjustment multipliers."""

    def test_control_game_run_multiplier_3_5x(self):
        """Test CONTROL_GAME boosts run by 3.5x with full adherence."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=1.0
        )

        assert adjustments['run'] == 3.5
        assert adjustments['pass'] == 0.5

    def test_desperation_pass_multiplier_2_0x(self):
        """Test DESPERATION boosts pass by 2.0x with full adherence."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.DESPERATION,
            game_script_adherence=1.0
        )

        assert adjustments['run'] == pytest.approx(0.15, rel=1e-2)
        assert adjustments['pass'] == 2.0

    def test_adherence_blending_high_0_9(self):
        """Test adherence=0.9 results in near-full multiplier enforcement."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=0.9
        )

        # Formula: 1.0 + (3.5 - 1.0) * 0.9 = 1.0 + 2.5 * 0.9 = 3.25
        assert adjustments['run'] == pytest.approx(3.25, rel=1e-2)
        # Formula: 1.0 + (0.5 - 1.0) * 0.9 = 1.0 - 0.5 * 0.9 = 0.55
        assert adjustments['pass'] == pytest.approx(0.55, rel=1e-2)

    def test_adherence_blending_low_0_3(self):
        """Test adherence=0.3 results in weak multiplier enforcement."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=0.3
        )

        # Formula: 1.0 + (3.5 - 1.0) * 0.3 = 1.0 + 2.5 * 0.3 = 1.75
        assert adjustments['run'] == pytest.approx(1.75, rel=1e-2)
        # Formula: 1.0 + (0.5 - 1.0) * 0.3 = 1.0 - 0.5 * 0.3 = 0.85
        assert adjustments['pass'] == pytest.approx(0.85, rel=1e-2)

    def test_adherence_zero_returns_neutral(self):
        """Test adherence=0.0 returns neutral 1.0x multipliers."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=0.0
        )

        assert adjustments['run'] == 1.0
        assert adjustments['pass'] == 1.0

    def test_competitive_returns_neutral(self):
        """Test COMPETITIVE script returns 1.0x multipliers regardless of adherence."""
        adjustments = GameScriptModifiers.get_run_pass_adjustment(
            game_script=GameScript.COMPETITIVE,
            game_script_adherence=1.0
        )

        assert adjustments['run'] == 1.0
        assert adjustments['pass'] == 1.0


class TestFormationMultipliers:
    """Test formation adjustment multipliers."""

    def test_formation_control_game_boosts_i_formation(self):
        """Test CONTROL_GAME boosts i_formation by 2.0x."""
        adjustments = GameScriptModifiers.get_formation_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=1.0
        )

        assert adjustments['i_formation'] == 2.0
        assert adjustments['shotgun'] == 0.5
        assert adjustments['four_wide'] == 0.4

    def test_formation_desperation_boosts_shotgun(self):
        """Test DESPERATION boosts shotgun by 2.5x and four_wide by 2.0x."""
        adjustments = GameScriptModifiers.get_formation_adjustment(
            game_script=GameScript.DESPERATION,
            game_script_adherence=1.0
        )

        assert adjustments['shotgun'] == 2.5
        assert adjustments['four_wide'] == 2.0
        assert adjustments['i_formation'] == pytest.approx(0.3, rel=1e-2)

    def test_formation_blending_with_adherence_0_5(self):
        """Test formation multipliers blend correctly with adherence=0.5."""
        adjustments = GameScriptModifiers.get_formation_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=0.5
        )

        # Formula: 1.0 + (2.0 - 1.0) * 0.5 = 1.5
        assert adjustments['i_formation'] == pytest.approx(1.5, rel=1e-2)
        # Formula: 1.0 + (0.5 - 1.0) * 0.5 = 0.75
        assert adjustments['shotgun'] == pytest.approx(0.75, rel=1e-2)

    def test_competitive_returns_empty_dict(self):
        """Test COMPETITIVE script returns empty dict (no formation changes)."""
        adjustments = GameScriptModifiers.get_formation_adjustment(
            game_script=GameScript.COMPETITIVE,
            game_script_adherence=1.0
        )

        assert adjustments == {}


class TestTempoAdjustments:
    """Test tempo adjustment recommendations."""

    def test_tempo_control_game_returns_slow(self):
        """Test CONTROL_GAME returns 'slow' tempo."""
        tempo = GameScriptModifiers.get_tempo_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=1.0
        )

        assert tempo == "slow"

    def test_tempo_desperation_returns_hurry_up(self):
        """Test DESPERATION returns 'hurry_up' tempo."""
        tempo = GameScriptModifiers.get_tempo_adjustment(
            game_script=GameScript.DESPERATION,
            game_script_adherence=1.0
        )

        assert tempo == "hurry_up"

    def test_tempo_low_adherence_returns_none(self):
        """Test adherence < 0.5 returns None (ignore script tempo)."""
        tempo = GameScriptModifiers.get_tempo_adjustment(
            game_script=GameScript.CONTROL_GAME,
            game_script_adherence=0.4
        )

        assert tempo is None

    def test_tempo_high_adherence_returns_recommendation(self):
        """Test adherence >= 0.5 returns script tempo recommendation."""
        tempo = GameScriptModifiers.get_tempo_adjustment(
            game_script=GameScript.COMEBACK_MODE,
            game_script_adherence=0.6
        )

        assert tempo == "hurry_up"


class TestDefensiveResponse:
    """Test defensive response to opponent game script."""

    def test_prevent_vs_desperation_opponent(self):
        """Test prevent defense triggers vs DESPERATION opponent with high prevent_usage."""
        response = GameScriptModifiers.get_defensive_response(
            opponent_script=GameScript.DESPERATION,
            prevent_defense_usage=0.6
        )

        assert response['use_prevent'] is True
        assert response['coverage_adjustment'] == 'Prevent'
        assert response['pressure'] is False  # 3-man rush

    def test_no_prevent_low_usage_dc(self):
        """Test DC with low prevent_usage doesn't use prevent vs DESPERATION."""
        response = GameScriptModifiers.get_defensive_response(
            opponent_script=GameScript.DESPERATION,
            prevent_defense_usage=0.3
        )

        assert response['use_prevent'] is False
        assert response['coverage_adjustment'] == 'Cover-2'  # Safe zone coverage
        assert response['pressure'] is False

    def test_normal_coverage_vs_competitive(self):
        """Test normal coverage vs COMPETITIVE opponent (no special adjustments)."""
        response = GameScriptModifiers.get_defensive_response(
            opponent_script=GameScript.COMPETITIVE,
            prevent_defense_usage=0.6
        )

        assert response['use_prevent'] is False
        assert response['coverage_adjustment'] is None
        assert response['pressure'] is None

    def test_prevent_threshold_at_0_4(self):
        """Test prevent triggers at exactly 0.4 prevent_usage threshold."""
        # Just below threshold - should not trigger
        response_below = GameScriptModifiers.get_defensive_response(
            opponent_script=GameScript.DESPERATION,
            prevent_defense_usage=0.4
        )
        assert response_below['use_prevent'] is False

        # Just above threshold - should trigger
        response_above = GameScriptModifiers.get_defensive_response(
            opponent_script=GameScript.DESPERATION,
            prevent_defense_usage=0.41
        )
        assert response_above['use_prevent'] is True
