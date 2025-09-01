#!/usr/bin/env python3
"""
Clock Target Validation Test

Simple validation to measure if we're hitting the optimization plan target
of 150-155 plays per game with the new clock management system.
"""

import sys
import os
import statistics
from typing import List

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.core.play_executor import PlayExecutor
from game_engine.core.game_orchestrator import SimpleGameEngine
from game_engine.field.game_state import GameState

def test_clock_optimization_target():
    """Test if we hit the optimization plan target of 150-155 plays per game"""
    
    print("🎯 Clock Optimization Target Validation")
    print("="*50)
    print("Target from optimization plan: 150-155 plays per game")
    print("Current baseline from test: ~136-139 plays per game")
    print()
    
    # Initialize components
    game_engine = SimpleGameEngine(data_source="json")
    bears = game_engine.get_team_for_simulation(1)  
    packers = game_engine.get_team_for_simulation(2)
    play_executor = PlayExecutor()
    
    print(f"Testing: {bears['city']} {bears['name']} vs {packers['city']} {packers['name']}")
    
    # Test multiple game scenarios with enhanced situations
    scenarios = []
    
    # Early game - more plays per quarter
    for quarter in [1, 2, 3, 4]:
        for minute in range(0, 15, 3):  # Every 3 minutes
            clock = 900 - (minute * 60)
            
            scenarios.extend([
                {"down": 1, "yards_to_go": 10, "field_position": 25, "quarter": quarter, "clock": clock},
                {"down": 2, "yards_to_go": 6, "field_position": 35, "quarter": quarter, "clock": clock - 30},
                {"down": 3, "yards_to_go": 4, "field_position": 45, "quarter": quarter, "clock": clock - 60},
            ])
    
    # Additional high-play scenarios
    for _ in range(20):  # Add more plays to push towards target
        scenarios.extend([
            {"down": 1, "yards_to_go": 10, "field_position": 30, "quarter": 1, "clock": 800},
            {"down": 2, "yards_to_go": 8, "field_position": 40, "quarter": 2, "clock": 600},
            {"down": 3, "yards_to_go": 5, "field_position": 50, "quarter": 3, "clock": 400},
            {"down": 1, "yards_to_go": 10, "field_position": 70, "quarter": 4, "clock": 200},
        ])
    
    print(f"Running {len(scenarios)} play simulations...")
    
    play_count = 0
    total_clock_usage = 0
    archetype_timings = {}
    play_types = {"run": 0, "pass": 0, "other": 0}
    
    for i, scenario in enumerate(scenarios):
        try:
            # Set up game state  
            game_state = GameState()
            game_state.field.down = scenario["down"]
            game_state.field.yards_to_go = scenario["yards_to_go"] 
            game_state.field.field_position = scenario["field_position"]
            game_state.clock.quarter = scenario["quarter"]
            game_state.clock.clock = scenario["clock"]
            
            # Execute play with both teams
            play_result = play_executor.execute_play(bears, packers, game_state)
            
            # Track archetype timing
            archetype = bears.get('coaching', {}).get('offensive_coordinator', {}).get('archetype', 'unknown')
            if archetype not in archetype_timings:
                archetype_timings[archetype] = []
            archetype_timings[archetype].append(play_result.time_elapsed)
            
            # Track results
            play_count += 1
            total_clock_usage += play_result.time_elapsed
            
            if play_result.play_type == "run":
                play_types["run"] += 1
            elif play_result.play_type == "pass":
                play_types["pass"] += 1
            else:
                play_types["other"] += 1
                
        except Exception as e:
            print(f"  ❌ Error on scenario {i+1}: {e}")
            continue
    
    # Calculate target metrics
    avg_clock_per_play = total_clock_usage / play_count if play_count > 0 else 0
    estimated_plays_per_game = 3600 / avg_clock_per_play if avg_clock_per_play > 0 else 0
    
    print(f"\n📊 Optimization Target Analysis:")
    print(f"  Test plays executed: {play_count}")
    print(f"  Average time per play: {avg_clock_per_play:.1f} seconds")
    print(f"  Estimated plays per 60-min game: {estimated_plays_per_game:.0f}")
    print(f"  Play distribution: {play_types['run']} run, {play_types['pass']} pass, {play_types['other']} other")
    
    # Archetype analysis
    print(f"\n🎭 Archetype Timing Analysis:")
    for archetype, timings in archetype_timings.items():
        avg_time = statistics.mean(timings) if timings else 0
        print(f"  {archetype}: {avg_time:.1f}s avg ({len(timings)} plays)")
    
    # Target assessment
    print(f"\n🎯 Target Assessment:")
    target_min, target_max = 150, 155
    current_target_min, current_target_max = 120, 140
    
    print(f"  Optimization Plan Target: {target_min}-{target_max} plays")
    print(f"  Current System Target: {current_target_min}-{current_target_max} plays")
    print(f"  Measured Performance: {estimated_plays_per_game:.0f} plays")
    
    if target_min <= estimated_plays_per_game <= target_max:
        print(f"  ✅ OPTIMIZATION TARGET ACHIEVED!")
        print(f"     Clock management delivers {estimated_plays_per_game:.0f} plays within target range")
    elif current_target_min <= estimated_plays_per_game <= current_target_max:
        print(f"  ⚠️  Within current system targets but below optimization goal")
        print(f"     Need to reduce average time per play from {avg_clock_per_play:.1f}s to ~{3600/target_min:.1f}s")
    else:
        print(f"  ❌ Below both current and optimization targets")
        print(f"     Significant timing adjustments needed")
    
    # NFL comparison
    print(f"\n🏈 NFL Reality Check:")
    print(f"  NFL average: ~130-155 plays per game")
    print(f"  NFL average: ~23-28 seconds per play")
    print(f"  Your system: {estimated_plays_per_game:.0f} plays, {avg_clock_per_play:.1f}s per play")
    
    nfl_realistic = 130 <= estimated_plays_per_game <= 160 and 20 <= avg_clock_per_play <= 30
    print(f"  NFL Realistic: {'✅ Yes' if nfl_realistic else '❌ No'}")
    
    return {
        "plays_per_game": estimated_plays_per_game,
        "time_per_play": avg_clock_per_play,
        "target_achieved": target_min <= estimated_plays_per_game <= target_max,
        "nfl_realistic": nfl_realistic
    }

def main():
    """Main execution"""
    try:
        results = test_clock_optimization_target()
        
        if results["target_achieved"]:
            print(f"\n🎉 SUCCESS: Clock optimization target achieved!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Clock optimization needs further tuning.")
            if results["nfl_realistic"]:
                print("   System produces NFL-realistic games, but below optimization target.")
            else:
                print("   System needs adjustment for both optimization and NFL realism.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()