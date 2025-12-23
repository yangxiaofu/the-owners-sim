"""
Game Cycle Draft Order Database API.

Manages draft order operations for the game_cycle.db database.
Uses the game_cycle draft_order schema (id, team_id, prospect_id, is_completed).

This is the SINGLE SOURCE OF TRUTH for game cycle draft order database operations.
"""

from typing import List, Optional
import sqlite3
from dataclasses import dataclass
import logging


@dataclass
class DraftPick:
    """
    Represents a single draft pick in the game cycle database.

    Attributes:
        id: Database primary key (auto-generated, None for new picks)
        dynasty_id: Dynasty identifier for isolation
        season: Draft year (e.g., 2025)
        round_number: Draft round (1-7)
        pick_in_round: Pick number within round (1-32)
        overall_pick: Overall pick number (1-262 for standard 7-round draft)
        team_id: Team that currently owns the pick (1-32)
        is_traded: Whether pick was acquired via trade
        original_team_id: Team that originally owned the pick (1-32)
        prospect_id: Prospect drafted with this pick (None if not executed)
        is_completed: Whether pick has been used to draft a prospect
    """
    id: Optional[int]
    dynasty_id: str
    season: int
    round_number: int
    pick_in_round: int
    overall_pick: int
    team_id: int
    is_traded: bool = False
    original_team_id: Optional[int] = None
    prospect_id: Optional[int] = None
    is_completed: bool = False


class DraftOrderAPI:
    """
    API for managing draft order database operations in game cycle.

    Handles all database operations for the draft_order table including:
    - Draft order persistence and retrieval
    - Pick ownership management (trades)
    - Pick execution tracking (prospect selection)
    - Dynasty isolation support

    Transaction-Aware Design:
    All methods accept an optional `connection` parameter for transaction support.
    - connection=None (default): Auto-commit mode, method manages connection lifecycle
    - connection=<Connection>: Transaction mode, caller manages connection/transaction
    """

    def __init__(self, db_path: str):
        """
        Initialize Draft Order API.

        Args:
            db_path: Path to SQLite database file (game_cycle.db)
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def save_draft_order(
        self,
        picks: List[DraftPick],
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Save complete draft order to database.

        Uses INSERT OR REPLACE to handle both new picks and updates.
        All picks must belong to the same dynasty_id and season.

        Args:
            picks: List of DraftPick objects to save
            conn: Optional existing connection (for transactions)

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Auto-commit mode
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> picks = [
            ...     DraftPick(None, "my_dynasty", 2025, 1, 1, 1, 7, False, 7, None, False),
            ...     DraftPick(None, "my_dynasty", 2025, 1, 2, 2, 9, False, 9, None, False),
            ... ]
            >>> success = api.save_draft_order(picks)
            >>> assert success
        """
        if not picks:
            self.logger.warning("No picks to save")
            return True

        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            # Validate all picks belong to same dynasty/season
            dynasty_ids = set(pick.dynasty_id for pick in picks)
            seasons = set(pick.season for pick in picks)

            if len(dynasty_ids) > 1:
                raise ValueError(f"Picks belong to multiple dynasties: {dynasty_ids}")
            if len(seasons) > 1:
                raise ValueError(f"Picks belong to multiple seasons: {seasons}")

            dynasty_id = picks[0].dynasty_id
            season = picks[0].season

            # Insert query (id auto-generated if None)
            query = """
                INSERT OR REPLACE INTO draft_order (
                    id, dynasty_id, season, round_number, pick_in_round,
                    overall_pick, team_id, is_traded, original_team_id,
                    prospect_id, is_completed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for pick in picks:
                cursor.execute(query, (
                    pick.id,
                    pick.dynasty_id,
                    pick.season,
                    pick.round_number,
                    pick.pick_in_round,
                    pick.overall_pick,
                    pick.team_id,
                    1 if pick.is_traded else 0,
                    pick.original_team_id,
                    pick.prospect_id,
                    1 if pick.is_completed else 0
                ))

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Saved {len(picks)} draft picks for dynasty '{dynasty_id}', season {season}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error saving draft order: {e}", exc_info=True)
            if should_close:
                conn.rollback()
            return False

        finally:
            if should_close and conn:
                conn.close()

    def get_draft_order(
        self,
        dynasty_id: str,
        season: int,
        round_number: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None
    ) -> List[DraftPick]:
        """
        Retrieve draft order for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            round_number: Optional round filter (1-7)
            conn: Optional existing connection

        Returns:
            List of DraftPick objects, ordered by overall_pick

        Examples:
            >>> # Get complete draft order
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> picks = api.get_draft_order("my_dynasty", 2025)
            >>> print(f"Total picks: {len(picks)}")

            >>> # Get only round 1 picks
            >>> round1_picks = api.get_draft_order("my_dynasty", 2025, round_number=1)
            >>> print(f"Round 1 picks: {len(round1_picks)}")
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            # Build query with optional round filter
            if round_number is not None:
                query = """
                    SELECT * FROM draft_order
                    WHERE dynasty_id = ? AND season = ? AND round_number = ?
                    ORDER BY overall_pick ASC
                """
                cursor.execute(query, (dynasty_id, season, round_number))
            else:
                query = """
                    SELECT * FROM draft_order
                    WHERE dynasty_id = ? AND season = ?
                    ORDER BY overall_pick ASC
                """
                cursor.execute(query, (dynasty_id, season))

            rows = cursor.fetchall()

            # Convert rows to DraftPick objects
            picks = []
            for row in rows:
                pick = DraftPick(
                    id=row[0],
                    dynasty_id=row[1],
                    season=row[2],
                    round_number=row[3],
                    pick_in_round=row[4],
                    overall_pick=row[5],
                    team_id=row[6],
                    is_traded=bool(row[7]),
                    original_team_id=row[8],
                    prospect_id=row[9],
                    is_completed=bool(row[10])
                )
                picks.append(pick)

            self.logger.debug(
                f"Retrieved {len(picks)} draft picks for dynasty '{dynasty_id}', "
                f"season {season}" + (f", round {round_number}" if round_number else "")
            )

            return picks

        except Exception as e:
            self.logger.error(
                f"Error retrieving draft order for dynasty '{dynasty_id}', "
                f"season {season}: {e}",
                exc_info=True
            )
            return []

        finally:
            if should_close and conn:
                conn.close()

    def get_team_picks(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> List[DraftPick]:
        """
        Get all picks owned by a team for a specific season.

        Returns picks currently owned by team (team_id), regardless
        of original ownership. Ordered by overall pick number.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team identifier (1-32)
            season: Draft year
            conn: Optional existing connection

        Returns:
            List of DraftPick objects owned by team, ordered by overall_pick

        Examples:
            >>> # Get all picks owned by team 22 (Lions)
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> lions_picks = api.get_team_picks("my_dynasty", 22, 2025)
            >>> for pick in lions_picks:
            ...     print(f"Round {pick.round_number}, Pick {pick.pick_in_round}")
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                SELECT * FROM draft_order
                WHERE dynasty_id = ? AND season = ? AND team_id = ?
                ORDER BY overall_pick ASC
            """
            cursor.execute(query, (dynasty_id, season, team_id))

            rows = cursor.fetchall()

            # Convert rows to DraftPick objects
            picks = []
            for row in rows:
                pick = DraftPick(
                    id=row[0],
                    dynasty_id=row[1],
                    season=row[2],
                    round_number=row[3],
                    pick_in_round=row[4],
                    overall_pick=row[5],
                    team_id=row[6],
                    is_traded=bool(row[7]),
                    original_team_id=row[8],
                    prospect_id=row[9],
                    is_completed=bool(row[10])
                )
                picks.append(pick)

            self.logger.debug(
                f"Retrieved {len(picks)} picks for team {team_id}, "
                f"dynasty '{dynasty_id}', season {season}"
            )

            return picks

        except Exception as e:
            self.logger.error(
                f"Error retrieving team picks for team {team_id}, "
                f"dynasty '{dynasty_id}', season {season}: {e}",
                exc_info=True
            )
            return []

        finally:
            if should_close and conn:
                conn.close()

    def update_pick_ownership(
        self,
        pick_id: int,
        new_owner_team_id: int,
        is_traded: bool = True,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Update pick ownership (for trades).

        Updates team_id and marks as traded.
        Does NOT change original_team_id (preserves draft order origin).

        Args:
            pick_id: Pick identifier (database primary key)
            new_owner_team_id: New owning team (1-32)
            is_traded: Whether acquired via trade (default True)
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Trade pick to different team
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> success = api.update_pick_ownership(
            ...     pick_id=123,
            ...     new_owner_team_id=9
            ... )
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                UPDATE draft_order
                SET team_id = ?,
                    is_traded = ?
                WHERE id = ?
            """

            cursor.execute(query, (
                new_owner_team_id,
                1 if is_traded else 0,
                pick_id
            ))

            # Check if update affected any rows
            if cursor.rowcount == 0:
                self.logger.warning(f"No pick found with id={pick_id}")
                return False

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Updated pick {pick_id} ownership to team {new_owner_team_id}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error updating pick ownership: {e}", exc_info=True)
            if should_close:
                conn.rollback()
            return False

        finally:
            if should_close and conn:
                conn.close()

    def mark_pick_completed(
        self,
        pick_id: int,
        prospect_id: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Mark a pick as completed (prospect drafted).

        Sets is_completed=True and assigns prospect_id to the pick.

        Args:
            pick_id: Pick identifier (database primary key)
            prospect_id: Prospect selected with this pick
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Mark pick as used
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> success = api.mark_pick_completed(pick_id=123, prospect_id=9876)
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                UPDATE draft_order
                SET is_completed = 1,
                    prospect_id = ?
                WHERE id = ?
            """

            cursor.execute(query, (prospect_id, pick_id))

            # Check if update affected any rows
            if cursor.rowcount == 0:
                self.logger.warning(f"No pick found with id={pick_id}")
                return False

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Marked pick {pick_id} as completed with prospect {prospect_id}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error marking pick completed: {e}", exc_info=True)
            if should_close:
                conn.rollback()
            return False

        finally:
            if should_close and conn:
                conn.close()

    def clear_draft_order(
        self,
        dynasty_id: str,
        season: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Clear draft order for a dynasty/season (for recalculation).

        Deletes all draft picks for the specified dynasty and season.
        Useful for regenerating draft order after standings changes.

        WARNING: This is a destructive operation. All pick history will
        be lost. Should only be used before draft begins.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Clear existing draft order for recalculation
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> success = api.clear_draft_order("my_dynasty", 2025)
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                DELETE FROM draft_order
                WHERE dynasty_id = ? AND season = ?
            """

            cursor.execute(query, (dynasty_id, season))
            rows_deleted = cursor.rowcount

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Cleared {rows_deleted} draft picks for dynasty '{dynasty_id}', "
                f"season {season}"
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Error clearing draft order for dynasty '{dynasty_id}', "
                f"season {season}: {e}",
                exc_info=True
            )
            if should_close:
                conn.rollback()
            return False

        finally:
            if should_close and conn:
                conn.close()

    def get_next_available_pick(
        self,
        dynasty_id: str,
        season: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> Optional[DraftPick]:
        """
        Get the next uncompleted pick in draft order.

        Returns the first pick where is_completed=False, ordered by overall_pick.
        Used for auto-advancing draft simulation.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            conn: Optional existing connection

        Returns:
            Next available DraftPick, or None if draft is complete

        Examples:
            >>> # Get next pick on the clock
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> next_pick = api.get_next_available_pick("my_dynasty", 2025)
            >>> if next_pick:
            ...     print(f"Pick {next_pick.overall_pick}: Team {next_pick.team_id}")
            >>> else:
            ...     print("Draft complete!")
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                SELECT * FROM draft_order
                WHERE dynasty_id = ? AND season = ? AND is_completed = 0
                ORDER BY overall_pick ASC
                LIMIT 1
            """

            cursor.execute(query, (dynasty_id, season))
            row = cursor.fetchone()

            if not row:
                return None

            pick = DraftPick(
                id=row[0],
                dynasty_id=row[1],
                season=row[2],
                round_number=row[3],
                pick_in_round=row[4],
                overall_pick=row[5],
                team_id=row[6],
                is_traded=bool(row[7]),
                original_team_id=row[8],
                prospect_id=row[9],
                is_completed=bool(row[10])
            )

            return pick

        except Exception as e:
            self.logger.error(
                f"Error getting next available pick for dynasty '{dynasty_id}', "
                f"season {season}: {e}",
                exc_info=True
            )
            return None

        finally:
            if should_close and conn:
                conn.close()

    def draft_order_exists(
        self,
        dynasty_id: str,
        season: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Check if draft order exists for a dynasty/season.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            conn: Optional existing connection

        Returns:
            True if at least one pick exists, False otherwise

        Examples:
            >>> api = DraftOrderAPI("data/database/game_cycle/game_cycle.db")
            >>> if not api.draft_order_exists("my_dynasty", 2025):
            ...     print("Need to generate draft order")
        """
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                SELECT COUNT(*) FROM draft_order
                WHERE dynasty_id = ? AND season = ?
            """

            cursor.execute(query, (dynasty_id, season))
            count = cursor.fetchone()[0]

            exists = count > 0
            self.logger.debug(
                f"Draft order exists check for dynasty '{dynasty_id}', "
                f"season {season}: {exists} ({count} picks)"
            )

            return exists

        except Exception as e:
            self.logger.error(
                f"Error checking draft order existence for dynasty '{dynasty_id}', "
                f"season {season}: {e}",
                exc_info=True
            )
            return False

        finally:
            if should_close and conn:
                conn.close()
