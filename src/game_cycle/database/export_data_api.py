"""
Export Data API for season-end statistics archival.

Provides streaming query access to game-level statistics data for CSV export.
Uses generators to handle large datasets efficiently without loading all data into memory.
"""

import sqlite3
from dataclasses import dataclass
from typing import Generator, List, Tuple, Any, Optional

from .connection import GameCycleDatabase


@dataclass
class TableRowCount:
    """Row count for a table in a specific dynasty/season."""
    table_name: str
    dynasty_id: str
    season: int
    row_count: int


class ExportDataAPI:
    """
    API for streaming export of game-level statistics.

    Provides efficient streaming queries for:
    - player_game_stats
    - player_game_grades
    - box_scores

    Uses generators to handle large datasets (30K+ rows per season)
    without loading all data into memory.
    """

    # Column names for each table (used for CSV headers)
    PLAYER_GAME_STATS_COLUMNS = [
        'id', 'dynasty_id', 'game_id', 'season_type', 'player_id', 'player_name',
        'team_id', 'position', 'passing_yards', 'passing_tds', 'passing_attempts',
        'passing_completions', 'passing_interceptions', 'passing_sacks',
        'passing_sack_yards', 'passing_rating', 'rushing_yards', 'rushing_tds',
        'rushing_attempts', 'rushing_long', 'rushing_fumbles', 'receiving_yards',
        'receiving_tds', 'receptions', 'targets', 'receiving_long', 'receiving_drops',
        'tackles_total', 'tackles_solo', 'tackles_assist', 'sacks', 'interceptions',
        'forced_fumbles', 'fumbles_recovered', 'passes_defended', 'field_goals_made',
        'field_goals_attempted', 'extra_points_made', 'extra_points_attempted',
        'punts', 'punt_yards', 'pass_blocks', 'pancakes', 'sacks_allowed',
        'hurries_allowed', 'pressures_allowed', 'run_blocking_grade',
        'pass_blocking_efficiency', 'missed_assignments', 'holding_penalties',
        'false_start_penalties', 'downfield_blocks', 'double_team_blocks',
        'chip_blocks', 'snap_counts_offense', 'snap_counts_defense',
        'snap_counts_special_teams', 'fantasy_points'
    ]

    PLAYER_GAME_GRADES_COLUMNS = [
        'id', 'dynasty_id', 'game_id', 'season', 'week', 'player_id', 'team_id',
        'position', 'overall_grade', 'passing_grade', 'rushing_grade',
        'receiving_grade', 'pass_blocking_grade', 'run_blocking_grade',
        'pass_rush_grade', 'run_defense_grade', 'coverage_grade', 'tackling_grade',
        'offensive_snaps', 'defensive_snaps', 'special_teams_snaps', 'epa_total',
        'success_rate', 'play_count', 'positive_plays', 'negative_plays', 'created_at'
    ]

    BOX_SCORES_COLUMNS = [
        'id', 'dynasty_id', 'game_id', 'team_id', 'q1_score', 'q2_score',
        'q3_score', 'q4_score', 'ot_score', 'first_downs', 'third_down_att',
        'third_down_conv', 'fourth_down_att', 'fourth_down_conv', 'total_yards',
        'passing_yards', 'rushing_yards', 'turnovers', 'penalties', 'penalty_yards',
        'time_of_possession'
    ]

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Row Count Methods --------------------

    def get_row_count(
        self,
        table_name: str,
        dynasty_id: str,
        season: int
    ) -> int:
        """
        Get the row count for a table filtered by dynasty and season.

        Args:
            table_name: Name of the table
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Number of rows matching the filter
        """
        # Map table names to their season column
        season_columns = {
            'player_game_stats': None,  # Uses game_id join
            'player_game_grades': 'season',
            'box_scores': None,  # Uses game_id join
        }

        if table_name not in season_columns:
            raise ValueError(f"Unknown table: {table_name}")

        season_col = season_columns[table_name]

        if season_col:
            # Direct season column
            sql = f"SELECT COUNT(*) FROM {table_name} WHERE dynasty_id = ? AND {season_col} = ?"
            result = self.db.execute(sql, (dynasty_id, season))
        else:
            # Join with games table to filter by season
            sql = f"""
                SELECT COUNT(*)
                FROM {table_name} t
                JOIN games g ON t.game_id = g.game_id AND t.dynasty_id = g.dynasty_id
                WHERE t.dynasty_id = ? AND g.season = ?
            """
            result = self.db.execute(sql, (dynasty_id, season))

        row = result.fetchone()
        return row[0] if row else 0

    def get_all_row_counts(
        self,
        dynasty_id: str,
        season: int
    ) -> List[TableRowCount]:
        """
        Get row counts for all exportable tables.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of TableRowCount for each table
        """
        tables = ['player_game_stats', 'player_game_grades', 'box_scores']
        return [
            TableRowCount(
                table_name=table,
                dynasty_id=dynasty_id,
                season=season,
                row_count=self.get_row_count(table, dynasty_id, season)
            )
            for table in tables
        ]

    # -------------------- Streaming Export Methods --------------------

    def stream_player_game_stats(
        self,
        dynasty_id: str,
        season: int,
        batch_size: int = 5000
    ) -> Generator[List[Tuple[Any, ...]], None, None]:
        """
        Stream player_game_stats rows for a season in batches.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            batch_size: Number of rows per batch

        Yields:
            Lists of row tuples
        """
        sql = """
            SELECT t.*
            FROM player_game_stats t
            JOIN games g ON t.game_id = g.game_id AND t.dynasty_id = g.dynasty_id
            WHERE t.dynasty_id = ? AND g.season = ?
            ORDER BY t.id
        """
        yield from self._stream_query(sql, (dynasty_id, season), batch_size)

    def stream_player_game_grades(
        self,
        dynasty_id: str,
        season: int,
        batch_size: int = 5000
    ) -> Generator[List[Tuple[Any, ...]], None, None]:
        """
        Stream player_game_grades rows for a season in batches.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            batch_size: Number of rows per batch

        Yields:
            Lists of row tuples
        """
        sql = """
            SELECT *
            FROM player_game_grades
            WHERE dynasty_id = ? AND season = ?
            ORDER BY id
        """
        yield from self._stream_query(sql, (dynasty_id, season), batch_size)

    def stream_box_scores(
        self,
        dynasty_id: str,
        season: int,
        batch_size: int = 5000
    ) -> Generator[List[Tuple[Any, ...]], None, None]:
        """
        Stream box_scores rows for a season in batches.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            batch_size: Number of rows per batch

        Yields:
            Lists of row tuples
        """
        sql = """
            SELECT t.*
            FROM box_scores t
            JOIN games g ON t.game_id = g.game_id AND t.dynasty_id = g.dynasty_id
            WHERE t.dynasty_id = ? AND g.season = ?
            ORDER BY t.id
        """
        yield from self._stream_query(sql, (dynasty_id, season), batch_size)

    def _stream_query(
        self,
        sql: str,
        params: Tuple[Any, ...],
        batch_size: int
    ) -> Generator[List[Tuple[Any, ...]], None, None]:
        """
        Execute a query and yield results in batches.

        Args:
            sql: SQL query string
            params: Query parameters
            batch_size: Number of rows per batch

        Yields:
            Lists of row tuples
        """
        cursor = self.db.execute(sql, params)

        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield batch

    # -------------------- Column Info Methods --------------------

    def get_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column names
        """
        column_map = {
            'player_game_stats': self.PLAYER_GAME_STATS_COLUMNS,
            'player_game_grades': self.PLAYER_GAME_GRADES_COLUMNS,
            'box_scores': self.BOX_SCORES_COLUMNS,
        }

        if table_name not in column_map:
            raise ValueError(f"Unknown table: {table_name}")

        return column_map[table_name]

    # -------------------- Season Discovery Methods --------------------

    def get_seasons_with_data(self, dynasty_id: str) -> List[int]:
        """
        Get all seasons that have game data for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            List of season years with game data, sorted ascending
        """
        sql = """
            SELECT DISTINCT season
            FROM games
            WHERE dynasty_id = ?
            ORDER BY season ASC
        """
        result = self.db.execute(sql, (dynasty_id,))
        return [row[0] for row in result.fetchall()]

    def get_oldest_season(self, dynasty_id: str) -> Optional[int]:
        """
        Get the oldest season with game data.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Oldest season year, or None if no data
        """
        seasons = self.get_seasons_with_data(dynasty_id)
        return seasons[0] if seasons else None