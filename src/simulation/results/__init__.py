"""
Simulation Results Package

Enhanced result type hierarchy for different event types.
Provides event-specific result classes while maintaining backward compatibility.
"""

from .base_result import SimulationResult, EventType
from .game_result import GameResult
from .training_result import TrainingResult
from .scouting_result import ScoutingResult
from .administrative_result import AdministrativeResult
from .rest_result import RestResult

__all__ = [
    'SimulationResult',
    'EventType',
    'GameResult', 
    'TrainingResult',
    'ScoutingResult',
    'AdministrativeResult',
    'RestResult'
]