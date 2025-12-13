"""
Database API for per-play grade operations.

Provides CRUD operations for:
- Player play grades (player_play_grades table)

This is the most granular level of grading data, storing grades
for every player on every play during FULL simulation mode.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from analytics.models import PlayGrade, PlayContext


class PlayGradesAPI:
    """API for per-play grade database operations."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def insert_play_grade(self, dynasty_id: str, grade: PlayGrade) -> int:
        """Insert a single play grade. Returns the inserted row ID."""
        conn = self._get_connection()
        try:
            # Extract context if available
            quarter = None
            down = None
            distance = None
            yard_line = None
            game_clock = None
            score_differential = None
            play_type = "unknown"
            is_offense = True

            if grade.context:
                quarter = grade.context.quarter
                down = grade.context.down
                distance = grade.context.distance
                yard_line = grade.context.yard_line
                game_clock = grade.context.game_clock
                score_differential = grade.context.score_differential
                play_type = grade.context.play_type
                is_offense = grade.context.is_offense

            # Extract component grades (up to 3 for storage)
            components = list(grade.grade_components.values())
            comp1 = components[0] if len(components) > 0 else None
            comp2 = components[1] if len(components) > 1 else None
            comp3 = components[2] if len(components) > 2 else None

            cursor = conn.execute(
                """
                INSERT INTO player_play_grades
                (dynasty_id, game_id, play_number, player_id, team_id, position,
                 quarter, down, distance, yard_line, game_clock, score_differential,
                 play_type, is_offense, play_grade,
                 grade_component_1, grade_component_2, grade_component_3,
                 was_positive_play, epa_contribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dynasty_id,
                    grade.game_id,
                    grade.play_number,
                    grade.player_id,
                    grade.team_id,
                    grade.position,
                    quarter,
                    down,
                    distance,
                    yard_line,
                    game_clock,
                    score_differential,
                    play_type,
                    1 if is_offense else 0,
                    grade.play_grade,
                    comp1,
                    comp2,
                    comp3,
                    1 if grade.was_positive_play else 0,
                    grade.epa_contribution,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def insert_play_grades_batch(
        self, dynasty_id: str, grades: List[PlayGrade]
    ) -> int:
        """Insert multiple play grades in a single transaction.

        This is the primary method for storing grades during game simulation,
        as it's much more efficient than individual inserts.
        """
        if not grades:
            return 0

        conn = self._get_connection()
        try:
            for grade in grades:
                # Extract context if available
                quarter = None
                down = None
                distance = None
                yard_line = None
                game_clock = None
                score_differential = None
                play_type = "unknown"
                is_offense = True

                if grade.context:
                    quarter = grade.context.quarter
                    down = grade.context.down
                    distance = grade.context.distance
                    yard_line = grade.context.yard_line
                    game_clock = grade.context.game_clock
                    score_differential = grade.context.score_differential
                    play_type = grade.context.play_type
                    is_offense = grade.context.is_offense

                # Extract component grades
                components = list(grade.grade_components.values())
                comp1 = components[0] if len(components) > 0 else None
                comp2 = components[1] if len(components) > 1 else None
                comp3 = components[2] if len(components) > 2 else None

                conn.execute(
                    """
                    INSERT INTO player_play_grades
                    (dynasty_id, game_id, play_number, player_id, team_id, position,
                     quarter, down, distance, yard_line, game_clock, score_differential,
                     play_type, is_offense, play_grade,
                     grade_component_1, grade_component_2, grade_component_3,
                     was_positive_play, epa_contribution)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dynasty_id,
                        grade.game_id,
                        grade.play_number,
                        grade.player_id,
                        grade.team_id,
                        grade.position,
                        quarter,
                        down,
                        distance,
                        yard_line,
                        game_clock,
                        score_differential,
                        play_type,
                        1 if is_offense else 0,
                        grade.play_grade,
                        comp1,
                        comp2,
                        comp3,
                        1 if grade.was_positive_play else 0,
                        grade.epa_contribution,
                    ),
                )
            conn.commit()
            return len(grades)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_game_play_grades(
        self, dynasty_id: str, game_id: str
    ) -> List[PlayGrade]:
        """Get all play grades for a game, ordered by play number."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT play_number, player_id, team_id, position,
                       quarter, down, distance, yard_line, game_clock,
                       score_differential, play_type, is_offense,
                       play_grade, grade_component_1, grade_component_2, grade_component_3,
                       was_positive_play, epa_contribution
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ?
                ORDER BY play_number, player_id
                """,
                (dynasty_id, game_id),
            )
            return [self._row_to_play_grade(row, game_id) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_player_play_grades(
        self, dynasty_id: str, player_id: int, game_id: str
    ) -> List[PlayGrade]:
        """Get play grades for a specific player in a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT play_number, player_id, team_id, position,
                       quarter, down, distance, yard_line, game_clock,
                       score_differential, play_type, is_offense,
                       play_grade, grade_component_1, grade_component_2, grade_component_3,
                       was_positive_play, epa_contribution
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ? AND player_id = ?
                ORDER BY play_number
                """,
                (dynasty_id, game_id, player_id),
            )
            return [self._row_to_play_grade(row, game_id) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_play_grades_by_context(
        self,
        dynasty_id: str,
        game_id: str,
        down: Optional[int] = None,
        quarter: Optional[int] = None,
        is_offense: Optional[bool] = None,
    ) -> List[PlayGrade]:
        """Get play grades filtered by game context."""
        conn = self._get_connection()
        try:
            query = """
                SELECT play_number, player_id, team_id, position,
                       quarter, down, distance, yard_line, game_clock,
                       score_differential, play_type, is_offense,
                       play_grade, grade_component_1, grade_component_2, grade_component_3,
                       was_positive_play, epa_contribution
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ?
            """
            params: List[Any] = [dynasty_id, game_id]

            if down is not None:
                query += " AND down = ?"
                params.append(down)

            if quarter is not None:
                query += " AND quarter = ?"
                params.append(quarter)

            if is_offense is not None:
                query += " AND is_offense = ?"
                params.append(1 if is_offense else 0)

            query += " ORDER BY play_number, player_id"

            cursor = conn.execute(query, params)
            return [self._row_to_play_grade(row, game_id) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_play_grade_summary(
        self, dynasty_id: str, game_id: str, player_id: int
    ) -> Dict[str, Any]:
        """Get summary statistics for a player's play grades in a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_plays,
                    AVG(play_grade) as avg_grade,
                    MIN(play_grade) as min_grade,
                    MAX(play_grade) as max_grade,
                    SUM(CASE WHEN was_positive_play = 1 THEN 1 ELSE 0 END) as positive_plays,
                    SUM(CASE WHEN play_grade < 60 THEN 1 ELSE 0 END) as negative_plays,
                    SUM(epa_contribution) as total_epa
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ? AND player_id = ?
                """,
                (dynasty_id, game_id, player_id),
            )
            row = cursor.fetchone()
            if row and row["total_plays"] > 0:
                return {
                    "total_plays": row["total_plays"],
                    "avg_grade": round(row["avg_grade"], 1) if row["avg_grade"] else 0.0,
                    "min_grade": row["min_grade"],
                    "max_grade": row["max_grade"],
                    "positive_plays": row["positive_plays"],
                    "negative_plays": row["negative_plays"],
                    "total_epa": round(row["total_epa"], 2) if row["total_epa"] else 0.0,
                }
            return {
                "total_plays": 0,
                "avg_grade": 0.0,
                "min_grade": None,
                "max_grade": None,
                "positive_plays": 0,
                "negative_plays": 0,
                "total_epa": 0.0,
            }
        finally:
            conn.close()

    def get_grade_distribution(
        self, dynasty_id: str, game_id: str
    ) -> Dict[str, int]:
        """Get distribution of grades across tiers for a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN play_grade >= 90 THEN 1 ELSE 0 END) as elite,
                    SUM(CASE WHEN play_grade >= 80 AND play_grade < 90 THEN 1 ELSE 0 END) as above_average,
                    SUM(CASE WHEN play_grade >= 60 AND play_grade < 80 THEN 1 ELSE 0 END) as average,
                    SUM(CASE WHEN play_grade >= 40 AND play_grade < 60 THEN 1 ELSE 0 END) as below_average,
                    SUM(CASE WHEN play_grade < 40 THEN 1 ELSE 0 END) as poor
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ?
                """,
                (dynasty_id, game_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "elite": row["elite"] or 0,
                    "above_average": row["above_average"] or 0,
                    "average": row["average"] or 0,
                    "below_average": row["below_average"] or 0,
                    "poor": row["poor"] or 0,
                }
            return {
                "elite": 0,
                "above_average": 0,
                "average": 0,
                "below_average": 0,
                "poor": 0,
            }
        finally:
            conn.close()

    def _row_to_play_grade(self, row: sqlite3.Row, game_id: str) -> PlayGrade:
        """Convert a database row to a PlayGrade object."""
        # Reconstruct context
        context = None
        if row["quarter"] is not None:
            context = PlayContext(
                game_id=game_id,
                play_number=row["play_number"],
                quarter=row["quarter"],
                down=row["down"] or 1,
                distance=row["distance"] or 10,
                yard_line=row["yard_line"] or 50,
                game_clock=row["game_clock"] or 900,
                score_differential=row["score_differential"] or 0,
                play_type=row["play_type"] or "unknown",
                is_offense=bool(row["is_offense"]),
            )

        # Reconstruct component grades
        grade_components = {}
        if row["grade_component_1"] is not None:
            grade_components["component_1"] = row["grade_component_1"]
        if row["grade_component_2"] is not None:
            grade_components["component_2"] = row["grade_component_2"]
        if row["grade_component_3"] is not None:
            grade_components["component_3"] = row["grade_component_3"]

        return PlayGrade(
            player_id=row["player_id"],
            game_id=game_id,
            play_number=row["play_number"],
            position=row["position"],
            team_id=row["team_id"],
            play_grade=row["play_grade"],
            grade_components=grade_components,
            context=context,
            was_positive_play=bool(row["was_positive_play"]),
            epa_contribution=row["epa_contribution"] or 0.0,
        )

    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================

    def delete_game_play_grades(self, dynasty_id: str, game_id: str) -> int:
        """Delete all play grades for a specific game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM player_play_grades WHERE dynasty_id = ? AND game_id = ?",
                (dynasty_id, game_id),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def get_play_count(self, dynasty_id: str, game_id: str) -> int:
        """Get total number of graded plays for a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT play_number) as count
                FROM player_play_grades
                WHERE dynasty_id = ? AND game_id = ?
                """,
                (dynasty_id, game_id),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
        finally:
            conn.close()
