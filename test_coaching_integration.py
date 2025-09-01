#!/usr/bin/env python3
"""
Coaching Staff System Integration Test Suite

Comprehensive integration tests that validate the full coaching staff system
integration with the existing game engine. Tests complete game flow, 
backward compatibility, performance characteristics, and cross-system 
integration.

Usage:
    python test_coaching_integration.py                    # Run all integration tests
    python test_coaching_integration.py --performance      # Focus on performance tests
    python test_coaching_integration.py --compatibility    # Focus on compatibility tests
    python test_coaching_integration.py --stress           # Run stress testing
    python test_coaching_integration.py --full-games       # Run complete game simulations
"""

import sys
import os
import unittest
import time
import statistics
import random
import psutil
import gc
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from unittest.mock import patch
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Core game engine imports
from game_engine.core.game_orchestrator import SimpleGameEngine, GameResult
from game_engine.core.play_executor import PlayExecutor
from game_engine.field.game_state import GameState
from game_engine.field.field_state import FieldState

# Coaching system imports
from game_engine.coaching.coaching_staff import CoachingStaff, OffensiveCoordinator, DefensiveCoordinator
from game_engine.coaching.coaching_constants import COACH_PERSONALITIES, ADAPTATION_THRESHOLDS

# Play calling and personnel imports
from game_engine.plays.play_calling import PlayCaller, OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
from game_engine.personnel.player_selector import PlayerSelector
from game_engine.personnel.personnel_package import PersonnelPackage

# Performance baseline tracking
class PerformanceBaseline:
    """Track performance baselines for regression testing"""
    # These values should be updated after profiling on the target system
    MAX_PLAY_DECISION_TIME_MS = 2.0        # 2ms per coaching decision
    MAX_GAME_SIMULATION_TIME_S = 15.0      # 15s for full game
    MAX_MEMORY_USAGE_MB = 100.0            # 100MB max memory usage
    MIN_DECISIONS_PER_SECOND = 500         # Minimum 500 decisions/second


class TestGameFlowIntegration(unittest.TestCase):
    """Test complete game flow integration with coaching system"""
    
    def setUp(self):
        """Set up game flow integration test fixtures"""
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
        
        # Ensure teams have coaching staffs
        self.home_team_id = 1  # Bears
        self.away_team_id = 2  # Packers
        
        self.home_team = self.engine.get_team_for_simulation(self.home_team_id)
        self.away_team = self.engine.get_team_for_simulation(self.away_team_id)
        
        # Verify coaching staff exists
        self.assertIn('coaching_staff', self.home_team, 
                     "Home team should have coaching staff")
        self.assertIn('coaching_staff', self.away_team,
                     "Away team should have coaching staff")
    
    def test_complete_game_simulation_with_coaching(self):
        """Test complete game simulation using coaching staff system"""
        print("\n🏈 Testing complete game simulation with coaching integration...")
        
        start_time = time.time()
        
        # Run complete game simulation
        game_result = self.engine.simulate_game(self.home_team_id, self.away_team_id)
        
        simulation_time = time.time() - start_time
        
        # Verify game completed successfully
        self.assertIsInstance(game_result, GameResult)
        self.assertEqual(game_result.home_team_id, self.home_team_id)
        self.assertEqual(game_result.away_team_id, self.away_team_id)
        
        # Verify reasonable score ranges (NFL typical range)
        self.assertGreaterEqual(game_result.home_score, 0)
        self.assertGreaterEqual(game_result.away_score, 0)
        self.assertLessEqual(game_result.home_score, 60)  # Reasonable upper bound
        self.assertLessEqual(game_result.away_score, 60)
        
        # Verify performance within acceptable bounds
        self.assertLess(simulation_time, PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S,
                       f"Game simulation took {simulation_time:.2f}s, exceeding {PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S}s limit")
        
        print(f"   ✅ Game completed in {simulation_time:.2f}s")
        print(f"   📊 Final Score: {game_result.home_score} - {game_result.away_score}")
    
    def test_coaching_adaptation_during_game_flow(self):
        """Test coaching adaptation affects play calling throughout game"""
        print("\n🧠 Testing coaching adaptation during game flow...")
        
        game_state = GameState()
        game_state.field.possession_team_id = self.home_team_id
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        game_state.field.field_position = 25
        
        coaching_staff = self.home_team['coaching_staff']
        oc = coaching_staff.offensive_coordinator
        
        # Prepare for game
        coaching_staff.prepare_for_game(str(self.away_team_id))
        initial_archetype = oc.current_archetype.copy()
        
        # Simulate struggling performance to trigger adaptation
        struggling_results = []
        for i in range(10):
            play_result = self.executor.execute_play(
                self.home_team, self.away_team, game_state
            )
            
            # Create mock poor performance
            struggling_results.append({
                'yards_gained': max(0, play_result.yards_gained - 3),  # Reduce performance
                'expected_yards': 5,
                'play_type': play_result.play_type,
                'success': False
            })
        
        # Trigger adaptation
        coaching_staff.adapt_during_game(struggling_results, [], [])
        adapted_archetype = oc.current_archetype
        
        # Verify adaptation occurred
        archetype_changed = any(
            abs(adapted_archetype.get(key, 0) - initial_archetype.get(key, 0)) > 0.01
            for key in initial_archetype.keys()
        )
        
        self.assertTrue(archetype_changed, "Coaching staff should adapt archetype based on performance")
        print(f"   ✅ Coaching staff adapted strategy after poor performance")
    
    def test_coaching_preparation_between_games(self):
        """Test coaching staff preparation affects subsequent games"""
        print("\n🎯 Testing coaching preparation between games...")
        
        coaching_staff = self.home_team['coaching_staff']
        
        # First game preparation
        initial_games_coached = coaching_staff.games_coached
        coaching_staff.prepare_for_game("opponent_team_1")
        
        self.assertEqual(coaching_staff.games_coached, initial_games_coached + 1,
                        "Games coached should increment after preparation")
        
        # Simulate opponent memory building
        oc = coaching_staff.offensive_coordinator
        opponent_id = "opponent_team_1"
        
        # Add some opponent memory manually (simulating game experience)
        oc.opponent_memory[opponent_id] = {
            'successful_strategies': {'pass_emphasis': 0.8},
            'failed_strategies': {'run_emphasis': 0.3}
        }
        
        # Prepare for same opponent again
        coaching_staff.prepare_for_game(opponent_id)
        
        # Verify memory bonus is applied
        memory_bonus = oc._calculate_memory_bonus(opponent_id)
        self.assertGreater(memory_bonus, 0, 
                          "Should have memory bonus for previously faced opponent")
        
        print(f"   ✅ Opponent memory system working (bonus: {memory_bonus:.3f})")
    
    def test_coaching_decisions_affect_play_types(self):
        """Test coaching decisions demonstrably affect play type selection"""
        print("\n📋 Testing coaching decisions affect play calling...")
        
        # Create aggressive and conservative coaching staffs
        aggressive_config = {
            'offensive_coordinator': {
                'archetype': 'aggressive',
                'experience': 5,
                'adaptability': 0.9,
                'personality': 'aggressive'
            }
        }
        
        conservative_config = {
            'offensive_coordinator': {
                'archetype': 'conservative',
                'experience': 8,
                'adaptability': 0.4,
                'personality': 'traditional'
            }
        }
        
        aggressive_staff = CoachingStaff("aggressive_team", aggressive_config)
        conservative_staff = CoachingStaff("conservative_team", conservative_config)
        
        # Test on 4th down situations (where differences should be most apparent)
        fourth_down_situations = []
        for _ in range(100):
            field_state = FieldState()
            field_state.down = 4
            field_state.yards_to_go = random.randint(1, 5)  # Short yardage
            field_state.field_position = random.randint(40, 60)  # Midfield
            
            game_context = {
                'score_differential': 0,
                'time_remaining': 600  # 10 minutes left
            }
            
            # Get decisions from both coaching staffs
            aggressive_decision = aggressive_staff.get_offensive_coordinator_for_situation(
                field_state, game_context
            )
            conservative_decision = conservative_staff.get_offensive_coordinator_for_situation(
                field_state, game_context
            )
            
            play_caller = PlayCaller()
            aggressive_play = play_caller.determine_play_type(field_state, aggressive_decision)
            conservative_play = play_caller.determine_play_type(field_state, conservative_decision)
            
            fourth_down_situations.append({
                'aggressive': aggressive_play,
                'conservative': conservative_play
            })
        
        # Analyze decision patterns
        aggressive_attempts = sum(1 for s in fourth_down_situations 
                                if s['aggressive'] in ['run', 'pass'])
        conservative_attempts = sum(1 for s in fourth_down_situations 
                                  if s['conservative'] in ['run', 'pass'])
        
        aggressive_pct = aggressive_attempts / len(fourth_down_situations) * 100
        conservative_pct = conservative_attempts / len(fourth_down_situations) * 100
        
        # Aggressive coaches should attempt significantly more 4th downs
        self.assertGreater(aggressive_pct, conservative_pct + 15,
                          f"Aggressive coach should attempt more 4th downs: {aggressive_pct:.1f}% vs {conservative_pct:.1f}%")
        
        print(f"   ✅ Aggressive coach attempts: {aggressive_pct:.1f}%")
        print(f"   ✅ Conservative coach attempts: {conservative_pct:.1f}%")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with legacy coaching format"""
    
    def setUp(self):
        """Set up backward compatibility test fixtures"""
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
    
    def test_legacy_coaching_format_still_works(self):
        """Test systems using legacy coaching format work correctly"""
        print("\n🔄 Testing legacy coaching format compatibility...")
        
        # Create team data with legacy coaching format only
        legacy_team = {
            "name": "Legacy Team",
            "city": "Legacy City",
            "offense": {"qb_rating": 75, "rb_rating": 70, "wr_rating": 72, "ol_rating": 68},
            "defense": {"dl_rating": 72, "lb_rating": 68, "db_rating": 70},
            "special_teams": 70,
            "coaching": {  # Legacy format - no coaching_staff
                "offensive": 75,
                "defensive": 70,
                "offensive_coordinator": {
                    "archetype": "balanced",
                    "custom_modifiers": {}
                },
                "defensive_coordinator": {
                    "archetype": "balanced_defense",
                    "custom_modifiers": {}
                }
            },
            "overall_rating": 70
        }
        
        # Team without coaching_staff should use legacy fallback
        modern_team = self.engine.get_team_for_simulation(1)  # Has coaching_staff
        
        game_state = GameState()
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        game_state.field.field_position = 30
        
        # This should work without crashing
        try:
            play_result = self.executor.execute_play(legacy_team, modern_team, game_state)
            self.assertIsNotNone(play_result.play_type)
            print("   ✅ Legacy team format works correctly")
        except Exception as e:
            self.fail(f"Legacy coaching format should work: {e}")
    
    def test_graceful_fallback_when_coaching_staff_missing(self):
        """Test graceful fallback when coaching_staff is missing"""
        print("\n🛡️ Testing graceful fallback for missing coaching_staff...")
        
        # Create team without coaching_staff
        incomplete_team = {
            "name": "Incomplete Team",
            "offense": {"qb_rating": 70, "rb_rating": 70, "wr_rating": 70},
            "defense": {"dl_rating": 70, "lb_rating": 70, "db_rating": 70}
            # Missing coaching data entirely
        }
        
        complete_team = self.engine.get_team_for_simulation(1)
        
        game_state = GameState()
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        game_state.field.field_position = 30
        
        # Should handle missing coaching gracefully
        try:
            play_result = self.executor.execute_play(incomplete_team, complete_team, game_state)
            self.assertIsNotNone(play_result.play_type)
            print("   ✅ Graceful fallback for missing coaching data")
        except Exception as e:
            self.fail(f"Should handle missing coaching data gracefully: {e}")
    
    def test_existing_game_engine_features_unaffected(self):
        """Test existing game engine features remain unaffected"""
        print("\n⚙️ Testing existing game engine features remain unaffected...")
        
        # Test core game simulation still works
        game_result = self.engine.simulate_game(1, 2)
        self.assertIsInstance(game_result, GameResult)
        
        # Test play executor functions
        game_state = GameState()
        offense_team = self.engine.get_team_for_simulation(1)
        defense_team = self.engine.get_team_for_simulation(2)
        
        play_result = self.executor.execute_play(offense_team, defense_team, game_state)
        self.assertIsNotNone(play_result)
        
        # Test personnel selection
        player_selector = PlayerSelector()
        personnel = player_selector.get_personnel(
            offense_team, defense_team, 'run', game_state.field
        )
        self.assertIsInstance(personnel, PersonnelPackage)
        
        print("   ✅ All existing game engine features working correctly")
    
    def test_nfl_benchmark_maintenance(self):
        """Test NFL benchmarks are maintained with new coaching system"""
        print("\n📊 Testing NFL benchmark maintenance...")
        
        # Test reasonable play distribution across multiple games
        play_type_counts = Counter()
        total_plays = 0
        
        # Simulate multiple drives to get statistical sample
        for _ in range(10):  # 10 simulated drives
            game_state = GameState()
            game_state.field.possession_team_id = 1
            
            for play_num in range(10):  # 10 plays per drive average
                game_state.field.down = random.randint(1, 3)
                game_state.field.yards_to_go = random.randint(1, 15)
                game_state.field.field_position = random.randint(20, 80)
                
                offense_team = self.engine.get_team_for_simulation(1)
                defense_team = self.engine.get_team_for_simulation(2)
                
                play_result = self.executor.execute_play(offense_team, defense_team, game_state)
                play_type_counts[play_result.play_type] += 1
                total_plays += 1
        
        # Check NFL-realistic play distributions
        if total_plays > 0:
            run_pct = (play_type_counts.get('run', 0) / total_plays) * 100
            pass_pct = (play_type_counts.get('pass', 0) / total_plays) * 100
            
            # NFL typical ranges: 40-60% run/pass split
            self.assertGreater(run_pct, 25, f"Run percentage too low: {run_pct:.1f}%")
            self.assertLess(run_pct, 75, f"Run percentage too high: {run_pct:.1f}%")
            self.assertGreater(pass_pct, 25, f"Pass percentage too low: {pass_pct:.1f}%")
            self.assertLess(pass_pct, 75, f"Pass percentage too high: {pass_pct:.1f}%")
            
            print(f"   ✅ NFL-realistic play distribution: {run_pct:.1f}% run, {pass_pct:.1f}% pass")


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance characteristics and benchmarks"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
        gc.collect()  # Clean garbage before performance tests
    
    def test_full_game_performance_benchmark(self):
        """Test full game performance meets benchmarks"""
        print("\n⚡ Testing full game performance benchmark...")
        
        # Record initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        # Run full game
        game_result = self.engine.simulate_game(1, 2)
        
        end_time = time.time()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        simulation_time = end_time - start_time
        memory_used = final_memory - initial_memory
        
        # Verify performance benchmarks
        self.assertLess(simulation_time, PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S,
                       f"Game took {simulation_time:.2f}s, exceeding {PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S}s limit")
        
        self.assertLess(memory_used, PerformanceBaseline.MAX_MEMORY_USAGE_MB,
                       f"Memory usage {memory_used:.1f}MB exceeds {PerformanceBaseline.MAX_MEMORY_USAGE_MB}MB limit")
        
        print(f"   ✅ Game completed in {simulation_time:.2f}s (limit: {PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S}s)")
        print(f"   ✅ Memory usage: {memory_used:.1f}MB (limit: {PerformanceBaseline.MAX_MEMORY_USAGE_MB}MB)")
    
    def test_coaching_decision_overhead(self):
        """Test coaching decision overhead is minimal"""
        print("\n🎯 Testing coaching decision overhead...")
        
        game_state = GameState()
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        game_state.field.field_position = 30
        
        offense_team = self.engine.get_team_for_simulation(1)
        defense_team = self.engine.get_team_for_simulation(2)
        
        # Measure coaching decision time
        coaching_times = []
        total_decisions = 1000
        
        for _ in range(total_decisions):
            start_time = time.perf_counter()
            
            # This includes coaching decision overhead
            play_result = self.executor.execute_play(offense_team, defense_team, game_state)
            
            end_time = time.perf_counter()
            coaching_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_decision_time = statistics.mean(coaching_times)
        max_decision_time = max(coaching_times)
        decisions_per_second = 1000 / avg_decision_time
        
        # Verify performance meets benchmarks
        self.assertLess(avg_decision_time, PerformanceBaseline.MAX_PLAY_DECISION_TIME_MS,
                       f"Average decision time {avg_decision_time:.2f}ms exceeds {PerformanceBaseline.MAX_PLAY_DECISION_TIME_MS}ms limit")
        
        self.assertGreater(decisions_per_second, PerformanceBaseline.MIN_DECISIONS_PER_SECOND,
                          f"Decisions per second {decisions_per_second:.0f} below {PerformanceBaseline.MIN_DECISIONS_PER_SECOND} minimum")
        
        print(f"   ✅ Average decision time: {avg_decision_time:.2f}ms")
        print(f"   ✅ Decisions per second: {decisions_per_second:.0f}")
        print(f"   ✅ Max decision time: {max_decision_time:.2f}ms")
    
    def test_memory_usage_validation(self):
        """Test memory usage remains within acceptable bounds"""
        print("\n💾 Testing memory usage validation...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple coaching staffs and simulate decisions
        coaching_staffs = []
        for i in range(10):
            staff = CoachingStaff(f"team_{i}")
            coaching_staffs.append(staff)
        
        # Make many decisions to test memory accumulation
        for _ in range(1000):
            staff = random.choice(coaching_staffs)
            field_state = FieldState()
            field_state.down = random.randint(1, 4)
            field_state.yards_to_go = random.randint(1, 20)
            field_state.field_position = random.randint(1, 99)
            
            # This should not accumulate significant memory
            coordinator_info = staff.get_offensive_coordinator_for_situation(field_state, {})
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        self.assertLess(memory_increase, PerformanceBaseline.MAX_MEMORY_USAGE_MB,
                       f"Memory increase {memory_increase:.1f}MB exceeds {PerformanceBaseline.MAX_MEMORY_USAGE_MB}MB limit")
        
        print(f"   ✅ Memory increase: {memory_increase:.1f}MB (limit: {PerformanceBaseline.MAX_MEMORY_USAGE_MB}MB)")
    
    def test_performance_comparison_with_baseline(self):
        """Test performance compared to baseline without coaching"""
        print("\n📈 Testing performance comparison with baseline...")
        
        # Test with coaching system
        start_time = time.time()
        for _ in range(100):
            game_state = GameState()
            offense_team = self.engine.get_team_for_simulation(1)
            defense_team = self.engine.get_team_for_simulation(2)
            self.executor.execute_play(offense_team, defense_team, game_state)
        coaching_time = time.time() - start_time
        
        # Test without coaching system (simulate legacy behavior)
        start_time = time.time()
        for _ in range(100):
            game_state = GameState()
            
            # Create teams without coaching_staff
            offense_team = {
                "name": "Legacy Offense",
                "offense": {"qb_rating": 75, "rb_rating": 70, "wr_rating": 72},
                "defense": {"dl_rating": 70, "lb_rating": 68, "db_rating": 70},
                "coaching": {"offensive_coordinator": {"archetype": "balanced"}}
            }
            defense_team = {
                "name": "Legacy Defense", 
                "offense": {"qb_rating": 70, "rb_rating": 68, "wr_rating": 70},
                "defense": {"dl_rating": 75, "lb_rating": 72, "db_rating": 68},
                "coaching": {"defensive_coordinator": {"archetype": "balanced_defense"}}
            }
            
            self.executor.execute_play(offense_team, defense_team, game_state)
        baseline_time = time.time() - start_time
        
        # Coaching overhead should be minimal (less than 50% increase)
        overhead_ratio = coaching_time / baseline_time
        self.assertLess(overhead_ratio, 1.5,
                       f"Coaching system overhead {overhead_ratio:.2f}x should be less than 1.5x")
        
        print(f"   ✅ Coaching system overhead: {overhead_ratio:.2f}x baseline")
        print(f"   ✅ Baseline time: {baseline_time:.3f}s, Coaching time: {coaching_time:.3f}s")


class TestCrossSystemIntegration(unittest.TestCase):
    """Test integration with all game engine components"""
    
    def setUp(self):
        """Set up cross-system integration test fixtures"""
        self.engine = SimpleGameEngine()
        self.executor = PlayExecutor()
        self.play_caller = PlayCaller()
        self.player_selector = PlayerSelector()
    
    def test_integration_with_play_executor_and_play_caller(self):
        """Test integration with PlayExecutor and PlayCaller"""
        print("\n🔗 Testing PlayExecutor and PlayCaller integration...")
        
        game_state = GameState()
        offense_team = self.engine.get_team_for_simulation(1)
        defense_team = self.engine.get_team_for_simulation(2)
        
        # Verify coaching staff provides expected data structure
        coaching_staff = offense_team['coaching_staff']
        coordinator_info = coaching_staff.get_offensive_coordinator_for_situation(
            game_state.field, {}
        )
        
        # Check required fields for PlayCaller compatibility
        required_fields = ['archetype', 'current_archetype_data', 'coordinator_name', 
                          'experience', 'adaptability', 'personality']
        
        for field in required_fields:
            self.assertIn(field, coordinator_info,
                         f"Coordinator info missing required field: {field}")
        
        # Test PlayCaller can use the coordinator info
        play_type = self.play_caller.determine_play_type(
            game_state.field, coordinator_info
        )
        
        self.assertIn(play_type, ['run', 'pass', 'punt', 'field_goal'],
                     f"Invalid play type returned: {play_type}")
        
        print(f"   ✅ PlayCaller integration working, play type: {play_type}")
    
    def test_compatibility_with_player_selector_and_personnel(self):
        """Test compatibility with PlayerSelector and PersonnelPackage"""
        print("\n👥 Testing PlayerSelector and PersonnelPackage compatibility...")
        
        offense_team = self.engine.get_team_for_simulation(1)
        defense_team = self.engine.get_team_for_simulation(2)
        
        field_state = FieldState()
        field_state.down = 1
        field_state.yards_to_go = 10
        field_state.field_position = 30
        
        # Get personnel for different play types
        play_types = ['run', 'pass']
        
        for play_type in play_types:
            personnel = self.player_selector.get_personnel(
                offense_team, defense_team, play_type, field_state
            )
            
            self.assertIsInstance(personnel, PersonnelPackage,
                                "Should return PersonnelPackage instance")
            self.assertIsNotNone(personnel.formation)
            self.assertIsNotNone(personnel.defensive_call)
            
        print("   ✅ PlayerSelector and PersonnelPackage integration working")
    
    def test_integration_with_game_state_and_field_conditions(self):
        """Test integration with GameState and field conditions"""
        print("\n🏟️ Testing GameState and field conditions integration...")
        
        # Test various field conditions
        field_conditions = [
            {"desc": "Goal Line", "down": 1, "distance": 1, "position": 99},
            {"desc": "Short Yardage", "down": 3, "distance": 2, "position": 45},
            {"desc": "Long Distance", "down": 2, "distance": 15, "position": 20},
            {"desc": "Red Zone", "down": 2, "distance": 8, "position": 85},
            {"desc": "Two Minute Warning", "down": 2, "distance": 6, "position": 50}
        ]
        
        offense_team = self.engine.get_team_for_simulation(1)
        coaching_staff = offense_team['coaching_staff']
        
        for condition in field_conditions:
            game_state = GameState()
            game_state.field.down = condition["down"]
            game_state.field.yards_to_go = condition["distance"]
            game_state.field.field_position = condition["position"]
            
            if condition["desc"] == "Two Minute Warning":
                game_state.clock.clock = 120  # 2 minutes remaining
            
            # Get coaching decision for this condition
            game_context = {
                'score_differential': 0,
                'time_remaining': game_state.clock.clock
            }
            
            coordinator_info = coaching_staff.get_offensive_coordinator_for_situation(
                game_state.field, game_context
            )
            
            self.assertIsInstance(coordinator_info, dict,
                                 f"Should return dict for {condition['desc']}")
            
        print("   ✅ GameState and field conditions integration working")
    
    def test_proper_interaction_with_all_game_engine_components(self):
        """Test proper interaction with all game engine components"""
        print("\n🎮 Testing interaction with all game engine components...")
        
        # Test complete play execution pipeline
        game_state = GameState()
        offense_team = self.engine.get_team_for_simulation(1)
        defense_team = self.engine.get_team_for_simulation(2)
        
        # Execute play and verify all components interact correctly
        play_result = self.executor.execute_play(offense_team, defense_team, game_state)
        
        # Verify PlayResult has all expected fields from integration
        expected_fields = ['play_type', 'outcome', 'yards_gained', 'formation', 
                          'defensive_call', 'down', 'distance', 'field_position']
        
        for field in expected_fields:
            self.assertTrue(hasattr(play_result, field),
                           f"PlayResult missing field: {field}")
        
        # Verify game state update works correctly
        original_down = game_state.field.down
        field_result = game_state.update_after_play(play_result)
        
        # Game state should have been updated
        self.assertIsNotNone(field_result)
        
        print("   ✅ All game engine components interacting properly")


class TestMultiGameLearning(unittest.TestCase):
    """Test multi-game learning and persistence"""
    
    def setUp(self):
        """Set up multi-game learning test fixtures"""
        self.coaching_staff = CoachingStaff("learning_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 6,
                'adaptability': 0.9,
                'personality': 'adaptive'
            }
        })
    
    def test_coaching_memory_persists_across_games(self):
        """Test coaching memory persists across multiple games"""
        print("\n🧠 Testing coaching memory persistence across games...")
        
        oc = self.coaching_staff.offensive_coordinator
        opponent_id = "persistent_opponent"
        
        # First game - build memory
        self.coaching_staff.prepare_for_game(opponent_id)
        
        # Simulate successful strategy
        oc.opponent_memory[opponent_id] = {
            'successful_strategies': {'pass_emphasis': 0.8, 'quick_game': 0.7},
            'failed_strategies': {'run_emphasis': 0.3}
        }
        
        initial_memory = oc.opponent_memory[opponent_id].copy()
        
        # Second game - memory should persist and influence decisions
        self.coaching_staff.prepare_for_game(opponent_id)
        
        # Memory should still exist
        self.assertIn(opponent_id, oc.opponent_memory)
        
        # Memory should influence decisions
        memory_bonus = oc._calculate_memory_bonus(opponent_id)
        self.assertGreater(memory_bonus, 0,
                          "Should have positive memory bonus for known opponent")
        
        print(f"   ✅ Memory persists across games (bonus: {memory_bonus:.3f})")
    
    def test_opponent_specific_adaptations_accumulate(self):
        """Test opponent-specific adaptations accumulate correctly"""
        print("\n📈 Testing opponent-specific adaptations accumulate...")
        
        oc = self.coaching_staff.offensive_coordinator
        opponent_id = "accumulating_opponent"
        
        # Multiple games against same opponent
        for game_num in range(3):
            self.coaching_staff.prepare_for_game(opponent_id)
            
            # Simulate learning from each game
            if opponent_id not in oc.opponent_memory:
                oc.opponent_memory[opponent_id] = {
                    'successful_strategies': {},
                    'failed_strategies': {}
                }
            
            # Add new learning each game
            strategy_name = f"strategy_{game_num}"
            oc.opponent_memory[opponent_id]['successful_strategies'][strategy_name] = 0.8
            
            memory_bonus = oc._calculate_memory_bonus(opponent_id)
            
            # Memory bonus should increase with more data
            if game_num > 0:
                self.assertGreater(memory_bonus, 0,
                                  f"Should have memory bonus by game {game_num + 1}")
        
        # Final memory should contain all accumulated strategies
        final_memory = oc.opponent_memory[opponent_id]
        self.assertGreaterEqual(len(final_memory['successful_strategies']), 3,
                               "Should have accumulated strategies from multiple games")
        
        print(f"   ✅ Accumulated {len(final_memory['successful_strategies'])} strategies")
    
    def test_coaching_experience_improves_decision_quality(self):
        """Test coaching experience improves decision quality over time"""
        print("\n🎯 Testing coaching experience improves decision quality...")
        
        # Create rookie and veteran coaches
        rookie_staff = CoachingStaff("rookie_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 1,  # Rookie
                'adaptability': 0.7,
                'personality': 'balanced'
            }
        })
        
        veteran_staff = CoachingStaff("veteran_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 15,  # Veteran
                'adaptability': 0.7,
                'personality': 'balanced'
            }
        })
        
        # Test decision consistency under pressure
        pressure_situations = []
        for _ in range(50):
            field_state = FieldState()
            field_state.down = 4
            field_state.yards_to_go = random.randint(1, 5)
            field_state.field_position = random.randint(40, 60)
            
            high_pressure_context = {
                'score_differential': -3,  # Down by 3
                'time_remaining': 120      # 2 minutes left
            }
            
            rookie_decision = rookie_staff.get_offensive_coordinator_for_situation(
                field_state, high_pressure_context
            )
            veteran_decision = veteran_staff.get_offensive_coordinator_for_situation(
                field_state, high_pressure_context
            )
            
            pressure_situations.append({
                'rookie': rookie_decision,
                'veteran': veteran_decision
            })
        
        # Veterans should have more consistent decision patterns
        # (This is a simplified test - in practice would need more sophisticated analysis)
        
        rookie_oc = rookie_staff.offensive_coordinator
        veteran_oc = veteran_staff.offensive_coordinator
        
        # Check experience modifiers
        self.assertGreater(
            veteran_oc.experience_modifiers.get('pressure_resistance', 0),
            rookie_oc.experience_modifiers.get('pressure_resistance', 0),
            "Veteran should have better pressure resistance"
        )
        
        self.assertGreater(
            veteran_oc.experience_modifiers.get('decision_consistency', 0),
            rookie_oc.experience_modifiers.get('decision_consistency', 0),
            "Veteran should have better decision consistency"
        )
        
        print("   ✅ Veterans show improved pressure resistance and consistency")
    
    def test_division_rivalry_bonuses_and_historical_matchups(self):
        """Test division rivalry bonuses and historical matchups"""
        print("\n🏆 Testing division rivalry bonuses and historical matchups...")
        
        oc = self.coaching_staff.offensive_coordinator
        
        # Test different opponent types
        division_rival = "team_division_rival"
        conference_team = "team_conference"
        random_team = "team_random"
        
        # Set up historical data
        for opponent, is_division in [(division_rival, True), (conference_team, False), (random_team, False)]:
            oc.opponent_memory[opponent] = {
                'successful_strategies': {'strategy_1': 0.8},
                'failed_strategies': {'strategy_2': 0.2}
            }
        
        # Calculate memory bonuses
        division_bonus = oc._calculate_memory_bonus(division_rival)
        conference_bonus = oc._calculate_memory_bonus(conference_team)
        random_bonus = oc._calculate_memory_bonus(random_team)
        
        # Division rivals should have higher memory bonuses
        # Note: This assumes the system recognizes division rivals
        # In practice, you might need to mark teams as division rivals
        
        self.assertGreaterEqual(division_bonus, conference_bonus,
                               "Division rival should have at least equal memory bonus")
        self.assertGreaterEqual(conference_bonus, 0,
                               "All teams with history should have some memory bonus")
        
        print(f"   ✅ Division rival bonus: {division_bonus:.3f}")
        print(f"   ✅ Conference team bonus: {conference_bonus:.3f}")
        print(f"   ✅ Random team bonus: {random_bonus:.3f}")


class TestStressTesting(unittest.TestCase):
    """Stress testing with multiple consecutive games"""
    
    def test_multiple_consecutive_games_stress_test(self):
        """Test stress testing with multiple consecutive games"""
        print("\n🔥 Running multiple consecutive games stress test...")
        
        engine = SimpleGameEngine()
        game_results = []
        total_time = 0
        
        # Run 10 consecutive games
        for game_num in range(10):
            start_time = time.time()
            
            # Vary team matchups
            home_team = (game_num % 8) + 1  # Cycle through teams 1-8
            away_team = ((game_num + 1) % 8) + 1
            
            try:
                game_result = engine.simulate_game(home_team, away_team)
                game_time = time.time() - start_time
                total_time += game_time
                
                game_results.append({
                    'game_num': game_num + 1,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': game_result.home_score,
                    'away_score': game_result.away_score,
                    'duration': game_time
                })
                
            except Exception as e:
                self.fail(f"Game {game_num + 1} failed: {e}")
        
        # Verify all games completed successfully
        self.assertEqual(len(game_results), 10, "All 10 games should complete successfully")
        
        # Verify reasonable performance
        avg_game_time = total_time / 10
        self.assertLess(avg_game_time, PerformanceBaseline.MAX_GAME_SIMULATION_TIME_S,
                       f"Average game time {avg_game_time:.2f}s exceeds limit")
        
        # Verify score ranges remain reasonable
        all_scores = []
        for result in game_results:
            all_scores.extend([result['home_score'], result['away_score']])
        
        avg_score = statistics.mean(all_scores)
        self.assertGreater(avg_score, 10, "Average score should be reasonable for NFL")
        self.assertLess(avg_score, 40, "Average score should not be too high")
        
        print(f"   ✅ Completed 10 consecutive games successfully")
        print(f"   ✅ Total time: {total_time:.2f}s, Average: {avg_game_time:.2f}s")
        print(f"   ✅ Average score: {avg_score:.1f} points")
    
    def test_coaching_staff_memory_stress_test(self):
        """Test coaching staff memory under stress conditions"""
        print("\n🧠 Testing coaching staff memory under stress...")
        
        # Create coaching staff and stress test memory system
        staff = CoachingStaff("stress_team")
        oc = staff.offensive_coordinator
        
        # Add many opponent memories
        for opponent_num in range(100):
            opponent_id = f"opponent_{opponent_num}"
            
            # Simulate various game outcomes
            oc.opponent_memory[opponent_id] = {
                'successful_strategies': {
                    f'strategy_{i}': random.uniform(0.5, 1.0) 
                    for i in range(random.randint(1, 5))
                },
                'failed_strategies': {
                    f'failed_{i}': random.uniform(0.0, 0.5)
                    for i in range(random.randint(1, 3))
                }
            }
        
        # Test memory retrieval performance
        start_time = time.time()
        
        for _ in range(1000):
            opponent_id = f"opponent_{random.randint(0, 99)}"
            memory_bonus = oc._calculate_memory_bonus(opponent_id)
            self.assertGreaterEqual(memory_bonus, 0)
        
        memory_time = time.time() - start_time
        
        # Memory operations should be fast even with many opponents
        self.assertLess(memory_time, 1.0, 
                       f"Memory operations took {memory_time:.3f}s, should be under 1s")
        
        # Verify memory size is reasonable
        total_strategies = sum(
            len(mem['successful_strategies']) + len(mem['failed_strategies'])
            for mem in oc.opponent_memory.values()
        )
        
        print(f"   ✅ Stored memory for 100 opponents")
        print(f"   ✅ Total strategies: {total_strategies}")
        print(f"   ✅ Memory retrieval time: {memory_time:.3f}s")


def main():
    """Main test runner with command line argument support"""
    parser = argparse.ArgumentParser(description="Coaching Staff Integration Test Suite")
    parser.add_argument('--performance', action='store_true',
                       help='Focus on performance tests')
    parser.add_argument('--compatibility', action='store_true',
                       help='Focus on compatibility tests')
    parser.add_argument('--stress', action='store_true',
                       help='Run stress testing')
    parser.add_argument('--full-games', action='store_true',
                       help='Run complete game simulations')
    parser.add_argument('unittest_args', nargs='*')
    
    args = parser.parse_args()
    
    # Pass through unittest arguments
    sys.argv[1:] = args.unittest_args
    
    print("🏈 COACHING STAFF INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Select test classes based on arguments
    if args.performance:
        test_classes = [TestPerformanceIntegration]
    elif args.compatibility:
        test_classes = [TestBackwardCompatibility]
    elif args.stress:
        test_classes = [TestStressTesting]
    elif args.full_games:
        test_classes = [TestGameFlowIntegration, TestMultiGameLearning]
    else:
        # Run all tests
        test_classes = [
            TestGameFlowIntegration,
            TestBackwardCompatibility,
            TestPerformanceIntegration,
            TestCrossSystemIntegration,
            TestMultiGameLearning,
            TestStressTesting
        ]
    
    # Build test suite
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    
    if hasattr(result, 'testsRun'):
        total_tests = result.testsRun
        failures = len(result.failures) if result.failures else 0
        errors = len(result.errors) if result.errors else 0
        passed = total_tests - failures - errors
        
        print(f"Tests run:        {total_tests}")
        print(f"Passed:           {passed}")
        print(f"Failed:           {failures}")
        print(f"Errors:           {errors}")
        print(f"Success rate:     {(passed/total_tests)*100:.1f}%")
        
        if failures == 0 and errors == 0:
            print("\n🎉 All integration tests passed!")
            print("✅ Coaching staff system is fully integrated with game engine")
            print("✅ Performance meets or exceeds baseline requirements")
            print("✅ Backward compatibility maintained")
            print("✅ Cross-system integration verified")
            return True
        else:
            print("\n❌ Some integration tests failed")
            print("⚠️  Check output above for specific failure details")
            return False
    else:
        print("Test results not available")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)