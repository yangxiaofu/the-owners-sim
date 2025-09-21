"""
Game Statistics Service

Main orchestrator for comprehensive game statistics persistence.
Called immediately after FullGameSimulator.simulate_game() to persist
all player and team statistics with transaction safety.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Import internal modules
from .extraction.player_statistics_extractor import PlayerStatisticsExtractor
from .extraction.team_statistics_extractor import TeamStatisticsExtractor
from .extraction.game_metadata_extractor import GameMetadataExtractor
from .mapping.database_mapper import DatabaseMapper
from .mapping.field_mapping_registry import FieldMappingRegistry
from .persistence.statistics_persister import StatisticsPersister
from .validation.statistics_validator import StatisticsValidator
from .models.persistence_result import PersistenceResult
from .models.extraction_context import ExtractionContext

# Import database connection
try:
    from ...database.connection import DatabaseConnection
except ImportError:
    # Fallback import path
    from database.connection import DatabaseConnection


class GameStatisticsService:
    """
    Main orchestrator for game statistics persistence.

    Coordinates extraction, mapping, validation, and persistence of
    comprehensive game statistics immediately after game simulation.
    """

    def __init__(self,
                 player_extractor: PlayerStatisticsExtractor,
                 team_extractor: TeamStatisticsExtractor,
                 metadata_extractor: GameMetadataExtractor,
                 mapper: DatabaseMapper,
                 persister: StatisticsPersister,
                 validator: Optional[StatisticsValidator] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the game statistics service.

        All dependencies are injected for maximum testability.

        Args:
            player_extractor: Extracts player statistics from game results
            team_extractor: Extracts team statistics from game results
            metadata_extractor: Extracts game metadata and context
            mapper: Maps extracted stats to database format
            persister: Handles database persistence operations
            validator: Optional validation for extracted statistics
            logger: Optional logger for debugging and monitoring
        """
        self.player_extractor = player_extractor
        self.team_extractor = team_extractor
        self.metadata_extractor = metadata_extractor
        self.mapper = mapper
        self.persister = persister
        self.validator = validator
        self.logger = logger or logging.getLogger(__name__)

        # Performance tracking
        self._stats_processed = 0
        self._total_processing_time = 0.0

    def persist_game_statistics(self,
                               game_result,
                               game_metadata: Dict[str, Any]) -> PersistenceResult:
        """
        Main public API method for persisting game statistics.

        Orchestrates the complete pipeline: extraction -> mapping -> validation -> persistence

        Args:
            game_result: Complete result from FullGameSimulator.simulate_game()
            game_metadata: Game context information (teams, date, week, etc.)

        Returns:
            PersistenceResult with comprehensive success/failure information
        """
        start_time = time.time()
        operation_id = f"game_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = PersistenceResult(
            success=True,
            operation_id=operation_id
        )

        try:
            self.logger.info(f"Starting game statistics persistence: {operation_id}")

            # Step 1: Create extraction context
            extraction_context = self._create_extraction_context(game_metadata)
            result.add_metadata("extraction_context", extraction_context)

            # Step 2: Extract statistics from game result
            extracted_stats = self._extract_statistics(game_result, extraction_context, result)
            if not result.success:
                return result

            # Step 3: Validate extracted statistics (if validator provided)
            if self.validator:
                validation_result = self._validate_statistics(extracted_stats, result)
                if not validation_result:
                    return result

            # Step 4: Map statistics to database format
            database_records = self._map_to_database_format(extracted_stats, extraction_context, result)
            if not result.success:
                return result

            # Step 5: Persist to database with transaction management
            persistence_success = self._persist_to_database(database_records, extraction_context, result)
            if not persistence_success:
                return result

            # Step 6: Update result with success metrics
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # Convert to milliseconds

            result.processing_time_ms = processing_time
            result.add_metadata("database_records_count", len(database_records.get('player_records', [])))
            result.add_metadata("extraction_context", extraction_context)

            self._update_performance_tracking(processing_time, result.records_processed)

            self.logger.info(f"Game statistics persistence completed successfully: {operation_id} "
                           f"({processing_time:.1f}ms, {result.records_processed} records)")

            return result

        except Exception as e:
            # Handle any unexpected errors gracefully
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000

            result.success = False
            result.processing_time_ms = processing_time
            result.add_error(f"Unexpected error during statistics persistence: {str(e)}")

            self.logger.error(f"Game statistics persistence failed: {operation_id} - {e}", exc_info=True)

            return result

    def _create_extraction_context(self, game_metadata: Dict[str, Any]) -> ExtractionContext:
        """
        Create extraction context from game metadata.

        Args:
            game_metadata: Game context information

        Returns:
            ExtractionContext object for guiding extraction
        """
        # Extract required fields with defaults
        game_id = game_metadata.get('game_id', f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        dynasty_id = game_metadata.get('dynasty_id', 'default_dynasty')
        game_date = game_metadata.get('date', datetime.now().date())
        away_team_id = game_metadata.get('away_team_id', 0)
        home_team_id = game_metadata.get('home_team_id', 0)
        week = game_metadata.get('week', 1)
        season_type = game_metadata.get('season_type', 'regular_season')

        context = ExtractionContext(
            game_id=game_id,
            dynasty_id=dynasty_id,
            game_date=game_date,
            away_team_id=away_team_id,
            home_team_id=home_team_id,
            week=week,
            season_type=season_type
        )

        # Add any additional metadata
        for key, value in game_metadata.items():
            if key not in ['game_id', 'dynasty_id', 'date', 'away_team_id', 'home_team_id', 'week', 'season_type']:
                context.add_metadata(key, value)

        return context

    def _extract_statistics(self, game_result, extraction_context: ExtractionContext, result: PersistenceResult) -> Dict[str, Any]:
        """
        Extract comprehensive statistics from game result.

        Args:
            game_result: Game simulation result
            extraction_context: Context for extraction operations
            result: Result object to update with metrics

        Returns:
            Dictionary with extracted statistics
        """
        try:
            extracted_stats = {}

            # Extract player statistics
            self.logger.debug("Extracting player statistics...")
            player_stats = self.player_extractor.extract_player_statistics(game_result, extraction_context)
            extracted_stats['player_stats'] = player_stats
            result.add_metadata("player_stats_count", len(player_stats))

            # Extract team statistics
            self.logger.debug("Extracting team statistics...")
            team_stats = self.team_extractor.extract_team_statistics(game_result, extraction_context)
            extracted_stats['team_stats'] = team_stats
            result.add_metadata("team_stats_count", len(team_stats))

            # Extract game metadata
            self.logger.debug("Extracting game metadata...")
            game_metadata = self.metadata_extractor.extract_game_metadata(game_result, extraction_context)
            extracted_stats['game_metadata'] = game_metadata

            result.records_processed = len(player_stats) + len(team_stats) + 1  # +1 for game metadata

            self.logger.debug(f"Extraction completed: {len(player_stats)} players, "
                            f"{len(team_stats)} teams, 1 game record")

            return extracted_stats

        except Exception as e:
            result.add_error(f"Statistics extraction failed: {str(e)}")
            self.logger.error(f"Statistics extraction error: {e}", exc_info=True)
            return {}

    def _validate_statistics(self, extracted_stats: Dict[str, Any], result: PersistenceResult) -> bool:
        """
        Validate extracted statistics.

        Args:
            extracted_stats: Extracted statistics to validate
            result: Result object to update with validation results

        Returns:
            True if validation passed, False otherwise
        """
        try:
            validation_result = self.validator.validate_statistics(extracted_stats)

            if validation_result.has_warnings():
                for warning in validation_result.warnings:
                    result.add_warning(f"Validation warning: {warning}")

            if not validation_result.is_valid():
                for error in validation_result.get_all_errors():
                    result.add_error(f"Validation error: {error}")
                return False

            result.add_metadata("validation_passed", True)
            return True

        except Exception as e:
            result.add_error(f"Statistics validation failed: {str(e)}")
            self.logger.error(f"Statistics validation error: {e}", exc_info=True)
            return False

    def _map_to_database_format(self, extracted_stats: Dict[str, Any],
                               extraction_context: ExtractionContext,
                               result: PersistenceResult) -> Dict[str, Any]:
        """
        Map extracted statistics to database format.

        Args:
            extracted_stats: Extracted statistics
            extraction_context: Context for mapping operations
            result: Result object to update with mapping results

        Returns:
            Dictionary with database-formatted records
        """
        try:
            database_records = {}

            # Map player statistics
            if 'player_stats' in extracted_stats:
                player_records = self.mapper.map_player_statistics(
                    extracted_stats['player_stats'],
                    extraction_context
                )
                database_records['player_records'] = player_records
                result.add_metadata("player_records_mapped", len(player_records))

            # Map team statistics
            if 'team_stats' in extracted_stats:
                team_records = self.mapper.map_team_statistics(
                    extracted_stats['team_stats'],
                    extraction_context
                )
                database_records['team_records'] = team_records
                result.add_metadata("team_records_mapped", len(team_records))

            # Map game metadata
            if 'game_metadata' in extracted_stats:
                game_record = self.mapper.map_game_metadata(
                    extracted_stats['game_metadata'],
                    extraction_context
                )
                database_records['game_record'] = game_record

            return database_records

        except Exception as e:
            result.add_error(f"Statistics mapping failed: {str(e)}")
            self.logger.error(f"Statistics mapping error: {e}", exc_info=True)
            return {}

    def _persist_to_database(self, database_records: Dict[str, Any],
                            extraction_context: ExtractionContext,
                            result: PersistenceResult) -> bool:
        """
        Persist database records with transaction management.

        Args:
            database_records: Database-formatted records
            extraction_context: Context for persistence operations
            result: Result object to update with persistence results

        Returns:
            True if persistence succeeded, False otherwise
        """
        try:
            persistence_result = self.persister.persist_statistics(database_records, extraction_context)

            if persistence_result.success:
                result.records_persisted = persistence_result.records_persisted
                result.add_metadata("persistence_time_ms", persistence_result.processing_time_ms)
                return True
            else:
                for error in persistence_result.errors:
                    result.add_error(f"Persistence error: {error}")
                return False

        except Exception as e:
            result.add_error(f"Database persistence failed: {str(e)}")
            self.logger.error(f"Database persistence error: {e}", exc_info=True)
            return False

    def _update_performance_tracking(self, processing_time_ms: float, records_processed: int) -> None:
        """
        Update internal performance tracking metrics.

        Args:
            processing_time_ms: Processing time in milliseconds
            records_processed: Number of records processed
        """
        self._stats_processed += records_processed
        self._total_processing_time += processing_time_ms

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this service instance.

        Returns:
            Dictionary with performance metrics
        """
        avg_processing_time = (self._total_processing_time / self._stats_processed
                             if self._stats_processed > 0 else 0)

        return {
            'total_stats_processed': self._stats_processed,
            'total_processing_time_ms': self._total_processing_time,
            'average_processing_time_per_stat_ms': avg_processing_time,
            'stats_per_second': (self._stats_processed / (self._total_processing_time / 1000)
                               if self._total_processing_time > 0 else 0)
        }

    @classmethod
    def create_default(cls, database_connection: Optional[DatabaseConnection] = None) -> 'GameStatisticsService':
        """
        Create a GameStatisticsService with default dependencies.

        Factory method for easy instantiation with reasonable defaults.

        Args:
            database_connection: Optional database connection (will create if not provided)

        Returns:
            Configured GameStatisticsService instance
        """
        # Create database connection if not provided
        if database_connection is None:
            database_connection = DatabaseConnection()

        # Create dependencies with defaults
        field_mapping_registry = FieldMappingRegistry.create_default()
        database_mapper = DatabaseMapper(field_mapping_registry)

        player_extractor = PlayerStatisticsExtractor()
        team_extractor = TeamStatisticsExtractor()
        metadata_extractor = GameMetadataExtractor()
        persister = StatisticsPersister(database_connection)
        validator = StatisticsValidator()

        # Create and return service
        return cls(
            player_extractor=player_extractor,
            team_extractor=team_extractor,
            metadata_extractor=metadata_extractor,
            mapper=database_mapper,
            persister=persister,
            validator=validator
        )

    def __str__(self) -> str:
        """String representation of the service."""
        return f"GameStatisticsService(processed={self._stats_processed} stats)"