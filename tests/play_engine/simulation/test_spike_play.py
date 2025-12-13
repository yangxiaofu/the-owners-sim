"""Tests for spike play simulation."""

import pytest
from src.play_engine.simulation.spike_play import SpikePlaySimulator


class TestSpikePlaySimulator:
    """Test spike play functionality."""

    @pytest.fixture
    def simulator(self):
        return SpikePlaySimulator()

    def test_spike_returns_zero_yards(self, simulator):
        """Test spike play gains zero yards."""
        result = simulator.simulate_spike()
        assert result.yards == 0

    def test_spike_has_correct_outcome(self, simulator):
        """Test spike has 'spike' outcome type."""
        result = simulator.simulate_spike()
        assert result.outcome == "spike"

    def test_spike_time_elapsed(self, simulator):
        """Test spike takes ~3 seconds."""
        result = simulator.simulate_spike()
        assert result.time_elapsed == 3.0

    def test_spike_not_scoring_play(self, simulator):
        """Test spike is not a scoring play."""
        result = simulator.simulate_spike()
        assert result.is_scoring_play is False

    def test_cannot_spike_on_fourth_down(self, simulator):
        """Test spike is illegal on 4th down."""
        assert simulator.can_spike(down=4, quarter=4) is False

    def test_can_spike_on_first_three_downs(self, simulator):
        """Test spike is legal on downs 1-3."""
        assert simulator.can_spike(down=1, quarter=4) is True
        assert simulator.can_spike(down=2, quarter=4) is True
        assert simulator.can_spike(down=3, quarter=4) is True