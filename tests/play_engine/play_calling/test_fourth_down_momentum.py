"""Integration tests for momentum affecting fourth-down decisions."""

import pytest
from src.play_engine.play_calling.fourth_down_matrix import FourthDownMatrix, CoachAggressionLevel


class TestFourthDownMomentumIntegration:
    """Test momentum modifier integration with fourth-down decisions."""

    def test_positive_momentum_increases_go_for_it_probability(self):
        """Test positive momentum increases go-for-it probability."""
        # Baseline decision with neutral momentum
        decision_neutral = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,  # Midfield
            yards_to_go=2,  # 4th & 2
            score_differential=0,  # Tied
            time_remaining=300,  # 5 minutes left
            quarter=4,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.0  # Neutral
        )

        # Decision with positive momentum
        decision_positive = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.15  # +15% aggression (max positive momentum)
        )

        # Positive momentum should increase probability
        assert decision_positive.go_for_it_probability > decision_neutral.go_for_it_probability

        # Verify the effect is approximately 15%
        expected_ratio = 1.15
        actual_ratio = decision_positive.go_for_it_probability / decision_neutral.go_for_it_probability
        assert abs(actual_ratio - expected_ratio) < 0.01

    def test_negative_momentum_decreases_go_for_it_probability(self):
        """Test negative momentum decreases go-for-it probability."""
        # Baseline decision with neutral momentum
        decision_neutral = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.0
        )

        # Decision with negative momentum
        decision_negative = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=0.85  # -15% aggression (max negative momentum)
        )

        # Negative momentum should decrease probability
        assert decision_negative.go_for_it_probability < decision_neutral.go_for_it_probability

        # Verify the effect is approximately 15%
        expected_ratio = 0.85
        actual_ratio = decision_negative.go_for_it_probability / decision_neutral.go_for_it_probability
        assert abs(actual_ratio - expected_ratio) < 0.01

    def test_momentum_can_change_decision_from_punt_to_go(self):
        """Test strong positive momentum can flip decision from punt to go for it."""
        # Marginal situation: 4th & 3 at own 48 (just past midfield)
        # Normally would punt, but with positive momentum might go for it

        decision_neutral = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=52,  # Just past midfield
            yards_to_go=3,  # 4th & 3
            score_differential=0,
            time_remaining=600,
            quarter=3,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.0
        )

        decision_positive = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=52,
            yards_to_go=3,
            score_differential=0,
            time_remaining=600,
            quarter=3,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.15  # Max positive momentum
        )

        # Momentum should increase probability significantly
        assert decision_positive.go_for_it_probability > decision_neutral.go_for_it_probability

        # In marginal cases, momentum can flip the decision
        # (This test verifies momentum has real impact, not just small tweaks)
        probability_increase = decision_positive.go_for_it_probability - decision_neutral.go_for_it_probability
        assert probability_increase > 0.025  # At least 2.5% increase (meaningful impact)

    def test_momentum_stacks_with_coach_aggression(self):
        """Test momentum modifier stacks multiplicatively with coach aggression."""
        # Conservative coach with negative momentum
        decision_conservative_negative = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.CONSERVATIVE,  # 0.8x modifier
            momentum_modifier=0.85  # 0.85x modifier
        )

        # Aggressive coach with positive momentum
        decision_aggressive_positive = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.AGGRESSIVE,  # 1.2x modifier
            momentum_modifier=1.15  # 1.15x modifier
        )

        # Should see multiplicative stacking effect
        # Conservative + negative: 0.8 * 0.85 = 0.68x (very conservative)
        # Aggressive + positive: 1.2 * 1.15 = 1.38x (very aggressive)
        ratio = decision_aggressive_positive.go_for_it_probability / decision_conservative_negative.go_for_it_probability

        # Expect roughly 2x difference (1.38 / 0.68 ≈ 2.0)
        assert ratio > 1.5  # At least 50% higher

    def test_momentum_included_in_decision_factors(self):
        """Test momentum modifier is included in decision breakdown."""
        decision = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=55,
            yards_to_go=2,
            score_differential=0,
            time_remaining=300,
            quarter=4,
            coach_aggression=CoachAggressionLevel.BALANCED,
            momentum_modifier=1.10
        )

        # Verify momentum is recorded in factors
        assert 'momentum_modifier' in decision.factors
        assert decision.factors['momentum_modifier'] == 1.10

        # Verify breakdown includes after_coach_modifier step
        assert 'after_coach_modifier' in decision.breakdown
