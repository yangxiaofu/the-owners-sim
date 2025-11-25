"""
Schedule API for game_cycle.

Handles all schedule-related database operations.
"""

from dataclasses import dataclass
from typing import List, Optional

from .database.connection import GameCycleDatabase


@dataclass
class ScheduledGame:
    """Represents a scheduled game."""
    id: int
    week: Optional[int]           # Week number (1-18) or None for playoffs
    round_name: Optional[str]     # Playoff round name or None for regular season
    home_team_id: int
    away_team_id: int
    home_score: Optional[int]
    away_score: Optional[int]
    is_played: bool
    is_divisional: bool
    is_conference: bool

    @property
    def is_playoff(self) -> bool:
        """True if this is a playoff game."""
        return self.round_name is not None

    @property
    def winner_id(self) -> Optional[int]:
        """Get winner team ID, or None if not played or tie."""
        if not self.is_played or self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team_id
        elif self.away_score > self.home_score:
            return self.away_team_id
        return None  # Tie


class ScheduleAPI:
    """
    API for schedule operations in game_cycle.

    Handles:
    - Querying games by week/round
    - Recording game results
    - Adding playoff games
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    def get_games_for_week(self, week: int) -> List[ScheduledGame]:
        """
        Get all games for a regular season week.

        Args:
            week: Week number (1-18)

        Returns:
            List of ScheduledGame for that week
        """
        rows = self.db.query_all(
            "SELECT * FROM schedule WHERE week = ? ORDER BY id",
            (week,)
        )
        return [self._row_to_game(row) for row in rows]

    def get_unplayed_games_for_week(self, week: int) -> List[ScheduledGame]:
        """Get only unplayed games for a week."""
        rows = self.db.query_all(
            "SELECT * FROM schedule WHERE week = ? AND is_played = 0 ORDER BY id",
            (week,)
        )
        return [self._row_to_game(row) for row in rows]

    def get_playoff_games(self, round_name: str) -> List[ScheduledGame]:
        """
        Get all games for a playoff round.

        Args:
            round_name: 'wild_card', 'divisional', 'conference', or 'super_bowl'

        Returns:
            List of ScheduledGame for that round
        """
        rows = self.db.query_all(
            "SELECT * FROM schedule WHERE round_name = ? ORDER BY id",
            (round_name,)
        )
        return [self._row_to_game(row) for row in rows]

    def get_unplayed_playoff_games(self, round_name: str) -> List[ScheduledGame]:
        """Get only unplayed games for a playoff round."""
        rows = self.db.query_all(
            "SELECT * FROM schedule WHERE round_name = ? AND is_played = 0 ORDER BY id",
            (round_name,)
        )
        return [self._row_to_game(row) for row in rows]

    def record_result(
        self,
        game_id: int,
        home_score: int,
        away_score: int
    ) -> None:
        """
        Record the result of a game.

        Args:
            game_id: Schedule ID of the game
            home_score: Home team's final score
            away_score: Away team's final score
        """
        self.db.execute(
            """UPDATE schedule
               SET home_score = ?, away_score = ?, is_played = 1
               WHERE id = ?""",
            (home_score, away_score, game_id)
        )

    def insert_playoff_game(
        self,
        round_name: str,
        home_team_id: int,
        away_team_id: int
    ) -> int:
        """
        Insert a new playoff game.

        Args:
            round_name: Playoff round ('wild_card', 'divisional', etc.)
            home_team_id: Home team ID (higher seed)
            away_team_id: Away team ID (lower seed)

        Returns:
            ID of the inserted game
        """
        cursor = self.db.execute(
            """INSERT INTO schedule (round_name, home_team_id, away_team_id)
               VALUES (?, ?, ?)""",
            (round_name, home_team_id, away_team_id)
        )
        return cursor.lastrowid

    def clear_playoff_games(self) -> None:
        """Remove all playoff games (to regenerate bracket)."""
        self.db.execute("DELETE FROM schedule WHERE round_name IS NOT NULL")

    def get_game_by_id(self, game_id: int) -> Optional[ScheduledGame]:
        """Get a specific game by ID."""
        row = self.db.query_one("SELECT * FROM schedule WHERE id = ?", (game_id,))
        return self._row_to_game(row) if row else None

    def get_week_count(self, week: int) -> int:
        """Get count of games in a week."""
        result = self.db.query_one(
            "SELECT COUNT(*) as count FROM schedule WHERE week = ?",
            (week,)
        )
        return result['count'] if result else 0

    def get_played_count(self, week: int) -> int:
        """Get count of played games in a week."""
        result = self.db.query_one(
            "SELECT COUNT(*) as count FROM schedule WHERE week = ? AND is_played = 1",
            (week,)
        )
        return result['count'] if result else 0

    def is_week_complete(self, week: int) -> bool:
        """Check if all games in a week have been played."""
        total = self.get_week_count(week)
        played = self.get_played_count(week)
        return total > 0 and total == played

    def is_round_complete(self, round_name: str) -> bool:
        """Check if all games in a playoff round have been played."""
        result = self.db.query_one(
            """SELECT
                   COUNT(*) as total,
                   SUM(CASE WHEN is_played = 1 THEN 1 ELSE 0 END) as played
               FROM schedule
               WHERE round_name = ?""",
            (round_name,)
        )
        if not result or result['total'] == 0:
            return False
        return result['total'] == result['played']

    def _row_to_game(self, row) -> ScheduledGame:
        """Convert database row to ScheduledGame."""
        return ScheduledGame(
            id=row['id'],
            week=row['week'],
            round_name=row['round_name'],
            home_team_id=row['home_team_id'],
            away_team_id=row['away_team_id'],
            home_score=row['home_score'],
            away_score=row['away_score'],
            is_played=bool(row['is_played']),
            is_divisional=bool(row['is_divisional']),
            is_conference=bool(row['is_conference'])
        )
