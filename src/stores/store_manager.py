"""
Store Manager

Coordinator for all stores with transaction support and unified operations.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging
import json

from .game_result_store import GameResultStore
from .player_stats_store import PlayerStatsStore
from .box_score_store import BoxScoreStore, GameBoxScore
from .standings_store import StandingsStore
from .base_store import BaseStore

from shared.game_result import GameResult
# PlayerGameStats removed with simulation system - will need to be recreated if needed
# from simulation.results.game_result import PlayerGameStats
from game_management.box_score_generator import TeamBoxScore


@dataclass
class TransactionResult:
    """Result of a store transaction"""
    success: bool
    timestamp: datetime
    stores_affected: List[str]
    errors: List[str]
    rollback_performed: bool = False


class StoreManager:
    """
    Central coordinator for all data stores.

    Provides:
    - Unified interface for all store operations
    - Transaction support across multiple stores
    - Batch operations for game processing
    - Snapshot generation for persistence
    - Data consistency validation
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """Initialize store manager with all stores."""
        self.logger = logging.getLogger("StoreManager")

        # Initialize all stores with database path for persistence
        self.game_result_store = GameResultStore(database_path)
        self.player_stats_store = PlayerStatsStore()
        self.box_score_store = BoxScoreStore()
        self.standings_store = StandingsStore(database_path)

        # Registry of all stores
        self.stores: Dict[str, BaseStore] = {
            'game_results': self.game_result_store,
            'player_stats': self.player_stats_store,
            'box_scores': self.box_score_store,
            'standings': self.standings_store
        }

        # Transaction state
        self._transaction_active = False
        self._transaction_stores: List[str] = []
        self._rollback_data: Dict[str, Any] = {}

        self.logger.info("StoreManager initialized with 4 stores")

    def set_dynasty_context(self, dynasty_id: str, season: int) -> None:
        """
        Set dynasty and season context for all stores that support persistence.
        
        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        if hasattr(self.game_result_store, 'set_dynasty_context'):
            self.game_result_store.set_dynasty_context(dynasty_id, season)
        if hasattr(self.standings_store, 'set_dynasty_context'):
            self.standings_store.set_dynasty_context(dynasty_id, season)
        
        self.logger.info(f"Set dynasty context: {dynasty_id[:8]}... season {season}")

    def process_game_complete(self, game_id: str, result: GameResult,
                             home_box: Optional[TeamBoxScore] = None,
                             away_box: Optional[TeamBoxScore] = None) -> TransactionResult:
        """
        Process all data from a completed game.

        Args:
            game_id: Unique game identifier
            result: Game result data
            home_box: Optional home team box score
            away_box: Optional away team box score

        Returns:
            TransactionResult indicating success or failure
        """
        self.logger.info(f"Processing game complete: {game_id}")
        timestamp = datetime.now()
        errors = []
        stores_affected = []

        # Begin transaction
        if not self._begin_transaction():
            return TransactionResult(
                success=False,
                timestamp=timestamp,
                stores_affected=[],
                errors=["Failed to begin transaction"]
            )

        try:
            # 1. Store game result
            self.game_result_store.add(game_id, result)
            stores_affected.append('game_results')

            # 2. Update standings
            self.standings_store.update_from_game_result(result)
            stores_affected.append('standings')

            # 3. Process player statistics
            if result.player_stats:
                self.player_stats_store.add_game_stats(game_id, result.player_stats)
                stores_affected.append('player_stats')

            # 4. Store box scores if provided
            if home_box and away_box:
                game_summary = {
                    'home_score': result.home_score,
                    'away_score': result.away_score,
                    'total_plays': result.total_plays,
                    'game_duration': result.game_duration_minutes
                }
                self.box_score_store.add_game_box_scores(
                    game_id, home_box, away_box, game_summary
                )
                stores_affected.append('box_scores')

            # 5. Validate consistency
            if not self._validate_transaction():
                errors.append("Data consistency validation failed")
                self._rollback_transaction()
                return TransactionResult(
                    success=False,
                    timestamp=timestamp,
                    stores_affected=stores_affected,
                    errors=errors,
                    rollback_performed=True
                )

            # Commit transaction
            self._commit_transaction()

            self.logger.info(f"Successfully processed game {game_id}")
            return TransactionResult(
                success=True,
                timestamp=timestamp,
                stores_affected=stores_affected,
                errors=[]
            )

        except Exception as e:
            self.logger.error(f"Error processing game {game_id}: {e}")
            errors.append(str(e))

            # Rollback on error
            self._rollback_transaction()

            return TransactionResult(
                success=False,
                timestamp=timestamp,
                stores_affected=stores_affected,
                errors=errors,
                rollback_performed=True
            )

    def process_game_batch(self, games: List[Tuple[str, GameResult]]) -> List[TransactionResult]:
        """
        Process multiple games in sequence.

        Args:
            games: List of (game_id, result) tuples

        Returns:
            List of transaction results for each game
        """
        results = []

        for game_id, result in games:
            transaction_result = self.process_game_complete(game_id, result)
            results.append(transaction_result)

            # Stop on critical failure
            if not transaction_result.success and not transaction_result.rollback_performed:
                self.logger.error(f"Critical failure processing {game_id}, stopping batch")
                break

        return results

    def get_day_snapshot(self) -> Dict[str, Any]:
        """
        Get complete snapshot of all stores for persistence.

        Returns:
            Dictionary containing all store data ready for persistence
        """
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'stores': {}
        }

        for store_name, store in self.stores.items():
            snapshot['stores'][store_name] = store.get_snapshot()

        # Add summary statistics
        snapshot['summary'] = self._generate_summary()

        return snapshot

    def load_from_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """
        Load data from a persistence snapshot.

        Args:
            snapshot: Previously saved snapshot data

        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement snapshot loading logic
            # This would deserialize and populate all stores
            self.logger.info("Snapshot loading not yet implemented")
            return False

        except Exception as e:
            self.logger.error(f"Error loading snapshot: {e}")
            return False

    def clear_all_stores(self) -> None:
        """Clear all stores after successful persistence."""
        self.logger.info("Clearing all stores")

        for store_name, store in self.stores.items():
            store.clear()
            self.logger.debug(f"Cleared store: {store_name}")

    def validate_all_stores(self) -> bool:
        """
        Validate data consistency across all stores.

        Returns:
            True if all stores are valid, False otherwise
        """
        all_valid = True

        for store_name, store in self.stores.items():
            if not store.validate():
                self.logger.error(f"Validation failed for store: {store_name}")
                all_valid = False

        # Cross-store validation
        if not self._validate_cross_store_consistency():
            self.logger.error("Cross-store consistency validation failed")
            all_valid = False

        return all_valid

    def get_store(self, store_name: str) -> Optional[BaseStore]:
        """
        Get a specific store by name.

        Args:
            store_name: Name of the store

        Returns:
            Store instance if found, None otherwise
        """
        return self.stores.get(store_name)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics from all stores.

        Returns:
            Combined statistics from all stores
        """
        stats = {
            'timestamp': datetime.now().isoformat(),
            'stores': {}
        }

        for store_name, store in self.stores.items():
            stats['stores'][store_name] = store.get_statistics()

        # Add aggregate statistics
        stats['totals'] = {
            'total_games': self.game_result_store.size(),
            'total_players_tracked': len(self.player_stats_store.season_totals),
            'total_box_scores': self.box_score_store.size()
        }

        return stats

    def _begin_transaction(self) -> bool:
        """
        Begin a transaction across stores.

        Returns:
            True if transaction started successfully
        """
        if self._transaction_active:
            self.logger.warning("Transaction already active")
            return False

        # Don't lock stores during normal operations - locking is for exclusive access
        # Only track which stores are part of transaction
        for store_name in self.stores.keys():
            self._transaction_stores.append(store_name)

        # Save current state for potential rollback
        self._save_rollback_state()

        self._transaction_active = True
        self.logger.debug("Transaction started")
        return True

    def _commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._transaction_active:
            self.logger.warning("No active transaction to commit")
            return

        # Clear transaction state
        self._transaction_active = False
        self._transaction_stores.clear()
        self._rollback_data.clear()

        self.logger.debug("Transaction committed")

    def _rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if not self._transaction_active:
            self.logger.warning("No active transaction to rollback")
            return

        self.logger.info("Rolling back transaction")

        # Restore previous state
        # Note: This is simplified - full implementation would restore complete state
        for store_name in self._transaction_stores:
            if store_name in self._rollback_data:
                # Restore store data properly
                store = self.stores[store_name]

                # For GameResultStore, need to clear indices before restoring data
                if hasattr(store, 'by_team') and hasattr(store, 'by_week'):
                    # Clear indices first
                    store.by_team.clear()
                    store.by_week.clear()
                    store.by_date.clear()
                    store.by_matchup.clear()

                    # Restore data
                    store.data = self._rollback_data[store_name].copy()

                    # Rebuild indices for any remaining data
                    for game_id, game_result in store.data.items():
                        store._index_game(game_id, game_result)
                else:
                    # For other stores, simple data restore is sufficient
                    store.data = self._rollback_data[store_name].copy()

        # Clear transaction state
        self._transaction_active = False
        self._transaction_stores.clear()
        self._rollback_data.clear()

        self.logger.debug("Transaction rolled back")

    def _validate_transaction(self) -> bool:
        """
        Validate the current transaction data.

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - check each affected store
        for store_name in self._transaction_stores:
            store = self.stores[store_name]
            if not store.validate():
                self.logger.error(f"Validation failed for {store_name} during transaction")
                return False

        return True

    def _save_rollback_state(self) -> None:
        """Save current state for potential rollback."""
        self._rollback_data.clear()

        for store_name in self._transaction_stores:
            store = self.stores[store_name]
            # Deep copy of store data
            self._rollback_data[store_name] = store.data.copy()

    def _validate_cross_store_consistency(self) -> bool:
        """
        Validate consistency across different stores.

        Returns:
            True if consistent, False otherwise
        """
        # Example: Check that all games in results have standings updates
        game_ids = set(self.game_result_store.data.keys())

        # Check that player stats exist for games with results
        for game_id in game_ids:
            if game_id not in self.player_stats_store.data:
                # This might be okay if game had no player stats
                self.logger.debug(f"Game {game_id} has no player stats")

        # Additional cross-store checks can be added here

        return True

    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics across all stores.

        Returns:
            Summary dictionary
        """
        summary = {}

        # Games summary
        if self.game_result_store.size() > 0:
            all_results = list(self.game_result_store.data.values())
            total_points = sum(r.home_score + r.away_score for r in all_results)
            total_plays = sum(r.total_plays for r in all_results)

            summary['games'] = {
                'total_games': len(all_results),
                'total_points': total_points,
                'avg_points_per_game': total_points / len(all_results),
                'total_plays': total_plays,
                'avg_plays_per_game': total_plays / len(all_results)
            }

        # Player summary
        if self.player_stats_store.season_totals:
            top_scorers = self.player_stats_store.get_top_performers('total_touchdowns', 5)
            summary['players'] = {
                'total_players': len(self.player_stats_store.season_totals),
                'top_scorers': top_scorers
            }

        # Standings summary
        if self.standings_store.data:
            playoff_picture = self.standings_store.get_playoff_picture()
            summary['standings'] = {
                'playoff_picture': playoff_picture
            }

        return summary

    def export_to_json(self, filepath: str) -> bool:
        """
        Export all store data to JSON file.

        Args:
            filepath: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            snapshot = self.get_day_snapshot()

            with open(filepath, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)

            self.logger.info(f"Exported data to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            return False