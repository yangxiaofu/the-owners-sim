from dataclasses import dataclass
from typing import Optional

@dataclass
class Scoreboard:
    """Manages game scoring"""
    
    def __init__(self):
        self.home_score = 0
        self.away_score = 0
        self.home_team_id: Optional[int] = None
        self.away_team_id: Optional[int] = None
    
    def add_touchdown(self, team_id: int, points: int = 6):
        """Add touchdown points to a team"""
        if team_id == self.home_team_id:
            self.home_score += points
        elif team_id == self.away_team_id:
            self.away_score += points
    
    def add_field_goal(self, team_id: int):
        """Add field goal points to a team"""
        if team_id == self.home_team_id:
            self.home_score += 3
        elif team_id == self.away_team_id:
            self.away_score += 3
    
    def add_safety(self, team_id: int):
        """Add safety points to a team"""
        if team_id == self.home_team_id:
            self.home_score += 2
        elif team_id == self.away_team_id:
            self.away_score += 2
    
    def add_extra_point(self, team_id: int):
        """Add extra point after touchdown"""
        if team_id == self.home_team_id:
            self.home_score += 1
        elif team_id == self.away_team_id:
            self.away_score += 1
    
    def add_two_point_conversion(self, team_id: int):
        """Add two-point conversion"""
        if team_id == self.home_team_id:
            self.home_score += 2
        elif team_id == self.away_team_id:
            self.away_score += 2
    
    def get_score(self) -> tuple:
        """Get current score as (home_score, away_score)"""
        return (self.home_score, self.away_score)
    
    def get_winning_team(self) -> Optional[int]:
        """Get the ID of the winning team, or None if tied"""
        if self.home_score > self.away_score:
            return self.home_team_id
        elif self.away_score > self.home_score:
            return self.away_team_id
        return None
    
    def is_tied(self) -> bool:
        """Check if the game is tied"""
        return self.home_score == self.away_score
    
    def get_score_differential(self, team_id: int) -> int:
        """Get score differential for a team (positive = winning)"""
        if team_id == self.home_team_id:
            return self.home_score - self.away_score
        elif team_id == self.away_team_id:
            return self.away_score - self.home_score
        return 0