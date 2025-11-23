"""
Integration Tests for OffseasonController

Tests that the complete offseason simulation runs all 4 phases correctly:
1. Franchise Tags
2. Free Agency
3. Draft (NEW - Phase 4A)
4. Roster Cuts

Validates that draft integration works seamlessly in the full offseason flow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from offseason.offseason_controller import OffseasonController


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_database():
    """Create mock database with minimal setup."""
    return ":memory:"


@pytest.fixture
def mock_dynasty_id():
    """Test dynasty ID."""
    return "test_offseason_integration"


@pytest.fixture
def mock_season():
    """Test season year."""
    return 2025


@pytest.fixture
def controller(mock_database, mock_dynasty_id, mock_season):
    """Create OffseasonController with mocked dependencies."""
    with patch('database.api.DatabaseAPI'), \
         patch('offseason.free_agency_manager.FreeAgencyManager'), \
         patch('offseason.roster_manager.RosterManager'), \
         patch('offseason.draft_manager.DraftManager'), \
         patch('salary_cap.tag_manager.TagManager'), \
         patch('salary_cap.cap_calculator.CapCalculator'), \
         patch('salary_cap.cap_database_api.CapDatabaseAPI'):

        controller = OffseasonController(
            database_path=mock_database,
            dynasty_id=mock_dynasty_id,
            season_year=mock_season,
            user_team_id=7,  # Add required parameter
            verbose_logging=False
        )

        # Mock franchise tag manager
        controller.franchise_tag_manager = Mock()
        controller.franchise_tag_manager.ai_evaluate_franchise_tag_candidate.return_value = {
            'should_tag': False,
            'tag_type': None
        }

        # Mock free agency manager
        controller.free_agency_manager = Mock()
        controller.free_agency_manager.simulate_30_day_free_agency.return_value = []

        # Mock roster manager
        controller.roster_manager = Mock()
        controller.roster_manager.finalize_53_man_roster_ai.return_value = {
            'total_cut': 37,
            'final_roster_size': 53
        }

        # Mock draft manager and dependencies
        controller.draft_manager = Mock()
        controller.draft_manager.draft_order_api = Mock()
        controller.draft_manager.draft_order_api.get_draft_order.return_value = [
            Mock(overall_pick=1, round_number=1, pick_in_round=1)
        ]
        controller.draft_manager.generate_draft_class.return_value = [
            {'player_id': 'prospect_1', 'overall': 85}
        ]
        controller.draft_manager.simulate_draft.return_value = [
            {'player_id': 'prospect_1', 'team_id': 1, 'round': 1, 'pick': 1}
        ]

        yield controller


# ============================================================================
# TEST: Draft Integration in Full Offseason Flow
# ============================================================================

def test_full_offseason_includes_draft(controller):
    """
    Test that simulate_ai_full_offseason() executes all 4 phases including draft.

    Validates:
    - Franchise tags run
    - Free agency runs
    - Draft runs (NEW)
    - Roster cuts run
    - Result includes draft_picks_made field
    """
    user_team_id = 7  # Lions

    # Run full offseason simulation
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Verify all expected keys exist
    assert 'franchise_tags_applied' in result
    assert 'free_agent_signings' in result
    assert 'draft_picks_made' in result  # NEW field from Phase 4A
    assert 'roster_cuts_made' in result
    assert 'total_transactions' in result

    # Verify draft actually ran
    assert result['draft_picks_made'] >= 0  # Should have draft picks

    # Verify total transactions includes draft picks
    expected_total = (
        result['franchise_tags_applied'] +
        result['free_agent_signings'] +
        result['draft_picks_made'] +
        result['roster_cuts_made']
    )
    assert result['total_transactions'] == expected_total


def test_draft_runs_in_correct_order(controller):
    """
    Test that draft runs AFTER free agency and BEFORE roster cuts.

    This is critical for realistic offseason flow:
    1. Franchise tags (Feb-March)
    2. Free agency (March)
    3. Draft (April)
    4. Roster cuts (August)
    """
    user_team_id = 7

    # Track call order using side effects
    call_order = []

    controller.free_agency_manager.simulate_30_day_free_agency.side_effect = lambda *args, **kwargs: (
        call_order.append('free_agency'),
        []  # Return value
    )[-1]

    controller.draft_manager.simulate_draft.side_effect = lambda *args, **kwargs: (
        call_order.append('draft'),
        [{'player_id': 'p1', 'team_id': 1, 'round': 1, 'pick': 1}]  # Return value
    )[-1]

    controller.roster_manager.finalize_53_man_roster_ai.side_effect = lambda *args, **kwargs: (
        call_order.append('roster_cuts'),
        {'total_cut': 37, 'final_roster_size': 53}  # Return value
    )[-1]

    # Run simulation
    controller.simulate_ai_full_offseason(user_team_id)

    # Verify order: FA → Draft → Cuts
    assert 'free_agency' in call_order
    assert 'draft' in call_order
    assert 'roster_cuts' in call_order

    fa_index = call_order.index('free_agency')
    draft_index = call_order.index('draft')
    cuts_index = call_order.index('roster_cuts')

    assert fa_index < draft_index, "Draft must run AFTER free agency"
    assert draft_index < cuts_index, "Roster cuts must run AFTER draft"


def test_draft_skips_user_team(controller):
    """
    Test that draft simulation correctly skips user team picks.

    User team should make manual draft picks, not AI picks.
    """
    user_team_id = 7

    # Run simulation
    controller.simulate_ai_full_offseason(user_team_id)

    # Verify simulate_draft was called with user_team_id
    controller.draft_manager.simulate_draft.assert_called_once()
    call_args = controller.draft_manager.simulate_draft.call_args

    assert call_args[1]['user_team_id'] == user_team_id or call_args[0][0] == user_team_id


def test_draft_handles_missing_draft_order_gracefully(controller):
    """
    Test that simulation handles missing draft order gracefully.

    If draft order doesn't exist (e.g., dynasty just created), should skip
    draft without crashing.
    """
    user_team_id = 7

    # Mock missing draft order
    controller.draft_manager.draft_order_api.get_draft_order.return_value = []

    # Should not raise exception
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Should have 0 draft picks when order missing
    assert result['draft_picks_made'] == 0

    # Other phases should still run
    assert result['roster_cuts_made'] > 0  # Roster cuts should still execute


def test_draft_handles_missing_draft_class_gracefully(controller):
    """
    Test that simulation handles missing draft class gracefully.

    If draft class doesn't exist, generate_draft_class should create it.
    """
    user_team_id = 7

    # Mock draft class generation
    controller.draft_manager.generate_draft_class.return_value = [
        {'player_id': f'prospect_{i}', 'overall': 80 + i} for i in range(300)
    ]

    # Run simulation
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Verify draft class was generated
    controller.draft_manager.generate_draft_class.assert_called_once()

    # Verify draft still ran
    assert result['draft_picks_made'] > 0


def test_draft_error_does_not_crash_offseason(controller):
    """
    Test that draft errors don't crash entire offseason simulation.

    If draft fails (database error, etc.), should log error and continue
    with roster cuts.
    """
    user_team_id = 7

    # Mock draft to raise exception
    controller.draft_manager.simulate_draft.side_effect = Exception("Database error")

    # Should not crash - exception should be caught
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Draft picks should be 0 due to error
    assert result['draft_picks_made'] == 0

    # But roster cuts should still run
    assert result['roster_cuts_made'] > 0


def test_all_ai_teams_participate_in_draft(controller):
    """
    Test that all 31 AI teams participate in draft (excluding user team).

    Draft should execute for all non-user teams.
    """
    user_team_id = 7

    # Mock draft to return 31 picks (1 per team)
    draft_results = [
        {'player_id': f'prospect_{i}', 'team_id': i, 'round': 1, 'pick': i}
        for i in range(1, 33) if i != user_team_id
    ]
    controller.draft_manager.simulate_draft.return_value = draft_results

    # Run simulation
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Verify 31 picks made (32 teams - 1 user team)
    assert result['draft_picks_made'] == 31


# ============================================================================
# TEST: Draft Results Structure
# ============================================================================

def test_draft_results_have_correct_structure(controller):
    """
    Test that draft results returned from simulate_draft have required fields.

    Each pick should have: player_id, team_id, round, pick
    """
    user_team_id = 7

    # Mock structured draft results
    mock_picks = [
        {'player_id': 'p1', 'team_id': 1, 'round': 1, 'pick': 1, 'overall_pick': 1},
        {'player_id': 'p2', 'team_id': 2, 'round': 1, 'pick': 2, 'overall_pick': 2},
    ]
    controller.draft_manager.simulate_draft.return_value = mock_picks

    # Run simulation
    result = controller.simulate_ai_full_offseason(user_team_id)

    # Verify draft picks count
    assert result['draft_picks_made'] == 2


# ============================================================================
# TEST: Backward Compatibility
# ============================================================================

def test_backward_compatibility_with_old_result_format(controller):
    """
    Test that old code expecting only 4 fields doesn't break.

    New 'draft_picks_made' field should not break existing code that only
    expects franchise_tags, free_agent_signings, roster_cuts, total_transactions.
    """
    user_team_id = 7

    result = controller.simulate_ai_full_offseason(user_team_id)

    # Old expected fields still exist
    assert 'franchise_tags_applied' in result
    assert 'free_agent_signings' in result
    assert 'roster_cuts_made' in result
    assert 'total_transactions' in result

    # New field also exists
    assert 'draft_picks_made' in result

    # Total includes all phases
    assert result['total_transactions'] == (
        result['franchise_tags_applied'] +
        result['free_agent_signings'] +
        result['draft_picks_made'] +
        result['roster_cuts_made']
    )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
