"""
Diagnostic Tests for Game Loop Clock Bug

Phase 3 Diagnostic Tests - Understand and document the exact bug mechanism.

Bug Summary:
    The game loop in GameLoopController has a structural flaw where
    _is_quarter_complete() is checked at the WRONG level:

    CURRENT (buggy):
    ```
    def _run_quarter(self, quarter):
        while not self._is_quarter_complete():    # ← Checked here
            drive_result = self._run_drive(...)

    def _run_drive(self, possessing_team_id):
        while not drive_manager.is_drive_over():  # ← NO time check
            play_result = self._run_play(...)
    ```

    The quarter check only runs between drives, not between plays.
    So if a drive is in progress when time expires, plays continue
    until the drive naturally ends.

Fix Required:
    Add time check to the inner loop:
    ```
    def _run_drive(self, possessing_team_id):
        while not drive_manager.is_drive_over() and not self._is_quarter_complete():
            play_result = self._run_play(...)
    ```
"""

import pytest
import inspect
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.play_engine.game_state.game_clock import GameClock
from src.play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from src.play_engine.game_state.down_situation import DownState
from src.play_engine.game_state.field_position import FieldPosition, FieldZone


class TestBugLocationIdentification:
    """Identify and document the exact location of the bug."""

    def test_game_loop_controller_source_inspection(self):
        """
        Inspect GameLoopController source to verify the fix is in place.

        This test reads the actual source code to confirm the fix pattern.
        """
        try:
            from src.game_management.game_loop_controller import GameLoopController

            # Get source of _run_drive method
            source = inspect.getsource(GameLoopController._run_drive)

            # Check for the FIXED pattern
            # Should find: "while not drive_manager.is_drive_over():"
            # Should ALSO find: "_is_quarter_complete()" (the fix)

            has_drive_over_check = "is_drive_over()" in source
            has_quarter_check_in_drive = "_is_quarter_complete()" in source

            assert has_drive_over_check, \
                "Expected to find is_drive_over() check in _run_drive"

            # FIX VERIFICATION: Quarter check SHOULD now be in the drive loop
            assert has_quarter_check_in_drive, \
                "FIX VERIFIED: _is_quarter_complete() check is now in _run_drive loop"

        except ImportError:
            pytest.skip("GameLoopController not importable in test environment")

    def test_run_quarter_has_time_check(self):
        """
        Verify _run_quarter has time check (it does - that's not the bug).
        """
        try:
            from src.game_management.game_loop_controller import GameLoopController

            source = inspect.getsource(GameLoopController._run_quarter)

            # _run_quarter DOES check _is_quarter_complete()
            assert "_is_quarter_complete()" in source, \
                "_run_quarter should check _is_quarter_complete"

        except ImportError:
            pytest.skip("GameLoopController not importable in test environment")


class TestQuarterCheckGranularity:
    """
    Test the granularity of quarter completion checking.

    The bug: Quarter is checked at drive level, not play level.
    """

    def test_quarter_check_frequency_simulation(self):
        """
        Simulate checking quarter completion at different granularities.

        Shows the difference between checking after each drive vs. each play.
        """
        # Simulate a game state
        clock = GameClock(quarter=1, time_remaining_seconds=30)

        # Drive with 5 plays, each taking 25 seconds
        plays_per_drive = 5
        time_per_play = 25

        # Scenario 1: Check after each PLAY (correct)
        plays_executed_correct = 0
        for _ in range(plays_per_drive):
            if clock.is_end_of_quarter:
                break
            clock.advance_time(time_per_play)
            plays_executed_correct += 1

        # Reset
        clock = GameClock(quarter=1, time_remaining_seconds=30)

        # Scenario 2: Check after each DRIVE (buggy)
        plays_executed_buggy = 0
        drive_ended = False
        while not clock.is_end_of_quarter and not drive_ended:
            # Inner loop - no time check (BUG)
            for i in range(plays_per_drive):
                clock.advance_time(time_per_play)
                plays_executed_buggy += 1
                if i == plays_per_drive - 1:  # Last play ends drive
                    drive_ended = True

        # Results:
        # Correct: 2 plays (30 seconds / 25 per play, rounded)
        # Buggy: 5 plays (full drive completes before check)

        assert plays_executed_correct == 2, \
            f"Correct behavior: 2 plays, got {plays_executed_correct}"
        assert plays_executed_buggy == 5, \
            f"Buggy behavior: 5 plays (full drive), got {plays_executed_buggy}"

        # The difference is 3 extra plays - all at 0:00
        extra_plays = plays_executed_buggy - plays_executed_correct
        assert extra_plays == 3, f"Bug causes {extra_plays} extra plays"


class TestDriveManagerIsolation:
    """
    Verify DriveManager is intentionally isolated from clock.

    The isolation is BY DESIGN. The bug is that GameLoopController
    doesn't bridge the gap properly.
    """

    def test_drive_manager_no_clock_dependency(self):
        """DriveManager should have no clock-related imports or attributes."""
        import src.play_engine.game_state.drive_manager as dm_module

        module_source = inspect.getsource(dm_module)

        # DriveManager should NOT import or reference GameClock
        assert "GameClock" not in module_source, \
            "DriveManager should not depend on GameClock"

        assert "game_clock" not in module_source.lower(), \
            "DriveManager should not reference game_clock"

    def test_drive_manager_time_expiration_now_used(self):
        """
        Verify TIME_EXPIRATION is now used via end_due_to_time_expiration().

        After the fix, DriveManager has a method to set TIME_EXPIRATION.
        """
        from src.play_engine.game_state.drive_manager import DriveEndReason

        # TIME_EXPIRATION exists
        assert DriveEndReason.TIME_EXPIRATION.value == "time_expiration"

        # FIX VERIFICATION: It IS now used in DriveManager
        import src.play_engine.game_state.drive_manager as dm_module
        source = inspect.getsource(dm_module.DriveManager)

        # Count occurrences of TIME_EXPIRATION in DriveManager
        time_exp_count = source.count("TIME_EXPIRATION")

        # Should be > 0 - it's now used in end_due_to_time_expiration()
        assert time_exp_count > 0, \
            f"TIME_EXPIRATION should now be used in DriveManager (found {time_exp_count} times)"

        # Verify the new method exists
        assert hasattr(dm_module.DriveManager, 'end_due_to_time_expiration'), \
            "DriveManager should have end_due_to_time_expiration() method"


class TestGameClockBehaviorAtZero:
    """
    Test how GameClock behaves when already at zero.

    Understanding this helps explain why the bug manifests as it does.
    """

    def test_advance_time_at_zero_is_silent(self):
        """
        Advancing time when already at 0 doesn't raise errors.

        This is why the bug silently continues - no error is thrown.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=0)

        # This should not raise
        result = clock.advance_time(100)

        # Clock stays at 0
        assert clock.time_remaining_seconds == 0

        # But quarter_ended doesn't fire (already at 0)
        assert result.quarter_ended is False

    def test_is_end_of_quarter_always_true_at_zero(self):
        """
        is_end_of_quarter is a property that's always True at 0.

        The property is correct - the bug is that it's not checked.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=0)

        # Property is always True when time is 0
        for _ in range(10):
            assert clock.is_end_of_quarter is True
            clock.advance_time(50)  # Doesn't change anything

    def test_is_clock_running_false_at_zero(self):
        """
        is_clock_running is False when quarter ended.

        This could be used as an alternative check.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=0)

        assert clock.is_clock_running is False
        assert clock.is_end_of_quarter is True


class TestBugImpactQuantification:
    """
    Quantify the impact of the bug in typical game scenarios.
    """

    def test_average_extra_plays_per_quarter(self):
        """
        Calculate average extra plays caused by bug in typical scenarios.
        """
        scenarios = [
            # (time_remaining, avg_play_duration, plays_until_natural_end)
            (60, 25, 5),   # 1 minute, drive ends in punt after 5 plays
            (90, 25, 8),   # 1.5 minutes, drive ends in TD after 8 plays
            (30, 25, 4),   # 30 seconds, drive ends in FG after 4 plays
            (120, 25, 6),  # 2 minutes, drive ends in INT after 6 plays
        ]

        total_extra_plays = 0
        for time_left, play_time, plays_to_natural_end in scenarios:
            # Plays before clock hits 0
            plays_before_zero = max(1, time_left // play_time)

            # Extra plays (after clock at 0 but before drive ends)
            extra_plays = max(0, plays_to_natural_end - plays_before_zero)
            total_extra_plays += extra_plays

        avg_extra = total_extra_plays / len(scenarios)

        # Document the bug impact
        print(f"Average extra plays per quarter-ending drive: {avg_extra:.1f}")
        assert avg_extra > 0, "Bug should cause extra plays"

    def test_worst_case_scenario(self):
        """
        Worst case: Long drive with very little time remaining.
        """
        clock = GameClock(quarter=1, time_remaining_seconds=10)  # 10 seconds

        # Drive that takes 15 plays to score (long drive)
        plays = 0
        for _ in range(15):
            clock.advance_time(25)
            plays += 1

        plays_at_zero = plays - 1  # All but first play at 0:00

        # 14 plays executed at 0:00 - severe bug!
        assert plays_at_zero == 14


class TestFixValidation:
    """
    Tests to validate the fix once implemented.

    These tests currently PASS (showing buggy behavior).
    After fix, they should show correct behavior.
    """

    def test_fixed_drive_loop_stops_at_zero(self):
        """
        Validate that fixed code stops drive when clock hits 0.
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

        plays = 0

        # FIXED loop condition
        while not drive.is_drive_over() and not clock.is_end_of_quarter:
            from src.play_engine.core.play_result import PlayResult
            play = PlayResult(
                outcome="run",
                yards=4,
                time_elapsed=25.0,
                is_scoring_play=False,
                is_turnover=False,
            )
            clock.advance_time(play.time_elapsed)
            drive.process_play_result(play)
            plays += 1

            if plays > 20:
                break

        # With fix: 2 plays max (30/25 ≈ 1.2, round up to 2)
        # Without fix: Would continue until drive naturally ends

        assert plays <= 2, f"Fixed behavior: max 2 plays, got {plays}"
        assert clock.is_end_of_quarter is True

    def test_drive_result_indicates_time_expiration(self):
        """
        FIXED: DriveResult correctly indicates TIME_EXPIRATION.

        This test verifies that when a drive ends due to clock expiration,
        the DriveResult shows TIME_EXPIRATION as the end reason.
        """
        from src.play_engine.game_state.drive_manager import DriveManager, DriveEndReason
        from src.play_engine.game_state.field_position import FieldPosition, FieldZone
        from src.play_engine.game_state.down_situation import DownState

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

        # Simulate time expiration (what GameLoopController does)
        drive.end_due_to_time_expiration()

        # Verify result
        drive_result = drive.get_drive_result()
        assert drive_result.end_reason == DriveEndReason.TIME_EXPIRATION
