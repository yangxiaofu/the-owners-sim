"""
Position-specific stat benchmarks for contract valuation.

Provides percentile lookup for player statistical performance
across all 25 NFL positions. Based on 2023-2024 NFL season data.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class StatBenchmark:
    """
    Benchmark values for a single statistic.

    All values are per-game except rate stats (pct, rating, yards_per_x).

    Attributes:
        stat_name: Name of the statistic
        poor: 25th percentile value
        average: 50th percentile value
        good: 75th percentile value
        elite: 90th percentile value
        inverted: True if lower is better (e.g., interceptions, fumbles)
        is_rate_stat: True for %, rating, yards_per_x (not converted to per-game)
    """

    stat_name: str
    poor: float
    average: float
    good: float
    elite: float
    inverted: bool = False
    is_rate_stat: bool = False


class PositionBenchmarks:
    """
    Centralized NFL stat benchmarks by position.

    Provides percentile lookup for player statistical performance
    across all 25 positions. Positions without direct benchmarks
    map to position groups.

    Usage:
        benchmarks = PositionBenchmarks()
        percentile = benchmarks.get_stat_percentile("QB", "passing_yards", 265)
        tier = benchmarks.get_tier_for_percentile(percentile)  # "elite"
    """

    # Position group mappings (specific -> generic)
    POSITION_GROUPS: Dict[str, str] = {
        "LOLB": "EDGE",
        "ROLB": "EDGE",
        "LE": "EDGE",
        "RE": "EDGE",
        "MLB": "LB",
        "FS": "S",
        "SS": "S",
        "LT": "OT",
        "RT": "OT",
        "LG": "OG",
        "RG": "OG",
    }

    # Positions with no meaningful stat benchmarks
    NO_STAT_POSITIONS: set = {"FB", "OT", "OG", "C", "KR", "PR", "LS"}

    # Stat weights by position (must sum to 1.0)
    STAT_WEIGHTS: Dict[str, Dict[str, float]] = {
        "QB": {
            "passing_yards": 0.25,
            "passing_tds": 0.25,
            "completion_pct": 0.20,
            "passer_rating": 0.20,
            "interceptions": 0.10,
        },
        "RB": {
            "rushing_yards": 0.30,
            "rushing_tds": 0.20,
            "yards_per_carry": 0.25,
            "receptions": 0.10,
            "receiving_yards": 0.10,
            "fumbles": 0.05,
        },
        "WR": {
            "receiving_yards": 0.30,
            "receptions": 0.20,
            "receiving_tds": 0.25,
            "yards_per_reception": 0.15,
            "catch_rate": 0.10,
        },
        "TE": {
            "receiving_yards": 0.30,
            "receptions": 0.25,
            "receiving_tds": 0.25,
            "yards_per_reception": 0.20,
        },
        "EDGE": {
            "sacks": 0.35,
            "tackles": 0.20,
            "qb_hits": 0.25,
            "tfl": 0.15,
            "forced_fumbles": 0.05,
        },
        "DT": {
            "tackles": 0.30,
            "sacks": 0.30,
            "tfl": 0.25,
            "qb_hits": 0.15,
        },
        "LB": {
            "tackles": 0.35,
            "sacks": 0.15,
            "tfl": 0.20,
            "interceptions": 0.15,
            "passes_defended": 0.15,
        },
        "CB": {
            "passes_defended": 0.35,
            "interceptions": 0.35,
            "tackles": 0.20,
            "forced_fumbles": 0.10,
        },
        "S": {
            "tackles": 0.30,
            "interceptions": 0.30,
            "passes_defended": 0.25,
            "forced_fumbles": 0.15,
        },
        "K": {
            "fg_pct": 0.50,
            "fg_made": 0.30,
            "fg_long": 0.20,
        },
        "P": {
            "punt_avg": 0.45,
            "punt_inside_20_pct": 0.35,
            "punt_long": 0.20,
        },
    }

    def __init__(self):
        """Initialize with default NFL benchmarks."""
        self._benchmarks = self._load_default_benchmarks()

    def get_benchmarks(self, position: str) -> Dict[str, StatBenchmark]:
        """
        Get all stat benchmarks for a position.

        Args:
            position: Player position (e.g., "QB", "LOLB")

        Returns:
            Dict mapping stat_name -> StatBenchmark.
            Empty dict if position has no benchmarks.
        """
        mapped = self.get_mapped_position(position)
        return self._benchmarks.get(mapped, {})

    def get_stat_percentile(
        self,
        position: str,
        stat_name: str,
        value: float,
    ) -> Optional[float]:
        """
        Calculate percentile for a stat value.

        Args:
            position: Player position
            stat_name: Statistic name (e.g., "passing_yards")
            value: The stat value (per-game for counting stats)

        Returns:
            Percentile (0-100) or None if no benchmark exists
        """
        benchmarks = self.get_benchmarks(position)
        if stat_name not in benchmarks:
            return None

        benchmark = benchmarks[stat_name]
        return self._value_to_percentile(
            value,
            benchmark.poor,
            benchmark.average,
            benchmark.good,
            benchmark.elite,
            benchmark.inverted,
        )

    def get_composite_percentile(
        self,
        position: str,
        stats: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate weighted composite percentile across all stats.

        Args:
            position: Player position
            stats: Dict of stat_name -> value (per-game for counting stats)
            weights: Optional custom weights (default uses position weights)

        Returns:
            Weighted average percentile (0-100)
        """
        benchmarks = self.get_benchmarks(position)
        if not benchmarks:
            return 50.0  # Default to average if no benchmarks

        if weights is None:
            weights = self.get_stat_weights(position)

        weighted_sum = 0.0
        weight_sum = 0.0

        for stat_name, value in stats.items():
            percentile = self.get_stat_percentile(position, stat_name, value)
            if percentile is not None:
                weight = weights.get(stat_name, 0.1)
                weighted_sum += percentile * weight
                weight_sum += weight

        if weight_sum == 0:
            return 50.0

        return weighted_sum / weight_sum

    def get_tier_for_percentile(self, percentile: float) -> str:
        """
        Map percentile to contract tier.

        Args:
            percentile: 0-100 percentile value

        Returns:
            "backup", "starter", "quality", or "elite"
        """
        if percentile >= 90:
            return "elite"
        elif percentile >= 50:
            return "quality"
        elif percentile >= 25:
            return "starter"
        else:
            return "backup"

    def has_benchmarks(self, position: str) -> bool:
        """Check if position has stat benchmarks."""
        mapped = self.get_mapped_position(position)
        return mapped in self._benchmarks

    def get_mapped_position(self, position: str) -> str:
        """
        Get the benchmark position (may be group) for a position.

        Args:
            position: Player position (e.g., "LOLB")

        Returns:
            Benchmark position key (e.g., "EDGE")
        """
        upper = position.upper()
        return self.POSITION_GROUPS.get(upper, upper)

    def get_stat_weights(self, position: str) -> Dict[str, float]:
        """
        Get stat weights for composite calculation.

        Args:
            position: Player position

        Returns:
            Dict of stat_name -> weight (sums to 1.0)
        """
        mapped = self.get_mapped_position(position)
        return self.STAT_WEIGHTS.get(mapped, {})

    def _value_to_percentile(
        self,
        value: float,
        poor: float,
        average: float,
        good: float,
        elite: float,
        inverted: bool = False,
    ) -> float:
        """
        Convert stat value to percentile (0-100).

        Uses poor (25th), average (50th), good (75th), elite (90th) as reference.
        For inverted stats, lower values produce higher percentiles.
        """
        if inverted:
            # For inverted stats (lower is better), negate all values
            # This transforms the comparison: original high values become low (bad)
            # and original low values become high (good)
            value, poor, average, good, elite = -value, -poor, -average, -good, -elite

        if value <= poor:
            # Below poor = 0-25 percentile range
            if poor == 0:
                return 0
            ratio = max(0, value / poor) if poor != 0 else 0
            return ratio * 25
        elif value <= average:
            # Poor to average = 25-50 percentile range
            if average == poor:
                return 25
            ratio = (value - poor) / (average - poor)
            return 25 + (ratio * 25)
        elif value <= good:
            # Average to good = 50-75 percentile range
            if good == average:
                return 50
            ratio = (value - average) / (good - average)
            return 50 + (ratio * 25)
        elif value <= elite:
            # Good to elite = 75-90 percentile range
            if elite == good:
                return 75
            ratio = (value - good) / (elite - good)
            return 75 + (ratio * 15)
        else:
            # Above elite = 90-100 percentile range
            excess = value - elite
            # Quick saturation to 100
            bonus = min(10, excess * 2)
            return 90 + bonus

    @staticmethod
    def _load_default_benchmarks() -> Dict[str, Dict[str, StatBenchmark]]:
        """
        Load hardcoded NFL benchmarks (2023-2024 data).

        Returns:
            Dict mapping position -> stat_name -> StatBenchmark
        """
        return {
            "QB": {
                "passing_yards": StatBenchmark(
                    "passing_yards", 150, 210, 250, 280
                ),
                "passing_tds": StatBenchmark(
                    "passing_tds", 0.8, 1.4, 1.8, 2.2
                ),
                "completion_pct": StatBenchmark(
                    "completion_pct", 58, 65, 68, 72, is_rate_stat=True
                ),
                "passer_rating": StatBenchmark(
                    "passer_rating", 75, 90, 100, 105, is_rate_stat=True
                ),
                "interceptions": StatBenchmark(
                    "interceptions", 1.2, 0.8, 0.6, 0.4, inverted=True
                ),
            },
            "RB": {
                "rushing_yards": StatBenchmark(
                    "rushing_yards", 40, 70, 85, 100
                ),
                "rushing_tds": StatBenchmark(
                    "rushing_tds", 0.2, 0.5, 0.7, 0.9
                ),
                "yards_per_carry": StatBenchmark(
                    "yards_per_carry", 3.5, 4.3, 4.8, 5.2, is_rate_stat=True
                ),
                "receptions": StatBenchmark(
                    "receptions", 1.5, 3.0, 4.0, 5.0
                ),
                "receiving_yards": StatBenchmark(
                    "receiving_yards", 10, 25, 35, 45
                ),
                "fumbles": StatBenchmark(
                    "fumbles", 0.15, 0.08, 0.05, 0.02, inverted=True
                ),
            },
            "WR": {
                "receiving_yards": StatBenchmark(
                    "receiving_yards", 35, 65, 80, 95
                ),
                "receptions": StatBenchmark(
                    "receptions", 2.5, 5.0, 6.5, 7.5
                ),
                "receiving_tds": StatBenchmark(
                    "receiving_tds", 0.2, 0.4, 0.55, 0.7
                ),
                "yards_per_reception": StatBenchmark(
                    "yards_per_reception", 10, 13, 14.5, 16, is_rate_stat=True
                ),
                "catch_rate": StatBenchmark(
                    "catch_rate", 55, 65, 70, 75, is_rate_stat=True
                ),
            },
            "TE": {
                "receiving_yards": StatBenchmark(
                    "receiving_yards", 20, 40, 52, 65
                ),
                "receptions": StatBenchmark(
                    "receptions", 2.0, 3.5, 4.5, 5.5
                ),
                "receiving_tds": StatBenchmark(
                    "receiving_tds", 0.1, 0.3, 0.45, 0.6
                ),
                "yards_per_reception": StatBenchmark(
                    "yards_per_reception", 8, 11, 12.5, 14, is_rate_stat=True
                ),
            },
            "EDGE": {
                "sacks": StatBenchmark(
                    "sacks", 0.2, 0.5, 0.7, 0.9
                ),
                "tackles": StatBenchmark(
                    "tackles", 2.0, 4.0, 5.0, 6.0
                ),
                "qb_hits": StatBenchmark(
                    "qb_hits", 0.3, 0.6, 0.8, 1.0
                ),
                "tfl": StatBenchmark(
                    "tfl", 0.2, 0.5, 0.7, 0.9
                ),
                "forced_fumbles": StatBenchmark(
                    "forced_fumbles", 0.02, 0.06, 0.09, 0.12
                ),
            },
            "DT": {
                "tackles": StatBenchmark(
                    "tackles", 1.5, 3.0, 3.8, 4.5
                ),
                "sacks": StatBenchmark(
                    "sacks", 0.1, 0.3, 0.45, 0.6
                ),
                "tfl": StatBenchmark(
                    "tfl", 0.2, 0.4, 0.55, 0.7
                ),
                "qb_hits": StatBenchmark(
                    "qb_hits", 0.2, 0.4, 0.55, 0.7
                ),
            },
            "LB": {
                "tackles": StatBenchmark(
                    "tackles", 4.0, 7.0, 8.5, 10.0
                ),
                "sacks": StatBenchmark(
                    "sacks", 0.05, 0.2, 0.35, 0.5
                ),
                "tfl": StatBenchmark(
                    "tfl", 0.2, 0.5, 0.65, 0.8
                ),
                "interceptions": StatBenchmark(
                    "interceptions", 0.02, 0.06, 0.09, 0.12
                ),
                "passes_defended": StatBenchmark(
                    "passes_defended", 0.1, 0.3, 0.45, 0.6
                ),
            },
            "CB": {
                "passes_defended": StatBenchmark(
                    "passes_defended", 0.3, 0.6, 0.8, 1.0
                ),
                "interceptions": StatBenchmark(
                    "interceptions", 0.05, 0.15, 0.22, 0.3
                ),
                "tackles": StatBenchmark(
                    "tackles", 2.0, 4.0, 5.0, 6.0
                ),
                "forced_fumbles": StatBenchmark(
                    "forced_fumbles", 0.02, 0.04, 0.06, 0.08
                ),
            },
            "S": {
                "tackles": StatBenchmark(
                    "tackles", 3.0, 5.0, 6.2, 7.5
                ),
                "interceptions": StatBenchmark(
                    "interceptions", 0.05, 0.12, 0.18, 0.25
                ),
                "passes_defended": StatBenchmark(
                    "passes_defended", 0.2, 0.4, 0.55, 0.7
                ),
                "forced_fumbles": StatBenchmark(
                    "forced_fumbles", 0.02, 0.05, 0.075, 0.10
                ),
            },
            "K": {
                "fg_pct": StatBenchmark(
                    "fg_pct", 75, 85, 88, 92, is_rate_stat=True
                ),
                "fg_made": StatBenchmark(
                    "fg_made", 1.2, 1.8, 2.0, 2.2
                ),
                "fg_long": StatBenchmark(
                    "fg_long", 45, 52, 55, 58, is_rate_stat=True
                ),
            },
            "P": {
                "punt_avg": StatBenchmark(
                    "punt_avg", 42, 46, 48, 50, is_rate_stat=True
                ),
                "punt_inside_20_pct": StatBenchmark(
                    "punt_inside_20_pct", 30, 40, 45, 50, is_rate_stat=True
                ),
                "punt_long": StatBenchmark(
                    "punt_long", 50, 58, 62, 65, is_rate_stat=True
                ),
            },
        }
