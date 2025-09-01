#!/usr/bin/env python3
"""
NFL Realism Validation Test Suite

Tests critical scenarios to ensure coaching decisions match NFL realism:
1. Conservative vs Aggressive archetype differentiation
2. 4th down desperation context override behavior 
3. Two-point conversion decision logic
4. Critical game situation response patterns
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game_engine.coaching.clock.context.game_context import GameContext
from src.game_engine.field.game_state import GameState
from src.game_engine.field.field_state import FieldState
from src.game_engine.plays.play_calling import PlayCaller

def create_test_scenario(quarter: int, time_remaining: int, home_score: int, away_score: int, 
                        field_position: int, down: int, yards_to_go: int):
    """Create a test game scenario"""
    game_state = GameState()
    
    # Set field state
    game_state.field.down = down
    game_state.field.yards_to_go = yards_to_go
    game_state.field.field_position = field_position
    game_state.field.possession_team_id = 1  # Home team has possession
    
    # Set clock
    game_state.clock.quarter = quarter
    game_state.clock.clock = time_remaining
    
    # Set scoreboard
    game_state.scoreboard.home_team_id = 1
    game_state.scoreboard.away_team_id = 2
    game_state.scoreboard.home_score = home_score
    game_state.scoreboard.away_score = away_score
    
    return game_state

def test_archetype_differentiation():
    """Test that conservative and aggressive archetypes behave differently"""
    print("🧪 Testing Archetype Differentiation")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Critical 4th down scenario: 4th & 4 at midfield, tied game, 5 minutes left
    game_state = create_test_scenario(
        quarter=4, time_remaining=300, home_score=14, away_score=14,
        field_position=50, down=4, yards_to_go=4
    )
    
    conservative_coord = {"archetype": "conservative"}
    aggressive_coord = {"archetype": "aggressive"}
    
    # Test multiple trials to see decision patterns
    conservative_decisions = []
    aggressive_decisions = []
    
    for i in range(20):
        # Test conservative archetype
        conservative_decision = play_caller.determine_play_type(
            game_state.field, conservative_coord, score_differential=0
        )
        conservative_decisions.append(conservative_decision)
        
        # Test aggressive archetype
        aggressive_decision = play_caller.determine_play_type(
            game_state.field, aggressive_coord, score_differential=0
        )
        aggressive_decisions.append(aggressive_decision)
    
    # Analyze patterns
    conservative_punt = conservative_decisions.count("punt")
    conservative_go_for_it = len([d for d in conservative_decisions if d in ["run", "pass"]])
    
    aggressive_punt = aggressive_decisions.count("punt")
    aggressive_go_for_it = len([d for d in aggressive_decisions if d in ["run", "pass"]])
    
    print(f"Conservative 4th Down (20 trials): Punt={conservative_punt}, Go-for-it={conservative_go_for_it}")
    print(f"Aggressive 4th Down (20 trials): Punt={aggressive_punt}, Go-for-it={aggressive_go_for_it}")
    
    # NFL realism expectations
    conservative_should_punt_more = conservative_punt > aggressive_punt
    aggressive_should_go_more = aggressive_go_for_it > conservative_go_for_it
    
    print(f"✅ Conservative punts more: {conservative_should_punt_more}")
    print(f"✅ Aggressive goes for it more: {aggressive_should_go_more}")
    
    return conservative_should_punt_more and aggressive_should_go_more

def test_desperation_context_override():
    """Test that desperation context overrides normal archetype behavior"""
    print("\n🧪 Testing Desperation Context Override")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Desperation scenario: Down by 10, 4th & 3, 2:30 remaining, opponent territory
    game_state = create_test_scenario(
        quarter=4, time_remaining=150, home_score=7, away_score=17,
        field_position=65, down=4, yards_to_go=3
    )
    
    conservative_coord = {"archetype": "conservative"}
    
    # Even conservative coaches should be aggressive in desperation
    decisions = []
    for i in range(20):
        decision = play_caller.determine_play_type(
            game_state.field, conservative_coord, score_differential=-10
        )
        decisions.append(decision)
    
    punt_count = decisions.count("punt")
    go_for_it_count = len([d for d in decisions if d in ["run", "pass"]])
    fg_count = decisions.count("field_goal")
    
    print(f"Conservative in Desperation (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}, FG={fg_count}")
    
    # NFL realism: Conservative coaches should still go for it in desperation (punt <25%)
    desperation_override_working = punt_count <= 5  # 25% or less
    
    print(f"✅ Desperation override working (punt ≤25%): {desperation_override_working}")
    
    return desperation_override_working

def test_protect_lead_behavior():
    """Test that coaches protect leads appropriately"""
    print("\n🧪 Testing Protect Lead Behavior")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Protect lead scenario: Leading by 7, 4th & 5, 6 minutes left, own territory
    game_state = create_test_scenario(
        quarter=4, time_remaining=360, home_score=21, away_score=14,
        field_position=35, down=4, yards_to_go=5
    )
    
    aggressive_coord = {"archetype": "aggressive"}
    
    # Even aggressive coaches should be more conservative when protecting leads
    decisions = []
    for i in range(20):
        decision = play_caller.determine_play_type(
            game_state.field, aggressive_coord, score_differential=7
        )
        decisions.append(decision)
    
    punt_count = decisions.count("punt")
    go_for_it_count = len([d for d in decisions if d in ["run", "pass"]])
    
    print(f"Aggressive Protecting Lead (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}")
    
    # NFL realism: Even aggressive coaches should punt more when protecting leads (punt >60%)
    protect_lead_working = punt_count >= 12  # 60% or more
    
    print(f"✅ Protect lead behavior working (punt ≥60%): {protect_lead_working}")
    
    return protect_lead_working

def test_red_zone_critical_context():
    """Test red zone critical context for touchdown emphasis"""
    print("\n🧪 Testing Red Zone Critical Context")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # Red zone critical: Down by 4, 4th & goal from 5, 3 minutes left
    game_state = create_test_scenario(
        quarter=4, time_remaining=180, home_score=17, away_score=21,
        field_position=95, down=4, yards_to_go=5  # Goal line
    )
    
    conservative_coord = {"archetype": "conservative"}
    
    decisions = []
    for i in range(20):
        decision = play_caller.determine_play_type(
            game_state.field, conservative_coord, score_differential=-4
        )
        decisions.append(decision)
    
    fg_count = decisions.count("field_goal")
    td_attempts = len([d for d in decisions if d in ["run", "pass"]])
    
    print(f"Red Zone Critical (20 trials): FG={fg_count}, TD attempts={td_attempts}")
    
    # NFL realism: When trailing by more than FG, should favor TD attempts
    red_zone_working = td_attempts >= fg_count  # More TD attempts than FGs
    
    print(f"✅ Red zone critical context working (TD attempts ≥ FG): {red_zone_working}")
    
    return red_zone_working

def test_time_urgency_factors():
    """Test time urgency factors in 2-minute drill scenarios"""
    print("\n🧪 Testing Time Urgency Factors")
    print("=" * 50)
    
    play_caller = PlayCaller()
    
    # 2-minute drill: Down by 7, 4th & 6, 1:45 remaining, opponent territory
    game_state = create_test_scenario(
        quarter=4, time_remaining=105, home_score=14, away_score=21,
        field_position=55, down=4, yards_to_go=6
    )
    
    balanced_coord = {"archetype": "balanced"}
    
    decisions = []
    for i in range(20):
        decision = play_caller.determine_play_type(
            game_state.field, balanced_coord, score_differential=-7
        )
        decisions.append(decision)
    
    punt_count = decisions.count("punt")
    go_for_it_count = len([d for d in decisions if d in ["run", "pass"]])
    
    print(f"2-Minute Drill Urgency (20 trials): Punt={punt_count}, Go-for-it={go_for_it_count}")
    
    # NFL realism: 2-minute drill should drastically reduce punting
    time_urgency_working = punt_count <= 4  # 20% or less punting
    
    print(f"✅ Time urgency factors working (punt ≤20%): {time_urgency_working}")
    
    return time_urgency_working

def run_nfl_realism_validation():
    """Run all NFL realism validation tests"""
    print("🏈 NFL REALISM VALIDATION TEST SUITE")
    print("=" * 60)
    print("Testing contextual decision-making for NFL coaching realism\n")
    
    # Run all validation tests
    test_results = {}
    test_results["archetype_differentiation"] = test_archetype_differentiation()
    test_results["desperation_override"] = test_desperation_context_override()
    test_results["protect_lead"] = test_protect_lead_behavior()
    test_results["red_zone_critical"] = test_red_zone_critical_context()
    test_results["time_urgency"] = test_time_urgency_factors()
    
    # Summary
    print("\n" + "=" * 60)
    print("NFL REALISM VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 ALL NFL REALISM TESTS PASSED!")
        print("The contextual decision-making system demonstrates NFL-realistic behavior.")
    else:
        print(f"⚠️  {total_tests - passed_tests} NFL realism issues identified.")
        print("Some coaching decisions do not match expected NFL patterns.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_nfl_realism_validation()
    exit(0 if success else 1)