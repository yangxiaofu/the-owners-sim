"""
Database API for player persona operations.

Part of Tollgate 3: Persona Service.
Handles CRUD operations for player personas with dynasty isolation.
"""
import sqlite3
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PersonaRecord:
    """Database record for player persona."""

    player_id: int
    persona_type: str
    money_importance: int = 50
    winning_importance: int = 50
    location_importance: int = 50
    playing_time_importance: int = 50
    loyalty_importance: int = 50
    market_size_importance: int = 50
    coaching_fit_importance: int = 50
    relationships_importance: int = 50
    birthplace_state: Optional[str] = None
    college_state: Optional[str] = None
    drafting_team_id: Optional[int] = None
    career_earnings: int = 0
    championship_count: int = 0
    pro_bowl_count: int = 0


class PersonaAPI:
    """API for player persona database operations.

    Follows dynasty isolation pattern - all operations require dynasty_id.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._logger = logging.getLogger(__name__)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def insert_persona(self, dynasty_id: str, record: PersonaRecord) -> bool:
        """Insert or replace a player persona.

        Args:
            dynasty_id: Dynasty identifier for isolation
            record: PersonaRecord with player persona data

        Returns:
            True if successful

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO player_personas
                (dynasty_id, player_id, persona_type,
                 money_importance, winning_importance, location_importance,
                 playing_time_importance, loyalty_importance, market_size_importance,
                 coaching_fit_importance, relationships_importance,
                 birthplace_state, college_state, drafting_team_id,
                 career_earnings, championship_count, pro_bowl_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    dynasty_id,
                    record.player_id,
                    record.persona_type,
                    record.money_importance,
                    record.winning_importance,
                    record.location_importance,
                    record.playing_time_importance,
                    record.loyalty_importance,
                    record.market_size_importance,
                    record.coaching_fit_importance,
                    record.relationships_importance,
                    record.birthplace_state,
                    record.college_state,
                    record.drafting_team_id,
                    record.career_earnings,
                    record.championship_count,
                    record.pro_bowl_count,
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def insert_personas_batch(
        self, dynasty_id: str, records: List[PersonaRecord]
    ) -> int:
        """Insert multiple personas in a single transaction.

        Args:
            dynasty_id: Dynasty identifier for isolation
            records: List of PersonaRecord objects

        Returns:
            Number of records inserted

        Raises:
            sqlite3.Error: On database failure (with rollback)
        """
        if not records:
            return 0

        conn = self._get_connection()
        try:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO player_personas
                    (dynasty_id, player_id, persona_type,
                     money_importance, winning_importance, location_importance,
                     playing_time_importance, loyalty_importance, market_size_importance,
                     coaching_fit_importance, relationships_importance,
                     birthplace_state, college_state, drafting_team_id,
                     career_earnings, championship_count, pro_bowl_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        dynasty_id,
                        record.player_id,
                        record.persona_type,
                        record.money_importance,
                        record.winning_importance,
                        record.location_importance,
                        record.playing_time_importance,
                        record.loyalty_importance,
                        record.market_size_importance,
                        record.coaching_fit_importance,
                        record.relationships_importance,
                        record.birthplace_state,
                        record.college_state,
                        record.drafting_team_id,
                        record.career_earnings,
                        record.championship_count,
                        record.pro_bowl_count,
                    ),
                )
            conn.commit()
            return len(records)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_persona(self, dynasty_id: str, player_id: int) -> Optional[Dict[str, Any]]:
        """Get a single player's persona.

        Args:
            dynasty_id: Dynasty identifier for isolation
            player_id: Player ID

        Returns:
            Dict with persona data or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, persona_type,
                       money_importance, winning_importance, location_importance,
                       playing_time_importance, loyalty_importance, market_size_importance,
                       coaching_fit_importance, relationships_importance,
                       birthplace_state, college_state, drafting_team_id,
                       career_earnings, championship_count, pro_bowl_count,
                       created_at, updated_at
                FROM player_personas
                WHERE dynasty_id = ? AND player_id = ?
            """,
                (dynasty_id, player_id),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_all_personas(self, dynasty_id: str) -> List[Dict[str, Any]]:
        """Get all personas for a dynasty.

        Args:
            dynasty_id: Dynasty identifier for isolation

        Returns:
            List of dicts with persona data
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, persona_type,
                       money_importance, winning_importance, location_importance,
                       playing_time_importance, loyalty_importance, market_size_importance,
                       coaching_fit_importance, relationships_importance,
                       birthplace_state, college_state, drafting_team_id,
                       career_earnings, championship_count, pro_bowl_count
                FROM player_personas
                WHERE dynasty_id = ?
                ORDER BY player_id
            """,
                (dynasty_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_personas_by_team(
        self, dynasty_id: str, team_id: int
    ) -> List[Dict[str, Any]]:
        """Get all personas for players on a specific team.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID to filter by

        Returns:
            List of dicts with persona data

        Note:
            Requires a join with players table to filter by current team.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT pp.player_id, pp.persona_type,
                       pp.money_importance, pp.winning_importance, pp.location_importance,
                       pp.playing_time_importance, pp.loyalty_importance, pp.market_size_importance,
                       pp.coaching_fit_importance, pp.relationships_importance,
                       pp.birthplace_state, pp.college_state, pp.drafting_team_id,
                       pp.career_earnings, pp.championship_count, pp.pro_bowl_count
                FROM player_personas pp
                JOIN players p ON pp.dynasty_id = p.dynasty_id AND pp.player_id = p.player_id
                WHERE pp.dynasty_id = ? AND p.team_id = ?
                ORDER BY pp.player_id
            """,
                (dynasty_id, team_id),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_career_context(
        self,
        dynasty_id: str,
        player_id: int,
        career_earnings: int,
        championship_count: int,
        pro_bowl_count: int,
    ) -> bool:
        """Update career context fields for a persona.

        Args:
            dynasty_id: Dynasty identifier for isolation
            player_id: Player ID
            career_earnings: Total career earnings
            championship_count: Number of championships won
            pro_bowl_count: Number of Pro Bowl selections

        Returns:
            True if a row was updated

        Raises:
            sqlite3.Error: On database failure
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                UPDATE player_personas
                SET career_earnings = ?,
                    championship_count = ?,
                    pro_bowl_count = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE dynasty_id = ? AND player_id = ?
            """,
                (career_earnings, championship_count, pro_bowl_count, dynasty_id, player_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_persona(self, dynasty_id: str, player_id: int) -> bool:
        """Delete a player's persona.

        Args:
            dynasty_id: Dynasty identifier for isolation
            player_id: Player ID

        Returns:
            True if a row was deleted
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                DELETE FROM player_personas
                WHERE dynasty_id = ? AND player_id = ?
            """,
                (dynasty_id, player_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def persona_exists(self, dynasty_id: str, player_id: int) -> bool:
        """Check if a persona exists for a player.

        Args:
            dynasty_id: Dynasty identifier for isolation
            player_id: Player ID

        Returns:
            True if persona exists
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT 1 FROM player_personas
                WHERE dynasty_id = ? AND player_id = ?
                LIMIT 1
            """,
                (dynasty_id, player_id),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_persona_count(self, dynasty_id: str) -> int:
        """Get total number of personas for a dynasty.

        Args:
            dynasty_id: Dynasty identifier for isolation

        Returns:
            Count of personas
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM player_personas
                WHERE dynasty_id = ?
            """,
                (dynasty_id,),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
        finally:
            conn.close()