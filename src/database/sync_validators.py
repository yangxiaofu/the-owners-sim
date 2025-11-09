"""
Calendar-Database Synchronization Validators

This module provides pre-sync and post-sync validation to detect calendar-database
drift and prevent the silent failure bug (CALENDAR-DRIFT-2025-001).

Key Features:
- Pre-sync validation: Check system state before calendar advancement
- Post-sync verification: Verify calendar and database are synchronized after save
- Drift detection: Calculate and classify calendar-database drift
- Recovery recommendations: Suggest recovery strategies based on drift severity

Usage Example:
    from database.sync_validators import SyncValidator

    validator = SyncValidator(state_model, calendar_manager)

    # Before advancing calendar
    pre_validation = validator.validate_pre_sync()
    if not pre_validation.valid:
        raise CalendarSyncDriftException(...)

    # Advance calendar and save to database
    calendar_manager.advance_day()
    state_model.save_state(...)

    # After saving
    post_validation = validator.verify_post_sync(expected_date, expected_phase)
    if not post_validation.valid:
        raise CalendarSyncPersistenceException(...)
"""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from src.database.sync_exceptions import (
    PreSyncValidationResult,
    PostSyncVerificationResult
)


@dataclass
class DriftInfo:
    """
    Information about calendar-database drift.

    Attributes:
        drift_days: Number of days calendar is ahead/behind database
        calendar_date: Current calendar date string
        db_date: Database date string
        severity: "none", "minor", "major", or "severe"
        description: Human-readable drift description
        recovery_recommendation: Suggested recovery action
    """
    drift_days: int
    calendar_date: str
    db_date: str
    severity: str
    description: str
    recovery_recommendation: str

    @classmethod
    def from_dates(cls, calendar_date: str, db_date: str) -> 'DriftInfo':
        """
        Calculate drift information from two date strings.

        Args:
            calendar_date: Calendar date (YYYY-MM-DD)
            db_date: Database date (YYYY-MM-DD)

        Returns:
            DriftInfo instance with calculated drift
        """
        # Parse dates
        cal_dt = datetime.strptime(calendar_date, "%Y-%m-%d")
        db_dt = datetime.strptime(db_date, "%Y-%m-%d")

        # Calculate drift (calendar - database)
        drift_delta = cal_dt - db_dt
        drift_days = drift_delta.days

        # Determine severity
        if drift_days == 0:
            severity = "none"
            description = "Calendar and database are synchronized"
            recovery = "No action needed"
        elif 1 <= drift_days <= 3:
            severity = "minor"
            description = f"Minor drift detected: {drift_days} days ahead"
            recovery = "Auto-correct to calendar state"
        elif 4 <= drift_days <= 20:
            severity = "major"
            description = f"Major drift detected: {drift_days} days ahead"
            recovery = "Reload from database or restore from backup"
        else:
            severity = "severe"
            description = f"Severe drift detected: {drift_days} days ahead"
            recovery = "Contact support - database may be corrupted"

        return cls(
            drift_days=drift_days,
            calendar_date=calendar_date,
            db_date=db_date,
            severity=severity,
            description=description,
            recovery_recommendation=recovery
        )


class SyncValidator:
    """
    Validator for calendar-database synchronization.

    Provides methods to validate state before calendar advancement and
    verify synchronization after database writes. Detects and reports
    calendar-database drift to prevent silent corruption.

    Attributes:
        _state_model: SimulationDataModel for database state access
        _calendar_manager: CalendarManager for calendar date access
        _logger: Logger for validation messages
        _max_acceptable_drift: Maximum acceptable drift in days (default: 3)
    """

    def __init__(
        self,
        state_model: Any,
        calendar_manager: Any,
        max_acceptable_drift: int = 3
    ):
        """
        Initialize sync validator.

        Args:
            state_model: SimulationDataModel instance
            calendar_manager: CalendarManager instance
            max_acceptable_drift: Maximum acceptable drift before error (default: 3 days)
        """
        self._state_model = state_model
        self._calendar_manager = calendar_manager
        self._max_acceptable_drift = max_acceptable_drift
        self._logger = logging.getLogger(__name__)

    def validate_pre_sync(self) -> PreSyncValidationResult:
        """
        Validate system state before calendar advancement.

        Checks:
        1. Calendar is initialized
        2. Database state exists
        3. Calendar-database drift is within acceptable threshold
        4. Phase consistency

        Returns:
            PreSyncValidationResult with validation outcome

        Example:
            >>> validator = SyncValidator(state_model, calendar_manager)
            >>> result = validator.validate_pre_sync()
            >>> if not result.valid:
            ...     print(f"Pre-sync validation failed: {result.issues}")
        """
        issues = {}

        # Check 1: Calendar initialized
        if not self._calendar_manager:
            issues['calendar'] = "Calendar manager not initialized"
            return PreSyncValidationResult(valid=False, drift=0, issues=issues)

        try:
            calendar_date = self._calendar_manager.get_current_date()
            if not calendar_date:
                issues['calendar'] = "Calendar date is None"
                return PreSyncValidationResult(valid=False, drift=0, issues=issues)
        except Exception as e:
            issues['calendar'] = f"Failed to get calendar date: {e}"
            return PreSyncValidationResult(valid=False, drift=0, issues=issues)

        # Check 2: Database state exists
        try:
            db_state = self._state_model.get_state()
            if not db_state:
                issues['database'] = "No database state found"
                return PreSyncValidationResult(valid=False, drift=0, issues=issues)

            db_date = db_state.get('current_date')
            db_phase = db_state.get('current_phase')

            if not db_date:
                issues['database'] = "Database state missing current_date"
                return PreSyncValidationResult(valid=False, drift=0, issues=issues)

        except Exception as e:
            issues['database'] = f"Failed to load database state: {e}"
            return PreSyncValidationResult(valid=False, drift=0, issues=issues)

        # Check 3: Calendar-database drift
        calendar_date_str = str(calendar_date)
        drift_info = DriftInfo.from_dates(calendar_date_str, db_date)

        if drift_info.drift_days > self._max_acceptable_drift:
            issues['drift'] = drift_info.description
            issues['drift_days'] = drift_info.drift_days
            issues['calendar_date'] = calendar_date_str
            issues['db_date'] = db_date
            issues['recovery'] = drift_info.recovery_recommendation

            self._logger.warning(
                f"Pre-sync validation failed: {drift_info.description}\n"
                f"Calendar: {calendar_date_str}, Database: {db_date}\n"
                f"Recovery: {drift_info.recovery_recommendation}"
            )

            return PreSyncValidationResult(
                valid=False,
                drift=drift_info.drift_days,
                issues=issues
            )

        # Check 4: Phase consistency (if accessible)
        try:
            # Try to get current phase from calendar/controller
            # This is optional since phase might not be accessible
            calendar_phase = getattr(self._calendar_manager, 'current_phase', None)
            if calendar_phase and db_phase:
                if calendar_phase.lower() != db_phase.lower():
                    issues['phase_mismatch'] = (
                        f"Calendar phase '{calendar_phase}' != Database phase '{db_phase}'"
                    )
                    self._logger.warning(f"Phase mismatch detected: {issues['phase_mismatch']}")
        except Exception:
            # Phase check is optional, don't fail validation if it's not accessible
            pass

        # All checks passed
        self._logger.debug(
            f"Pre-sync validation passed. Drift: {drift_info.drift_days} days "
            f"(within threshold of {self._max_acceptable_drift})"
        )

        return PreSyncValidationResult(
            valid=True,
            drift=drift_info.drift_days,
            issues={}
        )

    def verify_post_sync(
        self,
        expected_date: str,
        expected_phase: str
    ) -> PostSyncVerificationResult:
        """
        Verify calendar and database are synchronized after save.

        Checks:
        1. Database write succeeded (date matches expected)
        2. Calendar date matches expected date
        3. Phase matches expected phase
        4. No drift between calendar and database

        Args:
            expected_date: Expected date after advancement (YYYY-MM-DD)
            expected_phase: Expected phase after advancement

        Returns:
            PostSyncVerificationResult with verification outcome

        Example:
            >>> # After calendar.advance_day() and state_model.save_state()
            >>> result = validator.verify_post_sync(
            ...     expected_date="2025-09-15",
            ...     expected_phase="regular_season"
            ... )
            >>> if not result.valid:
            ...     print(f"Post-sync verification failed: {result.issues}")
        """
        issues = {}

        # Get current calendar date
        try:
            calendar_date = self._calendar_manager.get_current_date()
            calendar_date_str = str(calendar_date)
        except Exception as e:
            issues['calendar'] = f"Failed to get calendar date: {e}"
            return PostSyncVerificationResult(
                valid=False,
                actual_calendar_date=None,
                actual_phase=None,
                drift=0,
                issues=issues
            )

        # Get current database state
        try:
            db_state = self._state_model.get_state()
            if not db_state:
                issues['database'] = "No database state found after save"
                return PostSyncVerificationResult(
                    valid=False,
                    actual_calendar_date=calendar_date_str,
                    actual_phase=None,
                    drift=0,
                    issues=issues
                )

            db_date = db_state.get('current_date')
            db_phase = db_state.get('current_phase')

        except Exception as e:
            issues['database'] = f"Failed to load database state: {e}"
            return PostSyncVerificationResult(
                valid=False,
                actual_calendar_date=calendar_date_str,
                actual_phase=None,
                drift=0,
                issues=issues
            )

        # Check 1: Database date matches expected
        if db_date != expected_date:
            issues['db_date_mismatch'] = (
                f"Database date '{db_date}' != Expected date '{expected_date}'"
            )

        # Check 2: Calendar date matches expected
        if calendar_date_str != expected_date:
            issues['calendar_date_mismatch'] = (
                f"Calendar date '{calendar_date_str}' != Expected date '{expected_date}'"
            )

        # Check 3: Phase matches expected
        if db_phase and db_phase.lower() != expected_phase.lower():
            issues['phase_mismatch'] = (
                f"Database phase '{db_phase}' != Expected phase '{expected_phase}'"
            )

        # Check 4: Calendar-database drift
        drift_info = DriftInfo.from_dates(calendar_date_str, db_date)

        if drift_info.drift_days != 0:
            issues['drift'] = drift_info.description
            issues['drift_days'] = drift_info.drift_days
            issues['calendar_date'] = calendar_date_str
            issues['db_date'] = db_date
            issues['recovery'] = drift_info.recovery_recommendation

        # Determine validity
        valid = len(issues) == 0

        if not valid:
            self._logger.error(
                f"Post-sync verification failed:\n"
                f"Expected: {expected_date} / {expected_phase}\n"
                f"Calendar: {calendar_date_str}\n"
                f"Database: {db_date} / {db_phase}\n"
                f"Issues: {issues}"
            )
        else:
            self._logger.debug(
                f"Post-sync verification passed: {expected_date} / {expected_phase}"
            )

        return PostSyncVerificationResult(
            valid=valid,
            actual_calendar_date=calendar_date_str,
            actual_phase=db_phase,
            drift=drift_info.drift_days,
            issues=issues
        )

    def calculate_drift(self) -> DriftInfo:
        """
        Calculate current calendar-database drift.

        Returns:
            DriftInfo with drift details and recovery recommendations

        Example:
            >>> validator = SyncValidator(state_model, calendar_manager)
            >>> drift_info = validator.calculate_drift()
            >>> if drift_info.severity != "none":
            ...     print(f"{drift_info.description}")
            ...     print(f"Recovery: {drift_info.recovery_recommendation}")
        """
        try:
            calendar_date = str(self._calendar_manager.get_current_date())
            db_state = self._state_model.get_state()
            db_date = db_state.get('current_date', calendar_date)

            return DriftInfo.from_dates(calendar_date, db_date)

        except Exception as e:
            self._logger.error(f"Failed to calculate drift: {e}")
            return DriftInfo(
                drift_days=0,
                calendar_date="unknown",
                db_date="unknown",
                severity="error",
                description=f"Failed to calculate drift: {e}",
                recovery_recommendation="Check database connection and calendar initialization"
            )


# Convenience functions for direct use

def validate_sync_state(
    state_model: Any,
    calendar_manager: Any,
    max_drift: int = 3
) -> PreSyncValidationResult:
    """
    Convenience function for pre-sync validation.

    Args:
        state_model: SimulationDataModel instance
        calendar_manager: CalendarManager instance
        max_drift: Maximum acceptable drift (default: 3 days)

    Returns:
        PreSyncValidationResult

    Example:
        >>> result = validate_sync_state(state_model, calendar_manager)
        >>> if not result.valid:
        ...     raise CalendarSyncDriftException(...)
    """
    validator = SyncValidator(state_model, calendar_manager, max_drift)
    return validator.validate_pre_sync()


def verify_sync_write(
    state_model: Any,
    calendar_manager: Any,
    expected_date: str,
    expected_phase: str
) -> PostSyncVerificationResult:
    """
    Convenience function for post-sync verification.

    Args:
        state_model: SimulationDataModel instance
        calendar_manager: CalendarManager instance
        expected_date: Expected date (YYYY-MM-DD)
        expected_phase: Expected phase

    Returns:
        PostSyncVerificationResult

    Example:
        >>> result = verify_sync_write(state_model, calendar_manager, "2025-09-15", "regular_season")
        >>> if not result.valid:
        ...     raise CalendarSyncPersistenceException(...)
    """
    validator = SyncValidator(state_model, calendar_manager)
    return validator.verify_post_sync(expected_date, expected_phase)


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Sync Validator Examples")
    print("=" * 80)

    # Mock classes for demonstration
    class MockStateModel:
        def __init__(self, date: str, phase: str):
            self.date = date
            self.phase = phase

        def get_state(self):
            return {
                'current_date': self.date,
                'current_phase': self.phase
            }

    class MockCalendarManager:
        def __init__(self, date: str):
            self.date = date

        def get_current_date(self):
            return self.date

    # Example 1: No drift (perfect sync)
    print("\n1. Perfect Synchronization:")
    state_model = MockStateModel("2025-09-15", "regular_season")
    calendar = MockCalendarManager("2025-09-15")

    result = validate_sync_state(state_model, calendar)
    print(f"Valid: {result.valid}")
    print(f"Drift: {result.drift} days")

    # Example 2: Minor drift (3 days)
    print("\n" + "=" * 80)
    print("\n2. Minor Drift (3 days):")
    state_model = MockStateModel("2025-09-12", "regular_season")
    calendar = MockCalendarManager("2025-09-15")

    result = validate_sync_state(state_model, calendar)
    print(f"Valid: {result.valid}")
    print(f"Drift: {result.drift} days")

    # Example 3: Major drift (116 days - actual bug)
    print("\n" + "=" * 80)
    print("\n3. Major Drift (116 days - CALENDAR-DRIFT-2025-001):")
    state_model = MockStateModel("2025-11-09", "playoffs")
    calendar = MockCalendarManager("2026-03-03")

    result = validate_sync_state(state_model, calendar, max_drift=3)
    print(f"Valid: {result.valid}")
    print(f"Drift: {result.drift} days")
    print(f"Issues: {result.issues}")

    # Calculate drift info
    validator = SyncValidator(state_model, calendar)
    drift_info = validator.calculate_drift()
    print(f"\nDrift Info:")
    print(f"  Severity: {drift_info.severity}")
    print(f"  Description: {drift_info.description}")
    print(f"  Recovery: {drift_info.recovery_recommendation}")

    # Example 4: Post-sync verification
    print("\n" + "=" * 80)
    print("\n4. Post-Sync Verification:")
    state_model = MockStateModel("2025-09-16", "regular_season")
    calendar = MockCalendarManager("2025-09-16")

    result = verify_sync_write(
        state_model,
        calendar,
        expected_date="2025-09-16",
        expected_phase="regular_season"
    )
    print(f"Valid: {result.valid}")
    print(f"Drift: {result.drift} days")
    print(f"Actual calendar date: {result.actual_calendar_date}")
    print(f"Actual phase: {result.actual_phase}")

    print("\n" + "=" * 80)
    print("\nAll sync validator examples completed successfully!")
