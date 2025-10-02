"""
Persistence Result Classes

Provides detailed feedback about persistence operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class PersistenceStatus(Enum):
    """Status of persistence operation"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ROLLBACK = "rollback"


@dataclass
class PersistenceResult:
    """
    Result of a persistence operation with detailed metrics.

    Provides comprehensive feedback for debugging and monitoring.
    """
    status: PersistenceStatus
    timestamp: datetime = field(default_factory=datetime.now)

    # Metrics
    records_persisted: int = 0
    records_failed: int = 0
    processing_time_ms: float = 0.0

    # Details
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Transaction info
    transaction_id: Optional[str] = None
    rollback_performed: bool = False

    @property
    def success(self) -> bool:
        """Check if operation was successful"""
        return self.status == PersistenceStatus.SUCCESS

    @property
    def total_records(self) -> int:
        """Total records processed"""
        return self.records_persisted + self.records_failed

    @property
    def success_rate(self) -> float:
        """Percentage of successful records"""
        if self.total_records == 0:
            return 0.0
        return (self.records_persisted / self.total_records) * 100

    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
        self.records_failed += 1

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata"""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'records_persisted': self.records_persisted,
            'records_failed': self.records_failed,
            'processing_time_ms': self.processing_time_ms,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'transaction_id': self.transaction_id,
            'rollback_performed': self.rollback_performed,
            'success_rate': self.success_rate
        }

    def __str__(self) -> str:
        """String representation"""
        return (f"PersistenceResult(status={self.status.value}, "
                f"persisted={self.records_persisted}, "
                f"failed={self.records_failed}, "
                f"time={self.processing_time_ms:.2f}ms)")


@dataclass
class CompositePersistenceResult:
    """
    Result of multiple persistence operations combined.

    Useful for orchestrators that perform multiple persistence steps.
    """
    overall_status: PersistenceStatus
    results: Dict[str, PersistenceResult] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def total_records_persisted(self) -> int:
        """Total records persisted across all operations"""
        return sum(r.records_persisted for r in self.results.values())

    @property
    def total_records_failed(self) -> int:
        """Total records failed across all operations"""
        return sum(r.records_failed for r in self.results.values())

    @property
    def total_processing_time_ms(self) -> float:
        """Total processing time across all operations"""
        return sum(r.processing_time_ms for r in self.results.values())

    @property
    def all_errors(self) -> List[str]:
        """All errors from all operations"""
        errors = []
        for operation, result in self.results.items():
            for error in result.errors:
                errors.append(f"{operation}: {error}")
        return errors

    @property
    def all_warnings(self) -> List[str]:
        """All warnings from all operations"""
        warnings = []
        for operation, result in self.results.items():
            for warning in result.warnings:
                warnings.append(f"{operation}: {warning}")
        return warnings

    @property
    def success(self) -> bool:
        """Check if all operations were successful"""
        return self.overall_status == PersistenceStatus.SUCCESS

    def add_result(self, operation_name: str, result: PersistenceResult) -> None:
        """Add a result from an operation"""
        self.results[operation_name] = result

        # Update overall status
        if not result.success:
            if self.overall_status == PersistenceStatus.SUCCESS:
                self.overall_status = PersistenceStatus.PARTIAL_SUCCESS
            if result.status == PersistenceStatus.FAILURE:
                self.overall_status = PersistenceStatus.FAILURE

    def finalize(self) -> None:
        """Mark the composite operation as complete"""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all operations"""
        return {
            'overall_status': self.overall_status.value,
            'total_operations': len(self.results),
            'total_records_persisted': self.total_records_persisted,
            'total_records_failed': self.total_records_failed,
            'total_processing_time_ms': self.total_processing_time_ms,
            'operations': {
                name: result.to_dict()
                for name, result in self.results.items()
            },
            'errors_count': len(self.all_errors),
            'warnings_count': len(self.all_warnings)
        }

    def __str__(self) -> str:
        """String representation"""
        return (f"CompositePersistenceResult(status={self.overall_status.value}, "
                f"operations={len(self.results)}, "
                f"persisted={self.total_records_persisted}, "
                f"failed={self.total_records_failed})")
