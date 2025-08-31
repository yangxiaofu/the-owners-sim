#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine.plays.run_plays import DetailedRunSimulator
from game_engine.simulation.blocking.data_structures import RunPlayCall, BlockingResult, RunResult

def create_sample_teams():
    """Create sample offensive and defensive teams for testing"""
    
    offense_strong = {
        "offense": {
            "rb_rating": 85,    # Elite RB
            "ol_rating": 80,    # Strong O-Line
            "te_rating": 75     # Good blocking TE
        }
    }
    
    offense_weak = {
        "offense": {
            "rb_rating": 55,    # Weak RB
            "ol_rating": 45,    # Poor O-Line
            "te_rating": 50     # Poor TE
        }
    }
    
    defense_strong = {
        "defense": {
            "dl_rating": 85,    # Elite D-Line
            "lb_rating": 80,    # Strong LBs
            "db_rating": 75     # Good secondary
        }
    }
    
    defense_weak = {
        "defense": {
            "dl_rating": 50,    # Weak D-Line
            "lb_rating": 55,    # Poor LBs
            "db_rating": 60     # Average secondary
        }
    }
    
    return offense_strong, offense_weak, defense_strong, defense_weak

def test_individual_blocking_matchups():
    """Test that blocking calculations work correctly"""
    print("Testing individual blocking matchups...")
    
    simulator = DetailedRunSimulator()
    offense_strong, _, defense_weak, defense_strong = create_sample_teams()
    
    # Test strong offense vs weak defense
    play_call = RunPlayCall(direction="center", play_type="power", formation="I_formation")
    result = simulator.simulate_run(offense_strong, defense_weak, play_call)
    
    print(f"  Strong O vs Weak D: {result.yards_gained} yards ({result.outcome})")
    print(f"    Blocking success: {sum(1 for r in result.blocking_results if r.success)}/{len(result.blocking_results)}")
    print(f"    RB success rate: {result.rb_vs_defenders['success_rate']:.2f}")
    print(f"    Breakdown: {result.play_breakdown}")
    
    # Test weak offense vs strong defense  
    result2 = simulator.simulate_run(offense_strong, defense_strong, play_call)
    print(f"\n  Strong O vs Strong D: {result2.yards_gained} yards ({result2.outcome})")
    print(f"    Blocking success: {sum(1 for r in result2.blocking_results if r.success)}/{len(result2.blocking_results)}")
    print(f"    Breakdown: {result2.play_breakdown}")

def test_play_type_differences():
    """Test that different play types produce different results"""
    print("\nTesting different play types...")
    
    simulator = DetailedRunSimulator()
    offense, _, _, defense = create_sample_teams()
    
    play_types = ["dive", "power", "sweep", "draw", "counter"]
    
    for play_type in play_types:
        results = []
        for _ in range(20):  # Run 20 simulations of each play type
            play_call = RunPlayCall(direction="center", play_type=play_type, formation="singleback")
            result = simulator.simulate_run(offense, defense, play_call)
            results.append(result.yards_gained)
        
        avg_yards = sum(results) / len(results)
        print(f"  {play_type.upper()}: Avg {avg_yards:.1f} yards (Range: {min(results)} to {max(results)})")

def test_direction_differences():
    """Test that run direction affects results"""
    print("\nTesting run direction differences...")
    
    simulator = DetailedRunSimulator()
    offense, _, _, defense = create_sample_teams()
    
    directions = ["left", "right", "center"]
    
    for direction in directions:
        results = []
        blocking_success_rates = []
        
        for _ in range(15):
            play_call = RunPlayCall(direction=direction, play_type="dive", formation="singleback")
            result = simulator.simulate_run(offense, defense, play_call)
            results.append(result.yards_gained)
            
            success_rate = sum(1 for r in result.blocking_results if r.success) / len(result.blocking_results)
            blocking_success_rates.append(success_rate)
        
        avg_yards = sum(results) / len(results)
        avg_blocking = sum(blocking_success_rates) / len(blocking_success_rates)
        
        print(f"  {direction.upper()}: Avg {avg_yards:.1f} yards, {avg_blocking:.1%} blocking success")

def test_edge_cases():
    """Test extreme scenarios"""
    print("\nTesting edge cases...")
    
    simulator = DetailedRunSimulator()
    
    # Create extreme teams
    offense_elite = {
        "offense": {"rb_rating": 99, "ol_rating": 99, "te_rating": 99}
    }
    offense_terrible = {
        "offense": {"rb_rating": 20, "ol_rating": 20, "te_rating": 20}
    }
    defense_elite = {
        "defense": {"dl_rating": 99, "lb_rating": 99, "db_rating": 99}
    }
    defense_terrible = {
        "defense": {"dl_rating": 20, "lb_rating": 20, "db_rating": 20}
    }
    
    test_scenarios = [
        ("Elite O vs Terrible D", offense_elite, defense_terrible),
        ("Terrible O vs Elite D", offense_terrible, defense_elite),
        ("Elite O vs Elite D", offense_elite, defense_elite),
        ("Terrible O vs Terrible D", offense_terrible, defense_terrible)
    ]
    
    for scenario_name, offense, defense in test_scenarios:
        results = []
        touchdowns = 0
        fumbles = 0
        
        for _ in range(50):
            play_call = RunPlayCall.default_inside_run()
            result = simulator.simulate_run(offense, defense, play_call)
            results.append(result.yards_gained)
            
            if result.outcome == "touchdown":
                touchdowns += 1
            elif result.outcome == "fumble":
                fumbles += 1
        
        avg_yards = sum(results) / len(results)
        print(f"  {scenario_name}: Avg {avg_yards:.1f} yards, {touchdowns} TDs, {fumbles} fumbles")

def test_detailed_breakdown():
    """Test the play breakdown text generation"""
    print("\nTesting play breakdown generation...")
    
    simulator = DetailedRunSimulator()
    offense, _, _, defense = create_sample_teams()
    
    # Run a few plays and show detailed breakdowns
    for i in range(3):
        play_call = RunPlayCall(
            direction=["left", "right", "center"][i % 3],
            play_type=["power", "sweep", "dive"][i % 3], 
            formation="singleback"
        )
        
        result = simulator.simulate_run(offense, defense, play_call)
        
        print(f"\n  Play {i+1}: {play_call.play_type.title()} {play_call.direction}")
        print(f"    Result: {result.yards_gained} yards ({result.outcome})")
        print(f"    Breakdown: {result.play_breakdown}")
        
        # Show individual blocking results
        print("    Blocking details:")
        for block in result.blocking_results:
            status = "✓" if block.success else "✗"
            print(f"      {status} {block.blocker_position}({block.blocker_rating}) vs {block.defender_position}({block.defender_rating})")

def test_statistical_distribution():
    """Test that results follow expected statistical patterns"""
    print("\nTesting statistical distribution over many plays...")
    
    simulator = DetailedRunSimulator()
    offense, _, _, defense = create_sample_teams()
    
    results = []
    outcomes = {"gain": 0, "touchdown": 0, "fumble": 0, "safety": 0}
    
    # Run 1000 plays
    for _ in range(1000):
        play_call = RunPlayCall.default_inside_run()
        result = simulator.simulate_run(offense, defense, play_call)
        results.append(result.yards_gained)
        outcomes[result.outcome] += 1
    
    # Calculate statistics
    avg_yards = sum(results) / len(results)
    positive_plays = sum(1 for y in results if y > 0)
    big_plays = sum(1 for y in results if y >= 10)  # 10+ yard gains
    losses = sum(1 for y in results if y < 0)
    
    print(f"  1000 plays summary:")
    print(f"    Average yards: {avg_yards:.2f}")
    print(f"    Positive plays: {positive_plays}/1000 ({positive_plays/10:.1f}%)")
    print(f"    Big plays (10+): {big_plays}/1000 ({big_plays/10:.1f}%)")
    print(f"    Losses: {losses}/1000 ({losses/10:.1f}%)")
    print(f"    Outcomes: {outcomes}")

def main():
    print("=" * 60)
    print("         DETAILED RUN SIMULATION TEST SUITE")
    print("=" * 60)
    
    test_individual_blocking_matchups()
    test_play_type_differences()
    test_direction_differences()  
    test_edge_cases()
    test_detailed_breakdown()
    test_statistical_distribution()
    
    print("\n" + "=" * 60)
    print("All detailed run simulation tests completed!")

if __name__ == "__main__":
    main()