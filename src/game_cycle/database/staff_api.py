"""
Staff API - Database operations for GM and Head Coach management.

Part of Milestone 13: Owner Review.
Handles staff assignments, candidate generation, and hire/fire operations.
"""

import json
from typing import Optional, List, Dict, Any

from .connection import GameCycleDatabase
from ..models.staff_member import StaffMember, StaffCandidate, StaffType


class StaffAPI:
    """
    API for team staff (GM, HC) database operations.

    Handles:
    - Getting/setting current GM and HC assignments
    - Managing candidate pools during hiring
    - Tracking staff tenure across seasons

    All operations require dynasty_id for data isolation.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Staff Assignments --------------------

    def get_staff_assignment(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[Dict[str, StaffMember]]:
        """
        Get current GM and HC for a team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Dict with 'gm' and 'hc' keys containing StaffMember objects,
            or None if no assignment exists
        """
        row = self.db.query_one(
            """SELECT * FROM team_staff_assignments
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        if not row:
            return None
        return {
            'gm': self._row_to_gm(row),
            'hc': self._row_to_hc(row),
        }

    def save_staff_assignment(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        gm: StaffMember,
        hc: StaffMember
    ) -> bool:
        """
        Save or update GM and HC assignments.

        Uses INSERT OR REPLACE for upsert behavior.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            gm: StaffMember for GM
            hc: StaffMember for HC

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO team_staff_assignments
               (dynasty_id, team_id, season,
                gm_id, gm_name, gm_archetype_key, gm_custom_traits,
                gm_history, gm_hire_season,
                hc_id, hc_name, hc_archetype_key, hc_custom_traits,
                hc_history, hc_hire_season, modified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                dynasty_id, team_id, season,
                gm.staff_id, gm.name, gm.archetype_key,
                json.dumps(gm.custom_traits) if gm.custom_traits else None,
                gm.history, gm.hire_season,
                hc.staff_id, hc.name, hc.archetype_key,
                json.dumps(hc.custom_traits) if hc.custom_traits else None,
                hc.history, hc.hire_season,
            )
        )
        return True

    def save_staff_assignment_dict(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        gm_data: Dict[str, Any],
        hc_data: Dict[str, Any]
    ) -> bool:
        """
        Save staff assignment from dictionaries.

        Convenience method for backwards compatibility.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            gm_data: Dict with GM staff fields
            hc_data: Dict with HC staff fields

        Returns:
            True if successful
        """
        gm = StaffMember(
            staff_id=gm_data["staff_id"],
            staff_type=StaffType.GM,
            name=gm_data["name"],
            archetype_key=gm_data["archetype_key"],
            custom_traits=gm_data.get("custom_traits", {}),
            history=gm_data.get("history", ""),
            hire_season=gm_data["hire_season"],
        )
        hc = StaffMember(
            staff_id=hc_data["staff_id"],
            staff_type=StaffType.HEAD_COACH,
            name=hc_data["name"],
            archetype_key=hc_data["archetype_key"],
            custom_traits=hc_data.get("custom_traits", {}),
            history=hc_data.get("history", ""),
            hire_season=hc_data["hire_season"],
        )
        return self.save_staff_assignment(dynasty_id, team_id, season, gm, hc)

    # -------------------- Staff Candidates --------------------

    def get_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: StaffType
    ) -> List[StaffCandidate]:
        """
        Get candidate pool for a staff type.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: StaffType.GM or StaffType.HEAD_COACH

        Returns:
            List of StaffCandidate objects
        """
        rows = self.db.query_all(
            """SELECT * FROM staff_candidates
               WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?
               ORDER BY id""",
            (dynasty_id, team_id, season, staff_type.value)
        )
        return [self._row_to_candidate(row, staff_type) for row in rows]

    def save_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: StaffType,
        candidates: List[StaffCandidate]
    ) -> int:
        """
        Save candidate pool for hiring.

        Clears existing candidates of this type before inserting new ones.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: StaffType.GM or StaffType.HEAD_COACH
            candidates: List of StaffCandidate objects

        Returns:
            Number of candidates saved
        """
        # Clear existing candidates of this type
        self.db.execute(
            """DELETE FROM staff_candidates
               WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?""",
            (dynasty_id, team_id, season, staff_type.value)
        )

        # Insert new candidates
        for candidate in candidates:
            self.db.execute(
                """INSERT INTO staff_candidates
                   (dynasty_id, team_id, season, candidate_id, staff_type,
                    name, archetype_key, custom_traits, history, is_selected)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dynasty_id, team_id, season,
                    candidate.staff_id, staff_type.value,
                    candidate.name, candidate.archetype_key,
                    json.dumps(candidate.custom_traits) if candidate.custom_traits else None,
                    candidate.history, 1 if candidate.is_selected else 0,
                )
            )

        return len(candidates)

    def save_candidates_dict(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type_str: str,
        candidates: List[Dict[str, Any]]
    ) -> int:
        """
        Save candidate pool from dictionaries.

        Convenience method for backwards compatibility.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type_str: 'GM' or 'HC'
            candidates: List of candidate dicts with staff fields

        Returns:
            Number of candidates saved
        """
        staff_type = StaffType(staff_type_str)
        candidate_objects = [
            StaffCandidate(
                staff_id=c["staff_id"],
                staff_type=staff_type,
                name=c["name"],
                archetype_key=c["archetype_key"],
                custom_traits=c.get("custom_traits", {}),
                history=c.get("history", ""),
                is_selected=c.get("is_selected", False),
            )
            for c in candidates
        ]
        return self.save_candidates(dynasty_id, team_id, season, staff_type, candidate_objects)

    def clear_candidates(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        staff_type: Optional[StaffType] = None
    ) -> int:
        """
        Clear candidate pool after hire is complete.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            staff_type: StaffType.GM or StaffType.HEAD_COACH, or None to clear both

        Returns:
            Number of rows deleted
        """
        if staff_type:
            cursor = self.db.execute(
                """DELETE FROM staff_candidates
                   WHERE dynasty_id = ? AND team_id = ? AND season = ? AND staff_type = ?""",
                (dynasty_id, team_id, season, staff_type.value)
            )
        else:
            cursor = self.db.execute(
                """DELETE FROM staff_candidates
                   WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
                (dynasty_id, team_id, season)
            )
        return cursor.rowcount

    def mark_candidate_selected(
        self,
        dynasty_id: str,
        candidate_id: str
    ) -> bool:
        """
        Mark a candidate as selected (hired).

        Args:
            dynasty_id: Dynasty identifier
            candidate_id: Candidate's staff_id

        Returns:
            True if a candidate was updated
        """
        cursor = self.db.execute(
            """UPDATE staff_candidates SET is_selected = 1
               WHERE dynasty_id = ? AND candidate_id = ?""",
            (dynasty_id, candidate_id)
        )
        return cursor.rowcount > 0

    # -------------------- Season Management --------------------

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
        """
        row = self.db.query_one(
            """SELECT * FROM team_staff_assignments
               WHERE dynasty_id = ? AND team_id = ?
               ORDER BY season DESC
               LIMIT 1""",
            (dynasty_id, team_id)
        )
        if not row:
            return None

        return {
            "season": row["season"],
            "gm": self._row_to_gm(row),
            "hc": self._row_to_hc(row),
        }

    # -------------------- Private Methods --------------------

    def _row_to_gm(self, row) -> StaffMember:
        """Extract GM from staff assignment row."""
        return StaffMember(
            staff_id=row['gm_id'],
            staff_type=StaffType.GM,
            name=row['gm_name'],
            archetype_key=row['gm_archetype_key'],
            custom_traits=json.loads(row['gm_custom_traits']) if row['gm_custom_traits'] else {},
            history=row['gm_history'] or '',
            hire_season=row['gm_hire_season'],
        )

    def _row_to_hc(self, row) -> StaffMember:
        """Extract HC from staff assignment row."""
        return StaffMember(
            staff_id=row['hc_id'],
            staff_type=StaffType.HEAD_COACH,
            name=row['hc_name'],
            archetype_key=row['hc_archetype_key'],
            custom_traits=json.loads(row['hc_custom_traits']) if row['hc_custom_traits'] else {},
            history=row['hc_history'] or '',
            hire_season=row['hc_hire_season'],
        )

    def _row_to_candidate(self, row, staff_type: StaffType) -> StaffCandidate:
        """Convert candidate row to StaffCandidate."""
        return StaffCandidate(
            staff_id=row['candidate_id'],
            staff_type=staff_type,
            name=row['name'],
            archetype_key=row['archetype_key'],
            custom_traits=json.loads(row['custom_traits']) if row['custom_traits'] else {},
            history=row['history'] or '',
            is_selected=bool(row['is_selected']),
        )
