"""
Box Score Store

Store for game box scores with formatted statistical displays.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .base_store import BaseStore
from game_management.box_score_generator import TeamBoxScore


@dataclass
class GameBoxScore:
    """Complete box score for a game with both teams"""
    game_id: str
    date: datetime
    home_box_score: TeamBoxScore
    away_box_score: TeamBoxScore
    game_summary: Dict[str, Any]  # Final score, total plays, etc.


class BoxScoreStore(BaseStore[GameBoxScore]):
    """
    Store for game box scores.

    Maintains formatted box scores for display and reporting,
    separate from raw statistical data.
    """

    def __init__(self):
        """Initialize box score store."""
        super().__init__("box_scores")

    def add(self, key: str, item: GameBoxScore) -> None:
        """
        Add a game box score.

        Args:
            key: Game identifier
            item: Complete game box score
        """
        if self.is_locked():
            self.logger.warning(f"Cannot add to locked store {self.store_name}")
            return

        # Store the box score
        self.data[key] = item

        self._update_metadata()
        self._log_transaction('add', key, True, {
            'home_team': item.home_box_score.team.team_id if item.home_box_score.team else None,
            'away_team': item.away_box_score.team.team_id if item.away_box_score.team else None
        })

    def add_game_box_scores(self, game_id: str, home_box: TeamBoxScore,
                           away_box: TeamBoxScore, game_summary: Dict[str, Any]) -> None:
        """
        Convenience method to add box scores for both teams.

        Args:
            game_id: Game identifier
            home_box: Home team box score
            away_box: Away team box score
            game_summary: Game summary information
        """
        game_box = GameBoxScore(
            game_id=game_id,
            date=datetime.now(),  # Should be actual game date
            home_box_score=home_box,
            away_box_score=away_box,
            game_summary=game_summary
        )
        self.add(game_id, game_box)

    def get(self, key: str) -> Optional[GameBoxScore]:
        """
        Get a game's box score.

        Args:
            key: Game identifier

        Returns:
            GameBoxScore if found, None otherwise
        """
        return self.data.get(key)

    def get_all(self) -> Dict[str, GameBoxScore]:
        """Get all box scores."""
        return self.data.copy()

    def clear(self) -> None:
        """Clear all box scores."""
        if self.is_locked():
            self.logger.warning(f"Cannot clear locked store {self.store_name}")
            return

        self.data.clear()
        self.metadata.last_cleared = datetime.now()
        self._update_metadata()
        self._log_transaction('clear', None, True)

    def validate(self) -> bool:
        """
        Validate box score consistency.

        Returns:
            True if all data is valid, False otherwise
        """
        try:
            for game_id, box_score in self.data.items():
                # Verify both teams have box scores
                if not box_score.home_box_score or not box_score.away_box_score:
                    self.logger.error(f"Missing team box score for game {game_id}")
                    return False

                # Verify box scores have sections
                if not box_score.home_box_score.sections:
                    self.logger.error(f"Home team has no box score sections for game {game_id}")
                    return False

                if not box_score.away_box_score.sections:
                    self.logger.error(f"Away team has no box score sections for game {game_id}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize box scores for persistence.

        Returns:
            Serializable dictionary
        """
        serialized = {}

        for game_id, box_score in self.data.items():
            serialized[game_id] = {
                'date': box_score.date.isoformat(),
                'game_summary': box_score.game_summary,
                'home_team': {
                    'team_id': box_score.home_box_score.team.team_id if box_score.home_box_score.team else None,
                    'team_name': box_score.home_box_score.team.full_name if box_score.home_box_score.team else None,
                    'sections': [
                        {
                            'title': section.title,
                            'headers': section.headers,
                            'rows': section.rows,
                            'footnotes': section.footnotes
                        }
                        for section in box_score.home_box_score.sections
                    ],
                    'totals': box_score.home_box_score.team_totals
                },
                'away_team': {
                    'team_id': box_score.away_box_score.team.team_id if box_score.away_box_score.team else None,
                    'team_name': box_score.away_box_score.team.full_name if box_score.away_box_score.team else None,
                    'sections': [
                        {
                            'title': section.title,
                            'headers': section.headers,
                            'rows': section.rows,
                            'footnotes': section.footnotes
                        }
                        for section in box_score.away_box_score.sections
                    ],
                    'totals': box_score.away_box_score.team_totals
                }
            }

        return serialized