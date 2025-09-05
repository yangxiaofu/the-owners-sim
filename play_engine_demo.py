#!/usr/bin/env python3

# Add src to path so we can import play_engine
import sys
sys.path.append('src')

import play_engine
from play_engine_params import PlayEngineParams
from offensive_play_type import OffensivePlayType
from defensive_play_type import DefensivePlayType
from personnel_package_manager import PersonnelPackageManager, TeamRosterGenerator
from formation import OffensiveFormation, DefensiveFormation

# Import enhanced play call system
from play_calls.offensive_play_call import OffensivePlayCall
from play_calls.defensive_play_call import DefensivePlayCall
from play_calls.play_call_factory import PlayCallFactory

def main():
    # Generate complete team rosters
    lions_roster = TeamRosterGenerator.generate_sample_roster("Detroit Lions")
    commanders_roster = TeamRosterGenerator.generate_sample_roster("Washington Commanders")
    
    # Create personnel managers for each team
    lions_personnel = PersonnelPackageManager(lions_roster)
    commanders_personnel = PersonnelPackageManager(commanders_roster)

    # STEP 1: Choose formations (independent of play type)
    offensive_formation = OffensiveFormation.I_FORMATION  # Formation choice
    defensive_formation = DefensiveFormation.FOUR_THREE   # Formation choice
    
    # STEP 2: Get personnel based on formations
    offensive_players = lions_personnel.get_offensive_personnel(offensive_formation)
    defensive_players = commanders_personnel.get_defensive_personnel(defensive_formation)
    
    print("=== Formation-Based Personnel Selection ===")
    print(f"Lions Offensive Formation: {offensive_formation}")
    print(f"Lions Offensive Personnel: {lions_personnel.get_personnel_summary(offensive_players)}")
    print(f"Commanders Defensive Formation: {defensive_formation}")
    print(f"Commanders Defensive Personnel: {commanders_personnel.get_personnel_summary(defensive_players)}")
    print()
    
    # STEP 3: Now call plays within those formations using enhanced play calls
    print("=== Enhanced Play Calls Within Formations ===")
    print(f"From {offensive_formation}, Lions could call: run plays, play action, etc.")
    print(f"From {defensive_formation}, Commanders could call: Cover 2, blitz packages, etc.")
    print()

    # Create enhanced play calls with integrated formations and concepts
    power_run = OffensivePlayCall(OffensivePlayType.RUN, offensive_formation, concept="power")
    cover_2_defense = DefensivePlayCall(DefensivePlayType.COVER_2, defensive_formation, coverage="zone")
    
    print(f"Offensive Play Call: {power_run}")
    print(f"Defensive Play Call: {cover_2_defense}")

    # Create play engine parameters with enhanced play calls
    params = PlayEngineParams(
        offensive_players=offensive_players,  # 11 Lions offensive players
        defensive_players=defensive_players,  # 11 Commanders defensive players
        offensive_play_call=power_run,
        defensive_play_call=cover_2_defense
    )

    # Call the play engine
    result = play_engine.simulate(params)
    print(f"Enhanced play result: {result}")
    print()
    
    # Demonstrate how different plays can be called from the same formation
    print("=== Multiple Enhanced Play Calls From Same Formation ===")
    print("The only one that has been programmed so far.")
    # Same I-Formation personnel, different enhanced play calls
    run_call = OffensivePlayCall(OffensivePlayType.RUN, offensive_formation, concept="power")
    cover_2_call = DefensivePlayCall(DefensivePlayType.COVER_2, defensive_formation, coverage="zone")
    
    run_params = PlayEngineParams(
        offensive_players=offensive_players,  # Same I-Formation players
        defensive_players=defensive_players,  # Same 4-3 players
        offensive_play_call=run_call,
        defensive_play_call=cover_2_call
    )
    run_result = play_engine.simulate(run_params)
    print(f"I-Formation Power Run vs 4-3 Cover 2: {run_result}")
    
    # Same personnel, different enhanced play call
    play_action_call = OffensivePlayCall(OffensivePlayType.PLAY_ACTION_PASS, offensive_formation, concept="deep_ball")
    blitz_call = DefensivePlayCall(DefensivePlayType.BLITZ, defensive_formation, coverage="man", blitz_package="safety_blitz")
    
    play_action_params = PlayEngineParams(
        offensive_players=offensive_players,  # Same I-Formation players
        defensive_players=defensive_players,  # Same 4-3 players
        offensive_play_call=play_action_call,
        defensive_play_call=blitz_call
    )

    play_action_result = play_engine.simulate(play_action_params)
    print(f"I-Formation Play Action vs 4-3 Safety Blitz: {play_action_result}")
    print()
    
    # Show how different formations have different personnel with enhanced play calls
    print("=== Different Formations = Different Personnel with Enhanced Play Calls ===")
    
    # Shotgun formation for passing
    shotgun_formation = OffensiveFormation.SHOTGUN
    shotgun_players = lions_personnel.get_offensive_personnel(shotgun_formation)
    print(f"Shotgun Formation Personnel: {lions_personnel.get_personnel_summary(shotgun_players)}")
    
    # Nickel defense for passing situations
    nickel_formation = DefensiveFormation.NICKEL
    nickel_players = commanders_personnel.get_defensive_personnel(nickel_formation)
    print(f"Nickel Defense Personnel: {commanders_personnel.get_personnel_summary(nickel_players)}")
    
    # Same personnel can run different enhanced passing plays
    pass_call = OffensivePlayCall(OffensivePlayType.PASS, shotgun_formation, concept="quick_slants")
    nickel_defense_call = DefensivePlayCall(DefensivePlayType.NICKEL_DEFENSE, nickel_formation, coverage="man")
    
    shotgun_pass_params = PlayEngineParams(
        offensive_players=shotgun_players,
        defensive_players=nickel_players,
        offensive_play_call=pass_call,
        defensive_play_call=nickel_defense_call
    )
    shotgun_pass_result = play_engine.simulate(shotgun_pass_params)
    print(f"Shotgun Quick Slants vs Nickel Man: {shotgun_pass_result}")
    
    # Same personnel, different enhanced play call
    screen_call = OffensivePlayCall(OffensivePlayType.SCREEN_PASS, shotgun_formation, concept="bubble_screen")
    
    shotgun_screen_params = PlayEngineParams(
        offensive_players=shotgun_players,  # Same shotgun personnel
        defensive_players=nickel_players,   # Same nickel personnel
        offensive_play_call=screen_call,
        defensive_play_call=nickel_defense_call
    )
    shotgun_screen_result = play_engine.simulate(shotgun_screen_params)
    print(f"Shotgun Bubble Screen vs Nickel Man: {shotgun_screen_result}")
    
    # Advanced Factory-Created Play Combinations
    print("\n" + "="*60)
    print("=== ADVANCED FACTORY-CREATED PLAY COMBINATIONS ===")
    print("="*60)
    
    # Show factory-created play combinations
    print("\n=== Factory-Created Play Combinations ===")
    
    # Quick pass vs blitz using factory methods
    quick_pass = PlayCallFactory.create_quick_pass(OffensiveFormation.SHOTGUN)
    safety_blitz = PlayCallFactory.create_blitz("safety_blitz")
    
    print(f"Factory-created Quick Pass: {quick_pass}")
    print(f"Factory-created Safety Blitz: {safety_blitz}")
    
    quick_pass_params = PlayEngineParams(
        offensive_players=shotgun_players,
        defensive_players=nickel_players,
        offensive_play_call=quick_pass,
        defensive_play_call=safety_blitz
    )
    
    quick_pass_result = play_engine.simulate(quick_pass_params)
    print(f"Quick Pass vs Safety Blitz: {quick_pass_result}")
    
    # Situational play calling demonstration
    print("\n=== Situational Play Calling ===")
    
    # 3rd and 8 from own 35 - should favor passing
    third_down_offense = PlayCallFactory.create_situational_offense(down=3, distance=8, field_position=35)
    third_down_defense = PlayCallFactory.create_situational_defense(down=3, distance=8, field_position=65)
    
    print(f"3rd & 8 from own 35-yard line:")
    print(f"  Offensive call: {third_down_offense}")
    print(f"  Defensive call: {third_down_defense}")
    
    situational_params = PlayEngineParams(
        offensive_players=shotgun_players,
        defensive_players=nickel_players,
        offensive_play_call=third_down_offense,
        defensive_play_call=third_down_defense
    )
    
    situational_result = play_engine.simulate(situational_params)
    print(f"  Result: {situational_result}")
    
    # Goal line situation - should favor running
    print(f"\nGoal line from 2-yard line:")
    goal_line_offense = PlayCallFactory.create_situational_offense(down=1, distance=2, field_position=98)
    goal_line_defense = PlayCallFactory.create_situational_defense(down=1, distance=2, field_position=2)
    
    print(f"  Offensive call: {goal_line_offense}")
    print(f"  Defensive call: {goal_line_defense}")
    
    print("\n=== System Consistency Check ===")
    print("All play calls now use the enhanced system with integrated formations!")
    print("No more backward compatibility complexity - clean, single system approach.")

if __name__ == "__main__":
    main()