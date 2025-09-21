"""
Persistence Module

Handles saving simulation data to the database.
Includes both batch daily persistence and immediate game statistics persistence.
"""

from .daily_persister import DailyDataPersister
from .game_statistics import GameStatisticsService

__all__ = ['DailyDataPersister', 'GameStatisticsService']