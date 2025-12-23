"""
Report Generator for Contract Valuation Benchmarks.

Generates human-readable text reports and JSON exports from benchmark results.

Usage:
    from contract_valuation.testing import ReportGenerator, BenchmarkHarness

    harness = BenchmarkHarness()
    report = harness.run_all_cases(BENCHMARK_CASES)

    generator = ReportGenerator()
    print(generator.generate_summary(report))
    json_data = generator.generate_json(report)
"""

from typing import Dict, Any, List
from datetime import datetime

from contract_valuation.testing.benchmark_cases import (
    BenchmarkReport,
    BenchmarkResult,
    get_all_categories,
)


class ReportGenerator:
    """
    Generates reports from benchmark results.

    Provides text summaries for console output and JSON exports
    for programmatic analysis.
    """

    # Target deviation threshold (pass if below this)
    DEVIATION_TARGET = 0.15  # 15%

    def __init__(self, deviation_target: float = 0.15):
        """
        Initialize report generator.

        Args:
            deviation_target: Target maximum deviation (default 15%)
        """
        self._deviation_target = deviation_target

    def generate_summary(self, report: BenchmarkReport) -> str:
        """
        Generate human-readable text summary.

        Args:
            report: BenchmarkReport to summarize

        Returns:
            Formatted text summary string
        """
        lines = [
            "BENCHMARK REPORT - Contract Valuation Engine",
            "=" * 50,
            "",
            f"Total Cases: {report.total_cases}",
            f"Passed: {report.passed_cases} ({report.pass_rate:.0%})",
            f"Failed: {report.failed_cases} ({1 - report.pass_rate:.0%})",
            "",
            "By Category:",
        ]

        # Category breakdown
        for category in get_all_categories():
            cat_results = report.get_results_by_category(category)
            if cat_results:
                passed = sum(1 for r in cat_results if r.passed)
                total = len(cat_results)
                pct = passed / total if total > 0 else 0
                lines.append(f"  - {category}: {passed}/{total} ({pct:.0%})")

        # Average deviation
        lines.append("")
        lines.append(f"Average Deviation: {report.average_deviation:.1%}")
        lines.append(f"Target: < {self._deviation_target:.0%}")

        # Overall status
        passed_overall = (
            report.pass_rate >= 0.80 and
            report.average_deviation <= self._deviation_target
        )
        status = "PASS" if passed_overall else "FAIL"
        lines.append(f"Status: {status}")

        # Failed cases detail if any
        failed = report.get_failed_results()
        if failed:
            lines.append("")
            lines.append("Failed Cases:")
            for r in failed[:5]:  # Show first 5
                actual = r.actual_aav
                expected_min = r.case.expected_aav_min
                expected_max = r.case.expected_aav_max
                lines.append(
                    f"  - {r.case.name}: ${actual:,} "
                    f"(expected ${expected_min:,}-${expected_max:,}, "
                    f"deviation {r.deviation_pct:.1%})"
                )
            if len(failed) > 5:
                lines.append(f"  ... and {len(failed) - 5} more")

        return "\n".join(lines)

    def generate_json(self, report: BenchmarkReport) -> Dict[str, Any]:
        """
        Generate JSON-serializable dictionary with full results.

        Args:
            report: BenchmarkReport to export

        Returns:
            Dictionary ready for JSON serialization
        """
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "deviation_target": self._deviation_target,
            },
            "summary": {
                "total_cases": report.total_cases,
                "passed_cases": report.passed_cases,
                "failed_cases": report.failed_cases,
                "pass_rate": round(report.pass_rate, 4),
                "average_deviation": round(report.average_deviation, 4),
                "overall_pass": (
                    report.pass_rate >= 0.80 and
                    report.average_deviation <= self._deviation_target
                ),
            },
            "by_category": self._generate_category_summary(report),
            "results": [
                self._result_to_dict(r) for r in report.results
            ],
        }

    def generate_deviation_analysis(self, report: BenchmarkReport) -> str:
        """
        Generate detailed deviation analysis showing worst cases.

        Args:
            report: BenchmarkReport to analyze

        Returns:
            Text analysis of deviation patterns
        """
        lines = [
            "DEVIATION ANALYSIS",
            "=" * 50,
            "",
        ]

        # Sort by deviation (worst first)
        sorted_results = sorted(
            report.results,
            key=lambda r: abs(r.deviation_pct),
            reverse=True,
        )

        # Top 10 worst deviations
        lines.append("Top 10 Worst Deviations:")
        for i, r in enumerate(sorted_results[:10], 1):
            sign = "+" if r.actual_aav > r.case.expected_midpoint else "-"
            lines.append(
                f"  {i}. {r.case.name}: {sign}{abs(r.deviation_pct):.1%} "
                f"(${r.actual_aav:,} vs ${r.case.expected_midpoint:,})"
            )

        # Best performers
        lines.append("")
        lines.append("Best 5 Performers:")
        for i, r in enumerate(reversed(sorted_results[-5:]), 1):
            lines.append(
                f"  {i}. {r.case.name}: {r.deviation_pct:.1%} "
                f"(${r.actual_aav:,})"
            )

        # Category analysis
        lines.append("")
        lines.append("Average Deviation by Category:")
        for category in get_all_categories():
            cat_results = report.get_results_by_category(category)
            if cat_results:
                avg_dev = sum(abs(r.deviation_pct) for r in cat_results) / len(cat_results)
                lines.append(f"  - {category}: {avg_dev:.1%}")

        return "\n".join(lines)

    def _generate_category_summary(self, report: BenchmarkReport) -> Dict[str, Dict[str, Any]]:
        """Generate summary statistics for each category."""
        summary = {}
        for category in get_all_categories():
            cat_results = report.get_results_by_category(category)
            if cat_results:
                passed = sum(1 for r in cat_results if r.passed)
                total = len(cat_results)
                avg_dev = sum(abs(r.deviation_pct) for r in cat_results) / len(cat_results)
                summary[category] = {
                    "total": total,
                    "passed": passed,
                    "pass_rate": round(passed / total, 4) if total > 0 else 0,
                    "average_deviation": round(avg_dev, 4),
                }
        return summary

    def _result_to_dict(self, result: BenchmarkResult) -> Dict[str, Any]:
        """Convert a single BenchmarkResult to dictionary."""
        return {
            "case_name": result.case.name,
            "category": result.case.category,
            "player_position": result.case.player_data.get("position"),
            "player_rating": result.case.player_data.get("overall_rating"),
            "player_age": result.case.player_data.get("age"),
            "expected_aav_min": result.case.expected_aav_min,
            "expected_aav_max": result.case.expected_aav_max,
            "expected_midpoint": result.case.expected_midpoint,
            "actual_aav": result.actual_aav,
            "in_range": result.in_range,
            "deviation_pct": round(result.deviation_pct, 4),
            "passed": result.passed,
            "gm_style": result.case.gm_style,
            "pressure_level": result.case.pressure_level,
            "notes": result.case.notes,
        }

    def get_exit_code(self, report: BenchmarkReport) -> int:
        """
        Get CI-friendly exit code based on results.

        Args:
            report: BenchmarkReport to evaluate

        Returns:
            0 if passed, 1 if failed
        """
        overall_pass = (
            report.pass_rate >= 0.80 and
            report.average_deviation <= self._deviation_target
        )
        return 0 if overall_pass else 1


def run_benchmark_with_report() -> int:
    """
    Run benchmarks and print report.

    Returns:
        Exit code (0=pass, 1=fail)
    """
    from contract_valuation.testing.benchmark_cases import BENCHMARK_CASES
    from contract_valuation.testing.test_harness import BenchmarkHarness

    harness = BenchmarkHarness()
    report = harness.run_all_cases(BENCHMARK_CASES)

    generator = ReportGenerator()
    print(generator.generate_summary(report))
    print()
    print(generator.generate_deviation_analysis(report))

    return generator.get_exit_code(report)


if __name__ == "__main__":
    import sys
    exit_code = run_benchmark_with_report()
    sys.exit(exit_code)
