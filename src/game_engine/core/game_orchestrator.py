import random
from typing import Optional
from dataclasses import dataclass
from .play_executor import PlayExecutor
from ..field.game_state import GameState
from ..plays.data_structures import PlayResult

@dataclass
class GameResult:
    home_score: int
    away_score: int
    winner_id: Optional[int]
    home_team_id: int
    away_team_id: int

class SimpleGameEngine:
    def __init__(self):
        # TODO: Replace data with data from the database.  Fix at a later stage.
        # Comprehensive team data structure
        self.teams_data = {
            1: {  # Bears
                "name": "Bears", "city": "Chicago",
                "offense": {"qb_rating": 68, "rb_rating": 75, "wr_rating": 62, "ol_rating": 70, "te_rating": 65},
                "defense": {"dl_rating": 82, "lb_rating": 78, "db_rating": 70},
                "special_teams": 72,
                "coaching": {"offensive": 60, "defensive": 75},
                "overall_rating": 65
            },
            2: {  # Packers
                "name": "Packers", "city": "Green Bay",
                "offense": {"qb_rating": 88, "rb_rating": 70, "wr_rating": 85, "ol_rating": 72, "te_rating": 78},
                "defense": {"dl_rating": 75, "lb_rating": 68, "db_rating": 72},
                "special_teams": 78,
                "coaching": {"offensive": 85, "defensive": 70},
                "overall_rating": 75
            },
            3: {  # Lions
                "name": "Lions", "city": "Detroit",
                "offense": {"qb_rating": 72, "rb_rating": 65, "wr_rating": 68, "ol_rating": 58, "te_rating": 62},
                "defense": {"dl_rating": 62, "lb_rating": 55, "db_rating": 58},
                "special_teams": 60,
                "coaching": {"offensive": 65, "defensive": 55},
                "overall_rating": 60
            },
            4: {  # Vikings
                "name": "Vikings", "city": "Minneapolis",
                "offense": {"qb_rating": 78, "rb_rating": 68, "wr_rating": 82, "ol_rating": 65, "te_rating": 70},
                "defense": {"dl_rating": 72, "lb_rating": 75, "db_rating": 68},
                "special_teams": 70,
                "coaching": {"offensive": 72, "defensive": 68},
                "overall_rating": 70
            },
            5: {  # Cowboys
                "name": "Cowboys", "city": "Dallas",
                "offense": {"qb_rating": 82, "rb_rating": 85, "wr_rating": 88, "ol_rating": 75, "te_rating": 72},
                "defense": {"dl_rating": 78, "lb_rating": 80, "db_rating": 82},
                "special_teams": 82,
                "coaching": {"offensive": 80, "defensive": 78},
                "overall_rating": 80
            },
            6: {  # Eagles
                "name": "Eagles", "city": "Philadelphia", 
                "offense": {"qb_rating": 75, "rb_rating": 78, "wr_rating": 75, "ol_rating": 80, "te_rating": 68},
                "defense": {"dl_rating": 85, "lb_rating": 72, "db_rating": 75},
                "special_teams": 75,
                "coaching": {"offensive": 75, "defensive": 80},
                "overall_rating": 72
            },
            7: {  # Giants
                "name": "Giants", "city": "New York",
                "offense": {"qb_rating": 70, "rb_rating": 72, "wr_rating": 65, "ol_rating": 62, "te_rating": 75},
                "defense": {"dl_rating": 68, "lb_rating": 70, "db_rating": 65},
                "special_teams": 68,
                "coaching": {"offensive": 68, "defensive": 70},
                "overall_rating": 68
            },
            8: {  # Commanders
                "name": "Commanders", "city": "Washington",
                "offense": {"qb_rating": 65, "rb_rating": 70, "wr_rating": 72, "ol_rating": 60, "te_rating": 65},
                "defense": {"dl_rating": 72, "lb_rating": 65, "db_rating": 62},
                "special_teams": 65,
                "coaching": {"offensive": 62, "defensive": 65},
                "overall_rating": 62
            }
        }
    
    def get_team_for_simulation(self, team_id: int) -> dict:
        """Get complete team data for simulation"""
        return self.teams_data.get(team_id, {})
    
    def calculate_team_strength(self, team_id: int) -> float:
        """Calculate overall team strength for scoring"""
        team_data = self.get_team_for_simulation(team_id)
        return team_data.get("overall_rating", 50.0)
    
    def simulate_game(self, home_team_id: int, away_team_id: int) -> GameResult:
        # Get complete team data for simulation
        home_team = self.get_team_for_simulation(home_team_id)
        away_team = self.get_team_for_simulation(away_team_id)
        
        # Initialize play-by-play simulation with new architecture
        play_executor = PlayExecutor()
        game_state = GameState()
        game_state.field.possession_team_id = home_team_id  # Home team starts with ball
        game_state.scoreboard.home_team_id = home_team_id
        game_state.scoreboard.away_team_id = away_team_id
        
        play_count = 0
        max_plays = 200  # Safety limit to prevent infinite loops
        
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
            play_result = play_executor.execute_play(offense_team, defense_team, game_state)

            # TODO: Add a stats tracker here later on.
            
            # Update game state using the centralized method
            field_result = game_state.update_after_play(play_result)
            
            # Handle possession changes for scoring
            if play_result.is_score:
                # TODO: Handle kickoff after score properly
                # For now, just switch possession
                game_state.field.possession_team_id = away_team_id if game_state.field.possession_team_id == home_team_id else home_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                game_state.field.field_position = 25
            
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
        
        return GameResult(
            home_score=game_state.scoreboard.home_score,
            away_score=game_state.scoreboard.away_score,
            winner_id=winner_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id
        )
    
    def _generate_score(self, team_strength: float, is_home: bool) -> int:
        base_score = 14
        
        strength_modifier = (team_strength - 50) * 0.3
        home_advantage = 3 if is_home else 0
        
        variance = random.normalvariate(0, 7)
        
        final_score = max(0, round(base_score + strength_modifier + home_advantage + variance))
        return final_score