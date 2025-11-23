"""
Test RosterManager GM Integration

Verifies that GM personality modifiers are correctly applied to roster cuts.
"""

import pytest
from unittest.mock import MagicMock, patch
from offseason.roster_manager import RosterManager
from team_management.gm_archetype import GMArchetype


@pytest.fixture
def mock_database_path():
    """Mock database path for testing."""
    return ":memory:"


@pytest.fixture
def mock_dynasty_id():
    """Mock dynasty ID for testing."""
    return "test_dynasty"


@pytest.fixture
def loyal_gm():
    """Create a GM with high loyalty (should protect long-tenured players)."""
    return GMArchetype(
        name="Loyal Larry",
        description="Values team loyalty",
        loyalty=0.9,  # High loyalty
        veteran_preference=0.7,
        risk_tolerance=0.3,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        star_chasing=0.3
    )


@pytest.fixture
def ruthless_gm():
    """Create a GM with low loyalty (should cut long-tenured players more easily)."""
    return GMArchetype(
        name="Ruthless Rick",
        description="Values performance over loyalty",
        loyalty=0.1,  # Low loyalty
        veteran_preference=0.3,
        risk_tolerance=0.7,
        win_now_mentality=0.8,
        draft_pick_value=0.3,
        cap_management=0.7,
        trade_frequency=0.7,
        star_chasing=0.6
    )


def test_roster_manager_accepts_gm_archetype(mock_database_path, mock_dynasty_id, loyal_gm):
    """Test that RosterManager accepts GM archetype in constructor."""
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        manager = RosterManager(
            database_path=mock_database_path,
            dynasty_id=mock_dynasty_id,
            season_year=2024,
            enable_persistence=False,
            gm_archetype=loyal_gm
        )

        assert manager.gm == loyal_gm
        assert manager.context_service is not None


def test_roster_manager_without_gm_archetype(mock_database_path, mock_dynasty_id):
    """Test that RosterManager works without GM archetype (backward compatibility)."""
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        manager = RosterManager(
            database_path=mock_database_path,
            dynasty_id=mock_dynasty_id,
            season_year=2024,
            enable_persistence=False
        )

        assert manager.gm is None
        assert manager.context_service is None


def test_finalize_53_man_roster_ai_with_gm_parameter(mock_database_path, mock_dynasty_id, loyal_gm):
    """Test that finalize_53_man_roster_ai accepts GM archetype parameter."""
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        manager = RosterManager(
            database_path=mock_database_path,
            dynasty_id=mock_dynasty_id,
            season_year=2024,
            enable_persistence=False
        )

        # Mock roster data
        manager._get_mock_90_man_roster = MagicMock(return_value=[])

        # Call with GM archetype parameter
        result = manager.finalize_53_man_roster_ai(team_id=1, gm_archetype=loyal_gm)

        assert 'final_roster' in result
        assert 'cuts' in result


def test_years_with_team_calculation():
    """Test _calculate_years_with_team helper method."""
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        manager = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False
        )

        # Test valid date
        years = manager._calculate_years_with_team("2018-09-01", 2024)
        assert years == 6

        # Test same year (rookie)
        years = manager._calculate_years_with_team("2024-04-01", 2024)
        assert years == 0

        # Test None date
        years = manager._calculate_years_with_team(None, 2024)
        assert years == 0

        # Test invalid date format
        years = manager._calculate_years_with_team("invalid", 2024)
        assert years == 0


def test_player_dict_to_player_object_conversion():
    """Test _create_player_from_dict helper method."""
    with patch('offseason.roster_manager.PlayerRosterAPI'), \
         patch('offseason.roster_manager.CapDatabaseAPI'), \
         patch('offseason.roster_manager.TransactionLogger'):

        manager = RosterManager(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            enable_persistence=False
        )

        player_dict = {
            'player_id': 123,
            'player_name': 'John Doe',
            'number': 88,
            'position': 'wide_receiver',
            'overall': 85,
            'age': 28,
            'cap_hit': 5_000_000,
            'joined_date': '2019-09-01'
        }

        player_obj = manager._create_player_from_dict(player_dict)

        assert player_obj.player_id == 123
        assert player_obj.name == 'John Doe'
        assert player_obj.number == 88
        assert player_obj.primary_position == 'wide_receiver'
        assert player_obj.age == 28
        assert player_obj.cap_hit == 5_000_000
        assert player_obj.years_with_team == 5  # 2024 - 2019
        assert player_obj.ratings['overall'] == 85


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
