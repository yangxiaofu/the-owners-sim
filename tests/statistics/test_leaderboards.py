"""
Integration Tests for LeaderboardBuilder

Tests leaderboard generation across all statistical categories with filters,
rankings, and dataclass conversions.
"""
import pytest
from statistics.leaderboards import LeaderboardBuilder
from statistics.models import PassingStats, RushingStats, ReceivingStats, DefensiveStats, SpecialTeamsStats
from database.api import DatabaseAPI


@pytest.fixture
def test_db_api(in_memory_db):
    """Create DatabaseAPI instance with test database connection"""
    db_api = DatabaseAPI(":memory:")
    db_api.db_connection.conn = in_memory_db  # Override with test database
    return db_api


class TestPassingLeaderboard:
    """Test passing leaderboard generation"""

    def test_basic_passing_leaderboard(self, test_db_api):
        """Test basic passing leaderboard without filters"""
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=10)

        # Verify we got results
        assert len(leaders) > 0
        assert len(leaders) <= 10

        # Verify all are PassingStats dataclasses
        for leader in leaders:
            assert isinstance(leader, PassingStats)

        # Verify sorted by passing yards descending
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards

    def test_passing_leaderboard_with_conference_filter(self, test_db_api):
        """Test passing leaderboard filtered by conference"""
        builder = LeaderboardBuilder(test_db_api)

        # Get AFC leaders
        afc_leaders = builder.build_passing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'conference': 'AFC'}
        )

        # Get NFC leaders
        nfc_leaders = builder.build_passing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'conference': 'NFC'}
        )

        # Verify we have leaders from both conferences
        assert len(afc_leaders) > 0
        assert len(nfc_leaders) > 0

        # Verify different results
        afc_teams = {leader.team_id for leader in afc_leaders}
        nfc_teams = {leader.team_id for leader in nfc_leaders}
        assert afc_teams != nfc_teams

    def test_passing_leaderboard_with_division_filter(self, test_db_api):
        """Test passing leaderboard filtered by division"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        # Get AFC East leaders
        leaders = builder.build_passing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'division': 'East'}
        )

        # Should have some leaders
        assert len(leaders) > 0

    def test_passing_leaderboard_with_min_attempts_filter(self, test_db_api):
        """Test passing leaderboard with minimum attempts filter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        # Get leaders with min 30 attempts
        leaders = builder.build_passing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'min_attempts': 30}
        )

        # Verify all have >= 30 attempts
        for leader in leaders:
            assert leader.attempts >= 30

    def test_passing_leaderboard_has_calculated_metrics(self, test_db_api):
        """Test that passing leaderboard includes all calculated metrics"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=5)

        for leader in leaders:
            # Verify passer rating is calculated
            assert leader.passer_rating >= 0.0
            assert leader.passer_rating <= 158.3

            # Verify yards per attempt
            assert leader.yards_per_attempt >= 0.0

            # Verify yards per game
            assert leader.yards_per_game >= 0.0

            # Verify completion percentage
            assert leader.completion_pct >= 0.0
            assert leader.completion_pct <= 100.0

    def test_passing_leaderboard_has_rankings(self, test_db_api):
        """Test that passing leaderboard includes rankings"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=10)

        # Verify league rankings are present
        for i, leader in enumerate(leaders):
            assert leader.league_rank is not None
            assert leader.league_rank >= 1

        # Verify first place is ranked #1
        assert leaders[0].league_rank == 1

    def test_passing_leaderboard_empty_results(self, test_db_api):
        """Test passing leaderboard with no matching data"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        # Query with impossible filter
        leaders = builder.build_passing_leaderboard(
            "nonexistent_dynasty", 2024, limit=25
        )

        # Should return empty list
        assert leaders == []

    def test_passing_leaderboard_passer_rating_accuracy(self, test_db_api, known_passer_ratings):
        """Test that calculated passer ratings match known values"""
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=25)

        # Find specific QBs and verify their ratings
        for leader in leaders:
            if leader.player_name in known_passer_ratings:
                expected_rating = known_passer_ratings[leader.player_name]
                # Allow small tolerance for rounding differences
                assert abs(leader.passer_rating - expected_rating) < 0.5, \
                    f"{leader.player_name}: Expected {expected_rating}, got {leader.passer_rating}"


class TestRushingLeaderboard:
    """Test rushing leaderboard generation"""

    def test_basic_rushing_leaderboard(self, test_db_api):
        """Test basic rushing leaderboard without filters"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=10)

        # Verify we got results
        assert len(leaders) > 0
        assert len(leaders) <= 10

        # Verify all are RushingStats dataclasses
        for leader in leaders:
            assert isinstance(leader, RushingStats)

        # Verify sorted by rushing yards descending
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards

    def test_rushing_leaderboard_with_conference_filter(self, test_db_api):
        """Test rushing leaderboard filtered by conference"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        afc_leaders = builder.build_rushing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'conference': 'AFC'}
        )

        assert len(afc_leaders) > 0
        for leader in afc_leaders:
            assert isinstance(leader, RushingStats)

    def test_rushing_leaderboard_with_position_filter(self, test_db_api):
        """Test rushing leaderboard filtered by position"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        # Get only RB leaders
        leaders = builder.build_rushing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'position': 'RB'}
        )

        # Verify all are RBs
        for leader in leaders:
            assert leader.position == 'RB'

    def test_rushing_leaderboard_has_calculated_metrics(self, test_db_api):
        """Test that rushing leaderboard includes calculated metrics"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=5)

        for leader in leaders:
            # Verify yards per carry
            if leader.attempts > 0:
                expected_ypc = leader.yards / leader.attempts
                assert abs(leader.yards_per_carry - expected_ypc) < 0.1

            # Verify yards per game
            if leader.games > 0:
                expected_ypg = leader.yards / leader.games
                assert abs(leader.yards_per_game - expected_ypg) < 0.1

    def test_rushing_leaderboard_has_rankings(self, test_db_api):
        """Test that rushing leaderboard includes rankings"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=10)

        # Verify league rankings
        for leader in leaders:
            assert leader.league_rank is not None
            assert leader.league_rank >= 1

        # First place should be #1
        assert leaders[0].league_rank == 1

    def test_rushing_leaderboard_with_min_attempts_filter(self, test_db_api):
        """Test rushing leaderboard with minimum attempts filter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'min_attempts': 15}
        )

        # Verify all have >= 15 attempts
        for leader in leaders:
            assert leader.attempts >= 15


class TestReceivingLeaderboard:
    """Test receiving leaderboard generation"""

    def test_basic_receiving_leaderboard(self, test_db_api):
        """Test basic receiving leaderboard without filters"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard("test_dynasty", 2024, limit=10)

        # Verify we got results
        assert len(leaders) > 0
        assert len(leaders) <= 10

        # Verify all are ReceivingStats dataclasses
        for leader in leaders:
            assert isinstance(leader, ReceivingStats)

        # Verify sorted by receiving yards descending
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards

    def test_receiving_leaderboard_with_conference_filter(self, test_db_api):
        """Test receiving leaderboard filtered by conference"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        nfc_leaders = builder.build_receiving_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'conference': 'NFC'}
        )

        assert len(nfc_leaders) > 0
        for leader in nfc_leaders:
            assert isinstance(leader, ReceivingStats)

    def test_receiving_leaderboard_with_position_filter(self, test_db_api):
        """Test receiving leaderboard filtered by position"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        # Get only WR leaders
        leaders = builder.build_receiving_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'position': 'WR'}
        )

        # Verify all are WRs
        for leader in leaders:
            assert leader.position == 'WR'

    def test_receiving_leaderboard_has_calculated_metrics(self, test_db_api):
        """Test that receiving leaderboard includes calculated metrics"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard("test_dynasty", 2024, limit=5)

        for leader in leaders:
            # Verify catch rate
            if leader.targets > 0:
                expected_catch_rate = (leader.receptions / leader.targets) * 100
                assert abs(leader.catch_rate - expected_catch_rate) < 0.5

            # Verify yards per reception
            if leader.receptions > 0:
                expected_ypr = leader.yards / leader.receptions
                assert abs(leader.yards_per_reception - expected_ypr) < 0.1

            # Verify yards per target
            if leader.targets > 0:
                expected_ypt = leader.yards / leader.targets
                assert abs(leader.yards_per_target - expected_ypt) < 0.1

    def test_receiving_leaderboard_has_rankings(self, test_db_api):
        """Test that receiving leaderboard includes rankings"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard("test_dynasty", 2024, limit=10)

        # Verify league rankings
        for leader in leaders:
            assert leader.league_rank is not None
            assert leader.league_rank >= 1

    def test_receiving_leaderboard_with_min_receptions_filter(self, test_db_api):
        """Test receiving leaderboard with minimum receptions filter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'min_receptions': 5}
        )

        # Verify all have >= 5 receptions
        for leader in leaders:
            assert leader.receptions >= 5


class TestDefensiveLeaderboard:
    """Test defensive leaderboard generation"""

    def test_tackles_leaderboard(self, test_db_api):
        """Test tackles leaderboard"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "tackles_total", limit=10
        )

        # Verify we got results
        assert len(leaders) > 0
        assert len(leaders) <= 10

        # Verify all are DefensiveStats dataclasses
        for leader in leaders:
            assert isinstance(leader, DefensiveStats)

        # Verify sorted by tackles descending
        for i in range(len(leaders) - 1):
            assert leaders[i].tackles_total >= leaders[i + 1].tackles_total

    def test_sacks_leaderboard(self, test_db_api):
        """Test sacks leaderboard"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "sacks", limit=10
        )

        # Verify we got results
        assert len(leaders) > 0

        # Verify sorted by sacks descending
        for i in range(len(leaders) - 1):
            assert leaders[i].sacks >= leaders[i + 1].sacks

    def test_interceptions_leaderboard(self, test_db_api):
        """Test interceptions leaderboard"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "interceptions", limit=10
        )

        # Verify we got results
        assert len(leaders) > 0

        # Verify sorted by interceptions descending
        for i in range(len(leaders) - 1):
            assert leaders[i].interceptions >= leaders[i + 1].interceptions

    def test_defensive_leaderboard_invalid_category(self, test_db_api):
        """Test defensive leaderboard with invalid stat category"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        with pytest.raises(ValueError, match="Invalid defensive stat_category"):
            builder.build_defensive_leaderboard(
                "test_dynasty", 2024, "invalid_stat", limit=10
            )

    def test_defensive_leaderboard_with_conference_filter(self, test_db_api):
        """Test defensive leaderboard filtered by conference"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "tackles_total", limit=25,
            filters={'conference': 'AFC'}
        )

        assert len(leaders) > 0

    def test_defensive_leaderboard_with_position_filter(self, test_db_api):
        """Test defensive leaderboard filtered by position"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "tackles_total", limit=25,
            filters={'position': 'LB'}
        )

        # Verify all are LBs
        for leader in leaders:
            assert leader.position == 'LB'

    def test_defensive_leaderboard_has_rankings(self, test_db_api):
        """Test that defensive leaderboard includes rankings"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard(
            "test_dynasty", 2024, "sacks", limit=10
        )

        # Verify league rankings
        for leader in leaders:
            assert leader.league_rank is not None
            assert leader.league_rank >= 1


class TestSpecialTeamsLeaderboard:
    """Test special teams leaderboard generation"""

    def test_basic_special_teams_leaderboard(self, test_db_api):
        """Test basic special teams leaderboard without filters"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_special_teams_leaderboard("test_dynasty", 2024, limit=10)

        # Verify we got results
        assert len(leaders) > 0
        assert len(leaders) <= 10

        # Verify all are SpecialTeamsStats dataclasses
        for leader in leaders:
            assert isinstance(leader, SpecialTeamsStats)

    def test_special_teams_leaderboard_has_calculated_metrics(self, test_db_api):
        """Test that special teams leaderboard includes calculated metrics"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_special_teams_leaderboard("test_dynasty", 2024, limit=5)

        for leader in leaders:
            # Verify FG percentage
            assert leader.fg_percentage >= 0.0
            assert leader.fg_percentage <= 100.0

    def test_special_teams_leaderboard_with_conference_filter(self, test_db_api):
        """Test special teams leaderboard filtered by conference"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_special_teams_leaderboard(
            "test_dynasty", 2024, limit=25, filters={'conference': 'NFC'}
        )

        assert len(leaders) > 0

    def test_special_teams_leaderboard_has_rankings(self, test_db_api):
        """Test that special teams leaderboard includes rankings"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_special_teams_leaderboard("test_dynasty", 2024, limit=10)

        # Verify league rankings
        for leader in leaders:
            assert leader.league_rank is not None
            assert leader.league_rank >= 1


class TestLeaderboardDataclassConversion:
    """Test dataclass conversion and structure"""

    def test_passing_stats_dataclass_fields(self, test_db_api):
        """Test that PassingStats dataclass has all required fields"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=1)
        if len(leaders) > 0:
            stat = leaders[0]
            # Verify all fields are present
            assert hasattr(stat, 'player_id')
            assert hasattr(stat, 'player_name')
            assert hasattr(stat, 'team_id')
            assert hasattr(stat, 'position')
            assert hasattr(stat, 'games')
            assert hasattr(stat, 'completions')
            assert hasattr(stat, 'attempts')
            assert hasattr(stat, 'yards')
            assert hasattr(stat, 'touchdowns')
            assert hasattr(stat, 'interceptions')
            assert hasattr(stat, 'completion_pct')
            assert hasattr(stat, 'yards_per_attempt')
            assert hasattr(stat, 'yards_per_game')
            assert hasattr(stat, 'passer_rating')
            assert hasattr(stat, 'league_rank')
            assert hasattr(stat, 'conference_rank')
            assert hasattr(stat, 'division_rank')

    def test_rushing_stats_dataclass_fields(self, test_db_api):
        """Test that RushingStats dataclass has all required fields"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=1)
        if len(leaders) > 0:
            stat = leaders[0]
            assert hasattr(stat, 'player_id')
            assert hasattr(stat, 'player_name')
            assert hasattr(stat, 'yards_per_carry')
            assert hasattr(stat, 'yards_per_game')
            assert hasattr(stat, 'league_rank')

    def test_receiving_stats_dataclass_fields(self, test_db_api):
        """Test that ReceivingStats dataclass has all required fields"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard("test_dynasty", 2024, limit=1)
        if len(leaders) > 0:
            stat = leaders[0]
            assert hasattr(stat, 'catch_rate')
            assert hasattr(stat, 'yards_per_reception')
            assert hasattr(stat, 'yards_per_target')
            assert hasattr(stat, 'yards_per_game')

    def test_defensive_stats_dataclass_fields(self, test_db_api):
        """Test that DefensiveStats dataclass has all required fields"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_defensive_leaderboard("test_dynasty", 2024, "tackles_total", limit=1)
        if len(leaders) > 0:
            stat = leaders[0]
            assert hasattr(stat, 'tackles_total')
            assert hasattr(stat, 'sacks')
            assert hasattr(stat, 'interceptions')
            assert hasattr(stat, 'league_rank')

    def test_special_teams_stats_dataclass_fields(self, test_db_api):
        """Test that SpecialTeamsStats dataclass has all required fields"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_special_teams_leaderboard("test_dynasty", 2024, limit=1)
        if len(leaders) > 0:
            stat = leaders[0]
            assert hasattr(stat, 'field_goals_made')
            assert hasattr(stat, 'field_goals_attempted')
            assert hasattr(stat, 'fg_percentage')
            assert hasattr(stat, 'xp_percentage')
            assert hasattr(stat, 'league_rank')


class TestLeaderboardSorting:
    """Test leaderboard sorting logic"""

    def test_passing_leaderboard_sorted_by_yards(self, test_db_api):
        """Test that passing leaderboard is sorted by yards descending"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_passing_leaderboard("test_dynasty", 2024, limit=20)

        # Verify descending order
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards

    def test_rushing_leaderboard_sorted_by_yards(self, test_db_api):
        """Test that rushing leaderboard is sorted by yards descending"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=20)

        # Verify descending order
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards

    def test_receiving_leaderboard_sorted_by_yards(self, test_db_api):
        """Test that receiving leaderboard is sorted by yards descending"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders = builder.build_receiving_leaderboard("test_dynasty", 2024, limit=20)

        # Verify descending order
        for i in range(len(leaders) - 1):
            assert leaders[i].yards >= leaders[i + 1].yards


class TestLeaderboardLimits:
    """Test leaderboard limit parameter"""

    def test_passing_leaderboard_respects_limit(self, test_db_api):
        """Test that passing leaderboard respects limit parameter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders_5 = builder.build_passing_leaderboard("test_dynasty", 2024, limit=5)
        leaders_10 = builder.build_passing_leaderboard("test_dynasty", 2024, limit=10)

        assert len(leaders_5) <= 5
        assert len(leaders_10) <= 10
        assert len(leaders_10) >= len(leaders_5)

    def test_rushing_leaderboard_respects_limit(self, test_db_api):
        """Test that rushing leaderboard respects limit parameter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders_3 = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=3)
        leaders_15 = builder.build_rushing_leaderboard("test_dynasty", 2024, limit=15)

        assert len(leaders_3) <= 3
        assert len(leaders_15) <= 15

    def test_defensive_leaderboard_respects_limit(self, test_db_api):
        """Test that defensive leaderboard respects limit parameter"""
        
        
        builder = LeaderboardBuilder(test_db_api)

        leaders_5 = builder.build_defensive_leaderboard("test_dynasty", 2024, "tackles_total", limit=5)

        assert len(leaders_5) <= 5
