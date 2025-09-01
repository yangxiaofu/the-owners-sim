"""
Validators Module

Provides comprehensive validation for game state transitions to ensure
all state changes are legal and consistent with NFL rules.
"""

from .validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory, 
    ValidationSeverity, ValidationIssue, create_success_result, create_error_result
)
from .transition_validator import TransitionValidator, GameStateTransition
from .field_validator import FieldValidator
from .possession_validator import PossessionValidator, PossessionChangeReason
from .score_validator import ScoreValidator, ScoreType
from .nfl_rules_validator import NFLRulesValidator

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