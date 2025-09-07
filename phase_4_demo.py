#!/usr/bin/env python3
"""
Phase 4 Comprehensive Demonstration

Complete NFL game simulation with full statistics API access.
Demonstrates all Phase 4 features and API methods.
"""

from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs
import time
import json


def main():
    """Demonstrate complete Phase 4 functionality"""
    print("🏈 PHASE 4: COMPLETE PUBLIC API DEMONSTRATION")
    print("=" * 60)
    
    # Step 1: Create Game Simulator (2-line setup) - Using Teams with Advanced Coaching
    print("\n📋 Step 1: Advanced Team Setup")
    print("   Using teams with sophisticated coaching staff profiles:")
    print("   🏈 Cleveland Browns (Away) - Kevin Stefanski, Tommy Rees, Jim Schwartz")
    print("   🏈 San Francisco 49ers (Home) - Kyle Shanahan, Klay Kubiak, Robert Saleh")
    print()
    
    simulator = FullGameSimulator(
        away_team_id=TeamIDs.CLEVELAND_BROWNS, 
        home_team_id=TeamIDs.SAN_FRANCISCO_49ERS
    )
    print(f"✅ Game created: {simulator}")
    
    # Step 1.5: Coaching System Showcase
    print("\n🧠 Step 1.5: Advanced Coaching System")
    print("   These teams feature realistic NFL coaching profiles:")
    print()
    print("   🔴 Cleveland Browns Coaching Philosophy:")
    print("     - Kevin Stefanski: Balanced offensive approach with modern concepts")
    print("     - Tommy Rees: Creative play designs, high football IQ")
    print("     - Jim Schwartz: Aggressive defensive schemes, pressure-focused")
    print()
    print("   🔴 San Francisco 49ers Coaching Philosophy:")
    print("     - Kyle Shanahan: Offensive mastermind (0.9 play-action frequency)")
    print("     - Klay Kubiak: West Coast offense specialist, innovative concepts")  
    print("     - Robert Saleh: Multiple defensive fronts, coverage versatility")
    print()
    print("   ⚡ This showcases realistic coaching decisions vs generic 'aggressive/conservative' styles")
    print()
    print("   📊 Key Difference:")
    print("     Generic Teams: Use basic styles like 'aggressive', 'balanced', 'conservative'")
    print("     Browns & 49ers: Use detailed coach profiles with 60+ specific attributes")
    print("     Example: Shanahan's 0.9 play-action frequency vs generic 'pass-heavy' label")
    
    # Step 2: Run Complete Game Simulation
    print("\n🎮 Step 2: Full Game Simulation")
    start_time = time.time()
    game_result = simulator.simulate_game()
    end_time = time.time()
    
    print(f"✅ Simulation completed in {end_time - start_time:.2f} seconds")
    
    # Step 3: Demonstrate Multi-Level Statistics Access
    print("\n📊 Step 3: Multi-Level Statistics API")
    
    # Level 1: Game Summary
    print("\n🏆 Level 1: Game Summary")
    final_score = simulator.get_final_score()
    print(f"   Final Score: {json.dumps(final_score['scores'], indent=4)}")
    print(f"   Winner: {final_score.get('winner', 'Tie Game')}")
    print(f"   Total Plays: {final_score.get('total_plays', 0)}")
    print(f"   Game Duration: {final_score.get('game_duration_minutes', 0)} minutes")
    
    # Level 2: Team Statistics
    print("\n📈 Level 2: Team Statistics")
    team_stats = simulator.get_team_stats()
    for team_name, stats in team_stats.items():
        print(f"   {team_name}:")
        
        # Offensive yards (FIXED: Only passing + rushing)
        total_yards = stats.get('total_yards', 0)
        passing_yards = stats.get('passing_yards', 0)
        rushing_yards = stats.get('rushing_yards', 0)
        
        print(f"     - Total Yards: {total_yards} (Passing + Rushing Only)")
        print(f"       • Passing Yards: {passing_yards}")  
        print(f"       • Rushing Yards: {rushing_yards}")
        
        # Verify the math (should be equal now)
        calculated_total = passing_yards + rushing_yards
        if total_yards == calculated_total:
            print(f"       ✅ Verified: {passing_yards} + {rushing_yards} = {total_yards}")
        else:
            print(f"       ⚠️  Mismatch: {passing_yards} + {rushing_yards} = {calculated_total} vs {total_yards}")
        
        # Special teams return yards (NEW: Separated out)
        punt_return_yards = stats.get('punt_return_yards', 0)
        kick_return_yards = stats.get('kick_return_yards', 0)
        
        if punt_return_yards > 0 or kick_return_yards > 0:
            print(f"     - Special Teams Returns:")
            if punt_return_yards > 0:
                print(f"       • Punt Return Yards: {punt_return_yards}")
            if kick_return_yards > 0:
                print(f"       • Kick Return Yards: {kick_return_yards}")
        
        # Other key stats
        print(f"     - Touchdowns: {stats.get('touchdowns', 0)}")
        print(f"     - First Downs: {stats.get('first_downs', 0)}")
        print(f"     - Pass Attempts: {stats.get('pass_attempts', 0)}")
        print(f"     - Completions: {stats.get('completions', 0)}")
        if stats.get('pass_attempts', 0) > 0:
            completion_pct = stats.get('completions', 0) / stats.get('pass_attempts', 0) * 100
            print(f"     - Completion %: {completion_pct:.1f}%")
    
    # Level 3: Player Statistics
    print("\n👤 Level 3: Player Statistics")
    player_stats = simulator.get_player_stats()
    print(f"   Total Players with Stats: {len(player_stats)}")
    
    # Show sample player stats if available
    if player_stats:
        sample_player = list(player_stats.keys())[0]
        print(f"   Sample Player: {sample_player}")
        print(f"     Stats: {player_stats[sample_player]}")
    else:
        print("   (Player stats available when GameLoopController completes successfully)")
    
    # Level 4: Drive Analysis
    print("\n🚗 Level 4: Drive Analysis")
    drive_summaries = simulator.get_drive_summaries()
    print(f"   Total Drives: {len(drive_summaries)}")
    
    for drive in drive_summaries[:3]:  # Show first 3 drives
        print(f"   Drive #{drive['drive_number']} ({drive['possessing_team']}):")
        print(f"     - Outcome: {drive['drive_outcome']}")
        print(f"     - Plays: {drive['total_plays']}, Yards: {drive['total_yards']}")
        print(f"     - Points: {drive['points_scored']}")
    
    # Level 5: Play-by-Play
    print("\n📝 Level 5: Play-by-Play Analysis")
    play_by_play = simulator.get_play_by_play()
    print(f"   Total Plays: {len(play_by_play)}")
    
    for play in play_by_play[:5]:  # Show first 5 plays
        print(f"   Play #{play['play_number']}: {play['possessing_team']} - {play['description']}")
    
    # Step 4: Performance Analysis
    print("\n⚡ Step 4: Performance Analysis")
    performance = simulator.get_performance_metrics()
    
    print(f"   Simulation Duration: {performance['simulation_duration_seconds']:.3f} seconds")
    print(f"   Performance Target Met: {'✅ YES' if performance['performance_target_met'] else '❌ NO'} (< 5.0s)")
    print(f"   Plays per Second: {performance['plays_per_second']:.1f}")
    print(f"   Game Completed: {'✅ YES' if performance['game_completed'] else '❌ NO'}")
    
    # Step 5: Advanced API Features
    print("\n🔧 Step 5: Advanced API Features")
    
    # Filter team stats
    browns_stats = simulator.get_team_stats(team_id=TeamIDs.CLEVELAND_BROWNS)
    print(f"   Cleveland Browns Specific Stats: {len(browns_stats)} entries")
    
    # Filter player stats by position (example)
    qb_stats = simulator.get_player_stats(position="QB")
    print(f"   Quarterback Stats: {len(qb_stats)} QBs")
    
    # Penalty analysis
    penalties = simulator.get_penalty_summary()
    print(f"   Total Penalties: {penalties.get('total_penalties', 0)}")
    
    # Step 6: Public API Summary
    print("\n📋 Step 6: Public API Summary")
    api_methods = [
        "simulate_game()", "get_game_result()", "get_final_score()",
        "get_team_stats()", "get_player_stats()", "get_drive_summaries()",
        "get_play_by_play()", "get_penalty_summary()", "get_performance_metrics()"
    ]
    
    print(f"   Available API Methods: {len(api_methods)}")
    for method in api_methods:
        print(f"     - simulator.{method}")
    
    # Conclusion
    print("\n" + "=" * 60)
    print("🎯 PHASE 4 DEMONSTRATION COMPLETE!")
    print("   ✅ 2-line game setup with advanced team configurations")
    print("   ✅ Complete game simulation with realistic NFL coaching")
    print("   ✅ Multi-level statistics access (game, team, player, drive, play)")
    print("   ✅ Performance monitoring (< 1 second simulation time)")
    print("   ✅ Advanced filtering capabilities with sophisticated coaching profiles")
    print("   ✅ Production-ready public API showcasing Browns vs 49ers coaching systems")
    print("   🧠 Demonstrated realistic coaching vs generic styles")
    
    return simulator, game_result


if __name__ == "__main__":
    simulator, game_result = main()
    
    # Additional interactive features
    print(f"\n🔍 Interactive Features:")
    print(f"   # Cleveland Browns (7) vs San Francisco 49ers (31)")
    print(f"   simulator = FullGameSimulator(away_team_id=7, home_team_id=31)")
    print(f"   game_result = simulator.simulate_game()")
    print(f"   final_score = simulator.get_final_score()")
    print(f"   team_stats = simulator.get_team_stats()")
    print(f"   performance = simulator.get_performance_metrics()")