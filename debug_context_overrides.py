#!/usr/bin/env python3
"""
Debug Context Override System
Test to see exactly what's happening with the context override logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game_engine.field.field_state import FieldState
from src.game_engine.plays.play_calling import PlayCaller, PlayCallingBalance

def debug_red_zone_critical():
    """Debug red zone critical context"""
    print("🔍 Debugging Red Zone Critical Context")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Create field state: 4th & goal from 5, down by 4
    field_state = FieldState()
    field_state.down = 4
    field_state.yards_to_go = 5  # Goal line
    field_state.field_position = 95  # Red zone
    
    coordinator = {"archetype": "conservative"}
    
    # Set score differential for context overrides
    play_caller._current_score_differential = -4  # Down by 4
    
    print(f"Field position: {field_state.field_position} (RED_ZONE_THRESHOLD: {PlayCallingBalance.RED_ZONE_THRESHOLD})")
    print(f"Score differential: {play_caller._current_score_differential}")
    print(f"Down: {field_state.down}")
    
    # Check if red zone critical would be triggered
    game_context = play_caller._create_simplified_context(field_state)
    print(f"Game context: {game_context}")
    
    is_red_zone_critical = play_caller._is_red_zone_critical(field_state, game_context)
    print(f"Is red zone critical: {is_red_zone_critical}")
    
    # Test the base probabilities before override
    situation = play_caller._classify_game_situation(field_state)
    print(f"Situation classification: {situation}")
    
    base_probs = PlayCallingBalance.BASE_PLAY_TENDENCIES.get(situation, {})
    print(f"Base probabilities: {base_probs}")
    
    # Test context override directly
    if is_red_zone_critical:
        print("\n🎯 Testing red zone context override...")
        modified_probs = play_caller._apply_red_zone_context(base_probs.copy(), game_context)
        print(f"After red zone context: {modified_probs}")
    else:
        print("\n⚠️  Red zone critical context NOT triggered!")
        
        # Check individual conditions
        in_red_zone = field_state.field_position >= PlayCallingBalance.RED_ZONE_THRESHOLD
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        close_game = abs(score_diff) <= 7
        trailing_with_time_pressure = score_diff < 0 and time_remaining <= 600
        
        print(f"  - In red zone: {in_red_zone}")
        print(f"  - Score diff: {score_diff}")
        print(f"  - Time remaining: {time_remaining}")  
        print(f"  - Close game: {close_game}")
        print(f"  - Trailing with time pressure: {trailing_with_time_pressure}")
        print(f"  - Final condition: {in_red_zone and (close_game or trailing_with_time_pressure)}")

def debug_archetype_differentiation():
    """Debug why conservative and aggressive are behaving the same"""
    print("\n🔍 Debugging Archetype Differentiation")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # 4th & 4 at midfield, tied game
    field_state = FieldState()
    field_state.down = 4
    field_state.yards_to_go = 4
    field_state.field_position = 50
    
    conservative_coord = {"archetype": "conservative"}
    aggressive_coord = {"archetype": "aggressive"}
    
    # Test score differential = 0 (tied)
    play_caller._current_score_differential = 0
    
    situation = play_caller._classify_game_situation(field_state)
    print(f"Situation: {situation}")
    
    base_probs = PlayCallingBalance.BASE_PLAY_TENDENCIES.get(situation, {}).copy()
    print(f"Base probabilities: {base_probs}")
    
    # Test conservative archetype
    print(f"\n🛡️  Conservative Archetype:")
    conservative_probs = play_caller._apply_offensive_archetype(
        base_probs.copy(), conservative_coord, field_state
    )
    print(f"Conservative probabilities: {conservative_probs}")
    
    # Test aggressive archetype  
    print(f"\n⚡ Aggressive Archetype:")
    aggressive_probs = play_caller._apply_offensive_archetype(
        base_probs.copy(), aggressive_coord, field_state
    )
    print(f"Aggressive probabilities: {aggressive_probs}")
    
    # Show the difference
    print(f"\n📊 Difference Analysis:")
    for play_type in base_probs.keys():
        conservative_val = conservative_probs.get(play_type, 0)
        aggressive_val = aggressive_probs.get(play_type, 0)
        diff = aggressive_val - conservative_val
        print(f"  {play_type}: Conservative={conservative_val:.3f}, Aggressive={aggressive_val:.3f}, Diff={diff:+.3f}")

if __name__ == "__main__":
    debug_red_zone_critical()
    debug_archetype_differentiation()