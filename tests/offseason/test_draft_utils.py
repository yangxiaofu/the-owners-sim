"""
Unit Tests for Draft Utility Converter Functions

Tests data conversion functions including:
- convert_standings_to_team_records() - DatabaseAPI → DraftOrderService format
- convert_draft_pick_order_to_draft_pick() - DraftOrderService → Database format
- convert_all_draft_picks() - Batch conversion
"""

import pytest
from typing import Dict, Any

from offseason.draft_utils import (
    convert_standings_to_team_records,
    convert_draft_pick_order_to_draft_pick,
    convert_all_draft_picks
)
from offseason.draft_order_service import TeamRecord, DraftPickOrder
from database.draft_order_database_api import DraftPick
from stores.standings_store import EnhancedTeamStanding


# ============================================================================
# FIXTURES & TEST DATA
# ============================================================================


@pytest.fixture
def sample_standings_dict():
    """Create sample standings dict matching DatabaseAPI.get_standings() format."""
    return {
        'divisions': {
            'AFC East': [
                {
                    'team': None,  # Team object not needed for converter
                    'standing': EnhancedTeamStanding(
                        team_id=1,
                        wins=12,
                        losses=5,
                        ties=0,
                        points_for=450,
                        points_against=320,
                        conference_wins=8,
                        conference_losses=4,
                        division_wins=4,
                        division_losses=2
                    )
                },
                {
                    'team': None,
                    'standing': EnhancedTeamStanding(
                        team_id=2,
                        wins=10,
                        losses=7,
                        ties=0,
                        points_for=400,
                        points_against=350,
                        conference_wins=7,
                        conference_losses=5,
                        division_wins=3,
                        division_losses=3
                    )
                },
                {
                    'team': None,
                    'standing': EnhancedTeamStanding(
                        team_id=3,
                        wins=8,
                        losses=8,
                        ties=1,
                        points_for=380,
                        points_against=380,
                        conference_wins=6,
                        conference_losses=6,
                        division_wins=2,
                        division_losses=4
                    )
                },
                {
                    'team': None,
                    'standing': EnhancedTeamStanding(
                        team_id=4,
                        wins=5,
                        losses=12,
                        ties=0,
                        points_for=300,
                        points_against=450,
                        conference_wins=3,
                        conference_losses=9,
                        division_wins=1,
                        division_losses=5
                    )
                }
            ],
            # Add more divisions to reach 32 teams (simplified for testing)
            'AFC North': [
                {'team': None, 'standing': EnhancedTeamStanding(5, 11, 6, 0, 420, 340, 8, 4, 4, 2)},
                {'team': None, 'standing': EnhancedTeamStanding(6, 9, 8, 0, 390, 370, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(7, 6, 11, 0, 320, 410, 4, 8, 2, 4)},
                {'team': None, 'standing': EnhancedTeamStanding(8, 7, 10, 0, 350, 400, 5, 7, 3, 3)}
            ],
            'AFC South': [
                {'team': None, 'standing': EnhancedTeamStanding(9, 10, 7, 0, 380, 360, 7, 5, 4, 2)},
                {'team': None, 'standing': EnhancedTeamStanding(10, 8, 9, 0, 360, 380, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(11, 7, 10, 0, 340, 390, 5, 7, 2, 4)},
                {'team': None, 'standing': EnhancedTeamStanding(12, 6, 11, 0, 330, 420, 4, 8, 2, 4)}
            ],
            'AFC West': [
                {'team': None, 'standing': EnhancedTeamStanding(13, 11, 6, 0, 410, 330, 8, 4, 5, 1)},
                {'team': None, 'standing': EnhancedTeamStanding(14, 9, 8, 0, 390, 370, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(15, 7, 10, 0, 350, 400, 5, 7, 2, 4)},
                {'team': None, 'standing': EnhancedTeamStanding(16, 5, 12, 0, 310, 440, 3, 9, 1, 5)}
            ],
            'NFC East': [
                {'team': None, 'standing': EnhancedTeamStanding(17, 13, 4, 0, 470, 310, 9, 3, 5, 1)},
                {'team': None, 'standing': EnhancedTeamStanding(18, 10, 7, 0, 400, 350, 7, 5, 4, 2)},
                {'team': None, 'standing': EnhancedTeamStanding(19, 8, 9, 0, 370, 380, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(20, 6, 11, 0, 330, 410, 4, 8, 2, 4)}
            ],
            'NFC North': [
                {'team': None, 'standing': EnhancedTeamStanding(21, 12, 5, 0, 440, 320, 8, 4, 5, 1)},
                {'team': None, 'standing': EnhancedTeamStanding(22, 9, 8, 0, 380, 370, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(23, 8, 9, 0, 370, 390, 5, 7, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(24, 7, 10, 0, 350, 400, 5, 7, 2, 4)}
            ],
            'NFC South': [
                {'team': None, 'standing': EnhancedTeamStanding(25, 10, 7, 0, 390, 360, 7, 5, 4, 2)},
                {'team': None, 'standing': EnhancedTeamStanding(26, 8, 9, 0, 360, 380, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(27, 7, 10, 0, 340, 390, 5, 7, 2, 4)},
                {'team': None, 'standing': EnhancedTeamStanding(28, 5, 12, 0, 310, 430, 3, 9, 1, 5)}
            ],
            'NFC West': [
                {'team': None, 'standing': EnhancedTeamStanding(29, 11, 6, 0, 420, 340, 8, 4, 4, 2)},
                {'team': None, 'standing': EnhancedTeamStanding(30, 9, 8, 0, 380, 370, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(31, 8, 9, 0, 360, 380, 6, 6, 3, 3)},
                {'team': None, 'standing': EnhancedTeamStanding(32, 6, 11, 0, 330, 410, 4, 8, 2, 4)}
            ]
        },
        'conferences': {},
        'playoff_picture': {}
    }


@pytest.fixture
def sample_draft_pick_order():
    """Create sample DraftPickOrder object."""
    return DraftPickOrder(
        round_number=1,
        pick_in_round=1,
        overall_pick=1,
        team_id=4,  # Team with worst record
        original_team_id=4,
        reason="non_playoff",
        team_record="5-12-0",
        strength_of_schedule=0.520
    )


# ============================================================================
# TESTS: convert_standings_to_team_records()
# ============================================================================


def test_convert_standings_success(sample_standings_dict):
    """Test successful conversion of standings to team records."""
    team_records = convert_standings_to_team_records(sample_standings_dict)

    # Should have all 32 teams
    assert len(team_records) == 32

    # All should be TeamRecord objects
    for record in team_records:
        assert isinstance(record, TeamRecord)
        assert hasattr(record, 'team_id')
        assert hasattr(record, 'wins')
        assert hasattr(record, 'losses')
        assert hasattr(record, 'ties')
        assert hasattr(record, 'win_percentage')


def test_convert_standings_team_ids(sample_standings_dict):
    """Test that all 32 team IDs are present."""
    team_records = convert_standings_to_team_records(sample_standings_dict)

    team_ids = {record.team_id for record in team_records}
    expected_ids = set(range(1, 33))  # Teams 1-32

    assert team_ids == expected_ids


def test_convert_standings_win_percentage_calculation(sample_standings_dict):
    """Test win percentage calculation."""
    team_records = convert_standings_to_team_records(sample_standings_dict)

    # Find team 1 (12-5-0)
    team1 = next(r for r in team_records if r.team_id == 1)
    expected_pct = 12 / 17  # 12 wins out of 17 games
    assert abs(team1.win_percentage - expected_pct) < 0.001

    # Find team 3 (8-8-1, has a tie)
    team3 = next(r for r in team_records if r.team_id == 3)
    expected_pct = (8 + 0.5 * 1) / 17  # 8.5 / 17
    assert abs(team3.win_percentage - expected_pct) < 0.001


def test_convert_standings_empty_dict():
    """Test error handling for empty standings dict."""
    with pytest.raises(ValueError, match="Invalid standings_dict"):
        convert_standings_to_team_records({})


def test_convert_standings_missing_divisions():
    """Test error handling for missing divisions key."""
    with pytest.raises(ValueError, match="missing 'divisions' key"):
        convert_standings_to_team_records({'foo': 'bar'})


def test_convert_standings_incomplete_teams():
    """Test error handling when not all 32 teams are present."""
    incomplete_dict = {
        'divisions': {
            'AFC East': [
                {
                    'team': None,
                    'standing': EnhancedTeamStanding(1, 10, 7, 0, 400, 350, 7, 5, 4, 2)
                }
            ]
        }
    }

    with pytest.raises(ValueError, match="Expected 32 team records, got 1"):
        convert_standings_to_team_records(incomplete_dict)


# ============================================================================
# TESTS: convert_draft_pick_order_to_draft_pick()
# ============================================================================


def test_convert_pick_order_success(sample_draft_pick_order):
    """Test successful conversion of DraftPickOrder to DraftPick."""
    db_pick = convert_draft_pick_order_to_draft_pick(
        sample_draft_pick_order,
        dynasty_id="test_dynasty",
        season=2025
    )

    assert isinstance(db_pick, DraftPick)
    assert db_pick.dynasty_id == "test_dynasty"
    assert db_pick.season == 2025
    assert db_pick.round_number == 1
    assert db_pick.pick_in_round == 1
    assert db_pick.overall_pick == 1
    assert db_pick.original_team_id == 4
    assert db_pick.current_team_id == 4


def test_convert_pick_order_defaults(sample_draft_pick_order):
    """Test that default values are set correctly."""
    db_pick = convert_draft_pick_order_to_draft_pick(
        sample_draft_pick_order,
        dynasty_id="test_dynasty",
        season=2025
    )

    # Check defaults
    assert db_pick.pick_id is None  # Auto-generated
    assert db_pick.player_id is None  # Not drafted yet
    assert db_pick.draft_class_id is None  # Not assigned yet
    assert db_pick.is_executed is False
    assert db_pick.is_compensatory is False
    assert db_pick.comp_round_end is False
    assert db_pick.acquired_via_trade is False
    assert db_pick.trade_date is None
    assert db_pick.original_trade_id is None


def test_convert_pick_order_all_rounds():
    """Test conversion for picks across all 7 rounds."""
    picks_to_convert = [
        DraftPickOrder(1, 1, 1, 4, 4, "non_playoff", "5-12-0", 0.520),
        DraftPickOrder(2, 1, 33, 4, 4, "non_playoff", "5-12-0", 0.520),
        DraftPickOrder(3, 1, 65, 4, 4, "non_playoff", "5-12-0", 0.520),
        DraftPickOrder(7, 32, 224, 17, 17, "super_bowl_win", "13-4-0", 0.485)
    ]

    for pick_order in picks_to_convert:
        db_pick = convert_draft_pick_order_to_draft_pick(
            pick_order,
            dynasty_id="test_dynasty",
            season=2025
        )

        assert db_pick.round_number == pick_order.round_number
        assert db_pick.pick_in_round == pick_order.pick_in_round
        assert db_pick.overall_pick == pick_order.overall_pick


# ============================================================================
# TESTS: convert_all_draft_picks()
# ============================================================================


def test_convert_all_picks_success():
    """Test batch conversion of all 224 draft picks."""
    # Create sample picks for all 7 rounds
    pick_orders = []
    overall = 1
    for round_num in range(1, 8):  # Rounds 1-7
        for pick_in_round in range(1, 33):  # Picks 1-32
            pick_orders.append(
                DraftPickOrder(
                    round_number=round_num,
                    pick_in_round=pick_in_round,
                    overall_pick=overall,
                    team_id=pick_in_round,  # Simplified: team_id = pick_in_round
                    original_team_id=pick_in_round,
                    reason="non_playoff",
                    team_record="8-9-0",
                    strength_of_schedule=0.500
                )
            )
            overall += 1

    # Convert all
    db_picks = convert_all_draft_picks(pick_orders, "test_dynasty", 2025)

    # Verify count
    assert len(db_picks) == 224

    # Verify all are DraftPick objects
    for db_pick in db_picks:
        assert isinstance(db_pick, DraftPick)
        assert db_pick.dynasty_id == "test_dynasty"
        assert db_pick.season == 2025

    # Verify ordering preserved
    assert db_picks[0].overall_pick == 1
    assert db_picks[32].overall_pick == 33  # First pick of round 2
    assert db_picks[223].overall_pick == 224  # Last pick


def test_convert_all_picks_empty():
    """Test batch conversion with empty list."""
    db_picks = convert_all_draft_picks([], "test_dynasty", 2025)
    assert db_picks == []


def test_convert_all_picks_preserves_order():
    """Test that pick order is preserved during conversion."""
    pick_orders = [
        DraftPickOrder(1, 1, 1, 4, 4, "non_playoff", "5-12-0", 0.520),
        DraftPickOrder(1, 2, 2, 16, 16, "non_playoff", "6-11-0", 0.510),
        DraftPickOrder(1, 32, 32, 17, 17, "super_bowl_win", "13-4-0", 0.485)
    ]

    db_picks = convert_all_draft_picks(pick_orders, "test_dynasty", 2025)

    assert len(db_picks) == 3
    assert db_picks[0].overall_pick == 1
    assert db_picks[1].overall_pick == 2
    assert db_picks[2].overall_pick == 32
    assert db_picks[0].current_team_id == 4
    assert db_picks[1].current_team_id == 16
    assert db_picks[2].current_team_id == 17
