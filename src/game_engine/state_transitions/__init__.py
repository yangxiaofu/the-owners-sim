"""
Game State Transitions System

This package provides a clean, testable, and maintainable approach to managing
all game state changes in the football simulation. It separates the concerns of:
- Calculating what changes should happen (pure functions)
- Validating changes are legal (rule enforcement)  
- Applying changes atomically (transactional updates)
- Tracking statistics and auditing (separate concerns)

Key Components:
- data_structures: Immutable transition objects ✅
- calculators: Pure business logic functions ✅
- validators: Comprehensive rule validation ✅ 
- applicators: Atomic state application ✅
- tracking: Statistics and auditing ✅
"""

# Import all components with error handling
components = {}

# Data structures (immutable transition objects)
try:
    from .data_structures import (
        GameStateTransition as DataGameStateTransition,
        FieldTransition, PossessionTransition, ScoreTransition, 
        ClockTransition, SpecialSituationTransition
    )
    components['data_structures'] = True
except ImportError as e:
    print(f"Warning: Could not import data structures: {e}")
    components['data_structures'] = False

# Calculators (pure business logic functions)  
try:
    from .calculators import (
        TransitionCalculator, FieldCalculator, PossessionCalculator,
        ScoreCalculator, ClockCalculator, SpecialSituationsCalculator,
        calculate_transitions
    )
    components['calculators'] = True
except ImportError as e:
    print(f"Warning: Could not import calculators: {e}")
    components['calculators'] = False

# Validators (rule validation and consistency checks)
try:
    from .validators import (
        TransitionValidator, FieldValidator, PossessionValidator, 
        ScoreValidator, NFLRulesValidator,
        ValidationResult, ValidationResultBuilder, ValidationCategory,
        PossessionChangeReason, ScoreType
    )
    # Note: GameStateTransition is now properly available from data_structures
    components['validators'] = True
except ImportError as e:
    print(f"Warning: Could not import validators: {e}")
    components['validators'] = False

# Applicators (atomic state application)
try:
    from .applicators import (
        TransitionApplicator, AtomicStateChanger, StateRollbackManager
    )
    components['applicators'] = True
except ImportError as e:
    print(f"Warning: Could not import applicators: {e}")
    components['applicators'] = False

# Tracking (statistics and auditing)
try:
    from .tracking import (
        GameStatisticsTracker, PlayByPlayAuditor, PerformanceTracker,
        create_integrated_tracker
    )
    components['tracking'] = True
except ImportError as e:
    print(f"Warning: Could not import tracking: {e}")
    components['tracking'] = False

# Export the main transition object (prefer data structures, fallback to validators)
GameStateTransition = DataGameStateTransition

# Build dynamic exports based on available components
__all__ = ['GameStateTransition']

if components.get('data_structures'):
    __all__.extend([
        'FieldTransition', 'PossessionTransition', 'ScoreTransition', 
        'ClockTransition', 'SpecialSituationTransition'
    ])

if components.get('calculators'):
    __all__.extend([
        'TransitionCalculator', 'FieldCalculator', 'PossessionCalculator',
        'ScoreCalculator', 'ClockCalculator', 'SpecialSituationsCalculator',
        'calculate_transitions'
    ])

if components.get('validators'):
    __all__.extend([
        'TransitionValidator', 'FieldValidator', 'PossessionValidator', 
        'ScoreValidator', 'NFLRulesValidator',
        'ValidationResult', 'ValidationResultBuilder', 'ValidationCategory',
        'PossessionChangeReason', 'ScoreType'
    ])

if components.get('applicators'):
    __all__.extend([
        'TransitionApplicator', 'AtomicStateChanger', 'StateRollbackManager'
    ])

if components.get('tracking'):
    __all__.extend([
        'GameStatisticsTracker', 'PlayByPlayAuditor', 'PerformanceTracker',
        'create_integrated_tracker'
    ])

# Summary of available components
_available_components = [name for name, available in components.items() if available]
_missing_components = [name for name, available in components.items() if not available]

if _missing_components:
    print(f"State transitions system: {len(_available_components)}/{len(components)} components available")
    print(f"Available: {', '.join(_available_components)}")
    print(f"Missing: {', '.join(_missing_components)}")
else:
    print(f"✅ All {len(components)} state transition components available")