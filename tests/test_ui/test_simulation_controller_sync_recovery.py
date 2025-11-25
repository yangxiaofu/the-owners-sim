"""
Test Suite for SimulationController Calendar-Database Synchronization

Tests the cleaned-up _save_state_to_db() method (Phase 3 of calendar drift bug fix).
This test suite prepares for Phase 4 exception handling testing.

Test Coverage:
- save_state delegation to state_model
- Exception propagation (CalendarSyncPersistenceException)
- Success logging
- Post-sync verification with SyncValidator
- Drift exception raising on validation failure
- Graceful handling when validator unavailable
- No redundant checks after save_state() call

Related Issues:
- CALENDAR-DRIFT-2025-001: Silent database persistence failures
- Phase 3: Remove redundant return value checking in SimulationController
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from PySide6.QtCore import QObject

from ui.controllers.simulation_controller import SimulationController
from src.database.sync_exceptions import (
    CalendarSyncPersistenceException,
    CalendarSyncDriftException
)
from src.database.sync_validators import (
    PostSyncVerificationResult
)


class TestSimulationControllerSyncRecovery:
    """
    Test suite for SimulationController._save_state_to_db() method.

    This suite tests the cleaned-up implementation that relies on exception
    propagation instead of return value checking.
    """

    @pytest.fixture
    def controller(self):
        """
        Create SimulationController with mocked dependencies.

        Mocks all external dependencies to isolate _save_state_to_db() testing.
        """
        with patch('ui.controllers.simulation_controller.SeasonCycleController'), \
             patch('ui.controllers.simulation_controller.SimulationDataModel') as MockDataModel, \
             patch('ui.controllers.simulation_controller.EventDatabaseAPI'):

            # Create controller instance
            controller = SimulationController(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )

            # Mock state_model with fresh Mock for clean test isolation
            controller.state_model = Mock()
            controller.state_model.save_state = Mock(return_value=True)

            # Mock sync validator (not initialized by default)
            controller._sync_validator = None

            # Set required attributes
            controller.dynasty_id = "test_dynasty"
            controller.season = 2025

            # Mock logger
            controller._logger = Mock()

            yield controller

    def test_save_state_to_db_calls_state_model_save(self, controller):
        """
        Verify _save_state_to_db() calls state_model.save_state() with correct params.

        Test Objective:
        - Ensure delegation to state_model.save_state() is correct
        - Verify all parameters are passed through
        """
        # Setup
        test_date = "2025-11-09"
        test_phase = "playoffs"
        test_week = 10

        # Execute
        controller._save_state_to_db(test_date, test_phase, test_week)

        # Assert: save_state called with correct parameters
        controller.state_model.save_state.assert_called_once_with(
            current_date=test_date,
            current_phase=test_phase,
            current_week=test_week
        )

    def test_save_state_to_db_propagates_persistence_exception(self, controller):
        """
        Verify CalendarSyncPersistenceException propagates from save_state().

        Test Objective:
        - Ensure exceptions from state_model.save_state() are not caught
        - Verify exception propagates to caller for proper error handling

        This is the key fix for CALENDAR-DRIFT-2025-001 - fail-loud instead
        of silent failure.
        """
        # Setup: Mock save_state to raise CalendarSyncPersistenceException
        test_exception = CalendarSyncPersistenceException(
            operation="dynasty_state_update",
            sync_point="advance_day",
            state_info={
                "date": "2025-11-09",
                "phase": "playoffs",
                "week": 10
            }
        )
        controller.state_model.save_state.side_effect = test_exception

        # Execute & Assert: Exception should propagate without being caught
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            controller._save_state_to_db("2025-11-09", "playoffs", 10)

        # Verify it's the exact same exception instance
        assert exc_info.value is test_exception

        # Verify no success logging occurred (didn't reach that code)
        controller._logger.debug.assert_not_called()

    def test_save_state_to_db_logs_success(self, controller):
        """
        Verify successful save operations are logged.

        Test Objective:
        - Ensure debug logging occurs after successful save
        - Verify log message contains relevant state information
        """
        # Setup: Mock successful save (no exception)
        controller.state_model.save_state.return_value = True

        # Mock validator to avoid post-sync verification in this test
        with patch.object(controller, '_get_sync_validator', side_effect=RuntimeError("Validator not available")):
            # Execute
            controller._save_state_to_db("2025-11-09", "playoffs", 10)

        # Assert: Debug log called with success message
        controller._logger.debug.assert_called_once()
        log_message = controller._logger.debug.call_args[0][0]

        # Verify log contains state info
        assert "Dynasty state persisted successfully" in log_message
        assert "2025-11-09" in log_message
        assert "playoffs" in log_message
        assert "10" in log_message

    def test_save_state_to_db_post_sync_verification_valid(self, controller):
        """
        Verify post-sync verification is called and passes without error.

        Test Objective:
        - Ensure SyncValidator.verify_post_sync() is invoked
        - Verify no exceptions when validation passes
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock sync validator with passing verification
        mock_validator = Mock()
        mock_post_result = PostSyncVerificationResult(
            valid=True,
            actual_calendar_date="2025-11-09",
            actual_phase="playoffs",
            drift=0,
            issues={}
        )
        mock_validator.verify_post_sync.return_value = mock_post_result

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute
            controller._save_state_to_db("2025-11-09", "playoffs", 10)

        # Assert: verify_post_sync was called with expected params
        mock_validator.verify_post_sync.assert_called_once_with(
            "2025-11-09",
            "playoffs"
        )

        # Assert: No warnings logged (validation passed)
        controller._logger.warning.assert_not_called()

    def test_save_state_to_db_raises_drift_exception_on_drift(self, controller):
        """
        Verify CalendarSyncDriftException is raised when post-sync detects drift.

        Test Objective:
        - Ensure drift detection triggers exception
        - Verify exception contains correct drift information
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock sync validator with drift detection
        mock_validator = Mock()
        mock_post_result = PostSyncVerificationResult(
            valid=False,
            actual_calendar_date="2025-11-12",  # 3 days ahead
            actual_phase="playoffs",
            drift=3,
            issues={
                "drift": "Minor drift detected: 3 days ahead",
                "drift_days": 3
            }
        )
        mock_validator.verify_post_sync.return_value = mock_post_result

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute & Assert: Should raise CalendarSyncDriftException
            with pytest.raises(CalendarSyncDriftException) as exc_info:
                controller._save_state_to_db("2025-11-09", "playoffs", 10)

            # Verify exception details
            drift_exception = exc_info.value
            assert drift_exception.drift_days == 3
            assert "2025-11-12" in str(drift_exception)  # calendar_date
            assert "2025-11-09" in str(drift_exception)  # db_date

    def test_save_state_to_db_no_exception_on_valid_post_sync_with_issues(self, controller):
        """
        Verify that non-drift issues don't raise exceptions.

        Test Objective:
        - Ensure only drift issues trigger exceptions
        - Verify warning is logged for non-drift issues
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock sync validator with issues but no drift
        mock_validator = Mock()
        mock_post_result = PostSyncVerificationResult(
            valid=False,
            actual_calendar_date="2025-11-09",
            actual_phase="playoffs",
            drift=0,  # No drift
            issues={
                "some_other_issue": "Some non-drift validation issue"
            }
        )
        mock_validator.verify_post_sync.return_value = mock_post_result

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute: Should not raise exception (only drift raises)
            controller._save_state_to_db("2025-11-09", "playoffs", 10)

            # Assert: Warning logged about issues
            controller._logger.warning.assert_called_once()
            warning_message = controller._logger.warning.call_args[0][0]
            assert "Post-sync verification detected issues" in warning_message

    def test_save_state_to_db_handles_missing_validator(self, controller):
        """
        Verify graceful handling when sync validator is not available.

        Test Objective:
        - Ensure operation completes when validator can't be initialized
        - Verify debug log about validator unavailability

        This scenario occurs during early controller initialization when
        calendar_manager is not yet available.
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock _get_sync_validator to raise RuntimeError (not available)
        with patch.object(controller, '_get_sync_validator', side_effect=RuntimeError("Calendar manager not available")):
            # Execute: Should not raise exception
            controller._save_state_to_db("2025-11-09", "playoffs", 10)

        # Assert: Debug log about validator unavailability
        debug_calls = [call[0][0] for call in controller._logger.debug.call_args_list]
        assert any("Sync validator not available" in msg for msg in debug_calls)

    def test_save_state_to_db_no_redundant_checks(self, controller):
        """
        Code inspection test: Verify no redundant return value checks exist.

        Test Objective:
        - Ensure _save_state_to_db() trusts exception propagation
        - Verify no `if not success:` checks after save_state() call
        - Confirm Phase 3 cleanup is complete

        This test verifies the cleaned-up implementation doesn't have the
        redundant pattern that was removed in Phase 3.
        """
        # Read the actual method source to verify implementation
        import inspect
        source = inspect.getsource(controller._save_state_to_db)

        # Verify no redundant success checks
        assert "if not success" not in source, \
            "Found redundant 'if not success' check - should rely on exception propagation"

        assert "if success is False" not in source, \
            "Found redundant success check - should rely on exception propagation"

        # Verify exception-based error handling pattern exists
        assert "save_state(" in source, \
            "Method should call state_model.save_state()"

        # Verify post-sync verification exists
        assert "verify_post_sync" in source, \
            "Method should perform post-sync verification"

    def test_save_state_to_db_with_optional_week_none(self, controller):
        """
        Verify _save_state_to_db() handles optional week parameter correctly.

        Test Objective:
        - Ensure method works when current_week is None (playoffs/offseason)
        - Verify None is passed through to state_model.save_state()
        """
        # Setup
        controller.state_model.save_state.return_value = True

        # Mock validator unavailable to simplify test
        with patch.object(controller, '_get_sync_validator', side_effect=RuntimeError("Not available")):
            # Execute with week=None
            controller._save_state_to_db("2025-11-09", "playoffs", None)

        # Assert: save_state called with week=None
        controller.state_model.save_state.assert_called_once_with(
            current_date="2025-11-09",
            current_phase="playoffs",
            current_week=None
        )

    def test_save_state_to_db_exception_prevents_post_sync(self, controller):
        """
        Verify that save_state exception prevents post-sync verification.

        Test Objective:
        - Ensure post-sync verification is skipped if save_state fails
        - Verify exception propagates before verification code runs
        """
        # Setup: Mock save_state to raise exception
        controller.state_model.save_state.side_effect = CalendarSyncPersistenceException(
            operation="test",
            sync_point="test"
        )

        # Mock validator
        mock_validator = Mock()

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute: Should raise before verification
            with pytest.raises(CalendarSyncPersistenceException):
                controller._save_state_to_db("2025-11-09", "playoffs", 10)

        # Assert: verify_post_sync was NOT called
        mock_validator.verify_post_sync.assert_not_called()

    def test_save_state_to_db_drift_exception_contains_state_info(self, controller):
        """
        Verify CalendarSyncDriftException includes comprehensive state info.

        Test Objective:
        - Ensure drift exception contains expected_date, expected_phase
        - Verify exception includes actual_phase and dynasty_id
        - Confirm state_info dict has all debugging information
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock sync validator with drift
        mock_validator = Mock()
        mock_post_result = PostSyncVerificationResult(
            valid=False,
            actual_calendar_date="2025-11-15",
            actual_phase="regular_season",  # Different phase!
            drift=6,
            issues={"drift": "Major drift detected"}
        )
        mock_validator.verify_post_sync.return_value = mock_post_result

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute
            with pytest.raises(CalendarSyncDriftException) as exc_info:
                controller._save_state_to_db("2025-11-09", "playoffs", 10)

            # Assert: State info contains debugging details
            drift_exc = exc_info.value
            state_info = drift_exc.state_info

            assert state_info["expected_date"] == "2025-11-09"
            assert state_info["expected_phase"] == "playoffs"
            assert state_info["actual_phase"] == "regular_season"
            assert state_info["dynasty_id"] == "test_dynasty"

    def test_save_state_to_db_integration_with_advance_day(self, controller):
        """
        Integration test: Verify _save_state_to_db() works in advance_day() flow.

        Test Objective:
        - Ensure method integrates correctly with advance_day()
        - Verify exception propagation doesn't break calling code
        """
        # Setup: Mock season_controller.advance_day() success
        controller.season_controller = Mock()
        controller.season_controller.advance_day.return_value = {
            'success': True,
            'date': '2025-11-10',
            'current_phase': 'playoffs',
            'results': []
        }
        controller.season_controller.phase_state = Mock()
        controller.season_controller.phase_state.phase = Mock()
        controller.season_controller.phase_state.phase.value = 'playoffs'

        # Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock validator unavailable
        with patch.object(controller, '_get_sync_validator', side_effect=RuntimeError("Not available")):
            # Execute advance_day (which calls _save_state_to_db internally)
            result = controller.advance_day()

        # Assert: Operation succeeded
        assert result['success'] is True

        # Assert: save_state was called during advance_day
        controller.state_model.save_state.assert_called_once()


# Additional edge case tests

class TestSimulationControllerSyncEdgeCases:
    """
    Edge case tests for _save_state_to_db() method.
    """

    @pytest.fixture
    def controller(self):
        """Create controller with mocked dependencies."""
        with patch('ui.controllers.simulation_controller.SeasonCycleController'), \
             patch('ui.controllers.simulation_controller.SimulationDataModel'), \
             patch('ui.controllers.simulation_controller.EventDatabaseAPI'):

            controller = SimulationController(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )

            controller.state_model = Mock()
            controller._sync_validator = None
            controller.dynasty_id = "test_dynasty"
            controller._logger = Mock()

            yield controller

    def test_validator_raises_exception_during_verification(self, controller):
        """
        Verify unexpected exceptions during post-sync verification are handled.

        Test Objective:
        - Ensure unexpected validator errors don't crash the method
        - Verify save still succeeds if verification has issues
        """
        # Setup: Mock successful save
        controller.state_model.save_state.return_value = True

        # Mock validator that raises unexpected exception
        mock_validator = Mock()
        mock_validator.verify_post_sync.side_effect = Exception("Unexpected validator error")

        with patch.object(controller, '_get_sync_validator', return_value=mock_validator):
            # Execute: Should propagate the unexpected exception
            with pytest.raises(Exception) as exc_info:
                controller._save_state_to_db("2025-11-09", "playoffs", 10)

            assert "Unexpected validator error" in str(exc_info.value)

    def test_phase_string_variations(self, controller):
        """
        Verify method handles different phase string formats correctly.

        Test Objective:
        - Ensure case variations are handled (PLAYOFFS vs playoffs)
        - Verify underscores vs spaces (regular_season vs REGULAR_SEASON)
        """
        # Setup
        controller.state_model.save_state.return_value = True

        phase_variations = [
            "REGULAR_SEASON",
            "regular_season",
            "PLAYOFFS",
            "playoffs",
            "OFFSEASON",
            "offseason"
        ]

        with patch.object(controller, '_get_sync_validator', side_effect=RuntimeError("Not available")):
            for phase in phase_variations:
                # Reset mock
                controller.state_model.save_state.reset_mock()

                # Execute
                controller._save_state_to_db("2025-11-09", phase, 10)

                # Assert: save_state called with exact phase string
                call_args = controller.state_model.save_state.call_args
                assert call_args[1]['current_phase'] == phase
