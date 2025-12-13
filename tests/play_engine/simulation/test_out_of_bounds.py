"""Tests for out-of-bounds logic."""

import pytest
from src.play_engine.simulation.pass_plays import PassPlaySimulator
from team_management.players.player import Player, Position


class TestOutOfBounds:
    """Test OOB probability and determination."""

    @pytest.fixture
    def simulator(self):
        """Create PassPlaySimulator with minimal setup."""
        # Create mock players for testing
        offensive_players = [Player(name=f"Off{i}", primary_position=Position.WR) for i in range(11)]
        defensive_players = [Player(name=f"Def{i}", primary_position=Position.CB) for i in range(11)]

        return PassPlaySimulator(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_formation="singleback",
            defensive_formation="cover_2"
        )

    def test_sideline_routes_high_oob_chance(self, simulator):
        """Test sideline routes have ~35% OOB probability."""
        oob_count = 0
        trials = 100

        for _ in range(trials):
            went_oob = simulator._determine_out_of_bounds(
                concept='sideline_routes',
                yards_gained=10,
                receiver_awareness=75,
                field_position=50
            )
            if went_oob:
                oob_count += 1

        # Should be around 35% (allow 20-50% range due to variance)
        assert 20 <= oob_count <= 50

    def test_non_sideline_routes_low_oob_chance(self, simulator):
        """Test non-sideline routes have low OOB probability."""
        oob_count = 0
        trials = 100

        for _ in range(trials):
            went_oob = simulator._determine_out_of_bounds(
                concept='quick_slant',
                yards_gained=10,
                receiver_awareness=75,
                field_position=50
            )
            if went_oob:
                oob_count += 1

        # Should be around 5% (allow 0-15% range)
        assert oob_count <= 15

    def test_high_awareness_reduces_oob(self, simulator):
        """Test high awareness receivers stay inbounds more."""
        low_awareness_oob = 0
        high_awareness_oob = 0
        trials = 100

        for _ in range(trials):
            # Low awareness (60)
            if simulator._determine_out_of_bounds('sideline_routes', 10, 60, 50):
                low_awareness_oob += 1
            # High awareness (95)
            if simulator._determine_out_of_bounds('sideline_routes', 10, 95, 50):
                high_awareness_oob += 1

        # High awareness should have fewer OOB
        assert high_awareness_oob < low_awareness_oob

    def test_longer_plays_increase_oob(self, simulator):
        """Test longer plays have higher OOB chance."""
        short_oob = 0
        long_oob = 0
        trials = 100

        for _ in range(trials):
            # Short play (5 yards)
            if simulator._determine_out_of_bounds('sideline_routes', 5, 75, 50):
                short_oob += 1
            # Long play (30 yards)
            if simulator._determine_out_of_bounds('sideline_routes', 30, 75, 50):
                long_oob += 1

        # Long plays should have more OOB
        assert long_oob > short_oob

    def test_play_result_has_oob_field(self):
        """Test PlayResult includes went_out_of_bounds field."""
        from src.play_engine.core.play_result import PlayResult

        result = PlayResult(outcome="completion", went_out_of_bounds=True)
        assert result.went_out_of_bounds is True

        result2 = PlayResult(outcome="incomplete")
        assert result2.went_out_of_bounds is False  # Default