"""
Game Persistence Orchestrator

Coordinates complete game persistence using composition.
Orchestrates multiple persistence operations with transaction management.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_demo_persister import DemoPersister
from .persistence_result import (
    PersistenceResult,
    CompositePersistenceResult,
    PersistenceStatus
)


class GamePersistenceOrchestrator:
    """
    Orchestrates complete game persistence operations.

    Uses composition to coordinate multiple persistence steps:
    1. Game result
    2. Player statistics
    3. Team statistics
    4. Standings updates

    Design Pattern: Facade + Orchestrator
    - Provides simple interface for complex persistence workflow
    - Manages transaction lifecycle
    - Aggregates results from multiple operations
    """

    def __init__(
        self,
        persister: DemoPersister,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize orchestrator with a persistence strategy.

        Args:
            persister: Concrete DemoPersister implementation (strategy injection)
            logger: Optional logger
        """
        self.persister = persister
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Statistics
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0

    def persist_complete_game(
        self,
        game_id: str,
        game_result: Any,
        player_stats: Optional[List[Any]] = None,
        dynasty_id: str = "default",
        season: int = 2024,
        week: int = 1,
        simulation_date: Optional[Any] = None
    ) -> CompositePersistenceResult:
        """
        Persist all game data in a single atomic transaction.

        This is the main entry point for persisting complete game data.
        Orchestrates all persistence operations with transaction management.

        Args:
            game_id: Unique game identifier
            game_result: GameResult object or simulation result
            player_stats: Optional list of player statistics
            dynasty_id: Dynasty context identifier
            season: Season year
            week: Week number
            simulation_date: Simulation date for created_at timestamp (optional)

        Returns:
            CompositePersistenceResult with detailed operation outcomes
        """
        composite_result = CompositePersistenceResult(
            overall_status=PersistenceStatus.SUCCESS
        )

        self.logger.info(f"Starting complete game persistence: {game_id}")

        # Extract game data
        game_data = self._extract_game_data(game_result, season, week)
        if not game_data:
            composite_result.overall_status = PersistenceStatus.FAILURE
            result = PersistenceResult(status=PersistenceStatus.FAILURE)
            result.add_error("Failed to extract game data from game_result")
            composite_result.add_result("extraction", result)
            composite_result.finalize()
            return composite_result

        # Begin transaction for atomicity
        transaction_started = self.persister.begin_transaction()
        if not transaction_started:
            composite_result.overall_status = PersistenceStatus.FAILURE
            result = PersistenceResult(status=PersistenceStatus.FAILURE)
            result.add_error("Failed to start database transaction")
            composite_result.add_result("transaction_start", result)
            composite_result.finalize()
            return composite_result

        try:
            # Step 1: Persist game result
            game_result_persistence = self.persister.persist_game_result(
                game_id, game_data, dynasty_id, simulation_date
            )
            composite_result.add_result("game_result", game_result_persistence)

            if not game_result_persistence.success:
                raise Exception("Game result persistence failed")

            # Step 2: Persist player statistics (if available)
            if player_stats:
                player_stats_persistence = self.persister.persist_player_stats(
                    game_id, player_stats, dynasty_id
                )
                composite_result.add_result("player_stats", player_stats_persistence)

                # Partial success is acceptable for player stats
                if player_stats_persistence.status == PersistenceStatus.FAILURE:
                    self.logger.warning("Player stats persistence failed, but continuing")

            # Step 3: Persist team statistics
            home_stats, away_stats = self._extract_team_stats(game_result)
            team_stats_persistence = self.persister.persist_team_stats(
                game_id, home_stats, away_stats, dynasty_id
            )
            composite_result.add_result("team_stats", team_stats_persistence)

            # Step 4: Update standings
            standings_persistence = self.persister.update_standings(
                home_team_id=game_data['home_team_id'],
                away_team_id=game_data['away_team_id'],
                home_score=game_data['home_score'],
                away_score=game_data['away_score'],
                dynasty_id=dynasty_id,
                season=season
            )
            composite_result.add_result("standings", standings_persistence)

            if not standings_persistence.success:
                raise Exception("Standings update failed")

            # Commit transaction
            commit_success = self.persister.commit_transaction()
            if not commit_success:
                raise Exception("Failed to commit transaction")

            self.successful_operations += 1
            self.logger.info(f"Successfully persisted complete game: {game_id}")

        except Exception as e:
            # Rollback on any error
            self.logger.error(f"Error during game persistence, rolling back: {e}")
            rollback_success = self.persister.rollback_transaction()

            composite_result.overall_status = PersistenceStatus.ROLLBACK
            error_result = PersistenceResult(status=PersistenceStatus.FAILURE)
            error_result.add_error(f"Transaction failed: {str(e)}")
            error_result.rollback_performed = rollback_success
            composite_result.add_result("error", error_result)

            self.failed_operations += 1

        finally:
            self.total_operations += 1
            composite_result.finalize()

        return composite_result

    def persist_game_batch(
        self,
        games: List[Dict[str, Any]],
        dynasty_id: str = "default"
    ) -> List[CompositePersistenceResult]:
        """
        Persist multiple games in sequence.

        Args:
            games: List of game dictionaries with required fields
            dynasty_id: Dynasty context

        Returns:
            List of CompositePersistenceResults
        """
        results = []

        self.logger.info(f"Starting batch persistence of {len(games)} games")

        for game_data in games:
            game_id = game_data.get('game_id', f"game_{len(results)}")
            game_result = game_data.get('game_result')
            player_stats = game_data.get('player_stats')
            season = game_data.get('season', 2024)
            week = game_data.get('week', 1)

            result = self.persist_complete_game(
                game_id, game_result, player_stats, dynasty_id, season, week
            )
            results.append(result)

            # Stop on critical failure if specified
            if not result.success and game_data.get('stop_on_failure', False):
                self.logger.warning(f"Stopping batch due to failure at game {game_id}")
                break

        self.logger.info(f"Batch persistence complete: {len(results)} games processed")
        return results

    def get_orchestrator_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for this orchestrator instance.

        Returns:
            Dictionary with orchestrator metrics
        """
        persister_stats = self.persister.get_statistics()

        return {
            'orchestrator': {
                'total_operations': self.total_operations,
                'successful_operations': self.successful_operations,
                'failed_operations': self.failed_operations,
                'success_rate': (
                    (self.successful_operations / self.total_operations * 100)
                    if self.total_operations > 0 else 0.0
                )
            },
            'persister': persister_stats
        }

    def _extract_game_data(
        self,
        game_result: Any,
        season: int,
        week: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extract game data from game result object.

        Handles different game result formats (GameResult, dict, etc.)

        Args:
            game_result: Game result object
            season: Season year
            week: Week number

        Returns:
            Dictionary with standardized game data
        """
        try:
            # Check if it's already a dictionary
            if isinstance(game_result, dict):
                game_data = game_result.copy()
            # Check if it has the GameResult interface
            elif hasattr(game_result, 'home_team_id') and hasattr(game_result, 'away_team_id'):
                game_data = {
                    'home_team_id': game_result.home_team_id,
                    'away_team_id': game_result.away_team_id,
                    'home_score': game_result.home_score,
                    'away_score': game_result.away_score,
                    'total_plays': getattr(game_result, 'total_plays', 0),
                    'game_duration_minutes': getattr(game_result, 'game_duration_minutes', 180),
                    'overtime_periods': getattr(game_result, 'overtime_periods', 0),
                }
            # Check if it's a simulation result with metadata
            elif hasattr(game_result, 'metadata') and isinstance(game_result.metadata, dict):
                game_data = game_result.metadata.copy()
            else:
                self.logger.error(f"Unknown game result format: {type(game_result)}")
                return None

            # Ensure required fields
            game_data.setdefault('season', season)
            game_data.setdefault('week', week)
            game_data.setdefault('season_type', 'regular_season')

            return game_data

        except Exception as e:
            self.logger.error(f"Error extracting game data: {e}", exc_info=True)
            return None

    def _extract_team_stats(self, game_result: Any) -> tuple:
        """
        Extract team statistics from game result.

        Args:
            game_result: Game result object

        Returns:
            Tuple of (home_stats, away_stats) dictionaries
        """
        home_stats = {}
        away_stats = {}

        try:
            # Extract team stats if available
            if hasattr(game_result, 'home_team_stats'):
                home_stats = game_result.home_team_stats or {}
            if hasattr(game_result, 'away_team_stats'):
                away_stats = game_result.away_team_stats or {}

            # Could also aggregate from player stats if needed
            # This is a placeholder for future enhancement

        except Exception as e:
            self.logger.warning(f"Error extracting team stats: {e}")

        return home_stats, away_stats

    def __str__(self) -> str:
        """String representation"""
        return (f"GamePersistenceOrchestrator("
                f"persister={self.persister}, "
                f"operations={self.total_operations})")
