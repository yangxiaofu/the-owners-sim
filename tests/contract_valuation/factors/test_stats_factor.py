"""
Unit tests for StatsFactor.

Tests NFL benchmark comparisons and percentile calculations.
"""

import pytest

from contract_valuation.factors.stats_factor import StatsFactor
from contract_valuation.context import ValuationContext


class TestStatsFactor:
    """Tests for StatsFactor valuation."""

    @pytest.fixture
    def factor(self):
        """StatsFactor instance."""
        return StatsFactor()

    def test_elite_qb_stats(self, factor, default_context, sample_qb_data):
        """Test 280+ yards, 2+ TDs returns quality/elite percentile."""
        result = factor.calculate(sample_qb_data, default_context)

        assert result.name == "stats_based"
        # Per-game: 4500/17 = 265 yards, 35/17 = 2.06 TDs
        # High interceptions (10) bring down composite
        assert result.breakdown["composite_percentile"] >= 70
        assert result.breakdown["tier"] in ["quality", "elite"]

    def test_average_rb_stats(self, factor, default_context, sample_rb_data):
        """Test 70 yards, 4.3 YPC returns ~50th percentile."""
        result = factor.calculate(sample_rb_data, default_context)

        # Per-game: 1100/16 = 68.75 yards, 4.5 YPC
        percentiles = result.breakdown["percentiles"]

        # Should be around average for rushing yards
        assert "rushing_yards" in percentiles
        assert 40 <= percentiles["rushing_yards"] <= 65

    def test_below_average_wr_stats(self, factor, default_context, backup_player_data):
        """Test 40 yards, 3 receptions returns low AAV."""
        result = factor.calculate(backup_player_data, default_context)

        # Per-game: 180/14 = 12.9 yards, 15/14 = 1.07 receptions
        assert result.breakdown["tier"] == "backup"
        # Backup WR interpolated from 2M floor to 8M starter ceiling
        assert result.raw_value <= 8_000_000

    def test_inverted_stat_interceptions(self, factor, default_context):
        """Test high INTs correctly penalize QB."""
        high_int_qb = {
            "player_id": 100,
            "name": "Turnover Machine",
            "position": "QB",
            "overall_rating": 80,
            "stats": {
                "passing_yards": 3500,
                "passing_tds": 20,
                "completion_pct": 62,
                "passer_rating": 82,
                "interceptions": 20,  # Very high
            },
            "games_played": 16,
        }

        low_int_qb = {
            "player_id": 101,
            "name": "Ball Security",
            "position": "QB",
            "overall_rating": 80,
            "stats": {
                "passing_yards": 3500,
                "passing_tds": 20,
                "completion_pct": 62,
                "passer_rating": 82,
                "interceptions": 5,  # Very low
            },
            "games_played": 16,
        }

        high_result = factor.calculate(high_int_qb, default_context)
        low_result = factor.calculate(low_int_qb, default_context)

        # Low INT QB should have higher interceptions percentile
        assert low_result.breakdown["percentiles"]["interceptions"] > high_result.breakdown["percentiles"]["interceptions"]
        # And higher overall value
        assert low_result.raw_value > high_result.raw_value

    def test_partial_stats_reduces_confidence(self, factor, default_context):
        """Test missing 2+ stats lowers confidence."""
        partial_stats = {
            "player_id": 100,
            "name": "Partial Stats",
            "position": "QB",
            "overall_rating": 80,
            "stats": {
                "passing_yards": 3500,
                "passing_tds": 22,
                # Missing: completion_pct, passer_rating, interceptions
            },
            "games_played": 16,
        }

        result = factor.calculate(partial_stats, default_context)

        # Missing 3 stats = -0.15 from base 0.70 + 0.16 games = 0.71
        # 0.86 - 0.15 = 0.71
        assert result.confidence <= 0.75
        assert len(result.breakdown["missing_stats"]) >= 2

    def test_games_played_affects_confidence(self, factor, default_context):
        """Test 16 games has higher confidence than 8 games."""
        full_season = {
            "player_id": 100,
            "name": "Full Season",
            "position": "RB",
            "overall_rating": 80,
            "stats": {
                "rushing_yards": 1000,
                "rushing_tds": 8,
                "yards_per_carry": 4.5,
                "receptions": 40,
                "receiving_yards": 300,
                "fumbles": 1,
            },
            "games_played": 16,
        }

        half_season = {
            "player_id": 101,
            "name": "Half Season",
            "position": "RB",
            "overall_rating": 80,
            "stats": {
                "rushing_yards": 500,
                "rushing_tds": 4,
                "yards_per_carry": 4.5,
                "receptions": 20,
                "receiving_yards": 150,
                "fumbles": 1,
            },
            "games_played": 8,
        }

        full_result = factor.calculate(full_season, default_context)
        half_result = factor.calculate(half_season, default_context)

        assert full_result.confidence > half_result.confidence

    def test_position_group_mapping(self, factor, default_context, edge_rusher_data):
        """Test LOLB maps to EDGE benchmarks."""
        result = factor.calculate(edge_rusher_data, default_context)

        assert result.breakdown["benchmark_position"] == "EDGE"
        # Should use EDGE benchmarks for sacks, tackles, etc.
        assert "sacks" in result.breakdown["percentiles"]

    def test_no_stats_returns_fallback(self, factor, default_context):
        """Test empty stats returns 0.40 confidence."""
        player_data = {
            "player_id": 100,
            "name": "No Stats",
            "position": "WR",
            "overall_rating": 75,
            "stats": {},
            "games_played": 0,
        }

        result = factor.calculate(player_data, default_context)

        assert result.confidence == 0.40
        assert result.breakdown.get("no_stats") is True
