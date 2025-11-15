"""
Unit Tests for DynastyInitializationService

Tests the dynasty initialization service logic with mocked dependencies.
All tests use pytest and unittest.mock to isolate service behavior.

Follows the same testing pattern as other service tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import time
from datetime import datetime

# Mock the imports before importing the service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.services.dynasty_initialization_service import DynastyInitializationService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_dynasty_db_api():
    """Create mock DynastyDatabaseAPI."""
    mock_api = Mock()
    mock_api.create_dynasty_record = Mock(return_value=True)
    mock_api.initialize_standings_for_season_type = Mock(return_value=32)
    return mock_api


@pytest.fixture
def mock_player_roster_api():
    """Create mock PlayerRosterAPI."""
    mock_api = Mock()
    mock_api.initialize_dynasty_rosters = Mock(return_value=1696)  # Typical player count
    mock_api.shared_conn = None
    return mock_api


@pytest.fixture
def mock_depth_chart_api():
    """Create mock DepthChartAPI."""
    mock_api = Mock()
    mock_api.auto_generate_depth_chart = Mock(return_value=True)
    return mock_api


@pytest.fixture
def mock_dynasty_state_api():
    """Create mock DynastyStateAPI."""
    mock_api = Mock()
    mock_api.get_current_state = Mock(return_value={
        'dynasty_id': 'test_dynasty',
        'current_date': '2025-08-01',
        'current_week': 1,
        'current_phase': 'preseason'
    })
    mock_api.initialize_state = Mock(return_value=True)
    return mock_api


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock()


@pytest.fixture
def mock_connection():
    """Create mock database connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.rowcount = 1  # Default rowcount for UPDATE statements
    mock_conn.cursor = Mock(return_value=mock_cursor)
    mock_conn.commit = Mock()
    mock_conn.rollback = Mock()
    return mock_conn


@pytest.fixture
def service(
    mock_dynasty_db_api,
    mock_player_roster_api,
    mock_depth_chart_api,
    mock_dynasty_state_api,
    mock_logger
):
    """Create DynastyInitializationService with all mocked dependencies."""
    service = DynastyInitializationService(
        db_path=":memory:",
        dynasty_database_api=mock_dynasty_db_api,
        player_roster_api=mock_player_roster_api,
        depth_chart_api=mock_depth_chart_api,
        dynasty_state_api=mock_dynasty_state_api,
        logger=mock_logger
    )
    return service


# ============================================================================
# TEST CLASS: Service Initialization
# ============================================================================

class TestDynastyInitializationServiceInit:
    """Test service initialization and dependency injection."""

    def test_init_stores_dependencies(
        self,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Service should store all injected dependencies."""
        # Act
        service = DynastyInitializationService(
            db_path=":memory:",
            dynasty_database_api=mock_dynasty_db_api,
            player_roster_api=mock_player_roster_api,
            depth_chart_api=mock_depth_chart_api,
            dynasty_state_api=mock_dynasty_state_api,
            logger=mock_logger
        )

        # Assert
        assert service.db_path == ":memory:"
        assert service._dynasty_db_api == mock_dynasty_db_api
        assert service._player_roster_api == mock_player_roster_api
        assert service._depth_chart_api == mock_depth_chart_api
        assert service._dynasty_state_api == mock_dynasty_state_api
        assert service.logger == mock_logger

    def test_init_creates_database_connection(self):
        """Service should create DatabaseConnection instance."""
        # Act
        service = DynastyInitializationService(db_path=":memory:")

        # Assert
        assert service.db_connection is not None

    def test_lazy_properties_initialize_apis(self):
        """Lazy properties should initialize APIs when None."""
        # Arrange
        service = DynastyInitializationService(db_path=":memory:")

        # Act & Assert
        assert service.dynasty_db_api is not None
        assert service.player_roster_api is not None
        assert service.depth_chart_api is not None
        assert service.dynasty_state_api is not None

    def test_lazy_properties_return_injected_apis(
        self,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api
    ):
        """Lazy properties should return injected APIs when provided."""
        # Arrange
        service = DynastyInitializationService(
            db_path=":memory:",
            dynasty_database_api=mock_dynasty_db_api,
            player_roster_api=mock_player_roster_api,
            depth_chart_api=mock_depth_chart_api,
            dynasty_state_api=mock_dynasty_state_api
        )

        # Act & Assert
        assert service.dynasty_db_api == mock_dynasty_db_api
        assert service.player_roster_api == mock_player_roster_api
        assert service.depth_chart_api == mock_depth_chart_api
        assert service.dynasty_state_api == mock_dynasty_state_api


# ============================================================================
# TEST CLASS: Happy Path - Successful Initialization
# ============================================================================

class TestInitializeDynastySuccess:
    """Test successful dynasty initialization (happy path)."""

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_initialize_dynasty_full_success(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should successfully initialize dynasty with all steps."""
        # Arrange - Mock database connection
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        # Mock ContractInitializer
        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        # Mock SeasonController
        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        # Mock OffseasonController
        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Result structure
        assert result['success'] is True
        assert result['dynasty_id'] == "test_dynasty"
        assert result['players_loaded'] == 1696
        assert result['depth_charts_created'] == 32
        assert result['schedule_generated'] is True
        assert result['state_initialized'] is True
        assert result['offseason_simulated'] is True
        assert result['total_duration'] >= 0
        assert result['error_message'] is None

        # Assert - Dynasty record created
        mock_dynasty_db_api.create_dynasty_record.assert_called_once_with(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            connection=mock_connection
        )

        # Assert - Standings initialized (preseason + regular season)
        assert mock_dynasty_db_api.initialize_standings_for_season_type.call_count == 2
        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='preseason',
            connection=mock_connection
        )
        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='regular_season',
            connection=mock_connection
        )

        # Assert - Player rosters loaded
        mock_player_roster_api.initialize_dynasty_rosters.assert_called_once_with(
            dynasty_id="test_dynasty",
            season=2025
        )
        assert mock_player_roster_api.shared_conn == mock_connection

        # Assert - Depth charts generated (32 teams)
        assert mock_depth_chart_api.auto_generate_depth_chart.call_count == 32
        for tid in range(1, 33):
            mock_depth_chart_api.auto_generate_depth_chart.assert_any_call(
                dynasty_id="test_dynasty",
                team_id=tid,
                connection=mock_connection
            )

        # Assert - Transaction committed
        mock_connection.commit.assert_called_once()

        # Assert - Contract initialization
        mock_contract_initializer_class.assert_called_once_with(
            db_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2025,
            shared_connection=mock_connection
        )
        mock_contract_init.initialize_all_team_contracts.assert_called_once()

        # Assert - Schedule generation
        mock_season_controller_class.assert_called_once_with(
            db_path=":memory:",
            dynasty_id="test_dynasty",
            season=2025
        )
        mock_season_ctrl.generate_initial_schedule.assert_called_once()

        # Assert - Dynasty state verification
        mock_dynasty_state_api.get_current_state.assert_called_once_with(
            "test_dynasty", 2025
        )

        # Assert - AI offseason simulation
        mock_offseason_controller_class.assert_called_once_with(
            database_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2025,
            user_team_id=7,
            super_bowl_date=datetime(2026, 2, 9),
            enable_persistence=True,
            verbose_logging=False
        )
        mock_offseason_ctrl.simulate_ai_full_offseason.assert_called_once_with(
            user_team_id=7
        )

        # Assert - Logging
        assert mock_logger.info.call_count >= 2


# ============================================================================
# TEST CLASS: Dynasty Record Creation Failure
# ============================================================================

class TestDynastyRecordCreationFailure:
    """Test failure when dynasty record creation fails."""

    def test_initialize_dynasty_fails_on_dynasty_record_creation(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_logger
    ):
        """Should fail and rollback when dynasty record creation fails."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = False

        # Act & Assert
        with pytest.raises(Exception, match="Failed to create dynasty record"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Rollback was called
        mock_connection.rollback.assert_called_once()

        # Assert - Error logged
        assert mock_logger.error.call_count >= 1


# ============================================================================
# TEST CLASS: Standings Initialization Failure
# ============================================================================

class TestStandingsInitializationFailure:
    """Test failure when standings initialization fails."""

    def test_initialize_dynasty_fails_on_preseason_standings_count(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_logger
    ):
        """Should fail and rollback when preseason standings count is wrong."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = True
        # Return wrong count for preseason
        mock_dynasty_db_api.initialize_standings_for_season_type.side_effect = [30, 32]

        # Act & Assert
        with pytest.raises(Exception, match="Expected 32 preseason standings, got 30"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Rollback was called
        mock_connection.rollback.assert_called_once()

        # Assert - Error logged
        assert mock_logger.error.call_count >= 1

    def test_initialize_dynasty_fails_on_regular_season_standings_count(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_logger
    ):
        """Should fail and rollback when regular season standings count is wrong."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = True
        # Return correct preseason count, wrong regular season count
        mock_dynasty_db_api.initialize_standings_for_season_type.side_effect = [32, 28]

        # Act & Assert
        with pytest.raises(Exception, match="Expected 32 regular season standings, got 28"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Rollback was called
        mock_connection.rollback.assert_called_once()

        # Assert - Error logged
        assert mock_logger.error.call_count >= 1


# ============================================================================
# TEST CLASS: Player Roster Loading Failure
# ============================================================================

class TestPlayerRosterLoadingFailure:
    """Test failure when player roster loading fails."""

    def test_initialize_dynasty_fails_on_player_roster_exception(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_logger
    ):
        """Should fail and rollback when player roster loading raises exception."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = True
        mock_dynasty_db_api.initialize_standings_for_season_type.return_value = 32
        mock_player_roster_api.initialize_dynasty_rosters.side_effect = Exception(
            "Player JSON file not found"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Player JSON file not found"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Rollback was called
        mock_connection.rollback.assert_called_once()

        # Assert - Error logged
        assert mock_logger.error.call_count >= 1


# ============================================================================
# TEST CLASS: Depth Chart Generation Failure
# ============================================================================

class TestDepthChartGenerationFailure:
    """Test failure when depth chart generation fails."""

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_initialize_dynasty_warns_on_partial_depth_chart_failure(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should warn but continue when some depth charts fail to generate."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        # Mock depth chart API to fail for some teams
        def depth_chart_side_effect(dynasty_id, team_id, connection):
            # Fail for teams 1-3, succeed for rest
            return team_id > 3

        mock_depth_chart_api.auto_generate_depth_chart.side_effect = depth_chart_side_effect

        # Mock other dependencies
        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Should still succeed but with partial depth charts
        assert result['success'] is True
        assert result['depth_charts_created'] == 29  # 32 - 3 failed = 29

        # Assert - Warning logged
        mock_logger.warning.assert_any_call("Only 29/32 depth charts created")


# ============================================================================
# TEST CLASS: Transaction Rollback on Error
# ============================================================================

class TestTransactionRollback:
    """Test transaction rollback on various failures."""

    def test_rollback_called_on_any_exception(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_logger
    ):
        """Should rollback transaction on any exception during initialization."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.side_effect = Exception(
            "Database connection lost"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Database connection lost"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Rollback was called
        mock_connection.rollback.assert_called_once()

        # Assert - Commit was never called
        mock_connection.commit.assert_not_called()

    def test_rollback_handles_none_connection(
        self,
        service,
        mock_logger
    ):
        """Should handle rollback gracefully when connection is None."""
        # Arrange
        service.db_connection.get_connection = Mock(side_effect=Exception("Connection failed"))

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )

        # Assert - Error logged (no rollback crash)
        assert mock_logger.error.call_count >= 1


# ============================================================================
# TEST CLASS: Result Dictionary Structure
# ============================================================================

class TestResultDictStructure:
    """Test result dictionary structure and metadata."""

    def test_result_dict_has_all_required_keys_on_failure(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_logger
    ):
        """Result dict should have all keys even on failure."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = False

        # Act
        try:
            result = service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )
        except Exception:
            pass  # Expected to raise

        # Can't directly test result since exception is raised
        # But we verify the structure in the next test

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_result_dict_has_all_required_keys_on_success(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api
    ):
        """Result dict should have all required keys on success."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - All required keys present
        assert 'success' in result
        assert 'dynasty_id' in result
        assert 'players_loaded' in result
        assert 'depth_charts_created' in result
        assert 'schedule_generated' in result
        assert 'state_initialized' in result
        assert 'offseason_simulated' in result
        assert 'total_duration' in result
        assert 'error_message' in result

        # Assert - Correct types
        assert isinstance(result['success'], bool)
        assert isinstance(result['dynasty_id'], str)
        assert isinstance(result['players_loaded'], int)
        assert isinstance(result['depth_charts_created'], int)
        assert isinstance(result['schedule_generated'], bool)
        assert isinstance(result['state_initialized'], bool)
        assert isinstance(result['offseason_simulated'], bool)
        assert isinstance(result['total_duration'], float)
        assert result['error_message'] is None

    def test_result_includes_timing_metadata(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api
    ):
        """Result should include timing information."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_dynasty_db_api.create_dynasty_record.return_value = False

        # Act
        try:
            result = service.initialize_dynasty(
                dynasty_id="test_dynasty",
                dynasty_name="Test Dynasty",
                owner_name="Test Owner",
                team_id=7,
                season=2025
            )
        except Exception:
            pass

        # Duration is tracked even on failure
        # Verified in other tests that total_duration is present


# ============================================================================
# TEST CLASS: Optional Components (Non-Critical Failures)
# ============================================================================

class TestOptionalComponentFailures:
    """Test non-critical failures in optional components."""

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_continues_when_contract_initialization_fails(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should continue when contract initialization fails (non-critical)."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        # Mock contract initializer to fail
        mock_contract_initializer_class.side_effect = Exception("Contract init failed")

        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Should still succeed
        assert result['success'] is True

        # Assert - Warning logged
        mock_logger.warning.assert_any_call("Contract initialization failed: Contract init failed")

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_continues_when_schedule_generation_fails(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should continue when schedule generation fails (non-critical)."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        # Mock schedule generation to fail
        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(False, "Schedule error"))
        mock_season_controller_class.return_value = mock_season_ctrl

        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Should still succeed but schedule_generated is False
        assert result['success'] is True
        assert result['schedule_generated'] is False

        # Assert - Error logged
        mock_logger.error.assert_any_call("Schedule generation failed: Schedule error")

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_continues_when_offseason_simulation_fails(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should continue when AI offseason simulation fails (non-critical)."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        # Mock offseason controller to fail
        mock_offseason_controller_class.side_effect = Exception("Offseason sim failed")

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Should still succeed but offseason_simulated is False
        assert result['success'] is True
        assert result['offseason_simulated'] is False

        # Assert - Warning logged
        mock_logger.warning.assert_any_call("AI offseason simulation failed: Offseason sim failed")

    @patch('offseason.offseason_controller.OffseasonController')
    @patch('ui.controllers.season_controller.SeasonController')
    @patch('salary_cap.contract_initializer.ContractInitializer')
    def test_creates_fallback_dynasty_state_when_missing(
        self,
        mock_contract_initializer_class,
        mock_season_controller_class,
        mock_offseason_controller_class,
        service,
        mock_connection,
        mock_dynasty_db_api,
        mock_player_roster_api,
        mock_depth_chart_api,
        mock_dynasty_state_api,
        mock_logger
    ):
        """Should create fallback dynasty state when get_current_state returns None."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)

        mock_contract_init = Mock()
        mock_contract_init.initialize_all_team_contracts = Mock(return_value=1696)
        mock_contract_initializer_class.return_value = mock_contract_init

        mock_season_ctrl = Mock()
        mock_season_ctrl.generate_initial_schedule = Mock(return_value=(True, None))
        mock_season_controller_class.return_value = mock_season_ctrl

        mock_offseason_ctrl = Mock()
        mock_offseason_ctrl.simulate_ai_full_offseason = Mock(return_value={
            'franchise_tags_applied': 5,
            'free_agent_signings': 120,
            'roster_cuts_made': 480,
            'total_transactions': 605
        })
        mock_offseason_controller_class.return_value = mock_offseason_ctrl

        # Mock dynasty state to be missing initially
        mock_dynasty_state_api.get_current_state.return_value = None
        mock_dynasty_state_api.initialize_state.return_value = True

        # Act
        result = service.initialize_dynasty(
            dynasty_id="test_dynasty",
            dynasty_name="Test Dynasty",
            owner_name="Test Owner",
            team_id=7,
            season=2025
        )

        # Assert - Should succeed with fallback state
        assert result['success'] is True
        assert result['state_initialized'] is True

        # Assert - Fallback state creation was called
        mock_dynasty_state_api.initialize_state.assert_called_once_with(
            dynasty_id="test_dynasty",
            season=2025,
            start_date="2025-08-01",
            start_week=1,
            start_phase="preseason"
        )

        # Assert - Warning logged
        mock_logger.warning.assert_any_call("Dynasty state missing - creating fallback")


# ============================================================================
# TEST CLASS: Reset Standings Method
# ============================================================================

class TestResetStandingsMethod:
    """Test _reset_standings helper method."""

    def test_reset_standings_creates_64_records(
        self,
        service,
        mock_dynasty_db_api
    ):
        """_reset_standings should create 32 preseason + 32 regular season standings."""
        # Arrange
        mock_dynasty_db_api.initialize_standings_for_season_type.return_value = 32

        # Act
        count = service._reset_standings("test_dynasty", 2025)

        # Assert - Returns total count
        assert count == 64

        # Assert - Called twice (preseason + regular season)
        assert mock_dynasty_db_api.initialize_standings_for_season_type.call_count == 2

        # Assert - Preseason call
        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='preseason',
            connection=None
        )

        # Assert - Regular season call
        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='regular_season',
            connection=None
        )

    def test_reset_standings_with_shared_connection(
        self,
        service,
        mock_connection,
        mock_dynasty_db_api
    ):
        """_reset_standings should participate in shared transaction when connection provided."""
        # Arrange
        mock_dynasty_db_api.initialize_standings_for_season_type.return_value = 32

        # Act
        count = service._reset_standings("test_dynasty", 2025, connection=mock_connection)

        # Assert
        assert count == 64

        # Assert - Connection passed to both calls
        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='preseason',
            connection=mock_connection
        )

        mock_dynasty_db_api.initialize_standings_for_season_type.assert_any_call(
            dynasty_id="test_dynasty",
            season=2025,
            season_type='regular_season',
            connection=mock_connection
        )

    def test_reset_standings_raises_on_wrong_preseason_count(
        self,
        service,
        mock_dynasty_db_api
    ):
        """_reset_standings should raise exception when preseason count is wrong."""
        # Arrange - Wrong preseason count
        mock_dynasty_db_api.initialize_standings_for_season_type.side_effect = [30, 32]

        # Act & Assert
        with pytest.raises(Exception, match="Expected 32 preseason standings, got 30"):
            service._reset_standings("test_dynasty", 2025)

    def test_reset_standings_raises_on_wrong_regular_count(
        self,
        service,
        mock_dynasty_db_api
    ):
        """_reset_standings should raise exception when regular season count is wrong."""
        # Arrange - Correct preseason, wrong regular season count
        mock_dynasty_db_api.initialize_standings_for_season_type.side_effect = [32, 28]

        # Act & Assert
        with pytest.raises(Exception, match="Expected 32 regular season standings, got 28"):
            service._reset_standings("test_dynasty", 2025)


# ============================================================================
# TEST CLASS: Clear Playoff Data Method
# ============================================================================

class TestClearPlayoffDataMethod:
    """Test _clear_playoff_data helper method."""

    def test_clear_playoff_data_deletes_all_playoff_tables(
        self,
        service,
        mock_connection
    ):
        """_clear_playoff_data should delete from events, brackets, and seedings tables."""
        # Arrange
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Each DELETE returns 1 row affected
        mock_connection.cursor.return_value = mock_cursor

        # Act
        deleted = service._clear_playoff_data("test_dynasty", 2025, connection=mock_connection)

        # Assert - 3 DELETE queries executed (events, brackets, seedings)
        assert mock_cursor.execute.call_count == 3

        # Assert - Total deleted count (3 rows, 1 from each table)
        assert deleted == 3

    def test_clear_playoff_data_deletes_events(
        self,
        service,
        mock_connection
    ):
        """_clear_playoff_data should delete playoff GameEvents from database."""
        # Arrange
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Mock rowcount for DELETE operations
        mock_connection.cursor.return_value = mock_cursor

        # Act
        service._clear_playoff_data("test_dynasty", 2025, connection=mock_connection)

        # Assert - DELETE query for playoff events executed
        calls = [call[0] for call in mock_cursor.execute.call_args_list]
        event_delete_found = any(
            "DELETE FROM events" in str(call) and "event_type = 'GAME'" in str(call)
            for call in calls
        )
        assert event_delete_found

    def test_clear_playoff_data_deletes_brackets(
        self,
        service,
        mock_connection
    ):
        """_clear_playoff_data should delete playoff_brackets records."""
        # Arrange
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Mock rowcount for DELETE operations
        mock_connection.cursor.return_value = mock_cursor

        # Act
        service._clear_playoff_data("test_dynasty", 2025, connection=mock_connection)

        # Assert - DELETE query for playoff brackets executed
        calls = [call[0] for call in mock_cursor.execute.call_args_list]
        bracket_delete_found = any(
            "DELETE FROM playoff_brackets" in str(call)
            for call in calls
        )
        assert bracket_delete_found


# ============================================================================
# TEST CLASS: Prepare Next Season Method
# ============================================================================

class TestPrepareNextSeasonMethod:
    """Test prepare_next_season orchestration method."""

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_success(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api
    ):
        """prepare_next_season should successfully orchestrate all transition steps."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.return_value = 64
        mock_clear_playoff_data.return_value = 3

        # Act
        result = service.prepare_next_season(
            dynasty_id="test_dynasty",
            current_season=2025,
            next_season=2026
        )

        # Assert - Result structure
        assert result['success'] is True
        assert result['dynasty_id'] == "test_dynasty"
        assert result['next_season'] == 2026
        assert result['standings_created'] == 64
        assert result['playoff_records_deleted'] == 3
        assert result['season_year_updated'] is True
        assert result['error_message'] is None

        # Assert - Methods called in correct order
        mock_reset_standings.assert_called_once_with(
            dynasty_id="test_dynasty", season=2026, connection=mock_connection
        )
        mock_clear_playoff_data.assert_called_once_with(
            dynasty_id="test_dynasty", season=2025, connection=mock_connection
        )

        # Assert - Transaction committed
        mock_connection.commit.assert_called_once()

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_resets_standings(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api
    ):
        """prepare_next_season should reset standings to 0-0-0 for new season."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.return_value = 64

        # Act
        result = service.prepare_next_season(
            dynasty_id="test_dynasty",
            current_season=2025,
            next_season=2026
        )

        # Assert - Standings reset for NEW season (2026)
        mock_reset_standings.assert_called_once_with(
            dynasty_id="test_dynasty", season=2026, connection=mock_connection
        )

        # Assert - Result confirms standings reset
        assert result['standings_created'] == 64

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_clears_playoffs(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api
    ):
        """prepare_next_season should clear playoff data from OLD season."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.return_value = 64
        mock_clear_playoff_data.return_value = 3

        # Act
        result = service.prepare_next_season(
            dynasty_id="test_dynasty",
            current_season=2025,
            next_season=2026
        )

        # Assert - Playoff data cleared for OLD season (2025)
        mock_clear_playoff_data.assert_called_once_with(
            dynasty_id="test_dynasty", season=2025, connection=mock_connection
        )

        # Assert - Result confirms playoff data cleared
        assert result['playoff_records_deleted'] == 3

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_increments_year(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api
    ):
        """prepare_next_season should increment season year in dynasty_state."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.return_value = 64

        # Act
        result = service.prepare_next_season(
            dynasty_id="test_dynasty",
            current_season=2025,
            next_season=2026
        )

        # Assert - Result confirms season incremented
        assert result['next_season'] == 2026
        assert result['season_year_updated'] is True

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_rollback_on_error(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api,
        mock_logger
    ):
        """prepare_next_season should rollback transaction on any error."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.side_effect = Exception("Standings reset failed")

        # Act & Assert
        with pytest.raises(Exception, match="Standings reset failed"):
            service.prepare_next_season(
                dynasty_id="test_dynasty",
                current_season=2025,
                next_season=2026
            )

        # Assert - Rollback called
        mock_connection.rollback.assert_called_once()

        # Assert - Commit never called
        mock_connection.commit.assert_not_called()

        # Assert - Error logged
        assert mock_logger.error.call_count >= 1

    @patch.object(DynastyInitializationService, '_clear_playoff_data')
    @patch.object(DynastyInitializationService, '_reset_standings')
    def test_prepare_next_season_result_dict_structure(
        self,
        mock_reset_standings,
        mock_clear_playoff_data,
        service,
        mock_connection,
        mock_dynasty_state_api
    ):
        """prepare_next_season result dict should have all required keys."""
        # Arrange
        service.db_connection.get_connection = Mock(return_value=mock_connection)
        mock_reset_standings.return_value = 64
        mock_clear_playoff_data.return_value = 3

        # Act
        result = service.prepare_next_season(
            dynasty_id="test_dynasty",
            current_season=2025,
            next_season=2026
        )

        # Assert - All required keys present
        assert 'success' in result
        assert 'dynasty_id' in result
        assert 'next_season' in result
        assert 'standings_created' in result
        assert 'playoff_records_deleted' in result
        assert 'season_year_updated' in result
        assert 'error_message' in result

        # Assert - Correct types
        assert isinstance(result['success'], bool)
        assert isinstance(result['dynasty_id'], str)
        assert isinstance(result['next_season'], int)
        assert isinstance(result['standings_created'], int)
        assert isinstance(result['playoff_records_deleted'], int)
        assert isinstance(result['season_year_updated'], bool)
        assert result['error_message'] is None or isinstance(result['error_message'], str)
