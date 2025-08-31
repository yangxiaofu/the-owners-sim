#!/usr/bin/env python3
import sys
import os
from typing import List, Tuple, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from game_engine import SimpleGameEngine, GameResult
from game_engine.data.loaders.team_loader import TeamLoader

class FootballSimTerminal:
    def __init__(self, data_source: str = "json"):
        """
        Initialize football simulation terminal.
        
        Args:
            data_source: Data source type ("json", "database", "mock")
        """
        # Configure data source
        if data_source == "json":
            config = {
                "base_path": "src/game_engine/data/sample_data"
            }
        else:
            config = {}
        
        # Initialize game engine with new loader system
        self.engine = SimpleGameEngine(data_source=data_source, **config)
        
        # Load teams using the new loader system
        try:
            self.team_loader = TeamLoader(data_source, **config)
            self.teams = self.load_teams_from_loader()
        except Exception as e:
            print(f"Warning: Could not load teams from {data_source}, using fallback: {e}")
            self.teams = self.create_sample_teams()
    
    def load_teams_from_loader(self) -> List[Tuple[int, str, str]]:
        """Load teams using the new loader system."""
        teams_dict = self.team_loader.get_all()
        teams_list = []
        
        for team in teams_dict.values():
            teams_list.append((team.id, team.name, team.city))
        
        # Sort by team ID for consistent ordering
        teams_list.sort(key=lambda t: t[0])
        return teams_list
    
    def create_sample_teams(self) -> List[Tuple[int, str, str]]:
        """Fallback method for creating sample teams."""
        return [
            (1, "Bears", "Chicago"),
            (2, "Packers", "Green Bay"),
            (3, "Lions", "Detroit"),
            (4, "Vikings", "Minneapolis"),
            (5, "Cowboys", "Dallas"),
            (6, "Eagles", "Philadelphia"),
            (7, "Giants", "New York"),
            (8, "Commanders", "Washington")
        ]
        
    def get_teams(self) -> List[Tuple[int, str, str]]:
        return self.teams
    
    def display_teams(self, teams: List[Tuple[int, str, str]]):
        print("\nAvailable Teams:")
        print("-" * 40)
        for i, (team_id, name, city) in enumerate(teams, 1):
            print(f"{i:2d}. {city} {name}")
        print("-" * 40)
    
    def select_team(self, teams: List[Tuple[int, str, str]], prompt: str) -> Optional[int]:
        while True:
            try:
                choice = input(prompt).strip()
                if choice.lower() in ['q', 'quit', 'exit']:
                    return None
                
                team_num = int(choice)
                if 1 <= team_num <= len(teams):
                    return teams[team_num - 1][0]  # Return team_id
                else:
                    print(f"Please enter a number between 1 and {len(teams)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                return None
    
    def get_team_name(self, team_id: int) -> str:
        for tid, name, city in self.teams:
            if tid == team_id:
                return f"{city} {name}"
        return f"Team {team_id}"
    
    def simulate_game_interactive(self):
        teams = self.get_teams()
        if not teams:
            print("No teams found in database!")
            return
        
        print("\n" + "="*50)
        print("           SIMULATE FOOTBALL GAME")
        print("="*50)
        
        self.display_teams(teams)
        
        home_team_id = self.select_team(teams, "\nSelect HOME team (number or 'q' to quit): ")
        if home_team_id is None:
            return
        
        away_team_id = self.select_team(teams, "Select AWAY team (number or 'q' to quit): ")
        if away_team_id is None:
            return
        
        if home_team_id == away_team_id:
            print("Teams cannot play themselves! Please select different teams.")
            return
        
        home_name = self.get_team_name(home_team_id)
        away_name = self.get_team_name(away_team_id)
        
        print(f"\n🏈 Simulating game: {away_name} @ {home_name}")
        print("⏳ Running simulation...")
        
        result = self.engine.simulate_game(home_team_id, away_team_id)
        
        print("\n" + "="*50)
        print("              FINAL SCORE")
        print("="*50)
        print(f"{away_name:25} {result.away_score:3d}")
        print(f"{home_name:25} {result.home_score:3d}")
        print("-" * 50)
        
        if result.winner_id:
            winner_name = self.get_team_name(result.winner_id)
            print(f"🏆 WINNER: {winner_name}")
        else:
            print("🤝 TIE GAME")
    
    def view_recent_games(self):
        print("\nGame history feature not available in this version.")
    
    def main_menu(self):
        while True:
            print("\n" + "="*50)
            print("        FOOTBALL OWNER SIMULATION")
            print("="*50)
            print("1. Simulate Game")
            print("2. Exit")
            print("-" * 50)
            
            try:
                choice = input("Select option (1-2): ").strip()
                
                if choice == "1":
                    self.simulate_game_interactive()
                elif choice == "2":
                    print("\nThanks for playing! 🏈")
                    break
                else:
                    print("Please enter 1 or 2")
                    
            except KeyboardInterrupt:
                print("\n\nThanks for playing! 🏈")
                break
            except Exception as e:
                print(f"An error occurred: {e}")

if __name__ == "__main__":
    import sys
    
    # Allow user to specify data source via command line
    data_source = "json"  # Default to JSON
    if len(sys.argv) > 1:
        data_source = sys.argv[1]
    
    print(f"🏈 Starting Football Owner Simulation with {data_source} data source")
    
    try:
        app = FootballSimTerminal(data_source=data_source)
        app.main_menu()
    except Exception as e:
        print(f"❌ Error initializing simulation: {e}")
        print("💡 Trying fallback with mock data...")
        try:
            app = FootballSimTerminal(data_source="mock")
            app.main_menu()
        except Exception as fallback_error:
            print(f"❌ Fallback failed: {fallback_error}")
            print("Please check your data source configuration.")