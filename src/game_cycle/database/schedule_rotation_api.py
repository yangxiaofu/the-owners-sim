"""
Schedule Rotation API - Database operations for NFL schedule rotation state.

Manages rotation state persistence across seasons to ensure proper opponent cycling
following the NFL's 3-year in-conference and 4-year cross-conference rotation system.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .connection import GameCycleDatabase


@dataclass
class RotationState:
    """Represents rotation state for a division in a season."""
    division_id: int
    in_conference_opponent_div: int
    cross_conference_opponent_div: int
    season: int


class ScheduleRotationAPI:
    """
    API for schedule rotation state management.

    Handles CRUD operations on the schedule_rotation table with dynasty isolation.
    Used by NFLScheduleGenerator to determine opponent matchups based on NFL
    rotation rules.

    The NFL uses two rotation cycles:
    - 3-year cycle: Each division plays one other in-conference division
    - 4-year cycle: Each division plays one cross-conference division
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Query Methods --------------------

    def get_rotation_state(
        self,
        dynasty_id: str,
        season: int,
        division_id: int
    ) -> Optional[RotationState]:
        """
        Get rotation state for a specific division in a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            division_id: Division ID (1-8)

        Returns:
            RotationState or None if not found

        Raises:
            ValueError: If division_id is invalid
        """
        if not (1 <= division_id <= 8):
            raise ValueError(f"Invalid division_id: {division_id}. Must be 1-8.")

        row = self.db.query_one(
            """SELECT division_id, in_conference_opponent_div, cross_conference_opponent_div, season
               FROM schedule_rotation
               WHERE dynasty_id = ? AND season = ? AND division_id = ?""",
            (dynasty_id, season, division_id)
        )

        return self._row_to_rotation_state(row) if row else None

    def get_all_rotations_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> List[RotationState]:
        """
        Get rotation state for all 8 divisions in a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of RotationState (8 records, one per division)
        """
        rows = self.db.query_all(
            """SELECT division_id, in_conference_opponent_div, cross_conference_opponent_div, season
               FROM schedule_rotation
               WHERE dynasty_id = ? AND season = ?
               ORDER BY division_id""",
            (dynasty_id, season)
        )

        return [self._row_to_rotation_state(row) for row in rows]

    def has_rotations_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """
        Check if rotation state exists for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if rotations exist for this season
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as cnt
               FROM schedule_rotation
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )

        return row['cnt'] > 0 if row else False

    # -------------------- Write Methods --------------------

    def save_rotation_state(
        self,
        dynasty_id: str,
        season: int,
        division_id: int,
        in_conference_opponent_div: int,
        cross_conference_opponent_div: int
    ) -> None:
        """
        Save rotation state for a division (INSERT or UPDATE).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            division_id: Division ID (1-8)
            in_conference_opponent_div: In-conference opponent division (1-8)
            cross_conference_opponent_div: Cross-conference opponent division (1-8)

        Raises:
            ValueError: If invalid division IDs or self-play attempted
        """
        # Validation
        if not (1 <= division_id <= 8):
            raise ValueError(f"Invalid division_id: {division_id}. Must be 1-8.")
        if not (1 <= in_conference_opponent_div <= 8):
            raise ValueError(
                f"Invalid in_conference_opponent_div: {in_conference_opponent_div}. Must be 1-8."
            )
        if not (1 <= cross_conference_opponent_div <= 8):
            raise ValueError(
                f"Invalid cross_conference_opponent_div: {cross_conference_opponent_div}. Must be 1-8."
            )
        if in_conference_opponent_div == division_id:
            raise ValueError(
                f"Division {division_id} cannot play itself in rotation."
            )

        # Conference validation
        # AFC: 1-4, NFC: 5-8
        own_conference_afc = division_id <= 4
        in_conf_opponent_afc = in_conference_opponent_div <= 4
        cross_conf_opponent_afc = cross_conference_opponent_div <= 4

        if own_conference_afc != in_conf_opponent_afc:
            raise ValueError(
                f"In-conference opponent must be same conference. "
                f"Division {division_id} ({'AFC' if own_conference_afc else 'NFC'}) "
                f"vs {in_conference_opponent_div} ({'AFC' if in_conf_opponent_afc else 'NFC'})"
            )

        if own_conference_afc == cross_conf_opponent_afc:
            raise ValueError(
                f"Cross-conference opponent must be different conference. "
                f"Division {division_id} ({'AFC' if own_conference_afc else 'NFC'}) "
                f"vs {cross_conference_opponent_div} ({'AFC' if cross_conf_opponent_afc else 'NFC'})"
            )

        # Use INSERT OR REPLACE for upsert behavior
        self.db.execute(
            """INSERT INTO schedule_rotation (
                   dynasty_id, season, division_id,
                   in_conference_opponent_div, cross_conference_opponent_div
               ) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(dynasty_id, season, division_id)
               DO UPDATE SET
                   in_conference_opponent_div = excluded.in_conference_opponent_div,
                   cross_conference_opponent_div = excluded.cross_conference_opponent_div""",
            (dynasty_id, season, division_id, in_conference_opponent_div, cross_conference_opponent_div)
        )

    def initialize_rotations(
        self,
        dynasty_id: str,
        season: int
    ) -> None:
        """
        Initialize rotation state for all 8 divisions for a season.

        Calculates rotation opponents based on NFL formula using season year.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year (used as base for rotation calculations)
        """
        for division_id in range(1, 9):
            in_conf = self._calculate_in_conference_opponent(division_id, season)
            cross_conf = self._calculate_cross_conference_opponent(division_id, season)

            self.save_rotation_state(
                dynasty_id=dynasty_id,
                season=season,
                division_id=division_id,
                in_conference_opponent_div=in_conf,
                cross_conference_opponent_div=cross_conf
            )

    def delete_rotations_for_dynasty(
        self,
        dynasty_id: str
    ) -> int:
        """
        Delete all rotation records for a dynasty.

        Used for testing/cleanup.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of records deleted
        """
        # Get count first since execute doesn't return rowcount easily
        row = self.db.query_one(
            "SELECT COUNT(*) as cnt FROM schedule_rotation WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        count = row['cnt'] if row else 0

        self.db.execute(
            "DELETE FROM schedule_rotation WHERE dynasty_id = ?",
            (dynasty_id,)
        )

        return count

    def delete_rotations_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Delete rotation records for a specific season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of records deleted
        """
        row = self.db.query_one(
            "SELECT COUNT(*) as cnt FROM schedule_rotation WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        count = row['cnt'] if row else 0

        self.db.execute(
            "DELETE FROM schedule_rotation WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )

        return count

    # -------------------- Private Methods --------------------

    def _row_to_rotation_state(self, row) -> RotationState:
        """Convert database row to RotationState."""
        return RotationState(
            division_id=row['division_id'],
            in_conference_opponent_div=row['in_conference_opponent_div'],
            cross_conference_opponent_div=row['cross_conference_opponent_div'],
            season=row['season']
        )

    def _calculate_in_conference_opponent(self, division_id: int, season: int) -> int:
        """
        Calculate which in-conference division to play (3-year rotation).

        The NFL rotates each division through the other 3 divisions in their
        conference over a 3-year cycle.

        Args:
            division_id: Division ID (1-8)
            season: Season year

        Returns:
            Opponent division ID (same conference, different division)

        Example:
            AFC East (1) rotates through AFC North (2), South (3), West (4)
            Year 0: Play AFC North (2)
            Year 1: Play AFC South (3)
            Year 2: Play AFC West (4)
            Year 3: Play AFC North (2) [cycle repeats]
        """
        # Determine conference divisions
        if division_id <= 4:  # AFC
            all_divisions = [1, 2, 3, 4]
        else:  # NFC
            all_divisions = [5, 6, 7, 8]

        # Remove own division to get 3 possible opponents
        other_divisions = [d for d in all_divisions if d != division_id]

        # Sort to ensure consistent rotation
        other_divisions.sort()

        # Use season modulo 3 to select opponent
        rotation_index = season % 3

        return other_divisions[rotation_index]

    def _calculate_cross_conference_opponent(self, division_id: int, season: int) -> int:
        """
        Calculate which cross-conference division to play (4-year rotation).

        The NFL rotates each division through all 4 divisions in the opposite
        conference over a 4-year cycle.

        Args:
            division_id: Division ID (1-8)
            season: Season year

        Returns:
            Opponent division ID (opposite conference)

        Example:
            AFC East (1) rotates through NFC East (5), North (6), South (7), West (8)
            Year 0: Play NFC East (5)
            Year 1: Play NFC North (6)
            Year 2: Play NFC South (7)
            Year 3: Play NFC West (8)
            Year 4: Play NFC East (5) [cycle repeats]
        """
        # Determine opposite conference divisions
        if division_id <= 4:  # AFC division plays NFC
            opponent_divisions = [5, 6, 7, 8]
        else:  # NFC division plays AFC
            opponent_divisions = [1, 2, 3, 4]

        # Use season modulo 4 to select opponent
        rotation_index = season % 4

        return opponent_divisions[rotation_index]
