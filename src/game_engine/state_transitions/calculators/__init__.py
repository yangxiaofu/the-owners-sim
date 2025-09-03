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
from game_engine.state_transitions.calculators.transition_calculator import TransitionCalculator, calculate_transitions
# Import BaseGameStateTransition from data structures (no longer defined in calculator)
from game_engine.state_transitions.data_structures import BaseGameStateTransition
from game_engine.state_transitions.calculators.field_calculator import FieldCalculator
from game_engine.state_transitions.calculators.possession_calculator import PossessionCalculator
from game_engine.state_transitions.calculators.score_calculator import ScoreCalculator
from game_engine.state_transitions.calculators.clock_calculator import ClockCalculator
from game_engine.state_transitions.calculators.special_situations_calculator import SpecialSituationsCalculator, KickoffResult

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
    'KickoffResult',
]