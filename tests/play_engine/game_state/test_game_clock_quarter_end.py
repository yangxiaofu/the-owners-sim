"""
Tests for GameClock Quarter End Detection

Phase 1 Unit Tests - Isolate the clock management bug by testing:
1. Quarter detection when clock hits exactly 0
2. Quarter detection when play time exceeds remaining time
3. Behavior when advancing time at 0:00 (bug diagnostic)
4. Quarter transition mechanics

Bug Context:
Play-by-play data shows 8+ plays executing at Q1/Q3/Q4 0:00.
This should be impossible - quarter should end when time expires.
"""

import pytest
from src.play_engine.game_state.game_clock import GameClock, ClockResult, GamePhase


class TestQuarterEndDetection:
    """Test GameClock's ability to detect quarter end conditions."""

    def test_clock_detects_quarter_end_at_zero(self):
        """Verify is_end_of_quarter is True when time hits exactly 0."""
        clock = GameClock(quarter=1, time_remaining_seconds=5)

        # Advance time by exactly the remaining seconds
        result = clock.advance_time(5)

        assert clock.time_remaining_seconds == 0
        assert clock.is_end_of_quarter is True
        assert result.quarter_ended is True
        assert "End of Q1" in result.clock_events

    def test_clock_detects_quarter_end_with_overflow(self):
        """Verify quarter ends even if play time exceeds remaining time."""
        clock = GameClock(quarter=1, time_remaining_seconds=3)

        # Play takes 10 seconds but only 3 seconds left
        result = clock.advance_time(10)

        # Clock should cap at 0, not go negative
        assert clock.time_remaining_seconds == 0
        assert clock.is_end_of_quarter is True
        assert result.quarter_ended is True

    def test_clock_stays_at_zero_on_subsequent_advances(self):
        """
        BUG DIAGNOSTIC: What happens if we advance time when already at 0?

        This tests the exact scenario from the bug - plays executing at 0:00.
        If the game loop allows plays after time expires, this test reveals
        what the clock does when asked to advance from 0.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=0)

        # Already at 0:00, try to advance by typical play time
        result = clock.advance_time(25)

        # Clock should stay at 0
        assert clock.time_remaining_seconds == 0
        assert clock.is_end_of_quarter is True

        # Key question: Does quarter_ended fire again?
        # If not, the game loop might not know to stop
        # Note: Current implementation returns quarter_ended=False when already at 0
        # because the condition checks `new_time == 0 and original_time > 0`

    def test_quarter_ended_flag_only_fires_once(self):
        """
        Test that quarter_ended flag fires exactly once at transition.

        Bug hypothesis: If quarter_ended only fires when transitioning
        FROM non-zero TO zero, subsequent plays at 0:00 won't trigger it,
        and the game loop might not notice the quarter is over.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=5)

        # First advance - crosses the threshold
        result1 = clock.advance_time(5)
        assert result1.quarter_ended is True, "Should fire when crossing to 0"

        # Second advance - already at 0
        result2 = clock.advance_time(25)
        assert result2.quarter_ended is False, "Should NOT fire again (already at 0)"

        # This confirms the bug mechanism: once at 0:00, quarter_ended
        # won't fire again, so if the loop doesn't check is_end_of_quarter
        # property, it will keep running plays

    def test_is_end_of_quarter_property_persists(self):
        """
        Test that is_end_of_quarter property returns True even after
        multiple advance_time calls at 0:00.

        The property should be the reliable check, not the event flag.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=5)

        # Advance to 0
        clock.advance_time(5)
        assert clock.is_end_of_quarter is True

        # Advance again while at 0
        clock.advance_time(25)
        assert clock.is_end_of_quarter is True, "Property should persist"

        # Advance multiple times
        for _ in range(10):
            clock.advance_time(30)
        assert clock.is_end_of_quarter is True, "Property should always be True at 0:00"


class TestQuarterTransitions:
    """Test quarter-to-quarter transitions."""

    def test_q1_to_q2_transition(self):
        """Test transition from Q1 to Q2."""
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        # End Q1
        result = clock.advance_time(10)
        assert result.quarter_ended is True
        assert clock.quarter == 1  # Still Q1 until explicitly transitioned

        # Start Q2
        clock.start_new_quarter(2)
        assert clock.quarter == 2
        assert clock.time_remaining_seconds == 900
        assert clock.is_end_of_quarter is False

    def test_q2_ends_triggers_halftime(self):
        """Test that Q2 ending triggers halftime phase."""
        clock = GameClock(quarter=2, time_remaining_seconds=5)

        result = clock.advance_time(5)

        assert result.quarter_ended is True
        assert result.half_ended is True
        assert clock.is_halftime is True
        assert result.new_phase == GamePhase.HALFTIME
        assert "End of first half" in result.clock_events

    def test_q4_ends_triggers_regulation_end(self):
        """Test that Q4 ending triggers end of regulation."""
        clock = GameClock(quarter=4, time_remaining_seconds=5)

        result = clock.advance_time(5)

        assert result.quarter_ended is True
        assert result.half_ended is True
        assert "End of regulation" in result.clock_events
        # Note: game_ended is NOT set here - GameManager decides based on score

    def test_halftime_blocks_time_advancement(self):
        """Test that clock doesn't advance during halftime."""
        clock = GameClock(quarter=2, time_remaining_seconds=0)
        clock.is_halftime = True

        result = clock.advance_time(100)

        assert result.time_advanced == 0.0
        assert "halftime" in result.clock_events[0].lower()


class TestTwoMinuteWarning:
    """Test two-minute warning detection."""

    def test_two_minute_warning_in_q2(self):
        """Test two-minute warning triggers in Q2."""
        clock = GameClock(quarter=2, time_remaining_seconds=130)

        # Cross the 2:00 threshold
        result = clock.advance_time(15)

        assert result.two_minute_warning is True
        assert "Two-minute warning" in result.clock_events
        assert clock.is_two_minute_warning_active is True

    def test_two_minute_warning_in_q4(self):
        """Test two-minute warning triggers in Q4."""
        clock = GameClock(quarter=4, time_remaining_seconds=125)

        result = clock.advance_time(10)

        assert result.two_minute_warning is True
        assert clock.is_two_minute_warning_active is True

    def test_no_two_minute_warning_in_q1(self):
        """Test two-minute warning does NOT trigger in Q1."""
        clock = GameClock(quarter=1, time_remaining_seconds=130)

        result = clock.advance_time(15)

        assert result.two_minute_warning is False
        assert clock.is_two_minute_warning_active is False

    def test_no_two_minute_warning_in_q3(self):
        """Test two-minute warning does NOT trigger in Q3."""
        clock = GameClock(quarter=3, time_remaining_seconds=130)

        result = clock.advance_time(15)

        assert result.two_minute_warning is False


class TestClockEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_time_advance_raises(self):
        """Test that negative time advancement raises error."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        with pytest.raises(ValueError, match="negative"):
            clock.advance_time(-10)

    def test_zero_time_advance_is_valid(self):
        """Test that zero time advancement is valid (e.g., for spikes)."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        result = clock.advance_time(0)

        assert result.time_advanced == 0
        assert clock.time_remaining_seconds == 100

    def test_large_time_advance_caps_at_zero(self):
        """Test that large time values cap at zero, not negative."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        clock.advance_time(10000)

        assert clock.time_remaining_seconds == 0
        assert clock.time_remaining_seconds >= 0

    def test_fractional_time_is_truncated(self):
        """Test that fractional seconds are truncated to int."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        clock.advance_time(5.7)

        # Should truncate to 5, leaving 95
        assert clock.time_remaining_seconds == 95

    def test_overtime_quarter_detection(self):
        """Test overtime quarter (Q5+) is detected correctly."""
        clock = GameClock(quarter=5, time_remaining_seconds=600)  # 10 min OT

        assert clock.is_overtime is True
        assert clock.game_phase == GamePhase.OVERTIME

        # End overtime
        clock.advance_time(600)
        assert clock.is_end_of_quarter is True
        assert clock.is_overtime is True
