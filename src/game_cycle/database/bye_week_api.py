"""
Bye Week API - Database operations for bye week management.

Part of Milestone 11: Schedule & Rivalries, Tollgate 3.
Handles CRUD operations for bye week assignments with dynasty isolation.
"""

import logging
from collections import Counter
from typing import Dict, List, Optional

from .connection import GameCycleDatabase


class ByeWeekAPI:
    """
    API for bye week database operations.

    Follows dynasty isolation pattern - all operations require dynasty_id.
    Provides methods for saving, querying, and validating bye week assignments.

    NFL bye week rules enforced:
    - Each team gets exactly 1 bye week per season
    - Bye weeks occur between weeks 5-14
    - Maximum 4 teams per bye week
    """

    # Constants for bye week constraints
    BYE_WEEK_START = 5
    BYE_WEEK_END = 14
    MAX_TEAMS_PER_BYE = 4
    TOTAL_TEAMS = 32

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db
        self._logger = logging.getLogger(__name__)

    # -------------------- Query Methods --------------------

    def get_team_bye_week(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> Optional[int]:
        """
        Get a team's bye week for the season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID (1-32)

        Returns:
            Bye week number (5-14) or None if not found
        """
        row = self.db.query_one(
            """SELECT bye_week FROM bye_weeks
               WHERE dynasty_id = ? AND season = ? AND team_id = ?""",
            (dynasty_id, season, team_id)
        )
        return row['bye_week'] if row else None

    def get_teams_on_bye(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[int]:
        """
        Get all teams on bye for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            List of team IDs on bye that week (sorted)
        """
        rows = self.db.query_all(
            """SELECT team_id FROM bye_weeks
               WHERE dynasty_id = ? AND season = ? AND bye_week = ?
               ORDER BY team_id""",
            (dynasty_id, season, week)
        )
        return [row['team_id'] for row in rows]

    def get_all_bye_weeks(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[int, int]:
        """
        Get all bye week assignments for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict mapping team_id -> bye_week
        """
        rows = self.db.query_all(
            """SELECT team_id, bye_week FROM bye_weeks
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return {row['team_id']: row['bye_week'] for row in rows}

    def get_bye_week_count(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Get total number of bye week assignments for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of assignments
        """
        row = self.db.query_one(
            "SELECT COUNT(*) as count FROM bye_weeks WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        return row['count'] if row else 0

    def get_bye_week_distribution(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[int, int]:
        """
        Get count of teams per bye week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict mapping bye_week -> count of teams
        """
        rows = self.db.query_all(
            """SELECT bye_week, COUNT(*) as count FROM bye_weeks
               WHERE dynasty_id = ? AND season = ?
               GROUP BY bye_week
               ORDER BY bye_week""",
            (dynasty_id, season)
        )
        return {row['bye_week']: row['count'] for row in rows}

    # -------------------- Save Methods --------------------

    def save_bye_weeks(
        self,
        dynasty_id: str,
        season: int,
        bye_assignments: Dict[int, int],
        validate: bool = True
    ) -> int:
        """
        Persist bye week assignments for a season.

        Validates assignments before saving. Replaces any existing assignments.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            bye_assignments: Dict mapping team_id -> bye_week
            validate: Whether to validate constraints (skip for official NFL schedules)

        Returns:
            Number of assignments saved

        Raises:
            ValueError: If assignments violate constraints
        """
        # Validate before saving (unless skipped for official schedules)
        if validate:
            self._validate_bye_assignments(bye_assignments)

        # Clear existing assignments for this season
        self.delete_bye_weeks(dynasty_id, season)

        # Insert new assignments
        count = 0
        for team_id, bye_week in bye_assignments.items():
            self.db.execute(
                """INSERT INTO bye_weeks (dynasty_id, season, team_id, bye_week)
                   VALUES (?, ?, ?, ?)""",
                (dynasty_id, season, team_id, bye_week)
            )
            count += 1

        self._logger.debug(
            f"Saved {count} bye week assignments for dynasty={dynasty_id}, season={season}"
        )
        return count

    # -------------------- Delete Methods --------------------

    def delete_bye_weeks(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Delete all bye week assignments for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of assignments deleted
        """
        cursor = self.db.execute(
            "DELETE FROM bye_weeks WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        return cursor.rowcount

    def clear_all_bye_weeks(self, dynasty_id: str) -> int:
        """
        Clear all bye week records for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of records deleted
        """
        cursor = self.db.execute(
            "DELETE FROM bye_weeks WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        return cursor.rowcount

    # -------------------- Validation Methods --------------------

    def _validate_bye_assignments(self, bye_assignments: Dict[int, int]) -> None:
        """
        Validate bye week assignments meet all constraints.

        Constraints:
        - All 32 teams have exactly one bye
        - All byes in weeks 5-14
        - Max 4 teams per bye week

        Args:
            bye_assignments: Dict mapping team_id -> bye_week

        Raises:
            ValueError: If any constraint violated
        """
        # Check all 32 teams present
        if len(bye_assignments) != self.TOTAL_TEAMS:
            raise ValueError(
                f"Expected {self.TOTAL_TEAMS} teams, got {len(bye_assignments)}"
            )

        # Check team ID range
        if set(bye_assignments.keys()) != set(range(1, self.TOTAL_TEAMS + 1)):
            missing = set(range(1, self.TOTAL_TEAMS + 1)) - set(bye_assignments.keys())
            extra = set(bye_assignments.keys()) - set(range(1, self.TOTAL_TEAMS + 1))
            raise ValueError(
                f"Invalid team IDs. Missing: {missing}, Extra: {extra}"
            )

        # Check bye week range
        for team_id, bye_week in bye_assignments.items():
            if not (self.BYE_WEEK_START <= bye_week <= self.BYE_WEEK_END):
                raise ValueError(
                    f"Team {team_id} bye week {bye_week} outside valid range "
                    f"[{self.BYE_WEEK_START}-{self.BYE_WEEK_END}]"
                )

        # Check max teams per bye week
        week_counts = Counter(bye_assignments.values())
        for week, count in week_counts.items():
            if count > self.MAX_TEAMS_PER_BYE:
                raise ValueError(
                    f"Week {week} has {count} teams on bye "
                    f"(max {self.MAX_TEAMS_PER_BYE})"
                )

    def is_team_on_bye(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        week: int
    ) -> bool:
        """
        Check if a specific team has a bye on a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID (1-32)
            week: Week number

        Returns:
            True if team has bye that week
        """
        bye_week = self.get_team_bye_week(dynasty_id, season, team_id)
        return bye_week == week if bye_week is not None else False
