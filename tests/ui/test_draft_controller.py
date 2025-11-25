"""
Unit Tests for Draft Controller

Tests the DraftDemoController business logic for interactive draft day simulation.

Test Coverage:
- Controller initialization with database validation
- Draft order loading and current pick tracking
- Available prospects retrieval and sorting
- User pick execution with validation
- AI pick execution with needs-based evaluation
- Team needs retrieval
- Pick history tracking
- Draft progress monitoring
- Error handling for invalid states
- Dynasty isolation
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch, Mock
from typing import List, Dict, Any

# Add demo directory to path for imports
demo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'demo/draft_day_demo')
if demo_path not in sys.path:
    sys.path.insert(0, demo_path)

from draft_demo_controller import DraftDemoController


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_draft_class_api():
    """Create mock DraftClassAPI"""
    mock_api = MagicMock()

    # Mock dynasty has draft class
    mock_api.dynasty_has_draft_class.return_value = True

    # Mock get all prospects
    mock_api.get_all_prospects.return_value = [
        {
            'player_id': 1001,
            'first_name': 'Test',
            'last_name': 'QB1',
            'position': 'QB',
            'overall': 95,
            'college': 'Ohio State',
            'age': 21,
            'is_drafted': False,
            'projected_pick_min': 1,
            'projected_pick_max': 3
        },
        {
            'player_id': 1002,
            'first_name': 'Test',
            'last_name': 'WR1',
            'position': 'WR',
            'overall': 90,
            'college': 'Alabama',
            'age': 22,
            'is_drafted': False,
            'projected_pick_min': 3,
            'projected_pick_max': 8
        },
        {
            'player_id': 1003,
            'first_name': 'Test',
            'last_name': 'CB1',
            'position': 'CB',
            'overall': 88,
            'college': 'Georgia',
            'age': 21,
            'is_drafted': False,
            'projected_pick_min': 5,
            'projected_pick_max': 12
        }
    ]

    # Mock get prospect by ID
    def get_prospect_by_id(player_id, dynasty_id):
        prospects = mock_api.get_all_prospects.return_value
        for p in prospects:
            if p['player_id'] == player_id:
                return p
        return None

    mock_api.get_prospect_by_id.side_effect = get_prospect_by_id

    return mock_api


@pytest.fixture
def mock_draft_order():
    """Create mock draft order (32 picks for testing)"""
    from database.draft_order_database_api import DraftPick

    picks = []
    for i in range(1, 33):
        picks.append(DraftPick(
            pick_id=i,
            dynasty_id='test_dynasty',
            season=2025,
            round_number=1,
            pick_in_round=i,
            overall_pick=i,
            original_team_id=i,
            current_team_id=i,
            is_executed=False,
            player_id=None
        ))

    return picks


@pytest.fixture
def mock_draft_order_api(mock_draft_order):
    """Create mock DraftOrderDatabaseAPI"""
    mock_api = MagicMock()

    # Mock get_draft_order
    mock_api.get_draft_order.return_value = mock_draft_order

    # Mock mark_pick_executed
    def mark_pick_executed(pick_id, player_id):
        for pick in mock_draft_order:
            if pick.pick_id == pick_id:
                pick.is_executed = True
                pick.player_id = player_id
                return True
        return False

    mock_api.mark_pick_executed.side_effect = mark_pick_executed

    return mock_api


@pytest.fixture
def mock_draft_manager():
    """Create mock DraftManager"""
    mock_manager = MagicMock()

    # Mock make_draft_selection
    mock_manager.make_draft_selection.return_value = {
        'success': True,
        'player_id': 1001,
        'message': 'Draft selection successful'
    }

    # Mock _evaluate_prospect
    def evaluate_prospect(prospect, team_needs, pick_position):
        # Simple scoring: overall + position match bonus
        base_score = prospect['overall']

        # Add bonus for team needs
        for need in team_needs:
            if need['position'] == prospect['position']:
                base_score += need['urgency_score'] * 5
                break

        return base_score

    mock_manager._evaluate_prospect.side_effect = evaluate_prospect

    return mock_manager


@pytest.fixture
def mock_needs_analyzer():
    """Create mock TeamNeedsAnalyzer"""
    mock_analyzer = MagicMock()

    # Mock analyze_team_needs
    def analyze_team_needs(team_id, season, include_future_contracts):
        # Return simple needs structure
        from offseason.team_needs_analyzer import NeedUrgency

        return [
            {
                'position': 'QB',
                'urgency': NeedUrgency.CRITICAL,
                'urgency_score': 5,
                'starter_overall': 65,
                'depth_count': 1,
                'avg_depth_overall': 60.0,
                'starter_leaving': False,
                'reason': 'No quality starter'
            },
            {
                'position': 'WR',
                'urgency': NeedUrgency.HIGH,
                'urgency_score': 4,
                'starter_overall': 72,
                'depth_count': 2,
                'avg_depth_overall': 68.0,
                'starter_leaving': True,
                'reason': 'Starter leaving in free agency'
            }
        ]

    mock_analyzer.analyze_team_needs.side_effect = analyze_team_needs

    return mock_analyzer


@pytest.fixture
def mock_team_loader():
    """Create mock TeamDataLoader"""
    mock_loader = MagicMock()

    # Mock get_team_by_id
    def get_team_by_id(team_id):
        mock_team = MagicMock()
        mock_team.team_id = team_id
        mock_team.full_name = f"Test Team {team_id}"
        mock_team.abbreviation = f"TT{team_id}"
        return mock_team

    mock_loader.get_team_by_id.side_effect = get_team_by_id

    return mock_loader


@pytest.fixture
def draft_controller(mock_draft_class_api, mock_draft_order_api, mock_draft_manager,
                     mock_needs_analyzer, mock_team_loader):
    """Create DraftDemoController with all mocked dependencies"""
    with patch('draft_demo_controller.DraftClassAPI', return_value=mock_draft_class_api):
        with patch('draft_demo_controller.DraftOrderDatabaseAPI', return_value=mock_draft_order_api):
            with patch('draft_demo_controller.DraftManager', return_value=mock_draft_manager):
                with patch('draft_demo_controller.TeamNeedsAnalyzer', return_value=mock_needs_analyzer):
                    with patch('draft_demo_controller.TeamDataLoader', return_value=mock_team_loader):
                        controller = DraftDemoController(
                            db_path="test.db",
                            dynasty_id="test_dynasty",
                            season=2025,
                            user_team_id=7  # Detroit Lions
                        )

                        # Inject mocked dependencies for direct access in tests
                        controller.draft_api = mock_draft_class_api
                        controller.draft_order_api = mock_draft_order_api
                        controller.draft_manager = mock_draft_manager
                        controller.needs_analyzer = mock_needs_analyzer
                        controller.team_loader = mock_team_loader

                        return controller


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_controller_initialization(draft_controller):
    """Test that controller initializes properly with all dependencies"""
    assert draft_controller.db_path == "test.db"
    assert draft_controller.dynasty_id == "test_dynasty"
    assert draft_controller.season == 2025
    assert draft_controller.user_team_id == 7
    assert draft_controller.draft_api is not None
    assert draft_controller.draft_order_api is not None
    assert draft_controller.draft_manager is not None
    assert draft_controller.needs_analyzer is not None
    assert draft_controller.team_loader is not None
    assert len(draft_controller.draft_order) == 32  # Mocked order
    assert draft_controller.current_pick_index == 0  # First pick


def test_controller_initialization_missing_draft_class():
    """Test that controller raises error if draft class not found"""
    mock_api = MagicMock()
    mock_api.dynasty_has_draft_class.return_value = False
    mock_api.get_draft_order.return_value = [MagicMock()]

    with patch('draft_demo_controller.DraftClassAPI', return_value=mock_api):
        with patch('draft_demo_controller.DraftOrderDatabaseAPI', return_value=MagicMock()):
            with pytest.raises(ValueError, match="No draft class found"):
                DraftDemoController(
                    db_path="test.db",
                    dynasty_id="test_dynasty",
                    season=2025,
                    user_team_id=7
                )


def test_controller_initialization_missing_draft_order():
    """Test that controller raises error if draft order not found"""
    mock_draft_api = MagicMock()
    mock_draft_api.dynasty_has_draft_class.return_value = True

    mock_order_api = MagicMock()
    mock_order_api.get_draft_order.return_value = []  # Empty draft order

    with patch('draft_demo_controller.DraftClassAPI', return_value=mock_draft_api):
        with patch('draft_demo_controller.DraftOrderDatabaseAPI', return_value=mock_order_api):
            with pytest.raises(ValueError, match="No draft order found"):
                DraftDemoController(
                    db_path="test.db",
                    dynasty_id="test_dynasty",
                    season=2025,
                    user_team_id=7
                )


# ============================================================================
# DRAFT ORDER TESTS
# ============================================================================

def test_load_draft_order(draft_controller):
    """Test that draft order loads correctly"""
    # TODO: Implement when ready
    pass


def test_get_current_pick(draft_controller):
    """Test retrieving current pick information"""
    current_pick = draft_controller.get_current_pick()

    assert current_pick is not None
    assert current_pick['round'] == 1
    assert current_pick['pick_in_round'] == 1
    assert current_pick['overall_pick'] == 1
    assert current_pick['team_id'] == 1
    assert 'team_name' in current_pick
    assert 'is_user_pick' in current_pick
    assert 'pick_id' in current_pick


def test_get_current_pick_draft_complete(draft_controller):
    """Test get_current_pick returns None when draft is complete"""
    # Set current_pick_index beyond draft order length
    draft_controller.current_pick_index = len(draft_controller.draft_order)

    current_pick = draft_controller.get_current_pick()

    assert current_pick is None


def test_is_user_pick(draft_controller):
    """Test detecting if current pick belongs to user"""
    # Set current pick to user's team
    draft_controller.current_pick_index = 6  # Pick 7 = user team (7)

    current_pick = draft_controller.get_current_pick()
    assert current_pick['is_user_pick'] is True

    # Set current pick to different team
    draft_controller.current_pick_index = 0  # Pick 1 = team 1

    current_pick = draft_controller.get_current_pick()
    assert current_pick['is_user_pick'] is False


# ============================================================================
# PROSPECTS TESTS
# ============================================================================

def test_get_available_prospects(draft_controller):
    """Test retrieving available prospects sorted by overall"""
    prospects = draft_controller.get_available_prospects(limit=10)

    assert len(prospects) == 3  # Mocked data has 3 prospects

    # Should be sorted by overall (descending)
    assert prospects[0]['overall'] == 95  # QB1
    assert prospects[1]['overall'] == 90  # WR1
    assert prospects[2]['overall'] == 88  # CB1

    # Should include required fields
    for prospect in prospects:
        assert 'player_id' in prospect
        assert 'first_name' in prospect
        assert 'last_name' in prospect
        assert 'position' in prospect
        assert 'overall' in prospect
        assert 'college' in prospect


def test_get_available_prospects_respects_limit(draft_controller):
    """Test that limit parameter works correctly"""
    prospects = draft_controller.get_available_prospects(limit=2)

    assert len(prospects) == 2  # Should only return 2 even though 3 available


# ============================================================================
# TEAM NEEDS TESTS
# ============================================================================

def test_get_team_needs(draft_controller):
    """Test retrieving team needs"""
    needs = draft_controller.get_team_needs(team_id=7)

    assert len(needs) == 2  # Mocked data has 2 needs

    # Should include required fields
    for need in needs:
        assert 'position' in need
        assert 'urgency' in need
        assert 'urgency_score' in need
        assert 'starter_overall' in need
        assert 'depth_count' in need


# ============================================================================
# USER PICK TESTS
# ============================================================================

def test_execute_pick_user_team(draft_controller):
    """Test executing a pick for user's team"""
    # Set current pick to user's team
    draft_controller.current_pick_index = 6  # Pick 7 = user team (7)

    result = draft_controller.execute_user_pick(player_id=1001)

    assert result['success'] is True
    assert result['player_id'] == 1001
    assert result['player_name'] == 'Test QB1'
    assert result['position'] == 'QB'
    assert result['overall'] == 95
    assert result['team_id'] == 7
    assert 'team_name' in result
    assert 'college' in result

    # Should advance to next pick
    assert draft_controller.current_pick_index == 7


def test_execute_pick_not_user_team(draft_controller):
    """Test that executing pick for non-user team raises error"""
    # Current pick is team 1 (not user's team 7)
    with pytest.raises(ValueError, match="Not user's pick"):
        draft_controller.execute_user_pick(player_id=1001)


def test_execute_pick_draft_complete(draft_controller):
    """Test that executing pick when draft is complete raises error"""
    # Set current_pick_index beyond draft order length
    draft_controller.current_pick_index = len(draft_controller.draft_order)

    with pytest.raises(ValueError, match="Draft is complete"):
        draft_controller.execute_user_pick(player_id=1001)


def test_execute_pick_invalid_player(draft_controller):
    """Test that executing pick with invalid player raises error"""
    # Set current pick to user's team
    draft_controller.current_pick_index = 6  # Pick 7 = user team (7)

    with pytest.raises(ValueError, match="Prospect .* not found"):
        draft_controller.execute_user_pick(player_id=9999)


def test_execute_pick_already_drafted_player(draft_controller):
    """Test that executing pick with already drafted player raises error"""
    # Set current pick to user's team
    draft_controller.current_pick_index = 6  # Pick 7 = user team (7)

    # Mark player as drafted
    draft_controller.draft_api.get_all_prospects.return_value[0]['is_drafted'] = True

    with pytest.raises(ValueError, match="already drafted"):
        draft_controller.execute_user_pick(player_id=1001)


# ============================================================================
# AI PICK TESTS
# ============================================================================

def test_execute_pick_ai_team(draft_controller):
    """Test executing an AI team's pick with needs-based evaluation"""
    # Current pick is team 1 (AI team)
    result = draft_controller.execute_ai_pick()

    assert result['success'] is True
    assert 'player_id' in result
    assert 'player_name' in result
    assert 'position' in result
    assert 'overall' in result
    assert 'team_id' in result
    assert 'team_name' in result
    assert 'needs_match' in result
    assert 'eval_score' in result

    # Should advance to next pick
    assert draft_controller.current_pick_index == 1


def test_execute_pick_ai_current_pick_is_user(draft_controller):
    """Test that executing AI pick when current pick is user's raises error"""
    # Set current pick to user's team
    draft_controller.current_pick_index = 6  # Pick 7 = user team (7)

    with pytest.raises(ValueError, match="Current pick belongs to user"):
        draft_controller.execute_ai_pick()


def test_execute_pick_ai_no_prospects(draft_controller):
    """Test that executing AI pick with no prospects raises error"""
    # Mock empty prospects list
    draft_controller.draft_api.get_all_prospects.return_value = []

    with pytest.raises(ValueError, match="No prospects available"):
        draft_controller.execute_ai_pick()


# ============================================================================
# PICK HISTORY TESTS
# ============================================================================

def test_simulate_next_pick(draft_controller):
    """Test simulating next pick (user or AI)"""
    # TODO: Implement when ready
    pass


def test_get_pick_history(draft_controller):
    """Test retrieving pick history"""
    # Execute a few picks first
    draft_controller.current_pick_index = 0
    draft_controller.execute_ai_pick()
    draft_controller.execute_ai_pick()

    history = draft_controller.get_pick_history(limit=5)

    assert len(history) == 2

    # Should be in reverse order (most recent first)
    assert history[0]['overall_pick'] == 2
    assert history[1]['overall_pick'] == 1

    # Should include required fields
    for pick in history:
        assert 'round' in pick
        assert 'pick' in pick
        assert 'overall_pick' in pick
        assert 'team_id' in pick
        assert 'team_name' in pick
        assert 'player_id' in pick
        assert 'player_name' in pick
        assert 'position' in pick
        assert 'overall' in pick


def test_get_pick_history_respects_limit(draft_controller):
    """Test that pick history respects limit parameter"""
    # Execute 5 picks
    for _ in range(5):
        draft_controller.execute_ai_pick()

    history = draft_controller.get_pick_history(limit=3)

    assert len(history) == 3


# ============================================================================
# DRAFT PROGRESS TESTS
# ============================================================================

def test_save_draft_progress(draft_controller):
    """Test saving draft progress to database"""
    # TODO: Implement when ready
    pass


def test_get_draft_progress(draft_controller):
    """Test retrieving draft progress statistics"""
    progress = draft_controller.get_draft_progress()

    assert progress['picks_completed'] == 0
    assert progress['picks_remaining'] == 32
    assert progress['total_picks'] == 32
    assert progress['completion_pct'] == 0.0
    assert progress['current_round'] == 1
    assert progress['is_complete'] is False

    # Execute some picks and check again
    draft_controller.execute_ai_pick()
    draft_controller.execute_ai_pick()

    progress = draft_controller.get_draft_progress()
    assert progress['picks_completed'] == 2
    assert progress['picks_remaining'] == 30
    assert progress['completion_pct'] == pytest.approx(6.25, rel=0.1)


def test_is_draft_complete(draft_controller):
    """Test detecting when draft is complete"""
    assert draft_controller.is_draft_complete() is False

    # Set current_pick_index to end
    draft_controller.current_pick_index = len(draft_controller.draft_order)

    assert draft_controller.is_draft_complete() is True


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_error_handling_invalid_pick(draft_controller):
    """Test error handling for invalid pick operations"""
    # TODO: Implement when ready
    pass


# ============================================================================
# DYNASTY ISOLATION TESTS
# ============================================================================

def test_dynasty_isolation(draft_controller):
    """Test that controller properly isolates draft data by dynasty"""
    # Verify dynasty_id is passed to all API calls
    draft_controller.get_available_prospects()

    # Check that get_all_prospects was called with correct dynasty_id
    draft_controller.draft_api.get_all_prospects.assert_called()
    call_kwargs = draft_controller.draft_api.get_all_prospects.call_args[1]
    assert call_kwargs['dynasty_id'] == 'test_dynasty'
    assert call_kwargs['season'] == 2025


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
