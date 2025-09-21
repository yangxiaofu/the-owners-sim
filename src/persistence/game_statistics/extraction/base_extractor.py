"""
Base Extractor

Abstract base class for all statistics extractors.
Provides common functionality and interface definition.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

from ..models.extraction_context import ExtractionContext


class BaseExtractor(ABC):
    """
    Abstract base class for statistics extractors.

    Defines the common interface and provides shared functionality
    for all extractor implementations.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the base extractor.

        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self, game_result: Any, context: ExtractionContext) -> List[Any]:
        """
        Extract statistics from game result.

        Abstract method that must be implemented by all extractors.

        Args:
            game_result: Game simulation result
            context: Extraction context with game metadata

        Returns:
            List of extracted statistics objects
        """
        pass

    def validate_game_result(self, game_result: Any) -> bool:
        """
        Validate that game result has required structure.

        Args:
            game_result: Game simulation result to validate

        Returns:
            True if game result is valid for extraction
        """
        if game_result is None:
            self.logger.warning("Game result is None")
            return False

        # Basic validation - subclasses can override for specific checks
        if not hasattr(game_result, 'final_statistics'):
            self.logger.warning("Game result missing final_statistics attribute")
            return False

        return True

    def validate_context(self, context: ExtractionContext) -> bool:
        """
        Validate that extraction context has required information.

        Args:
            context: Extraction context to validate

        Returns:
            True if context is valid for extraction
        """
        if context is None:
            self.logger.warning("Extraction context is None")
            return False

        required_fields = ['game_id', 'dynasty_id', 'away_team_id', 'home_team_id']
        for field in required_fields:
            if not hasattr(context, field) or getattr(context, field) is None:
                self.logger.warning(f"Extraction context missing required field: {field}")
                return False

        return True

    def safe_extract(self, game_result: Any, context: ExtractionContext) -> List[Any]:
        """
        Safely extract statistics with validation and error handling.

        Wrapper around the abstract extract method that provides
        validation and error handling.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            List of extracted statistics (empty list if extraction fails)
        """
        try:
            # Validate inputs
            if not self.validate_game_result(game_result):
                self.logger.error("Game result validation failed")
                return []

            if not self.validate_context(context):
                self.logger.error("Extraction context validation failed")
                return []

            # Perform extraction
            return self.extract(game_result, context)

        except Exception as e:
            self.logger.error(f"Statistics extraction failed: {e}", exc_info=True)
            return []

    def get_safe_attribute(self, obj: Any, attribute: str, default: Any = None) -> Any:
        """
        Safely get attribute from object with default fallback.

        Args:
            obj: Object to get attribute from
            attribute: Attribute name
            default: Default value if attribute doesn't exist

        Returns:
            Attribute value or default
        """
        try:
            return getattr(obj, attribute, default)
        except Exception:
            return default

    def get_nested_attribute(self, obj: Any, path: str, default: Any = None) -> Any:
        """
        Safely get nested attribute using dot notation.

        Args:
            obj: Object to traverse
            path: Dot-separated attribute path (e.g., 'stats.passing.yards')
            default: Default value if path doesn't exist

        Returns:
            Nested attribute value or default
        """
        try:
            current = obj
            for attr in path.split('.'):
                current = getattr(current, attr)
            return current
        except (AttributeError, TypeError):
            return default

    def extract_player_stats_dict(self, game_result: Any) -> Dict[str, Any]:
        """
        Extract player statistics dictionary from game result.

        Common utility method for getting player stats from different
        game result formats.

        Args:
            game_result: Game simulation result

        Returns:
            Dictionary mapping player names to stats objects
        """
        # Check direct access to player_stats (discovered format: list of dicts)
        if hasattr(game_result, 'player_stats'):
            player_stats = getattr(game_result, 'player_stats')
            self.logger.debug(f"Found player_stats attribute, type: {type(player_stats)}")

            if isinstance(player_stats, list) and player_stats:
                # Convert list of player stat dicts to dict keyed by player_name
                player_stats_dict = {}
                for player_stat in player_stats:
                    if isinstance(player_stat, dict) and 'player_name' in player_stat:
                        player_name = player_stat['player_name']
                        player_stats_dict[player_name] = player_stat

                self.logger.debug(f"Converted player_stats list to dict with {len(player_stats_dict)} entries")
                return player_stats_dict
            elif isinstance(player_stats, dict) and player_stats:
                self.logger.debug(f"player_stats is a dict with {len(player_stats)} entries")
                return player_stats

        # Try multiple paths to find player statistics (fallback for other formats)
        possible_paths = [
            'final_statistics.player_statistics',    # Original nested path
            'player_statistics',                     # Direct player_statistics
            'stats.players',                         # Alternative nested path
        ]

        for path in possible_paths:
            player_stats = self.get_nested_attribute(game_result, path)
            if player_stats and isinstance(player_stats, dict):
                self.logger.debug(f"Found player statistics at path: {path}")
                return player_stats

        self.logger.warning("Could not find player statistics in game result")
        return {}

    def __str__(self) -> str:
        """String representation of the extractor."""
        return f"{self.__class__.__name__}()"