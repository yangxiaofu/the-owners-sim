#!/usr/bin/env python3

# Add src to path so we can import play_engine
import sys
sys.path.append('src')

import play_engine
from playcall import PlayCall
from play_engine_params import PlayEngineParams
from offensive_play_type import OffensivePlayType
from defensive_play_type import DefensivePlayType
from play_call_params import PlayCallParams
from personnel_package_manager import PersonnelPackageManager, TeamRosterGenerator
from formation import OffensiveFormation, DefensiveFormation

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
    
    # STEP 3: Now call plays within those formations
    print("=== Play Calls Within Formations ===")
    print(f"From {offensive_formation}, Lions could call: {OffensivePlayType.RUN} or {OffensivePlayType.PLAY_ACTION_PASS}")
    print(f"From {defensive_formation}, Commanders could call: {DefensivePlayType.COVER_2} or {DefensivePlayType.BLITZ}")
    print()

    # Create play call parameters - same personnel, different plays
    offensive_play_params = PlayCallParams(OffensivePlayType.RUN)  # Run from I-Formation
    defensive_play_params = PlayCallParams(DefensivePlayType.COVER_2)  # Cover 2 from 4-3

    # Create play engine parameters
    params = PlayEngineParams(
        offensive_players=offensive_players,  # 11 Lions offensive players
        defensive_players=defensive_players,  # 11 Commanders defensive players
        offensive_playCallParams=offensive_play_params,
        defensive_playCallParams=defensive_play_params
    )

    # TODO: Add offensive play caller that selects both formation and play call
    # Call the play engine
    result = play_engine.simulate(params)
    print(f"Play result: {result}")
    
    # Demonstrate how different plays can be called from the same formation
    print("=== Multiple Plays From Same Formation ===")
    
    # Same I-Formation personnel, different play calls
    run_params = PlayEngineParams(
        offensive_players=offensive_players,  # Same I-Formation players
        defensive_players=defensive_players,  # Same 4-3 players  
        offensive_playCallParams=PlayCallParams(OffensivePlayType.RUN),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.COVER_2)
    )
    run_result = play_engine.simulate(run_params)
    print(f"I-Formation Run vs 4-3 Cover 2: {run_result}")
    
    # Same personnel, different play call  
    play_action_params = PlayEngineParams(
        offensive_players=offensive_players,  # Same I-Formation players
        defensive_players=defensive_players,  # Same 4-3 players
        offensive_playCallParams=PlayCallParams(OffensivePlayType.PLAY_ACTION_PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.BLITZ)
    )


    play_action_result = play_engine.simulate(play_action_params)
    print(f"I-Formation Play Action vs 4-3 Blitz: {play_action_result}")
    print()
    
    # Show how different formations have different personnel
    print("=== Different Formations = Different Personnel ===")
    
    # Shotgun formation for passing
    shotgun_formation = OffensiveFormation.SHOTGUN
    shotgun_players = lions_personnel.get_offensive_personnel(shotgun_formation)
    print(f"Shotgun Formation Personnel: {lions_personnel.get_personnel_summary(shotgun_players)}")
    
    # Nickel defense for passing situations
    nickel_formation = DefensiveFormation.NICKEL
    nickel_players = commanders_personnel.get_defensive_personnel(nickel_formation)
    print(f"Nickel Defense Personnel: {commanders_personnel.get_personnel_summary(nickel_players)}")
    
    # Same personnel can run different passing plays
    shotgun_pass_params = PlayEngineParams(
        offensive_players=shotgun_players,
        defensive_players=nickel_players,
        offensive_playCallParams=PlayCallParams(OffensivePlayType.PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.NICKEL_DEFENSE)
    )
    shotgun_pass_result = play_engine.simulate(shotgun_pass_params)
    print(f"Shotgun Pass vs Nickel: {shotgun_pass_result}")
    
    shotgun_screen_params = PlayEngineParams(
        offensive_players=shotgun_players,  # Same shotgun personnel
        defensive_players=nickel_players,   # Same nickel personnel
        offensive_playCallParams=PlayCallParams(OffensivePlayType.SCREEN_PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.NICKEL_DEFENSE)
    )
    shotgun_screen_result = play_engine.simulate(shotgun_screen_params)
    print(f"Shotgun Screen vs Nickel: {shotgun_screen_result}")

if __name__ == "__main__":
    main()