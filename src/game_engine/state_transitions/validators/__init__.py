"""
Validators Module

Provides comprehensive validation for game state transitions to ensure
all state changes are legal and consistent with NFL rules.
"""

from game_engine.state_transitions.validators.validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory, 
    ValidationSeverity, ValidationIssue, create_success_result, create_error_result
)
from game_engine.state_transitions.validators.transition_validator import TransitionValidator, GameStateTransition
from game_engine.state_transitions.validators.field_validator import FieldValidator
from game_engine.state_transitions.validators.possession_validator import PossessionValidator, PossessionChangeReason
from game_engine.state_transitions.validators.score_validator import ScoreValidator
from game_engine.state_transitions.data_structures.score_transition import ScoreType
from game_engine.state_transitions.validators.nfl_rules_validator import NFLRulesValidator

__all__ = [
    # Main validation classes
    'TransitionValidator',
    'FieldValidator', 
    'PossessionValidator',
    'ScoreValidator',
    'NFLRulesValidator',
    
    # Data structures
    'GameStateTransition',
    'ValidationResult',
    'ValidationResultBuilder',
    'ValidationCategory',
    'ValidationSeverity',
    'ValidationIssue',
    'PossessionChangeReason',
    'ScoreType',
    
    # Utility functions
    'create_success_result',
    'create_error_result',
]