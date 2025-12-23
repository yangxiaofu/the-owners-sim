"""
Unit tests for PositionBenchmarks class.

Tests stat benchmark lookups, percentile calculations, and position mappings.
"""

import pytest

from contract_valuation.benchmarks.position_benchmarks import (
    PositionBenchmarks,
    StatBenchmark,
)


@pytest.fixture
def benchmarks():
    """PositionBenchmarks instance."""
    return PositionBenchmarks()


class TestPositionBenchmarks:
    """Tests for PositionBenchmarks class."""

    def test_all_core_positions_have_benchmarks(self, benchmarks):
        """Verify QB, RB, WR, TE, EDGE, DT, LB, CB, S, K, P have benchmarks."""
        core_positions = ["QB", "RB", "WR", "TE", "EDGE", "DT", "LB", "CB", "S", "K", "P"]

        for position in core_positions:
            assert benchmarks.has_benchmarks(position), f"{position} should have benchmarks"
            pos_benchmarks = benchmarks.get_benchmarks(position)
            assert len(pos_benchmarks) > 0, f"{position} should have at least one stat benchmark"

    def test_position_group_mapping(self, benchmarks):
        """Verify LOLB->EDGE, MLB->LB, FS->S, LT->OT mappings work."""
        # Test position group mappings
        assert benchmarks.get_mapped_position("LOLB") == "EDGE"
        assert benchmarks.get_mapped_position("ROLB") == "EDGE"
        assert benchmarks.get_mapped_position("LE") == "EDGE"
        assert benchmarks.get_mapped_position("RE") == "EDGE"
        assert benchmarks.get_mapped_position("MLB") == "LB"
        assert benchmarks.get_mapped_position("FS") == "S"
        assert benchmarks.get_mapped_position("SS") == "S"
        assert benchmarks.get_mapped_position("LT") == "OT"
        assert benchmarks.get_mapped_position("RT") == "OT"
        assert benchmarks.get_mapped_position("LG") == "OG"
        assert benchmarks.get_mapped_position("RG") == "OG"

        # Test that mapped positions get benchmarks via parent
        assert benchmarks.has_benchmarks("LOLB")
        lolb_benchmarks = benchmarks.get_benchmarks("LOLB")
        edge_benchmarks = benchmarks.get_benchmarks("EDGE")
        assert lolb_benchmarks == edge_benchmarks

    def test_percentile_calculation_normal(self, benchmarks):
        """Test average stat returns ~50th percentile."""
        # QB average passing yards per game is 210 (50th percentile)
        percentile = benchmarks.get_stat_percentile("QB", "passing_yards", 210)
        assert percentile is not None
        assert 45 <= percentile <= 55, f"Average value should be ~50th percentile, got {percentile}"

        # RB average rushing yards per game is 70
        percentile = benchmarks.get_stat_percentile("RB", "rushing_yards", 70)
        assert percentile is not None
        assert 45 <= percentile <= 55, f"Average value should be ~50th percentile, got {percentile}"

    def test_percentile_calculation_elite(self, benchmarks):
        """Test elite stat returns 90+ percentile."""
        # QB elite passing yards per game is 280+
        percentile = benchmarks.get_stat_percentile("QB", "passing_yards", 280)
        assert percentile is not None
        assert percentile >= 90, f"Elite value should be 90+ percentile, got {percentile}"

        # Even higher should approach 100
        percentile = benchmarks.get_stat_percentile("QB", "passing_yards", 320)
        assert percentile is not None
        assert percentile >= 95, f"Super-elite value should be 95+ percentile, got {percentile}"

    def test_percentile_calculation_inverted(self, benchmarks):
        """Test interceptions (lower is better) inverts correctly."""
        # QB interceptions: lower is better
        # Poor = 1.2 (25th), Average = 0.8 (50th), Elite = 0.4 (90th)

        # High interceptions (bad) should be low percentile
        percentile = benchmarks.get_stat_percentile("QB", "interceptions", 1.2)
        assert percentile is not None
        assert percentile <= 30, f"High INTs should be low percentile, got {percentile}"

        # Low interceptions (good) should be high percentile
        percentile = benchmarks.get_stat_percentile("QB", "interceptions", 0.4)
        assert percentile is not None
        assert percentile >= 85, f"Low INTs should be high percentile, got {percentile}"

        # RB fumbles also inverted
        percentile = benchmarks.get_stat_percentile("RB", "fumbles", 0.02)
        assert percentile is not None
        assert percentile >= 85, f"Low fumbles should be high percentile, got {percentile}"

    def test_composite_percentile_uses_weights(self, benchmarks):
        """Test weighted composite respects stat weights."""
        # Create QB stats where passing_yards is elite but everything else is poor
        # passing_yards weight is 0.25
        elite_yards_only = {
            "passing_yards": 280,  # Elite
            "passing_tds": 0.8,  # Poor
            "completion_pct": 58,  # Poor
            "passer_rating": 75,  # Poor
            "interceptions": 1.2,  # Poor (inverted, so this is bad)
        }

        # Create stats where all are average
        all_average = {
            "passing_yards": 210,  # Average
            "passing_tds": 1.4,  # Average
            "completion_pct": 65,  # Average
            "passer_rating": 90,  # Average
            "interceptions": 0.8,  # Average
        }

        elite_composite = benchmarks.get_composite_percentile("QB", elite_yards_only)
        average_composite = benchmarks.get_composite_percentile("QB", all_average)

        # Elite yards with poor everything else should be lower than all-average
        # because yards is only 25% of weight
        assert elite_composite < average_composite, (
            f"One elite stat with poor others ({elite_composite}) should be worse "
            f"than all average ({average_composite})"
        )

        # All average should be around 50
        assert 45 <= average_composite <= 55

    def test_no_benchmark_positions_return_empty(self, benchmarks):
        """Test FB, OT, OG, C, KR, PR, LS return empty benchmarks or map to group."""
        no_stat_positions = ["FB", "KR", "PR", "LS"]

        for position in no_stat_positions:
            pos_benchmarks = benchmarks.get_benchmarks(position)
            # Should either be empty or position isn't in benchmarks
            if position in PositionBenchmarks.NO_STAT_POSITIONS:
                assert len(pos_benchmarks) == 0, f"{position} should have no benchmarks"

        # OT, OG, C map to groups but those groups don't have benchmarks either
        # So they should return empty
        for position in ["OT", "OG", "C"]:
            pos_benchmarks = benchmarks.get_benchmarks(position)
            assert len(pos_benchmarks) == 0, f"{position} should have no benchmarks"

    def test_tier_mapping(self, benchmarks):
        """Test percentile-to-tier mapping (0-24=backup, 25-49=starter, 50-89=quality, 90+=elite)."""
        assert benchmarks.get_tier_for_percentile(10) == "backup"
        assert benchmarks.get_tier_for_percentile(24) == "backup"
        assert benchmarks.get_tier_for_percentile(25) == "starter"
        assert benchmarks.get_tier_for_percentile(49) == "starter"
        assert benchmarks.get_tier_for_percentile(50) == "quality"
        assert benchmarks.get_tier_for_percentile(75) == "quality"
        assert benchmarks.get_tier_for_percentile(89) == "quality"
        assert benchmarks.get_tier_for_percentile(90) == "elite"
        assert benchmarks.get_tier_for_percentile(100) == "elite"


class TestStatBenchmark:
    """Tests for StatBenchmark dataclass."""

    def test_stat_benchmark_creation(self):
        """Test creating a StatBenchmark."""
        benchmark = StatBenchmark(
            stat_name="passing_yards",
            poor=150,
            average=210,
            good=250,
            elite=280,
        )
        assert benchmark.stat_name == "passing_yards"
        assert benchmark.poor == 150
        assert benchmark.average == 210
        assert benchmark.good == 250
        assert benchmark.elite == 280
        assert benchmark.inverted is False
        assert benchmark.is_rate_stat is False

    def test_stat_benchmark_inverted(self):
        """Test creating an inverted StatBenchmark."""
        benchmark = StatBenchmark(
            stat_name="interceptions",
            poor=1.2,
            average=0.8,
            good=0.6,
            elite=0.4,
            inverted=True,
        )
        assert benchmark.inverted is True

    def test_stat_benchmark_rate_stat(self):
        """Test creating a rate stat benchmark."""
        benchmark = StatBenchmark(
            stat_name="completion_pct",
            poor=58,
            average=65,
            good=68,
            elite=72,
            is_rate_stat=True,
        )
        assert benchmark.is_rate_stat is True
