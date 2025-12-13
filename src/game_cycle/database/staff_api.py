"""
Staff API - Database operations for GM and Head Coach management.

Part of Milestone 13: Owner Review.
Handles staff assignments, candidate generation, and hire/fire operations.
"""

import sqlite3
import logging
import json
from typing import Optional, List, Dict, Any


class StaffAPI:
    """
    API for team staff (GM, HC) database operations.

    Handles:
    - Getting/setting current GM and HC assignments
    - Managing candidate pools during hiring
    - Tracking staff tenure across seasons

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

    def get_staff_assignment(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get current GM and HC for a team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Dict with 'gm' and 'hc' keys containing staff data,
            or None if no assignment exists

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT gm_id, gm_name, gm_archetype_key, gm_custom_traits,
                          gm_history, gm_hire_season,
                          hc_id, hc_name, hc_archetype_key, hc_custom_traits,
                          hc_history, hc_hire_season
                   FROM team_staff_assignments
                   WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
                (dynasty_id, team_id, season)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "gm": {
                    "staff_id": row["gm_id"],
                    "name": row["gm_name"],
                    "archetype_key": row["gm_archetype_key"],
                    "custom_traits": json.loads(row["gm_custom_traits"] or "{}"),
                    "history": row["gm_history"],
                    "hire_season": row["gm_hire_season"],
                },
                "hc": {
                    "staff_id": row["hc_id"],
                    "name": row["hc_name"],
                    "archetype_key": row["hc_archetype_key"],
                    "custom_traits": json.loads(row["hc_custom_traits"] or "{}"),
                    "history": row["hc_history"],
                    "hire_season": row["hc_hire_season"],
                }
            }
        finally:
            conn.close()

    def save_staff_assignment(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        gm_data: Dict[str, Any],
        hc_data: Dict[str, Any]
    ) -> bool:
        """
        Save or update GM and HC assignments.

        Uses INSERT OR REPLACE for upsert behavior.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            gm_data: Dict with GM staff fields
            hc_data: Dict with HC staff fields

        Returns:
            True if successful

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO team_staff_assignments
                   (dynasty_id, team_id, season,
                    gm_id, gm_name, gm_archetype_key, gm_custom_traits,
                    gm_history, gm_hire_season,
                    hc_id, hc_name, hc_archetype_key, hc_custom_traits,
                    hc_history, hc_hire_season, modified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    dynasty_id, team_id, season,
                    gm_data["staff_id"], gm_data["name"], gm_data["archetype_key"],
                    json.dumps(gm_data.get("custom_traits", {})),
                    gm_data.get("history", ""), gm_data["hire_season"],
                    hc_data["staff_id"], hc_data["name"], hc_data["archetype_key"],
                    json.dumps(hc_data.get("custom_traits", {})),
                    hc_data.get("history", ""), hc_data["hire_season"],
                )
            )
            conn.commit()
            self._logger.debug(
                f"Saved staff assignment for dynasty={dynasty_id}, team={team_id}, season={season}"
            )
            return True
        finally:
            conn.close()

    def save_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: str,
        candidates: List[Dict[str, Any]]
    ) -> bool:
        """
        Save candidate pool for hiring.

        Clears existing candidates of this type before inserting new ones.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: 'GM' or 'HC'
            candidates: List of candidate dicts with staff fields

        Returns:
            True if successful

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            # Clear existing candidates of this type
            conn.execute(
                """DELETE FROM staff_candidates
                   WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?""",
                (dynasty_id, team_id, season, staff_type)
            )

            # Insert new candidates
            for candidate in candidates:
                conn.execute(
                    """INSERT INTO staff_candidates
                       (dynasty_id, team_id, season, candidate_id, staff_type,
                        name, archetype_key, custom_traits, history)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        dynasty_id, team_id, season,
                        candidate["staff_id"], staff_type,
                        candidate["name"], candidate["archetype_key"],
                        json.dumps(candidate.get("custom_traits", {})),
                        candidate.get("history", ""),
                    )
                )

            conn.commit()
            self._logger.debug(
                f"Saved {len(candidates)} {staff_type} candidates for team={team_id}"
            )
            return True
        finally:
            conn.close()

    def get_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get candidate pool for a staff type.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: 'GM' or 'HC'

        Returns:
            List of candidate dicts

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT candidate_id, name, archetype_key, custom_traits, history
                   FROM staff_candidates
                   WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?
                   ORDER BY id""",
                (dynasty_id, team_id, season, staff_type)
            )

            return [
                {
                    "staff_id": row["candidate_id"],
                    "name": row["name"],
                    "archetype_key": row["archetype_key"],
                    "custom_traits": json.loads(row["custom_traits"] or "{}"),
                    "history": row["history"],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def clear_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: Optional[str] = None
    ) -> bool:
        """
        Clear candidate pool after hire is complete.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: 'GM' or 'HC', or None to clear both

        Returns:
            True if rows were deleted

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            if staff_type:
                cursor = conn.execute(
                    """DELETE FROM staff_candidates
                       WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?""",
                    (dynasty_id, team_id, season, staff_type)
                )
            else:
                cursor = conn.execute(
                    """DELETE FROM staff_candidates
                       WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
                    (dynasty_id, team_id, season)
                )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def copy_staff_to_next_season(
        self,
        dynasty_id: str,
        team_id: int,
        from_season: int,
        to_season: int
    ) -> bool:
        """
        Copy staff assignment from one season to the next.

        Used when advancing to a new season to preserve hired staff.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            from_season: Source season
            to_season: Target season

        Returns:
            True if successful

        Raises:
            sqlite3.Error: On database failure
        """
        current = self.get_staff_assignment(dynasty_id, team_id, from_season)
        if current:
            return self.save_staff_assignment(
                dynasty_id, team_id, to_season,
                current["gm"], current["hc"]
            )
        return False

    def get_latest_staff_assignment(
        self,
        dynasty_id: str,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent staff assignment for a team.

        Useful when initializing a new season before explicit assignment.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)

        Returns:
            Dict with 'gm', 'hc', and 'season' keys, or None

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT season, gm_id, gm_name, gm_archetype_key, gm_custom_traits,
                          gm_history, gm_hire_season,
                          hc_id, hc_name, hc_archetype_key, hc_custom_traits,
                          hc_history, hc_hire_season
                   FROM team_staff_assignments
                   WHERE dynasty_id = ? AND team_id = ?
                   ORDER BY season DESC
                   LIMIT 1""",
                (dynasty_id, team_id)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "season": row["season"],
                "gm": {
                    "staff_id": row["gm_id"],
                    "name": row["gm_name"],
                    "archetype_key": row["gm_archetype_key"],
                    "custom_traits": json.loads(row["gm_custom_traits"] or "{}"),
                    "history": row["gm_history"],
                    "hire_season": row["gm_hire_season"],
                },
                "hc": {
                    "staff_id": row["hc_id"],
                    "name": row["hc_name"],
                    "archetype_key": row["hc_archetype_key"],
                    "custom_traits": json.loads(row["hc_custom_traits"] or "{}"),
                    "history": row["hc_history"],
                    "hire_season": row["hc_hire_season"],
                }
            }
        finally:
            conn.close()
