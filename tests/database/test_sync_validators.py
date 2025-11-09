"""
Tests for Calendar-Database Sync Validators

Tests the fail-loud validation system that fixes CALENDAR-DRIFT-2025-001.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.database.sync_validators import (
    SyncValidator,
    DriftInfo,
    validate_sync_state,
    verify_sync_write
)
from src.database.sync_exceptions import (
    PreSyncValidationResult,
    PostSyncVerificationResult
)


# Fixtures

@pytest.fixture
def mock_state_model():
    """Mock SimulationDataModel"""
    model = Mock()
    model.get_state.return_value = {
        'current_date': '2025-09-15',
        'current_phase': 'regular_season',
        'current_week': 3
    }
    return model


@pytest.fixture
def mock_calendar_manager():
    """Mock CalendarManager"""
    manager = Mock()
    manager.get_current_date.return_value = '2025-09-15'
    return manager


@pytest.fixture
def sync_validator(mock_state_model, mock_calendar_manager):
    """Create SyncValidator instance"""
    return SyncValidator(mock_state_model, mock_calendar_manager)


# DriftInfo Tests

class TestDriftInfo:
    """Test DriftInfo dataclass"""

    def test_no_drift(self):
        """Test drift calculation when dates match"""
        drift = DriftInfo.from_dates("2025-09-15", "2025-09-15")

        assert drift.drift_days == 0
        assert drift.severity == "none"
        assert drift.calendar_date == "2025-09-15"
        assert drift.db_date == "2025-09-15"
        assert "synchronized" in drift.description.lower()

    def test_minor_drift(self):
        """Test minor drift (1-3 days)"""
        drift = DriftInfo.from_dates("2025-09-18", "2025-09-15")

        assert drift.drift_days == 3
        assert drift.severity == "minor"
        assert "auto-correct" in drift.recovery_recommendation.lower()

    def test_major_drift(self):
        """Test major drift (4-20 days)"""
        drift = DriftInfo.from_dates("2025-09-25", "2025-09-15")

        assert drift.drift_days == 10
        assert drift.severity == "major"
        assert "reload" in drift.recovery_recommendation.lower()

    def test_severe_drift(self):
        """Test severe drift (>20 days) - actual bug scenario"""
        drift = DriftInfo.from_dates("2026-03-03", "2025-11-09")

        assert drift.drift_days == 114  # Actual drift from bug
        assert drift.severity == "severe"
        assert "support" in drift.recovery_recommendation.lower()


# Pre-Sync Validation Tests

class TestPreSyncValidation:
    """Test pre-sync validation"""

    def test_valid_state(self, sync_validator):
        """Test validation passes with synchronized state"""
        result = sync_validator.validate_pre_sync()

        assert result.valid is True
        assert result.drift == 0
        assert len(result.issues) == 0

    def test_calendar_not_initialized(self, mock_state_model):
        """Test validation fails when calendar is None"""
        validator = SyncValidator(mock_state_model, None)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert 'calendar' in result.issues
        assert "not initialized" in result.issues['calendar']

    def test_calendar_date_none(self, mock_state_model, mock_calendar_manager):
        """Test validation fails when calendar date is None"""
        mock_calendar_manager.get_current_date.return_value = None

        validator = SyncValidator(mock_state_model, mock_calendar_manager)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert 'calendar' in result.issues

    def test_database_state_missing(self, mock_state_model, mock_calendar_manager):
        """Test validation fails when database state is None"""
        mock_state_model.get_state.return_value = None

        validator = SyncValidator(mock_state_model, mock_calendar_manager)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert 'database' in result.issues
        assert "No database state" in result.issues['database']

    def test_database_date_missing(self, mock_state_model, mock_calendar_manager):
        """Test validation fails when database current_date is missing"""
        mock_state_model.get_state.return_value = {
            'current_phase': 'regular_season'
            # Missing current_date
        }

        validator = SyncValidator(mock_state_model, mock_calendar_manager)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert 'database' in result.issues
        assert "missing current_date" in result.issues['database']

    def test_acceptable_drift(self, mock_state_model, mock_calendar_manager):
        """Test validation passes with minor drift within threshold"""
        # Calendar 2 days ahead (within 3-day threshold)
        mock_calendar_manager.get_current_date.return_value = '2025-09-17'
        mock_state_model.get_state.return_value = {
            'current_date': '2025-09-15',
            'current_phase': 'regular_season'
        }

        validator = SyncValidator(mock_state_model, mock_calendar_manager, max_acceptable_drift=3)
        result = validator.validate_pre_sync()

        assert result.valid is True
        assert result.drift == 2
        assert len(result.issues) == 0

    def test_unacceptable_drift(self, mock_state_model, mock_calendar_manager):
        """Test validation fails with drift exceeding threshold"""
        # Calendar 4 days ahead (exceeds 3-day threshold)
        mock_calendar_manager.get_current_date.return_value = '2025-09-19'
        mock_state_model.get_state.return_value = {
            'current_date': '2025-09-15',
            'current_phase': 'regular_season'
        }

        validator = SyncValidator(mock_state_model, mock_calendar_manager, max_acceptable_drift=3)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert result.drift == 4
        assert 'drift' in result.issues
        assert result.issues['drift_days'] == 4

    def test_calendar_drift_bug_scenario(self, mock_state_model, mock_calendar_manager):
        """Test validation catches the actual calendar drift bug"""
        # Actual bug: Calendar at 2026-03-03, DB at 2025-11-09
        mock_calendar_manager.get_current_date.return_value = '2026-03-03'
        mock_state_model.get_state.return_value = {
            'current_date': '2025-11-09',
            'current_phase': 'playoffs'
        }

        validator = SyncValidator(mock_state_model, mock_calendar_manager)
        result = validator.validate_pre_sync()

        assert result.valid is False
        assert result.drift > 100  # Massive drift
        assert 'drift' in result.issues
        assert 'recovery' in result.issues


# Post-Sync Verification Tests

class TestPostSyncVerification:
    """Test post-sync verification"""

    def test_successful_sync(self, sync_validator, mock_calendar_manager, mock_state_model):
        """Test verification passes when sync is successful"""
        # Setup: Both calendar and DB at expected date
        expected_date = "2025-09-16"
        expected_phase = "regular_season"

        mock_calendar_manager.get_current_date.return_value = expected_date
        mock_state_model.get_state.return_value = {
            'current_date': expected_date,
            'current_phase': expected_phase
        }

        result = sync_validator.verify_post_sync(expected_date, expected_phase)

        assert result.valid is True
        assert result.drift == 0
        assert len(result.issues) == 0
        assert result.actual_calendar_date == expected_date
        assert result.actual_phase == expected_phase

    def test_database_write_failed(self, sync_validator, mock_calendar_manager, mock_state_model):
        """Test verification fails when database write didn't persist"""
        expected_date = "2025-09-16"
        expected_phase = "regular_season"

        # Calendar advanced but database still at old date (write failed)
        mock_calendar_manager.get_current_date.return_value = expected_date
        mock_state_model.get_state.return_value = {
            'current_date': '2025-09-15',  # Old date - write failed!
            'current_phase': expected_phase
        }

        result = sync_validator.verify_post_sync(expected_date, expected_phase)

        assert result.valid is False
        assert 'db_date_mismatch' in result.issues
        assert result.drift == 1  # Calendar 1 day ahead

    def test_calendar_date_wrong(self, sync_validator, mock_calendar_manager, mock_state_model):
        """Test verification fails when calendar didn't advance"""
        expected_date = "2025-09-16"
        expected_phase = "regular_season"

        # Database updated but calendar didn't advance
        mock_calendar_manager.get_current_date.return_value = '2025-09-15'
        mock_state_model.get_state.return_value = {
            'current_date': expected_date,
            'current_phase': expected_phase
        }

        result = sync_validator.verify_post_sync(expected_date, expected_phase)

        assert result.valid is False
        assert 'calendar_date_mismatch' in result.issues

    def test_phase_mismatch(self, sync_validator, mock_calendar_manager, mock_state_model):
        """Test verification fails when phase doesn't match"""
        expected_date = "2025-09-16"
        expected_phase = "playoffs"

        mock_calendar_manager.get_current_date.return_value = expected_date
        mock_state_model.get_state.return_value = {
            'current_date': expected_date,
            'current_phase': 'regular_season'  # Wrong phase!
        }

        result = sync_validator.verify_post_sync(expected_date, expected_phase)

        assert result.valid is False
        assert 'phase_mismatch' in result.issues

    def test_drift_after_sync(self, sync_validator, mock_calendar_manager, mock_state_model):
        """Test verification detects drift even when dates partially match"""
        expected_date = "2025-09-16"
        expected_phase = "regular_season"

        # Calendar ahead of database
        mock_calendar_manager.get_current_date.return_value = "2025-09-18"
        mock_state_model.get_state.return_value = {
            'current_date': "2025-09-16",
            'current_phase': expected_phase
        }

        result = sync_validator.verify_post_sync(expected_date, expected_phase)

        assert result.valid is False
        assert result.drift == 2
        assert 'drift' in result.issues


# Convenience Function Tests

class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_validate_sync_state(self, mock_state_model, mock_calendar_manager):
        """Test validate_sync_state convenience function"""
        result = validate_sync_state(mock_state_model, mock_calendar_manager)

        assert isinstance(result, PreSyncValidationResult)
        assert result.valid is True

    def test_verify_sync_write(self, mock_state_model, mock_calendar_manager):
        """Test verify_sync_write convenience function"""
        mock_calendar_manager.get_current_date.return_value = "2025-09-16"
        mock_state_model.get_state.return_value = {
            'current_date': "2025-09-16",
            'current_phase': "regular_season"
        }

        result = verify_sync_write(
            mock_state_model,
            mock_calendar_manager,
            "2025-09-16",
            "regular_season"
        )

        assert isinstance(result, PostSyncVerificationResult)
        assert result.valid is True


# Integration Tests

class TestSyncValidatorIntegration:
    """Integration tests for complete validation flow"""

    def test_advance_day_happy_path(self, mock_state_model, mock_calendar_manager):
        """Test complete advance_day validation flow"""
        validator = SyncValidator(mock_state_model, mock_calendar_manager)

        # Pre-sync validation
        pre_result = validator.validate_pre_sync()
        assert pre_result.valid is True

        # Simulate calendar advancement
        mock_calendar_manager.get_current_date.return_value = "2025-09-16"

        # Simulate database save
        mock_state_model.get_state.return_value = {
            'current_date': "2025-09-16",
            'current_phase': "regular_season"
        }

        # Post-sync verification
        post_result = validator.verify_post_sync("2025-09-16", "regular_season")
        assert post_result.valid is True

    def test_advance_day_with_save_failure(self, mock_state_model, mock_calendar_manager):
        """Test validation catches database save failure"""
        validator = SyncValidator(mock_state_model, mock_calendar_manager)

        # Pre-sync: OK
        pre_result = validator.validate_pre_sync()
        assert pre_result.valid is True

        # Calendar advances
        mock_calendar_manager.get_current_date.return_value = "2025-09-16"

        # Database save FAILS (date doesn't update)
        mock_state_model.get_state.return_value = {
            'current_date': "2025-09-15",  # Still old date!
            'current_phase': "regular_season"
        }

        # Post-sync: FAIL
        post_result = validator.verify_post_sync("2025-09-16", "regular_season")
        assert post_result.valid is False
        assert 'db_date_mismatch' in post_result.issues

    def test_calculate_drift_current_state(self, mock_state_model, mock_calendar_manager):
        """Test drift calculation on current state"""
        # Setup 10-day drift
        mock_calendar_manager.get_current_date.return_value = "2025-09-25"
        mock_state_model.get_state.return_value = {
            'current_date': "2025-09-15",
            'current_phase': "regular_season"
        }

        validator = SyncValidator(mock_state_model, mock_calendar_manager)
        drift_info = validator.calculate_drift()

        assert drift_info.drift_days == 10
        assert drift_info.severity == "major"
        assert drift_info.calendar_date == "2025-09-25"
        assert drift_info.db_date == "2025-09-15"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
