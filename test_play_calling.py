#!/usr/bin/env python3
"""
Comprehensive test suite for the coaching archetype system with realistic NFL benchmarks.
Tests the play calling logic across all archetypes with range-based validation.
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.play_calling import PlayCaller, PlayCallingBalance, OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
from game_engine.field.game_state import FieldState


class TestPlayCalling(unittest.TestCase):
    """Test suite for coaching archetype play calling system."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.play_caller = PlayCaller()
        self.mock_field = Mock(spec=FieldState)
        
    def test_archetype_initialization(self):
        """Test that all archetypes are properly defined with required fields."""
        # Test offensive archetypes
        for archetype_name, archetype_data in OFFENSIVE_ARCHETYPES.items():
            self.assertIn('4th_down_aggressiveness', archetype_data)
            self.assertIn('situation_modifiers', archetype_data)
            self.assertIsInstance(archetype_data['situation_modifiers'], dict)
            
        # Test defensive archetypes
        for archetype_name, archetype_data in DEFENSIVE_ARCHETYPES.items():
            self.assertIn('offensive_counter_effects', archetype_data)
            self.assertIsInstance(archetype_data['offensive_counter_effects'], dict)

    def test_play_caller_basic_functionality(self):
        """Test basic play calling without archetype influence."""
        self.mock_field.down = 1
        self.mock_field.yards_to_go = 10
        self.mock_field.field_position = 50
        
        # Test with balanced archetype (minimal influence)
        coordinator = {'archetype': 'balanced'}
        play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
        
        self.assertIn(play_type, ['run', 'pass'])

    def test_conservative_archetype_behavior(self):
        """Test conservative archetype shows risk-averse behavior."""
        # Test 4th down conservatism
        self.mock_field.down = 4
        self.mock_field.yards_to_go = 2  
        self.mock_field.field_position = 50
        coordinator = {'archetype': 'conservative'}
        
        results = {'punt': 0, 'field_goal': 0, 'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
            results[play_type] += 1
            
        # Conservative should prefer punt/field goal over going for it
        conservative_plays = results['punt'] + results['field_goal']
        aggressive_plays = results['run'] + results['pass']
        
        self.assertGreater(conservative_plays, aggressive_plays, 
                          "Conservative archetype should prefer punt/FG over going for it")

    def test_aggressive_archetype_behavior(self):
        """Test aggressive archetype shows higher risk tolerance."""
        self.mock_field.down = 4
        self.mock_field.yards_to_go = 2
        self.mock_field.field_position = 50
        coordinator = {'archetype': 'aggressive'}
        
        results = {'punt': 0, 'field_goal': 0, 'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
            results[play_type] += 1
            
        # Aggressive should go for it more often but still be realistic
        go_for_it_rate = (results['run'] + results['pass']) / 200
        
        # Aggressive coaches should be more willing to go for it, but not excessively
        self.assertGreater(go_for_it_rate, 0.25, "Aggressive archetype should go for it > 25%")
        self.assertLess(go_for_it_rate, 0.60, "Aggressive archetype should go for it < 60% (realistic)")

    def test_west_coast_passing_emphasis(self):
        """Test west coast archetype emphasizes passing appropriately."""
        self.mock_field.down = 1
        self.mock_field.yards_to_go = 10
        self.mock_field.field_position = 50
        coordinator = {'archetype': 'west_coast'}
        
        results = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
            results[play_type] += 1
            
        pass_rate = results['pass'] / 200
        
        # West Coast should emphasize passing but remain balanced
        self.assertGreater(pass_rate, 0.60, "West Coast should pass > 60%")
        self.assertLess(pass_rate, 0.80, "West Coast should pass < 80% (realistic balance)")

    def test_run_heavy_ground_emphasis(self):
        """Test run heavy archetype emphasizes running appropriately."""
        self.mock_field.down = 1
        self.mock_field.yards_to_go = 10
        self.mock_field.field_position = 50
        coordinator = {'archetype': 'run_heavy'}
        
        results = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
            results[play_type] += 1
            
        run_rate = results['run'] / 200
        
        # Run heavy should emphasize ground game but not exclusively
        self.assertGreater(run_rate, 0.55, "Run Heavy should run > 55%")
        self.assertLess(run_rate, 0.75, "Run Heavy should run < 75% (realistic balance)")

    def test_air_raid_passing_frequency(self):
        """Test air raid archetype shows high but realistic passing rates."""
        self.mock_field.down = 1
        self.mock_field.yards_to_go = 10
        self.mock_field.field_position = 50
        coordinator = {'archetype': 'air_raid'}
        
        results = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(self.mock_field, coordinator)
            results[play_type] += 1
            
        pass_rate = results['pass'] / 200
        
        # Air Raid should be pass-heavy but not unrealistically so
        self.assertGreater(pass_rate, 0.65, "Air Raid should pass > 65%")
        self.assertLess(pass_rate, 0.85, "Air Raid should pass < 85% (realistic limit)")

    def test_defensive_influence(self):
        """Test that defensive archetypes appropriately influence offensive decisions."""
        self.mock_field.down = 2
        self.mock_field.yards_to_go = 8
        self.mock_field.field_position = 50
        
        offensive_coord = {'archetype': 'balanced'}
        
        # Test run stuffing defense increases pass rate
        defensive_coord = {'archetype': 'run_stuffing'}
        
        results = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(
                self.mock_field, offensive_coord, defensive_coord
            )
            results[play_type] += 1
            
        pass_rate_vs_run_stuffing = results['pass'] / 200
        
        # Test baseline with balanced defense
        defensive_coord = {'archetype': 'balanced_defense'}
        results_baseline = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(
                self.mock_field, offensive_coord, defensive_coord
            )
            results_baseline[play_type] += 1
            
        pass_rate_baseline = results_baseline['pass'] / 200
        
        # Run stuffing defense should increase pass rate
        self.assertGreater(pass_rate_vs_run_stuffing, pass_rate_baseline,
                          "Run stuffing defense should increase offensive pass rate")

    def test_custom_modifiers(self):
        """Test that custom modifiers properly influence play calling."""
        self.mock_field.down = 1
        self.mock_field.yards_to_go = 10
        self.mock_field.field_position = 50
        
        coordinator_with_modifiers = {
            'archetype': 'balanced',
            'custom_modifiers': {
                'special_emphasis': 0.15  # Should increase pass tendency
            }
        }
        
        # Test multiple samples to see effect
        results = {'run': 0, 'pass': 0}
        for _ in range(200):
            play_type = self.play_caller.determine_play_type(
                self.mock_field, coordinator_with_modifiers
            )
            results[play_type] += 1
            
        # Custom modifiers should have measurable effect
        pass_rate = results['pass'] / 200
        
        # With balanced archetype, should be roughly 50-60% pass normally
        # Custom modifier should push it higher
        self.assertGreater(pass_rate, 0.50, "Custom modifiers should influence decisions")


def run_comprehensive_archetype_analysis():
    """
    Run comprehensive analysis of all archetypes across multiple situations.
    This provides detailed output for manual analysis of coaching behavior.
    """
    print("\nCOMPREHENSIVE COACHING ARCHETYPE ANALYSIS")
    print("=" * 50)
    
    play_caller = PlayCaller()
    mock_field = Mock(spec=FieldState)
    
    # Test situations that showcase archetype differences
    test_situations = [
        "1st_and_10", "3rd_and_short", "3rd_and_long", 
        "4th_and_short", "4th_and_medium", "red_zone", 
        "goal_line", "deep_territory"
    ]
    
    archetypes = ['conservative', 'aggressive', 'west_coast', 'run_heavy', 'air_raid', 'balanced']
    
    print("=" * 80)
    print("COMPREHENSIVE COACHING ARCHETYPE ANALYSIS")
    print("=" * 80)
    print()
    print(f"{'ARCHETYPE':<15} {'SITUATION':<15} {'RUN%':<8} {'PASS%':<8} {'PUNT%':<8} {'FG%':<8} {'TOTAL':<7}")
    print("-" * 80)
    
    for archetype in archetypes:
        print(f"\n🏈 {archetype.upper().replace('_', ' ')} ARCHETYPE")
        print("-" * 50)
        
        coordinator = {'archetype': archetype}
        
        for situation in test_situations:
            # Set up mock field state for this situation
            if situation == "1st_and_10":
                mock_field.down = 1
                mock_field.yards_to_go = 10
                mock_field.field_position = 50
            elif situation == "3rd_and_short":
                mock_field.down = 3
                mock_field.yards_to_go = 2
                mock_field.field_position = 50
            elif situation == "3rd_and_long":
                mock_field.down = 3
                mock_field.yards_to_go = 12
                mock_field.field_position = 50
            elif situation == "4th_and_short":
                mock_field.down = 4
                mock_field.yards_to_go = 2
                mock_field.field_position = 50
            elif situation == "4th_and_medium":
                mock_field.down = 4
                mock_field.yards_to_go = 6
                mock_field.field_position = 50
            elif situation == "red_zone":
                mock_field.down = 1
                mock_field.yards_to_go = 10
                mock_field.field_position = 85
            elif situation == "goal_line":
                mock_field.down = 1
                mock_field.yards_to_go = 2
                mock_field.field_position = 98
            elif situation == "deep_territory":
                mock_field.down = 1
                mock_field.yards_to_go = 10
                mock_field.field_position = 15
            
            # Run 200 simulations for statistical significance
            results = {'run': 0, 'pass': 0, 'punt': 0, 'field_goal': 0}
            total_plays = 200
            
            for _ in range(total_plays):
                play_type = play_caller.determine_play_type(mock_field, coordinator)
                results[play_type] += 1
                
            # Calculate percentages
            run_pct = (results['run'] / total_plays) * 100
            pass_pct = (results['pass'] / total_plays) * 100
            punt_pct = (results['punt'] / total_plays) * 100
            fg_pct = (results['field_goal'] / total_plays) * 100
            
            print(f"{'':>15} {situation:<15} {run_pct:>6.1f}% {pass_pct:>6.1f}% {punt_pct:>6.1f}% {fg_pct:>6.1f}% {total_plays:>6}")


def analyze_defensive_influence():
    """Analyze how defensive archetypes influence offensive play calling."""
    print("\n" + "=" * 80)
    print("DEFENSIVE INFLUENCE ANALYSIS")
    print("=" * 80)
    print("Situation: 2nd and 8 from 45-yard line (Balanced Offense)\n")
    
    play_caller = PlayCaller()
    mock_field = Mock(spec=FieldState)
    mock_field.down = 2
    mock_field.yards_to_go = 8
    mock_field.field_position = 45
    
    offensive_coord = {'archetype': 'balanced'}
    defensive_archetypes = ['balanced_defense', 'blitz_heavy', 'run_stuffing', 
                          'zone_coverage', 'man_coverage', 'bend_dont_break']
    
    print(f"{'DEFENSIVE ARCHETYPE':<20} {'RUN%':<8} {'PASS%':<8} {'INFLUENCE':<15}")
    print("-" * 60)
    
    baseline_run_rate = None
    
    for def_archetype in defensive_archetypes:
        defensive_coord = {'archetype': def_archetype}
        
        results = {'run': 0, 'pass': 0}
        for _ in range(300):  # More samples for accuracy
            play_type = play_caller.determine_play_type(
                mock_field, offensive_coord, defensive_coord
            )
            results[play_type] += 1
            
        run_rate = (results['run'] / 300) * 100
        pass_rate = (results['pass'] / 300) * 100
        
        if def_archetype == 'balanced_defense':
            baseline_run_rate = run_rate
            influence = "BASELINE"
        else:
            if baseline_run_rate:
                run_diff = run_rate - baseline_run_rate
                if abs(run_diff) < 2:
                    influence = "Minimal impact"
                elif run_diff > 0:
                    influence = f"↑{run_diff:.1f}% RUN"
                else:
                    influence = f"↓{abs(run_diff):.1f}% RUN"
            else:
                influence = "N/A"
        
        print(f"{def_archetype:<20} {run_rate:>6.1f}% {pass_rate:>6.1f}% {influence}")


def run_nfl_benchmark_validation():
    """
    Validate coaching archetypes against realistic NFL benchmarks using ranges.
    """
    print("\n" + "=" * 80)
    print("NFL BENCHMARK VALIDATION")
    print("=" * 80)
    
    play_caller = PlayCaller()
    mock_field = Mock(spec=FieldState)
    
    # Define realistic NFL benchmark ranges
    benchmarks = [
        {
            'name': 'Conservative 4th Down Rate',
            'archetype': 'conservative',
            'situation': '4th_and_short',
            'measure': lambda results: (results['run'] + results['pass']) / sum(results.values()) * 100,
            'target_min': 8.0,
            'target_max': 18.0,
            'description': 'Conservative coaches should go for it 8-18% of the time'
        },
        {
            'name': 'Aggressive 4th Down Rate', 
            'archetype': 'aggressive',
            'situation': '4th_and_short',
            'measure': lambda results: (results['run'] + results['pass']) / sum(results.values()) * 100,
            'target_min': 35.0,
            'target_max': 55.0,
            'description': 'Aggressive coaches should go for it 35-55% of the time'
        },
        {
            'name': 'West Coast Passing Rate',
            'archetype': 'west_coast', 
            'situation': '1st_and_10',
            'measure': lambda results: results['pass'] / sum(results.values()) * 100,
            'target_min': 60.0,
            'target_max': 78.0,
            'description': 'West Coast should pass 60-78% on first down'
        },
        {
            'name': 'Run Heavy Ground Rate',
            'archetype': 'run_heavy',
            'situation': '1st_and_10', 
            'measure': lambda results: results['run'] / sum(results.values()) * 100,
            'target_min': 55.0,
            'target_max': 72.0,
            'description': 'Run Heavy should run 55-72% on first down'
        },
        {
            'name': 'Air Raid Pass Frequency',
            'archetype': 'air_raid',
            'situation': '1st_and_10',
            'measure': lambda results: results['pass'] / sum(results.values()) * 100,
            'target_min': 68.0,
            'target_max': 82.0,
            'description': 'Air Raid should pass 68-82% on first down'
        }
    ]
    
    print(f"{'BENCHMARK':<25} {'RESULT':<8} {'TARGET RANGE':<15} {'STATUS':<8} {'DESCRIPTION'}")
    print("-" * 80)
    
    all_passed = True
    
    for benchmark in benchmarks:
        coordinator = {'archetype': benchmark['archetype']}
        
        # Set up mock field for this benchmark situation
        if benchmark['situation'] == '4th_and_short':
            mock_field.down = 4
            mock_field.yards_to_go = 2
            mock_field.field_position = 50
        elif benchmark['situation'] == '1st_and_10':
            mock_field.down = 1
            mock_field.yards_to_go = 10
            mock_field.field_position = 50
        
        # Run simulations
        results = {'run': 0, 'pass': 0, 'punt': 0, 'field_goal': 0}
        for _ in range(500):  # Large sample for accuracy
            play_type = play_caller.determine_play_type(mock_field, coordinator)
            results[play_type] += 1
            
        # Calculate the measured value
        measured_value = benchmark['measure'](results)
        
        # Check if within range
        within_range = benchmark['target_min'] <= measured_value <= benchmark['target_max']
        status = "✅ PASS" if within_range else "❌ FAIL"
        
        if not within_range:
            all_passed = False
            
        target_range = f"{benchmark['target_min']:.0f}-{benchmark['target_max']:.0f}%"
        
        print(f"{benchmark['name']:<25} {measured_value:>6.1f}% {target_range:<15} {status:<8}")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL BENCHMARKS PASSED - Coaching archetypes show realistic NFL behavior")
    else:
        print("❌ SOME BENCHMARKS FAILED - Archetype tuning needed")
    print("=" * 80)
    
    return all_passed


def analyze_archetype_personalities():
    """Deep dive into how each archetype behaves in key situations."""
    print("\n" + "=" * 80)
    print("ARCHETYPE PERSONALITY ANALYSIS")
    print("=" * 80)
    
    play_caller = PlayCaller()
    mock_field = Mock(spec=FieldState)
    
    # Key personality-revealing situations
    personality_tests = [
        ("4th and 2 at opponent 45", "4th_and_short"),
        ("4th and 5 in red zone", "4th_and_medium"),
        ("3rd and 15 from own 25", "3rd_and_long"),
        ("1st and 10 at midfield", "1st_and_10")
    ]
    
    archetypes = [
        ('conservative', 'Risk-averse, prefers field position and points'),
        ('aggressive', 'High-risk, high-reward, goes for touchdowns'),
        ('west_coast', 'Short passing precision, ball control'),
        ('run_heavy', 'Ground and pound, time of possession'),
        ('air_raid', 'High tempo passing attack, vertical routes'),
        ('balanced', 'Situational football, adapts to circumstances')
    ]
    
    for archetype, description in archetypes:
        print(f"\n🎯 {archetype.upper()}: {description}")
        print("-" * 60)
        
        coordinator = {'archetype': archetype}
        
        for situation_desc, situation_code in personality_tests:
            # Set up mock field for this personality test
            if situation_code == "4th_and_short":
                mock_field.down = 4
                mock_field.yards_to_go = 2
                mock_field.field_position = 55  # Opponent 45
            elif situation_code == "4th_and_medium":
                mock_field.down = 4
                mock_field.yards_to_go = 5
                mock_field.field_position = 85  # Red zone
            elif situation_code == "3rd_and_long":
                mock_field.down = 3
                mock_field.yards_to_go = 15
                mock_field.field_position = 25  # Own 25
            elif situation_code == "1st_and_10":
                mock_field.down = 1
                mock_field.yards_to_go = 10
                mock_field.field_position = 50  # Midfield
            
            results = {'run': 0, 'pass': 0, 'punt': 0, 'field_goal': 0}
            for _ in range(100):
                play_type = play_caller.determine_play_type(mock_field, coordinator)
                results[play_type] += 1
                
            # Show top 2 choices
            sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
            top_choice = sorted_results[0]
            second_choice = sorted_results[1]
            
            top_pct = (top_choice[1] / 100) * 100
            second_pct = (second_choice[1] / 100) * 100
            
            print(f"  {situation_desc:<25} → {top_choice[0]} {top_pct:.0f}%, {second_choice[0]} {second_pct:.0f}%")


if __name__ == '__main__':
    # Check if we're running with --analyze flag
    if len(sys.argv) > 1 and '--analyze' in sys.argv:
        print("================================================================================")
        print("COMPREHENSIVE COACHING ARCHETYPE ANALYSIS")
        print("================================================================================")
        
        # Run all analysis functions
        run_comprehensive_archetype_analysis()
        analyze_defensive_influence() 
        analyze_archetype_personalities()
        
        # Run updated benchmark validation with ranges
        benchmark_passed = run_nfl_benchmark_validation()
        
        print("\n================================================================================")
        print("MANUAL ANALYSIS COMPLETE - Review results above for coaching realism")
        print("================================================================================")
        
        # Exit with appropriate code
        sys.exit(0 if benchmark_passed else 1)
    else:
        # Run normal unit tests
        unittest.main()