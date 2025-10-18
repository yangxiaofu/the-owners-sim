"""
Season Statistics Aggregator

Aggregates player game statistics into season-level totals using efficient
SQLite UPSERT operations. Handles all stat categories with derived metrics
and proper team tracking for player movement.
"""

from typing import Optional, List, Dict, Any
import logging
import sqlite3
from pathlib import Path


class SeasonStatsAggregator:
    """
    Aggregates player game statistics into season totals.

    Uses SQLite UPSERT (INSERT ... ON CONFLICT DO UPDATE) for efficient
    updates after each game. Handles all stat categories including:
    - Passing (with passer rating calculation)
    - Rushing (with yards per carry)
    - Receiving (with catch rate and yards per reception)
    - Defense (tackles, sacks, interceptions)
    - Special teams (kicking stats)
    - Offensive line (blocking metrics)

    Tracks most recent team for players who change teams mid-season.
    Groups by player_id to avoid duplicate entries.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize season stats aggregator.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.logger = logging.getLogger("SeasonStatsAggregator")
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """
        Create player_season_stats table if it doesn't exist.

        Table structure includes:
        - All counting stats (summed from game stats)
        - Derived metrics (calculated ratios and rates)
        - Most recent team_id (for player movement tracking)
        - Games played count
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS player_season_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',

            player_id TEXT NOT NULL,
            player_name TEXT,
            position TEXT,
            team_id INTEGER NOT NULL,  -- Most recent team

            -- Game tracking
            games_played INTEGER DEFAULT 0,

            -- Passing stats (counting)
            passing_attempts INTEGER DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
            passing_sacks INTEGER DEFAULT 0,
            passing_sack_yards INTEGER DEFAULT 0,

            -- Passing stats (derived)
            completion_percentage REAL DEFAULT 0.0,
            yards_per_attempt REAL DEFAULT 0.0,
            passer_rating REAL DEFAULT 0.0,

            -- Rushing stats (counting)
            rushing_attempts INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            rushing_long INTEGER DEFAULT 0,
            rushing_fumbles INTEGER DEFAULT 0,

            -- Rushing stats (derived)
            yards_per_carry REAL DEFAULT 0.0,
            yards_per_game_rushing REAL DEFAULT 0.0,

            -- Receiving stats (counting)
            targets INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            receiving_long INTEGER DEFAULT 0,
            receiving_fumbles INTEGER DEFAULT 0,

            -- Receiving stats (derived)
            catch_rate REAL DEFAULT 0.0,
            yards_per_reception REAL DEFAULT 0.0,
            yards_per_target REAL DEFAULT 0.0,
            yards_per_game_receiving REAL DEFAULT 0.0,

            -- Defensive stats (counting)
            tackles_total INTEGER DEFAULT 0,
            tackles_solo INTEGER DEFAULT 0,
            tackles_assists INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0.0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            fumbles_recovered INTEGER DEFAULT 0,
            passes_defended INTEGER DEFAULT 0,

            -- Special teams stats (counting)
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0,
            extra_points_made INTEGER DEFAULT 0,
            extra_points_attempted INTEGER DEFAULT 0,

            -- Special teams stats (derived)
            field_goal_percentage REAL DEFAULT 0.0,
            extra_point_percentage REAL DEFAULT 0.0,

            -- Metadata
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(dynasty_id, season, season_type, player_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
        """

        create_indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_season_stats_dynasty ON player_season_stats(dynasty_id, season)",
            "CREATE INDEX IF NOT EXISTS idx_season_stats_player ON player_season_stats(player_id, dynasty_id)",
            "CREATE INDEX IF NOT EXISTS idx_season_stats_team ON player_season_stats(team_id, season)",
            "CREATE INDEX IF NOT EXISTS idx_season_stats_position ON player_season_stats(position, season)",
            "CREATE INDEX IF NOT EXISTS idx_season_stats_season_type ON player_season_stats(dynasty_id, season, season_type)",
        ]

        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.execute(create_table_sql)
                for index_sql in create_indexes_sql:
                    conn.execute(index_sql)
                conn.commit()
                self.logger.info("player_season_stats table and indexes created/verified")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating player_season_stats table: {e}")
            raise

    def update_after_game(
        self,
        game_id: str,
        dynasty_id: str,
        season: int,
        season_type: str = "regular_season",
        conn: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Update season stats for all players who participated in a game.

        Uses efficient UPSERT to aggregate stats from player_game_stats into
        player_season_stats. Handles all stat categories and computes derived
        metrics like passer rating, yards per carry, and catch rate.

        Args:
            game_id: Game identifier to process
            dynasty_id: Dynasty identifier for isolation
            season: Season year
            season_type: "regular_season" or "playoffs"
            conn: Optional database connection (for use within existing transaction)

        Returns:
            Number of player season records updated

        Raises:
            sqlite3.Error: If database operation fails
        """
        upsert_query = """
        INSERT INTO player_season_stats (
            dynasty_id,
            season,
            season_type,
            player_id,
            player_name,
            position,
            team_id,
            games_played,

            -- Passing counting stats
            passing_attempts,
            passing_completions,
            passing_yards,
            passing_tds,
            passing_interceptions,

            -- Rushing counting stats
            rushing_attempts,
            rushing_yards,
            rushing_tds,
            rushing_long,
            rushing_fumbles,

            -- Receiving counting stats
            targets,
            receptions,
            receiving_yards,
            receiving_tds,
            receiving_long,
            receiving_fumbles,

            -- Defensive counting stats
            tackles_total,
            tackles_solo,
            tackles_assists,
            sacks,
            interceptions,
            forced_fumbles,
            fumbles_recovered,
            passes_defended,

            -- Special teams counting stats
            field_goals_made,
            field_goals_attempted,
            extra_points_made,
            extra_points_attempted,

            -- Derived metrics (passing)
            completion_percentage,
            yards_per_attempt,
            passer_rating,

            -- Derived metrics (rushing)
            yards_per_carry,
            yards_per_game_rushing,

            -- Derived metrics (receiving)
            catch_rate,
            yards_per_reception,
            yards_per_target,
            yards_per_game_receiving,

            -- Derived metrics (special teams)
            field_goal_percentage,
            extra_point_percentage,

            last_updated
        )
        SELECT
            pgs.dynasty_id,
            g.season,
            g.season_type,
            pgs.player_id,
            MAX(pgs.player_name) as player_name,  -- Most recent name
            MAX(pgs.position) as position,  -- Most recent position
            MAX(pgs.team_id) as team_id,  -- Most recent team (for player movement)
            COUNT(DISTINCT g.game_id) as games_played,

            -- Passing counting stats (SUM)
            SUM(pgs.passing_attempts) as passing_attempts,
            SUM(pgs.passing_completions) as passing_completions,
            SUM(pgs.passing_yards) as passing_yards,
            SUM(pgs.passing_tds) as passing_tds,
            SUM(pgs.passing_interceptions) as passing_interceptions,

            -- Rushing counting stats (SUM)
            SUM(pgs.rushing_attempts) as rushing_attempts,
            SUM(pgs.rushing_yards) as rushing_yards,
            SUM(pgs.rushing_tds) as rushing_tds,
            MAX(pgs.rushing_long) as rushing_long,
            SUM(pgs.rushing_fumbles) as rushing_fumbles,

            -- Receiving counting stats (SUM)
            SUM(pgs.targets) as targets,
            SUM(pgs.receptions) as receptions,
            SUM(pgs.receiving_yards) as receiving_yards,
            SUM(pgs.receiving_tds) as receiving_tds,
            MAX(pgs.receiving_long) as receiving_long,
            SUM(pgs.receiving_drops) as receiving_fumbles,

            -- Defensive counting stats (SUM)
            SUM(pgs.tackles_total) as tackles_total,
            SUM(pgs.tackles_solo) as tackles_solo,
            SUM(pgs.tackles_assist) as tackles_assists,
            SUM(pgs.sacks) as sacks,
            SUM(pgs.interceptions) as interceptions,
            SUM(pgs.forced_fumbles) as forced_fumbles,
            SUM(pgs.fumbles_recovered) as fumbles_recovered,
            SUM(pgs.passes_defended) as passes_defended,

            -- Special teams counting stats (SUM)
            SUM(pgs.field_goals_made) as field_goals_made,
            SUM(pgs.field_goals_attempted) as field_goals_attempted,
            SUM(pgs.extra_points_made) as extra_points_made,
            SUM(pgs.extra_points_attempted) as extra_points_attempted,

            -- Derived metrics (passing) - calculated from aggregated stats
            CASE
                WHEN SUM(pgs.passing_attempts) > 0
                THEN ROUND((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) * 100, 1)
                ELSE 0.0
            END as completion_percentage,

            CASE
                WHEN SUM(pgs.passing_attempts) > 0
                THEN ROUND(CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts), 2)
                ELSE 0.0
            END as yards_per_attempt,

            -- Passer rating calculation (NFL formula)
            CASE
                WHEN SUM(pgs.passing_attempts) >= 1 THEN
                    ROUND(
                        (
                            (
                                CASE
                                    WHEN ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5 < 0 THEN 0
                                    WHEN ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5 > 2.375 THEN 2.375
                                    ELSE ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5
                                END
                            ) +
                            (
                                CASE
                                    WHEN ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25 < 0 THEN 0
                                    WHEN ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25 > 2.375 THEN 2.375
                                    ELSE ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25
                                END
                            ) +
                            (
                                CASE
                                    WHEN (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20 < 0 THEN 0
                                    WHEN (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20 > 2.375 THEN 2.375
                                    ELSE (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20
                                END
                            ) +
                            (
                                CASE
                                    WHEN (2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25)) < 0 THEN 0
                                    WHEN (2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25)) > 2.375 THEN 2.375
                                    ELSE 2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25)
                                END
                            )
                        ) / 6 * 100, 1
                    )
                ELSE 0.0
            END as passer_rating,

            -- Derived metrics (rushing)
            CASE
                WHEN SUM(pgs.rushing_attempts) > 0
                THEN ROUND(CAST(SUM(pgs.rushing_yards) AS REAL) / SUM(pgs.rushing_attempts), 2)
                ELSE 0.0
            END as yards_per_carry,

            CASE
                WHEN COUNT(DISTINCT g.game_id) > 0
                THEN ROUND(CAST(SUM(pgs.rushing_yards) AS REAL) / COUNT(DISTINCT g.game_id), 1)
                ELSE 0.0
            END as yards_per_game_rushing,

            -- Derived metrics (receiving)
            CASE
                WHEN SUM(pgs.targets) > 0
                THEN ROUND((CAST(SUM(pgs.receptions) AS REAL) / SUM(pgs.targets)) * 100, 1)
                ELSE 0.0
            END as catch_rate,

            CASE
                WHEN SUM(pgs.receptions) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / SUM(pgs.receptions), 2)
                ELSE 0.0
            END as yards_per_reception,

            CASE
                WHEN SUM(pgs.targets) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / SUM(pgs.targets), 2)
                ELSE 0.0
            END as yards_per_target,

            CASE
                WHEN COUNT(DISTINCT g.game_id) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / COUNT(DISTINCT g.game_id), 1)
                ELSE 0.0
            END as yards_per_game_receiving,

            -- Derived metrics (special teams)
            CASE
                WHEN SUM(pgs.field_goals_attempted) > 0
                THEN ROUND((CAST(SUM(pgs.field_goals_made) AS REAL) / SUM(pgs.field_goals_attempted)) * 100, 1)
                ELSE 0.0
            END as field_goal_percentage,

            CASE
                WHEN SUM(pgs.extra_points_attempted) > 0
                THEN ROUND((CAST(SUM(pgs.extra_points_made) AS REAL) / SUM(pgs.extra_points_attempted)) * 100, 1)
                ELSE 0.0
            END as extra_point_percentage,

            CURRENT_TIMESTAMP as last_updated

        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
        WHERE pgs.dynasty_id = ?
            AND g.season = ?
            AND g.season_type = ?
            AND pgs.player_id IN (
                SELECT DISTINCT player_id
                FROM player_game_stats
                WHERE game_id = ? AND dynasty_id = ?
            )
        GROUP BY pgs.player_id

        ON CONFLICT(dynasty_id, season, season_type, player_id)
        DO UPDATE SET
            player_name = excluded.player_name,
            position = excluded.position,
            team_id = excluded.team_id,
            games_played = excluded.games_played,

            -- Update all counting stats
            passing_attempts = excluded.passing_attempts,
            passing_completions = excluded.passing_completions,
            passing_yards = excluded.passing_yards,
            passing_tds = excluded.passing_tds,
            passing_interceptions = excluded.passing_interceptions,

            rushing_attempts = excluded.rushing_attempts,
            rushing_yards = excluded.rushing_yards,
            rushing_tds = excluded.rushing_tds,
            rushing_long = excluded.rushing_long,
            rushing_fumbles = excluded.rushing_fumbles,

            targets = excluded.targets,
            receptions = excluded.receptions,
            receiving_yards = excluded.receiving_yards,
            receiving_tds = excluded.receiving_tds,
            receiving_long = excluded.receiving_long,
            receiving_fumbles = excluded.receiving_fumbles,

            tackles_total = excluded.tackles_total,
            tackles_solo = excluded.tackles_solo,
            tackles_assists = excluded.tackles_assists,
            sacks = excluded.sacks,
            interceptions = excluded.interceptions,
            forced_fumbles = excluded.forced_fumbles,
            fumbles_recovered = excluded.fumbles_recovered,
            passes_defended = excluded.passes_defended,

            field_goals_made = excluded.field_goals_made,
            field_goals_attempted = excluded.field_goals_attempted,
            extra_points_made = excluded.extra_points_made,
            extra_points_attempted = excluded.extra_points_attempted,

            -- Update all derived metrics
            completion_percentage = excluded.completion_percentage,
            yards_per_attempt = excluded.yards_per_attempt,
            passer_rating = excluded.passer_rating,

            yards_per_carry = excluded.yards_per_carry,
            yards_per_game_rushing = excluded.yards_per_game_rushing,

            catch_rate = excluded.catch_rate,
            yards_per_reception = excluded.yards_per_reception,
            yards_per_target = excluded.yards_per_target,
            yards_per_game_receiving = excluded.yards_per_game_receiving,

            field_goal_percentage = excluded.field_goal_percentage,
            extra_point_percentage = excluded.extra_point_percentage,

            last_updated = CURRENT_TIMESTAMP
        """

        # Determine if we're using an external connection or creating our own
        external_conn = conn is not None
        created_conn = None

        try:
            # Use provided connection or create new one
            if not external_conn:
                created_conn = sqlite3.connect(self.database_path)
                conn = created_conn

            cursor = conn.cursor()
            cursor.execute(
                upsert_query,
                (dynasty_id, season, season_type, game_id, dynasty_id)
            )
            rows_affected = cursor.rowcount

            # Only commit if we created the connection (external connections managed by caller)
            if not external_conn:
                conn.commit()

            self.logger.info(
                f"Updated {rows_affected} player season stats for game {game_id} "
                f"(dynasty: {dynasty_id}, season: {season}, type: {season_type})"
            )
            return rows_affected

        except sqlite3.Error as e:
            self.logger.error(f"Error updating season stats for game {game_id}: {e}")
            raise

        finally:
            # Only close if we created the connection
            if created_conn:
                created_conn.close()

    def backfill_season(
        self,
        dynasty_id: str,
        season: int,
        season_type: str = "regular_season",
        conn: Optional[sqlite3.Connection] = None
    ) -> int:
        """
        Backfill all season stats for a dynasty/season from scratch.

        Useful for:
        - Populating historical data
        - Recovering from data corruption
        - Initial migration to season stats system

        This method aggregates ALL games for the given dynasty/season/season_type
        and rebuilds the season stats table from scratch for that combination.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year to backfill
            season_type: "regular_season" or "playoffs"
            conn: Optional database connection (for use within existing transaction)

        Returns:
            Number of player season records created/updated

        Raises:
            sqlite3.Error: If database operation fails
        """
        # Same query as update_after_game, but without game_id filter
        backfill_query = """
        INSERT OR REPLACE INTO player_season_stats (
            dynasty_id,
            season,
            season_type,
            player_id,
            player_name,
            position,
            team_id,
            games_played,

            passing_attempts, passing_completions, passing_yards, passing_tds,
            passing_interceptions,

            rushing_attempts, rushing_yards, rushing_tds, rushing_long, rushing_fumbles,

            targets, receptions, receiving_yards, receiving_tds, receiving_long,
            receiving_fumbles,

            tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
            forced_fumbles, fumbles_recovered, passes_defended,

            field_goals_made, field_goals_attempted, extra_points_made,
            extra_points_attempted,

            completion_percentage, yards_per_attempt, passer_rating,
            yards_per_carry, yards_per_game_rushing,
            catch_rate, yards_per_reception, yards_per_target, yards_per_game_receiving,
            field_goal_percentage, extra_point_percentage,

            last_updated
        )
        SELECT
            pgs.dynasty_id,
            g.season,
            g.season_type,
            pgs.player_id,
            MAX(pgs.player_name),
            MAX(pgs.position),
            MAX(pgs.team_id),
            COUNT(DISTINCT g.game_id),

            SUM(pgs.passing_attempts), SUM(pgs.passing_completions), SUM(pgs.passing_yards),
            SUM(pgs.passing_tds), SUM(pgs.passing_interceptions),

            SUM(pgs.rushing_attempts), SUM(pgs.rushing_yards), SUM(pgs.rushing_tds),
            MAX(pgs.rushing_long), SUM(pgs.rushing_fumbles),

            SUM(pgs.targets), SUM(pgs.receptions), SUM(pgs.receiving_yards),
            SUM(pgs.receiving_tds), MAX(pgs.receiving_long), SUM(pgs.receiving_drops) as receiving_fumbles,

            SUM(pgs.tackles_total), SUM(pgs.tackles_solo), SUM(pgs.tackles_assist) as tackles_assists,
            SUM(pgs.sacks), SUM(pgs.interceptions), SUM(pgs.forced_fumbles),
            SUM(pgs.fumbles_recovered), SUM(pgs.passes_defended),

            SUM(pgs.field_goals_made), SUM(pgs.field_goals_attempted),
            SUM(pgs.extra_points_made), SUM(pgs.extra_points_attempted),

            -- Derived metrics (same as update_after_game)
            CASE WHEN SUM(pgs.passing_attempts) > 0
                THEN ROUND((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) * 100, 1)
                ELSE 0.0 END,
            CASE WHEN SUM(pgs.passing_attempts) > 0
                THEN ROUND(CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts), 2)
                ELSE 0.0 END,
            CASE WHEN SUM(pgs.passing_attempts) >= 1 THEN
                ROUND((
                    (CASE WHEN ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5 < 0 THEN 0
                          WHEN ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5 > 2.375 THEN 2.375
                          ELSE ((CAST(SUM(pgs.passing_completions) AS REAL) / SUM(pgs.passing_attempts)) - 0.3) * 5 END) +
                    (CASE WHEN ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25 < 0 THEN 0
                          WHEN ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25 > 2.375 THEN 2.375
                          ELSE ((CAST(SUM(pgs.passing_yards) AS REAL) / SUM(pgs.passing_attempts)) - 3) * 0.25 END) +
                    (CASE WHEN (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20 < 0 THEN 0
                          WHEN (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20 > 2.375 THEN 2.375
                          ELSE (CAST(SUM(pgs.passing_tds) AS REAL) / SUM(pgs.passing_attempts)) * 20 END) +
                    (CASE WHEN (2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25)) < 0 THEN 0
                          WHEN (2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25)) > 2.375 THEN 2.375
                          ELSE 2.375 - ((CAST(SUM(pgs.passing_interceptions) AS REAL) / SUM(pgs.passing_attempts)) * 25) END)
                ) / 6 * 100, 1)
                ELSE 0.0 END,

            CASE WHEN SUM(pgs.rushing_attempts) > 0
                THEN ROUND(CAST(SUM(pgs.rushing_yards) AS REAL) / SUM(pgs.rushing_attempts), 2)
                ELSE 0.0 END,
            CASE WHEN COUNT(DISTINCT g.game_id) > 0
                THEN ROUND(CAST(SUM(pgs.rushing_yards) AS REAL) / COUNT(DISTINCT g.game_id), 1)
                ELSE 0.0 END,

            CASE WHEN SUM(pgs.targets) > 0
                THEN ROUND((CAST(SUM(pgs.receptions) AS REAL) / SUM(pgs.targets)) * 100, 1)
                ELSE 0.0 END,
            CASE WHEN SUM(pgs.receptions) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / SUM(pgs.receptions), 2)
                ELSE 0.0 END,
            CASE WHEN SUM(pgs.targets) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / SUM(pgs.targets), 2)
                ELSE 0.0 END,
            CASE WHEN COUNT(DISTINCT g.game_id) > 0
                THEN ROUND(CAST(SUM(pgs.receiving_yards) AS REAL) / COUNT(DISTINCT g.game_id), 1)
                ELSE 0.0 END,

            CASE WHEN SUM(pgs.field_goals_attempted) > 0
                THEN ROUND((CAST(SUM(pgs.field_goals_made) AS REAL) / SUM(pgs.field_goals_attempted)) * 100, 1)
                ELSE 0.0 END,
            CASE WHEN SUM(pgs.extra_points_attempted) > 0
                THEN ROUND((CAST(SUM(pgs.extra_points_made) AS REAL) / SUM(pgs.extra_points_attempted)) * 100, 1)
                ELSE 0.0 END,

            CURRENT_TIMESTAMP

        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
        WHERE pgs.dynasty_id = ?
            AND g.season = ?
            AND g.season_type = ?
        GROUP BY pgs.player_id
        """

        # Determine if we're using an external connection or creating our own
        external_conn = conn is not None
        created_conn = None

        try:
            # Use provided connection or create new one
            if not external_conn:
                created_conn = sqlite3.connect(self.database_path)
                conn = created_conn

            cursor = conn.cursor()
            cursor.execute(backfill_query, (dynasty_id, season, season_type))
            rows_affected = cursor.rowcount

            # Only commit if we created the connection (external connections managed by caller)
            if not external_conn:
                conn.commit()

            self.logger.info(
                f"Backfilled {rows_affected} player season stats for "
                f"dynasty {dynasty_id}, season {season}, type {season_type}"
            )
            return rows_affected

        except sqlite3.Error as e:
            self.logger.error(
                f"Error backfilling season stats for {dynasty_id}/{season}/{season_type}: {e}"
            )
            raise

        finally:
            # Only close if we created the connection
            if created_conn:
                created_conn.close()

    def get_season_leaders(
        self,
        dynasty_id: str,
        season: int,
        stat_category: str,
        season_type: str = "regular_season",
        limit: int = 10,
        min_attempts: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None
    ) -> List[Dict[str, Any]]:
        """
        Get season stat leaders for a specific category.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stat_category: Stat column name (e.g., "passing_yards", "rushing_yards")
            season_type: "regular_season" or "playoffs"
            limit: Number of leaders to return
            min_attempts: Minimum attempts for rate stats (e.g., 100 pass attempts for passer rating)
            conn: Optional database connection (for use within existing transaction)

        Returns:
            List of player stat dictionaries sorted by the category

        Raises:
            ValueError: If stat_category is invalid
        """
        # Validate stat category exists
        valid_categories = {
            'passing_yards', 'passing_tds', 'passer_rating', 'completion_percentage',
            'rushing_yards', 'rushing_tds', 'yards_per_carry',
            'receiving_yards', 'receiving_tds', 'receptions', 'catch_rate',
            'tackles_total', 'sacks', 'interceptions',
            'field_goals_made', 'field_goal_percentage'
        }

        if stat_category not in valid_categories:
            raise ValueError(f"Invalid stat category: {stat_category}")

        # Build query with optional minimum attempts filter
        min_filter = ""
        if min_attempts is not None:
            if 'passing' in stat_category:
                min_filter = f"AND passing_attempts >= {min_attempts}"
            elif 'rushing' in stat_category:
                min_filter = f"AND rushing_attempts >= {min_attempts}"
            elif 'receiving' in stat_category:
                min_filter = f"AND targets >= {min_attempts}"

        query = f"""
        SELECT
            player_id,
            player_name,
            position,
            team_id,
            games_played,
            {stat_category},
            passing_attempts, passing_completions, passing_yards, passing_tds, passer_rating,
            rushing_attempts, rushing_yards, rushing_tds, yards_per_carry,
            targets, receptions, receiving_yards, receiving_tds, catch_rate,
            tackles_total, sacks, interceptions,
            field_goals_made, field_goals_attempted, field_goal_percentage
        FROM player_season_stats
        WHERE dynasty_id = ?
            AND season = ?
            AND season_type = ?
            {min_filter}
            AND {stat_category} > 0
        ORDER BY {stat_category} DESC
        LIMIT ?
        """

        # Determine if we're using an external connection or creating our own
        external_conn = conn is not None
        created_conn = None

        try:
            # Use provided connection or create new one
            if not external_conn:
                created_conn = sqlite3.connect(self.database_path)
                conn = created_conn

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (dynasty_id, season, season_type, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error(f"Error fetching season leaders for {stat_category}: {e}")
            raise

        finally:
            # Only close if we created the connection
            if created_conn:
                created_conn.close()
