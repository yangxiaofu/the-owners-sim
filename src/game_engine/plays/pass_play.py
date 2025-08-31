import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState


class PassPlay(PlayType):
    """Handles all passing play simulation logic"""
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a passing play using selected personnel"""
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Apply formation modifier
        formation_modifier = self._get_formation_modifier(
            personnel.formation, personnel.defensive_call, "pass"
        )
        
        outcome, yards_gained = self._simulate_personnel_pass(
            offense_ratings, defense_ratings, personnel, formation_modifier
        )
        
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
    
    def _simulate_personnel_pass(self, offense_ratings: Dict, defense_ratings: Dict,
                                personnel, formation_modifier: float) -> tuple[str, int]:
        """Enhanced pass simulation using personnel data and formation advantages"""
        import random
        
        # Get key ratings with fallbacks
        qb_rating = offense_ratings.get('qb', 50)
        wr_rating = offense_ratings.get('wr', 50)
        ol_rating = offense_ratings.get('ol', 50)
        db_rating = defense_ratings.get('db', 50)
        dl_rating = defense_ratings.get('dl', 50)
        
        # Apply formation modifier
        passing_strength = (qb_rating + wr_rating) * formation_modifier
        
        # Pressure calculation (affects completion rate)
        pressure_rate = dl_rating / (dl_rating + ol_rating * 1.2)
        
        # Base completion probability
        completion_prob = passing_strength / (passing_strength + db_rating * 1.3)
        
        # Adjust for pressure
        completion_prob *= (1.0 - pressure_rate * 0.3)
        
        # Individual player adjustments
        if personnel.individual_players:
            # QB accuracy bonus/penalty based on effective rating
            # WR route running and hands
            # DB coverage skills
            pass  # Placeholder for detailed individual player logic
        
        # Determine outcome
        if random.random() < pressure_rate * 0.15:  # Sack chance
            return "sack", random.randint(-8, -1)
        elif random.random() < 0.02:  # Interception chance
            return "interception", 0
        elif random.random() < completion_prob:
            # Completed pass
            base_yards = random.randint(5, 18)
            
            # Big play chance based on formation and players
            big_play_chance = 0.12
            if personnel.formation in ["shotgun_spread", "shotgun"]:
                big_play_chance *= 1.3
                
            if random.random() < big_play_chance:
                base_yards += random.randint(15, 50)
                
            # Touchdown chance on big plays
            if base_yards >= 25 and random.random() < 0.18:
                return "touchdown", base_yards
                
            return "gain", base_yards
        else:
            # Incomplete pass
            return "incomplete", 0
    
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