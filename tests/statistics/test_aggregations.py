"""
Unit tests for statistical aggregation utilities.

Tests team, position, conference, and league aggregations.
"""
import pytest
from statistics.aggregations import (
    aggregate_team_stats,
    aggregate_position_stats,
    aggregate_conference_stats,
    calculate_league_averages,
    aggregate_all_teams,
    compare_teams,
)


@pytest.fixture
def mock_player_stats():
    """Mock player stats for multiple teams, positions, and players."""
    return [
        # Team 1 (Buffalo Bills - AFC East)
        {
            'player_id': 1,
            'team_id': 1,
            'position': 'QB',
            'passing_yards': 4500,
            'passing_touchdowns': 35,
            'rushing_yards': 250,
            'rushing_touchdowns': 3,
            'receiving_yards': 0,
            'receiving_touchdowns': 0,
            'games': 17,
        },
        {
            'player_id': 2,
            'team_id': 1,
            'position': 'RB',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 1200,
            'rushing_touchdowns': 12,
            'receiving_yards': 400,
            'receiving_touchdowns': 2,
            'games': 16,
        },
        {
            'player_id': 3,
            'team_id': 1,
            'position': 'WR',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 50,
            'rushing_touchdowns': 1,
            'receiving_yards': 1400,
            'receiving_touchdowns': 10,
            'games': 17,
        },
        # Team 9 (Chicago Bears - NFC North)
        {
            'player_id': 4,
            'team_id': 9,
            'position': 'QB',
            'passing_yards': 3800,
            'passing_touchdowns': 28,
            'rushing_yards': 400,
            'rushing_touchdowns': 5,
            'receiving_yards': 0,
            'receiving_touchdowns': 0,
            'games': 16,
        },
        {
            'player_id': 5,
            'team_id': 9,
            'position': 'RB',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 1000,
            'rushing_touchdowns': 8,
            'receiving_yards': 300,
            'receiving_touchdowns': 2,
            'games': 15,
        },
        {
            'player_id': 6,
            'team_id': 9,
            'position': 'TE',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 0,
            'rushing_touchdowns': 0,
            'receiving_yards': 800,
            'receiving_touchdowns': 6,
            'games': 17,
        },
        # Team 15 (Kansas City Chiefs - AFC West)
        {
            'player_id': 7,
            'team_id': 15,
            'position': 'QB',
            'passing_yards': 4800,
            'passing_touchdowns': 40,
            'rushing_yards': 200,
            'rushing_touchdowns': 2,
            'receiving_yards': 0,
            'receiving_touchdowns': 0,
            'games': 17,
        },
        {
            'player_id': 8,
            'team_id': 15,
            'position': 'WR',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 30,
            'rushing_touchdowns': 0,
            'receiving_yards': 1300,
            'receiving_touchdowns': 12,
            'games': 17,
        },
        # Team 22 (Detroit Lions - NFC North)
        {
            'player_id': 9,
            'team_id': 22,
            'position': 'QB',
            'passing_yards': 4200,
            'passing_touchdowns': 32,
            'rushing_yards': 150,
            'rushing_touchdowns': 1,
            'receiving_yards': 0,
            'receiving_touchdowns': 0,
            'games': 16,
        },
        {
            'player_id': 10,
            'team_id': 22,
            'position': 'RB',
            'passing_yards': 0,
            'passing_touchdowns': 0,
            'rushing_yards': 1500,
            'rushing_touchdowns': 15,
            'receiving_yards': 500,
            'receiving_touchdowns': 3,
            'games': 17,
        },
    ]


@pytest.fixture
def empty_player_stats():
    """Empty player stats list."""
    return []


class TestAggregateTeamStats:
    """Test team aggregation."""

    def test_single_team_aggregation(self, mock_player_stats):
        """Test aggregating stats for a single team."""
        result = aggregate_team_stats(mock_player_stats, team_id=1)

        assert result['team_id'] == 1
        assert result['total_passing_yards'] == 4500
        assert result['total_passing_tds'] == 35
        assert result['total_rushing_yards'] == 1500  # 250 + 1200 + 50
        assert result['total_rushing_tds'] == 16  # 3 + 12 + 1
        assert result['total_receiving_yards'] == 1800  # 0 + 400 + 1400
        assert result['total_receiving_tds'] == 12  # 0 + 2 + 10
        assert result['total_points_scored'] == (35 + 16 + 12) * 6  # 378 points
        assert result['player_count'] == 3
        assert result['games'] == 17  # Max games

    def test_team_with_no_players(self, mock_player_stats):
        """Test aggregating stats for a team with no players."""
        result = aggregate_team_stats(mock_player_stats, team_id=32)

        assert result['team_id'] == 32
        assert result['total_passing_yards'] == 0
        assert result['total_passing_tds'] == 0
        assert result['total_rushing_yards'] == 0
        assert result['total_rushing_tds'] == 0
        assert result['total_receiving_yards'] == 0
        assert result['total_receiving_tds'] == 0
        assert result['total_points_scored'] == 0
        assert result['player_count'] == 0
        assert result['games'] == 0

    def test_empty_stats_list(self, empty_player_stats):
        """Test aggregating with empty stats list."""
        result = aggregate_team_stats(empty_player_stats, team_id=1)

        assert result['team_id'] == 1
        assert result['player_count'] == 0
        assert result['total_passing_yards'] == 0


class TestAggregatePositionStats:
    """Test position aggregation."""

    def test_qb_position_aggregation(self, mock_player_stats):
        """Test aggregating QB stats."""
        result = aggregate_position_stats(mock_player_stats, position='QB')

        assert result['position'] == 'QB'
        assert result['player_count'] == 4  # 4 QBs
        assert result['total_yards'] == 4500 + 250 + 3800 + 400 + 4800 + 200 + 4200 + 150  # 18300
        assert result['total_touchdowns'] == 35 + 3 + 28 + 5 + 40 + 2 + 32 + 1  # 146
        assert result['avg_yards_per_player'] == 18300 / 4
        assert result['avg_tds_per_player'] == 146 / 4

    def test_rb_position_aggregation(self, mock_player_stats):
        """Test aggregating RB stats."""
        result = aggregate_position_stats(mock_player_stats, position='RB')

        assert result['position'] == 'RB'
        assert result['player_count'] == 3  # 3 RBs
        # Total yards: (1200 + 400) + (1000 + 300) + (1500 + 500) = 4900
        assert result['total_yards'] == 4900
        # Total TDs: (12 + 2) + (8 + 2) + (15 + 3) = 42
        assert result['total_touchdowns'] == 42
        assert result['avg_yards_per_player'] == pytest.approx(4900 / 3)
        assert result['avg_tds_per_player'] == 42 / 3

    def test_wr_position_aggregation(self, mock_player_stats):
        """Test aggregating WR stats."""
        result = aggregate_position_stats(mock_player_stats, position='WR')

        assert result['position'] == 'WR'
        assert result['player_count'] == 2  # 2 WRs
        # Total yards: (50 + 1400) + (30 + 1300) = 2780
        assert result['total_yards'] == 2780
        # Total TDs: (1 + 10) + (0 + 12) = 23
        assert result['total_touchdowns'] == 23

    def test_te_position_aggregation(self, mock_player_stats):
        """Test aggregating TE stats."""
        result = aggregate_position_stats(mock_player_stats, position='TE')

        assert result['position'] == 'TE'
        assert result['player_count'] == 1  # 1 TE
        assert result['total_yards'] == 800
        assert result['total_touchdowns'] == 6

    def test_position_with_no_players(self, mock_player_stats):
        """Test aggregating position with no players."""
        result = aggregate_position_stats(mock_player_stats, position='K')

        assert result['position'] == 'K'
        assert result['player_count'] == 0
        assert result['total_yards'] == 0
        assert result['total_touchdowns'] == 0
        assert result['avg_yards_per_player'] == 0.0
        assert result['avg_tds_per_player'] == 0.0

    def test_empty_stats_list(self, empty_player_stats):
        """Test aggregating position with empty stats list."""
        result = aggregate_position_stats(empty_player_stats, position='QB')

        assert result['player_count'] == 0


class TestAggregateConferenceStats:
    """Test conference aggregation."""

    def test_afc_aggregation(self, mock_player_stats):
        """Test aggregating AFC stats."""
        result = aggregate_conference_stats(mock_player_stats, conference='AFC')

        assert result['conference'] == 'AFC'
        # AFC teams: 1 (Buffalo), 9 (Houston), 15 (Las Vegas)
        assert result['player_count'] == 8  # 3 from Buffalo + 3 from Houston + 2 from Las Vegas
        # Passing yards: 4500 + 3800 + 4800 = 13100
        assert result['total_passing_yards'] == 13100
        # Rushing yards: 250 + 1200 + 50 + 400 + 1000 + 0 + 200 + 30 = 3130
        assert result['total_rushing_yards'] == 3130
        # Receiving yards: 0 + 400 + 1400 + 0 + 300 + 800 + 0 + 1300 = 4200
        assert result['total_receiving_yards'] == 4200
        # Total TDs: (35 + 3) + (12 + 2) + (1 + 10) + (28 + 5) + (8 + 2) + (0 + 6) + (40 + 2) + (0 + 12) = 166
        assert result['total_touchdowns'] == 166

    def test_nfc_aggregation(self, mock_player_stats):
        """Test aggregating NFC stats."""
        result = aggregate_conference_stats(mock_player_stats, conference='NFC')

        assert result['conference'] == 'NFC'
        # NFC teams: 22 (Detroit)
        assert result['player_count'] == 2  # 2 from Detroit
        # Passing yards: 4200
        assert result['total_passing_yards'] == 4200
        # Rushing yards: 150 + 1500 = 1650
        assert result['total_rushing_yards'] == 1650
        # Receiving yards: 0 + 500 = 500
        assert result['total_receiving_yards'] == 500
        # Total TDs: (32 + 1) + (15 + 3) = 51
        assert result['total_touchdowns'] == 51

    def test_conference_with_no_players(self):
        """Test aggregating conference with no matching players."""
        # Create stats with no valid team_id
        invalid_stats = [
            {'player_id': 1, 'team_id': None, 'position': 'QB', 'passing_yards': 1000}
        ]
        result = aggregate_conference_stats(invalid_stats, conference='AFC')

        assert result['conference'] == 'AFC'
        assert result['player_count'] == 0

    def test_empty_stats_list(self, empty_player_stats):
        """Test aggregating conference with empty stats list."""
        result = aggregate_conference_stats(empty_player_stats, conference='AFC')

        assert result['player_count'] == 0


class TestCalculateLeagueAverages:
    """Test league average calculations."""

    def test_league_averages(self, mock_player_stats):
        """Test calculating league-wide averages."""
        result = calculate_league_averages(mock_player_stats)

        # 10 players total
        total_passing = 4500 + 3800 + 4800 + 4200  # 17300
        total_rushing = 250 + 1200 + 50 + 400 + 1000 + 200 + 30 + 150 + 1500  # 4780
        total_receiving = 400 + 1400 + 300 + 800 + 1300 + 500  # 4700
        total_tds = (35 + 3) + (12 + 2 + 1 + 10) + (28 + 5) + (8 + 2 + 6) + (40 + 2) + (12) + (32 + 1) + (15 + 3)  # 217
        total_games = 17 + 16 + 17 + 16 + 15 + 17 + 17 + 17 + 16 + 17  # 165

        assert result['avg_passing_yards'] == total_passing / 10
        assert result['avg_rushing_yards'] == total_rushing / 10
        assert result['avg_receiving_yards'] == total_receiving / 10
        assert result['avg_touchdowns'] == total_tds / 10
        assert result['avg_games_played'] == total_games / 10

    def test_empty_stats_list(self, empty_player_stats):
        """Test calculating averages with empty stats list."""
        result = calculate_league_averages(empty_player_stats)

        assert result['avg_passing_yards'] == 0.0
        assert result['avg_rushing_yards'] == 0.0
        assert result['avg_receiving_yards'] == 0.0
        assert result['avg_touchdowns'] == 0.0
        assert result['avg_games_played'] == 0.0


class TestAggregateAllTeams:
    """Test aggregating all 32 teams."""

    def test_all_teams_aggregation(self, mock_player_stats):
        """Test aggregating all 32 NFL teams."""
        result = aggregate_all_teams(mock_player_stats)

        assert len(result) == 32
        assert all(team['team_id'] == i + 1 for i, team in enumerate(result))

        # Check team 1 (Buffalo)
        team_1 = result[0]
        assert team_1['team_id'] == 1
        assert team_1['player_count'] == 3
        assert team_1['total_passing_yards'] == 4500

        # Check team 9 (Chicago)
        team_9 = result[8]
        assert team_9['team_id'] == 9
        assert team_9['player_count'] == 3

        # Check team 32 (should be empty)
        team_32 = result[31]
        assert team_32['team_id'] == 32
        assert team_32['player_count'] == 0

    def test_all_teams_with_empty_stats(self, empty_player_stats):
        """Test aggregating all teams with empty stats."""
        result = aggregate_all_teams(empty_player_stats)

        assert len(result) == 32
        assert all(team['player_count'] == 0 for team in result)


class TestCompareTeams:
    """Test team comparison."""

    def test_compare_two_teams(self, mock_player_stats):
        """Test comparing two teams."""
        result = compare_teams(mock_player_stats, team_id_1=1, team_id_2=9)

        # Team 1
        assert result['team_1']['team_id'] == 1
        assert result['team_1']['total_passing_yards'] == 4500

        # Team 2
        assert result['team_2']['team_id'] == 9
        assert result['team_2']['total_passing_yards'] == 3800

        # Differences (team_1 - team_2)
        assert result['differences']['total_passing_yards'] == 700  # 4500 - 3800
        assert result['differences']['player_count'] == 0  # 3 - 3

    def test_compare_team_with_empty_team(self, mock_player_stats):
        """Test comparing a team with stats to an empty team."""
        result = compare_teams(mock_player_stats, team_id_1=1, team_id_2=32)

        assert result['team_1']['player_count'] == 3
        assert result['team_2']['player_count'] == 0
        assert result['differences']['player_count'] == 3

    def test_compare_empty_teams(self, empty_player_stats):
        """Test comparing two teams with no stats."""
        result = compare_teams(empty_player_stats, team_id_1=1, team_id_2=2)

        assert result['team_1']['player_count'] == 0
        assert result['team_2']['player_count'] == 0
        assert result['differences']['total_passing_yards'] == 0

    def test_compare_same_team(self, mock_player_stats):
        """Test comparing a team with itself."""
        result = compare_teams(mock_player_stats, team_id_1=1, team_id_2=1)

        assert result['team_1']['team_id'] == 1
        assert result['team_2']['team_id'] == 1
        # All differences should be 0
        assert all(diff == 0 for diff in result['differences'].values())


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_stat_fields(self):
        """Test handling missing stat fields."""
        incomplete_stats = [
            {'player_id': 1, 'team_id': 1, 'position': 'QB', 'passing_yards': 1000},
            {'player_id': 2, 'team_id': 1, 'position': 'RB'},
        ]

        result = aggregate_team_stats(incomplete_stats, team_id=1)
        assert result['total_passing_yards'] == 1000
        assert result['total_rushing_yards'] == 0  # Missing field defaults to 0

    def test_zero_values(self):
        """Test handling zero values."""
        zero_stats = [
            {
                'player_id': 1,
                'team_id': 1,
                'position': 'QB',
                'passing_yards': 0,
                'passing_touchdowns': 0,
                'rushing_yards': 0,
                'rushing_touchdowns': 0,
                'receiving_yards': 0,
                'receiving_touchdowns': 0,
                'games': 0,
            }
        ]

        result = aggregate_team_stats(zero_stats, team_id=1)
        assert result['player_count'] == 1
        assert result['total_points_scored'] == 0

    def test_large_numbers(self):
        """Test handling large stat values."""
        large_stats = [
            {
                'player_id': 1,
                'team_id': 1,
                'position': 'QB',
                'passing_yards': 10000,
                'passing_touchdowns': 100,
                'rushing_yards': 5000,
                'rushing_touchdowns': 50,
                'receiving_yards': 0,
                'receiving_touchdowns': 0,
                'games': 50,
            }
        ]

        result = aggregate_team_stats(large_stats, team_id=1)
        assert result['total_passing_yards'] == 10000
        assert result['total_passing_tds'] == 100
        assert result['total_points_scored'] == (100 + 50) * 6  # 900 points
