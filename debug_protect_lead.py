#!/usr/bin/env python3
"""Debug protect lead context override"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game_engine.field.field_state import FieldState
from src.game_engine.plays.play_calling import PlayCaller, PlayCallingBalance

def debug_protect_lead():
    """Debug why protect lead isn't working"""
    print("🔍 Debugging Protect Lead Behavior")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Same scenario as the failing test: Leading by 7, 4th & 5, 6 minutes left
    field_state = FieldState()
    field_state.down = 4
    field_state.yards_to_go = 5
    field_state.field_position = 35  # Own territory
    
    aggressive_coord = {"archetype": "aggressive"}
    
    # Set score differential for context overrides (leading by 7)
    play_caller._current_score_differential = 7
    
    print(f"Score differential: {play_caller._current_score_differential}")
    print(f"Field position: {field_state.field_position}")
    print(f"Down and distance: {field_state.down} & {field_state.yards_to_go}")
    
    # Create game context
    game_context = play_caller._create_simplified_context(field_state)
    print(f"Game context: {game_context}")
    
    # Check if protect lead would be triggered
    should_protect = play_caller._should_protect_lead(game_context)
    print(f"Should protect lead: {should_protect}")
    
    if should_protect:
        print("✅ Protect lead context would be triggered")
    else:
        print("❌ Protect lead context NOT triggered")
        
        # Check individual conditions
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 900)
        
        score_condition = score_diff >= PlayCallingBalance.PROTECT_LEAD_SCORE_THRESHOLD
        time_condition = time_remaining <= PlayCallingBalance.PROTECT_LEAD_TIME_THRESHOLD
        
        print(f"  - Score diff: {score_diff} >= {PlayCallingBalance.PROTECT_LEAD_SCORE_THRESHOLD}: {score_condition}")
        print(f"  - Time remaining: {time_remaining} <= {PlayCallingBalance.PROTECT_LEAD_TIME_THRESHOLD}: {time_condition}")
        print(f"  - Combined condition: {score_condition and time_condition}")
    
    # Test the archetype modification
    situation = play_caller._classify_game_situation(field_state)
    print(f"\nSituation: {situation}")
    
    base_probs = PlayCallingBalance.BASE_PLAY_TENDENCIES[situation].copy()
    print(f"Base probabilities: {base_probs}")
    
    # Apply aggressive archetype
    modified_probs = play_caller._apply_offensive_archetype(
        base_probs.copy(), aggressive_coord, field_state
    )
    print(f"Aggressive archetype probabilities: {modified_probs}")

if __name__ == "__main__":
    debug_protect_lead()