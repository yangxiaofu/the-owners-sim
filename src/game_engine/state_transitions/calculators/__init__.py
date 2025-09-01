"""
State Transition Calculators

Pure calculation functions that determine what state changes should happen
based on PlayResult and GameState inputs. All functions are side-effect free
and return immutable transition objects.

Key Modules:
- transition_calculator: Main coordinator for all calculations
- field_calculator: Field position, downs, yards to go logic
- possession_calculator: Team possession change rules
- score_calculator: Scoring and point calculation logic
- clock_calculator: Time management and quarter logic
- special_situations_calculator: Complex scenarios (punt, kickoff, turnover)
"""

# Import main calculator classes  
from .transition_calculator import TransitionCalculator, calculate_transitions
# Import BaseGameStateTransition from data structures (no longer defined in calculator)
from ..data_structures import BaseGameStateTransition
from .field_calculator import FieldCalculator, FieldTransition
from .possession_calculator import PossessionCalculator, PossessionTransition
from .score_calculator import ScoreCalculator, ScoreTransition
from .clock_calculator import ClockCalculator, ClockTransition
from .special_situations_calculator import (
    SpecialSituationsCalculator, 
    SpecialSituationTransition, 
    KickoffResult
)

__all__ = [
    # Main coordinator
    'TransitionCalculator',
    'BaseGameStateTransition',  # Now imported from data_structures
    'calculate_transitions',
    
    # Individual calculators
    'FieldCalculator',
    'PossessionCalculator',
    'ScoreCalculator', 
    'ClockCalculator',
    'SpecialSituationsCalculator',
    
    # Transition data structures
    'FieldTransition',
    'PossessionTransition',
    'ScoreTransition',
    'ClockTransition',
    'SpecialSituationTransition',
    'KickoffResult',
]