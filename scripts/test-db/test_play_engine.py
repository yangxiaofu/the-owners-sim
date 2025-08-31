#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine import PlayEngine, GameState, PlayResult, SimpleGameEngine

def test_individual_play():
    """Test a single play execution"""
    print("Testing individual play execution...")
    
    play_engine = PlayEngine()
    game_state = GameState()
    
    # Sample team data
    offense_team = {
        "offense": {"qb_rating": 75, "rb_rating": 70, "wr_rating": 80, "ol_rating": 65, "te_rating": 70},
        "defense": {"dl_rating": 60, "lb_rating": 65, "db_rating": 70}
    }
    defense_team = {
        "offense": {"qb_rating": 65, "rb_rating": 75, "wr_rating": 65, "ol_rating": 70, "te_rating": 60},
        "defense": {"dl_rating": 80, "lb_rating": 75, "db_rating": 78}
    }
    
    # Execute several plays
    for i in range(5):
        play_result = play_engine.execute_play(offense_team, defense_team, game_state)
        print(f"  Play {i+1}: {play_result.play_type} -> {play_result.outcome} ({play_result.yards_gained} yards, {play_result.time_elapsed}s)")
        
        # Update game state if it's a normal play
        if not play_result.is_turnover and not play_result.is_score and play_result.play_type not in ["punt", "field_goal"]:
            game_state.field.update_down(play_result.yards_gained)
            print(f"    Down: {game_state.field.down}, Yards to go: {game_state.field.yards_to_go}, Field position: {game_state.field.field_position}")

def test_game_state():
    """Test game state management"""
    print("\nTesting game state management...")
    
    game_state = GameState()
    print(f"Initial state: Down {game_state.field.down}, {game_state.field.yards_to_go} to go")
    
    # Test first down conversion
    result = game_state.field.update_down(12)
    print(f"After 12-yard gain: Down {game_state.field.down}, {game_state.field.yards_to_go} to go, Result: {result}")
    
    # Test normal down progression
    result = game_state.field.update_down(4)
    print(f"After 4-yard gain: Down {game_state.field.down}, {game_state.field.yards_to_go} to go, Result: {result}")
    
    result = game_state.field.update_down(2)
    print(f"After 2-yard gain: Down {game_state.field.down}, {game_state.field.yards_to_go} to go, Result: {result}")

def test_full_game_simulation():
    """Test complete game with play-by-play"""
    print("\nTesting full game simulation...")
    
    engine = SimpleGameEngine()
    
    print("🏈 Simulating Cowboys vs Packers...")
    result = engine.simulate_game(5, 2)  # Cowboys (ID 5) vs Packers (ID 2)
    
    print(f"\n📊 FINAL RESULT:")
    print(f"Cowboys: {result.home_score}")  
    print(f"Packers: {result.away_score}")
    print(f"Winner: Team {result.winner_id}" if result.winner_id else "Tie game")
    
def test_play_type_distribution():
    """Test that play calling seems reasonable"""
    print("\nTesting play type distribution...")
    
    play_engine = PlayEngine()
    play_counts = {"run": 0, "pass": 0, "punt": 0, "field_goal": 0}
    
    # Test different down/distance situations
    situations = [
        (1, 10, "1st and 10"),
        (2, 7, "2nd and 7"), 
        (3, 12, "3rd and 12"),
        (4, 8, "4th and 8"),
        (4, 2, "4th and 2")
    ]
    
    for down, yards_to_go, description in situations:
        print(f"\n{description} play calling (50 samples):")
        situation_counts = {"run": 0, "pass": 0, "punt": 0, "field_goal": 0}
        
        for _ in range(50):
            play_type = play_engine._determine_play_type(down, yards_to_go)
            situation_counts[play_type] += 1
            
        for play_type, count in situation_counts.items():
            if count > 0:
                print(f"  {play_type}: {count} ({count/50*100:.0f}%)")

def main():
    print("="*50)
    print("       PLAY ENGINE TEST SUITE")
    print("="*50)
    
    test_individual_play()
    test_game_state()
    test_play_type_distribution()
    test_full_game_simulation()
    
    print("\n" + "="*50)
    print("All tests completed!")

if __name__ == "__main__":
    main()