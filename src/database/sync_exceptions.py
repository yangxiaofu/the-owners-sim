"""
Calendar-Database Synchronization Exception Hierarchy

This module defines exceptions for calendar-database synchronization failures,
addressing the root cause of the calendar drift bug (CALENDAR-DRIFT-2025-001).

These exceptions implement the fail-loud philosophy, ensuring database save
failures are immediately surfaced instead of failing silently.

Exception Hierarchy:
    CalendarDatabaseSyncException (base)
    ├── CalendarSyncInitializationException
    ├── CalendarSyncDriftException
    ├── CalendarSyncPersistenceException
    └── CalendarSyncPhaseException

All exceptions track:
- Sync point (where failure occurred)
- Sync type (read, write, verify)
- State information (calendar date, DB date, phase, etc.)
- User recoverability (can user fix this?)
- Recovery action (what to do next)
"""

from typing import Any, Dict, Optional
from datetime import datetime


class CalendarDatabaseSyncException(Exception):
    """
    Base exception for calendar-database synchronization failures.

    Raised when calendar state (in-memory) diverges from database state
    and cannot be automatically recovered. This is the root exception for
    all calendar-database sync issues.

    Attributes:
        message: Human-readable error message
        sync_point: Where failure occurred (e.g., "advance_day", "initialize")
        sync_type: Type of sync operation ("read", "write", "verify")
        error_code: Unique error code for this failure
        state_info: State information (calendar date, DB date, phase, etc.)
        user_recoverable: Can the user recover from this error?
        recovery_action: What action should be taken
        timestamp: When the exception was raised
    """

    def __init__(
        self,
        message: str,
        sync_point: str,
        sync_type: str,
        error_code: str = "SYNC_000",
        state_info: Optional[Dict[str, Any]] = None,
        user_recoverable: bool = False,
        recovery_action: Optional[str] = None
    ):
        self.message = message
        self.sync_point = sync_point
        self.sync_type = sync_type
        self.error_code = error_code
        self.state_info = state_info or {}
        self.user_recoverable = user_recoverable
        self.recovery_action = recovery_action
        self.timestamp = datetime.now().isoformat()

        # Build detailed error message
        full_message = self._build_error_message()
        super().__init__(full_message)

    def _build_error_message(self) -> str:
        """Build comprehensive error message with all context"""
        lines = [
            f"[{self.error_code}] {self.message}",
            f"Sync Point: {self.sync_point} ({self.sync_type})",
            f"Timestamp: {self.timestamp}"
        ]

        if self.state_info:
            lines.append("State Information:")
            for key, value in self.state_info.items():
                lines.append(f"  {key}: {value}")

        if self.recovery_action:
            lines.append(f"\nRecovery Action: {self.recovery_action}")

        if self.user_recoverable:
            lines.append("This error may be recoverable by the user")
        else:
            lines.append("This error requires system intervention")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "sync_point": self.sync_point,
            "sync_type": self.sync_type,
            "state_info": self.state_info,
            "user_recoverable": self.user_recoverable,
            "recovery_action": self.recovery_action,
            "timestamp": self.timestamp
        }


class CalendarSyncInitializationException(CalendarDatabaseSyncException):
    """
    Raised when calendar-database initialization or loading fails.

    Examples:
    - Calendar not initialized before advancement
    - Database state not found for dynasty
    - State loading failed during controller creation
    - Invalid state data in database
    """

    def __init__(
        self,
        message: str,
        state_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            sync_point=kwargs.get('sync_point', 'initialization'),
            sync_type=kwargs.get('sync_type', 'read'),
            error_code="SYNC_INIT_001",
            state_info=state_info,
            user_recoverable=True,
            recovery_action="Reload simulation or restart dynasty"
        )


class CalendarSyncDriftException(CalendarDatabaseSyncException):
    """
    Raised when calendar-database drift is detected.

    This exception is raised when the calendar state (in-memory) and database
    state diverge beyond acceptable thresholds. This prevents the silent
    corruption bug documented in CALENDAR-DRIFT-2025-001.

    Drift Levels:
    - Minor (1-3 days): Auto-correct possible
    - Major (4+ days): Requires user intervention
    - Severe (phase mismatch): System broken

    Examples:
    - Calendar shows March 3, database shows November 9
    - Calendar phase differs from database phase
    - Week counter doesn't match phase
    """

    def __init__(
        self,
        calendar_date: str,
        db_date: str,
        drift_days: int,
        sync_point: str = "drift_detection",
        state_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        # Determine severity and recovery based on drift
        if drift_days <= 3:
            severity = "minor"
            user_recoverable = True
            recovery_action = "Auto-correct to calendar state"
        elif drift_days <= 20:
            severity = "major"
            user_recoverable = True
            recovery_action = "Reload from database or restore from backup"
        else:
            severity = "severe"
            user_recoverable = False
            recovery_action = "Contact support - database may be corrupted"

        # Build state info
        full_state_info = {
            "calendar_date": calendar_date,
            "db_date": db_date,
            "drift_days": drift_days,
            "severity": severity,
            **(state_info or {})
        }

        message = f"Calendar-database drift detected: {drift_days} days\n"
        message += f"Calendar: {calendar_date}, Database: {db_date}"

        super().__init__(
            message=message,
            sync_point=sync_point,
            sync_type=kwargs.get('sync_type', 'verify'),
            error_code="SYNC_DRIFT_002",
            state_info=full_state_info,
            user_recoverable=user_recoverable,
            recovery_action=recovery_action
        )

        # Store severity for external access
        self.drift_severity = severity
        self.drift_days = drift_days


class CalendarSyncPersistenceException(CalendarDatabaseSyncException):
    """
    Raised when database persistence fails.

    This exception addresses the root cause of CALENDAR-DRIFT-2025-001.
    Instead of silently returning False when database saves fail, this
    exception is raised to fail-loud and prevent data corruption.

    Examples:
    - Dynasty state write failed
    - Database connection lost
    - Transaction rollback failed
    - Post-save verification failed (written data doesn't match expected)
    """

    def __init__(
        self,
        operation: str,
        sync_point: str = "persistence",
        state_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        message = f"Failed to persist {operation} to database"

        super().__init__(
            message=message,
            sync_point=sync_point,
            sync_type="write",
            error_code="SYNC_PERSIST_003",
            state_info=state_info,
            user_recoverable=True,
            recovery_action="Retry save or reload from database"
        )

        self.operation = operation


class CalendarSyncPhaseException(CalendarDatabaseSyncException):
    """
    Raised when phase consistency is violated between calendar and database.

    Phase mismatches indicate critical state corruption where the calendar
    thinks it's in one phase but the database shows a different phase.

    Examples:
    - Calendar shows "offseason" but database shows "playoffs"
    - Phase transition incomplete (calendar advanced but database didn't)
    - Week counter doesn't match phase (week 20 during regular season)
    """

    def __init__(
        self,
        calendar_phase: str,
        db_phase: str,
        sync_point: str = "phase_verification",
        state_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        full_state_info = {
            "calendar_phase": calendar_phase,
            "db_phase": db_phase,
            **(state_info or {})
        }

        message = f"Phase mismatch between calendar and database:\n"
        message += f"Calendar: {calendar_phase}, Database: {db_phase}"

        super().__init__(
            message=message,
            sync_point=sync_point,
            sync_type=kwargs.get('sync_type', 'verify'),
            error_code="SYNC_PHASE_004",
            state_info=full_state_info,
            user_recoverable=True,
            recovery_action="Reload from database to restore phase consistency"
        )

        self.calendar_phase = calendar_phase
        self.db_phase = db_phase


# Validation Result Classes
class PreSyncValidationResult:
    """
    Result of pre-sync validation checks.

    Returned by validation methods before calendar advancement to ensure
    system is in a valid state before making changes.
    """

    def __init__(
        self,
        valid: bool,
        drift: int = 0,
        issues: Optional[Dict[str, Any]] = None
    ):
        self.valid = valid
        self.drift = drift
        self.issues = issues or {}

    def __bool__(self) -> bool:
        return self.valid


class PostSyncVerificationResult:
    """
    Result of post-sync verification checks.

    Returned by verification methods after calendar advancement to ensure
    calendar and database are synchronized.
    """

    def __init__(
        self,
        valid: bool,
        actual_calendar_date: Optional[str] = None,
        actual_phase: Optional[str] = None,
        drift: int = 0,
        issues: Optional[Dict[str, Any]] = None
    ):
        self.valid = valid
        self.actual_calendar_date = actual_calendar_date
        self.actual_phase = actual_phase
        self.drift = drift
        self.issues = issues or {}

    def __bool__(self) -> bool:
        return self.valid


# Example usage patterns
if __name__ == "__main__":
    print("="*80)
    print("Calendar-Database Sync Exception Examples")
    print("="*80)

    # Example 1: Minor drift (auto-correctable)
    print("\n1. Minor Drift (3 days):")
    try:
        raise CalendarSyncDriftException(
            calendar_date="2025-09-15",
            db_date="2025-09-12",
            drift_days=3,
            sync_point="advance_day",
            state_info={
                "dynasty_id": "test_dynasty",
                "season": 2025,
                "phase": "regular_season"
            }
        )
    except CalendarSyncDriftException as e:
        print(e)
        print(f"\nSeverity: {e.drift_severity}")
        print(f"Recoverable: {e.user_recoverable}")

    # Example 2: Major drift (requires intervention)
    print("\n" + "="*80)
    print("\n2. Major Drift (116 days - actual bug):")
    try:
        raise CalendarSyncDriftException(
            calendar_date="2026-03-03",
            db_date="2025-11-09",
            drift_days=116,
            sync_point="advance_to_end_of_phase",
            state_info={
                "dynasty_id": "1st",
                "season": 2025,
                "calendar_phase": "offseason",
                "db_phase": "playoffs"
            }
        )
    except CalendarSyncDriftException as e:
        print(e)
        print(f"\nSeverity: {e.drift_severity}")
        print(f"Recovery: {e.recovery_action}")

    # Example 3: Persistence failure
    print("\n" + "="*80)
    print("\n3. Database Persistence Failure:")
    try:
        raise CalendarSyncPersistenceException(
            operation="dynasty state update",
            sync_point="advance_day",
            state_info={
                "intended_date": "2025-09-15",
                "intended_phase": "regular_season",
                "intended_week": 3,
                "error": "SQLite database is locked"
            }
        )
    except CalendarSyncPersistenceException as e:
        print(e)
        print(f"\nOperation: {e.operation}")
        print(f"As dict: {e.to_dict()}")

    # Example 4: Phase mismatch
    print("\n" + "="*80)
    print("\n4. Phase Consistency Violation:")
    try:
        raise CalendarSyncPhaseException(
            calendar_phase="offseason",
            db_phase="playoffs",
            sync_point="post_advancement_verification",
            state_info={
                "dynasty_id": "1st",
                "season": 2025,
                "date": "2026-03-03",
                "expected_phase": "offseason"
            }
        )
    except CalendarSyncPhaseException as e:
        print(e)

    # Example 5: Initialization failure
    print("\n" + "="*80)
    print("\n5. Initialization Failure:")
    try:
        raise CalendarSyncInitializationException(
            message="Calendar not initialized before advancement",
            state_info={
                "dynasty_id": "test_dynasty",
                "context": "pre_advance_validation"
            }
        )
    except CalendarSyncInitializationException as e:
        print(e)
        print(f"\nRecovery: {e.recovery_action}")

    print("\n" + "="*80)
    print("\nAll calendar-database sync exceptions demonstrated successfully!")
