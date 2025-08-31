#!/usr/bin/env python3
"""
Quick Play Execution Test

Fast validation script to ensure the play execution system works correctly.
Runs a series of automated tests with different game situations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.core.play_executor import PlayExecutor
from game_engine.core.game_orchestrator import SimpleGameEngine
from game_engine.field.game_state import GameState
from game_engine.plays.play_factory import PlayFactory


def test_basic_functionality():
    """Test basic play execution functionality"""
    print("🏈 Testing Basic Play Execution")
    print("-" * 35)
    
    # Initialize components
    engine = SimpleGameEngine()
    executor = PlayExecutor()
    game_state = GameState()
    
    # Setup game situation: 2nd & 7 from own 35
    game_state.field.down = 2
    game_state.field.yards_to_go = 7
    game_state.field.field_position = 35
    game_state.field.possession_team_id = 1  # Bears
    game_state.clock.quarter = 2
    game_state.clock.clock = 450  # 7:30 remaining
    
    # Get team data
    offense_team = engine.get_team_for_simulation(1)  # Bears
    defense_team = engine.get_team_for_simulation(2)  # Packers
    
    print(f"Situation: {game_state.field.down}&{game_state.field.yards_to_go} from {game_state.field.field_position}")
    print(f"Matchup: {offense_team['name']} vs {defense_team['name']}")
    
    # Execute play
    play_result = executor.execute_play(offense_team, defense_team, game_state)
    
    # Display results
    print(f"✅ Play executed successfully!")
    print(f"   Type: {play_result.play_type}")
    print(f"   Outcome: {play_result.outcome}")
    print(f"   Yards: {play_result.yards_gained}")
    print(f"   Formation: {play_result.formation}")
    print(f"   Defense: {play_result.defensive_call}")
    print(f"   Summary: {play_result.get_summary()}")
    
    return True


def test_all_play_types():
    """Test all supported play types"""
    print("\n🎯 Testing All Play Types")
    print("-" * 30)
    
    engine = SimpleGameEngine()
    executor = PlayExecutor()
    
    # Get supported play types
    play_types = PlayFactory.get_supported_play_types()
    print(f"Supported play types: {play_types}")
    
    for play_type in play_types:
        try:
            # Create appropriate game situation for each play type
            game_state = GameState()
            
            if play_type == "punt":
                game_state.field.down = 4
                game_state.field.yards_to_go = 12
                game_state.field.field_position = 35
            elif play_type == "field_goal":
                game_state.field.down = 4
                game_state.field.yards_to_go = 3
                game_state.field.field_position = 75  # Close enough for FG
            else:
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                game_state.field.field_position = 25
            
            game_state.field.possession_team_id = 1
            
            # Force the play type by temporarily modifying the executor
            original_method = executor._determine_play_type
            executor._determine_play_type = lambda field_state: play_type
            
            offense_team = engine.get_team_for_simulation(1)
            defense_team = engine.get_team_for_simulation(2)
            
            # Execute play
            play_result = executor.execute_play(offense_team, defense_team, game_state)
            
            print(f"✅ {play_type.upper()}: {play_result.get_summary()}")
            
            # Restore original method
            executor._determine_play_type = original_method
            
        except Exception as e:
            print(f"❌ {play_type.upper()}: Failed - {e}")
            return False
    
    return True


def test_game_situations():
    """Test different game situations"""
    print("\n⚡ Testing Game Situations")
    print("-" * 30)
    
    engine = SimpleGameEngine()
    executor = PlayExecutor()
    
    situations = [
        {"name": "Goal Line", "down": 1, "distance": 1, "field_pos": 99},
        {"name": "Short Yardage", "down": 3, "distance": 2, "field_pos": 45},
        {"name": "Long Distance", "down": 2, "distance": 15, "field_pos": 20},
        {"name": "4th & Long", "down": 4, "distance": 12, "field_pos": 30},
        {"name": "Red Zone", "down": 2, "distance": 8, "field_pos": 85}
    ]
    
    offense_team = engine.get_team_for_simulation(1)
    defense_team = engine.get_team_for_simulation(2)
    
    for situation in situations:
        game_state = GameState()
        game_state.field.down = situation["down"]
        game_state.field.yards_to_go = situation["distance"]
        game_state.field.field_position = situation["field_pos"]
        game_state.field.possession_team_id = 1
        
        try:
            play_result = executor.execute_play(offense_team, defense_team, game_state)
            
            situation_context = ""
            if play_result.goal_line_play:
                situation_context += " [GOAL LINE]"
            if play_result.big_play:
                situation_context += " [BIG PLAY]"
            
            print(f"✅ {situation['name']}: {play_result.play_type} -> {play_result.get_summary()}{situation_context}")
            
        except Exception as e:
            print(f"❌ {situation['name']}: Failed - {e}")
            return False
    
    return True


def test_personnel_system():
    """Test personnel selection system"""
    print("\n👥 Testing Personnel System")
    print("-" * 30)
    
    from game_engine.personnel.player_selector import PlayerSelector
    from game_engine.field.field_state import FieldState
    
    engine = SimpleGameEngine()
    offense_team = engine.get_team_for_simulation(1)
    defense_team = engine.get_team_for_simulation(2)
    player_selector = PlayerSelector()
    
    # Test different personnel situations
    situations = [
        {"play": "run", "down": 1, "distance": 10, "field_pos": 25},
        {"play": "pass", "down": 3, "distance": 8, "field_pos": 45},
        {"play": "run", "down": 3, "distance": 1, "field_pos": 99},  # Goal line
        {"play": "pass", "down": 2, "distance": 15, "field_pos": 20}   # Long distance
    ]
    
    for situation in situations:
        field_state = FieldState()
        field_state.down = situation["down"]
        field_state.yards_to_go = situation["distance"]
        field_state.field_position = situation["field_pos"]
        
        try:
            personnel = player_selector.get_personnel(
                offense_team, defense_team, situation["play"], field_state
            )
            
            print(f"✅ {situation['play']} play: {personnel.formation} vs {personnel.defensive_call}")
            
        except Exception as e:
            print(f"❌ Personnel selection failed: {e}")
            return False
    
    return True


def main():
    """Run all tests"""
    print("🏈 QUICK PLAY EXECUTION TESTS")
    print("=" * 40)
    
    tests = [
        test_basic_functionality,
        test_all_play_types,
        test_game_situations,
        test_personnel_system
    ]
    
    passed = 0
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_func.__name__} failed!")
        except Exception as e:
            print(f"❌ {test_func.__name__} crashed: {e}")
    
    print(f"\n📊 TEST RESULTS")
    print("-" * 20)
    print(f"✅ Passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Play execution system is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    main()