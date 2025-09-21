"""
Persistence Result Models

Value objects for representing the outcome of persistence operations.
Provides structured success/failure information with detailed error reporting.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PersistenceResult:
    """
    Result object for statistics persistence operations.

    Provides comprehensive information about the success or failure
    of persistence operations, including detailed error reporting
    and operation metadata.
    """

    success: bool
    operation_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Success metrics
    records_processed: int = 0
    records_persisted: int = 0
    processing_time_ms: float = 0.0

    # Error information
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Operation details
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error_message: str) -> None:
        """
        Add an error message to the result.

        Args:
            error_message: Descriptive error message
        """
        self.errors.append(error_message)
        self.success = False

    def add_warning(self, warning_message: str) -> None:
        """
        Add a warning message to the result.

        Args:
            warning_message: Descriptive warning message
        """
        self.warnings.append(warning_message)

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the result.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the persistence result.

        Returns:
            String summary of the operation
        """
        status = "SUCCESS" if self.success else "FAILED"
        summary = f"Persistence {status}: {self.records_persisted}/{self.records_processed} records"

        if self.errors:
            summary += f", {len(self.errors)} errors"

        if self.warnings:
            summary += f", {len(self.warnings)} warnings"

        summary += f", {self.processing_time_ms:.1f}ms"

        return summary

    def has_errors(self) -> bool:
        """Check if the result has any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if the result has any warnings."""
        return len(self.warnings) > 0

    def is_success(self) -> bool:
        """Check if the operation was successful."""
        return self.success

    def __str__(self) -> str:
        """String representation of the result."""
        return self.get_summary()


@dataclass
class ValidationResult:
    """
    Result object for validation operations.

    Used during data validation phases to track
    validation success/failure and specific issues.
    """

    valid: bool
    field_errors: Dict[str, List[str]] = field(default_factory=dict)
    general_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_field_error(self, field_name: str, error_message: str) -> None:
        """
        Add a field-specific validation error.

        Args:
            field_name: Name of the field with the error
            error_message: Descriptive error message
        """
        if field_name not in self.field_errors:
            self.field_errors[field_name] = []
        self.field_errors[field_name].append(error_message)
        self.valid = False

    def add_general_error(self, error_message: str) -> None:
        """
        Add a general validation error.

        Args:
            error_message: Descriptive error message
        """
        self.general_errors.append(error_message)
        self.valid = False

    def add_warning(self, warning_message: str) -> None:
        """
        Add a validation warning.

        Args:
            warning_message: Descriptive warning message
        """
        self.warnings.append(warning_message)

    def get_all_errors(self) -> List[str]:
        """
        Get all errors (field-specific and general) as a flat list.

        Returns:
            List of all error messages
        """
        all_errors = self.general_errors.copy()

        for field_name, field_error_list in self.field_errors.items():
            for error in field_error_list:
                all_errors.append(f"{field_name}: {error}")

        return all_errors

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid

    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return not self.valid

    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return len(self.warnings) > 0