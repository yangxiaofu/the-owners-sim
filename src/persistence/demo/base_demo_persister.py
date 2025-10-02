"""
Base Demo Persister Interface

Abstract base class defining the contract for all demo persistence strategies.
Uses ABC to enforce implementation of required methods.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from .persistence_result import PersistenceResult


class DemoPersister(ABC):
    """
    Abstract base class for demo persistence strategies.

    Defines the interface that all concrete persistence implementations
    must follow. Allows for flexible strategy swapping (database, file, memory).

    Design Pattern: Strategy Pattern
    - Encapsulates persistence algorithms
    - Makes strategies interchangeable
    - Enables runtime strategy selection
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize base persister.

        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def persist_game_result(
        self,
        game_id: str,
        game_data: Dict[str, Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist game result to storage.

        Args:
            game_id: Unique game identifier
            game_data: Game result data including scores, teams, metadata
            dynasty_id: Dynasty context identifier

        Returns:
            PersistenceResult with operation outcome
        """
        pass

    @abstractmethod
    def persist_player_stats(
        self,
        game_id: str,
        player_stats: List[Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist player statistics to storage.

        Args:
            game_id: Game identifier
            player_stats: List of player statistics objects
            dynasty_id: Dynasty context identifier

        Returns:
            PersistenceResult with operation outcome
        """
        pass

    @abstractmethod
    def persist_team_stats(
        self,
        game_id: str,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist team statistics to storage.

        Args:
            game_id: Game identifier
            home_stats: Home team statistics
            away_stats: Away team statistics
            dynasty_id: Dynasty context identifier

        Returns:
            PersistenceResult with operation outcome
        """
        pass

    @abstractmethod
    def update_standings(
        self,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        dynasty_id: str = "default",
        season: int = 2024
    ) -> PersistenceResult:
        """
        Update team standings based on game result.

        Args:
            home_team_id: Home team identifier
            away_team_id: Away team identifier
            home_score: Home team score
            away_score: Away team score
            dynasty_id: Dynasty context identifier
            season: Season year

        Returns:
            PersistenceResult with operation outcome
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> bool:
        """
        Begin a transaction for atomic operations.

        Returns:
            True if transaction started successfully
        """
        pass

    @abstractmethod
    def commit_transaction(self) -> bool:
        """
        Commit the current transaction.

        Returns:
            True if transaction committed successfully
        """
        pass

    @abstractmethod
    def rollback_transaction(self) -> bool:
        """
        Rollback the current transaction.

        Returns:
            True if transaction rolled back successfully
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get persistence statistics.

        Returns:
            Dictionary with persistence metrics
        """
        pass

    def validate_game_data(self, game_data: Dict[str, Any]) -> List[str]:
        """
        Validate game data before persistence.

        Args:
            game_data: Game data to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        required_fields = ['home_team_id', 'away_team_id', 'home_score', 'away_score']
        for field in required_fields:
            if field not in game_data:
                errors.append(f"Missing required field: {field}")

        # Validate team IDs
        if 'home_team_id' in game_data:
            if not (1 <= game_data['home_team_id'] <= 32):
                errors.append(f"Invalid home_team_id: {game_data['home_team_id']}")

        if 'away_team_id' in game_data:
            if not (1 <= game_data['away_team_id'] <= 32):
                errors.append(f"Invalid away_team_id: {game_data['away_team_id']}")

        # Validate scores
        if 'home_score' in game_data:
            if game_data['home_score'] < 0:
                errors.append(f"Invalid home_score: {game_data['home_score']}")

        if 'away_score' in game_data:
            if game_data['away_score'] < 0:
                errors.append(f"Invalid away_score: {game_data['away_score']}")

        return errors

    def __str__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}()"
