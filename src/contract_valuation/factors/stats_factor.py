"""
Stats-based valuation factor.

Evaluates player statistics against NFL benchmarks to determine
contract value. Uses position-specific stat weights and percentile
calculations.
"""

from typing import Dict, Any, List, Optional, Tuple

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext
from contract_valuation.factors.base import ValueFactor


class StatsFactor(ValueFactor):
    """
    Valuation factor based on statistical performance.

    Compares player stats to NFL benchmarks using per-game averages,
    calculates percentiles, and maps composite percentile to AAV range.

    Confidence: 0.70 base + 0.01 per game played (max 0.85)
                -0.05 per missing key stat
    """

    # NFL benchmarks: {stat_name: (poor, average, elite)} per game
    # Based on 2023 NFL season data
    NFL_BENCHMARKS = {
        "QB": {
            "passing_yards": (150, 210, 280),
            "passing_tds": (0.8, 1.4, 2.2),
            "completion_pct": (58, 65, 72),
            "passer_rating": (75, 90, 105),
            "interceptions": (1.2, 0.8, 0.4),  # Inverted - lower is better
        },
        "RB": {
            "rushing_yards": (40, 70, 100),
            "rushing_tds": (0.2, 0.5, 0.9),
            "yards_per_carry": (3.5, 4.3, 5.2),
            "receptions": (1.5, 3.0, 5.0),
            "receiving_yards": (10, 25, 45),
            "fumbles": (0.15, 0.08, 0.02),  # Inverted
        },
        "WR": {
            "receiving_yards": (35, 65, 95),
            "receptions": (2.5, 5.0, 7.5),
            "receiving_tds": (0.2, 0.4, 0.7),
            "yards_per_reception": (10, 13, 16),
            "catch_rate": (55, 65, 75),
        },
        "TE": {
            "receiving_yards": (20, 40, 65),
            "receptions": (2.0, 3.5, 5.5),
            "receiving_tds": (0.1, 0.3, 0.6),
            "yards_per_reception": (8, 11, 14),
        },
        "EDGE": {
            "sacks": (0.2, 0.5, 0.9),
            "tackles": (2.0, 4.0, 6.0),
            "qb_hits": (0.3, 0.6, 1.0),
            "tfl": (0.2, 0.5, 0.9),
            "forced_fumbles": (0.02, 0.06, 0.12),
        },
        "DT": {
            "tackles": (1.5, 3.0, 4.5),
            "sacks": (0.1, 0.3, 0.6),
            "tfl": (0.2, 0.4, 0.7),
            "qb_hits": (0.2, 0.4, 0.7),
        },
        "LB": {
            "tackles": (4.0, 7.0, 10.0),
            "sacks": (0.05, 0.2, 0.5),
            "tfl": (0.2, 0.5, 0.8),
            "interceptions": (0.02, 0.06, 0.12),
            "passes_defended": (0.1, 0.3, 0.6),
        },
        "CB": {
            "passes_defended": (0.3, 0.6, 1.0),
            "interceptions": (0.05, 0.15, 0.3),
            "tackles": (2.0, 4.0, 6.0),
            "forced_fumbles": (0.02, 0.04, 0.08),
        },
        "S": {
            "tackles": (3.0, 5.0, 7.5),
            "interceptions": (0.05, 0.12, 0.25),
            "passes_defended": (0.2, 0.4, 0.7),
            "forced_fumbles": (0.02, 0.05, 0.10),
        },
        "K": {
            "fg_pct": (75, 85, 92),
            "fg_made": (1.2, 1.8, 2.2),
            "fg_long": (45, 52, 58),
        },
        "P": {
            "punt_avg": (42, 46, 50),
            "punt_inside_20_pct": (30, 40, 50),
            "punt_long": (50, 58, 65),
        },
    }

    # Position stat weights (must sum to 1.0 per position)
    STAT_WEIGHTS = {
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

    # Position group mappings
    POSITION_GROUPS = {
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

    # Inverted stats (lower is better)
    INVERTED_STATS = {"interceptions", "fumbles"}

    @property
    def factor_name(self) -> str:
        """Return factor identifier."""
        return "stats_based"

    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV based on statistical performance.

        Args:
            player_data: Must contain 'position'
                        Should contain 'stats' dict with season totals
                        Optional: 'games_played' for per-game calculations
            context: Market context with position rates

        Returns:
            FactorResult with AAV estimate

        Raises:
            ValueError: If required fields missing
        """
        self.validate_player_data(player_data)

        position = player_data["position"].upper()
        stats = player_data.get("stats", {})
        games_played = player_data.get("games_played", 16)

        # Handle case where stats is not a dict
        if not isinstance(stats, dict):
            return self._fallback_result(player_data, context)

        # Map position to group for benchmarks
        benchmark_position = self.POSITION_GROUPS.get(position, position)

        # Check if we have benchmarks for this position
        if benchmark_position not in self.NFL_BENCHMARKS:
            return self._no_benchmarks_result(player_data, context)

        # Convert season totals to per-game stats
        per_game_stats = self._calculate_per_game_stats(stats, games_played)

        # Calculate percentiles for each stat
        percentiles, missing_stats = self._calculate_percentiles(
            benchmark_position, per_game_stats
        )

        if not percentiles:
            return self._fallback_result(player_data, context)

        # Calculate weighted composite percentile
        composite_percentile = self._calculate_composite_percentile(
            benchmark_position, percentiles
        )

        # Map percentile to AAV
        final_aav = self._percentile_to_aav(
            position, composite_percentile, context
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            games_played, missing_stats
        )

        breakdown = {
            "position": position,
            "benchmark_position": benchmark_position,
            "games_played": games_played,
            "per_game_stats": per_game_stats,
            "percentiles": percentiles,
            "missing_stats": missing_stats,
            "composite_percentile": round(composite_percentile, 1),
            "tier": self._percentile_to_tier(composite_percentile),
            "final_aav": final_aav,
        }

        return FactorResult(
            name=self.factor_name,
            raw_value=final_aav,
            confidence=confidence,
            breakdown=breakdown,
        )

    def _calculate_per_game_stats(
        self,
        stats: Dict[str, Any],
        games_played: int
    ) -> Dict[str, float]:
        """Convert season totals to per-game stats."""
        if games_played <= 0:
            games_played = 1

        per_game = {}
        for stat_name, value in stats.items():
            if isinstance(value, (int, float)):
                # Percentage/rate stats don't need per-game conversion
                if (stat_name.endswith("_pct") or
                    stat_name.endswith("_rate") or
                    stat_name.endswith("_rating") or
                    stat_name == "yards_per_carry" or
                    stat_name == "yards_per_reception" or
                    stat_name == "catch_rate"):
                    per_game[stat_name] = value
                else:
                    per_game[stat_name] = value / games_played

        return per_game

    def _calculate_percentiles(
        self,
        position: str,
        per_game_stats: Dict[str, float]
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Calculate percentile for each stat.

        Returns:
            Tuple of (percentiles dict, list of missing stats)
        """
        benchmarks = self.NFL_BENCHMARKS.get(position, {})
        if not benchmarks:
            return {}, []

        percentiles = {}
        missing = []

        for stat_name, (poor, avg, elite) in benchmarks.items():
            if stat_name not in per_game_stats:
                missing.append(stat_name)
                continue

            value = per_game_stats[stat_name]
            percentile = self._value_to_percentile(
                value, poor, avg, elite,
                inverted=stat_name in self.INVERTED_STATS
            )
            percentiles[stat_name] = percentile

        return percentiles, missing

    def _value_to_percentile(
        self,
        value: float,
        poor: float,
        avg: float,
        elite: float,
        inverted: bool = False
    ) -> float:
        """
        Convert stat value to percentile (0-100).

        Uses poor (25th), avg (50th), elite (90th) as reference points.
        For inverted stats, lower values produce higher percentiles.
        """
        if inverted:
            # Flip the value for inverted stats
            value, poor, avg, elite = -value, -elite, -avg, -poor

        if value <= poor:
            # Below poor = 0-25 percentile range
            if poor == 0:
                return 0
            ratio = max(0, value / poor)
            return ratio * 25
        elif value <= avg:
            # Poor to avg = 25-50 percentile range
            if avg == poor:
                return 25
            ratio = (value - poor) / (avg - poor)
            return 25 + (ratio * 25)
        elif value <= elite:
            # Avg to elite = 50-90 percentile range
            if elite == avg:
                return 50
            ratio = (value - avg) / (elite - avg)
            return 50 + (ratio * 40)
        else:
            # Above elite = 90-100 percentile range
            # Cap at 100
            excess = value - elite
            bonus = min(10, excess * 2)  # Quick saturation
            return 90 + bonus

    def _calculate_composite_percentile(
        self,
        position: str,
        percentiles: Dict[str, float]
    ) -> float:
        """Calculate weighted average of percentiles."""
        weights = self.STAT_WEIGHTS.get(position, {})
        if not weights:
            return sum(percentiles.values()) / len(percentiles)

        weighted_sum = 0.0
        weight_sum = 0.0

        for stat_name, percentile in percentiles.items():
            weight = weights.get(stat_name, 0.1)
            weighted_sum += percentile * weight
            weight_sum += weight

        if weight_sum == 0:
            return 50.0

        # Normalize by actual weight sum (in case some stats missing)
        return weighted_sum / weight_sum

    def _percentile_to_tier(self, percentile: float) -> str:
        """Map percentile to tier."""
        if percentile >= 90:
            return "elite"
        elif percentile >= 50:
            return "quality"
        elif percentile >= 25:
            return "starter"
        else:
            return "backup"

    def _percentile_to_aav(
        self,
        position: str,
        percentile: float,
        context: ValuationContext
    ) -> int:
        """Map percentile to AAV using market rates."""
        tier = self._percentile_to_tier(percentile)

        # Get tier boundaries
        tier_floor = context.get_market_rate(position, tier)
        if tier_floor is None:
            # Try position groups
            mapped = self.POSITION_GROUPS.get(position, position)
            tier_floor = context.get_market_rate(mapped, tier)

        if tier_floor is None:
            # Fallback
            tier_floor = int(context.salary_cap * 0.01)

        # Get ceiling from next tier up
        tier_ceiling = tier_floor
        if tier == "backup":
            tier_ceiling = context.get_market_rate(position, "starter") or tier_floor * 2
        elif tier == "starter":
            tier_ceiling = context.get_market_rate(position, "quality") or tier_floor * 1.8
        elif tier == "quality":
            tier_ceiling = context.get_market_rate(position, "elite") or tier_floor * 1.5

        # Interpolate within tier based on percentile
        tier_ranges = {
            "elite": (90, 100),
            "quality": (50, 90),
            "starter": (25, 50),
            "backup": (0, 25),
        }

        pct_min, pct_max = tier_ranges[tier]
        if pct_max == pct_min:
            position_in_tier = 0.5
        else:
            position_in_tier = (percentile - pct_min) / (pct_max - pct_min)

        aav = tier_floor + int((tier_ceiling - tier_floor) * position_in_tier)
        return aav

    def _calculate_confidence(
        self,
        games_played: int,
        missing_stats: List[str]
    ) -> float:
        """
        Calculate confidence based on sample size and completeness.

        Base 0.70 + 0.01 per game (max +0.15) - 0.05 per missing stat.
        """
        base = 0.70

        # Games played bonus
        games_bonus = min(0.15, games_played * 0.01)

        # Missing stats penalty
        missing_penalty = len(missing_stats) * 0.05

        confidence = base + games_bonus - missing_penalty
        return max(0.40, min(0.85, confidence))

    def _fallback_result(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """Return fallback result when no stats available."""
        position = player_data["position"].upper()

        base_rate = context.get_market_rate(position, "starter")
        if base_rate is None:
            base_rate = int(context.salary_cap * 0.01)

        return FactorResult(
            name=self.factor_name,
            raw_value=base_rate,
            confidence=0.40,
            breakdown={
                "position": position,
                "no_stats": True,
                "fallback_tier": "starter",
                "base_rate": base_rate,
                "final_aav": base_rate,
            },
        )

    def _no_benchmarks_result(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """Return result when no benchmarks exist for position."""
        position = player_data["position"].upper()

        # Use overall rating to estimate tier
        rating = player_data.get("overall_rating", 75)
        tier = self.get_position_tier(position, rating, context)

        base_rate = context.get_market_rate(position, tier)
        if base_rate is None:
            base_rate = int(context.salary_cap * 0.01)

        return FactorResult(
            name=self.factor_name,
            raw_value=base_rate,
            confidence=0.50,
            breakdown={
                "position": position,
                "no_benchmarks": True,
                "rating_based_tier": tier,
                "base_rate": base_rate,
                "final_aav": base_rate,
            },
        )
