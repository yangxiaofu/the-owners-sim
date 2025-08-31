#!/usr/bin/env python3
"""
Interactive Play Execution Test Script

Tests the restructured play execution system to ensure all components work correctly.
Allows testing individual plays with different game situations and team matchups.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.core.play_executor import PlayExecutor
from game_engine.core.game_orchestrator import SimpleGameEngine
from game_engine.field.game_state import GameState
from game_engine.plays.play_factory import PlayFactory
from game_engine.personnel.player_selector import PlayerSelector


class PlayTestRunner:
    """Interactive test runner for play execution"""
    
    def __init__(self):
        self.engine = SimpleGameEngine()
        self.play_executor = PlayExecutor()
        self.game_state = GameState()
        
        # Setup default game state
        self._setup_default_game_state()
        
        print("🏈 Football Play Execution Test System")
        print("=" * 50)
        
    def _setup_default_game_state(self):
        """Setup a default game situation for testing"""
        # Default: 1st & 10 from own 25-yard line, 1st quarter
        self.game_state.field.down = 1
        self.game_state.field.yards_to_go = 10
        self.game_state.field.field_position = 25
        self.game_state.field.possession_team_id = 1  # Bears have possession
        
        self.game_state.clock.quarter = 1
        self.game_state.clock.clock = 900  # 15:00 remaining
        
        self.game_state.scoreboard.home_team_id = 1
        self.game_state.scoreboard.away_team_id = 2
        self.game_state.scoreboard.home_score = 0
        self.game_state.scoreboard.away_score = 0
    
    def display_teams(self):
        """Display available teams"""
        print("\n📋 Available Teams:")
        print("-" * 30)
        for team_id, team_data in self.engine.teams_data.items():
            print(f"{team_id}: {team_data['city']} {team_data['name']} (Overall: {team_data['overall_rating']})")
            print(f"   Offense: QB({team_data['offense']['qb_rating']}) RB({team_data['offense']['rb_rating']}) WR({team_data['offense']['wr_rating']}) OL({team_data['offense']['ol_rating']})")
            print(f"   Defense: DL({team_data['defense']['dl_rating']}) LB({team_data['defense']['lb_rating']}) DB({team_data['defense']['db_rating']})")
    
    def display_current_situation(self):
        """Display the current game situation"""
        offense_team = self.engine.get_team_for_simulation(self.game_state.field.possession_team_id)
        defense_team_id = 2 if self.game_state.field.possession_team_id == 1 else 1
        defense_team = self.engine.get_team_for_simulation(defense_team_id)
        
        print(f"\n🎯 Current Game Situation:")
        print("-" * 35)
        print(f"Quarter: {self.game_state.clock.quarter}")
        print(f"Time: {self.game_state.clock.get_time_remaining_text()}")
        print(f"Score: {self.game_state.scoreboard.home_score} - {self.game_state.scoreboard.away_score}")
        print(f"Down: {self.game_state.field.down}")
        print(f"Distance: {self.game_state.field.yards_to_go}")
        print(f"Field Position: {self.game_state.field.get_field_position_text()}")
        print(f"Possession: {offense_team['city']} {offense_team['name']}")
        print(f"Defense: {defense_team['city']} {defense_team['name']}")
        
        # Show situational context
        if self.game_state.field.is_goal_line():
            print("🔥 RED ZONE SITUATION!")
        elif self.game_state.field.is_short_yardage():
            print("💪 SHORT YARDAGE SITUATION!")
        elif self.game_state.field.yards_to_go >= 10:
            print("🎯 LONG DISTANCE SITUATION!")
    
    def display_play_result(self, play_result):
        """Display detailed play result information"""
        print(f"\n🏈 Play Result:")
        print("-" * 25)
        print(f"Play Type: {play_result.play_type.upper()}")
        print(f"Formation: {play_result.formation}")
        print(f"Defense: {play_result.defensive_call}")
        print(f"Outcome: {play_result.outcome}")
        print(f"Yards Gained: {play_result.yards_gained}")
        print(f"Time Elapsed: {play_result.time_elapsed} seconds")
        
        print(f"\n📊 Play Summary: {play_result.get_summary()}")
        
        # Special situations
        if play_result.is_score:
            print(f"🎉 SCORE! +{play_result.score_points} points")
        if play_result.is_turnover:
            print(f"😱 TURNOVER!")
        if play_result.big_play:
            print(f"💥 BIG PLAY! (20+ yards)")
        if play_result.goal_line_play:
            print(f"🔥 Goal line play")
        
        print(f"\n🕐 Context:")
        print(f"   Situation: {play_result.down}&{play_result.distance}")
        print(f"   Field Position: {play_result.field_position}")
        print(f"   Quarter: {play_result.quarter}")
        print(f"   Game Clock: {play_result.game_clock} seconds")
    
    def setup_custom_situation(self):
        """Allow user to customize the game situation"""
        print("\n⚙️ Custom Game Situation Setup")
        print("-" * 35)
        
        try:
            # Down and distance
            down = input(f"Down (1-4) [current: {self.game_state.field.down}]: ").strip()
            if down:
                self.game_state.field.down = int(down)
            
            distance = input(f"Distance (1-99) [current: {self.game_state.field.yards_to_go}]: ").strip()
            if distance:
                self.game_state.field.yards_to_go = int(distance)
            
            # Field position
            field_pos = input(f"Field Position (1-99) [current: {self.game_state.field.field_position}]: ").strip()
            if field_pos:
                self.game_state.field.field_position = int(field_pos)
            
            # Teams
            offense_team = input(f"Offensive Team ID (1-8) [current: {self.game_state.field.possession_team_id}]: ").strip()
            if offense_team:
                self.game_state.field.possession_team_id = int(offense_team)
            
            # Quarter and time
            quarter = input(f"Quarter (1-4) [current: {self.game_state.clock.quarter}]: ").strip()
            if quarter:
                self.game_state.clock.quarter = int(quarter)
            
            time_remaining = input(f"Time Remaining (0-900 seconds) [current: {self.game_state.clock.clock}]: ").strip()
            if time_remaining:
                self.game_state.clock.clock = int(time_remaining)
            
            print("✅ Game situation updated!")
            
        except ValueError:
            print("❌ Invalid input. Please enter numbers only.")
    
    def execute_single_play(self):
        """Execute a single play and display results"""
        offense_team_id = self.game_state.field.possession_team_id
        defense_team_id = 2 if offense_team_id == 1 else 1
        
        offense_team = self.engine.get_team_for_simulation(offense_team_id)
        defense_team = self.engine.get_team_for_simulation(defense_team_id)
        
        # Execute the play
        play_result = self.play_executor.execute_play(offense_team, defense_team, self.game_state)
        
        # Display results
        self.display_play_result(play_result)
        
        # Update game state (basic version)
        field_result = self.game_state.update_after_play(play_result)
        
        if field_result == "touchdown":
            print("\n🏆 TOUCHDOWN SCORED!")
        elif field_result == "safety":
            print("\n🛡️ SAFETY SCORED!")
        
        return play_result
    
    def execute_multiple_plays(self, count=5):
        """Execute multiple plays in sequence"""
        print(f"\n🔄 Executing {count} consecutive plays...")
        print("=" * 40)
        
        for i in range(count):
            print(f"\n--- Play #{i+1} ---")
            self.display_current_situation()
            
            play_result = self.execute_single_play()
            
            # Check for game-changing events
            if play_result.is_score or play_result.is_turnover:
                print(f"\n🚨 Game-changing play! Stopping sequence.")
                break
                
            if self.game_state.field.down > 4:
                print(f"\n🔄 Turnover on downs!")
                self.game_state.field.possession_team_id = 2 if self.game_state.field.possession_team_id == 1 else 1
                self.game_state.field.down = 1
                self.game_state.field.yards_to_go = 10
            
            input("\nPress Enter to continue to next play...")
    
    def test_specific_play_type(self):
        """Test a specific play type"""
        play_types = PlayFactory.get_supported_play_types()
        
        print(f"\n🎯 Available Play Types:")
        for i, play_type in enumerate(play_types, 1):
            print(f"{i}: {play_type}")
        
        try:
            choice = int(input("\nSelect play type (number): ")) - 1
            if 0 <= choice < len(play_types):
                selected_play_type = play_types[choice]
                
                # Force the play type by temporarily modifying the executor
                original_method = self.play_executor._determine_play_type
                self.play_executor._determine_play_type = lambda field_state: selected_play_type
                
                print(f"\n🏈 Forcing {selected_play_type.upper()} play...")
                self.execute_single_play()
                
                # Restore original method
                self.play_executor._determine_play_type = original_method
            else:
                print("❌ Invalid selection")
                
        except ValueError:
            print("❌ Invalid input")
    
    def run_interactive_menu(self):
        """Main interactive menu loop"""
        while True:
            print("\n" + "="*50)
            print("🏈 PLAY EXECUTION TEST MENU")
            print("="*50)
            print("1. View Current Game Situation")
            print("2. Execute Single Play")
            print("3. Execute Multiple Plays (5)")
            print("4. Test Specific Play Type")
            print("5. Setup Custom Game Situation")
            print("6. View Available Teams")
            print("7. Reset to Default Situation")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-7): ").strip()
            
            if choice == "0":
                print("👋 Thanks for testing! Goodbye!")
                break
            elif choice == "1":
                self.display_current_situation()
            elif choice == "2":
                self.display_current_situation()
                self.execute_single_play()
            elif choice == "3":
                self.execute_multiple_plays(5)
            elif choice == "4":
                self.test_specific_play_type()
            elif choice == "5":
                self.setup_custom_situation()
            elif choice == "6":
                self.display_teams()
            elif choice == "7":
                self._setup_default_game_state()
                print("✅ Reset to default game situation")
            else:
                print("❌ Invalid choice. Please try again.")
            
            if choice != "0":
                input("\nPress Enter to continue...")


def main():
    """Main function to run the test script"""
    try:
        test_runner = PlayTestRunner()
        test_runner.run_interactive_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Please check that all game engine components are properly installed.")


if __name__ == "__main__":
    main()