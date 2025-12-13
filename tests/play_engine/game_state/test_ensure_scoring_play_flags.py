"""
Tests for ensure_scoring_play_flags helper function.

This helper reconciles any mismatch between the play engine's touchdown
detection and DriveManager's field position detection (the SSOT).
"""

import pytest
from play_engine.game_state.drive_manager import ensure_scoring_play_flags
from play_engine.core.play_result import PlayResult


class TestEnsureScoringPlayFlags:
    """Tests for scoring flag reconciliation helper."""

    def test_backfills_missing_td_flags(self):
        """Should set is_scoring_play=True and points=6 for missed TD."""
        play = PlayResult(outcome='run', yards=10, is_scoring_play=False, points=0)
        ensure_scoring_play_flags(play, 6)
        assert play.is_scoring_play is True
        assert play.points == 6

    def test_no_change_when_already_correct(self):
        """Should not modify already-correct play."""
        play = PlayResult(outcome='run', yards=10, is_scoring_play=True, points=6)
        ensure_scoring_play_flags(play, 6)
        assert play.is_scoring_play is True
        assert play.points == 6

    def test_corrects_wrong_points(self):
        """Should fix points mismatch."""
        play = PlayResult(outcome='run', yards=10, is_scoring_play=True, points=3)
        ensure_scoring_play_flags(play, 6)
        assert play.points == 6

    def test_corrects_missing_scoring_flag_with_correct_points(self):
        """Should fix missing is_scoring_play even if points are correct."""
        play = PlayResult(outcome='run', yards=10, is_scoring_play=False, points=6)
        ensure_scoring_play_flags(play, 6)
        assert play.is_scoring_play is True
        assert play.points == 6

    def test_field_goal_points(self):
        """Should work for field goals too."""
        play = PlayResult(outcome='field_goal_made', yards=0, is_scoring_play=False, points=0)
        ensure_scoring_play_flags(play, 3)
        assert play.is_scoring_play is True
        assert play.points == 3

    def test_pass_completion_td(self):
        """Should work for pass completion touchdowns."""
        play = PlayResult(outcome='completion', yards=35, is_scoring_play=False, points=0)
        ensure_scoring_play_flags(play, 6)
        assert play.is_scoring_play is True
        assert play.points == 6

    def test_incomplete_pass_not_modified_to_td(self):
        """Incomplete passes should still get TD flags if DriveManager detected TD.

        This is a defensive case - normally shouldn't happen, but if field
        position says TD, we trust it.
        """
        play = PlayResult(outcome='incomplete', yards=0, is_scoring_play=False, points=0)
        ensure_scoring_play_flags(play, 6)
        assert play.is_scoring_play is True
        assert play.points == 6

    def test_preserves_other_fields(self):
        """Should not modify other PlayResult fields."""
        play = PlayResult(
            outcome='run',
            yards=15,
            time_elapsed=5.5,
            is_scoring_play=False,
            points=0,
            is_turnover=False,
            achieved_first_down=True
        )
        ensure_scoring_play_flags(play, 6)

        # Verify modified fields
        assert play.is_scoring_play is True
        assert play.points == 6

        # Verify preserved fields
        assert play.outcome == 'run'
        assert play.yards == 15
        assert play.time_elapsed == 5.5
        assert play.is_turnover is False
        assert play.achieved_first_down is True
