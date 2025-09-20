"""
Stores Module

Provides in-memory storage layer for game data entities before persistence.
Sits between game processing and database persistence, allowing for batch
operations and transaction support.
"""

from .base_store import BaseStore, StoreMetadata
from .game_result_store import GameResultStore
from .player_stats_store import PlayerStatsStore
from .box_score_store import BoxScoreStore
from .standings_store import StandingsStore
from .store_manager import StoreManager

__all__ = [
    'BaseStore',
    'StoreMetadata',
    'GameResultStore',
    'PlayerStatsStore',
    'BoxScoreStore',
    'StandingsStore',
    'StoreManager'
]