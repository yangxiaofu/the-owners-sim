"""
Statistics Models Module

Value objects and data structures for statistics persistence.
Immutable objects that represent data at different stages of the pipeline.

Components:
- PersistenceResult: Result objects for operations with success/failure details
- DatabaseRecord: Database record representations for different table types
- ExtractionContext: Context information for extraction operations
"""

from .persistence_result import PersistenceResult
from .database_record import (
    PlayerGameStatsRecord,
    TeamGameStatsRecord,
    GameContextRecord
)
from .extraction_context import ExtractionContext

__all__ = [
    'PersistenceResult',
    'PlayerGameStatsRecord',
    'TeamGameStatsRecord',
    'GameContextRecord',
    'ExtractionContext'
]