import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class PuntPlay(PlayType):
    """Handles punt simulation logic"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a punt and return the result"""
        
        # Extract ratings from personnel
        offense_ratings = self._extract_player_ratings(personnel, "offense") 
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        outcome, yards_gained = self._simulate_punt(offense_ratings, defense_ratings, field_state)
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("punt", outcome)
        is_turnover = False  # Punts are possession changes, not turnovers
        is_score = False  # Punts don't score directly
        score_points = 0
        
        return PlayResult(
            play_type="punt",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points
        )
    
    def _simulate_punt(self, offense_ratings: Dict, defense_ratings: Dict, field_state: FieldState) -> tuple[str, int]:
        """Simulate a punt based on field position and team ratings"""
        # Base punt distance
        base_distance = random.randint(35, 55)
        
        # Adjust for punter quality (use special teams rating)
        punter_rating = offense_ratings.get("special_teams", 70)
        rating_adjustment = (punter_rating - 70) * 0.2  # ±6 yards based on rating
        
        # Adjust for field position (harder to punt from deep)
        if field_state.field_position < 20:
            distance_penalty = random.randint(5, 15)
            base_distance -= distance_penalty
        
        final_distance = max(20, base_distance + rating_adjustment)
        
        # Small chance of blocked punt or poor snap
        if random.random() < 0.03:  # 3% chance of issues
            if random.random() < 0.5:
                return "blocked_punt", random.randint(0, 5)
            else:
                return "bad_punt", random.randint(15, 25)
        
        # Small chance of return touchdown
        if random.random() < 0.01:  # 1% chance
            return "punt_return_td", final_distance
            
        return "punt", final_distance