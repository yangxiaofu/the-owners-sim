"""
Tests for down_situation module.

Tests the calculate_first_down_line helper function to prevent
regressions where first_down_line exceeds valid field range (0-100).
"""

import pytest
from play_engine.game_state.down_situation import calculate_first_down_line, DownState


class TestCalculateFirstDownLine:
    """Tests for first down line calculation helper."""

    def test_normal_case_own_territory(self):
        """Standard 1st and 10 in own territory."""
        assert calculate_first_down_line(25, 10) == 35
        assert calculate_first_down_line(50, 10) == 60

    def test_normal_case_opponent_territory(self):
        """Standard 1st and 10 in opponent territory."""
        assert calculate_first_down_line(60, 10) == 70
        assert calculate_first_down_line(75, 10) == 85

    def test_clamps_at_goal_line(self):
        """First down line cannot exceed 100 (goal line).

        This is the bug fix case - field_position + yards_to_go > 100.
        """
        # The original bug: 92 + 10 = 102 which caused ValueError
        assert calculate_first_down_line(92, 10) == 100
        assert calculate_first_down_line(95, 10) == 100
        assert calculate_first_down_line(99, 5) == 100
        assert calculate_first_down_line(91, 10) == 100

    def test_exactly_at_goal_line(self):
        """When calculation equals exactly 100."""
        assert calculate_first_down_line(90, 10) == 100
        assert calculate_first_down_line(95, 5) == 100

    def test_just_short_of_goal_line(self):
        """First down line just short of goal."""
        assert calculate_first_down_line(89, 10) == 99
        assert calculate_first_down_line(88, 10) == 98

    def test_already_at_goal_line(self):
        """Edge case: already at goal line (shouldn't happen in practice)."""
        assert calculate_first_down_line(100, 10) == 100

    def test_short_distance_near_goal(self):
        """1st and goal scenarios with short yardage."""
        assert calculate_first_down_line(98, 2) == 100
        assert calculate_first_down_line(97, 3) == 100
        assert calculate_first_down_line(99, 1) == 100

    def test_various_distances(self):
        """Different yards to go values."""
        assert calculate_first_down_line(50, 1) == 51   # 4th and 1
        assert calculate_first_down_line(50, 5) == 55   # 2nd and 5
        assert calculate_first_down_line(50, 15) == 65  # After penalty


class TestDownStateValidation:
    """Tests that DownState properly validates first_down_line.

    These tests verify the validation that catches invalid values,
    ensuring our calculate_first_down_line function prevents these errors.
    """

    def test_valid_first_down_line(self):
        """DownState accepts valid first_down_line values."""
        # Should not raise
        state = DownState(current_down=1, yards_to_go=10, first_down_line=35)
        assert state.first_down_line == 35

    def test_first_down_line_at_goal(self):
        """DownState accepts first_down_line=100 (goal line)."""
        state = DownState(current_down=1, yards_to_go=5, first_down_line=100)
        assert state.first_down_line == 100

    def test_invalid_first_down_line_over_100(self):
        """DownState rejects first_down_line > 100.

        This is the error that was being raised before the fix.
        """
        with pytest.raises(ValueError, match="Invalid first down line: 102"):
            DownState(current_down=1, yards_to_go=10, first_down_line=102)

    def test_invalid_first_down_line_negative(self):
        """DownState rejects negative first_down_line."""
        with pytest.raises(ValueError, match="Invalid first down line: -5"):
            DownState(current_down=1, yards_to_go=10, first_down_line=-5)


class TestIntegrationWithDownState:
    """Integration tests using calculate_first_down_line with DownState."""

    def test_calculate_then_create_state_normal(self):
        """Normal case: calculate first_down_line then create DownState."""
        first_down = calculate_first_down_line(25, 10)
        state = DownState(current_down=1, yards_to_go=10, first_down_line=first_down)
        assert state.first_down_line == 35

    def test_calculate_then_create_state_near_goal(self):
        """Near goal: calculate first_down_line then create DownState.

        This is the exact scenario that caused the original bug.
        """
        first_down = calculate_first_down_line(92, 10)
        # Should NOT raise ValueError thanks to min(100, ...) clamping
        state = DownState(current_down=1, yards_to_go=10, first_down_line=first_down)
        assert state.first_down_line == 100
