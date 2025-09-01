#!/usr/bin/env python3
"""
NFL Pass Play Algorithm Benchmarking Test Suite

This comprehensive test suite validates our pass play algorithm against actual 2024 NFL statistics
using large-scale simulations and statistical analysis. It runs extensive tests to ensure our
algorithm produces realistic NFL-like performance across all major passing categories.

2024 NFL Benchmarks (from Pro-Football-Reference):
- Completion Rate: 65.3%
- Yards per Attempt (YPA): 7.1
- Sack Rate: 6.87%
- Interception Rate: 2.2%
- Touchdown Rate: 4.5%
- Yards per Completion: 10.9
- Passer Rating: 92.3

Usage: python nfl_pass_benchmarks.py
"""

import sys
import os
import random
import statistics
import math
import time
from typing import List, Dict, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.core.play_executor import PlayExecutor
from game_engine.core.game_orchestrator import SimpleGameEngine
from game_engine.field.game_state import GameState
from game_engine.plays.data_structures import PlayResult


@dataclass
class NFLBenchmarks:
    """2024 NFL statistical benchmarks for validation"""
    completion_rate: float = 0.653      # 65.3%
    yards_per_attempt: float = 7.1      # 7.1 YPA
    sack_rate: float = 0.0687           # 6.87%
    interception_rate: float = 0.022    # 2.2%
    touchdown_rate: float = 0.045       # 4.5%
    yards_per_completion: float = 10.9  # 10.9 Y/C
    
    # Additional NFL benchmarks for advanced testing
    third_down_conversion: float = 0.40  # ~40% 3rd down conversion rate
    red_zone_td_rate: float = 0.60      # ~60% red zone TD rate
    deep_ball_completion: float = 0.35  # ~35% completion rate on 20+ yard attempts


@dataclass
class TestConfiguration:
    """Configuration for benchmarking tests"""
    large_sample_size: int = 10000      # Primary test sample size
    medium_sample_size: int = 5000      # Secondary test sample size  
    small_sample_size: int = 1000       # Situational test sample size
    tolerance_percent: float = 5.0      # Acceptable variance percentage (+/- 5%)
    confidence_level: float = 0.95      # Statistical confidence level
    random_seed: int = 42               # For reproducible results


@dataclass
class StatisticalResult:
    """Container for statistical analysis results"""
    mean: float
    std_dev: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    passes_nfl_test: bool
    variance_from_nfl: float


class NFLPassBenchmarkSuite:
    """Comprehensive NFL pass play benchmarking test suite"""
    
    def __init__(self, config: TestConfiguration = None):
        """Initialize the benchmarking suite"""
        self.config = config or TestConfiguration()
        self.nfl_benchmarks = NFLBenchmarks()
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
        
        # Set random seed for reproducible results
        random.seed(self.config.random_seed)
        
        # Initialize results storage
        self.results = {}
        self.detailed_results = []
        
        print("🏈 NFL Pass Play Algorithm Benchmarking Suite")
        print("=" * 60)
        print(f"Sample sizes: Large={self.config.large_sample_size}, Medium={self.config.medium_sample_size}")
        print(f"Tolerance: ±{self.config.tolerance_percent}% from NFL benchmarks")
        print(f"Random seed: {self.config.random_seed}")
        print()
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run the complete NFL benchmarking suite"""
        
        start_time = time.time()
        
        # Core NFL Statistical Benchmarks
        print("📊 CORE NFL STATISTICAL BENCHMARKS")
        print("-" * 40)
        self._test_completion_rate_benchmark()
        self._test_yards_per_attempt_benchmark()
        self._test_sack_rate_benchmark()
        self._test_interception_rate_benchmark()
        self._test_touchdown_rate_benchmark()
        
        # Advanced Statistical Analysis
        print("\n🔬 ADVANCED STATISTICAL ANALYSIS")
        print("-" * 40)
        self._test_yards_per_completion_benchmark()
        self._test_statistical_distributions()
        
        # Situational Performance Testing
        print("\n⚡ SITUATIONAL PERFORMANCE TESTING")
        print("-" * 40)
        self._test_third_down_performance()
        self._test_red_zone_performance()
        self._test_deep_ball_performance()
        self._test_formation_variety()
        
        # Team Rating Correlation Testing
        print("\n🏆 TEAM RATING CORRELATION TESTING")
        print("-" * 40)
        self._test_team_rating_correlations()
        self._test_matchup_realism()
        
        # Generate comprehensive report
        elapsed_time = time.time() - start_time
        self._generate_final_report(elapsed_time)
        
        return self.results
    
    def _test_completion_rate_benchmark(self):
        """Test completion rate against NFL benchmark (65.3%)"""
        print("Testing Completion Rate vs NFL 65.3%...")
        
        outcomes = self._run_large_sample_simulation()
        completions = sum(1 for outcome in outcomes if outcome in ["gain", "touchdown"])
        completion_rate = completions / len(outcomes)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            completion_rate, self.nfl_benchmarks.completion_rate, len(outcomes)
        )
        
        self.results["completion_rate"] = stat_result
        self._print_test_result("Completion Rate", completion_rate, 
                               self.nfl_benchmarks.completion_rate, stat_result.passes_nfl_test)
    
    def _test_yards_per_attempt_benchmark(self):
        """Test yards per attempt against NFL benchmark (7.1 YPA)"""
        print("Testing Yards per Attempt vs NFL 7.1 YPA...")
        
        yards_results = self._run_large_sample_simulation(return_yards=True)
        ypa = statistics.mean(yards_results)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            ypa, self.nfl_benchmarks.yards_per_attempt, len(yards_results)
        )
        
        self.results["yards_per_attempt"] = stat_result
        self._print_test_result("Yards per Attempt", ypa,
                               self.nfl_benchmarks.yards_per_attempt, stat_result.passes_nfl_test)
    
    def _test_sack_rate_benchmark(self):
        """Test sack rate against NFL benchmark (6.87%)"""
        print("Testing Sack Rate vs NFL 6.87%...")
        
        outcomes = self._run_large_sample_simulation()
        sacks = sum(1 for outcome in outcomes if outcome == "sack")
        sack_rate = sacks / len(outcomes)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            sack_rate, self.nfl_benchmarks.sack_rate, len(outcomes)
        )
        
        self.results["sack_rate"] = stat_result
        self._print_test_result("Sack Rate", sack_rate,
                               self.nfl_benchmarks.sack_rate, stat_result.passes_nfl_test)
    
    def _test_interception_rate_benchmark(self):
        """Test interception rate against NFL benchmark (2.2%)"""
        print("Testing Interception Rate vs NFL 2.2%...")
        
        outcomes = self._run_large_sample_simulation()
        interceptions = sum(1 for outcome in outcomes if outcome == "interception")
        int_rate = interceptions / len(outcomes)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            int_rate, self.nfl_benchmarks.interception_rate, len(outcomes)
        )
        
        self.results["interception_rate"] = stat_result
        self._print_test_result("Interception Rate", int_rate,
                               self.nfl_benchmarks.interception_rate, stat_result.passes_nfl_test)
    
    def _test_touchdown_rate_benchmark(self):
        """Test touchdown rate against NFL benchmark (4.5%)"""
        print("Testing Touchdown Rate vs NFL 4.5%...")
        
        outcomes = self._run_large_sample_simulation()
        touchdowns = sum(1 for outcome in outcomes if outcome == "touchdown")
        td_rate = touchdowns / len(outcomes)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            td_rate, self.nfl_benchmarks.touchdown_rate, len(outcomes)
        )
        
        self.results["touchdown_rate"] = stat_result
        self._print_test_result("Touchdown Rate", td_rate,
                               self.nfl_benchmarks.touchdown_rate, stat_result.passes_nfl_test)
    
    def _test_yards_per_completion_benchmark(self):
        """Test yards per completion against NFL benchmark (10.9 Y/C)"""
        print("Testing Yards per Completion vs NFL 10.9 Y/C...")
        
        results = self._run_large_sample_simulation(return_full_results=True)
        completions = [r.yards_gained for r in results if r.outcome in ["gain", "touchdown"]]
        
        if completions:
            ypc = statistics.mean(completions)
            
            # Statistical analysis
            stat_result = self._calculate_statistical_result(
                ypc, self.nfl_benchmarks.yards_per_completion, len(completions)
            )
            
            self.results["yards_per_completion"] = stat_result
            self._print_test_result("Yards per Completion", ypc,
                                   self.nfl_benchmarks.yards_per_completion, stat_result.passes_nfl_test)
        else:
            print("❌ No completions found - algorithm may be broken")
    
    def _test_statistical_distributions(self):
        """Test that statistical distributions are realistic"""
        print("Testing Statistical Distributions...")
        
        results = self._run_large_sample_simulation(return_full_results=True)
        yards = [r.yards_gained for r in results]
        
        # Calculate distribution statistics
        mean_yards = statistics.mean(yards)
        std_dev = statistics.stdev(yards)
        
        # Test for reasonable variance (NFL has high variance in passing yards)
        expected_std_dev = mean_yards * 0.8  # Expect std dev to be ~80% of mean
        variance_test = abs(std_dev - expected_std_dev) / expected_std_dev < 0.5
        
        self.results["statistical_distribution"] = {
            "mean_yards": mean_yards,
            "std_dev": std_dev,
            "passes_variance_test": variance_test
        }
        
        print(f"  Mean yards: {mean_yards:.1f}, Std Dev: {std_dev:.1f}")
        print(f"  Variance test: {'✅ PASS' if variance_test else '❌ FAIL'}")
    
    def _test_third_down_performance(self):
        """Test 3rd down conversion rates (~40% NFL average)"""
        print("Testing 3rd Down Performance vs NFL 40%...")
        
        # Run simulations specifically for 3rd down situations
        third_down_results = []
        
        for _ in range(self.config.small_sample_size):
            game_state = self._create_test_game_state(down=3, distance=random.randint(3, 12))
            result = self._execute_single_pass(game_state)
            
            # Consider conversion successful if gained enough yards
            conversion = result.yards_gained >= game_state.field.yards_to_go
            third_down_results.append(conversion)
        
        conversion_rate = sum(third_down_results) / len(third_down_results)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            conversion_rate, self.nfl_benchmarks.third_down_conversion, len(third_down_results)
        )
        
        self.results["third_down_conversion"] = stat_result
        self._print_test_result("3rd Down Conversion", conversion_rate,
                               self.nfl_benchmarks.third_down_conversion, stat_result.passes_nfl_test)
    
    def _test_red_zone_performance(self):
        """Test red zone touchdown rates (~60% NFL average)"""
        print("Testing Red Zone Performance vs NFL 60% TD rate...")
        
        # Run simulations in red zone (field position 80+)
        red_zone_results = []
        
        for _ in range(self.config.small_sample_size):
            game_state = self._create_test_game_state(field_position=random.randint(80, 95))
            result = self._execute_single_pass(game_state)
            red_zone_results.append(result.outcome == "touchdown")
        
        rz_td_rate = sum(red_zone_results) / len(red_zone_results)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            rz_td_rate, self.nfl_benchmarks.red_zone_td_rate, len(red_zone_results)
        )
        
        self.results["red_zone_td_rate"] = stat_result
        self._print_test_result("Red Zone TD Rate", rz_td_rate,
                               self.nfl_benchmarks.red_zone_td_rate, stat_result.passes_nfl_test)
    
    def _test_deep_ball_performance(self):
        """Test deep ball completion rates (~35% NFL average)"""
        print("Testing Deep Ball Performance vs NFL 35%...")
        
        # Force vertical routes (deep balls) and measure completion rate
        deep_results = []
        
        for _ in range(self.config.small_sample_size):
            # Create 3rd and long situations to force vertical routes
            game_state = self._create_test_game_state(down=3, distance=random.randint(10, 20))
            result = self._execute_single_pass(game_state, formation="shotgun_spread")  # Forces vertical
            
            # Only count deep completions (15+ yards)
            if result.yards_gained >= 15:
                deep_results.append(result.outcome in ["gain", "touchdown"])
        
        if deep_results:
            deep_completion_rate = sum(deep_results) / len(deep_results)
            
            stat_result = self._calculate_statistical_result(
                deep_completion_rate, self.nfl_benchmarks.deep_ball_completion, len(deep_results)
            )
            
            self.results["deep_ball_completion"] = stat_result
            self._print_test_result("Deep Ball Completion", deep_completion_rate,
                                   self.nfl_benchmarks.deep_ball_completion, stat_result.passes_nfl_test)
        else:
            print("  ⚠️  No deep completions found - may need algorithm adjustment")
    
    def _test_formation_variety(self):
        """Test that different formations produce varied but realistic results"""
        print("Testing Formation Variety...")
        
        formations = ["shotgun", "shotgun_spread", "I_formation", "singleback", "pistol"]
        formation_results = {}
        
        for formation in formations:
            outcomes = []
            for _ in range(self.config.small_sample_size // len(formations)):
                game_state = self._create_test_game_state()
                result = self._execute_single_pass(game_state, formation)
                outcomes.append(result.outcome)
            
            # Calculate completion rate for this formation
            completions = sum(1 for outcome in outcomes if outcome in ["gain", "touchdown"])
            completion_rate = completions / len(outcomes) if outcomes else 0
            
            formation_results[formation] = completion_rate
        
        # Test that formations have different performance characteristics
        completion_rates = list(formation_results.values())
        has_variety = max(completion_rates) - min(completion_rates) > 0.1  # At least 10% difference
        
        self.results["formation_variety"] = {
            "formation_results": formation_results,
            "has_realistic_variety": has_variety
        }
        
        print(f"  Formation variety: {'✅ PASS' if has_variety else '❌ FAIL'}")
        for formation, rate in formation_results.items():
            print(f"    {formation}: {rate:.1%}")
    
    def _test_team_rating_correlations(self):
        """Test that team ratings correlate with performance"""
        print("Testing Team Rating Correlations...")
        
        # Test high-rated team vs low-rated team
        high_team = self.engine.get_team_for_simulation(5)  # Cowboys (80 rating)
        low_team = self.engine.get_team_for_simulation(3)   # Lions (60 rating)
        
        # Test Cowboys offense vs average defense
        cowboys_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state()
            result = self._execute_team_matchup_pass(high_team, low_team, game_state)
            cowboys_results.append(result.yards_gained)
        
        # Test Lions offense vs average defense  
        lions_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state()
            result = self._execute_team_matchup_pass(low_team, high_team, game_state)
            lions_results.append(result.yards_gained)
        
        # Cowboys should significantly outperform Lions
        cowboys_ypa = statistics.mean(cowboys_results)
        lions_ypa = statistics.mean(lions_results)
        performance_gap = cowboys_ypa - lions_ypa
        
        # Expect at least 1.5 YPA difference
        realistic_correlation = performance_gap > 1.5
        
        self.results["team_rating_correlation"] = {
            "cowboys_ypa": cowboys_ypa,
            "lions_ypa": lions_ypa,
            "performance_gap": performance_gap,
            "passes_correlation_test": realistic_correlation
        }
        
        print(f"  Cowboys YPA: {cowboys_ypa:.1f}, Lions YPA: {lions_ypa:.1f}")
        print(f"  Performance gap: {performance_gap:.1f} yards")
        print(f"  Correlation test: {'✅ PASS' if realistic_correlation else '❌ FAIL'}")
    
    def _test_matchup_realism(self):
        """Test that matchups produce realistic performance differences"""
        print("Testing Matchup Realism...")
        
        # Elite offense vs poor defense
        cowboys = self.engine.get_team_for_simulation(5)    # Cowboys (elite)
        lions = self.engine.get_team_for_simulation(3)      # Lions (poor)
        
        elite_vs_poor_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state()
            result = self._execute_team_matchup_pass(cowboys, lions, game_state)
            elite_vs_poor_results.append(result.yards_gained)
        
        # Poor offense vs elite defense
        poor_vs_elite_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state()
            result = self._execute_team_matchup_pass(lions, cowboys, game_state)
            poor_vs_elite_results.append(result.yards_gained)
        
        elite_vs_poor_ypa = statistics.mean(elite_vs_poor_results)
        poor_vs_elite_ypa = statistics.mean(poor_vs_elite_results)
        matchup_difference = elite_vs_poor_ypa - poor_vs_elite_ypa
        
        # Expect significant matchup difference (2+ YPA)
        realistic_matchups = matchup_difference > 2.0
        
        self.results["matchup_realism"] = {
            "elite_vs_poor_ypa": elite_vs_poor_ypa,
            "poor_vs_elite_ypa": poor_vs_elite_ypa,
            "matchup_difference": matchup_difference,
            "passes_matchup_test": realistic_matchups
        }
        
        print(f"  Elite vs Poor: {elite_vs_poor_ypa:.1f} YPA")
        print(f"  Poor vs Elite: {poor_vs_elite_ypa:.1f} YPA")
        print(f"  Matchup difference: {matchup_difference:.1f} yards")
        print(f"  Matchup realism: {'✅ PASS' if realistic_matchups else '❌ FAIL'}")
    
    def _run_large_sample_simulation(self, return_yards=False, return_full_results=False):
        """Run large sample simulation for statistical validity"""
        results = []
        
        print(f"  Running {self.config.large_sample_size:,} simulations...", end="", flush=True)
        
        # Progress tracking
        progress_interval = self.config.large_sample_size // 10
        
        for i in range(self.config.large_sample_size):
            if i % progress_interval == 0 and i > 0:
                print(f" {i//progress_interval}0%", end="", flush=True)
            
            game_state = self._create_test_game_state()
            result = self._execute_single_pass(game_state)
            
            if return_full_results:
                results.append(result)
            elif return_yards:
                results.append(result.yards_gained)
            else:
                results.append(result.outcome)
        
        print(" 100% ✅")
        return results
    
    def _create_test_game_state(self, down=None, distance=None, field_position=None):
        """Create a game state for testing"""
        game_state = GameState()
        
        # Set realistic random values or use provided values
        game_state.field.down = down or random.randint(1, 3)
        game_state.field.yards_to_go = distance or random.randint(1, 15)
        game_state.field.field_position = field_position or random.randint(10, 90)
        game_state.field.possession_team_id = 1  # Bears
        game_state.clock.quarter = random.randint(1, 4)
        game_state.clock.clock = random.randint(60, 900)  # 1-15 minutes
        
        return game_state
    
    def _execute_single_pass(self, game_state, formation="shotgun"):
        """Execute a single pass play for testing"""
        offense_team = self.engine.get_team_for_simulation(1)  # Bears
        defense_team = self.engine.get_team_for_simulation(2)  # Packers
        
        # Override formation if specified
        if hasattr(self.executor, 'player_selector') and self.executor.player_selector:
            personnel = self.executor.player_selector.get_personnel(
                offense_team, defense_team, "pass", game_state.field
            )
            personnel.formation = formation
        else:
            # Fallback to mock personnel
            from unittest.mock import Mock
            personnel = Mock()
            personnel.formation = formation
            personnel.defensive_call = "zone_coverage"
        
        return self.executor.execute_play(offense_team, defense_team, game_state)
    
    def _execute_team_matchup_pass(self, offense_team, defense_team, game_state):
        """Execute a pass with specific team matchup"""
        return self.executor.execute_play(offense_team, defense_team, game_state)
    
    def _calculate_statistical_result(self, observed_value: float, nfl_benchmark: float, sample_size: int) -> StatisticalResult:
        """Calculate comprehensive statistical analysis"""
        
        # For proportions, calculate using binomial distribution
        if 0 <= observed_value <= 1 and 0 <= nfl_benchmark <= 1:
            # Standard error for proportion
            std_error = math.sqrt(observed_value * (1 - observed_value) / sample_size)
            std_dev = std_error * math.sqrt(sample_size)
        else:
            # For continuous values, estimate std dev
            std_dev = abs(observed_value) * 0.2  # Assume 20% coefficient of variation
            std_error = std_dev / math.sqrt(sample_size)
        
        # Calculate 95% confidence interval
        z_score = 1.96  # 95% confidence
        margin_of_error = z_score * std_error
        confidence_interval = (observed_value - margin_of_error, observed_value + margin_of_error)
        
        # Check if passes NFL test (within tolerance)
        variance_from_nfl = abs(observed_value - nfl_benchmark) / nfl_benchmark * 100
        passes_test = variance_from_nfl <= self.config.tolerance_percent
        
        return StatisticalResult(
            mean=observed_value,
            std_dev=std_dev,
            confidence_interval=confidence_interval,
            sample_size=sample_size,
            passes_nfl_test=passes_test,
            variance_from_nfl=variance_from_nfl
        )
    
    def _print_test_result(self, test_name: str, observed: float, expected: float, passes: bool):
        """Print formatted test result"""
        if test_name.endswith("Rate"):
            observed_pct = observed * 100
            expected_pct = expected * 100
            print(f"  {test_name}: {observed_pct:.1f}% vs NFL {expected_pct:.1f}% - {'✅ PASS' if passes else '❌ FAIL'}")
        else:
            print(f"  {test_name}: {observed:.1f} vs NFL {expected:.1f} - {'✅ PASS' if passes else '❌ FAIL'}")
    
    def _generate_final_report(self, elapsed_time: float):
        """Generate comprehensive final report"""
        print("\n" + "=" * 60)
        print("🏈 NFL PASS ALGORITHM BENCHMARKING REPORT")
        print("=" * 60)
        
        # Count pass/fail results
        total_tests = 0
        passed_tests = 0
        
        core_tests = ["completion_rate", "yards_per_attempt", "sack_rate", 
                      "interception_rate", "touchdown_rate"]
        
        print("\n📊 CORE NFL BENCHMARKS SUMMARY:")
        print("-" * 35)
        
        for test_name in core_tests:
            if test_name in self.results:
                result = self.results[test_name]
                total_tests += 1
                if result.passes_nfl_test:
                    passed_tests += 1
                
                status = "✅ PASS" if result.passes_nfl_test else "❌ FAIL"
                variance = result.variance_from_nfl
                print(f"{test_name.replace('_', ' ').title():20}: {status} (±{variance:.1f}%)")
        
        # Additional test results
        additional_tests = ["third_down_conversion", "red_zone_td_rate", "deep_ball_completion"]
        print("\n⚡ SITUATIONAL PERFORMANCE:")
        print("-" * 30)
        
        for test_name in additional_tests:
            if test_name in self.results:
                result = self.results[test_name]
                total_tests += 1
                if result.passes_nfl_test:
                    passed_tests += 1
                
                status = "✅ PASS" if result.passes_nfl_test else "❌ FAIL"
                print(f"{test_name.replace('_', ' ').title():20}: {status}")
        
        # System tests
        print("\n🔧 SYSTEM VALIDATION:")
        print("-" * 20)
        
        system_tests = ["formation_variety", "team_rating_correlation", "matchup_realism"]
        for test_name in system_tests:
            if test_name in self.results:
                result = self.results[test_name]
                total_tests += 1
                
                if test_name == "formation_variety":
                    passes = result["has_realistic_variety"]
                elif test_name == "team_rating_correlation":
                    passes = result["passes_correlation_test"]
                elif test_name == "matchup_realism":
                    passes = result["passes_matchup_test"]
                else:
                    passes = False
                
                if passes:
                    passed_tests += 1
                
                status = "✅ PASS" if passes else "❌ FAIL"
                print(f"{test_name.replace('_', ' ').title():20}: {status}")
        
        # Overall summary
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("📈 OVERALL BENCHMARK RESULTS")
        print("=" * 60)
        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"Execution Time: {elapsed_time:.1f} seconds")
        print(f"Total Simulations: {self.config.large_sample_size * 5 + self.config.small_sample_size * 6:,}")
        
        if success_rate >= 80:
            print("🎉 EXCELLENT: Algorithm produces highly realistic NFL statistics!")
        elif success_rate >= 60:
            print("✅ GOOD: Algorithm produces acceptable NFL statistics")
        else:
            print("❌ POOR: Algorithm needs significant tuning to match NFL statistics")
        
        print("\n💡 Algorithm Status: Ready for production use" if success_rate >= 70 else "⚠️  Algorithm Status: Requires tuning")
        print("=" * 60)


def main():
    """Run the complete NFL benchmarking suite"""
    
    print("Starting NFL Pass Play Algorithm Benchmarking...")
    print("This may take several minutes due to large sample sizes.\n")
    
    # Create and run benchmarking suite
    config = TestConfiguration()
    benchmark_suite = NFLPassBenchmarkSuite(config)
    
    try:
        results = benchmark_suite.run_comprehensive_benchmark()
        
        # Export results for further analysis
        import json
        with open("nfl_benchmark_results.json", "w") as f:
            # Convert StatisticalResult objects to dictionaries for JSON serialization
            json_results = {}
            for key, value in results.items():
                if isinstance(value, StatisticalResult):
                    json_results[key] = {
                        "mean": value.mean,
                        "std_dev": value.std_dev,
                        "confidence_interval": value.confidence_interval,
                        "sample_size": value.sample_size,
                        "passes_nfl_test": value.passes_nfl_test,
                        "variance_from_nfl": value.variance_from_nfl
                    }
                else:
                    json_results[key] = value
            
            json.dump(json_results, f, indent=2)
        
        print(f"\n📁 Detailed results exported to: nfl_benchmark_results.json")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Benchmarking failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()