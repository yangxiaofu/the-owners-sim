#!/usr/bin/env python3
"""
Debug Punt Zero Yards Issue

Reproduces the exact scenario where punt results in 0 yards to identify
the root cause of the PuntSimulator failure.
"""

import sys
import os
from typing import Dict, Any

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.core.engine import simulate
from play_engine.core.params import PlayEngineParams
from play_engine.play_calls.offensive_play_call import OffensivePlayCall
from play_engine.play_calls.defensive_play_call import DefensivePlayCall
from play_engine.play_types.offensive_types import OffensivePlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from play_engine.mechanics.formations import OffensiveFormation
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from constants.team_ids import TeamIDs
from play_engine.play_calling.special_teams_coordinator import SpecialTeamsCoordinator


def test_punt_execution():
    """Test punt execution to identify why it's returning 0 yards"""
    
    print("🔍 DEBUG: Testing Punt Execution Flow")
    print("=" * 60)
    
    # Generate minimal rosters
    home_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.KANSAS_CITY_CHIEFS)
    away_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.NEW_ENGLAND_PATRIOTS)
    
    home_personnel = PersonnelPackageManager(home_roster)
    away_personnel = PersonnelPackageManager(away_roster)
    
    # Create the exact same offensive call that SpecialTeamsCoordinator would create
    print("1. Creating punt offensive call (same as SpecialTeamsCoordinator)...")
    offensive_call = OffensivePlayCall(
        play_type=OffensivePlayType.PUNT,
        formation=OffensiveFormation.PUNT,  # Exactly what SpecialTeamsCoordinator uses
        concept="standard_punt",
        personnel_package="punt_team"
    )
    
    # Create defensive call (punt return)
    print("2. Creating punt defensive call...")
    defensive_call = DefensivePlayCall(
        play_type=DefensivePlayType.PUNT_RETURN,
        formation="punt_return",  # UnifiedDefensiveFormation coordinator name
        coverage="safe_punt_return"
    )
    
    print(f"   Offensive: {offensive_call.play_type} | {offensive_call.formation}")
    print(f"   Defensive: {defensive_call.play_type} | {defensive_call.formation}")
    
    # Get personnel for formations
    print("3. Getting personnel packages...")
    try:
        offensive_players = home_personnel.get_offensive_personnel(
            offensive_call.formation
        )
        defensive_players = away_personnel.get_defensive_personnel(
            defensive_call.formation
        )
        print(f"   ✅ Personnel retrieved successfully")
        print(f"      Offensive players: {len(offensive_players)}")
        print(f"      Defensive players: {len(defensive_players)}")
    except Exception as e:
        print(f"   ❌ Personnel retrieval failed: {e}")
        return
    
    # Create play engine params  
    print("4. Creating play engine params...")
    try:
        play_params = PlayEngineParams(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_play_call=offensive_call,
            defensive_play_call=defensive_call
        )
        print(f"   ✅ PlayEngineParams created successfully")
    except Exception as e:
        print(f"   ❌ PlayEngineParams creation failed: {e}")
        return
    
    # Execute the play and capture any exceptions
    print("5. Executing punt play through engine...")
    try:
        result = simulate(play_params)
        print(f"   ✅ Punt executed successfully!")
        print(f"      Outcome: {result.outcome}")
        print(f"      Yards: {result.yards}")
        print(f"      Time: {result.time_elapsed}")
        print(f"      Is Punt: {getattr(result, 'is_punt', 'Not set')}")
        
        if result.yards == 0:
            print(f"   ⚠️  ISSUE FOUND: Punt returned 0 yards")
            print(f"      This suggests PuntSimulator is failing internally")
        
    except Exception as e:
        print(f"   ❌ Punt execution failed with exception: {e}")
        print(f"      Exception type: {type(e).__name__}")
        
        # This would trigger create_failed_punt_result() which returns 0 yards
        print(f"   📝 This exception would cause create_failed_punt_result() to return 0 yards")
        
        import traceback
        print(f"   📋 Full traceback:")
        traceback.print_exc()


def test_special_teams_coordinator_punt():
    """Test the SpecialTeamsCoordinator punt creation directly"""
    print("\n🔍 DEBUG: Testing SpecialTeamsCoordinator Punt Creation")
    print("=" * 60)
    
    from play_engine.play_calling.special_teams_coordinator import create_balanced_special_teams_coordinator
    
    # Create a special teams coordinator
    st_coordinator = create_balanced_special_teams_coordinator("Test Team")
    
    # Test context for punt decision
    context = {
        'field_position': 40,
        'yards_to_go': 15,
        'score_differential': 0,
        'time_remaining': 600
    }
    
    print("1. Creating punt play through SpecialTeamsCoordinator...")
    try:
        punt_call = st_coordinator._select_punt_play(context)
        print(f"   ✅ Punt call created successfully!")
        print(f"      Play Type: {punt_call.play_type}")
        print(f"      Formation: {punt_call.formation}")
        print(f"      Concept: {punt_call.concept}")
        print(f"      Personnel: {punt_call.personnel_package}")
    except Exception as e:
        print(f"   ❌ SpecialTeamsCoordinator punt creation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_special_teams_coordinator_punt()
    test_punt_execution()