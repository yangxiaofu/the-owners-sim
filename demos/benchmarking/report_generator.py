"""
Benchmark Report Generator

Compares simulation results against NFL benchmarks and generates
reports in multiple formats (console, CSV, JSON, Markdown).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import csv
from pathlib import Path

from .nfl_benchmarks import NFLBenchmarks2023, NFLBenchmark
from .stats_aggregator import BenchmarkStatsAggregator


@dataclass
class BenchmarkComparison:
    """Comparison result for a single metric."""
    metric_name: str
    category: str
    simulated_value: float
    nfl_benchmark: float
    nfl_min: float
    nfl_max: float
    deviation_percent: float
    status: str  # 'PASS', 'WARNING', 'FAIL'
    unit: str


class BenchmarkReportGenerator:
    """
    Generates benchmark comparison reports in multiple formats.

    Compares aggregated simulation statistics against NFL 2023 benchmarks
    and flags metrics that deviate significantly.
    """

    # Deviation thresholds
    PASS_THRESHOLD = 10.0      # < 10% deviation = PASS
    WARNING_THRESHOLD = 15.0   # 10-15% = WARNING, > 15% = FAIL

    def __init__(self, aggregator: BenchmarkStatsAggregator):
        """
        Initialize report generator.

        Args:
            aggregator: BenchmarkStatsAggregator with simulation results
        """
        self.aggregator = aggregator
        self.comparisons: List[BenchmarkComparison] = []
        self._metadata: Dict[str, Any] = {}

    def run_comparison(self, benchmarks: Optional[NFLBenchmarks2023] = None):
        """
        Compare aggregated stats against NFL benchmarks.

        Args:
            benchmarks: NFLBenchmarks2023 instance (creates default if None)
        """
        if benchmarks is None:
            benchmarks = NFLBenchmarks2023()

        self.comparisons = []

        # Get simulation averages
        game_avgs = self.aggregator.get_game_averages()
        qb_avgs = self.aggregator.get_qb_averages()
        rb_avgs = self.aggregator.get_rb_averages()
        wr_avgs = self.aggregator.get_wr_averages()
        te_avgs = self.aggregator.get_te_averages()
        kicker_avgs = self.aggregator.get_kicker_averages()
        defense_avgs = self.aggregator.get_defense_averages()

        # Store metadata
        self._metadata = {
            'games_simulated': int(game_avgs.get('_games_simulated', 0)),
            'total_simulation_time': game_avgs.get('_total_simulation_time', 0),
        }

        # Compare game-level metrics
        self._compare_category(
            game_avgs,
            benchmarks.GAME_BENCHMARKS,
            'Game'
        )

        # Compare QB metrics
        self._compare_category(
            qb_avgs,
            benchmarks.QB_BENCHMARKS,
            'QB'
        )

        # Compare RB metrics
        self._compare_category(
            rb_avgs,
            benchmarks.RB_BENCHMARKS,
            'RB'
        )

        # Compare WR metrics
        self._compare_category(
            wr_avgs,
            benchmarks.WR_BENCHMARKS,
            'WR'
        )

        # Compare TE metrics
        self._compare_category(
            te_avgs,
            benchmarks.TE_BENCHMARKS,
            'TE'
        )

        # Compare Kicker metrics
        self._compare_category(
            kicker_avgs,
            benchmarks.KICKER_BENCHMARKS,
            'Kicker'
        )

        # Compare Defense metrics
        self._compare_category(
            defense_avgs,
            benchmarks.DEFENSE_BENCHMARKS,
            'Defense'
        )

    def _compare_category(
        self,
        simulated: Dict[str, float],
        benchmarks: Dict[str, NFLBenchmark],
        category_label: str
    ):
        """Compare a category of metrics against benchmarks."""
        for metric_name, benchmark in benchmarks.items():
            sim_value = simulated.get(metric_name, 0)

            deviation = self._calculate_deviation(sim_value, benchmark.nfl_average)
            status = self._determine_status(sim_value, benchmark)

            self.comparisons.append(BenchmarkComparison(
                metric_name=metric_name,
                category=category_label,
                simulated_value=round(sim_value, 2),
                nfl_benchmark=benchmark.nfl_average,
                nfl_min=benchmark.nfl_min,
                nfl_max=benchmark.nfl_max,
                deviation_percent=round(deviation, 1),
                status=status,
                unit=benchmark.unit,
            ))

    def _calculate_deviation(self, simulated: float, benchmark: float) -> float:
        """Calculate percentage deviation from benchmark."""
        if benchmark == 0:
            return 0.0 if simulated == 0 else 100.0
        return ((simulated - benchmark) / benchmark) * 100

    def _determine_status(self, simulated: float, benchmark: NFLBenchmark) -> str:
        """
        Determine status based on whether value is within acceptable range.

        Uses NFL min/max range first, then falls back to deviation threshold.
        """
        # Check if within NFL acceptable range
        if benchmark.nfl_min <= simulated <= benchmark.nfl_max:
            return 'PASS'

        # Calculate deviation from average
        deviation = abs(self._calculate_deviation(simulated, benchmark.nfl_average))

        if deviation < self.PASS_THRESHOLD:
            return 'PASS'
        elif deviation < self.WARNING_THRESHOLD:
            return 'WARNING'
        return 'FAIL'

    def generate_console_report(self) -> str:
        """
        Generate formatted console output.

        Returns:
            String with ASCII table report
        """
        lines = []

        # Header
        lines.append("=" * 90)
        lines.append("NFL GAME SIMULATION BENCHMARK RESULTS")
        lines.append("=" * 90)

        # Metadata
        games = self._metadata.get('games_simulated', 0)
        total_time = self._metadata.get('total_simulation_time', 0)
        avg_time = total_time / games if games > 0 else 0

        lines.append(f"Games Simulated: {games} | "
                    f"Total Time: {total_time:.1f}s ({avg_time:.2f}s/game avg)")
        lines.append("")

        # Group comparisons by category
        categories = {}
        for comp in self.comparisons:
            if comp.category not in categories:
                categories[comp.category] = []
            categories[comp.category].append(comp)

        # Generate table for each category
        for category, comps in categories.items():
            lines.append(f"{category.upper()} METRICS")
            lines.append("-" * 90)
            lines.append(
                f"{'Metric':<32} {'Simulated':>10} {'NFL Avg':>10} "
                f"{'Deviation':>12} {'Status':>10}"
            )
            lines.append("-" * 90)

            for comp in comps:
                # Format deviation with sign
                dev_str = f"{comp.deviation_percent:+.1f}%"

                # Status indicator
                if comp.status == 'PASS':
                    status_str = "PASS"
                elif comp.status == 'WARNING':
                    status_str = "WARNING"
                else:
                    status_str = "FAIL"

                # Format values based on unit
                if comp.unit == 'percentage':
                    sim_str = f"{comp.simulated_value:.1f}%"
                    nfl_str = f"{comp.nfl_benchmark:.1f}%"
                elif comp.unit == 'count':
                    sim_str = f"{comp.simulated_value:.1f}"
                    nfl_str = f"{comp.nfl_benchmark:.1f}"
                else:
                    sim_str = f"{comp.simulated_value:.1f}"
                    nfl_str = f"{comp.nfl_benchmark:.1f}"

                lines.append(
                    f"{comp.metric_name:<32} {sim_str:>10} {nfl_str:>10} "
                    f"{dev_str:>12} {status_str:>10}"
                )

            lines.append("")

        # Summary
        lines.append("=" * 90)
        failed = [c for c in self.comparisons if c.status == 'FAIL']
        warnings = [c for c in self.comparisons if c.status == 'WARNING']
        passed = [c for c in self.comparisons if c.status == 'PASS']

        lines.append(f"Summary: {len(passed)} PASSED, {len(warnings)} WARNINGS, {len(failed)} FAILED")

        if failed:
            lines.append("")
            lines.append("METRICS REQUIRING ATTENTION (>15% deviation):")
            for comp in failed:
                lines.append(
                    f"  - {comp.metric_name}: {comp.simulated_value:.1f} vs "
                    f"{comp.nfl_benchmark:.1f} ({comp.deviation_percent:+.1f}%)"
                )

        lines.append("=" * 90)

        return "\n".join(lines)

    def generate_csv_report(self, output_path: str):
        """
        Export detailed CSV for analysis.

        Args:
            output_path: Path to output CSV file
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'metric_name',
                'category',
                'simulated',
                'nfl_average',
                'nfl_min',
                'nfl_max',
                'deviation_pct',
                'status',
                'unit',
            ])

            # Data rows
            for comp in self.comparisons:
                writer.writerow([
                    comp.metric_name,
                    comp.category,
                    comp.simulated_value,
                    comp.nfl_benchmark,
                    comp.nfl_min,
                    comp.nfl_max,
                    comp.deviation_percent,
                    comp.status,
                    comp.unit,
                ])

    def generate_json_report(self, output_path: str):
        """
        Export JSON for programmatic consumption.

        Args:
            output_path: Path to output JSON file
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'metadata': {
                'games_simulated': self._metadata.get('games_simulated', 0),
                'total_simulation_time_seconds': self._metadata.get('total_simulation_time', 0),
            },
            'summary': {
                'passed': len([c for c in self.comparisons if c.status == 'PASS']),
                'warnings': len([c for c in self.comparisons if c.status == 'WARNING']),
                'failed': len([c for c in self.comparisons if c.status == 'FAIL']),
            },
            'comparisons': [
                {
                    'metric_name': comp.metric_name,
                    'category': comp.category,
                    'simulated': comp.simulated_value,
                    'nfl_benchmark': comp.nfl_benchmark,
                    'nfl_min': comp.nfl_min,
                    'nfl_max': comp.nfl_max,
                    'deviation_percent': comp.deviation_percent,
                    'status': comp.status,
                    'unit': comp.unit,
                }
                for comp in self.comparisons
            ],
            'raw_data': self.aggregator.export_raw_data(),
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def generate_markdown_report(self, output_path: str):
        """
        Generate markdown report with tables.

        Args:
            output_path: Path to output markdown file
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []

        # Title
        lines.append("# NFL Game Simulation Benchmark Results")
        lines.append("")

        # Metadata
        games = self._metadata.get('games_simulated', 0)
        total_time = self._metadata.get('total_simulation_time', 0)
        avg_time = total_time / games if games > 0 else 0

        lines.append(f"**Games Simulated:** {games}")
        lines.append(f"**Total Time:** {total_time:.1f}s ({avg_time:.2f}s/game)")
        lines.append("")

        # Summary
        failed = [c for c in self.comparisons if c.status == 'FAIL']
        warnings = [c for c in self.comparisons if c.status == 'WARNING']
        passed = [c for c in self.comparisons if c.status == 'PASS']

        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Status | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| PASS | {len(passed)} |")
        lines.append(f"| WARNING | {len(warnings)} |")
        lines.append(f"| FAIL | {len(failed)} |")
        lines.append("")

        # Group by category
        categories = {}
        for comp in self.comparisons:
            if comp.category not in categories:
                categories[comp.category] = []
            categories[comp.category].append(comp)

        # Tables for each category
        for category, comps in categories.items():
            lines.append(f"## {category} Metrics")
            lines.append("")
            lines.append("| Metric | Simulated | NFL Avg | Deviation | Status |")
            lines.append("|--------|-----------|---------|-----------|--------|")

            for comp in comps:
                dev_str = f"{comp.deviation_percent:+.1f}%"
                lines.append(
                    f"| {comp.metric_name} | {comp.simulated_value:.1f} | "
                    f"{comp.nfl_benchmark:.1f} | {dev_str} | {comp.status} |"
                )

            lines.append("")

        # Failed metrics
        if failed:
            lines.append("## Metrics Requiring Attention")
            lines.append("")
            lines.append("The following metrics deviate more than 15% from NFL averages:")
            lines.append("")
            for comp in failed:
                lines.append(
                    f"- **{comp.metric_name}**: {comp.simulated_value:.1f} vs "
                    f"{comp.nfl_benchmark:.1f} ({comp.deviation_percent:+.1f}%)"
                )
            lines.append("")

        with open(path, 'w') as f:
            f.write("\n".join(lines))

    def get_failed_metrics(self) -> List[BenchmarkComparison]:
        """Return list of failed comparisons."""
        return [c for c in self.comparisons if c.status == 'FAIL']

    def get_warning_metrics(self) -> List[BenchmarkComparison]:
        """Return list of warning comparisons."""
        return [c for c in self.comparisons if c.status == 'WARNING']

    def all_passed(self) -> bool:
        """Check if all benchmarks passed."""
        return all(c.status == 'PASS' for c in self.comparisons)
