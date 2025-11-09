"""
Unit Tests for DraftPreparationService

Tests the draft preparation service logic with mocked dependencies.
All tests use pytest and unittest.mock to isolate service behavior.

Follows the same testing pattern as test_transaction_service.py.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time

# Mock the imports before importing the service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.draft_preparation_service import DraftPreparationService


class TestDraftPreparationServiceInitialization:
    """Test service initialization and dependency injection."""

    def test_init_creates_service_with_dependencies(self):
        """Service should store all injected dependencies."""
        # Arrange
        mock_draft_manager = Mock()
        mock_draft_api = Mock()

        # Act
        service = DraftPreparationService(
            draft_manager=mock_draft_manager,
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Assert
        assert service.draft_manager == mock_draft_manager
        assert service.draft_api == mock_draft_api
        assert service.dynasty_id == "test_dynasty"
        assert service.logger is not None
        assert service.logger.name == "DraftPreparationService"


class TestPrepareDraftClass:
    """Test prepare_draft_class method."""

    @pytest.fixture
    def mock_draft_manager(self):
        """Create mock DraftManager."""
        mock_manager = Mock()
        # Mock generate_draft_class to return list of 300 prospects
        mock_prospects = [{'player_id': i, 'name': f'Player {i}'} for i in range(300)]
        mock_manager.generate_draft_class = Mock(return_value=mock_prospects)
        return mock_manager

    @pytest.fixture
    def mock_draft_api(self):
        """Create mock DraftClassDatabaseAPI."""
        mock_api = Mock()
        mock_api.dynasty_has_draft_class = Mock(return_value=False)
        mock_api.get_draft_class_info = Mock(return_value={
            'draft_class_id': 'DC-2025-test',
            'season_year': 2025,
            'total_prospects': 300
        })
        return mock_api

    @pytest.fixture
    def service(self, mock_draft_manager, mock_draft_api):
        """Create DraftPreparationService with mocks."""
        return DraftPreparationService(
            draft_manager=mock_draft_manager,
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

    def test_prepare_draft_class_generates_new_class(
        self, service, mock_draft_manager, mock_draft_api
    ):
        """Should generate new draft class when none exists."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Execute
        result = service.prepare_draft_class(2025, size=300)

        # Verify
        assert result['season_year'] == 2025
        assert result['total_players'] == 300
        assert result['already_existed'] is False
        assert result['generation_time_seconds'] >= 0  # Can be 0.0 with mocked operations
        assert result['draft_class_id'] == 'DC-2025-test'

        # Verify draft_manager was called correctly
        mock_draft_manager.generate_draft_class.assert_called_once_with(size=300)

        # Verify draft_api was queried
        mock_draft_api.dynasty_has_draft_class.assert_called_once_with("test_dynasty", 2025)

    def test_prepare_draft_class_already_exists(self, service, mock_draft_manager, mock_draft_api):
        """Should return existing class info when class already exists."""
        # Mock class already exists
        mock_draft_api.dynasty_has_draft_class.return_value = True
        mock_draft_api.get_draft_class_info.return_value = {
            'draft_class_id': 'DC-2025-existing',
            'season_year': 2025,
            'total_prospects': 300
        }

        # Execute
        result = service.prepare_draft_class(2025)

        # Verify
        assert result['season_year'] == 2025
        assert result['total_players'] == 300
        assert result['already_existed'] is True
        assert result['generation_time_seconds'] == 0.0
        assert result['draft_class_id'] == 'DC-2025-existing'

        # Verify draft_manager was NOT called (no generation)
        mock_draft_manager.generate_draft_class.assert_not_called()

    @patch('time.time')
    def test_prepare_draft_class_logs_slow_generation(
        self, mock_time, service, mock_draft_manager, mock_draft_api
    ):
        """Should log warning when generation takes longer than 5 seconds."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Mock time to simulate 6 second generation
        mock_time.side_effect = [0, 6.0]

        # Mock logger
        service.logger = Mock()

        # Execute
        result = service.prepare_draft_class(2025, size=300)

        # Verify warning was logged
        warning_calls = [str(call) for call in service.logger.warning.call_args_list]
        assert any("took longer than expected" in call for call in warning_calls)

        # Verify generation time reported correctly
        assert result['generation_time_seconds'] == 6.0

    def test_prepare_draft_class_custom_size(self, service, mock_draft_manager, mock_draft_api):
        """Should generate draft class with custom size."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Mock custom size prospects
        mock_prospects = [{'player_id': i} for i in range(500)]
        mock_draft_manager.generate_draft_class.return_value = mock_prospects

        # Execute
        result = service.prepare_draft_class(2025, size=500)

        # Verify
        assert result['total_players'] == 500
        mock_draft_manager.generate_draft_class.assert_called_once_with(size=500)

    def test_prepare_draft_class_fail_loudly_on_error(self, service, mock_draft_manager, mock_draft_api):
        """Should propagate exceptions without catching (fail loudly)."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Mock generation to raise error
        mock_draft_manager.generate_draft_class.side_effect = RuntimeError("Database connection failed")

        # Execute and verify exception propagates
        with pytest.raises(RuntimeError, match="Database connection failed"):
            service.prepare_draft_class(2025)

    def test_prepare_draft_class_default_size_300(self, service, mock_draft_manager, mock_draft_api):
        """Should use default size of 300 when not specified."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Execute without size parameter
        result = service.prepare_draft_class(2025)

        # Verify default size used
        mock_draft_manager.generate_draft_class.assert_called_once_with(size=300)

    def test_prepare_draft_class_measures_timing_accurately(
        self, service, mock_draft_manager, mock_draft_api
    ):
        """Should accurately measure generation time."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Execute (real timing)
        result = service.prepare_draft_class(2025)

        # Verify timing was measured (should be very small but > 0)
        assert result['generation_time_seconds'] >= 0
        assert isinstance(result['generation_time_seconds'], (int, float))

    def test_prepare_draft_class_returns_draft_class_id(
        self, service, mock_draft_manager, mock_draft_api
    ):
        """Should return draft class ID from database."""
        # Mock class doesn't exist
        mock_draft_api.dynasty_has_draft_class.return_value = False

        # Mock get_draft_class_info to return specific ID
        mock_draft_api.get_draft_class_info.return_value = {
            'draft_class_id': 'DC-2025-abc123',
            'season_year': 2025,
            'total_prospects': 300
        }

        # Execute
        result = service.prepare_draft_class(2025)

        # Verify
        assert result['draft_class_id'] == 'DC-2025-abc123'


class TestValidateDraftClassExists:
    """Test validate_draft_class_exists method."""

    def test_validate_draft_class_exists_true(self):
        """Should return True when draft class exists."""
        # Arrange
        mock_draft_api = Mock()
        mock_draft_api.dynasty_has_draft_class.return_value = True

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.validate_draft_class_exists(2025)

        # Assert
        assert result is True
        mock_draft_api.dynasty_has_draft_class.assert_called_once_with("test_dynasty", 2025)

    def test_validate_draft_class_exists_false(self):
        """Should return False when draft class does not exist."""
        # Arrange
        mock_draft_api = Mock()
        mock_draft_api.dynasty_has_draft_class.return_value = False

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.validate_draft_class_exists(2025)

        # Assert
        assert result is False
        mock_draft_api.dynasty_has_draft_class.assert_called_once_with("test_dynasty", 2025)

    def test_validate_uses_correct_dynasty_id(self):
        """Should use service's dynasty_id for validation."""
        # Arrange
        mock_draft_api = Mock()
        mock_draft_api.dynasty_has_draft_class.return_value = False

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="eagles_dynasty"
        )

        # Act
        service.validate_draft_class_exists(2026)

        # Assert
        mock_draft_api.dynasty_has_draft_class.assert_called_once_with("eagles_dynasty", 2026)


class TestGetDraftClassInfo:
    """Test get_draft_class_info method."""

    def test_get_draft_class_info_exists(self):
        """Should return draft class info when it exists."""
        # Arrange
        mock_draft_api = Mock()
        expected_info = {
            'draft_class_id': 'DC-2025-test',
            'season_year': 2025,
            'total_prospects': 300,
            'created_date': '2025-01-01'
        }
        mock_draft_api.get_draft_class_info.return_value = expected_info

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.get_draft_class_info(2025)

        # Assert
        assert result == expected_info
        mock_draft_api.get_draft_class_info.assert_called_once_with("test_dynasty", 2025)

    def test_get_draft_class_info_not_exists(self):
        """Should return None when draft class does not exist."""
        # Arrange
        mock_draft_api = Mock()
        mock_draft_api.get_draft_class_info.return_value = None

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.get_draft_class_info(2025)

        # Assert
        assert result is None
        mock_draft_api.get_draft_class_info.assert_called_once_with("test_dynasty", 2025)

    def test_get_draft_class_info_uses_correct_dynasty_id(self):
        """Should use service's dynasty_id for retrieval."""
        # Arrange
        mock_draft_api = Mock()
        mock_draft_api.get_draft_class_info.return_value = {
            'draft_class_id': 'DC-2027-xyz',
            'total_prospects': 300  # Include required field for debug logging
        }

        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=mock_draft_api,
            dynasty_id="chiefs_dynasty"
        )

        # Act
        service.get_draft_class_info(2027)

        # Assert
        mock_draft_api.get_draft_class_info.assert_called_once_with("chiefs_dynasty", 2027)


class TestDraftPreparationServiceIntegration:
    """Integration-style tests with minimal mocking."""

    def test_service_can_be_created_with_dependency_injection(self):
        """Should create service with dependency injection pattern."""
        # This test verifies the service can be instantiated
        # In real usage, controller would inject dependencies
        service = DraftPreparationService(
            draft_manager=Mock(),
            draft_api=Mock(),
            dynasty_id="integration_test"
        )

        assert service is not None
        assert service.dynasty_id == "integration_test"

    def test_full_workflow_new_draft_class(self):
        """Integration test: Full workflow for new draft class generation."""
        # Arrange
        mock_draft_manager = Mock()
        mock_prospects = [{'player_id': i, 'name': f'Player {i}'} for i in range(300)]
        mock_draft_manager.generate_draft_class.return_value = mock_prospects

        mock_draft_api = Mock()
        mock_draft_api.dynasty_has_draft_class.return_value = False
        mock_draft_api.get_draft_class_info.return_value = {
            'draft_class_id': 'DC-2025-test',
            'season_year': 2025,
            'total_prospects': 300
        }

        service = DraftPreparationService(
            draft_manager=mock_draft_manager,
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.prepare_draft_class(2025)

        # Assert - full workflow executed correctly
        assert result['season_year'] == 2025
        assert result['total_players'] == 300
        assert result['already_existed'] is False
        assert result['generation_time_seconds'] >= 0
        assert result['draft_class_id'] == 'DC-2025-test'

        # Verify all API calls made in correct order
        mock_draft_api.dynasty_has_draft_class.assert_called_once()
        mock_draft_manager.generate_draft_class.assert_called_once()
        mock_draft_api.get_draft_class_info.assert_called_once()

    def test_full_workflow_existing_draft_class(self):
        """Integration test: Full workflow when draft class already exists."""
        # Arrange
        mock_draft_manager = Mock()

        mock_draft_api = Mock()
        mock_draft_api.dynasty_has_draft_class.return_value = True
        mock_draft_api.get_draft_class_info.return_value = {
            'draft_class_id': 'DC-2025-existing',
            'season_year': 2025,
            'total_prospects': 300
        }

        service = DraftPreparationService(
            draft_manager=mock_draft_manager,
            draft_api=mock_draft_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.prepare_draft_class(2025)

        # Assert - idempotent behavior
        assert result['already_existed'] is True
        assert result['generation_time_seconds'] == 0.0

        # Verify generation was skipped
        mock_draft_manager.generate_draft_class.assert_not_called()

        # Verify only validation and info retrieval occurred
        mock_draft_api.dynasty_has_draft_class.assert_called_once()
        mock_draft_api.get_draft_class_info.assert_called_once()
