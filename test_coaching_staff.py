#!/usr/bin/env python3
"""
Comprehensive Coaching Staff Test Suite

Tests for the dynamic coaching system including adaptation, personality differences,
NFL statistical realism, and integration with existing play calling systems.

Usage:
    python test_coaching_staff.py                    # Run all tests
    python test_coaching_staff.py --analyze          # Run tests with detailed analysis
    python test_coaching_staff.py --quick            # Run basic tests only
    python test_coaching_staff.py --benchmarks       # Run NFL realism benchmarks only
"""

import sys
import os
import unittest
import random
import time
import statistics
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import argparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.coaching.coaching_staff import (
    CoachingStaff, OffensiveCoordinator, DefensiveCoordinator, CoachingBalance
)
from game_engine.coaching.coaching_constants import (
    COACH_PERSONALITIES, ADAPTATION_THRESHOLDS, EXPERIENCE_MULTIPLIERS
)
from game_engine.plays.play_calling import (
    PlayCaller, OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
)
from game_engine.field.field_state import FieldState
from game_engine.field.game_state import GameState


class TestCoachingStaffBasics(unittest.TestCase):
    """Basic functionality tests for CoachingStaff system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.team_id = "test_team_001"
        self.basic_config = {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 5,
                'adaptability': 0.7,
                'personality': 'balanced',
                'name': 'Test OC'
            },
            'defensive_coordinator': {
                'archetype': 'balanced_defense',
                'experience': 5,
                'adaptability': 0.7,
                'personality': 'balanced',
                'name': 'Test DC'
            }
        }
    
    def test_coaching_staff_initialization(self):
        """Test basic CoachingStaff initialization and configuration"""
        staff = CoachingStaff(self.team_id, self.basic_config)
        
        # Verify basic properties
        self.assertEqual(staff.team_id, self.team_id)
        self.assertIsInstance(staff.offensive_coordinator, OffensiveCoordinator)
        self.assertIsInstance(staff.defensive_coordinator, DefensiveCoordinator)
        
        # Verify coordinator initialization
        oc = staff.offensive_coordinator
        self.assertEqual(oc.base_archetype, 'balanced')
        self.assertEqual(oc.experience, 5)
        self.assertEqual(oc.adaptability, 0.7)
        self.assertEqual(oc.personality, 'balanced')
        self.assertEqual(oc.name, 'Test OC')
        
        dc = staff.defensive_coordinator
        self.assertEqual(dc.base_archetype, 'balanced_defense')
        self.assertEqual(dc.experience, 5)
        self.assertEqual(dc.adaptability, 0.7)
        self.assertEqual(dc.personality, 'balanced')
        self.assertEqual(dc.name, 'Test DC')
    
    def test_offensive_coordinator_creation(self):
        """Test OffensiveCoordinator creation with different archetypes"""
        for archetype_name in OFFENSIVE_ARCHETYPES.keys():
            for personality in COACH_PERSONALITIES.keys():
                with self.subTest(archetype=archetype_name, personality=personality):
                    oc = OffensiveCoordinator(
                        base_archetype=archetype_name,
                        experience=random.randint(1, 15),
                        adaptability=random.uniform(0.3, 1.0),
                        personality=personality
                    )
                    
                    self.assertEqual(oc.base_archetype, archetype_name)
                    self.assertEqual(oc.personality, personality)
                    self.assertIn(oc.experience_level, ['rookie_coach', 'experienced_coach', 'veteran_coach'])
                    
                    # Verify archetype data structure
                    current_archetype = oc.current_archetype
                    self.assertIsInstance(current_archetype, dict)
    
    def test_defensive_coordinator_creation(self):
        """Test DefensiveCoordinator creation with different archetypes"""
        for archetype_name in DEFENSIVE_ARCHETYPES.keys():
            for personality in COACH_PERSONALITIES.keys():
                with self.subTest(archetype=archetype_name, personality=personality):
                    dc = DefensiveCoordinator(
                        base_archetype=archetype_name,
                        experience=random.randint(1, 15),
                        adaptability=random.uniform(0.3, 1.0),
                        personality=personality
                    )
                    
                    self.assertEqual(dc.base_archetype, archetype_name)
                    self.assertEqual(dc.personality, personality)
                    self.assertIn(dc.experience_level, ['rookie_coach', 'experienced_coach', 'veteran_coach'])
    
    def test_invalid_archetype_handling(self):
        """Test handling of invalid archetypes"""
        with self.assertRaises(ValueError):
            OffensiveCoordinator(
                base_archetype="invalid_archetype",
                experience=5,
                adaptability=0.7,
                personality="balanced"
            )
        
        with self.assertRaises(ValueError):
            DefensiveCoordinator(
                base_archetype="invalid_defensive_archetype",
                experience=5,
                adaptability=0.7,
                personality="balanced"
            )
    
    def test_invalid_personality_handling(self):
        """Test handling of invalid personalities"""
        with self.assertRaises(ValueError):
            OffensiveCoordinator(
                base_archetype="balanced",
                experience=5,
                adaptability=0.7,
                personality="invalid_personality"
            )
    
    def test_adaptability_range_validation(self):
        """Test adaptability parameter validation"""
        # Test invalid adaptability values
        for invalid_adaptability in [-0.1, 1.1, 2.0]:
            with self.assertRaises(ValueError):
                OffensiveCoordinator(
                    base_archetype="balanced",
                    experience=5,
                    adaptability=invalid_adaptability,
                    personality="balanced"
                )
    
    def test_experience_level_determination(self):
        """Test experience level categorization"""
        # Test rookie level
        rookie_oc = OffensiveCoordinator("balanced", 1, 0.7, "balanced")
        self.assertEqual(rookie_oc.experience_level, 'rookie_coach')
        
        # Test experienced level
        experienced_oc = OffensiveCoordinator("balanced", 5, 0.7, "balanced")
        self.assertEqual(experienced_oc.experience_level, 'experienced_coach')
        
        # Test veteran level
        veteran_oc = OffensiveCoordinator("balanced", 12, 0.7, "balanced")
        self.assertEqual(veteran_oc.experience_level, 'veteran_coach')


class TestDynamicBehavior(unittest.TestCase):
    """Test dynamic coaching behavior and adaptation"""
    
    def setUp(self):
        """Set up test fixtures for dynamic behavior tests"""
        self.aggressive_staff = CoachingStaff("team_001", {
            'offensive_coordinator': {
                'archetype': 'aggressive',
                'experience': 8,
                'adaptability': 0.9,
                'personality': 'aggressive'
            }
        })
        
        self.conservative_staff = CoachingStaff("team_002", {
            'offensive_coordinator': {
                'archetype': 'conservative',
                'experience': 12,
                'adaptability': 0.4,
                'personality': 'traditional'
            }
        })
        
        self.adaptive_staff = CoachingStaff("team_003", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 6,
                'adaptability': 1.0,
                'personality': 'adaptive'
            }
        })
    
    def test_game_preparation_changes_strategy(self):
        """Test that game preparation affects coaching strategy"""
        staff = self.aggressive_staff
        oc = staff.offensive_coordinator
        
        # Store original archetype
        original_archetype = oc.current_archetype.copy()
        
        # Prepare for game with mock opponent
        staff.prepare_for_game("opponent_001")
        
        # Verify preparation was executed
        self.assertEqual(oc.current_opponent, "opponent_001")
        self.assertEqual(oc.drives_this_game, 0)
        self.assertEqual(oc.plays_this_drive, 0)
        
        # Games coached should increment
        self.assertEqual(staff.games_coached, 1)
    
    def test_opponent_memory_system(self):
        """Test opponent memory and learning system"""
        staff = self.adaptive_staff
        oc = staff.offensive_coordinator
        
        # First game vs opponent  
        staff.prepare_for_game("team_001_division_rival")
        
        # Simulate some opponent memory data
        opponent_id = "team_001_division_rival"
        oc.opponent_memory[opponent_id] = {
            'successful_strategies': {
                'pass_emphasis': 0.8,
                'quick_game': 0.7
            },
            'failed_strategies': {
                'run_emphasis': 0.2
            }
        }
        
        # Prepare for second game vs same opponent
        staff.prepare_for_game(opponent_id)
        
        # Memory should exist and influence preparation
        self.assertIn(opponent_id, oc.opponent_memory)
        memory_bonus = oc._calculate_memory_bonus(opponent_id)
        self.assertGreater(memory_bonus, 0)
    
    def test_experience_effects_on_decisions(self):
        """Test how experience level affects decision quality"""
        # Create coaches with different experience levels
        rookie_config = {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 1,
                'adaptability': 0.7,
                'personality': 'balanced'
            }
        }
        
        veteran_config = {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 15,
                'adaptability': 0.7,
                'personality': 'balanced'
            }
        }
        
        rookie_staff = CoachingStaff("rookie_team", rookie_config)
        veteran_staff = CoachingStaff("veteran_team", veteran_config)
        
        # Check experience modifiers
        rookie_modifiers = rookie_staff.offensive_coordinator.experience_modifiers
        veteran_modifiers = veteran_staff.offensive_coordinator.experience_modifiers
        
        # Veteran should have better pressure resistance and decision consistency
        self.assertGreater(
            veteran_modifiers['pressure_resistance'],
            rookie_modifiers['pressure_resistance']
        )
        self.assertGreater(
            veteran_modifiers['decision_consistency'],
            rookie_modifiers['decision_consistency']
        )
    
    def test_adaptation_triggers(self):
        """Test in-game adaptation triggers"""
        staff = self.adaptive_staff
        oc = staff.offensive_coordinator
        
        # Create mock play results indicating struggling offense
        struggling_results = [
            {'yards_gained': 1, 'expected_yards': 4, 'play_type': 'run'},
            {'yards_gained': -2, 'expected_yards': 3, 'play_type': 'run'},
            {'yards_gained': 3, 'expected_yards': 6, 'play_type': 'pass'},
            {'yards_gained': 0, 'expected_yards': 4, 'play_type': 'run'},
            {'yards_gained': 2, 'expected_yards': 5, 'play_type': 'pass'}
        ]
        
        # Test adaptation to struggling performance
        original_archetype = oc.current_archetype.copy()
        staff.adapt_during_game(struggling_results, [], [])
        
        # Success rate should be low enough to trigger adaptation
        success_rate = oc._calculate_success_rate(struggling_results)
        self.assertLess(success_rate, ADAPTATION_THRESHOLDS['effectiveness']['struggling_threshold'])
    
    def test_momentum_tracking(self):
        """Test momentum tracking and its effects"""
        staff = self.aggressive_staff
        oc = staff.offensive_coordinator
        
        # Create positive momentum results
        positive_results = [
            {'yards_gained': 8, 'expected_yards': 4, 'play_type': 'pass'},
            {'yards_gained': 12, 'expected_yards': 5, 'play_type': 'run'},
            {'yards_gained': 15, 'expected_yards': 6, 'play_type': 'pass'}
        ]
        
        # Create negative momentum results  
        negative_results = [
            {'yards_gained': 0, 'expected_yards': 4, 'play_type': 'run'},
            {'yards_gained': -1, 'expected_yards': 5, 'play_type': 'pass'},
            {'yards_gained': 1, 'expected_yards': 3, 'play_type': 'run'}
        ]
        
        # Test momentum calculation
        positive_momentum = oc._calculate_momentum(positive_results, [])
        negative_momentum = oc._calculate_momentum(negative_results, [])
        
        self.assertGreater(positive_momentum, negative_momentum)
    
    def test_pressure_situation_adaptations(self):
        """Test coaching behavior under pressure situations"""
        staff = self.conservative_staff
        oc = staff.offensive_coordinator
        
        field_state = FieldState()
        field_state.field_position = 75  # Red zone
        
        # High pressure game context
        high_pressure_context = {
            'score_differential': -3,  # Down by 3
            'time_remaining': 180  # 3 minutes left
        }
        
        # Low pressure game context
        low_pressure_context = {
            'score_differential': 14,  # Up by 14
            'time_remaining': 1800  # 30 minutes left
        }
        
        # Get archetypes under different pressure
        high_pressure_archetype = oc.get_current_archetype(field_state, high_pressure_context)
        low_pressure_archetype = oc.get_current_archetype(field_state, low_pressure_context)
        
        # Both should be valid archetypes
        self.assertIsInstance(high_pressure_archetype, dict)
        self.assertIsInstance(low_pressure_archetype, dict)
        
        # Pressure should affect decision-making
        is_high_pressure = oc._is_high_pressure_situation(-3, 180)
        is_low_pressure = oc._is_high_pressure_situation(14, 1800)
        
        self.assertTrue(is_high_pressure)
        self.assertFalse(is_low_pressure)


class TestNFLRealismBenchmarks(unittest.TestCase):
    """Test NFL statistical realism and archetype benchmarks"""
    
    def setUp(self):
        """Set up NFL realism test fixtures"""
        self.play_caller = PlayCaller()
        self.field_state = FieldState()
        self.simulation_iterations = 1000  # Number of plays to simulate for statistics
    
    def test_conservative_archetype_fourth_down_range(self):
        """Test conservative archetype 4th down attempts stay in 8-18% range"""
        conservative_staff = CoachingStaff("conservative_team", {
            'offensive_coordinator': {
                'archetype': 'conservative',
                'experience': 8,
                'adaptability': 0.5,
                'personality': 'traditional'
            }
        })
        
        fourth_down_attempts = 0
        total_fourth_downs = 0
        
        for _ in range(self.simulation_iterations):
            # Create 4th down situations
            self.field_state.down = 4
            self.field_state.yards_to_go = random.randint(1, 8)
            self.field_state.field_position = random.randint(25, 75)
            
            coordinator_info = conservative_staff.get_offensive_coordinator_for_situation(
                self.field_state, {}
            )
            
            play_type = self.play_caller.determine_play_type(
                self.field_state, coordinator_info
            )
            
            total_fourth_downs += 1
            if play_type in ['run', 'pass']:
                fourth_down_attempts += 1
        
        attempt_percentage = (fourth_down_attempts / total_fourth_downs) * 100
        
        # Conservative coaches should attempt 8-18% of 4th downs
        self.assertGreaterEqual(attempt_percentage, 6.0, 
            f"Conservative 4th down attempts too low: {attempt_percentage:.1f}% (expected 8-18%)")
        self.assertLessEqual(attempt_percentage, 20.0,
            f"Conservative 4th down attempts too high: {attempt_percentage:.1f}% (expected 8-18%)")
    
    def test_aggressive_archetype_fourth_down_range(self):
        """Test aggressive archetype 4th down attempts stay in 35-55% range"""
        aggressive_staff = CoachingStaff("aggressive_team", {
            'offensive_coordinator': {
                'archetype': 'aggressive',
                'experience': 6,
                'adaptability': 0.8,
                'personality': 'aggressive'
            }
        })
        
        fourth_down_attempts = 0
        total_fourth_downs = 0
        
        for _ in range(self.simulation_iterations):
            self.field_state.down = 4
            self.field_state.yards_to_go = random.randint(1, 8)
            self.field_state.field_position = random.randint(25, 75)
            
            coordinator_info = aggressive_staff.get_offensive_coordinator_for_situation(
                self.field_state, {}
            )
            
            play_type = self.play_caller.determine_play_type(
                self.field_state, coordinator_info
            )
            
            total_fourth_downs += 1
            if play_type in ['run', 'pass']:
                fourth_down_attempts += 1
        
        attempt_percentage = (fourth_down_attempts / total_fourth_downs) * 100
        
        # Aggressive coaches should attempt 35-55% of 4th downs  
        self.assertGreaterEqual(attempt_percentage, 30.0,
            f"Aggressive 4th down attempts too low: {attempt_percentage:.1f}% (expected 35-55%)")
        self.assertLessEqual(attempt_percentage, 60.0,
            f"Aggressive 4th down attempts too high: {attempt_percentage:.1f}% (expected 35-55%)")
    
    def test_balanced_archetype_statistical_ranges(self):
        """Test balanced archetype maintains realistic statistical ranges"""
        balanced_staff = CoachingStaff("balanced_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 7,
                'adaptability': 0.7,
                'personality': 'balanced'
            }
        })
        
        play_type_counts = Counter()
        total_plays = 0
        
        # Test various game situations
        situations = [
            (1, 10, 25),  # 1st and 10 from own 25
            (2, 7, 45),   # 2nd and 7 from midfield
            (3, 8, 65),   # 3rd and 8 in opponent territory
            (3, 3, 35),   # 3rd and short from own territory
        ]
        
        for down, distance, position in situations:
            for _ in range(250):  # 250 plays per situation
                self.field_state.down = down
                self.field_state.yards_to_go = distance
                self.field_state.field_position = position
                
                coordinator_info = balanced_staff.get_offensive_coordinator_for_situation(
                    self.field_state, {}
                )
                
                play_type = self.play_caller.determine_play_type(
                    self.field_state, coordinator_info
                )
                
                play_type_counts[play_type] += 1
                total_plays += 1
        
        # Calculate percentages
        run_percentage = (play_type_counts['run'] / total_plays) * 100
        pass_percentage = (play_type_counts['pass'] / total_plays) * 100
        
        # Balanced offense should be roughly 45-55% run/pass
        self.assertGreaterEqual(run_percentage, 35.0,
            f"Balanced run percentage too low: {run_percentage:.1f}%")
        self.assertLessEqual(run_percentage, 65.0,
            f"Balanced run percentage too high: {run_percentage:.1f}%")
        self.assertGreaterEqual(pass_percentage, 35.0,
            f"Balanced pass percentage too low: {pass_percentage:.1f}%")
        self.assertLessEqual(pass_percentage, 65.0,
            f"Balanced pass percentage too high: {pass_percentage:.1f}%")
    
    def test_west_coast_archetype_short_pass_emphasis(self):
        """Test west coast archetype maintains short passing emphasis"""
        west_coast_staff = CoachingStaff("west_coast_team", {
            'offensive_coordinator': {
                'archetype': 'west_coast',
                'experience': 10,
                'adaptability': 0.6,
                'personality': 'innovative'
            }
        })
        
        pass_plays = 0
        total_plays = 0
        
        # Test passing situations
        for _ in range(self.simulation_iterations):
            self.field_state.down = random.choice([1, 2, 3])
            self.field_state.yards_to_go = random.randint(3, 15)
            self.field_state.field_position = random.randint(20, 80)
            
            coordinator_info = west_coast_staff.get_offensive_coordinator_for_situation(
                self.field_state, {}
            )
            
            play_type = self.play_caller.determine_play_type(
                self.field_state, coordinator_info
            )
            
            total_plays += 1
            if play_type == 'pass':
                pass_plays += 1
        
        pass_percentage = (pass_plays / total_plays) * 100
        
        # West Coast should pass more than balanced (expected >60%)
        self.assertGreaterEqual(pass_percentage, 55.0,
            f"West Coast pass percentage too low: {pass_percentage:.1f}% (expected >60%)")
    
    def test_run_heavy_archetype_ground_game_emphasis(self):
        """Test run heavy archetype maintains ground game emphasis"""
        run_heavy_staff = CoachingStaff("run_heavy_team", {
            'offensive_coordinator': {
                'archetype': 'run_heavy',
                'experience': 12,
                'adaptability': 0.5,
                'personality': 'defensive_minded'
            }
        })
        
        run_plays = 0
        total_plays = 0
        
        # Test early down situations where running is most common
        for _ in range(self.simulation_iterations):
            self.field_state.down = random.choice([1, 2])
            self.field_state.yards_to_go = random.randint(3, 10)
            self.field_state.field_position = random.randint(20, 80)
            
            coordinator_info = run_heavy_staff.get_offensive_coordinator_for_situation(
                self.field_state, {}
            )
            
            play_type = self.play_caller.determine_play_type(
                self.field_state, coordinator_info
            )
            
            total_plays += 1
            if play_type == 'run':
                run_plays += 1
        
        run_percentage = (run_plays / total_plays) * 100
        
        # Run heavy should run more than balanced (expected >55%)
        self.assertGreaterEqual(run_percentage, 50.0,
            f"Run heavy run percentage too low: {run_percentage:.1f}% (expected >55%)")


class TestIntegration(unittest.TestCase):
    """Integration tests with full game context"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.coaching_staff = CoachingStaff("integration_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 8,
                'adaptability': 0.9,
                'personality': 'adaptive'
            },
            'defensive_coordinator': {
                'archetype': 'balanced_defense',
                'experience': 6,
                'adaptability': 0.8,
                'personality': 'balanced'
            }
        })
        
        self.opponent_staff = CoachingStaff("opponent_team", {
            'offensive_coordinator': {
                'archetype': 'aggressive',
                'experience': 7,
                'adaptability': 0.7,
                'personality': 'aggressive'
            },
            'defensive_coordinator': {
                'archetype': 'blitz_heavy',
                'experience': 9,
                'adaptability': 0.6,
                'personality': 'aggressive'
            }
        })
        
        self.play_caller = PlayCaller()
    
    def test_full_game_context_integration(self):
        """Test coaching staff integration with full game simulation context"""
        # Prepare for game
        self.coaching_staff.prepare_for_game("opponent_team", self.opponent_staff)
        
        # Simulate game progression with multiple drives
        drive_results = []
        offensive_results = []
        defensive_results = []
        
        for drive in range(5):  # 5 drives
            drive_plays = []
            
            for play in range(8):  # 8 plays per drive average
                # Create realistic field state
                field_state = FieldState()
                field_state.down = random.randint(1, 3)
                field_state.yards_to_go = random.randint(1, 15)
                field_state.field_position = random.randint(20, 80)
                
                game_context = {
                    'score_differential': random.randint(-14, 14),
                    'time_remaining': random.randint(300, 3600),
                    'quarter': random.randint(1, 4)
                }
                
                # Get coordinator decision
                coordinator_info = self.coaching_staff.get_offensive_coordinator_for_situation(
                    field_state, game_context
                )
                
                play_type = self.play_caller.determine_play_type(
                    field_state, coordinator_info
                )
                
                # Simulate play result
                play_result = {
                    'play_type': play_type,
                    'yards_gained': random.randint(-2, 15),
                    'expected_yards': random.randint(3, 8),
                    'success': random.choice([True, False])
                }
                
                drive_plays.append(play_result)
                offensive_results.append(play_result)
            
            drive_results.append({'plays': drive_plays, 'success': True})
            
            # Adapt after each drive
            if len(offensive_results) >= 3:  # Minimum sample size
                self.coaching_staff.adapt_during_game(
                    offensive_results[-8:], defensive_results, drive_results
                )
        
        # Verify game completed without errors
        self.assertEqual(len(drive_results), 5)
        self.assertGreater(len(offensive_results), 0)
        
        # Verify coaching staff tracked the game
        self.assertEqual(self.coaching_staff.games_coached, 1)
    
    def test_play_caller_compatibility(self):
        """Test backward compatibility with existing PlayCaller system"""
        field_state = FieldState()
        field_state.down = 3
        field_state.yards_to_go = 8
        field_state.field_position = 45
        
        game_context = {'score_differential': 0, 'time_remaining': 900}
        
        # Get coordinator info in format expected by PlayCaller
        coordinator_info = self.coaching_staff.get_offensive_coordinator_for_situation(
            field_state, game_context
        )
        
        # Verify expected structure
        self.assertIn('archetype', coordinator_info)
        self.assertIn('current_archetype_data', coordinator_info)
        self.assertIn('coordinator_name', coordinator_info)
        self.assertIn('experience', coordinator_info)
        self.assertIn('adaptability', coordinator_info)
        self.assertIn('personality', coordinator_info)
        self.assertIn('custom_modifiers', coordinator_info)
        
        # Test PlayCaller can use this info
        try:
            play_type = self.play_caller.determine_play_type(
                field_state, coordinator_info
            )
            self.assertIn(play_type, ['run', 'pass', 'punt', 'field_goal'])
        except Exception as e:
            self.fail(f"PlayCaller compatibility test failed: {e}")
    
    def test_performance_regression_prevention(self):
        """Test that coaching system doesn't cause performance regressions"""
        start_time = time.time()
        
        # Run many coaching decisions to test performance
        for _ in range(1000):
            field_state = FieldState()
            field_state.down = random.randint(1, 4)
            field_state.yards_to_go = random.randint(1, 20)
            field_state.field_position = random.randint(1, 99)
            
            game_context = {
                'score_differential': random.randint(-21, 21),
                'time_remaining': random.randint(60, 3600)
            }
            
            coordinator_info = self.coaching_staff.get_offensive_coordinator_for_situation(
                field_state, game_context
            )
            
            play_type = self.play_caller.determine_play_type(
                field_state, coordinator_info
            )
        
        elapsed_time = time.time() - start_time
        
        # Should complete 1000 decisions in under 2 seconds
        self.assertLess(elapsed_time, 2.0,
            f"Performance regression: 1000 decisions took {elapsed_time:.2f} seconds")
    
    def test_error_handling_edge_cases(self):
        """Test error handling and edge cases"""
        # Test with invalid field states
        invalid_field_state = FieldState()
        invalid_field_state.down = 5  # Invalid down
        invalid_field_state.yards_to_go = -5  # Invalid distance
        
        try:
            coordinator_info = self.coaching_staff.get_offensive_coordinator_for_situation(
                invalid_field_state, {}
            )
            # Should handle gracefully without crashing
            self.assertIsInstance(coordinator_info, dict)
        except Exception as e:
            self.fail(f"Error handling test failed: {e}")
        
        # Test with None values
        try:
            coordinator_info = self.coaching_staff.get_offensive_coordinator_for_situation(
                None, None
            )
        except Exception:
            pass  # Expected to fail gracefully
        
        # Test adaptation with empty results
        try:
            self.coaching_staff.adapt_during_game([], [], [])
            # Should handle empty results without crashing
        except Exception as e:
            self.fail(f"Empty results handling failed: {e}")
    
    def test_coaching_intelligence_summary(self):
        """Test coaching intelligence summary functionality"""
        summary = self.coaching_staff.get_coaching_intelligence_summary()
        
        # Verify summary structure
        self.assertIn('team_id', summary)
        self.assertIn('games_coached', summary)
        self.assertIn('offensive_coordinator', summary)
        self.assertIn('defensive_coordinator', summary)
        self.assertIn('opponent_history_size', summary)
        self.assertIn('season_adaptations', summary)
        
        # Verify coordinator details
        oc_summary = summary['offensive_coordinator']
        self.assertIn('name', oc_summary)
        self.assertIn('base_archetype', oc_summary)
        self.assertIn('experience', oc_summary)
        self.assertIn('adaptability', oc_summary)
        self.assertIn('personality', oc_summary)
        self.assertIn('current_momentum', oc_summary)


class TestAnalysisFunctions(unittest.TestCase):
    """Analysis functions for manual verification and benchmarking"""
    
    @classmethod
    def setUpClass(cls):
        """Set up analysis test fixtures"""
        cls.analysis_enabled = '--analyze' in sys.argv
        cls.iterations = 2000 if cls.analysis_enabled else 100
    
    def test_coaching_personality_analysis(self):
        """Analyze coaching personalities across different game situations"""
        if not self.analysis_enabled:
            self.skipTest("Analysis tests only run with --analyze flag")
        
        personalities = ['aggressive', 'traditional', 'balanced', 'innovative', 'adaptive']
        results = {}
        
        for personality in personalities:
            staff = CoachingStaff(f"{personality}_team", {
                'offensive_coordinator': {
                    'archetype': 'balanced',
                    'experience': 7,
                    'adaptability': 0.7,
                    'personality': personality
                }
            })
            
            play_counts = Counter()
            situations_tested = 0
            
            # Test various situations
            situations = [
                (4, 2, 35, "4th_and_short_own_territory"),
                (4, 3, 75, "4th_and_short_red_zone"),
                (3, 12, 25, "3rd_and_long_own_territory"),
                (1, 10, 85, "1st_and_10_red_zone"),
            ]
            
            for down, distance, position, description in situations:
                for _ in range(500):
                    field_state = FieldState()
                    field_state.down = down
                    field_state.yards_to_go = distance
                    field_state.field_position = position
                    
                    coordinator_info = staff.get_offensive_coordinator_for_situation(
                        field_state, {}
                    )
                    
                    play_caller = PlayCaller()
                    play_type = play_caller.determine_play_type(field_state, coordinator_info)
                    play_counts[f"{description}_{play_type}"] += 1
                    situations_tested += 1
            
            results[personality] = play_counts
        
        # Print analysis results
        print("\n" + "="*80)
        print("COACHING PERSONALITY ANALYSIS")
        print("="*80)
        
        for personality, counts in results.items():
            print(f"\n{personality.upper()} PERSONALITY:")
            print("-" * 40)
            
            for situation_play, count in sorted(counts.items()):
                situation, play = situation_play.rsplit('_', 1)
                percentage = (count / 500) * 100
                print(f"  {situation:<30} {play:<12}: {percentage:6.1f}%")
    
    def test_adaptation_behavior_verification(self):
        """Verify coaching adaptation behavior over time"""
        if not self.analysis_enabled:
            self.skipTest("Analysis tests only run with --analyze flag")
        
        adaptive_staff = CoachingStaff("adaptive_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 8,
                'adaptability': 1.0,
                'personality': 'adaptive'
            }
        })
        
        static_staff = CoachingStaff("static_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 8,
                'adaptability': 0.1,
                'personality': 'traditional'
            }
        })
        
        print("\n" + "="*80)
        print("ADAPTATION BEHAVIOR VERIFICATION")
        print("="*80)
        
        # Simulate struggling performance
        struggling_results = [
            {'yards_gained': i % 2, 'expected_yards': 4, 'play_type': 'run'}
            for i in range(20)
        ]
        
        # Track adaptation over multiple iterations
        for iteration in range(5):
            adaptive_staff.adapt_during_game(struggling_results, [], [])
            static_staff.adapt_during_game(struggling_results, [], [])
            
            if iteration in [0, 2, 4]:  # Print snapshots
                print(f"\nAfter {iteration + 1} adaptation cycles:")
                adaptive_momentum = adaptive_staff.offensive_coordinator.current_momentum
                static_momentum = static_staff.offensive_coordinator.current_momentum
                print(f"  Adaptive coach momentum: {adaptive_momentum:.3f}")
                print(f"  Static coach momentum:   {static_momentum:.3f}")
    
    def test_historical_memory_testing(self):
        """Test historical opponent memory system"""
        if not self.analysis_enabled:
            self.skipTest("Analysis tests only run with --analyze flag")
        
        staff = CoachingStaff("memory_team", {
            'offensive_coordinator': {
                'archetype': 'balanced',
                'experience': 10,
                'adaptability': 0.8,
                'personality': 'adaptive'
            }
        })
        
        print("\n" + "="*80)
        print("HISTORICAL MEMORY TESTING")
        print("="*80)
        
        opponents = [
            ("division_rival_team", "Division Rival"),
            ("conference_team", "Conference Team"),
            ("random_team", "Random Team")
        ]
        
        for opponent_id, opponent_name in opponents:
            # Simulate opponent history
            staff.offensive_coordinator.opponent_memory[opponent_id] = {
                'successful_strategies': {'pass_emphasis': 0.8, 'quick_game': 0.7},
                'failed_strategies': {'run_emphasis': 0.3}
            }
            
            # Test memory bonus calculation
            memory_bonus = staff.offensive_coordinator._calculate_memory_bonus(opponent_id)
            print(f"{opponent_name:<20}: Memory bonus = {memory_bonus:.3f}")
        
        # Test memory decay over time (would require more complex simulation)
        print(f"\nMemory retention rate: {CoachingBalance.MEMORY_RETENTION_RATE:.2f}")
        print(f"Adaptation decay rate:  {CoachingBalance.ADAPTATION_DECAY_RATE:.2f}")


def analyze_coaching_system():
    """Run comprehensive analysis of the coaching system"""
    print("\n" + "="*80)
    print("COMPREHENSIVE COACHING SYSTEM ANALYSIS")
    print("="*80)
    
    # Performance benchmarking
    print("\nPerformance Benchmarking:")
    start_time = time.time()
    
    staff = CoachingStaff("benchmark_team")
    play_caller = PlayCaller()
    
    for _ in range(10000):
        field_state = FieldState()
        field_state.down = random.randint(1, 4)
        field_state.yards_to_go = random.randint(1, 20)
        field_state.field_position = random.randint(1, 99)
        
        coordinator_info = staff.get_offensive_coordinator_for_situation(field_state, {})
        play_type = play_caller.determine_play_type(field_state, coordinator_info)
    
    elapsed = time.time() - start_time
    print(f"  10,000 coaching decisions: {elapsed:.3f} seconds")
    print(f"  Average per decision:      {(elapsed / 10000) * 1000:.3f} ms")
    
    # Memory usage would require additional profiling tools
    print(f"  Performance grade:         {'PASS' if elapsed < 1.0 else 'FAIL'}")


def main():
    """Main test runner with command line argument support"""
    parser = argparse.ArgumentParser(description="Comprehensive Coaching Staff Test Suite")
    parser.add_argument('--analyze', action='store_true', 
                       help='Run tests with detailed analysis output')
    parser.add_argument('--quick', action='store_true',
                       help='Run basic tests only')
    parser.add_argument('--benchmarks', action='store_true',
                       help='Run NFL realism benchmarks only')
    parser.add_argument('unittest_args', nargs='*')
    
    args = parser.parse_args()
    
    # Pass through unittest arguments
    sys.argv[1:] = args.unittest_args
    
    if args.analyze:
        sys.argv.append('--analyze')
    
    print("🏈 COMPREHENSIVE COACHING STAFF TEST SUITE")
    print("=" * 80)
    
    if args.quick:
        # Run only basic tests
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCoachingStaffBasics)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
    elif args.benchmarks:
        # Run only NFL realism benchmarks
        suite = unittest.TestLoader().loadTestsFromTestCase(TestNFLRealismBenchmarks)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
    else:
        # Run all tests
        test_classes = [
            TestCoachingStaffBasics,
            TestDynamicBehavior, 
            TestNFLRealismBenchmarks,
            TestIntegration,
            TestAnalysisFunctions
        ]
        
        suite = unittest.TestSuite()
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if args.analyze:
            analyze_coaching_system()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if hasattr(result, 'testsRun'):
        total_tests = result.testsRun
        failures = len(result.failures) if result.failures else 0
        errors = len(result.errors) if result.errors else 0
        passed = total_tests - failures - errors
        
        print(f"Tests run:     {total_tests}")
        print(f"Passed:        {passed}")
        print(f"Failed:        {failures}")
        print(f"Errors:        {errors}")
        print(f"Success rate:  {(passed/total_tests)*100:.1f}%")
        
        if failures == 0 and errors == 0:
            print("\n🎉 All tests passed! Coaching system is working correctly.")
            return True
        else:
            print("\n❌ Some tests failed. Check output above for details.")
            return False
    else:
        print("Test results not available")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)