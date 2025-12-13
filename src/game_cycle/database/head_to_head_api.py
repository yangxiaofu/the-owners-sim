"""
Database API for head-to-head history operations.

Part of Milestone 11: Schedule & Rivalries, Tollgate 2.
Handles CRUD operations for head-to-head records with dynasty isolation.
"""

import logging
from typing import List, Optional

from .connection import GameCycleDatabase
from ..models.head_to_head import HeadToHeadRecord


class HeadToHeadAPI:
    """
    API for head-to-head history database operations.

    Follows dynasty isolation pattern - all operations require dynasty_id.
    Provides methods for querying and updating head-to-head records.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db
        self._logger = logging.getLogger(__name__)

    # -------------------- Query Methods --------------------

    def get_record(
        self,
        dynasty_id: str,
        team_id_1: int,
        team_id_2: int
    ) -> Optional[HeadToHeadRecord]:
        """
        Get head-to-head record between two teams.

        Args:
            dynasty_id: Dynasty identifier
            team_id_1: First team ID (1-32)
            team_id_2: Second team ID (1-32)

        Returns:
            HeadToHeadRecord if exists, None otherwise
        """
        # Ensure consistent ordering for lookup
        team_a = min(team_id_1, team_id_2)
        team_b = max(team_id_1, team_id_2)

        row = self.db.query_one(
            """SELECT record_id, team_a_id, team_b_id, team_a_wins, team_b_wins, ties,
                      team_a_home_wins, team_a_away_wins, last_meeting_season,
                      last_meeting_winner, current_streak_team, current_streak_count,
                      playoff_meetings, playoff_team_a_wins, playoff_team_b_wins,
                      created_at, updated_at
               FROM head_to_head
               WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
            (dynasty_id, team_a, team_b)
        )
        return HeadToHeadRecord.from_db_row(row) if row else None

    def get_team_all_records(
        self,
        dynasty_id: str,
        team_id: int
    ) -> List[HeadToHeadRecord]:
        """
        Get all head-to-head records for a specific team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)

        Returns:
            List of HeadToHeadRecord objects sorted by total games descending
        """
        rows = self.db.query_all(
            """SELECT record_id, team_a_id, team_b_id, team_a_wins, team_b_wins, ties,
                      team_a_home_wins, team_a_away_wins, last_meeting_season,
                      last_meeting_winner, current_streak_team, current_streak_count,
                      playoff_meetings, playoff_team_a_wins, playoff_team_b_wins,
                      created_at, updated_at
               FROM head_to_head
               WHERE dynasty_id = ? AND (team_a_id = ? OR team_b_id = ?)
               ORDER BY (team_a_wins + team_b_wins + ties) DESC""",
            (dynasty_id, team_id, team_id)
        )
        return [HeadToHeadRecord.from_db_row(row) for row in rows]

    def get_top_matchups_by_games(
        self,
        dynasty_id: str,
        limit: int = 10
    ) -> List[HeadToHeadRecord]:
        """
        Get matchups with the most games played.

        Args:
            dynasty_id: Dynasty identifier
            limit: Maximum number of records to return

        Returns:
            List of HeadToHeadRecord objects sorted by total games descending
        """
        rows = self.db.query_all(
            """SELECT record_id, team_a_id, team_b_id, team_a_wins, team_b_wins, ties,
                      team_a_home_wins, team_a_away_wins, last_meeting_season,
                      last_meeting_winner, current_streak_team, current_streak_count,
                      playoff_meetings, playoff_team_a_wins, playoff_team_b_wins,
                      created_at, updated_at
               FROM head_to_head
               WHERE dynasty_id = ?
               ORDER BY (team_a_wins + team_b_wins + ties) DESC
               LIMIT ?""",
            (dynasty_id, limit)
        )
        return [HeadToHeadRecord.from_db_row(row) for row in rows]

    def get_longest_streaks(
        self,
        dynasty_id: str,
        limit: int = 10
    ) -> List[HeadToHeadRecord]:
        """
        Get matchups with the longest current winning streaks.

        Args:
            dynasty_id: Dynasty identifier
            limit: Maximum number of records to return

        Returns:
            List of HeadToHeadRecord objects sorted by streak length descending
        """
        rows = self.db.query_all(
            """SELECT record_id, team_a_id, team_b_id, team_a_wins, team_b_wins, ties,
                      team_a_home_wins, team_a_away_wins, last_meeting_season,
                      last_meeting_winner, current_streak_team, current_streak_count,
                      playoff_meetings, playoff_team_a_wins, playoff_team_b_wins,
                      created_at, updated_at
               FROM head_to_head
               WHERE dynasty_id = ? AND current_streak_count > 0
               ORDER BY current_streak_count DESC
               LIMIT ?""",
            (dynasty_id, limit)
        )
        return [HeadToHeadRecord.from_db_row(row) for row in rows]

    def get_record_count(self, dynasty_id: str) -> int:
        """
        Get total number of head-to-head records for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of records
        """
        row = self.db.query_one(
            "SELECT COUNT(*) as count FROM head_to_head WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        return row['count'] if row else 0

    # -------------------- Update Methods --------------------

    def update_after_game(
        self,
        dynasty_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        season: int,
        is_playoff: bool = False
    ) -> None:
        """
        Update head-to-head record after a game result.

        Creates the record if it doesn't exist (upsert pattern).

        Args:
            dynasty_id: Dynasty identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            season: Season year
            is_playoff: True if playoff game
        """
        # Normalize team ordering
        team_a = min(home_team_id, away_team_id)
        team_b = max(home_team_id, away_team_id)

        # Determine game outcome
        is_tie = home_score == away_score
        winner = None if is_tie else (home_team_id if home_score > away_score else away_team_id)

        # Determine perspective (who is home from team_a's view)
        team_a_is_home = (home_team_id == team_a)
        team_a_won = (winner == team_a) if winner else False
        team_b_won = (winner == team_b) if winner else False

        # Get or create record
        existing = self.get_record(dynasty_id, team_a, team_b)

        if existing is None:
            self._create_initial_record(dynasty_id, team_a, team_b)

        # Build update based on outcome
        if is_playoff:
            self._update_playoff_result(
                dynasty_id, team_a, team_b, team_a_won, team_b_won
            )
        else:
            self._update_regular_result(
                dynasty_id, team_a, team_b,
                team_a_won, team_b_won, is_tie,
                team_a_is_home
            )

        # Update last meeting and streak
        self._update_last_meeting(dynasty_id, team_a, team_b, season, winner)
        self._update_streak(dynasty_id, team_a, team_b, winner)

        self._logger.debug(
            f"Updated H2H: Team {team_a} vs Team {team_b}, "
            f"winner={winner}, playoff={is_playoff}"
        )

    def _create_initial_record(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int
    ) -> None:
        """Create initial head-to-head record with all zeros."""
        self.db.execute(
            """INSERT INTO head_to_head
               (dynasty_id, team_a_id, team_b_id)
               VALUES (?, ?, ?)""",
            (dynasty_id, team_a, team_b)
        )

    def _update_regular_result(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int,
        team_a_won: bool,
        team_b_won: bool,
        is_tie: bool,
        team_a_is_home: bool
    ) -> None:
        """Update record for regular season game result."""
        updates = ["updated_at = CURRENT_TIMESTAMP"]

        if is_tie:
            updates.append("ties = ties + 1")
        elif team_a_won:
            updates.append("team_a_wins = team_a_wins + 1")
            if team_a_is_home:
                updates.append("team_a_home_wins = team_a_home_wins + 1")
            else:
                updates.append("team_a_away_wins = team_a_away_wins + 1")
        elif team_b_won:
            updates.append("team_b_wins = team_b_wins + 1")
            # team_b wins tracked inversely for home/away
            # When team_b wins at home (team_a is away), no need to track separately
            # When team_b wins away (team_a is home), no need to track separately

        sql = f"""UPDATE head_to_head SET {', '.join(updates)}
                  WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?"""
        self.db.execute(sql, (dynasty_id, team_a, team_b))

    def _update_playoff_result(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int,
        team_a_won: bool,
        team_b_won: bool
    ) -> None:
        """Update record for playoff game result."""
        updates = [
            "updated_at = CURRENT_TIMESTAMP",
            "playoff_meetings = playoff_meetings + 1"
        ]

        if team_a_won:
            updates.append("playoff_team_a_wins = playoff_team_a_wins + 1")
        elif team_b_won:
            updates.append("playoff_team_b_wins = playoff_team_b_wins + 1")

        sql = f"""UPDATE head_to_head SET {', '.join(updates)}
                  WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?"""
        self.db.execute(sql, (dynasty_id, team_a, team_b))

    def _update_last_meeting(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int,
        season: int,
        winner: Optional[int]
    ) -> None:
        """Update last meeting info."""
        self.db.execute(
            """UPDATE head_to_head
               SET last_meeting_season = ?, last_meeting_winner = ?, updated_at = CURRENT_TIMESTAMP
               WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
            (season, winner, dynasty_id, team_a, team_b)
        )

    def _update_streak(
        self,
        dynasty_id: str,
        team_a: int,
        team_b: int,
        winner: Optional[int]
    ) -> None:
        """
        Update winning streak after a game.

        Streak logic:
        - If tie: reset streak to None/0
        - If winner matches current streak team: increment
        - If winner differs from streak team: reset to winner with count=1
        """
        if winner is None:
            # Tie breaks any streak
            self.db.execute(
                """UPDATE head_to_head
                   SET current_streak_team = NULL, current_streak_count = 0, updated_at = CURRENT_TIMESTAMP
                   WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
                (dynasty_id, team_a, team_b)
            )
        else:
            # Get current streak state
            row = self.db.query_one(
                """SELECT current_streak_team, current_streak_count
                   FROM head_to_head
                   WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
                (dynasty_id, team_a, team_b)
            )

            if row and row['current_streak_team'] == winner:
                # Extend streak
                self.db.execute(
                    """UPDATE head_to_head
                       SET current_streak_count = current_streak_count + 1, updated_at = CURRENT_TIMESTAMP
                       WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
                    (dynasty_id, team_a, team_b)
                )
            else:
                # Start new streak
                self.db.execute(
                    """UPDATE head_to_head
                       SET current_streak_team = ?, current_streak_count = 1, updated_at = CURRENT_TIMESTAMP
                       WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
                    (winner, dynasty_id, team_a, team_b)
                )

    def clear_records(self, dynasty_id: str) -> int:
        """
        Clear all head-to-head records for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of records deleted
        """
        cursor = self.db.execute(
            "DELETE FROM head_to_head WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        return cursor.rowcount

    def delete_record(
        self,
        dynasty_id: str,
        team_id_1: int,
        team_id_2: int
    ) -> bool:
        """
        Delete a specific head-to-head record.

        Args:
            dynasty_id: Dynasty identifier
            team_id_1: First team ID
            team_id_2: Second team ID

        Returns:
            True if record was deleted
        """
        team_a = min(team_id_1, team_id_2)
        team_b = max(team_id_1, team_id_2)

        cursor = self.db.execute(
            "DELETE FROM head_to_head WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?",
            (dynasty_id, team_a, team_b)
        )
        return cursor.rowcount > 0
