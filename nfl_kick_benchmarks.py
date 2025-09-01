#!/usr/bin/env python3
"""
NFL Kick Algorithm Benchmarking Test Suite

This comprehensive test suite validates our kick algorithm against actual 2024 NFL statistics
using large-scale simulations and statistical analysis. It runs extensive tests to ensure our
algorithm produces realistic NFL-like performance across all major kicking categories.

2024 NFL Benchmarks (from Pro-Football-Reference):
- Extra Point: 95.8% success rate
- 30-39 yards: 92.9% success rate  
- 40-49 yards: 85.1% success rate
- 50+ yards: 73.5% success rate
- Overall FG: 84.0% success rate
- Block Rate: ~1.5% (NFL average)

Usage: python nfl_kick_benchmarks.py
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
class NFLKickBenchmarks:
    """2024 NFL statistical benchmarks for kicking validation"""
    extra_point_rate: float = 0.958        # 95.8%
    short_fg_rate: float = 0.929           # 92.9% (30-39 yards)
    medium_fg_rate: float = 0.851          # 85.1% (40-49 yards)
    long_fg_rate: float = 0.735            # 73.5% (50+ yards)
    overall_fg_rate: float = 0.840         # 84.0%
    block_rate: float = 0.015              # ~1.5%
    
    # Additional situational benchmarks
    clutch_time_penalty: float = 0.05      # ~5% penalty in clutch time
    dome_vs_outdoor_difference: float = 0.02  # ~2% better in dome


@dataclass
class TestConfiguration:
    """Configuration for benchmarking tests"""
    large_sample_size: int = 10000         # Primary test sample size
    medium_sample_size: int = 5000         # Secondary test sample size  
    small_sample_size: int = 1000          # Situational test sample size
    tolerance_percent: float = 3.0         # Acceptable variance percentage (+/- 3%)
    confidence_level: float = 0.95         # Statistical confidence level
    random_seed: int = 42                  # For reproducible results


@dataclass
class StatisticalResult:
    """Container for statistical analysis results"""
    mean: float
    std_dev: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    passes_nfl_test: bool
    variance_from_nfl: float


class NFLKickBenchmarkSuite:
    """Comprehensive NFL kicking algorithm benchmarking test suite"""
    
    def __init__(self, config: TestConfiguration = None):
        """Initialize the benchmarking suite"""
        self.config = config or TestConfiguration()
        self.nfl_benchmarks = NFLKickBenchmarks()
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
        
        # Set random seed for reproducible results
        random.seed(self.config.random_seed)
        
        # Initialize results storage
        self.results = {}
        self.detailed_results = []
        
        print("🏈 NFL Kick Algorithm Benchmarking Suite")
        print("=" * 60)
        print(f"Sample sizes: Large={self.config.large_sample_size}, Medium={self.config.medium_sample_size}")
        print(f"Tolerance: ±{self.config.tolerance_percent}% from NFL benchmarks")
        print(f"Random seed: {self.config.random_seed}")
        print()
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run the complete NFL kicking benchmarking suite"""
        
        start_time = time.time()
        
        # Core NFL Statistical Benchmarks
        print("🎯 CORE NFL KICKING BENCHMARKS")
        print("-" * 40)
        self._test_extra_point_rate_benchmark()
        self._test_short_fg_rate_benchmark()
        self._test_medium_fg_rate_benchmark()
        self._test_long_fg_rate_benchmark()
        self._test_overall_fg_rate_benchmark()
        
        # Block Rate Testing
        print("\n🛡️ BLOCK RATE ANALYSIS")
        print("-" * 40)
        self._test_block_rate_benchmark()
        
        # Distance-Based Performance Testing
        print("\n📏 DISTANCE-BASED PERFORMANCE")
        print("-" * 40)
        self._test_distance_accuracy_correlation()
        self._test_extreme_distance_performance()
        
        # Situational Performance Testing
        print("\n⚡ SITUATIONAL PERFORMANCE TESTING")
        print("-" * 40)
        self._test_pressure_situation_performance()
        self._test_environmental_factors()
        
        # Team Rating Correlation Testing
        print("\n🏆 TEAM RATING CORRELATION TESTING")
        print("-" * 40)
        self._test_team_rating_correlations()
        
        # Generate comprehensive report
        elapsed_time = time.time() - start_time
        self._generate_final_report(elapsed_time)
        
        return self.results
    
    def _test_extra_point_rate_benchmark(self):
        """Test extra point success rate against NFL benchmark (95.8%)"""
        print("Testing Extra Point Rate vs NFL 95.8%...")
        
        # Force extra points by setting field position at goal line
        outcomes = []
        for _ in range(self.config.medium_sample_size):
            game_state = GameState()
            game_state.field.field_position = 98  # Goal line - forces XP distance
            game_state.field.down = 4
            game_state.field.yards_to_go = 1  # This should be treated as XP attempt
            
            # Execute directly with kick play since play executor won't call FG for 4th and 1
            from game_engine.plays.kick_play import KickPlay
            from unittest.mock import Mock
            
            kick_play = KickPlay()
            personnel = Mock()
            personnel.kicker_rating = 75
            
            offense_ratings = {'ol': 70, 'special_teams': 75}
            defense_ratings = {'dl': 60}
            
            outcome, _ = kick_play._calculate_kick_outcome_from_matrix(
                offense_ratings, defense_ratings, personnel, game_state.field
            )
            outcomes.append(outcome)
        
        successes = sum(1 for outcome in outcomes if outcome in ["extra_point", "field_goal"])
        success_rate = successes / len(outcomes)
        
        # Statistical analysis
        stat_result = self._calculate_statistical_result(
            success_rate, self.nfl_benchmarks.extra_point_rate, len(outcomes)
        )
        
        self.results["extra_point_rate"] = stat_result
        self._print_test_result("Extra Point Rate", success_rate, 
                               self.nfl_benchmarks.extra_point_rate, stat_result.passes_nfl_test)
    
    def _test_short_fg_rate_benchmark(self):
        """Test short field goal rate against NFL benchmark (92.9%)"""
        print("Testing Short FG Rate (30-39 yards) vs NFL 92.9%...")
        
        outcomes = self._run_distance_specific_simulation(distance_range=(30, 39))
        successes = sum(1 for outcome in outcomes if outcome in ["field_goal"])
        success_rate = successes / len(outcomes)
        
        stat_result = self._calculate_statistical_result(
            success_rate, self.nfl_benchmarks.short_fg_rate, len(outcomes)
        )
        
        self.results["short_fg_rate"] = stat_result
        self._print_test_result("Short FG Rate", success_rate,
                               self.nfl_benchmarks.short_fg_rate, stat_result.passes_nfl_test)
    
    def _test_medium_fg_rate_benchmark(self):
        """Test medium field goal rate against NFL benchmark (85.1%)"""
        print("Testing Medium FG Rate (40-49 yards) vs NFL 85.1%...")
        
        outcomes = self._run_distance_specific_simulation(distance_range=(40, 49))
        successes = sum(1 for outcome in outcomes if outcome in ["field_goal"])
        success_rate = successes / len(outcomes)
        
        stat_result = self._calculate_statistical_result(
            success_rate, self.nfl_benchmarks.medium_fg_rate, len(outcomes)
        )
        
        self.results["medium_fg_rate"] = stat_result
        self._print_test_result("Medium FG Rate", success_rate,
                               self.nfl_benchmarks.medium_fg_rate, stat_result.passes_nfl_test)
    
    def _test_long_fg_rate_benchmark(self):
        """Test long field goal rate against NFL benchmark (73.5%)"""
        print("Testing Long FG Rate (50+ yards) vs NFL 73.5%...")
        
        outcomes = self._run_distance_specific_simulation(distance_range=(50, 65))
        successes = sum(1 for outcome in outcomes if outcome in ["field_goal"])
        success_rate = successes / len(outcomes)
        
        stat_result = self._calculate_statistical_result(
            success_rate, self.nfl_benchmarks.long_fg_rate, len(outcomes)
        )
        
        self.results["long_fg_rate"] = stat_result
        self._print_test_result("Long FG Rate", success_rate,
                               self.nfl_benchmarks.long_fg_rate, stat_result.passes_nfl_test)
    
    def _test_overall_fg_rate_benchmark(self):
        """Test overall field goal rate against NFL benchmark (84.0%)"""
        print("Testing Overall FG Rate vs NFL 84.0%...")
        
        # Mixed distance simulation to match NFL distribution
        outcomes = []
        # NFL distance distribution approximation
        short_kicks = self._run_distance_specific_simulation((30, 39), sample_size=self.config.medium_sample_size // 4)
        medium_kicks = self._run_distance_specific_simulation((40, 49), sample_size=self.config.medium_sample_size // 2)
        long_kicks = self._run_distance_specific_simulation((50, 65), sample_size=self.config.medium_sample_size // 4)
        
        outcomes.extend(short_kicks)
        outcomes.extend(medium_kicks)
        outcomes.extend(long_kicks)
        
        successes = sum(1 for outcome in outcomes if outcome in ["field_goal"])
        success_rate = successes / len(outcomes)
        
        stat_result = self._calculate_statistical_result(
            success_rate, self.nfl_benchmarks.overall_fg_rate, len(outcomes)
        )
        
        self.results["overall_fg_rate"] = stat_result
        self._print_test_result("Overall FG Rate", success_rate,
                               self.nfl_benchmarks.overall_fg_rate, stat_result.passes_nfl_test)
    
    def _test_block_rate_benchmark(self):
        """Test block rate against NFL benchmark (~1.5%)"""
        print("Testing Block Rate vs NFL 1.5%...")
        
        outcomes = self._run_large_sample_simulation()
        blocks = sum(1 for outcome in outcomes if outcome == "blocked_kick")
        block_rate = blocks / len(outcomes)
        
        stat_result = self._calculate_statistical_result(
            block_rate, self.nfl_benchmarks.block_rate, len(outcomes)
        )
        
        self.results["block_rate"] = stat_result
        self._print_test_result("Block Rate", block_rate,
                               self.nfl_benchmarks.block_rate, stat_result.passes_nfl_test)
    
    def _test_distance_accuracy_correlation(self):
        """Test that accuracy decreases with distance as expected"""
        print("Testing Distance-Accuracy Correlation...")
        
        distance_ranges = [(20, 29), (30, 39), (40, 49), (50, 59)]
        success_rates = []
        
        for distance_range in distance_ranges:
            outcomes = self._run_distance_specific_simulation(distance_range, self.config.small_sample_size // len(distance_ranges))
            successes = sum(1 for outcome in outcomes if outcome in ["field_goal", "extra_point"])
            success_rate = successes / len(outcomes) if outcomes else 0
            success_rates.append(success_rate)
            print(f"  {distance_range[0]}-{distance_range[1]} yards: {success_rate:.1%}")
        
        # Test that success rate generally decreases with distance
        correlation_test = all(success_rates[i] >= success_rates[i+1] - 0.05 for i in range(len(success_rates)-1))
        
        self.results["distance_correlation"] = {
            "success_rates_by_distance": {f"{r[0]}-{r[1]}": rate for r, rate in zip(distance_ranges, success_rates)},
            "passes_correlation_test": correlation_test
        }
        
        print(f"  Distance correlation: {'✅ PASS' if correlation_test else '❌ FAIL'}")
    
    def _test_extreme_distance_performance(self):
        """Test performance on very long kicks (60+ yards)"""
        print("Testing Extreme Distance Performance (60+ yards)...")
        
        outcomes = self._run_distance_specific_simulation((60, 70), self.config.small_sample_size)
        if outcomes:
            successes = sum(1 for outcome in outcomes if outcome in ["field_goal"])
            success_rate = successes / len(outcomes)
            
            # Expect very low success rate for 60+ yard kicks
            realistic_extreme = success_rate <= 0.30  # Should be 30% or less
            
            self.results["extreme_distance"] = {
                "success_rate": success_rate,
                "passes_realism_test": realistic_extreme
            }
            
            print(f"  60+ yard success rate: {success_rate:.1%}")
            print(f"  Extreme distance realism: {'✅ PASS' if realistic_extreme else '❌ FAIL'}")
        else:
            print("  ⚠️  No extreme distance attempts generated")
    
    def _test_pressure_situation_performance(self):
        """Test performance in high-pressure situations"""
        print("Testing Pressure Situation Performance...")
        
        # Regular situation kicks
        normal_outcomes = self._run_distance_specific_simulation((30, 50), self.config.small_sample_size // 2)
        normal_successes = sum(1 for outcome in normal_outcomes if outcome in ["field_goal"])
        normal_rate = normal_successes / len(normal_outcomes) if normal_outcomes else 0
        
        # TODO: Implement pressure situation detection in game state
        # For now, assume all 4th down kicks are pressure situations
        pressure_outcomes = self._run_distance_specific_simulation((30, 50), self.config.small_sample_size // 2, pressure=True)
        pressure_successes = sum(1 for outcome in pressure_outcomes if outcome in ["field_goal"])
        pressure_rate = pressure_successes / len(pressure_outcomes) if pressure_outcomes else 0
        
        performance_difference = normal_rate - pressure_rate
        realistic_pressure_effect = 0 <= performance_difference <= 0.10  # 0-10% penalty is realistic
        
        self.results["pressure_situation"] = {
            "normal_rate": normal_rate,
            "pressure_rate": pressure_rate,
            "performance_difference": performance_difference,
            "passes_pressure_test": realistic_pressure_effect
        }
        
        print(f"  Normal situation: {normal_rate:.1%}")
        print(f"  Pressure situation: {pressure_rate:.1%}")
        print(f"  Pressure penalty: {performance_difference:.1%}")
        print(f"  Pressure realism: {'✅ PASS' if realistic_pressure_effect else '❌ FAIL'}")
    
    def _test_environmental_factors(self):
        """Test environmental factors (placeholder for future implementation)"""
        print("Testing Environmental Factors...")
        
        # TODO: Implement dome vs outdoor, weather effects
        # For now, just test basic consistency
        outcomes1 = self._run_distance_specific_simulation((30, 50), self.config.small_sample_size // 2)
        outcomes2 = self._run_distance_specific_simulation((30, 50), self.config.small_sample_size // 2)
        
        rate1 = sum(1 for outcome in outcomes1 if outcome in ["field_goal"]) / len(outcomes1)
        rate2 = sum(1 for outcome in outcomes2 if outcome in ["field_goal"]) / len(outcomes2)
        
        consistency = abs(rate1 - rate2) < 0.05  # Should be within 5%
        
        self.results["environmental_consistency"] = {
            "sample1_rate": rate1,
            "sample2_rate": rate2,
            "difference": abs(rate1 - rate2),
            "passes_consistency_test": consistency
        }
        
        print(f"  Sample consistency: {'✅ PASS' if consistency else '❌ FAIL'}")
    
    def _test_team_rating_correlations(self):
        """Test that team ratings correlate with kicking performance"""
        print("Testing Team Rating Correlations...")
        
        # Test high-rated team vs low-rated team special teams
        high_team = self.engine.get_team_for_simulation(5)  # Cowboys (high special teams)
        low_team = self.engine.get_team_for_simulation(3)   # Lions (lower special teams)
        
        # High-rated team kicks
        high_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state(distance=random.randint(35, 45))
            result = self._execute_team_kick(high_team, low_team, game_state)
            high_results.append(result.outcome)
        
        # Low-rated team kicks
        low_results = []
        for _ in range(self.config.small_sample_size // 2):
            game_state = self._create_test_game_state(distance=random.randint(35, 45))
            result = self._execute_team_kick(low_team, high_team, game_state)
            low_results.append(result.outcome)
        
        high_rate = sum(1 for outcome in high_results if outcome in ["field_goal", "extra_point"]) / len(high_results)
        low_rate = sum(1 for outcome in low_results if outcome in ["field_goal", "extra_point"]) / len(low_results)
        performance_gap = high_rate - low_rate
        
        # Expect some performance difference (2-8% is realistic)
        realistic_correlation = 0.02 <= performance_gap <= 0.08
        
        self.results["team_rating_correlation"] = {
            "high_team_rate": high_rate,
            "low_team_rate": low_rate,
            "performance_gap": performance_gap,
            "passes_correlation_test": realistic_correlation
        }
        
        print(f"  High-rated team: {high_rate:.1%}")
        print(f"  Low-rated team: {low_rate:.1%}")
        print(f"  Performance gap: {performance_gap:.1%}")
        print(f"  Correlation test: {'✅ PASS' if realistic_correlation else '❌ FAIL'}")
    
    def _run_large_sample_simulation(self):
        """Run large sample simulation for statistical validity"""
        results = []
        
        print(f"  Running {self.config.large_sample_size:,} simulations...", end="", flush=True)
        
        # Progress tracking
        progress_interval = self.config.large_sample_size // 10
        
        for i in range(self.config.large_sample_size):
            if i % progress_interval == 0 and i > 0:
                print(f" {i//progress_interval}0%", end="", flush=True)
            
            # Random distance distribution matching NFL
            distance = self._get_realistic_kick_distance()
            game_state = self._create_test_game_state(distance=distance)
            result = self._execute_single_kick(game_state)
            results.append(result.outcome)
        
        print(" 100% ✅")
        return results
    
    def _run_distance_specific_simulation(self, distance_range: Tuple[int, int], 
                                        sample_size: int = None, pressure: bool = False):
        """Run simulation for specific distance range"""
        if sample_size is None:
            sample_size = self.config.medium_sample_size
        
        results = []
        for _ in range(sample_size):
            distance = random.randint(distance_range[0], distance_range[1])
            
            # Create field state directly based on distance
            from game_engine.field.field_state import FieldState
            field_state = FieldState()
            field_position = max(1, 100 - distance + 17)
            field_state.field_position = field_position
            field_state.down = 4
            field_state.yards_to_go = random.randint(4, 8)  # Force FG attempt
            
            # Execute directly with kick play to bypass play executor's logic
            from game_engine.plays.kick_play import KickPlay
            from unittest.mock import Mock
            
            kick_play = KickPlay()
            personnel = Mock()
            personnel.kicker_rating = 75
            
            offense_ratings = {'ol': 70, 'special_teams': 75}
            defense_ratings = {'dl': 60}
            
            outcome, _ = kick_play._calculate_kick_outcome_from_matrix(
                offense_ratings, defense_ratings, personnel, field_state
            )
            results.append(outcome)
        
        return results
    
    def _get_realistic_kick_distance(self) -> int:
        """Generate realistic kick distance based on NFL distribution"""
        # NFL distance distribution (approximate)
        rand = random.random()
        if rand < 0.15:
            return random.randint(18, 29)  # Extra points and very short FGs
        elif rand < 0.40:
            return random.randint(30, 39)  # Short FGs
        elif rand < 0.75:
            return random.randint(40, 49)  # Medium FGs
        else:
            return random.randint(50, 65)  # Long FGs
    
    def _create_test_game_state(self, distance: int = None, pressure: bool = False):
        """Create a game state for testing kicks"""
        game_state = GameState()
        
        if distance is None:
            distance = self._get_realistic_kick_distance()
        
        # Calculate field position from kick distance (distance = 100 - field_position + 17)
        field_position = max(1, 100 - distance + 17)
        
        game_state.field.field_position = field_position
        # Force field goal scenarios by using 4th down with appropriate yards_to_go
        game_state.field.down = 4
        if distance <= 30:  # Extra points and very short FGs
            game_state.field.yards_to_go = random.randint(1, 2)
        elif distance <= 45:  # Should trigger FG attempts  
            game_state.field.yards_to_go = random.randint(4, 8)
        else:  # Long FGs - still attempt rather than punt
            game_state.field.yards_to_go = random.randint(4, 6)
        
        game_state.field.possession_team_id = 1  # Bears
        game_state.clock.quarter = random.randint(1, 4)
        game_state.clock.clock = random.randint(60, 900)
        
        return game_state
    
    def _execute_single_kick(self, game_state):
        """Execute a single kick for testing"""
        offense_team = self.engine.get_team_for_simulation(1)  # Bears
        defense_team = self.engine.get_team_for_simulation(2)  # Packers
        
        return self.executor.execute_play(offense_team, defense_team, game_state)
    
    def _execute_team_kick(self, offense_team, defense_team, game_state):
        """Execute a kick with specific team matchup"""
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
        observed_pct = observed * 100
        expected_pct = expected * 100
        print(f"  {test_name}: {observed_pct:.1f}% vs NFL {expected_pct:.1f}% - {'✅ PASS' if passes else '❌ FAIL'}")
    
    def _generate_final_report(self, elapsed_time: float):
        """Generate comprehensive final report"""
        print("\n" + "=" * 60)
        print("🏈 NFL KICK ALGORITHM BENCHMARKING REPORT")
        print("=" * 60)
        
        # Count pass/fail results
        total_tests = 0
        passed_tests = 0
        
        core_tests = ["extra_point_rate", "short_fg_rate", "medium_fg_rate", 
                      "long_fg_rate", "overall_fg_rate", "block_rate"]
        
        print("\n🎯 CORE NFL BENCHMARKS SUMMARY:")
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
        additional_tests = ["distance_correlation", "extreme_distance", "pressure_situation"]
        print("\n⚡ SITUATIONAL PERFORMANCE:")
        print("-" * 30)
        
        for test_name in additional_tests:
            if test_name in self.results:
                result = self.results[test_name]
                total_tests += 1
                
                if test_name == "distance_correlation":
                    passes = result["passes_correlation_test"]
                elif test_name == "extreme_distance":
                    passes = result["passes_realism_test"]
                elif test_name == "pressure_situation":
                    passes = result["passes_pressure_test"]
                else:
                    passes = False
                
                if passes:
                    passed_tests += 1
                
                status = "✅ PASS" if passes else "❌ FAIL"
                print(f"{test_name.replace('_', ' ').title():20}: {status}")
        
        # System tests
        print("\n🔧 SYSTEM VALIDATION:")
        print("-" * 20)
        
        system_tests = ["environmental_consistency", "team_rating_correlation"]
        for test_name in system_tests:
            if test_name in self.results:
                result = self.results[test_name]
                total_tests += 1
                
                if test_name == "environmental_consistency":
                    passes = result["passes_consistency_test"]
                elif test_name == "team_rating_correlation":
                    passes = result["passes_correlation_test"]
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
        print(f"Total Simulations: {self.config.large_sample_size + self.config.medium_sample_size * 3:,}")
        
        if success_rate >= 80:
            print("🎉 EXCELLENT: Algorithm produces highly realistic NFL kicking statistics!")
        elif success_rate >= 60:
            print("✅ GOOD: Algorithm produces acceptable NFL kicking statistics")
        else:
            print("❌ POOR: Algorithm needs significant tuning to match NFL statistics")
        
        print("\n💡 Algorithm Status: Ready for production use" if success_rate >= 70 else "⚠️  Algorithm Status: Requires tuning")
        print("=" * 60)


def main():
    """Run the complete NFL kicking benchmarking suite"""
    
    print("Starting NFL Kick Algorithm Benchmarking...")
    print("This may take several minutes due to large sample sizes.\n")
    
    # Create and run benchmarking suite
    config = TestConfiguration()
    benchmark_suite = NFLKickBenchmarkSuite(config)
    
    try:
        results = benchmark_suite.run_comprehensive_benchmark()
        
        # Export results for further analysis
        import json
        with open("nfl_kick_benchmark_results.json", "w") as f:
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
        
        print(f"\n📁 Detailed results exported to: nfl_kick_benchmark_results.json")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Benchmarking failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()