"""
Playoff Bracket API for game_cycle.

Handles all playoff bracket database operations with dynasty/season isolation.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .connection import GameCycleDatabase


@dataclass
class PlayoffMatchup:
    """Represents a playoff bracket matchup."""
    id: int
    dynasty_id: str
    season: int
    round_name: str
    conference: str
    game_number: int
    higher_seed: int  # Home team (higher seed)
    lower_seed: int   # Away team (lower seed)
    winner: Optional[int]
    home_score: Optional[int]
    away_score: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'id': self.id,
            'dynasty_id': self.dynasty_id,
            'season': self.season,
            'round_name': self.round_name,
            'conference': self.conference,
            'game_number': self.game_number,
            'higher_seed': self.higher_seed,
            'lower_seed': self.lower_seed,
            'winner': self.winner,
            'home_score': self.home_score,
            'away_score': self.away_score,
        }


class PlayoffBracketAPI:
    """
    API for playoff bracket operations in game_cycle.

    Handles:
    - Querying matchups by dynasty/season/round
    - Inserting new matchups (seeding)
    - Updating results after games
    - Getting round winners for bracket advancement

    All operations require dynasty_id and season for proper isolation.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Query Methods --------------------

    def get_matchups_for_round(
        self,
        dynasty_id: str,
        season: int,
        round_name: str
    ) -> List[PlayoffMatchup]:
        """
        Get all matchups for a specific playoff round.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: 'wild_card', 'divisional', 'conference', or 'super_bowl'

        Returns:
            List of PlayoffMatchup sorted by conference and game_number
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, round_name, conference, game_number,
                      higher_seed, lower_seed, winner, home_score, away_score
               FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ? AND round_name = ?
               ORDER BY conference, game_number""",
            (dynasty_id, season, round_name)
        )
        return [self._row_to_matchup(row) for row in rows]

    def get_all_matchups(
        self,
        dynasty_id: str,
        season: int
    ) -> List[PlayoffMatchup]:
        """
        Get all playoff matchups for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of all PlayoffMatchup for the playoffs
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, round_name, conference, game_number,
                      higher_seed, lower_seed, winner, home_score, away_score
               FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ?
               ORDER BY
                   CASE round_name
                       WHEN 'wild_card' THEN 1
                       WHEN 'divisional' THEN 2
                       WHEN 'conference' THEN 3
                       WHEN 'super_bowl' THEN 4
                   END,
                   conference, game_number""",
            (dynasty_id, season)
        )
        return [self._row_to_matchup(row) for row in rows]

    def get_round_winners(
        self,
        dynasty_id: str,
        season: int,
        round_name: str,
        conference: str
    ) -> List[int]:
        """
        Get winners from a playoff round for a specific conference.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: Playoff round name
            conference: 'AFC' or 'NFC'

        Returns:
            List of winning team IDs
        """
        rows = self.db.query_all(
            """SELECT winner FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ? AND round_name = ?
                     AND conference = ? AND winner IS NOT NULL""",
            (dynasty_id, season, round_name, conference)
        )
        return [row['winner'] for row in rows]

    # -------------------- Insert/Update Methods --------------------

    def insert_matchup(
        self,
        dynasty_id: str,
        season: int,
        round_name: str,
        conference: str,
        game_number: int,
        higher_seed: int,
        lower_seed: int
    ) -> PlayoffMatchup:
        """
        Insert a new playoff matchup (seeding).

        Uses INSERT OR REPLACE to handle re-seeding scenarios.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: 'wild_card', 'divisional', 'conference', or 'super_bowl'
            conference: 'AFC', 'NFC', or 'SUPER_BOWL'
            game_number: Game number within round/conference
            higher_seed: Team ID of higher seed (home team)
            lower_seed: Team ID of lower seed (away team)

        Returns:
            The created PlayoffMatchup
        """
        self.db.execute(
            """INSERT OR REPLACE INTO playoff_bracket
               (dynasty_id, season, round_name, conference, game_number,
                higher_seed, lower_seed, winner, home_score, away_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)""",
            (dynasty_id, season, round_name, conference, game_number,
             higher_seed, lower_seed)
        )

        # Get the inserted row
        row = self.db.query_one(
            """SELECT id, dynasty_id, season, round_name, conference, game_number,
                      higher_seed, lower_seed, winner, home_score, away_score
               FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ? AND round_name = ?
                     AND conference = ? AND game_number = ?""",
            (dynasty_id, season, round_name, conference, game_number)
        )
        return self._row_to_matchup(row)

    def update_result(
        self,
        dynasty_id: str,
        season: int,
        round_name: str,
        conference: str,
        game_number: int,
        home_score: int,
        away_score: int,
        winner: int
    ) -> bool:
        """
        Update a matchup with game result.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: Playoff round
            conference: Conference
            game_number: Game number
            home_score: Home team (higher seed) score
            away_score: Away team (lower seed) score
            winner: Winning team ID

        Returns:
            True if update was successful
        """
        cursor = self.db.execute(
            """UPDATE playoff_bracket
               SET home_score = ?, away_score = ?, winner = ?
               WHERE dynasty_id = ? AND season = ? AND round_name = ?
                     AND conference = ? AND game_number = ?""",
            (home_score, away_score, winner, dynasty_id, season,
             round_name, conference, game_number)
        )
        return cursor.rowcount > 0

    def clear_bracket(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Clear all playoff bracket data for a dynasty/season.

        Useful for reset/testing scenarios.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of rows deleted
        """
        cursor = self.db.execute(
            """DELETE FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return cursor.rowcount

    def clear_round(
        self,
        dynasty_id: str,
        season: int,
        round_name: str
    ) -> int:
        """
        Clear a specific round's data (for re-seeding).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            round_name: Round to clear

        Returns:
            Number of rows deleted
        """
        cursor = self.db.execute(
            """DELETE FROM playoff_bracket
               WHERE dynasty_id = ? AND season = ? AND round_name = ?""",
            (dynasty_id, season, round_name)
        )
        return cursor.rowcount

    # -------------------- Private Methods --------------------

    def _row_to_matchup(self, row) -> PlayoffMatchup:
        """Convert database row to PlayoffMatchup."""
        return PlayoffMatchup(
            id=row['id'],
            dynasty_id=row['dynasty_id'],
            season=row['season'],
            round_name=row['round_name'],
            conference=row['conference'],
            game_number=row['game_number'],
            higher_seed=row['higher_seed'],
            lower_seed=row['lower_seed'],
            winner=row['winner'],
            home_score=row['home_score'],
            away_score=row['away_score']
        )
