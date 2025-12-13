"""Tests for HeadCoach timeout decisions."""

import pytest
from src.play_engine.play_calling.head_coach import HeadCoach, GameManagementTraits, TimeoutDecision


@pytest.fixture
def smart_coach():
    """Create coach with high timeout intelligence."""
    return HeadCoach(
        name="Smart Coach",
        game_management=GameManagementTraits(timeout_usage_intelligence=0.9)
    )


@pytest.fixture
def average_coach():
    """Create coach with moderate timeout intelligence."""
    return HeadCoach(
        name="Average Coach",
        game_management=GameManagementTraits(timeout_usage_intelligence=0.5)
    )


class TestTimeoutDecisions:
    """Test timeout decision logic."""

    def test_no_timeout_when_none_remaining(self, smart_coach):
        """Test returns False when no timeouts left."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=0,
            time_remaining=120,
            quarter=4,
            score_differential=-3
        )

        assert decision.should_use_timeout is False
        assert decision.confidence == 1.0
        assert "No timeouts remaining" in decision.reasoning

    def test_use_timeout_two_minute_drill_trailing(self, smart_coach):
        """Test uses timeout in two-minute drill when trailing."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=2,
            time_remaining=90,  # 1:30 left
            quarter=4,
            score_differential=-3,  # Down by 3
            clock_running=True,
            possession=True
        )

        assert decision.should_use_timeout is True
        assert decision.urgency_level > 0.8
        assert decision.timeout_type == "clock_stop"

    def test_preserve_timeout_when_winning_late(self, smart_coach):
        """Test doesn't use timeout when winning in final 2 minutes."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=3,
            time_remaining=90,
            quarter=4,
            score_differential=3,  # Winning by 3
            clock_running=True,
            possession=True
        )

        assert decision.should_use_timeout is False
        assert "Preserve timeouts" in decision.reasoning

    def test_use_timeout_end_of_half(self, smart_coach):
        """Test uses timeout at end of half (use it or lose it)."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=1,
            time_remaining=25,  # 25 seconds left in half
            quarter=2,
            score_differential=0,
            clock_running=True
        )

        assert decision.should_use_timeout is True
        assert "End of half" in decision.reasoning

    def test_last_timeout_preservation(self, smart_coach):
        """Test smart coach preserves last timeout until final minute."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=1,
            time_remaining=90,  # 1:30 left (not final minute)
            quarter=4,
            score_differential=-3,
            clock_running=True,
            possession=True
        )

        # Smart coach waits for final minute with last timeout
        assert decision.should_use_timeout is False

    def test_last_timeout_final_minute(self, smart_coach):
        """Test uses last timeout in final minute when trailing."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=1,
            time_remaining=45,  # Final minute
            quarter=4,
            score_differential=-3,
            clock_running=True,
            possession=True
        )

        assert decision.should_use_timeout is True
        assert decision.urgency_level == 1.0

    def test_multiple_timeouts_aggressive_usage(self, smart_coach):
        """Test uses timeouts aggressively when multiple available."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=3,
            time_remaining=90,
            quarter=4,
            score_differential=-7,  # Down by 7
            clock_running=True,
            possession=True
        )

        assert decision.should_use_timeout is True
        assert decision.confidence >= 0.7

    def test_no_timeout_when_clock_stopped(self, smart_coach):
        """Test doesn't use timeout when clock already stopped."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=3,
            time_remaining=90,
            quarter=4,
            score_differential=-3,
            clock_running=False,  # Clock already stopped
            possession=True
        )

        # Clock already stopped, no need for timeout
        assert decision.should_use_timeout is False

    def test_defensive_timeout_consideration(self, smart_coach):
        """Test defensive timeout consideration in close games."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=2,
            time_remaining=300,  # 5 minutes left
            quarter=4,
            score_differential=-3,  # Close game
            clock_running=True,
            possession=False  # On defense
        )

        # This is a strategic consideration, not an immediate timeout
        assert decision.timeout_type in ["regroup", "none"]

    def test_integration_with_get_game_management_decision(self, smart_coach):
        """Test timeout decision integrates with get_game_management_decision."""
        context = {
            'timeouts_remaining': 2,
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': -3,
            'clock_running': True,
            'possession': True
        }

        decisions = smart_coach.get_game_management_decision('timeout_decision', context)

        assert 'timeout' in decisions
        assert decisions['timeout']['call_timeout'] is True
        assert 'confidence' in decisions['timeout']
        assert 'reasoning' in decisions['timeout']

    def test_end_of_quarter_four_timeout_usage(self, smart_coach):
        """Test uses timeout at end of Q4 when trailing."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=2,
            time_remaining=20,
            quarter=4,
            score_differential=-3,
            clock_running=True,
            possession=True
        )

        assert decision.should_use_timeout is True
        assert decision.urgency_level >= 0.8

    def test_tied_game_timeout_strategy(self, smart_coach):
        """Test timeout strategy in tied game."""
        decision = smart_coach.should_call_timeout(
            timeouts_remaining=2,
            time_remaining=90,
            quarter=4,
            score_differential=0,  # Tied
            clock_running=True,
            possession=True
        )

        # In tied game in final 2 minutes, should manage clock
        # Behavior depends on if it's treated as "trailing" (it shouldn't be)
        assert decision.should_use_timeout is False or decision.confidence < 0.9
