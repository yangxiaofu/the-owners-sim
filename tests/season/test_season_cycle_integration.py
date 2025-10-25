"""
Integration Test for SeasonCycleController Phase Transition System

Tests that SeasonCycleController properly integrates with the new testable
phase transition architecture (PhaseCompletionChecker + PhaseTransitionManager).
"""

import pytest
import tempfile
import os
from unittest.mock import Mock


class TestSeasonCycleIntegration:
    """Integration tests for SeasonCycleController with phase transition system"""

    @pytest.fixture
    def temp_database(self):
        """Create a temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        try:
            os.unlink(path)
        except:
            pass

    def test_season_cycle_controller_creates_default_checkers(self, temp_database):
        """Test that SeasonCycleController creates default phase checkers"""
        # conftest.py already adds src/ to path
        from src.season.season_cycle_controller import SeasonCycleController
        from src.calendar.date_models import Date

        # Act: Create controller (should create default checkers)
        controller = SeasonCycleController(
            database_path=temp_database,
            dynasty_id="test_dynasty",
            season_year=2024,
            start_date=Date(2024, 9, 4),
            verbose_logging=False
        )

        # Assert: Check that phase transition components exist
        assert hasattr(controller, 'phase_completion_checker')
        assert hasattr(controller, 'phase_transition_manager')
        assert controller.phase_completion_checker is not None
        assert controller.phase_transition_manager is not None

    def test_season_cycle_controller_accepts_custom_checkers(self, temp_database):
        """Test that SeasonCycleController accepts injected phase checkers"""
        # conftest.py already adds src/ to path
        from src.season.season_cycle_controller import SeasonCycleController
        from src.season.phase_transition.phase_completion_checker import PhaseCompletionChecker
        from src.season.phase_transition.phase_transition_manager import PhaseTransitionManager
        from src.calendar.date_models import Date
        from src.calendar.phase_state import PhaseState
        from src.calendar.season_phase_tracker import SeasonPhase

        # Arrange: Create custom checkers for testing
        mock_checker = PhaseCompletionChecker(
            get_games_played=lambda: 0,
            get_current_date=lambda: Date(2024, 9, 5),
            get_last_regular_season_game_date=lambda: Date(2025, 1, 7),
            is_super_bowl_complete=lambda: False
        )

        phase_state = PhaseState(SeasonPhase.REGULAR_SEASON)
        mock_manager = PhaseTransitionManager(
            phase_state=phase_state,
            phase_completion_checker=mock_checker
        )

        # Act: Create controller with custom checkers
        controller = SeasonCycleController(
            database_path=temp_database,
            dynasty_id="test_dynasty",
            season_year=2024,
            start_date=Date(2024, 9, 4),
            verbose_logging=False,
            phase_completion_checker=mock_checker,
            phase_transition_manager=mock_manager
        )

        # Assert: Controller uses the injected checkers
        assert controller.phase_completion_checker is mock_checker
        assert controller.phase_transition_manager is mock_manager

    def test_phase_completion_checker_integration(self, temp_database):
        """Test that PhaseCompletionChecker correctly checks completion"""
        # conftest.py already adds src/ to path
        from src.season.season_cycle_controller import SeasonCycleController
        from src.calendar.date_models import Date

        # Arrange: Create controller
        controller = SeasonCycleController(
            database_path=temp_database,
            dynasty_id="test_dynasty",
            season_year=2024,
            start_date=Date(2024, 9, 4),
            verbose_logging=False
        )

        # Act: Check regular season completion (should be incomplete initially)
        is_complete = controller.phase_completion_checker.is_regular_season_complete()

        # Assert
        assert is_complete is False, "Regular season should not be complete initially"

    def test_phase_transition_manager_integration(self, temp_database):
        """Test that PhaseTransitionManager correctly checks transitions"""
        # conftest.py already adds src/ to path
        from src.season.season_cycle_controller import SeasonCycleController
        from src.calendar.date_models import Date

        # Arrange: Create controller
        controller = SeasonCycleController(
            database_path=temp_database,
            dynasty_id="test_dynasty",
            season_year=2024,
            start_date=Date(2024, 9, 4),
            verbose_logging=False
        )

        # Act: Check for transitions (should be None initially)
        transition = controller.phase_transition_manager.check_transition_needed()

        # Assert
        assert transition is None, "No transition should be needed initially"

    def test_check_phase_transition_uses_manager(self, temp_database):
        """Test that _check_phase_transition uses PhaseTransitionManager"""
        # conftest.py already adds src/ to path
        from src.season.season_cycle_controller import SeasonCycleController
        from src.calendar.date_models import Date

        # Arrange: Create controller
        controller = SeasonCycleController(
            database_path=temp_database,
            dynasty_id="test_dynasty",
            season_year=2024,
            start_date=Date(2024, 9, 4),
            verbose_logging=False
        )

        # Act: Call _check_phase_transition (should use manager internally)
        transition_result = controller._check_phase_transition()

        # Assert: No transition should occur initially
        assert transition_result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
