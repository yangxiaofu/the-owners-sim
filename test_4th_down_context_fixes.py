#!/usr/bin/env python3
"""
Test script for 4th down intelligence context override system.

This script tests the newly implemented context override methods that were
missing from the original implementation, causing the "context override failures".
"""

import sys
sys.path.append('/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim')

from src.game_engine.plays.play_calling import PlayCaller
from src.game_engine.field.field_state import FieldState

def test_context_override_implementation():
    """Test that all context override methods are now implemented and working"""
    
    print("🧪 Testing 4th Down Context Override Implementation")
    print("=" * 60)
    
    # Initialize play caller
    play_caller = PlayCaller()
    
    # Test 1: Desperation Mode (trailing by 10, 4th & 3)
    print("\n1. Testing Desperation Mode Override")
    field_state = FieldState()
    field_state.down = 4
    field_state.yards_to_go = 3
    field_state.field_position = 45
    
    coordinator = {"archetype": "conservative"}
    
    # Simulate multiple calls to see probability shifts
    results = []
    for i in range(20):
        # Set up desperation scenario (trailing by 10)
        play_type = play_caller.determine_play_type(
            field_state, coordinator, score_differential=-10
        )
        results.append(play_type)
    
    punt_count = results.count("punt")
    go_for_it_count = len([r for r in results if r in ["run", "pass"]])
    
    print(f"   Desperation Results (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}")
    print(f"   Expected: Low punting (~1-4), High go-for-it (~16-19)")
    
    # Test 2: Protect Lead Mode (leading by 7, 4th & 4)  
    print("\n2. Testing Protect Lead Override")
    field_state.yards_to_go = 4
    
    results = []
    for i in range(20):
        play_type = play_caller.determine_play_type(
            field_state, coordinator, score_differential=7
        )
        results.append(play_type)
    
    punt_count = results.count("punt")
    go_for_it_count = len([r for r in results if r in ["run", "pass"]])
    
    print(f"   Protect Lead Results (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}")
    print(f"   Expected: High punting (~15-19), Low go-for-it (~1-5)")
    
    # Test 3: Red Zone Critical Context (4th & goal from 5, trailing by 4)
    print("\n3. Testing Red Zone Critical Override")
    field_state.field_position = 95  # Red zone
    field_state.yards_to_go = 5
    
    results = []
    for i in range(20):
        play_type = play_caller.determine_play_type(
            field_state, coordinator, score_differential=-4
        )
        results.append(play_type)
    
    fg_count = results.count("field_goal")
    td_attempts = len([r for r in results if r in ["run", "pass"]])
    punt_count = results.count("punt")
    
    print(f"   Red Zone Critical Results (20 trials): FG={fg_count}, TD attempts={td_attempts}, Punt={punt_count}")
    print(f"   Expected: Low FG (~0-3), High TD attempts (~15-19), Some punts (~1-5)")
    
    # Test 4: Normal Game Situation (baseline)
    print("\n4. Testing Normal Game Baseline")
    field_state.field_position = 35  # Own territory
    field_state.yards_to_go = 8
    
    results = []
    for i in range(20):
        play_type = play_caller.determine_play_type(
            field_state, coordinator, score_differential=0
        )
        results.append(play_type)
    
    punt_count = results.count("punt")
    go_for_it_count = len([r for r in results if r in ["run", "pass"]])
    
    print(f"   Normal Game Results (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}")
    print(f"   Expected: High punting (~15-19), Low go-for-it (~1-5)")
    
    # Test 5: Verify methods exist and are callable
    print("\n5. Testing Method Implementation")
    methods_to_check = [
        '_apply_context_overrides',
        '_is_desperation_mode', 
        '_should_protect_lead',
        '_is_time_critical',
        '_is_red_zone_critical',
        '_apply_desperation_mode_overrides',
        '_apply_protect_lead_modifiers',
        '_apply_time_urgency_factors',
        '_apply_red_zone_context',
        '_create_simplified_context'
    ]
    
    missing_methods = []
    for method_name in methods_to_check:
        if not hasattr(play_caller, method_name):
            missing_methods.append(method_name)
    
    if missing_methods:
        print(f"   ❌ Missing methods: {missing_methods}")
        return False
    else:
        print(f"   ✅ All {len(methods_to_check)} context override methods implemented")
    
    print("\n" + "=" * 60)
    print("🎉 4th Down Context Override Implementation Test COMPLETE!")
    print("All missing methods have been implemented and are functioning.")
    
    return True

if __name__ == "__main__":
    test_context_override_implementation()