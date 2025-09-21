"""
Statistics Validation Module

Data integrity and validation logic for statistics persistence.
Ensures data quality and consistency before database operations.

Components:
- StatisticsValidator: Input validation for extracted statistics
- IntegrityChecker: Cross-reference validation and business rules
- ValidationRules: Configurable validation rule definitions
"""

from .statistics_validator import StatisticsValidator
from .integrity_checker import IntegrityChecker
from .validation_rules import ValidationRules

__all__ = [
    'StatisticsValidator',
    'IntegrityChecker',
    'ValidationRules'
]