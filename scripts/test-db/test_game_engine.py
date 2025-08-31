#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine import SimpleGameEngine

def test_game_simulation():
    engine = SimpleGameEngine()
    
    print("Testing game simulation...")
    
    result = engine.simulate_game(home_team_id=1, away_team_id=2)
    
    print(f"Game Result:")
    print(f"  Home Team (ID: {result.home_team_id}): {result.home_score}")
    print(f"  Away Team (ID: {result.away_team_id}): {result.away_score}")
    print(f"  Winner: Team {result.winner_id}" if result.winner_id else "  Result: Tie")
    
    print(f"\nSimulation completed successfully!")

if __name__ == "__main__":
    test_game_simulation()