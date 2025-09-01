"""
Immutable Data Structures for Game State Transitions

This module contains all the immutable data structures that represent different
types of state changes in the football game simulation. Each transition object
is frozen (immutable) and contains all the data needed for that specific type
of state change.

All transition objects follow these principles:
- Immutable using @dataclass(frozen=True)
- Comprehensive type hints for all fields
- Complete docstrings explaining each field
- Contains all data needed for the specific transition type
- Can be easily tested and verified
"""

from .game_state_transition import BaseGameStateTransition, GameStateTransition
from .field_transition import FieldTransition
from .possession_transition import PossessionTransition
from .score_transition import ScoreTransition
from .clock_transition import ClockTransition
from .special_situation_transition import SpecialSituationTransition
from .transition_utils import enhance_base_transition, extract_base_transition, create_transition_id

__all__ = [
    'BaseGameStateTransition',
    'GameStateTransition',
    'FieldTransition',
    'PossessionTransition', 
    'ScoreTransition',
    'ClockTransition',
    'SpecialSituationTransition',
    # Utility functions
    'enhance_base_transition',
    'extract_base_transition', 
    'create_transition_id',
]