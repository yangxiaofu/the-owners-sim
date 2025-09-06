#!/usr/bin/env python3
"""
Debug Demo Punt Issue - Reproduce the exact demo scenario
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.play_calling.play_caller import PlayCallContext, PlayCallerFactory
from play_engine.game_state.drive_manager import DriveSituation
from constants.team_ids import TeamIDs

def test_demo_punt_scenario():
    """Test the exact scenario that occurs in the demo"""
    print("🔍 DEBUG: Testing Demo Punt Scenario")
    print("=" * 60)
    
    # Create the same coaching staff as demo
    offensive_play_caller = PlayCallerFactory.create_chiefs_style_caller()
    
    # Create 4th down situation like in demo
    situation = DriveSituation(
        down=4,
        yards_to_go=15,
        field_position=40,
        possessing_team="Kansas City Chiefs",
        time_remaining=800
    )
    
    play_context = PlayCallContext(
        situation=situation,
        game_flow="neutral"
    )
    
    print("1. Testing offensive play call on 4th down...")
    try:
        offensive_call = offensive_play_caller.select_offensive_play(play_context)
        print(f"   ✅ Offensive call created")
        print(f"      Play Type: {offensive_call.play_type}")
        print(f"      Formation: {offensive_call.formation}")
        print(f"      Concept: {offensive_call.concept}")
    except Exception as e:
        print(f"   ❌ Offensive call failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n2. Testing defensive play call on 4th down...")
    try:
        defensive_play_caller = PlayCallerFactory.create_patriots_style_caller()
        defensive_call = defensive_play_caller.select_defensive_play(play_context)
        print(f"   ✅ Defensive call created")
        print(f"      Play Type: {defensive_call.play_type}")
        print(f"      Formation: {defensive_call.formation}")
        print(f"      Coverage: {defensive_call.coverage}")
    except Exception as e:
        print(f"   ❌ Defensive call failed: {e}")
        import traceback
        traceback.print_exc()
        return
        
    print("\n3. Now testing execution with same setup as demo...")
    from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
    from play_engine.core.params import PlayEngineParams
    from play_engine.core.engine import simulate
    from play_engine.core.play_result import PlayResult
    
    # Same personnel setup as demo
    home_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.KANSAS_CITY_CHIEFS)
    away_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.NEW_ENGLAND_PATRIOTS)
    
    offensive_personnel = PersonnelPackageManager(home_roster)
    defensive_personnel = PersonnelPackageManager(away_roster)
    
    try:
        # Get personnel for formations (same as demo)
        offensive_players = offensive_personnel.get_offensive_personnel(
            offensive_call.get_formation()
        )
        defensive_players = defensive_personnel.get_defensive_personnel(
            defensive_call.get_formation()
        )
        
        # Create play engine params (same as demo)
        play_params = PlayEngineParams(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_play_call=offensive_call,
            defensive_play_call=defensive_call
        )
        
        # Execute play using existing engine (same as demo)
        engine_result = simulate(play_params)
        
        print(f"   ✅ Engine result:")
        print(f"      Outcome: {engine_result.outcome}")
        print(f"      Yards: {engine_result.yards}")
        print(f"      Time: {engine_result.time_elapsed}")
        print(f"      Is Punt: {getattr(engine_result, 'is_punt', 'Not set')}")
        
        # Now do the SAME conversion as the demo (this is where the bug might be)
        play_result = PlayResult(
            outcome=engine_result.outcome,
            yards=engine_result.yards,
            time_elapsed=engine_result.time_elapsed,
            points=engine_result.points,
            is_scoring_play=(engine_result.points > 0),
            achieved_first_down=False,  # Will be determined by DriveManager
            penalty_occurred=False,  # Simplified for demo
            penalty_yards=0
            # NOTE: is_punt is NOT copied here!
        )
        
        print(f"   ⚠️  After demo conversion:")
        print(f"      Outcome: {play_result.outcome}")
        print(f"      Yards: {play_result.yards}")
        print(f"      Time: {play_result.time_elapsed}")
        print(f"      Is Punt: {getattr(play_result, 'is_punt', 'Not set')}")
        
        if hasattr(engine_result, 'is_punt') and engine_result.is_punt:
            if not hasattr(play_result, 'is_punt') or not play_result.is_punt:
                print(f"   🚨 BUG FOUND: Demo is losing the is_punt flag!")
                print(f"      Engine result has is_punt={engine_result.is_punt}")
                print(f"      Demo result has is_punt={getattr(play_result, 'is_punt', False)}")
        
    except Exception as e:
        print(f"   ❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_demo_punt_scenario()