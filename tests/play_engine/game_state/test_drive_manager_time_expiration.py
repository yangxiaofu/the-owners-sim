"""
Tests for DriveManager Time Expiration Handling

Phase 1 Unit Tests - Diagnostic tests to confirm DriveManager doesn't
handle time expiration, which is the root cause of the clock bug.

Bug Context:
DriveManager.is_drive_over() only checks play outcomes (TD, punt, turnover).
It does NOT check for TIME_EXPIRATION, even though that DriveEndReason exists.
This means drives continue even after the quarter clock hits 0:00.

Key Finding:
The TIME_EXPIRATION enum value exists in DriveEndReason but is NEVER used.
DriveManager has no awareness of game clock - it's purely outcome-based.
"""

import pytest
from src.play_engine.game_state.drive_manager import (
    DriveManager,
    DriveEndReason,
    DriveStats,
)
from src.play_engine.game_state.down_situation import DownState
from src.play_engine.game_state.field_position import FieldPosition, FieldZone
from src.play_engine.core.play_result import PlayResult


def create_test_drive(
    down: int = 1,
    distance: int = 10,
    yard_line: int = 25,
    team_id: int = 1
) -> DriveManager:
    """
    Helper to create a DriveManager at specified game situation.

    Args:
        down: Current down (1-4)
        distance: Yards to go for first down
        yard_line: Current field position (0-100)
        team_id: Possessing team ID (1-32)

    Returns:
        DriveManager initialized with specified situation
    """
    starting_position = FieldPosition(
        yard_line=yard_line,
        possession_team=team_id,
        field_zone=FieldZone.OWN_TERRITORY if yard_line < 50 else FieldZone.OPPONENT_TERRITORY
    )
    down_state = DownState(
        current_down=down,
        yards_to_go=distance,
        first_down_line=min(yard_line + distance, 100)
    )
    return DriveManager(starting_position, down_state, team_id)


class TestTimeExpirationEnumExists:
    """Verify TIME_EXPIRATION exists in DriveEndReason."""

    def test_time_expiration_enum_exists(self):
        """Confirm TIME_EXPIRATION is a valid DriveEndReason."""
        assert hasattr(DriveEndReason, "TIME_EXPIRATION")
        assert DriveEndReason.TIME_EXPIRATION.value == "time_expiration"

    def test_all_drive_end_reasons(self):
        """Document all possible drive end reasons."""
        expected_reasons = {
            "TOUCHDOWN",
            "FIELD_GOAL",
            "FIELD_GOAL_MISSED",
            "SAFETY",
            "TURNOVER_INTERCEPTION",
            "TURNOVER_FUMBLE",
            "TURNOVER_ON_DOWNS",
            "PUNT",
            "TIME_EXPIRATION",
        }
        actual_reasons = {reason.name for reason in DriveEndReason}
        assert expected_reasons == actual_reasons


class TestDriveManagerNoTimeAwareness:
    """
    DIAGNOSTIC: Prove that DriveManager has no time awareness.

    These tests document the current (buggy) behavior where DriveManager
    doesn't know or care about game clock state.
    """

    def test_drive_manager_has_no_clock_reference(self):
        """
        Verify DriveManager doesn't store or reference game clock.

        DriveManager is intentionally decoupled from game clock (per design).
        This test documents that the clock check must happen at a higher level.
        """
        drive = create_test_drive()

        # DriveManager has no clock-related attributes
        assert not hasattr(drive, "game_clock")
        assert not hasattr(drive, "time_remaining")
        assert not hasattr(drive, "quarter")
        assert not hasattr(drive, "clock")

    def test_is_drive_over_ignores_time(self):
        """
        BUG CONFIRMATION: is_drive_over() only checks drive_ended flag.

        The drive_ended flag is only set by _end_drive() which is called
        for play outcomes (TD, punt, etc.) but NEVER for time expiration.
        """
        drive = create_test_drive()

        # Fresh drive - not over
        assert drive.is_drive_over() is False
        assert drive.drive_ended is False

        # Run a normal play that doesn't end drive
        play = PlayResult(
            outcome="run",
            yards=5,
            time_elapsed=25.0,  # Clock would have advanced
            is_scoring_play=False,
            is_turnover=False,
        )
        drive.process_play_result(play)

        # Drive still not over (even if clock were at 0:00)
        assert drive.is_drive_over() is False

    def test_drive_continues_after_simulated_clock_expiration(self):
        """
        Simulate what happens when clock should be at 0:00.

        This test shows that even if we know clock is expired,
        DriveManager will happily keep processing plays.
        """
        drive = create_test_drive(down=1, distance=10, yard_line=25)

        # Simulate 3 plays that would total more than 15 minutes
        # (In reality, this would mean clock expired mid-drive)
        for i in range(3):
            play = PlayResult(
                outcome="incomplete",
                yards=0,
                time_elapsed=320.0,  # 5+ minutes per play (unrealistic but proves point)
                is_scoring_play=False,
                is_turnover=False,
            )
            drive.process_play_result(play)

        # Total time: 3 * 320 = 960 seconds = 16 minutes
        # But DriveManager doesn't care!
        assert drive.stats.time_of_possession_seconds == 960.0
        assert drive.is_drive_over() is False  # Still going!
        assert drive.stats.plays_run == 3

    def test_time_expiration_never_set_as_end_reason(self):
        """
        Document that TIME_EXPIRATION is never used as a drive end reason.

        Run various plays and verify TIME_EXPIRATION is never the reason.
        """
        # Test various drive-ending scenarios
        scenarios = [
            # (play_result_kwargs, expected_end_reason)
            ({"is_punt": True}, DriveEndReason.PUNT),
            ({"is_turnover": True, "turnover_type": "interception"},
             DriveEndReason.TURNOVER_INTERCEPTION),
            ({"is_turnover": True, "turnover_type": "fumble"},
             DriveEndReason.TURNOVER_FUMBLE),
            ({"is_scoring_play": True, "points": 6},
             DriveEndReason.TOUCHDOWN),
            ({"is_scoring_play": True, "points": 3},
             DriveEndReason.FIELD_GOAL),
        ]

        for play_kwargs, expected_reason in scenarios:
            drive = create_test_drive()
            play = PlayResult(
                outcome="test",
                yards=0,
                time_elapsed=25.0,
                **play_kwargs
            )
            drive.process_play_result(play)

            assert drive.is_drive_over() is True
            assert drive.end_reason == expected_reason
            assert drive.end_reason != DriveEndReason.TIME_EXPIRATION


class TestExpectedBehavior:
    """
    Verify TIME_EXPIRATION behavior after bug fix.

    These tests verify the fix is working correctly.
    """

    def test_drive_should_have_time_expiration_method(self):
        """
        FIXED: DriveManager now has a method to end drive on time expiration.

        This is called by GameLoopController when clock hits 0:00.
        """
        drive = create_test_drive()

        # Method now exists and works
        drive.end_due_to_time_expiration()
        assert drive.is_drive_over() is True
        assert drive.end_reason == DriveEndReason.TIME_EXPIRATION

    def test_drive_result_should_indicate_time_expiration(self):
        """
        FIXED: DriveResult correctly indicates TIME_EXPIRATION reason.

        When a drive ends due to clock expiration, the result shows
        TIME_EXPIRATION as the end reason.
        """
        drive = create_test_drive()

        # End due to time expiration
        drive.end_due_to_time_expiration()

        # Get drive result
        result = drive.get_drive_result()

        # Verify result
        assert result.drive_ended is True
        assert result.end_reason == DriveEndReason.TIME_EXPIRATION

    def test_time_expiration_only_sets_once(self):
        """
        Verify end_due_to_time_expiration() is idempotent.

        Calling it multiple times should not change the result.
        """
        drive = create_test_drive()

        # End due to time expiration
        drive.end_due_to_time_expiration()
        assert drive.end_reason == DriveEndReason.TIME_EXPIRATION

        # Call again - should not change anything
        drive.end_due_to_time_expiration()
        assert drive.end_reason == DriveEndReason.TIME_EXPIRATION

    def test_time_expiration_does_not_override_natural_end(self):
        """
        Verify time expiration doesn't override a natural drive end.

        If drive already ended (TD, punt, etc.), time expiration is ignored.
        """
        drive = create_test_drive()

        # End drive with a touchdown play
        td_play = PlayResult(
            outcome="run",
            yards=75,
            time_elapsed=10.0,
            is_scoring_play=True,
            points=6,
            is_turnover=False,
        )
        drive.process_play_result(td_play)

        # Drive ended with TD
        assert drive.is_drive_over() is True
        assert drive.end_reason == DriveEndReason.TOUCHDOWN

        # Try to set time expiration - should be ignored
        drive.end_due_to_time_expiration()

        # Should still be TD, not time expiration
        assert drive.end_reason == DriveEndReason.TOUCHDOWN


class TestDriveSituationTimeContext:
    """Test that DriveSituation can receive time context from external source."""

    def test_situation_accepts_time_context(self):
        """
        Verify DriveSituation accepts external time context.

        This is how time info SHOULD flow - from GameManager to DriveManager
        via get_current_situation(game_context).
        """
        drive = create_test_drive()

        # Get situation with time context
        game_context = {
            "time_remaining": 130,  # 2:10 left (more than 2 minutes)
            "quarter": 1,
            "score_differential": -7
        }
        situation = drive.get_current_situation(game_context)

        assert situation.time_remaining == 130
        assert situation.quarter == 1
        assert situation.is_two_minute_warning is False  # > 120 seconds

    def test_situation_detects_two_minute_warning(self):
        """Test DriveSituation correctly identifies two-minute warning."""
        drive = create_test_drive()

        game_context = {"time_remaining": 90}  # 1:30 left
        situation = drive.get_current_situation(game_context)

        assert situation.is_two_minute_warning is True

    def test_situation_without_time_context(self):
        """Test DriveSituation handles missing time context gracefully."""
        drive = create_test_drive()

        # No game context provided
        situation = drive.get_current_situation(None)

        assert situation.time_remaining is None
        assert situation.is_two_minute_warning is False


class TestStatsTrackingIncludesTime:
    """Verify DriveStats tracks time of possession correctly."""

    def test_time_of_possession_accumulated(self):
        """Test that time_of_possession_seconds accumulates from plays."""
        drive = create_test_drive()

        # Run several plays with varying times
        times = [25.0, 30.0, 15.0, 40.0]
        for t in times:
            play = PlayResult(
                outcome="run",
                yards=3,
                time_elapsed=t,
                is_scoring_play=False,
                is_turnover=False,
            )
            drive.process_play_result(play)

        assert drive.stats.time_of_possession_seconds == sum(times)
        assert drive.stats.time_of_possession_seconds == 110.0

    def test_time_accumulated_even_on_zero_yard_plays(self):
        """Test that incomplete passes still consume time."""
        drive = create_test_drive()

        play = PlayResult(
            outcome="incomplete",
            yards=0,
            time_elapsed=6.0,  # Incomplete pass ~6 seconds
            is_scoring_play=False,
            is_turnover=False,
        )
        drive.process_play_result(play)

        assert drive.stats.time_of_possession_seconds == 6.0
