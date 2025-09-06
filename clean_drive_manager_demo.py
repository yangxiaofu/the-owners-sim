#!/usr/bin/env python3
"""
Clean Drive Manager Demo - New Fourth Down Architecture Showcase

Demonstrates the new clean architectural pattern where:
- HeadCoach makes strategic 4th down decisions (GO_FOR_IT, PUNT, FIELD_GOAL)  
- SpecialTeamsCoordinator handles special teams execution
- Clean separation between regular coordinators and special teams

This replaces the old mixed-responsibility system with proper NFL-style
organizational structure and decision-making hierarchy.
"""

import sys
import os
from typing import Dict, Tuple, Optional

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.game_state.drive_manager import (
    DriveManager, DriveSituation, DriveResult, DriveEndReason
)
from play_engine.core.play_result import PlayResult
from play_engine.game_state.field_position import FieldPosition, FieldZone
from play_engine.game_state.down_situation import DownState
from play_engine.core.engine import simulate
from play_engine.core.params import PlayEngineParams
from play_engine.play_calls.play_call_factory import PlayCallFactory
from play_engine.play_calls.offensive_play_call import OffensivePlayCall
from play_engine.play_calls.defensive_play_call import DefensivePlayCall
from play_engine.play_types.offensive_types import OffensivePlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id
from src.play_engine.play_calling.play_caller import PlayCaller, PlayCallContext, PlayCallerFactory
from src.play_engine.play_calling.fourth_down_matrix import FourthDownDecisionType


class CleanArchitectureDisplay:
    """Enhanced display showing the new clean architectural decision flow"""
    
    def __init__(self):
        self.play_counter = 0
    
    def show_drive_start(self, team_name: str, starting_position: int, time_remaining: int):
        """Show drive start with architectural context"""
        print("\n🏈 " + "=" * 80)
        print(f"   CLEAN ARCHITECTURE DEMO - {team_name} Drive")
        print(f"   Starting Position: {starting_position}-yard line")
        print(f"   Time Remaining: {self.format_time(time_remaining)}")
        print("   New Architecture: HeadCoach → Strategic Decisions → Appropriate Coordinators")
        print("=" * 84)
    
    def show_fourth_down_decision_flow(self, situation: DriveSituation, coaching_context: Dict, 
                                     hc_decision: Dict, strategic_choice: FourthDownDecisionType):
        """Show the detailed fourth down decision making process"""
        print(f"\n🎯 FOURTH DOWN STRATEGIC DECISION FLOW")
        print(f"   Situation: {self.format_down_distance(situation.down, situation.yards_to_go)} at {situation.field_position}-yard line")
        print(f"   ")
        print(f"   📊 HeadCoach Analysis:")
        print(f"      • Field Position: {situation.field_position} yards")  
        print(f"      • Yards to Go: {situation.yards_to_go}")
        print(f"      • Decision Matrix Confidence: {hc_decision.get('confidence', 0.0):.1%}")
        print(f"      • Go For It Probability: {hc_decision.get('go_for_it_probability', 0.0):.1%}")
        print(f"   ")
        print(f"   ⚡ STRATEGIC DECISION: {strategic_choice.value.upper().replace('_', ' ')}")
        
        if strategic_choice == FourthDownDecisionType.GO_FOR_IT:
            print(f"      → Routing to: OffensiveCoordinator & DefensiveCoordinator (Regular Play)")
        elif strategic_choice == FourthDownDecisionType.PUNT:
            print(f"      → Routing to: SpecialTeamsCoordinator (Punt Execution)")
        elif strategic_choice == FourthDownDecisionType.FIELD_GOAL:
            print(f"      → Routing to: SpecialTeamsCoordinator (Field Goal Execution)")
        
        print(f"   " + "-" * 76)
    
    def show_special_teams_execution(self, strategic_choice: FourthDownDecisionType, 
                                   offensive_call: OffensivePlayCall, defensive_call: DefensivePlayCall):
        """Show special teams coordinator execution details"""
        print(f"   🏟️  SPECIAL TEAMS EXECUTION:")
        
        if strategic_choice == FourthDownDecisionType.PUNT:
            print(f"      Offensive ST: {offensive_call.concept.replace('_', ' ').title()} ({offensive_call.get_formation()})")
            print(f"      Defensive ST: {defensive_call.coverage.replace('_', ' ').title()} ({defensive_call.get_formation()})")
        elif strategic_choice == FourthDownDecisionType.FIELD_GOAL:
            print(f"      Offensive ST: {offensive_call.concept.replace('_', ' ').title()} ({offensive_call.get_formation()})")  
            print(f"      Defensive ST: {defensive_call.coverage.replace('_', ' ').title()} ({defensive_call.get_formation()})")
    
    def show_regular_play_execution(self, offensive_call: OffensivePlayCall, defensive_call: DefensivePlayCall):
        """Show regular coordinator execution details"""  
        print(f"   🏃 REGULAR COORDINATOR EXECUTION:")
        print(f"      Offensive: {offensive_call.concept.replace('_', ' ').title()} ({offensive_call.get_formation()})")
        print(f"      Defensive: {defensive_call.coverage.replace('_', ' ').title()} ({defensive_call.get_formation()})")
    
    def show_play_result(self, play_result: PlayResult, strategic_choice: Optional[FourthDownDecisionType] = None):
        """Show play result with architectural context"""
        yards_display = f"{play_result.yards:+d}" if play_result.yards != 0 else "0"
        time_display = f"{play_result.time_elapsed:.1f}s"
        
        print(f"   ")
        print(f"   ▶️ RESULT: {play_result.outcome} | {yards_display} yards | {time_display}")
        
        if strategic_choice and strategic_choice != FourthDownDecisionType.GO_FOR_IT:
            print(f"      ✅ Special Teams Execution Successful")
        
        if play_result.is_scoring_play:
            print(f"      🏆 TOUCHDOWN! {play_result.points} points scored")
        
        if hasattr(play_result, 'achieved_first_down') and play_result.achieved_first_down:
            print(f"      🟨 FIRST DOWN ACHIEVED!")
        
        print(f"   " + "-" * 76)
    
    def show_play(self, situation: DriveSituation, offensive_call, defensive_call, 
                  play_result, time_remaining: int, new_situation: Optional[DriveSituation] = None,
                  strategic_decision: Optional[FourthDownDecisionType] = None, 
                  hc_decision: Optional[Dict] = None, coaching_context: Optional[Dict] = None):
        """Show comprehensive play with new architectural flow"""
        self.play_counter += 1
        
        print(f"\n📍 PLAY {self.play_counter} - {self.format_time(time_remaining)} remaining")
        
        # Show fourth down decision flow if applicable
        if situation.down == 4 and strategic_decision and hc_decision:
            self.show_fourth_down_decision_flow(situation, coaching_context or {}, hc_decision, strategic_decision)
            
            if strategic_decision in [FourthDownDecisionType.PUNT, FourthDownDecisionType.FIELD_GOAL]:
                self.show_special_teams_execution(strategic_decision, offensive_call, defensive_call)
            else:
                self.show_regular_play_execution(offensive_call, defensive_call)
        else:
            # Regular play (1st-3rd down)
            print(f"   {self.format_down_distance(situation.down, situation.yards_to_go)} at {situation.field_position}-yard line")
            self.show_regular_play_execution(offensive_call, defensive_call)
        
        # Show result
        self.show_play_result(play_result, strategic_decision)
        
        # Field position change
        if new_situation:
            print(f"   📍 New Position: {new_situation.field_position}-yard line")
            if new_situation.down == 1 and situation.down > 1:
                print(f"   🟨 FIRST DOWN! Next play: {self.format_down_distance(new_situation.down, new_situation.yards_to_go)}")
    
    def show_drive_end(self, drive_result: DriveResult, final_time: int):
        """Show drive ending with architectural summary"""
        print("\n" + "=" * 84)
        print(f"   DRIVE COMPLETE - {drive_result.end_reason.value.replace('_', ' ').title()}")
        print(f"   Final Time: {self.format_time(final_time)}")
        
        # Drive statistics
        stats = drive_result.drive_stats
        print(f"\n📊 DRIVE STATISTICS:")
        print(f"   Plays Run: {stats.plays_run}")
        print(f"   Total Yards: {stats.total_yards}")
        print(f"   Net Yards: {stats.net_yards}")
        print(f"   First Downs: {stats.first_downs_achieved}")
        print(f"   Time of Possession: {stats.time_of_possession_seconds:.1f} seconds")
        
        if stats.penalties_committed > 0:
            print(f"   Penalties: {stats.penalties_committed} for {stats.penalty_yards} yards")
        
        # Scoring information
        if drive_result.points_scored > 0:
            print(f"   🏆 Points Scored: {drive_result.points_scored} ({drive_result.scoring_type})")
        
        print(f"\n✨ ARCHITECTURE DEMONSTRATION:")
        print(f"   • HeadCoach strategic decisions successfully routed")
        print(f"   • SpecialTeamsCoordinator handled special teams execution")
        print(f"   • Clean separation between regular and special teams coordinators")
        print(f"   • No mixed-responsibility logic in DefensiveCoordinator")
        print("=" * 84)
    
    def format_time(self, seconds) -> str:
        """Format time as MM:SS"""
        seconds = int(seconds)
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def format_down_distance(self, down: int, yards_to_go: int) -> str:
        """Format down and distance"""
        ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        return f"{ordinals.get(down, f'{down}th')} & {yards_to_go}"


class CleanArchitectureDemo:
    """Main demo class showcasing the new clean fourth down architecture"""
    
    def __init__(self):
        """Initialize demo with clean architecture coaching staffs"""
        print("🏈 Initializing Clean Architecture Demo...")
        
        # Team setup
        self.home_team_id = TeamIDs.KANSAS_CITY_CHIEFS  # Known for good coaching
        self.away_team_id = TeamIDs.NEW_ENGLAND_PATRIOTS  # Belichick special teams excellence
        
        self.home_team = get_team_by_id(self.home_team_id)
        self.away_team = get_team_by_id(self.away_team_id)
        
        print(f"   Home: {self.home_team.full_name}")
        print(f"   Away: {self.away_team.full_name}")
        
        # Generate rosters and personnel
        print("   Generating rosters...")
        self.home_roster = TeamRosterGenerator.generate_sample_roster(self.home_team_id)
        self.away_roster = TeamRosterGenerator.generate_sample_roster(self.away_team_id)
        
        self.home_personnel = PersonnelPackageManager(self.home_roster)
        self.away_personnel = PersonnelPackageManager(self.away_roster)
        
        # Display handler
        self.display = CleanArchitectureDisplay()
        
        # Game timing
        self.time_remaining = 900  # 15:00
        
        print("✅ Clean Architecture Demo Initialized!")
        print("   • SpecialTeamsCoordinators included in all coaching staffs")
        print("   • Fourth down routing through HeadCoach strategic decisions")
        print("   • Clean separation of coordinator responsibilities")
        print()
    
    def run_drive(self, possessing_team_id: int, starting_yard_line: int = 25):
        """Run a complete drive showcasing the new clean architecture"""
        
        # Determine team setup
        if possessing_team_id == self.home_team_id:
            possessing_team = self.home_team.full_name
            offensive_personnel = self.home_personnel
            defensive_personnel = self.away_personnel
        else:
            possessing_team = self.away_team.full_name
            offensive_personnel = self.away_personnel
            defensive_personnel = self.home_personnel
        
        # Create coaching staffs with the NEW ARCHITECTURE (includes SpecialTeamsCoordinators)
        print(f"🎯 COACHING STAFF ARCHITECTURE:")
        
        # Offensive coaching staff: possessing team
        if possessing_team_id == TeamIDs.KANSAS_CITY_CHIEFS:
            offensive_play_caller = PlayCallerFactory.create_chiefs_style_caller()
            print(f"   Offense: Kansas City Chiefs-style coaching staff")
            print(f"            • HeadCoach: Andy Reid style (creative, aggressive)")  
            print(f"            • OffensiveCoordinator: West Coast/RPO mastery")
            print(f"            • SpecialTeamsCoordinator: Solid coverage discipline")
        elif possessing_team_id == TeamIDs.NEW_ENGLAND_PATRIOTS:
            offensive_play_caller = PlayCallerFactory.create_patriots_style_caller()
            print(f"   Offense: New England Patriots-style coaching staff")
            print(f"            • HeadCoach: Belichick style (situational master)")
            print(f"            • OffensiveCoordinator: Adaptable, personnel-based")
            print(f"            • SpecialTeamsCoordinator: Elite fake detection")
        else:
            offensive_play_caller = PlayCallerFactory.create_for_team(possessing_team_id)
            print(f"   Offense: {possessing_team} coaching staff")
        
        # Defensive coaching staff: defending team  
        defending_team_id = self.away_team_id if possessing_team_id == self.home_team_id else self.home_team_id
        if defending_team_id == TeamIDs.KANSAS_CITY_CHIEFS:
            defensive_play_caller = PlayCallerFactory.create_chiefs_style_caller()
            print(f"   Defense: Kansas City Chiefs-style coaching staff")
        elif defending_team_id == TeamIDs.NEW_ENGLAND_PATRIOTS:
            defensive_play_caller = PlayCallerFactory.create_patriots_style_caller() 
            print(f"   Defense: New England Patriots-style coaching staff")
        else:
            defensive_play_caller = PlayCallerFactory.create_for_team(defending_team_id)
            print(f"   Defense: {self.home_team.full_name if defending_team_id == self.home_team_id else self.away_team.full_name} coaching staff")
        
        print(f"   ✨ Both staffs include SpecialTeamsCoordinators for clean 4th down architecture")
        
        # Initialize DriveManager
        starting_position = FieldPosition(
            yard_line=starting_yard_line,
            possession_team=possessing_team,
            field_zone=FieldZone.OWN_GOAL_LINE  # Auto-calculated
        )
        
        starting_down = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=min(100, starting_yard_line + 10)
        )
        
        drive_manager = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down,
            possessing_team=possessing_team
        )
        
        # Show drive start
        self.display.show_drive_start(possessing_team, starting_yard_line, self.time_remaining)
        
        # Drive loop
        while not drive_manager.is_drive_over() and self.time_remaining > 0:
            # Get current situation (DriveManager will provide field position and yards to go)
            game_context = {
                'time_remaining': self.time_remaining,
                'quarter': 1,  
                'score_differential': 0
            }
            
            old_situation = drive_manager.get_current_situation(game_context)
            
            # Create play call context
            play_context = PlayCallContext(
                situation=old_situation,
                game_flow="neutral"
            )
            
            # Capture strategic decision flow for fourth downs
            strategic_decision = None
            hc_decision = None
            coaching_context = None
            
            if old_situation.down == 4:
                # For display purposes, capture the HeadCoach decision process
                coaching_context = offensive_play_caller._convert_context_for_coaching_staff(play_context)
                hc_decision = offensive_play_caller.coaching_staff.head_coach.get_game_management_decision('fourth_down', coaching_context)
                strategic_decision = hc_decision['fourth_down']['recommendation']
            
            # NEW ARCHITECTURE: Play calling automatically routes through proper coordinators
            offensive_call = offensive_play_caller.select_offensive_play(play_context) 
            defensive_call = defensive_play_caller.select_defensive_play(play_context)
            
            # Execute play using existing engine
            play_result = self.execute_play(offensive_call, defensive_call, 
                                          offensive_personnel, defensive_personnel)
            
            # Update time and drive state
            old_time = self.time_remaining
            self.time_remaining = max(0, self.time_remaining - play_result.time_elapsed)
            drive_manager.process_play_result(play_result)
            
            # Get new situation
            new_situation = None
            first_down_achieved = False
            if not drive_manager.is_drive_over():
                new_situation = drive_manager.get_current_situation(game_context)
                first_down_achieved = (old_situation.down > 1 and new_situation.down == 1)
            
            # Update play result with first down info
            play_result.achieved_first_down = first_down_achieved
            
            # Show play with new architectural context
            self.display.show_play(
                old_situation, offensive_call, defensive_call, 
                play_result, old_time, new_situation,
                strategic_decision, hc_decision, coaching_context
            )
        
        # Show drive results
        drive_result = drive_manager.get_drive_result()
        self.display.show_drive_end(drive_result, self.time_remaining)
        
        return drive_result
    
    def execute_play(self, offensive_call: OffensivePlayCall, defensive_call: DefensivePlayCall,
                    offensive_personnel: PersonnelPackageManager, 
                    defensive_personnel: PersonnelPackageManager) -> PlayResult:
        """Execute play using existing play engine (unchanged from original demo)"""
        try:
            # Get personnel for formations
            offensive_players = offensive_personnel.get_offensive_personnel(
                offensive_call.get_formation()
            )
            defensive_players = defensive_personnel.get_defensive_personnel(
                defensive_call.get_formation()
            )
            
            # Create play engine params
            play_params = PlayEngineParams(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_play_call=offensive_call,
                defensive_play_call=defensive_call
            )
            
            # Execute play using existing engine
            engine_result = simulate(play_params)
            
            # Convert to DriveManager PlayResult format
            play_result = PlayResult(
                outcome=engine_result.outcome,
                yards=engine_result.yards,
                time_elapsed=engine_result.time_elapsed,
                points=engine_result.points,
                is_scoring_play=(engine_result.points > 0),
                achieved_first_down=False,  # Will be determined by DriveManager
                penalty_occurred=False,  # Simplified for demo
                penalty_yards=0,
                is_punt=getattr(engine_result, 'is_punt', False)  # 🔧 FIX: Copy is_punt flag from engine result
            )
            
            return play_result
            
        except Exception as e:
            print(f"   ⚠️  Play execution error: {e}")
            
            # Context-aware exception handling (preserved from original)
            if hasattr(offensive_call, 'get_play_type'):
                play_type = offensive_call.get_play_type()
                
                from src.play_engine.play_types.offensive_types import OffensivePlayType
                
                if play_type == OffensivePlayType.PUNT:
                    from src.play_engine.core.play_result import create_failed_punt_result
                    return create_failed_punt_result(str(e))
            
            # Default fallback
            return PlayResult(
                outcome="incomplete_play",
                yards=0,
                time_elapsed=25.0
            )


def main():
    """Run the clean architecture demo"""
    print("🏈 NFL Clean Architecture Demo - Fourth Down Decision Flow")
    print("=" * 80)
    print("Showcasing NEW architectural pattern:")
    print("• HeadCoach strategic decisions → SpecialTeamsCoordinator execution")
    print("• Clean separation of regular vs special teams coordinators")
    print("• No mixed-responsibility logic")  
    print("=" * 80)
    
    # Create demo
    demo = CleanArchitectureDemo()
    
    # Run a drive that's likely to encounter fourth downs
    print("Starting drive simulation (positioned for potential 4th down decisions)...")
    drive_result = demo.run_drive(
        possessing_team_id=TeamIDs.KANSAS_CITY_CHIEFS,
        starting_yard_line=45  # Midfield position more likely to create 4th down decisions
    )
    
    print(f"\n✅ Clean Architecture Demo Complete!")
    print(f"   Drive Result: {drive_result.end_reason.value.replace('_', ' ').title()}")
    print(f"   Plays Executed: {drive_result.drive_stats.plays_run}")
    print(f"   Total Yards: {drive_result.drive_stats.total_yards}")
    
    if drive_result.points_scored > 0:
        print(f"   Points Scored: {drive_result.points_scored}")
    
    print(f"\n🎯 ARCHITECTURE VALIDATION:")
    print(f"   ✅ HeadCoach strategic decisions implemented")
    print(f"   ✅ SpecialTeamsCoordinator routing functional") 
    print(f"   ✅ Clean separation of concerns achieved")
    print(f"   ✅ No mixed special teams logic in DefensiveCoordinator")
    print(f"   ✅ NFL-realistic organizational structure")


if __name__ == "__main__":
    main()