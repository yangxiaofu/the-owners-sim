"""
Position Benchmarks & Market Data module.

Provides centralized stat benchmarks and market rates for contract valuation
across all 25 NFL positions.

Usage:
    from contract_valuation.benchmarks import (
        PositionBenchmarks,
        StatBenchmark,
        MarketRates,
        PositionMarketRate,
        load_nfl_contracts,
    )

    # Stat percentile lookup
    benchmarks = PositionBenchmarks()
    percentile = benchmarks.get_stat_percentile("QB", "passing_yards", 265)

    # Market rate lookup
    rates = MarketRates()
    aav = rates.get_rate("QB", "elite")  # 50_000_000
"""

from contract_valuation.benchmarks.position_benchmarks import (
    PositionBenchmarks,
    StatBenchmark,
)
from contract_valuation.benchmarks.market_rates import (
    MarketRates,
    PositionMarketRate,
    load_nfl_contracts,
)

__all__ = [
    # Position benchmarks
    "PositionBenchmarks",
    "StatBenchmark",
    # Market rates
    "MarketRates",
    "PositionMarketRate",
    "load_nfl_contracts",
]
