"""
Game Metadata Extractor

Extracts game context and metadata from game results.
"""

from typing import Dict, Any
import logging
from datetime import datetime

from .base_extractor import BaseExtractor
from ..models.extraction_context import ExtractionContext


class GameMetadata:
    """
    Extracted game metadata object.

    Contains game context information and metadata.
    """

    def __init__(self):
        self.game_id = ""
        self.dynasty_id = ""
        self.away_team_id = 0
        self.home_team_id = 0
        self.game_date = None
        self.week = 0
        self.season_type = ""
        self.away_score = 0
        self.home_score = 0
        self.winning_team_id = None
        self.total_plays = 0
        self.game_duration_minutes = 0
        self.created_at = datetime.now()


class GameMetadataExtractor(BaseExtractor):
    """
    Extracts game context and metadata from game results.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the game metadata extractor.

        Args:
            logger: Optional logger for debugging
        """
        super().__init__(logger)

    def extract_game_metadata(self, game_result: Any, context: ExtractionContext) -> GameMetadata:
        """
        Extract game metadata from game result.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            GameMetadata object
        """
        metadata = GameMetadata()

        # Extract from context (primary source)
        metadata.game_id = context.game_id
        metadata.dynasty_id = context.dynasty_id
        metadata.away_team_id = context.away_team_id
        metadata.home_team_id = context.home_team_id
        metadata.game_date = context.game_date
        metadata.week = context.week
        metadata.season_type = context.season_type

        # Extract from game result
        self._extract_from_game_result(game_result, metadata)

        return metadata

    def _extract_from_game_result(self, game_result: Any, metadata: GameMetadata) -> None:
        """
        Extract metadata from game result object.

        Args:
            game_result: Game simulation result
            metadata: GameMetadata to populate
        """
        # Extract scores
        self._extract_scores(game_result, metadata)

        # Extract game metrics
        metadata.total_plays = self.get_safe_attribute(game_result, 'total_plays', 0)
        metadata.game_duration_minutes = self.get_safe_attribute(game_result, 'game_duration_minutes', 0)

        # Determine winning team
        if metadata.away_score > metadata.home_score:
            metadata.winning_team_id = metadata.away_team_id
        elif metadata.home_score > metadata.away_score:
            metadata.winning_team_id = metadata.home_team_id
        # else: tie game, winning_team_id remains None

    def _extract_scores(self, game_result: Any, metadata: GameMetadata) -> None:
        """
        Extract final scores from game result.

        Args:
            game_result: Game simulation result
            metadata: GameMetadata to populate
        """
        # Try multiple ways to get scores
        final_score = self.get_safe_attribute(game_result, 'final_score')
        if final_score and isinstance(final_score, dict):
            if 'scores' in final_score:
                scores = final_score['scores']
                metadata.away_score = scores.get(metadata.away_team_id, 0)
                metadata.home_score = scores.get(metadata.home_team_id, 0)
                return

        # Try direct attributes
        metadata.away_score = self.get_safe_attribute(game_result, 'away_score', 0)
        metadata.home_score = self.get_safe_attribute(game_result, 'home_score', 0)

    def extract(self, game_result: Any, context: ExtractionContext) -> GameMetadata:
        """
        Extract implementation for base class compatibility.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            GameMetadata object (wrapped in list for base class compatibility)
        """
        return [self.extract_game_metadata(game_result, context)]