#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine.simulation.blocking.simulator import BlockingSimulator
from game_engine.simulation.blocking.strategies import (
    RunBlockingStrategy, PassBlockingStrategy, BlockingContext
)

def test_run_blocking_scenarios():
    """Test various run blocking scenarios"""
    print("=== RUN BLOCKING SCENARIOS ===")
    
    simulator = BlockingSimulator(RunBlockingStrategy())
    
    # Elite offense vs average defense
    elite_blockers = {
        "LT": 95, "LG": 90, "C": 92, "RG": 88, "RT": 94, "TE": 85
    }
    average_defenders = {
        "LE": 78, "DT1": 80, "NT": 82, "DT2": 79, "RE": 81, "OLB": 75
    }
    
    print("\n1. Power Run (Elite OL vs Average Defense)")
    context = BlockingContext.for_run_play("power", "center", "I_formation", 3, 2, 95)
    results = simulator.simulate_matchups(elite_blockers, average_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    grade = simulator.calculate_overall_blocking_grade(results)
    
    print(f"   Matchups: {len(results)}")
    print(f"   Successful blocks: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"   Overall grade: {grade:.3f}")
    
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} {result.blocker_position}({result.blocker_rating}) vs {result.defender_position}({result.defender_rating}) - Impact: {result.impact_factor:.2f}")
    
    # Average offense vs elite defense
    average_blockers = {
        "LT": 75, "LG": 72, "C": 78, "RG": 74, "RT": 76
    }
    elite_defenders = {
        "LE": 92, "DT": 95, "NT": 90, "RE": 94, "OLB": 88
    }
    
    print("\n2. Sweep Run (Average OL vs Elite Defense)")
    context = BlockingContext.for_run_play("sweep", "right", "singleback", 1, 10, 50)
    results = simulator.simulate_matchups(average_blockers, elite_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    grade = simulator.calculate_overall_blocking_grade(results)
    
    print(f"   Matchups: {len(results)}")
    print(f"   Successful blocks: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"   Overall grade: {grade:.3f}")
    
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} {result.blocker_position}({result.blocker_rating}) vs {result.defender_position}({result.defender_rating}) - Impact: {result.impact_factor:.2f}")

def test_pass_protection_scenarios():
    """Test various pass protection scenarios"""
    print("\n\n=== PASS PROTECTION SCENARIOS ===")
    
    simulator = BlockingSimulator(PassBlockingStrategy())
    
    # Balanced matchup
    balanced_blockers = {
        "LT": 85, "LG": 80, "C": 83, "RG": 82, "RT": 87, "RB": 70
    }
    balanced_defenders = {
        "LE": 84, "DT1": 81, "NT": 85, "DT2": 80, "RE": 88
    }
    
    print("\n1. Deep Pass (Max Protection)")
    context = BlockingContext.for_pass_play("deep", "max_protect", "shotgun", 3, 12, 30)
    results = simulator.simulate_matchups(balanced_blockers, balanced_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    grade = simulator.calculate_overall_blocking_grade(results)
    
    print(f"   Matchups: {len(results)}")
    print(f"   Successful blocks: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"   Overall grade: {grade:.3f}")
    
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} {result.blocker_position}({result.blocker_rating}) vs {result.defender_position}({result.defender_rating}) - Impact: {result.impact_factor:.2f}")
    
    print("\n2. Quick Pass (Slide Protection)")
    context = BlockingContext.for_pass_play("quick", "slide", "shotgun", 1, 10, 50)
    results = simulator.simulate_matchups(balanced_blockers, balanced_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    grade = simulator.calculate_overall_blocking_grade(results)
    
    print(f"   Matchups: {len(results)}")
    print(f"   Successful blocks: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"   Overall grade: {grade:.3f}")
    
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} {result.blocker_position}({result.blocker_rating}) vs {result.defender_position}({result.defender_rating}) - Impact: {result.impact_factor:.2f}")

def test_situational_blocking():
    """Test how different situations affect blocking"""
    print("\n\n=== SITUATIONAL BLOCKING TESTS ===")
    
    run_sim = BlockingSimulator(RunBlockingStrategy())
    pass_sim = BlockingSimulator(PassBlockingStrategy())
    
    blockers = {"LT": 80, "LG": 75, "C": 78, "RG": 76, "RT": 82}
    defenders = {"LE": 82, "DT": 85, "NT": 80, "RE": 83, "OLB": 77}
    
    situations = [
        ("1st & 10 (midfield)", 1, 10, 50),
        ("3rd & 2 (short yardage)", 3, 2, 60),
        ("3rd & 15 (obvious pass)", 3, 15, 25),
        ("4th & 1 (goal line)", 4, 1, 99)
    ]
    
    for desc, down, yards, field_pos in situations:
        print(f"\n{desc}:")
        
        # Run blocking
        run_context = BlockingContext.for_run_play("dive", "center", "I_formation", down, yards, field_pos)
        run_results = run_sim.simulate_matchups(blockers, defenders, run_context)
        run_success = sum(1 for r in run_results if r.success) / len(run_results)
        
        # Pass blocking  
        pass_context = BlockingContext.for_pass_play("intermediate", "slide", "shotgun", down, yards, field_pos)
        pass_results = pass_sim.simulate_matchups(blockers, defenders, pass_context)
        pass_success = sum(1 for r in pass_results if r.success) / len(pass_results)
        
        print(f"   Run blocking success: {run_success*100:.1f}%")
        print(f"   Pass protection success: {pass_success*100:.1f}%")

def test_multiple_simulations():
    """Run multiple simulations to show variance"""
    print("\n\n=== SIMULATION VARIANCE TEST ===")
    
    simulator = BlockingSimulator(RunBlockingStrategy())
    
    blockers = {"LT": 85, "LG": 80, "C": 82, "RG": 79, "RT": 86}
    defenders = {"LE": 83, "DT": 87, "NT": 81, "RE": 85}
    
    context = BlockingContext.for_run_play("power", "left", "I_formation", 1, 10, 50)
    
    print("\nRunning 10 identical power run simulations:")
    print("Run # | Success Rate | Overall Grade | Unblocked Defenders")
    print("-" * 55)
    
    for i in range(10):
        results = simulator.simulate_matchups(blockers, defenders, context)
        successful = sum(1 for r in results if r.success)
        success_rate = successful / len(results)
        grade = simulator.calculate_overall_blocking_grade(results)
        unblocked = len(simulator.get_unblocked_defenders(results))
        
        print(f"  {i+1:2d}  |    {success_rate*100:5.1f}%   |    {grade:6.3f}    |        {unblocked}")

def test_extreme_matchups():
    """Test extreme rating differences"""
    print("\n\n=== EXTREME MATCHUP TESTS ===")
    
    run_sim = BlockingSimulator(RunBlockingStrategy())
    
    print("\n1. Elite OL vs Terrible Defense:")
    elite_blockers = {"LT": 99, "LG": 98, "C": 99}
    terrible_defenders = {"LE": 40, "DT": 35, "NT": 38}
    
    context = BlockingContext.for_run_play("dive", "center", "singleback", 1, 10, 50)
    results = run_sim.simulate_matchups(elite_blockers, terrible_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    print(f"   Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    
    print("\n2. Terrible OL vs Elite Defense:")
    terrible_blockers = {"LT": 35, "LG": 40, "C": 38}
    elite_defenders = {"LE": 99, "DT": 98, "NT": 99}
    
    results = run_sim.simulate_matchups(terrible_blockers, elite_defenders, context)
    
    successful = sum(1 for r in results if r.success)
    print(f"   Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")

def main():
    print("=== BLOCKING SIMULATOR TEST SCRIPT ===")
    print("This script demonstrates various blocking simulation scenarios\n")
    
    test_run_blocking_scenarios()
    test_pass_protection_scenarios()
    test_situational_blocking()
    test_multiple_simulations()
    test_extreme_matchups()
    
    print("\n" + "=" * 50)
    print("All blocking simulator tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()