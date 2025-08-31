#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine.simulation.blocking.strategies import (
    RunBlockingStrategy, PassBlockingStrategy, BlockingContext
)
from game_engine.simulation.blocking.simulator import BlockingSimulator
from game_engine.plays.run_plays import DetailedRunSimulator

def test_blocking_context_creation():
    """Test BlockingContext factory methods"""
    print("Testing BlockingContext creation...")
    
    # Test run play context
    run_context = BlockingContext.for_run_play(
        play_type="power",
        direction="left", 
        formation="I_formation",
        down=3,
        yards_to_go=2,
        field_position=95
    )
    
    assert run_context.blocking_type == "run_blocking"
    assert run_context.play_details["play_type"] == "power"
    assert run_context.situation["down"] == 3
    print("  ✓ Run play context created correctly")
    
    # Test pass play context
    pass_context = BlockingContext.for_pass_play(
        pass_type="deep",
        protection_scheme="max_protect",
        formation="shotgun",
        down=3,
        yards_to_go=15,
        field_position=25
    )
    
    assert pass_context.blocking_type == "pass_protection"
    assert pass_context.play_details["pass_type"] == "deep"
    assert pass_context.situation["yards_to_go"] == 15
    print("  ✓ Pass play context created correctly")

def test_run_blocking_strategy():
    """Test run blocking strategy calculations"""
    print("\nTesting RunBlockingStrategy...")
    
    strategy = RunBlockingStrategy()
    
    # Test power run context (should favor guards/center)
    context = BlockingContext.for_run_play("power", "center", "I_formation", 1, 10, 50)
    
    # Test basic matchup calculation
    prob_guard_vs_dt = strategy.calculate_matchup_probability(80, 75, "LG", "DT", context)
    prob_tackle_vs_de = strategy.calculate_matchup_probability(80, 75, "LT", "DE", context)
    
    print(f"  Guard vs DT (power): {prob_guard_vs_dt:.3f}")
    print(f"  Tackle vs DE (power): {prob_tackle_vs_de:.3f}")
    
    # Guards should get bonus in power runs
    assert prob_guard_vs_dt > prob_tackle_vs_de, "Guards should be better in power runs"
    
    # Test situational modifiers
    short_yardage_context = BlockingContext.for_run_play("dive", "center", "I_formation", 3, 1, 95)
    base_prob = 0.6
    modified_prob = strategy.apply_situation_modifiers(base_prob, "C", short_yardage_context)
    
    print(f"  Short yardage modifier: {base_prob:.3f} -> {modified_prob:.3f}")
    assert modified_prob > base_prob, "Short yardage should boost blocking"
    
    print("  ✓ Run blocking strategy working correctly")

def test_pass_blocking_strategy():
    """Test pass blocking strategy calculations"""
    print("\nTesting PassBlockingStrategy...")
    
    strategy = PassBlockingStrategy()
    
    # Test pass protection context
    context = BlockingContext.for_pass_play("deep", "max_protect", "shotgun", 3, 12, 30)
    
    # Test basic matchup calculation (should favor pass rushers)
    prob_tackle_vs_edge = strategy.calculate_matchup_probability(80, 80, "LT", "DE", context)
    prob_guard_vs_dt = strategy.calculate_matchup_probability(80, 80, "LG", "DT", context)
    
    print(f"  Tackle vs Edge rusher: {prob_tackle_vs_edge:.3f}")
    print(f"  Guard vs DT: {prob_guard_vs_dt:.3f}")
    
    # Should be harder than run blocking
    assert prob_tackle_vs_edge < 0.6, "Pass protection should be challenging"
    
    # Test quick pass vs deep pass
    quick_context = BlockingContext.for_pass_play("quick", "slide", "shotgun", 1, 10, 50)
    quick_prob = strategy.calculate_matchup_probability(75, 80, "LT", "DE", quick_context)
    
    deep_context = BlockingContext.for_pass_play("deep", "slide", "shotgun", 1, 10, 50)
    deep_prob = strategy.calculate_matchup_probability(75, 80, "LT", "DE", deep_context)
    
    print(f"  Quick pass protection: {quick_prob:.3f}")
    print(f"  Deep pass protection: {deep_prob:.3f}")
    
    assert quick_prob > deep_prob, "Quick passes should be easier to protect"
    
    print("  ✓ Pass blocking strategy working correctly")

def test_blocking_simulator():
    """Test the BlockingSimulator with different strategies"""
    print("\nTesting BlockingSimulator...")
    
    # Create sample blockers and defenders
    blockers = {
        "LT": 80,
        "LG": 75,
        "C": 78,
        "RG": 76,
        "RT": 82
    }
    
    defenders = {
        "LE": 78,
        "DT": 85,
        "NT": 80,
        "DE": 83,
        "OLB": 75
    }
    
    # Test with run blocking strategy
    run_strategy = RunBlockingStrategy()
    run_simulator = BlockingSimulator(run_strategy)
    
    run_context = BlockingContext.for_run_play("power", "center", "I_formation", 1, 10, 50)
    run_results = run_simulator.simulate_matchups(blockers, defenders, run_context)
    
    print(f"  Run blocking results: {len(run_results)} matchups")
    successful_run_blocks = sum(1 for r in run_results if r.success)
    print(f"  Successful run blocks: {successful_run_blocks}/{len(run_results)}")
    
    # Test with pass blocking strategy
    pass_strategy = PassBlockingStrategy()
    pass_simulator = BlockingSimulator(pass_strategy)
    
    pass_context = BlockingContext.for_pass_play("intermediate", "slide", "shotgun", 2, 8, 40)
    pass_results = pass_simulator.simulate_matchups(blockers, defenders, pass_context)
    
    print(f"  Pass blocking results: {len(pass_results)} matchups")
    successful_pass_blocks = sum(1 for r in pass_results if r.success)
    print(f"  Successful pass blocks: {successful_pass_blocks}/{len(pass_results)}")
    
    # Calculate overall grades
    run_grade = run_simulator.calculate_overall_blocking_grade(run_results)
    pass_grade = pass_simulator.calculate_overall_blocking_grade(pass_results)
    
    print(f"  Run blocking grade: {run_grade:.3f}")
    print(f"  Pass blocking grade: {pass_grade:.3f}")
    
    print("  ✓ BlockingSimulator working with both strategies")

def test_strategy_differences():
    """Test that different strategies produce meaningfully different results"""
    print("\nTesting strategy differences...")
    
    blockers = {"LT": 80, "LG": 75, "C": 78}
    defenders = {"DE": 85, "DT": 80, "LB": 75}
    
    # Same matchup with different strategies
    run_context = BlockingContext.for_run_play("power", "left", "I_formation", 3, 2, 95)
    pass_context = BlockingContext.for_pass_play("deep", "max_protect", "shotgun", 3, 15, 25)
    
    run_sim = BlockingSimulator(RunBlockingStrategy())
    pass_sim = BlockingSimulator(PassBlockingStrategy())
    
    # Run 50 simulations of each
    run_success_rates = []
    pass_success_rates = []
    
    for _ in range(50):
        run_results = run_sim.simulate_matchups(blockers, defenders, run_context)
        pass_results = pass_sim.simulate_matchups(blockers, defenders, pass_context)
        
        run_success_rates.append(sum(1 for r in run_results if r.success) / len(run_results))
        pass_success_rates.append(sum(1 for r in pass_results if r.success) / len(pass_results))
    
    avg_run_success = sum(run_success_rates) / len(run_success_rates)
    avg_pass_success = sum(pass_success_rates) / len(pass_success_rates)
    
    print(f"  Average run blocking success: {avg_run_success:.3f}")
    print(f"  Average pass blocking success: {avg_pass_success:.3f}")
    
    # Run blocking should generally be more successful
    assert avg_run_success > avg_pass_success, "Run blocking should be more successful than pass protection"
    
    print("  ✓ Strategies produce different realistic results")

def test_integration_with_detailed_run_sim():
    """Test that the new blocking system integrates with DetailedRunSimulator"""
    print("\nTesting integration with DetailedRunSimulator...")
    
    simulator = DetailedRunSimulator()
    
    # Sample team data
    offense = {
        "offense": {
            "rb_rating": 85,
            "ol_rating": 80,
            "te_rating": 75
        }
    }
    
    defense = {
        "defense": {
            "dl_rating": 82,
            "lb_rating": 78,
            "db_rating": 75
        }
    }
    
    # Run several simulations
    results = []
    for _ in range(10):
        result = simulator.simulate_run(offense, defense)
        results.append(result)
    
    print(f"  Ran {len(results)} detailed simulations")
    
    # Check that blocking results are present and detailed
    first_result = results[0]
    assert len(first_result.blocking_results) > 0, "Should have blocking results"
    
    for block_result in first_result.blocking_results:
        assert hasattr(block_result, 'success'), "Should have success flag"
        assert hasattr(block_result, 'impact_factor'), "Should have impact factor"
        assert block_result.blocker_position, "Should have blocker position"
        assert block_result.defender_position, "Should have defender position"
    
    # Check yards gained distribution
    yards_list = [r.yards_gained for r in results]
    avg_yards = sum(yards_list) / len(yards_list)
    
    print(f"  Average yards: {avg_yards:.1f}")
    print(f"  Yards range: {min(yards_list)} to {max(yards_list)}")
    print(f"  Sample breakdown: {first_result.play_breakdown}")
    
    assert -5 <= min(yards_list) <= max(yards_list) <= 80, "Yards should be in realistic range"
    
    print("  ✓ Integration working correctly")

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\nTesting edge cases...")
    
    strategy = RunBlockingStrategy()
    simulator = BlockingSimulator(strategy)
    
    # Test with mismatched blocker/defender counts
    few_blockers = {"LT": 80}
    many_defenders = {"DE1": 85, "DE2": 80, "LB1": 75, "LB2": 70}
    
    context = BlockingContext.for_run_play("dive", "center", "singleback", 1, 10, 50)
    results = simulator.simulate_matchups(few_blockers, many_defenders, context)
    
    print(f"  Mismatched counts: {len(few_blockers)} blockers vs {len(many_defenders)} defenders")
    print(f"  Results: {len(results)} matchups created")
    
    # Test extreme ratings
    elite_blockers = {"LT": 99}
    terrible_defenders = {"DE": 1}
    
    extreme_results = simulator.simulate_matchups(elite_blockers, terrible_defenders, context)
    elite_success = extreme_results[0].success if extreme_results else False
    
    print(f"  Elite vs Terrible result: {'Success' if elite_success else 'Failure'}")
    
    # Test empty inputs
    empty_results = simulator.simulate_matchups({}, {}, context)
    print(f"  Empty inputs result: {len(empty_results)} matchups")
    
    assert len(empty_results) == 0, "Empty inputs should produce no results"
    
    print("  ✓ Edge cases handled correctly")

def main():
    print("=" * 70)
    print("            BLOCKING STRATEGIES TEST SUITE")
    print("=" * 70)
    
    test_blocking_context_creation()
    test_run_blocking_strategy()
    test_pass_blocking_strategy()
    test_blocking_simulator()
    test_strategy_differences()
    test_integration_with_detailed_run_sim()
    test_edge_cases()
    
    print("\n" + "=" * 70)
    print("All blocking strategy tests completed successfully! 🏈")

if __name__ == "__main__":
    main()