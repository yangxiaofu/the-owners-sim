"""
Game Management Module

Provides game-level orchestration components including scoreboard tracking,
game state coordination, and high-level game flow management.

This module operates above the play engine level, coordinating multiple
systems without modifying the underlying play simulation logic.
"""

from .scoreboard import Scoreboard, ScoringType, ScoringEvent
from .scoring_mapper import ScoringTypeMapper

__all__ = [
    'Scoreboard',
    'ScoringType', 
    'ScoringEvent',
    'ScoringTypeMapper'
]