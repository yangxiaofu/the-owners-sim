#!/usr/bin/env python3
"""
Demo of the new RunPlaySimulator with individual player statistics
Shows the two-phase simulation approach with comprehensive stat tracking
"""

import sys
sys.path.append('src')

from plays.run_play import RunPlaySimulator
from personnel_package_manager import TeamRosterGenerator, PersonnelPackageManager
from formation import OffensiveFormation, DefensiveFormation

def main():
    print("=== Run Play Simulation with Individual Player Stats ===\n")
    
    # Generate team rosters
    lions_roster = TeamRosterGenerator.generate_sample_roster("Detroit Lions")
    commanders_roster = TeamRosterGenerator.generate_sample_roster("Washington Commanders")
    
    # Create personnel managers
    lions_personnel = PersonnelPackageManager(lions_roster)
    commanders_personnel = PersonnelPackageManager(commanders_roster)
    
    # Get I-Formation offense vs 4-3 defense
    offensive_players = lions_personnel.get_offensive_personnel(OffensiveFormation.I_FORMATION)
    defensive_players = commanders_personnel.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
    
    print("Formation Matchup: I-Formation vs 4-3 Base Defense")
    print(f"Offensive Personnel: {lions_personnel.get_personnel_summary(offensive_players)}")
    print(f"Defensive Personnel: {commanders_personnel.get_personnel_summary(defensive_players)}")
    print()
    
    # Create and run simulator
    simulator = RunPlaySimulator(
        offensive_players=offensive_players,
        defensive_players=defensive_players,
        offensive_formation=OffensiveFormation.I_FORMATION,
        defensive_formation=DefensiveFormation.FOUR_THREE
    )
    
    # Simulate the play
    play_summary = simulator.simulate_run_play()
    
    # Show play results
    print("=== Play Results ===")
    print(f"Play Type: {play_summary.play_type}")
    print(f"Yards Gained: {play_summary.yards_gained}")
    print(f"Time Elapsed: {play_summary.time_elapsed} seconds")
    print()
    
    # Show individual player statistics
    print("=== Individual Player Statistics ===")
    players_with_stats = play_summary.get_players_with_stats()
    
    for player_stats in players_with_stats:
        print(f"{player_stats.player_name} (#{player_stats.player_number}, {player_stats.position}):")
        stats = player_stats.get_total_stats()
        for stat_name, value in stats.items():
            print(f"  - {stat_name}: {value}")
        print()
    
    # Show play leaders
    print("=== Play Leaders ===")
    rushing_leader = play_summary.get_rushing_leader()
    if rushing_leader:
        print(f"Rushing: {rushing_leader.player_name} - {rushing_leader.carries} carry, {rushing_leader.rushing_yards} yards")
    
    leading_tackler = play_summary.get_leading_tackler()
    if leading_tackler:
        total_tackles = leading_tackler.tackles + leading_tackler.assisted_tackles
        print(f"Leading Tackler: {leading_tackler.player_name} - {total_tackles} total tackles")
    
    print()
    
    # Show formation advantage example
    print("=== Formation Advantage Example ===")
    print("Running same I-Formation vs different defenses:")
    
    # I-Formation vs Nickel (should be better for offense)
    nickel_defense = commanders_personnel.get_defensive_personnel(DefensiveFormation.NICKEL)
    nickel_sim = RunPlaySimulator(offensive_players, nickel_defense,
                                  OffensiveFormation.I_FORMATION, DefensiveFormation.NICKEL)
    
    # Run multiple simulations to show average difference
    base_defense_results = []
    nickel_defense_results = []
    
    for _ in range(5):
        base_result = simulator.simulate_run_play()
        nickel_result = nickel_sim.simulate_run_play()
        base_defense_results.append(base_result.yards_gained)
        nickel_defense_results.append(nickel_result.yards_gained)
    
    base_avg = sum(base_defense_results) / len(base_defense_results)
    nickel_avg = sum(nickel_defense_results) / len(nickel_defense_results)
    
    print(f"I-Formation vs 4-3 Base: {base_avg:.1f} yards average")
    print(f"I-Formation vs Nickel: {nickel_avg:.1f} yards average")
    print(f"Formation Advantage: +{nickel_avg - base_avg:.1f} yards vs Nickel (as expected)")

if __name__ == "__main__":
    main()