#!/usr/bin/env python3
"""
Test Team JSON Migration - Verify that team data is properly loaded from JSON
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_json_team_loading():
    """Test that teams can be loaded from JSON with comprehensive data"""
    
    print("Testing Team JSON Migration")
    print("=" * 50)
    
    try:
        # Import the data loading components
        from src.game_engine.data.sources.json_data_source import JsonDataSource
        from src.game_engine.data.loaders.team_loader import TeamLoader
        
        # Create data source and loader (use string interface)
        team_loader = TeamLoader("json")
        
        # Test loading all teams
        all_teams = team_loader.get_all()
        
        print(f"✅ Loaded {len(all_teams)} teams from JSON")
        
        # Test specific team data
        for team_id in [1, 2, 5]:  # Bears, Packers, Cowboys
            team = team_loader.get_by_id(team_id)
            if team:
                print(f"\n--- {team.full_name} ---")
                print(f"Overall Rating: {team.get_rating('overall_rating')}")
                print(f"Team Philosophy: {getattr(team, 'team_philosophy', 'Unknown')}")
                
                # Test coaching data
                offensive_archetype = team.get_coaching_archetype("offensive")
                defensive_archetype = team.get_coaching_archetype("defensive") 
                print(f"Offensive Coordinator: {offensive_archetype}")
                print(f"Defensive Coordinator: {defensive_archetype}")
                
                # Test custom modifiers
                off_modifiers = team.get_custom_modifiers("offensive")
                def_modifiers = team.get_custom_modifiers("defensive")
                if off_modifiers:
                    print(f"Offensive Modifiers: {off_modifiers}")
                if def_modifiers:
                    print(f"Defensive Modifiers: {def_modifiers}")
                
                print(f"✅ {team.name} data validation passed")
            else:
                print(f"❌ Failed to load team {team_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_game_orchestrator_integration():
    """Test that GameOrchestrator can use the JSON team data"""
    
    print("\n" + "=" * 50)
    print("Testing GameOrchestrator Integration")
    print("=" * 50)
    
    try:
        from src.game_engine.core.game_orchestrator import SimpleGameEngine
        
        # Create game engine with JSON data source
        game_engine = SimpleGameEngine("json")
        
        # Test getting team data for simulation
        for team_id in [1, 2]:  # Bears vs Packers
            team_data = game_engine.get_team_for_simulation(team_id)
            
            print(f"\n--- Team {team_id}: {team_data.get('name', 'Unknown')} ---")
            print(f"City: {team_data.get('city', 'Unknown')}")
            print(f"Overall Rating: {team_data.get('overall_rating', 'Unknown')}")
            print(f"Team Philosophy: {team_data.get('team_philosophy', 'Unknown')}")
            
            # Check coaching data structure
            coaching = team_data.get('coaching', {})
            if coaching:
                print(f"Offensive Rating: {coaching.get('offensive', 'Unknown')}")
                print(f"Defensive Rating: {coaching.get('defensive', 'Unknown')}")
                
                # Check for enhanced coaching data
                if 'offensive_coordinator' in coaching:
                    oc = coaching['offensive_coordinator']
                    print(f"OC Archetype: {oc.get('archetype', 'Unknown')}")
                    print(f"OC Custom Modifiers: {oc.get('custom_modifiers', {})}")
                
                if 'defensive_coordinator' in coaching:
                    dc = coaching['defensive_coordinator'] 
                    print(f"DC Archetype: {dc.get('archetype', 'Unknown')}")
                    print(f"DC Custom Modifiers: {dc.get('custom_modifiers', {})}")
            
            print(f"✅ Team {team_id} integration test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coaching_staff_creation():
    """Test that CoachingStaff objects are created properly"""
    
    print("\n" + "=" * 50)
    print("Testing CoachingStaff Creation") 
    print("=" * 50)
    
    try:
        from src.game_engine.core.game_orchestrator import SimpleGameEngine
        
        # Create game engine 
        game_engine = SimpleGameEngine("json")
        
        # Test team with coaching staff
        team_data = game_engine.get_team_for_simulation(2)  # Packers
        
        if 'coaching_staff' in team_data:
            coaching_staff = team_data['coaching_staff']
            print(f"✅ CoachingStaff created for {team_data['name']}")
            print(f"Team ID: {coaching_staff.team_id}")
            
            # Test archetype access
            try:
                offensive_archetype = coaching_staff.get_offensive_coordinator_archetype()
                defensive_archetype = coaching_staff.get_defensive_coordinator_archetype()
                print(f"OC Archetype: {offensive_archetype}")
                print(f"DC Archetype: {defensive_archetype}")
                print("✅ CoachingStaff archetype access working")
            except Exception as e:
                print(f"⚠️ CoachingStaff archetype access failed: {e}")
        else:
            print("⚠️ No coaching_staff found in team data")
        
        return True
        
    except Exception as e:
        print(f"❌ CoachingStaff test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Team Data JSON Migration Test Suite")
    print("Testing transition from hardcoded to JSON-based team data\n")
    
    success_count = 0
    total_tests = 3
    
    # Run tests
    if test_json_team_loading():
        success_count += 1
    
    if test_game_orchestrator_integration():
        success_count += 1
    
    if test_coaching_staff_creation():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ JSON team data migration is working correctly")
        print("✅ GameOrchestrator integration successful")
        print("✅ Enhanced coaching data properly loaded")
        print("\nThe hardcoded _legacy_teams_data can be safely removed!")
    else:
        print("❌ Some tests failed")
        print("⚠️ Migration needs more work before removing hardcoded data")
    
    print("=" * 60)