"""Tests for two-minute drill tempo and spike decisions."""

import pytest
from src.play_engine.play_calling.offensive_coordinator import OffensiveCoordinator, OffensivePhilosophy, SituationalCalling


@pytest.fixture
def coordinator():
    """Create default OffensiveCoordinator."""
    philosophy = OffensivePhilosophy(
        run_preference=0.5,
        pass_preference=0.5,
        deep_ball_tendency=0.5,
        no_huddle_usage=0.3,
        play_action_frequency=0.3
    )
    situational = SituationalCalling(
        red_zone_efficiency=0.7,
        two_minute_drill_efficiency=0.7,
        third_down_aggression=0.6
    )
    return OffensiveCoordinator(
        name="Test OC",
        philosophy=philosophy,
        situational_calling=situational
    )


class TestTwoMinuteTempo:
    """Test tempo management in two-minute drill."""

    def test_two_minute_tempo_when_trailing(self, coordinator):
        """Test returns 'two_minute' tempo when trailing in final 2 min."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': -3
        }

        tempo = coordinator.get_offensive_tempo('two_minute', context)
        assert tempo == "two_minute"

    def test_hurry_up_tempo_when_tied(self, coordinator):
        """Test returns 'hurry_up' tempo when tied in final 2 min."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': 0
        }

        tempo = coordinator.get_offensive_tempo('two_minute', context)
        assert tempo == "hurry_up"

    def test_normal_tempo_when_winning(self, coordinator):
        """Test returns 'normal' tempo when winning in final 2 min."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': 3
        }

        tempo = coordinator.get_offensive_tempo('two_minute', context)
        assert tempo == "normal"


class TestSpikeDecisions:
    """Test spike play decision logic."""

    def test_spike_when_trailing_no_timeouts(self, coordinator):
        """Test spikes when trailing with no timeouts."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': -3,
            'down': 2,
            'clock_running': True,
            'timeouts_remaining': 0
        }

        assert coordinator.should_spike(context) is True

    def test_no_spike_when_have_timeouts(self, coordinator):
        """Test doesn't spike when timeouts available."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': -3,
            'down': 2,
            'clock_running': True,
            'timeouts_remaining': 2
        }

        assert coordinator.should_spike(context) is False

    def test_no_spike_on_fourth_down(self, coordinator):
        """Test never spikes on 4th down."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': -3,
            'down': 4,
            'clock_running': True,
            'timeouts_remaining': 0
        }

        assert coordinator.should_spike(context) is False

    def test_no_spike_when_winning(self, coordinator):
        """Test doesn't spike when winning."""
        context = {
            'time_remaining': 90,
            'quarter': 4,
            'score_differential': 3,
            'down': 2,
            'clock_running': True,
            'timeouts_remaining': 0
        }

        assert coordinator.should_spike(context) is False