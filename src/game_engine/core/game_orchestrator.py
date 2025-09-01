import random
from typing import Optional, Dict, Any
from dataclasses import dataclass
from .play_executor import PlayExecutor
from ..field.game_state import GameState
from ..plays.data_structures import PlayResult
from ..data.loaders.team_loader import TeamLoader
from ..data.loaders.player_loader import PlayerLoader
from ..personnel.player_selector import PlayerSelector
from ..coaching import CoachingStaff

@dataclass
class GameResult:
    home_score: int
    away_score: int
    winner_id: Optional[int]
    home_team_id: int
    away_team_id: int
    play_count: int = 0
    play_type_counts: Dict[str, int] = None
    clock_stats: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize default values for tracking fields."""
        if self.play_type_counts is None:
            self.play_type_counts = {"run": 0, "pass": 0, "kick": 0, "punt": 0}
        if self.clock_stats is None:
            self.clock_stats = {"total_clock_used": 0.0, "avg_per_play": 0.0, "run_avg": 0.0, "pass_avg": 0.0, "special_avg": 0.0}

class SimpleGameEngine:
    def __init__(self, data_source: str = "json", **config):
        """
        Initialize the game engine with pluggable data loaders.
        
        Args:
            data_source: Type of data source ("json", "database", "mock")
            **config: Configuration passed to data loaders
        """
        # Initialize data loaders
        self.team_loader = TeamLoader(data_source, **config)
        self.player_loader = PlayerLoader(data_source, **config)
        
        # Initialize play executor
        self.play_executor = PlayExecutor()
        
        # Configure for individual players if supported
        if self.player_loader.data_source.supports_entity_type("players"):
            player_selector = PlayerSelector(use_individual_players=True)
            self.play_executor.player_selector = player_selector
        
        # Initialize coaching staff for all teams
        self._initialize_coaching_staffs()
    
    def _initialize_coaching_staffs(self):
        """Initialize CoachingStaff instances for all teams from JSON data."""
        # CoachingStaff instances are now created on-demand in _convert_team_to_legacy_format
        # using data directly from teams.json - no hardcoded configurations needed
        pass
    
    def _convert_team_to_legacy_format(self, team) -> Dict[str, Any]:
        """Convert new Team object to legacy format for backward compatibility."""
        team_data = {
            "team_id": team.id,  # Include team_id for score differential calculation
            "name": team.name,
            "city": team.city,
            "offense": team.ratings.get("offense", {}),
            "defense": team.ratings.get("defense", {}),
            "special_teams": team.ratings.get("special_teams", 50),
            "coaching": team.ratings.get("coaching", {}),
            "overall_rating": team.ratings.get("overall_rating", 50),
            "team_philosophy": getattr(team, 'team_philosophy', 'balanced_approach')
        }
        
        # Add coaching staff integration for enhanced play calling
        if hasattr(team, 'team_philosophy'):
            
            # Extract coordinator data from team ratings
            coaching = team.ratings.get("coaching", {})
            offensive_coord = coaching.get("offensive_coordinator", {})
            defensive_coord = coaching.get("defensive_coordinator", {})
            
            coaching_config = {
                "offensive_coordinator_archetype": offensive_coord.get("archetype", "balanced_attack"),
                "defensive_coordinator_archetype": defensive_coord.get("archetype", "multiple_defense"),
                "offensive_coordinator_personality": offensive_coord.get("personality", "balanced"),
                "defensive_coordinator_personality": defensive_coord.get("personality", "balanced"),
                "team_philosophy": team.team_philosophy,
                "custom_modifiers": {
                    "offensive": offensive_coord.get("custom_modifiers", {}),
                    "defensive": defensive_coord.get("custom_modifiers", {})
                }
            }
            
            # Create CoachingStaff instance for this team
            coaching_staff = CoachingStaff(team_id=str(team.id), coaching_config=coaching_config)
            team_data["coaching_staff"] = coaching_staff
        
        return team_data
    
    def get_team_for_simulation(self, team_id: int) -> dict:
        """Get complete team data for simulation"""
        # Load team data from JSON using the loader system
        team = self.team_loader.get_by_id(team_id)
        if not team:
            raise ValueError(f"Team with ID {team_id} not found in team data. Check teams.json configuration.")
        
        return self._convert_team_to_legacy_format(team)
    
    def calculate_team_strength(self, team_id: int) -> float:
        """Calculate overall team strength for scoring"""
        team_data = self.get_team_for_simulation(team_id)
        return team_data.get("overall_rating", 50.0)
    
    def simulate_game(self, home_team_id: int, away_team_id: int) -> GameResult:
        # Get complete team data for simulation
        home_team = self.get_team_for_simulation(home_team_id)
        away_team = self.get_team_for_simulation(away_team_id)
        
        # Load team rosters if using individual players
        if hasattr(self.play_executor, 'player_selector') and self.play_executor.player_selector:
            try:
                home_roster = self.player_loader.get_team_roster(home_team_id)
                away_roster = self.player_loader.get_team_roster(away_team_id)
                
                self.play_executor.player_selector.set_team_rosters({
                    home_team_id: home_roster,
                    away_team_id: away_roster
                })
            except Exception as e:
                print(f"Warning: Could not load individual players, using team ratings: {e}")
        
        # Initialize game state
        game_state = GameState()
        game_state.field.possession_team_id = home_team_id  # Home team starts with ball
        game_state.scoreboard.home_team_id = home_team_id
        game_state.scoreboard.away_team_id = away_team_id
        
        play_count = 0
        max_plays = 200  # Safety limit to prevent infinite loops
        
        # Initialize tracking variables
        play_type_counts = {"run": 0, "pass": 0, "kick": 0, "punt": 0}
        clock_usage_by_type = {"run": [], "pass": [], "kick": [], "punt": []}
        total_clock_used = 0.0
        
        # Main game loop - play by play until game ends
        while not game_state.is_game_over() and play_count < max_plays:
            # Determine which team has possession
            if game_state.field.possession_team_id == home_team_id:
                offense_team = home_team
                defense_team = away_team
            else:
                offense_team = away_team  
                defense_team = home_team
            
            # Execute the play using new architecture
            play_result = self.play_executor.execute_play(offense_team, defense_team, game_state)

            # Track clock usage for this play using PlayResult.time_elapsed
            clock_used_this_play = play_result.time_elapsed
            total_clock_used += clock_used_this_play
            
            # Track play type and clock usage
            play_type = play_result.play_type
            if play_type in play_type_counts:
                play_type_counts[play_type] += 1
                clock_usage_by_type[play_type].append(clock_used_this_play)
            else:
                # Handle special cases or default to "run"
                play_type_counts["run"] += 1
                clock_usage_by_type["run"].append(clock_used_this_play)
            
            # Update game state using the centralized method
            field_result = game_state.update_after_play(play_result)
            
            # Handle possession changes for scoring
            if play_result.is_score:
                # Execute kickoff after score
                scoring_team_id = game_state.field.possession_team_id
                receiving_team_id = away_team_id if scoring_team_id == home_team_id else home_team_id
                
                kickoff_result = self._simulate_kickoff(scoring_team_id, receiving_team_id)
                
                # Update field state after kickoff
                game_state.field.possession_team_id = receiving_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                game_state.field.field_position = kickoff_result.final_field_position
            
            # Handle turnovers
            elif play_result.is_turnover:
                # Switch possession
                game_state.field.possession_team_id = away_team_id if game_state.field.possession_team_id == home_team_id else home_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                # TODO: Set field position based on turnover location
                game_state.field.field_position = 50  # Simplified
            
            # Handle punts
            elif play_result.play_type == "punt":
                # Switch possession
                game_state.field.possession_team_id = away_team_id if game_state.field.possession_team_id == home_team_id else home_team_id  
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                # TODO: Calculate punt field position
                game_state.field.field_position = max(20, 100 - play_result.yards_gained)
            
            # Handle normal plays - check if it resulted in a score
            elif field_result == "touchdown":
                # Handle touchdown scored by normal play
                game_state.field.possession_team_id = away_team_id if game_state.field.possession_team_id == home_team_id else home_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10 
                game_state.field.field_position = 25
            
            # Check for turnover on downs
            elif game_state.field.down > 4:
                # Turnover on downs
                game_state.field.possession_team_id = away_team_id if game_state.field.possession_team_id == home_team_id else home_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                # Field position stays the same (simplified)
            
            # Check for end of quarter
            if game_state.clock.clock <= 0:
                game_state.clock.advance_quarter()
            
            play_count += 1
        
        # Determine winner
        winner_id = home_team_id if game_state.scoreboard.home_score > game_state.scoreboard.away_score else away_team_id if game_state.scoreboard.away_score > game_state.scoreboard.home_score else None
        
        # Calculate clock statistics
        avg_per_play = total_clock_used / play_count if play_count > 0 else 0.0
        run_avg = sum(clock_usage_by_type["run"]) / len(clock_usage_by_type["run"]) if clock_usage_by_type["run"] else 0.0
        pass_avg = sum(clock_usage_by_type["pass"]) / len(clock_usage_by_type["pass"]) if clock_usage_by_type["pass"] else 0.0
        special_avg = (sum(clock_usage_by_type["kick"]) + sum(clock_usage_by_type["punt"])) / (len(clock_usage_by_type["kick"]) + len(clock_usage_by_type["punt"])) if (clock_usage_by_type["kick"] or clock_usage_by_type["punt"]) else 0.0
        
        clock_stats = {
            "total_clock_used": total_clock_used,
            "avg_per_play": avg_per_play,
            "run_avg": run_avg,
            "pass_avg": pass_avg,
            "special_avg": special_avg
        }
        
        return GameResult(
            home_score=game_state.scoreboard.home_score,
            away_score=game_state.scoreboard.away_score,
            winner_id=winner_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            play_count=play_count,
            play_type_counts=play_type_counts.copy(),
            clock_stats=clock_stats
        )

    
    def _simulate_kickoff(self, kicking_team_id: int, receiving_team_id: int):
        """Simulate a kickoff play between two teams"""
        from ..plays.play_factory import PlayFactory
        from unittest.mock import Mock
        
        # Create kickoff play
        kickoff_play = PlayFactory.create_play("kickoff")
        
        # Get team data for kickoff simulation  
        kicking_team = self.get_team_for_simulation(kicking_team_id)
        receiving_team = self.get_team_for_simulation(receiving_team_id)
        
        # Create mock personnel package for kickoff
        personnel = Mock()
        personnel.special_teams_rating = kicking_team.get('special_teams', 70)
        personnel.kicker_on_field = None  # Use team ratings for now
        personnel.returner_on_field = None  # Use team ratings for now
        
        # Create simplified field state (kickoffs start from 35-yard line)
        field_state = Mock()
        field_state.down = 1
        field_state.yards_to_go = 10
        field_state.field_position = 35  # NFL kickoff position
        field_state.is_goal_line = lambda: False
        field_state.is_short_yardage = lambda: False
        
        # Simulate the kickoff
        return kickoff_play.simulate(personnel, field_state)