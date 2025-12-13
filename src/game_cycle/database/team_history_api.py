"""
Team History API for game_cycle.

Handles database operations for team season history tracking,
used for calculating 5-year window metrics like contender score.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .connection import GameCycleDatabase


@dataclass
class SeasonHistoryRecord:
    """Represents a team's single season result."""
    team_id: int
    season: int
    wins: int
    losses: int
    made_playoffs: bool = False
    playoff_round_reached: Optional[str] = None  # 'wild_card', 'divisional', 'conference', 'super_bowl'
    won_super_bowl: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            'team_id': self.team_id,
            'season': self.season,
            'wins': self.wins,
            'losses': self.losses,
            'made_playoffs': self.made_playoffs,
            'playoff_round_reached': self.playoff_round_reached,
            'won_super_bowl': self.won_super_bowl,
        }


class TeamHistoryAPI:
    """
    API for team season history database operations.

    Handles:
    - Recording season results (W-L, playoffs, Super Bowl)
    - Querying history with year limits (5-year window)
    - Getting specific season records
    - Dynasty isolation for all operations
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Query Methods --------------------

    def get_team_history(
        self,
        dynasty_id: str,
        team_id: int,
        years: int = 5
    ) -> List[SeasonHistoryRecord]:
        """
        Get the last N years of history for a team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            years: Number of years to retrieve (default 5)

        Returns:
            List of SeasonHistoryRecord sorted by season descending (most recent first)
        """
        rows = self.db.query_all(
            """SELECT team_id, season, wins, losses, made_playoffs,
                      playoff_round_reached, won_super_bowl
               FROM team_season_history
               WHERE dynasty_id = ? AND team_id = ?
               ORDER BY season DESC
               LIMIT ?""",
            (dynasty_id, team_id, years)
        )
        return [self._row_to_record(row) for row in rows]

    def get_season_record(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[SeasonHistoryRecord]:
        """
        Get a specific season's record for a team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            SeasonHistoryRecord if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT team_id, season, wins, losses, made_playoffs,
                      playoff_round_reached, won_super_bowl
               FROM team_season_history
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        return self._row_to_record(row) if row else None

    def get_all_teams_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> List[SeasonHistoryRecord]:
        """
        Get all 32 teams' records for a specific season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of SeasonHistoryRecord for all teams with records
        """
        rows = self.db.query_all(
            """SELECT team_id, season, wins, losses, made_playoffs,
                      playoff_round_reached, won_super_bowl
               FROM team_season_history
               WHERE dynasty_id = ? AND season = ?
               ORDER BY team_id""",
            (dynasty_id, season)
        )
        return [self._row_to_record(row) for row in rows]

    # -------------------- Insert/Update Methods --------------------

    def record_season(
        self,
        dynasty_id: str,
        record: SeasonHistoryRecord
    ) -> bool:
        """
        Insert or update a team's season record.

        Uses INSERT OR REPLACE to handle re-recording scenarios.

        Args:
            dynasty_id: Dynasty identifier
            record: SeasonHistoryRecord with season data

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO team_season_history
               (dynasty_id, team_id, season, wins, losses, made_playoffs,
                playoff_round_reached, won_super_bowl)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id,
                record.team_id,
                record.season,
                record.wins,
                record.losses,
                1 if record.made_playoffs else 0,
                record.playoff_round_reached,
                1 if record.won_super_bowl else 0
            )
        )
        return True

    def record_seasons_batch(
        self,
        dynasty_id: str,
        records: List[SeasonHistoryRecord]
    ) -> int:
        """
        Record multiple season records in batch.

        Args:
            dynasty_id: Dynasty identifier
            records: List of SeasonHistoryRecord

        Returns:
            Number of records inserted/updated
        """
        count = 0
        for record in records:
            if self.record_season(dynasty_id, record):
                count += 1
        return count

    def delete_season(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> bool:
        """
        Delete a specific season record.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            True if a record was deleted
        """
        cursor = self.db.execute(
            """DELETE FROM team_season_history
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        return cursor.rowcount > 0

    def clear_team_history(
        self,
        dynasty_id: str,
        team_id: int
    ) -> int:
        """
        Clear all history for a team (useful for testing).

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)

        Returns:
            Number of records deleted
        """
        cursor = self.db.execute(
            """DELETE FROM team_season_history
               WHERE dynasty_id = ? AND team_id = ?""",
            (dynasty_id, team_id)
        )
        return cursor.rowcount

    def clear_season_history(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Clear all team records for a season (useful for testing).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of records deleted
        """
        cursor = self.db.execute(
            """DELETE FROM team_season_history
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return cursor.rowcount

    # -------------------- Aggregate Methods --------------------

    def get_playoff_count(
        self,
        dynasty_id: str,
        team_id: int,
        years: int = 5
    ) -> int:
        """
        Get number of playoff appearances in last N years.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            years: Number of years to check

        Returns:
            Count of playoff appearances
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM (
                   SELECT 1 FROM team_season_history
                   WHERE dynasty_id = ? AND team_id = ? AND made_playoffs = 1
                   ORDER BY season DESC
                   LIMIT ?
               )""",
            (dynasty_id, team_id, years)
        )
        # Count from subquery of playoff seasons within the year limit
        history = self.get_team_history(dynasty_id, team_id, years)
        return sum(1 for h in history if h.made_playoffs)

    def get_super_bowl_count(
        self,
        dynasty_id: str,
        team_id: int,
        years: int = 5
    ) -> int:
        """
        Get number of Super Bowl wins in last N years.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            years: Number of years to check

        Returns:
            Count of Super Bowl wins
        """
        history = self.get_team_history(dynasty_id, team_id, years)
        return sum(1 for h in history if h.won_super_bowl)

    def get_average_wins(
        self,
        dynasty_id: str,
        team_id: int,
        years: int = 5
    ) -> float:
        """
        Get average wins per season in last N years.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            years: Number of years to check

        Returns:
            Average wins (0.0 if no history)
        """
        history = self.get_team_history(dynasty_id, team_id, years)
        if not history:
            return 0.0
        return sum(h.wins for h in history) / len(history)

    # -------------------- Private Methods --------------------

    def _row_to_record(self, row) -> SeasonHistoryRecord:
        """Convert database row to SeasonHistoryRecord."""
        return SeasonHistoryRecord(
            team_id=row['team_id'],
            season=row['season'],
            wins=row['wins'],
            losses=row['losses'],
            made_playoffs=bool(row['made_playoffs']),
            playoff_round_reached=row['playoff_round_reached'],
            won_super_bowl=bool(row['won_super_bowl'])
        )
