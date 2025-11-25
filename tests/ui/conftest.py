"""
Pytest Fixtures for UI Tests

Provides shared fixtures for draft dialog and controller testing:
- Mock database fixtures
- Mock dynasty context
- Sample draft class data
- Sample draft order data
- Mock DraftManager instances
"""

import pytest
import os
import sys
from unittest.mock import MagicMock
from typing import List, Dict, Any

# Add paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
src_path = os.path.join(project_root, 'src')
demo_path = os.path.join(project_root, 'demo/draft_day_demo')

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(demo_path) not in sys.path:
    sys.path.insert(0, str(demo_path))


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def mock_database_path():
    """Mock database path for testing"""
    return ":memory:"


@pytest.fixture
def mock_dynasty_id():
    """Mock dynasty ID for testing"""
    return "test_dynasty_draft"


@pytest.fixture
def mock_season():
    """Mock season year for testing (2024 season, April 2025 offseason)"""
    # NOTE: April 2025 dates are in the offseason for the 2024 season
    # DynastyStateAPI infers season from date, so we use 2024 here
    return 2024


@pytest.fixture
def mock_user_team_id():
    """Mock user team ID (Detroit Lions)"""
    return 7


# ============================================================================
# DRAFT CLASS FIXTURES
# ============================================================================

@pytest.fixture
def sample_draft_class():
    """
    Sample draft class with 20 prospects across positions.

    Returns:
        List of prospect dicts with realistic attributes
    """
    prospects = []

    # QB prospects (3)
    prospects.extend([
        {
            'player_id': 1001,
            'first_name': 'Marcus',
            'last_name': 'Johnson',
            'position': 'QB',
            'overall': 95,
            'college': 'Ohio State',
            'age': 21,
            'height': '6-3',
            'weight': 220,
            'speed': 85,
            'strength': 78,
            'awareness': 92,
            'projected_pick_min': 1,
            'projected_pick_max': 3,
            'is_drafted': False
        },
        {
            'player_id': 1002,
            'first_name': 'Tyrell',
            'last_name': 'Williams',
            'position': 'QB',
            'overall': 88,
            'college': 'Alabama',
            'age': 22,
            'height': '6-4',
            'weight': 225,
            'speed': 82,
            'strength': 80,
            'awareness': 88,
            'projected_pick_min': 8,
            'projected_pick_max': 15,
            'is_drafted': False
        },
        {
            'player_id': 1003,
            'first_name': 'Jake',
            'last_name': 'Martinez',
            'position': 'QB',
            'overall': 82,
            'college': 'USC',
            'age': 21,
            'height': '6-2',
            'weight': 215,
            'speed': 84,
            'strength': 75,
            'awareness': 85,
            'projected_pick_min': 25,
            'projected_pick_max': 40,
            'is_drafted': False
        }
    ])

    # WR prospects (4)
    prospects.extend([
        {
            'player_id': 1004,
            'first_name': 'DeAndre',
            'last_name': 'Jackson',
            'position': 'WR',
            'overall': 92,
            'college': 'LSU',
            'age': 21,
            'height': '6-1',
            'weight': 195,
            'speed': 95,
            'strength': 72,
            'awareness': 86,
            'projected_pick_min': 3,
            'projected_pick_max': 8,
            'is_drafted': False
        },
        {
            'player_id': 1005,
            'first_name': 'Chris',
            'last_name': 'Thompson',
            'position': 'WR',
            'overall': 87,
            'college': 'Georgia',
            'age': 22,
            'height': '6-0',
            'weight': 190,
            'speed': 93,
            'strength': 70,
            'awareness': 82,
            'projected_pick_min': 12,
            'projected_pick_max': 20,
            'is_drafted': False
        },
        {
            'player_id': 1006,
            'first_name': 'Malik',
            'last_name': 'Davis',
            'position': 'WR',
            'overall': 85,
            'college': 'Clemson',
            'age': 21,
            'height': '5-11',
            'weight': 185,
            'speed': 94,
            'strength': 68,
            'awareness': 80,
            'projected_pick_min': 18,
            'projected_pick_max': 28,
            'is_drafted': False
        },
        {
            'player_id': 1007,
            'first_name': 'Jordan',
            'last_name': 'Harris',
            'position': 'WR',
            'overall': 80,
            'college': 'Oklahoma',
            'age': 22,
            'height': '6-2',
            'weight': 200,
            'speed': 90,
            'strength': 74,
            'awareness': 78,
            'projected_pick_min': 35,
            'projected_pick_max': 50,
            'is_drafted': False
        }
    ])

    # CB prospects (3)
    prospects.extend([
        {
            'player_id': 1008,
            'first_name': 'Terrance',
            'last_name': 'Brown',
            'position': 'CB',
            'overall': 90,
            'college': 'Florida',
            'age': 21,
            'height': '6-0',
            'weight': 190,
            'speed': 95,
            'strength': 70,
            'awareness': 88,
            'projected_pick_min': 5,
            'projected_pick_max': 12,
            'is_drafted': False
        },
        {
            'player_id': 1009,
            'first_name': 'Anthony',
            'last_name': 'Mitchell',
            'position': 'CB',
            'overall': 86,
            'college': 'Penn State',
            'age': 22,
            'height': '5-11',
            'weight': 185,
            'speed': 94,
            'strength': 68,
            'awareness': 84,
            'projected_pick_min': 15,
            'projected_pick_max': 25,
            'is_drafted': False
        },
        {
            'player_id': 1010,
            'first_name': 'Jamaal',
            'last_name': 'Robinson',
            'position': 'CB',
            'overall': 83,
            'college': 'Michigan',
            'age': 21,
            'height': '6-1',
            'weight': 195,
            'speed': 92,
            'strength': 72,
            'awareness': 80,
            'projected_pick_min': 28,
            'projected_pick_max': 45,
            'is_drafted': False
        }
    ])

    # EDGE prospects (3)
    prospects.extend([
        {
            'player_id': 1011,
            'first_name': 'Xavier',
            'last_name': 'Carter',
            'position': 'EDGE',
            'overall': 91,
            'college': 'Texas',
            'age': 21,
            'height': '6-4',
            'weight': 255,
            'speed': 88,
            'strength': 90,
            'awareness': 85,
            'projected_pick_min': 4,
            'projected_pick_max': 10,
            'is_drafted': False
        },
        {
            'player_id': 1012,
            'first_name': 'Derek',
            'last_name': 'Wilson',
            'position': 'EDGE',
            'overall': 87,
            'college': 'Notre Dame',
            'age': 22,
            'height': '6-3',
            'weight': 250,
            'speed': 86,
            'strength': 88,
            'awareness': 82,
            'projected_pick_min': 14,
            'projected_pick_max': 22,
            'is_drafted': False
        },
        {
            'player_id': 1013,
            'first_name': 'Brandon',
            'last_name': 'Taylor',
            'position': 'EDGE',
            'overall': 84,
            'college': 'Oregon',
            'age': 21,
            'height': '6-5',
            'weight': 260,
            'speed': 85,
            'strength': 92,
            'awareness': 78,
            'projected_pick_min': 22,
            'projected_pick_max': 35,
            'is_drafted': False
        }
    ])

    # OT prospects (3)
    prospects.extend([
        {
            'player_id': 1014,
            'first_name': 'Michael',
            'last_name': 'Anderson',
            'position': 'OT',
            'overall': 89,
            'college': 'Wisconsin',
            'age': 22,
            'height': '6-6',
            'weight': 315,
            'speed': 75,
            'strength': 95,
            'awareness': 86,
            'projected_pick_min': 6,
            'projected_pick_max': 14,
            'is_drafted': False
        },
        {
            'player_id': 1015,
            'first_name': 'Isaiah',
            'last_name': 'Moore',
            'position': 'OT',
            'overall': 85,
            'college': 'Iowa',
            'age': 21,
            'height': '6-5',
            'weight': 310,
            'speed': 73,
            'strength': 93,
            'awareness': 82,
            'projected_pick_min': 16,
            'projected_pick_max': 28,
            'is_drafted': False
        },
        {
            'player_id': 1016,
            'first_name': 'Connor',
            'last_name': 'Smith',
            'position': 'OT',
            'overall': 81,
            'college': 'Stanford',
            'age': 22,
            'height': '6-7',
            'weight': 320,
            'speed': 70,
            'strength': 94,
            'awareness': 80,
            'projected_pick_min': 32,
            'projected_pick_max': 48,
            'is_drafted': False
        }
    ])

    # RB prospects (2)
    prospects.extend([
        {
            'player_id': 1017,
            'first_name': 'Darius',
            'last_name': 'Green',
            'position': 'RB',
            'overall': 86,
            'college': 'Auburn',
            'age': 21,
            'height': '5-10',
            'weight': 215,
            'speed': 92,
            'strength': 82,
            'awareness': 80,
            'projected_pick_min': 20,
            'projected_pick_max': 32,
            'is_drafted': False
        },
        {
            'player_id': 1018,
            'first_name': 'Jamal',
            'last_name': 'Lewis',
            'position': 'RB',
            'overall': 83,
            'college': 'Florida State',
            'age': 22,
            'height': '6-0',
            'weight': 225,
            'speed': 90,
            'strength': 85,
            'awareness': 78,
            'projected_pick_min': 28,
            'projected_pick_max': 42,
            'is_drafted': False
        }
    ])

    # TE prospects (2)
    prospects.extend([
        {
            'player_id': 1019,
            'first_name': 'Tyler',
            'last_name': 'White',
            'position': 'TE',
            'overall': 84,
            'college': 'Iowa',
            'age': 22,
            'height': '6-5',
            'weight': 250,
            'speed': 82,
            'strength': 88,
            'awareness': 80,
            'projected_pick_min': 24,
            'projected_pick_max': 38,
            'is_drafted': False
        },
        {
            'player_id': 1020,
            'first_name': 'Austin',
            'last_name': 'King',
            'position': 'TE',
            'overall': 80,
            'college': 'Notre Dame',
            'age': 21,
            'height': '6-4',
            'weight': 245,
            'speed': 80,
            'strength': 86,
            'awareness': 78,
            'projected_pick_min': 38,
            'projected_pick_max': 55,
            'is_drafted': False
        }
    ])

    return prospects


@pytest.fixture
def sample_draft_order_round_1():
    """
    Sample first round draft order (32 picks).

    Returns:
        List of DraftPick objects for round 1
    """
    from database.draft_order_database_api import DraftPick

    picks = []

    # Create 32 picks for round 1
    # Order: worst record → best record
    team_order = [9, 1, 11, 17, 2, 10, 7, 18, 19, 12, 3, 20, 13, 21, 4, 14,
                  22, 5, 15, 23, 6, 16, 24, 25, 26, 27, 28, 29, 30, 31, 32, 8]

    for i, team_id in enumerate(team_order, start=1):
        picks.append(DraftPick(
            pick_id=i,
            dynasty_id='test_dynasty_draft',
            season=2025,
            round_number=1,
            pick_in_round=i,
            overall_pick=i,
            original_team_id=team_id,
            current_team_id=team_id,
            is_executed=False,
            player_id=None
        ))

    return picks


@pytest.fixture
def sample_draft_order_full():
    """
    Sample complete draft order (224 picks, 7 rounds).

    Returns:
        List of DraftPick objects for all 7 rounds
    """
    from database.draft_order_database_api import DraftPick

    picks = []
    overall_pick = 1

    # Team order (based on reverse standings)
    team_order = [9, 1, 11, 17, 2, 10, 7, 18, 19, 12, 3, 20, 13, 21, 4, 14,
                  22, 5, 15, 23, 6, 16, 24, 25, 26, 27, 28, 29, 30, 31, 32, 8]

    # Create 7 rounds of 32 picks each
    for round_num in range(1, 8):
        for pick_in_round, team_id in enumerate(team_order, start=1):
            picks.append(DraftPick(
                pick_id=overall_pick,
                dynasty_id='test_dynasty_draft',
                season=2025,
                round_number=round_num,
                pick_in_round=pick_in_round,
                overall_pick=overall_pick,
                original_team_id=team_id,
                current_team_id=team_id,
                is_executed=False,
                player_id=None
            ))
            overall_pick += 1

    return picks


# ============================================================================
# MOCK MANAGER FIXTURES
# ============================================================================

@pytest.fixture
def mock_draft_manager():
    """
    Create mock DraftManager with realistic behavior.

    Returns:
        MagicMock configured to simulate draft manager operations
    """
    mock_manager = MagicMock()

    # Mock make_draft_selection
    def make_draft_selection(round_num, pick_num, player_id, team_id):
        return {
            'success': True,
            'player_id': player_id,
            'team_id': team_id,
            'round': round_num,
            'pick': pick_num,
            'message': 'Draft selection successful'
        }

    mock_manager.make_draft_selection.side_effect = make_draft_selection

    # Mock _evaluate_prospect
    def evaluate_prospect(prospect, team_needs, pick_position):
        # Simple scoring: overall + needs match bonus
        base_score = prospect['overall']

        # Add bonus for team needs
        for need in team_needs:
            if need['position'] == prospect['position']:
                base_score += need['urgency_score'] * 5
                break

        # Slight bonus for draft position fit
        proj_min = prospect.get('projected_pick_min', 1)
        proj_max = prospect.get('projected_pick_max', 224)

        if proj_min <= pick_position <= proj_max:
            base_score += 5  # Good value

        return base_score

    mock_manager._evaluate_prospect.side_effect = evaluate_prospect

    return mock_manager


# ============================================================================
# SAMPLE TEAM NEEDS FIXTURES
# ============================================================================

@pytest.fixture
def sample_team_needs():
    """
    Sample team needs for testing.

    Returns:
        Dict mapping team_id to list of needs
    """
    from offseason.team_needs_analyzer import NeedUrgency

    return {
        7: [  # Detroit Lions
            {
                'position': 'CB',
                'urgency': NeedUrgency.CRITICAL,
                'urgency_score': 5,
                'starter_overall': 62,
                'depth_count': 2,
                'avg_depth_overall': 58.0,
                'starter_leaving': False,
                'reason': 'No quality starter (62 overall)'
            },
            {
                'position': 'EDGE',
                'urgency': NeedUrgency.HIGH,
                'urgency_score': 4,
                'starter_overall': 68,
                'depth_count': 1,
                'avg_depth_overall': 64.0,
                'starter_leaving': True,
                'reason': 'Starter contract expiring'
            },
            {
                'position': 'WR',
                'urgency': NeedUrgency.MEDIUM,
                'urgency_score': 3,
                'starter_overall': 75,
                'depth_count': 3,
                'avg_depth_overall': 70.0,
                'starter_leaving': False,
                'reason': 'Depth needed'
            }
        ],
        1: [  # Different team
            {
                'position': 'QB',
                'urgency': NeedUrgency.CRITICAL,
                'urgency_score': 5,
                'starter_overall': 60,
                'depth_count': 1,
                'avg_depth_overall': 55.0,
                'starter_leaving': False,
                'reason': 'No franchise QB'
            },
            {
                'position': 'OT',
                'urgency': NeedUrgency.HIGH,
                'urgency_score': 4,
                'starter_overall': 65,
                'depth_count': 2,
                'avg_depth_overall': 62.0,
                'starter_leaving': True,
                'reason': 'Starter retiring'
            }
        ]
    }


if __name__ == '__main__':
    pytest.main(['-v'])
