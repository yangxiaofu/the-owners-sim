"""
Statistics Mapping Module

Configuration-driven transformation of extracted statistics to database format.
Handles schema evolution, type conversions, and field mappings.

Components:
- DatabaseMapper: Main mapping orchestrator
- FieldMappingRegistry: Configurable field mapping management
- SchemaValidator: Output format validation
"""

from .database_mapper import DatabaseMapper
from .field_mapping_registry import FieldMappingRegistry
from .schema_validator import SchemaValidator

__all__ = [
    'DatabaseMapper',
    'FieldMappingRegistry',
    'SchemaValidator'
]