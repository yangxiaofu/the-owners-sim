"""
Database API for analytics operations.

Provides CRUD operations for:
- Player game grades (player_game_grades table)
- Player season grades (player_season_grades table)
- Advanced game metrics (advanced_game_metrics table)
"""

import sqlite3
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from analytics.models import GameGrade, SeasonGrade, AdvancedMetrics


# Maps UI position abbreviations/groups to database position names
POSITION_GROUPS = {
    'QB': ['quarterback'],
    'RB': ['running_back', 'halfback', 'fullback'],
    'WR': ['wide_receiver'],
    'TE': ['tight_end'],
    'OL': ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle',
           'offensive_guard', 'offensive_tackle', 'guard', 'tackle'],
    'DL': ['defensive_end', 'defensive_tackle', 'nose_tackle'],
    'LB': ['linebacker', 'inside_linebacker', 'middle_linebacker',
           'outside_linebacker', 'mike_linebacker', 'sam_linebacker', 'will_linebacker'],
    'DB': ['cornerback', 'safety', 'free_safety', 'strong_safety'],
}


class AnalyticsAPI:
    """API for analytics database operations."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # GAME GRADES
    # =========================================================================

    def insert_game_grade(self, dynasty_id: str, grade: GameGrade) -> int:
        """Insert a game grade record. Returns the inserted row ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO player_game_grades
                (dynasty_id, game_id, season, week, player_id, team_id, position,
                 overall_grade, passing_grade, rushing_grade, receiving_grade,
                 pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                 run_defense_grade, coverage_grade, tackling_grade,
                 offensive_snaps, defensive_snaps, special_teams_snaps,
                 epa_total, success_rate, play_count, positive_plays, negative_plays)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dynasty_id,
                    grade.game_id,
                    grade.season,
                    grade.week,
                    grade.player_id,
                    grade.team_id,
                    grade.position,
                    grade.overall_grade,
                    grade.passing_grade,
                    grade.rushing_grade,
                    grade.receiving_grade,
                    grade.pass_blocking_grade,
                    grade.run_blocking_grade,
                    grade.pass_rush_grade,
                    grade.run_defense_grade,
                    grade.coverage_grade,
                    grade.tackling_grade,
                    grade.offensive_snaps,
                    grade.defensive_snaps,
                    grade.special_teams_snaps,
                    grade.epa_total,
                    grade.success_rate,
                    grade.play_count,
                    grade.positive_plays,
                    grade.negative_plays,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def insert_game_grades_batch(
        self, dynasty_id: str, grades: List[GameGrade]
    ) -> int:
        """Insert multiple game grades in a single transaction."""
        if not grades:
            return 0

        conn = self._get_connection()
        try:
            for grade in grades:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO player_game_grades
                    (dynasty_id, game_id, season, week, player_id, team_id, position,
                     overall_grade, passing_grade, rushing_grade, receiving_grade,
                     pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                     run_defense_grade, coverage_grade, tackling_grade,
                     offensive_snaps, defensive_snaps, special_teams_snaps,
                     epa_total, success_rate, play_count, positive_plays, negative_plays)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dynasty_id,
                        grade.game_id,
                        grade.season,
                        grade.week,
                        grade.player_id,
                        grade.team_id,
                        grade.position,
                        grade.overall_grade,
                        grade.passing_grade,
                        grade.rushing_grade,
                        grade.receiving_grade,
                        grade.pass_blocking_grade,
                        grade.run_blocking_grade,
                        grade.pass_rush_grade,
                        grade.run_defense_grade,
                        grade.coverage_grade,
                        grade.tackling_grade,
                        grade.offensive_snaps,
                        grade.defensive_snaps,
                        grade.special_teams_snaps,
                        grade.epa_total,
                        grade.success_rate,
                        grade.play_count,
                        grade.positive_plays,
                        grade.negative_plays,
                    ),
                )
            conn.commit()
            return len(grades)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_game_grades(self, dynasty_id: str, game_id: str) -> List[GameGrade]:
        """Get all player grades for a specific game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, game_id, season, week, position, team_id,
                       overall_grade, passing_grade, rushing_grade, receiving_grade,
                       pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                       run_defense_grade, coverage_grade, tackling_grade,
                       offensive_snaps, defensive_snaps, special_teams_snaps,
                       epa_total, success_rate, play_count, positive_plays, negative_plays
                FROM player_game_grades
                WHERE dynasty_id = ? AND game_id = ?
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, game_id),
            )
            return [self._row_to_game_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_player_game_grades(
        self, dynasty_id: str, player_id: int, season: Optional[int] = None, limit: int = 20
    ) -> List[GameGrade]:
        """Get game grades for a specific player, optionally filtered by season."""
        conn = self._get_connection()
        try:
            if season is not None:
                cursor = conn.execute(
                    """
                    SELECT player_id, game_id, season, week, position, team_id,
                           overall_grade, passing_grade, rushing_grade, receiving_grade,
                           pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                           run_defense_grade, coverage_grade, tackling_grade,
                           offensive_snaps, defensive_snaps, special_teams_snaps,
                           epa_total, success_rate, play_count, positive_plays, negative_plays
                    FROM player_game_grades
                    WHERE dynasty_id = ? AND player_id = ? AND season = ?
                    ORDER BY week DESC
                    LIMIT ?
                    """,
                    (dynasty_id, player_id, season, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT player_id, game_id, season, week, position, team_id,
                           overall_grade, passing_grade, rushing_grade, receiving_grade,
                           pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                           run_defense_grade, coverage_grade, tackling_grade,
                           offensive_snaps, defensive_snaps, special_teams_snaps,
                           epa_total, success_rate, play_count, positive_plays, negative_plays
                    FROM player_game_grades
                    WHERE dynasty_id = ? AND player_id = ?
                    ORDER BY season DESC, week DESC
                    LIMIT ?
                    """,
                    (dynasty_id, player_id, limit),
                )
            return [self._row_to_game_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_game_grades_for_season(
        self, dynasty_id: str, season: int
    ) -> List[GameGrade]:
        """Get all game grades for a season (for aggregation)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, game_id, season, week, position, team_id,
                       overall_grade, passing_grade, rushing_grade, receiving_grade,
                       pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                       run_defense_grade, coverage_grade, tackling_grade,
                       offensive_snaps, defensive_snaps, special_teams_snaps,
                       epa_total, success_rate, play_count, positive_plays, negative_plays
                FROM player_game_grades
                WHERE dynasty_id = ? AND season = ?
                ORDER BY player_id, week
                """,
                (dynasty_id, season),
            )
            return [self._row_to_game_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _row_to_game_grade(self, row: sqlite3.Row) -> GameGrade:
        """Convert a database row to a GameGrade object."""
        return GameGrade(
            player_id=row["player_id"],
            game_id=row["game_id"],
            season=row["season"],
            week=row["week"],
            position=row["position"],
            team_id=row["team_id"],
            overall_grade=row["overall_grade"],
            passing_grade=row["passing_grade"],
            rushing_grade=row["rushing_grade"],
            receiving_grade=row["receiving_grade"],
            pass_blocking_grade=row["pass_blocking_grade"],
            run_blocking_grade=row["run_blocking_grade"],
            pass_rush_grade=row["pass_rush_grade"],
            run_defense_grade=row["run_defense_grade"],
            coverage_grade=row["coverage_grade"],
            tackling_grade=row["tackling_grade"],
            offensive_snaps=row["offensive_snaps"] or 0,
            defensive_snaps=row["defensive_snaps"] or 0,
            special_teams_snaps=row["special_teams_snaps"] or 0,
            epa_total=row["epa_total"] or 0.0,
            success_rate=row["success_rate"],
            play_count=row["play_count"] or 0,
            positive_plays=row["positive_plays"] or 0,
            negative_plays=row["negative_plays"] or 0,
        )

    # =========================================================================
    # SEASON GRADES
    # =========================================================================

    def upsert_season_grade(self, dynasty_id: str, grade: SeasonGrade) -> int:
        """Insert or update a season grade record."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO player_season_grades
                (dynasty_id, season, player_id, team_id, position,
                 overall_grade, passing_grade, rushing_grade, receiving_grade,
                 pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                 run_defense_grade, coverage_grade, tackling_grade,
                 total_snaps, games_graded, total_plays_graded, positive_play_rate,
                 epa_total, epa_per_play, position_rank, overall_rank, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    dynasty_id,
                    grade.season,
                    grade.player_id,
                    grade.team_id,
                    grade.position,
                    grade.overall_grade,
                    grade.passing_grade,
                    grade.rushing_grade,
                    grade.receiving_grade,
                    grade.pass_blocking_grade,
                    grade.run_blocking_grade,
                    grade.pass_rush_grade,
                    grade.run_defense_grade,
                    grade.coverage_grade,
                    grade.tackling_grade,
                    grade.total_snaps,
                    grade.games_graded,
                    grade.total_plays_graded,
                    grade.positive_play_rate,
                    grade.epa_total,
                    grade.epa_per_play,
                    grade.position_rank,
                    grade.overall_rank,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def upsert_season_grades_batch(
        self, dynasty_id: str, grades: List[SeasonGrade]
    ) -> int:
        """Insert or update multiple season grades."""
        if not grades:
            return 0

        conn = self._get_connection()
        try:
            for grade in grades:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO player_season_grades
                    (dynasty_id, season, player_id, team_id, position,
                     overall_grade, passing_grade, rushing_grade, receiving_grade,
                     pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                     run_defense_grade, coverage_grade, tackling_grade,
                     total_snaps, games_graded, total_plays_graded, positive_play_rate,
                     epa_total, epa_per_play, position_rank, overall_rank, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        dynasty_id,
                        grade.season,
                        grade.player_id,
                        grade.team_id,
                        grade.position,
                        grade.overall_grade,
                        grade.passing_grade,
                        grade.rushing_grade,
                        grade.receiving_grade,
                        grade.pass_blocking_grade,
                        grade.run_blocking_grade,
                        grade.pass_rush_grade,
                        grade.run_defense_grade,
                        grade.coverage_grade,
                        grade.tackling_grade,
                        grade.total_snaps,
                        grade.games_graded,
                        grade.total_plays_graded,
                        grade.positive_play_rate,
                        grade.epa_total,
                        grade.epa_per_play,
                        grade.position_rank,
                        grade.overall_rank,
                    ),
                )
            conn.commit()
            return len(grades)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_season_grade(
        self, dynasty_id: str, player_id: int, season: int
    ) -> Optional[SeasonGrade]:
        """Get season grade for a specific player and season."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, season, position, team_id,
                       overall_grade, passing_grade, rushing_grade, receiving_grade,
                       pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                       run_defense_grade, coverage_grade, tackling_grade,
                       total_snaps, games_graded, total_plays_graded, positive_play_rate,
                       epa_total, epa_per_play, position_rank, overall_rank
                FROM player_season_grades
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
                """,
                (dynasty_id, player_id, season),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_season_grade(row)
            return None
        finally:
            conn.close()

    def get_grade_leaders(
        self,
        dynasty_id: str,
        season: int,
        position: Optional[str] = None,
        limit: int = 25,
    ) -> List[SeasonGrade]:
        """Get top players by overall grade for a season."""
        conn = self._get_connection()
        try:
            if position:
                cursor = conn.execute(
                    """
                    SELECT player_id, season, position, team_id,
                           overall_grade, passing_grade, rushing_grade, receiving_grade,
                           pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                           run_defense_grade, coverage_grade, tackling_grade,
                           total_snaps, games_graded, total_plays_graded, positive_play_rate,
                           epa_total, epa_per_play, position_rank, overall_rank
                    FROM player_season_grades
                    WHERE dynasty_id = ? AND season = ? AND position = ?
                    ORDER BY overall_grade DESC
                    LIMIT ?
                    """,
                    (dynasty_id, season, position, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT player_id, season, position, team_id,
                           overall_grade, passing_grade, rushing_grade, receiving_grade,
                           pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                           run_defense_grade, coverage_grade, tackling_grade,
                           total_snaps, games_graded, total_plays_graded, positive_play_rate,
                           epa_total, epa_per_play, position_rank, overall_rank
                    FROM player_season_grades
                    WHERE dynasty_id = ? AND season = ?
                    ORDER BY overall_grade DESC
                    LIMIT ?
                    """,
                    (dynasty_id, season, limit),
                )
            return [self._row_to_season_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_team_season_grades(
        self, dynasty_id: str, team_id: int, season: int
    ) -> List[SeasonGrade]:
        """Get all player grades for a team in a season."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, season, position, team_id,
                       overall_grade, passing_grade, rushing_grade, receiving_grade,
                       pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                       run_defense_grade, coverage_grade, tackling_grade,
                       total_snaps, games_graded, total_plays_graded, positive_play_rate,
                       epa_total, epa_per_play, position_rank, overall_rank
                FROM player_season_grades
                WHERE dynasty_id = ? AND team_id = ? AND season = ?
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, team_id, season),
            )
            return [self._row_to_season_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_season_grades(
        self, dynasty_id: str, season: int
    ) -> List[SeasonGrade]:
        """Get all season grades for a season."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT player_id, season, position, team_id,
                       overall_grade, passing_grade, rushing_grade, receiving_grade,
                       pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                       run_defense_grade, coverage_grade, tackling_grade,
                       total_snaps, games_graded, total_plays_graded, positive_play_rate,
                       epa_total, epa_per_play, position_rank, overall_rank
                FROM player_season_grades
                WHERE dynasty_id = ? AND season = ?
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, season),
            )
            return [self._row_to_season_grade(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_grade_leaders_from_game_grades(
        self,
        dynasty_id: str,
        season: int,
        position: Optional[str] = None,
        limit: int = 25,
        min_snaps: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get top players by aggregated game grades (for when season grades aren't updated).

        Aggregates directly from player_game_grades table with snap-weighted averages.
        Includes position rank calculated via window function.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            position: Optional position filter (e.g., 'QB', 'WR')
            limit: Number of leaders to return
            min_snaps: Minimum total snaps required. If None, calculates dynamically
                       as (current_week * 20) to require ~20 snaps/game average.
        """
        conn = self._get_connection()
        try:
            # Build position filter using POSITION_GROUPS mapping
            params = [dynasty_id, season, dynasty_id, season]  # Extra params for season_progress CTE
            if position:
                positions_list = POSITION_GROUPS.get(position, [position])
                placeholders = ','.join(['?' for _ in positions_list])
                position_filter = f"AND pg.position IN ({placeholders})"
                params.extend(positions_list)
            else:
                position_filter = ""

            # Handle min_snaps: if provided, use fixed value; otherwise use dynamic calculation
            if min_snaps is not None:
                min_snaps_clause = str(min_snaps)
            else:
                # Dynamic: current_week * MIN_SNAPS_PER_GAME_FOR_LEADERS
                from analytics.grading_constants import MIN_SNAPS_PER_GAME_FOR_LEADERS
                min_snaps_clause = f"(SELECT COALESCE(MAX(week), 1) * {MIN_SNAPS_PER_GAME_FOR_LEADERS} FROM season_progress)"

            params.append(limit)

            # Use CTEs: first get season progress, then aggregate, then calculate ranks
            cursor = conn.execute(
                f"""
                WITH season_progress AS (
                    SELECT MAX(week) as current_week
                    FROM player_game_grades
                    WHERE dynasty_id = ? AND season = ?
                ),
                aggregated AS (
                    SELECT
                        pg.player_id,
                        pg.position,
                        pg.team_id,
                        SUM(pg.overall_grade * (pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps)) /
                        NULLIF(SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps), 0) as overall_grade,
                        SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps) as total_snaps,
                        COUNT(DISTINCT pg.game_id) as games_graded,
                        SUM(pg.epa_total) as epa_total,
                        p.first_name || ' ' || p.last_name as player_name
                    FROM player_game_grades pg
                    LEFT JOIN players p ON pg.player_id = p.player_id AND pg.dynasty_id = p.dynasty_id
                    WHERE pg.dynasty_id = ? AND pg.season = ?
                    {position_filter}
                    GROUP BY pg.player_id, pg.position, pg.team_id
                    HAVING total_snaps >= {min_snaps_clause}
                )
                SELECT
                    player_id,
                    position,
                    team_id,
                    overall_grade,
                    total_snaps,
                    games_graded,
                    epa_total,
                    player_name,
                    RANK() OVER (PARTITION BY position ORDER BY overall_grade DESC) as position_rank,
                    RANK() OVER (ORDER BY overall_grade DESC) as overall_rank
                FROM aggregated
                ORDER BY overall_grade DESC
                LIMIT ?
                """,
                params,
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'position': row['position'],
                    'team_id': row['team_id'],
                    'overall_grade': row['overall_grade'] or 0.0,
                    'total_snaps': row['total_snaps'] or 0,
                    'games_graded': row['games_graded'] or 0,
                    'epa_total': row['epa_total'] or 0.0,
                    'player_name': row['player_name'] or 'Unknown',
                    'position_rank': row['position_rank'],
                    'overall_rank': row['overall_rank'],
                })
            return results
        finally:
            conn.close()

    def get_team_grades_from_game_grades(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
    ) -> List[Dict]:
        """
        Get all player grades for a team from aggregated game grades.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    pg.player_id,
                    pg.position,
                    pg.team_id,
                    SUM(pg.overall_grade * (pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps)) /
                    NULLIF(SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps), 0) as overall_grade,
                    SUM(pg.offensive_snaps) as offense_snaps,
                    SUM(pg.defensive_snaps) as defense_snaps,
                    SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps) as total_snaps,
                    COUNT(DISTINCT pg.game_id) as games_graded,
                    SUM(pg.epa_total) as epa_total,
                    p.first_name || ' ' || p.last_name as player_name
                FROM player_game_grades pg
                LEFT JOIN players p ON pg.player_id = p.player_id AND pg.dynasty_id = p.dynasty_id
                WHERE pg.dynasty_id = ? AND pg.team_id = ? AND pg.season = ?
                GROUP BY pg.player_id, pg.position, pg.team_id
                HAVING total_snaps > 0
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, team_id, season),
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'position': row['position'],
                    'team_id': row['team_id'],
                    'overall_grade': row['overall_grade'] or 0.0,
                    'offense_grade': row['overall_grade'] if row['offense_snaps'] > 0 else 0.0,
                    'defense_grade': row['overall_grade'] if row['defense_snaps'] > 0 else 0.0,
                    'total_snaps': row['total_snaps'] or 0,
                    'games_graded': row['games_graded'] or 0,
                    'epa_total': row['epa_total'] or 0.0,
                    'player_name': row['player_name'] or 'Unknown',
                })
            return results
        finally:
            conn.close()

    def get_league_grades_from_game_grades(
        self,
        dynasty_id: str,
        season: int,
    ) -> List[Dict]:
        """
        Get all player grades league-wide from aggregated game grades.
        Used for calculating position rankings across all teams.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    pg.player_id,
                    pg.position,
                    pg.team_id,
                    SUM(pg.overall_grade * (pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps)) /
                    NULLIF(SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps), 0) as overall_grade,
                    SUM(pg.offensive_snaps + pg.defensive_snaps + pg.special_teams_snaps) as total_snaps,
                    COUNT(DISTINCT pg.game_id) as games_graded,
                    p.first_name || ' ' || p.last_name as player_name
                FROM player_game_grades pg
                LEFT JOIN players p ON pg.player_id = p.player_id AND pg.dynasty_id = p.dynasty_id
                WHERE pg.dynasty_id = ? AND pg.season = ?
                GROUP BY pg.player_id, pg.position, pg.team_id
                HAVING total_snaps > 0
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, season),
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'position': row['position'],
                    'team_id': row['team_id'],
                    'overall_grade': row['overall_grade'] or 0.0,
                    'total_snaps': row['total_snaps'] or 0,
                    'games_graded': row['games_graded'] or 0,
                    'player_name': row['player_name'] or 'Unknown',
                })
            return results
        finally:
            conn.close()

    def get_player_game_history(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
    ) -> List[Dict]:
        """
        Get a player's game-by-game grade history for a season.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player to query
            season: Season year

        Returns:
            List of game grade dictionaries with week, opponent, grades, snaps
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    pg.game_id,
                    pg.week,
                    pg.overall_grade,
                    pg.offensive_snaps,
                    pg.defensive_snaps,
                    pg.special_teams_snaps,
                    pg.epa_total,
                    pg.team_id,
                    g.home_team_id,
                    g.away_team_id
                FROM player_game_grades pg
                LEFT JOIN games g ON pg.game_id = g.game_id AND pg.dynasty_id = g.dynasty_id
                WHERE pg.dynasty_id = ? AND pg.player_id = ? AND pg.season = ?
                ORDER BY pg.week ASC
                """,
                (dynasty_id, player_id, season),
            )

            results = []
            for row in cursor.fetchall():
                player_team = row['team_id']
                home_team = row['home_team_id']
                away_team = row['away_team_id']

                # Determine opponent
                if player_team == home_team:
                    opponent_id = away_team
                else:
                    opponent_id = home_team

                off_snaps = row['offensive_snaps'] or 0
                def_snaps = row['defensive_snaps'] or 0
                st_snaps = row['special_teams_snaps'] or 0
                total_snaps = off_snaps + def_snaps + st_snaps

                results.append({
                    'game_id': row['game_id'],
                    'week': row['week'],
                    'overall_grade': row['overall_grade'] or 0.0,
                    'offense_grade': row['overall_grade'] if off_snaps > 0 else 0.0,
                    'defense_grade': row['overall_grade'] if def_snaps > 0 else 0.0,
                    'snaps': total_snaps,
                    'opponent_team_id': opponent_id,
                    'epa_total': row['epa_total'] or 0.0,
                    'key_stats': '-',  # Placeholder for future enhancement
                })
            return results
        finally:
            conn.close()

    def _row_to_season_grade(self, row: sqlite3.Row) -> SeasonGrade:
        """Convert a database row to a SeasonGrade object."""
        return SeasonGrade(
            player_id=row["player_id"],
            season=row["season"],
            position=row["position"],
            team_id=row["team_id"],
            overall_grade=row["overall_grade"],
            passing_grade=row["passing_grade"],
            rushing_grade=row["rushing_grade"],
            receiving_grade=row["receiving_grade"],
            pass_blocking_grade=row["pass_blocking_grade"],
            run_blocking_grade=row["run_blocking_grade"],
            pass_rush_grade=row["pass_rush_grade"],
            run_defense_grade=row["run_defense_grade"],
            coverage_grade=row["coverage_grade"],
            tackling_grade=row["tackling_grade"],
            total_snaps=row["total_snaps"] or 0,
            games_graded=row["games_graded"] or 0,
            total_plays_graded=row["total_plays_graded"] or 0,
            positive_play_rate=row["positive_play_rate"],
            epa_total=row["epa_total"] or 0.0,
            epa_per_play=row["epa_per_play"],
            position_rank=row["position_rank"],
            overall_rank=row["overall_rank"],
        )

    # =========================================================================
    # ADVANCED METRICS
    # =========================================================================

    def insert_advanced_metrics(
        self, dynasty_id: str, metrics: AdvancedMetrics
    ) -> int:
        """Insert advanced game metrics for a team."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO advanced_game_metrics
                (dynasty_id, game_id, team_id,
                 epa_total, epa_passing, epa_rushing, epa_per_play,
                 success_rate, passing_success_rate, rushing_success_rate,
                 air_yards_total, yac_total, completion_pct_over_expected,
                 avg_time_to_throw, pressure_rate,
                 pass_rush_win_rate, coverage_success_rate, missed_tackle_rate,
                 forced_incompletions, qb_hits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dynasty_id,
                    metrics.game_id,
                    metrics.team_id,
                    metrics.epa_total,
                    metrics.epa_passing,
                    metrics.epa_rushing,
                    metrics.epa_per_play,
                    metrics.success_rate,
                    metrics.passing_success_rate,
                    metrics.rushing_success_rate,
                    metrics.air_yards_total,
                    metrics.yac_total,
                    metrics.completion_pct_over_expected,
                    metrics.avg_time_to_throw,
                    metrics.pressure_rate,
                    metrics.pass_rush_win_rate,
                    metrics.coverage_success_rate,
                    metrics.missed_tackle_rate,
                    metrics.forced_incompletions,
                    metrics.qb_hits,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_game_advanced_metrics(
        self, dynasty_id: str, game_id: str
    ) -> List[AdvancedMetrics]:
        """Get advanced metrics for both teams in a game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT game_id, team_id,
                       epa_total, epa_passing, epa_rushing, epa_per_play,
                       success_rate, passing_success_rate, rushing_success_rate,
                       air_yards_total, yac_total, completion_pct_over_expected,
                       avg_time_to_throw, pressure_rate,
                       pass_rush_win_rate, coverage_success_rate, missed_tackle_rate,
                       forced_incompletions, qb_hits
                FROM advanced_game_metrics
                WHERE dynasty_id = ? AND game_id = ?
                """,
                (dynasty_id, game_id),
            )
            return [self._row_to_advanced_metrics(row, dynasty_id) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_team_advanced_metrics(
        self, dynasty_id: str, team_id: int, season: int, limit: int = 20
    ) -> List[AdvancedMetrics]:
        """Get advanced metrics history for a team."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT am.game_id, am.team_id,
                       am.epa_total, am.epa_passing, am.epa_rushing, am.epa_per_play,
                       am.success_rate, am.passing_success_rate, am.rushing_success_rate,
                       am.air_yards_total, am.yac_total, am.completion_pct_over_expected,
                       am.avg_time_to_throw, am.pressure_rate,
                       am.pass_rush_win_rate, am.coverage_success_rate, am.missed_tackle_rate,
                       am.forced_incompletions, am.qb_hits
                FROM advanced_game_metrics am
                JOIN games g ON am.game_id = g.game_id AND am.dynasty_id = g.dynasty_id
                WHERE am.dynasty_id = ? AND am.team_id = ? AND g.season = ?
                ORDER BY g.week DESC
                LIMIT ?
                """,
                (dynasty_id, team_id, season, limit),
            )
            return [self._row_to_advanced_metrics(row, dynasty_id) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _row_to_advanced_metrics(
        self, row: sqlite3.Row, dynasty_id: str
    ) -> AdvancedMetrics:
        """Convert a database row to an AdvancedMetrics object."""
        return AdvancedMetrics(
            game_id=row["game_id"],
            team_id=row["team_id"],
            dynasty_id=dynasty_id,
            epa_total=row["epa_total"] or 0.0,
            epa_passing=row["epa_passing"] or 0.0,
            epa_rushing=row["epa_rushing"] or 0.0,
            epa_per_play=row["epa_per_play"],
            success_rate=row["success_rate"],
            passing_success_rate=row["passing_success_rate"],
            rushing_success_rate=row["rushing_success_rate"],
            air_yards_total=row["air_yards_total"] or 0,
            yac_total=row["yac_total"] or 0,
            completion_pct_over_expected=row["completion_pct_over_expected"],
            avg_time_to_throw=row["avg_time_to_throw"],
            pressure_rate=row["pressure_rate"],
            pass_rush_win_rate=row["pass_rush_win_rate"],
            coverage_success_rate=row["coverage_success_rate"],
            missed_tackle_rate=row["missed_tackle_rate"],
            forced_incompletions=row["forced_incompletions"] or 0,
            qb_hits=row["qb_hits"] or 0,
        )

    # =========================================================================
    # SEASON GRADE AGGREGATION
    # =========================================================================

    def aggregate_season_grades_from_stats(
        self,
        dynasty_id: str,
        season: int,
    ) -> int:
        """
        Generate player_season_grades from player_game_stats.

        This is a FALLBACK method when player_game_grades don't exist.
        It calculates synthetic grades based on raw statistics using
        position-specific formulas.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year to aggregate

        Returns:
            Number of player season grades created/updated
        """
        conn = self._get_connection()
        try:
            # First, delete existing season grades for this dynasty/season
            conn.execute(
                "DELETE FROM player_season_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )

            # SIMPLIFIED aggregation for performance
            # Universal production-based formula instead of complex position-specific CASE
            cursor = conn.execute(
                """
                WITH player_stats AS (
                    SELECT
                        dynasty_id,
                        CAST(player_id AS INTEGER) as player_id,
                        team_id,
                        position,
                        COUNT(DISTINCT game_id) as games_played,
                        -- Total production stats
                        COALESCE(SUM(passing_yards), 0) + COALESCE(SUM(rushing_yards), 0) +
                            COALESCE(SUM(receiving_yards), 0) as total_yards,
                        COALESCE(SUM(passing_tds), 0) + COALESCE(SUM(rushing_tds), 0) +
                            COALESCE(SUM(receiving_tds), 0) as total_tds,
                        COALESCE(SUM(passing_interceptions), 0) +
                            COALESCE(SUM(rushing_fumbles), 0) as turnovers,
                        -- Defensive big plays
                        COALESCE(SUM(sacks), 0) as sacks,
                        COALESCE(SUM(interceptions), 0) as def_ints,
                        COALESCE(SUM(forced_fumbles), 0) as ff,
                        COALESCE(SUM(tackles_total), 0) as tackles,
                        -- Snaps
                        COALESCE(SUM(snap_counts_offense), 0) +
                            COALESCE(SUM(snap_counts_defense), 0) +
                            COALESCE(SUM(snap_counts_special_teams), 0) as total_snaps
                    FROM player_game_stats
                    WHERE dynasty_id = ? AND season_type = 'regular_season'
                    GROUP BY dynasty_id, player_id, team_id, position
                    HAVING games_played >= 1
                ),
                graded AS (
                    SELECT
                        dynasty_id, player_id, team_id, position, games_played, total_snaps,
                        -- SIMPLIFIED universal grade formula
                        MIN(100, MAX(30, 50 +
                            (CAST(total_yards AS REAL) / NULLIF(games_played, 0) / 20) +
                            (total_tds * 3) +
                            (sacks * 3) + (def_ints * 8) + (ff * 4) +
                            (CAST(tackles AS REAL) / NULLIF(games_played, 0)) -
                            (turnovers * 2)
                        )) as overall_grade
                    FROM player_stats
                ),
                ranked AS (
                    SELECT *,
                        RANK() OVER (PARTITION BY position ORDER BY overall_grade DESC) AS position_rank,
                        RANK() OVER (ORDER BY overall_grade DESC) AS overall_rank
                    FROM graded
                )
                INSERT INTO player_season_grades (
                    dynasty_id, season, player_id, team_id, position,
                    overall_grade, total_snaps, games_graded, position_rank, overall_rank
                )
                SELECT
                    dynasty_id, ?, player_id, team_id, position,
                    overall_grade, total_snaps, games_played, position_rank, overall_rank
                FROM ranked
                """,
                (dynasty_id, season),
            )
            conn.commit()

            # Get count of inserted rows
            count_cursor = conn.execute(
                "SELECT COUNT(*) FROM player_season_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )
            return count_cursor.fetchone()[0]

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def aggregate_season_grades_from_game_grades(
        self,
        dynasty_id: str,
        season: int,
    ) -> int:
        """
        Aggregate player_game_grades into player_season_grades.

        This method MUST be called before awards calculation to populate
        the player_season_grades table that the eligibility checker uses.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year to aggregate

        Returns:
            Number of player season grades created/updated
        """
        conn = self._get_connection()
        try:
            # First, delete existing season grades for this dynasty/season
            conn.execute(
                "DELETE FROM player_season_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )

            # Aggregate game grades into season grades with snap-weighted averages
            # and calculate ranks using window functions
            cursor = conn.execute(
                """
                WITH aggregated AS (
                    SELECT
                        dynasty_id,
                        season,
                        player_id,
                        team_id,
                        position,
                        -- Snap-weighted overall grade
                        SUM(overall_grade * (offensive_snaps + defensive_snaps + special_teams_snaps)) /
                            NULLIF(SUM(offensive_snaps + defensive_snaps + special_teams_snaps), 0)
                            AS overall_grade,
                        -- Average positional grades (NULL if no data)
                        AVG(CASE WHEN passing_grade IS NOT NULL THEN passing_grade END) AS passing_grade,
                        AVG(CASE WHEN rushing_grade IS NOT NULL THEN rushing_grade END) AS rushing_grade,
                        AVG(CASE WHEN receiving_grade IS NOT NULL THEN receiving_grade END) AS receiving_grade,
                        AVG(CASE WHEN pass_blocking_grade IS NOT NULL THEN pass_blocking_grade END) AS pass_blocking_grade,
                        AVG(CASE WHEN run_blocking_grade IS NOT NULL THEN run_blocking_grade END) AS run_blocking_grade,
                        AVG(CASE WHEN pass_rush_grade IS NOT NULL THEN pass_rush_grade END) AS pass_rush_grade,
                        AVG(CASE WHEN run_defense_grade IS NOT NULL THEN run_defense_grade END) AS run_defense_grade,
                        AVG(CASE WHEN coverage_grade IS NOT NULL THEN coverage_grade END) AS coverage_grade,
                        AVG(CASE WHEN tackling_grade IS NOT NULL THEN tackling_grade END) AS tackling_grade,
                        -- Totals
                        SUM(offensive_snaps + defensive_snaps + special_teams_snaps) AS total_snaps,
                        COUNT(DISTINCT game_id) AS games_graded,
                        SUM(play_count) AS total_plays_graded,
                        -- Positive play rate
                        CAST(SUM(positive_plays) AS REAL) /
                            NULLIF(SUM(positive_plays + negative_plays), 0) AS positive_play_rate,
                        -- EPA metrics
                        SUM(epa_total) AS epa_total,
                        SUM(epa_total) / NULLIF(SUM(play_count), 0) AS epa_per_play
                    FROM player_game_grades
                    WHERE dynasty_id = ? AND season = ?
                    GROUP BY dynasty_id, season, player_id, team_id, position
                    HAVING total_snaps > 0
                ),
                ranked AS (
                    SELECT
                        *,
                        RANK() OVER (PARTITION BY position ORDER BY overall_grade DESC) AS position_rank,
                        RANK() OVER (ORDER BY overall_grade DESC) AS overall_rank
                    FROM aggregated
                )
                INSERT INTO player_season_grades (
                    dynasty_id, season, player_id, team_id, position,
                    overall_grade, passing_grade, rushing_grade, receiving_grade,
                    pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                    run_defense_grade, coverage_grade, tackling_grade,
                    total_snaps, games_graded, total_plays_graded, positive_play_rate,
                    epa_total, epa_per_play, position_rank, overall_rank
                )
                SELECT
                    dynasty_id, season, player_id, team_id, position,
                    overall_grade, passing_grade, rushing_grade, receiving_grade,
                    pass_blocking_grade, run_blocking_grade, pass_rush_grade,
                    run_defense_grade, coverage_grade, tackling_grade,
                    total_snaps, games_graded, total_plays_graded, positive_play_rate,
                    epa_total, epa_per_play, position_rank, overall_rank
                FROM ranked
                """,
                (dynasty_id, season),
            )
            conn.commit()
            return cursor.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def season_grades_exist(self, dynasty_id: str, season: int) -> bool:
        """
        Check if season grades already exist for this dynasty/season.

        Used to skip expensive aggregation if grades were already calculated.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if season grades exist, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM player_season_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )
            count = cursor.fetchone()[0]
            return count > 0
        except Exception:
            return False
        finally:
            conn.close()

    def game_grades_exist(self, dynasty_id: str, season: int) -> bool:
        """
        Check if game grades exist for this dynasty/season.

        Used to determine whether to aggregate from game_grades (preferred)
        or fall back to stats-based grading.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            True if game grades exist, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM player_game_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )
            count = cursor.fetchone()[0]
            return count > 0
        except Exception:
            return False
        finally:
            conn.close()

    # =========================================================================
    # FAST CANDIDATE RETRIEVAL
    # =========================================================================

    def get_top_candidates_by_position(
        self,
        dynasty_id: str,
        season: int,
        min_games: int = 12,
        min_snaps: int = 50,  # Lowered to 50 to allow K/P through; Python handles position-specific limits
        per_position_limit: int = 15,  # Kept for API compatibility but not used in SQL
    ) -> List[Dict[str, Any]]:
        """
        Get all eligible candidates with SQL-level filtering.

        This is a FAST alternative to get_all_season_grades() that:
        1. Filters by minimum games played
        2. Filters by minimum snaps played
        3. JOINs player info in single query
        4. Aggregates season stats from player_game_stats

        NOTE: Does NOT pre-rank by grade. Python-side scoring handles ranking
        to ensure top statistical performers aren't filtered out before scoring.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            min_games: Minimum games played (default 12 = 67% of season)
            min_snaps: Minimum snaps played (default 100)
            per_position_limit: Kept for API compatibility (ranking done in Python)

        Returns:
            List of candidate dicts with all needed fields for awards
        """
        conn = self._get_connection()
        try:
            # First, get the season stats aggregated by player
            # We need to extract season from game_id (format: "YYYY_WXX_AWAY_HOME")
            cursor = conn.execute(
                """
                WITH season_stats AS (
                    SELECT
                        pgs.player_id,
                        SUM(pgs.passing_yards) as passing_yards,
                        SUM(pgs.passing_tds) as passing_tds,
                        SUM(pgs.passing_interceptions) as passing_interceptions,
                        CASE
                            WHEN SUM(pgs.passing_attempts) > 0
                            THEN (SUM(pgs.passing_completions) * 100.0 / SUM(pgs.passing_attempts))
                            ELSE 0
                        END as completion_pct,
                        SUM(pgs.rushing_yards) as rushing_yards,
                        SUM(pgs.rushing_tds) as rushing_tds,
                        SUM(pgs.receiving_yards) as receiving_yards,
                        SUM(pgs.receiving_tds) as receiving_tds,
                        SUM(pgs.receptions) as receptions,
                        SUM(pgs.sacks) as sacks,
                        SUM(pgs.interceptions) as interceptions,
                        SUM(pgs.tackles_total) as tackles_total,
                        SUM(pgs.forced_fumbles) as forced_fumbles
                    FROM player_game_stats pgs
                    INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                    WHERE pgs.dynasty_id = ?
                        AND g.season = ?
                        AND pgs.season_type = 'regular_season'
                    GROUP BY pgs.player_id
                ),
                eligible_candidates AS (
                    SELECT
                        psg.player_id,
                        psg.team_id,
                        psg.position,
                        psg.overall_grade,
                        psg.passing_grade,
                        psg.rushing_grade,
                        psg.receiving_grade,
                        psg.tackling_grade,
                        psg.pass_blocking_grade,
                        psg.run_blocking_grade,
                        psg.pass_rush_grade,
                        psg.run_defense_grade,
                        psg.coverage_grade,
                        psg.games_graded,
                        psg.total_snaps,
                        psg.position_rank,
                        psg.overall_rank,
                        psg.epa_total,
                        p.first_name,
                        p.last_name,
                        p.years_pro,
                        p.birthdate,
                        -- Season stats from aggregation
                        COALESCE(ss.passing_yards, 0) as passing_yards,
                        COALESCE(ss.passing_tds, 0) as passing_tds,
                        COALESCE(ss.passing_interceptions, 0) as passing_interceptions,
                        COALESCE(ss.completion_pct, 0) as completion_pct,
                        COALESCE(ss.rushing_yards, 0) as rushing_yards,
                        COALESCE(ss.rushing_tds, 0) as rushing_tds,
                        COALESCE(ss.receiving_yards, 0) as receiving_yards,
                        COALESCE(ss.receiving_tds, 0) as receiving_tds,
                        COALESCE(ss.receptions, 0) as receptions,
                        COALESCE(ss.sacks, 0) as sacks,
                        COALESCE(ss.interceptions, 0) as interceptions,
                        COALESCE(ss.tackles_total, 0) as tackles_total,
                        COALESCE(ss.forced_fumbles, 0) as forced_fumbles
                    FROM player_season_grades psg
                    JOIN players p ON psg.dynasty_id = p.dynasty_id
                        AND psg.player_id = p.player_id
                    LEFT JOIN season_stats ss ON CAST(psg.player_id AS TEXT) = ss.player_id
                    WHERE psg.dynasty_id = ?
                        AND psg.season = ?
                        AND psg.games_graded >= ?
                        AND psg.total_snaps >= ?
                        AND psg.overall_grade >= 50
                )
                SELECT * FROM eligible_candidates
                ORDER BY overall_grade DESC
                """,
                (dynasty_id, season, dynasty_id, season, min_games, min_snaps),
            )

            results = []
            for row in cursor.fetchall():
                # Calculate passer rating from component stats
                # Indices shifted due to birthdate column added after years_pro
                passing_yards = row[22] or 0
                passing_tds = row[23] or 0
                passing_ints = row[24] or 0
                completion_pct = row[25] or 0

                # Simplified passer rating approximation
                passer_rating = 0.0
                if passing_yards > 0:
                    # Basic passer rating formula approximation
                    passer_rating = min(158.3, max(0,
                        (completion_pct * 0.5) +
                        (passing_tds * 5) +
                        (passing_yards / 100) -
                        (passing_ints * 3)
                    ))

                # Calculate years_pro from birthdate if not set
                years_pro = row[20] or 0
                birthdate = row[21]
                if years_pro == 0 and birthdate:
                    try:
                        birth_year = int(birthdate[:4])
                        entry_year = birth_year + 22  # Assume entry at age 22
                        years_pro = max(0, season - entry_year)
                    except (ValueError, TypeError):
                        years_pro = 0

                results.append({
                    'player_id': row[0],
                    'team_id': row[1],
                    'position': row[2],
                    'overall_grade': row[3],
                    'passing_grade': row[4],
                    'rushing_grade': row[5],
                    'receiving_grade': row[6],
                    'tackling_grade': row[7],
                    'pass_blocking_grade': row[8],
                    'run_blocking_grade': row[9],
                    'pass_rush_grade': row[10],
                    'run_defense_grade': row[11],
                    'coverage_grade': row[12],
                    'games_graded': row[13],
                    'total_snaps': row[14],
                    'position_rank': row[15],
                    'overall_rank': row[16],
                    'epa_total': row[17],
                    'first_name': row[18],
                    'last_name': row[19],
                    'years_pro': years_pro,  # Calculated from birthdate if needed
                    'player_name': f"{row[18]} {row[19]}".strip(),
                    # Season stats (indices shifted by 1 due to birthdate)
                    'passing_yards': passing_yards,
                    'passing_tds': passing_tds,
                    'passing_interceptions': passing_ints,
                    'passer_rating': passer_rating,
                    'rushing_yards': row[26] or 0,
                    'rushing_tds': row[27] or 0,
                    'receiving_yards': row[28] or 0,
                    'receiving_tds': row[29] or 0,
                    'receptions': row[30] or 0,
                    'sacks': row[31] or 0,
                    'interceptions': row[32] or 0,
                    'tackles_total': row[33] or 0,
                    'forced_fumbles': row[34] or 0,
                })

            return results

        except Exception:
            raise
        finally:
            conn.close()

    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================

    def delete_game_grades(self, dynasty_id: str, game_id: str) -> int:
        """Delete all game grades for a specific game."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM player_game_grades WHERE dynasty_id = ? AND game_id = ?",
                (dynasty_id, game_id),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def delete_season_grades(self, dynasty_id: str, season: int) -> int:
        """Delete all season grades for a specific season."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM player_season_grades WHERE dynasty_id = ? AND season = ?",
                (dynasty_id, season),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
