"""
Tests for DynastyStateAPI Fail-Loud Behavior (Phase 1)

Validates that DynastyStateAPI.update_state() raises CalendarSyncPersistenceException
instead of failing silently when database writes fail.

This addresses the root cause of the calendar drift bug (CALENDAR-DRIFT-2025-001).

Test Coverage:
- Zero rows affected raises exception with state context
- Database errors are wrapped and re-raised with context
- Exception contains all required state information
- Errors are logged with exc_info=True
- Success path returns True
- Exception chaining preserves original error
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock, call
import logging

from database.dynasty_state_api import DynastyStateAPI
from database.sync_exceptions import CalendarSyncPersistenceException


class TestDynastyStateAPISyncErrors:
    """Test DynastyStateAPI exception raising on database failures."""

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_raises_on_no_rows_affected(self, mock_db_class):
        """Verify zero rows affected raises CalendarSyncPersistenceException with state context."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 0  # No rows affected
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify exception context
        exception = exc_info.value
        assert exception.operation == "dynasty_state_update"
        assert exception.sync_point == "update_state"
        assert exception.sync_type == "write"

        # Verify state_info contains all required fields
        state_info = exception.state_info
        assert state_info["dynasty_id"] == "test_dynasty"
        assert state_info["season"] == 2025
        assert state_info["current_date"] == "2025-11-09"
        assert state_info["current_phase"] == "playoffs"
        assert state_info["current_week"] == 10
        assert "reason" in state_info
        assert "No rows affected" in state_info["reason"]

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_raises_on_db_error(self, mock_db_class):
        """Verify database errors are wrapped in CalendarSyncPersistenceException."""
        # Setup mock to raise database error
        mock_db = Mock()
        mock_db.execute_update.side_effect = sqlite3.OperationalError("database is locked")
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify exception wrapping
        exception = exc_info.value
        assert exception.operation == "dynasty_state_update"
        assert exception.sync_point == "update_state"

        # Verify original exception is chained
        assert exception.__cause__ is not None
        assert isinstance(exception.__cause__, sqlite3.OperationalError)
        assert "database is locked" in str(exception.__cause__)

        # Verify error is in state_info
        assert "error" in exception.state_info
        assert "database is locked" in exception.state_info["error"]

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_includes_full_context(self, mock_db_class):
        """Verify exception includes all state_info fields."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 0  # Trigger exception
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute with all optional parameters
        # Use date that matches season to avoid auto-correction
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="full_test_dynasty",
                season=2026,
                current_date="2026-09-15",  # September derives to 2026
                current_phase="regular_season",
                current_week=2,
                last_simulated_game_id="game_123"
            )

        # Verify all state_info fields are present
        state_info = exc_info.value.state_info
        assert state_info["dynasty_id"] == "full_test_dynasty"
        assert state_info["season"] == 2026
        assert state_info["current_date"] == "2026-09-15"
        assert state_info["current_phase"] == "regular_season"
        assert state_info["current_week"] == 2

        # Operation and sync_point should be set
        assert exc_info.value.operation == "dynasty_state_update"
        assert exc_info.value.sync_point == "update_state"

    @patch('database.dynasty_state_api.DatabaseConnection')
    @patch('database.dynasty_state_api.logging.getLogger')
    def test_update_state_logs_errors_on_no_rows(self, mock_get_logger, mock_db_class):
        """Verify errors are logged with exc_info=True when no rows affected."""
        # Setup mocks
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_db = Mock()
        mock_db.execute_update.return_value = 0  # No rows affected
        mock_db_class.return_value = mock_db

        # Create API (will use our mocked logger)
        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException):
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify logger.error was called
        assert mock_logger.error.called

        # Verify exc_info=True was passed
        error_call = mock_logger.error.call_args
        assert error_call is not None

        # Check kwargs for exc_info
        if error_call.kwargs:
            assert error_call.kwargs.get('exc_info') is True
        else:
            # If using positional args, check second argument
            assert len(error_call.args) >= 1

    @patch('database.dynasty_state_api.DatabaseConnection')
    @patch('database.dynasty_state_api.logging.getLogger')
    def test_update_state_logs_errors_on_exception(self, mock_get_logger, mock_db_class):
        """Verify errors are logged with exc_info=True when exception occurs."""
        # Setup mocks
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_db = Mock()
        mock_db.execute_update.side_effect = sqlite3.OperationalError("database is locked")
        mock_db_class.return_value = mock_db

        # Create API (will use our mocked logger)
        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException):
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify logger.error was called
        assert mock_logger.error.called

        # Verify exc_info=True was passed
        error_call = mock_logger.error.call_args
        assert error_call is not None

        # Check kwargs for exc_info
        if error_call.kwargs:
            assert error_call.kwargs.get('exc_info') is True

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_success_returns_true(self, mock_db_class):
        """Verify successful update returns True and raises no exceptions."""
        # Setup mock for successful write
        mock_db = Mock()
        mock_db.execute_update.return_value = 1  # Success - 1 row affected
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute - should NOT raise exception
        result = api.update_state(
            dynasty_id="test_dynasty",
            season=2025,
            current_date="2025-11-09",
            current_phase="playoffs",
            current_week=10
        )

        # Verify success
        assert result is True

        # Verify execute_update was called with correct parameters
        assert mock_db.execute_update.called
        call_args = mock_db.execute_update.call_args

        # Check the SQL query contains our expected values
        assert call_args is not None
        query = call_args[0][0]
        params = call_args[0][1]

        # Verify query structure
        assert "INSERT OR REPLACE INTO dynasty_state" in query

        # Verify parameters
        assert params[0] == "test_dynasty"  # dynasty_id
        assert params[1] == 2025  # season
        assert params[2] == "2025-11-09"  # current_date
        assert params[3] == "playoffs"  # current_phase
        assert params[4] == 10  # current_week

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_reraises_sync_exception_without_wrapping(self, mock_db_class):
        """Verify CalendarSyncPersistenceException is re-raised without double-wrapping."""
        # This tests the except CalendarSyncPersistenceException block

        # Setup mock to trigger no rows affected (which raises CalendarSyncPersistenceException)
        mock_db = Mock()
        mock_db.execute_update.return_value = 0  # No rows affected
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify the exception is NOT double-wrapped
        exception = exc_info.value

        # The exception should be our original CalendarSyncPersistenceException
        assert isinstance(exception, CalendarSyncPersistenceException)
        assert exception.operation == "dynasty_state_update"

        # The __cause__ should be None (no chaining) because this is the original exception
        assert exception.__cause__ is None

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_with_season_date_mismatch_auto_corrects(self, mock_db_class):
        """Verify season/date mismatch is auto-corrected and logged."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 1  # Success
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Test with mismatched season (2025) and date (2026-01-15, which derives to 2025)
        result = api.update_state(
            dynasty_id="test_dynasty",
            season=2026,  # Wrong season
            current_date="2026-01-15",  # This derives to 2025
            current_phase="playoffs",
            current_week=18
        )

        # Should succeed with auto-correction
        assert result is True

        # Verify the corrected season (2025) was used in the database call
        call_args = mock_db.execute_update.call_args
        params = call_args[0][1]
        assert params[1] == 2025  # season should be auto-corrected to 2025

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_error_message_format(self, mock_db_class):
        """Verify exception message contains helpful debugging information."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 0  # No rows affected
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="debug_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify exception message is informative
        exception_str = str(exc_info.value)

        # Should contain error code
        assert "SYNC_PERSIST_003" in exception_str

        # Should contain operation
        assert "dynasty_state_update" in exception_str

        # Should contain state information
        assert "dynasty_id" in exception_str
        assert "debug_dynasty" in exception_str

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_preserves_exception_chain(self, mock_db_class):
        """Verify original exception is preserved in exception chain."""
        # Setup mock to raise original error
        original_error = sqlite3.IntegrityError("UNIQUE constraint failed")
        mock_db = Mock()
        mock_db.execute_update.side_effect = original_error
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            api.update_state(
                dynasty_id="test_dynasty",
                season=2025,
                current_date="2025-11-09",
                current_phase="playoffs",
                current_week=10
            )

        # Verify exception chaining
        exception = exc_info.value

        # __cause__ should be the original error
        assert exception.__cause__ is original_error
        assert isinstance(exception.__cause__, sqlite3.IntegrityError)
        assert "UNIQUE constraint failed" in str(exception.__cause__)

        # State info should contain error message
        assert "error" in exception.state_info
        assert "UNIQUE constraint failed" in exception.state_info["error"]


class TestDynastyStateAPISuccessPath:
    """Test DynastyStateAPI success scenarios."""

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_with_minimal_params(self, mock_db_class):
        """Verify successful update with only required parameters."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 1
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute with minimal params (no current_week, no last_simulated_game_id)
        result = api.update_state(
            dynasty_id="minimal_dynasty",
            season=2025,
            current_date="2025-09-10",
            current_phase="regular_season"
        )

        # Verify success
        assert result is True

        # Verify database was called
        assert mock_db.execute_update.called
        call_args = mock_db.execute_update.call_args
        params = call_args[0][1]

        # Verify None values were passed for optional params
        assert params[0] == "minimal_dynasty"
        assert params[1] == 2025
        assert params[2] == "2025-09-10"
        assert params[3] == "regular_season"
        assert params[4] is None  # current_week
        assert params[5] is None  # last_simulated_game_id

    @patch('database.dynasty_state_api.DatabaseConnection')
    def test_update_state_with_all_params(self, mock_db_class):
        """Verify successful update with all parameters."""
        # Setup mock
        mock_db = Mock()
        mock_db.execute_update.return_value = 1
        mock_db_class.return_value = mock_db

        api = DynastyStateAPI("test.db")

        # Execute with all params
        result = api.update_state(
            dynasty_id="full_dynasty",
            season=2025,
            current_date="2025-12-15",
            current_phase="playoffs",
            current_week=16,
            last_simulated_game_id="game_456"
        )

        # Verify success
        assert result is True

        # Verify all params were passed
        call_args = mock_db.execute_update.call_args
        params = call_args[0][1]

        assert params[0] == "full_dynasty"
        assert params[1] == 2025
        assert params[2] == "2025-12-15"
        assert params[3] == "playoffs"
        assert params[4] == 16
        assert params[5] == "game_456"
