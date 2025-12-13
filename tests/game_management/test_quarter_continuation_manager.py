"""
Unit tests for QuarterContinuationManager

Tests quarter transition logic in isolation:
- Q1→Q2: Drive continues with preserved down/distance
- Q2→Q3: Halftime - new drive (kickoff)
- Q3→Q4: Drive continues with preserved down/distance
- Touchdowns, punts, turnovers: Do NOT continue
"""

import pytest
from game_management.quarter_continuation_manager import (
    QuarterContinuationManager, DriveEndState, ContinuationState
)
from play_engine.game_state.drive_manager import DriveEndReason


class TestQuarterContinuationManager:
    """Tests for QuarterContinuationManager"""

    def test_q1_time_expiration_continues_drive(self):
        """Q1 time expiration should preserve down state for Q2"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=35,
            down=2,
            yards_to_go=7,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is True
        assert continuation.down == 2
        assert continuation.yards_to_go == 7
        assert continuation.field_position == 35
        assert continuation.possessing_team_id == 1
        assert continuation.reason == "quarter_continuation"

    def test_q3_time_expiration_continues_drive(self):
        """Q3 time expiration should preserve down state for Q4"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=2,
            field_position=49,
            down=3,
            yards_to_go=4,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=3
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is True
        assert continuation.down == 3
        assert continuation.yards_to_go == 4
        assert continuation.field_position == 49
        assert continuation.possessing_team_id == 2

    def test_q2_time_expiration_does_not_continue(self):
        """Q2 end (halftime) should NOT continue drive - kickoff instead"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=40,
            down=2,
            yards_to_go=5,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=2
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False
        assert continuation.reason == "new_drive"

    def test_q4_time_expiration_does_not_continue(self):
        """Q4 end (game over) should NOT continue drive"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=50,
            down=1,
            yards_to_go=10,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=4
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_touchdown_does_not_continue(self):
        """Touchdown at any quarter should NOT continue - kickoff instead"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=100,
            down=1,
            yards_to_go=5,
            end_reason=DriveEndReason.TOUCHDOWN,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_field_goal_does_not_continue(self):
        """Field goal should NOT continue - kickoff instead"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=70,
            down=4,
            yards_to_go=3,
            end_reason=DriveEndReason.FIELD_GOAL,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_punt_does_not_continue(self):
        """Punt should NOT continue - possession changes"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=30,
            down=4,
            yards_to_go=15,
            end_reason=DriveEndReason.PUNT,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_interception_does_not_continue(self):
        """Interception should NOT continue - possession changes"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=50,
            down=2,
            yards_to_go=8,
            end_reason=DriveEndReason.TURNOVER_INTERCEPTION,
            quarter=3
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_fumble_does_not_continue(self):
        """Fumble should NOT continue - possession changes"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=2,
            field_position=45,
            down=1,
            yards_to_go=10,
            end_reason=DriveEndReason.TURNOVER_FUMBLE,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_turnover_on_downs_does_not_continue(self):
        """Turnover on downs should NOT continue - possession changes"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=60,
            down=4,
            yards_to_go=2,
            end_reason=DriveEndReason.TURNOVER_ON_DOWNS,
            quarter=3
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_safety_does_not_continue(self):
        """Safety should NOT continue - possession changes via free kick"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=1,
            down=3,
            yards_to_go=15,
            end_reason=DriveEndReason.SAFETY,
            quarter=2
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.should_continue is False

    def test_continuation_cleared_after_retrieval(self):
        """Continuation state should be cleared after get_next_drive_state()"""
        manager = QuarterContinuationManager()

        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=35,
            down=2,
            yards_to_go=7,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state)

        # First call returns continuation
        cont1 = manager.get_next_drive_state()
        assert cont1.should_continue is True

        # Second call returns default (continuation was cleared)
        cont2 = manager.get_next_drive_state()
        assert cont2.should_continue is False
        assert cont2.down == 1
        assert cont2.yards_to_go == 10

    def test_has_pending_continuation(self):
        """has_pending_continuation should accurately report state"""
        manager = QuarterContinuationManager()

        # Initially no continuation
        assert manager.has_pending_continuation() is False

        # After Q1 time expiration, should have continuation
        end_state = DriveEndState(
            possessing_team_id=1,
            field_position=35,
            down=2,
            yards_to_go=7,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=1
        )
        manager.capture_drive_end(end_state)
        assert manager.has_pending_continuation() is True

        # After retrieval, should be cleared
        manager.get_next_drive_state()
        assert manager.has_pending_continuation() is False

    def test_new_drive_default_values(self):
        """New drive should have 1st & 10 with specified field position"""
        manager = QuarterContinuationManager()

        # No capture_drive_end called, should return new drive defaults
        continuation = manager.get_next_drive_state(default_field_position=30)

        assert continuation.should_continue is False
        assert continuation.down == 1
        assert continuation.yards_to_go == 10
        assert continuation.field_position == 30
        assert continuation.reason == "new_drive"

    def test_consecutive_quarters_q1_q3(self):
        """Both Q1 and Q3 time expirations should continue their respective drives"""
        manager = QuarterContinuationManager()

        # Q1 end
        end_state_q1 = DriveEndState(
            possessing_team_id=1,
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

        # Q3 end (after halftime, new drive ended with time expiration)
        end_state_q3 = DriveEndState(
            possessing_team_id=2,
            field_position=55,
            down=3,
            yards_to_go=2,
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=3
        )
        manager.capture_drive_end(end_state_q3)
        cont_q4 = manager.get_next_drive_state()
        assert cont_q4.should_continue is True
        assert cont_q4.down == 3
        assert cont_q4.possessing_team_id == 2

    def test_drive_ending_normally_then_time_expires(self):
        """If a drive ends normally (TD, punt, etc.) before quarter ends, no continuation"""
        manager = QuarterContinuationManager()

        # Drive ends with touchdown mid-quarter
        td_state = DriveEndState(
            possessing_team_id=1,
            field_position=100,
            down=1,
            yards_to_go=3,
            end_reason=DriveEndReason.TOUCHDOWN,
            quarter=1
        )
        manager.capture_drive_end(td_state)

        # Should NOT continue (new kickoff)
        continuation = manager.get_next_drive_state()
        assert continuation.should_continue is False

    def test_preserves_all_state_fields(self):
        """All state fields should be preserved exactly"""
        manager = QuarterContinuationManager()

        # Specific values to verify
        end_state = DriveEndState(
            possessing_team_id=17,  # Specific team
            field_position=73,     # Specific position
            down=4,                # 4th down
            yards_to_go=1,         # Short yardage
            end_reason=DriveEndReason.TIME_EXPIRATION,
            quarter=3
        )
        manager.capture_drive_end(end_state)

        continuation = manager.get_next_drive_state()

        assert continuation.possessing_team_id == 17
        assert continuation.field_position == 73
        assert continuation.down == 4
        assert continuation.yards_to_go == 1
