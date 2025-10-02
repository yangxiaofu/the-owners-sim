"""
Demo Persistence Module

Provides reusable persistence strategies for demo applications.
Uses composition and strategy pattern for maximum flexibility and testability.
"""

from .base_demo_persister import DemoPersister
from .persistence_result import PersistenceResult, PersistenceStatus, CompositePersistenceResult
from .game_persistence_orchestrator import GamePersistenceOrchestrator
from .database_demo_persister import DatabaseDemoPersister

__all__ = [
    'DemoPersister',
    'PersistenceResult',
    'PersistenceStatus',
    'CompositePersistenceResult',
    'GamePersistenceOrchestrator',
    'DatabaseDemoPersister'
]
