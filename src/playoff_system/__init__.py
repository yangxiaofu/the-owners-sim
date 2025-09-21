"""
NFL Playoff System

Comprehensive system for calculating playoff seeding using official NFL rules
and managing playoff tournament progression.

Components:
- seeding: Playoff seeding calculation with complex tiebreaker rules
- management: Tournament bracket management and game scheduling
- persistence: Database storage and in-memory caching
- validation: Data validation and historical accuracy testing
"""

from .seeding.seeding_data_models import PlayoffSeed, PlayoffSeeding, TiebreakerResult
from .seeding.playoff_seeding_calculator import PlayoffSeedingCalculator
from .seeding.nfl_tiebreaker_engine import NFLTiebreakerEngine

__all__ = [
    'PlayoffSeed',
    'PlayoffSeeding',
    'TiebreakerResult',
    'PlayoffSeedingCalculator',
    'NFLTiebreakerEngine'
]