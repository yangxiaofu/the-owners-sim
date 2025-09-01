#!/usr/bin/env python3
"""
Clock Management Optimization Validation Test

This script validates that the clock management optimization achieves the target
play counts per game (150-155 plays) as outlined in the optimization plan.
"""

import sys
import statistics
from typing import List, Dict, Any
from src.game_engine.core.game_orchestrator import GameOrchestrator

def run_validation_test(num_games: int = 20) -> Dict[str, Any]:
    """
    Run validation test to measure play counts per game with optimized clock management.
    
    Args:
        num_games: Number of games to simulate for statistical validation
        
    Returns:
        Dict containing validation results and statistics
    """
    print(f"Running clock optimization validation with {num_games} games...")
    
    play_counts = []
    time_per_play = []
    archetype_results = {}
    
    orchestrator = GameOrchestrator()
    
    for game_num in range(num_games):
        try:
            print(f"Simulating game {game_num + 1}/{num_games}...", end=' ')
            
            # Run a complete game simulation
            result = orchestrator.simulate_game()
            
            # Extract key metrics
            total_plays = len(result.get('plays', []))
            total_time = 3600  # Full 60-minute game
            avg_time_per_play = total_time / total_plays if total_plays > 0 else 0
            
            play_counts.append(total_plays)
            time_per_play.append(avg_time_per_play)
            
            # Track by offensive archetype if available
            for play in result.get('plays', []):
                archetype = play.get('offensive_archetype', 'unknown')
                if archetype not in archetype_results:
                    archetype_results[archetype] = []
                # We can't get per-play timing easily, so we'll focus on overall counts
                
            print(f"✓ {total_plays} plays ({avg_time_per_play:.1f}s per play)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
    
    if not play_counts:
        return {"error": "No games completed successfully"}
    
    # Calculate validation statistics
    avg_plays = statistics.mean(play_counts)
    median_plays = statistics.median(play_counts)
    stdev_plays = statistics.stdev(play_counts) if len(play_counts) > 1 else 0
    min_plays = min(play_counts)
    max_plays = max(play_counts)
    
    avg_time_per_play = statistics.mean(time_per_play)
    
    # Determine if we hit our target
    target_min = 150
    target_max = 155
    target_hit = target_min <= avg_plays <= target_max
    
    return {
        "games_simulated": len(play_counts),
        "play_count_stats": {
            "average": avg_plays,
            "median": median_plays,
            "std_dev": stdev_plays,
            "min": min_plays,
            "max": max_plays,
            "target_range": f"{target_min}-{target_max}",
            "target_achieved": target_hit
        },
        "timing_stats": {
            "avg_seconds_per_play": avg_time_per_play
        },
        "raw_data": play_counts
    }

def print_validation_report(results: Dict[str, Any]):
    """Print formatted validation report"""
    if "error" in results:
        print(f"\n❌ Validation failed: {results['error']}")
        return
    
    stats = results["play_count_stats"]
    timing = results["timing_stats"]
    
    print("\n" + "="*60)
    print("CLOCK OPTIMIZATION VALIDATION REPORT")
    print("="*60)
    
    print(f"Games Simulated: {results['games_simulated']}")
    print()
    
    print("PLAY COUNT ANALYSIS:")
    print(f"  Average plays per game: {stats['average']:.1f}")
    print(f"  Median plays per game:  {stats['median']:.1f}")
    print(f"  Standard deviation:     {stats['std_dev']:.1f}")
    print(f"  Range:                  {stats['min']} - {stats['max']} plays")
    print(f"  Target range:           {stats['target_range']} plays")
    print()
    
    print("TIMING ANALYSIS:")
    print(f"  Average time per play:  {timing['avg_seconds_per_play']:.1f} seconds")
    print()
    
    print("OPTIMIZATION RESULTS:")
    if stats['target_achieved']:
        print(f"  ✅ TARGET ACHIEVED! Average of {stats['average']:.1f} plays within target range")
    else:
        print(f"  ❌ Target missed. Average of {stats['average']:.1f} plays outside target range")
        if stats['average'] < 150:
            print(f"     Need to reduce clock time per play (currently {timing['avg_seconds_per_play']:.1f}s)")
        else:
            print(f"     Need to increase clock time per play (currently {timing['avg_seconds_per_play']:.1f}s)")
    
    print()
    print("INDIVIDUAL GAME RESULTS:")
    for i, count in enumerate(results['raw_data'][:10]):  # Show first 10 games
        status = "✅" if 150 <= count <= 155 else "❌"
        print(f"  Game {i+1:2d}: {count:3d} plays {status}")
    
    if len(results['raw_data']) > 10:
        print(f"  ... and {len(results['raw_data']) - 10} more games")
        
    print("="*60)

def main():
    """Main validation execution"""
    try:
        # Run validation with a reasonable number of games for statistical significance
        results = run_validation_test(num_games=15)
        print_validation_report(results)
        
        # Return appropriate exit code
        if results.get("play_count_stats", {}).get("target_achieved", False):
            print("\n🎉 Clock optimization validation PASSED!")
            sys.exit(0)
        else:
            print("\n⚠️  Clock optimization validation needs adjustment.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()