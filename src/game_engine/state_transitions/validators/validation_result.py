"""
Validation Result Data Structures

Provides comprehensive data structures for representing validation results,
including success/failure states and detailed error information.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"        # Prevents state transition
    WARNING = "warning"    # Allows transition but flags issue
    INFO = "info"         # Informational only


class ValidationCategory(Enum):
    """Categories of validation rules"""
    FIELD_BOUNDS = "field_bounds"
    DOWN_DISTANCE = "down_distance"
    POSSESSION_CHANGE = "possession_change" 
    SCORING_RULES = "scoring_rules"
    CLOCK_CONSTRAINTS = "clock_constraints"
    NFL_RULES = "nfl_rules"
    GAME_STATE = "game_state"


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    rule_reference: Optional[str] = None
    
    def __str__(self) -> str:
        """Human-readable representation of the validation issue"""
        parts = [f"[{self.severity.value.upper()}] {self.message}"]
        
        if self.field_name:
            parts.append(f"Field: {self.field_name}")
            
        if self.current_value is not None:
            parts.append(f"Current: {self.current_value}")
            
        if self.expected_value is not None:
            parts.append(f"Expected: {self.expected_value}")
            
        if self.rule_reference:
            parts.append(f"Rule: {self.rule_reference}")
            
        return " | ".join(parts)


@dataclass
class ValidationResult:
    """Comprehensive validation result containing all issues and summary"""
    
    is_valid: bool
    issues: List[ValidationIssue]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided"""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues"""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues"""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    @property  
    def error_count(self) -> int:
        """Count of error-level issues"""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues"""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
    
    def get_issues_by_category(self, category: ValidationCategory) -> List[ValidationIssue]:
        """Get all issues for a specific category"""
        return [issue for issue in self.issues if issue.category == category]
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues for a specific severity level"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the result"""
        self.issues.append(issue)
        # Update validity based on error presence
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge another validation result into this one"""
        merged_issues = self.issues + other.issues
        merged_metadata = {**self.metadata, **other.metadata}
        
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            issues=merged_issues,
            metadata=merged_metadata
        )
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the validation result"""
        if self.is_valid:
            if not self.issues:
                return "Validation passed with no issues"
            else:
                return f"Validation passed with {self.warning_count} warning(s)"
        else:
            return f"Validation failed with {self.error_count} error(s) and {self.warning_count} warning(s)"
    
    def get_detailed_report(self) -> str:
        """Get a detailed report of all validation issues"""
        if not self.issues:
            return "No validation issues found"
        
        report = [self.get_summary(), ""]
        
        # Group issues by category
        categories = {}
        for issue in self.issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)
        
        for category, issues in categories.items():
            report.append(f"{category.value.upper().replace('_', ' ')} Issues:")
            for issue in issues:
                report.append(f"  - {issue}")
            report.append("")
        
        return "\n".join(report)


class ValidationResultBuilder:
    """Builder pattern for constructing validation results"""
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.metadata: Dict[str, Any] = {}
        self._is_valid = True
    
    def add_error(self, category: ValidationCategory, message: str, 
                  field_name: Optional[str] = None, current_value: Optional[Any] = None,
                  expected_value: Optional[Any] = None, rule_reference: Optional[str] = None) -> 'ValidationResultBuilder':
        """Add an error-level validation issue"""
        issue = ValidationIssue(
            category=category,
            severity=ValidationSeverity.ERROR,
            message=message,
            field_name=field_name,
            current_value=current_value,
            expected_value=expected_value,
            rule_reference=rule_reference
        )
        self.issues.append(issue)
        self._is_valid = False
        return self
    
    def add_warning(self, category: ValidationCategory, message: str,
                    field_name: Optional[str] = None, current_value: Optional[Any] = None,
                    expected_value: Optional[Any] = None, rule_reference: Optional[str] = None) -> 'ValidationResultBuilder':
        """Add a warning-level validation issue"""
        issue = ValidationIssue(
            category=category,
            severity=ValidationSeverity.WARNING,
            message=message,
            field_name=field_name,
            current_value=current_value,
            expected_value=expected_value,
            rule_reference=rule_reference
        )
        self.issues.append(issue)
        return self
    
    def add_info(self, category: ValidationCategory, message: str,
                 field_name: Optional[str] = None, current_value: Optional[Any] = None,
                 expected_value: Optional[Any] = None, rule_reference: Optional[str] = None) -> 'ValidationResultBuilder':
        """Add an info-level validation issue"""
        issue = ValidationIssue(
            category=category,
            severity=ValidationSeverity.INFO,
            message=message,
            field_name=field_name,
            current_value=current_value,
            expected_value=expected_value,
            rule_reference=rule_reference
        )
        self.issues.append(issue)
        return self
    
    def add_metadata(self, key: str, value: Any) -> 'ValidationResultBuilder':
        """Add metadata to the validation result"""
        self.metadata[key] = value
        return self
    
    def build(self) -> ValidationResult:
        """Build the final validation result"""
        return ValidationResult(
            is_valid=self._is_valid,
            issues=self.issues.copy(),
            metadata=self.metadata.copy()
        )


def create_success_result(metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Create a successful validation result with no issues"""
    return ValidationResult(
        is_valid=True,
        issues=[],
        metadata=metadata or {}
    )


def create_error_result(category: ValidationCategory, message: str,
                       field_name: Optional[str] = None, current_value: Optional[Any] = None,
                       expected_value: Optional[Any] = None, rule_reference: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Create a validation result with a single error"""
    issue = ValidationIssue(
        category=category,
        severity=ValidationSeverity.ERROR,
        message=message,
        field_name=field_name,
        current_value=current_value,
        expected_value=expected_value,
        rule_reference=rule_reference
    )
    
    return ValidationResult(
        is_valid=False,
        issues=[issue],
        metadata=metadata or {}
    )