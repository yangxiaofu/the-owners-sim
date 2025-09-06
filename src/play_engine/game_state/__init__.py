"""
Game State Management Module

This module handles all game state progression between plays including:
- Field position tracking and boundary management
- Down situation tracking and first down detection  
- Ball possession tracking with clean separation of concerns
- Game clock and timing management
- Unified game state coordination

Components:
- FieldPosition: Data structure for field position
- FieldTracker: Processes field position changes and scoring
- DownState: Data structure for down and distance situation
- DownTracker: Processes down progression and conversions
- PossessionManager: Simple ball possession tracking ("who has the ball")
- PossessionChange: Data structure for possession change events
- GameClock: Game timing and quarter management
- ClockResult: Data structure for clock advancement results
- GamePhase: Enum for game phases (first half, halftime, etc.)
- GameStateManager: Orchestrates field and down tracking
- GameStateResult: Unified result combining field and down information
"""

from .field_position import FieldPosition, FieldTracker, FieldZone
from .down_situation import DownState, DownTracker  
from .game_state_manager import GameStateManager, GameStateResult, GameState
from .possession_manager import PossessionManager, PossessionChange
from .game_clock import GameClock, ClockResult, GamePhase

__all__ = [
    'FieldPosition',
    'FieldTracker',
    'FieldZone', 
    'DownState',
    'DownTracker',
    'GameStateManager',
    'GameStateResult',
    'GameState',
    'PossessionManager',
    'PossessionChange',
    'GameClock',
    'ClockResult',
    'GamePhase'
]