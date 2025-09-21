"""
Statistics Extraction Module

Pure logic components for extracting comprehensive statistics from game results.
No side effects or external dependencies for maximum testability.

Components:
- BaseExtractor: Abstract base class for all extractors
- PlayerStatisticsExtractor: Extract comprehensive player statistics
- TeamStatisticsExtractor: Extract team-level aggregate statistics
- GameMetadataExtractor: Extract game context and metadata
"""

from .base_extractor import BaseExtractor
from .player_statistics_extractor import PlayerStatisticsExtractor
from .team_statistics_extractor import TeamStatisticsExtractor
from .game_metadata_extractor import GameMetadataExtractor

__all__ = [
    'BaseExtractor',
    'PlayerStatisticsExtractor',
    'TeamStatisticsExtractor',
    'GameMetadataExtractor'
]