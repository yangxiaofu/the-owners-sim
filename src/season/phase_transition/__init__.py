"""
Phase Transition Package

Contains classes for managing NFL season phase transitions in a testable way.

Key Components:
- PhaseTransition: Model representing a phase transition
- PhaseTransitionManager: Coordinates transition detection and execution
- PhaseCompletionChecker: Checks if phases are complete (testable logic)
- Transition Handlers: Execute specific transitions (Regular→Playoffs, etc.)
"""

from .models import PhaseTransition, TransitionFailedError
from .phase_transition_manager import PhaseTransitionManager
from .phase_completion_checker import PhaseCompletionChecker

__all__ = [
    'PhaseTransition',
    'TransitionFailedError',
    'PhaseTransitionManager',
    'PhaseCompletionChecker',
]
