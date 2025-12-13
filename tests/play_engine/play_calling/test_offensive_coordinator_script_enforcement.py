"""Tests for OffensiveCoordinator game script enforcement."""

import pytest
from src.play_engine.play_calling.offensive_coordinator import (
    OffensiveCoordinator,
    OffensivePhilosophy,
    SituationalCalling
)
from src.play_engine.play_calling.game_situation_analyzer import (
    GameScript,
    GameContext,
    GamePhase
)


@pytest.fixture
def high_adherence_coordinator():
    """Create OC with high game_script_adherence (0.9)."""
    return OffensiveCoordinator(
        name="High Adherence OC",
        game_script_adherence=0.9,
        philosophy=OffensivePhilosophy(),
        situational_calling=SituationalCalling()
    )


@pytest.fixture
def low_adherence_coordinator():
    """Create OC with low game_script_adherence (0.3)."""
    return OffensiveCoordinator(
        name="Low Adherence OC",
        game_script_adherence=0.3,
        philosophy=OffensivePhilosophy(),
        situational_calling=SituationalCalling()
    )


class TestPlayConceptScriptEnforcement:
    """Test game script enforcement in play concept preferences."""

    def test_control_game_increases_run_concepts(self, high_adherence_coordinator):
        """Test CONTROL_GAME increases run concept weights."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,  # Up by 2 TDs
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        concepts = high_adherence_coordinator.get_play_concept_preference('first_down', context)

        # Run concepts should be boosted significantly (3.5x with adherence=0.9)
        run_concepts = ['power', 'sweep', 'off_tackle']
        pass_concepts = ['slants', 'quick_out', 'comeback']

        # Get average weights
        avg_run_weight = sum(concepts.get(c, 0) for c in run_concepts) / len(run_concepts)
        avg_pass_weight = sum(concepts.get(c, 0) for c in pass_concepts) / len(pass_concepts)

        # Run concepts should have higher weight than pass concepts
        assert avg_run_weight > avg_pass_weight

    def test_desperation_increases_pass_concepts(self, high_adherence_coordinator):
        """Test DESPERATION increases pass concept weights."""
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=-21,  # Down by 3 TDs
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.DESPERATION,
            momentum='negative'
        )

        context = {'game_context': game_context}
        concepts = high_adherence_coordinator.get_play_concept_preference('first_down', context)

        # Pass concepts should be boosted significantly (2.0x with adherence=0.9)
        run_concepts = ['power', 'sweep', 'off_tackle']
        pass_concepts = ['slants', 'quick_out', 'comeback', 'four_verticals']

        avg_run_weight = sum(concepts.get(c, 0) for c in run_concepts) / len(run_concepts)
        avg_pass_weight = sum(concepts.get(c, 0) for c in pass_concepts) / len(pass_concepts)

        # Pass concepts should have much higher weight than run concepts
        assert avg_pass_weight > avg_run_weight * 2

    def test_high_adherence_strict_enforcement(self, high_adherence_coordinator):
        """Test high adherence (0.9) enforces script strictly."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        concepts = high_adherence_coordinator.get_play_concept_preference('first_down', context)

        # With adherence=0.9, run multiplier should be ~3.25 (1.0 + (3.5-1.0)*0.9)
        # Power should have base weight 0.4 * 3.25 = 1.3
        assert concepts.get('power', 0) >= 1.0  # At least 1.0 after multiplier

    def test_low_adherence_flexible_enforcement(self, low_adherence_coordinator):
        """Test low adherence (0.3) applies script weakly."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        concepts = low_adherence_coordinator.get_play_concept_preference('first_down', context)

        # With adherence=0.3, run multiplier should be ~1.75 (1.0 + (3.5-1.0)*0.3)
        # Power should have base weight 0.4 * 1.75 = 0.7
        assert concepts.get('power', 0) <= 1.0  # Less dramatic boost

    def test_competitive_no_script_changes(self, high_adherence_coordinator):
        """Test COMPETITIVE script applies neutral multipliers."""
        game_context = GameContext(
            quarter=3,
            time_remaining=900,
            score_differential=0,  # Tied game
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.THIRD_QUARTER,
            game_script=GameScript.COMPETITIVE,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        concepts = high_adherence_coordinator.get_play_concept_preference('first_down', context)

        # COMPETITIVE applies 1.0x multipliers, so weights should match base philosophy
        # Just verify no errors and concepts exist
        assert 'power' in concepts
        assert 'slants' in concepts

    def test_no_game_context_backward_compatible(self, high_adherence_coordinator):
        """Test coordinator works without game_context (backward compatible)."""
        # No game_context in context dict
        context = {}
        concepts = high_adherence_coordinator.get_play_concept_preference('first_down', context)

        # Should still return valid concepts based on philosophy alone
        assert len(concepts) > 0
        assert 'power' in concepts
        assert 'slants' in concepts


class TestFormationScriptEnforcement:
    """Test game script enforcement in formation preferences."""

    def test_control_game_boosts_i_formation_2x(self, high_adherence_coordinator):
        """Test CONTROL_GAME boosts i_formation significantly."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context}
        formations = high_adherence_coordinator.get_formation_preference('first_down', context)

        # With adherence=0.9, i_formation gets ~1.9x multiplier (1.0 + (2.0-1.0)*0.9)
        # i_formation should have highest or near-highest weight
        assert formations.get('i_formation', 0) > formations.get('shotgun', 0)

    def test_desperation_boosts_shotgun_2_5x(self, high_adherence_coordinator):
        """Test DESPERATION boosts shotgun and four_wide."""
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=-21,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.DESPERATION,
            momentum='negative'
        )

        context = {'game_context': game_context}
        formations = high_adherence_coordinator.get_formation_preference('first_down', context)

        # Shotgun and four_wide should dominate
        assert formations.get('shotgun', 0) > formations.get('i_formation', 0)
        assert formations.get('four_wide', 0) > formations.get('i_formation', 0)


class TestTempoScriptEnforcement:
    """Test game script enforcement in tempo selection."""

    def test_script_tempo_control_game_slow(self, high_adherence_coordinator):
        """Test CONTROL_GAME returns 'slow' tempo."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context, 'quarter': 4, 'time_remaining': 600, 'score_differential': 14}
        tempo = high_adherence_coordinator.get_offensive_tempo('first_down', context)

        assert tempo == "slow"

    def test_script_tempo_desperation_hurry_up(self, high_adherence_coordinator):
        """Test DESPERATION returns 'hurry_up' tempo."""
        game_context = GameContext(
            quarter=4,
            time_remaining=300,
            score_differential=-21,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_LATE,
            game_script=GameScript.DESPERATION,
            momentum='negative'
        )

        context = {'game_context': game_context, 'quarter': 4, 'time_remaining': 300, 'score_differential': -21}
        tempo = high_adherence_coordinator.get_offensive_tempo('first_down', context)

        assert tempo == "hurry_up"

    def test_low_adherence_ignores_script_tempo(self, low_adherence_coordinator):
        """Test low adherence (<0.5) ignores script tempo."""
        game_context = GameContext(
            quarter=4,
            time_remaining=600,
            score_differential=14,
            field_position=50,
            down=1,
            yards_to_go=10,
            game_phase=GamePhase.FOURTH_QUARTER_EARLY,
            game_script=GameScript.CONTROL_GAME,
            momentum='neutral'
        )

        context = {'game_context': game_context, 'quarter': 4, 'time_remaining': 600, 'score_differential': 14}
        tempo = low_adherence_coordinator.get_offensive_tempo('first_down', context)

        # Adherence < 0.5 returns None from script, falls back to normal
        assert tempo == "normal"
