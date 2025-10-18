"""
Unit tests for statistical filtering utilities.

Tests all filtering methods with various scenarios including:
- Conference filtering (AFC vs NFC)
- Division filtering (East, North, South, West)
- Combined conference+division filtering
- Team filtering
- Position filtering (single and multiple)
- Minimum stat filtering
- Games played filtering
- Edge cases and error handling
"""
import pytest
from typing import List, Dict, Any

from statistics.filters import StatFilters


# Mock player data fixtures
@pytest.fixture
def mock_afc_east_players() -> List[Dict[str, Any]]:
    """Mock players from AFC East teams"""
    return [
        # Buffalo Bills (team_id=1)
        {
            'player_id': 'BUF_QB1',
            'player_name': 'Josh Allen',
            'team_id': 1,
            'position': 'QB',
            'games': 17,
            'attempts': 450,
            'completions': 300,
            'yards': 4200,
            'touchdowns': 35,
            'interceptions': 10
        },
        {
            'player_id': 'BUF_RB1',
            'player_name': 'James Cook',
            'team_id': 1,
            'position': 'RB',
            'games': 16,
            'attempts': 250,
            'yards': 1100,
            'touchdowns': 8
        },
        # Miami Dolphins (team_id=2)
        {
            'player_id': 'MIA_QB1',
            'player_name': 'Tua Tagovailoa',
            'team_id': 2,
            'position': 'QB',
            'games': 15,
            'attempts': 400,
            'completions': 280,
            'yards': 3900,
            'touchdowns': 28,
            'interceptions': 8
        },
        {
            'player_id': 'MIA_WR1',
            'player_name': 'Tyreek Hill',
            'team_id': 2,
            'position': 'WR',
            'games': 17,
            'receptions': 110,
            'targets': 150,
            'yards': 1600,
            'touchdowns': 12
        },
    ]


@pytest.fixture
def mock_nfc_north_players() -> List[Dict[str, Any]]:
    """Mock players from NFC North teams"""
    return [
        # Detroit Lions (team_id=22)
        {
            'player_id': 'DET_QB1',
            'player_name': 'Jared Goff',
            'team_id': 22,
            'position': 'QB',
            'games': 17,
            'attempts': 480,
            'completions': 340,
            'yards': 4500,
            'touchdowns': 38,
            'interceptions': 9
        },
        {
            'player_id': 'DET_RB1',
            'player_name': 'David Montgomery',
            'team_id': 22,
            'position': 'RB',
            'games': 14,
            'attempts': 200,
            'yards': 850,
            'touchdowns': 6
        },
        # Chicago Bears (team_id=21)
        {
            'player_id': 'CHI_QB1',
            'player_name': 'Justin Fields',
            'team_id': 21,
            'position': 'QB',
            'games': 12,
            'attempts': 300,
            'completions': 180,
            'yards': 2500,
            'touchdowns': 15,
            'interceptions': 8
        },
    ]


@pytest.fixture
def mock_afc_west_players() -> List[Dict[str, Any]]:
    """Mock players from AFC West teams"""
    return [
        # Kansas City Chiefs (team_id=14)
        {
            'player_id': 'KC_QB1',
            'player_name': 'Patrick Mahomes',
            'team_id': 14,
            'position': 'QB',
            'games': 17,
            'attempts': 500,
            'completions': 350,
            'yards': 4800,
            'touchdowns': 40,
            'interceptions': 12
        },
        {
            'player_id': 'KC_TE1',
            'player_name': 'Travis Kelce',
            'team_id': 14,
            'position': 'TE',
            'games': 17,
            'receptions': 95,
            'targets': 130,
            'yards': 1200,
            'touchdowns': 9
        },
    ]


@pytest.fixture
def mock_nfc_east_players() -> List[Dict[str, Any]]:
    """Mock players from NFC East teams"""
    return [
        # Philadelphia Eagles (team_id=19)
        {
            'player_id': 'PHI_QB1',
            'player_name': 'Jalen Hurts',
            'team_id': 19,
            'position': 'QB',
            'games': 16,
            'attempts': 420,
            'completions': 290,
            'yards': 4000,
            'touchdowns': 32,
            'interceptions': 7
        },
    ]


@pytest.fixture
def all_mock_players(mock_afc_east_players, mock_nfc_north_players,
                     mock_afc_west_players, mock_nfc_east_players) -> List[Dict[str, Any]]:
    """Combined fixture with players from all conferences and divisions"""
    return (mock_afc_east_players + mock_nfc_north_players +
            mock_afc_west_players + mock_nfc_east_players)


# Conference filtering tests
class TestConferenceFiltering:
    """Tests for filter_by_conference"""

    def test_filter_afc_teams(self, all_mock_players):
        """Test filtering AFC teams"""
        result = StatFilters.filter_by_conference(all_mock_players, 'AFC')

        # Should have Buffalo, Miami, and Kansas City players
        assert len(result) == 6
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {1, 2, 14}  # BUF, MIA, KC

    def test_filter_nfc_teams(self, all_mock_players):
        """Test filtering NFC teams"""
        result = StatFilters.filter_by_conference(all_mock_players, 'NFC')

        # Should have Detroit, Chicago, and Philadelphia players
        assert len(result) == 4
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {22, 21, 19}  # DET, CHI, PHI

    def test_conference_case_insensitive(self, all_mock_players):
        """Test that conference filtering is case-insensitive"""
        result_upper = StatFilters.filter_by_conference(all_mock_players, 'AFC')
        result_lower = StatFilters.filter_by_conference(all_mock_players, 'afc')
        result_mixed = StatFilters.filter_by_conference(all_mock_players, 'AfC')

        assert len(result_upper) == len(result_lower) == len(result_mixed)

    def test_conference_invalid_conference(self, all_mock_players):
        """Test that invalid conference raises ValueError"""
        with pytest.raises(ValueError, match="Invalid conference"):
            StatFilters.filter_by_conference(all_mock_players, 'XFL')

    def test_conference_empty_list(self):
        """Test filtering empty list returns empty list"""
        result = StatFilters.filter_by_conference([], 'AFC')
        assert result == []

    def test_conference_missing_team_id(self):
        """Test filtering with missing team_id field"""
        stats = [{'player_name': 'Test', 'position': 'QB'}]
        result = StatFilters.filter_by_conference(stats, 'AFC')
        assert result == []


# Division filtering tests
class TestDivisionFiltering:
    """Tests for filter_by_division"""

    def test_filter_east_division(self, all_mock_players):
        """Test filtering East division teams"""
        result = StatFilters.filter_by_division(all_mock_players, 'East')

        # Should have AFC East (BUF, MIA) and NFC East (PHI) players
        assert len(result) == 5
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {1, 2, 19}  # BUF, MIA, PHI

    def test_filter_north_division(self, all_mock_players):
        """Test filtering North division teams"""
        result = StatFilters.filter_by_division(all_mock_players, 'North')

        # Should have NFC North (DET, CHI) players only
        assert len(result) == 3
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {22, 21}  # DET, CHI

    def test_filter_west_division(self, all_mock_players):
        """Test filtering West division teams"""
        result = StatFilters.filter_by_division(all_mock_players, 'West')

        # Should have AFC West (KC) players
        assert len(result) == 2
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {14}  # KC

    def test_division_case_insensitive(self, all_mock_players):
        """Test that division filtering is case-insensitive"""
        result_upper = StatFilters.filter_by_division(all_mock_players, 'EAST')
        result_lower = StatFilters.filter_by_division(all_mock_players, 'east')
        result_mixed = StatFilters.filter_by_division(all_mock_players, 'EaSt')

        assert len(result_upper) == len(result_lower) == len(result_mixed)

    def test_division_invalid_division(self, all_mock_players):
        """Test that invalid division raises ValueError"""
        with pytest.raises(ValueError, match="Invalid division"):
            StatFilters.filter_by_division(all_mock_players, 'Central')

    def test_division_empty_list(self):
        """Test filtering empty list returns empty list"""
        result = StatFilters.filter_by_division([], 'East')
        assert result == []


# Conference + Division filtering tests
class TestConferenceDivisionFiltering:
    """Tests for filter_by_conference_division"""

    def test_filter_afc_east(self, all_mock_players):
        """Test filtering AFC East teams"""
        result = StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'East')

        # Should have only BUF and MIA players
        assert len(result) == 4
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {1, 2}  # BUF, MIA

    def test_filter_nfc_north(self, all_mock_players):
        """Test filtering NFC North teams"""
        result = StatFilters.filter_by_conference_division(all_mock_players, 'NFC', 'North')

        # Should have only DET and CHI players
        assert len(result) == 3
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {22, 21}  # DET, CHI

    def test_filter_afc_west(self, all_mock_players):
        """Test filtering AFC West teams"""
        result = StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'West')

        # Should have only KC players
        assert len(result) == 2
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {14}  # KC

    def test_filter_nfc_east(self, all_mock_players):
        """Test filtering NFC East teams"""
        result = StatFilters.filter_by_conference_division(all_mock_players, 'NFC', 'East')

        # Should have only PHI players
        assert len(result) == 1
        team_ids = {p['team_id'] for p in result}
        assert team_ids == {19}  # PHI

    def test_conference_division_case_insensitive(self, all_mock_players):
        """Test that combined filtering is case-insensitive"""
        result1 = StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'East')
        result2 = StatFilters.filter_by_conference_division(all_mock_players, 'afc', 'east')
        result3 = StatFilters.filter_by_conference_division(all_mock_players, 'AfC', 'EaSt')

        assert len(result1) == len(result2) == len(result3)

    def test_conference_division_invalid_conference(self, all_mock_players):
        """Test that invalid conference raises ValueError"""
        with pytest.raises(ValueError, match="Invalid conference"):
            StatFilters.filter_by_conference_division(all_mock_players, 'XFL', 'East')

    def test_conference_division_invalid_division(self, all_mock_players):
        """Test that invalid division raises ValueError"""
        with pytest.raises(ValueError, match="Invalid division"):
            StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'Central')

    def test_conference_division_empty_result(self, all_mock_players):
        """Test filtering that returns no results"""
        # AFC South doesn't exist in mock data
        result = StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'South')
        assert result == []


# Team filtering tests
class TestTeamFiltering:
    """Tests for filter_by_team"""

    def test_filter_single_team(self, all_mock_players):
        """Test filtering by single team ID"""
        result = StatFilters.filter_by_team(all_mock_players, 22)  # Detroit Lions

        assert len(result) == 2
        assert all(p['team_id'] == 22 for p in result)
        player_names = {p['player_name'] for p in result}
        assert 'Jared Goff' in player_names
        assert 'David Montgomery' in player_names

    def test_filter_multiple_players_same_team(self, all_mock_players):
        """Test team with multiple players"""
        result = StatFilters.filter_by_team(all_mock_players, 1)  # Buffalo Bills

        assert len(result) == 2
        assert all(p['team_id'] == 1 for p in result)

    def test_filter_nonexistent_team(self, all_mock_players):
        """Test filtering by nonexistent team ID"""
        result = StatFilters.filter_by_team(all_mock_players, 999)
        assert result == []

    def test_filter_team_empty_list(self):
        """Test filtering empty list by team"""
        result = StatFilters.filter_by_team([], 22)
        assert result == []


# Position filtering tests
class TestPositionFiltering:
    """Tests for filter_by_position"""

    def test_filter_single_position(self, all_mock_players):
        """Test filtering by single position"""
        result = StatFilters.filter_by_position(all_mock_players, ['QB'])

        # Should have 6 QBs (BUF, MIA, DET, CHI, KC, PHI)
        assert len(result) == 6
        assert all(p['position'] == 'QB' for p in result)

    def test_filter_multiple_positions(self, all_mock_players):
        """Test filtering by multiple positions"""
        result = StatFilters.filter_by_position(all_mock_players, ['RB', 'WR', 'TE'])

        # Should have RBs, WRs, and TEs
        assert len(result) == 4  # 2 RB, 1 WR, 1 TE
        positions = {p['position'] for p in result}
        assert positions == {'RB', 'WR', 'TE'}

    def test_filter_position_case_insensitive(self, all_mock_players):
        """Test that position filtering is case-insensitive"""
        result_upper = StatFilters.filter_by_position(all_mock_players, ['QB'])
        result_lower = StatFilters.filter_by_position(all_mock_players, ['qb'])
        result_mixed = StatFilters.filter_by_position(all_mock_players, ['Qb'])

        assert len(result_upper) == len(result_lower) == len(result_mixed)

    def test_filter_position_empty_positions(self, all_mock_players):
        """Test filtering with empty positions list"""
        result = StatFilters.filter_by_position(all_mock_players, [])
        assert result == []

    def test_filter_position_nonexistent_position(self, all_mock_players):
        """Test filtering by position that doesn't exist in data"""
        result = StatFilters.filter_by_position(all_mock_players, ['K'])
        assert result == []

    def test_filter_position_missing_field(self):
        """Test filtering with missing position field"""
        stats = [{'player_name': 'Test', 'team_id': 1}]
        result = StatFilters.filter_by_position(stats, ['QB'])
        assert result == []


# Minimum stat filtering tests
class TestMinimumFiltering:
    """Tests for filter_by_minimum"""

    def test_filter_by_attempts_minimum(self, all_mock_players):
        """Test filtering QBs by minimum attempts"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'attempts', 400)

        # Should have QBs with 400+ attempts
        assert len(result) > 0
        assert all(p.get('attempts', 0) >= 400 for p in result)

    def test_filter_by_yards_minimum(self, all_mock_players):
        """Test filtering by minimum yards"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'yards', 4000)

        # Should have players with 4000+ yards
        assert len(result) > 0
        assert all(p.get('yards', 0) >= 4000 for p in result)

    def test_filter_minimum_touchdowns(self, all_mock_players):
        """Test filtering by minimum touchdowns"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'touchdowns', 30)

        # Should have players with 30+ TDs
        assert len(result) > 0
        assert all(p.get('touchdowns', 0) >= 30 for p in result)

    def test_filter_minimum_no_matches(self, all_mock_players):
        """Test filtering with minimum that excludes all players"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'attempts', 10000)
        assert result == []

    def test_filter_minimum_missing_stat(self, all_mock_players):
        """Test filtering by stat that doesn't exist"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'nonexistent_stat', 100)
        assert result == []

    def test_filter_minimum_zero(self, all_mock_players):
        """Test filtering with zero minimum (should return all with that stat)"""
        result = StatFilters.filter_by_minimum(all_mock_players, 'attempts', 0)

        # Should return all players with 'attempts' field
        expected_count = sum(1 for p in all_mock_players if 'attempts' in p)
        assert len(result) == expected_count


# Games played filtering tests
class TestGamesPlayedFiltering:
    """Tests for filter_by_games_played"""

    def test_filter_minimum_games(self, all_mock_players):
        """Test filtering by minimum games played"""
        result = StatFilters.filter_by_games_played(all_mock_players, 16)

        # Should have players with 16+ games
        assert len(result) > 0
        assert all(p.get('games', 0) >= 16 for p in result)

    def test_filter_games_all_players(self, all_mock_players):
        """Test filtering with low minimum includes most players"""
        result = StatFilters.filter_by_games_played(all_mock_players, 1)

        # Should have all players with games >= 1
        assert len(result) == len(all_mock_players)

    def test_filter_games_strict_minimum(self, all_mock_players):
        """Test filtering with strict minimum (full season)"""
        result = StatFilters.filter_by_games_played(all_mock_players, 17)

        # Should have only players who played all 17 games
        assert len(result) > 0
        assert all(p.get('games', 0) == 17 for p in result)

    def test_filter_games_no_matches(self, all_mock_players):
        """Test filtering with unrealistic minimum"""
        result = StatFilters.filter_by_games_played(all_mock_players, 20)
        assert result == []

    def test_filter_games_empty_list(self):
        """Test filtering empty list by games"""
        result = StatFilters.filter_by_games_played([], 10)
        assert result == []

    def test_filter_games_alternative_field_name(self):
        """Test filtering with 'games_played' instead of 'games'"""
        stats = [
            {'player_name': 'Player A', 'games_played': 17},
            {'player_name': 'Player B', 'games_played': 10},
        ]
        result = StatFilters.filter_by_games_played(stats, 15)

        assert len(result) == 1
        assert result[0]['player_name'] == 'Player A'


# Combined filtering tests
class TestCombinedFiltering:
    """Tests for chaining multiple filters"""

    def test_conference_and_position(self, all_mock_players):
        """Test filtering by conference then position"""
        afc_players = StatFilters.filter_by_conference(all_mock_players, 'AFC')
        afc_qbs = StatFilters.filter_by_position(afc_players, ['QB'])

        # Should have AFC QBs only
        assert len(afc_qbs) == 3  # BUF, MIA, KC
        assert all(p['position'] == 'QB' for p in afc_qbs)
        team_ids = {p['team_id'] for p in afc_qbs}
        assert team_ids == {1, 2, 14}

    def test_division_and_minimum(self, all_mock_players):
        """Test filtering by division then minimum stat"""
        north_players = StatFilters.filter_by_division(all_mock_players, 'North')
        north_qualified = StatFilters.filter_by_minimum(north_players, 'attempts', 400)

        # Should have NFC North QBs with 400+ attempts
        assert len(north_qualified) == 1  # Only DET QB
        assert north_qualified[0]['player_name'] == 'Jared Goff'

    def test_conference_division_position_games(self, all_mock_players):
        """Test complex multi-stage filtering"""
        # AFC East QBs with 15+ games
        afc_east = StatFilters.filter_by_conference_division(all_mock_players, 'AFC', 'East')
        qbs = StatFilters.filter_by_position(afc_east, ['QB'])
        qualified = StatFilters.filter_by_games_played(qbs, 15)

        # Should have BUF and MIA QBs
        assert len(qualified) == 2
        player_names = {p['player_name'] for p in qualified}
        assert player_names == {'Josh Allen', 'Tua Tagovailoa'}
