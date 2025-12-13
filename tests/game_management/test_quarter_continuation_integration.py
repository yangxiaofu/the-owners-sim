"""
Integration Tests for QuarterContinuationManager with GameLoopController

Tests that the QuarterContinuationManager is correctly integrated into
GameLoopController to preserve down state across quarter transitions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from game_management.quarter_continuation_manager import (
    QuarterContinuationManager, DriveEndState, ContinuationState
)
from play_engine.game_state.drive_manager import DriveEndReason


class TestQuarterContinuationIntegration:
    """Integration tests for QuarterContinuationManager in GameLoopController context."""

    def test_q1_end_captures_state_correctly(self):
        """Test that Q1 time expiration captures full down state."""
        manager = QuarterContinuationManager()

        # Simulate Q1 ending at 2nd & 7 on the 35 yard line
        end_state = DriveEndState(
            possessing_team_id=17,
            field_position=35,
            down=2,
            yards_to_go=7,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        # Verify continuation state
        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is True
        assert continuation.possessing_team_id == 17
        assert continuation.field_position == 35
        assert continuation.down == 2
        assert continuation.yards_to_go == 7
        assert continuation.reason == "quarter_continuation"

    def test_q3_end_captures_state_correctly(self):
        """Test that Q3 time expiration captures full down state."""
        manager = QuarterContinuationManager()

        # Simulate Q3 ending at 3rd & 1 on the 49 yard line
        end_state = DriveEndState(
            possessing_team_id=23,
            field_position=49,
            down=3,
            yards_to_go=1,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=3
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is True
        assert continuation.down == 3
        assert continuation.yards_to_go == 1
        assert continuation.field_position == 49

    def test_halftime_does_not_continue(self):
        """Test that halftime (Q2 end) does NOT preserve down state."""
        manager = QuarterContinuationManager()

        # Q2 ends (halftime)
        end_state = DriveEndState(
            possessing_team_id=17,
            field_position=45,
            down=2,
            yards_to_go=8,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=2
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False
        assert continuation.reason == "new_drive"
        # Default new drive values
        assert continuation.down == 1
        assert continuation.yards_to_go == 10

    def test_scoring_play_does_not_continue(self):
        """Test that scoring plays do NOT preserve down state (kickoff follows)."""
        manager = QuarterContinuationManager()

        # Touchdown in Q1
        end_state = DriveEndState(
            possessing_team_id=17,
            field_position=100,
            down=1,
            yards_to_go=5,
            end_reason=DriveEndReason.TOUCHDOWN,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_multiple_consecutive_quarter_transitions(self):
        """Test back-to-back quarter transitions (Q1→Q2, then Q3→Q4)."""
        manager = QuarterContinuationManager()

        # Q1 ends at 2nd & 8
        end_state_q1 = DriveEndState(
            possessing_team_id=17,
            field_position=40,
            down=2,
            yards_to_go=8,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state_q1)
        cont_q2 = manager.get_next_drive_state()

        assert cont_q2.should_continue is True
        assert cont_q2.down == 2
        assert cont_q2.yards_to_go == 8

        # Simulate several drives happening in Q2/Q3...

        # Q3 ends at 4th & 1
        end_state_q3 = DriveEndState(
            possessing_team_id=23,  # Different team
            field_position=55,
            down=4,
            yards_to_go=1,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=3
        )
        manager.capture_drive_end(end_state_q3)
        cont_q4 = manager.get_next_drive_state()

        assert cont_q4.should_continue is True
        assert cont_q4.down == 4
        assert cont_q4.yards_to_go == 1
        assert cont_q4.possessing_team_id == 23

    def test_continuation_only_happens_once(self):
        """Test that continuation state is consumed after first retrieval."""
        manager = QuarterContinuationManager()

        # Q1 ends
        end_state = DriveEndState(
            possessing_team_id=17,
            field_position=35,
            down=2,
            yards_to_go=7,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        # First retrieval - should continue
        cont1 = manager.get_next_drive_state()
        assert cont1.should_continue is True
        assert cont1.down == 2

        # Second retrieval - should NOT continue (state was cleared)
        cont2 = manager.get_next_drive_state()
        assert cont2.should_continue is False
        assert cont2.down == 1  # Default

    def test_interleaved_normal_and_continuation_drives(self):
        """Test normal drives don't interfere with quarter transitions."""
        manager = QuarterContinuationManager()

        # Normal drive ends with punt (no continuation)
        punt_state = DriveEndState(
            possessing_team_id=17,
            field_position=25,
            down=4,
            yards_to_go=15,
            end_reason=DriveEndReason.PUNT,
            quarter=1
        )
        manager.capture_drive_end(punt_state)

        cont1 = manager.get_next_drive_state()
        assert cont1.should_continue is False

        # Another drive ends at quarter end (should continue)
        time_exp_state = DriveEndState(
            possessing_team_id=23,
            field_position=50,
            down=3,
            yards_to_go=4,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(time_exp_state)

        cont2 = manager.get_next_drive_state()
        assert cont2.should_continue is True
        assert cont2.down == 3
        assert cont2.yards_to_go == 4


class TestAllDriveEndReasons:
    """Test all DriveEndReason values are handled correctly."""

    @pytest.fixture
    def manager(self):
        return QuarterContinuationManager()

    @pytest.mark.parametrize("end_reason,quarter,should_continue", [
        # Time expiration at Q1/Q3 - SHOULD continue
        (DriveEndReason.TIME_EXPIRATION, 1, True),
        (DriveEndReason.TIME_EXPIRATION, 3, True),

        # Time expiration at Q2/Q4 - should NOT continue
        (DriveEndReason.TIME_EXPIRATION, 2, False),
        (DriveEndReason.TIME_EXPIRATION, 4, False),

        # Scoring plays - should NOT continue (kickoff follows)
        (DriveEndReason.TOUCHDOWN, 1, False),
        (DriveEndReason.TOUCHDOWN, 3, False),
        (DriveEndReason.FIELD_GOAL, 1, False),
        (DriveEndReason.SAFETY, 1, False),

        # Possession changes - should NOT continue
        (DriveEndReason.PUNT, 1, False),
        (DriveEndReason.PUNT, 3, False),
        (DriveEndReason.TURNOVER_INTERCEPTION, 1, False),
        (DriveEndReason.TURNOVER_FUMBLE, 3, False),
        (DriveEndReason.TURNOVER_ON_DOWNS, 1, False),
    ])
    def test_drive_end_reason(self, manager, end_reason, quarter, should_continue):
        """Test each DriveEndReason is handled correctly."""
        end_state = DriveEndState(
            possessing_team_id=17,
            field_position=45,
            down=2,
            yards_to_go=8,
            end_reason=end_reason,
            quarter=quarter
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is should_continue, (
            f"DriveEndReason.{end_reason.name} at Q{quarter} should_continue={should_continue}"
        )
