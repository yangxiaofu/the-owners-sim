#!/usr/bin/env python3
"""
Simple Kicking Algorithm Benchmark Test

A streamlined test to validate kick algorithm performance against 2024 NFL statistics.
Run directly from root directory: python test_kick_benchmarks.py

2024 NFL Benchmarks:
- Extra Point: 95.8% success rate
- Short FG (30-39 yards): 92.9% success rate  
- Medium FG (40-49 yards): 85.1% success rate
- Long FG (50+ yards): 73.5% success rate
- Overall FG: 84.0% success rate
"""

import sys
import os
import random
from typing import Dict, Tuple

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.kick_play import KickPlay
from game_engine.field.field_state import FieldState
from unittest.mock import Mock


def quick_test():
    """Run quick kicking benchmark test"""
    print("🏈 Quick Kicking Algorithm Test")
    print("=" * 40)
    
    kick_play = KickPlay()
    random.seed(42)  # Reproducible results
    
    # NFL benchmarks
    benchmarks = {
        'Extra Point (20y)': {'range': (18, 22), 'nfl_rate': 0.958},
        'Short FG (30-39y)': {'range': (30, 39), 'nfl_rate': 0.929},
        'Medium FG (40-49y)': {'range': (40, 49), 'nfl_rate': 0.851},
        'Long FG (50+ yards)': {'range': (50, 65), 'nfl_rate': 0.735}
    }
    
    results = {}
    sample_size = 500
    
    for test_name, config in benchmarks.items():
        print(f"\nTesting {test_name}...")
        
        successes = 0
        for _ in range(sample_size):
            distance = random.randint(config['range'][0], config['range'][1])
            
            # Create field state
            field_state = FieldState()
            field_position = max(1, 100 - distance + 17)
            field_state.field_position = field_position
            field_state.down = 4
            field_state.yards_to_go = 5
            
            # Mock personnel
            personnel = Mock()
            personnel.kicker_rating = 75
            
            # Simulate kick
            outcome, _ = kick_play._calculate_kick_outcome_from_matrix(
                {'ol': 70}, {'dl': 60}, personnel, field_state
            )
            
            if outcome in ['field_goal', 'extra_point']:
                successes += 1
        
        success_rate = successes / sample_size
        nfl_rate = config['nfl_rate']
        variance = abs(success_rate - nfl_rate) / nfl_rate * 100
        status = "✅ PASS" if variance <= 10 else "❌ FAIL"
        
        results[test_name] = {'rate': success_rate, 'variance': variance, 'pass': variance <= 10}
        print(f"  Result: {success_rate:.1%} vs NFL {nfl_rate:.1%} (±{variance:.1f}%) {status}")
    
    # Summary
    passed = sum(1 for r in results.values() if r['pass'])
    total = len(results)
    
    print(f"\n📊 Summary: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("🎉 EXCELLENT: All tests pass!")
    elif passed >= total * 0.8:
        print("✅ GOOD: Most tests pass") 
    else:
        print("⚠️  NEEDS WORK: Consider tuning")
    
    return results


if __name__ == "__main__":
    quick_test()