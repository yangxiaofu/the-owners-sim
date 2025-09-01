#!/usr/bin/env python3
"""
Debug test to isolate the _calculate_return_yards method and verify if it's causing
the punt distance issue (21.91 yards vs expected 45-47 yards)
"""

import sys
import os
import random
import statistics

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.punt_play import PuntPlay, PUNT_SITUATION_MATRICES, PuntGameBalance


def test_return_yards_calculation():
    """Isolated test of _calculate_return_yards method"""
    
    punt_play = PuntPlay()
    
    print("="*60)
    print("DEBUGGING _calculate_return_yards METHOD")
    print("="*60)
    
    # Test parameters from the failing test
    coverage_effectiveness = 0.72  # 72% special teams rating
    
    # Test all punt situations
    situations = ["deep_punt", "midfield_punt", "short_punt", "emergency_punt"]
    
    for situation in situations:
        matrix = PUNT_SITUATION_MATRICES[situation]
        
        print(f"\n--- {situation.upper()} ---")
        print(f"Matrix return_vulnerability: {matrix['return_vulnerability']}")
        
        return_yards_samples = []
        
        # Run 100 samples to get statistics
        for i in range(100):
            return_yards = punt_play._calculate_return_yards(coverage_effectiveness, matrix)
            return_yards_samples.append(return_yards)
        
        avg_return = statistics.mean(return_yards_samples)
        min_return = min(return_yards_samples)
        max_return = max(return_yards_samples)
        
        print(f"Return yards - Avg: {avg_return:.2f}, Min: {min_return}, Max: {max_return}")
        
        # Manual calculation verification
        base_return = PuntGameBalance.NET_RETURN_BASE  # 2.0
        coverage_reduction = base_return * coverage_effectiveness * PuntGameBalance.COVERAGE_REDUCTION_FACTOR
        situation_bonus = base_return * (matrix["return_vulnerability"] - 1.0) * PuntGameBalance.SITUATION_BONUS_FACTOR
        expected_base = base_return - coverage_reduction + situation_bonus
        
        print(f"Expected calculation:")
        print(f"  base_return: {base_return}")
        print(f"  coverage_reduction: {coverage_reduction:.3f}")
        print(f"  situation_bonus: {situation_bonus:.3f}")
        print(f"  expected_before_variance: {expected_base:.3f}")
        print(f"  variance range: {PuntGameBalance.RETURN_VARIANCE_MIN}-{PuntGameBalance.RETURN_VARIANCE_MAX}")
        print(f"  max_return_cap: {PuntGameBalance.NET_RETURN_MAX}")


def test_full_punt_calculation():
    """Test the full punt calculation to see where the distance is lost"""
    
    punt_play = PuntPlay()
    
    print("\n" + "="*60)
    print("DEBUGGING FULL PUNT CALCULATION PIPELINE")
    print("="*60)
    
    # Mock the same setup as the failing test
    from unittest.mock import Mock
    
    field_state = Mock()
    field_state.down = 4
    field_state.yards_to_go = 8
    field_state.field_position = 50
    
    personnel = Mock()
    personnel.punter_rating = 70
    # No punter_on_field, so it should use fallback
    
    offense_ratings = {'special_teams': 72, 'ol': 70, 'dl': 68}
    defense_ratings = {'dl': 68}
    
    # Step by step calculation
    print(f"Field state: {field_state.down}th & {field_state.yards_to_go} at {field_state.field_position}")
    
    # Step 1: Determine punt situation
    punt_situation = punt_play._determine_punt_situation(field_state)
    matrix = PUNT_SITUATION_MATRICES[punt_situation]
    print(f"Punt situation: {punt_situation}")
    print(f"Base distance from matrix: {matrix['base_distance']}")
    
    # Step 2: Check block probability
    block_result = punt_play._calculate_block_probability(offense_ratings, defense_ratings, punt_situation)
    print(f"Block check: {block_result} (should be False for most cases)")
    
    if not block_result:
        # Step 3: Calculate effectiveness
        punter_effectiveness = punt_play._calculate_punter_effectiveness_for_situation(personnel, punt_situation)
        coverage_effectiveness = punt_play._calculate_coverage_effectiveness(personnel, offense_ratings)
        
        combined_effectiveness = (
            punter_effectiveness * (PuntGameBalance.PUNTER_LEG_STRENGTH_WEIGHT + 
                                   PuntGameBalance.PUNTER_HANG_TIME_WEIGHT + 
                                   PuntGameBalance.PUNTER_ACCURACY_WEIGHT) +
            coverage_effectiveness * PuntGameBalance.COVERAGE_EFFECTIVENESS_WEIGHT
        )
        
        print(f"Punter effectiveness: {punter_effectiveness:.3f}")
        print(f"Coverage effectiveness: {coverage_effectiveness:.3f}")
        print(f"Combined effectiveness: {combined_effectiveness:.3f}")
        
        # Step 4: Apply effectiveness to base distance
        effectiveness_modifier = (PuntGameBalance.EFFECTIVENESS_BASE_MODIFIER + 
                                (combined_effectiveness - PuntGameBalance.EFFECTIVENESS_TARGET) * 
                                PuntGameBalance.EFFECTIVENESS_SCALE_FACTOR)
        base_with_effectiveness = matrix["base_distance"] * effectiveness_modifier
        
        print(f"Effectiveness modifier: {effectiveness_modifier:.3f}")
        print(f"Base with effectiveness: {base_with_effectiveness:.2f}")
        
        # Step 5: Apply situational modifiers
        adjusted_distance = punt_play._apply_punt_situational_modifiers(
            base_with_effectiveness, field_state, punt_situation
        )
        print(f"After situational modifiers: {adjusted_distance:.2f}")
        
        # Step 6: Add variance (sample a few times)
        print(f"Variance range: {PuntGameBalance.BASE_VARIANCE_MIN} to {PuntGameBalance.BASE_VARIANCE_MAX * matrix['variance']}")
        
        gross_distances = []
        for i in range(5):
            variance = random.uniform(PuntGameBalance.BASE_VARIANCE_MIN, 
                                    PuntGameBalance.BASE_VARIANCE_MAX * matrix["variance"])
            final_gross_distance = adjusted_distance * variance
            gross_yards = max(PuntGameBalance.MIN_PUNT_DISTANCE, int(final_gross_distance))
            gross_distances.append(gross_yards)
        
        avg_gross = statistics.mean(gross_distances)
        print(f"Sample gross distances: {gross_distances}")
        print(f"Average gross distance: {avg_gross:.1f} yards")
        
        # Step 7: Test return calculation
        return_yards_samples = []
        for i in range(10):
            return_yards = punt_play._calculate_return_yards(coverage_effectiveness, matrix)
            return_yards_samples.append(return_yards)
        
        avg_return = statistics.mean(return_yards_samples)
        print(f"Sample return yards: {return_yards_samples}")
        print(f"Average return yards: {avg_return:.1f}")
        
        expected_net = avg_gross - avg_return
        print(f"Expected net punt distance: {expected_net:.1f} yards")
        
        # Compare with NFL target
        print(f"NFL target: 45.8 yards net")
        print(f"Difference: {expected_net - 45.8:.1f} yards")


def test_outcome_distribution():
    """Test what outcomes are actually occurring"""
    
    punt_play = PuntPlay()
    
    print("\n" + "="*60)
    print("DEBUGGING OUTCOME DISTRIBUTION")
    print("="*60)
    
    from unittest.mock import Mock
    
    field_state = Mock()
    field_state.down = 4
    field_state.yards_to_go = 8
    field_state.field_position = 50
    
    personnel = Mock()
    personnel.punter_rating = 70
    
    # Mock the rating extraction
    punt_play._extract_player_ratings = Mock(return_value={'special_teams': 72, 'ol': 70, 'dl': 68})
    punt_play._calculate_time_elapsed = Mock(return_value=8)
    punt_play._calculate_points = Mock(return_value=0)
    
    # Run 100 punt simulations
    outcomes = {}
    distances = []
    
    for i in range(100):
        result = punt_play.simulate(personnel, field_state)
        outcome = result.outcome
        yards = result.yards_gained
        
        if outcome not in outcomes:
            outcomes[outcome] = []
        outcomes[outcome].append(yards)
        distances.append(yards)
    
    print("Outcome distribution:")
    for outcome, yards_list in outcomes.items():
        count = len(yards_list)
        percentage = count / 100 * 100
        avg_yards = statistics.mean(yards_list) if yards_list else 0
        print(f"  {outcome}: {count} times ({percentage:.1f}%), avg {avg_yards:.1f} yards")
    
    overall_avg = statistics.mean(distances)
    print(f"\nOverall average distance: {overall_avg:.2f} yards")
    print(f"Expected: 45-47 yards")
    print(f"Shortfall: {45.8 - overall_avg:.1f} yards")


if __name__ == "__main__":
    # Set consistent seed for reproducible results
    random.seed(42)
    
    test_return_yards_calculation()
    test_full_punt_calculation()
    test_outcome_distribution()