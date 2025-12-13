"""
NFL Game Simulation Benchmarking System

Runs multiple full game simulations and compares statistics against
real NFL 2023 season averages for realism balancing.

Usage:
    python demos/benchmarking/benchmark_game_stats.py
    python demos/benchmarking/benchmark_game_stats.py --num-games 100
    python demos/benchmarking/benchmark_game_stats.py --workers 8 --output-dir ./results
"""

from .nfl_benchmarks import NFLBenchmarks2023, NFLBenchmark
from .stats_aggregator import BenchmarkStatsAggregator, GameSummary
from .report_generator import BenchmarkReportGenerator, BenchmarkComparison
from .parallel_simulator import ParallelGameSimulator, simulate_single_game

__all__ = [
    'NFLBenchmarks2023',
    'NFLBenchmark',
    'BenchmarkStatsAggregator',
    'GameSummary',
    'BenchmarkReportGenerator',
    'BenchmarkComparison',
    'ParallelGameSimulator',
    'simulate_single_game',
]
