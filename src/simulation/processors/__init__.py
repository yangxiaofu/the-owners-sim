"""
Result Processors Package

Result processing system for handling different types of simulation results
with event-specific logic and season state management.
"""

from .base_processor import BaseResultProcessor, ProcessingStrategy
from .game_processor import GameResultProcessor
from .training_processor import TrainingResultProcessor
from .scouting_processor import ScoutingResultProcessor
from .administrative_processor import AdministrativeResultProcessor
from .rest_processor import RestResultProcessor

__all__ = [
    'BaseResultProcessor',
    'ProcessingStrategy',
    'GameResultProcessor',
    'TrainingResultProcessor', 
    'ScoutingResultProcessor',
    'AdministrativeResultProcessor',
    'RestResultProcessor'
]