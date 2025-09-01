"""
Main Transition Calculator - Pure State Calculation Coordinator

This module coordinates all state transition calculations based on PlayResult and GameState.
It contains only pure functions with no side effects, calculating what should happen
without actually changing any state.

All functions take PlayResult and GameState as inputs and return appropriate 
transition objects from the data_structures module.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass

# Import existing PlayResult from the plays module
from ...plays.data_structures import PlayResult

# Import transition data structures from individual calculators
from .field_calculator import FieldTransition
from .possession_calculator import PossessionTransition  
from .score_calculator import ScoreTransition
from .clock_calculator import ClockTransition
from .special_situations_calculator import SpecialSituationTransition

# Import calculator modules
from .field_calculator import FieldCalculator
from .possession_calculator import PossessionCalculator  
from .score_calculator import ScoreCalculator
from .clock_calculator import ClockCalculator
from .special_situations_calculator import SpecialSituationsCalculator


@dataclass(frozen=True)
class GameStateTransition:
    """
    Main container for all calculated state changes.
    This represents everything that should happen after a play.
    """
    field_transition: Optional[FieldTransition] = None
    possession_transition: Optional[PossessionTransition] = None  
    score_transition: Optional[ScoreTransition] = None
    clock_transition: Optional[ClockTransition] = None
    special_situation_transitions: List[SpecialSituationTransition] = None
    
    def __post_init__(self):
        # Initialize empty list if None provided
        if self.special_situation_transitions is None:
            object.__setattr__(self, 'special_situation_transitions', [])


class TransitionCalculator:
    """
    Main coordinator for calculating all state transitions.
    
    This class orchestrates the various specialized calculators to determine
    what state changes should happen based on a PlayResult and current GameState.
    
    All methods are pure functions with no side effects.
    """
    
    def __init__(self):
        """Initialize all specialized calculators."""
        self.field_calculator = FieldCalculator()
        self.possession_calculator = PossessionCalculator()
        self.score_calculator = ScoreCalculator()
        self.clock_calculator = ClockCalculator()
        self.special_situations_calculator = SpecialSituationsCalculator()
    
    def calculate_all_transitions(self, play_result: PlayResult, game_state) -> GameStateTransition:
        """
        Calculate all state transitions for a play result.
        
        This is the main entry point that coordinates all specialized calculators
        to determine the complete set of state changes needed.
        
        Args:
            play_result: The result of executing a play
            game_state: Current game state (field, clock, scoreboard)
            
        Returns:
            GameStateTransition containing all calculated changes
        """
        # Calculate basic field changes (downs, yards to go, field position)
        field_transition = self.field_calculator.calculate_field_changes(
            play_result, game_state
        )
        
        # Calculate possession changes (turnovers, scores, punts)
        possession_transition = self.possession_calculator.calculate_possession_changes(
            play_result, game_state
        )
        
        # Calculate scoring changes  
        score_transition = self.score_calculator.calculate_score_changes(
            play_result, game_state
        )
        
        # Calculate clock changes
        clock_transition = self.clock_calculator.calculate_clock_changes(
            play_result, game_state
        )
        
        # Calculate special situations (kickoffs, complex scenarios)
        special_situations = self.special_situations_calculator.calculate_special_situations(
            play_result, game_state
        )
        
        return GameStateTransition(
            field_transition=field_transition,
            possession_transition=possession_transition,
            score_transition=score_transition,
            clock_transition=clock_transition,
            special_situation_transitions=special_situations
        )
    
    def calculate_field_only(self, play_result: PlayResult, game_state) -> FieldTransition:
        """Calculate only field position changes (for testing/specific scenarios)."""
        return self.field_calculator.calculate_field_changes(play_result, game_state)
    
    def calculate_possession_only(self, play_result: PlayResult, game_state) -> PossessionTransition:
        """Calculate only possession changes (for testing/specific scenarios)."""
        return self.possession_calculator.calculate_possession_changes(play_result, game_state)
    
    def calculate_score_only(self, play_result: PlayResult, game_state) -> ScoreTransition:
        """Calculate only scoring changes (for testing/specific scenarios)."""
        return self.score_calculator.calculate_score_changes(play_result, game_state)
    
    def calculate_clock_only(self, play_result: PlayResult, game_state) -> ClockTransition:
        """Calculate only clock changes (for testing/specific scenarios)."""
        return self.clock_calculator.calculate_clock_changes(play_result, game_state)
    
    def calculate_special_situations_only(self, play_result: PlayResult, game_state) -> List[SpecialSituationTransition]:
        """Calculate only special situation changes (for testing/specific scenarios)."""
        return self.special_situations_calculator.calculate_special_situations(play_result, game_state)


# Convenience function for external usage
def calculate_transitions(play_result: PlayResult, game_state) -> GameStateTransition:
    """
    Convenience function to calculate all transitions.
    
    This is the main external API for the transition calculation system.
    
    Args:
        play_result: The result of executing a play
        game_state: Current game state
        
    Returns:
        Complete GameStateTransition with all calculated changes
    """
    calculator = TransitionCalculator()
    return calculator.calculate_all_transitions(play_result, game_state)