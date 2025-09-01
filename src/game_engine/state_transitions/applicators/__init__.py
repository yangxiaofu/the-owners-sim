"""
Atomic State Application

This module handles the atomic application of state transitions to game state
objects. All changes are applied together or rolled back on any failure,
ensuring consistent game state at all times.

Key principles:
- Atomic transactions (all or nothing)
- Rollback capability on failures
- State consistency guarantees
- Error recovery mechanisms
- Thread-safe operations
"""

from .transition_applicator import TransitionApplicator
from .atomic_state_changer import AtomicStateChanger
from .state_rollback_manager import StateRollbackManager

__all__ = [
    'TransitionApplicator',
    'AtomicStateChanger', 
    'StateRollbackManager'
]