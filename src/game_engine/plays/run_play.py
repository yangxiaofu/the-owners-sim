import random
from typing import Dict
from .play_types import PlayType
from .data_structures import PlayResult
from ..field.field_state import FieldState
from ..simulation.blocking.data_structures import RunPlayCall
from .run_plays import DetailedRunSimulator


class RunPlay(PlayType):
    """Handles all running play simulation logic"""
    
    def __init__(self):
        self.detailed_run_simulator = DetailedRunSimulator()
    
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        """Simulate a running play using selected personnel"""
        
        # Extract player ratings from personnel package
        offense_ratings = self._extract_player_ratings(personnel, "offense")
        defense_ratings = self._extract_player_ratings(personnel, "defense")
        
        # Apply formation modifier
        formation_modifier = self._get_formation_modifier(
            personnel.formation, personnel.defensive_call, "run"
        )
        
        # Use enhanced simulation with personnel awareness
        outcome, yards_gained = self._simulate_personnel_run(
            offense_ratings, defense_ratings, personnel, formation_modifier
        )
        
        # Calculate time elapsed and points
        time_elapsed = self._calculate_time_elapsed("run", outcome)
        is_turnover = outcome == "fumble"
        is_score = outcome == "touchdown"
        score_points = self._calculate_points(outcome)
        
        return PlayResult(
            play_type="run",
            outcome=outcome,
            yards_gained=yards_gained,
            time_elapsed=time_elapsed,
            is_turnover=is_turnover,
            is_score=is_score,
            score_points=score_points
        )
    
    def _simulate_personnel_run(self, offense_ratings: Dict, defense_ratings: Dict, 
                               personnel, formation_modifier: float) -> tuple[str, int]:
        """Enhanced run simulation using personnel data and formation advantages"""
        import random
        
        # Get key ratings with fallbacks
        rb_rating = offense_ratings.get('rb', 50)
        ol_rating = offense_ratings.get('ol', 50)
        dl_rating = defense_ratings.get('dl', 50)
        lb_rating = defense_ratings.get('lb', 50)
        
        # Calculate run success probability
        offensive_strength = (rb_rating * 0.4 + ol_rating * 0.6)
        defensive_strength = (dl_rating * 0.5 + lb_rating * 0.5)
        
        # Apply formation modifier
        offensive_strength *= formation_modifier
        
        # Base success rate calculation
        success_rate = offensive_strength / (offensive_strength + defensive_strength * 1.1)
        
        # Individual player bonuses when available
        if personnel.individual_players and personnel.rb_on_field:
            rb = personnel.rb_on_field
            # Power runners get bonus on short yardage
            if hasattr(rb, 'power') and rb.power > 85:
                success_rate *= 1.05
            # Elusive runners get bonus yards
            if hasattr(rb, 'elusiveness') and rb.elusiveness > 85:
                success_rate *= 1.03
        
        # Determine outcome
        if random.random() < success_rate:
            # Successful run
            base_yards = random.randint(2, 8)
            
            # Big play chance based on personnel
            big_play_chance = 0.08
            if personnel.individual_players and personnel.rb_on_field:
                if hasattr(personnel.rb_on_field, 'speed') and personnel.rb_on_field.speed > 85:
                    big_play_chance *= 1.5
                    
            if random.random() < big_play_chance:
                base_yards += random.randint(10, 40)
                
            # Formation-specific yard bonuses
            if personnel.formation == "goal_line" and base_yards <= 3:
                base_yards = max(1, base_yards)  # Goal line formation gets short yardage
            elif personnel.formation == "singleback":
                base_yards = max(1, base_yards)  # Balanced formation
                
            # Touchdown chance
            if base_yards >= 15 and random.random() < 0.15:
                return "touchdown", base_yards
                
            return "gain", base_yards
        else:
            # Failed run
            if random.random() < 0.05:  # 5% fumble chance
                return "fumble", random.randint(-2, 0)
            elif random.random() < 0.15:  # Negative play
                return "loss", random.randint(-5, -1)
            else:  # Short gain
                return "gain", random.randint(0, 2)
    
    def _simulate_detailed_run(self, offense: Dict, defense: Dict) -> tuple[str, int]:
        """Legacy detailed simulation - kept for backward compatibility"""
        play_call = RunPlayCall.default_inside_run()
        detailed_result = self.detailed_run_simulator.simulate_run(offense, defense, play_call)
        return detailed_result.outcome, detailed_result.yards_gained
    
