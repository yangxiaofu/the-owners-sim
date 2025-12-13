#!/usr/bin/env python3
"""
NFL Game Simulation Benchmarking System

Runs N game simulations and compares results against NFL 2023 season averages
for realism balancing.

Usage:
    python demos/benchmarking/benchmark_game_stats.py                    # Default 500 games
    python demos/benchmarking/benchmark_game_stats.py --num-games 100    # Quick run
    python demos/benchmarking/benchmark_game_stats.py --num-games 10     # Very quick test
    python demos/benchmarking/benchmark_game_stats.py --workers 8        # Custom parallelism
    python demos/benchmarking/benchmark_game_stats.py --sequential       # No parallelism (debug)
    python demos/benchmarking/benchmark_game_stats.py --output-dir ./results --format all

Example with all options:
    python demos/benchmarking/benchmark_game_stats.py \\
        --num-games 500 \\
        --workers 4 \\
        --output-dir ./benchmark_results \\
        --format all

Output formats:
    - console: ASCII table printed to terminal (default)
    - csv: Detailed CSV for spreadsheet analysis
    - json: Structured JSON for programmatic use
    - markdown: Documentation-ready markdown tables
    - all: Generate all formats
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Add project paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))

from demos.benchmarking.parallel_simulator import ParallelGameSimulator
from demos.benchmarking.stats_aggregator import BenchmarkStatsAggregator
from demos.benchmarking.nfl_benchmarks import NFLBenchmarks2023
from demos.benchmarking.report_generator import BenchmarkReportGenerator


def progress_callback(completed: int, total: int, eta_seconds: float):
    """Display progress bar in terminal."""
    pct = (completed / total) * 100
    bar_len = 40
    filled = int(bar_len * completed / total)
    bar = '=' * filled + '-' * (bar_len - filled)

    eta_min = int(eta_seconds // 60)
    eta_sec = int(eta_seconds % 60)
    eta_str = f"{eta_min}m {eta_sec}s" if eta_min > 0 else f"{eta_sec}s"

    print(f"\rProgress: [{bar}] {completed}/{total} ({pct:.1f}%) ETA: {eta_str}    ",
          end='', flush=True)


def main():
    parser = argparse.ArgumentParser(
        description='NFL Game Simulation Benchmarking System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--num-games', '-n',
        type=int,
        default=500,
        help='Number of games to simulate (default: 500)'
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count - 1)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=None,
        help='Directory for output files (default: prints to console only)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['console', 'csv', 'json', 'markdown', 'all'],
        default='console',
        help='Output format (default: console)'
    )
    parser.add_argument(
        '--sequential', '-s',
        action='store_true',
        help='Run sequentially instead of parallel (for debugging)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress game-by-game output (always suppressed in parallel mode)'
    )
    parser.add_argument(
        '--round-robin',
        action='store_true',
        help='Use round-robin matchups instead of random'
    )

    args = parser.parse_args()

    # Validate inputs
    if args.num_games < 1:
        print("Error: num-games must be at least 1")
        sys.exit(1)
    if args.num_games > 1000:
        print("Warning: Running more than 1000 games may take a long time")

    # Header
    print("=" * 80)
    print("NFL GAME SIMULATION BENCHMARKING SYSTEM")
    print("=" * 80)
    print(f"Target games: {args.num_games}")
    print(f"Workers: {args.workers or 'auto'}")
    print(f"Mode: {'Sequential' if args.sequential else 'Parallel'}")
    print(f"Matchups: {'Round-robin' if args.round_robin else 'Random'}")
    print()

    # ==========================================================================
    # PHASE 1: Run Simulations
    # ==========================================================================
    print("Phase 1: Running simulations...")
    start_time = time.time()

    simulator = ParallelGameSimulator(
        num_games=args.num_games,
        num_workers=args.workers,
        suppress_output=True  # Always suppress in workers
    )

    if args.sequential:
        results = simulator.run_simulations_sequential(progress_callback=progress_callback)
    else:
        results = simulator.run_simulations(
            progress_callback=progress_callback,
            use_round_robin=args.round_robin
        )

    print()  # Newline after progress bar

    simulation_time = time.time() - start_time
    successful_games = len(results)
    failed_games = args.num_games - successful_games

    print(f"Simulations complete: {successful_games} successful, {failed_games} failed")
    print(f"Total time: {simulation_time:.1f}s ({simulation_time / args.num_games:.2f}s/game avg)")
    print()

    if successful_games == 0:
        print("Error: No games completed successfully. Cannot generate report.")
        sys.exit(1)

    # ==========================================================================
    # PHASE 2: Aggregate Statistics
    # ==========================================================================
    print("Phase 2: Aggregating statistics...")
    aggregator = BenchmarkStatsAggregator()

    for result in results:
        aggregator.add_game_result(
            game_id=result['game_id'],
            game_result=result['game_result'],
            all_stats=result['all_stats'],
            simulation_time=result['simulation_time']
        )

    print(f"Aggregated {len(aggregator.game_summaries)} games")
    print()

    # ==========================================================================
    # PHASE 3: Generate Comparison Report
    # ==========================================================================
    print("Phase 3: Comparing to NFL benchmarks...")
    benchmarks = NFLBenchmarks2023()
    report_gen = BenchmarkReportGenerator(aggregator)
    report_gen.run_comparison(benchmarks)

    # ==========================================================================
    # PHASE 4: Output Results
    # ==========================================================================
    print()

    # Console output
    if args.format in ['console', 'all']:
        print(report_gen.generate_console_report())

    # File outputs
    if args.output_dir:
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        base_name = f'benchmark_{args.num_games}games_{timestamp}'

        if args.format in ['csv', 'all']:
            csv_path = output_path / f'{base_name}.csv'
            report_gen.generate_csv_report(str(csv_path))
            print(f"CSV saved: {csv_path}")

        if args.format in ['json', 'all']:
            json_path = output_path / f'{base_name}.json'
            report_gen.generate_json_report(str(json_path))
            print(f"JSON saved: {json_path}")

        if args.format in ['markdown', 'all']:
            md_path = output_path / f'{base_name}.md'
            report_gen.generate_markdown_report(str(md_path))
            print(f"Markdown saved: {md_path}")

    # ==========================================================================
    # Final Summary
    # ==========================================================================
    print()
    print("=" * 80)

    failed_metrics = report_gen.get_failed_metrics()
    warning_metrics = report_gen.get_warning_metrics()

    if report_gen.all_passed():
        print("All benchmarks PASSED!")
    else:
        print(f"Results: {len(failed_metrics)} FAILED, {len(warning_metrics)} WARNINGS")

        if failed_metrics:
            print()
            print("METRICS REQUIRING ATTENTION (>15% deviation from NFL averages):")
            for metric in failed_metrics:
                direction = "HIGH" if metric.deviation_percent > 0 else "LOW"
                print(
                    f"  [{direction}] {metric.metric_name}: "
                    f"{metric.simulated_value:.1f} vs {metric.nfl_benchmark:.1f} "
                    f"({metric.deviation_percent:+.1f}%)"
                )

    print("=" * 80)

    # Exit code based on results
    if failed_metrics:
        sys.exit(1)  # Indicate benchmark failures
    sys.exit(0)


if __name__ == '__main__':
    main()
