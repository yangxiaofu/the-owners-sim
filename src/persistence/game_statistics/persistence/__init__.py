"""
Statistics Persistence Module

Database operations with transaction management and error handling.
Provides ACID compliance and rollback capabilities for data integrity.

Components:
- StatisticsPersister: Main persistence orchestrator
- PlayerStatsPersister: Player-specific database operations
- TeamStatsPersister: Team-specific database operations
- TransactionManager: Transaction coordination and rollback
- BatchOperations: Bulk insert optimizations
"""

from .statistics_persister import StatisticsPersister
from .player_stats_persister import PlayerStatsPersister
from .team_stats_persister import TeamStatsPersister
from .transaction_manager import TransactionManager
from .batch_operations import BatchOperations

__all__ = [
    'StatisticsPersister',
    'PlayerStatsPersister',
    'TeamStatsPersister',
    'TransactionManager',
    'BatchOperations'
]