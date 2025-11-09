"""
Playoff System Exception Hierarchy

This module defines a comprehensive exception hierarchy for the playoff system,
providing production-grade error handling with error codes, severity levels,
recovery strategies, and rich context information.

Exception Hierarchy:
    PlayoffException (base)
    ├── InvalidRoundException
    ├── InvalidSeedingException
    ├── InvalidBracketException
    ├── PlayoffStateException
    ├── PlayoffSchedulingException
    ├── PlayoffSynchronizationException
    └── InsufficientTeamDataException

All exceptions include:
- error_code: Unique identifier for programmatic handling
- severity: CRITICAL, ERROR, WARNING, INFO
- recovery_strategy: ABORT, RETRY, SKIP, ROLLBACK, RESET
- context_dict: Relevant context (dynasty_id, season, round, etc.)
- original_exception: Wrapped exception if from try/except
"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime


class ExceptionSeverity(Enum):
    """Severity levels for exceptions"""
    CRITICAL = "critical"  # System broken, immediate abort required
    ERROR = "error"        # Operation failed, cannot continue
    WARNING = "warning"    # Potential issue, can continue with caution
    INFO = "info"          # Informational only, no action required


class RecoveryStrategy(Enum):
    """Recovery strategies for exception handling"""
    ABORT = "abort"          # Stop all operations immediately
    RETRY = "retry"          # Retry the failed operation
    SKIP = "skip"            # Skip this operation and continue
    ROLLBACK = "rollback"    # Rollback to previous state
    RESET = "reset"          # Reset state and restart
    MANUAL = "manual"        # Requires manual intervention


class PlayoffException(Exception):
    """
    Base exception for all playoff system errors.

    This is the root of the playoff exception hierarchy. All playoff-specific
    exceptions should inherit from this class.

    Attributes:
        message: Human-readable error message
        error_code: Unique error code (e.g., "PLAYOFF_001")
        severity: Exception severity level
        recovery_strategy: Recommended recovery action
        context_dict: Additional context (dynasty_id, season, round, etc.)
        original_exception: Original exception if wrapping another exception
        timestamp: When the exception was raised
    """

    def __init__(
        self,
        message: str,
        error_code: str = "PLAYOFF_000",
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.ABORT,
        context_dict: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context_dict = context_dict or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now().isoformat()

        # Build detailed error message
        full_message = self._build_error_message()
        super().__init__(full_message)

    def _build_error_message(self) -> str:
        """Build comprehensive error message with all context"""
        lines = [
            f"[{self.error_code}] {self.message}",
            f"Severity: {self.severity.value}",
            f"Recovery: {self.recovery_strategy.value}",
            f"Timestamp: {self.timestamp}"
        ]

        if self.context_dict:
            lines.append("Context:")
            for key, value in self.context_dict.items():
                lines.append(f"  {key}: {value}")

        if self.original_exception:
            lines.append(f"Original Error: {type(self.original_exception).__name__}: {str(self.original_exception)}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "recovery_strategy": self.recovery_strategy.value,
            "context": self.context_dict,
            "timestamp": self.timestamp,
            "original_error": str(self.original_exception) if self.original_exception else None
        }


class InvalidRoundException(PlayoffException):
    """
    Raised when an invalid playoff round is specified or encountered.

    Examples:
    - Round name not in ['wild_card', 'divisional', 'conference', 'super_bowl']
    - Attempting to access a round that doesn't exist
    - Round progression violation (e.g., jumping from Wild Card to Conference)
    """

    def __init__(
        self,
        round_name: str,
        message: Optional[str] = None,
        valid_rounds: Optional[list] = None,
        **kwargs
    ):
        context = {
            "invalid_round": round_name,
            "valid_rounds": valid_rounds or ['wild_card', 'divisional', 'conference', 'super_bowl'],
            **kwargs.get('context_dict', {})
        }

        default_message = message or f"Invalid playoff round: '{round_name}'"

        super().__init__(
            message=default_message,
            error_code="PLAYOFF_ROUND_001",
            severity=ExceptionSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.ABORT,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class InvalidSeedingException(PlayoffException):
    """
    Raised when playoff seeding data is invalid or incomplete.

    Examples:
    - Missing seeds (not 7 per conference)
    - Invalid seed numbers (not 1-7)
    - Missing division winner flags
    - Duplicate team IDs in seeding
    - Team ID outside valid range (1-32)
    """

    def __init__(
        self,
        message: str,
        conference: Optional[str] = None,
        seed_number: Optional[int] = None,
        team_id: Optional[int] = None,
        **kwargs
    ):
        context = {
            "conference": conference,
            "seed_number": seed_number,
            "team_id": team_id,
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_SEED_002",
            severity=ExceptionSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.RESET,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class InvalidBracketException(PlayoffException):
    """
    Raised when playoff bracket structure is invalid.

    Examples:
    - Wrong number of games per round (Wild Card: 6, Divisional: 4, Conference: 2, SB: 1)
    - Conference distribution incorrect (should be 50/50 split except Super Bowl)
    - Game matchups invalid (same team on both sides, invalid seed matchups)
    - Bracket exists for unscheduled round
    """

    def __init__(
        self,
        message: str,
        round_name: Optional[str] = None,
        expected_game_count: Optional[int] = None,
        actual_game_count: Optional[int] = None,
        **kwargs
    ):
        context = {
            "round": round_name,
            "expected_games": expected_game_count,
            "actual_games": actual_game_count,
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_BRACKET_003",
            severity=ExceptionSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.RESET,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class PlayoffStateException(PlayoffException):
    """
    Raised when playoff system state is inconsistent or corrupted.

    Examples:
    - Current round doesn't match completed rounds
    - Game counts don't match (total_games_played != sum of completed_games)
    - Bracket state doesn't match database state
    - Round marked complete but has incomplete games
    - State invariants violated
    """

    def __init__(
        self,
        message: str,
        current_round: Optional[str] = None,
        total_games_played: Optional[int] = None,
        total_days_simulated: Optional[int] = None,
        **kwargs
    ):
        context = {
            "current_round": current_round,
            "total_games_played": total_games_played,
            "total_days_simulated": total_days_simulated,
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_STATE_004",
            severity=ExceptionSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.ROLLBACK,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class PlayoffSchedulingException(PlayoffException):
    """
    Raised when playoff game scheduling fails.

    Examples:
    - Failed to schedule next round
    - Game date conflicts
    - Cannot determine next matchups from completed games
    - Event creation failed
    - Insufficient completed games to advance round
    """

    def __init__(
        self,
        message: str,
        round_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = {
            "round": round_name,
            "operation": operation,  # e.g., "schedule_next_round", "create_events"
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_SCHEDULE_005",
            severity=ExceptionSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.RETRY,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class PlayoffSynchronizationException(PlayoffException):
    """
    Raised when playoff state synchronization fails.

    Examples:
    - Calendar and database out of sync
    - In-memory bracket doesn't match database events
    - Completed games mismatch between memory and database
    - Dynasty isolation violated
    """

    def __init__(
        self,
        message: str,
        sync_type: Optional[str] = None,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        **kwargs
    ):
        context = {
            "sync_type": sync_type,  # e.g., "calendar_database", "bracket_events", "game_counts"
            "expected": str(expected_value),
            "actual": str(actual_value),
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_SYNC_006",
            severity=ExceptionSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.ROLLBACK,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


class InsufficientTeamDataException(PlayoffException):
    """
    Raised when required team data is missing for playoff operations.

    Examples:
    - Cannot load team by ID
    - Team conference information missing
    - Team division information missing
    - Standings data incomplete
    """

    def __init__(
        self,
        message: str,
        team_id: Optional[int] = None,
        missing_field: Optional[str] = None,
        **kwargs
    ):
        context = {
            "team_id": team_id,
            "missing_field": missing_field,
            **kwargs.get('context_dict', {})
        }

        super().__init__(
            message=message,
            error_code="PLAYOFF_TEAM_007",
            severity=ExceptionSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.SKIP,
            context_dict=context,
            original_exception=kwargs.get('original_exception')
        )


# Convenience function for wrapping exceptions
def wrap_exception(
    original: Exception,
    message: str,
    exception_class: type = PlayoffException,
    **kwargs
) -> PlayoffException:
    """
    Wrap an existing exception in a PlayoffException.

    This is useful for converting generic exceptions (ValueError, RuntimeError, etc.)
    into playoff-specific exceptions with rich context.

    Args:
        original: The original exception to wrap
        message: New error message
        exception_class: Which PlayoffException subclass to use
        **kwargs: Additional context to include

    Returns:
        New PlayoffException wrapping the original

    Example:
        >>> try:
        ...     some_operation()
        ... except ValueError as e:
        ...     raise wrap_exception(
        ...         e,
        ...         "Failed to schedule playoff round",
        ...         exception_class=PlayoffSchedulingException,
        ...         round_name="divisional",
        ...         dynasty_id="my_dynasty"
        ...     )
    """
    context = kwargs.pop('context_dict', {})
    context.update(kwargs)

    return exception_class(
        message=message,
        context_dict=context,
        original_exception=original
    )


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Invalid round
    try:
        round_name = "quarter_finals"  # Invalid
        raise InvalidRoundException(
            round_name=round_name,
            message=f"Round '{round_name}' is not a valid NFL playoff round"
        )
    except InvalidRoundException as e:
        print(e)
        print("\nAs dict:", e.to_dict())

    print("\n" + "="*80 + "\n")

    # Example 2: Bracket consistency error
    try:
        raise InvalidBracketException(
            message="Wild Card round has wrong number of games",
            round_name="wild_card",
            expected_game_count=6,
            actual_game_count=5,
            context_dict={
                "dynasty_id": "test_dynasty",
                "season": 2025
            }
        )
    except InvalidBracketException as e:
        print(e)

    print("\n" + "="*80 + "\n")

    # Example 3: State corruption with rollback
    try:
        raise PlayoffStateException(
            message="Game counts don't match: total_games_played != sum of completed_games",
            current_round="divisional",
            total_games_played=12,
            total_days_simulated=28,
            context_dict={
                "dynasty_id": "corrupted_dynasty",
                "season": 2025,
                "expected_games": 10,
                "actual_games": 12
            }
        )
    except PlayoffStateException as e:
        print(e)
        print(f"\nRecovery: {e.recovery_strategy.value}")

    print("\n" + "="*80 + "\n")

    # Example 4: Wrapping generic exception
    try:
        # Simulated ValueError from some library
        raise ValueError("Cannot schedule games with same team ID on both sides")
    except ValueError as e:
        wrapped = wrap_exception(
            e,
            "Playoff scheduling failed during bracket generation",
            exception_class=PlayoffSchedulingException,
            round_name="wild_card",
            operation="generate_bracket",
            dynasty_id="test_dynasty",
            season=2025
        )
        print(wrapped)
