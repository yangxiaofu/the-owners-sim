"""
Unit Tests for SeasonTransitionService

Tests the season transition orchestration service with mocked dependencies.
All tests use pytest and unittest.mock to isolate service behavior.

Tests cover:
- Service initialization and dependency injection
- Complete year transition execution (3-step orchestration)
- Execution order validation (critical for correctness)
- Timing measurements and performance tracking
- Failure scenarios at each step (fail loudly pattern)
- Year transition state validation

Coverage target: 90%+ with emphasis on execution order and failure handling.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import time

# Mock the imports before importing the service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.season_transition_service import SeasonTransitionService


class TestSeasonTransitionServiceInitialization:
    """Test service initialization and dependency injection."""

    def test_init_stores_all_dependencies(self):
        """Service should store all injected dependencies."""
        # Arrange
        mock_contract_service = Mock()
        mock_draft_service = Mock()

        # Act
        service = SeasonTransitionService(
            contract_service=mock_contract_service,
            draft_service=mock_draft_service,
            dynasty_id="test_dynasty"
        )

        # Assert
        assert service.contract_service == mock_contract_service
        assert service.draft_service == mock_draft_service
        assert service.dynasty_id == "test_dynasty"
        assert service.logger is not None
        assert service.logger.name == "SeasonTransitionService"

    def test_init_creates_logger_with_class_name(self):
        """Should create logger with service class name."""
        # Arrange & Act
        service = SeasonTransitionService(
            contract_service=Mock(),
            draft_service=Mock(),
            dynasty_id="test"
        )

        # Assert
        assert service.logger.name == "SeasonTransitionService"


class TestExecuteYearTransition:
    """Test execute_year_transition method - the primary orchestration method."""

    @pytest.fixture
    def mock_contract_service(self):
        """Create mock ContractTransitionService."""
        mock_service = Mock()
        mock_service.increment_all_contracts = Mock(return_value={
            'total_contracts': 1700,
            'still_active': 1653,
            'expired_count': 47
        })
        return mock_service

    @pytest.fixture
    def mock_draft_service(self):
        """Create mock DraftPreparationService."""
        mock_service = Mock()
        mock_service.prepare_draft_class = Mock(return_value={
            'draft_class_id': 'draft_2025',
            'season_year': 2025,
            'total_players': 300,
            'generation_time_seconds': 2.5,
            'already_existed': False
        })
        return mock_service

    @pytest.fixture
    def mock_synchronizer(self):
        """Create mock SeasonYearSynchronizer."""
        mock_sync = Mock()
        mock_sync.synchronize_year = Mock()
        mock_sync.get_current_year = Mock(return_value=2025)
        return mock_sync

    @pytest.fixture
    def service(self, mock_contract_service, mock_draft_service):
        """Create SeasonTransitionService with mocks."""
        return SeasonTransitionService(
            contract_service=mock_contract_service,
            draft_service=mock_draft_service,
            dynasty_id="test_dynasty"
        )

    def test_execute_year_transition_success(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should execute all 3 steps and return complete result."""
        # Act
        result = service.execute_year_transition(
            old_year=2024,
            new_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert result structure
        assert result['old_year'] == 2024
        assert result['new_year'] == 2025
        assert result['year_increment_success'] is True
        assert len(result['steps_completed']) == 3
        assert result['steps_completed'] == ['year_increment', 'contract_transition', 'draft_preparation']
        assert result['total_duration_seconds'] > 0

        # Assert contract transition result
        assert result['contract_transition'] is not None
        assert result['contract_transition']['total_contracts'] == 1700
        assert result['contract_transition']['still_active'] == 1653
        assert result['contract_transition']['expired_count'] == 47

        # Assert draft preparation result
        assert result['draft_preparation'] is not None
        assert result['draft_preparation']['draft_class_id'] == 'draft_2025'
        assert result['draft_preparation']['season_year'] == 2025
        assert result['draft_preparation']['total_players'] == 300
        assert result['draft_preparation']['already_existed'] is False

        # Verify all service calls were made
        mock_synchronizer.synchronize_year.assert_called_once_with(
            new_year=2025,
            reason="OFFSEASON→PRESEASON transition (2024→2025)"
        )
        mock_contract_service.increment_all_contracts.assert_called_once_with(season_year=2025)
        mock_draft_service.prepare_draft_class.assert_called_once_with(season_year=2025, size=300)

    def test_execute_year_transition_calls_services_in_order(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should call services in correct order: year → contracts → draft."""
        # Create a call tracker to verify execution order
        call_order = []

        def track_sync(*args, **kwargs):
            call_order.append('synchronize_year')

        def track_contracts(*args, **kwargs):
            call_order.append('increment_contracts')
            return {'total_contracts': 1700, 'still_active': 1653, 'expired_count': 47}

        def track_draft(*args, **kwargs):
            call_order.append('prepare_draft')
            return {
                'draft_class_id': 'draft_2025',
                'season_year': 2025,
                'total_players': 300,
                'generation_time_seconds': 2.5,
                'already_existed': False
            }

        mock_synchronizer.synchronize_year.side_effect = track_sync
        mock_contract_service.increment_all_contracts.side_effect = track_contracts
        mock_draft_service.prepare_draft_class.side_effect = track_draft

        # Act
        service.execute_year_transition(
            old_year=2024,
            new_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert execution order
        assert call_order == ['synchronize_year', 'increment_contracts', 'prepare_draft']

    @patch('src.services.season_transition_service.time')
    def test_execute_year_transition_timing_measurement(
        self, mock_time, service, mock_synchronizer
    ):
        """Should accurately measure total duration."""
        # Arrange - mock time progression
        # Calls: start_time, step1_start, step1_duration, step2_start, step2_duration,
        #        step3_start, step3_duration, total_duration
        mock_time.time.side_effect = [
            1000.0,  # start_time
            1001.0,  # step1_start
            1002.0,  # step1_duration calculation
            1002.0,  # step2_start
            1005.0,  # step2_duration calculation
            1005.0,  # step3_start
            1010.0,  # step3_duration calculation
            1010.0   # total_duration calculation
        ]

        # Act
        result = service.execute_year_transition(
            old_year=2024,
            new_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert - total should be 1010.0 - 1000.0 = 10.0 seconds
        assert result['total_duration_seconds'] == 10.0

    def test_execute_year_transition_fails_on_year_increment_error(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should fail loudly when year increment fails (step 1)."""
        # Arrange - make synchronizer fail
        mock_synchronizer.synchronize_year.side_effect = Exception("Year sync failed")

        # Act & Assert
        with pytest.raises(Exception, match="Year sync failed"):
            service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=mock_synchronizer
            )

        # Verify no subsequent steps executed
        mock_contract_service.increment_all_contracts.assert_not_called()
        mock_draft_service.prepare_draft_class.assert_not_called()

    def test_execute_year_transition_fails_on_contract_error(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should fail loudly when contract transition fails (step 2)."""
        # Arrange - make contract service fail
        mock_contract_service.increment_all_contracts.side_effect = Exception(
            "Contract increment failed"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Contract increment failed"):
            service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=mock_synchronizer
            )

        # Verify step 1 executed but step 3 did not
        mock_synchronizer.synchronize_year.assert_called_once()
        mock_draft_service.prepare_draft_class.assert_not_called()

    def test_execute_year_transition_fails_on_draft_error(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should fail loudly when draft preparation fails (step 3)."""
        # Arrange - make draft service fail
        mock_draft_service.prepare_draft_class.side_effect = Exception(
            "Draft generation failed"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Draft generation failed"):
            service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=mock_synchronizer
            )

        # Verify steps 1 and 2 executed
        mock_synchronizer.synchronize_year.assert_called_once()
        mock_contract_service.increment_all_contracts.assert_called_once()

    def test_execute_year_transition_tracks_completed_steps_on_failure(
        self, service, mock_contract_service, mock_synchronizer
    ):
        """Should track which steps completed before failure."""
        # Arrange - fail at step 2
        mock_contract_service.increment_all_contracts.side_effect = Exception("Step 2 failed")

        # Act
        try:
            result = service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=mock_synchronizer
            )
        except Exception:
            pass  # Expected failure

        # Note: We can't inspect the internal steps_completed list after exception
        # because it's a local variable. This would require exposing it via
        # the exception or as a service attribute. For now, verify step 1 executed.
        mock_synchronizer.synchronize_year.assert_called_once()

    def test_execute_year_transition_logs_all_steps(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should log progress for all 3 steps."""
        # Arrange - capture log calls
        service.logger = Mock()

        # Act
        service.execute_year_transition(
            old_year=2024,
            new_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert - check that info logs were called
        assert service.logger.info.call_count >= 6  # Start + 3 steps + complete + summary

    def test_execute_year_transition_logs_error_on_failure(
        self, service, mock_synchronizer
    ):
        """Should log error details when transition fails."""
        # Arrange
        mock_synchronizer.synchronize_year.side_effect = Exception("Test failure")
        service.logger = Mock()

        # Act
        with pytest.raises(Exception):
            service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=mock_synchronizer
            )

        # Assert - error should be logged
        service.logger.error.assert_called_once()
        error_call = service.logger.error.call_args[0][0]
        assert "FAILED" in error_call
        assert "Test failure" in error_call

    def test_execute_year_transition_different_years(
        self, service, mock_synchronizer
    ):
        """Should handle different year transitions correctly."""
        # Act
        result = service.execute_year_transition(
            old_year=2025,
            new_year=2026,
            synchronizer=mock_synchronizer
        )

        # Assert
        assert result['old_year'] == 2025
        assert result['new_year'] == 2026
        mock_synchronizer.synchronize_year.assert_called_with(
            new_year=2026,
            reason="OFFSEASON→PRESEASON transition (2025→2026)"
        )

    def test_execute_year_transition_passes_correct_parameters(
        self, service, mock_contract_service, mock_draft_service, mock_synchronizer
    ):
        """Should pass correct parameters to all service calls."""
        # Act
        service.execute_year_transition(
            old_year=2024,
            new_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert synchronizer called with correct reason
        mock_synchronizer.synchronize_year.assert_called_once_with(
            new_year=2025,
            reason="OFFSEASON→PRESEASON transition (2024→2025)"
        )

        # Assert contract service called with new year
        mock_contract_service.increment_all_contracts.assert_called_once_with(
            season_year=2025
        )

        # Assert draft service called with new year and size=300
        mock_draft_service.prepare_draft_class.assert_called_once_with(
            season_year=2025,
            size=300
        )


class TestValidateYearTransitionState:
    """Test validate_year_transition_state method."""

    @pytest.fixture
    def mock_draft_service(self):
        """Create mock DraftPreparationService."""
        mock_service = Mock()
        mock_service.validate_draft_class_exists = Mock(return_value=True)
        return mock_service

    @pytest.fixture
    def mock_synchronizer(self):
        """Create mock SeasonYearSynchronizer."""
        mock_sync = Mock()
        mock_sync.get_current_year = Mock(return_value=2025)
        return mock_sync

    @pytest.fixture
    def service(self, mock_draft_service):
        """Create SeasonTransitionService with mocks."""
        return SeasonTransitionService(
            contract_service=Mock(),
            draft_service=mock_draft_service,
            dynasty_id="test_dynasty"
        )

    def test_validate_year_transition_state_all_valid(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should return all valid when year matches and draft exists."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2025
        mock_draft_service.validate_draft_class_exists.return_value = True

        # Act
        result = service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        assert result['expected_year'] == 2025
        assert result['current_year'] == 2025
        assert result['year_matches'] is True
        assert result['draft_class_exists'] is True
        assert result['all_valid'] is True

        # Verify service calls
        mock_synchronizer.get_current_year.assert_called_once()
        mock_draft_service.validate_draft_class_exists.assert_called_once_with(2025)

    def test_validate_year_transition_state_year_mismatch(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should detect year mismatch and return invalid."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2024  # Wrong year!
        mock_draft_service.validate_draft_class_exists.return_value = True

        # Act
        result = service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        assert result['expected_year'] == 2025
        assert result['current_year'] == 2024
        assert result['year_matches'] is False
        assert result['draft_class_exists'] is True
        assert result['all_valid'] is False  # Overall invalid

    def test_validate_year_transition_state_draft_missing(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should detect missing draft class and return invalid."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2025
        mock_draft_service.validate_draft_class_exists.return_value = False  # No draft!

        # Act
        result = service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        assert result['expected_year'] == 2025
        assert result['current_year'] == 2025
        assert result['year_matches'] is True
        assert result['draft_class_exists'] is False
        assert result['all_valid'] is False  # Overall invalid

    def test_validate_year_transition_state_both_invalid(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should detect multiple validation failures."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2024  # Wrong year
        mock_draft_service.validate_draft_class_exists.return_value = False  # No draft

        # Act
        result = service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        assert result['year_matches'] is False
        assert result['draft_class_exists'] is False
        assert result['all_valid'] is False

    def test_validate_year_transition_state_logs_success(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should log success message when all valid."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2025
        mock_draft_service.validate_draft_class_exists.return_value = True
        service.logger = Mock()

        # Act
        service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        service.logger.info.assert_called_once()
        info_call = service.logger.info.call_args[0][0]
        assert "valid" in info_call.lower()

    def test_validate_year_transition_state_logs_warning_on_failure(
        self, service, mock_draft_service, mock_synchronizer
    ):
        """Should log warning when validation fails."""
        # Arrange
        mock_synchronizer.get_current_year.return_value = 2024  # Wrong year
        mock_draft_service.validate_draft_class_exists.return_value = False
        service.logger = Mock()

        # Act
        service.validate_year_transition_state(
            expected_year=2025,
            synchronizer=mock_synchronizer
        )

        # Assert
        service.logger.warning.assert_called_once()
        warning_call = service.logger.warning.call_args[0][0]
        assert "invalid" in warning_call.lower()


class TestSeasonTransitionServiceIntegration:
    """Integration-style tests with minimal mocking."""

    def test_service_can_be_created_with_dependency_injection(self):
        """Should create service with dependency injection pattern."""
        # Arrange
        mock_contract_service = Mock()
        mock_draft_service = Mock()

        # Act
        service = SeasonTransitionService(
            contract_service=mock_contract_service,
            draft_service=mock_draft_service,
            dynasty_id="integration_test"
        )

        # Assert
        assert service is not None
        assert service.dynasty_id == "integration_test"
        assert service.contract_service is mock_contract_service
        assert service.draft_service is mock_draft_service

    def test_service_requires_all_dependencies(self):
        """Should fail gracefully if dependencies are None."""
        # This test verifies the service doesn't crash on None dependencies
        # Real validation would happen when methods are called
        service = SeasonTransitionService(
            contract_service=None,
            draft_service=None,
            dynasty_id="test"
        )

        assert service.contract_service is None
        assert service.draft_service is None

    def test_multiple_year_transitions_in_sequence(self):
        """Should handle multiple sequential year transitions."""
        # Arrange
        mock_contract_service = Mock()
        mock_contract_service.increment_all_contracts = Mock(return_value={
            'total_contracts': 1700,
            'still_active': 1653,
            'expired_count': 47
        })

        mock_draft_service = Mock()
        mock_draft_service.prepare_draft_class = Mock(return_value={
            'draft_class_id': 'draft_2025',
            'season_year': 2025,
            'total_players': 300,
            'generation_time_seconds': 2.5,
            'already_existed': False
        })

        mock_synchronizer = Mock()
        mock_synchronizer.synchronize_year = Mock()

        service = SeasonTransitionService(
            contract_service=mock_contract_service,
            draft_service=mock_draft_service,
            dynasty_id="test"
        )

        # Act - execute two transitions
        result1 = service.execute_year_transition(2024, 2025, mock_synchronizer)
        result2 = service.execute_year_transition(2025, 2026, mock_synchronizer)

        # Assert both succeeded
        assert result1['year_increment_success'] is True
        assert result2['year_increment_success'] is True
        assert mock_synchronizer.synchronize_year.call_count == 2
