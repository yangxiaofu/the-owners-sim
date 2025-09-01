#!/usr/bin/env python3
"""
Debug script to identify issues in the pass play algorithm
"""

import sys
import os
import random
from unittest.mock import Mock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.pass_play import PassPlay, ROUTE_CONCEPT_MATRICES, PassGameBalance
from game_engine.field.field_state import FieldState
from game_engine.core.game_orchestrator import SimpleGameEngine

def debug_route_concept_matrices():
    """Debug the base values in route concept matrices"""
    print("🔍 ROUTE CONCEPT MATRICES DEBUG")
    print("=" * 40)
    
    for concept, matrix in ROUTE_CONCEPT_MATRICES.items():
        print(f"\n{concept.upper()}:")
        print(f"  Base completion: {matrix['base_completion']:.1%}")
        print(f"  Base yards: {matrix['base_yards']:.1f}")
        print(f"  Time to throw: {matrix['time_to_throw']:.1f}s")
        print(f"  Variance: {matrix['variance']:.1f}")
        
        # Calculate YAC addition
        yac_multipliers = {
            "quick_game": 0.3, "intermediate": 0.5, "vertical": 0.6, "screens": 0.8, "play_action": 0.4
        }
        yac_potential = yac_multipliers.get(concept, 0.45)
        yac_yards = matrix['base_yards'] * yac_potential * PassGameBalance.YAC_MULTIPLIER
        total_expected_yards = matrix['base_yards'] + yac_yards
        
        print(f"  Expected YAC: {yac_yards:.1f}")
        print(f"  Total expected yards: {total_expected_yards:.1f}")

def debug_single_pass():
    """Debug a single pass execution"""
    print("\n🔍 SINGLE PASS EXECUTION DEBUG")
    print("=" * 40)
    
    # Create test scenario
    engine = SimpleGameEngine()
    pass_play = PassPlay()
    
    # Create mock personnel
    personnel = Mock()
    personnel.formation = "shotgun"
    personnel.defensive_call = "zone_coverage"
    personnel.qb_on_field = Mock()
    personnel.qb_on_field.accuracy = 75
    personnel.qb_on_field.release_time = 70
    personnel.qb_on_field.mobility = 60  # Add mobility attribute
    personnel.primary_wr = Mock()
    personnel.primary_wr.route_running = 70
    personnel.primary_wr.hands = 75
    personnel.rb_on_field = Mock()
    personnel.rb_on_field.pass_protection = 50
    personnel.te_on_field = Mock()
    personnel.te_on_field.pass_protection = 60
    
    # Create field state
    field_state = FieldState()
    field_state.down = 1
    field_state.yards_to_go = 10
    field_state.field_position = 50
    
    # Mock the ratings extraction
    pass_play._extract_player_ratings = Mock(return_value={
        'qb': 75, 'wr': 70, 'ol': 72, 'db': 68, 'dl': 70, 'lb': 65
    })
    pass_play._get_formation_modifier = Mock(return_value=1.0)
    pass_play._calculate_time_elapsed = Mock(return_value=6)
    pass_play._calculate_points = Mock(return_value=0)
    
    print("Input values:")
    print(f"  Formation: {personnel.formation}")
    print(f"  Defensive call: {personnel.defensive_call}")
    print(f"  Down & distance: {field_state.down} & {field_state.yards_to_go}")
    print(f"  Field position: {field_state.field_position}")
    
    # Step through the algorithm
    route_concept = pass_play._determine_route_concept(personnel.formation, field_state)
    coverage_type = pass_play._determine_defensive_coverage(personnel.defensive_call, personnel)
    matrix = ROUTE_CONCEPT_MATRICES[route_concept]
    
    print(f"\nAlgorithm steps:")
    print(f"  Route concept: {route_concept}")
    print(f"  Coverage type: {coverage_type}")
    print(f"  Base completion: {matrix['base_completion']:.1%}")
    print(f"  Base yards: {matrix['base_yards']:.1f}")
    
    # Calculate effectiveness values
    qb_eff = pass_play._calculate_qb_effectiveness_for_route_concept(personnel.qb_on_field, route_concept)
    wr_eff = pass_play._calculate_wr_effectiveness_for_route_concept(personnel.primary_wr, route_concept)
    
    print(f"  QB effectiveness: {qb_eff:.3f}")
    print(f"  WR effectiveness: {wr_eff:.3f}")
    
    # Calculate protection
    ol_rating = 72
    rb_protection = pass_play._get_rb_pass_protection(personnel.rb_on_field)
    te_protection = pass_play._get_te_pass_protection(personnel.te_on_field)
    
    protection_effectiveness = (
        ol_rating * PassGameBalance.OL_PROTECTION_WEIGHT +
        rb_protection * PassGameBalance.RB_PROTECTION_WEIGHT +
        te_protection * PassGameBalance.TE_PROTECTION_WEIGHT
    ) / 100.0
    
    print(f"  Protection effectiveness: {protection_effectiveness:.3f}")
    
    # Calculate coverage
    db_rating = 68
    coverage_modifier = matrix[f"vs_{coverage_type}_modifier"]
    coverage_effectiveness = db_rating / 100.0
    
    print(f"  Coverage effectiveness: {coverage_effectiveness:.3f}")
    print(f"  Coverage modifier: {coverage_modifier:.2f}")
    
    # Combined effectiveness
    combined_effectiveness = (
        qb_eff * PassGameBalance.QB_EFFECTIVENESS_WEIGHT +
        wr_eff * PassGameBalance.WR_EFFECTIVENESS_WEIGHT +
        protection_effectiveness * PassGameBalance.PROTECTION_WEIGHT +
        (1.0 - coverage_effectiveness) * PassGameBalance.COVERAGE_WEIGHT
    ) * 1.0 * coverage_modifier
    
    print(f"  Combined effectiveness: {combined_effectiveness:.3f}")
    
    # Final completion
    final_completion = matrix["base_completion"] * combined_effectiveness
    print(f"  Final completion probability: {final_completion:.3f}")
    
    # Simulate outcome multiple times
    print(f"\nSimulating 10 passes with these values:")
    outcomes = []
    yards_list = []
    
    for i in range(10):
        result = pass_play.simulate(personnel, field_state)
        outcomes.append(result.outcome)
        yards_list.append(result.yards_gained)
        print(f"  Pass {i+1}: {result.outcome}, {result.yards_gained} yards")
    
    completions = sum(1 for o in outcomes if o in ['gain', 'touchdown'])
    avg_yards = sum(yards_list) / len(yards_list)
    
    print(f"\nResults summary:")
    print(f"  Completions: {completions}/10 ({completions*10:.0f}%)")
    print(f"  Average yards: {avg_yards:.1f}")

def debug_team_ratings():
    """Debug team rating extraction"""
    print("\n🔍 TEAM RATINGS DEBUG")
    print("=" * 30)
    
    engine = SimpleGameEngine()
    
    # Get teams
    bears = engine.get_team_for_simulation(1)
    packers = engine.get_team_for_simulation(2)
    cowboys = engine.get_team_for_simulation(5)
    lions = engine.get_team_for_simulation(3)
    
    teams = [("Bears", bears), ("Packers", packers), ("Cowboys", cowboys), ("Lions", lions)]
    
    for name, team in teams:
        print(f"\n{name}:")
        print(f"  QB: {team['offense']['qb_rating']}")
        print(f"  WR: {team['offense']['wr_rating']}")  
        print(f"  OL: {team['offense']['ol_rating']}")
        print(f"  DB: {team['defense']['db_rating']}")
        print(f"  DL: {team['defense']['dl_rating']}")
        print(f"  Overall: {team['overall_rating']}")

def main():
    """Run all debug functions"""
    random.seed(42)  # Reproducible results
    
    debug_route_concept_matrices()
    debug_single_pass()
    debug_team_ratings()
    
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSIS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()