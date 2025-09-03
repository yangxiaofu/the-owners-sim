import random
from typing import Optional, Dict, Any
from dataclasses import dataclass
from game_engine.core.play_executor import PlayExecutor
from game_engine.core.game_state_manager import create_game_state_manager
from game_engine.field.game_state import GameState
from game_engine.plays.data_structures import PlayResult
from game_engine.data.loaders.team_loader import TeamLoader
from game_engine.data.loaders.player_loader import PlayerLoader
from game_engine.personnel.player_selector import PlayerSelector
from game_engine.coaching import CoachingStaff

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
    tracking_summary: Optional[Dict[str, Any]] = None
    
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
    
    def simulate_game(self, home_team_id: int, away_team_id: int, is_playoff_game: bool = False) -> GameResult:
        # Get complete team data for simulation
        home_team = self.get_team_for_simulation(home_team_id)
        away_team = self.get_team_for_simulation(away_team_id)
        
        # Load team rosters if using individual players
        if hasattr(self.play_executor, 'player_selector') and self.play_executor.player_selector:
            try:
                home_roster = self.player_loader.get_team_roster_by_position(home_team_id)
                away_roster = self.player_loader.get_team_roster_by_position(away_team_id)
                
                self.play_executor.player_selector.set_team_rosters({
                    home_team_id: home_roster,
                    away_team_id: away_roster
                })
            except Exception as e:
                print(f"Warning: Could not load individual players, using team ratings: {e}")
        
        # Initialize game state
        game_state = GameState(is_playoff_game)
        game_state.field.possession_team_id = home_team_id  # Home team starts with ball
        game_state.scoreboard.home_team_id = home_team_id
        game_state.scoreboard.away_team_id = away_team_id
        
        play_count = 0
        max_plays = 200  # Safety limit to prevent infinite loops
        
        # Initialize Game State Manager for clean state transitions
        game_state_manager = create_game_state_manager(
            game_id=f"game_{home_team_id}_{away_team_id}",
            home_team_id=str(home_team_id),
            away_team_id=str(away_team_id)
        )
        
        # Main game loop - Clean 4-step pattern replaces complex state management
        while not game_state.is_game_over() and play_count < max_plays:
            # Determine which team has possession
            if game_state.field.possession_team_id == home_team_id:
                offense_team = home_team
                defense_team = away_team
                possession_team_id = str(home_team_id)
            else:
                offense_team = away_team  
                defense_team = home_team
                possession_team_id = str(away_team_id)
            
            # Execute the play using existing play executor
            play_result = self.play_executor.execute_play(offense_team, defense_team, game_state)
            
            # Process play through Game State Manager (4-step pattern)
            # Step 1: Calculate → Step 2: Validate → Step 3: Apply → Step 4: Track
            transition_result = game_state_manager.process_play_result(
                play_result, game_state, possession_team_id
            )
            
            # Handle any state transition failures
            if not transition_result.success:
                print(f"⚠️ State transition failed: {transition_result.all_errors}")
                # Continue with fallback - original game_state unchanged
            
            play_count += 1
        
        # Determine winner
        winner_id = home_team_id if game_state.scoreboard.home_score > game_state.scoreboard.away_score else away_team_id if game_state.scoreboard.away_score > game_state.scoreboard.home_score else None
        
        # Get comprehensive statistics from Game State Manager tracking system
        comprehensive_stats = game_state_manager.get_game_statistics()
        clock_stats = comprehensive_stats.get('clock_management', {})
        
        # Get comprehensive tracking summary if available
        tracking_summary = game_state_manager.get_comprehensive_summary()
        
        # FINAL VALIDATION: Ensure no impossible scores before returning result
        game_state.scoreboard.fix_invalid_scores()
        if not game_state.scoreboard.validate_scores():
            print(f"🚨 WARNING: Game ended with invalid scores - this should not happen!")
        
        return GameResult(
            home_score=game_state.scoreboard.home_score,
            away_score=game_state.scoreboard.away_score,
            winner_id=winner_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            play_count=play_count,
            play_type_counts=comprehensive_stats.get('play_type_distribution', {}),
            clock_stats=clock_stats,
            tracking_summary=tracking_summary
        )

    
    def _simulate_kickoff(self, kicking_team_id: int, receiving_team_id: int):
        """Simulate a kickoff play between two teams"""
        from game_engine.plays.play_factory import PlayFactory
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