"""
Schema Validator

Validates database records against expected schema.
"""

from typing import List, Any
import logging

from ..models.database_record import PlayerGameStatsRecord, TeamGameStatsRecord
from ..models.persistence_result import ValidationResult


class SchemaValidator:
    """
    Validates database records against expected schema and constraints.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the schema validator.

        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)

    def validate_player_records(self, records: List[PlayerGameStatsRecord]) -> ValidationResult:
        """
        Validate player game stats records.

        Args:
            records: List of player records to validate

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult(valid=True)

        for i, record in enumerate(records):
            self._validate_single_player_record(record, f"record_{i}", result)

        return result

    def _validate_single_player_record(self, record: PlayerGameStatsRecord,
                                     record_id: str, result: ValidationResult) -> None:
        """
        Validate a single player record.

        Args:
            record: Player record to validate
            record_id: Identifier for error reporting
            result: ValidationResult to update
        """
        # Required fields validation
        if not record.dynasty_id:
            result.add_field_error(f"{record_id}.dynasty_id", "Dynasty ID is required")

        if not record.game_id:
            result.add_field_error(f"{record_id}.game_id", "Game ID is required")

        if not record.player_id:
            result.add_field_error(f"{record_id}.player_id", "Player ID is required")

        if not record.player_name:
            result.add_field_error(f"{record_id}.player_name", "Player name is required")

        if record.team_id <= 0:
            result.add_field_error(f"{record_id}.team_id", "Valid team ID is required")

        # Statistical validation for O-line stats
        if record.is_offensive_lineman():
            self._validate_oline_stats(record, record_id, result)

    def _validate_oline_stats(self, record: PlayerGameStatsRecord,
                             record_id: str, result: ValidationResult) -> None:
        """
        Validate offensive line statistics.

        Args:
            record: Player record to validate
            record_id: Identifier for error reporting
            result: ValidationResult to update
        """
        # Validate grade ranges
        if record.run_blocking_grade < 0 or record.run_blocking_grade > 100:
            result.add_field_error(f"{record_id}.run_blocking_grade",
                                 f"Run blocking grade must be 0-100, got {record.run_blocking_grade}")

        if record.pass_blocking_efficiency < 0 or record.pass_blocking_efficiency > 100:
            result.add_field_error(f"{record_id}.pass_blocking_efficiency",
                                 f"Pass blocking efficiency must be 0-100, got {record.pass_blocking_efficiency}")

        # Validate negative values
        negative_fields = ['pancakes', 'sacks_allowed', 'hurries_allowed', 'pressures_allowed',
                          'missed_assignments', 'holding_penalties', 'false_start_penalties',
                          'downfield_blocks', 'double_team_blocks', 'chip_blocks']

        for field in negative_fields:
            value = getattr(record, field, 0)
            if value < 0:
                result.add_field_error(f"{record_id}.{field}",
                                     f"{field} cannot be negative, got {value}")

        # Logical validation
        if record.pressures_allowed < (record.sacks_allowed + record.hurries_allowed):
            result.add_warning(f"{record_id}: Pressures allowed should be >= sacks + hurries")

    def validate_team_records(self, records: List[TeamGameStatsRecord]) -> ValidationResult:
        """
        Validate team game stats records.

        Args:
            records: List of team records to validate

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult(valid=True)

        for i, record in enumerate(records):
            self._validate_single_team_record(record, f"team_record_{i}", result)

        return result

    def _validate_single_team_record(self, record: TeamGameStatsRecord,
                                   record_id: str, result: ValidationResult) -> None:
        """
        Validate a single team record.

        Args:
            record: Team record to validate
            record_id: Identifier for error reporting
            result: ValidationResult to update
        """
        # Required fields
        if not record.dynasty_id:
            result.add_field_error(f"{record_id}.dynasty_id", "Dynasty ID is required")

        if not record.game_id:
            result.add_field_error(f"{record_id}.game_id", "Game ID is required")

        if record.team_id <= 0:
            result.add_field_error(f"{record_id}.team_id", "Valid team ID is required")

        # Logical validation
        if record.total_yards != (record.passing_yards + record.rushing_yards):
            result.add_warning(f"{record_id}: Total yards should equal passing + rushing yards")