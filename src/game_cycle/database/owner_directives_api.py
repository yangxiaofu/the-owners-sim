"""
Owner Directives API - Database operations for owner strategic guidance.

Part of Milestone 13: Owner Review.
Handles CRUD operations for owner directives with dynasty isolation.
"""

import sqlite3
import logging
import json
from typing import Optional, Dict, Any


class OwnerDirectivesAPI:
    """
    API for owner directives database operations.

    Handles:
    - Saving/loading owner directives
    - Managing win targets, position priorities, wishlists
    - Follows dynasty isolation pattern

    All operations require dynasty_id for data isolation.
    """

    def __init__(self, db_path: str):
        """Initialize with database path."""
        self._db_path = db_path
        self._logger = logging.getLogger(__name__)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get owner directives for a team/season.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Dict with directive fields, or None if not set

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT target_wins, priority_positions, fa_wishlist,
                          draft_wishlist, draft_strategy, fa_philosophy,
                          max_contract_years, max_guaranteed_percent
                   FROM owner_directives
                   WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
                (dynasty_id, team_id, season)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "dynasty_id": dynasty_id,
                "team_id": team_id,
                "season": season,
                "target_wins": row["target_wins"],
                "priority_positions": json.loads(row["priority_positions"] or "[]"),
                "fa_wishlist": json.loads(row["fa_wishlist"] or "[]"),
                "draft_wishlist": json.loads(row["draft_wishlist"] or "[]"),
                "draft_strategy": row["draft_strategy"],
                "fa_philosophy": row["fa_philosophy"],
                "max_contract_years": row["max_contract_years"],
                "max_guaranteed_percent": row["max_guaranteed_percent"],
            }
        finally:
            conn.close()

    def save_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        directives: Dict[str, Any]
    ) -> bool:
        """
        Save or update owner directives.

        Uses INSERT OR REPLACE for upsert behavior.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            directives: Dict with directive fields

        Returns:
            True if successful

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO owner_directives
                   (dynasty_id, team_id, season, target_wins, priority_positions,
                    fa_wishlist, draft_wishlist, draft_strategy, fa_philosophy,
                    max_contract_years, max_guaranteed_percent, modified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    dynasty_id,
                    team_id,
                    season,
                    directives.get("target_wins"),
                    json.dumps(directives.get("priority_positions", [])),
                    json.dumps(directives.get("fa_wishlist", [])),
                    json.dumps(directives.get("draft_wishlist", [])),
                    directives.get("draft_strategy", "balanced"),
                    directives.get("fa_philosophy", "balanced"),
                    directives.get("max_contract_years", 5),
                    directives.get("max_guaranteed_percent", 0.75),
                )
            )
            conn.commit()
            self._logger.debug(
                f"Saved directives for dynasty={dynasty_id}, team={team_id}, season={season}"
            )
            return True
        finally:
            conn.close()

    def clear_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> bool:
        """
        Delete directives for a team/season.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            True if rows were deleted

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """DELETE FROM owner_directives
                   WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
                (dynasty_id, team_id, season)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_directives_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get directives for all teams in a season.

        Useful for AI GM behavior during offseason processing.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict mapping team_id to directives

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT team_id, target_wins, priority_positions, fa_wishlist,
                          draft_wishlist, draft_strategy, fa_philosophy,
                          max_contract_years, max_guaranteed_percent
                   FROM owner_directives
                   WHERE dynasty_id = ? AND season = ?""",
                (dynasty_id, season)
            )

            result = {}
            for row in cursor.fetchall():
                result[row["team_id"]] = {
                    "dynasty_id": dynasty_id,
                    "team_id": row["team_id"],
                    "season": season,
                    "target_wins": row["target_wins"],
                    "priority_positions": json.loads(row["priority_positions"] or "[]"),
                    "fa_wishlist": json.loads(row["fa_wishlist"] or "[]"),
                    "draft_wishlist": json.loads(row["draft_wishlist"] or "[]"),
                    "draft_strategy": row["draft_strategy"],
                    "fa_philosophy": row["fa_philosophy"],
                    "max_contract_years": row["max_contract_years"],
                    "max_guaranteed_percent": row["max_guaranteed_percent"],
                }

            return result
        finally:
            conn.close()
