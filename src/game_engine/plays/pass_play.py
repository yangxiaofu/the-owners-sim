import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class PassPlay(PlayType):
    """Handles all passing play simulation logic"""
    
    def simulate(self, offense_team: Dict, defense_team: Dict, field_state: FieldState) -> PlayResult:
        """Simulate a passing play and return the result"""
        
        outcome, yards_gained = self._simulate_pass(offense_team, defense_team)
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("pass", outcome)
        is_turnover = outcome == "interception"
        is_score = outcome == "touchdown"
        score_points = self._calculate_points(outcome)
        
        return PlayResult(
            play_type="pass",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points
        )
    
    def _simulate_pass(self, offense: Dict, defense: Dict) -> tuple[str, int]:
        """Simulate a passing play based on team ratings"""
        qb_rating = offense["offense"]["qb_rating"]
        wr_rating = offense["offense"]["wr_rating"]
        db_rating = defense["defense"]["db_rating"]
        
        # Completion probability
        completion_prob = (qb_rating + wr_rating) / (qb_rating + wr_rating + db_rating * 1.5)
        
        if random.random() < completion_prob:
            # Completed pass
            yards = random.randint(3, 25)
            if random.random() < 0.08:  # 8% chance of big play
                yards += random.randint(15, 60)
                
            # Check for touchdown
            if yards >= 25 and random.random() < 0.12:
                return "touchdown", yards
                
            return "gain", yards
        else:
            # Incomplete pass or negative play
            if random.random() < 0.1:  # 10% chance of sack
                return "sack", random.randint(-8, -1)
            elif random.random() < 0.02:  # 2% chance of interception
                return "interception", 0
            else:
                return "incomplete", 0