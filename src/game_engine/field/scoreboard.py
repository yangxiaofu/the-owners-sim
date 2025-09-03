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
        # SAFETY CHECK: Prevent impossible 1-point total scores
        # Extra points should only be added after touchdowns, never as standalone scores
        if team_id == self.home_team_id:
            new_score = self.home_score + 1
            # Validate that this won't create an impossible score
            if new_score == 1:
                print(f"🚨 PREVENTED 1-POINT SCORE: Home team would have had 1 point (impossible in NFL)")
                return  # Don't add the point
            self.home_score = new_score
        elif team_id == self.away_team_id:
            new_score = self.away_score + 1
            # Validate that this won't create an impossible score
            if new_score == 1:
                print(f"🚨 PREVENTED 1-POINT SCORE: Away team would have had 1 point (impossible in NFL)")
                return  # Don't add the point
            self.away_score = new_score
    
    def add_two_point_conversion(self, team_id: int):
        """Add two-point conversion"""
        if team_id == self.home_team_id:
            self.home_score += 2
        elif team_id == self.away_team_id:
            self.away_score += 2
    
    def get_score(self) -> tuple:
        """Get current score as (home_score, away_score)"""
        # Validate scores before returning
        self.validate_scores()
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
    
    def validate_scores(self) -> bool:
        """Validate that current scores are possible in NFL football"""
        impossible_scores = [1, 4, 5]  # Cannot be achieved in NFL
        
        if self.home_score in impossible_scores or self.away_score in impossible_scores:
            print(f"🚨 INVALID SCORE DETECTED: Home {self.home_score}, Away {self.away_score}")
            return False
        return True
    
    def fix_invalid_scores(self):
        """Fix any invalid scores by rounding to nearest valid score"""
        if not self.validate_scores():
            # Fix impossible scores
            if self.home_score == 1:
                print(f"🔧 FIXING HOME SCORE: 1 → 0 (1-point not possible)")
                self.home_score = 0
            elif self.home_score == 4:
                print(f"🔧 FIXING HOME SCORE: 4 → 3 (4-point highly unlikely, probably missed extra point)")
                self.home_score = 3
            elif self.home_score == 5:
                print(f"🔧 FIXING HOME SCORE: 5 → 6 (5-point impossible, probably missed extra point)")
                self.home_score = 6
                
            if self.away_score == 1:
                print(f"🔧 FIXING AWAY SCORE: 1 → 0 (1-point not possible)")
                self.away_score = 0
            elif self.away_score == 4:
                print(f"🔧 FIXING AWAY SCORE: 4 → 3 (4-point highly unlikely, probably missed extra point)")
                self.away_score = 3
            elif self.away_score == 5:
                print(f"🔧 FIXING AWAY SCORE: 5 → 6 (5-point impossible, probably missed extra point)")
                self.away_score = 6