#!/usr/bin/env python3
"""
Demo of the new RunPlaySimulator with individual player statistics
Shows the two-phase simulation approach with comprehensive stat tracking
"""

import sys
sys.path.append('../src')

from play_engine.simulation.run_plays import RunPlaySimulator
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation

def main():
    print("=== Run Play Simulation with Individual Player Stats ===\n")
    
    # Generate team rosters using real MVP team IDs
    browns_roster = TeamRosterGenerator.generate_sample_roster(7)   # Cleveland Browns (real data)
    niners_roster = TeamRosterGenerator.generate_sample_roster(31)  # San Francisco 49ers (real data)
    
    # Create personnel managers
    browns_personnel = PersonnelPackageManager(browns_roster)
    niners_personnel = PersonnelPackageManager(niners_roster)

    #TODO: create playcalling algorithm by archetypes.

    # Get I-Formation offense vs 4-3 defense
    offensive_players = browns_personnel.get_offensive_personnel(OffensiveFormation.I_FORMATION)
    defensive_players = niners_personnel.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
    
    print("Formation Matchup: I-Formation vs 4-3 Base Defense")
    print("Browns offense vs 49ers defense - Real NFL players!")
    print(f"Offensive Personnel: {browns_personnel.get_personnel_summary(offensive_players)}")
    print(f"Defensive Personnel: {niners_personnel.get_personnel_summary(defensive_players)}")
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


    """
    The play summary will need to be adjusted at this stage.  For example, if it's at the 5-yard line. and the play summary calls for a 10 yard play, then it's really a 5 yard play. 
    I'm trying to understand the best flow for this. Run the play and get the output. Do an adjustment depending on where it's  on the field. But first, I think i need to have a field
    tracker that tracks the placement of hte ball. this might be the best.  The input of the playsummary will move the ball along the field.  
    
    
    """

    
    # Show play results
    print("=== Play Results ===")
    print(f"Play Type: {play_summary.play_type}")
    print(f"Yards Gained: {play_summary.yards_gained}")
    print(f"Time Elapsed: {play_summary.time_elapsed} seconds")
    print()
    
    # Show individual player statistics with enhanced real player info
    print("=== Individual Player Statistics (Enhanced with Real Player Data) ===")
    players_with_stats = play_summary.get_players_with_stats()
    
    for player_stats in players_with_stats:
        # Use enhanced player summary for real players
        player_info = player_stats.get_player_summary()
        print(f"{player_info}:")
        
        # Show if this is a real player
        if player_stats.is_real_player():
            print(f"  Real NFL Player - Key Attributes:")
            key_attrs = ['overall', 'speed', 'strength', 'discipline']
            for attr in key_attrs:
                value = player_stats.get_player_attribute(attr)
                print(f"    {attr}: {value}")
        
        # Show play statistics
        stats = player_stats.get_total_stats()
        print(f"  Play Statistics:")
        for stat_name, value in stats.items():
            print(f"    {stat_name}: {value}")
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
    
    # Show real player analysis
    print("=== Real Player Analysis ===")
    real_players = play_summary.get_real_players_summary()
    print(f"Real NFL players involved in this play: {len(real_players)}")
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
    
    # Show formation advantage example
    print("=== Formation Advantage Example ===")
    print("Running same I-Formation vs different defenses:")
    
    # I-Formation vs Nickel (should be better for offense)
    nickel_defense = niners_personnel.get_defensive_personnel(DefensiveFormation.NICKEL)
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