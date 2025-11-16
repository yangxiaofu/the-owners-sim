"""
Tests for DraftDataModel Integration

Tests the core integration logic that connects UI to draft order calculation system.
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add src and ui to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from domain_models.draft_data_model import DraftDataModel
from offseason.draft_order_service import TeamRecord


@pytest.fixture
def mock_database_api():
    """Create mock DatabaseAPI"""
    mock_api = MagicMock()

    # Mock standings response (simplified structure)
    mock_api.get_standings.return_value = {
        'divisions': {
            'AFC East': [
                {
                    'team': MagicMock(team_id=1, full_name='Team 1'),
                    'standing': MagicMock(team_id=1, wins=5, losses=12, ties=0)
                },
                {
                    'team': MagicMock(team_id=2, full_name='Team 2'),
                    'standing': MagicMock(team_id=2, wins=6, losses=11, ties=0)
                },
            ],
            'AFC North': [
                {
                    'team': MagicMock(team_id=3, full_name='Team 3'),
                    'standing': MagicMock(team_id=3, wins=7, losses=10, ties=0)
                },
                {
                    'team': MagicMock(team_id=4, full_name='Team 4'),
                    'standing': MagicMock(team_id=4, wins=8, losses=9, ties=0)
                },
            ],
            'AFC South': [
                {
                    'team': MagicMock(team_id=5, full_name='Team 5'),
                    'standing': MagicMock(team_id=5, wins=9, losses=8, ties=0)
                },
                {
                    'team': MagicMock(team_id=6, full_name='Team 6'),
                    'standing': MagicMock(team_id=6, wins=10, losses=7, ties=0)
                },
            ],
            'AFC West': [
                {
                    'team': MagicMock(team_id=7, full_name='Team 7'),
                    'standing': MagicMock(team_id=7, wins=11, losses=6, ties=0)
                },
                {
                    'team': MagicMock(team_id=8, full_name='Team 8'),
                    'standing': MagicMock(team_id=8, wins=12, losses=5, ties=0)
                },
            ],
            'NFC East': [
                {
                    'team': MagicMock(team_id=9, full_name='Team 9'),
                    'standing': MagicMock(team_id=9, wins=4, losses=13, ties=0)
                },
                {
                    'team': MagicMock(team_id=10, full_name='Team 10'),
                    'standing': MagicMock(team_id=10, wins=5, losses=12, ties=0)
                },
            ],
            'NFC North': [
                {
                    'team': MagicMock(team_id=11, full_name='Team 11'),
                    'standing': MagicMock(team_id=11, wins=6, losses=11, ties=0)
                },
                {
                    'team': MagicMock(team_id=12, full_name='Team 12'),
                    'standing': MagicMock(team_id=12, wins=7, losses=10, ties=0)
                },
            ],
            'NFC South': [
                {
                    'team': MagicMock(team_id=13, full_name='Team 13'),
                    'standing': MagicMock(team_id=13, wins=8, losses=9, ties=0)
                },
                {
                    'team': MagicMock(team_id=14, full_name='Team 14'),
                    'standing': MagicMock(team_id=14, wins=9, losses=8, ties=0)
                },
            ],
            'NFC West': [
                {
                    'team': MagicMock(team_id=15, full_name='Team 15'),
                    'standing': MagicMock(team_id=15, wins=10, losses=7, ties=0)
                },
                {
                    'team': MagicMock(team_id=16, full_name='Team 16'),
                    'standing': MagicMock(team_id=16, wins=11, losses=6, ties=0)
                },
            ],
        }
    }

    # Add more teams to reach 32 (simplified for testing)
    for i in range(17, 33):
        division = 'AFC East' if i % 2 == 0 else 'NFC East'
        if division not in mock_api.get_standings.return_value['divisions']:
            mock_api.get_standings.return_value['divisions'][division] = []
        mock_api.get_standings.return_value['divisions'][division].append({
            'team': MagicMock(team_id=i, full_name=f'Team {i}'),
            'standing': MagicMock(team_id=i, wins=5 + (i % 10), losses=12 - (i % 10), ties=0)
        })

    # Mock schedules
    mock_api.get_all_team_schedules.return_value = {
        i: [j for j in range(1, 33) if j != i][:17]  # 17 game schedule
        for i in range(1, 33)
    }

    return mock_api


@pytest.fixture
def mock_playoff_api():
    """Create mock PlayoffResultsAPI"""
    mock_api = MagicMock()

    # Mock complete playoff results
    mock_api.get_playoff_results.return_value = {
        'wild_card_losers': [17, 18, 19, 20, 21, 22],
        'divisional_losers': [23, 24, 25, 26],
        'conference_losers': [27, 28],
        'super_bowl_loser': 29,
        'super_bowl_winner': 30
    }

    return mock_api


@pytest.fixture
def mock_draft_order_service():
    """Create mock DraftOrderService"""
    mock_service = MagicMock()

    # Mock calculate_draft_order to return 224 picks
    from offseason.draft_order_service import DraftPickOrder

    mock_picks = []
    overall_pick = 1
    for round_num in range(1, 8):  # 7 rounds
        for pick_in_round in range(1, 33):  # 32 picks per round
            mock_picks.append(DraftPickOrder(
                round_number=round_num,
                pick_in_round=pick_in_round,
                overall_pick=overall_pick,
                team_id=pick_in_round,
                original_team_id=pick_in_round,
                reason="non_playoff",
                team_record=f"{5+pick_in_round}-{12-pick_in_round}-0",
                strength_of_schedule=0.500
            ))
            overall_pick += 1

    mock_service.calculate_draft_order.return_value = mock_picks

    return mock_service


def test_get_draft_order_returns_224_picks(mock_database_api, mock_playoff_api, mock_draft_order_service):
    """Test that get_draft_order returns 224 picks for all rounds"""
    with patch('domain_models.draft_data_model.DatabaseAPI', return_value=mock_database_api):
        with patch('domain_models.draft_data_model.PlayoffResultsAPI', return_value=mock_playoff_api):
            with patch('domain_models.draft_data_model.DraftOrderService', return_value=mock_draft_order_service):
                model = DraftDataModel(
                    db_path="test.db",
                    dynasty_id="test_dynasty",
                    season=2025
                )

                result = model.get_draft_order()

                # Should return dict with picks list
                assert 'picks' in result
                assert len(result['picks']) == 224, f"Expected 224 picks, got {len(result['picks'])}"
                assert result['playoffs_complete'] == True
                assert len(result['errors']) == 0


def test_get_draft_order_round_filtering(mock_database_api, mock_playoff_api, mock_draft_order_service):
    """Test that round filtering works correctly"""
    with patch('domain_models.draft_data_model.DatabaseAPI', return_value=mock_database_api):
        with patch('domain_models.draft_data_model.PlayoffResultsAPI', return_value=mock_playoff_api):
            with patch('domain_models.draft_data_model.DraftOrderService', return_value=mock_draft_order_service):
                model = DraftDataModel(
                    db_path="test.db",
                    dynasty_id="test_dynasty",
                    season=2025
                )

                # Test round 1 filtering
                result1 = model.get_draft_order(round_number=1)
                round1_picks = result1['picks']
                assert len(round1_picks) == 32, f"Expected 32 picks in round 1, got {len(round1_picks)}"
                assert all(p['round_number'] == 1 for p in round1_picks)

                # Test round 7 filtering
                result7 = model.get_draft_order(round_number=7)
                round7_picks = result7['picks']
                assert len(round7_picks) == 32, f"Expected 32 picks in round 7, got {len(round7_picks)}"
                assert all(p['round_number'] == 7 for p in round7_picks)


def test_calculate_strength_of_schedule():
    """Test SOS calculation is correct"""
    # Create a simple model instance
    model = DraftDataModel(
        db_path=":memory:",
        dynasty_id="test",
        season=2025
    )

    # Create test data
    team_records = [
        TeamRecord(team_id=1, wins=10, losses=7, ties=0, win_percentage=0.588),
        TeamRecord(team_id=2, wins=8, losses=9, ties=0, win_percentage=0.471),
        TeamRecord(team_id=3, wins=12, losses=5, ties=0, win_percentage=0.706),
    ]

    schedules = {
        1: [2, 3],  # Team 1 plays Teams 2 and 3
        2: [1, 3],  # Team 2 plays Teams 1 and 3
        3: [1, 2],  # Team 3 plays Teams 1 and 2
    }

    sos_dict = model._calculate_strength_of_schedule(schedules, team_records)

    # Team 1 SOS = average of Team 2 (.471) and Team 3 (.706) = 0.5885
    assert abs(sos_dict[1] - 0.5885) < 0.001, f"Team 1 SOS should be ~0.5885, got {sos_dict[1]}"

    # Team 2 SOS = average of Team 1 (.588) and Team 3 (.706) = 0.647
    assert abs(sos_dict[2] - 0.647) < 0.001, f"Team 2 SOS should be ~0.647, got {sos_dict[2]}"

    # Team 3 SOS = average of Team 1 (.588) and Team 2 (.471) = 0.5295
    assert abs(sos_dict[3] - 0.5295) < 0.001, f"Team 3 SOS should be ~0.5295, got {sos_dict[3]}"


def test_get_draft_order_structure():
    """Test that draft order returns correct data structure"""
    # This test verifies the dict structure is correct
    # We'll use minimal mocking since we mainly care about structure
    pass  # TODO: Implement once we can test with real data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
