"""
Draft Order Database API

Centralized API for all draft order database operations.
Provides clean interface for draft pick persistence and management.

This is the SINGLE SOURCE OF TRUTH for draft order database operations.
All draft-related components should use this API instead of raw SQL queries.
"""

from typing import List, Dict, Any, Optional
import sqlite3
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

from .connection import DatabaseConnection


@dataclass
class DraftPick:
    """
    Represents a single draft pick with ownership and execution tracking.

    Attributes:
        pick_id: Database primary key (auto-generated, None for new picks)
        dynasty_id: Dynasty identifier for isolation
        season: Draft year (e.g., 2025)
        round_number: Draft round (1-7)
        pick_in_round: Pick number within round (1-32, or more for compensatory)
        overall_pick: Overall pick number (1-262 for standard 7-round draft)
        original_team_id: Team that originally owned the pick (1-32)
        current_team_id: Team that currently owns the pick (1-32)
        player_id: Player drafted with this pick (None if not executed)
        draft_class_id: Draft class identifier (e.g., "2025_draft_class")
        is_executed: Whether pick has been used to draft a player
        is_compensatory: Whether this is a compensatory pick
        comp_round_end: Whether pick is at end of round (compensatory)
        acquired_via_trade: Whether pick was acquired via trade
        trade_date: Timestamp when pick was traded
        original_trade_id: Identifier of trade that moved the pick
    """
    pick_id: Optional[int]
    dynasty_id: str
    season: int
    round_number: int
    pick_in_round: int
    overall_pick: int
    original_team_id: int
    current_team_id: int
    player_id: Optional[int] = None
    draft_class_id: Optional[str] = None
    is_executed: bool = False
    is_compensatory: bool = False
    comp_round_end: bool = False
    acquired_via_trade: bool = False
    trade_date: Optional[str] = None
    original_trade_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return asdict(self)


class DraftOrderDatabaseAPI:
    """
    API for managing draft order database operations.

    Handles all database operations for the draft_order table including:
    - Draft order persistence and retrieval
    - Pick ownership management (trades)
    - Pick execution tracking (player selection)
    - Dynasty isolation support

    Transaction-Aware Design:
    All methods accept an optional `connection` parameter for transaction support.
    - connection=None (default): Auto-commit mode, method manages connection lifecycle
    - connection=<Connection>: Transaction mode, caller manages connection/transaction
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Draft Order Database API.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)

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
            >>> api = DraftOrderDatabaseAPI()
            >>> picks = [
            ...     DraftPick(None, "my_dynasty", 2025, 1, 1, 1, 7, 7),
            ...     DraftPick(None, "my_dynasty", 2025, 1, 2, 2, 9, 9),
            ... ]
            >>> success = api.save_draft_order(picks)
            >>> assert success

            >>> # Transaction mode
            >>> with TransactionContext(db_path) as conn:
            ...     success = api.save_draft_order(picks, conn=conn)
        """
        if not picks:
            self.logger.warning("No picks to save")
            return True

        should_close = False
        if conn is None:
            conn = self.db.get_connection()
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

            # Insert query (pick_id auto-generated if None)
            query = """
                INSERT OR REPLACE INTO draft_order (
                    pick_id, dynasty_id, season, round_number, pick_in_round,
                    overall_pick, original_team_id, current_team_id, player_id,
                    draft_class_id, is_executed, is_compensatory, comp_round_end,
                    acquired_via_trade, trade_date, original_trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for pick in picks:
                cursor.execute(query, (
                    pick.pick_id,
                    pick.dynasty_id,
                    pick.season,
                    pick.round_number,
                    pick.pick_in_round,
                    pick.overall_pick,
                    pick.original_team_id,
                    pick.current_team_id,
                    pick.player_id,
                    pick.draft_class_id,
                    1 if pick.is_executed else 0,
                    1 if pick.is_compensatory else 0,
                    1 if pick.comp_round_end else 0,
                    1 if pick.acquired_via_trade else 0,
                    pick.trade_date,
                    pick.original_trade_id
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
            >>> api = DraftOrderDatabaseAPI()
            >>> picks = api.get_draft_order("my_dynasty", 2025)
            >>> print(f"Total picks: {len(picks)}")

            >>> # Get only round 1 picks
            >>> round1_picks = api.get_draft_order("my_dynasty", 2025, round_number=1)
            >>> print(f"Round 1 picks: {len(round1_picks)}")
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
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
                    pick_id=row[0],
                    dynasty_id=row[1],
                    season=row[2],
                    round_number=row[3],
                    pick_in_round=row[4],
                    overall_pick=row[5],
                    original_team_id=row[6],
                    current_team_id=row[7],
                    player_id=row[8],
                    draft_class_id=row[9],
                    is_executed=bool(row[10]),
                    is_compensatory=bool(row[11]),
                    comp_round_end=bool(row[12]),
                    acquired_via_trade=bool(row[13]),
                    trade_date=row[14],
                    original_trade_id=row[15]
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

        Returns picks currently owned by team (current_team_id), regardless
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
            >>> api = DraftOrderDatabaseAPI()
            >>> lions_picks = api.get_team_picks("my_dynasty", 22, 2025)
            >>> for pick in lions_picks:
            ...     print(f"Round {pick.round_number}, Pick {pick.pick_in_round}")
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                SELECT * FROM draft_order
                WHERE dynasty_id = ? AND season = ? AND current_team_id = ?
                ORDER BY overall_pick ASC
            """
            cursor.execute(query, (dynasty_id, season, team_id))

            rows = cursor.fetchall()

            # Convert rows to DraftPick objects
            picks = []
            for row in rows:
                pick = DraftPick(
                    pick_id=row[0],
                    dynasty_id=row[1],
                    season=row[2],
                    round_number=row[3],
                    pick_in_round=row[4],
                    overall_pick=row[5],
                    original_team_id=row[6],
                    current_team_id=row[7],
                    player_id=row[8],
                    draft_class_id=row[9],
                    is_executed=bool(row[10]),
                    is_compensatory=bool(row[11]),
                    comp_round_end=bool(row[12]),
                    acquired_via_trade=bool(row[13]),
                    trade_date=row[14],
                    original_trade_id=row[15]
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
        acquired_via_trade: bool = True,
        trade_id: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Update pick ownership (for trades).

        Updates current_team_id and optionally marks as traded with trade metadata.
        Does NOT change original_team_id (preserves draft order origin).

        Args:
            pick_id: Pick identifier (database primary key)
            new_owner_team_id: New owning team (1-32)
            acquired_via_trade: Whether acquired via trade (default True)
            trade_id: Optional trade identifier for tracking
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Trade pick to different team
            >>> api = DraftOrderDatabaseAPI()
            >>> success = api.update_pick_ownership(
            ...     pick_id=123,
            ...     new_owner_team_id=9,
            ...     trade_id="trade_2025_001"
            ... )
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            # Get current timestamp
            trade_date = datetime.utcnow().isoformat() if acquired_via_trade else None

            query = """
                UPDATE draft_order
                SET current_team_id = ?,
                    acquired_via_trade = ?,
                    original_trade_id = ?,
                    trade_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE pick_id = ?
            """

            cursor.execute(query, (
                new_owner_team_id,
                1 if acquired_via_trade else 0,
                trade_id,
                trade_date,
                pick_id
            ))

            # Check if update affected any rows
            if cursor.rowcount == 0:
                self.logger.warning(f"No pick found with pick_id={pick_id}")
                return False

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Updated pick {pick_id} ownership to team {new_owner_team_id}"
                + (f" via trade {trade_id}" if trade_id else "")
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

    def mark_pick_executed(
        self,
        pick_id: int,
        player_id: int,
        conn: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Mark a pick as executed (player drafted).

        Sets is_executed=True and assigns player_id to the pick.

        Args:
            pick_id: Pick identifier (database primary key)
            player_id: Player selected with this pick
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Mark pick as used
            >>> api = DraftOrderDatabaseAPI()
            >>> success = api.mark_pick_executed(pick_id=123, player_id=9876)
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                UPDATE draft_order
                SET is_executed = 1,
                    player_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE pick_id = ?
            """

            cursor.execute(query, (player_id, pick_id))

            # Check if update affected any rows
            if cursor.rowcount == 0:
                self.logger.warning(f"No pick found with pick_id={pick_id}")
                return False

            # Auto-commit if managing own connection
            if should_close:
                conn.commit()

            self.logger.info(
                f"Marked pick {pick_id} as executed with player {player_id}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error marking pick executed: {e}", exc_info=True)
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

        WARNING: This is a destructive operation. All pick history and
        trade metadata will be lost. Should only be used before draft begins.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            conn: Optional existing connection

        Returns:
            True if successful, False otherwise

        Examples:
            >>> # Clear existing draft order for recalculation
            >>> api = DraftOrderDatabaseAPI()
            >>> success = api.clear_draft_order("my_dynasty", 2025)
            >>> assert success
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
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
        Get the next unexecuted pick in draft order.

        Returns the first pick where is_executed=False, ordered by overall_pick.
        Used for auto-advancing draft simulation.

        Args:
            dynasty_id: Dynasty identifier
            season: Draft year
            conn: Optional existing connection

        Returns:
            Next available DraftPick, or None if draft is complete

        Examples:
            >>> # Get next pick on the clock
            >>> api = DraftOrderDatabaseAPI()
            >>> next_pick = api.get_next_available_pick("my_dynasty", 2025)
            >>> if next_pick:
            ...     print(f"Pick {next_pick.overall_pick}: Team {next_pick.current_team_id}")
            >>> else:
            ...     print("Draft complete!")
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
            should_close = True

        try:
            cursor = conn.cursor()

            query = """
                SELECT * FROM draft_order
                WHERE dynasty_id = ? AND season = ? AND is_executed = 0
                ORDER BY overall_pick ASC
                LIMIT 1
            """

            cursor.execute(query, (dynasty_id, season))
            row = cursor.fetchone()

            if not row:
                return None

            pick = DraftPick(
                pick_id=row[0],
                dynasty_id=row[1],
                season=row[2],
                round_number=row[3],
                pick_in_round=row[4],
                overall_pick=row[5],
                original_team_id=row[6],
                current_team_id=row[7],
                player_id=row[8],
                draft_class_id=row[9],
                is_executed=bool(row[10]),
                is_compensatory=bool(row[11]),
                comp_round_end=bool(row[12]),
                acquired_via_trade=bool(row[13]),
                trade_date=row[14],
                original_trade_id=row[15]
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
            >>> api = DraftOrderDatabaseAPI()
            >>> if not api.draft_order_exists("my_dynasty", 2025):
            ...     print("Need to generate draft order")
        """
        should_close = False
        if conn is None:
            conn = self.db.get_connection()
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
