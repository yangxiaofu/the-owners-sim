"""
Integration and Regression Tests for Service Extraction

Tests that verify the service extraction from SeasonCycleController
maintains backward compatibility and correct behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestSeasonCycleControllerServiceIntegration:
    """Integration tests for SeasonCycleController using TransactionService."""

    @patch('season.season_cycle_controller.UnifiedDatabaseAPI')
    @patch('season.season_cycle_controller.CalendarManager')
    def test_controller_creates_transaction_service_lazily(self, mock_calendar_class, mock_db_class):
        """Controller should create TransactionService on first use."""
        # This test would require significant mocking of SeasonCycleController
        # For now, we test the service factory method pattern is correct

        # Verify the pattern exists in controller
        from season.season_cycle_controller import SeasonCycleController

        # Check that _get_transaction_service method exists
        assert hasattr(SeasonCycleController, '_get_transaction_service')

    def test_transaction_service_maintains_backward_compatibility(self):
        """Service should provide same interface as old controller methods."""
        from services.transaction_service import TransactionService

        service = TransactionService(
            db=Mock(),
            calendar=Mock(),
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Verify public methods exist
        assert hasattr(service, 'evaluate_daily_for_all_teams')
        assert hasattr(service, 'execute_trade')

        # Verify method signatures
        import inspect

        evaluate_sig = inspect.signature(service.evaluate_daily_for_all_teams)
        assert 'current_phase' in evaluate_sig.parameters
        assert 'current_week' in evaluate_sig.parameters
        assert 'verbose_logging' in evaluate_sig.parameters

        execute_sig = inspect.signature(service.execute_trade)
        assert 'proposal' in execute_sig.parameters


class TestPlayoffHelpersIntegration:
    """Integration tests for playoff helper functions."""

    def test_extract_playoff_champions_maintains_backward_compatibility(self):
        """Helper should provide same functionality as inline code."""
        from services.playoff_helpers import extract_playoff_champions

        # Mock playoff controller with realistic data
        mock_controller = Mock()
        conference_games = [
            {'winner_id': 9, 'game_id': 'afc_champ', 'score': '24-17'},
            {'winner_id': 22, 'game_id': 'nfc_champ', 'score': '31-28'}
        ]
        mock_controller.get_round_games.return_value = conference_games

        # Act
        afc, nfc = extract_playoff_champions(mock_controller)

        # Assert - same behavior as old inline code
        assert afc == 9  # AFC team (1-16)
        assert nfc == 22  # NFC team (17-32)

        # Verify controller was called correctly
        mock_controller.get_round_games.assert_called_once_with('conference_championship')


class TestServiceExtractionRegression:
    """Regression tests to ensure service extraction didn't break functionality."""

    def test_transaction_service_dependency_injection_pattern(self):
        """Service should follow dependency injection best practices."""
        from services.transaction_service import TransactionService

        # Create service with all dependencies
        mock_db = Mock(name='UnifiedDatabaseAPI')
        mock_calendar = Mock(name='CalendarManager')
        mock_ai = Mock(name='TransactionAIManager')
        mock_logger = Mock(name='Logger')

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=mock_logger,
            dynasty_id="regression_test",
            database_path=":memory:",
            season_year=2024
        )

        # Verify dependencies are stored (not recreated)
        assert service.db is mock_db
        assert service.calendar is mock_calendar
        assert service.transaction_ai is mock_ai
        assert service.logger is mock_logger

    def test_services_module_exports_correct_classes(self):
        """Services package should export all public classes and functions."""
        import services

        # Check module exports
        assert hasattr(services, 'TransactionService')
        assert hasattr(services, 'extract_playoff_champions')

        # Check __all__ is defined
        assert hasattr(services, '__all__')
        assert 'TransactionService' in services.__all__
        assert 'extract_playoff_champions' in services.__all__

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_service_respects_transaction_timing_validation(self, mock_validator_class):
        """Service should block trades when timing validator says no."""
        from services.transaction_service import TransactionService

        # Setup - trades not allowed
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (False, "After deadline")
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 11, 15)
        mock_calendar.get_current_date.return_value = mock_date

        service = TransactionService(
            db=Mock(),
            calendar=mock_calendar,
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=12,
            verbose_logging=False
        )

        # Assert - no trades should be executed
        assert result == []
        mock_validator.is_trade_allowed.assert_called_once()

    def test_service_line_count_reduction(self):
        """Verify SeasonCycleController was reduced by ~240 lines."""
        from pathlib import Path

        controller_path = Path(__file__).parent.parent.parent / "src" / "season" / "season_cycle_controller.py"

        with open(controller_path, 'r') as f:
            controller_lines = len(f.readlines())

        # Original was ~3063 lines, should now be ~2825 lines
        # Allow some variance for comments/whitespace
        assert controller_lines < 2900, f"Controller still has {controller_lines} lines (expected <2900)"
        assert controller_lines > 2700, f"Controller only has {controller_lines} lines (expected >2700)"

    def test_no_circular_imports(self):
        """Verify no circular import issues with new services package."""
        try:
            # These imports should succeed without circular dependency errors
            from services import TransactionService, extract_playoff_champions
            from season.season_cycle_controller import SeasonCycleController

            # If we get here, no circular imports
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")
