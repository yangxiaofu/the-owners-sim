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

def main():
    # Create simple team data
    team1 = {"name": "Lions"}
    team2 = {"name": "Commanders"}

    # Create play call parameters directly with specific play types
    offensive_play_params = PlayCallParams(OffensivePlayType.RUN)
    defensive_play_params = PlayCallParams(DefensivePlayType.COVER_2)

    # Create play engine parameters
    params = PlayEngineParams(
        offensive_team=team1,
        defensive_team=team2,
        offensive_playCallParams=offensive_play_params,
        defensive_playCallParams=defensive_play_params
    )

    # Call the play engine
    result = play_engine.simulate(params)
    print(f"Play result: {result}")
    
    # Demonstrate different play types
    print("\n--- Examples of different play types ---")
    
    # Example with PASS vs BLITZ
    pass_params = PlayEngineParams(
        offensive_team=team1,
        defensive_team=team2,
        offensive_playCallParams=PlayCallParams(OffensivePlayType.PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.BLITZ)
    )
    pass_result = play_engine.simulate(pass_params)
    print(f"Pass vs Blitz result: {pass_result}")
    
    # Example with FIELD_GOAL vs GOAL_LINE_DEFENSE
    fg_params = PlayEngineParams(
        offensive_team=team1,
        defensive_team=team2,
        offensive_playCallParams=PlayCallParams(OffensivePlayType.FIELD_GOAL),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.GOAL_LINE_DEFENSE)
    )
    fg_result = play_engine.simulate(fg_params)
    print(f"Field Goal vs Goal Line Defense result: {fg_result}")
    
    # Example with PLAY_ACTION vs COVER_3
    play_action_params = PlayEngineParams(
        offensive_team=team1,
        defensive_team=team2,
        offensive_playCallParams=PlayCallParams(OffensivePlayType.PLAY_ACTION_PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.COVER_3)
    )
    play_action_result = play_engine.simulate(play_action_params)
    print(f"Play Action vs Cover 3 result: {play_action_result}")
    
    # Example with SCREEN_PASS vs FOUR_MAN_RUSH
    screen_params = PlayEngineParams(
        offensive_team=team1,
        defensive_team=team2,
        offensive_playCallParams=PlayCallParams(OffensivePlayType.SCREEN_PASS),
        defensive_playCallParams=PlayCallParams(DefensivePlayType.FOUR_MAN_RUSH)
    )
    screen_result = play_engine.simulate(screen_params)
    print(f"Screen Pass vs Four Man Rush result: {screen_result}")

if __name__ == "__main__":
    main()