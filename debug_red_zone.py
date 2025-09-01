#!/usr/bin/env python3
"""
Ultra-think debug script to identify red zone TD logic issues
"""

import sys
import os
import random

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.pass_play import PassPlay
from game_engine.field.field_state import FieldState
from game_engine.core.game_orchestrator import SimpleGameEngine

def debug_red_zone_td_logic():
    """Debug why 85% red zone TD probability yields only 34.8% rate"""
    print("🔍 RED ZONE TD LOGIC DEBUG")
    print("=" * 50)
    
    engine = SimpleGameEngine()
    pass_play = PassPlay()
    
    # Red zone scenarios (field position 80-95)
    red_zone_positions = [80, 85, 90, 95]
    
    for field_pos in red_zone_positions:
        print(f"\n--- Field Position: {field_pos} ---")
        
        # Create field state
        field_state = FieldState()
        field_state.down = 1
        field_state.yards_to_go = 10
        field_state.field_position = field_pos
        
        # Use mock personnel
        from unittest.mock import Mock
        personnel = Mock()
        personnel.formation = "shotgun"
        personnel.defensive_call = "zone_coverage"
        personnel.qb_on_field = Mock()
        personnel.qb_on_field.accuracy = 75
        personnel.qb_on_field.release_time = 70
        personnel.qb_on_field.mobility = 60
        personnel.primary_wr = Mock()
        personnel.primary_wr.route_running = 70
        personnel.primary_wr.hands = 75
        personnel.rb_on_field = Mock()
        personnel.rb_on_field.pass_protection = 50
        personnel.te_on_field = Mock()
        personnel.te_on_field.pass_protection = 60
        
        # Mock the ratings extraction
        pass_play._extract_player_ratings = Mock(return_value={
            'qb': 75, 'wr': 70, 'ol': 72, 'db': 68, 'dl': 70, 'lb': 65
        })
        
        # Run 100 simulations for this field position
        outcomes = []
        completion_count = 0
        td_count = 0
        
        for i in range(100):
            result = pass_play.simulate(personnel, field_state)
            outcomes.append(result.outcome)
            
            if result.outcome in ['gain', 'touchdown']:
                completion_count += 1
            if result.outcome == 'touchdown':
                td_count += 1
        
        completion_rate = completion_count / 100
        td_rate = td_count / 100
        td_given_completion = (td_count / completion_count) if completion_count > 0 else 0
        
        print(f"  Completions: {completion_count}/100 ({completion_rate:.1%})")
        print(f"  TDs: {td_count}/100 ({td_rate:.1%})")
        print(f"  TD given completion: {td_given_completion:.1%}")
        
        # This should be ~85% based on our red zone logic
        expected_td_given_completion = 0.85
        print(f"  Expected TD|completion: {expected_td_given_completion:.1%}")
        
        if abs(td_given_completion - expected_td_given_completion) > 0.1:
            print(f"  ⚠️  RED ZONE LOGIC NOT WORKING!")
            print(f"     Expected {expected_td_given_completion:.1%}, got {td_given_completion:.1%}")

def debug_single_red_zone_pass():
    """Step through a single red zone pass to see exact flow"""
    print("\n🔍 SINGLE RED ZONE PASS STEP-BY-STEP")
    print("=" * 50)
    
    # Force deterministic outcome for debugging
    random.seed(1)  # Specific seed for reproducible debugging
    
    engine = SimpleGameEngine()
    pass_play = PassPlay()
    
    # Create red zone scenario
    field_state = FieldState()
    field_state.down = 1
    field_state.yards_to_go = 10
    field_state.field_position = 85  # Deep red zone
    
    from unittest.mock import Mock
    personnel = Mock()
    personnel.formation = "shotgun"
    personnel.defensive_call = "zone_coverage"
    personnel.qb_on_field = Mock()
    personnel.qb_on_field.accuracy = 75
    personnel.qb_on_field.release_time = 70
    personnel.qb_on_field.mobility = 60
    personnel.primary_wr = Mock()
    personnel.primary_wr.route_running = 70
    personnel.primary_wr.hands = 75
    personnel.rb_on_field = Mock()
    personnel.rb_on_field.pass_protection = 50
    personnel.te_on_field = Mock()
    personnel.te_on_field.pass_protection = 60
    
    # Mock the ratings extraction
    pass_play._extract_player_ratings = Mock(return_value={
        'qb': 75, 'wr': 70, 'ol': 72, 'db': 68, 'dl': 70, 'lb': 65
    })
    pass_play._get_formation_modifier = Mock(return_value=1.0)
    pass_play._calculate_time_elapsed = Mock(return_value=6)
    pass_play._calculate_points = Mock(return_value=0)
    
    print(f"Field Position: {field_state.field_position} (Red Zone: {field_state.field_position >= 80})")
    
    # Step through manually to see what happens
    route_concept = pass_play._determine_route_concept(personnel.formation, field_state)
    print(f"Route Concept: {route_concept}")
    
    # Test the outcome determination with a manual completion
    from game_engine.plays.pass_play import ROUTE_CONCEPT_MATRICES
    matrix = ROUTE_CONCEPT_MATRICES[route_concept]
    
    # Manually set completion probability high to isolate TD logic
    completion_probability = 0.9  # Force completion
    
    print(f"Forcing completion probability: {completion_probability}")
    print(f"Testing TD logic at field position {field_state.field_position}...")
    
    # Test TD determination logic multiple times
    td_outcomes = []
    for i in range(20):
        random.seed(i)  # Different seed for each test
        outcome, yards = pass_play._determine_pass_outcome(
            completion_probability, matrix, route_concept, "zone", field_state
        )
        td_outcomes.append(outcome == "touchdown")
        if i < 5:  # Show first few
            print(f"  Test {i+1}: {outcome}, {yards} yards")
    
    td_rate_in_test = sum(td_outcomes) / len(td_outcomes)
    print(f"\nTD rate in forced completion test: {td_rate_in_test:.1%}")
    print(f"Expected: ~85%")
    
    if td_rate_in_test < 0.75:
        print("⚠️  RED ZONE TD LOGIC IS BROKEN!")

if __name__ == "__main__":
    debug_red_zone_td_logic()
    debug_single_red_zone_pass()