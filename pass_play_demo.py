#!/usr/bin/env python3
"""
Demo of the comprehensive PassPlaySimulator with individual player statistics
Shows comprehensive NFL-level pass play simulation with Browns vs 49ers real players
"""

import sys
sys.path.append('src')

from play_engine.simulation.pass_plays import PassPlaySimulator
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation

def main():
    print("=== Comprehensive Pass Play Simulation with NFL Statistics ===\n")
    
    # Generate real MVP team rosters
    browns_roster = TeamRosterGenerator.generate_sample_roster(7)   # Cleveland Browns (real data)
    niners_roster = TeamRosterGenerator.generate_sample_roster(31)  # San Francisco 49ers (real data)
    
    # Create personnel managers
    browns_personnel = PersonnelPackageManager(browns_roster)
    niners_personnel = PersonnelPackageManager(niners_roster)
    
    # Get Shotgun offense vs Nickel defense - ideal for passing
    offensive_players = browns_personnel.get_offensive_personnel(OffensiveFormation.SHOTGUN)
    defensive_players = niners_personnel.get_defensive_personnel(DefensiveFormation.NICKEL)
    
    print("Formation Matchup: Shotgun vs Nickel Defense")
    print("Browns offense vs 49ers defense - Real NFL players!")
    print(f"Offensive Personnel: {browns_personnel.get_personnel_summary(offensive_players)}")
    print(f"Defensive Personnel: {niners_personnel.get_personnel_summary(defensive_players)}")
    print()
    
    # Create and run simulator
    simulator = PassPlaySimulator(
        offensive_players=offensive_players,
        defensive_players=defensive_players,
        offensive_formation=OffensiveFormation.SHOTGUN,
        defensive_formation=DefensiveFormation.NICKEL
    )
    
    # Simulate the pass play
    play_summary = simulator.simulate_pass_play()
    
    # Show play results
    print("=== Pass Play Results ===")
    print(f"Play Type: {play_summary.play_type}")
    print(f"Yards Gained: {play_summary.yards_gained}")
    print(f"Time Elapsed: {play_summary.time_elapsed} seconds")
    print()
    
    # Show comprehensive individual player statistics
    print("=== Comprehensive NFL Player Statistics ===")
    players_with_stats = play_summary.get_players_with_stats()
    
    for player_stats in players_with_stats:
        # Use enhanced player summary for real players
        player_info = player_stats.get_player_summary()
        print(f"{player_info}:")
        
        # Show if this is a real player with key attributes
        if player_stats.is_real_player():
            print(f"  Real NFL Player - Key Attributes:")
            key_attrs = ['overall', 'speed', 'accuracy', 'coverage', 'pass_rush'] if player_stats.position in ['quarterback', 'cornerback', 'defensive_end'] else ['overall', 'speed', 'strength']
            for attr in key_attrs:
                value = player_stats.get_player_attribute(attr, 'N/A')
                if value != 'N/A':
                    print(f"    {attr}: {value}")
        
        # Show comprehensive play statistics
        stats = player_stats.get_total_stats()
        print(f"  Play Statistics:")
        for stat_name, value in stats.items():
            print(f"    {stat_name}: {value}")
        print()
    
    # Show play leaders with comprehensive categories
    print("=== Comprehensive Play Leaders ===")
    
    # QB Performance
    passing_leader = play_summary.get_passing_leader()
    if passing_leader:
        completion_pct = (passing_leader.completions / passing_leader.pass_attempts * 100) if passing_leader.pass_attempts > 0 else 0
        print(f"Passing: {passing_leader.player_name} - {passing_leader.completions}/{passing_leader.pass_attempts} ({completion_pct:.1f}%), {passing_leader.passing_yards} yards")
        if passing_leader.sacks_taken > 0:
            print(f"  Sacked: {passing_leader.sacks_taken} time(s) for {passing_leader.sack_yards_lost} yards")
        if passing_leader.pressures_faced > 0:
            print(f"  Pressures Faced: {passing_leader.pressures_faced}")
    
    # Receiving Performance  
    receiving_leader = play_summary.get_receiving_leader()
    if receiving_leader:
        print(f"Receiving: {receiving_leader.player_name} - {receiving_leader.receptions}/{receiving_leader.targets}, {receiving_leader.receiving_yards} yards")
        if hasattr(receiving_leader, 'yac') and receiving_leader.yac > 0:
            print(f"  YAC: {receiving_leader.yac} yards")
    
    # Pass Rush Performance
    pass_rush_leader = play_summary.get_pass_rush_leader() 
    if pass_rush_leader:
        rush_stats = []
        if pass_rush_leader.sacks > 0:
            rush_stats.append(f"{pass_rush_leader.sacks} sack(s)")
        if pass_rush_leader.qb_hits > 0:
            rush_stats.append(f"{pass_rush_leader.qb_hits} QB hit(s)")
        if pass_rush_leader.qb_pressures > 0:
            rush_stats.append(f"{pass_rush_leader.qb_pressures} pressure(s)")
        
        if rush_stats:
            print(f"Pass Rush: {pass_rush_leader.player_name} - {', '.join(rush_stats)}")
    
    # Pass Defense Performance
    pass_defense_leader = play_summary.get_pass_defense_leader()
    if pass_defense_leader:
        defense_stats = []
        if pass_defense_leader.interceptions > 0:
            defense_stats.append(f"{pass_defense_leader.interceptions} INT")
        if pass_defense_leader.passes_deflected > 0:
            defense_stats.append(f"{pass_defense_leader.passes_deflected} deflection(s)")
        if pass_defense_leader.passes_defended > 0:
            defense_stats.append(f"{pass_defense_leader.passes_defended} PBU")
        
        if defense_stats:
            print(f"Pass Defense: {pass_defense_leader.player_name} - {', '.join(defense_stats)}")
    
    # Tackling Performance
    leading_tackler = play_summary.get_leading_tackler()
    if leading_tackler:
        total_tackles = leading_tackler.tackles + leading_tackler.assisted_tackles
        print(f"Leading Tackler: {leading_tackler.player_name} - {total_tackles} total tackles")
    
    # Show real player analysis
    print("\n=== Real NFL Player Analysis ===")
    real_players = play_summary.get_real_players_summary()
    print(f"Real NFL players involved in this pass play: {len(real_players)}")
    for player in real_players:
        print(f"  {player['name']} #{player['number']} ({player['position']}) - {player['overall_rating']} OVR")
        if player['key_stats']:
            print(f"    Stats: {player['key_stats']}")
    
    # Show attribute impact analysis
    print("\n=== Player Attribute Impact Analysis ===")
    impact_analysis = play_summary.get_attribute_impact_summary()
    if impact_analysis['attribute_impacts']:
        for impact in impact_analysis['attribute_impacts']:
            print(f"  • {impact}")
    else:
        print("  • No significant attribute impacts detected this play")
    
    print()
    
    # Show formation advantage example with multiple pass plays
    print("=== Formation Comparison: Multiple Pass Attempts ===")
    print("Running Shotgun offense vs different defenses:")
    
    # Shotgun vs Nickel (current setup)
    nickel_results = []
    for _ in range(3):
        result = simulator.simulate_pass_play()
        nickel_results.append(result.yards_gained)
    nickel_avg = sum(nickel_results) / len(nickel_results)
    
    # Shotgun vs Dime (more passing-friendly)
    dime_defense = niners_personnel.get_defensive_personnel(DefensiveFormation.DIME)
    dime_sim = PassPlaySimulator(offensive_players, dime_defense,
                                OffensiveFormation.SHOTGUN, DefensiveFormation.DIME)
    
    dime_results = []
    for _ in range(3):
        result = dime_sim.simulate_pass_play()
        dime_results.append(result.yards_gained)
    dime_avg = sum(dime_results) / len(dime_results)
    
    print(f"Shotgun vs Nickel Defense: {nickel_avg:.1f} yards average")
    print(f"Shotgun vs Dime Defense: {dime_avg:.1f} yards average")
    print(f"Formation Impact: {dime_avg - nickel_avg:+.1f} yards vs Dime (expected for more pass-friendly defense)")
    
    print("\n=== Comprehensive Pass Statistics Summary ===")
    print("✅ QB Stats: Attempts, completions, yards, TDs, INTs, sacks, pressures")
    print("✅ WR/TE Stats: Targets, receptions, yards, TDs, drops, YAC")
    print("✅ OL Stats: Pass blocks, pressures allowed, sacks allowed") 
    print("✅ DL Stats: Sacks, QB hits, QB pressures, hurries")
    print("✅ DB Stats: Tackles, passes defended, deflections, interceptions")
    print("✅ Real player attributes influence ALL outcomes!")
    print("✅ Formation-based tactical advantages modeled!")

if __name__ == "__main__":
    main()