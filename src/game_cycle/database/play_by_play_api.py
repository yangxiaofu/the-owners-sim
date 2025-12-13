"""
Database API for play-by-play persistence.

Provides CRUD operations for:
- Game drives (game_drives table)
- Individual plays (game_plays table)

Enables historical game review with full play-by-play data.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PlayByPlayAPI:
    """API for play-by-play database operations."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def insert_drives_batch(
        self, dynasty_id: str, game_id: str, drives: List[Any]
    ) -> int:
        """
        Insert all drives for a game in a single transaction.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            drives: List of DriveResult objects

        Returns:
            Number of drives inserted
        """
        if not drives:
            return 0

        conn = self._get_connection()
        try:
            count = 0
            for drive_num, drive in enumerate(drives, 1):
                # Extract drive outcome name
                outcome = "unknown"
                if hasattr(drive, 'drive_outcome'):
                    if hasattr(drive.drive_outcome, 'name'):
                        outcome = drive.drive_outcome.name.lower()
                    elif hasattr(drive.drive_outcome, 'value'):
                        outcome = str(drive.drive_outcome.value).lower()
                    else:
                        outcome = str(drive.drive_outcome).lower()

                conn.execute(
                    """
                    INSERT OR REPLACE INTO game_drives
                    (dynasty_id, game_id, drive_number, possession_team_id,
                     quarter_started, starting_clock_seconds, starting_field_position,
                     starting_down, starting_distance,
                     ending_field_position, drive_outcome, points_scored,
                     total_plays, total_yards, time_elapsed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dynasty_id,
                        game_id,
                        drive_num,
                        getattr(drive, 'possessing_team_id', 0),
                        getattr(drive, 'quarter_started', 1),
                        getattr(drive, 'starting_clock_seconds', 900),
                        getattr(drive, 'starting_field_position', 25),
                        getattr(drive, 'starting_down', 1),
                        getattr(drive, 'starting_distance', 10),
                        getattr(drive, 'ending_field_position', 0),
                        outcome,
                        getattr(drive, 'points_scored', 0),
                        getattr(drive, 'total_plays', len(getattr(drive, 'plays', []))),
                        getattr(drive, 'total_yards', 0),
                        getattr(drive, 'time_elapsed', 0),
                    ),
                )
                count += 1

            conn.commit()
            return count
        except Exception as e:
            logger.warning("Failed to insert drives for game %s: %s", game_id, e)
            conn.rollback()
            return 0
        finally:
            conn.close()

    def insert_plays_batch(
        self, dynasty_id: str, game_id: str, drives: List[Any],
        home_team_id: Optional[int] = None, away_team_id: Optional[int] = None
    ) -> int:
        """
        Insert all plays from all drives for a game in a single transaction.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            drives: List of DriveResult objects containing plays
            home_team_id: Home team ID (for score tracking)
            away_team_id: Away team ID (for score tracking)

        Returns:
            Number of plays inserted
        """
        if not drives:
            return 0

        conn = self._get_connection()
        try:
            play_number = 0  # Global play number
            count = 0
            home_score = 0
            away_score = 0

            for drive_num, drive in enumerate(drives, 1):
                plays = getattr(drive, 'plays', [])
                possession_team_id = getattr(drive, 'possessing_team_id', 0)
                quarter = getattr(drive, 'quarter_started', 1)

                # Track clock and field position through the drive
                clock_seconds = getattr(drive, 'starting_clock_seconds', 900)
                yard_line = getattr(drive, 'starting_field_position', 25)
                down = getattr(drive, 'starting_down', 1)
                distance = getattr(drive, 'starting_distance', 10)

                for drive_play_num, play in enumerate(plays, 1):
                    play_number += 1

                    # Determine play type from outcome
                    outcome = getattr(play, 'outcome', 'unknown')
                    play_type = self._classify_play_type(outcome)

                    # Generate play description
                    play_description = self._generate_play_description(play, play_type)

                    # Get yards
                    yards = getattr(play, 'yards', 0)

                    # Get scoring info
                    is_scoring = 1 if getattr(play, 'is_scoring_play', False) else 0
                    points = getattr(play, 'points', 0)

                    # Update score tracking
                    if points > 0:
                        if possession_team_id == home_team_id:
                            home_score += points
                        elif possession_team_id == away_team_id:
                            away_score += points

                    # Get turnover info
                    is_turnover = 1 if getattr(play, 'is_turnover', False) else 0
                    turnover_type = getattr(play, 'turnover_type', None)

                    # Get first down
                    is_first_down = 1 if getattr(play, 'achieved_first_down', False) else 0

                    # Get penalty info
                    is_penalty = 1 if getattr(play, 'penalty_occurred', False) else 0
                    penalty_yards = getattr(play, 'penalty_yards', 0) if is_penalty else None
                    penalty_type = None  # Would need to extract from enforcement_result

                    # Get time elapsed
                    time_elapsed = getattr(play, 'time_elapsed', 0)

                    # Get post-play state
                    down_after = getattr(play, 'down_after_play', None)
                    distance_after = getattr(play, 'distance_after_play', None)
                    field_position_after = getattr(play, 'field_position_after_play', None)

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO game_plays
                        (dynasty_id, game_id, play_number, drive_number, drive_play_number,
                         quarter, game_clock_seconds, down, distance, yard_line,
                         possession_team_id, home_score, away_score,
                         play_type, play_description, yards_gained, outcome,
                         is_scoring_play, is_turnover, turnover_type, is_first_down,
                         is_penalty, penalty_type, penalty_yards, penalty_team_id,
                         points_scored, down_after, distance_after, field_position_after,
                         time_elapsed_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            dynasty_id,
                            game_id,
                            play_number,
                            drive_num,
                            drive_play_num,
                            quarter,
                            int(clock_seconds),
                            down,
                            distance,
                            yard_line,
                            possession_team_id,
                            home_score,
                            away_score,
                            play_type,
                            play_description,
                            yards,
                            outcome,
                            is_scoring,
                            is_turnover,
                            turnover_type,
                            is_first_down,
                            is_penalty,
                            penalty_type,
                            penalty_yards,
                            None,  # penalty_team_id
                            points,
                            down_after,
                            distance_after,
                            field_position_after,
                            time_elapsed,
                        ),
                    )
                    count += 1

                    # Update tracking for next play
                    clock_seconds -= time_elapsed
                    if down_after is not None:
                        down = down_after
                    if distance_after is not None:
                        distance = distance_after
                    if field_position_after is not None:
                        yard_line = field_position_after

            conn.commit()
            return count
        except Exception as e:
            logger.warning("Failed to insert plays for game %s: %s", game_id, e)
            conn.rollback()
            return 0
        finally:
            conn.close()

    def _classify_play_type(self, outcome: str) -> str:
        """Classify play type from outcome string."""
        outcome_lower = outcome.lower()

        if 'pass' in outcome_lower or 'sack' in outcome_lower:
            return 'pass'
        elif 'rush' in outcome_lower or 'scramble' in outcome_lower:
            return 'run'
        elif 'punt' in outcome_lower:
            return 'punt'
        elif 'field_goal' in outcome_lower or 'fg_' in outcome_lower:
            return 'field_goal'
        elif 'kickoff' in outcome_lower:
            return 'kickoff'
        elif 'extra_point' in outcome_lower or 'pat' in outcome_lower:
            return 'extra_point'
        elif 'two_point' in outcome_lower:
            return 'two_point'
        elif 'kneel' in outcome_lower:
            return 'kneel'
        elif 'spike' in outcome_lower:
            return 'spike'
        elif 'intercept' in outcome_lower:
            return 'pass'
        elif 'fumble' in outcome_lower:
            return 'run'  # Default assumption
        else:
            return 'unknown'

    def _generate_play_description(self, play: Any, play_type: str) -> str:
        """Generate human-readable play description."""
        outcome = getattr(play, 'outcome', 'unknown')
        yards = getattr(play, 'yards', 0)

        if play_type == 'pass':
            if 'sack' in outcome.lower():
                return f"Sack for {abs(yards)} yard loss"
            elif 'intercept' in outcome.lower():
                return f"Pass intercepted"
            elif 'incomplete' in outcome.lower():
                return "Incomplete pass"
            elif yards > 0:
                return f"Pass complete for {yards} yards"
            else:
                return f"Pass for {yards} yards"

        elif play_type == 'run':
            if 'fumble' in outcome.lower():
                return f"Run for {yards} yards, FUMBLE"
            elif 'scramble' in outcome.lower():
                return f"QB scramble for {yards} yards"
            else:
                return f"Run for {yards} yards"

        elif play_type == 'punt':
            punt_dist = getattr(play, 'punt_distance', yards)
            return f"Punt for {punt_dist} yards"

        elif play_type == 'field_goal':
            if 'made' in outcome.lower() or 'good' in outcome.lower():
                return "Field goal GOOD"
            else:
                return "Field goal NO GOOD"

        elif play_type == 'kickoff':
            return f"Kickoff"

        elif play_type == 'extra_point':
            if getattr(play, 'is_scoring_play', False):
                return "Extra point GOOD"
            else:
                return "Extra point NO GOOD"

        elif play_type == 'kneel':
            return "QB kneel"

        elif play_type == 'spike':
            return "Spike to stop the clock"

        else:
            return f"{outcome} for {yards} yards"

    def has_play_by_play(self, dynasty_id: str, game_id: str) -> bool:
        """Check if play-by-play data exists for a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM game_plays
                WHERE dynasty_id = ? AND game_id = ?
                """,
                (dynasty_id, game_id),
            )
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    def get_game_drives(self, dynasty_id: str, game_id: str) -> List[Dict[str, Any]]:
        """Get all drives for a game, ordered by drive_number."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM game_drives
                WHERE dynasty_id = ? AND game_id = ?
                ORDER BY drive_number
                """,
                (dynasty_id, game_id),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_game_plays(self, dynasty_id: str, game_id: str) -> List[Dict[str, Any]]:
        """Get all plays for a game, ordered by play_number."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM game_plays
                WHERE dynasty_id = ? AND game_id = ?
                ORDER BY play_number
                """,
                (dynasty_id, game_id),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_drive_plays(
        self, dynasty_id: str, game_id: str, drive_number: int
    ) -> List[Dict[str, Any]]:
        """Get plays for a specific drive."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM game_plays
                WHERE dynasty_id = ? AND game_id = ? AND drive_number = ?
                ORDER BY drive_play_number
                """,
                (dynasty_id, game_id, drive_number),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def delete_game_play_by_play(self, dynasty_id: str, game_id: str) -> int:
        """Delete all play-by-play data for a game. Returns count deleted."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM game_plays WHERE dynasty_id = ? AND game_id = ?",
                (dynasty_id, game_id),
            )
            plays_deleted = cursor.rowcount

            cursor = conn.execute(
                "DELETE FROM game_drives WHERE dynasty_id = ? AND game_id = ?",
                (dynasty_id, game_id),
            )
            drives_deleted = cursor.rowcount

            conn.commit()
            return plays_deleted + drives_deleted
        finally:
            conn.close()
