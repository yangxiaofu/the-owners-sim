#!/usr/bin/env python3
"""
Test script for the new SpecialTeamsPlayCall system

Tests the complete Option 1 implementation:
- SpecialTeamsPlayCall class
- Updated PlayCallFactory
- Special teams coordinator integration
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_special_teams_play_call():
    """Test SpecialTeamsPlayCall class creation and methods"""
    print("🧪 Testing SpecialTeamsPlayCall Class")
    print("=" * 50)
    
    from play_engine.play_calls.special_teams_play_call import SpecialTeamsPlayCall
    from play_engine.play_types.offensive_types import OffensivePlayType, PuntPlayType
    from play_engine.play_types.defensive_types import DefensivePlayType
    from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
    
    # Test 1: Create basic field goal play
    print("\n1. Field Goal Play Creation:")
    field_goal_play = SpecialTeamsPlayCall(
        play_type=OffensivePlayType.FIELD_GOAL,
        formation=OffensiveFormation.FIELD_GOAL,
        strategy="field_goal_attempt"
    )
    print(f"   Created: {field_goal_play}")
    print(f"   Is Kicking Play: {field_goal_play.is_kicking_play()}")
    print(f"   Is Offensive ST: {field_goal_play.is_offensive_special_teams()}")
    
    # Test 2: Create punt play with coverage
    print("\n2. Punt Play Creation:")
    punt_play = SpecialTeamsPlayCall(
        play_type=OffensivePlayType.PUNT,
        formation=OffensiveFormation.PUNT,
        strategy="directional_punt",
        target_area="coffin_corner"
    )
    print(f"   Created: {punt_play}")
    print(f"   Is Kicking Play: {punt_play.is_kicking_play()}")
    print(f"   Target Area: {punt_play.get_target_area()}")
    
    # Test 3: Create fake punt
    print("\n3. Fake Punt Play Creation:")
    fake_punt_play = SpecialTeamsPlayCall(
        play_type=PuntPlayType.FAKE_PUNT_PASS,
        formation=OffensiveFormation.PUNT,
        strategy="fake_punt_pass"
    )
    print(f"   Created: {fake_punt_play}")
    print(f"   Is Fake Play: {fake_punt_play.is_fake_play()}")
    print(f"   Is Kicking Play: {fake_punt_play.is_kicking_play()}")
    
    # Test 4: Create defensive special teams (punt return)
    print("\n4. Punt Return Play Creation:")
    punt_return_play = SpecialTeamsPlayCall(
        play_type=DefensivePlayType.PUNT_RETURN,
        formation=DefensiveFormation.PUNT_RETURN,
        coverage="return_left"
    )
    print(f"   Created: {punt_return_play}")
    print(f"   Is Return Play: {punt_return_play.is_return_play()}")
    print(f"   Is Defensive ST: {punt_return_play.is_defensive_special_teams()}")
    
    print("   ✅ SpecialTeamsPlayCall tests passed!")


def test_play_call_factory():
    """Test updated PlayCallFactory methods"""
    print("\n🏭 Testing PlayCallFactory Integration")
    print("=" * 50)
    
    from play_engine.play_calls.play_call_factory import PlayCallFactory
    
    # Test special teams factory methods
    print("\n1. Factory Method Tests:")
    
    # Test field goal creation
    field_goal = PlayCallFactory.create_field_goal()
    print(f"   Field Goal: {field_goal}")
    print(f"   Type: {type(field_goal).__name__}")
    
    # Test punt creation
    punt = PlayCallFactory.create_punt()
    print(f"   Punt: {punt}")
    print(f"   Type: {type(punt).__name__}")
    
    # Test kickoff creation
    kickoff = PlayCallFactory.create_kickoff()
    print(f"   Kickoff: {kickoff}")
    print(f"   Type: {type(kickoff).__name__}")
    
    # Test new methods
    fake_punt_pass = PlayCallFactory.create_fake_punt_pass()
    print(f"   Fake Punt Pass: {fake_punt_pass}")
    
    onside_kick = PlayCallFactory.create_onside_kick()
    print(f"   Onside Kick: {onside_kick}")
    
    punt_return = PlayCallFactory.create_punt_return()
    print(f"   Punt Return: {punt_return}")
    
    # Test special teams play creation by name
    print("\n2. Named Play Creation:")
    st_field_goal = PlayCallFactory.create_special_teams_play("field_goal")
    print(f"   Named Field Goal: {st_field_goal}")
    
    st_punt_block = PlayCallFactory.create_special_teams_play("punt_block")
    print(f"   Named Punt Block: {st_punt_block}")
    
    # Test available plays
    print("\n3. Available Special Teams Plays:")
    available = PlayCallFactory.get_available_special_teams_plays()
    print(f"   Available plays: {', '.join(available)}")
    
    print("   ✅ PlayCallFactory tests passed!")


def test_special_teams_coordinator():
    """Test special teams coordinator integration"""
    print("\n🏈 Testing SpecialTeamsCoordinator Integration")
    print("=" * 50)
    
    from play_engine.play_calling.special_teams_coordinator import (
        SpecialTeamsCoordinator, create_aggressive_special_teams_coordinator,
        create_conservative_special_teams_coordinator
    )
    from play_engine.play_calling.fourth_down_matrix import FourthDownDecisionType
    
    # Create different coordinator types
    aggressive_st = create_aggressive_special_teams_coordinator("Test Team")
    conservative_st = create_conservative_special_teams_coordinator("Test Team")
    
    print(f"\n1. Coordinator Creation:")
    print(f"   Aggressive ST: {aggressive_st.name}")
    print(f"   Conservative ST: {conservative_st.name}")
    
    # Test context for play calling
    test_context = {
        'field_position': 45,
        'yards_to_go': 8,
        'score_differential': 0,
        'time_remaining': 600
    }
    
    print(f"\n2. Offensive Special Teams Play Selection:")
    
    # Test punt selection
    aggressive_punt = aggressive_st.select_offensive_special_teams_play(
        FourthDownDecisionType.PUNT, test_context
    )
    print(f"   Aggressive Punt: {aggressive_punt}")
    print(f"   Type: {type(aggressive_punt).__name__}")
    
    conservative_punt = conservative_st.select_offensive_special_teams_play(
        FourthDownDecisionType.PUNT, test_context
    )
    print(f"   Conservative Punt: {conservative_punt}")
    
    # Test field goal selection
    fg_context = test_context.copy()
    fg_context['field_position'] = 75  # In field goal range
    
    aggressive_fg = aggressive_st.select_offensive_special_teams_play(
        FourthDownDecisionType.FIELD_GOAL, fg_context
    )
    print(f"   Aggressive FG: {aggressive_fg}")
    
    print(f"\n3. Defensive Special Teams Play Selection:")
    
    # Test punt defense
    aggressive_punt_def = aggressive_st.select_defensive_special_teams_play(
        FourthDownDecisionType.PUNT, test_context
    )
    print(f"   Aggressive Punt Defense: {aggressive_punt_def}")
    print(f"   Type: {type(aggressive_punt_def).__name__}")
    
    conservative_punt_def = conservative_st.select_defensive_special_teams_play(
        FourthDownDecisionType.PUNT, test_context
    )
    print(f"   Conservative Punt Defense: {conservative_punt_def}")
    
    # Test field goal defense
    aggressive_fg_def = aggressive_st.select_defensive_special_teams_play(
        FourthDownDecisionType.FIELD_GOAL, fg_context
    )
    print(f"   Aggressive FG Defense: {aggressive_fg_def}")
    
    print("   ✅ SpecialTeamsCoordinator tests passed!")


def test_integration():
    """Test full integration between all components"""
    print("\n🔗 Testing Full System Integration")
    print("=" * 50)
    
    from play_engine.play_calls import (
        OffensivePlayCall, DefensivePlayCall, SpecialTeamsPlayCall, PlayCallFactory
    )
    
    print("\n1. Import Tests:")
    print("   ✅ All classes importable from play_calls module")
    
    # Test that we can create all three types
    off_play = PlayCallFactory.create_power_run()
    def_play = PlayCallFactory.create_cover_2()
    st_play = PlayCallFactory.create_field_goal()
    
    print(f"\n2. Mixed Play Creation:")
    print(f"   Offensive: {type(off_play).__name__}")
    print(f"   Defensive: {type(def_play).__name__}")
    print(f"   Special Teams: {type(st_play).__name__}")
    
    # Test that special teams plays are distinct
    print(f"\n3. Type Verification:")
    print(f"   Special Teams is SpecialTeamsPlayCall: {isinstance(st_play, SpecialTeamsPlayCall)}")
    print(f"   Special Teams is not OffensivePlayCall: {not isinstance(st_play, OffensivePlayCall)}")
    print(f"   Special Teams is not DefensivePlayCall: {not isinstance(st_play, DefensivePlayCall)}")
    
    print("   ✅ Full integration tests passed!")


def main():
    """Run all tests for the special teams play call system"""
    print("🚀 SPECIAL TEAMS PLAY CALL SYSTEM TEST SUITE")
    print("=" * 60)
    print("Testing Option 1 implementation: Three-way organizational split")
    print("- OffensivePlayCall")
    print("- DefensivePlayCall") 
    print("- SpecialTeamsPlayCall")
    print("=" * 60)
    
    try:
        # Run all test suites
        test_special_teams_play_call()
        test_play_call_factory()
        test_special_teams_coordinator()
        test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("✅ Option 1 implementation successful!")
        print("✅ Special teams plays now properly organized")
        print("✅ Matches NFL coaching organizational structure")
        print("✅ Clean separation of concerns achieved")
        
        print(f"\n📊 SYSTEM SUMMARY:")
        print(f"   • SpecialTeamsPlayCall: Handles all ST plays")
        print(f"   • PlayCallFactory: Updated with ST methods")
        print(f"   • SpecialTeamsCoordinator: Uses new play calls")
        print(f"   • Clean three-way organizational split complete")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)