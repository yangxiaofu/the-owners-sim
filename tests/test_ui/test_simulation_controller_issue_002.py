"""
Comprehensive test suite for ISSUE-002 refactoring (Template Method Pattern).

Tests the _execute_simulation_with_persistence() template method and all 4
refactored simulation methods (advance_day, advance_week, advance_to_end_of_phase,
simulate_to_new_season) to ensure behavioral equivalence after refactoring.

Test Coverage:
- Template method workflow (8 tests)
- advance_day() refactored method (4 tests)
- advance_week() refactored method (4 tests)
- advance_to_end_of_phase() refactored method (4 tests)
- simulate_to_new_season() refactored method (4 tests)
- Integration test (1 test)

Total: 25 tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from PySide6.QtWidgets import QDialog
from typing import Dict, Any

# Import the controller
from ui.controllers.simulation_controller import SimulationController

# Import exceptions
from src.database.sync_exceptions import (
    CalendarSyncPersistenceException,
    CalendarSyncDriftException
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database path for testing."""
    return str(tmp_path / "test_sim.db")


@pytest.fixture
def mock_controller(mock_db_path):
    """
    Create a SimulationController with mocked dependencies.

    Mocks:
    - state_model (SimulationDataModel)
    - season_controller (SeasonCycleController)
    - event_db (EventDatabaseAPI)
    - parent (QWidget)
    """
    with patch('ui.controllers.simulation_controller.SimulationDataModel') as MockDataModel, \
         patch('ui.controllers.simulation_controller.EventDatabaseAPI'), \
         patch('ui.controllers.simulation_controller.SeasonCycleController') as MockSeasonController:

        # Configure state model mock to return proper data
        mock_state_model = MockDataModel.return_value
        mock_state_model.initialize_state.return_value = {
            'current_date': '2025-09-05',
            'current_phase': 'REGULAR_SEASON',
            'current_week': 1
        }
        mock_state_model.season = 2025
        mock_state_model.get_current_week.return_value = 1

        # Configure season controller mock
        mock_season_ctrl = MockSeasonController.return_value
        mock_season_ctrl.phase_state = Mock()
        mock_season_ctrl.phase_state.phase = Mock()
        mock_season_ctrl.phase_state.phase.value = "regular_season"

        controller = SimulationController(
            db_path=mock_db_path,
            dynasty_id="test_dynasty",
            season=2025
        )

        # Mock parent() method to return None for dialog creation
        controller.parent = Mock(return_value=None)

        # Verify internal state was set correctly
        assert controller.current_date_str == "2025-09-05"

        yield controller


# ============================================================================
# Template Method Tests (8 tests)
# ============================================================================

def test_template_method_successful_workflow(mock_controller):
    """Test template method executes full workflow successfully."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    pre_save_called = []
    post_save_called = []

    def pre_save_hook(result):
        pre_save_called.append(result)

    def post_save_hook(result):
        post_save_called.append(result)

    # Mock _save_state_to_db to avoid actual DB operations
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller._execute_simulation_with_persistence(
        operation_name="test_op",
        backend_method=backend_method,
        hooks={
            'pre_save': pre_save_hook,
            'post_save': post_save_hook
        },
        extractors={
            'extract_state': lambda r: (r['date'], r['phase'], 1),
            'build_success_result': lambda r: r
        },
        failure_dict_factory=lambda msg: {"success": False, "message": msg}
    )

    # Verify
    assert result == backend_result
    assert backend_method.called
    assert len(pre_save_called) == 1
    assert len(post_save_called) == 1
    mock_controller._save_state_to_db.assert_called_once_with("2025-09-06", "regular_season", 1)


def test_template_method_backend_failure(mock_controller):
    """Test template method handles backend operation failure."""
    # Setup
    backend_result = {"success": False, "message": "Backend failed"}
    backend_method = Mock(return_value=backend_result)

    # Execute
    result = mock_controller._execute_simulation_with_persistence(
        operation_name="test_op",
        backend_method=backend_method,
        hooks={'pre_save': None, 'post_save': None},
        extractors={
            'extract_state': lambda r: (r.get('date', ''), r.get('phase', ''), 1),
            'build_success_result': lambda r: r
        },
        failure_dict_factory=lambda msg: {"success": False, "message": msg}
    )

    # Verify
    assert result["success"] is False
    assert result["message"] == "Backend failed"


def test_template_method_persistence_exception_abort(mock_controller):
    """Test template method handles CalendarSyncPersistenceException with user abort."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    # Mock _save_state_to_db to raise exception
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncPersistenceException(
            operation="test_save",
            sync_point="test_point",
            state_info={}
        )
    )

    # Mock dialog to return Rejected (abort)
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Rejected
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller._execute_simulation_with_persistence(
            operation_name="test_op",
            backend_method=backend_method,
            hooks={'pre_save': None, 'post_save': None},
            extractors={
                'extract_state': lambda r: (r['date'], r['phase'], 1),
                'build_success_result': lambda r: r
            },
            failure_dict_factory=lambda msg: {"success": False, "message": msg}
        )

    # Verify
    assert result["success"] is False
    assert "aborted" in result["message"]


def test_template_method_persistence_exception_retry(mock_controller):
    """Test template method handles CalendarSyncPersistenceException with retry."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    # Mock _save_state_to_db to fail once, then succeed
    mock_controller._save_state_to_db = Mock(
        side_effect=[
            CalendarSyncPersistenceException(
                operation="test_save",
                sync_point="test_point",
                state_info={}
            ),
            None  # Success on retry
        ]
    )

    # Mock dialog to return Accepted with retry action
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Accepted
        mock_dialog.get_recovery_action.return_value = "retry"
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller._execute_simulation_with_persistence(
            operation_name="test_op",
            backend_method=backend_method,
            hooks={'pre_save': None, 'post_save': None},
            extractors={
                'extract_state': lambda r: (r['date'], r['phase'], 1),
                'build_success_result': lambda r: r
            },
            failure_dict_factory=lambda msg: {"success": False, "message": msg}
        )

    # Verify - should succeed on retry
    assert result["success"] is True
    assert mock_controller._save_state_to_db.call_count == 2


def test_template_method_persistence_exception_reload(mock_controller):
    """Test template method handles CalendarSyncPersistenceException with reload."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    # Mock _save_state_to_db to raise exception
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncPersistenceException(
            operation="test_save",
            sync_point="test_point",
            state_info={}
        )
    )

    # Mock _load_state
    mock_controller._load_state = Mock()

    # Mock dialog to return Accepted with reload action
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Accepted
        mock_dialog.get_recovery_action.return_value = "reload"
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller._execute_simulation_with_persistence(
            operation_name="test_op",
            backend_method=backend_method,
            hooks={'pre_save': None, 'post_save': None},
            extractors={
                'extract_state': lambda r: (r['date'], r['phase'], 1),
                'build_success_result': lambda r: r
            },
            failure_dict_factory=lambda msg: {"success": False, "message": msg}
        )

    # Verify
    assert result["success"] is False
    assert "reloaded" in result["message"]
    mock_controller._load_state.assert_called_once()


def test_template_method_drift_exception(mock_controller):
    """Test template method handles CalendarSyncDriftException."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    # Mock _save_state_to_db to raise drift exception
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncDriftException(
            calendar_date="2025-09-10",
            db_date="2025-09-06",
            drift_days=4,
            sync_point="test_point",
            state_info={}
        )
    )

    # Mock dialog to return Rejected (abort)
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Rejected
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller._execute_simulation_with_persistence(
            operation_name="test_op",
            backend_method=backend_method,
            hooks={'pre_save': None, 'post_save': None},
            extractors={
                'extract_state': lambda r: (r['date'], r['phase'], 1),
                'build_success_result': lambda r: r
            },
            failure_dict_factory=lambda msg: {"success": False, "message": msg}
        )

    # Verify
    assert result["success"] is False
    assert "aborted" in result["message"]


def test_template_method_generic_exception(mock_controller):
    """Test template method handles unexpected exceptions."""
    # Setup
    backend_method = Mock(side_effect=ValueError("Unexpected error"))

    # Mock QMessageBox to avoid UI display
    with patch('ui.controllers.simulation_controller.QMessageBox.critical'):
        # Execute
        result = mock_controller._execute_simulation_with_persistence(
            operation_name="test_op",
            backend_method=backend_method,
            hooks={'pre_save': None, 'post_save': None},
            extractors={
                'extract_state': lambda r: (r['date'], r['phase'], 1),
                'build_success_result': lambda r: r
            },
            failure_dict_factory=lambda msg: {"success": False, "message": msg}
        )

    # Verify
    assert result["success"] is False
    assert "Unexpected error" in result["message"]


def test_template_method_no_hooks(mock_controller):
    """Test template method works without optional hooks."""
    # Setup
    backend_result = {"success": True, "date": "2025-09-06", "phase": "regular_season"}
    backend_method = Mock(return_value=backend_result)

    # Mock _save_state_to_db to avoid actual DB operations
    mock_controller._save_state_to_db = Mock()

    # Execute without hooks
    result = mock_controller._execute_simulation_with_persistence(
        operation_name="test_op",
        backend_method=backend_method,
        hooks={'pre_save': None, 'post_save': None},
        extractors={
            'extract_state': lambda r: (r['date'], r['phase'], 1),
            'build_success_result': lambda r: r
        },
        failure_dict_factory=lambda msg: {"success": False, "message": msg}
    )

    # Verify
    assert result["success"] is True
    assert result == backend_result


# ============================================================================
# advance_day() Tests (4 tests)
# ============================================================================

def test_advance_day_success(mock_controller):
    """Test advance_day() successfully advances simulation."""
    # Setup
    mock_controller.season_controller.advance_day = Mock(return_value={
        "success": True,
        "date": "2025-09-06",
        "current_phase": "regular_season",
        "results": [{"game_id": 1}, {"game_id": 2}]
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_day()

    # Verify
    assert result["success"] is True
    assert result["date"] == "2025-09-06"
    assert result["games_played"] == 2
    assert len(result["results"]) == 2


def test_advance_day_backend_failure(mock_controller):
    """Test advance_day() handles backend failure."""
    # Setup
    mock_controller.season_controller.advance_day = Mock(return_value={
        "success": False,
        "message": "No games scheduled"
    })

    # Execute
    result = mock_controller.advance_day()

    # Verify
    assert result["success"] is False
    assert "No games scheduled" in result["message"]


def test_advance_day_phase_transition(mock_controller):
    """Test advance_day() detects phase transition and emits signal."""
    # Setup
    mock_controller.season_controller.advance_day = Mock(return_value={
        "success": True,
        "date": "2026-01-05",
        "current_phase": "playoffs",
        "results": []
    })
    mock_controller._save_state_to_db = Mock()

    # Mock signal emission
    phase_changed_emitted = []
    mock_controller.phase_changed.connect(lambda old, new: phase_changed_emitted.append((old, new)))

    # Execute
    result = mock_controller.advance_day()

    # Verify
    assert result["success"] is True
    assert len(phase_changed_emitted) == 1
    assert phase_changed_emitted[0] == ("regular_season", "playoffs")


def test_advance_day_with_calendar_sync_error(mock_controller):
    """Test advance_day() handles calendar sync error with reload."""
    # Setup
    mock_controller.season_controller.advance_day = Mock(return_value={
        "success": True,
        "date": "2025-09-06",
        "current_phase": "regular_season",
        "results": []
    })
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncPersistenceException(
            operation="save_state",
            sync_point="advance_day",
            state_info={}
        )
    )
    mock_controller._load_state = Mock()

    # Mock dialog to reload
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Accepted
        mock_dialog.get_recovery_action.return_value = "reload"
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller.advance_day()

    # Verify
    assert result["success"] is False
    assert "reloaded" in result["message"]


# ============================================================================
# advance_week() Tests (4 tests)
# ============================================================================

def test_advance_week_success(mock_controller):
    """Test advance_week() successfully advances simulation."""
    # Setup
    mock_controller.season_controller.advance_week = Mock(return_value={
        "success": True,
        "date": "2025-09-12",
        "current_phase": "regular_season",
        "weeks_simulated": 1
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_week()

    # Verify
    assert result["success"] is True
    assert result["date"] == "2025-09-12"
    # Note: current_week is now queried from database, not tracked as instance variable


def test_advance_week_backend_failure(mock_controller):
    """Test advance_week() handles backend failure."""
    # Setup
    mock_controller.season_controller.advance_week = Mock(return_value={
        "success": False,
        "message": "Week advancement failed"
    })

    # Execute
    result = mock_controller.advance_week()

    # Verify
    assert result["success"] is False
    assert "Week advancement failed" in result["message"]


def test_advance_week_no_increment_in_playoffs(mock_controller):
    """Test advance_week() succeeds in playoffs phase."""
    # Setup
    mock_controller.season_controller.phase_state.phase.value = "playoffs"
    mock_controller.season_controller.advance_week = Mock(return_value={
        "success": True,
        "date": "2026-01-12",
        "current_phase": "playoffs",
        "weeks_simulated": 1
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_week()

    # Verify
    assert result["success"] is True
    assert result["date"] == "2026-01-12"
    # Note: Week tracking is now handled by schedule database queries


def test_advance_week_with_calendar_sync_error(mock_controller):
    """Test advance_week() handles calendar sync error with abort."""
    # Setup
    mock_controller.season_controller.advance_week = Mock(return_value={
        "success": True,
        "date": "2025-09-12",
        "current_phase": "regular_season"
    })
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncPersistenceException(
            operation="save_state",
            sync_point="advance_week",
            state_info={}
        )
    )

    # Mock dialog to abort
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Rejected
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller.advance_week()

    # Verify
    assert result["success"] is False
    assert "aborted" in result["message"]


# ============================================================================
# advance_to_end_of_phase() Tests (4 tests)
# ============================================================================

def test_advance_to_end_of_phase_success(mock_controller):
    """Test advance_to_end_of_phase() successfully completes phase."""
    # Setup
    mock_controller.season_controller.simulate_to_phase_end = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-01-05",
        "weeks_simulated": 17,
        "total_games": 272,
        "starting_phase": "regular_season",
        "ending_phase": "playoffs",
        "phase_transition": True
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_to_end_of_phase()

    # Verify
    assert result["success"] is True
    assert result["weeks_simulated"] == 17
    assert "Regular Season complete!" in result["message"]


def test_advance_to_end_of_phase_with_milestone(mock_controller):
    """Test advance_to_end_of_phase() handles offseason milestone stop."""
    # Setup
    mock_controller.season_controller.simulate_to_phase_end = Mock(return_value={
        "success": True,
        "start_date": "2026-02-15",
        "end_date": "2026-03-12",
        "days_simulated": 25,
        "milestone_reached": "Franchise Tag Deadline",
        "milestone_date": "2026-03-12",
        "starting_phase": "offseason",
        "ending_phase": "offseason"
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_to_end_of_phase()

    # Verify
    assert result["success"] is True
    assert "Stopped at: Franchise Tag Deadline" in result["message"]


def test_advance_to_end_of_phase_with_progress_callback(mock_controller):
    """Test advance_to_end_of_phase() passes progress callback to backend."""
    # Setup
    progress_updates = []
    def progress_callback(week, games):
        progress_updates.append((week, games))

    mock_controller.season_controller.simulate_to_phase_end = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-01-05",
        "weeks_simulated": 17,
        "total_games": 272,
        "starting_phase": "regular_season",
        "ending_phase": "playoffs",
        "phase_transition": True
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.advance_to_end_of_phase(progress_callback=progress_callback)

    # Verify callback was passed
    mock_controller.season_controller.simulate_to_phase_end.assert_called_once_with(
        progress_callback=progress_callback
    )


def test_advance_to_end_of_phase_with_calendar_sync_error(mock_controller):
    """Test advance_to_end_of_phase() handles high drift risk error."""
    # Setup
    mock_controller.season_controller.simulate_to_phase_end = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-01-05",
        "weeks_simulated": 17,
        "total_games": 272,
        "starting_phase": "regular_season",
        "ending_phase": "playoffs",
        "phase_transition": True
    })
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncDriftException(
            calendar_date="2026-02-01",
            db_date="2026-01-05",
            drift_days=27,
            sync_point="advance_to_end_of_phase",
            state_info={}
        )
    )

    # Mock dialog to abort
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Rejected
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller.advance_to_end_of_phase()

    # Verify
    assert result["success"] is False
    assert "aborted" in result["message"]


# ============================================================================
# simulate_to_new_season() Tests (4 tests)
# ============================================================================

def test_simulate_to_new_season_success(mock_controller):
    """Test simulate_to_new_season() successfully completes season."""
    # Setup
    mock_controller.season_controller.simulate_to_new_season = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-08-01",
        "weeks_simulated": 43,
        "total_games": 285,
        "starting_phase": "regular_season",
        "ending_phase": "preseason"
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.simulate_to_new_season()

    # Verify
    assert result["success"] is True
    assert result["weeks_simulated"] == 43
    assert result["ending_phase"] == "preseason"


def test_simulate_to_new_season_backend_failure(mock_controller):
    """Test simulate_to_new_season() handles backend failure."""
    # Setup
    mock_controller.season_controller.simulate_to_new_season = Mock(return_value={
        "success": False,
        "message": "Season simulation failed"
    })

    # Execute
    result = mock_controller.simulate_to_new_season()

    # Verify
    assert result["success"] is False
    assert "Season simulation failed" in result["message"]


def test_simulate_to_new_season_uses_ending_phase(mock_controller):
    """Test simulate_to_new_season() uses ending_phase from summary for save."""
    # Setup
    mock_controller.season_controller.simulate_to_new_season = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-08-01",
        "weeks_simulated": 43,
        "total_games": 285,
        "starting_phase": "regular_season",
        "ending_phase": "preseason"
    })
    mock_controller._save_state_to_db = Mock()

    # Execute
    result = mock_controller.simulate_to_new_season()

    # Verify save used ending_phase
    mock_controller._save_state_to_db.assert_called_once_with(
        "2026-08-01",
        "preseason",  # ending_phase from summary
        1
    )


def test_simulate_to_new_season_with_calendar_sync_error(mock_controller):
    """Test simulate_to_new_season() handles critical drift risk error."""
    # Setup
    mock_controller.season_controller.simulate_to_new_season = Mock(return_value={
        "success": True,
        "start_date": "2025-09-05",
        "end_date": "2026-08-01",
        "weeks_simulated": 43,
        "total_games": 285,
        "starting_phase": "regular_season",
        "ending_phase": "preseason"
    })
    mock_controller._save_state_to_db = Mock(
        side_effect=CalendarSyncPersistenceException(
            operation="save_state",
            sync_point="simulate_to_new_season",
            state_info={}
        )
    )
    mock_controller._load_state = Mock()

    # Mock dialog to reload
    with patch('ui.controllers.simulation_controller.CalendarSyncRecoveryDialog') as mock_dialog_class:
        mock_dialog = Mock()
        mock_dialog.exec.return_value = QDialog.Accepted
        mock_dialog.get_recovery_action.return_value = "reload"
        mock_dialog_class.return_value = mock_dialog

        # Execute
        result = mock_controller.simulate_to_new_season()

    # Verify
    assert result["success"] is False
    assert "reloaded" in result["message"]


# ============================================================================
# Integration Test (1 test)
# ============================================================================

def test_integration_full_simulation_flow(mock_controller):
    """
    Integration test: Simulate complete flow from day → week → phase end.

    Tests that all refactored methods work together correctly.
    """
    # Setup
    mock_controller._save_state_to_db = Mock()

    # Day advancement
    mock_controller.season_controller.advance_day = Mock(return_value={
        "success": True,
        "date": "2025-09-06",
        "current_phase": "regular_season",
        "results": [{"game_id": 1}]
    })

    day_result = mock_controller.advance_day()
    assert day_result["success"] is True
    assert day_result["games_played"] == 1

    # Week advancement
    mock_controller.season_controller.advance_week = Mock(return_value={
        "success": True,
        "date": "2025-09-13",
        "current_phase": "regular_season"
    })

    week_result = mock_controller.advance_week()
    assert week_result["success"] is True
    # Note: Week tracking is now handled by schedule database

    # Phase advancement
    mock_controller.season_controller.simulate_to_phase_end = Mock(return_value={
        "success": True,
        "start_date": "2025-09-13",
        "end_date": "2026-01-05",
        "weeks_simulated": 16,
        "total_games": 256,
        "starting_phase": "regular_season",
        "ending_phase": "playoffs",
        "phase_transition": True
    })

    phase_result = mock_controller.advance_to_end_of_phase()
    assert phase_result["success"] is True
    assert phase_result["phase_transition"] is True

    # Verify all operations called _save_state_to_db
    assert mock_controller._save_state_to_db.call_count == 3
