"""
Field Mapping Registry

Manages configurable field mappings for statistics persistence.
"""

import json
import os
from typing import Dict, Any, Optional
import logging


class FieldMappingRegistry:
    """
    Registry for configurable field mappings between extracted statistics
    and database format.
    """

    def __init__(self, config_dir: str = None, logger: logging.Logger = None):
        """
        Initialize the field mapping registry.

        Args:
            config_dir: Directory containing mapping configuration files
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_dir = config_dir or self._get_default_config_dir()
        self.mappings = {}
        self._load_mappings()

    def _get_default_config_dir(self) -> str:
        """Get default configuration directory."""
        current_dir = os.path.dirname(__file__)
        return os.path.join(current_dir, 'mapping_configs')

    def _load_mappings(self) -> None:
        """Load all mapping configurations from files."""
        try:
            self._load_player_stats_mapping()
            self.logger.info("Field mappings loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading field mappings: {e}")
            self._create_default_mappings()

    def _load_player_stats_mapping(self) -> None:
        """Load player statistics mapping configuration."""
        config_file = os.path.join(self.config_dir, 'player_stats_mapping.json')

        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.mappings['player_stats'] = config.get('player_stats_mappings', {})
                self.mappings['position_specific'] = config.get('position_specific_mappings', {})
        else:
            self.logger.warning(f"Player stats mapping file not found: {config_file}")
            self._create_default_player_mappings()

    def _create_default_mappings(self) -> None:
        """Create default mappings when config files are not available."""
        self._create_default_player_mappings()

    def _create_default_player_mappings(self) -> None:
        """Create default player statistics mappings."""
        self.mappings['player_stats'] = {
            # Traditional stats
            'passing_yards': {'db_field': 'passing_yards', 'type': 'integer', 'default': 0},
            'passing_tds': {'db_field': 'passing_tds', 'type': 'integer', 'default': 0},
            'rushing_yards': {'db_field': 'rushing_yards', 'type': 'integer', 'default': 0},
            'receiving_yards': {'db_field': 'receiving_yards', 'type': 'integer', 'default': 0},
            'tackles_total': {'db_field': 'tackles_total', 'type': 'integer', 'default': 0},
            'sacks': {'db_field': 'sacks', 'type': 'decimal', 'default': 0.0},

            # Comprehensive O-line stats
            'pancakes': {'db_field': 'pancakes', 'type': 'integer', 'default': 0},
            'sacks_allowed': {'db_field': 'sacks_allowed', 'type': 'integer', 'default': 0},
            'hurries_allowed': {'db_field': 'hurries_allowed', 'type': 'integer', 'default': 0},
            'pressures_allowed': {'db_field': 'pressures_allowed', 'type': 'integer', 'default': 0},
            'run_blocking_grade': {'db_field': 'run_blocking_grade', 'type': 'decimal', 'default': 0.0},
            'pass_blocking_efficiency': {'db_field': 'pass_blocking_efficiency', 'type': 'decimal', 'default': 0.0},
            'missed_assignments': {'db_field': 'missed_assignments', 'type': 'integer', 'default': 0},
            'holding_penalties': {'db_field': 'holding_penalties', 'type': 'integer', 'default': 0},
            'false_start_penalties': {'db_field': 'false_start_penalties', 'type': 'integer', 'default': 0},
            'downfield_blocks': {'db_field': 'downfield_blocks', 'type': 'integer', 'default': 0},
            'double_team_blocks': {'db_field': 'double_team_blocks', 'type': 'integer', 'default': 0},
            'chip_blocks': {'db_field': 'chip_blocks', 'type': 'integer', 'default': 0},
        }

    def get_mapping(self, category: str, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get mapping configuration for a specific field.

        Args:
            category: Mapping category ('player_stats', 'team_stats', etc.)
            field_name: Field name to get mapping for

        Returns:
            Mapping configuration or None if not found
        """
        if category in self.mappings:
            return self.mappings[category].get(field_name)
        return None

    def get_db_field_name(self, category: str, field_name: str) -> str:
        """
        Get database field name for a given field.

        Args:
            category: Mapping category
            field_name: Source field name

        Returns:
            Database field name
        """
        mapping = self.get_mapping(category, field_name)
        if mapping and 'db_field' in mapping:
            return mapping['db_field']
        return field_name  # Default to same name

    def get_default_value(self, category: str, field_name: str) -> Any:
        """
        Get default value for a field.

        Args:
            category: Mapping category
            field_name: Field name

        Returns:
            Default value
        """
        mapping = self.get_mapping(category, field_name)
        if mapping and 'default' in mapping:
            return mapping['default']
        return 0  # Default to 0

    def get_field_type(self, category: str, field_name: str) -> str:
        """
        Get data type for a field.

        Args:
            category: Mapping category
            field_name: Field name

        Returns:
            Field data type
        """
        mapping = self.get_mapping(category, field_name)
        if mapping and 'type' in mapping:
            return mapping['type']
        return 'integer'  # Default to integer

    def get_all_mapped_fields(self, category: str) -> Dict[str, str]:
        """
        Get all field mappings for a category.

        Args:
            category: Mapping category

        Returns:
            Dictionary mapping source fields to database fields
        """
        if category not in self.mappings:
            return {}

        return {
            field_name: config.get('db_field', field_name)
            for field_name, config in self.mappings[category].items()
        }

    @classmethod
    def create_default(cls) -> 'FieldMappingRegistry':
        """
        Create a FieldMappingRegistry with default configuration.

        Returns:
            Configured FieldMappingRegistry instance
        """
        return cls()