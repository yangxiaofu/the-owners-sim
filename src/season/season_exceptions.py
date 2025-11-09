"""
Season Management Exception Hierarchy

This module defines exceptions for season management operations including
phase transitions, season initialization, and season boundary violations.

Exception Hierarchy:
    SeasonException (base)
    ├── InvalidPhaseTransitionException
    ├── SeasonInitializationException
    ├── InvalidSeasonYearException
    ├── PhaseTransitionFailedException
    ├── SeasonBoundaryException
    └── InvalidSeasonStateException

All exceptions track:
- Season context (year, phase, dynasty_id)
- Operation that failed
- Recovery strategy
"""

from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class SeasonPhaseEnum(Enum):
    """Valid season phases for validation"""
    PRESEASON = "preseason"
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"
    OFFSEASON = "offseason"


class SeasonException(Exception):
    """
    Base exception for all season management errors.

    Root of the season exception hierarchy. All season-specific exceptions
    should inherit from this class.

    Attributes:
        message: Human-readable error message
        error_code: Unique error code
        season_context: Season information (year, phase, dynasty_id)
        operation: What operation was being performed
        recovery_strategy: How to recover from this error
        original_exception: Wrapped exception if from try/except
    """

    def __init__(
        self,
        message: str,
        error_code: str = "SEASON_000",
        season_context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        recovery_strategy: str = "abort",
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.season_context = season_context or {}
        self.operation = operation
        self.recovery_strategy = recovery_strategy
        self.original_exception = original_exception
        self.timestamp = datetime.now().isoformat()

        # Build detailed error message
        full_message = self._build_error_message()
        super().__init__(full_message)

    def _build_error_message(self) -> str:
        """Build comprehensive error message with all context"""
        lines = [
            f"[{self.error_code}] {self.message}",
            f"Timestamp: {self.timestamp}"
        ]

        if self.operation:
            lines.append(f"Operation: {self.operation}")

        if self.season_context:
            lines.append("Season Context:")
            for key, value in self.season_context.items():
                lines.append(f"  {key}: {value}")

        if self.recovery_strategy:
            lines.append(f"Recovery: {self.recovery_strategy}")

        if self.original_exception:
            lines.append(f"\nOriginal Error: {type(self.original_exception).__name__}: {str(self.original_exception)}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "operation": self.operation,
            "season_context": self.season_context,
            "recovery_strategy": self.recovery_strategy,
            "timestamp": self.timestamp,
            "original_error": str(self.original_exception) if self.original_exception else None
        }


class InvalidPhaseTransitionException(SeasonException):
    """
    Raised when an invalid phase transition is attempted.

    Valid transitions:
    - OFFSEASON → PRESEASON
    - PRESEASON → REGULAR_SEASON
    - REGULAR_SEASON → PLAYOFFS
    - PLAYOFFS → OFFSEASON

    Examples:
    - Attempting PRESEASON → PLAYOFFS (skips regular season)
    - Attempting PLAYOFFS → PRESEASON (wrong order)
    - Phase transition triggered when current phase doesn't match expected from_phase
    """

    def __init__(
        self,
        from_phase: str,
        to_phase: str,
        message: Optional[str] = None,
        **kwargs
    ):
        context = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "valid_next_phases": _get_valid_next_phases(from_phase),
            **kwargs.get('season_context', {})
        }

        default_message = message or f"Invalid phase transition: {from_phase} → {to_phase}"

        super().__init__(
            message=default_message,
            error_code="SEASON_PHASE_001",
            season_context=context,
            operation=kwargs.get('operation', 'phase_transition'),
            recovery_strategy="abort",
            original_exception=kwargs.get('original_exception')
        )

        self.from_phase = from_phase
        self.to_phase = to_phase


class SeasonInitializationException(SeasonException):
    """
    Raised when season initialization fails.

    Examples:
    - SeasonCycleController creation failed
    - Initial phase invalid
    - Start date invalid
    - Dynasty context missing
    - Required components failed to initialize
    """

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        **kwargs
    ):
        context = {
            "component": component,  # e.g., "calendar", "phase_tracker", "database"
            **kwargs.get('season_context', {})
        }

        super().__init__(
            message=message,
            error_code="SEASON_INIT_002",
            season_context=context,
            operation="initialization",
            recovery_strategy="reset",
            original_exception=kwargs.get('original_exception')
        )

        self.component = component


class InvalidSeasonYearException(SeasonException):
    """
    Raised when season year is invalid.

    Examples:
    - Year < 1920 (NFL founded in 1920)
    - Year > current year + 100 (unrealistic future)
    - Year mismatch between calendar and database
    - Negative year
    """

    def __init__(
        self,
        season_year: int,
        message: Optional[str] = None,
        **kwargs
    ):
        context = {
            "invalid_year": season_year,
            "min_year": 1920,
            "max_year": datetime.now().year + 100,
            **kwargs.get('season_context', {})
        }

        default_message = message or f"Invalid season year: {season_year} (must be >= 1920)"

        super().__init__(
            message=default_message,
            error_code="SEASON_YEAR_003",
            season_context=context,
            operation=kwargs.get('operation', 'validation'),
            recovery_strategy="reset",
            original_exception=kwargs.get('original_exception')
        )

        self.season_year = season_year


class PhaseTransitionFailedException(SeasonException):
    """
    Raised when phase transition execution fails.

    This is different from InvalidPhaseTransitionException - the transition
    is valid but execution failed (database write, handler error, etc.)

    Examples:
    - Transition handler raised exception
    - Database update failed during transition
    - Rollback failed
    - Post-transition verification failed
    """

    def __init__(
        self,
        from_phase: str,
        to_phase: str,
        failure_reason: str,
        **kwargs
    ):
        context = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "failure_reason": failure_reason,
            **kwargs.get('season_context', {})
        }

        message = f"Phase transition failed: {from_phase} → {to_phase}\nReason: {failure_reason}"

        super().__init__(
            message=message,
            error_code="SEASON_TRANSITION_004",
            season_context=context,
            operation="execute_phase_transition",
            recovery_strategy="rollback",
            original_exception=kwargs.get('original_exception')
        )

        self.from_phase = from_phase
        self.to_phase = to_phase
        self.failure_reason = failure_reason


class SeasonBoundaryException(SeasonException):
    """
    Raised when season boundary is violated.

    Examples:
    - Attempting to advance beyond end of season without transitioning
    - Week number > 18 during regular season
    - Date outside valid season window
    - Attempting operations in wrong phase (e.g., draft during regular season)
    """

    def __init__(
        self,
        message: str,
        boundary_type: str,
        **kwargs
    ):
        context = {
            "boundary_type": boundary_type,  # e.g., "week_limit", "date_range", "phase_operation"
            **kwargs.get('season_context', {})
        }

        super().__init__(
            message=message,
            error_code="SEASON_BOUNDARY_005",
            season_context=context,
            operation=kwargs.get('operation', 'boundary_check'),
            recovery_strategy="transition_to_next_phase",
            original_exception=kwargs.get('original_exception')
        )

        self.boundary_type = boundary_type


class InvalidSeasonStateException(SeasonException):
    """
    Raised when season state is inconsistent or corrupted.

    Examples:
    - Phase doesn't match date (playoffs in September)
    - Week number doesn't match phase
    - Calendar and phase tracker out of sync
    - State invariants violated
    """

    def __init__(
        self,
        message: str,
        state_issue: str,
        **kwargs
    ):
        context = {
            "state_issue": state_issue,
            **kwargs.get('season_context', {})
        }

        super().__init__(
            message=message,
            error_code="SEASON_STATE_006",
            season_context=context,
            operation=kwargs.get('operation', 'state_validation'),
            recovery_strategy="rollback",
            original_exception=kwargs.get('original_exception')
        )

        self.state_issue = state_issue


# Helper functions
def _get_valid_next_phases(from_phase: str) -> list:
    """Get valid next phases for a given current phase"""
    transitions = {
        "offseason": ["preseason"],
        "preseason": ["regular_season"],
        "regular_season": ["playoffs"],
        "playoffs": ["offseason"]
    }
    return transitions.get(from_phase.lower(), [])


def validate_phase_transition(from_phase: str, to_phase: str) -> bool:
    """
    Validate if a phase transition is allowed.

    Args:
        from_phase: Current phase
        to_phase: Target phase

    Returns:
        True if transition is valid

    Raises:
        InvalidPhaseTransitionException if transition is invalid
    """
    valid_next = _get_valid_next_phases(from_phase)

    if to_phase.lower() not in valid_next:
        raise InvalidPhaseTransitionException(
            from_phase=from_phase,
            to_phase=to_phase,
            message=f"Cannot transition from {from_phase} to {to_phase}. Valid next phases: {valid_next}"
        )

    return True


# Example usage patterns
if __name__ == "__main__":
    print("="*80)
    print("Season Management Exception Examples")
    print("="*80)

    # Example 1: Invalid phase transition
    print("\n1. Invalid Phase Transition:")
    try:
        raise InvalidPhaseTransitionException(
            from_phase="preseason",
            to_phase="playoffs",
            season_context={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "date": "2025-08-15"
            }
        )
    except InvalidPhaseTransitionException as e:
        print(e)
        print(f"\nValid next phases: {e.season_context['valid_next_phases']}")

    # Example 2: Season initialization failure
    print("\n" + "="*80)
    print("\n2. Season Initialization Failure:")
    try:
        raise SeasonInitializationException(
            message="Failed to initialize calendar component",
            component="calendar",
            season_context={
                "dynasty_id": "test_dynasty",
                "start_date": "2025-08-01",
                "initial_phase": "preseason"
            }
        )
    except SeasonInitializationException as e:
        print(e)
        print(f"\nComponent: {e.component}")

    # Example 3: Invalid season year
    print("\n" + "="*80)
    print("\n3. Invalid Season Year:")
    try:
        raise InvalidSeasonYearException(
            season_year=1800,
            season_context={
                "dynasty_id": "test_dynasty"
            }
        )
    except InvalidSeasonYearException as e:
        print(e)

    # Example 4: Phase transition execution failure
    print("\n" + "="*80)
    print("\n4. Phase Transition Execution Failure:")
    try:
        raise PhaseTransitionFailedException(
            from_phase="regular_season",
            to_phase="playoffs",
            failure_reason="Database update failed during transition",
            season_context={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "week": 18,
                "date": "2025-12-29"
            }
        )
    except PhaseTransitionFailedException as e:
        print(e)
        print(f"\nRecovery: {e.recovery_strategy}")

    # Example 5: Season boundary violation
    print("\n" + "="*80)
    print("\n5. Season Boundary Violation:")
    try:
        raise SeasonBoundaryException(
            message="Cannot advance beyond Week 18 without transitioning to playoffs",
            boundary_type="week_limit",
            season_context={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "current_week": 18,
                "current_phase": "regular_season",
                "attempted_week": 19
            }
        )
    except SeasonBoundaryException as e:
        print(e)

    # Example 6: Validation helper
    print("\n" + "="*80)
    print("\n6. Validation Helper:")
    try:
        validate_phase_transition("preseason", "playoffs")
    except InvalidPhaseTransitionException as e:
        print("Validation correctly caught invalid transition:")
        print(e)

    # Valid transition
    print("\n" + "="*80)
    print("\n7. Valid Transition Check:")
    try:
        is_valid = validate_phase_transition("regular_season", "playoffs")
        print(f"regular_season → playoffs: Valid = {is_valid}")
    except InvalidPhaseTransitionException as e:
        print(f"Unexpected error: {e}")

    print("\n" + "="*80)
    print("\nAll season management exceptions demonstrated successfully!")
