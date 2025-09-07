#!/usr/bin/env python3
"""
Simple Punt Demo - Focused Single Punt Play Execution

This demo shows the complete flow of executing ONE punt play:
1. Team setup with realistic rosters
2. Special teams play call creation (new SpecialTeamsPlayCall system)  
3. Play execution through the engine
4. Comprehensive PlayResult output

Demonstrates: 4th & 8, own 35-yard line punt situation
Teams: Kansas City Chiefs (punting) vs Detroit Lions (returning)
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.core.engine import simulate
from play_engine.core.params import PlayEngineParams
from play_engine.play_calls.play_call_factory import PlayCallFactory
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id


def create_punt_scenario():
    """Create a realistic 4th down punt scenario"""
    print("🏈 SIMPLE PUNT DEMO")
    print("=" * 50)
    print("Scenario: 4th & 8, Kansas City Chiefs 35-yard line")
    print("Chiefs punting to Lions")
    print("=" * 50)
    
    return {
        'down': 4,
        'yards_to_go': 8,
        'field_position': 35,
        'punting_team': 'Kansas City Chiefs',
        'receiving_team': 'Detroit Lions',
        'time_remaining': 450,  # 7:30 left in quarter
        'quarter': 2
    }


def setup_teams():
    """Set up both teams with realistic rosters"""
    print("\n📋 TEAM SETUP")
    print("-" * 30)
    
    # Get team information
    chiefs = get_team_by_id(TeamIDs.KANSAS_CITY_CHIEFS)
    lions = get_team_by_id(TeamIDs.DETROIT_LIONS)
    
    print(f"Punting Team: {chiefs.city} {chiefs.nickname}")
    print(f"Receiving Team: {lions.city} {lions.nickname}")
    
    # Generate rosters
    print("\nGenerating team rosters...")
    chiefs_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.KANSAS_CITY_CHIEFS)
    lions_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.DETROIT_LIONS)
    
    print(f"✅ Chiefs roster: {len(chiefs_roster)} players")
    print(f"✅ Lions roster: {len(lions_roster)} players")
    
    return chiefs_roster, lions_roster, chiefs, lions


def create_special_teams_play_calls():
    """Create special teams play calls using new SpecialTeamsPlayCall system"""
    print("\n🎯 SPECIAL TEAMS PLAY CALLS")
    print("-" * 35)
    
    # Create punt play call (Chiefs offensive special teams)
    punt_play_call = PlayCallFactory.create_punt()
    print(f"Offensive Play Call: {punt_play_call}")
    print(f"  Type: {type(punt_play_call).__name__}")
    print(f"  Play Type: {punt_play_call.get_play_type()}")
    print(f"  Formation: {punt_play_call.get_formation()}")
    print(f"  Strategy: {punt_play_call.get_strategy()}")
    
    # Create punt return play call (Lions defensive special teams)
    punt_return_call = PlayCallFactory.create_punt_return()
    print(f"\nDefensive Play Call: {punt_return_call}")
    print(f"  Type: {type(punt_return_call).__name__}")
    print(f"  Play Type: {punt_return_call.get_play_type()}")
    print(f"  Formation: {punt_return_call.get_formation()}")
    print(f"  Coverage: {punt_return_call.get_coverage()}")
    
    return punt_play_call, punt_return_call


def setup_personnel(chiefs_roster, lions_roster, punt_play_call, punt_return_call):
    """Set up 11-man units for punt play"""
    print("\n👥 PERSONNEL PACKAGES")
    print("-" * 25)
    
    # Set up Chiefs special teams unit (punting)
    chiefs_personnel = PersonnelPackageManager(chiefs_roster)
    offensive_players = chiefs_personnel.get_offensive_personnel(punt_play_call.get_formation())
    
    print(f"Chiefs Punt Unit ({len(offensive_players)} players):")
    for i, player in enumerate(offensive_players[:3]):  # Show first 3
        print(f"  {i+1}. {player.name} ({player.primary_position})")
    print(f"  ... and {len(offensive_players)-3} more players")
    
    # Set up Lions return unit (receiving)
    lions_personnel = PersonnelPackageManager(lions_roster)
    defensive_players = lions_personnel.get_defensive_personnel(punt_return_call.get_formation())
    
    print(f"\nLions Return Unit ({len(defensive_players)} players):")
    for i, player in enumerate(defensive_players[:3]):  # Show first 3
        print(f"  {i+1}. {player.name} ({player.primary_position})")
    print(f"  ... and {len(defensive_players)-3} more players")
    
    return offensive_players, defensive_players


def execute_punt_play(offensive_players, defensive_players, punt_play_call, punt_return_call):
    """Execute the punt play through the engine"""
    print("\n⚡ PLAY EXECUTION")
    print("-" * 20)
    
    # Create PlayEngineParams
    play_params = PlayEngineParams(
        offensive_players=offensive_players,
        defensive_players=defensive_players,
        offensive_play_call=punt_play_call,
        defensive_play_call=punt_return_call
    )
    
    print("Executing punt play through engine...")
    print("🏃 Punt in progress...")
    
    # Simulate the play
    play_result = simulate(play_params)
    
    print("✅ Play completed!")
    
    return play_result


def display_punt_results(play_result, scenario):
    """Display comprehensive punt play results with enhanced two-stage breakdown"""
    print("\n📊 PUNT PLAY RESULTS")
    print("=" * 40)
    
    # Basic play information
    print(f"Play Outcome: {play_result.outcome}")
    print(f"Net Field Position Change: {play_result.yards} yards")
    print(f"Time Elapsed: {play_result.time_elapsed:.1f} seconds")
    
    # NEW: Possession tracking
    print(f"\n🔄 POSSESSION CHANGE:")
    print(f"  Change of Possession: {'✅ YES' if play_result.change_of_possession else '❌ NO'}")
    print(f"  Turnover: {'⚠️ YES' if play_result.is_turnover else '✅ NO (normal)'}")
    
    # NEW: Enhanced punt breakdown with two-stage data
    print(f"\n🦵 DETAILED PUNT BREAKDOWN:")
    if play_result.punt_distance is not None:
        print(f"  Stage 1 - Punt Distance: {play_result.punt_distance} yards")
    if play_result.hang_time is not None:
        print(f"  Stage 1 - Hang Time: {play_result.hang_time:.1f} seconds")
    if play_result.coverage_pressure is not None:
        print(f"  Stage 1 - Coverage Pressure: {play_result.coverage_pressure:.2f}/1.0")
    if play_result.return_yards is not None:
        print(f"  Stage 2 - Return Yards: {play_result.return_yards} yards")
        
    # Analysis of two-stage results
    if play_result.punt_distance and play_result.return_yards is not None:
        print(f"  Net Calculation: {play_result.punt_distance} - {play_result.return_yards} = {play_result.yards} yards")
        
        # Contextual analysis
        if play_result.coverage_pressure and play_result.coverage_pressure > 0.7:
            print(f"  💪 Excellent coverage limited return opportunity")
        elif play_result.return_yards > 15:
            print(f"  🏃 Strong return execution by receiving team")
        elif play_result.return_yards == 0 and "fair_catch" in play_result.outcome:
            print(f"  🙋 Fair catch due to coverage pressure")
    
    # Field position analysis
    print(f"\n🏈 FIELD POSITION IMPACT:")
    print(f"  Starting: {scenario['punting_team']} {scenario['field_position']}-yard line")
    final_position = 100 - (scenario['field_position'] + play_result.yards)
    print(f"  Ending: {scenario['receiving_team']} {final_position}-yard line")
    print(f"  Field Position Swing: {abs(play_result.yards)} yards")
    
    # Determine punt outcome narrative
    outcome = play_result.outcome
    yards = play_result.yards
    
    print(f"\n📖 PLAY NARRATIVE:")
    if "fair_catch" in outcome:
        print(f"  • Returner signaled fair catch - no return attempted")
        print(f"  • Punt traveled {play_result.punt_distance or 'unknown'} yards")
    elif "punt_return" in outcome:
        print(f"  • Punt returned: {play_result.punt_distance or 'unknown'} yard punt, {play_result.return_yards or 'unknown'} yard return")
        print(f"  • Net punt effect: {yards} yards of field position")
    elif "touchback" in outcome:
        print(f"  • Punt into end zone resulted in touchback")
        print(f"  • Ball placed at 25-yard line")
    elif "blocked" in outcome:
        print(f"  • Punt was BLOCKED at the line of scrimmage!")
        print(f"  • This counts as a turnover: {play_result.is_turnover}")
    else:
        print(f"  • Punt outcome: {outcome}")
        print(f"  • Field position change: {yards} yards")
    
    # Player statistics (if available)
    if hasattr(play_result, 'player_stats_summary') and play_result.player_stats_summary:
        print(f"\n👤 PLAYER STATISTICS:")
        stats = play_result.player_stats_summary
        if hasattr(stats, 'yards_gained'):
            print(f"  Net yards recorded: {stats.yards_gained}")
        if hasattr(stats, 'play_type'):
            print(f"  Play type: {stats.play_type}")
    
    # Final summary
    print(f"\n🏁 POSSESSION SUMMARY:")
    print(f"  Down: 4th & {scenario['yards_to_go']}")
    print(f"  Ball possession changes from {scenario['punting_team']} to {scenario['receiving_team']}")
    if play_result.is_turnover:
        print(f"  ⚠️ Classified as TURNOVER (abnormal punt outcome)")
    else:
        print(f"  ✅ Normal possession change (not a turnover)")
    print(f"  Next play: {scenario['receiving_team']} 1st & 10 at their {final_position}-yard line")


def main():
    """Run the simple punt demo"""
    try:
        # 1. Create punt scenario
        scenario = create_punt_scenario()
        
        # 2. Set up teams with rosters
        chiefs_roster, lions_roster, chiefs, lions = setup_teams()
        
        # 3. Create special teams play calls
        punt_play_call, punt_return_call = create_special_teams_play_calls()
        
        # 4. Set up personnel packages
        offensive_players, defensive_players = setup_personnel(
            chiefs_roster, lions_roster, punt_play_call, punt_return_call
        )
        
        # 5. Execute punt play
        play_result = execute_punt_play(
            offensive_players, defensive_players, punt_play_call, punt_return_call
        )
        
        # 6. Display comprehensive results
        display_punt_results(play_result, scenario)
        
        print("\n" + "=" * 50)
        print("🎉 PUNT DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("✅ Single punt play executed and analyzed")
        print("✅ PlayResult contains comprehensive punt data")
        print("✅ New SpecialTeamsPlayCall system demonstrated")
        
    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)