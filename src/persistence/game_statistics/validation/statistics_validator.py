"""
Statistics Validator

Validates extracted statistics for data integrity and business rules.
"""

from typing import Dict, Any
import logging

from ..models.persistence_result import ValidationResult


class StatisticsValidator:
    """
    Validates extracted statistics for data integrity and business rules.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the statistics validator.

        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)

    def validate_statistics(self, extracted_stats: Dict[str, Any]) -> ValidationResult:
        """
        Validate extracted statistics.

        Args:
            extracted_stats: Dictionary of extracted statistics

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult(valid=True)

        # Validate player statistics
        if 'player_stats' in extracted_stats:
            self._validate_player_stats(extracted_stats['player_stats'], result)

        # Validate team statistics
        if 'team_stats' in extracted_stats:
            self._validate_team_stats(extracted_stats['team_stats'], result)

        # Validate game metadata
        if 'game_metadata' in extracted_stats:
            self._validate_game_metadata(extracted_stats['game_metadata'], result)

        return result

    def _validate_player_stats(self, player_stats: list, result: ValidationResult) -> None:
        """
        Validate player statistics.

        Args:
            player_stats: List of player statistics
            result: ValidationResult to update
        """
        if not player_stats:
            result.add_general_error("No player statistics found")
            return

        for i, player_stat in enumerate(player_stats):
            player_id = f"player_{i}"

            # Basic validation
            if not hasattr(player_stat, 'player_name') or not player_stat.player_name:
                result.add_field_error(f"{player_id}.player_name", "Player name is required")

            if not hasattr(player_stat, 'team_id') or player_stat.team_id <= 0:
                result.add_field_error(f"{player_id}.team_id", "Valid team ID is required")

            # O-line specific validation
            if hasattr(player_stat, 'is_offensive_lineman') and player_stat.is_offensive_lineman():
                self._validate_oline_player_stats(player_stat, player_id, result)

    def _validate_oline_player_stats(self, player_stat, player_id: str, result: ValidationResult) -> None:
        """
        Validate offensive line player statistics.

        Args:
            player_stat: Player statistic object
            player_id: Player identifier for error reporting
            result: ValidationResult to update
        """
        # Validate grade ranges
        if hasattr(player_stat, 'run_blocking_grade'):
            grade = player_stat.run_blocking_grade
            if grade < 0 or grade > 100:
                result.add_field_error(f"{player_id}.run_blocking_grade",
                                     f"Run blocking grade must be 0-100, got {grade}")

        if hasattr(player_stat, 'pass_blocking_efficiency'):
            efficiency = player_stat.pass_blocking_efficiency
            if efficiency < 0 or efficiency > 100:
                result.add_field_error(f"{player_id}.pass_blocking_efficiency",
                                     f"Pass blocking efficiency must be 0-100, got {efficiency}")

        # Validate logical relationships
        sacks_allowed = getattr(player_stat, 'sacks_allowed', 0)
        hurries_allowed = getattr(player_stat, 'hurries_allowed', 0)
        pressures_allowed = getattr(player_stat, 'pressures_allowed', 0)

        if pressures_allowed < (sacks_allowed + hurries_allowed):
            result.add_warning(f"{player_id}: Pressures allowed should be >= sacks + hurries allowed")

    def _validate_team_stats(self, team_stats: list, result: ValidationResult) -> None:
        """
        Validate team statistics.

        Args:
            team_stats: List of team statistics
            result: ValidationResult to update
        """
        if len(team_stats) != 2:
            result.add_general_error(f"Expected 2 team statistics, got {len(team_stats)}")

    def _validate_game_metadata(self, game_metadata, result: ValidationResult) -> None:
        """
        Validate game metadata.

        Args:
            game_metadata: Game metadata object
            result: ValidationResult to update
        """
        if not hasattr(game_metadata, 'game_id') or not game_metadata.game_id:
            result.add_field_error("game_metadata.game_id", "Game ID is required")

        if not hasattr(game_metadata, 'dynasty_id') or not game_metadata.dynasty_id:
            result.add_field_error("game_metadata.dynasty_id", "Dynasty ID is required")