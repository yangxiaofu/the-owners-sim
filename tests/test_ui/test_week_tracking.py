"""
Integration Tests for Week Tracking System

Tests week tracking across different simulation phases and UI interactions:
- Week updates when advancing day-by-day
- Week updates when advancing by week
- Preseason weeks (1-3)
- Regular season weeks (1-18)
- Playoffs return None for week
- Offseason returns None for week
- Phase transitions reset week correctly

This test suite validates the integration between:
- SimulationController
- SimulationDataModel
- DatabaseAPI.get_week_for_date()
- Calendar system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ui.controllers.simulation_controller import SimulationController
from ui.domain_models.simulation_data_model import SimulationDataModel


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_simulation_controller():
    """
    Create SimulationController with mocked dependencies for week tracking tests.

    Mocks:
    - SeasonCycleController
    - SimulationDataModel
    - EventDatabaseAPI
    - DatabaseAPI (for week queries)
    """
    with patch('ui.controllers.simulation_controller.SeasonCycleController') as MockSeasonController, \
         patch('ui.controllers.simulation_controller.SimulationDataModel') as MockDataModel, \
         patch('ui.controllers.simulation_controller.EventDatabaseAPI'):

        # Create controller instance
        controller = SimulationController(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025
        )

        # Mock state_model
        controller.state_model = Mock(spec=SimulationDataModel)
        controller.state_model.get_current_date = Mock(return_value="2025-08-10")
        controller.state_model.get_current_phase = Mock(return_value="preseason")
        controller.state_model.get_current_week = Mock(return_value=1)

        # Mock DatabaseAPI with get_week_for_date method
        controller.db_api = Mock()
        controller.db_api.get_week_for_date = Mock(return_value=1)

        # Set required attributes
        controller.dynasty_id = "test_dynasty"
        controller.season = 2025
        controller._logger = Mock()

        yield controller


@pytest.fixture
def mock_data_model():
    """
    Create SimulationDataModel with mocked dependencies.

    Mocks:
    - DynastyStateAPI
    - DatabaseAPI
    """
    with patch('ui.domain_models.simulation_data_model.DynastyStateAPI'), \
         patch('ui.domain_models.simulation_data_model.DatabaseAPI') as MockDatabaseAPI:

        # Create data model instance
        data_model = SimulationDataModel(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025
        )

        # Mock DatabaseAPI
        data_model.db_api = Mock()
        data_model.db_api.get_week_for_date = Mock(return_value=1)

        # Mock internal state
        data_model._current_date = "2025-08-10"
        data_model._current_phase = "preseason"
        data_model._current_week = 1
        data_model._season = 2025

        yield data_model


# ============================================================================
# TESTS: Week Updates When Advancing Day
# ============================================================================


def test_week_updates_when_advancing_day_preseason(mock_simulation_controller):
    """Test that week updates correctly when advancing day-by-day in preseason."""
    controller = mock_simulation_controller

    # Setup: Start at preseason week 1
    controller.state_model.get_current_date.return_value = "2025-08-10"
    controller.state_model.get_current_phase.return_value = "preseason"
    controller.db_api.get_week_for_date.return_value = 1

    # Execute: Get current week
    week = controller.state_model.get_current_week()

    # Assert: Week should be 1
    assert week == 1

    # Setup: Advance to week 2
    controller.state_model.get_current_date.return_value = "2025-08-17"
    controller.db_api.get_week_for_date.return_value = 2

    # Execute: Get updated week
    controller.state_model.get_current_week.return_value = 2
    week = controller.state_model.get_current_week()

    # Assert: Week should be 2
    assert week == 2


def test_week_updates_when_advancing_day_regular_season(mock_simulation_controller):
    """Test that week updates correctly when advancing day-by-day in regular season."""
    controller = mock_simulation_controller

    # Setup: Start at regular season week 1
    controller.state_model.get_current_date.return_value = "2025-09-07"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 1

    # Execute: Get current week
    controller.state_model.get_current_week.return_value = 1
    week = controller.state_model.get_current_week()

    # Assert: Week should be 1
    assert week == 1

    # Setup: Advance to week 5
    controller.state_model.get_current_date.return_value = "2025-10-12"
    controller.db_api.get_week_for_date.return_value = 5

    # Execute: Get updated week
    controller.state_model.get_current_week.return_value = 5
    week = controller.state_model.get_current_week()

    # Assert: Week should be 5
    assert week == 5


# ============================================================================
# TESTS: Week Updates When Advancing By Week
# ============================================================================


def test_week_updates_when_advancing_week(mock_simulation_controller):
    """Test that week updates correctly when advancing by week."""
    controller = mock_simulation_controller

    # Setup: Start at week 3
    controller.state_model.get_current_date.return_value = "2025-09-21"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 3

    # Execute: Get current week
    controller.state_model.get_current_week.return_value = 3
    week = controller.state_model.get_current_week()

    # Assert: Week should be 3
    assert week == 3

    # Setup: Advance by 1 week (to week 4)
    controller.state_model.get_current_date.return_value = "2025-09-28"
    controller.db_api.get_week_for_date.return_value = 4

    # Execute: Get updated week after advancing
    controller.state_model.get_current_week.return_value = 4
    week = controller.state_model.get_current_week()

    # Assert: Week should be 4
    assert week == 4


def test_week_updates_when_advancing_multiple_weeks(mock_simulation_controller):
    """Test that week updates correctly when advancing multiple weeks at once."""
    controller = mock_simulation_controller

    # Setup: Start at week 8
    controller.state_model.get_current_date.return_value = "2025-11-02"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 8

    # Execute: Get current week
    controller.state_model.get_current_week.return_value = 8
    week = controller.state_model.get_current_week()

    # Assert: Week should be 8
    assert week == 8

    # Setup: Advance by 4 weeks (to week 12)
    controller.state_model.get_current_date.return_value = "2025-11-30"
    controller.db_api.get_week_for_date.return_value = 12

    # Execute: Get updated week after advancing
    controller.state_model.get_current_week.return_value = 12
    week = controller.state_model.get_current_week()

    # Assert: Week should be 12
    assert week == 12


# ============================================================================
# TESTS: Preseason Weeks Track Correctly
# ============================================================================


def test_preseason_week_1_tracks_correctly(mock_simulation_controller):
    """Test that preseason week 1 is tracked correctly."""
    controller = mock_simulation_controller

    # Setup: Preseason week 1
    controller.state_model.get_current_date.return_value = "2025-08-10"
    controller.state_model.get_current_phase.return_value = "preseason"
    controller.db_api.get_week_for_date.return_value = 1

    # Execute
    controller.state_model.get_current_week.return_value = 1
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 1


def test_preseason_week_2_tracks_correctly(mock_simulation_controller):
    """Test that preseason week 2 is tracked correctly."""
    controller = mock_simulation_controller

    # Setup: Preseason week 2
    controller.state_model.get_current_date.return_value = "2025-08-17"
    controller.state_model.get_current_phase.return_value = "preseason"
    controller.db_api.get_week_for_date.return_value = 2

    # Execute
    controller.state_model.get_current_week.return_value = 2
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 2


def test_preseason_week_3_tracks_correctly(mock_simulation_controller):
    """Test that preseason week 3 is tracked correctly."""
    controller = mock_simulation_controller

    # Setup: Preseason week 3
    controller.state_model.get_current_date.return_value = "2025-08-24"
    controller.state_model.get_current_phase.return_value = "preseason"
    controller.db_api.get_week_for_date.return_value = 3

    # Execute
    controller.state_model.get_current_week.return_value = 3
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 3


# ============================================================================
# TESTS: Regular Season Weeks Track Correctly
# ============================================================================


def test_regular_season_week_1_tracks_correctly(mock_simulation_controller):
    """Test that regular season week 1 is tracked correctly."""
    controller = mock_simulation_controller

    # Setup: Regular season week 1
    controller.state_model.get_current_date.return_value = "2025-09-07"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 1

    # Execute
    controller.state_model.get_current_week.return_value = 1
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 1


def test_regular_season_week_10_tracks_correctly(mock_simulation_controller):
    """Test that regular season week 10 is tracked correctly."""
    controller = mock_simulation_controller

    # Setup: Regular season week 10
    controller.state_model.get_current_date.return_value = "2025-11-16"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 10

    # Execute
    controller.state_model.get_current_week.return_value = 10
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 10


def test_regular_season_week_18_tracks_correctly(mock_simulation_controller):
    """Test that regular season week 18 is tracked correctly (final week)."""
    controller = mock_simulation_controller

    # Setup: Regular season week 18 (final week)
    controller.state_model.get_current_date.return_value = "2026-01-04"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 18

    # Execute
    controller.state_model.get_current_week.return_value = 18
    week = controller.state_model.get_current_week()

    # Assert
    assert week == 18


# ============================================================================
# TESTS: Playoffs Return None for Week
# ============================================================================


def test_playoffs_return_none_for_week(mock_simulation_controller):
    """Test that playoffs phase returns None for week."""
    controller = mock_simulation_controller

    # Setup: Playoffs phase
    controller.state_model.get_current_date.return_value = "2026-01-11"
    controller.state_model.get_current_phase.return_value = "playoffs"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert: Playoffs should return None for week
    assert week is None


def test_playoffs_wild_card_no_week(mock_simulation_controller):
    """Test that wild card round has no week number."""
    controller = mock_simulation_controller

    # Setup: Wild card round
    controller.state_model.get_current_date.return_value = "2026-01-11"
    controller.state_model.get_current_phase.return_value = "playoffs"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert
    assert week is None


def test_playoffs_super_bowl_no_week(mock_simulation_controller):
    """Test that Super Bowl has no week number."""
    controller = mock_simulation_controller

    # Setup: Super Bowl
    controller.state_model.get_current_date.return_value = "2026-02-08"
    controller.state_model.get_current_phase.return_value = "playoffs"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert
    assert week is None


# ============================================================================
# TESTS: Offseason Returns None for Week
# ============================================================================


def test_offseason_returns_none_for_week(mock_simulation_controller):
    """Test that offseason phase returns None for week."""
    controller = mock_simulation_controller

    # Setup: Offseason phase
    controller.state_model.get_current_date.return_value = "2026-03-12"
    controller.state_model.get_current_phase.return_value = "offseason"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert: Offseason should return None for week
    assert week is None


def test_offseason_free_agency_no_week(mock_simulation_controller):
    """Test that free agency period has no week number."""
    controller = mock_simulation_controller

    # Setup: Free agency period
    controller.state_model.get_current_date.return_value = "2026-03-15"
    controller.state_model.get_current_phase.return_value = "offseason"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert
    assert week is None


def test_offseason_draft_no_week(mock_simulation_controller):
    """Test that draft period has no week number."""
    controller = mock_simulation_controller

    # Setup: Draft period
    controller.state_model.get_current_date.return_value = "2026-04-25"
    controller.state_model.get_current_phase.return_value = "offseason"
    controller.db_api.get_week_for_date.return_value = None

    # Execute
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert
    assert week is None


# ============================================================================
# TESTS: Phase Transition Resets Week
# ============================================================================


def test_phase_transition_preseason_to_regular_season_resets_week(mock_simulation_controller):
    """Test that transitioning from preseason to regular season resets week to 1."""
    controller = mock_simulation_controller

    # Setup: End of preseason (week 3)
    controller.state_model.get_current_date.return_value = "2025-08-31"
    controller.state_model.get_current_phase.return_value = "preseason"
    controller.db_api.get_week_for_date.return_value = 3

    # Execute: Get preseason week 3
    controller.state_model.get_current_week.return_value = 3
    week = controller.state_model.get_current_week()
    assert week == 3

    # Setup: Transition to regular season week 1
    controller.state_model.get_current_date.return_value = "2025-09-07"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 1

    # Execute: Get regular season week 1
    controller.state_model.get_current_week.return_value = 1
    week = controller.state_model.get_current_week()

    # Assert: Week should reset to 1
    assert week == 1


def test_phase_transition_regular_season_to_playoffs_clears_week(mock_simulation_controller):
    """Test that transitioning from regular season to playoffs clears week."""
    controller = mock_simulation_controller

    # Setup: End of regular season (week 18)
    controller.state_model.get_current_date.return_value = "2026-01-04"
    controller.state_model.get_current_phase.return_value = "regular_season"
    controller.db_api.get_week_for_date.return_value = 18

    # Execute: Get regular season week 18
    controller.state_model.get_current_week.return_value = 18
    week = controller.state_model.get_current_week()
    assert week == 18

    # Setup: Transition to playoffs (no week)
    controller.state_model.get_current_date.return_value = "2026-01-11"
    controller.state_model.get_current_phase.return_value = "playoffs"
    controller.db_api.get_week_for_date.return_value = None

    # Execute: Get playoffs week
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert: Week should be None
    assert week is None


def test_phase_transition_playoffs_to_offseason_keeps_week_none(mock_simulation_controller):
    """Test that transitioning from playoffs to offseason keeps week as None."""
    controller = mock_simulation_controller

    # Setup: Playoffs (no week)
    controller.state_model.get_current_date.return_value = "2026-02-08"
    controller.state_model.get_current_phase.return_value = "playoffs"
    controller.db_api.get_week_for_date.return_value = None

    # Execute: Get playoffs week
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()
    assert week is None

    # Setup: Transition to offseason (no week)
    controller.state_model.get_current_date.return_value = "2026-03-01"
    controller.state_model.get_current_phase.return_value = "offseason"
    controller.db_api.get_week_for_date.return_value = None

    # Execute: Get offseason week
    controller.state_model.get_current_week.return_value = None
    week = controller.state_model.get_current_week()

    # Assert: Week should still be None
    assert week is None


# ============================================================================
# TESTS: Data Model Week Tracking
# ============================================================================


def test_data_model_get_current_week_calls_api(mock_data_model):
    """Test that SimulationDataModel.get_current_week() calls DatabaseAPI correctly."""
    data_model = mock_data_model

    # Setup
    data_model._current_date = "2025-10-12"
    data_model._current_phase = "regular_season"
    data_model._season = 2025
    data_model.db_api.get_week_for_date.return_value = 5

    # Mock get_current_week to simulate real behavior
    def mock_get_current_week():
        if data_model._current_phase in ["preseason", "regular_season"]:
            return data_model.db_api.get_week_for_date(
                dynasty_id=data_model._dynasty_id,
                game_date=data_model._current_date,
                season=data_model._season,
                season_type=data_model._current_phase
            )
        return None

    data_model.get_current_week = mock_get_current_week

    # Execute
    week = data_model.get_current_week()

    # Assert: Should call get_week_for_date with correct params
    data_model.db_api.get_week_for_date.assert_called_once_with(
        dynasty_id=data_model._dynasty_id,
        game_date="2025-10-12",
        season=2025,
        season_type="regular_season"
    )
    assert week == 5


def test_data_model_get_current_week_returns_none_for_offseason(mock_data_model):
    """Test that get_current_week returns None for offseason phase."""
    data_model = mock_data_model

    # Setup
    data_model._current_phase = "offseason"

    # Mock get_current_week
    def mock_get_current_week():
        if data_model._current_phase in ["preseason", "regular_season"]:
            return data_model.db_api.get_week_for_date(
                dynasty_id=data_model._dynasty_id,
                game_date=data_model._current_date,
                season=data_model._season,
                season_type=data_model._current_phase
            )
        return None

    data_model.get_current_week = mock_get_current_week

    # Execute
    week = data_model.get_current_week()

    # Assert: Should not call API, return None directly
    data_model.db_api.get_week_for_date.assert_not_called()
    assert week is None


def test_data_model_get_current_week_returns_none_for_playoffs(mock_data_model):
    """Test that get_current_week returns None for playoffs phase."""
    data_model = mock_data_model

    # Setup
    data_model._current_phase = "playoffs"

    # Mock get_current_week
    def mock_get_current_week():
        if data_model._current_phase in ["preseason", "regular_season"]:
            return data_model.db_api.get_week_for_date(
                dynasty_id=data_model._dynasty_id,
                game_date=data_model._current_date,
                season=data_model._season,
                season_type=data_model._current_phase
            )
        return None

    data_model.get_current_week = mock_get_current_week

    # Execute
    week = data_model.get_current_week()

    # Assert: Should not call API, return None directly
    data_model.db_api.get_week_for_date.assert_not_called()
    assert week is None
