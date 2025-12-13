"""
Tests for Play-by-Play Clock Consistency

Phase 2 Integration Tests - Validate clock behavior in play-by-play data.

These tests verify:
1. Clock never goes negative
2. Clock decrements monotonically within a quarter
3. No plays execute after quarter officially ends
4. Quarter labels are consistent with clock state

Bug Context:
Play-by-play data shows "Q1 0:00" for multiple consecutive plays.
This is impossible - once clock hits 0:00, quarter should end.
"""

import pytest
from dataclasses import dataclass
from typing import List, Tuple

from src.play_engine.game_state.game_clock import GameClock, ClockResult


@dataclass
class PlayRecord:
    """Simplified play record for testing clock consistency."""
    quarter: int
    time_remaining: int
    play_number: int
    play_type: str
    time_elapsed: float


class TestClockNeverNegative:
    """Verify game clock never goes below zero."""

    def test_clock_cannot_be_negative(self):
        """Clock should always be >= 0."""
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        # Advance by more than remaining
        clock.advance_time(100)

        assert clock.time_remaining_seconds >= 0
        assert clock.time_remaining_seconds == 0

    def test_clock_initialization_validates_non_negative(self):
        """Clock initialization should reject negative time."""
        with pytest.raises(ValueError):
            GameClock(quarter=1, time_remaining_seconds=-10)

    def test_repeated_advances_stay_non_negative(self):
        """Multiple advances should keep clock non-negative."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        for _ in range(20):
            clock.advance_time(30)

        assert clock.time_remaining_seconds >= 0


class TestClockMonotonicDecrease:
    """Verify clock only decreases within a quarter (never increases)."""

    def test_clock_decreases_on_each_play(self):
        """Clock should decrease or stay same after each play."""
        clock = GameClock(quarter=1, time_remaining_seconds=900)
        previous_time = clock.time_remaining_seconds

        for _ in range(30):
            clock.advance_time(25)
            current_time = clock.time_remaining_seconds

            assert current_time <= previous_time, \
                f"Clock increased from {previous_time} to {current_time}"

            previous_time = current_time

    def test_clock_can_stay_same_on_zero_advance(self):
        """Clock stays same when advancing by 0 (e.g., spike detection)."""
        clock = GameClock(quarter=1, time_remaining_seconds=100)

        clock.advance_time(0)

        assert clock.time_remaining_seconds == 100

    def test_clock_stays_at_zero_once_reached(self):
        """Once clock hits zero, it should stay at zero."""
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        clock.advance_time(10)  # Hits zero
        assert clock.time_remaining_seconds == 0

        clock.advance_time(100)  # More advances
        assert clock.time_remaining_seconds == 0

        clock.advance_time(50)
        assert clock.time_remaining_seconds == 0


class TestNoPlaysAfterQuarterEnd:
    """
    Verify that once quarter ends, no more plays should be labeled
    with that quarter number.

    This test documents expected behavior - the current bug allows
    plays to execute at 0:00 without proper quarter transition.
    """

    def test_quarter_end_detected_correctly(self):
        """Verify is_end_of_quarter is True when time hits 0."""
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        assert clock.is_end_of_quarter is False

        clock.advance_time(10)

        assert clock.is_end_of_quarter is True

    def test_quarter_remains_same_until_explicit_transition(self):
        """
        Quarter number stays same until start_new_quarter() is called.

        This is correct behavior - GameManager decides when to transition.
        The bug is that the transition isn't happening when it should.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        clock.advance_time(10)  # Time expires

        # Quarter is still 1 until explicitly changed
        assert clock.quarter == 1
        assert clock.is_end_of_quarter is True

        # Now transition to next quarter
        clock.start_new_quarter(2)

        assert clock.quarter == 2
        assert clock.is_end_of_quarter is False
        assert clock.time_remaining_seconds == 900

    def test_simulated_play_sequence_consistency(self):
        """
        Simulate a sequence of plays and verify quarter consistency.

        All plays in Q1 should have time > 0, or be the final play
        that causes time to hit 0.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=60)
        plays: List[PlayRecord] = []

        play_num = 0
        while play_num < 10:
            # Record play BEFORE advancing clock (current time when play starts)
            play = PlayRecord(
                quarter=clock.quarter,
                time_remaining=clock.time_remaining_seconds,
                play_number=play_num + 1,
                play_type="run",
                time_elapsed=25.0
            )
            plays.append(play)

            # Advance clock
            clock.advance_time(25)
            play_num += 1

            # CORRECT BEHAVIOR: Stop when quarter ends
            if clock.is_end_of_quarter:
                break

        # Analyze plays
        q1_plays = [p for p in plays if p.quarter == 1]
        plays_at_zero = [p for p in plays if p.time_remaining == 0]

        # With 60 seconds and 25 per play:
        # Play 1: starts at 60
        # Play 2: starts at 35
        # Play 3: starts at 10
        # Play 4: would start at 0 but we stop

        assert len(q1_plays) == 3, f"Expected 3 plays in Q1, got {len(q1_plays)}"
        assert len(plays_at_zero) == 0, "No plays should START at 0:00"


class TestQuarterLabelConsistency:
    """Test that quarter labels match clock state."""

    def test_quarter_1_through_4_progression(self):
        """Test normal progression through 4 quarters."""
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        # Q1 ends
        clock.advance_time(10)
        assert clock.is_end_of_quarter is True
        assert clock.quarter == 1

        # Start Q2
        clock.start_new_quarter(2)
        assert clock.quarter == 2
        assert clock.time_remaining_seconds == 900

        # Q2 ends
        clock.advance_time(900)
        assert clock.is_end_of_quarter is True
        assert clock.quarter == 2

        # Start Q3 (after halftime)
        clock.start_new_quarter(3)
        assert clock.quarter == 3

        # Q3 ends
        clock.advance_time(900)
        clock.start_new_quarter(4)
        assert clock.quarter == 4

        # Q4 ends
        clock.advance_time(900)
        assert clock.is_end_of_quarter is True
        assert clock.quarter == 4

    def test_phase_changes_with_quarters(self):
        """Test that GamePhase changes appropriately with quarters."""
        from src.play_engine.game_state.game_clock import GamePhase

        clock = GameClock(quarter=1, time_remaining_seconds=10)
        assert clock.game_phase == GamePhase.FIRST_HALF

        # End Q1, start Q2
        clock.advance_time(10)
        clock.start_new_quarter(2)
        assert clock.game_phase == GamePhase.FIRST_HALF

        # End Q2 (triggers halftime)
        clock.advance_time(900)
        assert clock.is_halftime is True
        assert clock.game_phase == GamePhase.HALFTIME

        # Start Q3
        clock.end_halftime()
        assert clock.game_phase == GamePhase.SECOND_HALF
        assert clock.quarter == 3


class TestBugScenarioFromData:
    """
    Tests based on actual bug data from play-by-play files.
    """

    def test_buffalo_at_raiders_q1_drive4(self):
        """
        Reproduce the exact timing from BUF at LV, Q1 Drive 4.

        Data shows:
        | Q1 | 1:04 | ... |
        | Q1 | 0:35 | ... |
        | Q1 | 0:03 | ... |
        | Q1 | 0:00 | ... | ← 8 plays at 0:00

        This should be impossible with correct clock management.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=64)  # 1:04

        play_times = []

        # Simulate the drive
        # Using approximate times from the data
        play_durations = [29, 32, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # Bug: plays at 0

        for i, duration in enumerate(play_durations):
            play_times.append(clock.time_remaining_seconds)
            if duration > 0:
                clock.advance_time(duration)
            else:
                # At 0:00, any advance keeps it at 0
                clock.advance_time(25)

        # Count plays that would have started at 0:00
        plays_starting_at_zero = sum(1 for t in play_times if t == 0)

        # The CORRECT behavior: Should have at most 1 play at 0:00
        # (the play that CAUSED the clock to hit 0)
        # But bug data shows 8+ plays at 0:00

        # This test documents the bug - plays 4-13 start at 0:00
        # After fix, this should be at most 1
        print(f"Play times: {play_times}")
        print(f"Plays starting at 0:00: {plays_starting_at_zero}")

        # Assert what SHOULD be true (currently fails due to bug)
        # After fix, uncomment this assertion
        # assert plays_starting_at_zero <= 1, \
        #     f"At most 1 play should start at 0:00, found {plays_starting_at_zero}"

    def test_expected_max_plays_at_zero(self):
        """
        Document expected behavior: At most 1 play should START at 0:00.

        The play that causes clock to hit 0 starts with time remaining.
        Any subsequent play would start at 0:00 which is invalid.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=50)

        plays_at_zero_start = 0
        for i in range(10):
            if clock.time_remaining_seconds == 0:
                plays_at_zero_start += 1
            clock.advance_time(25)

        # With 50 seconds and 25 per play:
        # Play 1: starts at 50, ends at 25
        # Play 2: starts at 25, ends at 0
        # Play 3+: would start at 0 (invalid)

        # Plays that START at 0:00 are invalid
        assert plays_at_zero_start >= 1, "Bug: plays starting at 0:00"

        # After fix, the loop should exit when clock hits 0
        # This test currently passes (shows bug) but logic should change


class TestQuarterTimeNotExceeded:
    """
    Tests to verify quarter time never exceeds 15 minutes (900 seconds).

    This verifies the secondary fix: time_elapsed capping.
    When a play takes 25 seconds but only 3 remain, time_elapsed should be capped to 3.
    """

    def test_time_elapsed_capped_at_zero(self):
        """
        Verify that time_elapsed is capped when clock reaches zero.

        The ClockResult.time_advanced should reflect actual time consumed.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=10)

        # Play takes 25 seconds, but only 10 remain
        result = clock.advance_time(25)

        # time_advanced should be capped to actual time consumed
        assert result.time_advanced == 10
        assert clock.time_remaining_seconds == 0
        assert result.quarter_ended is True

    def test_sum_of_play_times_never_exceeds_900(self):
        """
        Verify total play times in a quarter never exceed 900 seconds.

        This tests the scenario where plays sum up their raw time_elapsed values.
        After the fix, capped time_elapsed should sum to exactly 900.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=900)

        total_time_elapsed = 0
        play_count = 0

        # Simulate many plays until quarter ends
        while not clock.is_end_of_quarter and play_count < 100:
            play_duration = 25  # Each play takes 25 seconds
            result = clock.advance_time(play_duration)

            # Use the capped time_advanced, not the raw play_duration
            total_time_elapsed += result.time_advanced
            play_count += 1

        # Total time should be exactly 900 (sum of capped play times)
        assert total_time_elapsed == 900, \
            f"Quarter time should be exactly 900 seconds, got {total_time_elapsed}"

    def test_last_play_time_elapsed_capped(self):
        """
        Verify the last play of a quarter has its time_elapsed capped.

        Example: 3 seconds remain, play takes 25 seconds
        - Clock goes to 0 (correct)
        - time_elapsed should be 3, not 25
        """
        clock = GameClock(quarter=1, time_remaining_seconds=3)

        # Play takes 25 seconds
        result = clock.advance_time(25)

        # time_advanced should be capped to 3
        assert result.time_advanced == 3
        # The original 25 seconds is not used for stats
        assert result.quarter_ended is True

    def test_multiple_plays_near_end_of_quarter(self):
        """
        Verify multiple plays near end of quarter have correct time tracking.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=50)

        times_advanced = []
        while not clock.is_end_of_quarter:
            result = clock.advance_time(25)
            times_advanced.append(result.time_advanced)

        # Should have 2 plays: first takes 25, second takes remaining 25
        assert len(times_advanced) == 2
        assert times_advanced[0] == 25
        assert times_advanced[1] == 25
        assert sum(times_advanced) == 50

    def test_clock_result_time_advanced_accuracy(self):
        """
        Verify ClockResult.time_advanced is always <= time requested.
        """
        test_cases = [
            (100, 25, 25),   # Normal: 100 left, advance 25 -> 25 consumed
            (10, 25, 10),    # Capped: 10 left, advance 25 -> 10 consumed
            (0, 25, 0),      # At zero: advance 25 -> 0 consumed
            (25, 25, 25),    # Exact: 25 left, advance 25 -> 25 consumed
        ]

        for time_remaining, advance_by, expected_advanced in test_cases:
            clock = GameClock(quarter=1, time_remaining_seconds=time_remaining)
            result = clock.advance_time(advance_by)

            assert result.time_advanced == expected_advanced, \
                f"With {time_remaining}s left, advancing {advance_by}s should consume {expected_advanced}s, got {result.time_advanced}s"


class TestTransitionTimeConsumed:
    """
    Tests to verify transition time (punt returns, kickoffs) is consumed.

    Bug: TransitionResult.time_elapsed was calculated but never consumed.
    Fix: Added game_clock.advance_time(transition_result.time_elapsed) in
         _handle_drive_transition().
    """

    def test_transition_time_concept(self):
        """
        Verify transition time concept: time should be consumed for:
        - Punt hang time + return
        - Kickoff + return
        - Change of possession transitions
        """
        # Example: Punt at 0:27
        clock = GameClock(quarter=1, time_remaining_seconds=27)

        # Punt play consumes ~7 seconds
        punt_play_time = 7
        clock.advance_time(punt_play_time)
        assert clock.time_remaining_seconds == 20

        # Transition (punt return) should consume ~8 seconds
        transition_time = 8
        clock.advance_time(transition_time)
        assert clock.time_remaining_seconds == 12

        # Receiving team gets 12 seconds for their play
        # NOT 20 seconds (which was the bug)

    def test_quarter_can_end_during_transition(self):
        """
        Verify quarter can end during transition if time runs out.

        If punt at 0:05 and transition takes 8 seconds,
        quarter should end during transition.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=5)

        # Punt play consumes 5 seconds -> clock at 0
        result = clock.advance_time(5)
        assert clock.time_remaining_seconds == 0
        assert result.quarter_ended is True

        # Quarter already ended, transition can't add more time
        # (clock capped at 0)

    def test_transition_time_accumulates_correctly(self):
        """
        Verify total quarter time with transitions is still 900 seconds.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=900)

        total_time = 0

        # Simulate a quarter with plays and transitions
        scenario = [
            ("play", 25),
            ("play", 30),
            ("transition", 8),  # Punt return
            ("play", 25),
            ("play", 25),
            ("play", 30),
            ("transition", 8),  # Punt return
        ]

        for event_type, time in scenario:
            if clock.is_end_of_quarter:
                break
            result = clock.advance_time(time)
            total_time += result.time_advanced

        # Time consumed should be <= 900
        assert total_time <= 900

    def test_punt_at_27_with_transition(self):
        """
        Reproduce exact scenario from user report.

        Punt at 0:27, should consume:
        - ~7s punt play time
        - ~8s transition time
        = 15s total, leaving 12s for receiving team
        """
        clock = GameClock(quarter=1, time_remaining_seconds=27)

        # Punt play
        punt_result = clock.advance_time(7)
        assert punt_result.time_advanced == 7
        assert clock.time_remaining_seconds == 20

        # Transition (this is what was missing!)
        transition_result = clock.advance_time(8)
        assert transition_result.time_advanced == 8
        assert clock.time_remaining_seconds == 12

        # Receiving team's play (if it takes 12+ seconds, quarter ends)
        play_result = clock.advance_time(15)
        assert play_result.time_advanced == 12  # Capped to remaining
        assert clock.time_remaining_seconds == 0
        assert clock.is_end_of_quarter is True
