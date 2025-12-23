"""
Contract Valuation Engine Testing Package.

Provides benchmark testing framework for validating contract valuations
against expected NFL market rates.

Classes:
    BenchmarkCase: A single test case with player data and expected AAV range
    BenchmarkResult: Result of running a single benchmark case
    BenchmarkReport: Aggregate report of all benchmark results
    BenchmarkHarness: Runner for executing benchmark cases
    ReportGenerator: Generates text and JSON reports from benchmark results
"""

from contract_valuation.testing.benchmark_cases import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkReport,
    BENCHMARK_CASES,
    get_cases_by_category,
    CATEGORY_ELITE,
    CATEGORY_STARTER,
    CATEGORY_BACKUP,
    CATEGORY_AGE_EXTREME,
    CATEGORY_GM_VARIANCE,
    CATEGORY_PRESSURE,
)
from contract_valuation.testing.test_harness import BenchmarkHarness
from contract_valuation.testing.report_generator import ReportGenerator


__all__ = [
    # Case definitions
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkReport",
    "BENCHMARK_CASES",
    "get_cases_by_category",
    # Category constants
    "CATEGORY_ELITE",
    "CATEGORY_STARTER",
    "CATEGORY_BACKUP",
    "CATEGORY_AGE_EXTREME",
    "CATEGORY_GM_VARIANCE",
    "CATEGORY_PRESSURE",
    # Classes
    "BenchmarkHarness",
    "ReportGenerator",
]
