"""Tests for PlayDuration calculations."""

import pytest
from src.play_engine.mechanics.play_duration import PlayDuration


class TestPlayDuration:
    """Test play duration calculations."""

    def test_incomplete_pass_duration(self):
        """Test incomplete pass base duration."""
        duration = PlayDuration.calculate_duration("incomplete", apply_variance=False)
        assert duration == 6

    def test_run_play_duration(self):
        """Test run play base duration."""
        duration = PlayDuration.calculate_duration("run", apply_variance=False)
        assert duration == 8

    def test_complete_pass_inbounds_duration(self):
        """Test complete pass (inbounds) base duration."""
        duration = PlayDuration.calculate_duration("complete_inbounds", apply_variance=False)
        assert duration == 7

    def test_timeout_duration(self):
        """Test timeout duration (NFL standard 1:40 = 100 seconds)."""
        duration = PlayDuration.calculate_duration("timeout", apply_variance=False)
        assert duration == 100

    def test_spike_duration(self):
        """Test spike play duration."""
        duration = PlayDuration.calculate_duration("spike", apply_variance=False)
        assert duration == 3

    def test_sack_duration(self):
        """Test sack play duration."""
        duration = PlayDuration.calculate_duration("sack", apply_variance=False)
        assert duration == 6

    def test_hurry_up_tempo_modifier(self):
        """Test hurry-up tempo reduces duration."""
        normal = PlayDuration.calculate_duration("run", tempo="normal", apply_variance=False)
        hurry_up = PlayDuration.calculate_duration("run", tempo="hurry_up", apply_variance=False)

        assert hurry_up < normal
        assert hurry_up == int(normal * 0.6)  # 40% faster

    def test_two_minute_tempo_modifier(self):
        """Test two-minute tempo reduces duration."""
        normal = PlayDuration.calculate_duration("run", tempo="normal", apply_variance=False)
        two_min = PlayDuration.calculate_duration("run", tempo="two_minute", apply_variance=False)

        assert two_min < normal
        assert two_min == int(normal * 0.5)  # 50% faster

    def test_slow_tempo_modifier(self):
        """Test slow tempo increases duration."""
        normal = PlayDuration.calculate_duration("run", tempo="normal", apply_variance=False)
        slow = PlayDuration.calculate_duration("run", tempo="slow", apply_variance=False)

        assert slow > normal
        assert slow == int(normal * 1.2)  # 20% slower

    def test_variance_adds_randomness(self):
        """Test variance creates different durations."""
        durations = [
            PlayDuration.calculate_duration("run", apply_variance=True)
            for _ in range(20)
        ]

        # Should have variation
        assert len(set(durations)) > 1

        # Should be within ±20% of base (8 seconds)
        assert all(6 <= d <= 10 for d in durations)

    def test_minimum_duration_is_one_second(self):
        """Test that duration is always at least 1 second."""
        # Even with variance and fast tempo, duration should be >= 1
        for _ in range(10):
            duration = PlayDuration.calculate_duration("spike", tempo="two_minute", apply_variance=True)
            assert duration >= 1

    def test_clock_stops_on_incomplete(self):
        """Test clock stops on incomplete pass."""
        assert PlayDuration.should_clock_stop("incomplete") is True

    def test_clock_stops_on_timeout(self):
        """Test clock stops when timeout called."""
        assert PlayDuration.should_clock_stop("run", timeout_called=True) is True

    def test_clock_stops_on_out_of_bounds(self):
        """Test clock stops when out of bounds."""
        assert PlayDuration.should_clock_stop("run", out_of_bounds=True) is True

    def test_clock_stops_on_spike(self):
        """Test clock stops on spike."""
        assert PlayDuration.should_clock_stop("run", is_spike=True) is True

    def test_clock_continues_on_inbounds_run(self):
        """Test clock continues on normal run play."""
        assert PlayDuration.should_clock_stop("run") is False

    def test_clock_stops_on_first_down_under_two_minutes(self):
        """Test clock stops briefly on first down in final 2 minutes."""
        assert PlayDuration.should_clock_stop(
            "run",
            first_down=True,
            under_two_minutes=True
        ) is True

    def test_clock_continues_on_first_down_not_under_two_minutes(self):
        """Test clock continues on first down when not in final 2 minutes."""
        assert PlayDuration.should_clock_stop(
            "run",
            first_down=True,
            under_two_minutes=False
        ) is False

    def test_penalty_stops_clock_when_specified(self):
        """Test clock stops on penalty when penalty_stops_clock is True."""
        assert PlayDuration.should_clock_stop(
            "run",
            penalty_stops_clock=True
        ) is True

    def test_special_plays_stop_clock(self):
        """Test that field goals, punts, and kickoffs stop the clock."""
        assert PlayDuration.should_clock_stop("field_goal") is True
        assert PlayDuration.should_clock_stop("punt") is True
        assert PlayDuration.should_clock_stop("kickoff") is True
