"""
Unit Tests for ContractTransitionService

Tests the contract transition service logic with mocked dependencies.
All tests use pytest and unittest.mock to isolate service behavior.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sqlite3

# Mock the imports before importing the service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.contract_transition_service import ContractTransitionService


class TestContractTransitionServiceInitialization:
    """Test service initialization and dependency injection."""

    def test_init_creates_service_with_dependencies(self):
        """Service should store all injected dependencies and create logger."""
        # Arrange
        mock_cap_api = Mock()
        dynasty_id = "test_dynasty"

        # Act
        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id=dynasty_id
        )

        # Assert
        assert service.cap_api == mock_cap_api
        assert service.dynasty_id == dynasty_id
        assert service.logger is not None
        assert service.logger.name == "ContractTransitionService"


class TestIncrementAllContracts:
    """Test increment_all_contracts method."""

    def test_increment_all_contracts_success(self):
        """Should query all 32 teams and return contract summary."""
        # Arrange
        mock_cap_api = Mock()

        # Mock contracts for each team (2 contracts per team)
        mock_contracts = [
            {'contract_id': '1', 'end_year': 2026},
            {'contract_id': '2', 'end_year': 2027}
        ]
        mock_cap_api.get_team_contracts.return_value = mock_contracts

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Mock deactivate_expired_contracts to return 0
        service.deactivate_expired_contracts = Mock(return_value=0)

        # Act
        result = service.increment_all_contracts(2025)

        # Assert
        assert result['total_contracts'] == 64  # 2 contracts x 32 teams
        assert result['still_active'] == 64
        assert result['expired_count'] == 0
        assert mock_cap_api.get_team_contracts.call_count == 32
        service.deactivate_expired_contracts.assert_called_once_with(2025)

    def test_increment_all_contracts_with_expirations(self):
        """Should correctly count expired contracts."""
        # Arrange
        mock_cap_api = Mock()

        # Mock contracts with some expiring
        mock_contracts = [
            {'contract_id': '1', 'end_year': 2024},  # Will expire
            {'contract_id': '2', 'end_year': 2026},  # Still active
            {'contract_id': '3', 'end_year': 2027}   # Still active
        ]
        mock_cap_api.get_team_contracts.return_value = mock_contracts

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Mock 5 contracts expired across all teams
        service.deactivate_expired_contracts = Mock(return_value=5)

        # Act
        result = service.increment_all_contracts(2025)

        # Assert
        assert result['total_contracts'] == 96  # 3 contracts x 32 teams
        assert result['still_active'] == 91  # 96 - 5
        assert result['expired_count'] == 5

    def test_increment_all_contracts_queries_previous_season(self):
        """Should query contracts from previous season (season_year - 1)."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_team_contracts.return_value = []

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )
        service.deactivate_expired_contracts = Mock(return_value=0)

        # Act
        service.increment_all_contracts(2025)

        # Assert
        # Should query with season=2024 (2025 - 1)
        for call_args in mock_cap_api.get_team_contracts.call_args_list:
            assert call_args[1]['season'] == 2024
            assert call_args[1]['dynasty_id'] == "test_dynasty"
            assert call_args[1]['active_only'] is True

    def test_increment_all_contracts_handles_database_error(self):
        """Should raise exception when database error occurs."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_team_contracts.side_effect = Exception("DB connection failed")

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act & Assert
        with pytest.raises(Exception, match="DB connection failed"):
            service.increment_all_contracts(2025)

    def test_increment_all_contracts_dynasty_isolation(self):
        """Should filter all operations by dynasty_id."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_team_contracts.return_value = []

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="eagles_dynasty"
        )
        service.deactivate_expired_contracts = Mock(return_value=0)

        # Act
        service.increment_all_contracts(2025)

        # Assert
        for call_args in mock_cap_api.get_team_contracts.call_args_list:
            assert call_args[1]['dynasty_id'] == "eagles_dynasty"


class TestGetExpiringContracts:
    """Test get_expiring_contracts method."""

    def test_get_expiring_contracts_queries_all_teams(self):
        """Should query all 32 teams for expiring contracts."""
        # Arrange
        mock_cap_api = Mock()

        # Return different contracts for different teams
        def mock_expiring(team_id, season, dynasty_id, active_only):
            if team_id == 7:
                return [{'contract_id': '100', 'player_id': 'P1', 'team_id': 7}]
            elif team_id == 15:
                return [{'contract_id': '200', 'player_id': 'P2', 'team_id': 15}]
            return []

        mock_cap_api.get_expiring_contracts.side_effect = mock_expiring

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.get_expiring_contracts(2024)

        # Assert
        assert mock_cap_api.get_expiring_contracts.call_count == 32
        assert len(result) == 2
        assert result[0]['team_id'] == 7
        assert result[1]['team_id'] == 15

    def test_get_expiring_contracts_empty_result(self):
        """Should return empty list when no contracts expiring."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_expiring_contracts.return_value = []

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.get_expiring_contracts(2024)

        # Assert
        assert result == []
        assert mock_cap_api.get_expiring_contracts.call_count == 32

    def test_get_expiring_contracts_correct_parameters(self):
        """Should call API with correct parameters for each team."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_expiring_contracts.return_value = []

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        service.get_expiring_contracts(2024)

        # Assert
        # Verify all 32 teams called with correct parameters
        expected_calls = [
            call(team_id=team_id, season=2024, dynasty_id="test_dynasty", active_only=True)
            for team_id in range(1, 33)
        ]
        mock_cap_api.get_expiring_contracts.assert_has_calls(expected_calls, any_order=True)

    def test_get_expiring_contracts_handles_exception(self):
        """Should raise exception when database error occurs."""
        # Arrange
        mock_cap_api = Mock()
        mock_cap_api.get_expiring_contracts.side_effect = Exception("Query failed")

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Query failed"):
            service.get_expiring_contracts(2024)


class TestDeactivateExpiredContracts:
    """Test deactivate_expired_contracts method."""

    def test_deactivate_expired_contracts_success(self):
        """Should execute SQL UPDATE and return count of deactivated contracts."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('C1', 'P1', 1, 2024, 4, 10000000),
            ('C2', 'P2', 7, 2024, 3, 8000000)
        ]
        mock_cursor.description = [
            ('contract_id',), ('player_id',), ('team_id',),
            ('end_year',), ('contract_years',), ('total_value',)
        ]
        mock_cursor.rowcount = 2

        mock_conn.execute.return_value = mock_cursor
        mock_conn.close = Mock()

        mock_cap_api = Mock()
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )
        service.log_contract_expirations = Mock()

        # Act
        result = service.deactivate_expired_contracts(2025)

        # Assert
        assert result == 2
        assert mock_conn.execute.call_count == 2  # SELECT + UPDATE
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        service.log_contract_expirations.assert_called_once()

    def test_deactivate_expired_contracts_zero_expired(self):
        """Should return 0 when no contracts expired."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 0
        mock_cursor.description = [
            ('contract_id',), ('player_id',), ('team_id',),
            ('end_year',), ('contract_years',), ('total_value',)
        ]

        mock_conn.execute.return_value = mock_cursor
        mock_conn.close = Mock()

        mock_cap_api = Mock()
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.deactivate_expired_contracts(2025)

        # Assert
        assert result == 0

    def test_deactivate_expired_contracts_correct_sql_query(self):
        """Should execute SQL with correct WHERE conditions."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 0
        mock_cursor.description = [
            ('contract_id',), ('player_id',), ('team_id',),
            ('end_year',), ('contract_years',), ('total_value',)
        ]

        mock_conn.execute.return_value = mock_cursor
        mock_conn.close = Mock()

        mock_cap_api = Mock()
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        service.deactivate_expired_contracts(2025)

        # Assert
        # Verify SQL calls
        calls = mock_conn.execute.call_args_list

        # First call (SELECT)
        select_sql, select_params = calls[0][0]
        assert 'end_year < ?' in select_sql
        assert 'dynasty_id = ?' in select_sql
        assert 'is_active = TRUE' in select_sql
        assert select_params == (2025, "test_dynasty")

        # Second call (UPDATE)
        update_sql, update_params = calls[1][0]
        assert 'UPDATE player_contracts' in update_sql
        assert 'SET is_active = FALSE' in update_sql
        assert 'modified_at = CURRENT_TIMESTAMP' in update_sql
        assert 'end_year < ?' in update_sql
        assert update_params == (2025, "test_dynasty")

    def test_deactivate_expired_contracts_closes_connection_on_error(self):
        """Should close connection even when error occurs."""
        # Arrange
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("SQL error")
        mock_conn.close = Mock()

        mock_cap_api = Mock()
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act & Assert
        with pytest.raises(Exception, match="SQL error"):
            service.deactivate_expired_contracts(2025)

        mock_conn.close.assert_called_once()

    def test_deactivate_expired_contracts_logs_before_deactivating(self):
        """Should log contract details before deactivating."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()

        expired_contracts_data = [
            ('C1', 'P1', 1, 2024, 4, 10000000),
            ('C2', 'P2', 7, 2024, 3, 8000000)
        ]
        mock_cursor.fetchall.return_value = expired_contracts_data
        mock_cursor.description = [
            ('contract_id',), ('player_id',), ('team_id',),
            ('end_year',), ('contract_years',), ('total_value',)
        ]
        mock_cursor.rowcount = 2

        mock_conn.execute.return_value = mock_cursor
        mock_conn.close = Mock()

        mock_cap_api = Mock()
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )
        service.log_contract_expirations = Mock()

        # Act
        service.deactivate_expired_contracts(2025)

        # Assert
        service.log_contract_expirations.assert_called_once()
        logged_contracts = service.log_contract_expirations.call_args[0][0]
        assert len(logged_contracts) == 2
        assert logged_contracts[0]['contract_id'] == 'C1'


class TestLogContractExpirations:
    """Test log_contract_expirations method."""

    def test_log_contract_expirations_detailed_output(self):
        """Should log detailed report with all contract information."""
        # Arrange
        mock_cap_api = Mock()
        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        expired_contracts = [
            {
                'player_id': 'P12345',
                'team_id': 7,
                'end_year': 2024,
                'contract_years': 4,
                'total_value': 40000000
            },
            {
                'player_id': 'P67890',
                'team_id': 15,
                'end_year': 2024,
                'contract_years': 3,
                'total_value': 15000000
            }
        ]

        # Mock logger to capture log calls
        with patch.object(service.logger, 'info') as mock_logger_info:
            # Act
            service.log_contract_expirations(expired_contracts)

            # Assert
            assert mock_logger_info.call_count >= 4  # Header + separator + entries + separator + footer

            # Verify log contains expected information
            log_calls = [str(call) for call in mock_logger_info.call_args_list]
            log_output = ' '.join(log_calls)

            assert 'CONTRACT EXPIRATION REPORT - Season 2024' in log_output
            assert 'Player ID P12345' in log_output
            assert 'Team 7' in log_output
            assert '4-year contract' in log_output
            assert '$40,000,000' in log_output
            assert 'Player ID P67890' in log_output
            assert 'Team 15' in log_output
            assert '3-year contract' in log_output
            assert '$15,000,000' in log_output
            assert 'Total: 2 contracts expired' in log_output
            assert '2 new free agents' in log_output

    def test_log_contract_expirations_empty_list(self):
        """Should log appropriate message when no contracts expired."""
        # Arrange
        mock_cap_api = Mock()
        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Mock logger
        with patch.object(service.logger, 'info') as mock_logger_info:
            # Act
            service.log_contract_expirations([])

            # Assert
            mock_logger_info.assert_called_once_with(
                "[CONTRACT_EXPIRATION_REPORT] No contracts expired this season"
            )

    def test_log_contract_expirations_handles_missing_fields(self):
        """Should handle contracts with missing optional fields."""
        # Arrange
        mock_cap_api = Mock()
        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Contract with missing fields
        expired_contracts = [
            {
                'end_year': 2024,
                # Missing player_id, team_id, contract_years, total_value
            }
        ]

        # Mock logger
        with patch.object(service.logger, 'info') as mock_logger_info:
            # Act
            service.log_contract_expirations(expired_contracts)

            # Assert
            log_calls = [str(call) for call in mock_logger_info.call_args_list]
            log_output = ' '.join(log_calls)

            # Should use defaults for missing fields
            assert 'UNKNOWN' in log_output
            assert 'Total: 1 contracts expired' in log_output

    def test_log_contract_expirations_formats_value_with_commas(self):
        """Should format contract values with thousand separators."""
        # Arrange
        mock_cap_api = Mock()
        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        expired_contracts = [
            {
                'player_id': 'P1',
                'team_id': 1,
                'end_year': 2024,
                'contract_years': 5,
                'total_value': 123456789  # Large number
            }
        ]

        # Mock logger
        with patch.object(service.logger, 'info') as mock_logger_info:
            # Act
            service.log_contract_expirations(expired_contracts)

            # Assert
            log_calls = [str(call) for call in mock_logger_info.call_args_list]
            log_output = ' '.join(log_calls)

            # Should have commas in value
            assert '$123,456,789' in log_output


class TestContractTransitionServiceIntegration:
    """Integration-style tests with minimal mocking."""

    def test_service_can_be_created_with_dependency_injection(self):
        """Should create service with dependency injection pattern."""
        # Arrange & Act
        service = ContractTransitionService(
            cap_api=Mock(),
            dynasty_id="integration_test"
        )

        # Assert
        assert service is not None
        assert service.dynasty_id == "integration_test"
        assert service.cap_api is not None
        assert service.logger is not None

    def test_full_contract_transition_workflow(self):
        """Should execute complete contract transition workflow."""
        # Arrange
        mock_cap_api = Mock()

        # Setup mock data
        mock_contracts = [
            {'contract_id': '1', 'end_year': 2024},  # Expires
            {'contract_id': '2', 'end_year': 2026},  # Active
        ]
        mock_cap_api.get_team_contracts.return_value = mock_contracts

        # Mock database connection for deactivate
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('C1', 'P1', 1, 2024, 4, 10000000)
        ]
        mock_cursor.description = [
            ('contract_id',), ('player_id',), ('team_id',),
            ('end_year',), ('contract_years',), ('total_value',)
        ]
        mock_cursor.rowcount = 1
        mock_conn.execute.return_value = mock_cursor
        mock_cap_api._get_connection.return_value = mock_conn

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.increment_all_contracts(2025)

        # Assert
        assert result['total_contracts'] == 64  # 2 contracts x 32 teams
        assert result['expired_count'] == 1
        assert result['still_active'] == 63

    def test_expiring_contracts_query_workflow(self):
        """Should query and return all expiring contracts."""
        # Arrange
        mock_cap_api = Mock()

        # Different teams have different expiring contracts
        def mock_expiring(team_id, season, dynasty_id, active_only):
            if team_id in [7, 15, 22]:
                return [{'contract_id': f'C{team_id}', 'team_id': team_id}]
            return []

        mock_cap_api.get_expiring_contracts.side_effect = mock_expiring

        service = ContractTransitionService(
            cap_api=mock_cap_api,
            dynasty_id="test_dynasty"
        )

        # Act
        result = service.get_expiring_contracts(2024)

        # Assert
        assert len(result) == 3
        assert result[0]['team_id'] == 7
        assert result[1]['team_id'] == 15
        assert result[2]['team_id'] == 22
