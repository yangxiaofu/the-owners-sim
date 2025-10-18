"""
Unit tests for statistical data models

Tests all dataclasses for type safety, immutability, and correctness.
"""
import pytest
from statistics.models import (
    PassingStats,
    RushingStats,
    ReceivingStats,
    DefensiveStats,
    SpecialTeamsStats,
    TeamStats,
)


class TestPassingStats:
    """Test suite for PassingStats dataclass"""

    def test_passing_stats_creation(self):
        """Test basic PassingStats creation"""
        stats = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        assert stats.player_id == "QB001"
        assert stats.player_name == "Test QB"
        assert stats.team_id == 1
        assert stats.position == "QB"
        assert stats.games == 10
        assert stats.completions == 250
        assert stats.attempts == 400
        assert stats.yards == 3000
        assert stats.touchdowns == 25
        assert stats.interceptions == 10
        assert stats.completion_pct == 62.5
        assert stats.yards_per_attempt == 7.5
        assert stats.yards_per_game == 300.0
        assert stats.passer_rating == 95.5

    def test_passing_stats_optional_rankings(self):
        """Test that rankings default to None"""
        stats = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        assert stats.league_rank is None
        assert stats.conference_rank is None
        assert stats.division_rank is None

    def test_passing_stats_with_rankings(self):
        """Test PassingStats with provided rankings"""
        stats = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
            league_rank=5,
            conference_rank=3,
            division_rank=1,
        )

        assert stats.league_rank == 5
        assert stats.conference_rank == 3
        assert stats.division_rank == 1

    def test_passing_stats_immutable(self):
        """Test that PassingStats is immutable (frozen)"""
        stats = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        with pytest.raises(AttributeError):
            stats.touchdowns = 30

    def test_passing_stats_equality(self):
        """Test PassingStats equality"""
        stats1 = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        stats2 = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        assert stats1 == stats2

    def test_passing_stats_with_zero_games(self):
        """Test PassingStats with edge case values (0 games)"""
        stats = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=0,
            completions=0,
            attempts=0,
            yards=0,
            touchdowns=0,
            interceptions=0,
            completion_pct=0.0,
            yards_per_attempt=0.0,
            yards_per_game=0.0,
            passer_rating=0.0,
        )

        assert stats.games == 0
        assert stats.completions == 0
        assert stats.yards_per_game == 0.0


class TestRushingStats:
    """Test suite for RushingStats dataclass"""

    def test_rushing_stats_creation(self):
        """Test basic RushingStats creation"""
        stats = RushingStats(
            player_id="RB001",
            player_name="Test RB",
            team_id=2,
            position="RB",
            games=12,
            attempts=200,
            yards=1000,
            touchdowns=10,
            yards_per_carry=5.0,
            yards_per_game=83.33,
        )

        assert stats.player_id == "RB001"
        assert stats.player_name == "Test RB"
        assert stats.team_id == 2
        assert stats.position == "RB"
        assert stats.games == 12
        assert stats.attempts == 200
        assert stats.yards == 1000
        assert stats.touchdowns == 10
        assert stats.yards_per_carry == 5.0
        assert stats.yards_per_game == 83.33

    def test_rushing_stats_optional_rankings(self):
        """Test that rankings default to None"""
        stats = RushingStats(
            player_id="RB001",
            player_name="Test RB",
            team_id=2,
            position="RB",
            games=12,
            attempts=200,
            yards=1000,
            touchdowns=10,
            yards_per_carry=5.0,
            yards_per_game=83.33,
        )

        assert stats.league_rank is None
        assert stats.conference_rank is None
        assert stats.division_rank is None

    def test_rushing_stats_immutable(self):
        """Test that RushingStats is immutable"""
        stats = RushingStats(
            player_id="RB001",
            player_name="Test RB",
            team_id=2,
            position="RB",
            games=12,
            attempts=200,
            yards=1000,
            touchdowns=10,
            yards_per_carry=5.0,
            yards_per_game=83.33,
        )

        with pytest.raises(AttributeError):
            stats.yards = 1500

    def test_rushing_stats_negative_yards(self):
        """Test RushingStats with negative yards"""
        stats = RushingStats(
            player_id="RB001",
            player_name="Test RB",
            team_id=2,
            position="RB",
            games=5,
            attempts=50,
            yards=-10,
            touchdowns=0,
            yards_per_carry=-0.2,
            yards_per_game=-2.0,
        )

        assert stats.yards == -10
        assert stats.yards_per_carry == -0.2
        assert stats.yards_per_game == -2.0


class TestReceivingStats:
    """Test suite for ReceivingStats dataclass"""

    def test_receiving_stats_creation(self):
        """Test basic ReceivingStats creation"""
        stats = ReceivingStats(
            player_id="WR001",
            player_name="Test WR",
            team_id=3,
            position="WR",
            games=15,
            receptions=80,
            targets=120,
            yards=1200,
            touchdowns=10,
            catch_rate=66.67,
            yards_per_reception=15.0,
            yards_per_target=10.0,
            yards_per_game=80.0,
        )

        assert stats.player_id == "WR001"
        assert stats.player_name == "Test WR"
        assert stats.team_id == 3
        assert stats.position == "WR"
        assert stats.games == 15
        assert stats.receptions == 80
        assert stats.targets == 120
        assert stats.yards == 1200
        assert stats.touchdowns == 10
        assert stats.catch_rate == 66.67
        assert stats.yards_per_reception == 15.0
        assert stats.yards_per_target == 10.0
        assert stats.yards_per_game == 80.0

    def test_receiving_stats_optional_rankings(self):
        """Test that rankings default to None"""
        stats = ReceivingStats(
            player_id="WR001",
            player_name="Test WR",
            team_id=3,
            position="WR",
            games=15,
            receptions=80,
            targets=120,
            yards=1200,
            touchdowns=10,
            catch_rate=66.67,
            yards_per_reception=15.0,
            yards_per_target=10.0,
            yards_per_game=80.0,
        )

        assert stats.league_rank is None
        assert stats.conference_rank is None
        assert stats.division_rank is None

    def test_receiving_stats_with_rankings(self):
        """Test ReceivingStats with provided rankings"""
        stats = ReceivingStats(
            player_id="WR001",
            player_name="Test WR",
            team_id=3,
            position="WR",
            games=15,
            receptions=80,
            targets=120,
            yards=1200,
            touchdowns=10,
            catch_rate=66.67,
            yards_per_reception=15.0,
            yards_per_target=10.0,
            yards_per_game=80.0,
            league_rank=10,
            conference_rank=5,
            division_rank=2,
        )

        assert stats.league_rank == 10
        assert stats.conference_rank == 5
        assert stats.division_rank == 2

    def test_receiving_stats_immutable(self):
        """Test that ReceivingStats is immutable"""
        stats = ReceivingStats(
            player_id="WR001",
            player_name="Test WR",
            team_id=3,
            position="WR",
            games=15,
            receptions=80,
            targets=120,
            yards=1200,
            touchdowns=10,
            catch_rate=66.67,
            yards_per_reception=15.0,
            yards_per_target=10.0,
            yards_per_game=80.0,
        )

        with pytest.raises(AttributeError):
            stats.receptions = 100


class TestDefensiveStats:
    """Test suite for DefensiveStats dataclass"""

    def test_defensive_stats_creation(self):
        """Test basic DefensiveStats creation"""
        stats = DefensiveStats(
            player_id="LB001",
            player_name="Test LB",
            team_id=4,
            position="LB",
            games=16,
            tackles_total=120,
            sacks=8.5,
            interceptions=3,
        )

        assert stats.player_id == "LB001"
        assert stats.player_name == "Test LB"
        assert stats.team_id == 4
        assert stats.position == "LB"
        assert stats.games == 16
        assert stats.tackles_total == 120
        assert stats.sacks == 8.5
        assert stats.interceptions == 3

    def test_defensive_stats_optional_rankings(self):
        """Test that rankings default to None"""
        stats = DefensiveStats(
            player_id="LB001",
            player_name="Test LB",
            team_id=4,
            position="LB",
            games=16,
            tackles_total=120,
            sacks=8.5,
            interceptions=3,
        )

        assert stats.league_rank is None
        assert stats.conference_rank is None
        assert stats.division_rank is None

    def test_defensive_stats_immutable(self):
        """Test that DefensiveStats is immutable"""
        stats = DefensiveStats(
            player_id="LB001",
            player_name="Test LB",
            team_id=4,
            position="LB",
            games=16,
            tackles_total=120,
            sacks=8.5,
            interceptions=3,
        )

        with pytest.raises(AttributeError):
            stats.tackles_total = 150

    def test_defensive_stats_with_fractional_sacks(self):
        """Test DefensiveStats with fractional sack values"""
        stats = DefensiveStats(
            player_id="DL001",
            player_name="Test DL",
            team_id=5,
            position="DL",
            games=16,
            tackles_total=60,
            sacks=12.5,
            interceptions=0,
        )

        assert stats.sacks == 12.5


class TestSpecialTeamsStats:
    """Test suite for SpecialTeamsStats dataclass"""

    def test_special_teams_stats_creation(self):
        """Test basic SpecialTeamsStats creation"""
        stats = SpecialTeamsStats(
            player_id="K001",
            player_name="Test K",
            team_id=6,
            position="K",
            games=16,
            field_goals_made=25,
            field_goals_attempted=30,
            extra_points_made=40,
            extra_points_attempted=42,
            fg_percentage=83.33,
            xp_percentage=95.24,
        )

        assert stats.player_id == "K001"
        assert stats.player_name == "Test K"
        assert stats.team_id == 6
        assert stats.position == "K"
        assert stats.games == 16
        assert stats.field_goals_made == 25
        assert stats.field_goals_attempted == 30
        assert stats.extra_points_made == 40
        assert stats.extra_points_attempted == 42
        assert stats.fg_percentage == 83.33
        assert stats.xp_percentage == 95.24

    def test_special_teams_stats_optional_ranking(self):
        """Test that league_rank defaults to None"""
        stats = SpecialTeamsStats(
            player_id="K001",
            player_name="Test K",
            team_id=6,
            position="K",
            games=16,
            field_goals_made=25,
            field_goals_attempted=30,
            extra_points_made=40,
            extra_points_attempted=42,
            fg_percentage=83.33,
            xp_percentage=95.24,
        )

        assert stats.league_rank is None

    def test_special_teams_stats_immutable(self):
        """Test that SpecialTeamsStats is immutable"""
        stats = SpecialTeamsStats(
            player_id="K001",
            player_name="Test K",
            team_id=6,
            position="K",
            games=16,
            field_goals_made=25,
            field_goals_attempted=30,
            extra_points_made=40,
            extra_points_attempted=42,
            fg_percentage=83.33,
            xp_percentage=95.24,
        )

        with pytest.raises(AttributeError):
            stats.field_goals_made = 30

    def test_special_teams_stats_perfect_kicker(self):
        """Test SpecialTeamsStats with 100% accuracy"""
        stats = SpecialTeamsStats(
            player_id="K001",
            player_name="Perfect K",
            team_id=6,
            position="K",
            games=16,
            field_goals_made=30,
            field_goals_attempted=30,
            extra_points_made=50,
            extra_points_attempted=50,
            fg_percentage=100.0,
            xp_percentage=100.0,
        )

        assert stats.fg_percentage == 100.0
        assert stats.xp_percentage == 100.0


class TestTeamStats:
    """Test suite for TeamStats dataclass"""

    def test_team_stats_creation(self):
        """Test basic TeamStats creation"""
        stats = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        assert stats.team_id == 7
        assert stats.season == 2024
        assert stats.dynasty_id == "test_dynasty"
        assert stats.total_passing_yards == 4500
        assert stats.total_rushing_yards == 2000
        assert stats.total_points == 450
        assert stats.total_points_allowed == 320
        assert stats.total_yards_allowed == 5000

    def test_team_stats_optional_rankings(self):
        """Test that rankings default to None"""
        stats = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        assert stats.offensive_rank is None
        assert stats.defensive_rank is None

    def test_team_stats_with_rankings(self):
        """Test TeamStats with provided rankings"""
        stats = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
            offensive_rank=5,
            defensive_rank=12,
        )

        assert stats.offensive_rank == 5
        assert stats.defensive_rank == 12

    def test_team_stats_immutable(self):
        """Test that TeamStats is immutable"""
        stats = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        with pytest.raises(AttributeError):
            stats.total_points = 500

    def test_team_stats_equality(self):
        """Test TeamStats equality"""
        stats1 = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        stats2 = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        assert stats1 == stats2

    def test_team_stats_string_representation(self):
        """Test TeamStats string representation"""
        stats = TeamStats(
            team_id=7,
            season=2024,
            dynasty_id="test_dynasty",
            total_passing_yards=4500,
            total_rushing_yards=2000,
            total_points=450,
            total_points_allowed=320,
            total_yards_allowed=5000,
        )

        str_repr = str(stats)
        assert "team_id=7" in str_repr
        assert "season=2024" in str_repr
        assert "dynasty_id='test_dynasty'" in str_repr


class TestEdgeCases:
    """Test edge cases across all models"""

    def test_all_stats_with_zero_values(self):
        """Test all stats models with zero values"""
        passing = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=0,
            completions=0,
            attempts=0,
            yards=0,
            touchdowns=0,
            interceptions=0,
            completion_pct=0.0,
            yards_per_attempt=0.0,
            yards_per_game=0.0,
            passer_rating=0.0,
        )

        rushing = RushingStats(
            player_id="RB001",
            player_name="Test RB",
            team_id=1,
            position="RB",
            games=0,
            attempts=0,
            yards=0,
            touchdowns=0,
            yards_per_carry=0.0,
            yards_per_game=0.0,
        )

        receiving = ReceivingStats(
            player_id="WR001",
            player_name="Test WR",
            team_id=1,
            position="WR",
            games=0,
            receptions=0,
            targets=0,
            yards=0,
            touchdowns=0,
            catch_rate=0.0,
            yards_per_reception=0.0,
            yards_per_target=0.0,
            yards_per_game=0.0,
        )

        assert passing.games == 0
        assert rushing.attempts == 0
        assert receiving.receptions == 0

    def test_inequality_between_different_stats(self):
        """Test that different stats objects are not equal"""
        passing = PassingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            completions=250,
            attempts=400,
            yards=3000,
            touchdowns=25,
            interceptions=10,
            completion_pct=62.5,
            yards_per_attempt=7.5,
            yards_per_game=300.0,
            passer_rating=95.5,
        )

        rushing = RushingStats(
            player_id="QB001",
            player_name="Test QB",
            team_id=1,
            position="QB",
            games=10,
            attempts=50,
            yards=200,
            touchdowns=2,
            yards_per_carry=4.0,
            yards_per_game=20.0,
        )

        assert passing != rushing
