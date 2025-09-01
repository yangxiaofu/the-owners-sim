#!/usr/bin/env python3
"""Quick single-play test to debug penalty detection issues."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tests.penalty_benchmarking_suite import MockGameSimulator

def test_single_play():
    """Test a single play to identify the exact error."""
    print("🔍 SINGLE PLAY PENALTY DEBUG TEST")
    print("-" * 40)
    
    simulator = MockGameSimulator()
    
    print("Offense team structure:")
    print(f"  Type: {type(simulator.offense_team)}")
    print(f"  Keys: {list(simulator.offense_team.keys()) if isinstance(simulator.offense_team, dict) else 'Not a dict'}")
    
    print("\nDefense team structure:")
    print(f"  Type: {type(simulator.defense_team)}")
    print(f"  Keys: {list(simulator.defense_team.keys()) if isinstance(simulator.defense_team, dict) else 'Not a dict'}")
    
    # Try to run one game
    try:
        stats = simulator.simulate_game()
        print("✅ Single game simulation successful!")
        print(f"Penalties detected: {stats.total_penalties}")
    except Exception as e:
        print(f"❌ Single game simulation failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_single_play()