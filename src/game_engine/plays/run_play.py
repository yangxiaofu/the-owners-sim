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
    
    def simulate(self, offense_team: Dict, defense_team: Dict, field_state: FieldState) -> PlayResult:
        """Simulate a running play and return the result"""
        
        # Use detailed position-by-position simulation
        outcome, yards_gained = self._simulate_detailed_run(offense_team, defense_team)
        
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
    
    def _simulate_detailed_run(self, offense: Dict, defense: Dict) -> tuple[str, int]:
        """Use detailed position-by-position simulation"""
        play_call = RunPlayCall.default_inside_run()
        detailed_result = self.detailed_run_simulator.simulate_run(offense, defense, play_call)
        return detailed_result.outcome, detailed_result.yards_gained
    
