"""
Game State Management Module

This module handles all game state progression between plays including:
- Field position tracking and boundary management
- Down situation tracking and first down detection  
- Unified game state coordination

Components:
- FieldPosition: Data structure for field position
- FieldTracker: Processes field position changes and scoring
- DownState: Data structure for down and distance situation
- DownTracker: Processes down progression and conversions
- GameStateManager: Orchestrates field and down tracking
- GameStateResult: Unified result combining field and down information
"""

from .field_position import FieldPosition, FieldTracker, FieldZone
from .down_situation import DownState, DownTracker  
from .game_state_manager import GameStateManager, GameStateResult, GameState

__all__ = [
    'FieldPosition',
    'FieldTracker',
    'FieldZone', 
    'DownState',
    'DownTracker',
    'GameStateManager',
    'GameStateResult',
    'GameState'
]