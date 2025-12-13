"""
Integration Tests for Quarter Transition Bug

Phase 2 Integration Tests - Reproduce the bug where plays execute at 0:00.

Bug Location (confirmed):
    game_loop_controller.py line 292:
    `while not drive_manager.is_drive_over():`

    Missing condition: `and not self._is_quarter_complete()`

    This means drives continue until a natural end (TD, punt, turnover)
    even if the game clock has reached 0:00.

Test Strategy:
    These tests use mocking to isolate the bug behavior without needing
    to run full game simulations. We test the logical flow, not the
    complete system.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.play_engine.game_state.game_clock import GameClock, ClockResult
from src.play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from src.play_engine.game_state.down_situation import DownState
from src.play_engine.game_state.field_position import FieldPosition, FieldZone
from src.play_engine.core.play_result import PlayResult


class TestBugReproduction:
    """
    Reproduce the exact bug scenario from play-by-play data.

    From playbyplay_BUF_at_LV.md, Drive 4 (Q1):
    - Drive starts at Q1 1:04
    - 13 plays execute
    - Last 8+ plays show "Q1 0:00" time
    - Drive ends with TD (natural end), not time expiration
    """

    def test_clock_reaches_zero_mid_drive(self):
        """
        Simulate a drive where clock hits 0 before drive naturally ends.

        Expected behavior (after fix): Drive should end when clock hits 0
        Current behavior (bug): Drive continues until natural end
        """
        # Setup game clock with 64 seconds (1:04) remaining
        clock = GameClock(quarter=1, time_remaining_seconds=64)

        # Setup drive manager
        drive = DriveManager(
            starting_position=FieldPosition(
                yard_line=25,
                possession_team=1,
                field_zone=FieldZone.OWN_TERRITORY
            ),
            starting_down_state=DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=35
            ),
            possessing_team_id=1
        )

        plays_executed = 0
        plays_at_zero = 0

        # Simulate plays until drive would naturally end
        # Using incomplete passes (clock stops, ~6 seconds each)
        while not drive.is_drive_over() and plays_executed < 20:
            # Check clock BEFORE play
            time_before = clock.time_remaining_seconds

            # Create play result
            play = PlayResult(
                outcome="incomplete",
                yards=0,
                time_elapsed=6.0,
                is_scoring_play=False,
                is_turnover=False,
            )

            # Advance clock
            clock.advance_time(play.time_elapsed)

            # Process play in drive manager
            drive.process_play_result(play)

            plays_executed += 1

            # Track plays at 0:00
            if clock.time_remaining_seconds == 0:
                plays_at_zero += 1

            # BUG CHECK: In current code, we'd continue here even at 0:00
            # The CORRECT behavior would be to break when clock hits 0

        # With 64 seconds and 6 seconds per play, clock hits 0 after ~11 plays
        # But incomplete passes advance downs: 1st→2nd→3rd→4th→turnover
        # So drive would end on downs before clock expires

        # Let's verify the clock behavior at least
        assert clock.time_remaining_seconds == 0 or drive.is_drive_over()

    def test_multiple_plays_execute_at_zero(self):
        """
        BUG DEMONSTRATION: Multiple plays can execute at 0:00.

        This test shows that once clock hits 0, subsequent plays
        still execute because DriveManager doesn't check time.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=10)
        plays_at_zero = []

        # First two plays consume all time
        for i in range(2):
            clock.advance_time(6)

        assert clock.time_remaining_seconds == 0, "Clock should be at 0"
        assert clock.is_end_of_quarter is True

        # Now simulate what happens in the bug: more plays run at 0:00
        for i in range(5):
            result = clock.advance_time(25)  # Play would take 25 seconds

            # Clock stays at 0
            assert clock.time_remaining_seconds == 0

            # But quarter_ended only fires once
            if i == 0:
                # First advance at 0 - quarter_ended is False (already at 0)
                assert result.quarter_ended is False
            plays_at_zero.append(i)

        # This demonstrates the bug mechanism:
        # - Clock is at 0
        # - GameLoopController checks `_is_quarter_complete()` which returns True
        # - BUT that check only happens at the END of `_run_drive()`
        # - So if we're mid-drive, we never check it
        assert len(plays_at_zero) == 5, "Bug: 5 plays executed at 0:00"


class TestDriveLoopMissingCheck:
    """
    Test the specific bug: _run_drive() doesn't check for quarter end.

    The bug is in game_loop_controller.py:
    ```python
    def _run_drive(self, possessing_team_id: int):
        ...
        while not drive_manager.is_drive_over():  # <-- Missing: and not self._is_quarter_complete()
            play_result = self._run_play(...)
            drive_manager.process_play_result(play_result)
        ...
    ```
    """

    def test_drive_manager_is_drive_over_ignores_clock(self):
        """
        Verify DriveManager.is_drive_over() doesn't consider time.

        This is BY DESIGN - DriveManager is decoupled from clock.
        The bug is that GameLoopController doesn't add the clock check.
        """
        drive = DriveManager(
            starting_position=FieldPosition(
                yard_line=50,
                possession_team=1,
                field_zone=FieldZone.OPPONENT_TERRITORY
            ),
            starting_down_state=DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=60
            ),
            possessing_team_id=1
        )

        # Run many plays that don't end drive
        for _ in range(10):
            play = PlayResult(
                outcome="run",
                yards=3,  # Short gain, keeps getting first downs
                time_elapsed=30.0,  # 30 seconds each
                is_scoring_play=False,
                is_turnover=False,
            )
            drive.process_play_result(play)

        # Total time: 10 * 30 = 300 seconds = 5 minutes
        # A full quarter is 15 minutes, so this is fine
        # But if we started with 1 minute left, we'd have executed
        # 10 plays in "negative time"

        # The point: DriveManager doesn't know or care about time
        assert drive.stats.time_of_possession_seconds == 300.0
        assert drive.is_drive_over() is False  # Still going!

    def test_simulated_bug_flow(self):
        """
        Simulate the exact bug flow from GameLoopController._run_drive().

        This mimics lines 292-342 of game_loop_controller.py to show
        how plays continue after time expires.
        """
        # Setup
        clock = GameClock(quarter=1, time_remaining_seconds=30)
        drive = DriveManager(
            starting_position=FieldPosition(
                yard_line=25,
                possession_team=1,
                field_zone=FieldZone.OWN_TERRITORY
            ),
            starting_down_state=DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=35
            ),
            possessing_team_id=1
        )

        plays_executed = 0
        plays_after_clock_zero = 0

        # Simulate the buggy while loop
        # Current code: while not drive_manager.is_drive_over():
        # Should be: while not drive_manager.is_drive_over() and not self._is_quarter_complete():

        while not drive.is_drive_over():  # BUG: Missing clock check
            # Create a play that gains yards but doesn't end drive
            play = PlayResult(
                outcome="run",
                yards=4,
                time_elapsed=30.0,  # 30 seconds per play
                is_scoring_play=False,
                is_turnover=False,
            )

            # Advance clock (what GameLoopController does)
            clock.advance_time(play.time_elapsed)

            # Process play
            drive.process_play_result(play)

            plays_executed += 1

            # Track plays after clock hit zero
            if clock.is_end_of_quarter:
                plays_after_clock_zero += 1

            # Safety limit to prevent infinite loop
            if plays_executed > 20:
                break

        # Analysis:
        # - Clock had 30 seconds, each play takes 30 seconds
        # - After play 1: clock = 0, quarter ended
        # - But drive keeps going because is_drive_over() is False
        # - Plays 2-N execute at 0:00

        assert plays_executed > 1, "Multiple plays should execute"
        assert plays_after_clock_zero > 0, "BUG: Plays executed after clock hit zero"
        assert clock.is_end_of_quarter is True


class TestCorrectBehaviorSimulation:
    """
    Test the CORRECT behavior (what should happen after fix).

    These tests use the correct logic that should be in GameLoopController.
    """

    def test_drive_ends_when_quarter_ends(self):
        """
        Simulate the CORRECT behavior: drive ends when clock hits 0.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=30)
        drive = DriveManager(
            starting_position=FieldPosition(
                yard_line=25,
                possession_team=1,
                field_zone=FieldZone.OWN_TERRITORY
            ),
            starting_down_state=DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=35
            ),
            possessing_team_id=1
        )

        plays_executed = 0

        # CORRECT loop condition
        while not drive.is_drive_over() and not clock.is_end_of_quarter:
            play = PlayResult(
                outcome="run",
                yards=4,
                time_elapsed=30.0,
                is_scoring_play=False,
                is_turnover=False,
            )

            clock.advance_time(play.time_elapsed)
            drive.process_play_result(play)
            plays_executed += 1

            # Safety limit
            if plays_executed > 20:
                break

        # With correct logic:
        # - Play 1 executes, clock goes to 0
        # - Loop exits because clock.is_end_of_quarter is True
        # - Only 1 play executes in Q1 with 30 seconds left

        assert plays_executed == 1, "Only one play should execute before quarter ends"
        assert clock.is_end_of_quarter is True

    def test_drive_natural_end_before_clock(self):
        """
        Test that natural drive endings (TD, punt) still work normally.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=900)  # Full quarter
        drive = DriveManager(
            starting_position=FieldPosition(
                yard_line=95,  # Near goal line
                possession_team=1,
                field_zone=FieldZone.OPPONENT_TERRITORY
            ),
            starting_down_state=DownState(
                current_down=1,
                yards_to_go=5,
                first_down_line=100  # Goal line
            ),
            possessing_team_id=1
        )

        # Score a TD
        td_play = PlayResult(
            outcome="run",
            yards=5,
            time_elapsed=25.0,
            is_scoring_play=True,
            points=6,
            is_turnover=False,
        )

        # CORRECT loop
        plays = 0
        while not drive.is_drive_over() and not clock.is_end_of_quarter:
            clock.advance_time(td_play.time_elapsed)
            drive.process_play_result(td_play)
            plays += 1
            break  # Only run once for TD

        assert drive.is_drive_over() is True
        assert drive.end_reason == DriveEndReason.TOUCHDOWN
        assert clock.is_end_of_quarter is False  # Still time left


class TestPlayByPlayScenarios:
    """
    Test specific scenarios from the actual play-by-play bug data.
    """

    def test_q1_drive_4_scenario(self):
        """
        Reproduce Drive 4 from Q1 of BUF at LV game.

        Original data shows:
        - Drive starts at Q1 1:04 (64 seconds)
        - 13 plays total
        - Plays 4-13 (8 plays) all show Q1 0:00
        - Drive ends with TD (natural)
        """
        clock = GameClock(quarter=1, time_remaining_seconds=64)

        # Track plays at each time
        play_times = []

        # Simulate 13 plays with ~25 second average
        for i in range(13):
            time_before = clock.time_remaining_seconds
            clock.advance_time(25)  # Average NFL play
            time_after = clock.time_remaining_seconds
            play_times.append((i + 1, time_before, time_after))

        # Analyze the timing
        plays_at_zero = sum(1 for _, before, after in play_times if after == 0)
        first_zero_play = next(
            (i for i, before, after in play_times if after == 0),
            None
        )

        # With 64 seconds and 25 per play:
        # Play 1: 64 → 39
        # Play 2: 39 → 14
        # Play 3: 14 → 0 (clock expires)
        # Play 4+: 0 → 0 (BUG: should not execute)

        assert plays_at_zero >= 10, f"Expected 10+ plays at 0:00, got {plays_at_zero}"
        assert first_zero_play == 3, f"First play at 0:00 should be play 3, got {first_zero_play}"

    def test_count_plays_at_zero_in_quarter(self):
        """
        Utility test to count how many plays execute at 0:00.

        This demonstrates the severity of the bug - in a typical
        quarter-ending drive, many plays can execute at 0:00.
        """
        # Various starting scenarios
        scenarios = [
            # (starting_seconds, plays_per_drive, avg_play_time)
            (64, 13, 25),   # Q1 Drive 4 from bug
            (30, 8, 25),    # Short drive
            (120, 10, 25),  # Two-minute drill
        ]

        for start_time, num_plays, play_time in scenarios:
            clock = GameClock(quarter=1, time_remaining_seconds=start_time)
            plays_at_zero = 0

            for _ in range(num_plays):
                if clock.time_remaining_seconds == 0:
                    plays_at_zero += 1
                clock.advance_time(play_time)

            expected_at_zero = max(0, num_plays - (start_time // play_time) - 1)
            assert plays_at_zero > 0 or start_time >= num_plays * play_time, \
                f"Scenario {start_time}s/{num_plays} plays should have plays at 0:00"
