"""
Unit tests for statistical ranking utilities.

Tests league, conference, and division rankings with comprehensive tie handling.
"""
import pytest
from statistics.rankings import (
    calculate_rankings,
    calculate_conference_rankings,
    calculate_division_rankings,
    get_percentile,
    add_all_rankings
)


@pytest.fixture
def mock_player_stats():
    """Mock player stats with multiple conferences and divisions."""
    return [
        # AFC East (Bills, Miami)
        {'player_id': 1, 'name': 'QB1', 'team_id': 1, 'passing_yards': 5000, 'interceptions': 10},   # Buffalo
        {'player_id': 2, 'name': 'QB2', 'team_id': 2, 'passing_yards': 4500, 'interceptions': 8},    # Miami
        # AFC North (Ravens, Cleveland)
        {'player_id': 3, 'name': 'QB3', 'team_id': 5, 'passing_yards': 4500, 'interceptions': 12},   # Baltimore
        {'player_id': 4, 'name': 'QB4', 'team_id': 7, 'passing_yards': 4000, 'interceptions': 8},    # Cleveland
        # AFC South (Kansas City, Denver)
        {'player_id': 5, 'name': 'QB5', 'team_id': 14, 'passing_yards': 3500, 'interceptions': 15},  # KC
        {'player_id': 6, 'name': 'QB6', 'team_id': 13, 'passing_yards': 3000, 'interceptions': 8},   # Denver
        # AFC West (Las Vegas, LA Chargers)
        {'player_id': 7, 'name': 'QB7', 'team_id': 15, 'passing_yards': 4800, 'interceptions': 9},   # LV
        {'player_id': 8, 'name': 'QB8', 'team_id': 16, 'passing_yards': 3200, 'interceptions': 14},  # LAC
        # NFC East (Cowboys, Eagles)
        {'player_id': 9, 'name': 'QB9', 'team_id': 17, 'passing_yards': 4600, 'interceptions': 11},  # Dallas
        {'player_id': 10, 'name': 'QB10', 'team_id': 19, 'passing_yards': 4400, 'interceptions': 7}, # Philly
        # NFC North (Packers, Lions)
        {'player_id': 11, 'name': 'QB11', 'team_id': 23, 'passing_yards': 4200, 'interceptions': 10}, # GB
        {'player_id': 12, 'name': 'QB12', 'team_id': 22, 'passing_yards': 3800, 'interceptions': 6},  # Detroit
        # NFC South (Saints, Falcons)
        {'player_id': 13, 'name': 'QB13', 'team_id': 27, 'passing_yards': 3600, 'interceptions': 13}, # NOLA
        {'player_id': 14, 'name': 'QB14', 'team_id': 25, 'passing_yards': 3400, 'interceptions': 9},  # ATL
        # NFC West (49ers, Seahawks)
        {'player_id': 15, 'name': 'QB15', 'team_id': 31, 'passing_yards': 4100, 'interceptions': 8},  # SF
        {'player_id': 16, 'name': 'QB16', 'team_id': 32, 'passing_yards': 3900, 'interceptions': 10}, # SEA
    ]


# Test League Rankings (Descending Order)
def test_league_rankings_descending(mock_player_stats):
    """Test league rankings for yards (descending - highest first)."""
    ranked = calculate_rankings(mock_player_stats, 'passing_yards', ascending=False)

    assert ranked[0]['passing_yards'] == 5000
    assert ranked[0]['league_rank'] == 1

    assert ranked[-1]['passing_yards'] == 3000
    assert ranked[-1]['league_rank'] == 16


def test_league_rankings_ascending(mock_player_stats):
    """Test league rankings for INTs (ascending - lowest first)."""
    ranked = calculate_rankings(mock_player_stats, 'interceptions', ascending=True)

    # Lowest INT should be rank 1
    assert ranked[0]['interceptions'] == 6
    assert ranked[0]['league_rank'] == 1

    # Highest INT should be rank 16
    assert ranked[-1]['interceptions'] == 15
    assert ranked[-1]['league_rank'] == 16


def test_league_rankings_with_ties():
    """Test tie handling - same stat gets same rank, next rank skips."""
    stats = [
        {'player_id': 1, 'yards': 5000},
        {'player_id': 2, 'yards': 4500},
        {'player_id': 3, 'yards': 4500},  # Tied with player 2
        {'player_id': 4, 'yards': 4000},
        {'player_id': 5, 'yards': 4000},  # Tied with player 4
        {'player_id': 6, 'yards': 4000},  # Three-way tie
        {'player_id': 7, 'yards': 3500},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # Check ranks
    assert ranked[0]['league_rank'] == 1  # 5000 yards
    assert ranked[1]['league_rank'] == 2  # 4500 yards (tied)
    assert ranked[2]['league_rank'] == 2  # 4500 yards (tied)
    assert ranked[3]['league_rank'] == 4  # 4000 yards (skips 3, three-way tie)
    assert ranked[4]['league_rank'] == 4  # 4000 yards (tied)
    assert ranked[5]['league_rank'] == 4  # 4000 yards (tied)
    assert ranked[6]['league_rank'] == 7  # 3500 yards (skips 5, 6)


def test_league_rankings_all_tied():
    """Test all players with same stat."""
    stats = [
        {'player_id': 1, 'yards': 4000},
        {'player_id': 2, 'yards': 4000},
        {'player_id': 3, 'yards': 4000},
        {'player_id': 4, 'yards': 4000},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # All should be rank 1
    for player in ranked:
        assert player['league_rank'] == 1


def test_league_rankings_single_player():
    """Test single player ranking."""
    stats = [{'player_id': 1, 'yards': 4000}]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    assert ranked[0]['league_rank'] == 1


def test_league_rankings_empty_input():
    """Test empty input."""
    ranked = calculate_rankings([], 'yards', ascending=False)
    assert ranked == []


def test_league_rankings_missing_stat_key():
    """Test handling of missing stat keys."""
    stats = [
        {'player_id': 1, 'yards': 5000},
        {'player_id': 2},  # Missing 'yards'
        {'player_id': 3, 'yards': 4500},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # Player with missing stat should be treated as 0 and ranked last
    assert ranked[-1]['player_id'] == 2
    assert ranked[-1].get('yards', 0) == 0


# Test Conference Rankings
def test_conference_rankings_afc_vs_nfc(mock_player_stats):
    """Test conference rankings separate AFC and NFC."""
    ranked = calculate_conference_rankings(mock_player_stats, 'passing_yards', ascending=False)

    # Find best AFC and NFC QBs
    afc_players = [p for p in ranked if p['team_id'] in [1, 2, 5, 7, 13, 14, 15, 16]]  # AFC teams
    nfc_players = [p for p in ranked if p['team_id'] in [17, 19, 22, 23, 25, 27, 31, 32]]  # NFC teams

    # Check AFC rankings
    afc_sorted = sorted(afc_players, key=lambda x: x['conference_rank'])
    assert afc_sorted[0]['passing_yards'] == 5000
    assert afc_sorted[0]['conference_rank'] == 1

    # Check NFC rankings
    nfc_sorted = sorted(nfc_players, key=lambda x: x['conference_rank'])
    assert nfc_sorted[0]['passing_yards'] == 4600
    assert nfc_sorted[0]['conference_rank'] == 1


def test_conference_rankings_with_ties():
    """Test conference tie handling."""
    stats = [
        {'player_id': 1, 'team_id': 1, 'yards': 5000},   # AFC Buffalo
        {'player_id': 2, 'team_id': 2, 'yards': 4500},   # AFC Miami
        {'player_id': 3, 'team_id': 3, 'yards': 4500},   # AFC New England (tied)
        {'player_id': 4, 'team_id': 17, 'yards': 4800},  # NFC Dallas
        {'player_id': 5, 'team_id': 19, 'yards': 4800},  # NFC Philadelphia (tied)
    ]

    ranked = calculate_conference_rankings(stats, 'yards', ascending=False)

    # AFC: ranks should be 1, 2, 2
    afc_players = [p for p in ranked if p['team_id'] in [1, 2, 3]]
    afc_sorted = sorted(afc_players, key=lambda x: x['yards'], reverse=True)
    assert afc_sorted[0]['conference_rank'] == 1
    assert afc_sorted[1]['conference_rank'] == 2
    assert afc_sorted[2]['conference_rank'] == 2

    # NFC: ranks should be 1, 1
    nfc_players = [p for p in ranked if p['team_id'] in [17, 19]]
    for player in nfc_players:
        assert player['conference_rank'] == 1


def test_conference_rankings_empty_input():
    """Test empty input for conference rankings."""
    ranked = calculate_conference_rankings([], 'yards', ascending=False)
    assert ranked == []


# Test Division Rankings
def test_division_rankings_all_divisions(mock_player_stats):
    """Test division rankings for all 8 divisions."""
    ranked = calculate_division_rankings(mock_player_stats, 'passing_yards', ascending=False)

    # Check each player has division_rank
    for player in ranked:
        assert 'division_rank' in player
        assert player['division_rank'] >= 1


def test_division_rankings_same_division():
    """Test division rankings within same division."""
    stats = [
        {'player_id': 1, 'team_id': 1, 'yards': 5000},   # AFC East (Buffalo)
        {'player_id': 2, 'team_id': 2, 'yards': 4500},   # AFC East (Miami)
        {'player_id': 3, 'team_id': 27, 'yards': 4600},  # NFC South (Saints)
        {'player_id': 4, 'team_id': 25, 'yards': 4400},  # NFC South (Falcons)
    ]

    ranked = calculate_division_rankings(stats, 'yards', ascending=False)

    # AFC East players
    afc_east = [p for p in ranked if p['team_id'] in [1, 2]]
    afc_east_sorted = sorted(afc_east, key=lambda x: x['division_rank'])
    assert afc_east_sorted[0]['yards'] == 5000
    assert afc_east_sorted[0]['division_rank'] == 1
    assert afc_east_sorted[1]['yards'] == 4500
    assert afc_east_sorted[1]['division_rank'] == 2

    # NFC South players
    nfc_south = [p for p in ranked if p['team_id'] in [25, 27]]
    nfc_south_sorted = sorted(nfc_south, key=lambda x: x['division_rank'])
    assert nfc_south_sorted[0]['yards'] == 4600
    assert nfc_south_sorted[0]['division_rank'] == 1
    assert nfc_south_sorted[1]['yards'] == 4400
    assert nfc_south_sorted[1]['division_rank'] == 2


def test_division_rankings_with_ties():
    """Test division tie handling."""
    stats = [
        {'player_id': 1, 'team_id': 1, 'yards': 5000},   # AFC East (Buffalo)
        {'player_id': 2, 'team_id': 2, 'yards': 4500},   # AFC East (Miami)
        {'player_id': 3, 'team_id': 27, 'yards': 4500},  # NFC South (Saints - tied with player 2, different division)
    ]

    ranked = calculate_division_rankings(stats, 'yards', ascending=False)

    # AFC East: ranks 1, 2
    afc_east = [p for p in ranked if p['team_id'] in [1, 2]]
    assert len(afc_east) == 2
    assert afc_east[0]['division_rank'] in [1, 2]
    assert afc_east[1]['division_rank'] in [1, 2]

    # NFC South: rank 1 (only player in division)
    nfc_south = [p for p in ranked if p['team_id'] == 27]
    assert nfc_south[0]['division_rank'] == 1


def test_division_rankings_empty_input():
    """Test empty input for division rankings."""
    ranked = calculate_division_rankings([], 'yards', ascending=False)
    assert ranked == []


# Test Percentile Calculations
def test_percentile_calculation():
    """Test percentile calculation."""
    all_stats = [3000, 3500, 4000, 4500, 5000]

    # Player with 4000 yards is better than 2 of 5 (40%)
    percentile = get_percentile(4000, all_stats)
    assert percentile == 40.0

    # Player with 5000 yards is better than 4 of 5 (80%)
    percentile = get_percentile(5000, all_stats)
    assert percentile == 80.0

    # Player with 3000 yards is better than 0 of 5 (0%)
    percentile = get_percentile(3000, all_stats)
    assert percentile == 0.0


def test_percentile_with_ties():
    """Test percentile with tied stats."""
    all_stats = [3000, 4000, 4000, 4000, 5000]

    # Player with 4000 yards is better than 1 of 5 (20%)
    percentile = get_percentile(4000, all_stats)
    assert percentile == 20.0

    # Player with 5000 yards is better than 4 of 5 (80%)
    percentile = get_percentile(5000, all_stats)
    assert percentile == 80.0


def test_percentile_empty_input():
    """Test percentile with empty input."""
    percentile = get_percentile(4000, [])
    assert percentile == 0.0


def test_percentile_single_player():
    """Test percentile with single player."""
    all_stats = [4000]

    # Player with 4000 yards is better than 0 of 1 (0%)
    percentile = get_percentile(4000, all_stats)
    assert percentile == 0.0

    # Player with 5000 yards is better than 1 of 1 (100%)
    percentile = get_percentile(5000, all_stats)
    assert percentile == 100.0


# Test add_all_rankings
def test_add_all_rankings(mock_player_stats):
    """Test adding all ranking types in one call."""
    ranked = add_all_rankings(mock_player_stats, 'passing_yards', ascending=False)

    # Check all ranking fields are present
    for player in ranked:
        assert 'league_rank' in player
        assert 'conference_rank' in player
        assert 'division_rank' in player

    # Verify top player has rank 1 in all categories
    top_player = ranked[0]
    assert top_player['league_rank'] == 1
    assert top_player['conference_rank'] == 1
    assert top_player['division_rank'] == 1


def test_add_all_rankings_empty_input():
    """Test add_all_rankings with empty input."""
    ranked = add_all_rankings([], 'yards', ascending=False)
    assert ranked == []


def test_add_all_rankings_ascending():
    """Test add_all_rankings with ascending order (for INTs)."""
    stats = [
        {'player_id': 1, 'team_id': 1, 'interceptions': 15},   # AFC Buffalo
        {'player_id': 2, 'team_id': 2, 'interceptions': 8},    # AFC Miami
        {'player_id': 3, 'team_id': 17, 'interceptions': 12},  # NFC Dallas
        {'player_id': 4, 'team_id': 19, 'interceptions': 6},   # NFC Philadelphia
    ]

    ranked = add_all_rankings(stats, 'interceptions', ascending=True)

    # Player with 6 INTs should be rank 1
    best_player = [p for p in ranked if p['interceptions'] == 6][0]
    assert best_player['league_rank'] == 1
    assert best_player['conference_rank'] == 1
    assert best_player['division_rank'] == 1

    # Player with 15 INTs should be rank 4
    worst_player = [p for p in ranked if p['interceptions'] == 15][0]
    assert worst_player['league_rank'] == 4


# Edge Cases
def test_ranking_with_zero_stats():
    """Test ranking with zero stats."""
    stats = [
        {'player_id': 1, 'yards': 5000},
        {'player_id': 2, 'yards': 0},
        {'player_id': 3, 'yards': 4500},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # Zero yards should be ranked last
    assert ranked[-1]['yards'] == 0
    assert ranked[-1]['league_rank'] == 3


def test_ranking_with_negative_stats():
    """Test ranking with negative stats (e.g., rushing yards with sacks)."""
    stats = [
        {'player_id': 1, 'yards': 100},
        {'player_id': 2, 'yards': -50},
        {'player_id': 3, 'yards': 50},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # Negative yards should be ranked last
    assert ranked[-1]['yards'] == -50
    assert ranked[-1]['league_rank'] == 3

    # Highest positive yards should be ranked first
    assert ranked[0]['yards'] == 100
    assert ranked[0]['league_rank'] == 1


def test_multiple_tie_scenarios():
    """Test complex tie scenarios."""
    stats = [
        {'player_id': 1, 'yards': 5000},
        {'player_id': 2, 'yards': 4500},
        {'player_id': 3, 'yards': 4500},
        {'player_id': 4, 'yards': 4500},  # Three-way tie
        {'player_id': 5, 'yards': 4000},
        {'player_id': 6, 'yards': 4000},  # Two-way tie
        {'player_id': 7, 'yards': 3500},
    ]

    ranked = calculate_rankings(stats, 'yards', ascending=False)

    # 5000 yards: rank 1
    assert ranked[0]['league_rank'] == 1

    # 4500 yards (3-way tie): all rank 2
    assert ranked[1]['league_rank'] == 2
    assert ranked[2]['league_rank'] == 2
    assert ranked[3]['league_rank'] == 2

    # 4000 yards (2-way tie): all rank 5 (skips 3, 4)
    assert ranked[4]['league_rank'] == 5
    assert ranked[5]['league_rank'] == 5

    # 3500 yards: rank 7 (skips 6)
    assert ranked[6]['league_rank'] == 7
