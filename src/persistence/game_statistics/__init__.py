"""
Game Statistics Persistence Module

Comprehensive statistics persistence system for NFL game simulation results.
Provides immediate, transactional persistence of player and team statistics
with extensible schema support and maximum testability.

Main Components:
- GameStatisticsService: Main orchestrator for statistics persistence
- Extraction: Pure logic for extracting statistics from game results
- Mapping: Configuration-driven transformation to database format
- Persistence: Database operations with transaction management
- Models: Value objects and data structures
- Validation: Data integrity and validation logic

Usage:
    from persistence.game_statistics import GameStatisticsService

    service = GameStatisticsService.create_default()
    result = service.persist_game_statistics(game_result, game_metadata)
"""

from .game_statistics_service import GameStatisticsService
from .models.persistence_result import PersistenceResult
from .models.database_record import PlayerGameStatsRecord, TeamGameStatsRecord

__all__ = [
    'GameStatisticsService',
    'PersistenceResult',
    'PlayerGameStatsRecord',
    'TeamGameStatsRecord'
]