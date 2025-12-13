"""
Database API for player progression history operations.

Part of Tollgate 6: Career History Tracking.
Tracks year-over-year player attribute changes from training camp.
"""
import json
import sqlite3
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ProgressionHistoryRecord:
    """Single season progression record."""
    player_id: int
    season: int
    age: int
    position: str
    team_id: int
    age_category: str
    overall_before: int
    overall_after: int
    overall_change: int
    attribute_changes: List[dict]
    created_at: Optional[str] = None


class ProgressionHistoryAPI:
    """API for player progression history database operations."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def insert_progression_record(
        self,
        dynasty_id: str,
        record: ProgressionHistoryRecord
    ) -> None:
        """Insert or replace a progression history record."""
        conn = self._get_connection()
        try:
            attr_changes_json = json.dumps(record.attribute_changes)
            conn.execute('''
                INSERT OR REPLACE INTO player_progression_history
                (dynasty_id, player_id, season, age, position, team_id,
                 age_category, overall_before, overall_after, overall_change,
                 attribute_changes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dynasty_id,
                record.player_id,
                record.season,
                record.age,
                record.position,
                record.team_id,
                record.age_category,
                record.overall_before,
                record.overall_after,
                record.overall_change,
                attr_changes_json
            ))
            conn.commit()
        finally:
            conn.close()

    def insert_progression_records_batch(
        self,
        dynasty_id: str,
        records: List[ProgressionHistoryRecord]
    ) -> int:
        """Insert multiple progression records in a single transaction."""
        if not records:
            return 0

        conn = self._get_connection()
        try:
            for record in records:
                attr_changes_json = json.dumps(record.attribute_changes)
                conn.execute('''
                    INSERT OR REPLACE INTO player_progression_history
                    (dynasty_id, player_id, season, age, position, team_id,
                     age_category, overall_before, overall_after, overall_change,
                     attribute_changes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dynasty_id,
                    record.player_id,
                    record.season,
                    record.age,
                    record.position,
                    record.team_id,
                    record.age_category,
                    record.overall_before,
                    record.overall_after,
                    record.overall_change,
                    attr_changes_json
                ))
            conn.commit()
            return len(records)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_player_history(
        self,
        dynasty_id: str,
        player_id: int,
        limit: int = 10
    ) -> List[dict]:
        """Get progression history for a player, newest first."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT season, age, position, team_id, age_category,
                       overall_before, overall_after, overall_change,
                       attribute_changes, created_at
                FROM player_progression_history
                WHERE dynasty_id = ? AND player_id = ?
                ORDER BY season DESC
                LIMIT ?
            ''', (dynasty_id, player_id, limit))

            return [
                {
                    "season": row["season"],
                    "age": row["age"],
                    "position": row["position"],
                    "team_id": row["team_id"],
                    "age_category": row["age_category"],
                    "overall_before": row["overall_before"],
                    "overall_after": row["overall_after"],
                    "overall_change": row["overall_change"],
                    "attribute_changes": json.loads(row["attribute_changes"]) if row["attribute_changes"] else [],
                    "created_at": row["created_at"]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_season_history(
        self,
        dynasty_id: str,
        season: int
    ) -> List[dict]:
        """Get all progression records for a season."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT player_id, age, position, team_id, age_category,
                       overall_before, overall_after, overall_change,
                       attribute_changes
                FROM player_progression_history
                WHERE dynasty_id = ? AND season = ?
                ORDER BY overall_change DESC
            ''', (dynasty_id, season))

            rows = cursor.fetchall()
            return [
                {
                    "player_id": row["player_id"],
                    "age": row["age"],
                    "position": row["position"],
                    "team_id": row["team_id"],
                    "age_category": row["age_category"],
                    "overall_before": row["overall_before"],
                    "overall_after": row["overall_after"],
                    "overall_change": row["overall_change"],
                    "attribute_changes": json.loads(row["attribute_changes"]) if row["attribute_changes"] else []
                }
                for row in rows
            ]
        finally:
            conn.close()

    def delete_player_history(
        self,
        dynasty_id: str,
        player_id: int
    ) -> int:
        """Delete all history for a player. Returns count deleted."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                DELETE FROM player_progression_history
                WHERE dynasty_id = ? AND player_id = ?
            ''', (dynasty_id, player_id))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
