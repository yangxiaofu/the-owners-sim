"""
Test suite for SimulationDataModel exception propagation behavior.

This test suite verifies Phase 2 of the Calendar Drift Bug fix:
- CalendarSyncPersistenceException propagates without wrapping
- No silent failures (no print statements, no try/except hiding exceptions)
- Success logging behavior
- Fail-loud behavior when database writes fail

Related to CALENDAR-DRIFT-2025-001 root cause analysis.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
import sys
from pathlib import Path

# Add project root and ui directory to path
project_root = Path(__file__).parent.parent.parent
ui_dir = project_root / 'ui'
src_dir = project_root / 'src'

for path in [str(project_root), str(ui_dir), str(src_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import directly without triggering __init__.py imports
# This avoids circular import issues with ui.domain_models prefix
import importlib.util
import sys

# Load SimulationDataModel directly
spec = importlib.util.spec_from_file_location(
    "simulation_data_model",
    ui_dir / "domain_models" / "simulation_data_model.py"
)
simulation_module = importlib.util.module_from_spec(spec)
sys.modules["simulation_data_model"] = simulation_module
spec.loader.exec_module(simulation_module)
SimulationDataModel = simulation_module.SimulationDataModel

# Import sync exceptions normally
from database.sync_exceptions import CalendarSyncPersistenceException


class TestSimulationDataModelSyncErrors:
    """Test suite for exception propagation in SimulationDataModel.save_state()"""

    @pytest.fixture
    def model(self):
        """Create SimulationDataModel with mocked dependencies"""
        with patch('simulation_data_model.DynastyStateAPI') as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api

            # Mock get_latest_state to return a state with season 2025
            mock_api.get_latest_state.return_value = {
                'current_date': '2025-09-05',
                'current_phase': 'REGULAR_SEASON',
                'current_week': 1,
                'season': 2025,
                'last_simulated_game_id': None
            }

            model = SimulationDataModel(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )
            model.dynasty_api = mock_api  # Inject mock
            yield model

    def test_save_state_propagates_persistence_exception(self, model):
        """
        Verify CalendarSyncPersistenceException propagates without wrapping.

        This test ensures that when DynastyStateAPI.update_state() raises
        CalendarSyncPersistenceException, it propagates unchanged through
        SimulationDataModel.save_state() without being caught or wrapped.

        This is CRITICAL for fail-loud behavior to prevent calendar drift.
        """
        # Setup: Mock update_state to raise exception
        test_exception = CalendarSyncPersistenceException(
            operation="test_operation",
            sync_point="test_save_state",
            state_info={
                "dynasty_id": "test_dynasty",
                "intended_date": "2025-09-10",
                "intended_phase": "REGULAR_SEASON"
            }
        )
        model.dynasty_api.update_state.side_effect = test_exception

        # Execute & Assert: Exception should propagate
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            model.save_state("2025-09-10", "REGULAR_SEASON", 2)

        # Verify it's the SAME exception (not wrapped or modified)
        assert exc_info.value is test_exception
        assert exc_info.value.operation == "test_operation"
        assert exc_info.value.sync_point == "test_save_state"

    def test_save_state_logs_success(self, model):
        """
        Verify save_state() logs success message when database write succeeds.

        This test ensures that successful saves are logged for debugging and
        audit trail purposes.
        """
        # Setup: Mock successful update_state call
        model.dynasty_api.update_state.return_value = None

        # Mock logger.debug to capture log messages
        with patch.object(model.logger, 'debug') as mock_debug:
            # Execute
            result = model.save_state("2025-09-10", "REGULAR_SEASON", 2)

            # Assert: Success logged
            assert result is True
            mock_debug.assert_called_once()

            # Verify log message contains key information
            log_message = mock_debug.call_args[0][0]
            assert "Dynasty state saved" in log_message
            assert "test_dynasty" in log_message
            assert "2025" in log_message
            assert "2025-09-10" in log_message
            assert "REGULAR_SEASON" in log_message

    def test_save_state_no_silent_failures(self, model):
        """
        Verify save_state() has no silent failure mechanisms.

        This test inspects the save_state() method to ensure:
        1. No print statements are used for error reporting
        2. No try/except blocks that catch and hide exceptions
        3. All exceptions propagate to caller

        This is a code inspection test that verifies the implementation
        follows fail-loud principles.
        """
        # Get the source code of save_state method
        import inspect
        source = inspect.getsource(model.save_state)

        # Assert: No print statements in save_state
        assert 'print(' not in source, \
            "save_state() must not use print() for error reporting"

        # Assert: No try/except blocks that catch exceptions
        # Look for actual exception handling, not comments mentioning "exception"
        lines = source.split('\n')
        code_lines = [line for line in lines if not line.strip().startswith('#')]

        try_blocks = [line for line in code_lines if 'try:' in line]
        except_blocks = [line for line in code_lines if line.strip().startswith('except')]

        # In the actual implementation, there should be NO try/except at all
        assert len(try_blocks) == 0, \
            f"save_state() must not use try/except blocks that hide exceptions. Found: {try_blocks}"
        assert len(except_blocks) == 0, \
            f"save_state() must not catch exceptions - they should propagate. Found: {except_blocks}"

    def test_save_state_returns_true_on_success(self, model):
        """
        Verify save_state() returns True when database write succeeds.

        This test ensures the return value contract is maintained:
        - Returns True on success
        - Raises exception on failure (never returns False)
        """
        # Setup: Mock successful update_state call
        model.dynasty_api.update_state.return_value = None

        # Execute
        result = model.save_state("2025-09-10", "REGULAR_SEASON", 2)

        # Assert: Returns True on success
        assert result is True

        # Verify update_state was called
        model.dynasty_api.update_state.assert_called_once()

    def test_save_state_passes_all_parameters(self, model):
        """
        Verify save_state() passes all parameters correctly to update_state().

        This test ensures parameter forwarding is correct including:
        - dynasty_id from model state
        - season from model.season property
        - All method parameters (current_date, current_phase, current_week, last_simulated_game_id)
        """
        # Setup: Mock successful update_state call
        model.dynasty_api.update_state.return_value = None

        # Execute with all parameters
        model.save_state(
            current_date="2025-09-15",
            current_phase="REGULAR_SEASON",
            current_week=3,
            last_simulated_game_id="game_123"
        )

        # Assert: All parameters passed correctly
        model.dynasty_api.update_state.assert_called_once_with(
            dynasty_id="test_dynasty",
            season=2025,  # From model.season property
            current_date="2025-09-15",
            current_phase="REGULAR_SEASON",
            current_week=3,
            last_simulated_game_id="game_123"
        )

    def test_save_state_with_optional_parameters_none(self, model):
        """
        Verify save_state() correctly handles optional parameters set to None.

        This test ensures optional parameters (current_week, last_simulated_game_id)
        are correctly passed as None when not provided.
        """
        # Setup: Mock successful update_state call
        model.dynasty_api.update_state.return_value = None

        # Execute with minimal parameters (optional params use defaults)
        model.save_state(
            current_date="2025-09-05",
            current_phase="REGULAR_SEASON"
        )

        # Assert: Optional parameters passed as None
        model.dynasty_api.update_state.assert_called_once_with(
            dynasty_id="test_dynasty",
            season=2025,
            current_date="2025-09-05",
            current_phase="REGULAR_SEASON",
            current_week=None,  # Default value
            last_simulated_game_id=None  # Default value
        )

    def test_save_state_uses_season_property(self, model):
        """
        Verify save_state() uses the season property (SINGLE SOURCE OF TRUTH).

        This test ensures save_state() reads season from model.season property
        which queries the database via get_latest_state(), not from initialization.
        """
        # Setup: Mock get_latest_state to return different season
        model.dynasty_api.get_latest_state.return_value = {
            'current_date': '2026-09-05',
            'current_phase': 'REGULAR_SEASON',
            'current_week': 1,
            'season': 2026,  # Different from initialization season
            'last_simulated_game_id': None
        }

        # Setup: Mock successful update_state call
        model.dynasty_api.update_state.return_value = None

        # Execute
        model.save_state("2026-09-10", "REGULAR_SEASON", 2)

        # Assert: Season comes from property (2026), not initialization (2025)
        call_args = model.dynasty_api.update_state.call_args
        assert call_args[1]['season'] == 2026, \
            "save_state() must use model.season property (database value), not initialization value"

    def test_save_state_exception_message_contains_context(self, model):
        """
        Verify CalendarSyncPersistenceException contains detailed context.

        This test ensures that when exceptions are raised, they contain
        sufficient context for debugging and error reporting.
        """
        # Setup: Mock update_state to raise exception with rich context
        test_exception = CalendarSyncPersistenceException(
            operation="dynasty_state_update",
            sync_point="save_state",
            state_info={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "intended_date": "2025-09-10",
                "intended_phase": "REGULAR_SEASON",
                "intended_week": 2,
                "error": "SQLite database locked"
            }
        )
        model.dynasty_api.update_state.side_effect = test_exception

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            model.save_state("2025-09-10", "REGULAR_SEASON", 2)

        # Verify exception contains all context
        exception = exc_info.value
        assert exception.operation == "dynasty_state_update"
        assert exception.sync_point == "save_state"
        assert exception.state_info["dynasty_id"] == "test_dynasty"
        assert exception.state_info["season"] == 2025
        assert exception.state_info["intended_date"] == "2025-09-10"
        assert exception.state_info["intended_phase"] == "REGULAR_SEASON"
        assert exception.state_info["intended_week"] == 2

    def test_save_state_no_return_value_checking(self, model):
        """
        Verify save_state() does NOT check return values for failure detection.

        This test ensures save_state() relies on exception propagation instead
        of checking return values (which leads to silent failures).

        The old pattern was:
            if not success:
                print("ERROR")  # Silent failure!

        The new pattern is:
            # update_state() raises exception on failure
            # No need to check return value
        """
        # Get the source code of save_state method
        import inspect
        source = inspect.getsource(model.save_state)

        # Assert: No "if not" or "if success" patterns
        assert "if not" not in source, \
            "save_state() must not check return values - use exception propagation"
        assert "if success" not in source, \
            "save_state() must not check return values - use exception propagation"

        # Assert: No boolean return value checking from update_state
        assert "= self.dynasty_api.update_state" not in source or \
               "success = self.dynasty_api.update_state" not in source, \
            "save_state() must not capture update_state() return value for checking"


class TestSimulationDataModelExceptionTypes:
    """Test suite for different exception types and edge cases"""

    @pytest.fixture
    def model(self):
        """Create SimulationDataModel with mocked dependencies"""
        with patch('simulation_data_model.DynastyStateAPI') as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api

            # Mock get_latest_state to return a state with season 2025
            mock_api.get_latest_state.return_value = {
                'current_date': '2025-09-05',
                'current_phase': 'REGULAR_SEASON',
                'current_week': 1,
                'season': 2025,
                'last_simulated_game_id': None
            }

            model = SimulationDataModel(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )
            model.dynasty_api = mock_api
            yield model

    def test_save_state_sqlite_error_propagates(self, model):
        """
        Verify SQLite errors are wrapped in CalendarSyncPersistenceException.

        When DynastyStateAPI encounters a database error, it should raise
        CalendarSyncPersistenceException with the underlying error details.
        """
        # Setup: Mock update_state to raise database-related exception
        db_error = CalendarSyncPersistenceException(
            operation="database_write",
            sync_point="update_state",
            state_info={
                "error": "SQLite Error: database is locked",
                "database_path": "test.db"
            }
        )
        model.dynasty_api.update_state.side_effect = db_error

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            model.save_state("2025-09-10", "REGULAR_SEASON", 2)

        # Verify error details preserved
        assert "database is locked" in exc_info.value.state_info.get("error", "")

    def test_save_state_connection_error_propagates(self, model):
        """
        Verify connection errors are wrapped in CalendarSyncPersistenceException.
        """
        # Setup: Mock connection failure
        conn_error = CalendarSyncPersistenceException(
            operation="database_connection",
            sync_point="update_state",
            state_info={
                "error": "Unable to connect to database",
                "database_path": "test.db"
            }
        )
        model.dynasty_api.update_state.side_effect = conn_error

        # Execute & Assert
        with pytest.raises(CalendarSyncPersistenceException) as exc_info:
            model.save_state("2025-09-10", "REGULAR_SEASON", 2)

        # Verify error type
        assert exc_info.value.operation == "database_connection"


class TestSimulationDataModelLogging:
    """Test suite for logging behavior in save_state()"""

    @pytest.fixture
    def model(self):
        """Create SimulationDataModel with mocked dependencies"""
        with patch('simulation_data_model.DynastyStateAPI') as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api

            # Mock get_latest_state to return a state with season 2025
            mock_api.get_latest_state.return_value = {
                'current_date': '2025-09-05',
                'current_phase': 'REGULAR_SEASON',
                'current_week': 1,
                'season': 2025,
                'last_simulated_game_id': None
            }

            model = SimulationDataModel(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )
            model.dynasty_api = mock_api
            yield model

    def test_save_state_debug_log_format(self, model):
        """
        Verify save_state() debug log contains all required information.

        The log message should include:
        - "Dynasty state saved" prefix
        - dynasty_id
        - season
        - date
        - phase
        """
        # Setup
        model.dynasty_api.update_state.return_value = None

        with patch.object(model.logger, 'debug') as mock_debug:
            # Execute
            model.save_state("2025-09-15", "PLAYOFFS", 3, "game_456")

            # Assert: Log format
            mock_debug.assert_called_once()
            log_message = mock_debug.call_args[0][0]

            assert "Dynasty state saved" in log_message
            assert "dynasty_id=test_dynasty" in log_message
            assert "season=2025" in log_message
            assert "date=2025-09-15" in log_message
            assert "phase=PLAYOFFS" in log_message

    def test_save_state_no_error_logging_on_success(self, model):
        """
        Verify save_state() does NOT log errors when successful.

        Success should only trigger debug logging, not error logging.
        """
        # Setup
        model.dynasty_api.update_state.return_value = None

        with patch.object(model.logger, 'error') as mock_error, \
             patch.object(model.logger, 'warning') as mock_warning:

            # Execute
            model.save_state("2025-09-10", "REGULAR_SEASON", 2)

            # Assert: No error or warning logs on success
            mock_error.assert_not_called()
            mock_warning.assert_not_called()

    def test_save_state_exception_not_logged(self, model):
        """
        Verify save_state() does NOT log exceptions (lets them propagate).

        When exceptions occur, they should propagate to the caller for
        proper error handling. The method should NOT catch and log them.
        """
        # Setup
        test_exception = CalendarSyncPersistenceException(
            operation="test_op",
            sync_point="test_point",
            state_info={}
        )
        model.dynasty_api.update_state.side_effect = test_exception

        with patch.object(model.logger, 'error') as mock_error, \
             patch.object(model.logger, 'warning') as mock_warning:

            # Execute & Assert
            with pytest.raises(CalendarSyncPersistenceException):
                model.save_state("2025-09-10", "REGULAR_SEASON", 2)

            # Verify: No logging of the exception (it propagates instead)
            mock_error.assert_not_called()
            mock_warning.assert_not_called()


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
