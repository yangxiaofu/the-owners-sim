"""
Unit Tests for TransactionService

Tests the extracted transaction service logic with mocked dependencies.
All tests use pytest and unittest.mock to isolate service behavior.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date

# Mock the imports before importing the service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.transaction_service import TransactionService
from src.season.season_constants import PhaseNames


class TestTransactionServiceInitialization:
    """Test service initialization and dependency injection."""

    def test_init_stores_all_dependencies(self):
        """Service should store all injected dependencies."""
        # Arrange
        mock_db = Mock()
        mock_calendar = Mock()
        mock_ai = Mock()
        mock_logger = Mock()

        # Act
        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=mock_logger,
            dynasty_id="test_dynasty",
            database_path="test.db",
            season_year=2024
        )

        # Assert
        assert service.db == mock_db
        assert service.calendar == mock_calendar
        assert service.transaction_ai == mock_ai
        assert service.logger == mock_logger
        assert service.dynasty_id == "test_dynasty"
        assert service.database_path == "test.db"
        assert service.season_year == 2024


class TestGetTeamRecord:
    """Test _get_team_record helper method."""

    def test_get_team_record_success(self):
        """Should return team record when standing exists."""
        # Arrange
        mock_db = Mock()
        mock_standing = Mock(wins=10, losses=5, ties=1)
        mock_db.standings_get_team.return_value = mock_standing

        service = TransactionService(
            db=mock_db,
            calendar=Mock(),
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service._get_team_record(team_id=7)

        # Assert
        assert result == {'wins': 10, 'losses': 5, 'ties': 1}
        mock_db.standings_get_team.assert_called_once_with(
            team_id=7,
            season=2024,
            season_type=PhaseNames.DB_REGULAR_SEASON
        )

    def test_get_team_record_no_standing_returns_zeros(self):
        """Should return 0-0-0 when no standing exists."""
        # Arrange
        mock_db = Mock()
        mock_db.standings_get_team.return_value = None

        service = TransactionService(
            db=mock_db,
            calendar=Mock(),
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service._get_team_record(team_id=15)

        # Assert
        assert result == {'wins': 0, 'losses': 0, 'ties': 0}

    def test_get_team_record_handles_database_error(self):
        """Should return 0-0-0 and log error on database failure."""
        # Arrange
        mock_db = Mock()
        mock_db.standings_get_team.side_effect = Exception("DB connection failed")
        mock_logger = Mock()

        service = TransactionService(
            db=mock_db,
            calendar=Mock(),
            transaction_ai=Mock(),
            logger=mock_logger,
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service._get_team_record(team_id=22)

        # Assert
        assert result == {'wins': 0, 'losses': 0, 'ties': 0}
        mock_logger.error.assert_called_once()


class TestExecuteTrade:
    """Test execute_trade method."""

    @patch('services.transaction_service.PlayerForPlayerTradeEvent')
    def test_execute_trade_success(self, mock_trade_event_class):
        """Should execute trade and return success result."""
        # Arrange
        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.__str__ = Mock(return_value="2024-11-03")
        mock_calendar.get_current_date.return_value = mock_date

        mock_event = Mock()
        mock_result = Mock(
            success=True,
            data={'team1_net_cap_change': -5000000, 'team2_net_cap_change': 5000000}
        )
        mock_event.simulate.return_value = mock_result
        mock_trade_event_class.return_value = mock_event

        service = TransactionService(
            db=Mock(),
            calendar=mock_calendar,
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test_dynasty",
            database_path="test.db",
            season_year=2024
        )

        proposal = {
            'team1_id': 7,
            'team2_id': 9,
            'team1_players': [101, 102],
            'team2_players': [201],
            'fair_value': 1.05
        }

        # Act
        result = service.execute_trade(proposal)

        # Assert
        assert result['success'] is True
        assert result['error_message'] is None
        assert result['trade_details']['team1_id'] == 7
        assert result['trade_details']['team2_id'] == 9
        assert result['trade_details']['team1_net_cap_change'] == -5000000
        mock_event.simulate.assert_called_once()

    @patch('services.transaction_service.PlayerForPlayerTradeEvent')
    def test_execute_trade_failure(self, mock_trade_event_class):
        """Should return failure result when trade event fails."""
        # Arrange
        mock_event = Mock()
        mock_result = Mock(success=False, error_message="Cap space violation")
        mock_event.simulate.return_value = mock_result
        mock_trade_event_class.return_value = mock_event

        mock_calendar = Mock()
        mock_calendar.get_current_date.return_value = Mock()

        service = TransactionService(
            db=Mock(),
            calendar=mock_calendar,
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        proposal = {'team1_id': 7, 'team2_id': 9, 'team1_players': [], 'team2_players': []}

        # Act
        result = service.execute_trade(proposal)

        # Assert
        assert result['success'] is False
        assert result['error_message'] == "Cap space violation"
        assert result['trade_details'] is None

    def test_execute_trade_handles_exception(self):
        """Should catch exceptions and return failure result."""
        # Arrange
        mock_calendar = Mock()
        mock_calendar.get_current_date.side_effect = Exception("Calendar error")
        mock_logger = Mock()

        service = TransactionService(
            db=Mock(),
            calendar=mock_calendar,
            transaction_ai=Mock(),
            logger=mock_logger,
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.execute_trade({'team1_id': 1, 'team2_id': 2})

        # Assert
        assert result['success'] is False
        assert "Calendar error" in result['error_message']
        mock_logger.error.assert_called_once()


class TestEvaluateDailyForAllTeams:
    """Test evaluate_daily_for_all_teams method."""

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_evaluate_blocked_by_timing_validator(self, mock_validator_class):
        """Should return empty list when trades not allowed."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (False, "After trade deadline")
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

        # Assert
        assert result == []
        mock_validator.is_trade_allowed.assert_called_once()

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_evaluate_processes_all_32_teams(self, mock_validator_class):
        """Should evaluate all 32 teams when trades allowed."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (True, None)
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 9, 15)
        mock_date.__str__ = Mock(return_value="2024-09-15")
        mock_calendar.get_current_date.return_value = mock_date

        mock_ai = Mock()
        mock_ai.evaluate_daily_transactions.return_value = ([], None)

        mock_db = Mock()
        mock_db.standings_get_team.return_value = Mock(wins=5, losses=3, ties=0)

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=3,
            verbose_logging=False
        )

        # Assert
        assert mock_ai.evaluate_daily_transactions.call_count == 32
        assert result == []

    @patch('services.transaction_service.TransactionTimingValidator')
    @patch('services.transaction_service.PlayerForPlayerTradeEvent')
    def test_evaluate_executes_approved_proposals(self, mock_trade_event, mock_validator_class):
        """Should execute approved trade proposals."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (True, None)
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 9, 15)
        mock_date.__str__ = Mock(return_value="2024-09-15")
        mock_calendar.get_current_date.return_value = mock_date

        # Mock proposal from AI
        mock_asset = Mock(asset_type="PLAYER", player_id=101)
        mock_proposal = Mock(
            team1_id=7,
            team2_id=9,
            team1_assets=[mock_asset],
            team2_assets=[],
            value_ratio=1.0
        )

        mock_ai = Mock()
        # Return proposal only for team 7
        def side_effect(team_id, **kwargs):
            if team_id == 7:
                return ([mock_proposal], None)
            return ([], None)
        mock_ai.evaluate_daily_transactions.side_effect = side_effect

        # Mock successful trade execution
        mock_event = Mock()
        mock_result = Mock(success=True, data={'team1_net_cap_change': 0, 'team2_net_cap_change': 0})
        mock_event.simulate.return_value = mock_result
        mock_trade_event.return_value = mock_event

        mock_db = Mock()
        mock_db.standings_get_team.return_value = Mock(wins=5, losses=3, ties=0)

        # Import AssetType for mocking
        from transactions.asset_models import AssetType
        mock_asset.asset_type = AssetType.PLAYER

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=3,
            verbose_logging=False
        )

        # Assert
        assert len(result) == 1
        assert result[0]['team1_id'] == 7
        assert result[0]['team2_id'] == 9

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_evaluate_skips_duplicate_player_trades(self, mock_validator_class):
        """Should skip proposals with players already traded."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (True, None)
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 9, 15)
        mock_date.__str__ = Mock(return_value="2024-09-15")
        mock_calendar.get_current_date.return_value = mock_date

        from transactions.asset_models import AssetType

        # Two proposals with overlapping player
        mock_asset1 = Mock(asset_type=AssetType.PLAYER, player_id=101)
        mock_asset2 = Mock(asset_type=AssetType.PLAYER, player_id=101)  # Duplicate!

        mock_proposal1 = Mock(
            team1_id=7, team2_id=9,
            team1_assets=[mock_asset1], team2_assets=[],
            value_ratio=1.0
        )
        mock_proposal2 = Mock(
            team1_id=7, team2_id=15,
            team1_assets=[mock_asset2], team2_assets=[],
            value_ratio=1.0
        )

        mock_ai = Mock()
        def side_effect(team_id, **kwargs):
            if team_id == 7:
                return ([mock_proposal1, mock_proposal2], None)
            return ([], None)
        mock_ai.evaluate_daily_transactions.side_effect = side_effect

        mock_db = Mock()
        mock_db.standings_get_team.return_value = Mock(wins=5, losses=3, ties=0)

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=Mock(),
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Mock first trade succeeds
        service.execute_trade = Mock(
            side_effect=[
                {'success': True, 'trade_details': {'team1_id': 7, 'team2_id': 9}},
                {'success': False}  # Should not be called
            ]
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=3,
            verbose_logging=False
        )

        # Assert
        # Only first trade should execute, second should be skipped
        assert service.execute_trade.call_count == 1

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_evaluate_handles_team_evaluation_errors(self, mock_validator_class):
        """Should continue evaluating other teams if one team fails."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (True, None)
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 9, 15)
        mock_date.__str__ = Mock(return_value="2024-09-15")
        mock_calendar.get_current_date.return_value = mock_date

        mock_ai = Mock()
        # Team 15 throws error, others succeed
        def side_effect(team_id, **kwargs):
            if team_id == 15:
                raise Exception("Team evaluation failed")
            return ([], None)
        mock_ai.evaluate_daily_transactions.side_effect = side_effect

        mock_db = Mock()
        mock_db.standings_get_team.return_value = Mock(wins=5, losses=3, ties=0)

        mock_logger = Mock()

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=mock_logger,
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=3,
            verbose_logging=False
        )

        # Assert
        assert mock_ai.evaluate_daily_transactions.call_count == 32
        mock_logger.error.assert_called()  # Error logged for team 15

    @patch('services.transaction_service.TransactionTimingValidator')
    def test_evaluate_logs_summary_statistics(self, mock_validator_class):
        """Should log summary of teams evaluated and trades executed."""
        # Arrange
        mock_validator = Mock()
        mock_validator.is_trade_allowed.return_value = (True, None)
        mock_validator_class.return_value = mock_validator

        mock_calendar = Mock()
        mock_date = Mock()
        mock_date.to_python_date.return_value = date(2024, 9, 15)
        mock_date.__str__ = Mock(return_value="2024-09-15")
        mock_calendar.get_current_date.return_value = mock_date

        mock_ai = Mock()
        mock_ai.evaluate_daily_transactions.return_value = ([], None)

        mock_db = Mock()
        mock_db.standings_get_team.return_value = Mock(wins=5, losses=3, ties=0)

        mock_logger = Mock()

        service = TransactionService(
            db=mock_db,
            calendar=mock_calendar,
            transaction_ai=mock_ai,
            logger=mock_logger,
            dynasty_id="test",
            database_path="test.db",
            season_year=2024
        )

        # Act
        result = service.evaluate_daily_for_all_teams(
            current_phase="regular_season",
            current_week=3,
            verbose_logging=False
        )

        # Assert
        # Check that summary was logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("SUMMARY" in call for call in log_calls)
        assert any("Teams Evaluated: 32/32" in call for call in log_calls)


class TestTransactionServiceIntegration:
    """Integration-style tests with minimal mocking."""

    def test_service_can_be_created_with_real_types(self):
        """Should create service with dependency injection pattern."""
        # This test verifies the service can be instantiated
        # In real usage, controller would inject dependencies
        service = TransactionService(
            db=Mock(),
            calendar=Mock(),
            transaction_ai=Mock(),
            logger=Mock(),
            dynasty_id="integration_test",
            database_path=":memory:",
            season_year=2024
        )

        assert service is not None
        assert service.dynasty_id == "integration_test"
