import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class KickPlay(PlayType):
    """Handles field goal and extra point attempts"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a field goal attempt and return the result"""
        
        # Extract ratings from personnel  
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        
        outcome, yards_gained = self._simulate_field_goal(offense_ratings, field_state)
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("field_goal", outcome)
        is_turnover = False  # Field goals don't result in turnovers
        is_score = outcome == "field_goal"
        score_points = self._calculate_points(outcome)
        
        return PlayResult(
            play_type="field_goal",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points
        )
    
    def _simulate_field_goal(self, offense_ratings: Dict, field_state: FieldState) -> tuple[str, int]:
        """Simulate a field goal attempt based on distance and team ratings"""
        # Calculate distance (field position + 17 yards for end zone and holder)
        distance = (100 - field_state.field_position) + 17
        
        # Base success rate decreases with distance
        base_success_rate = max(0.3, 0.95 - (distance - 20) * 0.015)
        
        # Adjust for kicker quality (use special teams rating as proxy)  
        kicker_rating = offense_ratings.get("special_teams", 70)
        rating_adjustment = (kicker_rating - 70) * 0.005  # ±15% based on rating
        
        # Weather, pressure, and other factors could be added here
        final_success_rate = min(0.95, max(0.15, base_success_rate + rating_adjustment))
        
        if random.random() < final_success_rate:
            return "field_goal", 0  # No yards gained, just points
        else:
            return "missed_fg", 0